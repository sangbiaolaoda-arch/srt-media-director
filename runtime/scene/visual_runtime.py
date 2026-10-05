"""Visual Runtime — Render Plan → 真实 SVG / HTML（Phase 2 · 第七优先级）。

Agent 不再负责底层 SVG / CSS / 坐标 / transform matrix：本运行时常量把
场景节点（已含世界变换）画成 SVG，并把每个状态帧包成可独立打开的 HTML，
供 Playwright / chromium 真实截图。

关键：节点的 world_box 已包含父子继承，所以子元素无需自己算 x/y。
"""
from __future__ import annotations

CANVAS = (680, 382)
PAL = {"ink": "#1f2933", "muted": "#52606d", "accent": "#d64545",
       "warn": "#f0b429", "line": "#9aa5b1", "bg": "#f5f7fa",
       "panel": "#ffffff", "good": "#2f9e6f"}


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _fs(weight, base):
    from .visual_weight import style_for
    return style_for(weight)["font"] if base is None else base


def _op(node):
    from .visual_weight import style_for
    return round(style_for(node.weight)["opacity"] * node.world_opacity(), 3)


def _fill(node, default):
    if node.weight == "primary":
        return node.style.get("fill", PAL["ink"])
    if node.weight == "decoration":
        return node.style.get("fill", PAL["line"])
    return node.style.get("fill", default)


def draw_node(node):
    """单节点 → SVG 片段（绝对坐标 = world_box）。"""
    x, y, w, h = node.world_box()
    cx, cy = x + w / 2.0, y + h / 2.0
    k = node.data.get("draw") or node.kind
    op = _op(node)
    g = '<g opacity="%s">' % op
    if k in ("scene", "group"):
        return ""  # 容器不绘制
    if k == "background":
        return ('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>'
                % (CANVAS[0], CANVAS[1], node.style.get("fill", PAL["bg"])))
    if k in ("text", "title", "emphasis", "label"):
        fs = _fs(node.weight, node.style.get("font"))
        col = node.style.get("fill", PAL["accent"] if k == "emphasis" else PAL["ink"])
        anchor = node.style.get("anchor", "middle")
        return (g + '<text x="%.1f" y="%.1f" font-family="sans-serif" '
                'font-size="%d" font-weight="%s" fill="%s" text-anchor="%s" '
                'dominant-baseline="middle">%s</text></g>'
                % (cx, cy, fs, "700" if node.weight == "primary" else "400",
                   col, anchor, _esc(node.text or node.id)))
    if k in ("circle", "head"):
        return (g + '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" '
                'stroke-width="2"/></g>'
                % (cx, cy, min(w, h) / 2.0, _fill(node, PAL["panel"]), PAL["ink"]))
    if k == "person":
        r = min(w, h * 0.36) / 2.0
        return (g
                + '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="2"/>'
                  % (cx, y + r + 4, r, PAL["panel"], PAL["ink"])
                + '<path d="M %.1f %.1f q %.1f %.1f 0 %.1f Z" fill="%s" stroke="%s" stroke-width="2"/>'
                  % (cx - w * 0.32, y + h * 0.42, w * 0.64, h * 0.5, h * 0.55, PAL["panel"], PAL["ink"])
                + '</g>')
    if k in ("box", "panel", "bar", "chip", "escalation", "badge"):
        fill = _fill(node, PAL["panel"] if k != "escalation" else PAL["warn"])
        rx = 8 if k not in ("escalation", "chip") else 14
        out = (g + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" '
               'fill="%s" stroke="%s" stroke-width="1.5"/>' % (x, y, w, h, rx, fill, PAL["ink"]))
        if node.text:
            out += ('<text x="%.1f" y="%.1f" font-family="sans-serif" font-size="12" '
                    'fill="%s" text-anchor="middle" dominant-baseline="middle">%s</text>'
                    % (cx, cy, PAL["ink"], _esc(node.text)))
        return out + "</g>"
    if k == "ring":
        return (g + '<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="none" '
                'stroke="%s" stroke-width="2" stroke-dasharray="6 5"/></g>'
                % (cx, cy, w / 2.0, h / 2.0, PAL["line"]))
    if k == "arrow":
        x2 = node.data.get("to", (cx + 60, cy))[0]
        y2 = node.data.get("to", (cx + 60, cy))[1]
        return (g + '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                'stroke-width="2"/>'
                '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/></g>'
                % (cx, cy, x2, y2, PAL["ink"], x2, y2, x2 - 9, y2 - 4, x2 - 9, y2 + 4, PAL["ink"]))
    # 默认：圆角矩形
    return (g + '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="8" '
            'fill="%s" stroke="%s" stroke-width="1.5"/></g>'
            % (x, y, w, h, _fill(node, PAL["panel"]), PAL["ink"]))


def to_spec(graph, bg=None):
    """场景图 → svg_compiler 兼容的 spec。"""
    els = []
    for n in graph.root.walk():
        if n.id == graph.root.id:
            continue
        if not n.visible:
            continue
        inner = draw_node(n)
        if not inner:
            continue
        els.append({"id": n.id, "svg": inner,
                    "box": [round(v, 2) for v in n.world_box()],
                    "weight": n.weight})
    return {"bg": bg or PAL["bg"], "elements": els}


def render_spec(spec, png_path):
    """真实截图（playwright 优先，如实降级）。"""
    from render.screenshot import screenshot_spec
    return screenshot_spec(spec, png_path, prefer="playwright")


def to_html(spec, title="beat"):
    from compiler.svg_compiler import to_html as _h
    return _h(spec, title=title)
