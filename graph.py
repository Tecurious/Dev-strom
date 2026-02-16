import json
import re
from typing import TypedDict

from deepagents import create_deep_agent
from langchain.agents.middleware import wrap_model_call
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


IDEAS_SYSTEM = """You are a project-idea generator for developers learning a tech stack.
Output exactly 3 concrete project ideas as valid JSON only. Do not use any tools.
Use this exact shape (no markdown, no extra text):
{"ideas": [{"name": "...", "problem_statement": "...", "why_it_fits": ["...", "..."], "real_world_value": "...", "implementation_plan": ["...", "..."]}, ...]}
Each idea: name, problem_statement (1-2 sentences), why_it_fits (list, one bullet per tech), real_world_value (one sentence), implementation_plan (list of 3-5 steps).
"""


@wrap_model_call
def log_model_call(request, handler):
    print("[DevStrom middleware] model call (generate_ideas agent)")
    return handler(request)


_idea_agent = create_deep_agent(
    name="idea_generator",
    model="gpt-4o-mini",
    tools=[],
    system_prompt=IDEAS_SYSTEM,
    middleware=[log_model_call],
)


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
    user_content = f"Tech stack: {tech_stack}\n\nWeb context:\n{web_context[:4000]}\n\nOutput exactly 3 ideas as JSON:\n"
    result = _idea_agent.invoke({
        "messages": [{"role": "user", "content": user_content}],
    })
    messages = result.get("messages", [])
    content = messages[-1].content if messages and hasattr(messages[-1], "content") else str(messages[-1]) if messages else ""
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
