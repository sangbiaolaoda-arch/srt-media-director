"""Camera (viewport) dimension tests (Final Practical Closeout Directive, P2).

The Camera layer is the World-State dimension after transform/motion: it does not
move one element, it *magnifies the whole composited beat* so the eye settles on
the beat's core. These tests prove the dimension is:

  * expected independently (pure, contract-driven expectation), and
  * observed on the REAL compiled player (browser-gated) and adjudicated — the
    composite magnification must match the independent Camera projection, and a
    ``push_in`` must never run in reverse.

The expectation never reads the player's embedded ``BEATS``.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from observer import browser, camera, production  # noqa: E402

HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")

GOLDEN = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


# --- pure expectation --------------------------------------------------------


def test_static_camera_is_identity_everywhere():
    cam = {"mode": "static"}
    assert camera.expected_zoom(cam, 0.0, 10.0, 0.0) == 1.0
    assert camera.expected_zoom(cam, 0.0, 10.0, 5.0) == 1.0
    assert camera.expected_zoom(cam, 0.0, 10.0, 9.9) == 1.0
    assert camera.is_identity(cam) is True


def test_push_in_starts_at_one_and_ramps_to_amplitude():
    cam = {"mode": "push_in"}
    start, end = 0.0, 10.0
    # ramp begins only after 45% of the beat; before that it is still 1.0
    assert camera.expected_zoom(cam, start, end, 1.0) == 1.0
    assert camera.expected_zoom(cam, start, end, 4.4) == 1.0
    # strictly increasing across the ramp window (45%..80%)
    z_mid = camera.expected_zoom(cam, start, end, 6.0)
    z_late = camera.expected_zoom(cam, start, end, 8.0)
    assert 1.0 < z_mid < z_late
    # settles at 1 + amplitude
    assert z_late == pytest.approx(1.06, abs=1e-9)
    assert camera.expected_zoom(cam, start, end, 10.0) == pytest.approx(1.06, abs=1e-9)
    assert camera.is_identity(cam) is False


def test_unknown_mode_has_no_formable_expectation():
    assert camera.observable({"mode": "orbit"}) is False
    assert camera.observable(None) is True           # absent == static == known
    assert camera.observable({"mode": "static"}) is True
    assert camera.observable({"mode": "push_in"}) is True
    # an unknown mode claims no magnification (honest default, never a false zoom)
    assert camera.expected_zoom({"mode": "orbit"}, 0.0, 10.0, 9.9) == 1.0


def test_zoom_series_follows_the_upstream_plan():
    beats = [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 10.0,
              "camera": {"mode": "static"}},
             {"beat_id": "b2", "start_sec": 10.0, "end_sec": 20.0,
              "camera": {"mode": "push_in"}}]
    assert camera.zoom_series(beats, 3.0) == 1.0
    assert camera.zoom_series(beats, 18.0) > 1.0


def test_build_samples_emits_camera_probes_for_known_modes():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 10.0,
                      "camera": {"mode": "push_in"},
                      "elements": [{"id": "t1", "type": "text"}]}]}
    rp = {"beats": [{"beat_id": "b1", "boxes": {"t1": {"x": 10, "y": 10, "w": 100, "h": 40}}}]}
    en = {"beats": [{"beat_id": "b1", "lifecycle": {"t1": {"enter": {"at": 0.0, "dur": 0.5}}}}]}
    probes = production.build_samples(dsl, rp, en)
    cam = [p for p in probes if p.get("probe") == "camera"]
    assert {p["phase"] for p in cam} == {"early", "late"}
    late = [p for p in cam if p["phase"] == "late"][0]
    assert late["exp"]["zoom"] > 1.0


def test_verify_flags_camera_zoom_mismatch():
    """A static beat that the renderer magnified is a real RENDER_FAIL."""
    probes = [
        {"id": "b1", "beat_id": "b1", "t": 0.5, "present": True, "probe": "camera",
         "phase": "early", "exp": {"zoom": 1.0}},
        {"id": "b1", "beat_id": "b1", "t": 9.85, "present": True, "probe": "camera",
         "phase": "late", "exp": {"zoom": 1.0}},
    ]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "b1", "beat_id": "b1", "t": 0.5, "probe": "camera", "phase": "early",
         "zw": 1.10, "zh": 1.10},
        {"id": "b1", "beat_id": "b1", "t": 9.85, "probe": "camera", "phase": "late",
         "zw": 1.10, "zh": 1.10},
    ]}
    rep = production.verify(probes, observed)
    assert rep["verdict"] == "RENDER_FAIL"
    assert any(p["kind"] == "camera_zoom_mismatch" for p in rep["problems"])


def test_verify_accepts_correct_push_in_and_counts_it():
    probes = [
        {"id": "b2", "beat_id": "b2", "t": 0.5, "present": True, "probe": "camera",
         "phase": "early", "exp": {"zoom": 1.0}},
        {"id": "b2", "beat_id": "b2", "t": 9.85, "present": True, "probe": "camera",
         "phase": "late", "exp": {"zoom": 1.06}},
    ]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "b2", "beat_id": "b2", "t": 0.5, "probe": "camera", "phase": "early",
         "zw": 1.0, "zh": 1.0},
        {"id": "b2", "beat_id": "b2", "t": 9.85, "probe": "camera", "phase": "late",
         "zw": 1.06, "zh": 1.06},
    ]}
    rep = production.verify(probes, observed)
    assert rep["camera_checked"] == 1
    assert not any(p["kind"] == "camera_zoom_mismatch" for p in rep["problems"])
    assert not any(p["kind"] == "camera_reversed" for p in rep["problems"])


def test_verify_flags_reversed_camera():
    """A push_in measured shrinking over the beat is a RENDER_FAIL."""
    probes = [
        {"id": "b3", "beat_id": "b3", "t": 0.5, "present": True, "probe": "camera",
         "phase": "early", "exp": {"zoom": 1.0}},
        {"id": "b3", "beat_id": "b3", "t": 9.85, "present": True, "probe": "camera",
         "phase": "late", "exp": {"zoom": 1.06}},
    ]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "b3", "beat_id": "b3", "t": 0.5, "probe": "camera", "phase": "early",
         "zw": 1.06, "zh": 1.06},
        {"id": "b3", "beat_id": "b3", "t": 9.85, "probe": "camera", "phase": "late",
         "zw": 1.02, "zh": 1.02},
    ]}
    rep = production.verify(probes, observed)
    assert any(p["kind"] == "camera_reversed" for p in rep["problems"])


def test_verify_flags_camera_probe_missing():
    probes = [
        {"id": "b1", "beat_id": "b1", "t": 0.5, "present": True, "probe": "camera",
         "phase": "early", "exp": {"zoom": 1.0}},
        {"id": "b1", "beat_id": "b1", "t": 9.85, "present": True, "probe": "camera",
         "phase": "late", "exp": {"zoom": 1.0}},
    ]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": []}
    rep = production.verify(probes, observed)
    assert any(p["kind"] == "camera_probe_missing" for p in rep["problems"])


# --- browser-gated: adjudicate the REAL player's Camera layer ----------------


@needs_browser
def test_real_film_camera_layer_applied(tmp_path):
    import pipeline
    out = str(tmp_path / "out")
    pipeline.run(GOLDEN, out, render_previews=False, log=lambda *a: None)
    film = os.path.join(out, "film", "index.html")
    assert os.path.exists(film)
    report = production.run(film, os.path.join(out, "work"))
    assert report["available"] is True, report
    # the contract exercised the camera dimension, not just presence/motion
    assert report["camera_checked"] > 0, report
    assert report["verdict"] == "PASS", json.dumps(report, ensure_ascii=False)
