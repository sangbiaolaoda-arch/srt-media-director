"""Render Plan — DSL → 一键编译（Phase 2 编译链）。

    Visual DSL → Render Plan → Constraint Solver → Motion Compiler → 帧

产物：
- boxes：每个根节点的像素位置（求解后）
- entrances：统一 Entrance Plan（强制）
- motions：每条状态迁移 → 动画参数
- frames：每个状态的可渲染 spec（用于截图）
- camera：相机焦点
"""
from __future__ import annotations

from . import composition, entrance as EN
from .constraint_solver import ConstraintSolver


def compile(dsl_ctx):
    """dsl_ctx = DSL.compile() 的产物。"""
    graph = dsl_ctx["graph"]
    rel = dsl_ctx["relations"]
    sg = dsl_ctx["states"]
    tl = dsl_ctx["timeline"]
    canvas = dsl_ctx["canvas"]

    # 1) 构图：显式 slot 已定位；未定位的 primary 居中
    composition.apply_default(graph, canvas)
    # 2) 若没有显式关系，按权重补构图关系（作为种子）
    if not rel.relations:
        for a, b, rtype in composition.auto_relations(graph):
            rel.add(a, b, rtype)
    # 3) 约束求解（root 级节点）
    solver = ConstraintSolver(graph, rel, canvas)
    boxes = solver.solve()
    _connectors(graph, rel)

    # 4) Entrance Plan（用 timeline 调度作为 start）
    schedule = {k: v for k, v in tl.schedule().items() if graph.has(k)}
    entrances = EN.build(graph, schedule=schedule)

    # 5) Motion Compiler：状态迁移 → 动画
    motions = {("%s->%s" % (t.frm, t.to)): t.to_motion() for t in dsl_ctx["transitions"]}

    # 6) 每个状态 → 一帧（关系在快照上重解，保证动态关系保持）
    frames = {}
    for name in sg.order:
        snap = sg.get(name).apply(graph)
        s2 = ConstraintSolver(snap, rel, canvas)
        s2.solve()
        _connectors(snap, rel)
        frames[name] = {"spec": _spec(snap), "boxes": _boxes(snap)}

    return {"scene_id": dsl_ctx["scene_id"], "canvas": canvas,
            "graph": graph, "relations": rel, "states": sg, "timeline": tl,
            "boxes": boxes, "entrances": entrances, "motions": motions,
            "frames": frames, "camera": dsl_ctx.get("camera_focus")}


def _spec(snap):
    from . import visual_runtime as VR
    return VR.to_spec(snap)


def _connectors(g, rel):
    """连接线端点随关系动态重算（A、B 位置变化 → arrow 端点自动更新）。"""
    for r in rel.relations:
        if r["type"] in ("point_to", "connect"):
            if g.has(r["a"]) and g.has(r["b"]):
                g.get(r["a"]).data["to"] = g.get(r["b"]).world_center()


def _boxes(snap):
    out = {}
    for n in snap.root.walk():
        if n.id == snap.root.id:
            continue
        out[n.id] = [round(v, 2) for v in n.world_box()]
    return out
