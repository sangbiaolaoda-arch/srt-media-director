"""visual_intent.py — Agent 输出的语义视觉意图（零坐标）。

本模块是 ``intent_layer`` 的规范入口（单一逻辑源）。核心契约见
``schemas/visual-intent.schema.json``：意图里**禁止**出现 strategy/template/像素键。
"""
import intent_layer as _il

REQUIRED = _il.REQUIRED
MOTION_INTENTS = _il.MOTION_INTENTS


def derive(beat):
    """从一拍推导视觉意图（零坐标）。"""
    return _il.derive_intent(beat)


def validate(intent):
    """意图契约校验；返回 issues（空 = PASS）。会拒斥模板选择器。"""
    return _il.validate_intent(intent)


def is_template_selector(obj):
    """是否「模板选择器」式输出（含 strategy/template/像素）——应被拒绝。"""
    return _il.is_template_selector(obj)


def leak_keys(obj):
    """递归找出模板 / 像素泄漏键的点路径（空 = 干净）。"""
    return _il.template_leak_keys(obj)


def schema_path():
    """意图 JSON Schema 的路径（供校验器 / 文档引用）。"""
    import os
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "schemas", "visual_intent.json")
