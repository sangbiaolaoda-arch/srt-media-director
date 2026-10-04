"""composition.py — 意图 → 构图（语法 1:N 实现）。

**关键**：语法到实现是 1:N，不是「语法 == 模板」。
    同一个语法可由不同实现表达；同一个实现可服务多个语法。
实现里所有坐标都来自 ref_frame 的**规则**（cols/rows/stroke），不来自 Agent。
"""
import composition_compiler as _cc

GRAMMAR_REALIZATION = _cc.GRAMMAR_REALIZATION


def compile_intent(intent):
    """意图 → (视觉 DSL, meta)。"""
    return _cc.compile_intent(intent)


def realize(intent, impl=None):
    """按指定实现（或自动选择）生成构图。"""
    if impl is None:
        return compile_intent(intent)
    import ref_frame as R
    spec = _cc._realize(intent, impl)
    meta = {"beat_id": intent.get("beat_id"), "realization": impl,
            "issues": R.audit_spec(spec)}
    return spec, meta


def realizations_for(op):
    """某语法可用的实现名集合（证明 1:N）。"""
    return list(GRAMMAR_REALIZATION.get(op, ()))


def coverage():
    """每个语法是否都有实现可画（Runtime 有视觉语言）。"""
    import visual_grammar as VG
    return {op: op in GRAMMAR_REALIZATION for op in VG.GRAMMAR_OPS}
