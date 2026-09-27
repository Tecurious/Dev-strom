"""Unit tests for the archify spec coercion/validation layer."""

import pytest

from app.cartographer.archify_spec import coerce_archify_spec, renderable_archify
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


# The spec prod stored for the sun-mmon-puzzle analysis, which the UI's Archify
# renderer rejected (no grid layout, showcase lint, label inside its source box).
PROD_REGRESSION = {
    "schema_version": 1,
    "diagram_type": "architecture",
    "meta": {"title": "System architecture", "quality_profile": "showcase"},
    "components": [
        {"id": "user", "col": 0, "row": 0, "type": "external", "label": "User", "sublabel": "browser client"},
        {"id": "spa", "col": 1, "row": 0, "type": "frontend", "label": "React SPA",
         "sublabel": "Vite + TypeScript + Tailwind"},
        {"id": "assets", "col": 1, "row": 1, "type": "frontend", "label": "Assets", "sublabel": "static resources"},
        {"id": "vite", "col": 0, "row": 1, "type": "cloud", "label": "Build Toolchain", "sublabel": "Vite / PostCSS"},
    ],
    "connections": [
        {"to": "spa", "from": "user", "label": "HTTPS", "variant": "emphasis"},
        {"to": "assets", "from": "spa", "label": "static fetch", "variant": "default"},
        {"to": "spa", "from": "vite", "label": "bundle", "variant": "dashed"},
    ],
    "boundaries": [{"kind": "security-group", "label": "Browser trust boundary", "wraps": ["spa", "assets"]}],
}


def test_emits_grid_layout_and_only_renderer_meta():
    spec = coerce_archify_spec(PROD_REGRESSION)
    assert spec["layout"]["mode"] == "grid"
    assert spec["layout"]["cols"] == 2
    assert spec["meta"] == {"title": "System architecture"}


def test_downward_same_column_label_moves_below_source():
    spec = coerce_archify_spec(PROD_REGRESSION)
    by_label = {c.get("label"): c for c in spec["connections"]}
    assert by_label["static fetch"]["labelDy"] == 24
    assert "labelDy" not in by_label["HTTPS"]


def test_renormalizing_is_a_no_op():
    once = coerce_archify_spec(PROD_REGRESSION)
    assert coerce_archify_spec(once) == once


def test_grid_is_compacted():
    sparse = {**GOOD, "components": [{**c, "col": c["col"] * 5, "row": c["row"] * 3} for c in GOOD["components"]]}
    spec = coerce_archify_spec(sparse)
    assert {(c["row"], c["col"]) for c in spec["components"]} == {(0, 0), (0, 1), (1, 0)}


def test_edge_skipping_a_component_uses_the_corridor():
    column = {**GOOD, "components": [
        {"id": "a", "type": "frontend", "label": "A", "row": 0, "col": 0},
        {"id": "b", "type": "backend", "label": "B", "row": 1, "col": 0},
        {"id": "c", "type": "database", "label": "C", "row": 2, "col": 0},
    ], "connections": [{"from": "a", "to": "c"}], "boundaries": []}
    conn = coerce_archify_spec(column)["connections"][0]
    assert conn["fromSide"] == conn["toSide"] == "right"
    assert len(conn["via"]) == 2 and conn["via"][0][0] == conn["via"][1][0]


def test_boxes_widen_for_long_labels():
    wide = {**GOOD, "components": [{**GOOD["components"][0], "label": "Authentication Service Gateway"},
                                   *GOOD["components"][1:]]}
    spec = coerce_archify_spec(wide)
    width = spec["components"][0]["size"][0]
    assert width > 120 and spec["layout"]["cellW"] == width + 10
    assert "size" not in coerce_archify_spec(GOOD)["components"][0]


def test_llm_supplied_geometry_is_recomputed():
    noisy = {**GOOD, "connections": [{**GOOD["connections"][0], "via": [[1, 1]], "labelDy": 999}]}
    conn = coerce_archify_spec(noisy)["connections"][0]
    assert "via" not in conn and "labelDy" not in conn


def test_renderable_archify_falls_back_to_none():
    assert renderable_archify({"components": []}) is None
    assert renderable_archify(None) is None
    assert renderable_archify(PROD_REGRESSION)["layout"]["mode"] == "grid"
