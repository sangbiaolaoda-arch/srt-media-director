"""Stage 3 — Visual Director: beats → visual plan + visual DSL.

Responsibilities (skills 03/04/05):
- extract & rank emphasis candidates from the *actual* narration;
- decide information encoding (part_to_whole / change_over_time / …);
- choose a composition strategy per beat, honoring GATE-R8
  (adjacent beats must not share a template; explicit overrides win);
- emit semantic elements & relations — asset-blind, no pixels (CORE-06).

v4.1 视觉政策（用户导演指令）：
- 不出现拟人形象；motif 词汇表全部为非具象物件（手机/月亮/盾牌/时钟/警示）。
- 主体每拍唯一（文字/图表/图形皆可），但允许 2-3 个 ambient 装饰附体
  （角标/点阵/圆环等，自带归一化 rect，不参与区域预算）丰富画面。
"""
import re

from procedural_canonical import rng as _proc_rng

import style_bible
import visual_grammar
from common import (CANVAS_H, CANVAS_W, COLORS, format_compact_num,
                    mood_palette, narrative_function_rank)

CANVAS = {"width": CANVAS_W, "height": CANVAS_H, "fps": 30}

STRATEGIES = ("single_focus", "left_to_right_flow", "cause_effect",
              "comparison", "center_cluster", "before_after")

# GATE-R8 邻拍避让时的轮换顺序（显式覆写优先，见 direct()）
ROTATION = ("single_focus", "cause_effect", "center_cluster",
            "comparison", "before_after", "left_to_right_flow")

# P2：构图策略决策权已收敛进 visual_grammar（导演不再自带决策表）。
SEMANTIC_DEFAULT = visual_grammar.SEMANTIC_DEFAULT

_RISK_WORDS = ("危险", "风险", "依赖", "害", "伤", "焦虑", "失眠")
_SAFE_WORDS = ("安全", "保护", "边界", "自律", "找回")

