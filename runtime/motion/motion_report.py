"""motion_report.py — 把 RenderPlan 的 motion 决策转成可读报告 / CSS。

供 CLI 与测试使用：解释每个元素为什么这样运动。
"""


def explain(plan):
    lines = []
    v = plan.get("validation", {})
    lines.append("Motion Coverage: %.2f | missing=%s | static(explicit)=%s | moving=%s / %s" % (
        v.get("motion_coverage", 0), v.get("motion_missing", "?"),
        v.get("static_explicit", "?"), v.get("moving", "?"), v.get("visible", "?")))
    for bp in plan.get("beats", []):
        lines.append("\n[%s] grammar=%s focal=%s" % (
            bp["beat_id"], bp.get("grammar"), bp.get("focal_point")))
        for e in bp["elements"]:
            p = e["motion_policy"]
            lines.append("   %-16s %-11s type=%-8s at=%+.2fs dur=%.2f src=%-9s  %s" % (
                e["id"], e.get("semantic_role"), p["type"], p.get("delay", 0),
                p.get("duration", 0), p.get("source"), p.get("reason")))
    return "\n".join(lines)
