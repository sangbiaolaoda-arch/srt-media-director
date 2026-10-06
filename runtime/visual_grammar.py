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
    """beat + encoding → 构图策略：构图语法决策的唯一权威。

    优先级（与收敛前 ``visual_director._direct_beat`` 完全一致）：
      数字/色彩编码 > 特色角色默认 > 语义关系提示 > 通用默认。
    R8 邻拍避让（同模板轮换）与显式覆写由 Director 在调用本函数后处理。
    """
    etype = encoding.get("type")
    if etype in ENCODING_STRATEGY:
        return ENCODING_STRATEGY[etype]
    role = beat.get("semantic_role")
    if role == "comparison":
        return "comparison"
    role_default = SEMANTIC_DEFAULT.get(role, DEFAULT_STRATEGY)
    if role_default != DEFAULT_STRATEGY:
        return role_default
    pairs = beat.get("semantic_pairs", [])
    if any(p["type"] in PRIMARY_RELATIONS for p in pairs):
        return "cause_effect"
    if any(p["type"] in SECONDARY_RELATIONS for p in pairs):
        return "comparison"
    return DEFAULT_STRATEGY
