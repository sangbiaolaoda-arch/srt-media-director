"""Stage 6a — Raster reference renderer (Pillow + svg_art), v4.2 cinema theme.

v4.2 视觉政策（用户反馈「画面好丑」后的重做）：
- 画布改为电影感暗色主题：纵向渐变底 + 径向暗角 + 胶片颗粒 + 遮幅黑边
  （常量集中在 common.THEME，HTML 播放器共用同一份，双侧一致）；
- 排版是主角：标题/关键词/金句/数字用衬线大字（Noto Serif CJK），
  注解用无衬线小字；强调元素带同色系柔光，而不是廉价描边框；
- motif 图形降级为背景水印（唯一 motif 时放大至画面高度 ~60%、透明度
  0.15 垫在文字之下；多 motif 对照时保持原位但降为半透明），不再是
  剪贴画式的主角；
- boxed 描边框 → 上下两条细金线（accent rule），信息用排版而非边框分区。

元素可见性仍由 entrance lifecycle 驱动；跨拍连续仍为拍首 TRANS_SEC
溶解 + inherit 主体位置插值（v4.1 语义不变，变的只是画法）。
"""
import math
import os
from procedural_canonical import rng as _proc_rng
from aesthetic_canonical import grade as _grade

from PIL import Image, ImageDraw, ImageFilter

import svg_art
from timeline import legacy as _legacy
from common import (CANVAS_W as W, CANVAS_H as H, COLORS, PALETTES, THEME,
                    ensure_dir, font, format_compact_num, hex2rgb)

TRANS_SEC = 0.45          # 跨拍溶解时长
DECOR_ALPHA = 0.38        # 装饰附体基础透明度（暗色主题下压低）
_WATERMARK_SCALE = 2.2    # 唯一 motif 作为水印时的放大倍数
_SERIF_SLOTS = {"title", "keyword", "word_left", "word_right",
                "cause", "result", "delta", "number"}

_BG_CACHE = {}
_VIGNETTE = None
_GRAIN_TILES = None


# ---------------------------------------------------------------- 主题基底

def _theme_bg(palette="night"):
    """纵向渐变底（按情绪调色板缓存；v4.4 全片不再一个色）。"""
    if palette not in _BG_CACHE:
        pal = PALETTES.get(palette, PALETTES["night"])
        top, bot = hex2rgb(pal["top"]), hex2rgb(pal["bottom"])
        col = Image.new("RGB", (1, 256))
        for y in range(256):
            t = y / 255.0
            col.putpixel((0, y), tuple(int(round(top[i] + (bot[i] - top[i]) * t))
                                       for i in range(3)))
        _BG_CACHE[palette] = col.resize((W, H))
    return _BG_CACHE[palette]


def _vignette_mask():
    """径向暗角蒙版（委托 aesthetic_canonical.grade —— 与 HTML 播放器同一模型）。"""
    global _VIGNETTE
    if _VIGNETTE is None:
        _VIGNETTE = _grade.vignette_mask_pil(320, 180, THEME).resize((W, H), Image.BILINEAR)
    return _VIGNETTE


def _grain_tile(i):
    global _GRAIN_TILES
    if _GRAIN_TILES is None:
        rnd = _proc_rng.default_rng()
        _GRAIN_TILES = []
        for _ in range(8):
            n = 256
            img = Image.new("L", (n, n))
            img.putdata([128 + rnd.randint(-40, 40) for _ in range(n * n)])
            _GRAIN_TILES.append(img.resize((W, H), Image.BILINEAR))
    return _GRAIN_TILES[i % len(_GRAIN_TILES)]


def _apply_grade(img, t):
    """电影质感三件套：暗角 → 颗粒 → 遮幅（画在最终帧上）。"""
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)),
                          img, _vignette_mask())
    grain = Image.merge("RGB", (_grain_tile(int(t * 24)),) * 3)
    img = Image.blend(img, grain, _grade.grain_strength(THEME) / 255.0)
    bar = _grade.letterbox_px(H, THEME)
    if bar > 0:
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, W, bar], fill=(0, 0, 0))
        dr.rectangle([0, H - bar, W, H], fill=(0, 0, 0))
    return img


