"""ref_frame.py — 参考帧构图语法 · 规则引擎（v7.2）

背景：用户给了三张**手写 SVG 信息图**（frame_01_hook / frame_02_cause_chain /
frame_03_comparison）让 Agent「学会」。关键在于区分：

  · **照抄** = 把那三张图原样重画：坐标写死、图标写死、只换颜色。
             换个内容就废、换个列数就崩。这是「模板动物园」。
  · **学会** = 从三张图里抽出**生成规则**（版心 / 分槽 / 描边角色 / 字阶 /
             强调预算 / 图层模型），使同一套规则既能**精确复现**参考帧，
             又能**外推**出作者没画过的构图（5 列、纵向堆叠、四象限、时间轴）。

本模块只保留「规则」，不保留「某一张具体的图」：
  规则0 画布版心    CANVAS_W/H, MARGIN, CONTENT_W
  规则1 分槽        cols(n) / rows(n)        —— n 任意（参考帧只示范过 3 列 / 2 面板）
  规则2 描边角色    stroke(role)             —— 强调 = 加粗 + 加深，不靠换色
  规则3 字阶        type_scale(name)
  规则4 强调预算    count_accent(spec) <= 1  —— 一帧只花一次强调
  规则5 图层模型    _E(...) -> {id,svg,box,motion,at}
  规则6 入场词汇    MOTIONS = rise|fade|pop|draw|grow
  规则7 机器校验    audit_spec(spec)

自证方式：`runtime/self_test.py` 第 16 道门禁用「cols(3) 必须精确等于参考帧坐标」
证明复现，用「cols(4/5) 仍合法」+「四象限/时间轴/清单新构型仍合法」证明泛化。
复现 ≠ 学会；能泛化才是学会。
"""

from procedural_canonical import layout as _layout

# ---------------------------------------------------------------- 设计令牌
BG = "#F3F2EF"; PANEL = "#FAFAF8"; INK = "#2B2B2B"
MID = "#8A8A86"; TMID = "#6B6B67"; ACC = "#C4452B"; MUT = "#D3D2CD"
FONT = "'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif"

# ---------------------------------------------------------------- 规则 0：画布版心
CANVAS_W, CANVAS_H = 680, 382
MARGIN = 48
CONTENT_W = CANVAS_W - 2 * MARGIN          # 584

# ---------------------------------------------------------------- 规则 1 间距令牌（参考帧实测）
COL_GAP = 67                                # 列间距（参考帧三节点实测）
NODE_H = 140                                # 链节点高
NODE_Y = 130                                # 链节点顶
TITLE_Y = 72                                # 顶部标题基线
CAPTION_Y = 344                             # 底部说明基线
FOOT_Y = 332                                # 脚注基线

# ---------------------------------------------------------------- 规则 6：入场词汇
MOTIONS = ("rise", "fade", "pop", "draw", "grow")


def cols(n, x0=MARGIN, total=CONTENT_W, gap=COL_GAP):
    """n 列等宽分槽规则。

    把参考帧的「列宽 + 列距」抽成规则而非写死坐标：
      n = 3 时精确复现参考帧 —— w = 150, x = [48, 265, 482]（与手写 SVG 完全一致）。
    因此同一函数既能复现，又能外推到参考帧没画过的 n（2 / 4 / 5 …）。
    """
    return _layout.slots(n, x0, total, gap)


def rows(n, y0, total, h_gap=COL_GAP):
    """n 行等高分行规则（纵向版 cols，用于参考帧没有的堆叠构型）。

    委托 procedural_canonical.layout.stacks —— 分槽算术只有一个实现。
    """
    return _layout.stacks(n, y0, total, h_gap)


# ---------------------------------------------------------------- 规则 2：描边角色
def stroke(role):
    """强调 = 加粗 + 加深；次级统一同一个灰。返回 (线宽, 颜色)。"""
    return {
        "primary":   (2.25, INK),
        "secondary": (1.25, MID),
        "tertiary":  (1.75, MID),
    }[role]


