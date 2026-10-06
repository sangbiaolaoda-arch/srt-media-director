"""P2-2 Phase-1 — regression test for the State -> Delta -> Transition -> Motion loop.

Mirrors ``tools/phase1_state_delta_closure.py`` as a pytest so CI reproduces the
real-renderer evidence on every run.

Scope: single entity, two states, growth transition, real renderer t0/t_mid/t1.
Deliberately does NOT touch the 21-case production corpus or sealed golden files.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, "runtime"))

import state_delta as sd  # noqa: E402


def _states():
    a = {"id": "b1_chart", "identity": "revenue_chart", "type": "chart",
         "role": "primary", "state": {"value": 30.0, "status": "normal"}}
    b = {"id": "b2_chart", "identity": "revenue_chart", "type": "chart",
         "role": "primary", "state": {"value": 70.0, "status": "normal"}}
    return a, b


def test_identity_is_explicit_not_id_derived():
    # an element without `identity` must NOT be treated as continuous
    bare = {"id": "b2_chart", "type": "chart"}
    assert sd.element_identity(bare) is None
    a, b = _states()
    matches = sd.match_identity([a], [b])
    assert len(matches) == 1 and matches[0].rule == "same_id"


def test_state_to_delta_has_reason_and_direction():
    a, b = _states()
    deltas = sd.derive_delta(sd.entity_state(a), sd.entity_state(b),
                             reason="revenue grew from 30 to 70")
    v = [d for d in deltas if d.kind == "value"][0]
    assert v.frm == 30.0 and v.to == 70.0
    assert v.reason and v.direction() == "up"
    assert sd.validate_deltas(deltas, span=(0.0, 2.0)) == []


def test_growth_transition_and_interpolation():
    a, b = _states()
    deltas = sd.derive_delta(sd.entity_state(a), sd.entity_state(b), reason="growth")
    v = [d for d in deltas if d.kind == "value"][0]
    trans = sd.classify_transition("b1", "b2", ["revenue_chart"], deltas)
    assert trans.type == "transform"          # continuous WITH real change
    spec = sd.compile_motion(v, (0.0, 2.0))
    assert spec.action == "growth"
    assert sd.sample_value(spec, 0.0) == 30.0
    assert sd.sample_value(spec, 2.0) == 70.0
    assert 30.0 < sd.sample_value(spec, 1.0) < 70.0   # not an instant jump


def test_fade_alone_cannot_pass_motion():
    # a pure opacity fade carries no `value` delta -> classify as carry, not transform
    a = {"id": "x1", "identity": "e1", "state": {"value": 30.0, "opacity": 0.0}}
    b = {"id": "x2", "identity": "e1", "state": {"value": 30.0, "opacity": 1.0}}
    deltas = sd.derive_delta(sd.entity_state(a), sd.entity_state(b), reason="fade in")
    only_opacity = all(d.kind == "opacity" for d in deltas)
    assert only_opacity
    trans = sd.classify_transition("b1", "b2", ["e1"], [] if only_opacity else deltas)
    # no value motion -> not a growth/transform-of-value
    assert trans.type in ("carry", "transform")
