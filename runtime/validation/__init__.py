"""validation — 渲染后校验层（多种检查器，各自独立）。

    geometry          —— 几何：框在画布内、元素不越界
    typography        —— 字排：字号来自字阶、文本在框内
    safe_area         —— 安全区：内容不越版心
    visual_regression —— 光栅：墨量 / 与基线差异（回归）

每个 check(spec) 返回 issue 列表（空 = PASS）。Critic 汇总它们判决。
"""
from . import geometry, typography, safe_area, visual_regression  # noqa: F401
from . import anti_ppt, cognitive_load  # noqa: F401

__all__ = ["geometry", "typography", "safe_area", "visual_regression",
           "anti_ppt", "cognitive_load"]
