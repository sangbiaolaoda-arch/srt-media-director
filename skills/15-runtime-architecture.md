# 15 · Runtime 目标架构（六包 + 生成-截图-评审-修复闭环）

> v7.4 新增。把 runtime 从「一堆平铺模块」重构为**职责清晰的六包**，并给出
> 用户要的那条闭环：`Agent → VisualIntent → Compiler → RenderPlan → HTML/SVG
> → 截图 → 检查 → 修复`。

## 目录结构（与目标架构一致）

```
runtime/
├── director/                 # Agent 的视觉决策层（只产语义意图，零坐标）
│   ├── visual_intent.py      # 视觉意图（Visual Claim/Grammar/Focal/Relationship/Density/Silence/Motion）
│   ├── grammar.py            # 抽象视觉语法词汇表
│   ├── relationship.py       # 关系图（图，不是列表）
│   └── critic.py             # 机器视觉 Critic：截图 + 规范 → 判决 + 修复路由
│
├── compiler/                 # Runtime 的几何层（意图 → 视觉 DSL → SVG）
│   ├── composition.py        # 意图 → 构图（语法 1:N 实现）
│   ├── constraints.py        # 构图约束门禁（强调预算 / 元素数 / 画布 / 语法可画）
│   ├── layout.py             # 构图求解（cols/rows 槽位 / 安全区）
│   └── svg_compiler.py       # 视觉 DSL → SVG / HTML
│
├── render/                   # 渲染层（多后端可降级）
│   ├── html_renderer.py      # DSL → 独立 HTML / SVG 文件
│   ├── playwright_renderer.py# Playwright（有则用，无则如实报不可用）
│   └── screenshot.py         # 自动选后端截帧：playwright > chromium(CLI) > cairosvg
│
├── validation/               # 渲染后校验层
│   ├── geometry.py           # 几何：框在画布内
│   ├── typography.py         # 字排：字号来自字阶
│   ├── safe_area.py          # 安全区：内容不越版心
│   └── visual_regression.py  # 光栅：墨量 / 与基线差异
│
├── primitives/               # 图元工厂（画法零件，函数化可复用）
│   ├── text.py  shape.py  path.py  chart.py  connector.py  motif.py
│
└── schemas/                  # 中间语言 JSON Schema（单一真值）
    ├── visual_intent.json  visual_plan.json  render_plan.json
```

`director_loop.py` 是顶层编排：把六包串成闭环。

## 核心闭环

```
Agent(intent)  →  director/
     │
     ▼
compiler/composition  →  DSL  →  compiler/constraints（编译期门禁）
     │
     ▼
render/svg_compiler  →  HTML/SVG
     │
     ▼
render/screenshot  →  PNG（真实光栅，多后端降级）
     │
     ▼
director/critic  →  判决
     ├── PASS → 下一个 Beat
     └── FAIL → route() 找上游层 → 修 intent/layout → 重新编译 → 重新截图
```

**修复路由**（§10：修复回到正确上游层）：

| 问题码 | 路由到 | 理由 |
|---|---|---|
| `CRITIC_OVERCROWDED` / `CRITIC_BLANK_FRAME` | `intent` | 太密/太空是语义决策 |
| `TYPO_*` | `intent` | 字号非词表 → 语义层 |
| `SAFE_*` / `GEO_*` | `layout` | 越界/越安全区 → 布局层 |
| `CRITIC_PNG_UNREADABLE` | `render` | 渲染问题 |

## 三条设计红线

1. **Agent 不画画。** `director` 只产语义意图；坐标是 `compiler` 的事。
   意图里出现 `strategy`/`template`/像素键 → 门禁 G17 拒斥。
2. **语法 ≠ 模板。** `grammar → 实现` 是 1:N（`compiler/composition`）；
   写成 `grammar == 模板` 就退化成模板选择器。
3. **能力如实报告。** `render/screenshot.backends()` 如实探测；没有 Playwright
   就降级 chromium/cairosvg，绝不假装有该能力。

## 复现

```bash
python runtime/self_test.py            # 含 G19（六包接线）+ G20（闭环 PASS + 修复路由）
python tools/_build_intent_demo.py   # 意图 → 构图 证据图
```

机器门禁：`G19` 断言六包与目标文件布局存在且跨包接线可用；`G20` 断言闭环
**真的渲染出 PNG 并 PASS**（真实证据），且问题码路由回正确上游层。