# ---------------------------------------------------------------- 基础工具

def _clamp01(v):
    return max(0.0, min(1.0, v))


def _ease(t):
    # Curve math lives in timeline.easing (single source of truth).
    return _legacy.raster_ease(t)


def _rgb(c):
    return hex2rgb(c) if isinstance(c, str) else tuple(c)


def _mix(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    t = _clamp01(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _fade(color, alpha):
    """暗色主题下，淡入淡出 = 与底色混合（不是与米色纸面）。"""
    return _mix(THEME["bg_top"], color, alpha)


def _role_color(el):
    role = el.get("color_role", "ink")
    if role == "ink":
        return hex2rgb(THEME["ink"])
    if role == "neutral":
        return hex2rgb(THEME["muted"])
    return hex2rgb(COLORS.get(role, THEME["ink"]))


_TEXT_ROLE = {
    "ink": "ink", "neutral": "muted",
    "negative": "text_negative", "positive": "text_positive", "info": "text_info",
}


def _text_color(el):
    """v6.1：主体文字一律走加深色，避免浅底上「文字像背景」。

    ink → 暗暖黑；语义色（红/绿/蓝灰）→ 同名加深变体，保证对比度 ≥4.5:1。
    """
    role = el.get("color_role", "ink")
    key = _TEXT_ROLE.get(role)
    if key and key in THEME:
        return hex2rgb(THEME[key])
    return hex2rgb(COLORS.get(role, THEME["ink"]))


def _center(b):
    return (b["x"] + b["w"] / 2.0, b["y"] + b["h"] / 2.0)


def _lerp_box(a, b, t):
    return {k: a[k] + (b[k] - a[k]) * t for k in ("x", "y", "w", "h")}


def _scaled_box(b, k, margin=0.03):
    cx, cy = _center(b)
    w, h = b["w"] * k, b["h"] * k
    w = min(w, W * (1 - 2 * margin))
    h = min(h, H * (1 - 2 * margin))
    return {"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h}


def _state(entrance_beat, t):
    """element_id -> {alpha, dy, scale}（lifecycle 驱动，v4.1 语义不变）。"""
    st = {}
    for eid, lc in entrance_beat["lifecycle"].items():
        e = lc["enter"]
        if e["motion"] == "inherit":
            st[eid] = {"alpha": 1.0, "dy": 0.0, "scale": 1.0}
            continue
        a = _ease((t - e["at"]) / max(e["dur"], 0.01))
        dy, scale = 0.0, 1.0
        if a < 1.0:
            if e["motion"] == "rise":
                dy = (1.0 - a) * 26.0
            elif e["motion"] == "pop":
                scale = 0.55 + 0.45 * a
        alpha = a
        x = lc.get("exit")
        if x and t >= x["at"]:
            q = _ease((t - x["at"]) / max(x["dur"], 0.01))
            alpha = a * (1.0 - q)
            if x["motion"] == "sink":
                dy += q * 34.0
            elif x["motion"] == "shrink":
                scale *= (1.0 - 0.55 * q)
        st[eid] = {"alpha": alpha, "dy": dy, "scale": scale}
    events = {}
    for ev in entrance_beat["events"]:
        p = _clamp01((t - ev["at"]) / 0.9)
        for tgt in ev["targets"]:
            events.setdefault(tgt, []).append((ev["action"], p))
    return st, events


# ---------------------------------------------------------------- 元素画法

def _paste_svg(img, box, art, color, alpha, scale=1.0):
    w, h = box["w"] * scale, box["h"] * scale
    if w < 2 or h < 2 or alpha <= 0.0:
        return
    x = box["x"] + (box["w"] - w) / 2.0
    y = box["y"] + (box["h"] - h) / 2.0
    color_hex = "#%02X%02X%02X" % _rgb(color)
    spr = svg_art.render_png(art, color_hex, int(round(w)), int(round(h)))
    if alpha < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(spr, (int(round(x)), int(round(y))), spr)


def _fit_size(dr, text, size, bold, serif, max_w):
    """按盒子宽度收缩字号，避免衬线大字溢出。"""
    while size > 12:
        f = font(int(size), bold, serif)
        if dr.textlength(text, font=f) <= max_w:
            return int(size)
        size -= 2
    return 12


def _draw_text(dr, b, text, size, bold, color, serif=False, tracking=0):
    f = font(max(8, int(size)), bold, serif)
    cx, cy = _center(b)
    if tracking > 0:
        total = sum(dr.textlength(ch, font=f) for ch in text) \
            + tracking * (len(text) - 1)
        x = cx - total / 2.0
        for ch in text:
            dr.text((x, cy), ch, font=f, fill=color, anchor="lm")
            x += dr.textlength(ch, font=f) + tracking
    else:
        dr.text((cx, cy), text, font=f, fill=color, anchor="mm")


def _draw_glow(img, b, text, size, bold, serif, color, alpha):
    """强调柔光：半分辨率模糊层，避免逐帧全幅高斯的开销。"""
    sw, sh = W // 2, H // 2
    layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(max(8, int(size / 2)), bold, serif)
    cx, cy = (b["x"] + b["w"] / 2) / 2, (b["y"] + b["h"] / 2) / 2
    ga = int(255 * 0.18 * alpha)  # 浅底上柔光减半，避免糊成色斑
    d.text((cx, cy), text, font=f, fill=_rgb(color) + (ga,), anchor="mm")
    layer = layer.filter(ImageFilter.GaussianBlur(7))
    layer = layer.resize((W, H), Image.BILINEAR)
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"),
              (0, 0))


def _draw_rules(dr, b, color, alpha):
    """关键词标签：玫色圆角填充块 + 同色描边（v6.0 参考图的盒装标签）。"""
    fill = _fade(THEME["rose_fill"], alpha * 0.92)
    edge = _fade(THEME["rose_edge"], alpha)
    pad_x = b["w"] * 0.16
    pad_y = b["h"] * 0.24
    r = (b["h"] + 2 * pad_y) * 0.40
    dr.rounded_rectangle([b["x"] - pad_x, b["y"] - pad_y,
                          b["x"] + b["w"] + pad_x, b["y"] + b["h"] + pad_y],
                         radius=r, fill=fill, outline=edge, width=2)


def _draw_glow_panel(dr, b, tone, alpha):
    """comparison 面板：米白主题下改为浅色圆角色块 + 细同色边。

    暗色主题用同心椭圆模拟光晕；浅底上光晕会糊成一团，改用干净的
    色块 + 描边，既是分区又承担「一侧对比」的语义着色。
    """
    bg = THEME["bg_top"]
    base = {"negative_soft": COLORS["negative"],
            "positive_soft": COLORS["positive"]}.get(tone, THEME["muted"])
    a = _clamp01(alpha)
    if a <= 0.0:
        return
    fill = _mix(bg, base, 0.10 * a)
    edge = _mix(bg, base, 0.55 * a)
    r = max(6.0, min(b["w"], b["h"]) * 0.10)
    dr.rounded_rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]],
                         radius=r, fill=fill, outline=edge, width=2)


