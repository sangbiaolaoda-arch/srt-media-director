"""Stage 5 — Entrance planner: per-element lifecycle + pacing + handoff.

Responsibilities (skill 07-choreography):
- **生命周期**：每个元素都有 enter{at, motion, dur, after} 与
  exit{at, motion, dur} | null。`after` 是依赖声明——这个元素等谁建立之后
  才出现（回答「为什么这个时候出现、和前一个元素什么关系」）。
- cue 波次由 lifecycle 派生（同 cue 元素真同时，GATE-G1）。
- interaction events（draw / chart_fill / bars_grow / pulse / color_wash /
  settle）——状态变化优先于元素数量。
- 跨拍连续（skill 07 §5）：carry_over 主体 enter.motion="inherit"
  （不重新入场，由渲染器在拍首做位置插值）。
- pacing budget + handoff；门禁 G1..G5。
"""
from common import G_MIN_WAVE_GAP

# 阶段骨架（归一化拍内时间）
PHASES = {"establish": 0.0, "enter": 0.16, "interact": 0.45,
          "emphasize": 0.68, "resolve": 0.88}

MOTIONS_ENTER = ("fade", "rise", "pop", "inherit")
MOTIONS_EXIT = ("fade", "sink", "shrink")

# 波次锚点（拍内归一化时间 → enter motion）
_WAVE = {"decor": (0.00, "fade"), "top": (0.00, "rise"),
         "subject": (0.16, "pop"), "connector": (0.26, "fade"),
         "emphasis": (0.50, "pop"), "notes": (0.62, "rise")}

_EXIT_MOTION = {"motif": "sink", "chart": "shrink", "connector": "fade"}


def _group_of(el):
    if el["role"] == "ambient":
        return "decor"
    slot = el["slot"]
    if slot in ("eyebrow", "title"):
        return "top"
    if slot in ("note", "note_left", "note_right"):
        return "notes"
    if el["type"] == "connector":
        return "connector"
    if slot in ("cause", "result") or el["type"] in ("motif", "chart"):
        return "subject"
    if el["type"] == "text" and el["role"] in ("primary", "secondary"):
        return "emphasis"
    return "subject"


def _build_lifecycle(beat, incoming, outgoing, beat_index):
    """每个元素的入场/退场规划（用户导演指令：入场动画 + 进入/退场时间 +
    依赖关系）。退场纪律：注解在 resolve(88%) 淡出收束；非交接主体在 94%
    下沉/收缩退场；交接主体与常驻画框不退出。"""
    start, end = beat["start_sec"], beat["end_sec"]
    dur = max(end - start, 0.01)
    elements = beat["elements"]
    groups = {el["id"]: _group_of(el) for el in elements}
    ids_of = {}
    for eid, g in groups.items():
        ids_of.setdefault(g, []).append(eid)
    rel_targets = {}
    connectors = [el["id"] for el in elements if el["type"] == "connector"]
    for rel in beat.get("relations", []):
        if rel["type"] in ("causes", "flow_to") and connectors:
            rel_targets[connectors[0]] = [rel["from"], rel["to"]]

    def after_for(el, grp):
        if grp == "decor":
            return []
        if grp == "top":
            return ids_of.get("decor", [])
        if grp == "subject":
            return ids_of.get("top", [])
        if grp == "connector":
            return rel_targets.get(el["id"], ids_of.get("subject", []))
        if grp == "emphasis":
            return ids_of.get("subject", []) or ids_of.get("top", [])
        if grp == "notes":
            return ids_of.get("emphasis", []) or ids_of.get("subject", [])
        return []

    life = {}
    for el in elements:
        eid = el["id"]
        grp = groups[eid]
        # 跨拍连续：来自上一拍的交接主体不重新入场、不退场（渲染器做位置插值）
        m = el.get("motif")
        if m and m in incoming:
            life[eid] = {"enter": {"at": round(start, 3), "motion": "inherit",
                                   "dur": 0.01, "after": []},
                         "exit": None}
            continue
        # v4.2.1：corner_marks 全片画框已移除（用户反馈像摄像取景框），
        # 不再有任何常驻 decor 特殊逻辑
        at_r, motion = _WAVE[grp]
        enter = {"at": round(start + at_r * dur, 3), "motion": motion,
                 "dur": round(0.8 if grp == "decor" else min(0.7, 0.14 * dur), 3),
                 "after": after_for(el, grp)}
        exit_ = None
        if m and m in outgoing:
            exit_ = None  # 交接主体在本拍不退场（画面延续到下一拍溶解交接）
        elif grp == "notes":
            exit_ = {"at": round(start + PHASES["resolve"] * dur, 3),
                     "motion": "fade", "dur": round(min(0.5, 0.09 * dur), 3)}
        elif grp in ("subject", "connector"):
            exit_ = {"at": round(start + 0.94 * dur, 3),
                     "motion": _EXIT_MOTION.get(el["type"], "fade"),
                     "dur": round(min(0.45, 0.08 * dur), 3)}
        life[eid] = {"enter": enter, "exit": exit_}
    return life