# 非拟人 motif 词汇表（v4.1 person 移除；v4.4 扩库承载更多语义）
_MOTIF_MAP = (
    # 时间 / 等待 / 方向
    ("睡前", "moon"), ("晚上", "moon"), ("夜里", "moon"), ("醒来", "moon"),
    ("很多年", "hourglass"), ("多年", "hourglass"), ("三年", "hourglass"),
    ("分钟", "hourglass"), ("时长", "hourglass"), ("时间", "clock"),
    ("等待", "hourglass"), ("等", "hourglass"), ("方向", "compass"),
    # 设备 / 依赖
    ("手机", "phone"), ("刷屏", "phone"), ("屏幕", "phone"), ("依赖", "phone"),
    # 危险 / 警告
    ("危险", "alert"), ("风险", "alert"), ("警告", "alert"), ("焦虑", "alert"),
    ("失眠", "alert"),
    # 安全 / 边界
    ("安全", "shield"), ("边界", "shield"), ("保护", "shield"),
    # 赢 / 承认（本片母题：trophy / key / lock）
    ("赢", "trophy"), ("承认", "key"), ("签字", "key"), ("结案", "lock"),
    ("锁", "lock"), ("关门", "lock"),
    # 那天 / 重来 / 过去
    ("那天", "calendar"), ("那一天", "calendar"), ("重来", "calendar"),
    ("过去", "hourglass"),
    # 话 / 台词 / 没说出口
    ("没说完", "envelope"), ("台词", "envelope"), ("亲口", "envelope"),
    ("话", "envelope"),
    # 目标 / 立场 / 仗
    ("目标", "target"), ("命中", "target"), ("仗", "flag"), ("立场", "flag"),
    ("位置", "flag"),
    # 想 / 领悟
    ("想过", "bulb"), ("决定", "bulb"), ("明白", "bulb"), ("想", "bulb"),
    # 记住 / 标记
    ("记住", "bookmark"), ("记得", "bookmark"), ("念到", "bookmark"),
    # 衡量 / 公正
    ("衡量", "balance"), ("公平", "balance"), ("凭什么", "balance"),
    # 拼 / 运转
    ("拼", "gears"), ("努力", "gears"), ("运转", "gears"),
    # 数据 / 增长 / 进度
    ("增长", "chart_line"), ("提升", "chart_bar"), ("超过", "chart_bar"),
    ("进度", "progress_ring"), ("完成", "progress_ring"),
    # 坐标 / 原点
    ("坐标", "map_pin"), ("原点", "map_pin"), ("原地", "map_pin"),
    # ---- 命理 / 心理学（《10月4日》母题：控制错觉 / 后见之明 / 命运）----
    # 命 / 注定 / 不由人
    ("万般皆是命", "compass"), ("皆是命", "compass"), ("命里", "compass"),
    ("信命", "compass"), ("说命", "compass"), ("命运", "compass"),
    ("不由人", "compass"), ("注定", "compass"), ("天意", "compass"), ("命", "compass"),
    # 实验 / 研究 / 判断 / 衡量
    ("实验", "puzzle"), ("研究者", "puzzle"), ("研究", "puzzle"),
    ("兰格", "puzzle"), ("菲施霍夫", "puzzle"), ("被试", "puzzle"),
    ("判断", "balance"), ("裁决", "balance"), ("判决", "balance"),
    ("估", "balance"), ("评估", "balance"), ("打分", "balance"),
    # 概率 / 数据 / 概率估计
    ("概率", "chart_bar"), ("开价", "chart_bar"), ("平均", "chart_bar"),
    ("数字", "chart_bar"), ("数据", "chart_bar"), ("几个", "chart_bar"), ("多少", "chart_bar"),
    ("翻一倍", "chart_line"), ("倍", "chart_line"), ("差", "chart_line"), ("涨", "chart_line"),
    # 中奖 / 结果 / 结局
    ("中奖", "target"), ("结局", "target"), ("结果", "target"), ("结尾", "target"),
    # 选择 / 随机（自己挑 = 控制的错觉）
    ("自己挑", "balance"), ("挑选", "balance"), ("选择", "balance"),
    ("随机", "puzzle"), ("发到", "puzzle"), ("拿票", "puzzle"),
    # 记忆 / 后见之明
    ("记忆", "bookmark"), ("回想", "bookmark"),
    # 错觉 / 大脑 / 规则（两台机器）
    ("错觉", "gears"), ("大脑", "gears"), ("机器", "gears"), ("规则", "gears"),
    # 时间 / 发生 / 结束
    ("发生", "clock"), ("开始", "hourglass"), ("结束", "hourglass"),
    # 归档 / 抽屉 / 盖章（办手续）
    ("归档", "lock"), ("抽屉", "lock"), ("盖章", "lock"), ("收进", "lock"), ("封存", "lock"),
)

# 无关键词命中时的兜底候选（内容驱动、跨拍变化；刻意不含 "phone"，
# 避免「上一支视频的母题」在无关内容上反复渗入背景水印）。
_GENERIC_MOTIFS = ("compass", "gears", "bulb", "puzzle", "balance",
                   "target", "hourglass", "map_pin", "flag", "bookmark",
                   "calendar", "clock")

# ---- 装饰附体（v4.4：策略主题 + 受控随机陪衬 + 跨拍冷却）----
# 落位区域池：画面四角 + 边缘中点，避开中央主体区
_DECOR_ZONES = (
    (0.050, 0.075, 0.100, 0.150),
    (0.845, 0.080, 0.100, 0.150),
    (0.050, 0.700, 0.110, 0.180),
    (0.835, 0.690, 0.110, 0.190),
    (0.045, 0.370, 0.085, 0.120),
    (0.860, 0.370, 0.085, 0.120),
    (0.420, 0.840, 0.170, 0.080),
)

