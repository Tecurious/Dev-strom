"""Validation + coercion for the Archify architecture spec the analyst emits.

Subset of the tt-a1i/archify architecture schema (MIT, v2.17) that
chartographer actually uses. Returns a normalized spec dict or raises
DiagramError with machine-readable diagnostics — the findings pass uses that
for its one retry, and the UI consumes the normalized spec with its vendored
Archify renderer.
"""

from __future__ import annotations

from typing import Any

from app.cartographer.diagram import DiagramError

_COMPONENT_TYPES = {"frontend", "backend", "database", "cloud", "security", "messagebus", "external"}
_VARIANTS = {"default", "emphasis", "security", "dashed"}
_BOUNDARY_KINDS = {"region", "security-group"}
_MAX_COMPONENTS = 15
_REQUIRED_META = {"schema_version": 1, "diagram_type": "architecture"}
_ALLOWED_COMPONENT_KEYS = {"id", "type", "label", "sublabel", "row", "col", "tag"}
_ALLOWED_CONNECTION_KEYS = {"from", "to", "label", "variant"}
_ALLOWED_BOUNDARY_KEYS = {"kind", "label", "wraps"}


def coerce_archify_spec(value: Any) -> dict | None:
    """Validate + normalize the analyst's archify spec. None when absent.

    Raises DiagramError with diagnostics when present-but-wrong so the
    findings retry hook can re-prompt with the reasons.
    """
    if value is None or value == {}:
        return None
    if not isinstance(value, dict):
        raise DiagramError("archify spec must be an object.", [_diag("schema/type", "", "not an object")])

    diags: list[dict] = []
    for key, want in _REQUIRED_META.items():
        if value.get(key) != want:
            diags.append(_diag("schema/field", key, f"must be {want!r}"))
    meta = value.get("meta")
    if not isinstance(meta, dict) or not meta.get("title"):
        diags.append(_diag("schema/field", "meta.title", "required non-empty string"))

    components = value.get("components")
    if not isinstance(components, list) or not components:
        diags.append(_diag("schema/field", "components", "must be a non-empty array"))
        raise DiagramError("archify spec invalid.", diags)
    if len(components) > _MAX_COMPONENTS:
        diags.append(_diag("schema/limit", "components", f"max {_MAX_COMPONENTS}, got {len(components)}"))

    ids: set[str] = set()
    cells: set[tuple[int, int]] = set()
    norm_components: list[dict] = []
    for i, comp in enumerate(components):
        if not isinstance(comp, dict):
            diags.append(_diag("schema/type", f"components[{i}]", "not an object"))
            continue
        cid = comp.get("id")
        if not isinstance(cid, str) or not cid:
            diags.append(_diag("schema/field", f"components[{i}].id", "required non-empty string"))
            continue
        if cid in ids:
            diags.append(_diag("schema/unique", f"components[{i}].id", f"duplicate id {cid!r}"))
        ids.add(cid)
        ctype = comp.get("type")
        if ctype not in _COMPONENT_TYPES:
            diags.append(_diag("schema/field", f"components[{i}].type", f"{ctype!r} not one of {sorted(_COMPONENT_TYPES)}"))
        if not comp.get("label"):
            diags.append(_diag("schema/field", f"components[{i}].label", "required non-empty string"))
        row, col = comp.get("row"), comp.get("col")
        if not isinstance(row, int) or not isinstance(col, int) or row < 0 or col < 0:
            diags.append(_diag("schema/field", f"components[{i}].row/col", "required non-negative integers"))
        else:
            if (row, col) in cells:
                diags.append(_diag("schema/unique", f"components[{i}]", f"grid cell ({row},{col}) already used"))
            cells.add((row, col))
        extra = set(comp) - _ALLOWED_COMPONENT_KEYS
        if extra:
            diags.append(_diag("schema/extra", f"components[{i}]", f"unknown keys {sorted(extra)}"))
        norm_components.append({
            "id": cid, "type": ctype if ctype in _COMPONENT_TYPES else "backend",
            "label": comp.get("label") or cid,
            **({"sublabel": comp["sublabel"]} if comp.get("sublabel") else {}),
            "row": row if isinstance(row, int) else 0, "col": col if isinstance(col, int) else 0,
        })

    known = {c["id"] for c in norm_components}
    norm_connections: list[dict] = []
    connections = value.get("connections") or []
    if not isinstance(connections, list):
        diags.append(_diag("schema/type", "connections", "must be an array"))
        connections = []
    for i, conn in enumerate(connections):
        if not isinstance(conn, dict):
            diags.append(_diag("schema/type", f"connections[{i}]", "not an object"))
            continue
        src, dst = conn.get("from"), conn.get("to")
        for endpoint in (src, dst):
            if endpoint not in known:
                diags.append(_diag("schema/ref", f"connections[{i}]", f"unknown component id {endpoint!r}"))
        variant = conn.get("variant", "default")
        if variant not in _VARIANTS:
            diags.append(_diag("schema/field", f"connections[{i}].variant", f"{variant!r} not one of {sorted(_VARIANTS)}"))
            variant = "default"
        extra = set(conn) - _ALLOWED_CONNECTION_KEYS
        if extra:
            diags.append(_diag("schema/extra", f"connections[{i}]", f"unknown keys {sorted(extra)}"))
        norm_connections.append({
            "from": src, "to": dst,
            **({"label": conn["label"]} if conn.get("label") else {}),
            "variant": variant,
        })

    norm_boundaries: list[dict] = []
    for i, b in enumerate(value.get("boundaries") or []):
        if not isinstance(b, dict):
            diags.append(_diag("schema/type", f"boundaries[{i}]", "not an object"))
            continue
        kind = b.get("kind")
        if kind not in _BOUNDARY_KINDS:
            diags.append(_diag("schema/field", f"boundaries[{i}].kind", f"{kind!r} not one of {sorted(_BOUNDARY_KINDS)}"))
        wraps = b.get("wraps")
        if not isinstance(wraps, list) or not wraps:
            diags.append(_diag("schema/field", f"boundaries[{i}].wraps", "required non-empty array of ids"))
        else:
            for wid in wraps:
                if wid not in known:
                    diags.append(_diag("schema/ref", f"boundaries[{i}].wraps", f"unknown component id {wid!r}"))
        extra = set(b) - _ALLOWED_BOUNDARY_KEYS
        if extra:
            diags.append(_diag("schema/extra", f"boundaries[{i}]", f"unknown keys {sorted(extra)}"))
        norm_boundaries.append({
            "kind": kind if kind in _BOUNDARY_KINDS else "region",
            "label": b.get("label") or "Boundary",
            "wraps": [w for w in (wraps or []) if w in known],
        })

    if diags:
        raise DiagramError("archify spec invalid.", diags)

    return {
        **_REQUIRED_META,
        "meta": meta if isinstance(meta, dict) else {"title": "System architecture"},
        "components": norm_components,
        "connections": norm_connections,
        "boundaries": norm_boundaries,
    }


def _diag(code: str, subject: Any, message: str) -> dict:
    return {"code": code, "subject": str(subject), "message": message}
