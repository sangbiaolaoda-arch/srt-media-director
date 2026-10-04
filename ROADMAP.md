# Roadmap

方向只有一个：**让「导演决策」与「执行验证」的边界更清晰、更可携带**。
方法论层（skills/）保持稳定，执行层（runtime/）逐步扩充已验证的能力。

## v6.0 — 生成后契约与修复闭环（已完成）

把「静音信息图」最常见的失败（画面一闪而过、转场接不上、风格漂移、
构图撞车）补成机器保证，并给出可定位、可预算的修复路径。

- [x] 生成后契约 `runtime/contracts.py`：每拍 `end_state` +
      `transition_in`（carry / cut / dissolve 三类型机器检查）
- [x] 静音停留下限：`hold ≥ min(阅读时间, 本拍时长) × 0.22`，低于即阻断
- [x] 视线路径 `attention_path`（≤4，primary 必在）+ ambient 幅度/主元素约束
- [x] 反空话过滤：视觉命题禁「高级感/科技感/震撼/有张力」等
- [x] 风格锁定 `runtime/style_guard.py` + `style_tokens.json`：token 外颜色/
      线宽/字体即 FAIL
- [x] 节拍表 + 末帧联系表（`beat_sheet.py` / `lastframe.py`）：渲整片前先纸面评审
- [x] 故障→修复层路由 + 单变量重拍预算（`repair_routing.py` / `diagnose.py`）
- [x] 同拍断句粘连修复、短拍波次重排修复
- [x] `self_test.py` 门禁 8 → 12；黄金基准重生成

## v5.0 — 可信度地基（已完成）

把主观口号落成可验证事实，回应「先证明它真的能出好画面」。

- [x] 默认底色改米白纸感 `#F4EFE6`（`THEME` cinema→paper）+ 5 套情绪色板换浅底
- [x] 墨迹度量改主题无关高通法（修复浅底把渐变误判为内容）
- [x] 真实样例库 `examples/showcase/`：4 类内容成片 + GIF 预览（含 3m41s 长片）
- [x] 已知失败案例 `examples/known-failures/`（F01–F06）
- [x] 重复感量化门禁 `runtime/rep_metrics.py`（REP-*，接入 L2）
- [x] 黄金回归 `tests/golden/`（五层产物归一化哈希）
- [x] 真 CI 矩阵：Python 3.9–3.12 × Linux/macOS/Windows + 真徽章
- [x] 修复黄金测试抓到的跨进程不可复现（`semantic_grouper` 集合迭代序）

## v5.1 — 关系类型驱动的模板扩充（候选）

按「语义关系 × 构图模板」覆盖矩阵补齐，不凭感觉加模板：

- [ ] 关系类型清单：对比 / 因果链 / 层级 / 时间线 / 循环 / 前后变化 / 分类 /
      递进强化 / 让步转折 / 问答 / 枚举 / 单一主体
- [ ] 覆盖矩阵文档 `docs/relationship-template-matrix.md`
- [ ] 补模板：层级（树/嵌套）→ 时间线 → 让步转折 → 循环 → 分类
- [ ] 镜头运动目录 `docs/camera-motion-catalog.md`（pan / zoom / follow /
      focus / reveal）与交接方式（carry_over / transform / bridge）

## v5.2 — 第二渲染器与一致性契约（候选）

- [ ] 接 Remotion 或 HyperFrames 适配器，**复用同一份 visual-dsl**（接不通
      就说明 DSL 漏进了渲染器细节）
- [ ] 渲染器一致性契约：`render-plan` 层的时间/元素集/坐标断言（非像素比对）
- [ ] 适配器接口：`prepare / emit / probe`（probe 供契约自动核验）

## v5.3 — Agent 环节评测（候选）

- [ ] 分拍评测集 `evals/segmentation/`（10–20 份人工标注 SRT + 期望分拍）
- [ ] 指标：边界 F1 ≥ 0.85 / 拍数偏差 ≤ 15% / 硬约束违规 = 0 / 时长偏差 ≤ 1.2s
- [ ] 视觉命题评测 `evals/claim/`（L4 视觉模型初筛，**明确不替代人工**）
- [ ] 规则遵循度审计 `tools/rule_audit.py`（miss_rate > 20% 且无机器检查 →
      降级为建议）
- [ ] 精简入口 `SKILL-lite.md`（短视频 < 60s / < 15 拍）

## v5.4 — 产品化（候选）

