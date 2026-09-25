"""Unit tests for the archify-styled deterministic diagram renderer.

Layout/routing/validation logic ported from tt-a1i/archify (MIT).
"""

import pytest

from app.cartographer.diagram import (
    DiagramError,
    layout,
    parse_mermaid,
    render_html,
    validate,
)

SRC = """flowchart TD
    Web[Web UI] --> API[FastAPI]
    API --> DB[(Postgres)]
    API -- chat completions --> LLM[OpenRouter]
    API -. web search .-> TAV[Tavily]
    GHA[GitHub Actions] -->|bump tag| ARGO[Argo CD]
    ARGO --> API"""


def test_parse_mermaid_topology():
    topo = parse_mermaid(SRC)
    assert set(topo.nodes) == {"Web", "API", "DB", "LLM", "TAV", "GHA", "ARGO"}
    assert topo.nodes["DB"] == "Postgres"          # shape markup stripped
    assert ("API", "LLM", "chat completions") in topo.edges
    assert ("GHA", "ARGO", "bump tag") in topo.edges
    assert ("API", "TAV", "web search") in topo.edges


def test_parse_mermaid_rejects_garbage():
    with pytest.raises(DiagramError):
        parse_mermaid("flowchart TD\n  A ~~> B((")
    with pytest.raises(DiagramError):  # cycle is caught at layout time
        layout(parse_mermaid("flowchart TD\n  A --> B\n  B --> A"))


def test_layout_and_validate_clean():
    topo = parse_mermaid(SRC)
    laid, routes, labels = layout(topo)
    assert len(laid) == 7
    assert len(routes) == 6
    # showcase-style checks: labels never mask nodes or other routes,
    # no edge crosses an unrelated node
    assert validate(laid, routes, labels) == []


def test_render_html_self_contained():
    html = render_html(SRC, title="Dev-Strom")
    assert html.startswith("<!DOCTYPE html>")
    assert "<svg" in html and "</svg>" in html
    assert "chat completions" in html
    assert "Postgres" in html and "(Postgres)" not in html
    # zero-JS: only the tiny theme toggle inline handler allowed
    assert "src=" not in html and "href=" not in html
    assert "tt-a1i/archify" in html  # MIT attribution retained


def test_edges_from_shared_port_are_spread():
    topo = parse_mermaid(SRC)  # API has 3 out-edges
    laid, routes, labels = layout(topo)
    starts = [tuple(r[0]) for r in routes.values()]
    assert len(set(starts)) == len(starts)  # no two edges share a port point
