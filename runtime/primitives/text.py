"""text.py — 文字图元。"""
import ref_frame as R


def title(txt, y=None, x=None, size=26):
    """版心标题（统一左对齐 x=MARGIN）。"""
    x = R.MARGIN if x is None else x
    y = R.TITLE_Y if y is None else y
    return (f'<text x="{x}" y="{y}" fill="{R.INK}" font-size="{size}" font-weight="500" '
            f'font-family="{R.FONT}">{R._esc(txt)}</text>')


def caption(txt, y=None, x=None, size=12):
    """底部说明。"""
    x = R.MARGIN if x is None else x
    y = R.CAPTION_Y if y is None else y
    return (f'<text x="{x}" y="{y}" fill="{R.TMID}" font-size="{size}" '
            f'font-family="{R.FONT}">{R._esc(txt)}</text>')


def label(txt, cx, y, col=None, size=14, weight=400, anchor="middle"):
    """任意定位标签。"""
    col = R.TMID if col is None else col
    return (f'<text x="{cx:.0f}" y="{y:.0f}" text-anchor="{anchor}" fill="{col}" '
            f'font-size="{size}" font-weight="{weight}" font-family="{R.FONT}">{R._esc(txt)}</text>')


def badge(num, cx, cy, r=12):
    """圆点徽标（强调色）。"""
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="{R.ACC}"/>'
            f'<text x="{cx:.0f}" y="{cy + r * 0.42:.0f}" text-anchor="middle" fill="#FFFFFF" '
            f'font-size="{r + 1}" font-weight="500" font-family="{R.FONT}">{R._esc(num)}</text>')


def multiline(lines, x, y, size=14, lh=1.4, col=None, weight=400, anchor="start"):
    """多行文本块（等行距）——把段落当可复用零件。"""
    col = R.TMID if col is None else col
    step = size * lh
    return "".join(
        f'<text x="{x:.0f}" y="{y + i * step:.0f}" text-anchor="{anchor}" fill="{col}" '
        f'font-size="{size}" font-weight="{weight}" font-family="{R.FONT}">{R._esc(ln)}</text>'
        for i, ln in enumerate(lines))
