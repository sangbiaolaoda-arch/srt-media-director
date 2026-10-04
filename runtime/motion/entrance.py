"""entrance.py — 依据序列 rank/分组，计算元素入场时刻与时长。

Agent 不提供 duration/delay/easing —— 全部由这里按
  角色权重 × 拍长 × 语法分组  自动生成（不硬编码成永远相同的数值）。
"""
from .semantics import ROLE_WEIGHT


def timing(seq, elements, beat_duration, step_ratio=0.14):
    """返回 {element_id: {'at':s, 'dur':s, 'group':int, 'static':bool}}（秒，相对拍首）。"""
    rank = seq["rank"]
    groups = seq.get("groups") or {}
    elems = {e["id"]: e for e in elements}

    active_ranks = [r for r in rank.values() if r >= 0]
    step = beat_duration * step_ratio
    group_gap = beat_duration * 0.18 if seq["mode"] == "split_two_groups" else 0.0

    out = {}
    for eid, r in rank.items():
        e = elems.get(eid, {})
        role = e.get("semantic_role")
        w = ROLE_WEIGHT.get(role, 0.5)
        if r < 0:
            out[eid] = {"at": 0.0, "dur": 0.0, "group": 0, "static": True}
            continue
        at = r * step
        if groups.get(eid) == 1:
            at += group_gap
        # 时长随重要度与拍长变化：焦点更长更明显，辅助更短更轻
        dur = (0.5 + 0.5 * w) * min(1.0, beat_duration * 0.24)
        dur = max(0.35, min(1.4, dur))
        at = max(0.0, min(at, beat_duration * 0.72))
        out[eid] = {"at": round(at, 3), "dur": round(dur, 3),
                    "group": groups.get(eid, 0), "static": False}
    return out
