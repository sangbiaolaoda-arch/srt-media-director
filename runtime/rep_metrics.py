"""Stage 7.5 — 重复感量化门禁（REP）。

把「画面重复 / 没有随机感」这种主观感觉变成机器可查的指标。设计原则
（对齐 SKILL「可验证优先」）：

1. 每个指标都能被单独解释，且能回溯到上游哪一层该修（模板 / 构图 /
   调色板 / 装饰），而不是给一个黑盒分数。
2. 阈值分 WARN / FAIL 两级；FAIL 让 L2 门禁整体不通过，WARN 只记录。
3. 指标只读产物 JSON（dsl / render-plan），不读像素——跨渲染器一致。

指标：
- template_run        同一构图模板连续使用的最大拍数
- template_entropy    模板分布的归一化香农熵（1=完全均匀，0=单一模板）
- adjacent_similarity 相邻拍相似度（模板/区域/调色板/装饰 加权和）
- palette_spread      最大调色板占比 & 出现的调色板种类数
- decor_cooldown      装饰画法重复出现的最小间隔拍数

纯函数，无副作用；`evaluate()` 返回结构供 validator 写入 L2 报告。
"""
import math
from collections import Counter

# --- 阈值（v5.0 基线；随样例库回归标定） -------------------------------------
THRESHOLDS = {
    "template_run":        {"limit": 2,    "level": "FAIL"},
    "template_entropy":    {"min": 1.2,    "level": "WARN"},
    "adjacent_similarity": {"warn": 0.60,  "fail": 0.78, "level": "FAIL"},
    "palette_max_share":   {"max": 0.60,   "level": "WARN"},
    "palette_min_kinds":   {"min": 2,      "level": "WARN"},
    "decor_cooldown":      {"min_gap": 1,  "level": "WARN"},
}

# adjacent_similarity 的加权方案（可解释：模板权重最高，装饰最低）
ADJ_WEIGHTS = {"template": 0.40, "region": 0.30, "palette": 0.15, "decor": 0.15}

_MOTIF_TYPES = ("motif", "decor")


def _entropy(counts, total):
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / float(total)
            h -= p * math.log(p)
    # 归一化：除以 log(可能取值数)。这里用实际种类数，衡量「是否均匀」。
    k = len([c for c in counts if c > 0])
    if k <= 1:
        return 0.0
    return h / math.log(k)


def _beat_strategy(b):
    return b.get("strategy") or "unknown"


def _beat_palette(b):
    p = b.get("palette")
    if isinstance(p, dict):
        return p.get("name") or p.get("key") or "custom"
    if isinstance(p, str):
        return p
    return "custom"


def _motifs_of(beat):
    """返回本拍用到的 motif/decor 画法名集合。"""
    out = set()
    for e in beat.get("elements", []):
        if e.get("type") in _MOTIF_TYPES:
            name = e.get("art") or e.get("kind") or e.get("id")
            if name:
                out.add(str(name))
    return out


def _slot_centers(render_beat, dsl_beat):
    """把渲染盒归一化到 [0,1] 画布，按 slot 归组取中心，用于区域相似度。"""
    boxes = render_beat.get("boxes") or {}
    slot_of = {}
    for e in dsl_beat.get("elements", []):
        slot_of[e["id"]] = e.get("slot") or e.get("type") or "x"
    # 画布尺寸从盒子最大值近似（render-plan 用像素坐标，取常识 1280x720）
    W, H = 1280.0, 720.0
    centers = {}
    for eid, box in boxes.items():
        slot = slot_of.get(eid, "x")
        cx = (box.get("x", 0) + box.get("w", 0) / 2.0) / W
        cy = (box.get("y", 0) + box.get("h", 0) / 2.0) / H
        centers.setdefault(slot, []).append((cx, cy))
    # 同 slot 多元素取均值，得到 slot -> 归一化中心
    out = {}
    for slot, pts in centers.items():
        out[slot] = (sum(p[0] for p in pts) / len(pts),
                     sum(p[1] for p in pts) / len(pts))
    return out


def _region_similarity(ca, cb):
    """两个拍的区域布局相似度：共有 slot 中心距离越小越相似。"""
    common = set(ca) & set(cb)
    if not common:
        return 0.0
    d = 0.0
    for slot in common:
        dx = ca[slot][0] - cb[slot][0]
        dy = ca[slot][1] - cb[slot][1]
        d += math.hypot(dx, dy)
    d /= len(common)
    # 距离 0 -> 1.0；距离 >=0.5(半画布) -> 0
    return max(0.0, 1.0 - d / 0.5)


def _jaccard(a, b):
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / float(len(u))


