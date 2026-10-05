# 17 — 场景编译层（Scene Compiler，Phase 2）

把「Agent 手写 HTML」升级为「Agent 编排一个可编译的视觉场景」。
Agent 只决定**画什么 / 为什么 / 关系 / 如何变化**；Runtime 决定**如何稳定渲染**。

## 编译链

```
SRT → Semantic Director → Scene Graph → Relation Graph → State Graph
    → Timeline Graph → Render Plan → Constraint Solver → Motion Compiler
    → Visual Runtime → HTML / SVG → Playwright → Visual Validation → MP4
```

## 模块（runtime/scene/）

| 模块 | 职责 | 对应阶段 |
|---|---|---|
| `scene_graph.py` | 结构/父子/变换继承（position/scale/rotation/opacity/visibility） | Phase 1 |
| `relation_graph.py` | 语义关系（left_of/right_of/above/below/inside/surround/attach_to/connect/point_to/follow/contrast/cause/result/...） | Phase 2 |
| `state_graph.py` | State + Transition（show/hide/expand/collapse/transform） | Phase 3 |
| `transitions.py` | 语义迁移动词 → 动画意图 | Phase 4 |
| `timeline.py` | before/after/with/overlap/delay/stagger/follow 调度 | Phase 4 |
| `entrance.py` | 统一 Entrance Plan（强制门禁，缺一即拦） | §7 |
| `motion_compiler.py` | 语义动作 → position/scale/opacity/rotation/delay/duration/easing | Phase 5 |
| `constraint_solver.py` | 语义约束 → 像素（center/right_of/above/below/surround/between...） | Phase 6 |
| `visual_weight.py` | Primary/Secondary/Support/Decoration 自动分档 | §11 |
| `composition.py` | 基础构图约束（center/split/focus/...） | §12 |
| `dsl.py` | Agent 面向的 Visual DSL | §16 |
| `render_plan.py` | DSL → Render Plan（一键编译） | 编译链 |
| `visual_runtime.py` | Render Plan → 真实 SVG / HTML | Phase 7 |
| `validator.py` | Machine Validator（渲染前拦错） | §18 |
| `continuity.py` | 跨镜头连续性（变化优先于重建） | §19 |

## Visual DSL 示例

```python
from scene import dsl, render_plan, validator

d = dsl.scene("choice_overload")
person  = d.group("person").at("center").weight("primary")
choices = d.group("choices").weight("secondary")
choices.child("chip", "c1", w=70, h=40)
d.surround(choices, person)
d.state("start").show("person").show("c1")
d.state("overload").expand("choices", 4)
d.transition("start", "overload").expand(choices).stagger(choices)
d.enter("person", action="slide", duration=0.5)
d.enter("choices", action="surround", after="person", duration=0.6)
d.camera().focus(person)

plan = render_plan.compile(d.compile())     # → boxes / entrances / motions / frames
assert validator.validate(plan)["status"] == "PASS"
```

Agent 侧**不写** x/y、不写 CSS animation、不写 transform matrix。

## 验证

- 独立套件：`python3 runtime/scene_test.py`
- 端到端：`python3 examples/phase2_scene_demo.py`（真实 SRT 镜头 → DSL → 编译 → Playwright 截图 → Validator → 8 条验收）
- 回归：`python3 runtime/self_test.py`（20/20）、`python3 runtime/spec_test.py`（35/35）

## 两条红线

1. **父子关系**（Scene Graph）解决「谁属于谁」——结构、继承、Transform。
2. **语义关系**（Relation Graph）解决「谁和谁有什么意义上的关系」——空间、因果、动态。

二者不可混淆，共同决定最终视觉；关系变化时（父移动、锚点移动）由 Constraint Solver 重算，连接线端点自动更新。
