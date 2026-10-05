"""Phase 0 step 7 — Browser Observer tests.

Two tiers:

  * always-run (no browser): normalization determinism, honest degradation,
    fidelity classification on synthetic observations.
  * browser-gated (skipped when no Chromium is launchable): real observation
    determinism, and the full loop Runtime -> HTML -> observe -> WorldState ->
    same validator.
"""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler, validator  # noqa: E402
from entailment import load_contract  # noqa: E402
from observer import browser, fidelity, normalize, render  # noqa: E402

CASES = os.path.join(ROOT, "cases")
HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")


def _anchor(case="cause_effect"):
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


# --- always-run -------------------------------------------------------------


def test_honest_degradation_when_no_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(browser, "find_browser", lambda: None)
    p = tmp_path / "x.html"
    p.write_text("<html><body></body></html>", encoding="utf-8")
    obs = browser.observe(str(p))
    assert obs["available"] is False
    assert obs["nodes"] == [] and obs["edges"] == []
    # fidelity must not fabricate a pass
    ws = compiler.compile_world_state(_anchor())
    rep = fidelity.compare(ws, obs)
    assert rep["status"] == "UNAVAILABLE" and rep["available"] is False


def test_normalization_deterministic_and_order_independent():
    obs = {"available": True, "backend": "x",
           "nodes": [{"id": "b", "x": 1.2, "y": 0.3, "w": 10.0, "h": 5.0,
                      "opacity": 1, "visibility": "visible", "display": "block",
                      "focus": False},
                     {"id": "a", "x": 0.4, "y": 0.0, "w": 8.0, "h": 4.0,
                      "opacity": 1, "visibility": "visible", "display": "block",
                      "focus": True}],
           "edges": [{"source": "a", "target": "b", "type": "causes", "phase": "active"}]}
    shuffled = copy.deepcopy(obs)
    shuffled["nodes"] = list(reversed(shuffled["nodes"]))
    assert normalize.normalized_hash(obs) == normalize.normalized_hash(shuffled)


def test_fidelity_ok_on_matching_synthetic():
    ws = compiler.compile_world_state(_anchor())
    ff = ws.frames[-1]
    nodes = []
    for i, (oid, o) in enumerate(sorted(ff.objects.items())):
        nodes.append({"id": oid, "x": 60 + i * 220, "y": 140, "w": 180, "h": 80,
                      "opacity": 1, "visibility": "visible", "display": "block",
                      "focus": o.focus})
    edges = [{"source": r.source, "target": r.target, "type": r.type,
              "phase": r.phase} for r in ff.relations]
    rep = fidelity.compare(ws, {"available": True, "backend": "x", "nodes": nodes, "edges": edges})
    assert rep["status"] == "FIDELITY_OK", rep


def test_fidelity_fail_on_missing_node():
    ws = compiler.compile_world_state(_anchor())
    rep = fidelity.compare(ws, {"available": True, "backend": "x", "nodes": [],
                                "edges": []})
    assert rep["status"] == "FIDELITY_FAIL"


def test_fidelity_fail_on_focus_lost():
    ws = compiler.compile_world_state(_anchor())
    ff = ws.frames[-1]
    nodes = [{"id": oid, "x": 10, "y": 10, "w": 180, "h": 80, "opacity": 1,
              "visibility": "visible", "display": "block", "focus": False}
             for oid in ff.objects]
    rep = fidelity.compare(ws, {"available": True, "backend": "x", "nodes": nodes,
                                "edges": []})
    assert rep["status"] == "FIDELITY_FAIL"
    assert any(p["kind"] == "focus_lost" for p in rep["problems"])


# --- browser-gated ----------------------------------------------------------


@needs_browser
def test_real_observation_is_deterministic(tmp_path):
    ws = compiler.compile_world_state(_anchor())
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    o1 = browser.observe(html)
    o2 = browser.observe(html)
    assert o1["available"] and o1["nodes"], o1
    assert normalize.normalized_hash(o1) == normalize.normalized_hash(o2)


@needs_browser
def test_full_loop_runtime_render_observe_validate(tmp_path):
    case = "cause_effect"
    anchor = _anchor(case)
    contract = load_contract("causes.v1")
    ws = compiler.compile_world_state(anchor, contract=contract)

    # final-frame fidelity
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    obs = browser.observe(html)
    rep = fidelity.compare(ws, obs)
    assert rep["status"] == "FIDELITY_OK", rep

    # replay the whole timeline -> observed reality -> shared WorldState
    observations, available = browser.observe_timeline(ws, str(tmp_path / "frames"))
    assert available and observations
    obs_ws = normalize.to_world_state_timeline(observations, case)

    with open(os.path.join(CASES, case, "expected_semantic.json"), encoding="utf-8") as f:
        exp_sem = json.load(f)
    with open(os.path.join(CASES, case, "expected_staging.json"), encoding="utf-8") as f:
        exp_sta = json.load(f)
    r = validator.validate(anchor, contract, exp_sem, exp_sta, obs_ws)
    assert r["verdict"] == "PASS", r


@needs_browser
def test_observed_timeline_recovers_precedence(tmp_path):
    """The replayed observation must recover cause-before-effect ordering."""
    anchor = _anchor("cause_effect")
    contract = load_contract("causes.v1")
    ws = compiler.compile_world_state(anchor, contract=contract)
    observations, available = browser.observe_timeline(ws, str(tmp_path / "frames"))
    assert available
    obs_ws = normalize.to_world_state_timeline(observations, "cause_effect")
    facts = obs_ws.facts()
    assert facts["first_focus"]["pressure"] < facts["first_focus"]["stability_failure"]
    assert facts["last_focus"] == "stability_failure"
    assert ("pressure", "stability_failure", "causes") in facts["relation_dirs"]


@needs_browser
def test_observed_geometry_matches_declared_layout(tmp_path):
    ws = compiler.compile_world_state(_anchor())
    order = sorted(ws.frames[-1].objects.keys(),
                   key=lambda k: (min(f.t for f in ws.frames if f.objects[k].focus), k))
    expected = render.layout_geometry(order)
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    obs = browser.observe(html)
    got = {n["id"]: n for n in obs["nodes"]}
    for oid, geo in expected.items():
        # browser adds the 2px border via box-sizing:border-box -> left/top match
        assert abs(got[oid]["x"] - geo["x"]) <= 1.0, (oid, got[oid], geo)
        assert abs(got[oid]["w"] - geo["w"]) <= 1.0, (oid, got[oid], geo)
