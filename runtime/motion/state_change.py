"""state_change.py — 元素「自身状态改变」的运动决策。

当同一元素跨拍存在、但其数值/形态发生变化时，应该 transform，而不是重新入场。
"""


def detect_state_change(prev_el, cur_el):
    """返回 (changed: bool, fields: list)。比对可能影响呈现的状态字段。"""
    if not prev_el or not cur_el:
        return False, []
    fields = []
    for k in ("value", "text", "count", "state", "highlight"):
        if k in prev_el or k in cur_el:
            if prev_el.get(k) != cur_el.get(k):
                fields.append(k)
    changed = bool(fields)
    return changed, fields


def state_motion(changed, is_focal=False):
    """状态改变 → 运动原语。焦点元素用更明显的 transform。"""
    if not changed:
        return "continue"
    return "transform"
