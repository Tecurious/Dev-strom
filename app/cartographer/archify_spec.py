"""Validation + coercion for the Archify architecture spec the analyst emits.

Subset of the tt-a1i/archify architecture schema (MIT, v2.17) that
chartographer actually uses. Returns a normalized spec dict or raises
DiagramError with machine-readable diagnostics — the findings pass uses that
for its one retry, and the UI consumes the normalized spec with its vendored
Archify renderer.
"""

from __future__ import annotations

import logging
import math
import unicodedata
from typing import Any

from app.cartographer.diagram import DiagramError

logger = logging.getLogger(__name__)

_COMPONENT_TYPES = {"frontend", "backend", "database", "cloud", "security", "messagebus", "external"}
_VARIANTS = {"default", "emphasis", "security", "dashed"}
_BOUNDARY_KINDS = {"region", "security-group"}
_MAX_COMPONENTS = 15
_REQUIRED_META = {"schema_version": 1, "diagram_type": "architecture"}
# Derived keys are recomputed on every pass, so re-normalizing a stored spec is a no-op.
_ALLOWED_COMPONENT_KEYS = {"id", "type", "label", "sublabel", "row", "col", "tag", "size"}
_ALLOWED_CONNECTION_KEYS = {"from", "to", "label", "variant", "labelDy", "labelSegment", "fromSide", "toSide", "via"}
_ALLOWED_BOUNDARY_KEYS = {"kind", "label", "wraps"}
_ALLOWED_META_KEYS = ("title", "subtitle", "locale")
_MAX_COLS = 12
_GAP_X_MIN, _GAP_X_MAX, _GAP_Y = 40, 150, 72
_ORIGIN, _CELL_PAD, _CELL_H, _BOX_H = (40, 80), 10, 64, 60
_BOX_W_MIN, _BOX_W_MAX = 120, 240


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

    cols = _compact_grid(norm_components)
    if cols > _MAX_COLS:
        diags.append(_diag("schema/limit", "components.col", f"max {_MAX_COLS} distinct columns, got {cols}"))

    if diags:
        raise DiagramError("archify spec invalid.", diags)

    box_w = _box_width(norm_components)
    if box_w > _BOX_W_MIN:
        for c in norm_components:
            c["size"] = [box_w, _BOX_H]
    layout = {"mode": "grid", "cols": cols, "origin": list(_ORIGIN), "cellW": box_w + _CELL_PAD, "cellH": _CELL_H,
              "gapX": _gap_x(norm_connections), "gapY": _GAP_Y}
    _route_connections(norm_components, norm_connections, layout, box_w)
    return {
        **_REQUIRED_META,
        "meta": {k: meta[k] for k in _ALLOWED_META_KEYS if isinstance(meta.get(k), str) and meta[k]},
        "layout": layout,
        "components": norm_components,
        "connections": norm_connections,
        "boundaries": norm_boundaries,
    }


def _compact_grid(components: list[dict]) -> int:
    """Renumber rows/cols to 0..n-1 (order kept) so empty tracks don't widen
    the canvas and Archify's `layout.cols` bound holds. Returns the col count."""
    for axis in ("row", "col"):
        index = {v: i for i, v in enumerate(sorted({c[axis] for c in components}))}
        for c in components:
            c[axis] = index[c[axis]]
    return max(c["col"] for c in components) + 1


