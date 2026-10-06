# P2-2 执行层设计（v2）—— 从「动画编排器」到「状态执行器」

> 目标：让**语义变化**（增长/减少/转移/替换/累积）以**连续的视觉状态迁移**被执行，
> 而不是每拍独立排版 + 淡入淡出。
>
> 基线：`sangbiaolaoda-arch/srt-media-director` @ `4f67450`（META-0 完成后）。
> v2 变更：吸收 `P2-2 架构学习材料`（Manim / Motion Canvas / Rive / GSAP Flip /
> video-talkcraft / Anything2Explainer / teach-me / KimiK3Manim），并**先回答 §24 的
> A–J 十问**（全部基于对真实源码的勘察），再给设计。本文档为**设计**，不含实现改动。

---

## 0. 开工前必答：A–J 十问（代码级勘察结论）

> 方法：只读 `runtime/` 真实源码（含渲染器），不做推测。凡"结论"均可回指到具体函数。

### 勘察到的两条关键事实（决定了后面所有判断）

**事实①：渲染器今天已有"极窄的跨拍连续性"。**
`runtime/raster_renderer.py::draw_frame` 与 `runtime/html_adapter.py` 在拍首
`TRANS_SEC = 0.45` 秒内做两件事：
- **溶解**：`Image.blend(prev_img, cur_img, q)`（HTML 端 `drawImage` 叠旧帧）；
- **主体位置插值**：`overrides[cid] = _lerp_box(pp["boxes"][pel["id"]], plan_beat["boxes"][cid], q)`。

但"carried 实体"的匹配键是 **motif 字符串**：
`cur_motifs = {e.get("motif"): e["id"] for e in beat_dsl["elements"] if e["type"]=="motif"}`。
→ **只有 motif 参与 box 插值；文字/数字/图表都没有。** 且通道只有 `{x,y,w,h}`。

**事实②：元素 id 是"拍内唯一"，不是"跨拍恒等"。**
`runtime/visual_director.py` 一律生成为 `"%s_%s" % (bid, slot)`（如 `b2_hero`、`b3_hero`），
`decor` 为 `{bid}_decor{i}`，`bridge/panel_*/number` 同理；`carry_over` 在 `visual_director.py`
里被**硬编码输出为空数组** `"carry_over": []`。
→ **同一实体跨拍没有稳定键**；渲染器只能靠 motif 名"猜"连续性。

**事实③：值与状态不做跨拍插值。**
图表/数字在每拍用自己的 `chart.before/after/value` 与 `events`（`bars_grow`/`chart_fill`，
进度 `p` 在 0.9s 内 0→1）动画；`b3` 的柱子不会从 `b2` 的数值"长"过去，而是**重新长一次**。

### A–J 逐问速答

