# 架构说明（ARCHITECTURE）

本文件回答一个问题：**这套东西由哪几层组成，数据如何流动，边界在哪。**
（`README.md` 讲怎么用，`skills/` 讲为什么这样做，本文件讲各部分如何拼装。）

## 一句话

```
SRT → 语义分拍 → 导演决策 → Visual DSL → 构图求解 → 入场编排
    → 光栅 / HTML 渲染 → 分层验证 → 局部修复 → 最终成片
```

Agent 负责**语义设计**（为什么、表达什么、关系、层级、时序、连续性）；
Runtime 负责**机器事实**（坐标、尺寸、碰撞、编译、渲染、验证）。
两者以中间产物（JSON）交接，不互相越界。

## 分层

| 层 | 目录 / 模块 | 职责 | 产物 |
|---|---|---|---|
| 方法论 | `skills/*.md` + `coordinator.md` | 规则、门禁、修复协议（语言无关） | 规范 |
| 时序真值 | `runtime/srt_parser.py` | SRT 解析、时间真值、数字/间隙检测 | `srt-analysis.json` |
| 语义分拍 | `runtime/semantic_grouper.py` + `beat_planner.py` | 语义检索（问答/让步/因果/蝉联/指代）+ 时长窗切拍 | `beat-plan.json` |
| 导演决策 | `runtime/visual_director.py` | 命题/强调/信息编码/策略/生命周期/motif/装饰/调色板 | `visual-plan.json` |
| 中间语言 | （`visual-dsl.json`） | 语义方位与关系，禁像素 | `visual-dsl.json` |
| 构图求解 | `runtime/composition_planner.py` | 区域预算、分组、落位、门禁 R1–R8 / A20 / A21 | `render-plan.json` / `layout-intent.json` / `layout-audit.json` |
| 入场编排 | `runtime/entrance_planner.py` | cue 序列、每元素 enter/exit/after、跨拍 handoff | `entrance-plan.json` |
| 渲染层 | `runtime/raster_renderer.py` / `html_adapter.py` | PIL 探针帧 / 可交互 HTML 播放器（同一份 SVG 画法） | `preview/*.png` / `film/index.html` |
| 画法库 | `runtime/svg_art.py` | 非拟人 SVG 画法（motif + decor）+ 越界审计 + 光栅化 | data-URL / PNG |
| 验证 | `runtime/validator.py` + `self_test.py` | L1 机器 / L3 光栅探针 / 12 道门禁 | `validation-report.json` |
| 编排 | `runtime/pipeline.py` / `cli.py` | 串联全链路 | 全套产物 |

## 数据流（不可逆）

```
srt-analysis.json  ──►  beat-plan.json  ──►  visual-plan.json  ──►  visual-dsl.json
                                             │
                          composition_planner（一次算完三层）
                                             ▼
                        render-plan.json + layout-intent.json + layout-audit.json
                                             │
                       entrance_planner ─────┤
                                             ▼
                                 entrance-plan.json
                                             │
                        raster / html 渲染 ──┤
                                             ▼
                        validation-report.json（L1/L2/L3）
```

## 三条不可动摇的边界

1. **SRT 是唯一时间真值。** 任何层不得按字数重新估算正式时间轴。
2. **DSL 里没有像素。** 导演层只给语义方位与关系；坐标由构图层算。
3. **修复回正确上游。** 语义错→分拍；视觉设计错→导演；坐标/碰撞错→构图；
   渲染错→渲染器。绝不手改生成物（`film/index.html` 视为只读编译产物）。

## 可复现性

- 装饰的受控随机以 `md5(beat_id + narration)` 为种子 → 同一输入任何机器产出一致。
- 光栅探针帧与 HTML 播放器共用同一 `svg_art` 画法与同一 `palette` →
  「机器看的帧」与「人看的画面」是同一幅画。

## 能力探测（诚实边界）

缺某模块时，实现**不得假装具备能力**：只有三种合法动作——
找到已验证的等价实现 → 简化表达 → 阻断并报告。
`runtime/self_test.py` 的 12 道门禁即是这条纪律的机器化。
