"""P0⑤ — Visual Necessity: 每个元素都必须能被「删除是否减弱命题」论证。

固定「编译/验证规则」，不固定「长相」。

旧规则是「每拍 ≥3 个图形要素」的**硬门禁** —— 它把「画面够不够丰富」写成了
固定数量，逼迫导演为凑数而堆元素。新规则把它换成**可论证的必要性**：

    对每个元素问一句「如果删掉它，这一拍的 Visual Claim 会变弱吗？」
    · 主元素承载命题           → required（必须存在）
    · 文字/图表/连接件传递信息 → supporting（承载信息）
    · 氛围陪衬（ambient/decor） → optional（默认允许，只因它不冒充信息）

只有「既非氛围、又不承载任何信息、删掉也无损」的元素才被判 UNJUSTIFIED。
数量于是成为结果而非约束：画面该密就密、该简就简。

本模块只做判定，不改画面。
"""
NECESSITY_LEVELS = ("required", "supporting", "optional")

_MEANING_TYPES = ("text", "chart", "connector")


def necessity_for_element(el, beat):
    """返回 {id, necessity, rationale}。"""
    eid = el.get("id")
    role = el.get("role")
    etype = el.get("type")

    if role == "ambient" or etype == "decor":
        return {"id": eid, "necessity": "optional",
                "rationale": "氛围陪衬：不承载命题，删除不减弱 Claim（允许存在）"}

    if role == "primary":
        return {"id": eid, "necessity": "required",
                "rationale": "承载本拍视觉命题主信息：删除则 Claim 不成立"}

    referenced = _is_referenced(eid, beat)
    if etype in _MEANING_TYPES or referenced or el.get("host"):
        return {"id": eid, "necessity": "supporting",
                "rationale": "传递命题的从属信息（%s）：删除会减弱 Claim 的可读性"
                             % ("被关系引用" if referenced else etype)}

    return {"id": eid, "necessity": "optional",
            "rationale": "既非氛围、也不承载信息、删掉无损"}


def _is_referenced(eid, beat):
    if not eid:
        return False
    for r in beat.get("relations", []):
        if r.get("from") == eid or r.get("to") == eid:
            return True
    return False


def audit_beat(beat):
    items, unjustified = [], []
    for el in beat.get("elements", []):
        rec = necessity_for_element(el, beat)
        items.append(rec)
        if rec["necessity"] == "optional" and not (
                el.get("role") == "ambient" or el.get("type") == "decor"):
            unjustified.append(rec["id"])
    has_primary = any(el.get("role") == "primary" for el in beat.get("elements", []))
    status = "PASS" if (not unjustified and has_primary) else "FAIL"
    return {"beat_id": beat.get("beat_id"), "status": status,
            "elements": items, "unjustified": unjustified}


def audit(dsl):
    """全片必要性审计。PASS 要求：每拍有 1 个 primary，且无 UNJUSTIFIED 元素。"""
    beats, issues = [], []
    for b in dsl.get("beats", []):
        r = audit_beat(b)
        beats.append(r)
        if r["status"] != "PASS":
            if r["unjustified"]:
                issues.append(_iss(b.get("beat_id"), "UNJUSTIFIED_ELEMENT",
                                   "元素存在但不承载意义：%s" % r["unjustified"]))
            else:
                issues.append(_iss(b.get("beat_id"), "NO_PRIMARY",
                                   "该拍没有承载命题的主元素"))
    return {"status": "PASS" if not issues else "FAIL",
            "beats": beats, "issues": issues}


def _iss(bid, code, msg):
    return {"severity": "err", "layer": "necessity", "code": code,
            "beat_id": bid, "msg": msg}