def _draw_arrow(dr, b, color, progress):
    y = b["y"] + b["h"] / 2
    x0, x1 = b["x"], b["x"] + b["w"] * progress
    if x1 - x0 < 4:
        return
    dr.line([x0, y, x1, y], fill=color, width=3)
    if progress > 0.85:
        s = b["h"] * 0.30
        dr.polygon([(x1, y), (x1 - s, y - s * 0.62), (x1 - s, y + s * 0.62)],
                   fill=color)


def _draw_donut(dr, b, value, color, progress):
    cx, cy = _center(b)
    r = min(b["w"], b["h"]) / 2 * 0.96
    track = _mix(THEME["bg_top"], THEME["ink"], 0.14)
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=track)
    frac = _clamp01(value / 100.0) * progress
    if frac > 0:
        dr.pieslice([cx - r, cy - r, cx + r, cy + r], start=-90,
                    end=-90 + 360 * frac, fill=color)
    inner = r * 0.62
    dr.ellipse([cx - inner, cy - inner, cx + inner, cy + inner],
               fill=_rgb(THEME["bg_bottom"]))


def _draw_bars(dr, b, before, after, color, progress):
    base_y = b["y"] + b["h"] * 0.88
    top_y = b["y"] + b["h"] * 0.10
    full = base_y - top_y
    hi = max(before, after, 1e-9)
    bw = b["w"] * 0.13
    for i, v in enumerate((before, after)):
        h = full * (v / hi) * progress
        cx = b["x"] + b["w"] * (0.32 + 0.26 * i)
        c = color if i == 1 else hex2rgb(THEME["muted"])
        dr.rectangle([cx - bw / 2, base_y - h, cx + bw / 2, base_y], fill=c)
        dr.text((cx, base_y + 14), format_compact_num(v), font=font(20),
                fill=hex2rgb(THEME["ink"]), anchor="mm")
    dr.line([b["x"] + b["w"] * 0.12, base_y, b["x"] + b["w"] * 0.88, base_y],
            fill=hex2rgb(THEME["muted"]), width=2)


