"""continuity.py — 跨 Beat 连续运动（carry_over / continue / transform / handoff / exit）。

Motion Planner 不能只看当前拍。上一拍已存在的元素，下一拍不应重新 fade in，
而应延续或状态改变。本模块在「已编译的各拍 plan」之间建立时序联系。
"""
from .state_change import detect_state_change, state_motion


def link_beats(beat_plans):
    """就地改写：为与前一拍共享 id 的元素标记 carry_over / continue / transform。

    beat_plans: [{'beat_id','elements':[...] , ...}, ...]（已各自拥有 motion_policy）
    返回 continuity 记录列表。
    """
    records = []
    prev = None
    for bp in beat_plans:
        by_id = {e["id"]: e for e in bp["elements"]}
        cont = []
        if prev is not None:
            prev_by_id = {e["id"]: e for e in prev["elements"]}
            shared = set(by_id) & set(prev_by_id)
            for eid in sorted(shared):
                cur, pre = by_id[eid], prev_by_id[eid]
                changed, fields = detect_state_change(pre, cur)
                mtype = state_motion(changed, is_focal=(cur.get("semantic_role") == "focal"))
                cur["motion_policy"] = {
                    "type": mtype,
                    "source": "continuity",
                    "role": cur.get("semantic_role"),
                    "duration": 0.6 if mtype == "transform" else 0.0,
                    "delay": 0.0,
                    "easing": "cubic-bezier(.2,.8,.2,1)",
                    "reason": "跨拍延续（%s），不重新入场%s" % (
                        "状态改变→transform" if changed else "保持",
                        ("；变化字段 %s" % fields) if fields else ""),
                    "carry_from": prev["beat_id"],
                    "changed_fields": fields,
                }
                cont.append({"element": eid, "type": mtype,
                             "changed_fields": fields, "from": prev["beat_id"]})
        bp["continuity"] = {"carried": cont, "shared_with_prev":
                            sorted(set(by_id) & set(e["id"] for e in prev["elements"])) if prev else []}
        records.append({"beat_id": bp["beat_id"], "carried": cont})
        prev = bp

    # 计算 exit：某元素在后续拍不再出现 → 记一次退场（信息性，供未来淡出使用）
    for i, bp in enumerate(beat_plans):
        nxt = beat_plans[i + 1] if i + 1 < len(beat_plans) else None
        if not nxt:
            continue
        nxt_ids = {e["id"] for e in nxt["elements"]}
        for e in bp["elements"]:
            if e["id"] not in nxt_ids and e.get("motion_policy", {}).get("type") not in ("static", "none"):
                e.setdefault("motion_policy", {})["exit"] = {"type": "fade", "requested": True}
    return records
