"""critic_rules.py — 视觉 Critic 的可扩展规则槽（默认空）。

专业团队在这里挂自己的审美规则（例：焦点必须落在黄金分割带、同一 Beat 内
不得超过 N 种线宽）。默认不做任何事，保持 Critic 行为可预测、可验证。
"""

RULES = []


def register(fn):
    """挂一条规则：fn(spec, png_path, intent) -> list[issue]。"""
    RULES.append(fn)
    return fn
