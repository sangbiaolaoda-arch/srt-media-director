"""runtime/motion — 独立 Motion Compiler 子系统。

职责分离（本次架构改造的核心）：

    Agent            → Why / What        （Visual Claim / Grammar / Focal / Relationship）
    Visual Grammar   → 语义视觉语汇
    Composition      → Where / Size / Relationship
    Motion Planner   → When / How 进入 / 如何变化     ← 本包
    Renderer         → How to render
    Motion Validator → 每个可见元素是否都有明确 Motion Decision
    Visual Critic    → 实际上好不好

强制不变量：
  · 任何进入 RenderPlan 的可见元素都必须带 motion_policy。
  · motion_policy 缺失 ≠ static。缺失会被 Validator 拦下并自动补全；补全仍失败则 FAIL。
  · Agent 不需要输出 duration/delay/easing/keyframe —— 这些由本包依据语义自动生成。
  · 允许并鼓励显式 static（有些元素静止本身就是节奏）。
"""
from .motion_registry import (MOTION_PRIMITIVES, VALID_MOTIONS, register_motion,
                              primitive, is_valid_motion)
from .motion_planner import MotionPlanner, compile_plan, MOTION_POLICY_SCHEMA
from .validator import validate_motion, coverage, AntiPPTChecker
from .continuity import link_beats

__all__ = [
    "MOTION_PRIMITIVES", "VALID_MOTIONS", "register_motion", "primitive",
    "is_valid_motion", "MotionPlanner", "compile_plan", "MOTION_POLICY_SCHEMA",
    "validate_motion", "coverage", "AntiPPTChecker", "link_beats",
]