# 策略主题装饰：与构图语义相关，优先出现（不算随机）
_STRATEGY_DECOR = {
    "single_focus": ("ring_pair",),
    "left_to_right_flow": ("arrow_chain", "wave"),
    "cause_effect": ("conn_nodes", "milestone"),
    "comparison": ("chip_row", "bar_mini"),
    "center_cluster": ("ring_pair", "orbit"),
    "before_after": ("mini_curve", "milestone"),
}

# 随机陪衬候选池（全部非拟人图形/图表）
_DECOR_POOL = ("dot_grid", "wave", "scatter", "brackets", "halftone",
               "cross_hatch", "spiral", "bar_mini", "ruler", "plus_field",
               "orbit", "arrow_chain", "milestone", "ring_pair", "tick_line")

_DECOR_COOLDOWN = 4   # 最近 N 拍用过的陪衬装饰冷却（避免邻拍雷同）


def _seed_for(beat):
    """稳定随机种子（委托 procedural_canonical.rng —— 单一真相源）。

    跨进程可复现；内置 hash 受 PYTHONHASHSEED 影响，不用。
    """
    return _proc_rng.stable_seed(_proc_rng.beat_key(beat))


def load_overrides(path):
    import json
    import os
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    return {}


# ---------------------------------------------------------------- emphasis

def extract_emphasis(beat, analysis_numbers):
    """Emphasis candidates — every candidate must trace back to a source span."""
    text = beat["narration"]
    cands = []
    for m in re.finditer(r"\d+(?:\.\d+)?%", text):
        cands.append({"span": m.group(0), "kind": "percentage",
                      "semantic_role": "part_to_whole",
                      "source_span": text[max(0, m.start() - 8):m.end() + 2]})
    for m in re.finditer(r"\d+(?:\.\d+)?(?!\s*%)(?:分钟|小时|次|天|个|秒)?", text):
        if any(c["span"] == m.group(0) for c in cands):
            continue
        cands.append({"span": m.group(0), "kind": "number",
                      "semantic_role": "magnitude",
                      "source_span": text[max(0, m.start() - 6):m.end() + 2]})
    for w in _RISK_WORDS:
        if w in text and not any(c["span"] == w for c in cands):
            cands.append({"span": w, "kind": "keyword", "semantic_role": "risk",
                          "source_span": w})
    for w in _SAFE_WORDS:
        if w in text and not any(c["span"] == w for c in cands):
            cands.append({"span": w, "kind": "keyword",
                          "semantic_role": "safety", "source_span": w})
    return cands


def rank_emphasis(beat, candidates):
    role_w = {"conclusion": 3, "turning_point": 3, "hook": 2,
              "comparison": 2, "emphasis": 2, "explanation": 1}
    kind_w = {"percentage": 3, "number": 2, "keyword": 2}
    return sorted(candidates,
                  key=lambda c: -(role_w.get(beat["semantic_role"], 1)
                                  + kind_w.get(c["kind"], 1)))


def decide_encoding(beat, emphasis):
    nums = [e for e in emphasis if e["kind"] in ("percentage", "number")]
    kws = [e for e in emphasis if e["kind"] == "keyword"]
    if len(nums) >= 2 and any(k in beat["narration"]
                              for k in ("从", "到", "→", "拉长", "增长")):
        return {"type": "change_over_time", "data_span": [n["span"] for n in nums[:2]]}
    if nums and nums[0]["kind"] == "percentage":
        return {"type": "part_to_whole", "data_span": nums[0]["span"]}
    if any(k["semantic_role"] == "risk" for k in kws) and \
            any(k["semantic_role"] == "safety" for k in kws):
        return {"type": "semantic_color_pair",
                "data_span": [kws[0]["span"], kws[-1]["span"]]}
    if kws:
        return {"type": "typography", "data_span": kws[0]["span"]}
    if nums:
        return {"type": "typography", "data_span": nums[0]["span"]}
    return {"type": "none", "data_span": None}


# ---------------------------------------------------------------- elements