def _route_connections(components: list[dict], connections: list[dict], layout: dict, box_w: int) -> None:
    """Pre-place what Archify's renderer leaves to a human author. An edge that
    would pass through a component between its endpoints is sent through the
    empty grid corridors instead, attaching on sides no other edge uses (Archify
    anchors waypoint edges at side centres and skips its port spreading for
    them) and staying inside the grid's footprint, which is all the canvas
    Archify sizes; parallel corridor runs get their own lane. A straight downward
    edge's label (anchored 10px above its start, inside the source box) moves
    into the gap below."""
    by_id = {c["id"]: c for c in components}
    cells = {(c["row"], c["col"]) for c in components}
    ox, oy = layout["origin"]
    step_x, step_y = layout["cellW"] + layout["gapX"], layout["cellH"] + layout["gapY"]
    half_gx, half_gy = (step_x - box_w) / 2, (step_y - _BOX_H) / 2
    grid_right = ox + (layout["cols"] - 1) * step_x + box_w
    grid_bottom = oy + max(c["row"] for c in components) * step_y + _BOX_H

    def left(c): return ox + c * step_x
    def top(r): return oy + r * step_y
    def cx(c): return left(c) + box_w / 2
    def cy(r): return top(r) + _BOX_H / 2
    def col_lane(c, side): return left(c) - half_gx if side == "left" else left(c) + box_w + half_gx
    def row_lane(r, side): return top(r) - half_gy if side == "top" else top(r) + _BOX_H + half_gy

    def blocked(r1, c1, r2, c2):
        return any((r, c) in cells and (r, c) not in ((r1, c1), (r2, c2))
                   for r in range(min(r1, r2), max(r1, r2) + 1) for c in range(min(c1, c2), max(c1, c2) + 1))

    used: dict[tuple[str, str], int] = {}
    corridor: list[tuple[dict, dict, dict]] = []
    for conn in connections:
        src, dst = by_id[conn["from"]], by_id[conn["to"]]
        if blocked(src["row"], src["col"], dst["row"], dst["col"]):
            corridor.append((conn, src, dst))
            continue
        if dst["col"] != src["col"]:
            sides = ("right", "left") if dst["col"] > src["col"] else ("left", "right")
        else:
            sides = ("bottom", "top") if dst["row"] > src["row"] else ("top", "bottom")
            if conn.get("label") and dst["row"] > src["row"]:
                conn["labelDy"] = 24
        used[(src["id"], sides[0])] = used.get((src["id"], sides[0]), 0) + 1
        used[(dst["id"], sides[1])] = used.get((dst["id"], sides[1]), 0) + 1

    lanes: dict[tuple[str, float], int] = {}

    def lane(axis: str, value: float) -> float:
        n = lanes.get((axis, value), 0)
        lanes[(axis, value)] = n + 1
        return value + (n + 1) // 2 * 8 * (1 if n % 2 else -1)

    for conn, src, dst in corridor:
        (r1, c1), (r2, c2) = (src["row"], src["col"]), (dst["row"], dst["col"])
        vs, vd = ("bottom", "top") if r2 > r1 else ("top", "bottom")
        hs, hd = ("right", "left") if c2 > c1 else ("left", "right")
        if c1 == c2:
            inner = "left" if c1 == layout["cols"] - 1 and c1 > 0 else "right"
            candidates = [(side, side, [("x", col_lane(c1, side), cy(r1)), ("x", col_lane(c1, side), cy(r2))])
                          for side in (inner, "right" if inner == "left" else "left")]
            candidates.append((vd, vs, [("y", cx(c1), row_lane(r1, vd)), ("xy", col_lane(c1, inner), row_lane(r1, vd)),
                                        ("xy", col_lane(c1, inner), row_lane(r2, vs)), ("y", cx(c2), row_lane(r2, vs))]))
        elif r1 == r2:
            candidates = [(side, side, [("y", cx(c1), row_lane(r1, side)), ("y", cx(c2), row_lane(r1, side))])
                          for side in ("bottom", "top")]
        else:
            candidates = [
                (vs, hd, [("y", cx(c1), row_lane(r1, vs)), ("xy", col_lane(c2, hd), row_lane(r1, vs)),
                          ("x", col_lane(c2, hd), cy(r2))]),
                (hs, vd, [("x", col_lane(c1, hs), cy(r1)), ("xy", col_lane(c1, hs), row_lane(r2, vd)),
                          ("y", cx(c2), row_lane(r2, vd))], 2),
                (vs, vs, [("y", cx(c1), row_lane(r1, vs)), ("xy", col_lane(c2, hd), row_lane(r1, vs)),
                          ("xy", col_lane(c2, hd), row_lane(r2, vs)), ("y", cx(c2), row_lane(r2, vs))]),
            ]
            if abs(r2 - r1) == 1:
                candidates.insert(0, (vs, vd, [("y", cx(c1), row_lane(r1, vs)), ("y", cx(c2), row_lane(r1, vs))]))
        from_side, to_side, points, *label_segment = min(candidates, key=lambda cand: (
            used.get((src["id"], cand[0]), 0) + used.get((dst["id"], cand[1]), 0)
            + 10 * any(x < ox or x > grid_right or y > grid_bottom for _, x, y in cand[2])))
        used[(src["id"], from_side)] = used.get((src["id"], from_side), 0) + 1
        used[(dst["id"], to_side)] = used.get((dst["id"], to_side), 0) + 1
        x_lane = next((x for axis, x, _ in points if "x" in axis), None)
        y_lane = next((y for axis, _, y in points if "y" in axis), None)
        x_off = 0 if x_lane is None else lane("x", x_lane) - x_lane
        y_off = 0 if y_lane is None else lane("y", y_lane) - y_lane
        if label_segment and conn.get("label"):
            conn["labelSegment"] = label_segment[0]
        conn.update(fromSide=from_side, toSide=to_side, via=[
            [x + (x_off if "x" in axis else 0), y + (y_off if "y" in axis else 0)] for axis, x, y in points])


def _box_width(components: list[dict]) -> int:
    """Uniform box width that fits every label (Archify: 6.6px per text unit,
    8px overhang allowed) and sublabel (6px legible minimum x 0.6 advance, 8px padding)."""
    need = max(max(_units(c["label"]) * 6.6 - 8, _units(c.get("sublabel", "")) * 3.6 + 8) for c in components)
    return int(min(_BOX_W_MAX, max(_BOX_W_MIN, math.ceil(need))))


def _gap_x(connections: list[dict]) -> int:
    """Column gap wide enough for the widest connection label (Archify sizes
    labels at 4.8px per text unit + 10px padding), plus room for corridor lanes."""
    units = max((_units(c["label"]) for c in connections if c.get("label")), default=0)
    return int(min(_GAP_X_MAX, max(_GAP_X_MIN, units * 4.8 + 42)))


def _units(text: str) -> int:
    """Archify text units: full-width glyphs count 2."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _diag(code: str, subject: Any, message: str) -> dict:
    return {"code": code, "subject": str(subject), "message": message}


def renderable_archify(stored: Any) -> dict | None:
    """Re-normalize a persisted spec so older rows get the current layout
    rules; None (UI falls back to mermaid) when it can't be made renderable."""
    try:
        return coerce_archify_spec(stored)
    except DiagramError as exc:
        logger.warning("stored archify spec not renderable: %s %s", exc, exc.diagnostics)
        return None
