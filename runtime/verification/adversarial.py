"""Adversarial detectors — the cheapest lazy paths must be catchable.

Each detector returns a list of findings (empty = clean).  A non-empty result is
a signal to FAIL/Repair, not to be ignored.  Thresholds are deliberately
conservative so genuine content is not over-flagged.
"""
from . import defaults


def all_same_composition(dsl, min_beats=4):
    beats = dsl.get("beats", [])
    if len(beats) < min_beats:
        return []
    strats = {b.get("strategy") for b in beats}
    if len(strats) == 1:
        return [{"lazy_path": "all_same_composition",
                 "detail": "%d beats all use %r" % (len(beats), next(iter(strats)))}]
    return []


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


def test_only_change(changed_paths):
    """A change that touches tests/tools but no runtime code is suspicious."""
    touch_tests = any(p.startswith("tests/") or p.startswith("tools/") for p in changed_paths)
    touch_impl = any(p.startswith("runtime/") for p in changed_paths)
    if touch_tests and not touch_impl:
        return [{"lazy_path": "test_only_change",
                 "detail": "tests/tools changed without runtime change"}]
    return []


def scan(dsl=None, entrance=None, changed_paths=None):
    findings = []
    if dsl is not None:
        findings += all_same_composition(dsl)
        findings += single_motif(dsl)
        findings += filler_decorations(dsl)
        findings += wall_of_text(dsl)
        findings += no_meaningful_change(dsl)
    if entrance is not None:
        findings += all_fade(entrance)
    if changed_paths is not None:
        findings += test_only_change(changed_paths)
    return findings
