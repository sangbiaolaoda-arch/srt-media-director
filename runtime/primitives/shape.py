"""shape.py — 基础形状图元（卡片 / 圆 / 柱 / 条）。"""
import ref_frame as R


def card(x, y, w, h, role="secondary", rx=12):
    """圆角卡片；role 决定描边（primary=强调加粗加深）。"""
    sw, sc = R.stroke(role)
    return (f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" '
            f'fill="{R.PANEL}" stroke="{sc}" stroke-width="{sw}"/>')


def dot(cx, cy, r=9, filled=False, role="secondary"):
    """圆点；filled=True 时用强调色（唯一强调）。"""
    if filled:
        return f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="{R.ACC}"/>'
    _, sc = R.stroke(role)
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="none" '
            f'stroke="{sc}" stroke-width="1.75"/>')


def bar(x, y_base, w, h, fill=False, accent=False):
    """柱；accent 柱为唯一强调（fill+stroke 同色=同一元素）。"""
    col = R.ACC if accent else R.MUT
    sc = R.ACC if accent else R.MID
    return (f'<rect x="{x:.0f}" y="{y_base - h:.0f}" width="{w:.0f}" height="{h:.0f}" rx="3" '
            f'fill="{col}" stroke="{sc}" stroke-width="1.25"/>')


def track(x, y, w, h, rx=20):
    """进度条底槽。"""
    return (f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" '
            f'fill="{R.PANEL}" stroke="{R.MID}" stroke-width="1.75"/>')


def fill(x, y, w, h, rx=18):
    """进度条填充（强调）。"""
    return f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{R.ACC}"/>'


def ring(cx, cy, r, w=6, accent=False, role="secondary"):
    """圆环 / 环带（甘特环、进度环、聚焦圈的通用零件）。"""
    col = R.ACC if accent else R.stroke(role)[1]
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="none" '
            f'stroke="{col}" stroke-width="{w}"/>')
