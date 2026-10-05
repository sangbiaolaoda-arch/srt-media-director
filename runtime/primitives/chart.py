"""chart.py — 图表图元（柱 / 累积柱组 / 刻度）。"""
import ref_frame as R
from . import shape, path


def accumulating_bars(x0, base_y, n=6, bw=20, gap=16, h0=14, dh=11, slope="up"):
    """累积柱组：n 根渐增（或渐减）短柱——表达 accumulation。"""
    g = ""
    for i in range(n):
        h = h0 + i * dh
        bx = x0 + i * (bw + gap)
        g += shape.bar(bx, base_y, bw, h)
    return g


def baseline(x0, x1, y):
    return path.line(x0, y, x1, y, role="secondary")


def ticks(x0, x1, y, n=6):
    g = ""
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        g += (f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x:.0f}" y2="{y + 6:.0f}" '
              f'stroke="{R.MID}" stroke-width="1.25" stroke-linecap="round"/>')
    return g


def sparkline(values, x, y, w, h, accent=False):
    """迷你趋势线：把一串数值归一化进 (x,y,w,h) 盒子里。"""
    vals = list(values)
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    n = len(vals)
    pts = [(x + (w * i / (n - 1) if n > 1 else 0.0),
            y + h * (1.0 - (v - lo) / span)) for i, v in enumerate(vals)]
    return path.polyline(pts, accent=accent)
