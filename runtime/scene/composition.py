"""Composition Layer — 构图约束（Phase 2 · 第十二优先级）。

构图不交给 Agent 临时决定。权重 → 固定构图槽位：
Primary → center；Secondary → right_of Primary；Explanation → below Primary；
Supporting chart → opposite side。最终由 Constraint Solver 算像素。
"""
from __future__ import annotations

CONSTRAINTS = ("center", "top", "bottom", "left", "right", "diagonal",
               "split", "focus", "surround", "contrast", "balance",
               "negative_space")

# 画布九宫格槽位（归一化中心）
SLOTS = {
    "center": (0.50, 0.50), "top": (0.50, 0.20), "bottom": (0.50, 0.80),
    "left": (0.22, 0.50), "right": (0.78, 0.50),
    "top_left": (0.24, 0.26), "top_right": (0.76, 0.26),
    "bottom_left": (0.24, 0.74), "bottom_right": (0.76, 0.74),
    "opposite": (0.80, 0.72),
}


def place(node, slot, canvas=(680, 382)):
    cx, cy = SLOTS[slot]
    W, H = canvas
    node.set_pos(cx * W - node.w / 2.0, cy * H - node.h / 2.0)
    node.data["explicit_pos"] = True
    return node


def apply_default(graph, canvas=(680, 382)):
    """按权重套用基础构图：primary 居中，其余让关系求解器摆位。"""
    primaries = [n for n in graph.root.children if n.weight == "primary"]
    for n in primaries:
        place(n, "center", canvas)
    return graph


def auto_relations(graph):
    """按权重自动补构图关系（作为 Relation Graph 的种子）。"""
    primaries = [n for n in graph.root.children if n.weight == "primary"]
    if not primaries:
        return []
    anchor = primaries[0].id
    out = []
    for n in graph.root.children:
        if n.id == anchor:
            continue
        if n.weight == "secondary":
            out.append((n.id, anchor, "right_of"))
        elif n.weight == "support":
            out.append((n.id, anchor, "below"))
        elif n.weight == "decoration":
            out.append((n.id, anchor, "far"))
    return out
