"""Stage 6 — 生成后契约（v6.0）。

用户需求（静音信息图的「生成 → 检查 → 定位 → 修复」闭环）：

1. 每拍声明 **end_state**（visible / positions / hold_ms）与 **transition_in**
   （carry / cut / dissolve 三选一，且必须写 reason）。下一拍必须接得上，
   或显式声明清场（cut）。
2. 转场三类型机器检查：
   - carry    : 元素跨拍保留 —— 元素 ID 必须在上一拍 end_state 里；
                位置变化要么在容差内，要么声明了 transform。
   - cut      : 全部清场再入新画面 —— 新旧构图必须有差异（布局模板或主体位置变化），
                否则报错「这不是转场，只是闪一下」。
   - dissolve : 溶解交接 —— 必须至少有一个 carried 元素，避免空溶解。
3. 静音停留下限 —— 每拍结束前 hold ≥ 字幕阅读所需时间的比例；低于下限直接阻断
   （「画面一闪而过」是静音信息图最常见的失败）。
4. 视线路径 attention_path —— ≤4，顺序 = 入场波次时间序，primary 必在路径内且最强。
5. ambient 持续微动 —— 主元素禁止 ambient；幅度上限；久静标警告。
6. 反空话过滤 —— 视觉命题禁「高级感/科技感/震撼/有张力」等，要求可画描述。

本模块只做「派生 + 校验」，不改画面：派生给出可满足的契约，校验独立复核。
"""
import json
import os

# ---- 可调参数（用样例试出来的系数）----
CPS_READ = 5.2          # 中文阅读速度（字/秒）
HOLD_RATIO = 0.22       # 要求 hold ≥ min(阅读时间, 本拍时长) × 该比例（样例试出）
HOLD_FLOOR_S = 0.45     # 绝对下限（秒）
HOLD_CAP_S = 7.0        # 长句封顶
POS_TOL_NORM = 0.070    # 位置容差（归一化：占画布宽/高比例）
AMBIENT_AMP_MAX = 0.030 # ambient 幅度上限（归一化）
STILL_WARN_S = 3.0      # 连续静止超过该值 → 警告

BANNED_CLAIM_WORDS = ("高级感", "科技感", "震撼", "有张力", "氛围感",
                      "未来感", "质感", "大气的", "史诗", "酷炫")

TRANSITION_TYPES = ("carry", "cut", "dissolve")


# ------------------------------------------------------------------ helpers
def _boxes(render_plan):
    return {b["beat_id"]: b.get("boxes", {}) for b in render_plan["beats"]}


def _life(entrance):
    return {b["beat_id"]: b.get("lifecycle", {}) for b in entrance["beats"]}


def _norm_pos(box, W, H):
    return [round(box["x"] / W, 4), round(box["y"] / H, 4)]


def _area(box):
    return box.get("w", 0) * box.get("h", 0)


def _read_time_s(narration):
    n = len([c for c in narration if not c.isspace()])
    return min(n / CPS_READ, HOLD_CAP_S)


