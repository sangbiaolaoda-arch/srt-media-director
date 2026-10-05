"""L2 Relationship / Scene Tests — 语义关系能够正确转化成运动。

Runtime Hardening · 测试金字塔 L2：Scene Graph + Relation Graph + State Graph +
Motion Graph。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from runtime.motion_runtime import (Relation, RelationRuntime, SceneGraph,
                                     StateRuntime, StateTransition)
from runtime.motion_runtime.connector import ConnectorRuntime
from runtime.motion_runtime.contracts import SceneCtx, make
from runtime.motion_runtime.identity import check_identity_continuity
from runtime.motion_runtime.scene import mat_mul, local_matrix


# ---------------------------------------------------------------- Scene Graph
def test_parent_transform_inherits_to_child():
    g = SceneGraph()
    g.add("group", parent="root", x=100, y=50)
    g.add("child", parent="group", x=10, y=10, w=20, h=20)
    before = g.world_center("child")
    g.get("group").x += 200       # 只移动父级
    after = g.world_center("child")
    assert abs((after[0] - before[0]) - 200) < 1e-9
    assert abs(after[1] - before[1]) < 1e-9


def test_world_matrix_equals_parent_times_local():
    g = SceneGraph()
    g.add("group", parent="root", x=30, y=40, scale=1.5, rotation=25)
    g.add("child", parent="group", x=5, y=6, w=10, h=10)
    expect = mat_mul(g.world_matrix("group"), local_matrix(g.get("child")))
    got = g.world_matrix("child")
    assert all(abs(a - b) < 1e-9 for a, b in zip(expect, got))


def test_world_opacity_multiplies_up_chain():
    g = SceneGraph()
    g.add("group", parent="root")
    g.add("child", parent="group")
    g.get("group").opacity = 0.5
    g.get("child").opacity = 0.5
    assert abs(g.world_opacity("child") - 0.25) < 1e-9


# ---------------------------------------------------------------- Relation
def test_relation_requires_source_and_target():
    r = Relation(source="", target="b", relation_type="CAUSE")
    errs = r.validate()
    assert any("source" in e for e in errs)


def test_relation_lifecycle_advances():
    rt = RelationRuntime()
    rel = rt.add(Relation(source="A", target="B", relation_type="CAUSE"))
    rt.advance(rel.id, "PROPAGATE")
    assert rt.get(rel.id).lifecycle == "PROPAGATE"


def test_cause_relation_drives_motion_not_just_fade():
    """CAUSE 关系必须编译出连接 + 传导运动，而不是 fade。"""
    rt = RelationRuntime()
    rel = rt.add(Relation(source="A", target="B", relation_type="CAUSE",
                          lifecycle="STRENGTHEN", trigger="A.activate"))
    prims = rt.compile_relation(rel)
    types = {p.motion_type for p in prims}
    assert "CONNECT" in types           # relation.establish
    assert "TRANSFER" in types or "DRAW" in types  # signal.propagate
    assert "ACTIVATE" not in types      # 不是简单 fade
    # 关系本身产生了运动
    assert prims
    for p in prims:
        assert p.reason and p.owner == rel.id


def test_surround_relation_compiles_surround_motion():
    rt = RelationRuntime()
    rel = rt.add(Relation(source="s1", target="subj", relation_type="SURROUND",
                          lifecycle="PROPAGATE"))
    types = {p.motion_type for p in rt.compile_relation(rel)}
    assert "SURROUND" in types


def test_relation_runtime_audit():
    rt = RelationRuntime()
    rt.add(Relation(source="A", target="B", relation_type="CAUSE"))
    assert rt.audit()["status"] == "PASS"


# ---------------------------------------------------------------- State
def test_state_requires_trigger():
    tr = StateTransition(from_state="inactive", to_state="active", trigger="")
    assert any("trigger" in e for e in tr.validate())


def test_state_chain_inactive_to_active():
    st = StateRuntime()
    st.default_chain()
    st.initial("n1", "inactive")
    assert st.fire("n1", "activate") is not None
    assert st.state_of("n1") == "activating"
    assert st.fire("n1", "complete") is not None
    assert st.state_of("n1") == "active"


def test_state_guard_blocks_without_condition():
    st = StateRuntime()
    st.register_guard("ready", lambda ctx: ctx.get("ok") is True)
    st.add_transition(StateTransition("inactive", "active", "go", guard="ready"))
    st.initial("n", "inactive")
    assert st.fire("n", "go", {"ok": False}) is None
    assert st.state_of("n") == "inactive"
    assert st.fire("n", "go", {"ok": True}) is not None
    assert st.state_of("n") == "active"


def test_state_change_has_reason():
    st = StateRuntime()
    st.default_chain()
    st.initial("n", "inactive")
    st.fire("n", "activate")
    h = st.history[-1]
    assert h["trigger"] == "activate"


# ---------------------------------------------------------------- Identity
def test_identity_preserved_in_normal_transition():
    viol = check_identity_continuity(["a", "b"], ["a", "b"],
                                     [make("MOVE", "a"), make("SCALE", "b")])
    assert viol == []


def test_identity_violation_when_id_changes_without_semantics():
    viol = check_identity_continuity(["a", "b"], ["a"], [make("MOVE", "a")])
    assert viol


def test_identity_allows_split():
    viol = check_identity_continuity(["a"], ["a", "a2"],
                                     [make("SPLIT", "a", params={"distance": 20})])
    assert viol == []
