# 16 — 行为规范（视觉导演 + 编译器，42 条）

本模块把用户提供的 42 条「视觉导演 + 编译器」规范固化为**可机器门禁**的
行为契约。每一条都有稳定编号 `R00..R42`，并与运行时代码一一对应：能算的
就进 `runtime/spec_audit.py` 注册表，由 `runtime/spec_test.py` 独立验证。

> 与 `00-core-contract.md` 的关系：`00` 是「永不可违反」的底线；本模块是
> 从「生成画面」升级到「导演 + 编译」的**增量行为规范**，`[强制]` 级规则
> 进入 `spec_test.py`（独立于 `self_test.py`，避免扰动已有 20 道门禁）。

## 分层

- `[强制]` 机器门禁：`spec_audit.run_all()` 会拦，`spec_test.py` 逐条证明。
- `[经验]` 默认遵守，偏离需写明理由（如参考帧 vs 构图族取舍）。
- `[建议]` 参考。

## 规则表（R00–R42）

| 编号 | 规则 | 实现 | 级别 |
|---|---|---|---|
| R00 | 导演思维，非模板化生成 | 全局 | 经验 |
| R01 | 先有布局意图再分配像素 | `composition_planner.plan` | 强制 |
| R02 | 语义约束→像素求解 | `compiler/anchor_layout.py::solve` | 强制 |
| R03 | 禁止裸绝对坐标 | `compiler/anchor_layout.py::rejects_raw_coordinates` | 强制 |
| R04 | 同输入同输出（可复现） | 全局 | 强制 |
| R05 | 视觉权重层级 P0..P3 | `director/hierarchy.py::audit_hierarchy` | 强制 |
| R06 | 装饰不得压过主体 | `director/hierarchy.py::audit_hierarchy` | 强制 |
| R07 | 实体级连续性（默认 PERSIST） | `director/continuity_graph.py::audit_continuity` | 强制 |
| R08 | 状态变化优于硬替换 | `director/continuity_graph.py::persist_ratio` | 经验 |
| R09 | 图元注册表 | `primitives/` | 强制 |
| R10 | 关系必须显式类型化 | `director/relationship.py` | 强制 |
| R11 | 语义锚点定位 | `compiler/anchor_layout.py::anchor_xy` | 强制 |
| R12 | 邻近成组 | `composition_planner._proximity_pairs` | 经验 |
| R13 | 视觉平衡检查 | `composition_planner._visual_balance` | 经验 |
| R14 | 动机（motif）复用优先 | `compiler/style_lock.py::reuse_decision` | 经验 |
| R15 | 锚点/关系/距离→像素 | `compiler/anchor_layout.py::solve` | 强制 |
| R16 | 关系图求解 | `compiler/anchor_layout.py::solve` | 强制 |
| R17 | 负空间/密度纪律 | `compiler/negative_space.py::audit_negative_space` | 强制 |
| R18 | 视觉预算（时长×密度→复杂度） | `compiler/visual_budget.py::audit_budget` | 强制 |
| R19 | 复杂度分档 | `compiler/visual_budget.py::tier_for` | 强制 |
| R20 | 安全区约束 | `validation/safe_area.py` | 强制 |
| R21 | 几何（不重叠/不出界） | `validation/geometry.py` | 强制 |
| R22 | 排版规则 | `validation/typography.py` | 强制 |
| R23 | 视觉回归对比 | `validation/visual_regression.py` | 强制 |
| R24 | 失败路由回上游层 | `repair_routing.py` | 强制 |
| R25 | 表现力指标 | `rep_metrics.py` | 经验 |
| R26 | 节拍审计 | `beat_audit.py` | 经验 |
| R27 | 导演 Critic 复核 | `director/critic.py` | 强制 |
| R28 | Anti-PPT 7 项检查 | `validation/anti_ppt.py::audit` | 强制 |
| R29 | 认知负荷≤时长承载 | `validation/cognitive_load.py::audit` | 强制 |
| R30 | 反同质化（节拍差异） | 全局 | 经验 |
| R31 | 强调编码唯一性 | `visual_grammar.py` | 经验 |
| R32 | 视觉必要性（无纯装饰堆砌） | `visual_necessity.py` | 经验 |
| R33 | 可读性下限 | `validation/typography.py` | 强制 |
| R34 | 不得为过检测而伪造 | `validation/anti_ppt.py`（strict） | 强制 |
| R35 | 参考帧构图法复刻 | `ref_frame.py` | 经验 |
| R36 | 构图语法族（16 类） | `compiler/composition_family.py` | 强制 |
| R37 | 每族≥1 策略支撑 | `compiler/composition_family.py::validate_families` | 强制 |
| R38 | 场景级样式锁 | `compiler/style_lock.py::audit_plan` | 强制 |
| R39 | 复用优先（entity>motif>style>layout>anim>new） | `compiler/style_lock.py::reuse_decision` | 经验 |
| R40 | 每元素可解释（reason/claim） | `visual_intent.py` | 强制 |
| R41 | 最终质量标准（构图+运动+连续性） | `spec_audit.run_all` | 强制 |
| R42 | 最重要：导演思维优先于生成 | 全局 | 强制 |

## 使用

```python
import spec_audit
report = spec_audit.run_all(plan)     # 统一判决 PASS/FAIL + issues
if report["status"] == "FAIL":
    ...                                # 按 issue.rule 路由回上游层（R24）
```

`spec_audit.registry_report()` 报告注册表健康度（已接线规则数）。

验证：`python3 runtime/spec_test.py`（独立套件）+ `python3 runtime/self_test.py`（回归，须保持 20/20）。
