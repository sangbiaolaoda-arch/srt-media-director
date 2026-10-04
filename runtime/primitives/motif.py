"""motif.py — 具象线稿图元（复用 ref_frame 的图标库）。

这些是「画法」，不是「模板」。函数化（cx/cy/scale/col）后可被任何构图复用。
"""
import ref_frame as R


def bell(cx, cy, s=1.0, col=None):
    return R.icon_bell(cx, cy, s, col or R.MID)


def focus_break(cx, cy, s=1.0, col=None):
    return R.icon_focus_break(cx, cy, s, col or R.INK)


def bar_half(cx, cy, s=1.0):
    return R.icon_bar_half(cx, cy, s)


def door(cx, cy, s=1.0, col=None):
    return R.icon_door(cx, cy, s, col or R.INK)


def phone(cx, cy, s=1.0, col=None, badge=None):
    return R.icon_phone(cx, cy, s, col or R.INK, badge=badge)


def registry():
    """可用具象图元清单（供文档 / 能力探测）。"""
    return {"bell": bell, "focus_break": focus_break, "bar_half": bar_half,
            "door": door, "phone": phone}
