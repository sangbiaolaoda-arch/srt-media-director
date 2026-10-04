"""constraints.py — 构图约束门禁（构图能不能成立）。

与 validation（渲染后校验）不同，这里在**编译期**就拦：
    强调预算（一帧一处，且只落一个元素）
    元素非空、id 唯一、框在画布内、motion 合法
    意图声明的每个语法都必须有实现可画
返回 {"status":"PASS"/"FAIL","issues":[...]}。
"""
import ref_frame as R


def check(spec, intent=None):
    issues = []
    for code in R.audit_spec(spec):
        issues.append({"code": "CON_%s" % code, "msg": code})
    if R.count_accent(spec) > 1:
        issues.append({"code": "CON_ACCENT_BUDGET",
                       "msg": "强调预算超支：%d（应 ≤ 1）" % R.count_accent(spec)})
    if intent is not None:
        from . import composition
        for op in intent.get("grammar", []):
            if op not in composition.GRAMMAR_REALIZATION:
                issues.append({"code": "CON_GRAMMAR_UNREALIZABLE",
                               "msg": "语法 %s 没有实现可画" % op})
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}