def _text_el(bid, slot, role, text, size, color, emphasis=False, boxed=False):
    return {"id": "%s_%s" % (bid, slot), "slot": slot, "type": "text",
            "role": role, "text": text, "size": size, "color_role": color,
            "emphasis": emphasis, "boxed": boxed}


def _motif_color(keyword, cue_ids, numbers_index):
    if keyword in _RISK_WORDS:
        return "negative"
    if keyword in _SAFE_WORDS:
        return "positive"
    return "info"


def _pick_motif(narration, override=None, salt=""):
    """关键词命中优先；未命中时做「内容驱动的确定性兜底」。

    旧实现返回固定 "phone"，导致上一支视频的母题在无关内容里被反复复用，
    背景水印每拍都是同一张图（用户可见的「重复手机」）。现改为：种子取自
    salt + 字幕文本，跨进程可复现，且随拍号/文案变化，不再钉死单张图。
    """
    if override:
        return override
    for w, name in _MOTIF_MAP:
        if w in narration:
            return name
    h = _proc_rng.stable_seed(salt + "|" + narration)
    return _GENERIC_MOTIFS[h % len(_GENERIC_MOTIFS)]


def _decor(strategy, beat_i, ghost_text=None, rng=None, recent=None):
    """装饰附体（ambient）：不参与区域预算，自带归一化 rect（skill 06/08）。

    v4.4：策略主题装饰 + 受控随机陪衬（种子来自 beat_id + 字幕）+ 跨拍冷却。
    每拍至少 3 件图形装饰（1-2 件主题 + 1-2 件随机陪衬），single_focus 追加
    关键词幽灵大字。用户反馈「太素 / 只画箭头 / 无随机」——本层让装饰在规则
    内真正随拍变化，而不是按模板钉死位置。
    """
    bid = "b%02d" % beat_i
    rng = rng if rng is not None else _proc_rng.default_rng()
    recent = recent if recent is not None else []
    used = set().union(*recent) if recent else set()

    chosen = [a for a in _STRATEGY_DECOR.get(strategy, ("ring_pair",))]
    pool = [a for a in _DECOR_POOL if a not in used and a not in chosen]
    rng.shuffle(pool)
    want = rng.randint(1, 2)
    for art in pool[:want]:
        chosen.append(art)
    for art in pool[want:]:                     # 兜底：保证 ≥3 件
        if len(chosen) >= 3:
            break
        chosen.append(art)
    chosen = chosen[:4]

    zones = list(range(len(_DECOR_ZONES)))
    rng.shuffle(zones)
    out = []
    for i, art in enumerate(chosen):
        z = _DECOR_ZONES[zones[i % len(zones)]]
        rect = [round(z[0] + rng.uniform(-0.012, 0.012), 3),
                round(z[1] + rng.uniform(-0.012, 0.012), 3),
                round(z[2] * rng.uniform(0.90, 1.12), 3),
                round(z[3] * rng.uniform(0.90, 1.12), 3)]
        out.append({"id": "%s_decor%d" % (bid, i), "slot": "decor",
                    "type": "decor", "role": "ambient", "rect": rect,
                    "art": art,
                    "color_role": rng.choice(("neutral", "info", "neutral"))})

    if strategy == "single_focus" and ghost_text:
        out.append({"id": "%s_decor_ghost" % bid, "slot": "decor",
                    "type": "decor", "role": "ambient",
                    "rect": [0.150, 0.300, 0.700, 0.420],
                    "text": ghost_text, "color_role": "ink"})

    recent.append({e["art"] for e in out if "art" in e})
    if len(recent) > _DECOR_COOLDOWN:
        del recent[:-_DECOR_COOLDOWN]
    return out


