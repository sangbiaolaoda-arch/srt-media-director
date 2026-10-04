"""P0③ — Style Bible: the *video-level* visual personality.

固定「审美原则」，不固定「视觉风格」。

`style_tokens.json` 锁的是**项目级**调色板/字体/线宽（一份物料清单）。
Style Bible 描述的是**视频级**的视觉人格：它由这一条片子的内容推导出来，
回答「这支片子整体是什么气质、多密、什么排版、什么对比与静默政策」，
而不是「第 7 拍用哪个素材」。

两者互补：tokens 保证画面不漂移，bible 保证气质随内容自适应。
本模块只做「推导 + 校验」，不渲染。
"""
from common import mood_palette, narrative_function_rank

STYLE_FAMILIES = ("editorial_flat", "editorial_textured",
                  "technical_diagram", "cinematic_muted")
MOODS = ("neutral", "tense", "warm", "cold", "calm")
DENSITIES = ("sparse", "balanced", "dense")
TEMPERAMENTS = ("restrained", "measured", "expressive")
CONTRAST_POLICIES = ("wcag_aa", "wcag_aaa", "high")

REQUIRED_KEYS = ("family", "mood", "density", "typography",
                 "motion_temperament", "contrast_policy", "silence_policy")


def derive_style_bible(beats):
    """从整条片子的 beat 序列推导视频级视觉人格。"""
    moods = [mood_palette(b.get("narration", ""), b.get("semantic_role"))
             for b in beats] or ["neutral"]
    mood = max(set(moods), key=moods.count)
    if mood == "night":
        mood = "neutral"

    avg_len = sum(len(b.get("narration", "")) for b in beats) / max(1, len(beats))
    density = "sparse" if avg_len < 12 else ("dense" if avg_len > 24 else "balanced")

    roles = sorted({b.get("semantic_role", "explanation") for b in beats},
                   key=narrative_function_rank)

    return {
        "family": "editorial_flat",
        "mood": mood,
        "density": density,
        "typography": {
            "scale": "eyebrow<note<label<keyword<display<number",
            "face": "serif-titles / sans-body",
            "contrast": "wcag_aa",
        },
        "motion_temperament": "restrained",
        "contrast_policy": "wcag_aa",
        "silence_policy": "hold >= min(read_time, beat_length) * 0.22",
        "narrative_roles": roles,
        "rationale": ("视觉人格由本条内容的情绪分布(主导 mood=%s)、平均句长"
                      "(density=%s) 与叙事角色集合推导，不预设固定风格。" % (mood, density)),
    }


def validate_bible(bible):
    issues = []
    for k in REQUIRED_KEYS:
        if k not in bible:
            issues.append(_iss("BIBLE_KEY_MISSING", "缺少字段 %s" % k))
    if bible.get("family") not in STYLE_FAMILIES:
        issues.append(_iss("BIBLE_FAMILY", "未知视觉家族 %r" % bible.get("family")))
    if bible.get("mood") not in MOODS:
        issues.append(_iss("BIBLE_MOOD", "未知情绪 %r" % bible.get("mood")))
    if bible.get("density") not in DENSITIES:
        issues.append(_iss("BIBLE_DENSITY", "未知密度 %r" % bible.get("density")))
    if bible.get("motion_temperament") not in TEMPERAMENTS:
        issues.append(_iss("BIBLE_TEMPERAMENT", "未知动势 %r" % bible.get("motion_temperament")))
    if bible.get("contrast_policy") not in CONTRAST_POLICIES:
        issues.append(_iss("BIBLE_CONTRAST", "未知对比政策 %r" % bible.get("contrast_policy")))
    if not bible.get("silence_policy"):
        issues.append(_iss("BIBLE_SILENCE", "缺少静默政策"))
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def _iss(code, msg):
    return {"severity": "err", "layer": "bible", "code": code, "msg": msg}
