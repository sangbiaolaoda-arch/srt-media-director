"""critic.py — 机器视觉 Critic：截图 → 判分 → PASS/FAIL → 修复路由。

这是「生成 → 截图 → 检查 → 修复」闭环里「检查」那一环。它读**截图**（真实光栅）
加**规范**（结构），给出判决与修复目标层：

    PASS → 下一个 Beat
    FAIL → route() 给出 target_layer（intent / layout / render）→ 回上游修复

Critic 不产生几何、不选模板；它只判断「这张图成不成立」，并指路。
"""
import os

from . import critic_rules  # noqa: F401  (可选的规则扩展点；见下)


def _score(issues):
    return max(0.0, 1.0 - 0.2 * len(issues))


def criticize(spec, png_path=None, intent=None):
    """对一帧（规范 + 截图）做机器视觉评审。

    返回 {"verdict","issues","raster","scores"}。
    """
    from validation import geometry, typography, safe_area, visual_regression

    issues = []
    issues += geometry.check(spec)
    issues += typography.check(spec)
    issues += safe_area.check(spec)

    raster = {}
    if png_path and os.path.exists(png_path):
        try:
            raster["ink_ratio"] = visual_regression.ink_ratio(png_path)
        except Exception as e:  # 图读不了也要给出明确问题
            issues.append({"code": "CRITIC_PNG_UNREADABLE", "msg": str(e)})
            raster["ink_ratio"] = None
        if raster.get("ink_ratio") is not None:
            if raster["ink_ratio"] < 0.005:
                issues.append({"code": "CRITIC_BLANK_FRAME", "msg": "几乎空帧（墨量过低）"})
            elif raster["ink_ratio"] > 0.6:
                issues.append({"code": "CRITIC_OVERCROWDED", "msg": "画面过密（墨量过高）"})

    verdict = "PASS" if not issues else "FAIL"
    return {
        "verdict": verdict,
        "issues": issues,
        "raster": raster,
        "scores": {"quality": round(_score(issues), 2), "ink": raster.get("ink_ratio")},
    }


# 问题码 → 上游修复层（§10 修复必须回到正确上游层）
_ROUTE = (
    ("CRITIC_OVERCROWDED", "intent"),   # 太密 → 改密度/留白，属语义决策
    ("CRITIC_BLANK_FRAME", "intent"),   # 太空 → 改意图
    ("TYPO_", "intent"),                # 字号非词表 → 语义层
    ("SAFE_", "layout"),                # 越安全区 → 布局层
    ("GEO_", "layout"),                 # 越界/尺寸 → 布局层
    ("CRITIC_PNG_UNREADABLE", "render"),
)


def route(issues):
    """把问题路由到上游层。返回 target_layer（intent/layout/render）与问题码。"""
    layers = []
    codes = [i.get("code", "") for i in issues]
    for code in codes:
        target = "layout"
        for pref, lay in _ROUTE:
            if code.startswith(pref):
                target = lay
                break
        if target not in layers:
            layers.append(target)
    # 优先级：语义 > 布局 > 渲染
    order = {"intent": 0, "layout": 1, "render": 2}
    layers.sort(key=lambda l: order.get(l, 3))
    return {"target_layer": layers[0] if layers else None,
            "all_layers": layers, "issue_codes": codes}
