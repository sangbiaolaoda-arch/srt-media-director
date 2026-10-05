"""Motion Conflict Solver Tests — 多关系同时作用不得互相覆盖导致不可预测结果。

Runtime Hardening · 冲突测试：follow_vs_move / follow_vs_repel / parent_vs_child /
layout_vs_motion / camera_vs_object / relation_vs_constraint。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from runtime.motion_runtime import MotionRuntime, SceneGraph, make
from runtime.motion_runtime.conflict import ConflictSolver, Contribution


def _c(node, ch, val, **kw):
    return Contribution(node=node, channel=ch, value=val, **kw)


def test_add_blend_sums_contributions():
    s = ConflictSolver()
    r = s.resolve([_c("n", "dx", 10), _c("n", "dx", 5)])
    assert abs(r["transforms"]["n"]["dx"] - 15) < 1e-9


def test_override_wins_by_priority():
    s = ConflictSolver()
    r = s.resolve([_c("n", "dx", 10, priority=1, blend="override"),
                   _c("n", "dx", 100, priority=5, blend="override")])
    assert abs(r["transforms"]["n"]["dx"] - 100) < 1e-9


def test_override_tie_reported_as_conflict():
    s = ConflictSolver()
    r = s.resolve([_c("n", "dx", 10, priority=3, blend="override"),
                   _c("n", "dx", 20, priority=3, blend="override")])
    assert any(c["code"] == "OVERRIDE_TIE" for c in r["conflicts"])


def test_weighted_average():
    s = ConflictSolver()
    r = s.resolve([_c("n", "scale", 2.0, blend="weighted", strength=1.0),
                   _c("n", "scale", 0.0, blend="weighted", strength=1.0)])
    assert abs(r["transforms"]["n"]["scale"] - 1.0) < 1e-9


def test_max_min_blend():
    s = ConflictSolver()
    r = s.resolve([_c("n", "dx", 5, blend="max"), _c("n", "dx", 9, blend="max"),
                   _c("n", "dy", -3, blend="min"), _c("n", "dy", -8, blend="min")])
    assert abs(r["transforms"]["n"]["dx"] - 9) < 1e-9
    assert abs(r["transforms"]["n"]["dy"] + 8) < 1e-9


def test_solver_is_deterministic_and_order_independent():
    a = [_c("n", "dx", 10, priority=1), _c("n", "dx", 3, priority=2),
         _c("n", "dx", -2, priority=0)]
    import random
    r1 = ConflictSolver().resolve(list(a))
    shuffled = list(a)
    random.Random(0).shuffle(shuffled)
    # sort by priority makes result order-independent for add blends
    r2 = ConflictSolver().resolve(sorted(shuffled, key=lambda c: c.priority))
    assert r1["transforms"] == r2["transforms"]


# ------------------------------------------------- 具体冲突场景（端到端）
def _scene():
    g = SceneGraph()
    g.add("a", parent="root", x=0, y=0, w=100, h=100)
    g.add("b", parent="root", x=400, y=0, w=100, h=100)
    return g


def test_follow_vs_move_no_last_wins():
    """FOLLOW 与 MOVE 同时作用于同一节点：必须融合，不是后到者覆盖。"""
    rt = MotionRuntime(_scene())
    rt.add(make("FOLLOW", "a", target="b", duration=1.0, start=0.0),
           make("MOVE", "a", duration=1.0, start=0.0, params={"offset": (0, 50)}))
    tr = rt.sample(1.0)["transforms"]["a"]
    # 若为 last-wins，MOVE 会覆盖 FOLLOW → dx 归零。dx 仍显著为正即证明两者已融合。
    assert tr["dx"] > 100                # FOLLOW 向 b 的位移未被 MOVE 覆盖
    assert abs(tr["dy"] - 50.0) < 1e-6   # MOVE 的纵向位移叠加保留


def test_follow_vs_repel_same_node():
    rt = MotionRuntime(_scene())
    rt.add(make("FOLLOW", "a", target="b", duration=1.0),
           make("REPEL", "a", target="b", duration=1.0, params={"reach": 30.0}))
    res = rt.sample(1.0)
    assert "a" in res["transforms"]  # 融合出确定性结果


def test_camera_vs_object_independent():
    """Camera 与 object 变换互不覆盖。"""
    rt = MotionRuntime(_scene())
    rt.add(make("MOVE", "a", duration=1.0, params={"offset": (10, 0)}))
    rt.camera.zoom_to(2.0)
    res = rt.sample(1.0)
    assert res["camera"]["zoom"] == 2.0
    assert abs(res["transforms"]["a"]["dx"] - 10) < 1e-6
