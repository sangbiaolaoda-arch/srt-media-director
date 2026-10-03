# Roadmap

方向只有一个：**让「导演决策」与「执行验证」的边界更清晰、更可携带**。
方法论层（skills/）保持稳定，执行层（runtime/）逐步扩充已验证的能力。

## v4.4 — 表达密度与去同质（已完成）

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
