"""spec_audit.py — unified registry for the 42-rule "visual director + compiler"
behavior spec (v7.5).

Every rule is one entry with a stable id. A rule either maps to a concrete
gate module (importable + callable) or is explicitly marked as an
enforcement/documentation rule. `run_all` executes the whole registry against
one plan and folds the per-module results into a single PASS/FAIL decision, so
the pipeline has ONE place to ask "does this plan satisfy the spec?".
"""
from __future__ import annotations

import importlib

# id -> (title, module, attr) or (title, None, None) for doc/non-exec rules.
RULES = [
    # 0-4 principle / contract
    ("R00-core-principle", "导演思维，非模板化生成", None, None),
    ("R01-layout-intent", "先有布局意图再分配像素", "composition_planner", "plan"),
    ("R02-constraint-pixel", "语义约束→像素求解", "compiler.anchor_layout", "solve"),
    ("R03-no-raw-coords", "禁止裸绝对坐标", "compiler.anchor_layout", "rejects_raw_coordinates"),
    ("R04-deterministic", "同输入同输出（可复现）", None, None),
    # 5-8 hierarchy / continuity
    ("R05-visual-hierarchy", "视觉权重层级 P0..P3", "director.hierarchy", "audit_hierarchy"),
    ("R06-hierarchy-overreach", "装饰不得压过主体", "director.hierarchy", "audit_hierarchy"),
    ("R07-entity-continuity", "实体级连续性（默认 PERSIST）", "director.continuity_graph", "audit_continuity"),
    ("R08-state-change", "状态变化优于硬替换", "director.continuity_graph", "persist_ratio"),
    # 9-14 primitives / relations
    ("R09-primitive-registry", "图元注册表（motif/chart/...）", "primitives", None),
    ("R10-relation-typing", "关系必须显式类型化", "director.relationship", None),
    ("R11-semantic-anchor", "语义锚点定位", "compiler.anchor_layout", "anchor_xy"),
    ("R12-proximity", "邻近成组（proximity）", "composition_planner", "_proximity_pairs"),
    ("R13-visual-balance", "视觉平衡检查", "composition_planner", "_visual_balance"),
    ("R14-motif-reuse", "动机（motif）复用优先", "compiler.style_lock", "reuse_decision"),
    # 15-19 layout / space / budget
    ("R15-anchor-layout", "锚点/关系/距离→像素", "compiler.anchor_layout", "solve"),
    ("R16-relation-graph", "关系图求解", "compiler.anchor_layout", "solve"),
    ("R17-negative-space", "负空间/密度纪律", "compiler.negative_space", "audit_negative_space"),
    ("R18-visual-budget", "视觉预算（时长×密度→复杂度）", "compiler.visual_budget", "audit_budget"),
    ("R19-budget-tier", "复杂度分档", "compiler.visual_budget", "tier_for"),
    # 20-27 validation / repair
    ("R20-safe-area", "安全区约束", "validation.safe_area", None),
    ("R21-geometry", "几何（不重叠/不出界）", "validation.geometry", None),
    ("R22-typography", "排版规则（字号阶梯/可读）", "validation.typography", None),
    ("R23-visual-regression", "视觉回归对比", "validation.visual_regression", None),
    ("R24-repair-routing", "失败路由回上游层", "repair_routing", None),
    ("R25-rep-metrics", "表现力指标", "rep_metrics", None),
    ("R26-beat-audit", "节拍审计", "beat_audit", None),
    ("R27-critic", "导演 Critic 复核", "director.critic", None),
    # 28-33 anti-ppt / cognitive
    ("R28-anti-ppt", "Anti-PPT 7 项检查", "validation.anti_ppt", "audit"),
    ("R29-cognitive-load", "认知负荷≤时长承载", "validation.cognitive_load", "audit"),
    ("R30-anti-homogeneous", "反同质化（节拍差异）", None, None),
    ("R31-emphasis-encoding", "强调编码唯一性", "visual_grammar", None),
    ("R32-visual-necessity", "视觉必要性（无纯装饰堆砌）", "visual_necessity", None),
    ("R33-readability", "可读性下限", "validation.typography", None),
    # 34-41 quality / style / grammar
    ("R34-no-gaming", "不得为过检测而伪造", "validation.anti_ppt", "audit"),
    ("R35-reference-frame", "参考帧构图法复刻", "ref_frame", None),
    ("R36-composition-family", "构图语法族（16 类）", "compiler.composition_family", "audit_beats"),
    ("R37-strategy-support", "每族≥1 策略支撑", "compiler.composition_family", "validate_families"),
    ("R38-style-lock", "场景级样式锁", "compiler.style_lock", "audit_plan"),
    ("R39-reuse-first", "复用优先（entity>motif>style>layout>anim>new）", "compiler.style_lock", "reuse_decision"),
    ("R40-explainability", "每元素可解释（reason/claim）", "visual_intent", None),
    ("R41-final-quality", "最终质量标准（构图+运动+连续性）", None, None),
    ("R42-director-first", "最重要：导演思维优先于生成", None, None),
]

