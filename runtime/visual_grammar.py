"""P0④ — Visual Grammar: the abstract syntax layer.

固定「视觉语法体系」，不固定「表达」。

Grammar operations describe WHAT a beat does semantically — causality, contrast,
progression, hierarchy, emphasis, juxtapose, transition, establish, abstract —
independently of any material/motif. A motif name (`phone`, `shield`, `compass`,
…) is only ONE of several possible **surface realizations** of a grammar op, and
every op carries a plural set of realizations. The director is therefore free to
express the same grammar with different surfaces on different beats/videos,
instead of pinning a fixed "material" to a semantic role.

This module is deliberately pure: it classifies and proposes, it does not render.
"""
GRAMMAR_OPS = ("establish", "causality", "contrast", "progression",
               "hierarchy", "emphasis", "juxtapose", "transition", "abstract",
               "accumulation", "trajectory", "threshold")

# 关系类型（DSL / 语义对）→ 抽象语法操作
RELATION_GRAMMAR = {
    "causes": "causality",
    "answer_to": "causality",
    "conclusion": "causality",
    "contrast": "contrast",
    "concession": "contrast",
    "flow_to": "progression",
    "sequence": "progression",
    "bound_to": "hierarchy",
    "host": "hierarchy",
    "emphasis": "emphasis",
    "juxtapose": "juxtapose",
}

# 语义角色缺省语法（无显式关系时的兜底）
ROLE_GRAMMAR = {
    "hook": "establish",
    "explanation": "hierarchy",
    "comparison": "contrast",
    "turning_point": "contrast",
    "emphasis": "emphasis",
    "conclusion": "causality",
}

# 抽象语法 → 多种可能的表层实现（motif / decor 画法名，皆为复数候选）
# 关键：语法到表达是一对多，导演可自由挑选；不做「语法==某个素材」的绑定。
GRAMMAR_SURFACES = {
    "establish": ("compass", "map_pin", "flag", "clock", "hourglass"),
    "causality": ("gears", "conn_nodes", "arrow_chain", "bulb", "puzzle"),
    "contrast": ("balance", "chip_row", "bar_mini"),
    "progression": ("arrow_chain", "milestone", "chart_line", "tick_line"),
    "hierarchy": ("ring_pair", "brackets", "orbit", "ruler"),
    "emphasis": ("target", "progress_ring", "halftone"),
    "juxtapose": ("bar_mini", "chip_row", "scatter"),
    "transition": ("wave", "spiral"),
    "abstract": ("dot_grid", "scatter", "plus_field", "cross_hatch"),
}


def relation_to_grammar(rel_type):
    """关系类型 → 语法操作（未知关系保守归为 hierarchy）。"""
    return RELATION_GRAMMAR.get(rel_type, "hierarchy")


def grammar_for_beat(beat):
    """给一拍推导其语法序列（显式关系优先，语义对其次，角色兜底）。

    返回去重后的语法操作列表；始终非空。
    """
    ops = []
    for r in beat.get("relations", []):
        op = relation_to_grammar(r.get("type"))
        if op not in ops:
            ops.append(op)
    for p in beat.get("semantic_pairs", []):
        op = relation_to_grammar(p.get("type"))
        if op not in ops:
            ops.append(op)
    if not ops:
        ops.append(ROLE_GRAMMAR.get(beat.get("semantic_role"), "establish"))
    return ops


def surface_candidates(op, exclude=()):
    """语法操作 → 可用表层实现候选（不固定表达）。"""
    cands = GRAMMAR_SURFACES.get(op, GRAMMAR_SURFACES["abstract"])
    out = tuple(c for c in cands if c not in set(exclude))
    return out or tuple(cands)


def audit(dsl):
    """机器门禁：每拍必须有一组合法的语法操作，且不把素材名当语法。"""
    issues = []
    for b in dsl.get("beats", []):
        ops = b.get("grammar_ops") or grammar_for_beat(b)
        if not ops:
            issues.append(_iss(b["beat_id"], "GRAMMAR_EMPTY", "该拍无语法操作"))
            continue
        for op in ops:
            if op not in GRAMMAR_OPS:
                issues.append(_iss(b["beat_id"], "GRAMMAR_UNKNOWN", "非法语法 %r" % op))
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}


def _iss(bid, code, msg):
    return {"severity": "err", "layer": "grammar", "code": code,
            "beat_id": bid, "msg": msg}


# ---------------------------------------------------------------------------
# P2 — 构图策略决策权（Visual Grammar 接管 Director）
# ---------------------------------------------------------------------------
# 语法层现在拥有「一个拍子用什么构图策略」的决策词汇。此前这些表（角色默认 +
# 语义关系提示 + 编码映射）散落在 visual_director 内部；现集中于此，Director
# 只是消费者。行为与收敛前逐字节等价，由
# tests/phase0/test_grammar_owns_strategy.py + tests/test_golden.py 双重校验。

SEMANTIC_DEFAULT = {
    "hook": "left_to_right_flow",
    "explanation": "single_focus",
    "turning_point": "single_focus",
    "conclusion": "single_focus",
    "comparison": "comparison",
    "emphasis": "center_cluster",
}

DEFAULT_STRATEGY = "single_focus"

# 信息编码类型 → 构图策略（数字/色彩证据优先于语义角色默认）
ENCODING_STRATEGY = {
    "part_to_whole": "center_cluster",
    "change_over_time": "before_after",
    "semantic_color_pair": "comparison",
}

