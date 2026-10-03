# 07 · 时序编排（Temporal Choreography：cue / 节奏 / 交接）

> 阶段产物：`entrance-plan.json`（含 lifecycle / cues / events / phases / pacing / handoff）
> 参考实现：`runtime/entrance_planner.py`
> 上游：06-composition · 约束：CORE-09 / CORE-10

## 1. cue 序列：语义顺序，而不是代码顺序

- **CHOR-01 [强制]** 元素入场编成 **cue 序列**（波次），顺序由语义决定：
  题头（eyebrow+title）→ 主体（图形/图表/因果框）→ 强调（关键词/数字）→
  注解波次。禁止按元素声明顺序往外蹦。
- **CHOR-02 [强制]** 同一 cue 内的元素**真同时**——`at` 值完全相同
  （门禁 `GATE-G1`）。「同时出现」不是大约同时。
- **CHOR-03 [强制]** 对比拍（comparison）的双方必须在**同一 cue** 揭示：
  对照关系的语义要求双方同时可见，先后出现会破坏「比较」这件事本身。

## 1.5 每元素生命周期（lifecycle，时序真值）

- **CHOR-11 [强制]** 每个元素都有独立的生命周期：
  `enter{at, motion, dur, after}` + `exit{at, motion, dur} | null`。
  **cue 序列只是 lifecycle 的派生视图**（同 `enter.at` 的元素编成一 cue）——
  改时序改 lifecycle，不改 cue。
- **CHOR-12 [强制]** `enter.after` 声明依赖：这个元素等谁建立之后才出现
  （回答「为什么这个时候出现、和前一个元素什么关系」）。例如 connector
  的 after 指向它连接的因果双方；强调词的 after 指向主体。
- **CHOR-13 [强制]** 入场 motion 词表：`fade` / `rise`（上浮 26px）/
  `pop`（0.55→1 缩放）/ `inherit`（**不重新入场**——交接主体
  专用，渲染器做跨拍位置插值）。退场 motion 词表：`fade` / `sink`（下沉
  34px）/ `shrink`（缩到 45%）。
- **CHOR-14 [强制]** 退场纪律：注解在 resolve（88%）淡出收束；非交接主体
  在拍尾（94%）下沉/收缩退场；**交接主体不退场**——
  结尾画面要干净（GATE-G5），但连续性元素不消失。

## 2. 阶段骨架（PHASES）

每拍时间轴按归一化比例划分为五个阶段：

```text
establish(0%) → enter(16%) → interact(45%) → emphasize(68%) → resolve(88%)
```

- **CHOR-04 [经验]** 波次默认锚点：top=5%、subject=16%、emphasis=42-55%、
  notes=60-66%、resolve=88%。可微调，但每拍最后一个有意义事件不得早于
  88%（见 GATE-G3）。
- **CHOR-05 [强制]** 每个事件必须承担至少一项工作：状态 / 关系 / 信息 /
  注意力 / 因果 / 连续性 / 镜头叙事（CORE-09）。入场即 fade 不算
  「interact」（CORE-10）。

## 3. 事件动作词汇表

参考实现支持的事件动作（renderer 双方都已实现）：

| action | 语义 | 典型目标 |
|---|---|---|
| `draw` | 连接线被画出来（关系建立） | connector |
| `chart_fill` | 环形图按比例填充（数值生长） | chart(donut) |
| `bars_grow` | 柱状图从 0 长到目标值 | chart(bars) |
| `pulse` | 短暂脉冲（注意力收束） | hosted 关键文本 |
| `color_wash` | 语义色从墨色洗入（属性改变） | 对照拍关键词 |
| `settle` | resolve 收束（无目标，标记拍尾） | — |

新增动作 = 扩展词汇表：必须同时在 PIL 渲染器与 HTML 适配器实现，
否则 L3 探针与播放画面不一致。

## 4. 节奏预算（Pacing Budget）

- **CHOR-06 [强制]** 每拍输出 pacing 指标：
  `first_meaningful_change_ratio`（首个有意义变化的位置）、
  `last_meaningful_event_ratio`（最后事件位置）、`idle_ratio`（尾段空窗占比）、
  `hold_reason`（有意识的静止必须给理由）。
- **CHOR-07 [经验]** 相邻波次间隔 ≥ 0.25s（`G_MIN_WAVE_GAP`，GATE-G2），
  否则观众感知不到「波次」，只有「一起出来」。

## 5. 交接（Handoff）

- **CHOR-08 [强制]** 每拍声明与下一拍的交接类型：
  - `carry_over`：主体跨拍延续（共享身份，如「手机」从拍 1 延续到拍 2），
    必须在 DSL 的 `carry_over` 字段给出 motif 与理由；
  - `hard_cut`：语义重置，必须写 `hard_cut_reason`；
  - `final_hold`：片尾收束。
- **CHOR-09 [强制]** 交接对着**下一拍**规划，不做单拍自闭环设计。
- **CHOR-10 [经验]** 连续性优先于特效：先回答「为什么 A 会变成 B」，
  再考虑具体动画效果。
- **CHOR-15 [强制]** 跨拍溶解：拍首 0.45s 内，上一拍末态（排除交接主体）
  溶解退出；交接主体（enter.motion=inherit）从上一拍位置插值滑动到新位置。
  PIL 渲染器与 HTML 播放器双侧同语义实现（raster `TRANS_SEC` = HTML `TRANS`）。

## 6. 编排门禁

| 门禁 | 规则 | 级别 |
|---|---|---|
| `GATE-G1` | cue 内元素真同时 | [强制] |
| `GATE-G2` | 波次间隔 ≥ 0.25s（G_MIN_WAVE_GAP） | [经验] |
| `GATE-G3` | `idle_ratio` ≤ 0.20（无 hold_reason 时） | [强制] |
| `GATE-G4` | 每拍必须声明 handoff | [强制] |
| `GATE-G5` | 生命周期完整：每元素有 enter；退场晚于入场；注解必退场；除非片尾收束、存在继承元素、或主体 carry_over 交接至下一拍（溶解过渡即动态），每拍至少一个元素退场 | [强制] |

## 7. 反模式

- 「所有元素一起出来 → 静止等待 → 下一镜重新开始」——G2/G3 会拦；
- 片尾 20% 时间没有任何事件也没有 hold_reason——G3 拦；
- 每拍都 carry_over 同一个主体但没有叙事理由——这是素材惰性
  （CORE-24），不是连续性设计。
