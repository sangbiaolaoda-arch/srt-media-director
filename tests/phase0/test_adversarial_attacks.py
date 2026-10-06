"""P0-4 gates — behaviour-level lazy-path detection (not field presence).

Attack classes:
  A. padding a count with empty-shell elements -> meaningless_elements
  B. motion that cannot be observed            -> fake_motion
  C. continuity that carries nothing            -> fake_continuity
  D. editing the judge/threshold with no impl   -> test_pollution
Plus positive controls proving genuine content is NOT flagged.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from verification import adversarial  # noqa: E402


def _paths(findings):
    return {f["lazy_path"] for f in findings}


# ------------------------------------------------------------------ A. padding
def test_empty_shell_elements_are_caught():
    dsl = {"beats": [{"beat_id": "b1", "elements": [
        {"id": "e1"}, {"id": "e2"}, {"id": "e3"}]}]}   # three useless shells
    assert "meaningless_elements" in _paths(adversarial.scan(dsl=dsl))


def test_semantically_participating_elements_are_not_flagged():
    dsl = {"beats": [{"beat_id": "b1", "elements": [
        {"id": "t", "type": "text", "text": "hello"},
        {"id": "m", "type": "motif", "motif": "arrow"},
        {"id": "x", "box": [0, 0, 10, 10]}]}]}
    assert "meaningless_elements" not in _paths(adversarial.scan(dsl=dsl))


# ------------------------------------------------------------------ B. fake motion
def test_instant_motion_in_long_beat_is_fake():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0, "end_sec": 6,
                      "elements": [{"id": "e1"}]}]}
    entrance = {"beats": [{"beat_id": "b1",
                           "lifecycle": {"e1": {"enter": {"motion": "fade", "duration": 0.0}}}}]}
    assert "fake_motion" in _paths(adversarial.scan(dsl=dsl, entrance=entrance))


def test_duration_longer_than_beat_is_fake():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0, "end_sec": 1.0,
                      "elements": [{"id": "e1"}]}]}
    entrance = {"beats": [{"beat_id": "b1",
                           "lifecycle": {"e1": {"enter": {"motion": "rise", "duration": 5.0}}}}]}
    assert "fake_motion" in _paths(adversarial.scan(dsl=dsl, entrance=entrance))


def test_observable_motion_is_not_flagged():
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0, "end_sec": 2.0,
                      "elements": [{"id": "e1"}]}]}
    entrance = {"beats": [{"beat_id": "b1",
                           "lifecycle": {"e1": {"enter": {"motion": "rise", "duration": 0.6}}}}]}
    assert "fake_motion" not in _paths(adversarial.scan(dsl=dsl, entrance=entrance))


# ------------------------------------------------------------------ C. fake continuity
def test_carry_over_without_previous_element_is_fake():
    dsl = {"beats": [{"beat_id": "b1", "elements": [{"id": "a"}]},
                     {"beat_id": "b2", "elements": [{"id": "b"}]}]}
    entrance = {"beats": [{"beat_id": "b1", "lifecycle": {"a": {"enter": {"motion": "fade"}}}},
                          {"beat_id": "b2", "lifecycle": {"b": {"enter": {"motion": "inherit"}}}}]}
    assert "fake_continuity" in _paths(adversarial.scan(dsl=dsl, entrance=entrance))


def test_persisted_element_reentering_is_fake():
    dsl = {"beats": [{"beat_id": "b1", "elements": [{"id": "a"}]},
                     {"beat_id": "b2", "elements": [{"id": "a"}]}]}
    entrance = {"beats": [{"beat_id": "b1", "lifecycle": {"a": {"enter": {"motion": "fade"}}}},
                          {"beat_id": "b2", "lifecycle": {"a": {"enter": {"motion": "fade"}}}}]}
    assert "fake_continuity" in _paths(adversarial.scan(dsl=dsl, entrance=entrance))


def test_genuine_carry_over_is_not_flagged():
    dsl = {"beats": [{"beat_id": "b1", "elements": [{"id": "a"}]},
                     {"beat_id": "b2", "elements": [{"id": "a"}, {"id": "b"}]}]}
    entrance = {"beats": [{"beat_id": "b1", "lifecycle": {"a": {"enter": {"motion": "fade"}}}},
                          {"beat_id": "b2", "lifecycle": {
                              "a": {"enter": {"motion": "inherit"}},
                              "b": {"enter": {"motion": "rise"}}}}]}
    assert "fake_continuity" not in _paths(adversarial.scan(dsl=dsl, entrance=entrance))


# ------------------------------------------------------------------ D. pollution
def test_judge_edit_without_impl_is_pollution():
    assert "test_pollution" in _paths(adversarial.scan(
        changed_paths=["runtime/validator.py"]))
    assert "test_pollution" in _paths(adversarial.scan(
        changed_paths=["tests/golden/01-minimal/entrance-plan.json"]))


def test_impl_change_with_judge_edit_is_not_pollution():
    assert "test_pollution" not in _paths(adversarial.scan(
        changed_paths=["runtime/pipeline.py", "runtime/validator.py"]))


def test_test_only_change_still_caught():
    assert "test_only_change" in _paths(adversarial.scan(changed_paths=["tests/x.py"]))
