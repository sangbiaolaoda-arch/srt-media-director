"""primitives — 图元工厂（画法的可复用零件）。

Agent 不碰这里；compiler 用它们拼几何。所有图元都是**函数**（吃 cx/cy/scale/col），
不是写死坐标的贴图——这样才能被新构图复用（v7.2 经验）。
"""
from . import text, shape, path, chart, connector, motif  # noqa: F401

__all__ = ["text", "shape", "path", "chart", "connector", "motif"]
