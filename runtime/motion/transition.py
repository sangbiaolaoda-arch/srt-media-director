"""transition.py — 拍与拍之间的转场 + 相机（camera）决策。

解决「硬切 / 断裂感」：优先 carry / dissolve，而不是每拍都重新 fade in。
"""


def camera_for(beat, density=None):
    """相机决策：默认 static；密度高或标为强调时用极轻推近。"""
    d = density if density is not None else beat.get("density", 0.5)
    if beat.get("camera") == "push_in" or d >= 0.75:
        return {"type": "push_in", "amount": 0.04}
    return {"type": "static", "amount": 0.0}


def beat_transition(prev_beat, cur_beat, prev_plan, cur_plan):
    """相邻拍转场。共享元素（同 id）→ carry/dissolve（保持连续）；否则 cut。"""
    prev_ids = {e["id"] for e in prev_plan.get("elements", [])} if prev_plan else set()
    cur_ids = {e["id"] for e in cur_plan.get("elements", [])} if cur_plan else set()
    shared = prev_ids & cur_ids
    if shared:
        return {"type": "carry", "duration": 0.5, "shared": sorted(shared),
                "reason": "存在延续元素，用承接而非重切"}
    return {"type": "dissolve", "duration": 0.4, "shared": [],
            "reason": "无共享元素，用短溶解过渡"}
