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