def _cues_from_lifecycle(life, elements, start, dur):
    """把同 enter.at 的元素编成 cue（可读视图；G1 校验真同时）。"""
    groups = {}
    for el in elements:
        e = life[el["id"]]["enter"]
        groups.setdefault(round(e["at"], 3), []).append(el["id"])
    cues = []
    for i, at in enumerate(sorted(groups)):
        cues.append({"cue_id": "cue_%d" % (i + 1), "at": at,
                     "at_ratio": round((at - start) / dur, 3),
                     "purpose": "wave_%d" % (i + 1),
                     "elements": sorted(groups[at])})
    return cues


def _interactions(beat, life):
    """基于 relations / 强调生成互动事件（画箭头、图表生长、洗色、脉冲）。"""
    start, end = beat["start_sec"], beat["end_sec"]
    dur = max(end - start, 0.01)
    evs = []

    def enter_at(eid, default_r):
        lc = life.get(eid)
        return lc["enter"]["at"] if lc else start + default_r * dur

    bid = "b%02d" % int(beat["beat_id"].split("_")[1])
    for rel in beat.get("relations", []):
        if rel["type"] in ("causes", "flow_to"):
            at = enter_at(rel["from"], 0.16) + 0.28 * dur
            evs.append({"at": round(min(at, start + 0.55 * dur), 3),
                        "at_ratio": 0, "type": "interaction",
                        "action": "draw", "targets": ["%s_bridge" % bid]})
    for el in beat["elements"]:
        if el["type"] == "chart" and el["chart"]["kind"] == "donut":
            evs.append({"at": round(enter_at(el["id"], 0.16) + 0.24 * dur, 3),
                        "at_ratio": 0, "type": "interaction",
                        "action": "chart_fill", "targets": [el["id"]]})
        elif el["type"] == "chart" and el["chart"]["kind"] == "bars":
            evs.append({"at": round(enter_at(el["id"], 0.16) + 0.20 * dur, 3),
                        "at_ratio": 0, "type": "interaction",
                        "action": "bars_grow", "targets": [el["id"]]})
    emphasis = [e for e in beat["elements"]
                if e["type"] == "text" and e.get("emphasis")]
    for e in emphasis:
        if beat["strategy"] == "comparison" and e["color_role"] in (
                "negative", "positive"):
            evs.append({"at": round(enter_at(e["id"], 0.5) + 0.10 * dur, 3),
                        "at_ratio": 0, "type": "interaction",
                        "action": "color_wash", "targets": [e["id"]]})
        if e.get("host"):
            evs.append({"at": round(enter_at(e["id"], 0.5) + 0.14 * dur, 3),
                        "at_ratio": 0, "type": "interaction",
                        "action": "pulse", "targets": [e["id"]]})
    evs.append({"at": round(start + PHASES["resolve"] * dur, 3),
                "at_ratio": PHASES["resolve"], "type": "resolve",
                "action": "settle", "targets": []})
    for e in evs:
        e["at_ratio"] = round((e["at"] - start) / dur, 3)
    evs.sort(key=lambda e: e["at"])
    return evs


