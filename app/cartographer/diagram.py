"""Archify-style deterministic diagram rendering for chartographer.

Parses the Analysis Mermaid flowchart into a typed topology, lays it out on a
grid, routes orthogonal edges, validates the result, and renders a
self-contained dark/light HTML artifact.

Layout geometry, port routing, and the validation checks are ported from
tt-a1i/archify (MIT, v2.17) — renderers/architecture/grid.mjs,
renderers/shared/geometry.mjs, renderers/shared/diagnostics.mjs.

# ponytail: TD-only layout and a single neutral node style — mermaid flowcharts
# carry no component-type information. Add type classification + LR support if
# a user asks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── parsing ──────────────────────────────────────────────────────────────────

_NODE_DEF = re.compile(
    r"(?P<id>[A-Za-z_][\w-]*)\s*(?:\[(?P<sq>[^\]]*)\]|\((?P<par>[^)]*)\)|\{(?P<br>[^}]*)\})?"
)
_EDGE = re.compile(
    r"(?P<a>[A-Za-z_][\w-]*)\s*(?:--\s*(?P<lbl>[^-]+?)\s*-|-{2,3}|-\.+->|=+>)\s*>?\s*(?P<b>[A-Za-z_][\w-]*)"
)


class DiagramError(ValueError):
    """Mermaid source the parser cannot turn into a clean topology."""

    def __init__(self, message: str, diagnostics: list[dict] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or []


@dataclass
class Topology:
    nodes: dict[str, str] = field(default_factory=dict)   # id -> label
    edges: list[tuple[str, str, str | None]] = field(default_factory=list)  # src, dst, label


def parse_mermaid(source: str) -> Topology:
    """Parse the flowchart subset chartographer's analyst emits.

    Supports `flowchart TD|graph TD` (+ LR), node defs `A[Label]` / `A(Label)` /
    plain ids, edges `-->`, `---`, `-.->`, `==>` with labels via
    `-- text -->` or `|text|`. Raises DiagramError on anything unparseable so
    the caller can retry the LLM once with the diagnostics.
    """
    topo = Topology()
    direction = "TD"
    body: list[str] = []
    for raw in (source or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        m = re.match(r"^(?:flowchart|graph)\s+(TD|TB|LR|RL)\b", line, re.I)
        if m:
            direction = m.group(1).upper()
            continue
        if re.match(r"^(subgraph|end|classDef|class|style|click)\b", line, re.I):
            continue
        body.append(line)

    # Edge statements first; leftovers are node definitions.
    for line in body:
        stmts = _split_statements(line)
        for stmt in stmts:
            if not _parse_edge_stmt(stmt, topo):
                if not _parse_node_def(stmt, topo):
                    raise DiagramError(
                        f"Unparseable mermaid statement: {stmt!r}",
                        [{"code": "parse/statement", "subject": stmt, "message": f"Cannot parse {stmt!r}"}],
                    )
    if not topo.nodes:
        raise DiagramError("No nodes found in mermaid source.")
    if topo.edges:
        known = set(topo.nodes)
        for a, b, _ in topo.edges:
            for endpoint in (a, b):
                if endpoint not in known:
                    raise DiagramError(f"Edge references undefined node {endpoint!r}.")
    topo.edges = topo.edges if direction != "RL" else [(b, a, lbl) for a, b, lbl in topo.edges]
    return topo


def _split_statements(line: str) -> list[str]:
    # `A --> B & C` — expand `&` chains on both sides.
    out: list[str] = []
    parts = re.split(r"\s+(?:(?:-{2,3}|-\.+|=+)\s*>)?\s*&\s+", line)
    if len(parts) > 1:
        # keep it simple: treat each `&`-separated chunk as its own statement
        out.extend(p.strip() for p in parts if p.strip())
    else:
        out.append(line)
    return out


def _parse_edge_stmt(stmt: str, topo: Topology) -> bool:
    label = None
    s = stmt
    # register inline node defs (`A[Label]`) and strip them for edge matching
    for m in re.finditer(r"([A-Za-z_][\w-]*)\s*(\[.*?\]|\(.*?\)|\{.*?\})", s):
        inner = m.group(2)[1:-1].strip()
        while len(inner) > 1 and inner[0] in "([{" and inner[-1] in ")]}":
            inner = inner[1:-1].strip()
        topo.nodes.setdefault(m.group(1), inner or m.group(1))
    s = re.sub(r"\[.*?\]|\(.*?\)|\{.*?\}", "", s)
    lm = re.search(r"\|([^|]+)\|", s)
    if lm:
        label = lm.group(1).strip()
        s = s.replace(lm.group(0), " ")
    # `A -- text --> B`
    m = re.match(
        r"^(?P<a>[A-Za-z_][\w-]*)\s*--\s*(?P<lbl>[^-]+?)\s*-->\s*(?P<b>[A-Za-z_][\w-]*)\s*$",
        s,
    )
    if not m:
        m = re.match(
            r"^(?P<a>[A-Za-z_][\w-]*)\s*-\.\s*(?P<lbl>[^.]+?)\s*\.->\s*(?P<b>[A-Za-z_][\w-]*)\s*$",
            s,
        )
    if not m:
        m = re.match(
            r"^(?P<a>[A-Za-z_][\w-]*)\s*(?P<arrow>-{2,3}>?|-\.+->|=+>|x-+>|o-+>|<-+>)\s*(?P<b>[A-Za-z_][\w-]*)\s*$",
            s,
        )
    if not m:
        return False
    if "lbl" in m.groupdict() and m.groupdict().get("lbl"):
        label = m.group("lbl").strip()
    topo.nodes.setdefault(m.group("a"), m.group("a"))
    topo.nodes.setdefault(m.group("b"), m.group("b"))
    topo.edges.append((m.group("a"), m.group("b"), label))
    return True


def _parse_node_def(stmt: str, topo: Topology) -> bool:
    m = _NODE_DEF.fullmatch(stmt.strip())
    if not m or not m.group("id"):
        return False
    label = (m.group("sq") or m.group("par") or m.group("br") or m.group("id") or "").strip()
    while len(label) > 1 and label[0] in "([{" and label[-1] in ")]}":
        label = label[1:-1].strip()
    topo.nodes[m.group("id")] = label or m.group("id")
    return True


# ── geometry (ported from archify grid.mjs + geometry.mjs, minimal subset) ───

CELL_W, CELL_H, GAP_X, GAP_Y = 150.0, 64.0, 70.0, 70.0
PAD = 40.0


@dataclass
class LaidNode:
    id: str
    label: str
    x: float
    y: float
    w: float = CELL_W
    h: float = CELL_H

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.w, self.h)


def layout(topo: Topology) -> tuple[list[LaidNode], dict[str, list[list[float]]], dict[str, tuple[float, float]]]:
    """Grid layout: longest-path layering (rows), appearance order (columns).

    Returns (nodes, routes, label_positions). Routes are lists of 2+ [x, y]
    points from the source's bottom port to the target's top port.
    """
    succ: dict[str, list[str]] = {n: [] for n in topo.nodes}
    indeg: dict[str, int] = {n: 0 for n in topo.nodes}
    for a, b, _ in topo.edges:
        if b not in succ[a]:
            succ[a].append(b)
            indeg[b] += 1

    # longest-path depth (Kahn, deterministic order)
    order = list(topo.nodes)  # insertion order = mermaid appearance order
    depth = {n: 0 for n in order}
    queue = [n for n in order if indeg[n] == 0]
    remaining = dict(indeg)
    seen = 0
    while queue:
        n = queue.pop(0)
        seen += 1
        for s in succ[n]:
            depth[s] = max(depth[s], depth[n] + 1)
            remaining[s] -= 1
            if remaining[s] == 0:
                queue.append(s)
    if seen != len(order):
        cyc = [n for n, r in remaining.items() if r > 0]
        raise DiagramError(
            "Mermaid graph has a cycle; flowchart diagrams must be acyclic.",
            [{"code": "layout/cycle", "subject": ",".join(cyc), "message": "cycle detected"}],
        )

    rows: dict[int, list[str]] = {}
    for n in order:
        rows.setdefault(depth[n], []).append(n)

    laid: list[LaidNode] = []
    pos: dict[str, LaidNode] = {}
    max_cols = max(len(r) for r in rows.values())
    width = max_cols * CELL_W + (max_cols - 1) * GAP_X
    for r, members in sorted(rows.items()):
        row_w = len(members) * CELL_W + (len(members) - 1) * GAP_X
        x0 = PAD + (width - row_w) / 2
        for c, nid in enumerate(members):
            node = LaidNode(id=nid, label=topo.nodes[nid], x=x0 + c * (CELL_W + GAP_X),
                            y=PAD + r * (CELL_H + GAP_Y))
            laid.append(node)
            pos[nid] = node

    routes: dict[str, list[list[float]]] = {}
    labels: dict[str, tuple[float, float]] = {}
    row_bands = {r: (PAD + r * (CELL_H + GAP_Y), PAD + r * (CELL_H + GAP_Y) + CELL_H) for r in rows}

    for i, (a, b, label) in enumerate(topo.edges):
        src, dst = pos[a], pos[b]
        # Port spread (archify): multiple edges leaving one node share its
        # bottom edge; arriving edges share the top edge. Offset each so
        # parallel drops never overlap.
        out_edges = [j for j, (x, _y, _l) in enumerate(topo.edges) if x == a]
        in_edges = [j for j, (_x, y, _l) in enumerate(topo.edges) if y == b]
        ko = out_edges.index(i)
        ki = in_edges.index(i)
        sx = src.x + src.w * (ko + 1) / (len(out_edges) + 1)
        sy = src.y + src.h
        tx = dst.x + dst.w * (ki + 1) / (len(in_edges) + 1)
        ty = dst.y
        ra, rb = depth[a], depth[b]
        lo, hi = min(ra, rb), max(ra, rb)
        elbow = sy + 12  # corridor-top elbow: short stub down, then horizontal
        if ra == rb:  # same row: route over the top through the gap above
            lane = row_bands[lo][0] - GAP_Y / 2
            path = [[sx, sy], [sx, lane], [tx, lane], [tx, ty]] if sx != tx else [[sx, sy], [tx, ty]]
            label_y = lane
        elif abs(sx - tx) < 1 and not _blocked(pos, sx, sy, ty, skip={a, b}):
            path = [[sx, sy], [tx, ty]]               # same column, clear drop
            label_y = (sy + ty) / 2
        else:
            path = [[sx, sy], [sx, elbow], [tx, elbow], [tx, ty]]
            label_y = elbow
            # Side bridge: if an intermediate row blocks the vertical drops,
            # detour around the nearer side (archify outside-bridge).
            crossed = [r for r in rows if lo < r < hi]
            for r in crossed:
                blockers = [pos[n] for n in rows[r]
                            if (min(sx, tx) - 20) < pos[n].x + pos[n].w and pos[n].x < (max(sx, tx) + 20)
                            and not (pos[n].y + pos[n].h <= sy or pos[n].y >= ty)]
                if not blockers:
                    continue
                grid_left = min(n.x for n in laid) - 40
                grid_right = max(n.x + n.w for n in laid) + 40
                # nearest side with room
                if abs(min(b2.x for b2 in blockers) - grid_left) <= abs(grid_right - max(b2.x + b2.w for b2 in blockers)):
                    bridge = grid_left
                else:
                    bridge = grid_right
                band_top, band_bot = row_bands[r][0], row_bands[r][1]
                approach = band_top - GAP_Y / 4
                exit_ = band_bot + GAP_Y / 4
                path = [[sx, sy], [sx, approach], [bridge, approach], [bridge, exit_], [tx, exit_], [tx, ty]]
                label_y = approach
                break
        key = f"e{i}"
        routes[key] = path
        if label:
            labels[key] = (sx + tx) / 2, label_y
    return laid, routes, labels


def _blocked(pos: dict[str, LaidNode], x: float, y_top: float, y_bot: float, skip: set[str]) -> bool:
    for n in pos.values():
        if n.id in skip:
            continue
        if abs(n.x + n.w / 2 - x) < (n.w / 2 + 6) and n.y < y_bot and n.y + n.h > y_top:
            return True
    return False


# ── validation (top 3 checks from archify diagnostics.mjs) ──────────────────

def rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float], gap: float = 0) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + gap <= bx or bx + bw + gap <= ax or ay + ah + gap <= by or by + bh + gap <= ay)


def _point_seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5


def _seg_rect_clearance(seg: tuple[list[float], list[float]], rect: tuple[float, float, float, float]) -> float:
    """Min distance from segment to rect; 0 when intersecting. (archify geometry.mjs)"""
    rx, ry, rw, rh = rect
    (x1, y1), (x2, y2) = seg[0], seg[-1]
    # axis-aligned segments only (our router) → cheap exact check
    if rx - max(x1, x2) > 0 or min(x1, x2) - (rx + rw) > 0 or \
       ry - max(y1, y2) > 0 or min(y1, y2) - (ry + rh) > 0:
        # disjoint bbox: distance from rect corners to segment
        corners = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)]
        return min(_point_seg_dist(cx, cy, x1, y1, x2, y2) for cx, cy in corners)
    return 0.0


def validate(laid: list[LaidNode], routes: dict[str, list[list[float]]],
             labels: dict[str, tuple[float, float]]) -> list[dict]:
    """Port of archify's top 3 showcase checks. Returns [] when clean."""
    diags: list[dict] = []
    label_w = 90.0  # label mask box (archify measures text; we budget worst-case)
    label_h = 14.0
    node_rects = {n.id: n.rect for n in laid}
    for key, (lx, ly) in labels.items():
        lrect = (lx - label_w / 2, ly - label_h / 2, label_w, label_h)
        for nid, nrect in node_rects.items():
            if rects_overlap(lrect, nrect):
                diags.append({
                    "code": "layout/label-overlaps-node", "subject": key,
                    "message": f"Label on {key} overlaps component {nid!r}",
                    "suggested_fix": "spread rows/cols (increase GAP_X/GAP_Y)",
                })
        for okey, opath in routes.items():
            if okey == key:
                continue
            for seg in zip(opath, opath[1:]):
                if _seg_rect_clearance(seg, lrect) < 4.0:
                    diags.append({
                        "code": "composition/label-route-clearance", "subject": key,
                        "message": f"Label on {key} is within 4px of route {okey}",
                        "suggested_fix": "increase GAP_Y between rows",
                    })
                    break
    for key, path in routes.items():
        seg_rects = [
            (min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]) or 0.01, abs(b[1] - a[1]) or 0.01)
            for a, b in zip(path, path[1:])
        ]
        src_id = topo_of(laid, path[0])
        dst_id = topo_of(laid, path[-1])
        for seg_rect in seg_rects:
            for nid, nrect in node_rects.items():
                if nid in (src_id, dst_id):
                    continue  # its own ports touch it by design
                if rects_overlap(seg_rect, nrect):
                    diags.append({
                        "code": "clean-flow/edge-crosses-node", "subject": key,
                        "message": f"Route {key} crosses component {nid!r}",
                        "suggested_fix": "reorder columns (appearance order) or increase GAP_X",
                    })
                    break
    return diags


