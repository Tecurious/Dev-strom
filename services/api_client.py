"""
HTTP client for the Dev-Strom FastAPI backend.
All Streamlit pages call these functions — never graph.py directly.
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── shared request helper ──────────────────────────────────────────────────────

def _post(path: str, payload: dict, *, timeout: int = 120) -> dict:
    """POST to the FastAPI server and return the parsed JSON body.
    Raises httpx.HTTPStatusError on non-2xx responses so callers can surface
    the error message without knowing HTTP details.
    """
    url = f"{_BASE}{path}"
    response = httpx.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


# ── public API ─────────────────────────────────────────────────────────────────

def get_ideas(
    tech_stack: str,
    *,
    domain: str | None = None,
    level: str | None = None,
    count: int = 3,
    enable_multi_query: bool = False,
) -> dict:
    """Call POST /ideas and return {ideas: [...], run_id: str}."""
    payload: dict = {
        "tech_stack": tech_stack,
        "count": count,
        "enable_multi_query": enable_multi_query,
    }
    if domain and domain.strip():
        payload["domain"] = domain.strip()
    if level and level.strip():
        payload["level"] = level.strip()
    return _post("/ideas", payload, timeout=120)


def expand_idea(run_id: str, pid: int) -> dict:
    """Call POST /expand and return the expanded idea dict."""
    return _post("/expand", {"run_id": run_id, "pid": pid}, timeout=90)


def export_idea(run_id: str, pid: int) -> str:
    """Call POST /export and return the raw Markdown string."""
    url = f"{_BASE}/export"
    response = httpx.post(url, json={"run_id": run_id, "pid": pid}, timeout=30)
    response.raise_for_status()
    return response.text
