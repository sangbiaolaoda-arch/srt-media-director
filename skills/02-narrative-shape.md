# 02 · 叙事形状（Narrative Shape）

> 阶段产物：`beat-plan.json` 内的 `narrative_shape` 字段
> 上游：01-srt-and-beats · 下游：03-emphasis-and-encoding、04-visual-storytelling

## 1. 先回答五个问题

切完拍之后、设计任何画面之前，每拍必须能回答（Level 1 的导演问题）：

```text
这一拍在讲什么？
观众这一拍最后应该理解什么？
什么东西最值得看？
画面从什么状态变成什么状态？
下一拍从哪里接？
```

答不出第 2 条的拍是「配乐拍」——它不该进入信息图动画，应该被合并或删除。

## 2. 叙事功能 → 认知变化

- **NARR-01 [强制]** 每拍声明叙事功能（沿用 `semantic_role`），并给出对应的
  **认知变化类型**（narrative_shape.type）：

  | 叙事功能 | 认知变化类型 | 观众的变化 |
  |---|---|---|
  | hook | `open_loop` | 产生一个未闭合的问题 |
  | explanation | `establish` | 建立一个新的概念/事实 |
  | turning_point | `reverse` | 先前假设被翻转 |
  | comparison | `compare` | 同时看见两个对象并理解差异 |
  | emphasis | `reveal` | 注意力被压到一个关键信息上 |
  | conclusion | `land` | 问题闭合，得到可带走的结论 |

- **NARR-02 [强制]** 每拍填写状态四元组：
  `before_state`（画面开场是什么状态）→ `change`（发生了什么变化）→
  `after_state`（这一拍结束时的状态）→ `handoff`（交给下一拍什么）。
  这正是 CORE-18「状态变化优先于元素数量」的可执行形式。
- **NARR-03 [强制]** 每个普通 Beat 都必须产生**场景级的新鲜信息**。
  新鲜不等于新文件：可以是新视觉结构、新信息层、新转化状态或新自绘图形；
  但不能只是把旧元素换个位置（惰性复用检测见 `10-anti-ppt.md`）。
- **NARR-04 [经验]** 转折拍（reverse）的视觉重心应落在「翻转的瞬间」，
  而不是翻转前后的陈述；结论拍（land）允许 `motion_policy: hold`，
  但必须是有意识的收束，并在 pacing 中给出理由。

## 3. 与下游的接口

- `narrative_shape.type` 决定信息编码与策略的候选集：
  - `compare` → 优先考虑 `comparison` 策略（见 `06-composition.md`）；
  - `reveal` + 数字 → 优先考虑 `center_cluster`/`before_after`；
  - `establish`/`open_loop` → `single_focus`/`left_to_right_flow` 等基础策略。
- `handoff` 字段是 `07-choreography.md` 中交接设计（carry_over / hard_cut）
  的输入；本层只写语义意图（「把『手机』这个主体交给下一拍」），
  不写动画参数。

## 4. 反模式

- 每拍都是 establish → 全片平铺直叙，没有任何认知落差；
- 把 handoff 写成「淡出」（这是效果，不是意图）；
- before/after 填写了但画面中没有任何元素体现该状态变化——
  L4 语义审查会打回（见 `09-validation-repair.md`）。
