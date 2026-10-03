# 08 · Visual DSL 规范

> 阶段产物：`visual-dsl.json`
> 约束：CORE-06（导演层禁止像素）· schema：`schemas/visual-dsl.schema.json`

## 1. DSL 的定位

Visual DSL 是导演层与执行层之间的**中间语言**：语义完备（足以表达
命题、层级、关系、时序意图），但不包含任何像素坐标。坐标由构图层
求解（`06-composition.md`），时序参数由编排层求解（`07-choreography.md`）。

```text
Agent：为什么、表达什么、视觉重点、关系、层级、时序、连续性
Runtime：坐标、尺寸、碰撞、测量、编译、渲染、机器事实
```

## 2. 元素（Element）

```json
{
  "id": "b05_number",
  "slot": "number",
  "type": "text | shape | motif | chart | connector | decor",
  "role": "primary | secondary | support | ambient",
  "text": "20%",
  "size": "eyebrow | note | label | keyword | display_small | word | number",
  "color_role": "negative | positive | info | neutral | ink",
  "emphasis": true,
  "host": "b05_hero"
}
```

- **DSL-01 [强制]** `id` 全片唯一，命名约定 `<拍短码>_<slot>`
  （如 `b03_keyword`）——跨层引用（host / relations / cues / events）
  全部依赖它。
- **DSL-02 [强制]** `slot` 必须是构图模板中存在的区域名；DSL 中出现
  模板没有的 slot，构图层会抛 `LayoutIntentIncomplete`（这正是设计：
  不允许编一个没预算过位置的新区域）。
- **DSL-03 [强制]** `role` 四值语义：
  `primary`（每拍恰好 1 个，GATE-R1）· `secondary`（≤2）·
  `support`（标题/注脚）· `ambient`（面板等氛围层，不计入安全区与碰撞）。
- **DSL-04 [强制]** `host` 表达「归属」关系：被强调元素绑定到图形/图表
  宿主（EMP-05）。host 必须引用同拍存在的元素 id（L1 校验
  `HOST_MISSING`）。

### 元素类型语义

| type | 含义 | 关键字段 |
|---|---|---|
| `text` | 文本（标题/关键词/数字/注脚） | `text` `size` `boxed` |
| `shape` | 氛围面板 | `tone`（negative_soft/positive_soft） |
| `motif` | 具象图形（**非拟人**，SVG 画法库） | `motif`（phone/moon/shield/clock/alert）+ `art`（画法名，缺省=motif） |
| `chart` | 数据图表 | `chart.kind`（donut: value / bars: before+after） |
| `connector` | 关系连接 | `connector`（arrow） |
| `decor` | 装饰附体（氛围层，role=ambient） | `art`（ring_pair/dot_grid/tick_line/divider，每拍 1-2 件策略相关）+ `rect`（自带归一化区域）；幽灵大字变体只有 `text` 无 `art` |

**Asset-blind**：DSL 只声明「要什么」，不声明「用哪张图」。
素材决策在更下游，且只有连续性理由才能复用（CORE-04 / CORE-24）。

## 3. 关系（Relation）

```json
{"from": "b05_number", "to": "b05_hero", "type": "bound_to"}
```

- **DSL-05 [强制]** 关系词汇表即全局语法（GRAM-05）：
  `causes` / `flow_to` / `contrast`（由双面板表达，不必显式连线）/
  `bound_to`。from/to 必须指向同拍元素（L1 校验 `RELATION_DANGLING`）。
- **DSL-06 [经验]** 没有关系的一拍通常意味着它只是「元素陈列」——
  回到 `04-visual-storytelling.md` 重新想命题。

## 4. 拍级字段

```json
{
  "beat_id": "beat_05", "narration": "（该拍 SRT 原文，用于播放器字幕条）",
  "start_sec": 18.0, "end_sec": 23.0,
  "strategy": "center_cluster",
  "motion_policy": "required",
  "visual_claim": "……",
  "elements": [], "relations": [],
  "camera": {"mode": "push_in", "reason": "数字是该拍核心信息"},
  "carry_over": [{"element_motif": "phone", "reason": "shared_identity_continuity"}]
}
```

- **DSL-07 [强制]** `start_sec/end_sec` 原样来自 beat-plan，下游不得
  修改（SRT-01）。
- **DSL-08 [强制]** `camera` 默认 static；非 static 必须有 reason（CAM-01）。

## 5. 禁止事项

- ❌ 任何 x/y/w/h 像素值出现在 DSL 中（CORE-06）；
- ❌ 在 DSL 里写动画时长/缓动参数（那是 `07-choreography.md` 的职责）；
- ❌ 为绕过模板限制而新增「自由 slot」——先扩展 Blueprint（06）并过门禁；
- ❌ 把编译产物（film/index.html）当 DSL 改（CORE-07）。
