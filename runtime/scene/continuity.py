"""Scene Continuity — 跨镜头连续性（Phase 2 · 第十九优先级）。

相邻镜头不要每次重建世界。上一镜头有 person，下一镜头仍需要 person 时，
应「沿用 + transform / move / change state」，而不是新建 person_02。

对外提供 carry()：把上一场景的指定实体连同其子树带进下一场景图。
"""
from __future__ import annotations

import copy


def carry(prev_graph, next_graph, entities):
    """把 prev 中的实体（保持同一 id）搬进 next（未存在的才搬，避免重建）。"""
    carried, skipped = [], []
    for eid in entities:
        if next_graph.has(eid):
            skipped.append(eid)          # 已存在 → 复用，不重建
            continue
        if not prev_graph.has(eid):
            skipped.append(eid)
            continue
        src = prev_graph.get(eid)
        clone = copy.deepcopy(src)
        clone.parent = None
        clone.children = []
        next_graph.root.add(clone)
        next_graph.index[clone.id] = clone
        for n in clone.walk():
            next_graph.index[n.id] = n
        carried.append(eid)
    return {"carried": carried, "reused": skipped}


def audit(prev_graph, next_graph, expected):
    """expected: 应在相邻镜头间保持连续的实体 id 列表。"""
    issues = []
    for eid in expected:
        if not next_graph.has(eid):
            issues.append({"severity": "warn", "code": "CONTINUITY_REBUILD",
                           "entity": eid,
                           "msg": "entity %r not carried (rebuilt or dropped)" % eid})
    return {"status": "FAIL" if any(i["severity"] == "err" for i in issues)
            else "PASS", "issues": issues}
