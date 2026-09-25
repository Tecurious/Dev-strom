"""Unit tests for the archify spec coercion/validation layer."""

import pytest

from app.cartographer.archify_spec import coerce_archify_spec
from app.cartographer.diagram import DiagramError

GOOD = {
    "schema_version": 1,
    "diagram_type": "architecture",
    "meta": {"title": "System", "quality_profile": "showcase"},
    "components": [
        {"id": "web", "type": "frontend", "label": "Web UI", "row": 0, "col": 0},
        {"id": "api", "type": "backend", "label": "API", "row": 0, "col": 1},
        {"id": "db", "type": "database", "label": "Postgres", "row": 1, "col": 0},
    ],
    "connections": [{"from": "web", "to": "api", "label": "HTTPS", "variant": "emphasis"}],
    "boundaries": [{"kind": "security-group", "label": "Trust", "wraps": ["api", "db"]}],
}


def test_valid_spec_passes_and_normalizes():
    spec = coerce_archify_spec(GOOD)
    assert spec["components"][0]["label"] == "Web UI"
    assert spec["connections"][0]["variant"] == "emphasis"
    assert spec["boundaries"][0]["wraps"] == ["api", "db"]


def test_absent_and_empty_are_none():
    assert coerce_archify_spec(None) is None
    assert coerce_archify_spec({}) is None


def test_bad_type_is_normalized_with_diagnostic_but_raises():
    bad = {**GOOD, "components": [{**GOOD["components"][0], "type": "weird"},
                                  *GOOD["components"][1:]]}
    with pytest.raises(DiagramError) as err:
        coerce_archify_spec(bad)
    assert any("not one of" in d["message"] for d in err.value.diagnostics)


def test_unknown_refs_raise():
    bad = {**GOOD, "connections": [{"from": "web", "to": "ghost"}]}
    with pytest.raises(DiagramError) as err:
        coerce_archify_spec(bad)
    assert any("ghost" in d["message"] for d in err.value.diagnostics)


def test_duplicate_cell_raises():
    dup = {**GOOD, "components": [
        GOOD["components"][0],
        {**GOOD["components"][1], "row": 0, "col": 0},
        GOOD["components"][2],
    ]}
    with pytest.raises(DiagramError) as err:
        coerce_archify_spec(dup)
    assert any("already used" in d["message"] for d in err.value.diagnostics)


def test_extra_keys_reported():
    bad = {**GOOD, "components": [{**GOOD["components"][0], "brand": {"x": 1}},
                                  *GOOD["components"][1:]]}
    with pytest.raises(DiagramError) as err:
        coerce_archify_spec(bad)
    assert any("unknown keys" in d["message"] for d in err.value.diagnostics)
