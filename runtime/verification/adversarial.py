"""Adversarial detectors — the cheapest lazy paths must be catchable.

Every detector inspects *behaviour*, not field presence:

  - ``meaningless_elements``  empty-shell elements that only pad a count
    (NOT ``element_count >= 3``)
  - ``fake_motion``           illegal time/duration, or a long beat whose only
    motion is instantaneous (NOT ``motion != null``)
  - ``fake_continuity``       carry-over with no real identity continuity, or a
    persisted element that re-enters for no reason (NOT ``carry_over exists``)
  - ``test_pollution``        tests/golden/threshold/validator/judge edits with no
    corresponding implementation change

Thresholds are conservative so genuine content is not over-flagged.  A non-empty
result is a signal to FAIL/Repair, not something to ignore.
"""
from . import defaults  # noqa: F401  (kept for parity / future shared thresholds)


# ------------------------------------------------------------------ composition
def all_same_composition(dsl, min_beats=4):
    beats = dsl.get("beats", [])
    if len(beats) < min_beats:
        return []
    strats = {b.get("strategy") for b in beats}
    if len(strats) == 1:
        return [{"lazy_path": "all_same_composition",
                 "detail": "%d beats all use %r" % (len(beats), next(iter(strats)))}]
    return []


def single_motif(dsl, min_beats=4):
    motifs = [e.get("motif") for b in dsl.get("beats", [])
              for e in b.get("elements", []) if e.get("type") == "motif"]
    beats = dsl.get("beats", [])
    if len(beats) >= min_beats and len(set(motifs)) == 1 and motifs:
        return [{"lazy_path": "single_motif",
                 "detail": "one motif reused across %d beats" % len(beats)}]
    return []


_LAZY_ROLES = {"decoration", "decorative", "filler", "ornament", "spacer"}


def filler_decorations(dsl, max_ratio=0.5, min_dec=2):
    findings = []
    for b in dsl.get("beats", []):
        els = b.get("elements", [])
        dec = [e for e in els if str(e.get("role", "")).lower() in _LAZY_ROLES]
        if len(dec) >= min_dec and els and len(dec) / len(els) > max_ratio:
            findings.append({"lazy_path": "filler_decorations", "beat": b.get("beat_id"),
                             "detail": "%d/%d decorative elements" % (len(dec), len(els))})
    return findings


def wall_of_text(dsl, max_ratio=0.8, min_elems=3):
    findings = []
    for b in dsl.get("beats", []):
        els = b.get("elements", [])
        if len(els) < min_elems:
            continue
        text = [e for e in els if e.get("type") == "text"]
        if len(text) / len(els) > max_ratio:
            findings.append({"lazy_path": "wall_of_text", "beat": b.get("beat_id"),
                             "detail": "%d/%d text elements" % (len(text), len(els))})
    return findings


def no_meaningful_change(dsl):
    findings = []
    beats = dsl.get("beats", [])
    for prev, cur in zip(beats, beats[1:]):
        ids_prev = {e.get("id") for e in prev.get("elements", [])}
        ids_cur = {e.get("id") for e in cur.get("elements", [])}
        if ids_prev and ids_prev == ids_cur and not cur.get("relations"):
            findings.append({"lazy_path": "no_meaningful_change",
                             "beats": [prev.get("beat_id"), cur.get("beat_id")],
                             "detail": "identical elements, no relation"})
    return findings


# ------------------------------------------------------------------ A. padding
_PAYLOAD_KEYS = ("type", "role", "text", "content", "motif", "label", "value", "glyph")
_GEOMETRY_KEYS = ("box", "rect", "position", "x", "y", "anchor", "bounds")


def meaningless_elements(dsl, min_elems=3):
    """Elements that merely pad a count: no semantic payload and no geometry.

    This is the behaviour check behind "do these elements really participate in
    semantic expression / relation / visual encoding?" — not a bare count.
    """
    findings = []
    for b in dsl.get("beats", []):
        els = b.get("elements", [])
        if len(els) < min_elems:
            continue
        shells = []
        for e in els:
            has_payload = any(str(e.get(k, "")).strip() for k in _PAYLOAD_KEYS)
            has_geometry = any(k in e for k in _GEOMETRY_KEYS)
            if not has_payload and not has_geometry:
                shells.append(e.get("id"))
        if shells:
            findings.append({"lazy_path": "meaningless_elements", "beat": b.get("beat_id"),
                             "detail": "%d empty-shell elements: %s" % (len(shells), shells)})
    return findings


