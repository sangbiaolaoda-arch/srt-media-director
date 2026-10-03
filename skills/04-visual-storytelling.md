# 04 · 视觉叙事与证据纪律（Visual Storytelling & Evidence）

> 阶段产物：`visual-plan.json` 的 `visual_claim` + `evidence`
> 上游：03-emphasis-and-encoding · 约束：CORE-05 / CORE-14 / CORE-16

## 1. Visual Claim：每拍一句话命题

- **CLAIM-01 [强制]** 每拍必须有一句 `visual_claim`：本拍画面让观众
  **看到/理解**什么。写不出命题的拍没有存在的理由（合并或删除）。
- **CLAIM-02 [强制]** 命题必须是**视觉命题**而非「复述字幕」。
  判据：把命题遮住、只看画面，观众能否得到这个理解？不能 → 退化为 PPT
  （`10-anti-ppt.md`）。

  | 旁白 | ❌ 复述型命题 | ✅ 视觉命题 |
  |---|---|---|
  | 「深度阅读时间占比只有 20%」 | 展示 20% 这个数字 | 让观众先看到大号 20%，再通过环形图理解它在整体中的占比之低 |
  | 「睡前把手机放到另一个房间」 | 显示「放下手机」四个字 | 给出可执行动作：用物理隔离（门—屏障—手机的空间关系）替代自律 |

- **CLAIM-03 [经验]** 命题与策略互相决定：对照命题 → `comparison`；
  占比命题 → `center_cluster`；变化命题 → `before_after`；因果命题 →
  `cause_effect`。命题先于模板（CORE-16）。

## 2. 证据纪律：三种推断类型

每个视觉声明必须标注它的推断类型（`evidence[].inference_type`）：

| 类型 | 含义 | 示例 |
|---|---|---|
| `literal` | 画面内容直接来自原文事实 | 环形图的 20% 来自原文「占比只有 20%」 |
| `semantic_abstraction` | 对原文关系的结构化抽象 | 把「睡前与醒来都是手机」抽象成因果链 |
| `visual_metaphor` | 导演加的隐喻，原文没有直说 | 用「屏障」图形表达「划出边界」 |

- **EVID-01 [强制]** `literal` 内容必须给出 `source_span` +
  `source_cue_ids`，可在 SRT 原文中定位。
- **EVID-02 [强制]** `semantic_abstraction` / `visual_metaphor` 必须显式
  标注类型——让观众和审查者知道这是导演加工，不是事实（CORE-05）。
  把隐喻伪装成事实 = 违反 CORE-14，等同编造。
- **EVID-03 [经验]** 一拍的证据链里隐喻占比不应过半；隐喻越多，
  L4 审查越要严格核对「它有没有误导观众对原文的理解」。

## 3. 状态转化（Visual Transformation）

- **TRANS-01 [强制]** 每拍定义画面级状态变化（承接 NARR-02 的四元组）：
  开场状态 → 变化 → 结束状态。变化可以是：元素关系建立（箭头连上）、
  属性改变（颜色语义洗入）、数值生长（图表填充）、主体位置/身份转换。
- **TRANS-02 [强制]** 纯淡入不算状态变化（CORE-10）。「所有元素 fade in
  然后静止」是反模式，不是设计。
- **TRANS-03 [经验]** 跨拍身份连续：同一主体（如「手机」）在相邻拍复用时，
  必须是有意的连续性设计（carry_over），而不是素材懒得换（CORE-24）。

## 3.5 主体形态纪律（v4.1）

- **FORM-01 [强制]** 主体词汇表**去拟人化**：文字、SVG 图形、图表都可以当
  画面主体；每拍主体只有一个（GATE-R1），但**主体与其他元素（含装饰附体）
  同时在场**——主体之下垫着圆环、点阵、刻度线等氛围层，不再是光秃秃的
  单元素画面。
- **FORM-02 [经验]** 具象图形优先走 `runtime/svg_art.py` 画法库（矢量、
  可审计、双侧渲染一致），不拟人、不依赖外部 PNG。

## 4. 镜头意图（Camera Intent）

- **CAM-01 [经验]** 默认静止镜头。`push_in` 只用于数字强调拍（把观众
  注意力压到关键数字上）；每次使用都要写 `reason`。
- **CAM-02 [强制]** 镜头语言属于全局语法（`05-global-grammar.md`），
  不得每拍发明新的镜头运动。

## 5. 产出契约（visual-plan.json 每拍字段）

```json
{
  "beat_id": "beat_05",
  "narration": "（原文）",
  "visual_claim": "让观众先看到 20% 这个关键数字……",
  "evidence": [{"source_span": "……", "source_cue_ids": [5],
                "inference_type": "literal"}],
  "strategy": "center_cluster",
  "emphasis_plan": {"primary_emphasis": "20%", "candidates": []},
  "information_encoding": {"type": "part_to_whole", "data_span": "20%"},
  "composition_thesis": {"reading_order": ["..."], "why": "……"},
  "motion_policy": "required",
  "camera_intent": {"mode": "push_in", "reason": "数字是该拍核心信息"}
}
```