| # | 问题 | 结论 | 证据 |
|---|------|------|------|
| **A** | 哪个模块拥有 Entity Identity？ | **没有任何模块正式拥有。** Identity 是渲染器里"靠 motif 名偶然达成"的副作用；`visual_dsl` schema 有 element `id`，但它是拍作用域 `{bid}_{slot}`，不跨拍。 | `visual_director.py` id 生成；`raster_renderer.draw_frame` 的 `cur_motifs` |
| **B** | 哪个模块拥有 Visual State？ | **分层但都不完整。** 拍级"稳态"在 `runtime/contracts.py` 的 `end_state{visible,positions,hold_ms}`；元素级"可见态"在渲染器 `_state()` 的 `{alpha,dy,scale}`（由 entrance lifecycle 的 enter/exit 驱动）。**没有语义状态**（value/status/threshold）。 | `contracts.py` derive；`raster_renderer._state` |
| **C** | 哪个模块负责 State Delta？ | **没有。** `contracts.py` 只做相邻拍**校验**（`CARRY_NOT_IN_PREV`/`CARRY_POS_DRIFT`/`CUT_NO_DIFF` 等），不产出 Delta 对象；渲染器的 box 差值不是数据模型，是临时变量。 | `contracts.py` validate；`_lerp_box` 内联 |
| **D** | 当前 DSL 能否表达"同一实体跨 Beat 变化"？ | **基本不能。** `id` 拍作用域化；schema 虽定义 `carry_over[]`，但被输出为空、无 delta 语义；唯一隐式跨拍键是 `motif`。 | `visual-dsl.schema.json` + `visual_director.py` |
| **E** | entrance_plan 是否把 Transition 误当成 Entrance？ | **部分成立，且 Transition 被"劈成两半"。** entrance-plan 只有 enter/exit 生命周期；跨拍 `transition_in(carry|cut|dissolve)` 却活在 `contracts.py`。**Transition 从未作为一个独立计划存在。** | `entrance_planner.py`；`contracts.py` |
| **F** | composition planner 能否产出两状态间的 layout delta？ | **不能。** `plan_beat` 对每拍**独立求解**静态 boxes；没有 A→B 布局差分。渲染器只用 `_lerp_box` 对 carried **motif** 补了一个 0.45s 的窄特例。 | `composition_planner.plan_beat`；`draw_frame` |
| **G** | renderer 是否真正支持 A → B interpolation？ | **部分支持，且仅限 box + 仅限 motif。** 有 box 线性插值与溶解；但**没有 value/状态插值**，数字与柱体每拍自播自的。 | `draw_frame` / `_state` / `_draw_bars` |
| **H** | 哪些现有模块可复用？ | `contracts.py`（end_state/transition_in/校验框架，最接近落点）；`visual-dsl` 的 `id/slot/type/role/carry_over/motion_policy`；`motion_canonical` 词表；`primitive_states.v1` 动作契约与渲染器消费模式；`timeline` 的 span/easing；渲染器 `_lerp_box`/溶解机制。 | 各文件 |
| **I** | 哪些模块必须重构？ | ①identity（拍作用域 id → 稳定实体键）；②`render-plan.schema.json`（补 state/transition/identity/delta）；③把 **Transition 从 entrance-plan/contracts 里拆成独立计划**；④`contracts.py`（从"只校验"升级为"派生 Delta"）；⑤`composition_planner`（产出布局 delta）；⑥渲染器（从 box 插值升级为 value/状态插值）。 | — |
| **J** | 最小兼容方案？ | **纯加法**：新字段全部 `optional`；复用已有 `carry_over`/`motion_policy` 做开关；缺省时输出与 `4f67450` **逐字节一致**（保 golden 哈希）；新契约 `state_delta.v1` 独立版本化；回滚 = 删 delta 键即复原。 | 见 §6 |

> **一句话结论**：项目已具备"导演决策层"，但执行层的"视觉状态机"只长了一半——
> **有状态、有校验，却没有 Delta、没有 Identity、Transition 没有独立形态、渲染器只会插 box。**

---

## 1. 统一心智模型（学习材料的收敛）

所有被研究的项目都在回答同一件事："**世界发生了变化**"，只是分层不同：

```
Manim → Object Transform          Motion Canvas → State-driven
Rive  → State Machine             GSAP Flip     → Layout State Transition
video-talkcraft → Shot/Lifecycle  teach-me      → Render/Critic/Repair
KimiK3Manim → Supervisor/typed artifacts
```

收敛为本项目 P2-2 的目标数据流：

```
Semantic Event → Visual State → State Delta → Identity Matching
→ Transition Planning → Motion Grammar → Composition/Geometry
→ Motion Executor → Render → Machine/Pixel Evidence
→ Human/Vision Critic → Repair Router → Recompile
```

并贯彻四条**架构原则**（学习材料 §0/§12/§15/§20）：
1. **能表达成"同一实体状态变化"的，不允许默认实现成"删除+重建"。**
2. **State Delta ≠ Animation Plan**：Delta 描述"发生了什么变化"，不描述"用什么动画"。
3. **Motion Grammar 描述"意义"**（growth/decline/…），不是"特效菜单"（scaleUp+fadeIn）。
4. **不做"为了防静止而制造运动"**；该动才动，不该动不动（主体静止 + 相机极缓推进 > 全场浮动）。

---

## 2. 应修改的模块（含改动性质）

