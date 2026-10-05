"""Dynamic timeline observation — Final Directive v5 §35-§36, §61.

Phase 0 observed a single (final) frame. v5 wants an *observed state per time
step*: ``ObservedState(t)`` for ``t0, t1, t2, t3, ...``, so that temporal
properties can be judged on observed reality, not on the runtime's claim.

What we actually check (§36) — NOT "did we take many screenshots":

  * ordering          first_focus(A) < first_focus(B)
  * state transition  an object's visibility/focus changes only where expected
  * relation lifecycle whether connector(A,B,t) holds across the window
  * focus transition  the focal object changes in the expected order

Camera transition is intentionally NOT claimed: the World-State has no camera
dimension yet (§21-§22 say do not advertise dimensions you do not cover). We say
so explicitly instead of faking coverage.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from world_state.model import WorldState

from . import projection

# Explicit per-step observed state. Deliberately a plain structure so it has no
# hidden dependency on the renderer.
ObservedState = Dict[str, Any]


def _state_from_observation(t: float, observed: Dict[str, Any]) -> ObservedState:
    nodes = observed.get("nodes", [])
    return {
        "t": t,
        "available": observed.get("available", False),
        "focus": {n["id"] for n in nodes if n.get("focus")},
        "visible": {n["id"] for n in nodes
                    if n.get("visibility") != "hidden" and n.get("display") != "none"
                    and float(n.get("opacity", 1)) > 0.01
                    and float(n.get("w", 0)) > 0 and float(n.get("h", 0)) > 0},
        "edges": {(e["source"], e["target"], e["type"]) for e in observed.get("edges", [])},
        "ids": {n["id"] for n in nodes},
    }


def expected_timeline(ws: WorldState) -> List[ObservedState]:
    """The expected ObservedState(t) per keyframe, derived from the world state.

    Structure (focus/visible/edges) comes from the world state directly; this is
    the contract the observed timeline is judged against.
    """
    out: List[ObservedState] = []
    for f in ws.frames:
        out.append({
            "t": f.t,
            "focus": {oid for oid, o in f.objects.items() if o.focus},
            "visible": {oid for oid, o in f.objects.items() if o.visible},
            "edges": {(r.source, r.target, r.type) for r in f.relations},
            "ids": set(f.objects.keys()),
        })
    return out


def observe_timeline(ws: WorldState, outdir: str) -> List[ObservedState]:
    """Render each keyframe and observe it in a real browser -> ObservedState(t).

    Browser-gated; degrades honestly (empty list) when no browser is available.
    """
    from . import browser, render  # local import: keep module import-light
    frames = render.render_timeline(ws, outdir)
    states: List[ObservedState] = []
    for path, t in frames:
        obs = browser.observe(path)
        states.append(_state_from_observation(t, obs))
    return states


def first_focus(states: List[ObservedState]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for s in states:
        for oid in s["focus"]:
            out.setdefault(oid, s["t"])
    return out


def _as_timeline(candidate) -> List[ObservedState]:
    """Accept either raw [(t, observed)] pairs or ready ObservedStates."""
    if candidate and isinstance(candidate[0], (tuple, list)):
        return [_state_from_observation(t, o) for t, o in candidate]
    return list(candidate)


def compare_timeline(expected: List[ObservedState], observed) -> Dict[str, Any]:
    """Judge an observed timeline against the expected one.

    Returns a report with the four temporal checks. Missing/unavailable
    observations degrade to OBSERVATION_FAIL rather than a false PASS.
    """
    observed = _as_timeline(observed)
    if not observed or not any(s.get("available", True) for s in observed):
        return {"status": "UNAVAILABLE", "failure_class": "ENVIRONMENT_FAIL",
                "checks": {}, "problems": []}

    problems: List[Dict[str, Any]] = []
    exp_ff, obs_ff = first_focus(expected), first_focus(observed)

    # 1. ordering: pairwise first-focus order must agree
    ordering_ok = True
    ids = sorted(set(exp_ff) | set(obs_ff))
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if a in exp_ff and b in exp_ff and a in obs_ff and b in obs_ff:
                if (exp_ff[a] < exp_ff[b]) != (obs_ff[a] < obs_ff[b]):
                    ordering_ok = False
                    problems.append({"kind": "ordering_mismatch", "detail": (a, b)})

    # align by time
    exp_by_t = {s["t"]: s for s in expected}
    obs_by_t = {s["t"]: s for s in observed}

    # 2. focus transition: the sequence of focal sets must match
    focus_ok = True
    for t, es in exp_by_t.items():
        os_ = obs_by_t.get(t)
        if os_ is None:
            focus_ok = False
            problems.append({"kind": "missing_step", "detail": t})
        elif es["focus"] != os_["focus"]:
            focus_ok = False
            problems.append({"kind": "focus_transition_mismatch", "detail": t})

    # 3. state transition: visibility change points must match
    state_ok = True
    for t, es in exp_by_t.items():
        os_ = obs_by_t.get(t)
        if os_ is None:
            state_ok = False
        elif es["visible"] != os_["visible"]:
            state_ok = False
            problems.append({"kind": "state_transition_mismatch", "detail": t})

    # 4. relation lifecycle: edges present at each step must match
    lifecycle_ok = True
    for t, es in exp_by_t.items():
        os_ = obs_by_t.get(t)
        if os_ is None:
            lifecycle_ok = False
        elif es["edges"] != os_["edges"]:
            lifecycle_ok = False
            problems.append({"kind": "relation_lifecycle_mismatch", "detail": t})

    checks = {
        "ordering": ordering_ok,
        "focus_transition": focus_ok,
        "state_transition": state_ok,
        "relation_lifecycle": lifecycle_ok,
        "camera_transition": None,  # not covered by the world-state yet (§21-§22)
    }
    ok = all(v for k, v in checks.items() if v is not None)
    return {
        "status": "TIMELINE_OK" if ok else "TIMELINE_FAIL",
        "failure_class": "PASS" if ok else "RENDER_FAIL",
        "steps": len(observed),
        "checks": checks,
        "problems": problems,
        "first_focus_expected": exp_ff,
        "first_focus_observed": obs_ff,
    }