# ---------------------------------------------------------------- 规则 3：字阶
def type_scale(name):
    """从参考帧抽取的字阶。返回 (size, weight, color)。"""
    return {
        "hero":     (34, 500, INK),
        "title":    (26, 500, INK),
        "node":     (15, 500, INK),
        "node_dim": (14, 400, TMID),
        "body":     (15, 400, TMID),
        "note":     (12, 400, TMID),
        "badge":    (13, 500, "#FFFFFF"),
    }[name]


# ---------------------------------------------------------------- 规则 5：图层模型
_CANVAS = ('<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="764" '
           'viewBox="0 0 680 382" role="img">%s</svg>')


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _E(eid, inner, box, motion, at=None):
    """一个元素 = 一个独立可渲染图层。"""
    return {"id": eid, "svg": _CANVAS % inner, "box": box, "motion": motion, "at": at}


def _spec(elements, bg=BG):
    return {"bg": bg, "elements": elements}


def _place(icon, cx, cy):
    """图标既可为已定位的 SVG 字符串，也可为按 (cx,cy) 定位的工厂函数——
    工厂形式让构图规则自己决定图标位置（这是『学会』而非『贴图』）。"""
    if callable(icon):
        return icon(cx, cy)
    return icon or ""


# ---------------------------------------------------------------- 规则 4：强调预算
def count_accent(spec):
    """一帧里**使用强调色的元素个数**。预算 = 1（一帧一处强调、且只落在一个元素上）。

    注意：一个强调元素内部可以 fill+stroke 同时用强调色（那是同一个元素），
    所以这里数「含强调色的元素」，而不是数颜色串出现次数。
    """
    return sum(1 for el in spec["elements"] if ACC in (el.get("svg") or ""))


# ---------------------------------------------------------------- 规则 7：机器校验
def audit_spec(spec):
    """图层规范机器门禁：可独立渲染 / 框在画布内 / motion 合法 / 强调 <= 1。"""
    issues = []
    els = spec.get("elements")
    if not isinstance(els, list) or not els:
        return ["no elements"]
    seen = set()
    for el in els:
        for k in ("id", "svg", "box", "motion", "at"):
            if k not in el:
                issues.append("element missing %s" % k)
        if el.get("id") in seen:
            issues.append("dup id %s" % el.get("id"))
        seen.add(el.get("id"))
        if el.get("motion") not in MOTIONS:
            issues.append("bad motion %s" % el.get("motion"))
        box = el.get("box")
        if not (isinstance(box, (tuple, list)) and len(box) == 4):
            issues.append("bad box %s" % (box,))
        else:
            x, y, w, h = box
            if x < -2 or y < -2 or x + w > CANVAS_W + 2 or y + h > CANVAS_H + 2:
                issues.append("box out of canvas %s" % (box,))
        svg = el.get("svg") or ""
        if svg.count("<svg") != 1:
            issues.append("element not an independent layer: %s" % el.get("id"))
    if count_accent(spec) > 1:
        issues.append("accent budget exceeded: %d" % count_accent(spec))
    return issues


# ---------------------------------------------------------------- 线稿图标库（参数化图元）
def icon_bell(cx, cy, s, col=MID):
    return (f'<g transform="translate({cx},{cy}) scale({s})" fill="none" '
            f'stroke="{col}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M-16 12 Q-16 -16 0 -20 Q16 -16 16 12 L23 20 L-23 20 Z"/>'
            f'<line x1="0" y1="-20" x2="0" y2="-27"/>'
            f'<path d="M-7 26 Q0 34 7 26"/>'
            f'<path d="M29 -8 Q35 0 29 8" stroke-width="1.25"/>'
            f'<path d="M-29 -8 Q-35 0 -29 8" stroke-width="1.25"/></g>')