| 模块 | 现状 | P2-2 改动 | 性质 |
|------|------|-----------|------|
| **新增** `runtime/state_delta.py` | — | 最小 Delta 计算 + Identity Matching（纯函数，无副作用） | 新模块 |
| **新增** `contracts/state_delta.v1.json` | — | Delta 契约（单一真相源），声明 identity 规则 / delta 种类 / 连续性要求 | 新契约 |
| `runtime/contracts.py` | 派生 end_state/transition_in + 校验 | 新增 `derive_state_delta()`：把相邻拍差分**显式化为 Delta 列表**；校验增 delta 连续性规则（§4.4） | 扩展（不改签名） |
| `runtime/visual_director.py` | element id 拍作用域 `{bid}_{slot}`；`carry_over` 输出 `[]` | element 增**稳定 `identity`**（默认沿用现有 `id` 语义但提升为跨拍键）+ 可选 `state{value,status,…}`；`carry_over` 语义化为 carried⊆delta | 增量字段 |
| `runtime/composition_planner.py` | 每拍**独立**求解静态 boxes | 可选产出 **layout state A/B/delta**（reposition/reflow/resize/regroup/split/merge 的机器表达），carried 实体禁止无理由重排 | 约束增强（不引入新求解器） |
| `runtime/entrance_planner.py` → `motion_canonical/entrance.py` | 只有 enter/exit | **拆出独立 Transition Plan**；增 `continue` 与 `state-change` 分发 | 结构拆分 |
| `runtime/motion_canonical/vocabulary.py` | 45+ canonical actions | 增补 6 个**语义动作**：growth/decline/progression/contrast/causality/collapse | 新增条目 |
| `runtime/pipeline.py` | 串 Stage 3→6 | Stage 6 后**透传 `state_delta`** 到 render plan/receipt；per-beat feature flag | 编排接线 |
| `runtime/html_adapter.py` / `runtime/raster_renderer.py` | 已实现 draw/chart_fill/bars_grow/color_wash/pulse + 溶解 + **motif-only** box lerp | 实现新语义动作的**真实插值**（value/position/status），不再只插 box | 消费者补实现 |
| `schemas/render-plan.schema.json` | 无 state/transition/identity | 增加**可选** `state`/`state_delta`/`transition`/`identity` | schema 增字段 |
| `schemas/visual-dsl.schema.json` | element 无跨拍恒等 | 增加**可选** `identity`/`state`；`carry_over` 语义化 | schema 增字段 |

**不动**：`runtime/motion`、`runtime/motion_runtime`（motion_semantics.v2 已声明两者"not in production path"；作设计蓝本，PHASE 6 再 migrate/delete）。

---

## 3. 不足的 schema / contract（逐条）

1. **`render-plan.schema.json`**：beats[] 仅 `beat_id/start_sec/end_sec/strategy/boxes/fonts`，`boxes` 仅 `{x,y,w,h}`。**无 state / transition / identity / delta。**
2. **`visual-dsl.schema.json`**：element `id` 只保证**拍内唯一**；`carry_over[]` 是拍级数组、无 delta 语义；`motion_policy ∈ required/optional/hold` 已存在（可复用为开关）。**缺跨拍恒等键与 state。**
3. **entrance-plan**：只有 `MOTIONS_ENTER=("fade","rise","pop","inherit")` / `MOTIONS_EXIT=("fade","sink","shrink")`；**缺 `continue` / `state-change` 类目**，Transition 无合法形态。
4. **完全缺失 `state_delta` 契约**：未声明 identity matching 规则、允许的 delta 种类、连续性要求。
5. **渲染器契约不对称**：`primitive_states.v1` 定义的是**动作**（draw/chart_fill/bars_grow/color_wash/pulse），无法表达"同一实体从状态 A 到 B"；渲染器因此只能对 motif 的 box 做特例插值。

---

## 4. 新增最小数据结构（够用即止）