def _build_elements(strategy, beat_i, ov, emphasis, encoding, narration,
                    numbers_index, rng=None, recent=None):
    bid = "b%02d" % beat_i
    primary = emphasis[0]["span"] if emphasis else narration[:6]
    els, rels = [], []

    def motif_el(slot, role, name, color):
        return {"id": "%s_%s" % (bid, slot), "slot": slot, "type": "motif",
                "role": role, "motif": name, "art": name, "color_role": color}

    if strategy == "single_focus":
        kw = ov.get("keyword", primary if len(primary) <= 8 else narration[:4])
        motif = _pick_motif(narration, ov.get("motif"))
        color = _motif_color(kw, beat_i, numbers_index)
        els.append(_text_el(bid, "keyword", "primary", kw, "keyword",
                            color if color in ("negative", "positive") else "ink",
                            emphasis=True, boxed=True))
        els.append(motif_el("hero", "secondary", motif, color))
        note = ov.get("note")
        if note:
            els.append(_text_el(bid, "note", "support", note, "note", "neutral"))
        rels.append({"from": "%s_keyword" % bid, "to": "%s_hero" % bid,
                     "type": "bound_to"})
        ghost = kw
    elif strategy == "left_to_right_flow":
        pair = ov.get("flow_pair")
        if pair:
            left, right = pair
        else:
            left = _pick_motif(narration.split("，")[0], salt="L")
            right = _pick_motif(narration, salt="R")
            if right == left:  # 左右两端不重复：顺延到下一个兜底候选
                i = _GENERIC_MOTIFS.index(right) if right in _GENERIC_MOTIFS else 0
                right = _GENERIC_MOTIFS[(i + 1) % len(_GENERIC_MOTIFS)]
        els.append(motif_el("hero_left", "primary", left, "info"))
        els.append({"id": "%s_bridge" % bid, "slot": "bridge",
                    "type": "connector", "role": "support",
                    "connector": "arrow", "color_role": "neutral"})
        els.append(motif_el("hero_right", "secondary", right, "ink"))
        note = ov.get("note")
        if note:
            els.append(_text_el(bid, "note", "support", note, "note", "neutral"))
        rels.append({"from": "%s_hero_left" % bid, "to": "%s_hero_right" % bid,
                     "type": "flow_to"})
        ghost = None
    elif strategy == "cause_effect":
        cause = ov.get("cause", (emphasis[0]["span"] if emphasis else narration[:4]))
        result = ov.get("result", narration[-6:].strip("，。！？"))
        els.append(_text_el(bid, "cause", "primary", cause, "label", "ink",
                            emphasis=True, boxed=True))
        els.append({"id": "%s_bridge" % bid, "slot": "bridge",
                    "type": "connector", "role": "support",
                    "connector": "arrow", "color_role": "neutral"})
        els.append(_text_el(bid, "result", "secondary", result, "label",
                            "info", boxed=True))
        note = ov.get("note")
        if note:
            els.append(_text_el(bid, "note", "support", note, "note", "neutral"))
        rels.append({"from": "%s_cause" % bid, "to": "%s_result" % bid,
                     "type": "causes"})
        ghost = None
    elif strategy == "comparison":
        risk = next((e["span"] for e in emphasis if e["semantic_role"] == "risk"),
                    ov.get("keyword", narration[:4]))
        safe = next((e["span"] for e in emphasis if e["semantic_role"] == "safety"),
                    ov.get("alt", "边界"))
        els.append({"id": "%s_panel_left" % bid, "slot": "panel_left",
                    "type": "shape", "role": "ambient", "tone": "negative_soft"})
        els.append({"id": "%s_panel_right" % bid, "slot": "panel_right",
                    "type": "shape", "role": "ambient", "tone": "positive_soft"})
        els.append(_text_el(bid, "word_left", "primary", risk, "word",
                            "negative", emphasis=True))
        els.append(_text_el(bid, "word_right", "secondary", safe, "word",
                            "positive", emphasis=True))
        els.append(_text_el(bid, "note_left", "support",
                            ov.get("note_left", "依赖"), "label", "neutral"))
        els.append(_text_el(bid, "note_right", "support",
                            ov.get("note_right", "边界"), "label", "neutral"))
        rels.append({"from": "%s_word_left" % bid, "to": "%s_word_right" % bid,
                     "type": "contrast"})
        ghost = None
    elif strategy == "center_cluster":
        pct = encoding["data_span"] if encoding["type"] == "part_to_whole" else None
        val = float(str(pct).rstrip("%")) if pct else float(
            ov.get("value", 50))
        els.append({"id": "%s_hero" % bid, "slot": "hero", "type": "chart",
                    "role": "secondary",
                    "chart": {"kind": "donut", "value": val},
                    "color_role": "info"})
        els.append({"id": "%s_number" % bid, "slot": "number", "type": "text",
                    "role": "primary", "text": ov.get("number", format_compact_num(val) + "%"),
                    "size": "number", "color_role": "info", "emphasis": True,
                    "host": "%s_hero" % bid})
        note = ov.get("note")
        if note:
            els.append(_text_el(bid, "note", "support", note, "note", "neutral"))
        rels.append({"from": "%s_number" % bid, "to": "%s_hero" % bid,
                     "type": "bound_to"})
        ghost = None
    elif strategy == "before_after":
        nums = encoding.get("data_span") or ["15", "45"]
        before = float(re.sub(r"[^\d.]", "", str(nums[0])) or 0)
        after = float(re.sub(r"[^\d.]", "", str(nums[1])) or 1) \
            if len(nums) > 1 else before * 3
        els.append({"id": "%s_hero" % bid, "slot": "hero", "type": "chart",
                    "role": "primary",
                    "chart": {"kind": "bars", "before": before, "after": after},
                    "color_role": "positive"})
        els.append(_text_el(bid, "delta", "secondary",
                            "×" + format_compact_num(after / before if before else 1),
                            "display_small", "info", emphasis=True))
        note = ov.get("note")
        if note:
            els.append(_text_el(bid, "note", "support", note, "note", "neutral"))
        rels.append({"from": "%s_delta" % bid, "to": "%s_hero" % bid,
                     "type": "bound_to"})
        ghost = None
    else:  # pragma: no cover - 策略集合受 STRATEGIES 约束
        raise ValueError("unknown strategy %s" % strategy)

    els += _decor(strategy, beat_i, ghost_text=ghost, rng=rng, recent=recent)
    return els, rels


