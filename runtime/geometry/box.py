"""box.py — canonical axis-aligned box semantics (code-capability upgrade).

The same "box questions" (area, center, overlap, normalized->pixel) were answered
by more than one subsystem with subtly different rules:

* ``composition_planner`` --- private ``_rect`` / ``_intersect`` / ``_area`` /
  ``_center_of``; boxes are dicts, and ``_area`` is a raw ``w*h`` (no clamp).
* ``compiler.negative_space`` --- its own ``_area`` that clamps to ``>=0`` and a
  hand-inlined intersection test; boxes are tuples.

Two representations and two area rules for the same concept. This module is the
single source of truth; it works on plain 4-tuples, and call sites convert. Pure,
browser-free, deterministic.
"""
from __future__ import annotations

from typing import Iterable, Tuple

Box = Tuple[float, float, float, float]
DEFAULT_TOL = 2.0


def area(box: Box) -> float:
    """Canonical area: degenerate boxes count as zero, never negative."""
    return max(0.0, float(box[2])) * max(0.0, float(box[3]))


def area_unsafe(box: Box) -> float:
    """Raw ``w*h`` (historical planner rule). Diverges from :func:`area` only
    for degenerate boxes; kept so the divergence stays measurable."""
    return float(box[2]) * float(box[3])


def center(box: Box) -> Tuple[float, float]:
    x, y, w, h = box
    return (x + w / 2.0, y + h / 2.0)


def rect_from_norm(norm: Box, W: float, H: float) -> Box:
    nx, ny, nw, nh = norm
    return (nx * W, ny * H, nw * W, nh * H)


def intersect_area(a: Box, b: Box) -> float:
    ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return max(0.0, ox) * max(0.0, oy)


def overlaps(a: Box, b: Box, tol: float = DEFAULT_TOL) -> bool:
    """True when the intersection exceeds ``tol`` on BOTH axes."""
    ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return ox > tol and oy > tol


def clamp(box: Box, W: float, H: float) -> Box:
    x, y, w, h = box
    x = max(0.0, min(x, max(0.0, W - w)))
    y = max(0.0, min(y, max(0.0, H - h)))
    return (round(x, 2), round(y, 2), round(w, 2), round(h, 2))


def translate(box: Box, dx: float, dy: float) -> Box:
    return (box[0] + dx, box[1] + dy, box[2], box[3])


def inflate(box: Box, pad: float) -> Box:
    return (box[0] - pad, box[1] - pad, box[2] + 2 * pad, box[3] + 2 * pad)


def bbox_of(boxes: Iterable[Box]) -> Box:
    xs = [(b[0], b[0] + b[2]) for b in boxes]
    ys = [(b[1], b[1] + b[3]) for b in boxes]
    x0 = min(x[0] for x in xs)
    x1 = max(x[1] for x in xs)
    y0 = min(y[0] for y in ys)
    y1 = max(y[1] for y in ys)
    return (x0, y0, x1 - x0, y1 - y0)


def to_dict(box: Box) -> dict:
    return {"x": box[0], "y": box[1], "w": box[2], "h": box[3]}


def from_dict(d: dict) -> Box:
    return (d["x"], d["y"], d["w"], d["h"])