```python
# runtime/state_delta.py —— 纯数据，无渲染依赖

@dataclass
class EntityState:                     # 实体在某一拍的"稳态快照"
    entity_id: str                     # 跨拍稳定键（提升自 element id；默认 = 现有 id）
    visible: bool = True
    value: float | None = None         # 数值型语义（增长/减少的载体）
    position: tuple[float, float] | None = None   # 归一化中心 (cx, cy)，与 contracts._norm_pos 同口径
    scale: float = 1.0
    opacity: float = 1.0
    status: str | None = None          # 语义标签：normal/critical/loading/done/…

@dataclass
class StateDelta:                      # 一条"从→到"的语义变化（不是动画）
    entity_id: str
    kind: str                          # value | position | scale | opacity | status | visibility
    frm: float | str | bool | None
    to:  float | str | bool | None
    reason: str                        # 必填：无原因的变化被禁止

@dataclass
class IdentityMatch:                   # 跨拍配对的机器表示
    entity_id: str
    rule: str                          # same_id | transform | move(推断) | grow | shrink | split | merge
    confidence: float = 1.0

@dataclass
class Transition:                      # 相邻拍之间的迁移（升级 contracts.transition_in）
    from_beat: str
    to_beat: str
    type: str                          # carry | cut | dissolve | transform
    carried: list[str]
    deltas: list[StateDelta]
    motion_policy: str = "required"    # required | optional | hold（复用 visual-dsl 既有枚举）

@dataclass
class MotionSpec:                      # Transition 的可执行形态（喂给 motion_canonical）
    entity_id: str
    action: str                        # 语义动作：growth/decline/progression/contrast/causality/collapse/…
    channels: dict                     # {dx,dy,scale,opacity,emphasis,…}
    span: tuple[float, float]          # 绝对 [start, end]（沿用 timeline span 模型）
```

**设计约束**：全部**可选注入**（老数据行为不变）；`StateDelta.reason` 必填（沿用 `motion_runtime/states.py`
"任何状态变化都必须拥有原因"的原则）。

---

## 5. 数据流：State → Delta → Transition → Motion

```
SRT → beats ─Stage3─▶ visual-dsl{elements[id, type, role, identity?, state?]}   ← P2-2 新增
                          │
                       Stage4
                          ▼
              composition-planner{boxes + (可选 layout state A/B/delta)}
                          │
                       Stage6
                          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ runtime/state_delta.py                                       │
  │  1) EntityState[]   ← 每拍 elements+boxes 抽稳态              │
  │  2) IdentityMatch[] ← 相邻拍配对（same_id/transform/…）        │
  │  3) StateDelta[]    ← 逐实体差分（value/position/scale/status）│
  │  4) Transition      ← 分类 carry|cut|dissolve|transform+deltas │
  └───────────────┬───────────────────────────┬──────────────────┘
                  ▼                           ▼
      ┌───────────────────────┐   ┌──────────────────────────────┐
      │ MotionSpec 编译        │   │ contracts.validate()          │
      │ action+channels+span   │   │  + delta 连续性规则（§4.4）    │
      │ 经 motion_canonical    │   │  → PASS/FAIL + issues         │
      └──────────┬────────────┘   └──────────────────────────────┘
                 ▼
      ┌────────────────────────────────────────────┐
      │ html_adapter / raster_renderer             │
      │  按 channel 在 [start,end] 上连续插值       │
      │  （升级：value/status 也插，不再只插 box）  │
      └────────────────────────────────────────────┘
```

- **4.1 EntityState 抽取**：合并每拍 `elements`（有 `identity`）与 `boxes`。
- **4.2 Identity Matching（五级）**：`same_id` > `transform{from}` > `move`(位置近+同型) > `grow/shrink`(同 id、value 变且符号一致) > `split/merge`（Phase 2+）。**Phase-1 只落 same_id + transform。**
- **4.3 Delta→Transition 分类**：有 carried 且无 delta/全 0 → `carry`；有 carried 且有非零 delta → **`transform`（P2-2 核心）**；无 carried → `cut`；半透明交接 → `dissolve`。
- **4.4 contracts.validate() 新增规则**：

| code | 触发 | 说明 |
|------|------|------|
| `DELTA_NO_REASON` | `StateDelta.reason` 空 | 无原因变化禁止 |
| `DELTA_INSTANT` | `span` 跨帧 ≤ 1 | 迁移必须连续（不能一帧跳变） |
| `DELTA_DIRECTION_UNSIGNED` | value delta 无正负语义 | 增长≠减少必须可判 |
| `IDENTITY_FORGED` | carried 与上一拍 end_state 无 identity 对应 | 防"重新生成冒充连续" |
| `CARRY_REFLOW_UNREASONED` | carried 位置大变但无 transform delta | 防无理由重排 |