def icon_focus_break(cx, cy, s, col=INK, acc=ACC):
    return (f'<g transform="translate({cx},{cy}) scale({s})" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f'<line x1="-42" y1="0" x2="-14" y2="0" stroke="{col}" stroke-width="2.25"/>'
            f'<path d="M-8 -12 L-2 0 L-10 0 L-4 12" stroke="{acc}" stroke-width="2.25"/>'
            f'<line x1="6" y1="0" x2="42" y2="0" stroke="{MID}" stroke-width="1.75" stroke-dasharray="3 5"/></g>')


def icon_bar_half(cx, cy, s, col=MID, fill=MID):
    return (f'<g transform="translate({cx},{cy}) scale({s})" fill="none">'
            f'<rect x="-40" y="-7" width="80" height="14" rx="7" stroke="{col}" stroke-width="1.75"/>'
            f'<rect x="-37" y="-4" width="30" height="8" rx="4" fill="{fill}"/>'
            f'<line x1="-40" y1="17" x2="-40" y2="23" stroke="{col}" stroke-width="1.25" stroke-linecap="round"/>'
            f'<line x1="0" y1="17" x2="0" y2="23" stroke="{col}" stroke-width="1.25" stroke-linecap="round"/>'
            f'<line x1="40" y1="17" x2="40" y2="23" stroke="{col}" stroke-width="1.25" stroke-linecap="round"/></g>')


def icon_door(cx, cy, s, col=INK):
    return (f'<g transform="translate({cx},{cy}) scale({s})" fill="none" '
            f'stroke="{col}" stroke-width="1.75" stroke-linejoin="round">'
            f'<path d="M-22 31 V-21 Q-22 -31 -12 -31 H12 Q22 -31 22 -21 V31"/>'
            f'<circle cx="12" cy="1" r="2.5" fill="{col}" stroke="none"/></g>')


def icon_phone(cx, cy, s, col=INK, badge=None):
    g = (f'<g transform="translate({cx},{cy}) scale({s})" fill="none" stroke-linecap="round">'
         f'<rect x="-59" y="-115" width="118" height="230" rx="18" fill="{PANEL}" '
         f'stroke="{col}" stroke-width="2"/>'
         f'<line x1="-15" y1="-102" x2="15" y2="-102" stroke="{MID}" stroke-width="1.25"/>'
         f'<rect x="-49" y="-87" width="98" height="190" rx="8" stroke="{MID}" stroke-width="1.25"/>')
    ys = [-75, -33, 9]
    for i, y in enumerate(ys):
        sc = col if i == 0 else MID
        sw = 1.75 if i == 0 else 1.25
        g += (f'<rect x="-41" y="{y}" width="82" height="32" rx="6" stroke="{sc}" stroke-width="{sw}"/>'
              f'<circle cx="-26" cy="{y + 16}" r="6" stroke="{sc}" stroke-width="{1.5 if i == 0 else 1.25}"/>'
              f'<line x1="-14" y1="{y + 11}" x2="27" y2="{y + 11}" stroke="{sc}" stroke-width="{1.5 if i == 0 else 1.25}"/>'
              f'<line x1="-14" y1="{y + 21}" x2="12" y2="{y + 21}" stroke="{MID}" stroke-width="1.25"/>')
    g += '</g>'
    if badge is not None:
        g += (f'<circle cx="{cx + 59 * s}" cy="{cy - 115 * s}" r="{12 * s}" fill="{ACC}"/>'
              f'<text x="{cx + 59 * s}" y="{cy - 115 * s + 5 * s}" text-anchor="middle" fill="#FFFFFF" '
              f'font-size="{13 * s:.0f}" font-weight="500" font-family="{FONT}">{_esc(badge)}</text>')
    return g


def _title(txt, y=TITLE_Y, size=26):
    return (f'<text x="{MARGIN}" y="{y}" fill="{INK}" font-size="{size}" font-weight="500" '
            f'font-family="{FONT}">{_esc(txt)}</text>')


def _caption(txt, y=CAPTION_Y, size=12):
    return (f'<text x="{MARGIN}" y="{y}" fill="{TMID}" font-size="{size}" '
            f'font-family="{FONT}">{_esc(txt)}</text>')


