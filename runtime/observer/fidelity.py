"""Render fidelity — does observed reality match the runtime's claim?

This is the *browser* half of the falsifiability loop. It compares the
runtime's claimed final frame against the state the browser actually produced,
using structural checks (presence, visibility, focus, edges) that are robust
in Phase 0.

Thresholds here are *browser* thresholds and are deliberately kept separate
from runtime thresholds (v4: never mix the two). Calibrating them (N>=1000,
p99) is an explicit later step; until then they are documented defaults.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from world_state.model import WorldState

# documented defaults, pending browser-threshold calibration.
MIN_AREA_PX2 = 1.0
OPACITY_MIN = 0.01


def compare(runtime_ws: WorldState, observed: Dict[str, Any]) -> Dict[str, Any]:
    """Return a fidelity report for the runtime's *final* frame vs observation."""
    if not observed.get("available", False):
        return {"status": "UNAVAILABLE", "available": False, "problems": [],
                "note": "no browser; fidelity not evaluated (honest degradation)"}

    rf = runtime_ws.frames[-1]
    obs_nodes = {n["id"]: n for n in observed.get("nodes", [])}
    problems: List[Tuple[str, Any]] = []

    for oid, o in rf.objects.items():
        n = obs_nodes.get(oid)
        if n is None:
            problems.append(("node_missing", oid))
            continue
        area = float(n["w"]) * float(n["h"])
        visible = (n.get("visibility") != "hidden"
                   and n.get("display") != "none"
                   and float(n.get("opacity", 1)) > OPACITY_MIN
                   and area > MIN_AREA_PX2)
        if o.visible and not visible:
            problems.append(("node_not_visible", oid))
        if o.focus and not n.get("focus"):
            problems.append(("focus_lost", oid))

    obs_edges = {(e["source"], e["target"], e["type"]) for e in observed.get("edges", [])}
    for r in rf.relations:
        if (r.source, r.target, r.type) not in obs_edges:
            problems.append(("edge_missing", (r.source, r.target, r.type)))

    geometry = {n["id"]: {"x": n["x"], "y": n["y"], "w": n["w"], "h": n["h"]}
                for n in observed.get("nodes", [])}
    return {
        "status": "FIDELITY_OK" if not problems else "FIDELITY_FAIL",
        "available": True,
        "backend": observed.get("backend"),
        "problems": [{"kind": k, "detail": d} for k, d in problems],
        "geometry": geometry,
    }
