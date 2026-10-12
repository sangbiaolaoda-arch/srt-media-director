"""visual_regression.py — 光栅校验（墨量 / 与基线差异）。"""
from PIL import Image


def _flat(im):
    """把图像像素规范化为「扁平通道整数列表」。

    Pillow 的 get_flattened_data() 在不同版本里返回形态不同：新版返回扁平整数
    序列，一些构建仍返回逐像素元组。这里统一成扁平整数列表，既可去掉
    getdata() 的弃用告警，又不依赖具体返回形态。
    """
    data = list(im.get_flattened_data())
    if data and isinstance(data[0], tuple):
        out = []
        for px in data:
            out.extend(px)
        return out
    return data


def ink_ratio(png_path):
    """非背景像素占比（墨量）。背景取暖灰 #F3F2EF。"""
    im = Image.open(png_path).convert("RGB")
    px = _flat(im)
    n = 0
    for i in range(0, len(px), 3):
        if abs(px[i] - 243) + abs(px[i + 1] - 242) + abs(px[i + 2] - 239) > 24:
            n += 1
    return round(n / (im.width * im.height), 4)


def diff(a_path, b_path, size=(160, 90)):
    """两图差异（0..255 平均通道差）。0 = 相同。"""
    a = Image.open(a_path).convert("RGB").resize(size)
    b = Image.open(b_path).convert("RGB").resize(size)
    pa, pb = _flat(a), _flat(b)
    d = sum(abs(x - y) for x, y in zip(pa, pb))
    return round(d / (size[0] * size[1] * 3), 1)


def check_against_baseline(png_path, baseline_path, max_diff=30.0):
    """与基线对比；超阈值算回归。"""
    d = diff(png_path, baseline_path)
    return {"code": "VR_REGRESSION", "msg": "与基线差异 %.1f" % d, "diff": d} if d > max_diff else None