# ---------------------------------------------------------------- 场景装配

def _draw_growth(dr, b, value, vmax, color):
    """P2-2 Phase-1：单实体数值「增长」——一根柱，高度按 value 连续插值。

    State-driven：调用方每帧传入由 State Delta 采样出的 value（见 state_delta.py），
    渲染器本身只负责把该 value 画成真实像素。既有 kind（donut/bars）行为不变。
    """
    base_y = b["y"] + b["h"] * 0.90
    top_y = b["y"] + b["h"] * 0.08
    full = base_y - top_y
    frac = 0.0 if vmax <= 0 else max(0.0, min(1.0, value / float(vmax)))
    h = full * frac
    bw = b["w"] * 0.20
    cx = b["x"] + b["w"] * 0.5
    dr.rectangle([cx - bw / 2, base_y - h, cx + bw / 2, base_y], fill=tuple(color))
    dr.line([b["x"] + b["w"] * 0.12, base_y, b["x"] + b["w"] * 0.88, base_y],
            fill=hex2rgb(THEME["muted"]), width=2)
    dr.text((cx, base_y + 16), format_compact_num(value), font=font(20),
            fill=hex2rgb(THEME["ink"]), anchor="mm")


def _render_scene(beat_dsl, plan_beat, entrance_beat, t,
                  exclude=(), box_override=None):
    """渲染一拍在时刻 t 的完整场景（不含质感后期——后期在 draw_frame 统一做，
    保证跨拍溶解时两帧先合成再一起压暗角/加颗粒）。"""
    img = _theme_bg(beat_dsl.get("palette", "night")).copy()
    dr = ImageDraw.Draw(img)
    st, events = _state(entrance_beat, t)
    fonts = plan_beat["fonts"]
    exclude = set(exclude)

    n_motifs = sum(1 for e in beat_dsl["elements"] if e["type"] == "motif")
    order = {"decor": -1, "shape": 0, "motif": 1, "chart": 1,
             "connector": 2, "text": 3}
    for el in sorted(beat_dsl["elements"],
                     key=lambda e: order.get(e["type"], 9)):
        eid = el["id"]
        if eid in exclude or eid not in plan_beat["boxes"]:
            continue
        s = st.get(eid)
        if not s or s["alpha"] <= 0.0:
            continue
        a = s["alpha"]
        b = dict(box_override[eid]) if box_override and eid in box_override \
            else dict(plan_beat["boxes"][eid])
        b["y"] += s["dy"]
        color = _role_color(el)
        evs = events.get(eid, [])
        tpe = el["type"]
        accent = hex2rgb(THEME["accent"])

        if tpe == "decor":
            if el.get("text"):  # 幽灵大字：衬线特大号，暗底上的浅色淡字
                fs = fonts.get(eid, {"size": 90, "bold": True})
                col = _mix(THEME["bg_top"], THEME["ink"],
                           THEME["ghost_alpha"] * a)
                _draw_text(dr, b, el["text"], fs["size"], True, col,
                           serif=True)
            elif el.get("art"):
                _paste_svg(img, b, el["art"], hex2rgb(THEME["muted"]),
                           a * DECOR_ALPHA)
        elif tpe == "shape":
            _draw_glow_panel(dr, b, el.get("tone", ""), a)
        elif tpe == "motif":
            # v5.1：不再放大成背景水印（旧版把唯一 motif 放大 2.2× 垫在文字
            # 之下，浅底上像一块「背景大图」，且上一支视频的母题会被反复复用）。
            # 现在唯一 motif 也按构图盒子画成前景插图（内容相关的图形），
            # 文字依旧是主角，背景保持纯米白。
            alpha_k = 0.92 if n_motifs == 1 else 0.55
            _paste_svg(img, b, el.get("art") or el.get("motif") or "compass",
                       color, a * alpha_k, scale=s["scale"])
        elif tpe == "connector":
            p = next((p for act, p in evs if act == "draw"), 1.0)
            _draw_arrow(dr, b, _fade(accent, a * 0.85), p)
        elif tpe == "chart":
            ch = el["chart"]
            if ch["kind"] == "growth":
                _draw_growth(dr, b, ch.get("value", 0.0), ch.get("vmax", 100.0),
                             _fade(hex2rgb(COLORS["positive"]), a))
            elif ch["kind"] == "donut":
                p = next((p for act, p in evs if act == "chart_fill"), 1.0)
                _draw_donut(dr, b, ch["value"],
                            _fade(hex2rgb(COLORS["info"]), a), p)
            else:
                p = next((p for act, p in evs if act == "bars_grow"), 1.0)
                _draw_bars(dr, b, ch["before"], ch["after"],
                           _fade(hex2rgb(COLORS["positive"]), a), p)
        elif tpe == "text":
            fs = fonts.get(eid, {"size": 26, "bold": False})
            slot = el.get("slot", "")
            serif = slot in _SERIF_SLOTS
            col = _text_color(el)
            wash = [p for act, p in evs if act == "color_wash"]
            if wash:
                col = _mix(THEME["ink"], color, wash[-1])
            size = fs["size"]
            pulse = [p for act, p in evs if act == "pulse"]
            if pulse and 0.0 < pulse[-1] < 1.0:
                size = size * (1.0 + 0.06 * math.sin(pulse[-1] * math.pi))
            size = _fit_size(dr, el["text"], size * s["scale"],
                             fs.get("bold", False), serif, b["w"] * 0.94)
            ink = _fade(col, a)
            is_primary = el["role"] == "primary" or el.get("emphasis")
            if is_primary:
                _draw_glow(img, b, el["text"], size, True, serif,
                           accent if el.get("emphasis") else col, a)
                dr = ImageDraw.Draw(img)  # glow 之后重建 Draw
            if el.get("boxed"):
                _draw_rules(dr, b, accent, a)
            tracking = 5 if slot == "eyebrow" else 0
            _draw_text(dr, b, el["text"], size,
                       fs.get("bold", False) or bool(el.get("emphasis")),
                       ink, serif=serif, tracking=tracking)
    return img


