"""Visual Weight — 视觉权重（Phase 2 · 第十一优先级）。

Primary / Secondary / Support / Decoration，自动控制
scale / contrast / position / animation intensity / visual density，
防止所有元素都抢注意力。
"""
from __future__ import annotations

WEIGHTS = ("primary", "secondary", "support", "decoration")

STYLE = {
    "primary":    {"scale": 1.00, "opacity": 1.00, "stroke_mult": 1.00,
                   "anim_intensity": 1.00, "font": 24, "density_budget": 0.30},
    "secondary":  {"scale": 0.86, "opacity": 0.96, "stroke_mult": 0.85,
                   "anim_intensity": 0.80, "font": 18, "density_budget": 0.30},
    "support":    {"scale": 0.74, "opacity": 0.86, "stroke_mult": 0.70,
                   "anim_intensity": 0.60, "font": 13, "density_budget": 0.25},
    "decoration": {"scale": 0.60, "opacity": 0.45, "stroke_mult": 0.45,
                   "anim_intensity": 0.30, "font": 10, "density_budget": 0.15},
}


def style_for(weight):
    return dict(STYLE.get(weight, STYLE["support"]))


def audit(graph, max_decoration_ratio=0.5):
    nodes = [n for n in graph.root.walk() if n.id != graph.root.id and n.visible]
    if not nodes:
        return {"status": "PASS", "issues": []}
    prim = [n for n in nodes if n.weight == "primary"]
    deco = [n for n in nodes if n.weight == "decoration"]
    issues = []
    if len(prim) == 0:
        issues.append({"severity": "warn", "code": "WEIGHT_NO_PRIMARY",
                       "msg": "visual weight hierarchy missing: no primary node"})
    if len(prim) > 1:
        issues.append({"severity": "warn", "code": "WEIGHT_AMBIGUOUS_PRIMARY",
                       "msg": "%d primary nodes compete for attention" % len(prim)})
    if nodes and len(deco) / len(nodes) > max_decoration_ratio:
        issues.append({"severity": "warn", "code": "WEIGHT_EXCESS_DECORATION",
                       "msg": "%d/%d nodes are decoration (excessive)"
                              % (len(deco), len(nodes))})
    return {"status": "FAIL" if any(i["severity"] == "err" for i in issues)
            else "PASS", "issues": issues,
            "counts": {w: sum(1 for n in nodes if n.weight == w) for w in WEIGHTS}}
