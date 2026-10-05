"""Temporal (ordering) dimension tests (Final Practical Closeout Directive, P2).

The Temporal layer is the World-State dimension that decides *when* an element is
allowed to be visible. Presence only sampled inside and after the alive window;
motion/camera/relation ask about shape, magnification and links. Neither noticed
the two time-ordering defects:

  * onset — an element painting before its enter cue (a spoilt reveal), and
  * precedence — a dependent entering while the dependency it names is not yet on
    screen.

These tests prove the dimension is expected independently (pure, contract-driven)
and observed on the REAL compiled player (browser-gated).
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from observer import browser, production, temporal  # noqa: E402

HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")

GOLDEN = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


# --- pure expectation --------------------------------------------------------


def test_onset_time_is_none_when_enter_is_at_beat_start():
    lc = {"enter": {"at": 0.0, "dur": 0.5}}
    assert temporal.onset_time(lc, 0.0, 10.0) is None
    # entering just inside the margin also has no observably-clear pre-roll
    assert temporal.onset_time({"enter": {"at": 0.2}}, 0.0, 10.0) is None
    # no enter cue at all -> no claim
    assert temporal.onset_time({}, 0.0, 10.0) is None


def test_onset_time_precedes_the_cue():
    lc = {"enter": {"at": 3.0, "dur": 0.5}}
    t = temporal.onset_time(lc, 0.0, 10.0)
    assert t is not None and t < 3.0
    assert t == pytest.approx(3.0 - 0.35, abs=1e-6)


def test_precedence_claims_require_a_real_lead():
    lc = {
        "a": {"enter": {"at": 0.0}},
        "b": {"enter": {"at": 2.0, "after": ["a"]}},   # lead 2.0 -> claim
        "c": {"enter": {"at": 2.1, "after": ["b"]}},   # lead 0.1 -> no claim
    }
    claims = temporal.precedence_claims(lc, 0.0, 10.0)
    pairs = {(c["dependent"], c["dep"]) for c in claims}
    assert ("b", "a") in pairs
    assert ("c", "b") not in pairs


def test_precedence_ignores_unknown_dependency():
    lc = {"b": {"enter": {"at": 2.0, "after": ["ghost"]}}}
    assert temporal.precedence_claims(lc, 0.0, 10.0) == []


def test_observable_reflects_presence_of_enter_cues():
    assert temporal.observable({}) is False
    assert temporal.observable(None) is False
    assert temporal.observable({"x": {"enter": {"at": 1.0}}}) is True
    assert temporal.observable({"x": {"exit": {"at": 1.0}}}) is False


def test_build_samples_emits_onset_and_precedence_probes():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 8.0,
                      "elements": [{"id": "a", "type": "text"},
                                   {"id": "b", "type": "text"}]}]}
    rp = {"beats": [{"beat_id": "b1", "boxes": {
        "a": {"x": 0, "y": 0, "w": 50, "h": 20}, "b": {"x": 100, "y": 0, "w": 50, "h": 20}}}]}
    en = {"beats": [{"beat_id": "b1", "lifecycle": {
        "a": {"enter": {"at": 0.0, "dur": 0.4}},
        "b": {"enter": {"at": 3.0, "dur": 0.4, "after": ["a"]}}}, "events": []}]}
    probes = production.build_samples(dsl, rp, en)
    tp = [p for p in probes if p.get("probe") == "temporal"]
    phases = {p["phase"] for p in tp}
    assert "onset" in phases and "precedence" in phases
    onset = [p for p in tp if p["phase"] == "onset"][0]
    assert onset["id"] == "b" and onset["present"] is False


def test_verify_flags_early_visible():
    probes = [{"id": "b", "beat_id": "b1", "t": 2.65, "present": False,
               "probe": "temporal", "phase": "onset"}]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "b", "beat_id": "b1", "t": 2.65, "probe": "temporal",
         "phase": "onset", "ink": 900}]}
    rep = production.verify(probes, observed)
    assert rep["verdict"] == "RENDER_FAIL"
    assert any(p["kind"] == "early_visible" for p in rep["problems"])


def test_verify_flags_precedence_violated():
    probes = [{"id": "a", "beat_id": "b1", "t": 3.2, "present": True,
               "probe": "temporal", "phase": "precedence"}]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "a", "beat_id": "b1", "t": 3.2, "probe": "temporal",
         "phase": "precedence", "ink": 0}]}
    rep = production.verify(probes, observed)
    assert any(p["kind"] == "precedence_violated" for p in rep["problems"])


def test_verify_flags_temporal_probe_missing():
    probes = [{"id": "b", "beat_id": "b1", "t": 2.65, "present": False,
               "probe": "temporal", "phase": "onset"}]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": []}
    rep = production.verify(probes, observed)
    assert any(p["kind"] == "temporal_probe_missing" for p in rep["problems"])


def test_verify_accepts_correct_temporal_and_counts_it():
    probes = [
        {"id": "b", "beat_id": "b1", "t": 2.65, "present": False,
         "probe": "temporal", "phase": "onset"},
        {"id": "a", "beat_id": "b1", "t": 3.2, "present": True,
         "probe": "temporal", "phase": "precedence"},
    ]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "b", "beat_id": "b1", "t": 2.65, "probe": "temporal", "phase": "onset", "ink": 0},
        {"id": "a", "beat_id": "b1", "t": 3.2, "probe": "temporal", "phase": "precedence", "ink": 400},
    ]}
    rep = production.verify(probes, observed)
    assert rep["temporal_checked"] == 2
    assert rep["verdict"] == "PASS", rep


# --- browser-gated: adjudicate the REAL player's Temporal layer --------------


@needs_browser
def test_real_film_temporal_layer_applied(tmp_path):
    import pipeline
    out = str(tmp_path / "out")
    pipeline.run(GOLDEN, out, render_previews=False, log=lambda *a: None)
    film = os.path.join(out, "film", "index.html")
    assert os.path.exists(film)
    report = production.run(film, os.path.join(out, "work"))
    assert report["available"] is True, report
    # the contract exercised the temporal dimension, not just presence/motion
    assert report["temporal_expected"] > 0, report
    assert report["temporal_checked"] == report["temporal_expected"], report
    assert report["verdict"] == "PASS", json.dumps(report, ensure_ascii=False)
