"""Stage 6 — 诊断树 CLI（v6.0）。

用法：
    python runtime/diagnose.py <out_dir>

读取 <out_dir>/work/ 的校验产物（validation / contract / style / layout），
把每个 issue 路由到「修复层 + 动作 + 单变量重拍预算」。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime"))
import repair_routing  # noqa


def _load(work, name):
    p = os.path.join(work, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def diagnose(out_dir):
    work = os.path.join(out_dir, "work")
    reports = {
        "contract": _load(work, "contract-audit.json"),
        "style": _load(work, "style-audit.json"),
        "layout": _load(work, "layout-audit.json"),
        "validation": _load(work, "validation-report.json"),
    }
    issues = []
    for src, rep in reports.items():
        if not rep:
            continue
        for i in rep.get("issues", []):
            issues.append(i)
    routed = repair_routing.route_all(issues)
    budget = repair_routing.RepairBudget()
    for r in routed:
        if r["layer"] in ("transition", "token", "contract"):
            budget.attempt(r.get("code", "?"))
    return {"issues": routed, "budget": budget.report(),
            "table": repair_routing.table_md()}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    out = diagnose(sys.argv[1])
    print(out["table"])
    print("\n## 本次产物诊断（%d 条）" % len(out["issues"]))
    for r in out["issues"][:30]:
        print("  [%s] %s → %s" % (r["layer"], r["code"], r["action"]))
    print("\n预算：", json.dumps(out["budget"], ensure_ascii=False))