- [ ] CJK 排版门禁 `TYPO-01`（避头尾 / 中英混排 / 字体回退 / 授权登记）
- [ ] 一条命令出 MP4（`make video`）+ 依赖锁版本
- [ ] `svglib` 纯 Python 兜底后端（当前 cairosvg → resvg → 明确降级）
- [ ] Schema 加 `$id` 版本号；打 release/tag；issue / PR 模板

## 适配器生态（长期，需 RFC）

- [ ] HyperFrames 适配器（`references/hyperframes-pitfalls.md` 先行）
- [ ] 素材库能力探针协议（Capability Probe）
- [ ] `camera_plan.json` 独立产物（当前 camera 意图嵌在 DSL beat 内）

## 验证深化（候选）

- [ ] L3 探针增加运动学检查：连续帧 diff，验证「有事件 ≠ 像素不变」
- [ ] `review-report.json` 结构化模板：把 L4 人工复核结论落成可追踪 JSON
- [ ] 跨拍连续性机器检查：carry_over 主体的视觉一致性抽样

## 明确不做（避免范围漂移）

- ❌ 实时编辑器 / GUI——本项目的交互界面是「SRT 进、播放器出」
- ❌ 与特定商业渲染 API 强耦合——中间语言必须保持可携带
- ❌ 自动化 L4（审美判断）——机器的归机器，人的归人（CORE-11）
- ❌ 视频理解 / 语音识别——输入永远是已经定稿的 SRT

## 贡献入口

想认领路线图条目：先开 Issue 引用本条目的编号与相关规则编号，
讨论清楚门禁设计（「机器怎么知道它做对了」）再动手。

- [x] SVG 画法库扩库：主体 motif 5 → 24（图表类 + 小物件类，全部非拟人）
- [x] 装饰附体 4 → 16（波形 / 散点 / 半调 / 交叉网格 / 螺旋 / 迷你柱 /
      标尺 / 加号阵 / 轨道 / 箭头链 / 里程碑 …）
- [x] 装饰受控随机：种子 = `md5(beat_id + narration)` + 4 拍冷却去重
- [x] 每拍 ≥3 个图形/图表/文字要素
- [x] 分段情绪背景调色板（night / warm / cold / tense / calm）
- [x] 工程配套：requirements.txt / pyproject.toml / Makefile / ARCHITECTURE.md

## v4.3 — 语义检索驱动分拍（已完成）

- [x] `runtime/semantic_grouper.py`：问答 / 让步 / 因果（硬约束）+
      蝉联 / 指代（软约束）
- [x] `beat_planner` 接入硬/软约束 + `HARD_CEIL = MAX_D × 1.75`
- [x] 导演层语义策略提示（问答/因果 → cause_effect，让步 → comparison）

## v4.2 — 视觉主题化（已完成）

- [x] cinema 暗色主题（渐变 / 暗角 / 颗粒 / 遮幅）
- [x] 衬线大字排版 + motif 水印化 + 金线替代描边框
- [x] v4.2.1 移除 corner_marks 画框（改由情绪调色板承担氛围）

## v5.0 — 适配器生态（候选，需 RFC）

- [ ] HyperFrames 适配器（references/hyperframes-pitfalls.md 先行：
      先沉淀踩坑，再写适配器）
- [ ] Remotion 适配器（React 生态用户）
- [ ] 素材库能力探针协议（Capability Probe）：素材可用性 → DSL 绑定决策
- [ ] `camera_plan.json` 独立产物（当前 camera 意图嵌在 DSL beat 内）

## 验证深化（候选）

- [ ] L3 探针增加运动学检查：连续帧 diff，验证「有事件 ≠ 像素不变」
- [ ] `review-report.json` 结构化模板：把 L4 人工复核结论落成可追踪 JSON
- [ ] `repair-log.json` 的 Runtime 自动草稿（修复循环时自动记录症状与层）
- [ ] 跨拍连续性机器检查：carry_over 主体的视觉一致性抽样

## 明确不做（避免范围漂移）

- ❌ 实时编辑器 / GUI——本项目的交互界面是「SRT 进、播放器出」
- ❌ 与特定商业渲染 API 强耦合——中间语言必须保持可携带
- ❌ 自动化 L4（审美判断）——机器的归机器，人的归人（CORE-11）
- ❌ 视频理解 / 语音识别——输入永远是已经定稿的 SRT

## 贡献入口

想认领路线图条目：先开 Issue 引用本条目的编号与相关规则编号，
讨论清楚门禁设计（「机器怎么知道它做对了」）再动手。
