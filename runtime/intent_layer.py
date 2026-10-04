"""intent_layer.py — v7.3 Agent 的「语义视觉意图层」。

Agent 只回答一个问题：**这句话应该被怎样视觉化？**
Agent 不回答：**怎么画。**

被明令禁止输出的（模板选择器 / 像素泄漏）：
    {"strategy": "cause_effect", "template": "left_to_right_flow",
     "hero_x": 300, "hero_y": 400}

应当输出的（视觉意图）：
    {"visual_claim": "small_repeated_actions_accumulate_into_large_change",
     "grammar": ["accumulation", "trajectory", "threshold"],
     "focal_point": "trajectory",
     "relationship": [{"from": "small_actions", "relation": "accumulate_into",
                       "to": "trajectory"},
                      {"from": "trajectory", "relation": "crosses", "to": "threshold"}],
     "density": 0.62, "silence": false, "motion_intent": "accumulate_then_reveal"}

这一层是「Agent 视觉决策能力」与「Runtime 视觉语言」的解耦点：
    Agent → 意图（本模块）；Runtime → 几何（composition_compiler.py）。
本模块是纯语义的：分类、校验、拒斥模板泄漏，不产生任何坐标。
"""
import re

import visual_grammar as VG

# ---------------------------------------------------------------- 契约
REQUIRED = ("beat_id", "visual_claim", "grammar", "focal_point",
            "relationship", "density", "silence", "motion_intent")

# 运动意图词汇（语义，不是缓动函数名）
MOTION_INTENTS = ("establish", "reveal", "accumulate_then_reveal", "cross_threshold",
                  "morph", "hold", "resolve", "assert", "contrast_then_focus", "draw_in")

# 模板选择器 / 像素泄漏键——出现即视为「没在做导演，而是在选模板」
_FORBIDDEN = {
    "strategy", "template", "layout", "pattern", "preset",
    "hero_x", "hero_y", "hero_w", "hero_h",
    "x", "y", "cx", "cy", "w", "h", "box", "rect", "coord", "coords",
    "pixel", "px", "anchor_x", "anchor_y", "move_x", "move_y",
}


# ---------------------------------------------------------------- 拒斥模板泄漏
def template_leak_keys(obj, _path=""):
    """递归找出所有「模板/像素」泄漏键，返回点路径列表。空列表 = 干净。

    这是「Agent 不当模板选择器」的机器证据：正确的意图 JSON 里，
    template_leak_keys(...) 必须为空。
    """
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{_path}.{k}" if _path else str(k)
            if str(k).lower() in _FORBIDDEN:
                hits.append(p)
            hits.extend(template_leak_keys(v, p))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            hits.extend(template_leak_keys(v, f"{_path}[{i}]"))
    return hits


def is_template_selector(obj):
    """是否是「模板选择器」式输出（含 strategy/template/像素）——应被拒绝。"""
    return bool(template_leak_keys(obj))


# ---------------------------------------------------------------- 意图校验
def _iss(bid, code, msg):
    return {"severity": "err", "layer": "intent", "code": code, "beat_id": bid, "msg": msg}


def validate_intent(intent):
    """意图契约机器门禁。返回 issues 列表（空 = PASS）。

    关键：**否决模板选择器**——只要有 forbidden 键，直接判不合法。
    """
    issues = []
    bid = intent.get("beat_id", "?")
    leak = template_leak_keys(intent)
    if leak:
        issues.append(_iss(bid, "INTENT_TEMPLATE_LEAK",
                           "意图里出现了模板/像素键（应交给 Runtime）：%s" % leak))
    for k in REQUIRED:
        if k not in intent:
            issues.append(_iss(bid, "INTENT_MISSING", "缺少字段 %s" % k))
    if issues:
        return issues

    if not isinstance(intent["visual_claim"], str) or not intent["visual_claim"].strip():
        issues.append(_iss(bid, "INTENT_CLAIM_EMPTY", "visual_claim 必须是非空字符串"))
    g = intent["grammar"]
    if not isinstance(g, list) or not g:
        issues.append(_iss(bid, "INTENT_GRAMMAR_EMPTY", "grammar 必须是非空列表"))
    else:
        for op in g:
            if op not in VG.GRAMMAR_OPS:
                issues.append(_iss(bid, "INTENT_GRAMMAR_UNKNOWN", "非法语法 %r" % op))
    ents = intent.get("entities") or []
    if intent["focal_point"] not in ents and ents:
        issues.append(_iss(bid, "INTENT_FOCAL_NOT_ENTITY",
                           "focal_point %r 不在 entities %s" % (intent["focal_point"], ents)))
    rel = intent["relationship"]
    if not isinstance(rel, list) or not rel:
        issues.append(_iss(bid, "INTENT_REL_EMPTY", "relationship 必须非空（图，不是列表）"))
    else:
        for r in rel:
            if not all(k in r for k in ("from", "relation", "to")):
                issues.append(_iss(bid, "INTENT_REL_MALFORMED", "关系缺 from/relation/to: %r" % r))
    if not isinstance(intent["density"], (int, float)) or not (0 <= intent["density"] <= 1):
        issues.append(_iss(bid, "INTENT_DENSITY_RANGE", "density 必须是 0..1"))
    if not isinstance(intent["silence"], bool):
        issues.append(_iss(bid, "INTENT_SILENCE_BOOL", "silence 必须是布尔"))
    if intent["motion_intent"] not in MOTION_INTENTS:
        issues.append(_iss(bid, "INTENT_MOTION_UNKNOWN", "未知 motion_intent %r" % intent["motion_intent"]))
    return issues


# ---------------------------------------------------------------- 从 beat 推导意图
def _entities_from(beat):
    ents = []
    for r in beat.get("relations", []) + beat.get("semantic_pairs", []):
        for k in ("from", "to"):
            v = r.get(k)
            if v and v not in ents:
                ents.append(v)
    for e in beat.get("entities", []) or []:
        if e not in ents:
            ents.append(e)
    return ents


def derive_intent(beat):
    """从一拍（含旁白/角色/关系）推导语义意图。纯语义，无坐标。"""
    narration = beat.get("narration", "") or ""
    grammar = VG.grammar_for_beat(beat)
    ents = _entities_from(beat)
    focal = beat.get("focal_point") or (ents[-1] if ents else beat.get("beat_id", "主体"))
    if not ents:
        ents = [focal]
    if focal not in ents:
        ents.append(focal)

    rel = [{"from": r.get("from", "?"), "relation": r.get("type", "relate"),
            "to": r.get("to", "?")} for r in beat.get("relations", [])]
    if not rel:
        rel = [{"from": ents[0], "relation": "relate", "to": focal}]

    density = round(min(0.85, max(0.25, 0.25 + len(narration) / 120.0)), 2)
    silence = len(narration.strip()) < 8
    if "accumulation" in grammar:
        motion = "accumulate_then_reveal"
    elif "threshold" in grammar:
        motion = "cross_threshold"
    elif grammar[0] == "establish":
        motion = "establish"
    elif grammar[0] == "contrast":
        motion = "contrast_then_focus"
    else:
        motion = "morph"

    claim = beat.get("visual_claim") or _claim_for(beat, grammar, ents)
    return {
        "beat_id": beat.get("beat_id", "b0"),
        "visual_claim": claim,
        "grammar": grammar,
        "focal_point": focal,
        "relationship": rel,
        "density": density,
        "silence": silence,
        "motion_intent": motion,
        "entities": ents,
    }


def _claim_for(beat, grammar, ents):
    role = beat.get("semantic_role", "beat")
    return "%s:%s" % (role, "+".join(grammar))
