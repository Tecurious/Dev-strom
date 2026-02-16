import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from graph import app as graph_app


class IdeasRequest(BaseModel):
    tech_stack: str
    domain: str | None = None
    level: str | None = None
    enable_multi_query: bool = False


api = FastAPI(title="Dev-Strom")


@api.post("/ideas")
def post_ideas(body: IdeasRequest):
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY and TAVILY_API_KEY in .env")
    inputs = {"tech_stack": body.tech_stack}
    if body.domain and body.domain.strip():
        inputs["domain"] = body.domain.strip()
    if body.level and body.level.strip():
        inputs["level"] = body.level.strip()
    if body.enable_multi_query:
        inputs["enable_multi_query"] = True
    result = graph_app.invoke(inputs)
    ideas = result.get("ideas", [])
    if len(ideas) != 3:
        raise HTTPException(status_code=500, detail="Expected 3 ideas from graph")
    return {"ideas": ideas}
