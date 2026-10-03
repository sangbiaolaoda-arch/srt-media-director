# 06 · 构图系统（Composition：Thesis → Blueprint → 求解 → 门禁）

> 阶段产物：`render-plan.json` + `layout-intent.json` + `content-footprint.json`
> + `layout-audit.json`
> 参考实现：`runtime/composition_planner.py`（`CP.plan(dsl)`）
> 约束：CORE-06 / CORE-20 / CORE-21 / CORE-23

## 1. 三层概念，各自只回答一个问题

| 概念 | 回答的问题 | 所在层 |
|---|---|---|
| **Composition Thesis** | 观众按什么顺序读这一拍？为什么？ | 导演层（visual-plan） |
| **Composition Blueprint** | 各 slot 分到哪块区域预算？ | 构图层（模板，归一化坐标） |
| **Layout Intent** | 本拍的对齐轴、阅读顺序、遮挡策略是什么？ | 构图层（layout-intent.json） |

原文档中三者职责曾互相重叠导致术语漂移；本版约定：**Thesis 管「读法」，
Blueprint 管「区域」，Intent 管「本次求解的约束声明」**，每个字段只回答
一个问题，不再互相借代。

## 2. 六套 Blueprint 模板

画布 1280×720，安全区 7%（`GATE-R5`）。模板以归一化区域定义 slot：

| 策略 | 区域骨架 | 适用命题 |
|---|---|---|
| `single_focus` | 居中主体 + 下方关键词 + 注脚 | 单概念强调 |
| `left_to_right_flow` | 左主体 → 箭头 → 右主体 + 注脚 | 流向/过程 |
| `cause_effect` | 左因（框）→ 箭头 → 右果（框）+ 注脚 | 因果 |
| `comparison` | 左右双面板（负/正柔色）+ 双方关键词与注脚 | 对照 |
| `center_cluster` | 居中环形图宿主 + 内嵌关键数字 + 注脚 | 占比（数字强调） |
| `before_after` | 居中双柱图 + 上方 delta 徽标 + 注脚 | 变化（数字强调） |

公共区：每拍顶部 `eyebrow`（编号+角色标签）与 `title`（小标题），
共享左对齐轴 x=0.07（对齐轴写进 layout-intent，供 L2 校验）。

**装饰附体层（v4.1；v4.2.1 起移除常驻画框）**：除模板元素外，每拍携带
2-3 个 `decor` 元素（`ring_pair` / `dot_grid` / `tick_line` / `divider`，
偶发**幽灵大字**——把关键词以特大号低透明度垫在主体之下）。
decor 元素自带归一化 `rect`、由导演层指定，**不参与模板区域预算**；
`role=ambient`，不计入安全区与碰撞门禁（DSL-03）。

## 3. 求解流程（一次算完，CORE-23）

1. **Content Footprint Preflight**：先用真实字体测量所有文本的实际尺寸
   （`measure_text`），再参与求解——禁止先摆位置后塞字。
2. **区域分配**：按策略模板把每个元素放进它的区域。
3. **精化**：文本按实测尺寸在区域内重新居中；图表取区域内切正方形。
4. **一次过门禁**（下一节）。任一硬门禁不过 →
   抛 `LayoutIntentIncomplete` **拒绝输出坐标**，由上游改 Blueprint/文案，
   而不是猜一个位置糊弄（CORE-06 的反向约束）。

## 4. 布局门禁

### R 级（[强制]，机器校验，写入 layout-audit.json）

| 门禁 | 规则 |
|---|---|
| `GATE-R1` | 单一视觉中心：每拍恰好 1 个 primary |
| `GATE-R2` | 文字不压图形（host 绑定除外——内嵌是有意设计） |
| `GATE-R3` | 注解互不重叠（同区域带的文本两两不撞） |
| `GATE-R4` | 注解不压主体（由 R2+R3 及区域分离联合保证） |
| `GATE-R5` | 非环境元素全部在安全区（7% 边距）内 |
| `GATE-R6` | 尺寸/位置对齐 8px 栅格（求解器取整） |
| `GATE-R7` | 墨留白：画面不为填满而填（与 L3 墨水量上限 0.65 呼应） |
| `GATE-R8` | 邻拍不同模板（GRAM-09） |

### A 级（[经验]，本次参考实现落地的两条）

| 门禁 | 规则 |
|---|---|
| `GATE-A15` | 焦点呼吸：primary 外圈 16px 呼吸环内不得有无关元素侵入 |
| `GATE-A19` | 尺度层级：分类型比较——primary 为文本时，其他文本不得用更大字号；primary 为图形/图表时，其面积不得小于 secondary 图形的 80%（其宿主豁免） |
| `GATE-A20` | 接近性（Gestalt proximity）：`bound_to` 关系对的中心距 ≤ 0.28 倍画布对角线——有关系才靠近，没关系才分开 |
| `GATE-A21` | 视觉平衡：主体级（primary/secondary）左右视觉重量比 ≥ 0.30，不得一边倒 |

## 5. 与导演层的接口

- 输入：`visual-dsl.json`（语义 slot + role，**无像素**，见 `08-dsl.md`）。
- 输出：`render-plan.json`（每元素精确像素盒子 + 字体），
  `content-footprint.json`（每个文本的实测尺寸，mode=measured/geometry/region）。
  `layout-intent.json` 附机器可读的构图质量事实：`whitespace_budget`
  （留白预算）、`proximity_pairs`（A20 实测距离）、`visual_balance`
  （A21 左右重量分布）。
- **构图层绝不修改叙事内容**：发现文本放不下时，抛错回上游，
  不擅自截断文案（CORE-08）。

## 6. 反模式

- 三层各自落位（主体硬居中、文字按语义带自摆、注解贪心找空位）——
  旧流程的「元素漂在纸上」，已被「一次算完」取代；
- 为通过门禁把文字缩小到不可读——门禁的意义是逼你改设计，不是逼你藏问题；
- 给模板加第 7 套「微调版」而不登记——模板即全局语法，新增必须进
  `global_visual_grammar` 并补 L2 门禁映射。