# ================================================================ 版式 = 规则调用示例
# 下面每个 frame_* 都只是「规则」的调用示例，不再含写死版式坐标。
# 其中 frame_quadrants / frame_timeline / frame_stack 是**参考帧里没有**的构型，
# 全部由 cols()/rows() 规则生成 —— 用来证明学到的是规则，不是三张图。

def frame_hero(title, sub, icon, icon_box, underline=True):
    """establish：大问句 + 副题 + 主体意象 + 单强调（复现 frame_01）。"""
    title_size, title_w, title_col = type_scale("hero")
    els = [_E("title", f'<text x="{MARGIN}" y="172" fill="{title_col}" font-size="{title_size}" '
              f'font-weight="{title_w}" font-family="{FONT}">{_esc(title)}</text>',
              (MARGIN - 8, 132, 340, 54), "rise", 0.00)]
    if underline:
        els.append(_E("underline", f'<line x1="{MARGIN}" y1="194" x2="{MARGIN + 64}" y2="194" '
                      f'stroke="{INK}" stroke-width="2" stroke-linecap="round"/>',
                      (MARGIN - 4, 188, 72, 14), "draw", 0.28))
    sub_size, sub_w, sub_col = type_scale("body")
    els.append(_E("sub", f'<text x="{MARGIN}" y="226" fill="{sub_col}" font-size="{sub_size}" '
                 f'font-family="{FONT}">{_esc(sub)}</text>', (MARGIN - 8, 206, 330, 30), "rise", 0.46))
    els.append(_E("icon", _place(icon, 500, 200), icon_box, "pop", 0.36))
    return _spec(els)


def frame_statement(lines, caption=None, size=30):
    """纯命题大字（established 的极简版）。lines = [(txt, accent)]。"""
    els = []
    y0 = CANVAS_H / 2 - (len(lines) - 1) * size * 0.7
    for i, (txt, accent) in enumerate(lines):
        yi = y0 + i * size * 1.45
        col = ACC if accent else INK
        els.append(_E(f"line{i}", f'<text x="{CANVAS_W / 2:.0f}" y="{yi:.0f}" text-anchor="middle" '
                      f'fill="{col}" font-size="{size}" font-weight="{500 if accent else 400}" '
                      f'font-family="{FONT}">{_esc(txt)}</text>',
                      (40, yi - size, 600, size * 1.5), "rise", 0.0 + i * 0.45))
    if caption:
        els.append(_E("caption", _caption(caption), (MARGIN - 8, CAPTION_Y - 14, 430, 26), "rise", 0.9))
    return _spec(els)


