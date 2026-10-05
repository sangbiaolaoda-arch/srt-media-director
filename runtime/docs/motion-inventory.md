# Motion Inventory — PHASE 1（MOTION UNIFICATION · P0）

> 本文件是 Motion 归一化（Runtime 三套并行运动系统去重）的**唯一审计基线**。
> 目标：Motion 只负责「状态如何随时间变化」，不得重复实现 Timeline（时间真相源）、
> Transform/Geometry（空间真相源）、Primitive（视觉对象真相源）。
> Observer 必须保持独立。迁移完成后删除旧实现，不接受长期兼容层堆积。

审计对象：`runtime/motion/`、`runtime/motion_runtime/`、`runtime/scene/`，
以及真实生产链 `runtime/entrance_planner.py` + `runtime/pipeline.py`。

审计基线 commit：`83230e5`（Composition 箱体语义归一，CI 全绿）。

---

## 0. 已有 Canonical 基础（本阶段要复用的单一真相源）

| 子系统 | 路径 | 单一真相源职责 |
|--------|------|----------------|
| Timeline / Easing | `runtime/timeline/easing.py`（+ `audit.py`、`legacy.py`） | 缓动曲线词汇表 + 纯时间参数化 `pr(t, start, end)` |
| Geometry / Transform | `runtime/geometry/matrix.py`、`box.py`（+ `audit.py`、`legacy.py`） | 2D 仿射变换 + 轴对齐世界箱体 |
| Primitive | `runtime/primitives/catalog.py`（+ `audit.py`、图元工厂） | 「存在哪些图元」的声明式真相源 |

> **关键结论**：Timeline / Geometry / Primitive 三层已经是唯一真相源（前几步已完成）。
> 三套 Motion 系统仍然**各自重复实现**了缓动、时间参数化、变换数学、原语词汇——
> 这正是本阶段要消除的重复。

---

## 1. 三套并行 Motion 系统 — 总览

| 系统 | 路径 | 文件数 | 代码行数 | 缓动来源 | 变换来源 | 原语词汇 | 生产链引用 |
|------|------|--------|----------|----------|----------|----------|-----------|
| **A. motion** | `runtime/motion/` | 12 | 1097 | 自带注册表 `easing` 字段（CSS 字符串，如 `cubic-bezier(...)`） | 自带（`render.py`） | `MOTION_PRIMITIVES`（24 项） | ❌ 仅 `_build_motion_tests.py`（开发工具） |
| **B. motion_runtime** | `runtime/motion_runtime/` | 14 | 2153 | `EASINGS` dict（9 个具名缓动 + 手写函数） | 自带 `scene.py`（`mat_mul`/`local_matrix`） | `PRIMITIVES`（22 项，大写） | ❌ 仅 `tests/motion_runtime/*` + `self_test.py` gate 21 |
| **C. scene** | `runtime/scene/` | 16 | 1511 | `BASE` dict 的 `ease` 字段（字符串） | 自带 `scene_graph.py`（`world_box`） | `BASE`（54 个语义动作） | ❌ 生产链不 import |
| **D. 生产链** | `runtime/entrance_planner.py` + `pipeline.py` | — | — | 字符串 motion 名，由 `html_adapter`/`raster_renderer` 解析 | `render_plan`/`visual_runtime` | `MOTIONS_ENTER`/`MOTIONS_EXIT` + `_WAVE` | ✅ 真实生产路径 |

> **核心症状（Production Chain Truth）**：`pipeline.py` 只 import
> `entrance_planner / composition_planner / contracts / html_adapter / srt_parser /
> validator / visual_director / beat_planner / style_guard`。
> **三套 Motion 系统全部游离在生产路径之外**，生产链自带第四套运动词汇。

---

## 2. 系统 A：`runtime/motion/`（1097 LOC）

