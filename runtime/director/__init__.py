"""director — Agent 的视觉决策层（只产出语义意图，不产出几何）。

Agent 在这里回答「这句话该怎么被视觉化」，不回答「怎么画」。
几何一律交给 ``compiler`` 包。见 skills/14-intent-layer.md、15-runtime-architecture.md。

    visual_intent  —— 视觉意图（Visual Claim / Grammar / Focal / Relationship / Density
                      / Silence / Motion Intent），零坐标
    grammar        —— 抽象视觉语法词汇表
    relationship   —— 关系图（图，不是列表）
    critic         —— 机器视觉 Critic（截图 → 判分 → PASS/FAIL → 修复路由）
"""
from . import grammar, relationship, visual_intent, critic  # noqa: F401

__all__ = ["grammar", "relationship", "visual_intent", "critic"]
