import os

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
    pid: int = Field(..., ge=1, description="ID of the idea to expand (from last POST /ideas response)")


class ExportRequest(BaseModel):
    pid: int = Field(..., ge=1, description="ID of the expanded idea to export (must have been expanded first)")


_api_last_ideas: list[dict] = []
_api_expanded_by_pid: dict[int, dict] = {}
_api_last_tech_stack: str = ""


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
    global _api_last_ideas, _api_expanded_by_pid, _api_last_tech_stack
    out = []
    for i, idea in enumerate(ideas, 1):
        d = idea if isinstance(idea, dict) else (idea.model_dump() if hasattr(idea, "model_dump") else {})
        d["pid"] = i
        out.append(d)
    _api_last_ideas = out
    _api_expanded_by_pid = {}
    _api_last_tech_stack = body.tech_stack
    return {"ideas": out}


@api.post("/expand")
def post_expand(body: ExpandRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY in .env")
    if body.pid < 1 or body.pid > len(_api_last_ideas):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pid. Call POST /ideas first; pid must be 1–{len(_api_last_ideas) or 1}.",
        )
    idea = _api_last_ideas[body.pid - 1].copy()
    idea.pop("pid", None)
    result = graph_expand_idea(idea)
    _api_expanded_by_pid[body.pid] = result
    return result


@api.post("/export")
def post_export(body: ExportRequest):
    if body.pid not in _api_expanded_by_pid:
        raise HTTPException(
            status_code=400,
            detail=f"Expand idea {body.pid} first (POST /expand with {{\"pid\": {body.pid}}}).",
        )
    expanded = _api_expanded_by_pid[body.pid]
    idea = expanded.get("idea", {})
    extended_plan = expanded.get("extended_plan", [])
    md = idea_to_markdown(idea, extended_plan, _api_last_tech_stack or None)
    name_slug = (idea.get("name") or "idea").replace(" ", "_")[:50]
    filename = f"devstrom_{name_slug}.md"
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