| 文件 | LOC | 关键符号 | 职责 | 重复的真相源 |
|------|-----|----------|------|--------------|
| `__init__.py` | 29 | 包导出 | — | — |
| `motion_registry.py` | 180 | `MOTION_PRIMITIVES`(24)、`register_motion`、`primitive`、`is_valid_motion`、`supports` | 动画原语注册表（enter/relation/state/static/continue） | ⚠ **原语词汇**（与 B/C 重复）；`easing` 字段（与 timeline 重复） |
| `motion_planner.py` | 218 | `compile_plan`、`MotionPlanner` | 「选择什么动画」 | — |
| `sequencing.py` | 100 | 序列/节奏 | 时间关系 | ⚠ **时间参数化**（与 timeline、C.timeline 重复） |
| `render.py` | 173 | `render_frames`、`beat_html` | 原语 → CSS 关键帧 | ⚠ **变换/渲染**（与 geometry、raster_renderer 重复） |
| `semantics.py` | 80 | 语义解释 | 语义标签 | — |
| `state_change.py` | 24 | 状态变化 | 状态迁移 | ⚠ 与 `transition.py`、C.state_graph 重复 |
| `transition.py` | 24 | 过渡 | 状态迁移 | ⚠ 同上 |
| `entrance.py` | 36 | 入场 | 入场计划 | ⚠ **与 C.entrance、entrance_planner 三重复** |
| `continuity.py` | 56 | `link_beats` | 跨拍连续 | ⚠ **与 C.continuity 重复** |
| `validator.py` | 156 | `validate_motion`、`coverage`、`AntiPPTChecker` | 运动校验 | ⚠ 与 C.validator 重复（但 Observer 需独立——见 §7） |
| `motion_report.py` | 21 | `explain` | 报告 | — |

**使用者**：仅 `runtime/_build_motion_tests.py`（开发/测试脚手架），**不在生产路径**。

---

## 3. 系统 B：`runtime/motion_runtime/`（2153 LOC）

| 文件 | LOC | 关键符号 | 职责 | 重复的真相源 |
|------|-----|----------|------|--------------|
| `contracts.py` | 548 | `MotionContract`、`MotionPrimitive`、`PRIMITIVES`(22)、`PrimitiveDef`、`SceneCtx`、`CHANNELS`、`CHANNEL_NEUTRAL`、`EASINGS`(9)、`audit_contracts`、`make` | 运动原语契约 + 执行 | ⚠ **缓动**（`EASINGS` 与 timeline 重复）；⚠ **原语词汇**（22 项大写，与 A/C 重复） |
| `scene.py` | 169 | `Node`、`SceneGraph`、`mat_mul`、`mat_apply`、`local_matrix`、`nearby` | 场景图层级 + 变换 | ⚠ **变换数学**（与 geometry 重复）；⚠ 与 C.scene_graph 职责重复 |
| `relations.py` | 163 | `Relation`、`RelationRuntime`、`RELATION_TYPES`、`PHASES` | 关系运行时 | ⚠ 与 scene.relation_graph 重复 |
| `states.py` | 144 | `StateRuntime`、`StateTransition`、`STATES` | 状态图 | ⚠ 与 scene.state_graph 重复 |
| `conflict.py` | 150 | `ConflictSolver`、`Contribution`、`BLEND_MODES` | 运动冲突求解 | — |
| `connector.py` | 69 | `ConnectorRuntime`、`DynamicConnector` | 动态连接线 | — |
| `camera.py` | 92 | `Camera`、`attention_sequence` | 注意力 / 相机 | ⚠ 与 scene_graph 的 `LAYERS`(camera) 语义重叠 |
| `events.py` | 138 | `Event`、`EventGraph`、`dependency`、`parallel`、`sequence`、`stagger` | 事件 / 时间线图 | ⚠ **时间参数化**（与 timeline、C.timeline 重复） |
| `identity.py` | 75 | `IdentityRegistry`、`check_identity_continuity` | 稳定身份 | ⚠ 与 A/C.continuity 语义重叠 |
| `invariants.py` | 115 | `run_all` + 7 个不变量 | 运动不变量 | ⚠ 与 validator 语义重叠（Observer 独立性相关） |
| `runtime.py` | 137 | `MotionRuntime` | 执行系统集成 | — |
| `casebook.py` | 310 | `CASE_NAMES`、`build_case`、`check_case` | 用例册 | — |

**使用者**：`tests/motion_runtime/*`（5 个测试）、`self_test.py` gate 21。**不在生产路径**。

---

## 4. 系统 C：`runtime/scene/`（1511 LOC）

