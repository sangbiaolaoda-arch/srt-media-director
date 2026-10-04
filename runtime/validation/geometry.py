"""geometry.py — 几何校验：框在画布内。"""
import ref_frame as R


def check(spec):
    issues = []
    for el in spec.get("elements", []):
        box = el.get("box")
        if not (isinstance(box, (tuple, list)) and len(box) == 4):
            issues.append({"code": "GEO_BAD_BOX", "msg": "元素 %s 的 box 非法" % el.get("id")})
            continue
        x, y, w, h = box
        if x < -2 or y < -2 or x + w > R.CANVAS_W + 2 or y + h > R.CANVAS_H + 2:
            issues.append({"code": "GEO_OUT_OF_CANVAS",
                           "msg": "元素 %s 越画布 %s" % (el.get("id"), box)})
    return issues
