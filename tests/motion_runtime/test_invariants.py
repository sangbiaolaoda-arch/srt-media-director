"""Motion Invariants Tests — 机器可验证的不变量。

Runtime Hardening · §17。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from runtime.motion_runtime import (Relation, SceneGraph, make)
from runtime.motion_runtime.connector import ConnectorRuntime
from runtime.motion_runtime.contracts import SceneCtx
from runtime.motion_runtime.invariants import (invariant_connector_reacts,
                                                invariant_identity,
                                                invariant_motion_trigger,
                                                invariant_parent,
                                                invariant_relation,
                                                invariant_state_trigger)
from runtime.motion_runtime.relations import RelationRuntime
from runtime.motion_runtime.states import StateRuntime


def test_invariant_parent_holds():
    g = SceneGraph()
    g.add("p", parent="root", x=10, y=20)
    g.add("c", parent="p", x=3, y=4, w=10, h=10)
    assert invariant_parent(g, "c", "p")["status"] == "PASS"


def test_invariant_connector_reacts_to_move():
    g = SceneGraph()
    g.add("a", parent="root", x=0, y=0, w=100, h=100)
    g.add("b", parent="root", x=300, y=0, w=100, h=100)
    cr = ConnectorRuntime()
    c = cr.bind("c1", "a", "b")
    before = g.clone()
    g.get("a").x += 50
    assert invariant_connector_reacts(c, before, g)["status"] == "PASS"


def test_invariant_connector_static_is_flagged():
    g = SceneGraph()
    g.add("a", parent="root", w=100, h=100)
    g.add("b", parent="root", x=300, w=100, h=100)
    cr = ConnectorRuntime()
    c = cr.bind("c1", "a", "b")
    # 不移动任何端点 → connector 不变化 → 被标记（说明它确实在动态重算）
    assert invariant_connector_reacts(c, g, g.clone())["status"] == "FAIL"


def test_invariant_state_trigger():
    st = StateRuntime()
    st.default_chain()
    assert invariant_state_trigger(st)["status"] == "PASS"


def test_invariant_relation_requires_endpoints():
    rt = RelationRuntime()
    rt.add(Relation(source="a", target="b"))
    assert invariant_relation(rt)["status"] == "PASS"


def test_invariant_motion_requires_trigger():
    p = make("MOVE", "a", duration=1.0, trigger="t0")
    assert invariant_motion_trigger([p])["status"] == "PASS"
    p2 = make("MOVE", "a", duration=1.0)
    assert invariant_motion_trigger([p2])["status"] == "FAIL"
    assert invariant_motion_trigger([p2], default_trigger="global")["status"] == "PASS"


def test_invariant_identity():
    assert invariant_identity(["a"], ["a"], [make("MOVE", "a")])["status"] == "PASS"