def draw_frame(beat_dsl, plan_beat, entrance_beat, t, prev=None):
    """Render one absolute-time frame（含跨拍溶解、镜头运动与质感后期）。"""
    start = beat_dsl["start_sec"]
    img = _render_scene(beat_dsl, plan_beat, entrance_beat, t)

    if prev is not None and 0.0 <= t - start < TRANS_SEC:
        q = _ease((t - start) / TRANS_SEC)
        pb, pp, pe = prev
        cur_motifs = {e.get("motif"): e["id"] for e in beat_dsl["elements"]
                      if e["type"] == "motif" and e.get("motif")}
        carried_prev_ids, overrides = [], {}
        for pel in pb["elements"]:
            m = pel.get("motif")
            if pel["type"] == "motif" and m in cur_motifs:
                carried_prev_ids.append(pel["id"])
                cid = cur_motifs[m]
                overrides[cid] = _lerp_box(pp["boxes"][pel["id"]],
                                           plan_beat["boxes"][cid], q)
        prev_img = _render_scene(pb, pp, pe, pb["end_sec"],
                                 exclude=carried_prev_ids)
        if overrides:
            img = _render_scene(beat_dsl, plan_beat, entrance_beat, t,
                                box_override=overrides)
        img = Image.blend(prev_img, img, q)

    camera = beat_dsl.get("camera", {})
    if camera.get("mode") == "push_in":
        dur = max(beat_dsl["end_sec"] - start, 0.01)
        z = 1.0 + 0.06 * _clamp01(
            (t - start - 0.45 * dur) / (0.35 * dur))
        if z > 1.001:
            cw, ch = W / z, H / z
            img = img.crop([(W - cw) / 2, (H - ch) / 2,
                            (W + cw) / 2, (H + ch) / 2]).resize((W, H))
    return _apply_grade(img, t)


