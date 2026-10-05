"""Transform divergence audit (code-capability upgrade).

Measures how far each subsystem's world-transform math drifts from the canonical
algebra in :mod:`geometry.matrix`. Findings are *evidence*, not failures: the
audit exists so that "the Agent described one local coordinate system and two
scene systems drew two world boxes" is a visible, quantified fact.

Every ``audit_*`` function returns a list of divergence records::

    {"source": <module/function>, "case": <scenario>, "canonical": <id>,
     "theirs": <impl note>, "max_delta": <float pixels>, "severity": <str>}

``max_delta`` is the max absolute difference (L-infinity over the four box
numbers) against the canonical box, maximized over a set of rotation samples.
Severity is by pixel magnitude: match <=1e-6, minor <2, material <50, else
severe.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import matrix as _m

_SAMPLE_ROTATIONS = [0.0, 15.0, 30.0, 45.0, 90.0, -30.0, 137.0]


def _linf(a: Tuple[float, float, float, float],
          b: Tuple[float, float, float, float]) -> float:
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


def _severity(px: float) -> str:
    if px <= 1e-6:
        return "match"
    if px < 2.0:
        return "minor"
    if px < 50.0:
        return "material"
    return "severe"


def _rec(source: str, case: str, canonical: str, theirs: str, delta: float) -> Dict[str, Any]:
    return {"source": source, "case": case, "canonical": canonical, "theirs": theirs,
            "max_delta": round(float(delta), 6), "severity": _severity(delta)}


def _canon_box(parts, w: float, h: float) -> Tuple[float, float, float, float]:
    return _m.world_box(_m.chain_world_matrix(parts), w, h)


def audit_motion_runtime_scene() -> List[Dict[str, Any]]:
    """motion_runtime.scene.world_box vs canonical (should be the same algebra)."""
    try:
        from motion_runtime.scene import SceneGraph as MSG  # type: ignore
    except Exception as e:  # pragma: no cover - import guard
        return [{"source": "motion_runtime.scene", "error": repr(e)}]
    worst = 0.0
    for rot in _SAMPLE_ROTATIONS:
        g = MSG("root")
        g.add("a", parent="root", x=100.0, y=50.0, rotation=rot, scale=1.5, w=40.0, h=20.0)
        g.add("b", parent="a", x=10.0, y=5.0, rotation=0.0, scale=1.0, w=8.0, h=6.0)
        theirs = tuple(float(v) for v in g.world_box("b"))
        canon = _canon_box([(100.0, 50.0, rot, 1.5), (10.0, 5.0, 0.0, 1.0)], 8.0, 6.0)
        worst = max(worst, _linf(theirs, canon))
    return [_rec("motion_runtime.scene.world_box", "rotated parent chain",
                 "geometry.matrix.world_box", "corner-based affine", worst)]


def audit_scene_graph() -> List[Dict[str, Any]]:
    """scene.scene_graph.world_box vs canonical: matches w/o rotation, drifts with it."""
    try:
        from scene.scene_graph import SceneGraph as SSG  # type: ignore
    except Exception as e:  # pragma: no cover - import guard
        return [{"source": "scene.scene_graph", "error": repr(e)}]
    no_rot = 0.0
    rot_worst = 0.0
    for rot in _SAMPLE_ROTATIONS:
        g = SSG("scene")
        g.add("scene", "a", x=100.0, y=50.0, rotation=rot, scale=1.5, w=40.0, h=20.0)
        g.add("a", "b", x=10.0, y=5.0, rotation=0.0, scale=1.0, w=8.0, h=6.0)
        theirs = tuple(float(v) for v in g.get("b").world_box())
        canon = _canon_box([(100.0, 50.0, rot, 1.5), (10.0, 5.0, 0.0, 1.0)], 8.0, 6.0)
        d = _linf(theirs, canon)
        if abs(rot) < 1e-9:
            no_rot = d
        else:
            rot_worst = max(rot_worst, d)
    return [
        _rec("scene.scene_graph.world_box", "translate+scale (no rotation)",
             "geometry.matrix.world_box", "scalar inheritance", no_rot),
        _rec("scene.scene_graph.world_box", "rotated parent chain",
             "geometry.matrix.world_box", "scalar inheritance (rotation ignored)", rot_worst),
    ]


def audit_box_helpers() -> List[Dict[str, Any]]:
    """Same box questions answered two ways: measure the drift.

    ``composition_planner._area`` is a raw ``w*h``; canonical clamps to >=0. They
    agree on every real box and differ only for degenerate (negative-dimension)
    boxes, which the audit makes explicit.
    """
    from . import box as _b

    normal = [(0.0, 0.0, 10.0, 10.0), (5.0, 5.0, 200.0, 80.0)]
    degen = [(0.0, 0.0, -5.0, 4.0)]

    normal_worst = max(abs(_b.area_unsafe(t) - _b.area(t)) for t in normal)
    degen_worst = max(abs(_b.area_unsafe(t) - _b.area(t)) for t in degen)

    # intersection rule drift: planner is strict >2px, canonical default tol=2.0
    a, b = (0.0, 0.0, 10.0, 10.0), (10.0, 0.0, 10.0, 10.0)  # edge-touching
    cross = 1.0 if _b.overlaps(a, b, tol=2.0) else 0.0

    return [
        _rec("composition_planner._area", "normal boxes",
             "geometry.box.area", "unclamped w*h", normal_worst),
        _rec("composition_planner._area", "degenerate box",
             "geometry.box.area", "unclamped w*h (canonical clamps to >=0)", degen_worst),
        _rec("composition_planner._intersect", "edge-touching boxes",
             "geometry.box.overlaps", "strict >2px both axes", cross),
    ]


def divergences() -> List[Dict[str, Any]]:
    """All divergence records across the audited subsystems."""
    out: List[Dict[str, Any]] = []
    for fn in (audit_motion_runtime_scene, audit_scene_graph, audit_box_helpers):
        out.extend(fn())
    return out


def diverging() -> List[Dict[str, Any]]:
    """Only records whose transform materially differs from canonical."""
    return [d for d in divergences() if d.get("severity") in ("material", "severe")]
