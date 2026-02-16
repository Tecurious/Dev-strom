import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from graph import app as graph_app, expand_idea as graph_expand_idea


class IdeasRequest(BaseModel):
    tech_stack: str
    domain: str | None = None
    level: str | None = None
    enable_multi_query: bool = False
    count: int = Field(default=3, ge=1, le=5)


class ExpandRequest(BaseModel):
    pid: int = Field(..., ge=1, description="ID of the idea to expand (from last POST /ideas response)")


_api_last_ideas: list[dict] = []


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
    global _api_last_ideas
    out = []
    for i, idea in enumerate(ideas, 1):
        d = idea if isinstance(idea, dict) else (idea.model_dump() if hasattr(idea, "model_dump") else {})
        d["pid"] = i
        out.append(d)
    _api_last_ideas = out
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
    return result