def _title_for(beat, beat_i, ov):
    return ov.get("title", "%02d · %s" % (beat_i, beat["narration"][:10]))


# ---------------------------------------------------------------- directing

def _direct_beat(beat, beat_i, ov, prev_strategy, numbers_index,
                 rng=None, recent=None):
    encoding = decide_encoding(beat, rank_emphasis(beat, extract_emphasis(
        beat, numbers_index)))
    emphasis = rank_emphasis(beat, extract_emphasis(beat, numbers_index))

    # P2：构图策略由 visual_grammar 层决断（Director 不再自带决策词汇）。
    strategy = visual_grammar.composition_strategy(beat, encoding)

    explicit = "strategy" in ov
    strategy = ov.get("strategy", strategy)
    if not explicit and strategy == prev_strategy:  # R8：邻拍不同模板（显式覆写优先）
        for cand in ROTATION:
            if cand != prev_strategy:
                strategy = cand
                break

    els, rels = _build_elements(strategy, beat_i, ov, emphasis, encoding,
                                beat["narration"], numbers_index, rng, recent)
    els.insert(0, _text_el("b%02d" % beat_i, "title", "support",
                           _title_for(beat, beat_i, ov), "label", "ink"))
    els.insert(0, _text_el("b%02d" % beat_i, "eyebrow", "support",
                           "%02d / %s" % (beat_i, beat["semantic_role"]),
                           "eyebrow", "neutral"))

    claim = ov.get("claim") or emphasis[0]["source_span"] if emphasis \
        else beat["narration"][:12]
    plan = {
        "beat_id": beat["beat_id"], "narration": beat["narration"],
        "visual_claim": claim,
        "evidence": [{"source_span": e["source_span"],
                      "source_cue_ids": [beat["cue_range"][0]],
                      "inference_type": "literal"} for e in emphasis[:3]] or
                     [{"source_span": beat["narration"][:12],
                       "source_cue_ids": [beat["cue_range"][0]],
                       "inference_type": "semantic_abstraction"}],
        "strategy": strategy,
        "emphasis_plan": {"candidates": emphasis,
                          "primary_emphasis": emphasis[0]["span"] if emphasis else None,
                          "secondary_emphasis": [e["span"] for e in emphasis[1:3]]},
        "information_encoding": encoding,
        "composition_thesis": {
            "reading_order": ["eyebrow", "title",
                              els[2]["slot"] if len(els) > 2 else "keyword"],
            "why": "先语境后主体，主体唯一；装饰附体只丰富氛围、不抢注意力"},
        "motion_policy": beat["motion_policy"],
        "camera_intent": {"mode": "push_in", "reason": "数字是该拍核心信息"}
        if encoding["type"] == "part_to_whole" else {"mode": "static"},
    }
    dsl_beat = {
        "beat_id": beat["beat_id"], "narration": beat["narration"],
        "start_sec": beat["start_sec"],
        "end_sec": beat["end_sec"], "strategy": strategy,
        "motion_policy": beat["motion_policy"], "visual_claim": claim,
        "elements": els, "relations": rels,
        "camera": plan["camera_intent"], "carry_over": [],
        "palette": mood_palette(beat["narration"], beat["semantic_role"]),
        # P0④：把语义关系编译为**抽象视觉语法**（causality/contrast/…），
        # 而非固定素材名——语法到表层实现是一对多，导演可自由挑选。
        "grammar_ops": visual_grammar.grammar_for_beat(beat),
    }
    return plan, dsl_beat, strategy


