"""primitives — 图元工厂（画法的可复用零件）。

Agent 不碰这里；compiler 用它们拼几何。所有图元都是**函数**（吃 cx/cy/scale/col），
不是写死坐标的贴图——这样才能被新构图复用（v7.2 经验）。

``catalog`` 是「存在哪些图元」的单一真相源（声明在
``contracts/primitive_catalog.v1.json``）；``audit`` 报告代码与声明之间的漂移。
"""
from . import text, shape, path, chart, connector, motif  # noqa: F401
from . import catalog, audit  # noqa: F401

__all__ = ["text", "shape", "path", "chart", "connector", "motif", "catalog", "audit"]
