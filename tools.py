import os
from langchain_core.tools import tool
from tavily import TavilyClient

MAX_SNIPPETS_CHARS = 3000
MAX_RESULTS = 5


def _search_web(tech_stack: str) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set in environment")
    query = f"project ideas and tutorials for {tech_stack}"
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=MAX_RESULTS)
    results = response.get("results", [])
    parts = []
    total = 0
    for r in results:
        title = r.get("title", "")
        content = r.get("content", "")
        block = f"**{title}**\n{content}".strip()
        if total + len(block) + 1 > MAX_SNIPPETS_CHARS:
            block = block[: MAX_SNIPPETS_CHARS - total - 1]
        parts.append(block)
        total += len(block) + 1
        if total >= MAX_SNIPPETS_CHARS:
            break
    return "\n\n".join(parts) if parts else ""


@tool
def web_search_project_ideas(tech_stack: str) -> str:
    """Search the web for project ideas and tutorials related to a tech stack. Call with the tech stack string (e.g. 'LangChain, LangGraph, Deep Agents'). Returns a concatenated string of snippets."""
    return _search_web(tech_stack)
