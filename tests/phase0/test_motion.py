"""Transform (Motion) dimension tests (Final Practical Closeout Directive, P2).

The Motion layer is the next World-State dimension after identity/visibility/
focus/relation/temporal: it drives *where an element is and how big it is over
time*. These tests prove the dimension is:
  * expected independently (pure, contract-driven expectation), and
  * observed on the REAL compiled player (browser-gated) and adjudicated
    directionally.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from observer import browser, motion, production  # noqa: E402

HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")

GOLDEN = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


# --- pure expectation -------------------------------------------------------


def test_ease_is_clamped_smoothstep():
    assert motion.ease(-1.0) == 0.0
    assert motion.ease(0.0) == 0.0
    assert motion.ease(1.0) == 1.0
    assert motion.ease(2.0) == 1.0
    assert abs(motion.ease(0.5) - 0.5) < 1e-9
    # strictly increasing on the open interval
    assert motion.ease(0.3) < motion.ease(0.6)


def test_rise_displaces_then_settles():
    lc = {"enter": {"at": 1.0, "dur": 1.0, "motion": "rise"}}
    early = motion.expected_transform(lc, 1.1)
    settle = motion.expected_transform(lc, 2.2)
    assert early["dy"] > 0.0
    assert settle["dy"] == 0.0
    assert settle["scale"] == 1.0


def test_pop_grows_from_min_to_one():
    lc = {"enter": {"at": 0.0, "dur": 1.0, "motion": "pop"}}
    early = motion.expected_transform(lc, 0.2)
    settle = motion.expected_transform(lc, 1.2)
    assert early["scale"] < settle["scale"]
    assert settle["scale"] == pytest.approx(1.0)
    assert early["scale"] >= 0.55


def test_exit_sink_and_shrink_apply_after_exit():
    lc = {"enter": {"at": 0.0, "dur": 0.5, "motion": "fade"},
          "exit": {"at": 2.0, "dur": 1.0, "motion": "sink"}}
    before = motion.expected_transform(lc, 1.5)
    after = motion.expected_transform(lc, 2.5)
    assert after["dy"] > before["dy"]

    lc2 = {"enter": {"at": 0.0, "dur": 0.5, "motion": "fade"},
           "exit": {"at": 2.0, "dur": 1.0, "motion": "shrink"}}
    assert motion.expected_transform(lc2, 2.5)["scale"] < \
        motion.expected_transform(lc2, 1.5)["scale"]


def test_inherit_is_identity():
    lc = {"enter": {"at": 0.0, "dur": 1.0, "motion": "inherit"}}
    assert motion.expected_transform(lc, 0.0) == {"dy": 0.0, "scale": 1.0, "alpha": 1.0}
    assert motion.expected_transform(lc, 5.0)["dy"] == 0.0


def test_transform_element_detects_geometry_motion():
    assert motion.transform_element({"enter": {"motion": "rise"}}) == "rise"
    assert motion.transform_element({"enter": {"motion": "fade"},
                                     "exit": {"motion": "shrink"}}) == "shrink"
    assert motion.transform_element({"enter": {"motion": "fade"}}) is None


def test_build_samples_emits_transform_probes_only_for_geometry_motions():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 4.0,
                      "elements": [{"id": "r1", "type": "text"},
                                   {"id": "f1", "type": "text"}]}]}
    rp = {"beats": [{"beat_id": "b1", "boxes": {
        "r1": {"x": 10, "y": 10, "w": 100, "h": 40},
        "f1": {"x": 10, "y": 60, "w": 100, "h": 40}}}]}
    en = {"beats": [{"beat_id": "b1", "lifecycle": {
        "r1": {"enter": {"at": 0.0, "dur": 0.6, "motion": "rise"}},
        "f1": {"enter": {"at": 0.0, "dur": 0.6, "motion": "fade"}}}}]}
    probes = production.build_samples(dsl, rp, en)
    t_ids = {p["id"] for p in probes if p.get("probe") == "transform"}
    assert t_ids == {"r1"}
    phases = {p["phase"] for p in probes if p.get("probe") == "transform" and p["id"] == "r1"}
    assert "settle" in phases and "early" in phases


def test_verify_flags_motion_not_applied():
    probes = [
        {"id": "r1", "beat_id": "b1", "t": 0.8, "present": True, "kind": "must",
         "box": {"x": 0, "y": 0, "w": 100, "h": 40}, "probe": "transform",
         "phase": "settle", "exp": {"dy": 0.0, "scale": 1.0, "alpha": 1.0}},
        {"id": "r1", "beat_id": "b1", "t": 0.1, "present": True, "kind": "must",
         "box": {"x": 0, "y": 0, "w": 100, "h": 40}, "probe": "transform",
         "phase": "early", "motion": "rise", "exp": {"dy": 20.0, "scale": 1.0, "alpha": 0.2}},
    ]
    # observed: early frame is at the SAME place as settled -> motion missing
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "r1", "t": 0.8, "present": True, "probe": "transform", "phase": "settle",
         "ink": 0, "gink": 500, "gbbox": {"x": 0, "y": 0, "w": 100, "h": 40}},
        {"id": "r1", "t": 0.1, "present": True, "probe": "transform", "phase": "early",
         "ink": 0, "gink": 500, "gbbox": {"x": 0, "y": 0, "w": 100, "h": 40}},
    ]}
    rep = production.verify(probes, observed)
    assert rep["verdict"] == "RENDER_FAIL"
    assert any(p["kind"] == "motion_not_applied" for p in rep["problems"])


def test_verify_accepts_correct_rise_and_pop():
    probes = [
        {"id": "r1", "beat_id": "b1", "t": 0.8, "present": True, "kind": "must",
         "box": {"x": 0, "y": 0, "w": 100, "h": 40}, "probe": "transform",
         "phase": "settle", "exp": {"dy": 0.0, "scale": 1.0, "alpha": 1.0}},
        {"id": "r1", "beat_id": "b1", "t": 0.1, "present": True, "kind": "must",
         "box": {"x": 0, "y": 0, "w": 100, "h": 40}, "probe": "transform",
         "phase": "early", "motion": "rise", "exp": {"dy": 20.0, "scale": 1.0, "alpha": 0.2}},
    ]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "r1", "t": 0.8, "present": True, "probe": "transform", "phase": "settle",
         "ink": 0, "gink": 500, "gbbox": {"x": 0, "y": 100, "w": 100, "h": 40}},
        {"id": "r1", "t": 0.1, "present": True, "probe": "transform", "phase": "early",
         "ink": 0, "gink": 500, "gbbox": {"x": 0, "y": 120, "w": 100, "h": 40}},
    ]}
    rep = production.verify(probes, observed)
    assert rep["transform_checked"] == 1
    assert not any(p["kind"] == "motion_not_applied" for p in rep["problems"])


# --- browser-gated: adjudicate the REAL player's Motion layer ----------------


@needs_browser
def test_real_film_motion_layer_applied(tmp_path):
    import pipeline
    out = str(tmp_path / "out")
    pipeline.run(GOLDEN, out, render_previews=False, log=lambda *a: None)
    film = os.path.join(out, "film", "index.html")
    assert os.path.exists(film)
    report = production.run(film, os.path.join(out, "work"))
    assert report["available"] is True, report
    # the contract exercised the motion dimension, not just presence
    assert report["transform_checked"] > 0, report
    assert report["verdict"] == "PASS", json.dumps(report, ensure_ascii=False)
