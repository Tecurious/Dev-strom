import os
from langchain_core.tools import tool
from tavily import TavilyClient

# ── tuneable constants ────────────────────────────────────────────────────────
MAX_RESULTS = 5
MAX_CHARS_SINGLE = 3_000
MAX_CHARS_MULTI = 6_000


# ── internal helpers ──────────────────────────────────────────────────────────

def _get_client() -> TavilyClient:
    """Return a TavilyClient, raising early if the API key is missing."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set in the environment")
    return TavilyClient(api_key=api_key)


def _search_single_query(client: TavilyClient, query: str, char_budget: int) -> str:
    """Run one Tavily search and return a snippet string within *char_budget* chars."""
    results = client.search(query=query, max_results=MAX_RESULTS).get("results", [])
    parts: list[str] = []
    used = 0
    for r in results:
        block = f"**{r.get('title', '')}**\n{r.get('content', '')}".strip()
        remaining = char_budget - used - len(parts)  # account for separators
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining]
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


# ── LangChain tool ────────────────────────────────────────────────────────────

@tool
def web_search_project_ideas(
    tech_stack: str,
    enable_multi_query: bool = False,
    domain: str | None = None,
) -> str:
    """Search the web for project ideas and tutorials related to a tech stack.

    Args:
        tech_stack: The tech stack to search for (e.g. 'LangChain, LangGraph').
        enable_multi_query: Run multiple complementary queries and merge results
            (default: False).  Produces richer output but costs more API calls.
        domain: Optional domain hint added as an extra query when multi-query is
            enabled (e.g. 'fintech', 'dev tools').

    Returns:
        Concatenated search-result snippets as a single string.
    """
    client = _get_client()

    if not enable_multi_query:
        query = f"project ideas and tutorials for {tech_stack}"
        return _search_single_query(client, query, MAX_CHARS_SINGLE)

    queries = [
        f"project ideas for {tech_stack}",
        f"{tech_stack} tutorials",
        f"{tech_stack} example projects",
    ]
    if domain:
        queries.append(f"{tech_stack} {domain} projects")

    char_budget = MAX_CHARS_MULTI // len(queries)
    snippets = [
        result
        for q in queries
        if (result := _search_single_query(client, q, char_budget))
    ]

    merged = "\n\n---\n\n".join(snippets)
    return merged[:MAX_CHARS_MULTI]  # hard cap in case of rounding