def frame_chain(title, nodes, caption=None):
    """causality / progression：n 节点横排 + (n-1) 连接箭头。

    nodes = [(label, icon|factory, primary)]。n **不再写死为 3**：由 cols(n) 分槽，
    n = 3 时精确复现 frame_02。
    """
    els = [_E("title", _title(title), (MARGIN - 8, 44, 440, 40), "rise", 0.00)]
    n = len(nodes)
    slots = cols(n)
    for i, (x, w) in enumerate(slots):
        label = nodes[i][0]
        icon = nodes[i][1] if len(nodes[i]) > 1 else ""
        primary = nodes[i][2] if len(nodes[i]) > 2 else False
        sw, sc = stroke("primary" if primary else "secondary")
        cxi = x + w / 2
        inner = (f'<rect x="{x:.0f}" y="{NODE_Y}" width="{w:.0f}" height="{NODE_H}" rx="12" '
                 f'fill="{PANEL}" stroke="{sc}" stroke-width="{sw}"/>')
        inner += _place(icon, cxi, NODE_Y + NODE_H / 2 - 10)
        col = INK if primary else TMID
        inner += (f'<text x="{cxi:.0f}" y="{NODE_Y + NODE_H - 20:.0f}" text-anchor="middle" fill="{col}" '
                  f'font-size="{15 if primary else 14}" font-weight="{500 if primary else 400}" '
                  f'font-family="{FONT}">{_esc(label)}</text>')
        els.append(_E(f"node{i}", inner, (x - 2, NODE_Y - 2, w + 4, NODE_H + 12), "pop", 0.15 + 0.25 * i))

    def _arrow(x0, x1, y):
        return (f'<line x1="{x0:.0f}" y1="{y:.0f}" x2="{x1 - 4:.0f}" y2="{y:.0f}" stroke="{MID}" '
                f'stroke-width="1.5" stroke-linecap="round"/>'
                f'<path d="M{x1 - 10:.0f} {y - 5:.0f} L{x1:.0f} {y:.0f} L{x1 - 10:.0f} {y + 5:.0f}" fill="none" '
                f'stroke="{MID}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')

    for i in range(n - 1):
        a0 = slots[i][0] + slots[i][1] + 8
        a1 = slots[i + 1][0] - 8
        y = NODE_Y + NODE_H / 2
        els.append(_E(f"arrow{i}", _arrow(a0, a1, y), (a0 - 4, y - 12, (a1 - a0) + 12, 24),
                      "draw", 0.52 + 0.26 * i))
    if caption:
        els.append(_E("caption", _caption(caption, y=FOOT_Y, size=14),
                      (MARGIN - 8, FOOT_Y - 14, 440, 26), "rise", 0.98))
    return _spec(els)


def frame_bar_detail(title, value_pct, caption=None, label=None):
    """单进度条详情（复现/细化 frame_02 第三节点的编码方式）。"""
    bx, by, bw, bh = 140, 190, 400, 40
    els = [_E("title", _title(title), (40, 44, 340, 40), "rise", 0.00)]
    if label:
        els.append(_E("label", f'<text x="{bx}" y="{by - 18}" fill="{TMID}" font-size="14" '
                      f'font-family="{FONT}">{_esc(label)}</text>', (bx, by - 40, 220, 28), "rise", 0.20))
    els.append(_E("track", f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="20" '
                 f'fill="{PANEL}" stroke="{MID}" stroke-width="1.75"/>', (bx, by, bw, bh), "fade", 0.15))
    els.append(_E("fill", f'<rect x="{bx + 3}" y="{by + 3}" width="{(bw - 6) * value_pct:.0f}" '
                 f'height="{bh - 6}" rx="18" fill="{ACC}"/>', (bx, by, bw, bh), "grow", 0.35))
    ticks = "".join(f'<line x1="{bx + bw * i / 5:.0f}" y1="{by + bh + 10}" x2="{bx + bw * i / 5:.0f}" '
                    f'y2="{by + bh + 20}" stroke="{MID}" stroke-width="1.25" stroke-linecap="round"/>'
                    for i in range(6))
    els.append(_E("ticks", ticks, (bx - 4, by + bh + 6, bw + 8, 22), "draw", 0.70))
    if caption:
        els.append(_E("caption", _caption(caption), (MARGIN - 8, CAPTION_Y - 14, 430, 26), "rise", 0.90))
    return _spec(els)


