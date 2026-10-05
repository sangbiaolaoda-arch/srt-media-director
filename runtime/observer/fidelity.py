"""Render fidelity — does observed reality match the runtime's claim?

This is the *browser* half of the falsifiability loop. It compares the
runtime's claimed final frame against the state the browser actually produced,
using structural checks (presence, visibility, focus, edges) plus a
**calibrated** geometry tolerance.

Thresholds are browser thresholds, kept separate from runtime thresholds (v4).
They come from :mod:`thresholds` — a measured calibration artifact when one
exists, documented defaults otherwise.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from world_state.model import WorldState

from . import projection, thresholds as thresholds_mod


def compare(runtime_ws: WorldState, observed: Dict[str, Any],
            thr: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a fidelity report for the runtime's *final* frame vs observation."""
    if not observed.get("available", False):
        return {"status": "UNAVAILABLE", "available": False, "problems": [],
                "note": "no browser; fidelity not evaluated (honest degradation)"}

    thr = thr or thresholds_mod.effective()
    area_min = float(thr.get("area_min_px2", 1.0))
    opacity_min = float(thr.get("opacity_min", 0.01))
    tol = float(thr.get("geometry_tol_px", 1.0))

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
                   and float(n.get("opacity", 1)) > opacity_min
                   and area > area_min)
        if o.visible and not visible:
            problems.append(("node_not_visible", oid))
        if o.focus and not n.get("focus"):
            problems.append(("focus_lost", oid))

    obs_edges = {(e["source"], e["target"], e["type"]) for e in observed.get("edges", [])}
    for r in rf.relations:
        if (r.source, r.target, r.type) not in obs_edges:
            problems.append(("edge_missing", (r.source, r.target, r.type)))

    # geometry fidelity: observed layout vs the INDEPENDENT render projection.
    # Deliberately NOT render.layout_geometry() — the verifier must not ask the
    # renderer what the answer is (Final Directive v5 §1, §4, §66).
    expected_layout = projection.expected_layout(runtime_ws)
    for oid, geo in expected_layout.items():
        n = obs_nodes.get(oid)
        if n is None:
            continue
        delta = max(abs(n["x"] - geo["x"]), abs(n["y"] - geo["y"]),
                    abs(n["w"] - geo["w"]), abs(n["h"] - geo["h"]))
        if delta > tol:
            problems.append(("geometry_out_of_tolerance", (oid, round(delta, 3))))

    geometry = {n["id"]: {"x": n["x"], "y": n["y"], "w": n["w"], "h": n["h"]}
                for n in observed.get("nodes", [])}
    # Fidelity problems are render-execution problems, mapped onto the v5 failure
    # taxonomy (Directive §44): a faithful renderer would not raise them.
    return {
        "status": "FIDELITY_OK" if not problems else "FIDELITY_FAIL",
        "failure_class": "PASS" if not problems else "RENDER_FAIL",
        "available": True,
        "backend": observed.get("backend"),
        "thresholds": {"source": thr.get("source"), "n": thr.get("n"),
                       "geometry_tol_px": tol},
        "problems": [{"kind": k, "detail": d} for k, d in problems],
        "geometry": geometry,
    }
