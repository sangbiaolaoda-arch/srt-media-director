"""render — 渲染层：视觉 DSL → HTML/SVG → PNG（多后端可降级）。

    html_renderer       —— DSL → 独立 HTML 文件
    playwright_renderer —— Playwright（若有）优先；否则降级
    screenshot          —— 自动选后端把一帧截成 PNG

后端优先级：playwright > chromium(CLI) > cairosvg。
纯 Python 环境也能跑（cairosvg 兜底），因此 CI 不依赖浏览器。
"""
from . import html_renderer, playwright_renderer, screenshot  # noqa: F401

__all__ = ["html_renderer", "playwright_renderer", "screenshot"]