---

## 6. 与现有 pipeline 的兼容方案（最小、可回滚）

**总原则：Delta 是"加法"，不是"替换"。**

1. **字段可选出厂**：新字段全 `optional`；缺省时 `derive_state_delta()` 退化为现有"相邻拍差分"，`transition_in` 输出与今天**逐字节一致**（保护 golden 哈希）。
2. **identity 复用现有 `id`**：Phase-1 不新增键，只要求"跨拍同名 = 同实体"；需"换形"时才引入 `identity`（默认 = `id`）。
3. **per-beat 开关**：复用已有 `motion_policy ∈ required|optional|hold`；`hold` = 不做连续迁移（= 旧行为）。
4. **契约版本化**：新契约 `state_delta.v1.json` 独立；仅在 `motion_semantics.v2` 的 `categories` 里把已定义但未用的 `state`/`continue` **标注为"由 state_delta.v1 驱动"**。
5. **渲染器渐进**：`html_adapter`/`raster_renderer` 只新增语义动作分支，未命中走原路径；两渲染器一致性由 `primitive_states` 同款 producer/consumer 测试守护。
6. **回滚安全**：Phase-1 若不过，只需移除 `state_delta` 键与 flag，生产链路回到 `4f67450` 行为。

---

## 7. 第一批测试策略（六类，离线确定性）

> 输入为固定 DSL + render-plan fixture；全部可在 CI 跑。

1. **State Test**：`before ≠ after` —— 迁移前后至少一个通道改变（采样密度对齐 `motion_runtime/runtime.py::sample_frames` 的归一化关键帧）。
2. **Temporal Test**：变化跨 **≥2 帧**；`t0` 与 `t0+ε` 无变化，`t0+d/2` 出现中间态；禁 instant jump。
3. **Direction Test**：构造仅符号相反的一对 fixture，断言插值单调性相反、`MotionSpec.channels` 符号相反。
4. **Identity Test**：同 `identity` 跨 ≥2 拍，引用同一 id、不触发 `IDENTITY_FORGED`、`carried` 命中。
5. **Pixel Motion Test**：两采样帧像素差分，非背景区变化比例 > 阈值；**仅 fade 不能单独通过**（"fade ≠ motion"的机器化）。
6. **Continuity Test**：3 拍 carry 链，identity 在 1/2/3 拍一致，每对相邻拍 `type ∈ {carry,transform}` 且 `carried` 非空。

**位置建议**：`tests/phase0/test_state_delta.py`、`tests/phase0/test_motion_continuity.py`。

---

## 8. 第一批六类 Motion Grammar（只做这六种，别铺开）

| 动作 | 必须体现 | Runtime 自行决定 |
|------|----------|------------------|
| **growth** | 量增、范围扩、柱高升、曲线增长 | geometry/height 插值 |
| **decline** | 量减、范围缩、柱低、曲线降 | 同上反向 |
| **progression** | A→A'→A''→B 的推进（非 A fade / B fade） | 分步 span 序列 |
| **contrast** | A↔B 通过空间分离/方向相反/尺度差/局部强化 | 位置/尺度/emphasis |
| **causality** | A→关系建立→B（非同时出现） | connector 按进度绘制 |
| **collapse** | 外围→中心 / 大→小 / 复杂→结论 | scale/位置向心 |

> 明确**不做**：把 `growth` 写成 `scaleUp + fadeIn`（那就把"增长"退化成普通特效）。

---

## 9. 实施顺序（最小可证明闭环优先）

