"""path.py — 线 / 折线 / 箭头图元。"""
import ref_frame as R


def line(x0, y0, x1, y1, role="secondary", dash=None):
    sw, sc = R.stroke(role)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" '
            f'stroke="{sc}" stroke-width="{sw}" stroke-linecap="round"{d}/>')


def arrow(x0, x1, y):
    """水平连接箭头（手绘，不依赖 <marker>，避免 cairosvg 兼容问题）。"""
    return (f'<line x1="{x0:.0f}" y1="{y:.0f}" x2="{x1 - 4:.0f}" y2="{y:.0f}" stroke="{R.MID}" '
            f'stroke-width="1.5" stroke-linecap="round"/>'
            f'<path d="M{x1 - 10:.0f} {y - 5:.0f} L{x1:.0f} {y:.0f} L{x1 - 10:.0f} {y + 5:.0f}" '
            f'fill="none" stroke="{R.MID}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')


def polyline(points, accent=False):
    """折线（轨迹）；accent=True 用强调色。"""
    col = R.ACC if accent else R.MID
    pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in points)
    g = (f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.25" '
         f'stroke-linecap="round" stroke-linejoin="round"/>')
    if accent:
        for x, y in points:
            g += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="{R.ACC}"/>'
    return g


def threshold(y, x0, x1, txt="阈值"):
    """阈值虚线 + 标签。"""
    return (f'<line x1="{x0:.0f}" y1="{y:.0f}" x2="{x1:.0f}" y2="{y:.0f}" stroke="{R.MID}" '
            f'stroke-width="1.75" stroke-dasharray="6 6" stroke-linecap="round"/>'
            f'<text x="{x1:.0f}" y="{y - 8:.0f}" text-anchor="end" fill="{R.TMID}" font-size="12" '
            f'font-family="{R.FONT}">{R._esc(txt)}</text>')
