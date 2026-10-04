"""connector.py — 连接线 / 关系连线图元。"""
import ref_frame as R


def elbow(x0, y0, x1, y1, role="secondary"):
    """直角折线连接。"""
    _, sc = R.stroke(role)
    midx = (x0 + x1) / 2
    return (f'<path d="M{x0:.0f} {y0:.0f} H{midx:.0f} V{y1:.0f} H{x1:.0f}" fill="none" '
            f'stroke="{sc}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')


def dashed(x0, y0, x1, y1, role="secondary"):
    """虚线连接（弱关系）。"""
    _, sc = R.stroke(role)
    return (f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="{sc}" '
            f'stroke-width="1.5" stroke-dasharray="4 5" stroke-linecap="round"/>')


def relation_edges(edges, positions):
    """按关系图连边：edges=[{from,relation,to}]，positions={node:(x,y)}。

    关系图来自 director.relationship；这里只把「谁连谁」画出来，不产生语义。
    """
    g = ""
    for e in edges or []:
        a = positions.get(e.get("from"))
        b = positions.get(e.get("to"))
        if a and b:
            g += dashed(a[0], a[1], b[0], b[1])
    return g
