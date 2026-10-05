"""Failure-taxonomy fault domains — Directive v5 §40-§44, §60.

Phase 0 had Spec/Runtime/Double faults. v5 adds three more domains, and each
must land on its OWN verdict so blame is never misattributed:

  Renderer fault    -> RENDER_FAIL      (renderer drew it wrong)
  Observer fault    -> OBSERVATION_FAIL (observer dropped what was emitted)
  Environment fault -> ENVIRONMENT_FAIL (browser could not observe at all)

The last two are the subtle ones: a broken observer must NOT be blamed on the
runtime, and a dead browser must NOT be blamed on the renderer.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from observer import fidelity, projection, taxonomy  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _anchor(case="cause_effect"):
    import json
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


def _faithful_observation(ws):
    geo = projection.expected_layout(ws)
    rf = ws.frames[-1]
    nodes = []
    for oid in sorted(geo):
        obj = rf.objects.get(oid)
        nodes.append({
            "id": oid, "x": geo[oid]["x"], "y": geo[oid]["y"],
            "w": geo[oid]["w"], "h": geo[oid]["h"], "opacity": 1,
            "visibility": "visible" if (obj is None or obj.visible) else "hidden",
            "display": "block", "focus": bool(obj and obj.focus),
        })
    edges = [{"source": r.source, "target": r.target, "type": r.type,
              "phase": r.phase} for r in rf.relations]
    return {"available": True, "backend": "synthetic", "nodes": nodes, "edges": edges}


# --- Renderer fault (§41) ---------------------------------------------------

def test_renderer_fault_is_render_fail():
    ws = compiler.compile_world_state(_anchor())
    obs = _faithful_observation(ws)
    for n in obs["nodes"]:
        n["x"] += 40
    rep = fidelity.compare(ws, obs)
    assert rep["status"] == "FIDELITY_FAIL"
    assert rep["failure_class"] == taxonomy.RENDER_FAIL
    assert rep["fault_domain"] == "renderer"


# --- Observer fault (§42) ---------------------------------------------------

def test_observer_drop_is_observation_fail_not_runtime():
    """The renderer emitted node B, but the observer dropped it from its report."""
    ws = compiler.compile_world_state(_anchor())
    obs = _faithful_observation(ws)
    # an independent record of what the renderer actually emitted
    emitted = {n["id"] for n in obs["nodes"]}
    victim = sorted(emitted)[0]
    obs = {**obs, "nodes": [n for n in obs["nodes"] if n["id"] != victim]}
    rep = fidelity.compare(ws, obs, emitted_ids=emitted)
    assert rep["status"] == "OBSERVATION_INVALID"
    assert rep["failure_class"] == taxonomy.OBSERVATION_FAIL
    assert rep["fault_domain"] == "observer"
    assert victim in rep["dropped_by_observer"]
    # crucially, the runtime is NOT blamed
    assert rep["failure_class"] != taxonomy.RUNTIME_FAIL


def test_missing_node_without_emitted_signal_reads_as_render_fail():
    """Absent the independent signal, a missing node looks like a render fault.

    This documents WHY the emitted-id signal exists: the two cases are
    indistinguishable from the observation alone.
    """
    ws = compiler.compile_world_state(_anchor())
    obs = _faithful_observation(ws)
    obs = {**obs, "nodes": obs["nodes"][1:]}
    rep = fidelity.compare(ws, obs)  # no emitted_ids
    assert rep["failure_class"] == taxonomy.RENDER_FAIL


# --- Environment fault (§43) ------------------------------------------------

def test_dead_browser_is_environment_fail():
    ws = compiler.compile_world_state(_anchor())
    obs = {"available": False, "backend": None, "nodes": [], "edges": []}
    rep = fidelity.compare(ws, obs)
    assert rep["status"] == "UNAVAILABLE"
    assert rep["failure_class"] == taxonomy.ENVIRONMENT_FAIL
    assert rep["fault_domain"] == "environment"


def test_browser_probe_error_is_environment_fail():
    """A browser that launched but failed to produce a probe attr -> environment."""
    ws = compiler.compile_world_state(_anchor())
    obs = {"available": True, "backend": "chromium", "nodes": [], "edges": [],
           "error": "probe attribute not found in dumped DOM"}
    rep = fidelity.compare(ws, obs)
    assert rep["failure_class"] == taxonomy.ENVIRONMENT_FAIL
    assert rep["fault_domain"] == "environment"


# --- taxonomy layer separation (§44-§45) ------------------------------------

def test_verdict_and_workflow_are_separate_layers():
    assert taxonomy.is_verdict("RUNTIME_FAIL")
    assert taxonomy.is_verdict("OBSERVATION_FAIL")
    assert not taxonomy.is_verdict("BLOCKED"), "BLOCKED is a workflow state, not a verdict"
    assert taxonomy.is_workflow_state("BLOCKED")
    assert taxonomy.is_workflow_state("ESCALATED")
    assert not taxonomy.is_workflow_state("SPEC_FAIL")


def test_every_verdict_has_a_fault_domain():
    for v in taxonomy.VERDICTS:
        assert taxonomy.fault_domain(v) in {
            "none", "spec", "runtime", "renderer",
            "observer", "environment", "pixel", "unknown"}


def test_ambiguous_escalates():
    assert taxonomy.workflow_for(taxonomy.AMBIGUOUS) == taxonomy.ESCALATED
    assert taxonomy.workflow_for(taxonomy.PASS) == taxonomy.RESOLVED
    assert taxonomy.workflow_for(taxonomy.RUNTIME_FAIL) == taxonomy.OPEN
