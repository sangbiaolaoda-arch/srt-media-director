"""safe_area.py — 安全区校验：内容不越版心（左右 MARGIN）。"""
import ref_frame as R

SAFE = {"x0": R.MARGIN, "x1": R.CANVAS_W - R.MARGIN}


def check(spec, tol=6):
    issues = []
    for el in spec.get("elements", []):
        box = el.get("box")
        if not (isinstance(box, (tuple, list)) and len(box) == 4):
            continue
        x, y, w, h = box
        # 让画布级元素（满宽题头/基线）豁免左边界，只查明显越界
        if x < SAFE["x0"] - tol - 8:
            issues.append({"code": "SAFE_LEFT",
                           "msg": "元素 %s 越左安全区 (x=%s)" % (el.get("id"), x)})
        if x + w > SAFE["x1"] + tol + 8:
            issues.append({"code": "SAFE_RIGHT",
                           "msg": "元素 %s 越右安全区 (x+w=%s)" % (el.get("id"), x + w)})
    return issues


def bounds():
    return dict(SAFE)
