"""render.py — Motion Renderer：把带 motion 的 RenderPlan 执行成真实 HTML 帧。

职责边界：Renderer 不猜「这个元素要不要动画」——它只执行 RenderPlan 里已确定的
motion_policy。为可复现与可逐时刻冻结，这里在 Python 侧按原语关键帧把元素在时刻 t
的状态（opacity / transform / clip-path）算好，写成内联样式，再交给 Playwright 截图。
整条链路仍是：RenderPlan → HTML（内联运动状态）→ Playwright → PNG。
"""
import os, re, html as _html
from timeline import legacy as _legacy
from .motion_registry import MOTION_PRIMITIVES, is_valid_motion, STATIC_LIKE

PALETTE_BG = {
    "night": "#F3F2EF", "warm": "#F8EFE3", "cold": "#EDF2F5",
    "tense": "#F8EDE8", "calm": "#EFF4EF", "dusk": "#EFEAE6",
}
INK = "#2B2B2B"; MID = "#8A8A86"; ACC = "#C4452B"
IDENTITY = {"opacity": 1.0, "tx": 0.0, "ty": 0.0, "sx": 1.0, "sy": 1.0,
            "rot": 0.0, "clip": None}


# ------------------------------------------------------------------ 缓动
def _ease(name, p):
    # Curve math lives in timeline.easing (single source of truth); this adapter
    # is byte-parity with the previous implementation.
    return _legacy.render_legacy_ease(name, p)


# ------------------------------------------------------------------ 关键帧解析
def _parse_props(props):
    d = dict(IDENTITY)
    if "opacity" in props:
        d["opacity"] = float(props["opacity"])
    t = props.get("transform")
    if t:
        for fn, val in re.findall(r"(translateX|translateY|scaleX|scaleY|scale|rotate)\(([-\d.]+)(?:px|deg)?\)", t):
            v = float(val)
            if fn == "translateX": d["tx"] = v
            elif fn == "translateY": d["ty"] = v
            elif fn in ("scale", "scaleX", "scaleY"):
                if fn == "scale": d["sx"] = d["sy"] = v
                elif fn == "scaleX": d["sx"] = v
                else: d["sy"] = v
            elif fn == "rotate": d["rot"] = v
    c = props.get("clip-path")
    if c:
        m = re.search(r"inset\(([-\d.]+%?)\s+([-\d.]+%?)\s+([-\d.]+%?)\s+([-\d.]+%?)", c)
        if m:
            vals = [float(x.replace("%", "")) for x in m.groups()]
            # inset(top right bottom left)：揭示动画用 right 从 100%→0
            d["clip"] = vals
    return d


def _lerp(a, b, p):
    return a + (b - a) * p


def _interp(d0, d1, p):
    out = {"opacity": _lerp(d0["opacity"], d1["opacity"], p),
           "tx": _lerp(d0["tx"], d1["tx"], p), "ty": _lerp(d0["ty"], d1["ty"], p),
           "sx": _lerp(d0["sx"], d1["sx"], p), "sy": _lerp(d0["sy"], d1["sy"], p),
           "rot": _lerp(d0["rot"], d1["rot"], p)}
    if d0["clip"] and d1["clip"]:
        out["clip"] = [_lerp(a, b, p) for a, b in zip(d0["clip"], d1["clip"])]
    else:
        out["clip"] = None
    return out


def _state(mtype, prog):
    prim = MOTION_PRIMITIVES.get(mtype)
    if not prim:
        return dict(IDENTITY)
    kf = prim["css"]
    d0 = _parse_props(kf[0][1]); d1 = _parse_props(kf[-1][1])
    return _interp(d0, d1, prog)