| 文件 | LOC | 关键符号 | 职责 | 重复的真相源 |
|------|-----|----------|------|--------------|
| `scene_graph.py` | 263 | `SceneNode`、`SceneGraph`、`WEIGHTS`、`LAYERS` | 场景图（父子/变换继承） | ⚠ **变换/箱体**（已部分委托 geometry——`5612ac0`）；⚠ 与 B.scene 重复 |
| `dsl.py` | 151 | Visual DSL | Agent 面向的 DSL | — |
| `visual_runtime.py` | 124 | Render Plan → SVG/HTML | 渲染 | ⚠ 与 raster_renderer/html_adapter 语义重叠 |
| `constraint_solver.py` | 116 | 语义约束 → 像素 | 布局求解 | — |
| `timeline.py` | 108 | `TimelineGraph`、`REL`、`schedule`、`audit` | 时间关系（before/after/with/stagger） | ⚠ **时间参数化**（与 timeline、B.events 重复） |
| `state_graph.py` | 108 | `State`、`StateGraph` | 状态 + 迁移 | ⚠ 与 B.states、A.state_change 重复 |
| `motion_compiler.py` | 95 | `BASE`(54)、`compile_action`、`compile_transition`、`SEMANTIC_ACTIONS` | 语义动作 → 动画参数 | ⚠ **缓动**（`ease` 字段）；⚠ **通道参数**（offset/scale/opacity 与 geometry 语义重叠）；⚠ 与 A.registry 原语词汇重叠 |
| `relation_graph.py` | 82 | 语义关系 | 关系 | ⚠ 与 B.relations 重复 |
| `render_plan.py` | 78 | DSL → Render Plan | 编译 | — |
| `validator.py` | 79 | `validate` | Machine Validator（§18） | ⚠ 与 A.validator 重复 |
| `entrance.py` | 71 | `make`、`build`、`audit`（REQUIRED 字段） | 入场门禁 | ⚠ **与 A.entrance、entrance_planner 三重复** |
| `continuity.py` | 44 | `carry`、`audit` | 跨镜头连续 | ⚠ **与 A.continuity 重复** |
| `transitions.py` | 61 | `Transition`、`VERBS`、`to_motion` | 语义迁移 → 动画意图 | ⚠ 与 A.transition/state_change 重复 |
| `visual_weight.py` | 46 | `WEIGHTS`、`STYLE`、`style_for`、`audit` | 视觉权重 | — |
| `composition.py` | 55 | 构图约束 | 构图 | — |

**使用者**：仅 scene 包内部；**生产链不 import**。

---

## 5. 系统 D：真实生产链

| 文件 | 关键符号 | 职责 | 与三套系统的关系 |
|------|----------|------|------------------|
| `runtime/entrance_planner.py` | `PHASES`、`MOTIONS_ENTER=("fade","rise","pop","inherit")`、`MOTIONS_EXIT=("fade","sink","shrink")`、`_WAVE`、`_build_lifecycle`、`_cues_from_lifecycle`、`_respace_cues`、`_interactions`、`plan`、`audit`(G1..G5) | 每元素生命周期 + 节奏 + handoff | **自带第四套运动词汇**；绕过 A/B/C |
| `runtime/pipeline.py` | `run()` → SRT→analysis→beat-plan→visual-plan→DSL→render-plan→entrance-plan→film/index.html→validation | 端到端编排 | 只 import `entrance_planner` 等，**不 import 任何 Motion 包** |

> 生产链的运动词汇（`fade/rise/pop/inherit/sink/shrink`）与
> `contracts/motion_projection.v1.json`（Observer 的 EXPECTED 侧）一致——
> 说明**真实被观测的运动词汇就是这一套**，而非 A/B/C 中的任何一套。

---

## 6. 缓动分歧量化（4 处独立实现）

| 来源 | 形式 | 具名曲线数 | 与 timeline 关系 |
|------|------|-----------|------------------|
| `runtime/timeline/easing.py` | **Canonical**：别名解析 + cubic-bezier 求解 + `pr(t)` | 20+ | 真相源 |
| `runtime/motion_runtime/contracts.py` | `EASINGS` dict（`ease_linear/in/out/in_out/out_cubic/...`） | 9 | ❌ 重复 |
| `runtime/motion/motion_registry.py` | 每个原语的 `easing` 字段（CSS 字符串） | 每原语 1 | ❌ 重复 |
| `runtime/scene/motion_compiler.py` | `BASE` 的 `ease` 字段（字符串） | 每动作 1 | ❌ 重复 |
| `entrance_planner.py` | 字符串 motion 名（由下游解析） | — | 隐式 |
| `contracts/motion_projection.v1.json` | `smoothstep` `t*t*(3-2*t)` | 1 | **Observer 独立**（不得合并） |

