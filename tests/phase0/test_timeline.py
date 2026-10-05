"""Dynamic timeline observation tests — Directive v5 §35-§36, §61.

Temporal properties must be judged on observed state over time, not on the
runtime's own claim. These tests exercise the timeline comparator with synthetic
observed timelines (no browser needed), and one live run when a browser exists.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from observer import browser, timeline  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _anchor(case="cause_effect"):
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


def _faithful_states(ws):
    """Build observed timelines that exactly mirror the expected states."""
    return [dict(s, available=True) for s in timeline.expected_timeline(ws)]


def _states(*steps):
    """Explicit synthetic ObservedState(t): each step is (t, focus, visible, edges)."""
    out = []
    for t, focus, visible, edges in steps:
        out.append({"t": t, "focus": set(focus), "visible": set(visible),
                    "edges": set(edges), "ids": set(focus) | set(visible),
                    "available": True})
    return out


def test_expected_timeline_has_one_state_per_frame():
    ws = compiler.compile_world_state(_anchor())
    exp = timeline.expected_timeline(ws)
    assert len(exp) == len(ws.frames)
    assert [s["t"] for s in exp] == [f.t for f in ws.frames]


def test_faithful_timeline_passes():
    ws = compiler.compile_world_state(_anchor())
    exp = timeline.expected_timeline(ws)
    rep = timeline.compare_timeline(exp, _faithful_states(ws))
    assert rep["status"] == "TIMELINE_OK", rep
    assert rep["checks"]["ordering"] is True
    assert rep["checks"]["focus_transition"] is True
    assert rep["checks"]["relation_lifecycle"] is True
    # camera is honestly NOT claimed
    assert rep["checks"]["camera_transition"] is None


def test_reversed_focus_order_fails_ordering():
    """If the observed first-focus order is swapped, ordering must fail."""
    exp = _states((0, {"A"}, {"A", "B"}, set()),
                  (1, {"B"}, {"A", "B"}, set()))
    obs = _states((0, {"B"}, {"A", "B"}, set()),
                  (1, {"A"}, {"A", "B"}, set()))
    rep = timeline.compare_timeline(exp, obs)
    assert rep["status"] == "TIMELINE_FAIL"
    assert rep["checks"]["ordering"] is False


def test_shifted_focus_step_fails_focus_transition():
    ws = compiler.compile_world_state(_anchor())
    exp = timeline.expected_timeline(ws)
    obs = _faithful_states(ws)
    obs[0]["focus"] = set()  # focus arrives a step late
    rep = timeline.compare_timeline(exp, obs)
    assert rep["status"] == "TIMELINE_FAIL"
    assert rep["checks"]["focus_transition"] is False


def test_broken_connector_fails_relation_lifecycle():
    """A connector that should persist but vanishes must fail lifecycle."""
    edge = ("A", "B", "causes")
    exp = _states((0, {"A"}, {"A", "B"}, {edge}),
                  (1, {"B"}, {"A", "B"}, {edge}))
    obs = _states((0, {"A"}, {"A", "B"}, {edge}),
                  (1, {"B"}, {"A", "B"}, set()))  # connector disappears
    rep = timeline.compare_timeline(exp, obs)
    assert rep["status"] == "TIMELINE_FAIL"
    assert rep["checks"]["relation_lifecycle"] is False


def test_missing_step_is_detected():
    ws = compiler.compile_world_state(_anchor())
    exp = timeline.expected_timeline(ws)
    obs = _faithful_states(ws)[:-1]
    rep = timeline.compare_timeline(exp, obs)
    assert rep["status"] == "TIMELINE_FAIL"


def test_unavailable_timeline_degrades_to_environment_fail():
    ws = compiler.compile_world_state(_anchor())
    exp = timeline.expected_timeline(ws)
    rep = timeline.compare_timeline(exp, [])
    assert rep["status"] == "UNAVAILABLE"
    assert rep["failure_class"] == "ENVIRONMENT_FAIL"


# --- live (browser-gated): the whole render->observe timeline ---------------

needs_browser = pytest.mark.skipif(not browser.available(),
                                   reason="no functional browser")


@needs_browser
def test_live_timeline_render_observe_passes(tmp_path):
    ws = compiler.compile_world_state(_anchor())
    exp = timeline.expected_timeline(ws)
    obs = timeline.observe_timeline(ws, str(tmp_path / "tl"))
    assert obs and all(s["available"] for s in obs), obs
    rep = timeline.compare_timeline(exp, obs)
    assert rep["status"] == "TIMELINE_OK", rep
