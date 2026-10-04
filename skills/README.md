# skills/ — 模块技能导航

原 v3.0 单文档（约 6900 行）按主题拆分为 11 个可独立阅读的模块技能，
外加一个**主协调器**（`coordinator.md`）负责按顺序调用它们。

拆分原则：**一个模块只回答一类问题**。复杂度被完整保留——所有硬规则
都在——但每条规则只出现一次，并带有稳定编号（如 `CORE-03`、`GATE-R8`），
供其他模块交叉引用，不再出现原文档的编号重叠与版本残留。

## 阅读 / 调用顺序

| 序 | 模块 | 回答的问题 | 主要产物 |
|---|---|---|---|
| 0 | [00-core-contract.md](00-core-contract.md) | 什么规则永远不可违反？ | —（约束全部下游） |
| 1 | [01-srt-and-beats.md](01-srt-and-beats.md) | 时间真值是什么？拍怎么切？ | `srt-analysis.json` / `beat-plan.json` |
| 2 | [02-narrative-shape.md](02-narrative-shape.md) | 这一拍让观众发生什么认知变化？ | `narrative_shape`（beat-plan 内） |
| 3 | [03-emphasis-and-encoding.md](03-emphasis-and-encoding.md) | 什么最值得看？数字/关系如何编码？ | Emphasis Plan / Information Encoding |
| 4 | [04-visual-storytelling.md](04-visual-storytelling.md) | 画面主张什么？证据在哪？ | Visual Claim + Evidence |
| 5 | [05-global-grammar.md](05-global-grammar.md) | 全片统一的视觉语法是什么？ | Global Visual Grammar |
| 6 | [06-composition.md](06-composition.md) | 元素占据哪块空间、过哪些布局门禁？ | `render-plan.json` / `layout-intent.json` / `layout-audit.json` |
| 7 | [07-choreography.md](07-choreography.md) | 元素何时出现、拍与拍如何交接？ | `entrance-plan.json`（含 pacing / handoff） |
| 8 | [08-dsl.md](08-dsl.md) | 语义层的 Visual DSL 长什么样？ | `visual-dsl.json`（禁像素） |
| 9 | [09-validation-repair.md](09-validation-repair.md) | 如何分层验证？错了回哪一层修？ | `validation-report.json` / `repair-log.json` |
| 10 | [10-anti-ppt.md](10-anti-ppt.md) | 如何防止退化成「字幕 PPT」？ | 质量门禁清单 |
| ★ | [coordinator.md](coordinator.md) | **主协调器：什么时候调哪个模块、出错怎么办** | 端到端流水线 |

## 给 Agent 的用法

1. **先读 `coordinator.md`**。它是统筹技能包：定义了阶段顺序、每阶段
   必须满足的产出契约、失败时的回退路径。
2. 执行到某一阶段时，**只加载对应模块**（例如切拍阶段只读
   `01-srt-and-beats.md`），避免一次性加载全部规则造成上下文过载——
   这正是拆分的意义。
3. 遇到规则冲突时，编号小的模块优先；`00-core-contract.md` 高于一切。
4. 规则分三级：`[强制]`（机器门禁，CI 会拦）、`[经验]`（默认遵守，
   偏离要写明理由）、`[建议]`（参考）。只有 `[强制]` 级进入
   `runtime/self_test.py` 与 CI。

## 与 runtime/ 的关系

`skills/` 定义**为什么与做什么**（语义层），`runtime/` 实现**怎么算**
（坐标、碰撞、测量、编译、机器事实）。Agent 不猜像素，Runtime 不替
Agent 决定叙事。模块文档中引用的运行时入口（如 `composition_planner.plan()`）
均已在本仓库的参考实现中通过 `runtime/self_test.py` 12 道门禁验证。
