"""P2 — Primitive state vocabulary gate (machine-executable).

The entrance planner emits element-level **state animations** (draw / chart_fill /
bars_grow / color_wash / pulse) plus a beat-level ``settle`` marker; BOTH renderers
implement them. Before this gate the vocabulary was a shared, UNCONTRACTED protocol.
This gate makes it a first-class single-source-of-truth:

  1. the contract ``contracts/primitive_states.v1.json`` and ``primitives.states``
     agree exactly;
  2. the producer (``motion_canonical.entrance``) emits only declared actions on
     real content, and emits every declared state action;
  3. every consumer renderer implements every declared state action;
  4. no undeclared action leaks from the producer.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, RUNTIME)

import beat_planner  # noqa: E402
import entrance_planner  # noqa: E402
import srt_parser  # noqa: E402
import visual_director  # noqa: E402
from primitives import states  # noqa: E402

CONTRACT = os.path.join(ROOT, "contracts", "primitive_states.v1.json")
CONSUMERS = ["html_adapter.py", "raster_renderer.py"]


def _contract():
    return json.load(open(CONTRACT, encoding="utf-8"))


def test_contract_matches_states_module():
    c = _contract()
    assert tuple(c["state_actions"]) == states.STATE_ACTIONS
    assert tuple(c["resolve_actions"]) == states.RESOLVE_ACTIONS
    assert not (set(states.STATE_ACTIONS) & set(states.RESOLVE_ACTIONS))


def _emitted_actions():
    """Collect every action the real entrance planner emits across real SRTs."""
    seen = set()
    for srt, ov in (("examples/minimal/attention.srt", None),
                    ("examples/showcase/03-data-comparison/case.srt", None),
                    ("tests/golden/01-minimal/case.srt", None)):
        p = os.path.join(ROOT, srt)
        if not os.path.isfile(p):
            continue
        analysis = srt_parser.analyze(p)
        beats = beat_planner.plan_beats(analysis["cues"])
        _, dsl = visual_director.direct(beats, {})
        plan = entrance_planner.plan(dsl)
        for b in plan["beats"]:
            for ev in b.get("events", []):
                seen.add(ev["action"])
    return seen


def test_producer_emits_only_declared_actions():
    emitted = _emitted_actions()
    assert emitted, "expected the entrance planner to emit interaction events"
    undeclared = emitted - set(states.ALL_ACTIONS)
    assert not undeclared, "undeclared primitive-state action(s): %s" % sorted(undeclared)
    # producer must exercise the full per-element state vocabulary on real content
    assert set(states.STATE_ACTIONS) <= emitted, sorted(set(states.STATE_ACTIONS) - emitted)


def test_every_consumer_implements_every_state_action():
    for fname in CONSUMERS:
        src = open(os.path.join(RUNTIME, fname), encoding="utf-8").read()
        missing = [a for a in states.STATE_ACTIONS
                   if not re.search(r'["\']%s["\']' % re.escape(a), src)]
        assert not missing, "%s does not implement: %s" % (fname, missing)
