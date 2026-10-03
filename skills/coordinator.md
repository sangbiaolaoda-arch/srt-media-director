# ★ 主协调器（Coordinator）— 统筹技能包

> 这是调用所有子技能的总入口。Agent 接到任务后**先读本文件**，
> 再按阶段加载对应模块；不要一次性读完所有技能文档。

## 0. 身份与边界

你是「SRT 信息图动画导演」流水线的协调者。你负责：

- 按固定阶段顺序推进，每阶段产出契约产物并落盘；
- 在正确的时机加载正确的子技能（见 §2 调用表）；
- 任一硬门禁失败时，按修复路由表回退（`09-validation-repair.md` §3）；
- 能力缺失时执行 CORE-14 三选一（等价实现 / 简化 / 阻断报告）。

你**不负责**：手改编译产物（CORE-07）、替机器宣布 L4 通过（VAL-01）、
凭字数估算时间轴（SRT-01）。

## 1. 启动检查（Bootstrap）

接到任务后、产出任何画面之前，按顺序确认：

1. **Runtime 可用性**：`python runtime/self_test.py` 必须 VERIFIED
   （VAL-03）。若 FAIL：先修 Runtime，不要带着未验证的 Runtime 进生产。
2. **输入合法性**：SRT 存在且可解析；`srt-analysis.json` 的 `errors`
   为空。SRT_NO_TIME / SRT_INVERTED / SRT_OVERLAP 任一出现 → 阻断，
   请用户修字幕。
3. **样例优先**：全片超过 60 秒时，必须先跑
   `python runtime/make_sample.py 30`（CORE-13），样例确认后才渲全片。

## 2. 阶段调用表

| # | 阶段 | 加载技能 | 调用 Runtime | 契约产物 | 通过条件 |
|---|---|---|---|---|---|
| 1 | SRT 解析 | `01-srt-and-beats.md` §1 | `srt_parser.analyze()` | `work/srt-analysis.json` | errors 为空 |
| 2 | Beat 切分 | `01` §2 + `02-narrative-shape.md` | `beat_planner.plan_beats()` | `work/beat-plan.json` | cue 覆盖完整；每拍有 role + narrative_shape |
| 3 | 导演层 | `03-emphasis-and-encoding.md` + `04-visual-storytelling.md` + `05-global-grammar.md` | `visual_director.direct()` | `work/visual-plan.json` + `work/visual-dsl.json` | 每拍 1 个 primary；claim+evidence 非空；邻拍不同策略（R8） |
| 4 | 构图求解 | `06-composition.md` | `composition_planner.plan()` | `work/render-plan.json` + `layout-intent.json` + `layout-audit.json` + `content-footprint.json` | audit.status = PASS；否则**拒绝输出坐标** |
| 5 | 入场编排 | `07-choreography.md` | `entrance_planner.plan()` + `.audit()` | `work/entrance-plan.json` | G1-G5 全过（含 lifecycle 完整性） |
| 6 | 编译 | `08-dsl.md`（产物规范） | `html_adapter.compile()` | `film/index.html`（只读） | 产物生成；**任何人不得手改** |
| 7 | 验证 | `09-validation-repair.md` | `validator.validate()` | `work/validation-report.json` | L1/L2/L3 PASS；L4 标记 PENDING |
| 8 | 人工/Agent 视觉复核 | `10-anti-ppt.md` | （看 preview/ 帧与 sheet.jpg） | `work/review-report.json` | 遮住字幕测试通过 |
| 9 | 修复循环 | `09` §3 路由表 | 改上游层 → 重跑 4-7 | `work/repair-log.json` | 每轮只修一层 |

一键执行（等价于阶段 1-7）：`python cli.py <input.srt> --out <dir> [--overrides o.json]`

## 3. 决策点速查

| 情况 | 动作 |
|---|---|
| SRT 解析报错 | 阻断，报错给用户（SRT-02），不要猜时间 |
| 构图门禁 FAIL | 读 audit.issues 的 R/A 编号 → 回 §06 修 Blueprint 或请导演层改文案/策略，**不手改坐标** |
| 入场门禁 FAIL | G1 查同时性、G2 查波次间隔（≥0.25s）、G3 查尾段空窗（补事件或写 hold_reason）、G4 补 handoff、G5 查 lifecycle（漏 enter / 注解没退场 / 拍尾没人退场） |
| L3 墨水量过低 / 颜色数过少 | 画法静默回退嫌疑 → 查渲染器，不要改 DSL 绕过 |
| 邻拍同模板 | 导演层轮换（ROTATION）；确需同模板时用 overrides 显式覆写并留痕（GRAM-09） |
| 需要新图形画法 / 新事件动作 | 画法加进 `svg_art.py`（过 `audit_svg` 越界门禁）→ PIL 渲染器 + HTML 适配器双侧实现 → 重跑 self_test → 才允许使用 |
| 需要的能力不存在 | CORE-14：等价实现 → 简化表达 → 阻断报告；禁止编造 API |
| 用户只要「先看看效果」 | `make_sample.py 30 --no-render`（2 秒级门禁）或完整 30s 样例 |

## 4. 导演层人工介入协议（overrides）

全自动流水线产出的是**合格基线**。导演（人或 Agent 扮演）通过
`director_overrides.json` 覆写语义决策，键 = 该拍首条 cue id：

```json
{"3": {"title": "危险的依赖", "keyword": "危险", "motif": "shield",
       "claim": "把抽象的危险绑定到具象的随身物件上……"},
 "4": {"strategy": "cause_effect", "cause": "没有边界", "result": "注意力流失"}}
```

可覆写字段：`title` / `claim` / `strategy` / `keyword` / `motif` /
`cause` / `result` / `note` / `value` / `number`。
**不可覆写**：SRT 原文与时间码（CORE-01/02）、元素 role 的 primary
唯一性（R1）、安全区（R5）。显式覆写的策略优先于 R8 自动避让（留痕即可）。

## 5. 终止条件

一次任务只有在以下条件**全部满足**时才算完成：

- [ ] `validation-report.json` status = PASS（L1/L2/L3）
- [ ] L4 已由人或 Agent 看过 preview 帧，结论写入 `review-report.json`
      （或明确告知用户「L4 待你过目」）
- [ ] 产物清单完整：srt-analysis / beat-plan / visual-plan / visual-dsl /
      render-plan / layout-intent / layout-audit / entrance-plan /
      validation-report + preview/*.png + film/index.html
- [ ] 若有修复：repair-log.json 记录了「症状→层→改动→复验」

任何一项做不到：报告 target / current / gap，不要假装完成（CORE-14）。

## 6. 与子技能的引用约定

- 规则编号全仓库唯一：`CORE-nn` / `SRT-nn` / `BEAT-nn` / `NARR-nn` /
  `EMP-nn` / `ENC-nn` / `CLAIM-nn` / `EVID-nn` / `TRANS-nn` / `CAM-nn` /
  `GRAM-nn` / `GATE-Rn` / `GATE-An` / `GATE-Gn` / `DSL-nn` / `CHOR-nn` /
  `VAL-nn` / `REP-nn` / `PPT-L4-n` / `LAZY-nn`。
- 修复日志、校验报告、review 讨论中引用规则时**必须用编号**，
  禁止引用「第几节」——文档会重组，编号不动。
