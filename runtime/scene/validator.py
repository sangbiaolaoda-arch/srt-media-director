"""Machine Validator — 渲染 MP4 前直接拦错（Phase 2 · 第十八优先级）。

ERROR 级（阻断）：
  node "x" has no entrance plan
  relation "a → b" unresolved
  node "x" exceeds safe area
  transition references nonexistent state
  child node has invalid parent
  chart has no semantic purpose
WARNING 级：
  all elements enter simultaneously
  visual weight hierarchy missing
  scene contains excessive decorative elements
"""
from __future__ import annotations

from . import entrance as EN
from . import visual_weight as VW


def _safe_area(graph, canvas):
    W, H = canvas
    issues = []
    for n in graph.root.walk():
        if n.id == graph.root.id or not n.visible:
            continue
        x, y, w, h = n.world_box()
        if x < -0.5 or y < -0.5 or x + w > W + 0.5 or y + h > H + 0.5:
            issues.append({"severity": "err", "code": "SAFE_AREA_EXCEEDED",
                           "node": n.id,
                           "msg": 'node "%s" exceeds safe area %s' % (n.id, [round(v, 1) for v in n.world_box()])})
    return issues


def _parents(graph):
    issues = []
    for n in graph.root.walk():
        if n.id == graph.root.id:
            continue
        if n.parent is None and n is not graph.root:
            issues.append({"severity": "err", "code": "INVALID_PARENT",
                           "node": n.id, "msg": 'node "%s" has invalid parent' % n.id})
    return issues


def _charts(graph):
    issues = []
    for n in graph.root.walk():
        if n.kind in ("chart", "bar") and not n.semantic_role:
            issues.append({"severity": "err", "code": "CHART_NO_PURPOSE",
                           "node": n.id,
                           "msg": 'chart "%s" has no semantic purpose' % n.id})
    return issues


def validate(plan):
    graph, rel, sg = plan["graph"], plan["relations"], plan["states"]
    canvas = plan["canvas"]
    visible_ids = [n.id for n in graph.root.walk()
                   if n.id != graph.root.id and n.visible]
    issues = []
    # ---- ERROR ----
    issues += EN.audit(plan["entrances"], visible_ids=visible_ids)["issues"]
    issues += rel.validate(graph)["issues"]
    issues += sg.validate()["issues"]
    issues += _safe_area(graph, canvas)
    issues += _parents(graph)
    issues += _charts(graph)
    # ---- WARNING ----
    vt = VW.audit(graph)
    issues += vt["issues"]
    starts = [e["entrance"]["start"] for e in plan["entrances"]]
    if len(starts) >= 3 and len(set(round(s, 2) for s in starts)) == 1:
        issues.append({"severity": "warn", "code": "ALL_SIMULTANEOUS",
                       "msg": "all elements enter simultaneously"})
    errors = [i for i in issues if i["severity"] == "err"]
    warns = [i for i in issues if i["severity"] == "warn"]
    return {"status": "FAIL" if errors else "PASS",
            "errors": errors, "warnings": warns, "issues": issues}
