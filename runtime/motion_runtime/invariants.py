"""runtime/motion_runtime/invariants.py — Motion Invariants（Runtime Hardening · P0）。

机器可验证的不变量（来自指令 §17）：

    Identity    object_id 在普通 transition 中不能改变
    Parent      parent 移动 → child world transform 必须同步
    Connector   source / target 移动 → connector 必须更新
    State       state transition 必须拥有 trigger
    Relation    semantic relation 必须拥有 source + target
    Motion      每个 motion 必须拥有 trigger
    Cleanup     motion 完成后不得留下 orphan animation

每条不变量返回 {name, status: PASS|FAIL, detail}。
"""
from __future__ import annotations

from typing import List

from .contracts import CHANNEL_NEUTRAL
from .identity import IdentityRegistry, check_identity_continuity
from .scene import SceneGraph


def _inv(name, ok, detail=""):
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def invariant_identity(before_ids, after_ids, motions):
    viol = check_identity_continuity(before_ids, after_ids, motions)
    return _inv("Identity", not viol, "; ".join(viol))


def invariant_parent(scene: SceneGraph, child: str, parent: str) -> dict:
    """父级世界矩阵必须在 child 的世界矩阵链中体现（继承生效）。"""
    if not scene.has(child) or not scene.has(parent):
        return _inv("Parent", False, "missing node")
    cm = scene.world_matrix(child)
    pm = scene.world_matrix(parent)
    # 合成一致性：world(child) == world(parent) @ local(child)
    from .scene import mat_mul, local_matrix
    expected = mat_mul(pm, local_matrix(scene.get(child)))
    ok = all(abs(a - b) < 1e-6 for a, b in zip(cm, expected))
    return _inv("Parent", ok, "world(child)=%s" % (tuple(round(v, 4) for v in cm),))


def invariant_connector_reacts(conn, scene_before, scene_after) -> dict:
    """端点移动后 connector 端点坐标必须变化（动态跟随而非静态坐标）。"""
    a = conn.recompute(scene_before)
    b = conn.recompute(scene_after)
    moved = (abs(a["x1"] - b["x1"]) > 1e-6 or abs(a["y1"] - b["y1"]) > 1e-6 or
             abs(a["x2"] - b["x2"]) > 1e-6 or abs(a["y2"] - b["y2"]) > 1e-6)
    return _inv("Connector", moved, "Δ endpoints recomputed=%s" % moved)


def invariant_state_trigger(state_runtime) -> dict:
    bad = [t for t in state_runtime._transitions if not t.trigger]  # noqa: SLF001
    return _inv("State", not bad, "%d transition(s) without trigger" % len(bad))


def invariant_relation(relation_runtime) -> dict:
    bad = [r.id for r in relation_runtime.all()
           if not r.source or not r.target]
    return _inv("Relation", not bad, "relations missing source/target: %s" % bad)


def invariant_motion_trigger(primitives, default_trigger=None) -> dict:
    bad = [p.motion_type for p in primitives
           if not p.trigger and not default_trigger]
    return _inv("Motion", not bad, "%d motion(s) without trigger" % len(bad))


def invariant_cleanup(primitives, ctx, t_end: float) -> dict:
    """motion 完成后不得留下 orphan animation。

    对声明 cleanup_policy='revert' 的原语，其作用窗口结束后采样必须回到中性通道。
    """
    orphans = []
    for p in primitives:
        c = p.contract()
        if c.cleanup_policy != "revert":
            continue
        _, e = p.time_range()
        if t_end <= e:
            continue
        s = p.sample(ctx, t_end)
        if s is None:
            continue
        for node, ch in s.items():
            for k, v in ch.items():
                if k == "state":
                    continue
                if abs(v - CHANNEL_NEUTRAL.get(k, 0.0)) > 1e-6:
                    orphans.append("%s.%s=%s" % (node, k, round(v, 4)))
    return _inv("Cleanup", not orphans, "orphan animation: %s" % orphans)


def run_all(*, scene, before_ids, after_ids, motions, primitives, ctx,
            state_runtime=None, relation_runtime=None, t_end=0.0,
            parent_child=None, connector=None, scene_before=None,
            scene_after=None) -> dict:
    checks = []
    checks.append(invariant_identity(before_ids, after_ids, motions))
    if parent_child:
        checks.append(invariant_parent(scene, *parent_child))
    if connector is not None and scene_before is not None and scene_after is not None:
        checks.append(invariant_connector_reacts(connector, scene_before, scene_after))
    if state_runtime is not None:
        checks.append(invariant_state_trigger(state_runtime))
    if relation_runtime is not None:
        checks.append(invariant_relation(relation_runtime))
    checks.append(invariant_motion_trigger(primitives))
    checks.append(invariant_cleanup(primitives, ctx, t_end))
    failed = [c for c in checks if c["status"] == "FAIL"]
    return {"status": "FAIL" if failed else "PASS", "checks": checks,
            "failed": [c["name"] for c in failed]}
