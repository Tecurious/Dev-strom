import os
import uuid
from collections import OrderedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from graph import app as graph_app, expand_idea as graph_expand_idea
from export_formatter import idea_to_markdown


class IdeasRequest(BaseModel):
    tech_stack: str
    domain: str | None = None
    level: str | None = None
    enable_multi_query: bool = False
    count: int = Field(default=3, ge=1, le=5)


class ExpandRequest(BaseModel):
    run_id: str = Field(..., description="Run ID from POST /ideas response")
    pid: int = Field(..., ge=1, description="ID of the idea to expand (1-based from that run)")


class ExportRequest(BaseModel):
    run_id: str = Field(..., description="Run ID from POST /ideas response")
    pid: int = Field(..., ge=1, description="ID of the expanded idea to export (must have been expanded first)")


_MAX_RUNS = 100
_run_store: OrderedDict[str, dict] = OrderedDict()


def _get_run(run_id: str) -> dict:
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found. Call POST /ideas first and use the returned run_id.")
    return _run_store[run_id]


api = FastAPI(title="Dev-Strom")


@api.post("/ideas")
def post_ideas(body: IdeasRequest):
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY and TAVILY_API_KEY in .env")
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
        raise HTTPException(status_code=500, detail=f"Expected {body.count} ideas from graph, got {len(ideas)}")
    out = []
    for i, idea in enumerate(ideas, 1):
        d = idea if isinstance(idea, dict) else (idea.model_dump() if hasattr(idea, "model_dump") else {})
        d["pid"] = i
        out.append(d)
    run_id = str(uuid.uuid4())
    while len(_run_store) >= _MAX_RUNS:
        _run_store.popitem(last=False)
    _run_store[run_id] = {
        "ideas": out,
        "expanded_by_pid": {},
        "tech_stack": body.tech_stack,
    }
    _run_store.move_to_end(run_id)
    return {"ideas": out, "run_id": run_id}


@api.post("/expand")
def post_expand(body: ExpandRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY in .env")
    run = _get_run(body.run_id)
    ideas = run["ideas"]
    if body.pid < 1 or body.pid > len(ideas):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pid. Use pid 1–{len(ideas)} for this run.",
        )
    idea = ideas[body.pid - 1].copy()
    idea.pop("pid", None)
    result = graph_expand_idea(idea)
    run["expanded_by_pid"][body.pid] = result
    return result


@api.post("/export")
def post_export(body: ExportRequest):
    run = _get_run(body.run_id)
    expanded_by_pid = run["expanded_by_pid"]
    if body.pid not in expanded_by_pid:
        raise HTTPException(
            status_code=400,
            detail=f"Expand idea {body.pid} first (POST /expand with {{\"run_id\": \"...\", \"pid\": {body.pid}}}).",
        )
    expanded = expanded_by_pid[body.pid]
    idea = expanded.get("idea", {})
    extended_plan = expanded.get("extended_plan", [])
    md = idea_to_markdown(idea, extended_plan, run.get("tech_stack") or None)
    name_slug = (idea.get("name") or "idea").replace(" ", "_")[:50]
    filename = f"devstrom_{name_slug}.md"
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
