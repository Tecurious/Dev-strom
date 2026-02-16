import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from graph import app as graph_app


class IdeasRequest(BaseModel):
    tech_stack: str


api = FastAPI(title="Dev-Strom")


@api.post("/ideas")
def post_ideas(body: IdeasRequest):
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY and TAVILY_API_KEY in .env")
    result = graph_app.invoke({"tech_stack": body.tech_stack})
    ideas = result.get("ideas", [])
    if len(ideas) != 3:
        raise HTTPException(status_code=500, detail="Expected 3 ideas from graph")
    return {"ideas": ideas}
