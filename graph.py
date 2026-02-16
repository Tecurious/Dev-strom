import json
import re
from typing import TypedDict

from deepagents import create_deep_agent
from langchain.agents.middleware import wrap_model_call
from langgraph.graph import END, START, StateGraph

from schema import ProjectIdea
from tools import web_search_project_ideas


class DevStromStateRequired(TypedDict):
    tech_stack: str
    web_context: str
    ideas: list


class DevStromStateOptional(TypedDict, total=False):
    domain: str
    level: str
    enable_summarization: bool


class DevStromState(DevStromStateRequired, DevStromStateOptional):
    pass


def fetch_web_context(state: DevStromState) -> dict:
    tech_stack = state["tech_stack"]
    result = web_search_project_ideas.invoke({"tech_stack": tech_stack})
    return {"web_context": result or ""}


IDEAS_SYSTEM = """You are a strictly-controlled project-idea generator for developers learning a tech stack.

Follow these instructions exactly and obey all guardrails:

1. Output MUST be valid JSON, using ONLY the exact shape below. Do NOT include markdown code fence, explanation, headings, or any extra text.
2. Generate exactly 3 concrete project ideas. No more, no less.
3. Use THIS JSON shape, and nothing else:
{
  "ideas": [
    {
      "name": "...",
      "problem_statement": "...",
      "why_it_fits": ["...", "..."],
      "real_world_value": "...",
      "implementation_plan": ["...", "..."]
    },
    ...
  ]
}
4. Each idea MUST include:
   - "name": Short, clear project title
   - "problem_statement": 1–2 sentences explaining what problem the project solves
   - "why_it_fits": A LIST with one bullet per tech (describe why each key tech is relevant)
   - "real_world_value": ONE sentence on practical value or impact
   - "implementation_plan": LIST of 3–5 actionable steps to implement the project
5. If user provides a domain (e.g. fintech, dev tools) or level (e.g. beginner, portfolio), bias ALL ideas toward that domain and/or level.
6. STRICT GUARDRAILS:
   - NO markdown, code blocks, comments, or text before/after/beside the JSON.
   - Do NOT use any tools or external APIs.
   - Do NOT invent new fields or deviate from required JSON structure.
   - If you cannot comply with all instructions, output an empty JSON: {"ideas": []}
"""


@wrap_model_call
def log_model_call(request, handler):
    print("[DevStrom middleware] model call (generate_ideas agent)")
    return handler(request)


@wrap_model_call
def log_summarizer_call(request, handler):
    print("[DevStrom middleware] model call (summarize_web_context agent)")
    return handler(request)


_idea_agent = None
_summarizer_agent = None


def _get_idea_agent():
    global _idea_agent
    if _idea_agent is None:
        _idea_agent = create_deep_agent(
            name="idea_generator",
            model="gpt-5-mini",
            tools=[],
            system_prompt=IDEAS_SYSTEM,
            middleware=[log_model_call],
        )
    return _idea_agent


def _get_summarizer_agent():
    global _summarizer_agent
    if _summarizer_agent is None:
        _summarizer_agent = create_deep_agent(
            name="web_context_summarizer",
            model="gpt-5-mini",
            tools=[],
            system_prompt="""You are a web context summarizer. Your task is to analyze raw web search snippets and extract key themes, trends, common project types, and important resources mentioned.

Output a concise summary (2-4 sentences) that captures:
- Main themes and trends related to the tech stack
- Common project types or use cases mentioned
- Key resources, tutorials, or examples referenced

Do not include markdown formatting. Output plain text only.""",
            middleware=[log_summarizer_call],
        )
    return _summarizer_agent


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


def summarize_web_context(state: DevStromState) -> dict:
    web_context = state["web_context"]
    if not web_context or not web_context.strip():
        return {"web_context": web_context}
    user_content = f"Summarize the following web snippets into a short themes summary:\n\n{web_context[:6000]}\n\nProvide a concise summary of themes, trends, project types, and key resources:"
    result = _get_summarizer_agent().invoke({
        "messages": [{"role": "user", "content": user_content}],
    })
    messages = result.get("messages", [])
    summary = messages[-1].content if messages and hasattr(messages[-1], "content") else str(messages[-1]) if messages else web_context
    summary = summary.strip()
    if not summary:
        summary = web_context
    return {"web_context": summary}


def generate_ideas(state: DevStromState) -> dict:
    tech_stack = state["tech_stack"]
    web_context = state["web_context"]
    domain = state.get("domain")
    level = state.get("level")
    parts = [f"Tech stack: {tech_stack}"]
    if domain:
        parts.append(f"Domain (bias ideas toward): {domain}")
    if level:
        parts.append(f"Level (bias ideas toward): {level}")
    parts.append(f"\nWeb context:\n{web_context[:4000]}\n\nOutput exactly 3 ideas as JSON:\n")
    user_content = "\n".join(parts)
    result = _get_idea_agent().invoke({
        "messages": [{"role": "user", "content": user_content}],
    })
    messages = result.get("messages", [])
    content = messages[-1].content if messages and hasattr(messages[-1], "content") else str(messages[-1]) if messages else ""
    ideas = _parse_ideas_response(content)
    if not ideas:
        ideas = [{"name": "", "problem_statement": "", "why_it_fits": [], "real_world_value": "", "implementation_plan": []}] * 3
    return {"ideas": [i.model_dump() if hasattr(i, "model_dump") else i for i in ideas]}


def should_summarize(state: DevStromState) -> str:
    if state.get("enable_summarization"):
        return "summarize_web_context"
    return "generate_ideas"


def build_graph():
    graph = StateGraph(DevStromState)
    graph.add_node("fetch_web_context", fetch_web_context)
    graph.add_node("summarize_web_context", summarize_web_context)
    graph.add_node("generate_ideas", generate_ideas)
    graph.add_edge(START, "fetch_web_context")
    graph.add_conditional_edges("fetch_web_context", should_summarize)
    graph.add_edge("summarize_web_context", "generate_ideas")
    graph.add_edge("generate_ideas", END)
    return graph.compile()


app = build_graph()
