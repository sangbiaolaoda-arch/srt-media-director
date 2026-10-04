"""playwright_renderer.py — Playwright 后端（有则用，无则明确降级）。

不假装有这个能力：import 失败就如实报 available=False，由 screenshot 层降级。
"""
import os


def available():
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def chromium_available():
    for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"):
        if os.path.exists(p):
            return p
    return None


def screenshot_html(html_path, png_path, width=680, height=382, scale=2):
    """用 Playwright 把 HTML 截成 PNG。不可用则抛错（由上层降级）。"""
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": height},
                        device_scale_factor=scale)
        pg.goto("file://" + os.path.abspath(html_path))
        pg.screenshot(path=png_path)
        b.close()
    return png_path
