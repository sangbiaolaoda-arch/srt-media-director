"""Render fidelity — does observed reality match the runtime's claim?

This is the *browser* half of the falsifiability loop. It compares the
runtime's claimed final frame against the state the browser actually produced,
using structural checks (presence, visibility, focus, edges) plus a
**calibrated** geometry tolerance.

Thresholds are browser thresholds, kept separate from runtime thresholds (v4).
They come from :mod:`thresholds` — a measured calibration artifact when one
exists, documented defaults otherwise.

Failure classification (Directive v5 §40-§44, §60) is honest about *whose*
fault a discrepancy is:

  * ``ENVIRONMENT_FAIL``   — the browser could not produce a valid observation
                             (no functional Chromium, timeout, probe error). The
                             runtime/renderer are NOT blamed (§43).
  * ``OBSERVATION_FAIL``   — the observer dropped nodes the renderer actually
                             emitted (detected against an independent emitted-id
                             set). We must not misattribute this to the runtime
                             (§42).
  * ``RENDER_FAIL``        — the renderer's output genuinely violates the
                             independent projection.
  * ``PERCEPTUAL_DRIFT``   — reserved for pixel-only problems (see pixel.py).
  * ``PASS``               — everything matched.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from world_state.model import WorldState

from . import projection, taxonomy, thresholds as thresholds_mod


def _classify(observed: Dict[str, Any], problems: List[Tuple[str, Any]],
              emitted_ids: Optional[Set[str]], obs_ids: Set[str]) -> Tuple[str, str]:
    """Return ``(status, failure_class)`` with honest, domain-specific blame."""
    if observed.get("error"):
        # Browser failed to produce a valid observation -> environment, not us.
        return "INVALID", taxonomy.ENVIRONMENT_FAIL
    if emitted_ids is not None:
        dropped = emitted_ids - obs_ids
        if dropped:
            # The DOM the renderer emitted contained these nodes, but the
            # observer never reported them -> the *observer* is at fault.
            return "OBSERVATION_INVALID", taxonomy.OBSERVATION_FAIL
    if problems:
        return "FIDELITY_FAIL", taxonomy.RENDER_FAIL
    return "FIDELITY_OK", taxonomy.PASS


def compare(runtime_ws: WorldState, observed: Dict[str, Any],
            thr: Optional[Dict[str, Any]] = None,
            *, emitted_ids: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Return a fidelity report for the runtime's *final* frame vs observation.

    ``emitted_ids`` is an *independent* signal: the node ids the renderer's HTML
    actually contained (from the DOM source, not from the observation). It lets
    us separate "renderer never drew it" (RENDER_FAIL) from "observer lost it"
    (OBSERVATION_FAIL) — a distinction that would otherwise be invisible.
    """
    if not observed.get("available", False):
        return {"status": "UNAVAILABLE", "failure_class": taxonomy.ENVIRONMENT_FAIL,
                "fault_domain": taxonomy.fault_domain(taxonomy.ENVIRONMENT_FAIL),
                "available": False, "problems": [],
                "note": "no browser; fidelity not evaluated (honest degradation)"}

    thr = thr or thresholds_mod.effective()
    area_min = float(thr.get("area_min_px2", 1.0))
    opacity_min = float(thr.get("opacity_min", 0.01))
    tol = float(thr.get("geometry_tol_px", 1.0))

    rf = runtime_ws.frames[-1]
    obs_nodes = {n["id"]: n for n in observed.get("nodes", [])}
    obs_ids = set(obs_nodes)
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

    status, failure_class = _classify(observed, problems, emitted_ids, obs_ids)
    report = {
        "status": status,
        "failure_class": failure_class,
        "fault_domain": taxonomy.fault_domain(failure_class),
        "available": True,
        "backend": observed.get("backend"),
        "thresholds": {"source": thr.get("source"), "n": thr.get("n"),
                       "geometry_tol_px": tol},
        "problems": [{"kind": k, "detail": d} for k, d in problems],
        "geometry": geometry,
    }
    if emitted_ids is not None:
        report["dropped_by_observer"] = sorted(emitted_ids - obs_ids)
    return report
