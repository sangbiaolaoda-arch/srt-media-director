"""scene — 可编译视觉场景子系统（Phase 2）。

把「Agent 手写 HTML」升级为「Agent 编排 Visual DSL → 编译成稳定渲染」。

分层：
  scene_graph      结构 / 父子 / 变换继承
  relation_graph   语义关系（空间 / 结构 / 语义）
  constraint_solver 语义约束 → 像素
  state_graph      状态 + 迁移
  transitions      语义迁移 → 动画意图
  timeline         时间关系（before/after/with/stagger/...）
  entrance         统一 Entrance Plan（强制门禁）
  motion_compiler  语义动作 → 动画参数
  visual_weight    视觉权重 Primary/Secondary/Support/Decoration
  composition      构图约束
  dsl              Agent 面向的 Visual DSL
  render_plan      DSL → Render Plan（一键编译）
  visual_runtime   Render Plan → SVG / HTML
  validator        Machine Validator（§18）
  continuity       跨镜头连续性
"""
from . import (scene_graph, relation_graph, constraint_solver, motion_compiler,
               state_graph, transitions, timeline, entrance, visual_weight,
               composition, dsl, render_plan, visual_runtime, validator,
               continuity)

__all__ = ["scene_graph", "relation_graph", "constraint_solver",
           "motion_compiler", "state_graph", "transitions", "timeline",
           "entrance", "visual_weight", "composition", "dsl", "render_plan",
           "visual_runtime", "validator", "continuity"]
