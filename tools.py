import os
from langchain_core.tools import tool
from tavily import TavilyClient

MAX_SNIPPETS_CHARS = 3000
MAX_RESULTS = 5
MAX_SNIPPETS_CHARS_MULTI_QUERY = 6000


def _search_single_query(client: TavilyClient, query: str, max_chars_per_query: int) -> str:
    response = client.search(query=query, max_results=MAX_RESULTS)
    results = response.get("results", [])
    parts = []
    total = 0
    for r in results:
        title = r.get("title", "")
        content = r.get("content", "")
        block = f"**{title}**\n{content}".strip()
        if total + len(block) + 1 > max_chars_per_query:
            block = block[: max_chars_per_query - total - 1]
        parts.append(block)
        total += len(block) + 1
        if total >= max_chars_per_query:
            break
    return "\n\n".join(parts) if parts else ""


def _search_web(tech_stack: str, enable_multi_query: bool = False, domain: str | None = None) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set in environment")
    client = TavilyClient(api_key=api_key)
    
    if not enable_multi_query:
        query = f"project ideas and tutorials for {tech_stack}"
        return _search_single_query(client, query, MAX_SNIPPETS_CHARS)
    
    queries = [
        f"project ideas for {tech_stack}",
        f"{tech_stack} tutorials",
        f"{tech_stack} example projects",
    ]
    if domain:
        queries.append(f"{tech_stack} {domain} projects")
    
    max_chars_per_query = MAX_SNIPPETS_CHARS_MULTI_QUERY // len(queries)
    query_results = []
    
    for query in queries:
        result = _search_single_query(client, query, max_chars_per_query)
        if result:
            query_results.append(result)
    
    merged = "\n\n---\n\n".join(query_results)
    if len(merged) > MAX_SNIPPETS_CHARS_MULTI_QUERY:
        merged = merged[:MAX_SNIPPETS_CHARS_MULTI_QUERY]
    return merged


@tool
def web_search_project_ideas(tech_stack: str, enable_multi_query: bool = False, domain: str | None = None) -> str:
    """Search the web for project ideas and tutorials related to a tech stack. Call with the tech stack string (e.g. 'LangChain, LangGraph, Deep Agents'). Returns a concatenated string of snippets.
    
    Args:
        tech_stack: The tech stack to search for
        enable_multi_query: If True, runs 2-3 queries and merges results (default: False)
        domain: Optional domain to include in queries (e.g. 'fintech', 'dev tools')
    """
    return _search_web(tech_stack, enable_multi_query, domain)