- **Phase 1（最小闭环，先做这个）**：`runtime/state_delta.py`（EntityState/Delta/Transition + same_id 匹配）→ contracts 派生 delta → **单实体、两状态**（如 `revenue_chart: value 30→70`）→ `growth` transition → 渲染 → **检查 t0/t_mid/t1 三帧**。目标：证明"语义变化已被编译成连续视觉变化"。
- **Phase 2**：render-plan / visual-dsl schema 增字段；`state_delta.v1.json`。
- **Phase 3**：motion_canonical 增 6 语义动作 + `MotionSpec` 编译。
- **Phase 4**：两渲染器实现**value/状态插值**（不再只插 box）。
- **Phase 5**：identity matching 扩到 transform/move/grow/shrink。
- **Phase 6**：六类测试全绿；golden 哈希不变；清理 `runtime/motion*` 遗留包。
- **Phase 7+**：split/merge、状态机（参考 `motion_runtime/states.py` 的 trigger/guard/rollback）。

**研发优先级（固定，学习材料 §22）**：
`Identity → Visual State → State Delta → Transition Planner → Semantic Motion Grammar → Motion Executor → Cross-beat Continuity → Temporal/Pixel Verification → Human Critic → Repair Loop → Second Renderer → 更多 motif/特效`

---

## 10. L4 不急于自动化：先建数据闭环

不要立刻造"审美 AI"。先建：

```
Real SRT → Render A → Render B → Human review → review-report.json → repair → Render C
```

记录 `case/beat/frame/dimension/severity/problem/repair/result`，尤其
`motion / continuity / hierarchy / composition / ppt_feeling / overall`。
先积累真数据，再考虑 Vision Critic。（对齐项目"信任模型天花板 / 无 ground truth"的已知短板。）

---

## 11. 吸收的"方法"（而非架构）

| 项目 | 吸收的单一思想 | 落到本项目 |
|------|----------------|-----------|
| Manim | 对象有状态，动画是状态间插值 | `EntityState` + `StateDelta`（§4） |
| Motion Canvas | State→Derived→Render；时间上是生成过程 | `state→derived→transition`（§5） |
| Rive | State / Input / Transition / Animation 分离 | `Transition` 独立计划（§2 E/I） |
| GSAP Flip | First-Last-Invert-Play：**布局差异即动画输入** | composition 产出 layout delta（§2 F） |
| video-talkcraft | 镜头生命周期 forming→resolved→hand-off→gone | 复用 `hold_ms`/`attention_path`；Anti-PPT 进入时域 |
| Anything2Explainer | 失败在"动画只发生入场" | 校验"是否有持续变化/跨多点/与语义一致"（§7） |
| teach-me | generate→render→observe→critic→repair | §10 人审闭环 |
| KimiK3Manim | Supervisor + typed artifacts；模型不控制全系统 | 坚持 Agent 说"为什么"/Runtime 管"怎么执行" |

---

## 12. 明确"不要走错的路"（学习材料 §15）

不要：堆更多 motion token／堆更多模板／所有元素持续 idle／每拍来一次新动画／
每次状态变化都 delete+recreate／Agent 直接写 renderer 动画代码／
用 `motion_count` 证明质量／用 `distinct_strategies` 证明好看／为防静止造无意义运动。

---

## 13. 附：需人工同步的过期文档（与设计分离）

- `docs/p2-1-final-audit.md` 仍含过期文案（"ENGINEERING BLOCKED ON JUDGE RE-SEAL"、
  "Do not start P2-2 until the seal passes"）——P2-1 应标为 **ACCEPTED**。
- `ROADMAP.md` 勾选需与真实代码对齐。

---

### 终局目标（学习材料 §最终）

Agent 输入"收入从 100 万增长到 150 万并突破警戒线"，不应输出 `fadeIn/scaleUp/slide`，
而应先形成 `Semantic Event: growth + threshold_crossing` →
`State A{revenue=100,status=normal}` / `State B{revenue=150,status=critical,threshold=crossed}` →
`Delta{value 100→150, bar 30→70, marker normal→critical, emphasis 0.3→1.0}` → `Transition{growth+threshold_crossing}`
→ Runtime 执行连续插值 → 渲染出 `frame A → intermediate → frame B`，而不是 `old screen → fade → new screen`。

> **不要让 Agent 学会"怎么做动画"，要让 Agent 和 Runtime 一起学会"一个视觉世界是如何从一个状态演化到另一个状态的"。**
