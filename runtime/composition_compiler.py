"""composition_compiler.py — v7.3 Runtime 的「意图 → 几何」编译器。

Agent 给语义意图（intent_layer），本模块**决定怎么画**：

    intent(grammar/focal/relationship/density/silence/motion_intent)
        ↓  语法→实现 的 1:N 映射（不是「语法==某模板」）
    实现选择器（按 grammar 组合选实现，density/silence 调参）
        ↓  复用 ref_frame 的**规则**（cols/rows/stroke/图标），不写死坐标
    视觉 DSL（ref_frame 图层规范 spec）

设计要点：
  · 坐标来自规则（cols/rows），不是来自 Agent —— 呼应 v7.2「坐标是规则的解」。
  · 「参考帧的那些版式」在这里降级为**语法的实现之一**，由编译器挑，不是 Agent 选。
  · 同一个语法可由不同实现表达；编译器按 density/silence 决定用几槽、多密。
"""
import ref_frame as R

# 语法 → 首选实现（1:N，值是可替换的实现名集合；这里给默认首选）
GRAMMAR_REALIZATION = {
    "establish": ("nodes_center",),
    "hierarchy": ("nodes_row",),
    "causality": ("nodes_row",),
    "progression": ("nodes_row",),
    "juxtapose": ("nodes_row",),
    "contrast": ("nodes_pair",),
    "emphasis": ("nodes_center",),
    "transition": ("nodes_row",),
    "abstract": ("nodes_row",),
    "accumulation": ("accum_trajectory_threshold",),
    "trajectory": ("accum_trajectory_threshold",),
    "threshold": ("accum_trajectory_threshold",),
}


def _title_svg(txt):
    return R._title(txt)


def _slot_count(intent):
    """density → 槽数（Runtime 决定放几个，不是 Agent 指定）。"""
    ents = intent.get("entities") or [intent["focal_point"]]
    n = len(ents)
    if intent.get("silence"):
        return 1
    d = intent.get("density", 0.5)
    if d < 0.4:
        return max(1, min(n, 2))
    if d < 0.7:
        return max(1, min(n, 3))
    return max(1, min(n, 5))


def _nodes_spec(intent, ncols=None):
    """通用实现：把实体排成 cols(n) 卡片行，焦点点亮为唯一强调。"""
    ents = list(intent.get("entities") or [intent["focal_point"]])
    if intent["focal_point"] not in ents:
        ents.append(intent["focal_point"])
    n = ncols or _slot_count(intent)
    ents = ents[:n]
    n = len(ents)
    slots = R.cols(n)
    els = [R._E("title", _title_svg(intent["visual_claim"]), (R.MARGIN - 8, 44, 520, 40), "rise", 0.0)]
    for i, (x, w) in enumerate(slots):
        label = ents[i]
        primary = (label == intent["focal_point"])
        sw, sc = R.stroke("primary" if primary else "secondary")
        cx = x + w / 2
        inner = (f'<rect x="{x:.0f}" y="{R.NODE_Y}" width="{w:.0f}" height="{R.NODE_H}" rx="12" '
                 f'fill="{R.PANEL}" stroke="{sc}" stroke-width="{sw}"/>')
        col = R.INK if primary else R.TMID
        inner += (f'<text x="{cx:.0f}" y="{R.NODE_Y + R.NODE_H - 20:.0f}" text-anchor="middle" '
                  f'fill="{col}" font-size="{15 if primary else 14}" '
                  f'font-weight="{500 if primary else 400}" font-family="{R.FONT}">{R._esc(label)}</text>')
        # 焦点点亮标记（唯一强调）
        if primary:
            inner += (f'<circle cx="{cx:.0f}" cy="{R.NODE_Y + 46:.0f}" r="9" fill="{R.ACC}"/>')
        else:
            inner += (f'<circle cx="{cx:.0f}" cy="{R.NODE_Y + 46:.0f}" r="9" fill="none" '
                      f'stroke="{R.MID}" stroke-width="1.75"/>')
        els.append(R._E(f"node{i}", inner, (x - 2, R.NODE_Y - 2, w + 4, R.NODE_H + 12),
                        "pop", 0.12 + 0.16 * i))
    return R._spec(els)