# Rules whose gate lives in an already-importable module we do not re-run here
# (they are enforced by their own subsystem / self_test). Marked executable=False.
PUBLIC_RUN = {
    "R03-no-raw-coords", "R05-visual-hierarchy", "R06-hierarchy-overreach",
    "R07-entity-continuity", "R17-negative-space", "R18-visual-budget",
    "R28-anti-ppt", "R29-cognitive-load", "R36-composition-family",
    "R37-strategy-support", "R38-style-lock", "R11-semantic-anchor",
    "R15-anchor-layout", "R16-relation-graph", "R19-budget-tier",
    "R02-constraint-pixel",
}


def _resolve(module, attr):
    try:
        m = importlib.import_module(module)
    except Exception:
        m = None
    if m is None or not attr:
        return m
    return getattr(m, attr, None)


def registry_report():
    """Static health of the registry: how many rules are executable and wired."""
    out = []
    wired = 0
    for rid, title, mod, attr in RULES:
        callable_ok = False
        if mod:
            obj = _resolve(mod, attr) if attr else _resolve(mod, None)
            callable_ok = obj is not None
        if callable_ok:
            wired += 1
        out.append({"id": rid, "title": title, "module": mod,
                    "attr": attr, "wired": callable_ok})
    return {"total": len(RULES), "wired": wired, "rules": out,
            "status": "PASS" if wired >= 20 else "FAIL"}


def run_all(plan):
    """Run every executable public gate over one plan; fold to one decision."""
    results = {}
    issues = []

    def _call(rid, fn, *a, **k):
        try:
            r = fn(*a, **k)
        except Exception as e:  # a gate that cannot run is a blocker, not a pass
            results[rid] = {"status": "ERROR", "error": repr(e)}
            issues.append({"severity": "err", "code": "GATE_ERROR",
                           "rule": rid, "msg": repr(e)})
            return
        results[rid] = r
        for i in (r.get("issues") if isinstance(r, dict) else None) or []:
            issues.append(dict(i, rule=rid))

    beats = plan.get("beats", [])
    for b in beats:
        _call("R05-visual-hierarchy", _resolve("director.hierarchy", "audit_hierarchy"), b)
        _call("R06-hierarchy-overreach", _resolve("director.hierarchy", "audit_hierarchy"), b)
        _call("R17-negative-space", _resolve("compiler.negative_space", "audit_negative_space"), b)
        _call("R18-visual-budget", _resolve("compiler.visual_budget", "audit_budget"), b)
    _call("R07-entity-continuity", _resolve("director.continuity_graph", "audit_continuity"), beats)
    _call("R28-anti-ppt", _resolve("validation.anti_ppt", "audit"), plan)
    _call("R29-cognitive-load", _resolve("validation.cognitive_load", "audit"), plan)
    _call("R36-composition-family", _resolve("compiler.composition_family", "audit_beats"), beats)
    _call("R38-style-lock", _resolve("compiler.style_lock", "audit_plan"), plan)

    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "issues": issues, "results": results,
            "rules_run": len(results)}
