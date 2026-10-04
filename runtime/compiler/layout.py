"""layout.py — 构图求解（区域 / 槽位 / 留白）。

把「几个元素、放哪儿」交给**规则**求解，而不是写死坐标：
    cols(n)   n 列等宽分槽
    rows(n)   n 行等高分行
数值全部来自 ref_frame 的版心常量（MARGIN / CONTENT_W / COL_GAP）。
"""
import ref_frame as R


def solve_slots(n, gap=R.COL_GAP):
    """n 列槽位：[(x, w), ...]。"""
    return R.cols(n, gap=gap)


def solve_rows(n, y0, total, gap=R.COL_GAP):
    """n 行槽位：[(y, h), ...]。"""
    return R.rows(n, y0, total, h_gap=gap)


def plan(dsl):
    """整片构图求解（复用已验证的 composition_planner）。"""
    import composition_planner as _cp
    return _cp.plan(dsl)


def safe_area():
    """安全区（版心）。"""
    return {"margin": R.MARGIN, "x0": R.MARGIN, "y0": 0,
            "x1": R.CANVAS_W - R.MARGIN, "y1": R.CANVAS_H}
