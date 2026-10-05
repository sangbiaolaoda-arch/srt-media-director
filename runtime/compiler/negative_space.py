"""Spec §17 — Negative space / density discipline.

The canvas must not be packed. We guard the Primary's neighbourhood and the
overall element density; over-density triggers recomposition rather than
shipping a crowded frame.
"""
from __future__ import annotations

from geometry import legacy as _geom_legacy

DENSITY_THRESHOLD = 0.58      # total element coverage of the canvas
PRIMARY_CLEAR_RATIO = 0.06    # minimum free ring around the primary


def _area(b):
    # delegate to the canonical box vocabulary (behavior-preserving)
    return _geom_legacy.negspace_area(b)


def density(boxes, canvas_w=1.0, canvas_h=1.0):
    total = sum(_area(b) for b in boxes.values())
    return round(total / max(canvas_w * canvas_h, 1e-9), 4)


def free_ring(box, others):
    """Ratio of the primary's surrounding ring that is NOT covered by others."""
    x, y, w, h = box
    pad = 0.5 * max(w, h)
    rx, ry, rw, rh = x - pad, y - pad, w + 2 * pad, h + 2 * pad
    ring = rw * rh - w * h
    if ring <= 0:
        return 1.0
    occluded = 0.0
    for o in others:
        ox, oy, ow, oh = o
        ix = max(0.0, min(rx + rw, ox + ow) - max(rx, ox))
        iy = max(0.0, min(ry + rh, oy + oh) - max(ry, oy))
        occluded += ix * iy
    return round(max(0.0, 1.0 - occluded / ring), 4)


def audit_negative_space(beat):
    boxes = beat.get("boxes") or {}
    elements = beat.get("elements", [])
    issues = []
    d = density(boxes, beat.get("canvas_w", 1.0), beat.get("canvas_h", 1.0))
    if d > DENSITY_THRESHOLD:
        issues.append({"code": "DENSITY_TOO_HIGH", "severity": "err",
                       "beat_id": beat.get("beat_id"),
                       "msg": "element_density %.3f > %.2f" % (d, DENSITY_THRESHOLD),
                       "fix": ["reduce element count", "shrink support elements",
                               "increase negative space"]})
    prim = [e for e in elements if e.get("role") == "primary"]
    if prim and boxes.get(prim[0].get("id")):
        pid = prim[0].get("id")
        others = [b for i, b in boxes.items() if i != pid and b]
        fr = free_ring(boxes[pid], others)
        if fr < PRIMARY_CLEAR_RATIO:
            issues.append({"code": "PRIMARY_CROWDED", "severity": "warn",
                           "beat_id": beat.get("beat_id"),
                           "msg": "primary free ring %.3f < %.2f" % (fr, PRIMARY_CLEAR_RATIO)})
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "density": d, "issues": issues}