def frame_compare(title, left, right, caption=None):
    """contrast：双面板 + 基线柱（复现 frame_03）。面板由 cols(2, gap=32) 规则生成。"""
    els = [_E("title", _title(title), (40, 44, 320, 40), "rise", 0.00)]
    panels = cols(2, gap=32)                 # x = [48, 356] w = 276
    roles = ("secondary", "primary")         # 右面板为主
    for i, (px, pw) in enumerate(panels):
        sw, sc = stroke(roles[i])
        els.append(_E(f"panel_{'lr'[i]}",
                      f'<rect x="{px:.0f}" y="104" width="{pw:.0f}" height="204" rx="12" '
                      f'fill="{PANEL}" stroke="{sc}" stroke-width="{sw}"/>',
                      (px, 104, pw, 204), "fade", 0.00 + 0.15 * i))
        els.append(_E(f"base_{'lr'[i]}",
                      f'<line x1="{px + 20:.0f}" y1="276" x2="{px + pw - 20:.0f}" y2="276" '
                      f'stroke="{MID}" stroke-width="1.25" stroke-linecap="round"/>',
                      (px + 12, 270, pw - 24, 14), "draw", 0.25 + 0.10 * i))
    for name, side, i in (("bar_l", left, 0), ("bar_r", right, 1)):
        px = panels[i][0]
        h = side["bar"]; y = 276 - h
        col = ACC if side.get("bar_accent") else MUT
        sc = ACC if side.get("bar_accent") else MID
        x0 = px + 60
        els.append(_E(name, f'<rect x="{x0}" y="{y}" width="64" height="{h}" rx="4" '
                     f'fill="{col}" stroke="{sc}" stroke-width="1.25"/>',
                     (x0 - 4, y - 2, 72, h + 6), "grow", 0.40 if i == 0 else 0.55))
    els.append(_E("icon_l", _place(left["icon_inner"], 0, 0), left["icon_box"], "pop", 0.62))
    els.append(_E("icon_r", _place(right["icon_inner"], 0, 0), right["icon_box"], "pop", 0.74))
    els.append(_E("lab_l", f'<text x="{panels[0][0] + 20:.0f}" y="134" fill="{TMID}" font-size="14" '
                 f'font-family="{FONT}">{_esc(left["label"])}</text>', (panels[0][0] + 12, 118, 200, 30), "rise", 0.50))
    els.append(_E("lab_r", f'<text x="{panels[1][0] + 20:.0f}" y="134" fill="{INK}" font-size="15" '
                 f'font-weight="500" font-family="{FONT}">{_esc(right["label"])}</text>',
                 (panels[1][0] + 12, 116, 250, 30), "rise", 0.62))
    els.append(_E("foot_l", f'<text x="{panels[0][0] + 20:.0f}" y="298" fill="{TMID}" font-size="12" '
                 f'font-family="{FONT}">专注时长</text>', (panels[0][0] + 16, 286, 90, 22), "rise", 0.80))
    els.append(_E("foot_r", f'<text x="{panels[1][0] + 20:.0f}" y="298" fill="{TMID}" font-size="12" '
                 f'font-family="{FONT}">专注时长</text>', (panels[1][0] + 16, 286, 90, 22), "rise", 0.84))
    if caption:
        els.append(_E("caption", _caption(caption), (MARGIN - 8, CAPTION_Y - 14, 440, 26), "rise", 0.92))
    return _spec(els)


# ---------------------------------------------------------------- 参考帧没有的新构型（泛化证明）
def frame_quadrants(title, cells, caption=None):
    """新构型：2×2 四象限卡片。由 cols(2) + rows(2) 规则生成（参考帧没有）。"""
    els = [_E("title", _title(title), (MARGIN - 8, 44, 420, 40), "rise", 0.00)]
    cxs = cols(2, gap=32)
    rys = rows(2, 104, 196, h_gap=20)       # y = [104, 212] h = 88
    i = 0
    for rx, rw in cxs:
        for ry, rh in rys:
            label, icon, primary = (cells[i] if i < len(cells) else ("", "", False))
            sw, sc = stroke("primary" if primary else "secondary")
            cx = rx + rw / 2
            cy = ry + rh / 2 - 10
            inner = (f'<rect x="{rx:.0f}" y="{ry:.0f}" width="{rw:.0f}" height="{rh:.0f}" rx="12" '
                     f'fill="{PANEL}" stroke="{sc}" stroke-width="{sw}"/>')
            inner += _place(icon, cx, cy)
            col = INK if primary else TMID
            inner += (f'<text x="{cx:.0f}" y="{ry + rh - 12:.0f}" text-anchor="middle" fill="{col}" '
                      f'font-size="{15 if primary else 14}" font-weight="{500 if primary else 400}" '
                      f'font-family="{FONT}">{_esc(label)}</text>')
            els.append(_E(f"cell{i}", inner, (rx - 2, ry - 2, rw + 4, rh + 4), "pop", 0.10 + 0.14 * i))
            i += 1
    if caption:
        els.append(_E("caption", _caption(caption), (MARGIN - 8, CAPTION_Y - 14, 440, 26), "rise", 0.92))
    return _spec(els)