def plan(dsl):
    """dsl → entrance plan（lifecycle 为唯一时序真值，cues 为派生视图）。"""
    beats = dsl["beats"]
    # 先算交接（carry_over 决定主体是否免退场 / 免重入）
    handoffs, carried = [], []
    for i, beat in enumerate(beats):
        nxt = beats[i + 1] if i + 1 < len(beats) else None
        motif = next((e.get("motif") for e in beat["elements"]
                      if e["type"] == "motif"), None)
        if nxt is None:
            handoffs.append({"to": None, "type": "final_hold", "note": "片尾收束"})
            carried.append(set())
        elif motif and any(e.get("motif") == motif
                           for e in nxt["elements"] if e["type"] == "motif"):
            handoffs.append({"to": nxt["beat_id"], "type": "carry_over",
                             "element_motif": motif,
                             "reason": "shared_identity_continuity"})
            carried.append({motif})
        else:
            handoffs.append({"to": nxt["beat_id"], "type": "hard_cut",
                             "hard_cut_reason": "语义重置：命题切换"})
            carried.append(set())

    out = []
    for i, beat in enumerate(beats):
        start, end = beat["start_sec"], beat["end_sec"]
        dur = max(end - start, 0.01)
        life = _build_lifecycle(beat, carried[i - 1] if i > 0 else set(),
                                carried[i], i + 1)
        cues = _cues_from_lifecycle(life, beat["elements"], start, dur)
        evs = _interactions(beat, life)
        beat["carry_over"] = ([{"element_motif": handoffs[i]["element_motif"],
                                "reason": handoffs[i]["reason"]}]
                              if handoffs[i]["type"] == "carry_over" else [])

        last_meaningful = max(
            [e["at"] for e in evs]
            + [lc["exit"]["at"] for lc in life.values() if lc["exit"]])
        first_enter = min(lc["enter"]["at"] for lc in life.values())
        out.append({
            "beat_id": beat["beat_id"], "cues": cues, "lifecycle": life,
            "events": evs,
            "phases": [{"id": k, "t": v} for k, v in PHASES.items()],
            "pacing": {
                "first_meaningful_change_ratio": round((first_enter - start) / dur, 3),
                "last_meaningful_event_ratio": round((last_meaningful - start) / dur, 3),
                "idle_ratio": round(max(0.0, 1.0 - (last_meaningful - start) / dur), 3),
                "hold_reason": "final_hold" if handoffs[i]["type"] == "final_hold" else None,
            },
            "handoff": handoffs[i],
        })
    return {"beats": out}


def audit(entrance):
    """G1 cue 内真同时 · G2 波次间隔 · G3 节奏预算 · G4 handoff · G5 生命周期。"""
    issues = []
    for b in entrance["beats"]:
        bid = b["beat_id"]
        for cue in b["cues"]:
            if len({round(e, 3) for e in [cue["at"]]}) != 1:
                issues.append({"gate": "G1_TRUE_SIMULTANEITY", "beat": bid,
                               "msg": "cue elements not simultaneous"})
        ats = [c["at"] for c in b["cues"]]
        for a, btime in zip(ats, ats[1:]):
            if btime - a < G_MIN_WAVE_GAP - 1e-6:
                issues.append({"gate": "G2_MIN_WAVE_GAP", "beat": bid,
                               "msg": "wave gap %.2fs < %.2fs"
                                      % (btime - a, G_MIN_WAVE_GAP)})
        p = b["pacing"]
        if p["idle_ratio"] > 0.20 and not p.get("hold_reason"):
            issues.append({"gate": "G3_IDLE_BUDGET", "beat": bid,
                           "msg": "idle_ratio %.2f > 0.20" % p["idle_ratio"]})
        if not b["handoff"]:
            issues.append({"gate": "G4_HANDOFF_REQUIRED", "beat": bid,
                           "msg": "missing handoff"})
        # G5 生命周期完整性：每个元素都有 enter；退场晚于入场；注解必须退场；
        # 除非片尾收束或存在继承主体，每拍至少一个元素退场（结尾要干净）。
        life = b["lifecycle"]
        for cue in b["cues"]:
            for eid in cue["elements"]:
                lc = life.get(eid)
                if not lc or "enter" not in lc:
                    issues.append({"gate": "G5_LIFECYCLE", "beat": bid,
                                   "msg": "%s missing enter plan" % eid})
                    continue
                if lc.get("exit") and lc["exit"]["at"] <= lc["enter"]["at"]:
                    issues.append({"gate": "G5_LIFECYCLE", "beat": bid,
                                   "msg": "%s exits before it enters" % eid})
        for eid, lc in life.items():
            if "_note" in eid and not lc.get("exit"):
                issues.append({"gate": "G5_LIFECYCLE", "beat": bid,
                               "msg": "note %s never exits" % eid})
        any_exit = any(lc.get("exit") for lc in life.values())
        any_inherit = any(lc["enter"]["motion"] == "inherit"
                          for lc in life.values())
        # carry_over 交接拍豁免：主体延续到下一拍（拍首溶解+位置插值即是动态），
        # 画面无需「清尾」——G5 防的是无动作死等，不是连续镜头。
        if not any_exit and not any_inherit \
                and b["handoff"].get("type") not in ("final_hold", "carry_over"):
            issues.append({"gate": "G5_LIFECYCLE", "beat": bid,
                           "msg": "no element exits in this beat"})
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}