---

## 7. 同名 / 同语义重复清单（跨系统）

| 语义 | 系统 A (`motion/`) | 系统 B (`motion_runtime/`) | 系统 C (`scene/`) | Canonical 归属 |
|------|-------------------|---------------------------|-------------------|----------------|
| 入场计划 | `entrance.py` | — | `entrance.py` | **Motion Canonical**（`entrance_planner` 为生产消费者） |
| 跨拍连续 | `continuity.py` | `identity.py` | `continuity.py` | **Motion Canonical** |
| 状态迁移 | `state_change.py` + `transition.py` | `states.py` | `state_graph.py` + `transitions.py` | **Motion Canonical** |
| 时间/序列 | `sequencing.py` | `events.py` | `timeline.py` | **Timeline**（时间真相源）+ Motion 只声明关系 |
| 原语词汇 | `motion_registry.py`(24) | `contracts.py`(22) | `motion_compiler.py`(54) | **Primitive/Canonical Motion 词汇表**统一 |
| 变换数学 | `render.py` | `scene.py` | `scene_graph.py` | **Geometry** |
| 校验/不变量 | `validator.py` | `invariants.py` | `validator.py` | **Motion Canonical**（Observer 另有独立实现，见下） |

**Observer 独立性红线**：`runtime/observer/`（含 `motion.py`、`camera.py`、
`relation.py`、`temporal.py`、`timeline.py`、`projection.py`）及其契约
（`contracts/motion_projection.v1.json`、`temporal_projection.v1.json`、
`camera_projection.v1.json`、`relation_projection.v1.json`）**必须保持独立**，
不得 import 生产 Motion 内部实现，也不得被合并进 Canonical Motion。

---

## 8. Motion → Canonical / Adapter / Delete 映射表

| # | 现有实现 | 归属决策 | 目标 Canonical 面 | 处置 |
|---|----------|----------|-------------------|------|
| 1 | `motion/motion_registry.py::MOTION_PRIMITIVES` | **词汇统一** | `motion_canonical` 原语词汇表 | 迁移后 **Delete**（词汇并入 canonical 契约） |
| 2 | `motion_runtime/contracts.py::PRIMITIVES` | **词汇统一** | 同上 | 合并入 canonical 词汇；重复项 **Delete** |
| 3 | `scene/motion_compiler.py::BASE` | **词汇统一** | 同上 | 语义动作并入 canonical；`ease` 字段 **委托 timeline** |
| 4 | `motion_runtime/contracts.py::EASINGS` | **委托 Timeline** | `timeline.easing` | **Delete**（调用点改走 canonical easing） |
| 5 | `motion/motion_registry.py` 各 `easing` 字段 | **委托 Timeline** | `timeline.easing` | **Delete**（字符串改为 canonical 解析） |
| 6 | `scene/motion_compiler.py` 各 `ease` 字段 | **委托 Timeline** | `timeline.easing` | **Delete** |
| 7 | `scene/timeline.py::TimelineGraph` | **委托 Timeline** | `timeline` 时间真相源 | 保留语义 API，运算 **委托** timeline |
| 8 | `motion/sequencing.py` | **委托 Timeline** | `timeline` | 迁移后 **Delete** |
| 9 | `motion_runtime/events.py`（时间部分） | **委托 Timeline** | `timeline` | 事件图保留，时间运算 **委托** |
| 10 | `motion_runtime/scene.py::mat_mul/local_matrix` | **委托 Geometry** | `geometry.matrix` | **Delete**（改调 geometry） |
| 11 | `scene/scene_graph.py` 变换/箱体 | **委托 Geometry** | `geometry.matrix/box` | 已部分委托（`5612ac0`），余项 **委托** |
| 12 | `motion/render.py` 变换数学 | **委托 Geometry** | `geometry.matrix` | 保留渲染入口，变换 **委托** |
| 13 | `motion/entrance.py` + `scene/entrance.py` + `entrance_planner.py` | **入场统一** | `motion_canonical.entrance` | 收敛为**一个**入场实现，生产链消费之；旧两处 **Delete** |
| 14 | `motion/continuity.py` + `scene/continuity.py` + `motion_runtime/identity.py` | **连续统一** | `motion_canonical.continuity` | 收敛为一处；旧实现 **Delete** |
| 15 | `motion/state_change.py` + `motion/transition.py` + `scene/state_graph.py` + `scene/transitions.py` + `motion_runtime/states.py` | **状态迁移统一** | `motion_canonical.state_change` | 收敛为一处；旧实现 **Delete** |
| 16 | `motion/validator.py` + `scene/validator.py` + `motion_runtime/invariants.py` | **校验统一** | `motion_canonical.validate` | 收敛为一处；**Observer 独立实现不并入** |
| 17 | `motion/motion_planner.py`、`motion/render.py`、`motion/motion_report.py`、`motion/semantics.py` | **Motion 核心** | `motion_canonical`（选择 + 报告） | 迁移后按是否仍被引用决定 Retention/Delete |
| 18 | `motion_runtime/runtime.py`、`conflict.py`、`connector.py`、`camera.py`、`relations.py`、`casebook.py` | **Motion 核心/周边** | `motion_canonical` 或保留为 runtime 执行层 | 逐项评估；`casebook` 为测试册可 **Delete** |
| 19 | `scene/`（除已归一者） | **视觉编译域** | 与 Motion 解耦：时间→timeline、空间→geometry、原语→primitives | 保留 scene 编译域，仅去除重复的 Motion/时间/变换实现 |