# 语义关系 → 因果提示（仅在角色默认为通用 single_focus 时介入）。
# 因果（answer_to/conclusion）优先于让步（concession），与收敛前一致。
PRIMARY_RELATIONS = ("answer_to", "conclusion")
SECONDARY_RELATIONS = ("concession",)


def composition_strategy(beat, encoding):
    """beat + encoding → 构图策略（单值，向后兼容）。

    P2-1 起，单一权威决策已升级为**候选集**（见 ``composition_candidates``）；
    本函数保留为「语义最佳候选」，与收敛前逐字节等价，供旧调用方与
    ``tests/phase0/test_grammar_owns_strategy.py`` 的等价门禁使用。
    """
    return composition_candidates(beat, encoding)[0]["strategy"]


# ---------------------------------------------------------------------------
# P2-1 — 构图候选集：一个语法语义 → 多个「语义有效」的构图候选
# ---------------------------------------------------------------------------
# 根因（docs/p2-1-root-cause.md）：旧决策是「单值 + 固定映射」，默认分支把大多数
# 语义压成 single_focus；Director 只能靠固定 ROTATION 硬轮换满足 GATE-R8，导致
# single_focus↔cause_effect（82%）机械交替。
# 修复：Grammar 给出每个语义组的**多候选**（``semantic_fit`` 表示贴合度），候选集
# 即「语义正确性的上界」；Director 只在候选中做连续性/多样性平局打破，绝不越过
# 语义正确性去换布局。首个候选恒等于旧单值决策（向后兼容）。

# 语义有效阈值：fit ≥ best - MARGIN 视为「同样合理」，可参与平局打破。
COMPOSITION_MARGIN = 0.2

_CAND_ENCODING = {
    "part_to_whole": (
        ("center_cluster", 1.0, "整体—部分：聚拢呈现整体结构"),
        ("single_focus", 0.8, "聚焦整体，语义仍成立"),
    ),
    "change_over_time": (
        ("before_after", 1.0, "时间变化：前后对照"),
        ("left_to_right_flow", 0.8, "时序自左向右流动，同样表达变化"),
    ),
    "semantic_color_pair": (
        ("comparison", 1.0, "色彩对照：并列比较"),
        ("center_cluster", 0.8, "聚拢对照亦成立"),
    ),
}

_CAND_ROLE = {
    "hook": (
        ("left_to_right_flow", 1.0, "开场铺陈：引入方向"),
        ("center_cluster", 0.82, "聚拢开场亦成立"),
        ("single_focus", 0.8, "单一焦点开场亦成立"),
    ),
    "comparison": (
        ("comparison", 1.0, "比较角色：并列"),
        ("left_to_right_flow", 0.8, "左右并置比较"),
    ),
    "emphasis": (
        ("center_cluster", 1.0, "强调：聚拢聚焦"),
        ("single_focus", 0.83, "单一焦点强调"),
    ),
}

_CAND_RELATION = {
    "causality": (
        ("cause_effect", 1.0, "因果：因→果"),
        ("left_to_right_flow", 0.82, "因果链自左向右流动"),
        ("center_cluster", 0.8, "因果聚拢呈现"),
    ),
    "contrast": (
        ("comparison", 1.0, "对照/让步：并列"),
        ("left_to_right_flow", 0.82, "左右并置对照"),
    ),
}

_CAND_DEFAULT = (
    ("single_focus", 1.0, "无显式关系：单一焦点"),
    ("center_cluster", 0.9, "无显式关系：聚拢呈现"),
    ("left_to_right_flow", 0.9, "无显式关系：横向铺陈"),
    ("comparison", 0.82, "无显式关系：并列呈现"),
)


def _candidate_group(beat, encoding):
    """该拍所属语义组的候选元组 ((strategy, semantic_fit, rationale), …)。"""
    etype = encoding.get("type")
    if etype in _CAND_ENCODING:
        return _CAND_ENCODING[etype]
    role = beat.get("semantic_role")
    if role in _CAND_ROLE:
        return _CAND_ROLE[role]
    pairs = beat.get("semantic_pairs", [])
    if any(p["type"] in PRIMARY_RELATIONS for p in pairs):
        return _CAND_RELATION["causality"]
    if any(p["type"] in SECONDARY_RELATIONS for p in pairs):
        return _CAND_RELATION["contrast"]
    return _CAND_DEFAULT


def composition_candidates(beat, encoding):
    """beat + encoding → 语义有效的构图候选集（semantic_fit 降序）。

    返回 ``[{"strategy", "semantic_fit", "rationale"}, …]``。每个候选都是语义
    成立的表达方式；首个候选恒等于旧 ``composition_strategy``（向后兼容）。
    """
    cands = [{"strategy": s, "semantic_fit": f, "rationale": r}
             for (s, f, r) in _candidate_group(beat, encoding)]
    cands.sort(key=lambda c: (-c["semantic_fit"], c["strategy"]))
    return cands


def acceptable_candidates(beat, encoding, margin=COMPOSITION_MARGIN):
    """语义有效阈值内的候选（fit ≥ best - margin）；恒非空且 ≥2（保证可满足 R8）。"""
    cands = composition_candidates(beat, encoding)
    best = cands[0]["semantic_fit"]
    acc = [c for c in cands if c["semantic_fit"] + 1e-9 >= best - margin]
    if len(acc) < 2 and len(cands) >= 2:
        acc = cands[:2]
    return acc
