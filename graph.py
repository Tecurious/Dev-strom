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
    enable_multi_query: bool


class DevStromState(DevStromStateRequired, DevStromStateOptional):
    pass


def fetch_web_context(state: DevStromState) -> dict:
    tech_stack = state["tech_stack"]
    enable_multi_query = state.get("enable_multi_query", False)
    domain = state.get("domain")
    result = web_search_project_ideas.invoke({
        "tech_stack": tech_stack,
        "enable_multi_query": enable_multi_query,
        "domain": domain,
    })
    return {"web_context": result or ""}


IDEAS_SYSTEM = """You are a strictly-controlled project-idea generator for developers learning a tech stack.

Follow these instructions exactly and obey all guardrails:

1. Output MUST be valid JSON, using ONLY the exact shape below. Do NOT include markdown code fences, explanations, headings, or any extra text.
2. Generate exactly 3 concrete project ideas. No more, no less.
3. Use THIS JSON shape, and nothing else:
{
  "ideas": [
    {
      "name": "Project Title",
      "problem_statement": "Clear, 1-2 sentence definition of the business problem.",
      "why_it_fits": [
        "Tech Name: Specific reason why this tech is the industry standard for this problem.",
        "Tech Name: Another specific reason..."
      ],
      "real_world_value": "One sentence on the business impact (e.g. revenue, efficiency, risk).",
      "implementation_plan": [
        "Step 1: Architect/Setup...",
        "Step 2: Core Logic...",
        "Step 3: Integration/Polish..."
      ]
    }
  ]
}

4. CONTENT GUIDELINES:
   - "name": Short, professional project title.
   - "problem_statement": 1–2 sentences describing what problem the project solves.
   - "why_it_fits": Each string MUST start with the Tech Name followed by a colon. Do not list generic benefits; link the tech to the specific domain problem. Aim for one bullet per key tech.
   - "real_world_value": Focus on business value (cost, speed, accuracy, risk), not just coding practice.
   - "implementation_plan": 3–5 high-level, actionable steps that a developer could realistically follow.

5. DOMAIN BIAS:
   - If a Domain/Company is provided (e.g. Walmart, Fintech), use terminology and architectural patterns specific to that industry (e.g. "SCD Type 2" for data warehousing, "circuit breakers" for microservices).
   - Do NOT invent specific internal tool names for companies. Use industry-standard equivalents instead (e.g. use "S3" instead of "Walmart Object Store").

6. LEVEL CALIBRATION:
   - If Level = "Beginner": Focus on core language syntax, simple data modeling, CLI/File I/O, and single-service apps. Avoid complex distributed systems.
   - If Level = "Intermediate": Focus on common frameworks (Spring, Django, React, etc.), databases, and simple APIs.
   - If Level = "Advanced" / "Architect": Focus on distributed systems patterns (CAP theorem, event sourcing, caching strategies, idempotency), scalability, reliability, and fault tolerance.

7. DISTINCT IDEAS:
   - All 3 ideas must be meaningfully different from each other (different core problem, architecture, or primary focus), even when using the same tech stack and domain.

8. STRICT GUARDRAILS:
   - NO markdown, code blocks, comments, or text before/after/beside the JSON.
   - Do NOT use any tools or external APIs.
   - Do NOT invent new fields or deviate from the required JSON structure.
   - If the user misspells a technology, silently map it to the standard name (e.g. "ReactJS" -> "React") and use the corrected name in the output.
   - If you cannot comply with all instructions, output exactly: {"ideas": []}

9. HALLUCINATION CHECK:
   - Do NOT suggest technologies that do not exist (e.g. "Apache Wifi").
   - Ensure each "problem_statement" describes a solvable engineering problem, not a physical impossibility (e.g. do not suggest "Track inventory using WiFi signals alone").
"""


@wrap_model_call
def log_model_call(request, handler):
    print("[DevStrom middleware] model call (generate_ideas agent)")
    return handler(request)


_idea_agent = None


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


def build_graph():
    graph = StateGraph(DevStromState)
    graph.add_node("fetch_web_context", fetch_web_context)
    graph.add_node("generate_ideas", generate_ideas)
    graph.add_edge(START, "fetch_web_context")
    graph.add_edge("fetch_web_context", "generate_ideas")
    graph.add_edge("generate_ideas", END)
    return graph.compile()


app = build_graph()