---

## 9. 拟议 Canonical Motion API 面（PHASE 2 草案）

`runtime/motion_canonical/`（新包，唯一 Motion 真相源）：

```
motion_canonical/
  vocabulary.py     # 唯一语义动作 + 原语词汇表（合并 A/B/C，声明式）
  easing.py         # 薄委托 → timeline.easing（禁止自带曲线）
  progress.py       # 时间参数化：pr/进度/时长/延迟 → 委托 timeline
  transform.py      # 通道→变换：scale/opacity/offset/rotation → 委托 geometry
  sequencing.py     # cue/wave/stagger/overlap/before/after/with（时间语义 → timeline 求解）
  entrance.py       # 唯一 Entrance lifecycle（生产链消费）
  transition.py     # 唯一状态迁移
  continuity.py     # 唯一跨拍连续
  validate.py       # 唯一运动校验（Observer 另有独立实现，不复用）
  __init__.py       # 公共导出 + 门禁
```

**边界契约**：
- Motion 唯一输出：`{action, duration, easing_ref, delay, channels:{...}, targets}`。
- `easing_ref` / 时间量一律经 `timeline`；`channels` 的空间应用一律经 `geometry`；
  视觉对象标识一律经 `primitives.catalog`。
- 不得 import `motion/`、`motion_runtime/`、`scene/`（旧实现删除后天然成立）。

---

## 10. 后续 PHASE（本文件为 PHASE 1 交付）

| PHASE | 交付 | 状态 |
|-------|------|------|
| 1 | 本 inventory + 映射表 | ✅ 本次 |
| 2 | `runtime/motion_canonical/` 唯一 API | pending |
| 3 | 三套系统迁移到 canonical（适配层） | pending |
| 4 | `contracts/motion_semantics.v2.json` + `tests/phase0/test_motion_canonical.py` | pending |
| 5 | 生产链 3 showcase 验证（explanatory-tech / narrative-emotion / data-comparison） | pending |
| 6 | 删除旧实现 + 更新 import graph/docs | pending |
| 7 | 回归门禁 + Motion canonicalization gate | pending |

---

## 11. 关键风险与已知障碍

1. **生产链绕过**：`entrance_planner.py` 自带词汇，不 import 任何 Motion 包。
   → 需将 `entrance_planner` 收敛为 `motion_canonical.entrance` 的消费者（行为保持）。
2. **四处缓动**：timeline（canonical）、motion_runtime、motion、scene、entrance_planner、observer 契约。
   → 生产/非 observer 全部收敛到 timeline；**observer 的 `smoothstep` 保持独立**。
3. **Observer 独立性**：`runtime/observer/*` 及 4 个 projection 契约不得并入 Motion。
4. **无静默兜底**：不得为「已通过测试」而静默保留旧实现；所有分歧必须显式记录、显式删除。
5. **词汇表规模**：A(24) + B(22) + C(54) 三套词汇需人工合并出唯一集合，
   逐一裁定「保留/别名/删除」，避免简单并集造成语义膨胀。