def ink_stats(img):
    """(ink_ratio, distinct_colors)。遮幅黑条不算内容，先裁掉。

    「墨迹」判定必须**与主题无关**（v5.0 米白底修复）：不能用「与单一底色
    常量比对」——同样的渐变/暗角在浅底上的绝对像素差远大于暗底，会把整片
    背景误判成墨迹（暗底实测 ~0.3、浅底飙到 0.78）。

    改为高通法：以大幅高斯模糊作为「局部背景估计」，把平滑的渐变、径向暗角
    与胶片颗粒都视为背景；只有与局部背景差异显著的像素（文字、图形、色块
    的真正边缘与填充）才计为内容墨。这条阈值在暗底/浅底上语义一致。
    """
    bar = _grade.letterbox_px(H, THEME)
    body = img.crop([0, bar, W, H - bar])
    small = body.resize((320, 180)).convert("RGB")
    # 局部背景估计：模糊半径远大于内容笔画宽度，抹掉平滑背景、保留内容高频
    bg_est = small.filter(ImageFilter.GaussianBlur(radius=10))
    px = list(small.getdata())
    bpx = list(bg_est.getdata())
    ink = 0
    for p, q in zip(px, bpx):
        if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) > 40:
            ink += 1
    q = body.convert("P", palette=Image.ADAPTIVE, colors=48)
    return ink / float(len(px)), len(q.getcolors())


def render_previews(dsl, render_plan, entrance, out_dir):
    """Render the settle-phase frame of every beat; return per-beat L3 facts."""
    ensure_dir(out_dir)
    plans = {b["beat_id"]: b for b in render_plan["beats"]}
    ents = {b["beat_id"]: b for b in entrance["beats"]}
    report = {}
    for beat in dsl["beats"]:
        dur = max(beat["end_sec"] - beat["start_sec"], 0.01)
        t = beat["start_sec"] + min(0.80 * dur, max(dur - 0.05, 0.0))
        img = draw_frame(beat, plans[beat["beat_id"]], ents[beat["beat_id"]], t)
        bdir = ensure_dir(os.path.join(out_dir, beat["beat_id"]))
        path = os.path.join(bdir, "final-%.1fs.png" % t)
        img.save(path)
        ratio, colors = ink_stats(img)
        report[beat["beat_id"]] = {
            "frame": path, "t": round(t, 2),
            "ink_ratio": round(ratio, 4), "distinct_colors": colors,
        }
    return report
