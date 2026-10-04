"""grammar.py — 抽象视觉语法词汇表（Agent 的「视觉语言」词表）。

只定义「有哪些语法操作」，**不定义「用哪个模板实现」**。
「语法 → 实现」的映射在 ``compiler.composition.GRAMMAR_REALIZATION``。
把两者混在一起，就是把 Agent 重新变回模板选择器。
"""
import visual_grammar as _vg

GRAMMAR_OPS = _vg.GRAMMAR_OPS

_DESC = {
    "establish":   "确立：先给全貌，建立主体与场景",
    "causality":   "因果：A 导致 / 引发 B",
    "contrast":    "对比：A 与 B 并置，突出差异",
    "progression": "进程：A→B→C 顺序推进",
    "hierarchy":   "层级：主次分明，权重有序",
    "emphasis":    "强调：把单一焦点放大",
    "juxtapose":   "并列：多主体同格横向比较",
    "transition":  "转场：一种状态迁移到另一种",
    "abstract":    "抽象：非具象的关系表达",
    "accumulation": "累积：小量反复叠加成大变化",
    "trajectory":  "轨迹：随时间上升 / 下降的路径",
    "threshold":   "阈值：越过某个临界线",
}


def describe(op):
    """语法操作的人类可读解释。"""
    return _DESC.get(op, "")


def unknown_ops(ops):
    """返回 ops 里不属于词表的项（空 = 全部合法）。"""
    return [o for o in ops if o not in GRAMMAR_OPS]


def catalog():
    """整张词表（供文档 / Critic / 前端展示）。"""
    return [{"op": o, "desc": _DESC.get(o, "")} for o in GRAMMAR_OPS]
