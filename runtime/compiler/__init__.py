"""compiler — Runtime 的几何层：意图 → 视觉 DSL → SVG。

Agent 不在这里。这里把 ``director`` 给的**语义意图**翻译成**可渲染几何**：

    composition   —— 意图 → 构图（语法 → 实现，1:N）
    constraints   —— 构图约束门禁（强调预算 / 元素数 / 画布 / 语法可画）
    layout        —— 构图求解（区域 / 槽位 / 留白）
    svg_compiler  —— 视觉 DSL → SVG / HTML
"""
from . import composition, constraints, layout, svg_compiler  # noqa: F401
from . import (anchor_layout, negative_space, visual_budget,  # noqa: F401
               composition_family, style_lock)

__all__ = ["composition", "constraints", "layout", "svg_compiler",
           "anchor_layout", "negative_space", "visual_budget",
           "composition_family", "style_lock"]