# ------------------------------------------------------------------ derive
def derive(dsl, render_plan, entrance, W, H):
    """派生每拍 end_state / transition_in / attention_path / ambient。"""
    from common import PALETTES  # noqa

    boxes = _boxes(render_plan)
    life = _life(entrance)
    beats = dsl["beats"]
    out = []

    for i, b in enumerate(beats):
        bid = b["beat_id"]
        start, end = b["start_sec"], b["end_sec"]
        dur = max(end - start, 1e-3)
        lb = life.get(bid, {})
        bx = boxes.get(bid, {})

        # --- end_state.visible：结束时仍可见的元素 ---
        visible, positions = [], {}
        settle = start
        for e in b["elements"]:
            eid = e["id"]
            l = lb.get(eid)
            if not l:
                continue
            en = l.get("enter") or {}
            ex = l.get("exit")
            ent_at = en.get("at", start)
            ent_end = ent_at + en.get("dur", 0.0)
            if ent_at <= end + 1e-6 and (ex is None or ex.get("at", end) >= end - 1e-6):
                visible.append(eid)
                if eid in bx:
                    positions[eid] = _norm_pos(bx[eid], W, H)
                settle = max(settle, ent_end)
        hold_s = max(0.0, end - settle)
        hold_ms = int(round(hold_s * 1000))

        # --- attention_path：入场时间序，≤4，primary 必在 ---
        # 只纳入「有信息量」的元素（文字 / 主体 / 图表 / 连接件），
        # 排除装饰与 ambient 陪衬 —— 那不该是观众的阅读顺序。
        def _meaningful(e):
            return e.get("type") != "decor" and e.get("role") != "ambient"
        prim = _primary_id(b, bx)
        ordered = []
        for e in b["elements"]:
            if not _meaningful(e):
                continue
            l = lb.get(e["id"])
            if l and l.get("enter"):
                ordered.append((l["enter"].get("at", start), e["id"]))
        ordered.sort(key=lambda t: (t[0], t[1]))
        path = [eid for _, eid in ordered][:4]
        if prim and prim not in path:
            path = (path[:3] + [prim])[:4]

        # --- ambient：仅装饰元素 ---
        ambient = {}
        for e in b["elements"]:
            if e.get("role") == "ambient":
                ambient[e["id"]] = {"kind": "drift",
                                    "amp": round(AMBIENT_AMP_MAX * 0.5, 4)}

        out.append({
            "beat_id": bid,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "primary": prim,
            "attention_path": path,
            "end_state": {"visible": visible, "positions": positions,
                          "hold_ms": hold_ms},
            "ambient": ambient,
            "trailing_still_s": round(hold_s, 3),
        })

    # --- transition_in：逐拍推导 ---
    for i, c in enumerate(out):
        if i == 0:
            c["transition_in"] = {"type": "cut", "carried": [],
                                  "reason": "开场：全清场建立首个画面"}
            continue
        prev = out[i - 1]
        cur = c
        prev_ids = set(prev["end_state"]["visible"])
        cur_ids = set(cur["end_state"]["visible"])
        carried = sorted(prev_ids & cur_ids)
        cur_b = beats[i]
        prev_b = beats[i - 1]
        same_template = cur_b.get("strategy") == prev_b.get("strategy")
        p_prev = _primary_pos(prev)
        p_cur = _primary_pos(cur)
        moved = _dist(p_prev, p_cur)
        if carried:
            # 有保留元素：位置稳 → carry；位置变 → dissolve（溶解交接）
            stable = all(
                _dist(prev["end_state"]["positions"].get(e),
                      cur["end_state"]["positions"].get(e)) <= POS_TOL_NORM
                for e in carried
            )
            if stable:
                c["transition_in"] = {
                    "type": "carry", "carried": carried,
                    "reason": "跨拍保留：%s 延续上一拍末态位置" % ",".join(carried[:3]),
                    "transform": "inherit"}
            else:
                c["transition_in"] = {
                    "type": "dissolve", "carried": carried,
                    "reason": "保留 %s 并溶解到新构图" % ",".join(carried[:3]),
                    "transform": "reflow"}
        else:
            # 全清场：必须有构图差异
            c["transition_in"] = {
                "type": "cut", "carried": [],
                "reason": "清场切镜：%s → %s" % (
                    prev_b.get("strategy"), cur_b.get("strategy")),
                "composition_changed": (not same_template) or (moved > POS_TOL_NORM),
                "moved": round(moved, 4)}
    return out


def _primary_id(beat, boxes):
    for e in beat["elements"]:
        if e.get("role") == "primary":
            return e["id"]
    # 无显式 primary：取面积最大者
    best, bid = -1, None
    for e in beat["elements"]:
        if e["id"] in boxes:
            a = _area(boxes[e["id"]])
            if a > best:
                best, bid = a, e["id"]
    return bid


def _primary_pos(c):
    pid = c["primary"]
    return c["end_state"]["positions"].get(pid) if pid else None


def _dist(a, b):
    if not a or not b:
        return 0.0
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