def topo_of(laid: list[LaidNode], point: list[float]) -> str | None:
    px, py = point
    for n in laid:
        if n.x <= px <= n.x + n.w and n.y <= py <= n.y + n.h:
            return n.id
    return None


# ── rendering: self-contained HTML, archify design tokens (MIT, attributed) ──

_CSS = """\
/* Design tokens adapted from tt-a1i/archify (MIT) — v2.17 */
:root { --bg:#0f1216; --panel:#161b22; --ink:#e6edf3; --muted:#8b949e;
  --accent:#4c8dff; --node:#1d2430; --node-border:#33415580; --edge:#5a6472; --label:#c3cbd6; }
.light { --bg:#ffffff; --panel:#f6f8fa; --ink:#1f2328; --muted:#59636e;
  --accent:#0969da; --node:#ffffff; --node-border:#d0d7de; --edge:#8c959f; --label:#424a53; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  display:flex; flex-direction:column; align-items:center; min-height:100vh; }
header { width:100%; display:flex; justify-content:space-between; align-items:center;
  padding:16px 24px; }
h1 { font-size:16px; margin:0; }
svg { background:var(--panel); border-radius:12px; max-width:96vw; height:auto; }
.node rect { fill:var(--node); stroke:var(--node-border); stroke-width:1.5; rx:10; }
.node text { fill:var(--ink); font-weight:600; font-size:13px; text-anchor:middle; }
.edge path { fill:none; stroke:var(--edge); stroke-width:1.5; }
.edge polygon { fill:var(--edge); stroke:none; }
.elabel { fill:var(--label); font-size:11px; text-anchor:middle;
  paint-order:stroke; stroke:var(--panel); stroke-width:4px; }
"""