def _style_from(state, prim):
    parts = ["opacity:" + repr(round(state["opacity"], 4))]
    tf = []
    if abs(state["tx"]) > 1e-4: tf.append("translateX(" + repr(round(state["tx"], 2)) + "px)")
    if abs(state["ty"]) > 1e-4: tf.append("translateY(" + repr(round(state["ty"], 2)) + "px)")
    if abs(state["sx"] - 1) > 1e-4 or abs(state["sy"] - 1) > 1e-4:
        if abs(state["sx"] - state["sy"]) < 1e-4:
            tf.append("scale(" + repr(round(state["sx"], 4)) + ")")
        else:
            tf.append("scaleX(" + repr(round(state["sx"], 4)) + ") scaleY(" + repr(round(state["sy"], 4)) + ")")
    if abs(state["rot"]) > 1e-4: tf.append("rotate(" + repr(round(state["rot"], 2)) + "deg)")
    if tf:
        parts.append("transform:" + " ".join(tf))
    if state.get("clip"):
        top, right, bottom, left = [round(v, 2) for v in state["clip"]]
        parts.append("clip-path:inset(%g%% %g%% %g%% %g%%)" % (top, right, bottom, left))
    if prim.get("origin"):
        parts.append("transform-origin:" + prim["origin"])
    return ";".join(parts)


def _el_style(e, t=None):
    box = e.get("box") or [0, 0, 100, 40]
    x, y, w, h = box
    p = e.get("motion_policy") or {}
    mtype = p.get("type")
    st = ["position:absolute",
          "left:" + repr(float(x)) + "px", "top:" + repr(float(y)) + "px",
          "width:" + repr(float(w)) + "px", "height:" + repr(float(h)) + "px"]
    prim = MOTION_PRIMITIVES.get(mtype)
    dur = p.get("duration") or 0.0
    delay = p.get("delay") or 0.0
    if t is None or not prim or dur <= 0:
        prog = 1.0
    else:
        ease = p.get("easing") or prim.get("easing", "linear")
        if t <= delay:
            prog = 0.0
        elif t >= delay + dur:
            prog = 1.0
        else:
            prog = _ease(ease, (t - delay) / dur)
    state = _state(mtype, prog) if prim else dict(IDENTITY)
    st.append(_style_from(state, prim or {}))
    return ";".join(st)


def _el_inner(e):
    if e.get("svg"):
        return e["svg"]
    role = e.get("semantic_role") or e.get("type") or ""
    label = _html.escape(str(e.get("label") or e["id"]))
    etype = e.get("type")
    if etype in ("connector", "path", "line"):
        return ('<div style="width:100%;height:100%;display:flex;align-items:center">'
                '<div style="flex:1;height:2px;background:' + MID + '"></div></div>')
    border = ACC if role == "focal" else MID
    bg = "transparent" if role in ("background", "decoration") else "#FFFFFF"
    return ('<div style="width:100%;height:100%;box-sizing:border-box;border:1.5px solid ' + border +
            ';border-radius:8px;background:' + bg + ';display:flex;flex-direction:column;'
            'align-items:center;justify-content:center;font-family:sans-serif">'
            '<div style="font-size:11px;color:' + MID + ';letter-spacing:.5px">' + _html.escape(role) + '</div>'
            '<div style="font-size:13px;color:' + INK + ';font-weight:600">' + label + '</div></div>')


def beat_html(bp, w=680, h=382, t=None):
    palette = bp.get("palette") or "night"
    bg = PALETTE_BG.get(palette, PALETTE_BG["night"])
    parts = ['<div class="stage" style="position:absolute;left:0;top:0;width:' + repr(w) +
             'px;height:' + repr(h) + 'px;background:' + bg + ';overflow:hidden">']
    for e in bp.get("elements", []):
        if not e.get("visible", True):
            continue
        parts.append('<div class="el" style="' + _el_style(e, t) + '">' + _el_inner(e) + "</div>")
    parts.append("</div>")
    return ("<!doctype html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;padding:0;width:" + repr(w) + "px;height:" + repr(h) + "px}"
            "*{box-sizing:border-box}</style></head><body>" + "".join(parts) + "</body></html>")


def render_frames(bp, out_dir, times, w=680, h=382, executable_path="/usr/bin/chromium"):
    """用 Playwright 逐时刻截图，冻结在动画时间 t。返回 [png_path]。"""
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=executable_path, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        for t in times:
            pg.set_content(beat_html(bp, w, h, t=t))
            fp = os.path.join(out_dir, "t%03d.png" % int(round(t * 100)))
            pg.screenshot(path=fp)
            paths.append(fp)
        b.close()
    return paths
