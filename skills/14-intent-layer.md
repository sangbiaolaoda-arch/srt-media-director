# 14 · 语义视觉意图层（Agent 不再「画画」）

> v7.3 新增。这一层解决的是「Agent 视觉决策能力太弱」——让它输出**语义意图**，
> 而不是**模板选择**。几何一律交给 Runtime。

## 核心分野

| 错误：模板选择器 | 正确：视觉意图 |
|---|---|
| `{"strategy": "cause_effect", "template": "left_to_right_flow", "hero_x": 300, "hero_y": 400}` | `{"visual_claim": "...", "grammar": ["accumulation","trajectory","threshold"], "focal_point": "trajectory", "relationship": [...], "density": 0.62, "silence": false, "motion_intent": "accumulate_then_reveal"}` |
| Agent 被训练成「选模板」 | Agent 表达「这句话该怎么被视觉化」 |
| 坐标泄漏进语义层 | 零坐标；坐标是 Runtime 的事 |

**判据**：意图 JSON 里一旦出现 `strategy` / `template` / `hero_x` / `x,y` 等键，
就是没在做导演。门禁 `G17` 用 `template_leak_keys()` 直接拒斥。

## 契约字段

| 字段 | 含义 | 约束 |
|---|---|---|
| `visual_claim` | 这一拍要观众相信/理解的一句话命题 | 非空字符串 |
| `grammar` | 抽象视觉语法操作（可组合） | 取自 `visual_grammar.GRAMMAR_OPS` |
| `focal_point` | 视觉焦点（唯一强调落点） | 必须是 `entities` 之一 |
| `relationship` | **关系图**（from/relation/to），不是列表 | 非空、每边三要素齐全 |
| `density` | 信息密度，决定 Runtime 放几个槽 | 0..1 |
| `silence` | 是否留白（少即是多） | 布尔 |
| `motion_intent` | 运动**意图**（语义，非缓动函数名） | 取自 `MOTION_INTENTS` |
| `entities`（可选） | 意图里的语义实体（名词节点，无坐标） | 字符串数组 |

## 编译链

```
Agent：intent_layer.derive_intent(beat)  →  视觉意图（零坐标）
                    │  validate_intent()（G17：拒斥模板泄漏）
                    ▼
Runtime：composition_compiler.compile_intent(intent)
                    │  grammar → 实现（1:N，按 density/silence 调参）
                    ▼
        ref_frame 规则（cols/rows/stroke/图标）→ 视觉 DSL（图层规范）
                    │  audit_spec()（框在画布内 / motion 合法 / 强调≤1）
                    ▼
                渲染 / 适配器
```

## 为什么「语法 → 实现」必须是 1:N

若写成 `grammar == 模板`，就只是把旧模板换了名字。真正解耦的是：

- **同一个语法**（如 `contrast`）可以由不同实现表达（双面板 / 前后叠化 / 并列柱）。
- **同一个实现**可服务多个语法（`nodes_row` 服务 causality / progression / hierarchy）。
- 编译器按 `density` / `silence` 决定**放几个槽**——这是 Runtime 的视觉语言，不是 Agent 指定的。

## 复现

```bash
python runtime/self_test.py          # 含 G17 意图层 + G18 编译器
python runtime/_build_intent_demo.py # 渲染「意图→构图」证据图
```