def frame_timeline(title, stops, caption=None):
    """新构型：水平时间轴 + n 个等距刻度。由『等距分点』规则生成（参考帧没有）。"""
    els = [_E("title", _title(title), (MARGIN - 8, 44, 420, 40), "rise", 0.00)]
    axis_y = 200
    x0, x1 = MARGIN + 12, CANVAS_W - MARGIN - 12
    els.append(_E("axis", f'<line x1="{x0}" y1="{axis_y}" x2="{x1}" y2="{axis_y}" stroke="{MID}" '
                 f'stroke-width="1.5" stroke-linecap="round"/>',
                 (x0 - 4, axis_y - 10, x1 - x0 + 8, 20), "draw", 0.10))
    n = len(stops)
    for i, stop in enumerate(stops):
        label = stop[0]
        icon = stop[1] if len(stop) > 1 else ""
        primary = stop[2] if len(stop) > 2 else False
        cx = x0 + (x1 - x0) * i / max(n - 1, 1)
        col = ACC if primary else MID
        inner = (f'<circle cx="{cx:.0f}" cy="{axis_y}" r="8" fill="{PANEL}" '
                 f'stroke="{col}" stroke-width="{2.25 if primary else 1.75}"/>')
        inner += _place(icon, cx, axis_y - 40)
        inner += (f'<text x="{cx:.0f}" y="{axis_y + 34:.0f}" text-anchor="middle" '
                  f'fill="{INK if primary else TMID}" font-size="{15 if primary else 14}" '
                  f'font-weight="{500 if primary else 400}" font-family="{FONT}">{_esc(label)}</text>')
        els.append(_E(f"stop{i}", inner, (cx - 44, axis_y - 52, 88, 96), "pop", 0.20 + 0.15 * i))
    if caption:
        els.append(_E("caption", _caption(caption), (MARGIN - 8, CAPTION_Y - 14, 440, 26), "rise", 0.94))
    return _spec(els)


def frame_stack(title, items, caption=None):
    """新构型：纵向清单卡片。由 rows(n) 规则生成（参考帧没有）。"""
    els = [_E("title", _title(title), (MARGIN - 8, 44, 420, 40), "rise", 0.00)]
    rys = rows(len(items), 116, 180, h_gap=16)
    for i, (y, h) in enumerate(rys):
        label = items[i][0]
        icon = items[i][1] if len(items[i]) > 1 else ""
        primary = items[i][2] if len(items[i]) > 2 else False
        sw, sc = stroke("primary" if primary else "secondary")
        inner = (f'<rect x="{MARGIN}" y="{y:.0f}" width="{CONTENT_W}" height="{h:.0f}" rx="12" '
                 f'fill="{PANEL}" stroke="{sc}" stroke-width="{sw}"/>')
        inner += _place(icon, MARGIN + 40, y + h / 2)
        tx = MARGIN + 72 if icon else MARGIN + 24
        inner += (f'<text x="{tx}" y="{y + h / 2 + 5:.0f}" fill="{INK if primary else TMID}" '
                  f'font-size="{15 if primary else 14}" font-weight="{500 if primary else 400}" '
                  f'font-family="{FONT}">{_esc(label)}</text>')
        els.append(_E(f"row{i}", inner, (MARGIN - 2, y - 2, CONTENT_W + 4, h + 4), "fade", 0.12 + 0.14 * i))
    if caption:
        els.append(_E("caption", _caption(caption), (MARGIN - 8, CAPTION_Y - 14, 440, 26), "rise", 0.94))
    return _spec(els)