def direct(beats, overrides=None):
    """beats → (visual_plan, visual_dsl). GATE-R8 enforced here."""
    overrides = overrides or {}
    vplans, dsl_beats = [], []
    prev_strategy = None
    recent_decor = []
    for i, beat in enumerate(beats, 1):
        ov = overrides.get(beat["cue_range"][0], {})
        rng = _proc_rng.rng_for_beat(beat)
        plan, dsl_beat, prev_strategy = _direct_beat(
            beat, i, ov, prev_strategy, None, rng, recent_decor)
        vplans.append(plan)
        dsl_beats.append(dsl_beat)
    vplan = {"global_visual_grammar": {
        "style": "paper-flat",
        "typography_language": "eyebrow < note < label < keyword < display",
        "color_roles": {k: COLORS[k] for k in
                        ("negative", "positive", "info", "neutral", "ink")},
        "relation_language": {"cause": "arrow", "contrast": "dual_panel",
                              "flow": "arrow", "bound": "host"},
        "camera_language": "static by default; push_in only for numeric emphasis",
        "emphasis_language": "one primary attention target per beat",
        "decor_language": "ambient decor only (per-strategy accent pieces, no "
                          "persistent frame); non-anthropomorphic motif vocabulary",
        "narrative_function_order": sorted(
            set(b["semantic_role"] for b in beats),
            key=narrative_function_rank),
        # P0③：视频级视觉人格由本条内容推导，不预设固定风格。
        "style_bible": style_bible.derive_style_bible(beats),
        # P0④：全片语法词汇表（抽象语法体系，固定；表达，不固定）。
        "grammar_language": list(visual_grammar.GRAMMAR_OPS),
    }, "beats": vplans}
    dsl = {"version": "4.4", "canvas": CANVAS, "beats": dsl_beats}
    return vplan, dsl


# v6.0：把参考图信息图装饰纳入随机陪衬池
_DECOR_POOL = tuple(_DECOR_POOL) + ("conn_nodes", "mini_curve", "chip_row")
