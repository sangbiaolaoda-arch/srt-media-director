"""typography.py — 字排校验：字号必须来自字阶。"""
import re

import ref_frame as R

# 允许的字号（来自 type_scale 阶梯 + 标题）
ALLOWED = {12, 13, 14, 15, 26, 30, 34}


def check(spec):
    issues = []
    for el in spec.get("elements", []):
        for m in re.finditer(r'font-size="([0-9.]+)"', el.get("svg", "")):
            size = float(m.group(1))
            if size not in ALLOWED:
                issues.append({"code": "TYPO_OFF_SCALE",
                               "msg": "元素 %s 用了非字阶字号 %s" % (el.get("id"), size)})
    return issues


def scale():
    """字阶表（供文档 / 前端）。"""
    return dict(R.type_scale.__wrapped__() if hasattr(R.type_scale, "__wrapped__") else {})
