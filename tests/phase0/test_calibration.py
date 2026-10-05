"""Phase 0 step 8 — Render Fidelity threshold calibration tests.

Pure derivation is browser-free. The real calibration is browser-gated.
"""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from entailment import load_contract  # noqa: E402
from observer import browser, calibrate, fidelity, render, thresholds  # noqa: E402

CASES = os.path.join(ROOT, "cases")
HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no functional browser")


def _anchor(case="cause_effect"):
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


def _layout():
    ws = compiler.compile_world_state(_anchor())
    return ws, render.layout_geometry(render.stable_order(ws))


# --- pure derivation (no browser) ------------------------------------------


def _synthetic_obs(layout, dx=0.0, dy=0.0):
    nodes = []
    for oid, g in layout.items():
        nodes.append({"id": oid, "x": g["x"] + dx, "y": g["y"] + dy,
                      "w": g["w"], "h": g["h"], "opacity": 1,
                      "visibility": "visible", "display": "block", "focus": False})
    return {"available": True, "backend": "x", "nodes": nodes, "edges": []}


def test_derive_zero_delta_gives_min_tolerance():
    ws, layout = _layout()
    obs = [_synthetic_obs(layout) for _ in range(50)]
    thr = calibrate.derive(layout, obs, 50)
    assert thr["source"] == "calibrated" and thr["n"] == 50
    assert thr["p99_geometry_delta_px"] == 0.0
    assert thr["geometry_tol_px"] >= 1.0  # never below the conservative floor
    assert thr["visibility_stable"] is True


def test_derive_tracks_measured_jitter():
    ws, layout = _layout()
    obs = []
    for i in range(100):
        # inject a small per-node x jitter
        dx = 0.0 if i < 99 else 7.0
        obs.append(_synthetic_obs(layout, dx=dx))
    thr = calibrate.derive(layout, obs, 100)
    assert thr["max_geometry_delta_px"] == 7.0
    # p99 with one 7px outlier out of 100 nodes*[2 nodes] stays below max
    assert thr["geometry_tol_px"] >= 1.0
    assert thr["geometry_tol_px"] <= 7.5 + 0.001


def test_derive_flags_missing_node():
    ws, layout = _layout()
    bad = _synthetic_obs(layout)
    bad["nodes"] = bad["nodes"][:-1]  # drop one node
    thr = calibrate.derive(layout, [bad], 1)
    assert thr["missing_nodes"] == 1
    assert thr["visibility_stable"] is False


def test_defaults_and_effective():
    d = thresholds.default()
    assert d["source"] == "default" and d["geometry_tol_px"] == 1.0
    # effective falls back to defaults when no artifact exists at a temp path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "nope.json")
        assert thresholds.effective(missing)["source"] == "default"


def test_committed_calibration_artifact_is_wellformed():
    """If a calibration artifact is committed, it must be self-describing."""
    art = thresholds.load_calibrated()
    if art is None:
        pytest.skip("no calibrated artifact committed")
    assert art["source"] == "calibrated"
    assert isinstance(art["n"], int) and art["n"] > 0
    assert art["geometry_tol_px"] >= 1.0


def test_fidelity_uses_thresholds(monkeypatch):
    ws, layout = _layout()
    obs = _synthetic_obs(layout, dx=50.0)  # way outside tolerance
    rep = fidelity.compare(ws, obs, {"source": "default", "n": 0,
                                     "geometry_tol_px": 1.0,
                                     "area_min_px2": 1.0, "opacity_min": 0.01})
    assert any(p["kind"] == "geometry_out_of_tolerance" for p in rep["problems"])


# --- browser-gated real calibration ----------------------------------------


@needs_browser
def test_real_calibration_is_consistent(tmp_path):
    ws = compiler.compile_world_state(_anchor())
    t1 = calibrate.calibrate_from_world_state(ws, str(tmp_path / "a"), reps=20)
    t2 = calibrate.calibrate_from_world_state(ws, str(tmp_path / "b"), reps=20)
    # browser is deterministic for static content -> identical thresholds
    assert t1["geometry_tol_px"] == t2["geometry_tol_px"]
    assert t1["p99_geometry_delta_px"] == t2["p99_geometry_delta_px"]
    assert t1["visibility_stable"] and t1["edge_stable"]


@needs_browser
def test_real_fidelity_ok_with_calibrated_thresholds(tmp_path):
    case = "cause_effect"
    anchor = _anchor(case)
    contract = load_contract("causes.v1")
    ws = compiler.compile_world_state(anchor, contract=contract)
    thr = calibrate.calibrate_from_world_state(ws, str(tmp_path / "c"), reps=15)
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    rep = fidelity.compare(ws, browser.observe(html), thr)
    assert rep["status"] == "FIDELITY_OK", rep
