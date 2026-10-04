"""sequencing.py — 把「一拍的元素」排成有时间关系的故事序列。

scene → sequence → element motion：
  本模块只决定「谁先谁后、如何分组」，不决定具体动画。
输出每个元素的叙事 rank（越小越早）+ 分组，供 entrance.py 计算时刻。
"""
from .semantics import GRAMMAR_SEQUENCING, NO_MOTION_ROLES


def _is_connector(el):
    return el.get("type") in ("connector", "path", "line") or el.get("semantic_role") == "relationship"


def _box_of(el, boxes):
    b = boxes.get(el["id"]) or el.get("box")
    if not b:
        return (0, 0, 0, 0)
    return tuple(b)


def _chain_order(active, relations):
    """causality/progression：用关系图做拓扑序，链接元素插在其 from 之后。"""
    ids = [e["id"] for e in active]
    indeg = {i: 0 for i in ids}
    adj = {i: [] for i in ids}
    for r in relations:
        f, t = r.get("from"), r.get("to")
        if f in indeg and t in indeg:
            adj[f].append(t)
            indeg[t] += 1
    queue = [i for i in ids if indeg[i] == 0]
    out = []
    while queue:
        n = queue.pop(0)
        out.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    for i in ids:            # 环或孤立点兜底
        if i not in out:
            out.append(i)
    return [e for i in out for e in active if e["id"] == i]


def build_sequence(beat, elements, boxes=None):
    """返回 {'mode', 'rank': {id: rank}, 'ambient', 'connectors', 'groups', 'active'}。"""
    boxes = boxes or {}
    grammar = beat.get("grammar") or beat.get("grammar_ops") or ["establish"]
    mode = GRAMMAR_SEQUENCING.get(grammar[0], "ambient_then_focal")

    ambient = {e["id"] for e in elements if e.get("semantic_role") in NO_MOTION_ROLES}
    connectors = {e["id"] for e in elements if _is_connector(e)} - ambient
    focal_id = beat.get("focal_point")

    active = [e for e in elements if e["id"] not in ambient and e["id"] not in connectors]

    def x_of(e): return _box_of(e, boxes)[0]
    def y_of(e): return _box_of(e, boxes)[1]

    if mode in ("left_to_right", "split_two_groups"):
        active.sort(key=lambda e: (x_of(e), y_of(e)))
    elif mode == "focal_last":
        active.sort(key=lambda e: (e["id"] == focal_id, y_of(e)))
    elif mode == "chain":
        active = _chain_order(active, beat.get("relations") or [])
    elif mode == "sequential_stagger":
        pass                                  # 保持给定顺序（语义上已排好）
    else:                                     # ambient_then_focal
        active.sort(key=lambda e: (e["id"] == focal_id,))

    rank = {e["id"]: i for i, e in enumerate(active)}

    # 关系类元素：紧随其 from 端点出现（表达「关系在两者之间形成」）
    rels = beat.get("relations") or []
    for cid in connectors:
        base = None
        for r in rels:
            if r.get("to") == cid and r.get("from") in rank:
                v = rank[r["from"]] + 0.5
                base = v if base is None else max(base, v)
            if r.get("from") == cid and r.get("to") in rank:
                v = rank[r["to"]] - 0.5
                base = v if base is None else min(base, v)
        if base is None:
            base = (max(rank.values()) + 0.5) if rank else 0.5
        rank[cid] = base

    for aid in ambient:
        rank[aid] = -1.0

    groups = {}
    if mode == "split_two_groups":
        half = (len(active) + 1) // 2
        for i, e in enumerate(active):
            groups[e["id"]] = 0 if i < half else 1

    return {"mode": mode, "rank": rank, "ambient": ambient,
            "connectors": connectors, "groups": groups,
            "active": [e["id"] for e in active]}