# ------------------------------------------------------------------ validate
def validate(dsl, contracts, W, H):
    """独立校验派生/手写的契约。返回 audit dict。"""
    issues = []
    beats = dsl["beats"]
    cbeats = {c["beat_id"]: c for c in contracts}
    for i, b in enumerate(beats):
        bid = b["beat_id"]
        c = cbeats.get(bid)
        if not c:
            issues.append(_iss("ERR", "CONTRACT_MISSING", bid, "缺少契约"))
            continue
        es = c.get("end_state", {})
        vis = es.get("visible", [])

        # 3. 停留下限：min(阅读时间, 本拍时长) × 比例，低于即阻断
        rt = _read_time_s(b.get("narration", ""))
        dur = max(b["end_sec"] - b["start_sec"], 1e-3)
        need_s = max(HOLD_FLOOR_S, min(rt, dur) * HOLD_RATIO)
        have_s = es.get("hold_ms", 0) / 1000.0
        if have_s + 1e-6 < need_s:
            issues.append(_iss("ERR", "HOLD_TOO_SHORT", bid,
                               "hold %.2fs < 下限 %.2fs（min(阅读%.2fs,时长%.2fs)×%.2f）"
                               % (have_s, need_s, rt, dur, HOLD_RATIO)))

        # 4. 视线路径
        path = c.get("attention_path", [])
        prim = c.get("primary")
        if len(path) > 4:
            issues.append(_iss("ERR", "PATH_TOO_LONG", bid, "路径 %d>4" % len(path)))
        if prim and prim not in path:
            issues.append(_iss("ERR", "PRIMARY_NOT_IN_PATH", bid,
                               "primary %s 不在视线路径" % prim))

        # 5. ambient
        for eid, amb in (c.get("ambient") or {}).items():
            if eid == prim:
                issues.append(_iss("ERR", "AMBIENT_ON_PRIMARY", bid,
                                   "主元素 %s 不允许 ambient" % eid))
            if amb.get("amp", 0) > AMBIENT_AMP_MAX + 1e-9:
                issues.append(_iss("ERR", "AMBIENT_OVER_AMP", bid,
                                   "ambient 幅度 %.3f>%.3f" % (amb["amp"], AMBIENT_AMP_MAX)))
        if c.get("trailing_still_s", 0) > STILL_WARN_S and not c.get("ambient"):
            issues.append(_iss("WARN", "LONG_STILL", bid,
                               "连续静止 %.1fs 无 ambient" % c["trailing_still_s"]))

        # 2. transition_in
        tr = c.get("transition_in", {})
        t = tr.get("type")
        if t not in TRANSITION_TYPES:
            issues.append(_iss("ERR", "TRANSITION_TYPE", bid, "非法类型 %r" % t))
            continue
        if not tr.get("reason"):
            issues.append(_iss("ERR", "TRANSITION_NO_REASON", bid, "未写 reason"))
        if i == 0:
            continue
        prev = cbeats[beats[i - 1]["beat_id"]]
        prev_ids = set(prev.get("end_state", {}).get("visible", []))
        carried = tr.get("carried", [])
        if t == "carry":
            for e in carried:
                if e not in prev_ids:
                    issues.append(_iss("ERR", "CARRY_NOT_IN_PREV", bid,
                                       "%s 不在上一拍 end_state" % e))
            # 位置容差或 transform
            if not tr.get("transform"):
                for e in carried:
                    d = _dist(prev["end_state"]["positions"].get(e),
                              es.get("positions", {}).get(e))
                    if d > POS_TOL_NORM:
                        issues.append(_iss("ERR", "CARRY_POS_DRIFT", bid,
                                           "%s 位移 %.3f>%.3f 且未声明 transform" %
                                           (e, d, POS_TOL_NORM)))
        elif t == "dissolve":
            if not carried:
                issues.append(_iss("ERR", "EMPTY_DISSOLVE", bid, "空溶解：无 carried"))
        elif t == "cut":
            if not tr.get("composition_changed"):
                issues.append(_iss("ERR", "CUT_NO_DIFF", bid,
                                   "这不是转场，只是闪一下（构图无差异）"))

    blocking = [i for i in issues if i["severity"] != "warn"]
    return {"status": "PASS" if not blocking else "FAIL", "issues": issues}


def _iss(sev, code, bid, msg):
    return {"severity": sev.lower(), "layer": "contract", "code": code,
            "beat_id": bid, "msg": msg}


# ------------------------------------------------------------------ anti-cliché
def check_claims(dsl):
    """反空话过滤：视觉命题 / 关键文本不得含空泛词。"""
    issues = []
    for b in dsl["beats"]:
        texts = [b.get("visual_claim", "")]
        for e in b["elements"]:
            if e.get("type") == "text":
                texts.append(e.get("text", ""))
        for t in texts:
            for w in BANNED_CLAIM_WORDS:
                if w in t:
                    issues.append(_iss("ERR", "CLICHE_CLAIM", b["beat_id"],
                                       "空泛词「%s」：请改成可画描述" % w))
    return issues


def load_tokens(root):
    p = os.path.join(root, "runtime", "style_tokens.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)
