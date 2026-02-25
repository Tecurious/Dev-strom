"""Dev-Strom FastAPI server.

Exposes endpoints for idea generation, expansion, export, and history.
All runs are persisted to PostgreSQL. Until auth is implemented, all
operations use the ANONYMOUS_USER_ID.
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from models.dto import ExpandRequest, ExportRequest, IdeasRequest

load_dotenv()

from graph import app as graph_app, expand_idea as graph_expand_idea
from services.export_formatter import idea_to_markdown
from services.run_service import get_run, load_history, save_expanded_idea, save_run

api = FastAPI(title="Dev-Strom")


# ── Idea Generation ───────────────────────────────────────────────────────────

@api.post("/ideas")
def post_ideas(body: IdeasRequest):
    """Generate project ideas and persist the run to the database."""
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Set OPENAI_API_KEY and TAVILY_API_KEY in .env",
        )

    inputs = {"tech_stack": body.tech_stack, "count": body.count}
    if body.domain and body.domain.strip():
        inputs["domain"] = body.domain.strip()
    if body.level and body.level.strip():
        inputs["level"] = body.level.strip()
    if body.enable_multi_query:
        inputs["enable_multi_query"] = True

    result = graph_app.invoke(inputs)
    ideas = result.get("ideas", [])
    if len(ideas) != body.count:
        raise HTTPException(
            status_code=500,
            detail=f"Expected {body.count} ideas from graph, got {len(ideas)}",
        )

    # Attach 1-based position IDs
    out = []
    for i, idea in enumerate(ideas, 1):
        d = idea if isinstance(idea, dict) else (
            idea.model_dump() if hasattr(idea, "model_dump") else {}
        )
        d["pid"] = i
        out.append(d)

    # Persist run to database
    run_id = save_run(
        tech_stack=body.tech_stack,
        domain=inputs.get("domain"),
        level=inputs.get("level"),
        count=body.count,
        enable_multi_query=body.enable_multi_query,
        ideas=out,
        web_context=result.get("web_context"),
    )

    return {"ideas": out, "run_id": run_id}


# ── Idea Expansion ────────────────────────────────────────────────────────────

@api.post("/expand")
def post_expand(body: ExpandRequest):
    """Expand a single idea into a deeper implementation plan."""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Set OPENAI_API_KEY in .env",
        )

    # Load run from database
    run = get_run(run_id=body.run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run {body.run_id} not found.",
        )

    ideas = run["ideas"]
    if body.pid < 1 or body.pid > len(ideas):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pid. Use pid 1–{len(ideas)} for this run.",
        )

    idea = ideas[body.pid - 1].copy()
    idea.pop("pid", None)
    result = graph_expand_idea(idea)

    # Persist expanded idea to database
    save_expanded_idea(
        run_id=body.run_id,
        pid=body.pid,
        extended_plan=result.get("extended_plan", []),
    )

    return result


# ── Export ─────────────────────────────────────────────────────────────────────

@api.post("/export")
def post_export(body: ExportRequest):
    """Export an expanded idea as a downloadable Markdown file."""
    run = get_run(run_id=body.run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run {body.run_id} not found.",
        )

    ideas = run["ideas"]
    if body.pid < 1 or body.pid > len(ideas):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pid. Use pid 1–{len(ideas)} for this run.",
        )

    # For export, we need to re-expand (or the caller can expand first).
    # Try to get the idea and its expansion from the graph.
    idea = ideas[body.pid - 1].copy()
    idea.pop("pid", None)

    # Re-expand the idea for export (consistent with original behavior)
    expanded = graph_expand_idea(idea)
    extended_plan = expanded.get("extended_plan", [])

    md = idea_to_markdown(idea, extended_plan, run.get("tech_stack"))
    name_slug = (idea.get("name") or "idea").replace(" ", "_")[:50]
    filename = f"devstrom_{name_slug}.md"

    return PlainTextResponse(
        md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── History ────────────────────────────────────────────────────────────────────

@api.get("/history")
def get_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max runs to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    """Return the user's past runs, most recent first."""
    runs = load_history(limit=limit, offset=offset)
    return {"runs": runs, "limit": limit, "offset": offset}


@api.get("/runs/{run_id}")
def get_run_detail(run_id: str):
    """Return full details of a single run including all ideas."""
    run = get_run(run_id=run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run {run_id} not found.",
        )
    return run
