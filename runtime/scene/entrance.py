"""Entrance Plan — 统一入场计划（Phase 2 · 第七优先级，强制门禁）。

每个可见对象都必须拥有 Entrance，且字段完整：
    method / start / duration / easing / delay / dependency / reason
禁止 visible=True 却没有任何 Entrance Plan。
"""
from __future__ import annotations

REQUIRED = ("method", "start", "duration", "easing", "reason")


def make(nid, method, start=0.0, duration=0.45, easing="easeOut",
         delay=0.0, dependency=None, reason=""):
    return {"id": nid, "entrance": {
        "method": method, "start": float(start), "duration": float(duration),
        "easing": easing, "delay": float(delay),
        "dependency": dependency, "reason": reason}}


def build(graph, default_method="fade", schedule=None):
    """为场景中所有可见节点生成 Entrance；已有 custom entrance 则保留。"""
    plans = []
    for n in graph.root.walk():
        if n.id == graph.root.id:
            continue
        if not n.visible:
            continue
        ce = n.data.get("entrance")
        if ce:
            plans.append({"id": n.id, "entrance": ce})
            continue
        start = 0.0
        dep = None
        if schedule and n.id in schedule:
            start = schedule[n.id]["start"]
        elif schedule and n.parent is not None and n.parent.id in schedule:
            idx = [c.id for c in n.parent.children].index(n.id)
            start = schedule[n.parent.id]["start"] + 0.1 * (idx + 1)
        if n.parent is not None and n.parent.id != graph.root.id:
            dep = n.parent.id
        plans.append(make(n.id, default_method, start=start,
                          dependency=dep,
                          reason=n.reason or ("作为 %s 入场" % n.weight)))
    return plans


def audit(plan, visible_ids=None):
    issues = []
    seen = set()
    for p in plan:
        nid = p.get("id")
        seen.add(nid)
        ent = p.get("entrance") or {}
        for f in REQUIRED:
            if f not in ent or ent[f] in (None, ""):
                issues.append({"severity": "err", "code": "ENTRANCE_INCOMPLETE",
                               "node": nid,
                               "msg": "node %r entrance missing field %r" % (nid, f)})
        dep = ent.get("dependency")
        if dep and visible_ids is not None and dep not in visible_ids:
            issues.append({"severity": "warn", "code": "ENTRANCE_DEPENDENCY",
                           "node": nid,
                           "msg": "dependency %r not visible" % dep})
    if visible_ids is not None:
        for nid in visible_ids:
            if nid not in seen:
                issues.append({"severity": "err", "code": "MISSING_ENTRANCE",
                               "node": nid,
                               "msg": 'node "%s" has no entrance plan' % nid})
    return {"status": "FAIL" if any(i["severity"] == "err" for i in issues)
            else "PASS", "issues": issues, "count": len(plan)}
