"""visual_regression.py — 光栅校验（墨量 / 与基线差异）。"""
from PIL import Image


def ink_ratio(png_path):
    """非背景像素占比（墨量）。背景取暖灰 #F3F2EF。"""
    im = Image.open(png_path).convert("RGB")
    px = im.getdata()
    n = sum(1 for p in px if abs(p[0] - 243) + abs(p[1] - 242) + abs(p[2] - 239) > 24)
    return round(n / (im.width * im.height), 4)


def diff(a_path, b_path, size=(160, 90)):
    """两图差异（0..255 平均通道差）。0 = 相同。"""
    a = Image.open(a_path).convert("RGB").resize(size)
    b = Image.open(b_path).convert("RGB").resize(size)
    pa, pb = list(a.getdata()), list(b.getdata())
    d = sum(abs(x[0] - y[0]) + abs(x[1] - y[1]) + abs(x[2] - y[2]) for x, y in zip(pa, pb))
    return round(d / (size[0] * size[1] * 3), 1)


def check_against_baseline(png_path, baseline_path, max_diff=30.0):
    """与基线对比；超阈值算回归。"""
    d = diff(png_path, baseline_path)
    return {"code": "VR_REGRESSION", "msg": "与基线差异 %.1f" % d, "diff": d} if d > max_diff else None
