"""Canonical entrance lifecycle — the ONE per-element enter/exit/pacing model.

This is the canonical home of the logic that previously lived only in
``entrance_planner.py`` (which the production pipeline actually runs) plus the
two forked ``entrance.py`` modules in ``motion/`` and ``scene/``.

Behaviour is preserved from ``entrance_planner`` (PHASE 3 wires it to delegate
here). Motion *only* plans state-over-time: the wave anchor ratio, enter/exit
motion names (resolved via :mod:`motion_canonical.vocabulary`) and the derived
cue view.
"""
from __future__ import annotations

from . import sequencing as _seq
from . import vocabulary as _vocab

# Phase skeleton (normalized in-beat time), preserved from entrance_planner.
PHASES = {"establish": 0.0, "enter": 0.16, "interact": 0.45,
          "emphasize": 0.68, "resolve": 0.88}

# Wave anchors: normalized in-beat time -> enter motion (canonical names).
_WAVE = {"decor": (0.00, "fade"), "top": (0.00, "rise"),
         "subject": (0.16, "pop"), "connector": (0.26, "fade"),
         "emphasis": (0.50, "pop"), "notes": (0.62, "rise")}

_EXIT_MOTION = {"motif": "sink", "chart": "shrink", "connector": "fade_out"}

# Default minimum wave gap (callers may override; production uses common.G_MIN_WAVE_GAP).
DEFAULT_MIN_WAVE_GAP = 0.35


def _norm_motion(name):
    """Resolve a production motion name to a canonical action name."""
    return _vocab.canonical(name)


def group_of(el):
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


def build_lifecycle(beat, incoming, outgoing, beat_index):
    """Per-element enter/exit plan (the single timing truth for a beat)."""
    start, end = beat["start_sec"], beat["end_sec"]
    dur = max(end - start, 0.01)
    elements = beat["elements"]
    groups = {el["id"]: group_of(el) for el in elements}
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
        m = el.get("motif")
        if m and m in incoming:
            life[eid] = {"enter": {"at": round(start, 3), "motion": "carry_over",
                                   "dur": 0.01, "after": []},
                         "exit": None}
            continue
        at_r, motion = _WAVE[grp]
        enter = {"at": round(start + at_r * dur, 3), "motion": _norm_motion(motion),
                 "dur": round(0.8 if grp == "decor" else min(0.7, 0.14 * dur), 3),
                 "after": after_for(el, grp)}
        exit_ = None
        if m and m in outgoing:
            exit_ = None
        elif grp == "notes":
            exit_ = {"at": round(start + PHASES["resolve"] * dur, 3),
                     "motion": "fade_out", "dur": round(min(0.5, 0.09 * dur), 3)}
        elif grp in ("subject", "connector"):
            exit_ = {"at": round(start + 0.94 * dur, 3),
                     "motion": _norm_motion(_EXIT_MOTION.get(el["type"], "fade_out")),
                     "dur": round(min(0.45, 0.08 * dur), 3)}
        life[eid] = {"enter": enter, "exit": exit_}
    return life


def cues_from_lifecycle(life, elements, start, dur):
    return _seq.cues_from_lifecycle(life, elements, start, dur)


def respace_cues(cues, life, start, dur, min_gap=None):
    """Re-space derived cues to >= ``min_gap``; merge nearest waves when too short."""
    min_gap = DEFAULT_MIN_WAVE_GAP if min_gap is None else min_gap
    cap = start + 0.86 * dur
    groups = [[c] for c in sorted(cues, key=lambda c: c["at"])]
    if len(groups) <= 1:
        return cues

    def _shift(gs):
        out, t = [], None
        for g in gs:
            a = g[0]["at"]
            t = a if t is None else max(a, t + min_gap)
            out.append(t)
        return out

    while len(groups) > 1 and _shift(groups)[-1] > cap + 1e-9:
        gaps = [groups[i + 1][0]["at"] - groups[i][-1]["at"]
                for i in range(len(groups) - 1)]
        i = min(range(len(gaps)), key=lambda k: gaps[k])
        groups[i] = groups[i] + groups[i + 1]
        groups.pop(i + 1)

    times = _shift(groups)
    out = []
    for g, t in zip(groups, times):
        eids = sorted(e for c in g for e in c["elements"])
        at = round(t, 3)
        for eid in eids:
            lc = life.get(eid)
            if lc and lc.get("enter"):
                lc["enter"]["at"] = at
        out.append({"cue_id": None, "at": at,
                    "at_ratio": round((at - start) / dur, 3),
                    "purpose": None, "elements": eids})
    for i, c in enumerate(out):
        c["cue_id"] = "cue_%d" % (i + 1)
        c["purpose"] = "wave_%d" % (i + 1)
    return out


def interactions(beat, life):
    """Interaction events (draw / chart_fill / bars_grow / pulse / color_wash / settle)."""
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


def plan(dsl, min_gap=None):
    """dsl -> entrance plan (lifecycle is the single timing truth; cues derived)."""
    beats = dsl["beats"]
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
        life = build_lifecycle(beat, carried[i - 1] if i > 0 else set(),
                               carried[i], i + 1)
        cues = cues_from_lifecycle(life, beat["elements"], start, dur)
        cues = respace_cues(cues, life, start, dur, min_gap)
        evs = interactions(beat, life)
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


def audit(entrance, min_gap=None):
    """G1 simultaneity · G2 wave gap · G3 idle budget · G4 handoff · G5 lifecycle."""
    min_gap = DEFAULT_MIN_WAVE_GAP if min_gap is None else min_gap
    issues = []
    for b in entrance["beats"]:
        bid = b["beat_id"]
        for cue in b["cues"]:
            if len({round(e, 3) for e in [cue["at"]]}) != 1:
                issues.append({"gate": "G1_TRUE_SIMULTANEITY", "beat": bid,
                               "msg": "cue elements not simultaneous"})
        ats = [c["at"] for c in b["cues"]]
        for a, btime in zip(ats, ats[1:]):
            if btime - a < min_gap - 1e-6:
                issues.append({"gate": "G2_MIN_WAVE_GAP", "beat": bid,
                               "msg": "wave gap %.2fs < %.2fs" % (btime - a, min_gap)})
        p = b["pacing"]
        if p["idle_ratio"] > 0.20 and not p.get("hold_reason"):
            issues.append({"gate": "G3_IDLE_BUDGET", "beat": bid,
                           "msg": "idle_ratio %.2f > 0.20" % p["idle_ratio"]})
        if not b["handoff"]:
            issues.append({"gate": "G4_HANDOFF_REQUIRED", "beat": bid,
                           "msg": "missing handoff"})
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
        any_inherit = any(lc["enter"]["motion"] == "carry_over"
                          for lc in life.values())
        if not any_exit and not any_inherit \
                and b["handoff"].get("type") not in ("final_hold", "carry_over"):
            issues.append({"gate": "G5_LIFECYCLE", "beat": bid,
                           "msg": "no element exits in this beat"})
    return {"status": "PASS" if not issues else "FAIL", "issues": issues}