def evaluate(dsl, render_plan):
    """计算全部 REP 指标。返回 dict（含 metrics/warnings/violations）。"""
    beats = dsl.get("beats", [])
    rbeats = {b.get("beat_id"): b for b in render_plan.get("beats", [])}
    n = len(beats)
    metrics = {"beats": n}
    warnings, violations = [], []

    def warn(code, msg):
        warnings.append({"code": code, "msg": msg})

    def fail(code, msg):
        violations.append({"code": code, "msg": msg})

    if n == 0:
        return {"metrics": metrics, "warnings": warnings,
                "violations": violations, "status": "PASS"}

    strategies = [_beat_strategy(b) for b in beats]
    palettes = [_beat_palette(b) for b in beats]

    # 1) template_run —— 最大连续同模板
    run = best = 1
    for i in range(1, n):
        run = run + 1 if strategies[i] == strategies[i - 1] else 1
        best = max(best, run)
    metrics["template_run"] = best
    tr = THRESHOLDS["template_run"]
    if best > tr["limit"]:
        fail("REP_TEMPLATE_RUN",
             "同一模板连续 %d 拍 > 上限 %d（相邻拍需换模板，见 R8 冷却）"
             % (best, tr["limit"]))

    # 2) template_entropy
    cnt = Counter(strategies)
    ent = _entropy(list(cnt.values()), n)
    metrics["template_entropy"] = round(ent, 4)
    metrics["strategy_distribution"] = dict(cnt)
    te = THRESHOLDS["template_entropy"]
    if n >= 4 and ent < te["min"]:
        warn("REP_TEMPLATE_ENTROPY",
             "模板分布熵 %.3f < %.2f：构图过于单一" % (ent, te["min"]))

    # 3) adjacent_similarity
    adj = []
    for i in range(1, n):
        ca = _slot_centers(rbeats.get(beats[i - 1]["beat_id"], {}), beats[i - 1])
        cb = _slot_centers(rbeats.get(beats[i]["beat_id"], {}), beats[i])
        s_tpl = 1.0 if strategies[i] == strategies[i - 1] else 0.0
        s_reg = _region_similarity(ca, cb)
        s_pal = 1.0 if palettes[i] == palettes[i - 1] else 0.0
        s_mot = _jaccard(_motifs_of(beats[i - 1]), _motifs_of(beats[i]))
        sim = (ADJ_WEIGHTS["template"] * s_tpl + ADJ_WEIGHTS["region"] * s_reg +
               ADJ_WEIGHTS["palette"] * s_pal + ADJ_WEIGHTS["decor"] * s_mot)
        adj.append({"pair": [beats[i - 1]["beat_id"], beats[i]["beat_id"]],
                    "similarity": round(sim, 4),
                    "parts": {"template": round(s_tpl, 3),
                              "region": round(s_reg, 3),
                              "palette": round(s_pal, 3),
                              "decor": round(s_mot, 3)}})
    metrics["adjacent_similarity"] = adj
    a_thr = THRESHOLDS["adjacent_similarity"]
    for a in adj:
        if a["similarity"] >= a_thr["fail"]:
            fail("REP_ADJACENT_SIMILAR",
                 "相邻拍 %s 相似度 %.3f ≥ %.2f：两拍太像"
                 % ("→".join(a["pair"]), a["similarity"], a_thr["fail"]))
        elif a["similarity"] >= a_thr["warn"]:
            warn("REP_ADJACENT_SIMILAR_SOFT",
                 "相邻拍 %s 相似度 %.3f 偏高" % ("→".join(a["pair"]),
                                                 a["similarity"]))

    # 4) palette_spread
    pc = Counter(palettes)
    max_share = max(pc.values()) / float(n)
    metrics["palette_max_share"] = round(max_share, 4)
    metrics["palette_distribution"] = dict(pc)
    ps = THRESHOLDS["palette_max_share"]
    if n >= 4 and max_share > ps["max"]:
        warn("REP_PALETTE_SHARE",
             "单一调色板占 %.0f%% > %.0f%%" % (max_share * 100, ps["max"] * 100))
    pk = THRESHOLDS["palette_min_kinds"]
    if n >= 4 and len(pc) < pk["min"]:
        warn("REP_PALETTE_KINDS",
             "调色板仅 %d 种 < %d 种" % (len(pc), pk["min"]))

    # 5) decor_cooldown —— 同一装饰画法最短复现间隔
    last_seen, min_gap = {}, None
    for i, b in enumerate(beats):
        for m in _motifs_of(b):
            if m in last_seen:
                gap = i - last_seen[m]
                min_gap = gap if min_gap is None else min(min_gap, gap)
            last_seen[m] = i
    metrics["decor_min_repeat_gap"] = min_gap
    dc = THRESHOLDS["decor_cooldown"]
    if min_gap is not None and min_gap < dc["min_gap"]:
        warn("REP_DECOR_COOLDOWN",
             "装饰画法最短复现间隔 %d 拍 < %d" % (min_gap, dc["min_gap"]))

    status = "FAIL" if violations else "PASS"
    return {"metrics": metrics, "warnings": warnings,
            "violations": violations, "status": status,
            "thresholds": THRESHOLDS}


def evaluate_workdir(work_dir):
    """从 work 目录读取 dsl / render-plan 并评估——供 validator 调用。"""
    from common import load_json
    import os
    dsl = load_json(os.path.join(work_dir, "visual-dsl.json"))
    render = load_json(os.path.join(work_dir, "render-plan.json"))
    return evaluate(dsl, render)
