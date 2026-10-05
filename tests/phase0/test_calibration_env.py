"""Calibration auditability tests (Final Practical Closeout Directive, P0).

A calibrated threshold is ground truth only for the environment it was measured
in. These tests prove the calibration artifact records that environment and its
hash, and that the derivation stays deterministic.

The heavy part — a real N>=1000 browser run — lives in the scheduled
``calibration`` workflow; here we exercise the pure derivation and a small
browser-gated smoke run.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from observer import browser, calibrate  # noqa: E402

HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")

ANCHOR = os.path.join(ROOT, "cases", "cause_effect", "anchor.json")


def test_environment_fingerprint_has_stable_hash():
    env1 = calibrate.environment_fingerprint()
    env2 = calibrate.environment_fingerprint()
    assert env1["environment_hash"] and env1["environment_hash"] == env2["environment_hash"]
    assert env1["python"] and env1["platform"]


def test_environment_hash_changes_with_inputs():
    a = calibrate.environment_fingerprint(extra={"note": "a"})
    b = calibrate.environment_fingerprint(extra={"note": "b"})
    assert a["environment_hash"] != b["environment_hash"]


def test_derive_records_environment_and_is_deterministic():
    layout = {"n1": {"x": 10.0, "y": 20.0, "w": 100.0, "h": 40.0},
              "n2": {"x": 50.0, "y": 60.0, "w": 80.0, "h": 30.0}}
    obs = [{"nodes": [{"id": "n1", "x": 10.0, "y": 20.0, "w": 100.0, "h": 40.0,
                       "visibility": "visible", "display": "block", "opacity": 1},
                      {"id": "n2", "x": 51.0, "y": 60.0, "w": 80.0, "h": 30.0,
                       "visibility": "visible", "display": "block", "opacity": 1}],
            "edges": []}]
    env = calibrate.environment_fingerprint()
    d1 = calibrate.derive(layout, obs, reps=1, environment=env)
    d2 = calibrate.derive(layout, obs, reps=1, environment=env)
    assert d1 == d2
    assert d1["source"] == "calibrated" and d1["n"] == 1
    assert d1["environment_hash"] == env["environment_hash"]
    assert d1["max_geometry_delta_px"] >= 1.0  # the 1px n2 shift must be visible


def test_derive_without_environment_has_no_hash():
    d = calibrate.derive({}, [], reps=0)
    assert "environment_hash" not in d


@needs_browser
def test_small_calibration_smoke_records_env(tmp_path):
    from world_state import compiler
    with open(ANCHOR, encoding="utf-8") as f:
        anchor = json.load(f)
    ws = compiler.compile_world_state(anchor)
    thr = calibrate.calibrate_from_world_state(ws, str(tmp_path), reps=3)
    assert thr["n"] == 3
    assert thr["environment_hash"]
    assert thr["environment"]["cjk_fonts_present"] in (True, False, None)