_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{css}</style></head>
<body>
<header><h1>{title}</h1>
<label><input type="checkbox" id="theme" onchange="document.body.classList.toggle('light')"> light mode</label>
</header>
{svg}
</body></html>"""


def render_html(mermaid: str, title: str = "Architecture") -> str:
    """Mermaid source -> self-contained archify-styled HTML. Raises DiagramError."""
    topo = parse_mermaid(mermaid)
    laid, routes, labels = layout(topo)
    diags = validate(laid, routes, labels)
    if diags:
        raise DiagramError("Diagram layout failed validation.", diags)

    xs = [float(p[0]) for path in routes.values() for p in path] + [n.x for n in laid] + [n.x + n.w for n in laid]
    ys = [float(p[1]) for path in routes.values() for p in path] + [n.y for n in laid] + [n.y + n.h for n in laid]
    min_x, max_x = min(xs) - 10, max(xs) + 10
    min_y, max_y = min(ys) - 10, max(ys) + 10
    parts = [f'<svg viewBox="{min_x:.0f} {min_y:.0f} {max_x - min_x:.0f} {max_y - min_y:.0f}" role="img">']
    for key, path in routes.items():
        d = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in path)
        parts.append(f'<g class="edge"><path d="{d}"/>'
                     f'<polygon points="{path[-1][0]:.1f},{path[-1][1]:.1f} '
                     f'{path[-1][0] - 4:.1f},{path[-1][1] - 8:.1f} {path[-1][0] + 4:.1f},{path[-1][1] - 8:.1f}"/></g>')
    for key, (lx, ly) in labels.items():
        parts.append(f'<text class="elabel" x="{lx:.1f}" y="{ly:.1f}">{_esc(labels_text(topo, key))}</text>')
    for n in laid:
        parts.append(
            f'<g class="node"><rect x="{n.x:.1f}" y="{n.y:.1f}" width="{n.w:.0f}" height="{n.h:.0f}" rx="10"/>'
            f'<text x="{n.x + n.w / 2:.1f}" y="{n.y + n.h / 2 + 4:.1f}">{_esc(n.label)}</text></g>'
        )
    parts.append("</svg>")
    return _TEMPLATE.format(title=_esc(title), css=_CSS, svg="\n".join(parts))


def labels_text(topo: Topology, key: str) -> str:
    i = int(key[1:])
    return topo.edges[i][2] or ""


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
