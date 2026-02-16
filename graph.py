import json
import re
from typing import TypedDict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from schema import ProjectIdea
from tools import web_search_project_ideas


class DevStromState(TypedDict):
    tech_stack: str
    web_context: str
    ideas: list


def fetch_web_context(state: DevStromState) -> dict:
    tech_stack = state["tech_stack"]
    result = web_search_project_ideas.invoke({"tech_stack": tech_stack})
    return {"web_context": result or ""}


IDEAS_PROMPT = """You are a project-idea generator for developers learning a tech stack.
Given the tech stack and web search context below, output exactly 3 concrete project ideas.
Each idea must have: name, problem_statement (1-2 sentences), why_it_fits (list of short bullets, one per tech), real_world_value (one sentence), implementation_plan (list of 3-5 high-level steps).
Output valid JSON only, in this exact shape (no markdown, no extra text):
{"ideas": [{"name": "...", "problem_statement": "...", "why_it_fits": ["...", "..."], "real_world_value": "...", "implementation_plan": ["...", "..."]}, ...]}
"""


def _parse_ideas_response(raw: str) -> list:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        ideas = data.get("ideas", [])
        if len(ideas) != 3:
            return ideas
        return [ProjectIdea.model_validate(i) for i in ideas]
    except Exception:
        return []


def generate_ideas(state: DevStromState) -> dict:
    tech_stack = state["tech_stack"]
    web_context = state["web_context"]
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    prompt = (
        IDEAS_PROMPT
        + f"\nTech stack: {tech_stack}\n\nWeb context:\n{web_context[:4000]}\n\nJSON output:\n"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)
    ideas = _parse_ideas_response(content)
    if not ideas:
        ideas = [{"name": "", "problem_statement": "", "why_it_fits": [], "real_world_value": "", "implementation_plan": []}] * 3
    return {"ideas": [i.model_dump() if hasattr(i, "model_dump") else i for i in ideas]}


def build_graph():
    graph = StateGraph(DevStromState)
    graph.add_node("fetch_web_context", fetch_web_context)
    graph.add_node("generate_ideas", generate_ideas)
    graph.add_edge(START, "fetch_web_context")
    graph.add_edge("fetch_web_context", "generate_ideas")
    graph.add_edge("generate_ideas", END)
    return graph.compile()


app = build_graph()
