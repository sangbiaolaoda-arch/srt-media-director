"""Behavior-preserving geometry adapters (code-capability upgrade).

The canonical algebra lives in :mod:`geometry.matrix`. Some existing call sites
predate it and must keep producing **exactly** their historical pixels (golden
frames, contract artifacts). These adapters reproduce the old arithmetic
byte-for-byte so a call site can *delegate* without changing output; the
deliberate semantic difference (rotation handling) stays a separately-tracked,
quantified divergence in :mod:`geometry.audit` rather than being silently applied.

In particular ``scene.scene_graph`` used scalar inheritance: ``world_origin``
offsets by *parent scale only* and ``world_box`` is ``[ox, oy, w*s, h*s]`` -- it
ignores rotation. ``scene_*`` below is that exact math.
"""
from __future__ import annotations

from typing import List, Tuple

from . import box as _box
from . import matrix as _m


# ---------------------------------------------------- scene.scene_graph (scalar)

def scene_world_scale(node) -> float:
    """Chain product of scales (node -> root), matching the old scene_graph."""
    s = node.scale
    n = node.parent
    while n is not None:
        s *= n.scale
        n = n.parent
    return s


def scene_world_origin(node) -> Tuple[float, float]:
    """Old scene_graph origin: recurse up, offset by *parent* accumulated scale."""
    if node.parent is None:
        return (node.x, node.y)
    px, py = scene_world_origin(node.parent)
    ps = scene_world_scale(node.parent)
    return (px + node.x * ps, py + node.y * ps)


def scene_world_box(node) -> List[float]:
    """Old scene_graph box: axis-aligned, rotation ignored."""
    ox, oy = scene_world_origin(node)
    s = scene_world_scale(node)
    return [ox, oy, node.w * s, node.h * s]


def scene_world_center(node) -> Tuple[float, float]:
    x, y, w, h = scene_world_box(node)
    return (x + w / 2.0, y + h / 2.0)


# -------------------------------- canonical mapping (what the adapter can't do)

def canonical_for_scene_box(node) -> Tuple[float, float, float, float]:
    """The canonical rotation-aware box for the same chain.

    Exposed so tests can assert the adapter matches canonical when every chain
    rotation is 0, and diverges (as tracked) when it is not.
    """
    parts = []
    chain = []
    n = node
    while n is not None:
        chain.append(n)
        n = n.parent
    for n in reversed(chain):
        parts.append((n.x, n.y, getattr(n, "rotation", 0.0), n.scale))
    return _m.world_box(_m.chain_world_matrix(parts), node.w, node.h)


# ------------------------------------------- box helpers (behavior-preserving)

def planner_rect(norm, W, H):
    """composition_planner._rect: normalized -> pixel dict box."""
    x, y, w, h = _box.rect_from_norm(norm, W, H)
    return {"x": x, "y": y, "w": w, "h": h}


def planner_intersect(a, b):
    """composition_planner._intersect: dict boxes, strict >2px on both axes."""
    return _box.overlaps((a["x"], a["y"], a["w"], a["h"]),
                         (b["x"], b["y"], b["w"], b["h"]), tol=2.0)


def planner_area(b):
    """composition_planner._area: historical unclamped ``w*h``."""
    return _box.area_unsafe((b["x"], b["y"], b["w"], b["h"]))


def planner_center(b):
    """composition_planner._center_of."""
    return _box.center((b["x"], b["y"], b["w"], b["h"]))


def negspace_area(b):
    """compiler.negative_space._area: clamped area over an indexable box."""
    if not b:
        return 0.0
    try:
        return _box.area((b[0], b[1], b[2], b[3]))
    except Exception:
        return 0.0
