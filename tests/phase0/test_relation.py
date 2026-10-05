"""Relation (semantic) dimension tests (Final Practical Closeout Directive, P2).

The Relation layer is the World-State dimension that makes a director's declared
link (``visual-dsl`` -> ``beat.relations``, ``{from, to, type}``) *legible*.
Neither presence ("did ink appear?"), motion ("did the element arrive?") nor
camera ("was the frame magnified?") noticed whether a declared relationship is
actually drawn as a link. These tests prove the dimension is:

  * expected independently (pure, contract-driven expectation), and
  * observed on the REAL compiled player (browser-gated) and adjudicated —
    a declared bridge must carry ink in the corridor between its endpoints, and a
    bound label must stay centred on its target.

The expectation never reads the player's embedded ``BEATS``.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from observer import browser, production, relation  # noqa: E402

HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")

GOLDEN = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


# --- pure expectation --------------------------------------------------------

_L = {"x": 100.0, "y": 200.0, "w": 100.0, "h": 60.0}   # centre (150, 230)
_R = {"x": 400.0, "y": 200.0, "w": 100.0, "h": 60.0}   # centre (450, 230)


def test_known_relation_types_are_observable():
    assert relation.observable("flow_to") is True
    assert relation.observable("causes") is True
    assert relation.observable("bound_to") is True
    assert relation.observable("telekinesis") is False
    assert relation.observable(None) is False


def test_bridge_corridor_spans_between_facing_edges():
    exp = relation.bridge_expectation(_L, _R)
    assert exp is not None
    # left box's right edge = 200; right box's left edge = 400
    assert exp["x0"] < 200.0 < exp["x1"]
    assert exp["x0"] < 400.0 < exp["x1"]
    assert exp["y0"] <= 230.0 <= exp["y1"]
    assert exp["span"] == pytest.approx(200.0)


def test_bridge_corridor_is_none_when_boxes_overlap_horizontally():
    a = {"x": 100.0, "y": 0.0, "w": 300.0, "h": 50.0}   # right edge 400
    b = {"x": 300.0, "y": 0.0, "w": 300.0, "h": 50.0}   # left edge 300 (inside a)
    assert relation.bridge_expectation(a, b) is None


def test_find_bridge_locates_the_connector_in_the_corridor():
    exp = relation.bridge_expectation(_L, _R)
    elements = [{"id": "dec", "type": "decor"}, {"id": "br", "type": "connector"}]
    boxes = {"dec": {"x": 0, "y": 0, "w": 10, "h": 10},
             "br": {"x": 210.0, "y": 220.0, "w": 180.0, "h": 20.0}}  # centre (300,230)
    assert relation.find_bridge(elements, boxes, exp) == "br"
    # a connector far outside the corridor is not accepted
    boxes2 = dict(boxes, br={"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0})
    assert relation.find_bridge(elements, boxes2, exp) is None


def test_align_expectation_tracks_the_target_centre():
    exp = relation.align_expectation(_L, _R)
    assert exp["target_cx"] == pytest.approx(450.0)
    assert exp["align_px"] > 0


def test_point_to_box_distance():
    box = {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}
    assert relation.point_to_box_dist(5.0, 5.0, box) == 0.0
    assert relation.point_to_box_dist(13.0, 5.0, box) == pytest.approx(3.0)


def test_build_samples_emits_relation_probes():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 6.0,
                      "elements": [{"id": "h1", "type": "motif"},
                                   {"id": "h2", "type": "motif"},
                                   {"id": "br", "type": "connector"}],
                      "relations": [{"from": "h1", "to": "h2", "type": "flow_to"}]}]}
    rp = {"beats": [{"beat_id": "b1", "boxes": {
        "h1": {"x": 100.0, "y": 200.0, "w": 100.0, "h": 60.0},
        "h2": {"x": 400.0, "y": 200.0, "w": 100.0, "h": 60.0},
        "br": {"x": 210.0, "y": 220.0, "w": 180.0, "h": 20.0}}}]}
    en = {"beats": [{"beat_id": "b1", "lifecycle": {
        "h1": {"enter": {"at": 0.0, "dur": 0.4}},
        "h2": {"enter": {"at": 0.0, "dur": 0.4}},
        "br": {"enter": {"at": 0.2, "dur": 0.4}}}, "events": []}]}
    probes = production.build_samples(dsl, rp, en)
    relp = [p for p in probes if p.get("probe") == "relation"]
    assert len(relp) == 1
    assert relp[0]["id"] == "br"
    assert relp[0]["rel"]["channel"] == "bridge_corridor"
    assert "box" in relp[0]


def test_verify_flags_unrendered_relation():
    probes = [{"id": "br", "beat_id": "b1", "t": 3.6, "present": True,
               "probe": "relation",
               "rel": {"type": "flow_to", "from": "h1", "to": "h2",
                       "channel": "bridge_corridor",
                       "corridor": {"x0": 190.0, "x1": 410.0, "y0": 200.0,
                                    "y1": 260.0, "min_w": 110}}}]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "br", "beat_id": "b1", "t": 3.6, "probe": "relation",
         "gink": 0, "gbbox": None}]}
    rep = production.verify(probes, observed)
    assert rep["verdict"] == "RENDER_FAIL"
    assert any(p["kind"] == "relation_unrendered" for p in rep["problems"])


def test_verify_flags_detached_bridge():
    probes = [{"id": "br", "beat_id": "b1", "t": 3.6, "present": True,
               "probe": "relation",
               "rel": {"type": "flow_to", "from": "h1", "to": "h2",
                       "channel": "bridge_corridor",
                       "corridor": {"x0": 190.0, "x1": 410.0, "y0": 200.0,
                                    "y1": 260.0, "min_w": 110}}}]
    # ink present but centred far outside the corridor
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "br", "beat_id": "b1", "t": 3.6, "probe": "relation",
         "gink": 4000, "gbbox": {"x": 900.0, "y": 900.0, "w": 200.0, "h": 4.0}}]}
    rep = production.verify(probes, observed)
    assert any(p["kind"] == "relation_detached" for p in rep["problems"])


def test_verify_flags_off_target_bound_label():
    probes = [{"id": "n1", "beat_id": "b1", "t": 3.6, "present": True,
               "probe": "relation",
               "rel": {"type": "bound_to", "from": "n1", "to": "h1",
                       "channel": "align_x", "target_cx": 640.0, "align_px": 16.0}}]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "n1", "beat_id": "b1", "t": 3.6, "probe": "relation",
         "gink": 3000, "gbbox": {"x": 200.0, "y": 100.0, "w": 100.0, "h": 40.0}}]}
    rep = production.verify(probes, observed)
    assert any(p["kind"] == "relation_detached" for p in rep["problems"])


def test_verify_accepts_correct_relation_and_counts_it():
    probes = [{"id": "br", "beat_id": "b1", "t": 3.6, "present": True,
               "probe": "relation",
               "rel": {"type": "flow_to", "from": "h1", "to": "h2",
                       "channel": "bridge_corridor",
                       "corridor": {"x0": 190.0, "x1": 410.0, "y0": 200.0,
                                    "y1": 260.0, "min_w": 110}}}]
    observed = {"available": True, "backend": "x", "beats": 1, "samples": [
        {"id": "br", "beat_id": "b1", "t": 3.6, "probe": "relation",
         "gink": 4000, "gbbox": {"x": 210.0, "y": 220.0, "w": 180.0, "h": 20.0}}]}
    rep = production.verify(probes, observed)
    assert rep["relation_checked"] == 1
    assert rep["verdict"] == "PASS", rep


# --- browser-gated: adjudicate the REAL player's Relation layer --------------


@needs_browser
def test_real_film_relation_layer_applied(tmp_path):
    import pipeline
    out = str(tmp_path / "out")
    pipeline.run(GOLDEN, out, render_previews=False, log=lambda *a: None)
    film = os.path.join(out, "film", "index.html")
    assert os.path.exists(film)
    report = production.run(film, os.path.join(out, "work"))
    assert report["available"] is True, report
    # the contract exercised the relation dimension, not just presence/motion
    assert report["relation_expected"] > 0, report
    assert report["relation_checked"] == report["relation_expected"], report
    assert report["verdict"] == "PASS", json.dumps(report, ensure_ascii=False)