# ------------------------------------------------------------------ B. fake motion
def fake_motion(dsl, entrance, long_beat_sec=3.0, instant_sec=0.1):
    """Motion that cannot actually be observed: bad timing, or a long beat whose
    only motion is instantaneous.
    """
    findings = []
    beat_len = {}
    if dsl:
        for b in dsl.get("beats", []):
            beat_len[b.get("beat_id")] = max(b.get("end_sec", 0) - b.get("start_sec", 0), 0.0)
    for b in entrance.get("beats", []):
        bid = b.get("beat_id")
        blen = beat_len.get(bid)
        durations = []
        for eid, lc in (b.get("lifecycle") or {}).items():
            ent = (lc or {}).get("enter") or {}
            if not ent.get("motion"):
                continue
            t, d = ent.get("time"), ent.get("duration")
            if isinstance(t, (int, float)) and t < 0:
                findings.append({"lazy_path": "fake_motion", "beat": bid, "element": eid,
                                 "detail": "negative enter time %s" % t})
            if isinstance(d, (int, float)):
                if d <= 0:
                    findings.append({"lazy_path": "fake_motion", "beat": bid, "element": eid,
                                     "detail": "non-positive duration %s" % d})
                elif blen is not None and d > blen + 1e-6:
                    findings.append({"lazy_path": "fake_motion", "beat": bid, "element": eid,
                                     "detail": "duration %.2f exceeds beat %.2f" % (d, blen)})
                durations.append(d)
        if (blen is not None and blen >= long_beat_sec and durations
                and all(d < instant_sec for d in durations)):
            findings.append({"lazy_path": "fake_motion", "beat": bid,
                             "detail": "long beat %.1fs but all motions instantaneous" % blen})
    return findings


# ------------------------------------------------------------------ C. fake continuity
CARRY = ("inherit", "carry_over")


def fake_continuity(dsl, entrance, carry=CARRY):
    """Continuity claims that carry no real continuity."""
    findings = []
    beats = dsl.get("beats", [])
    ent_by = {b.get("beat_id"): (b.get("lifecycle") or {}) for b in entrance.get("beats", [])}
    for prev, cur in zip(beats, beats[1:]):
        prev_ids = {e.get("id") for e in prev.get("elements", [])}
        cur_ids = {e.get("id") for e in cur.get("elements", [])}
        lc = ent_by.get(cur.get("beat_id"), {})
        for eid in cur_ids:
            m = ((lc.get(eid) or {}).get("enter") or {}).get("motion")
            if m in carry and eid not in prev_ids:
                findings.append({"lazy_path": "fake_continuity", "beat": cur.get("beat_id"),
                                 "element": eid,
                                 "detail": "carry-over but element absent in previous beat"})
            elif eid in prev_ids and m and m not in carry:
                findings.append({"lazy_path": "fake_continuity", "beat": cur.get("beat_id"),
                                 "element": eid,
                                 "detail": "persisted element re-enters with %r" % m})
    return findings


# ------------------------------------------------------------------ D. pollution
_JUDGE_TOUCH = ("tests/golden", "tests/test_golden.py", "runtime/validator.py",
                "runtime/verification", "runtime/gate", "threshold", "oracle",
                "tools/verify_change.py")


def test_only_change(changed_paths):
    """A change that touches tests/tools but no runtime code is suspicious."""
    touch_tests = any(p.startswith("tests/") or p.startswith("tools/") for p in changed_paths)
    touch_impl = any(p.startswith("runtime/") for p in changed_paths)
    if touch_tests and not touch_impl:
        return [{"lazy_path": "test_only_change",
                 "detail": "tests/tools changed without runtime change"}]
    return []


def test_pollution(changed_paths):
    """Editing the judges/thresholds/oracle without touching real implementation.

    The fine-grained, behaviour-level companion to ``test_only_change``: it names
    the judge surfaces so a passing run cannot be manufactured by editing the
    thing that measures it.
    """
    if not changed_paths:
        return []
    impl = [p for p in changed_paths
            if p.startswith("runtime/") and not p.startswith("runtime/verification")
            and not any(t in p for t in _JUDGE_TOUCH)]
    judged = [p for p in changed_paths if any(t in p for t in _JUDGE_TOUCH)]
    if judged and not impl:
        return [{"lazy_path": "test_pollution",
                 "detail": "judge/test/threshold files changed without impl: %s" % judged}]
    return []


# ------------------------------------------------------------------ aggregate
def scan(dsl=None, entrance=None, changed_paths=None):
    findings = []
    if dsl is not None:
        findings += all_same_composition(dsl)
        findings += single_motif(dsl)
        findings += filler_decorations(dsl)
        findings += wall_of_text(dsl)
        findings += no_meaningful_change(dsl)
        findings += meaningless_elements(dsl)
    if entrance is not None:
        findings += all_fade(entrance)
        findings += fake_motion(dsl, entrance)
    if dsl is not None and entrance is not None:
        findings += fake_continuity(dsl, entrance)
    if changed_paths is not None:
        findings += test_only_change(changed_paths)
        findings += test_pollution(changed_paths)
    return findings


def all_fade(entrance, min_elems=4):
    motions = []
    for b in entrance.get("beats", []):
        for lc in b.get("lifecycle", {}).values():
            m = (lc.get("enter") or {}).get("motion")
            if m:
                motions.append(m)
    if len(motions) >= min_elems and set(motions) == {"fade"}:
        return [{"lazy_path": "all_fade",
                 "detail": "all %d entering elements fade" % len(motions)}]
    return []