def _accum_traj_threshold(intent):
    """复合实现：accumulation + trajectory + threshold（用户示例的语法组合）。

    小动作累积（一排渐增短柱）→ 轨迹上升（折线）→ 越过阈值（虚线+标签）。
    焦点 trajectory 是唯一强调；柱/阈值为中性灰。坐标全部由规则常量算出。
    """
    base_y = 300
    x0, x1 = 72, 612
    # 1) 累积：6 根渐增短柱
    nbars = 6
    bw, gap = 20, 16
    bars = ""
    for i in range(nbars):
        h = 14 + i * 11
        bx = x0 + i * (bw + gap)
        bars += (f'<rect x="{bx}" y="{base_y - h}" width="{bw}" height="{h}" rx="3" '
                 f'fill="{R.MUT}" stroke="{R.MID}" stroke-width="1.25"/>')
    # 2) 轨迹：上升折线（焦点，唯一强调）
    pts = [(x0 + 6, 288), (x0 + 150, 268), (x0 + 300, 236),
           (x0 + 450, 196), (x1 - 24, 150)]
    poly = " ".join(f"{px},{py}" for px, py in pts)
    traj = (f'<polyline points="{poly}" fill="none" stroke="{R.ACC}" stroke-width="2.25" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    for px, py in pts:
        traj += f'<circle cx="{px}" cy="{py}" r="3" fill="{R.ACC}"/>'
    # 3) 阈值：虚线（被轨迹越过）
    thr_y = 214
    thr = (f'<line x1="{x0 - 8}" y1="{thr_y}" x2="{x1 + 8}" y2="{thr_y}" stroke="{R.MID}" '
           f'stroke-width="1.75" stroke-dasharray="6 6" stroke-linecap="round"/>'
           f'<text x="{x1 + 8}" y="{thr_y - 8}" text-anchor="end" fill="{R.TMID}" font-size="12" '
           f'font-family="{R.FONT}">阈值</text>')

    els = [
        R._E("title", _title_svg(intent["visual_claim"]), (R.MARGIN - 8, 44, 560, 40), "rise", 0.0),
        R._E("baseline", f'<line x1="{x0}" y1="{base_y}" x2="{x1}" y2="{base_y}" '
             f'stroke="{R.MID}" stroke-width="1.25" stroke-linecap="round"/>',
             (x0 - 6, base_y - 6, x1 - x0 + 12, 14), "draw", 0.08),
        R._E("accumulation", bars, (x0 - 6, 220, x1 - x0, 86), "rise", 0.18),
        R._E("threshold", thr, (x0 - 12, thr_y - 22, x1 - x0 + 30, 40), "draw", 0.62),
        R._E("trajectory", traj, (x0 - 8, 146, x1 - x0 + 16, 150), "draw", 0.80),
    ]
    return R._spec(els)


def _realize(intent, impl_name):
    return {
        "nodes_row": lambda: _nodes_spec(intent),
        "nodes_center": lambda: _nodes_spec(intent, ncols=1),
        "nodes_pair": lambda: _nodes_spec(intent, ncols=min(2, len(intent.get("entities") or [1]))),
        "accum_trajectory_threshold": lambda: _accum_traj_threshold(intent),
    }[impl_name]()


def _choose_realization(intent):
    ops = set(intent.get("grammar", []))
    # 复合语法优先（accumulation/trajectory/threshold 三者共存 → 复合作画）
    if {"accumulation", "trajectory", "threshold"} <= ops:
        return "accum_trajectory_threshold"
    for op in intent.get("grammar", []):
        cands = GRAMMAR_REALIZATION.get(op)
        if cands:
            return cands[0]
    return "nodes_row"


def compile_intent(intent):
    """意图 → 视觉 DSL。返回 (spec, meta)。Runtime 才知道怎么画。"""
    impl = _choose_realization(intent)
    spec = _realize(intent, impl)
    issues = R.audit_spec(spec)
    if R.count_accent(spec) > 1:
        issues.append("accent budget exceeded: %d" % R.count_accent(spec))
    meta = {"beat_id": intent.get("beat_id"), "grammar": intent.get("grammar"),
            "realization": impl, "focal_point": intent.get("focal_point"),
            "density": intent.get("density"), "motion_intent": intent.get("motion_intent"),
            "issues": issues}
    return spec, meta
