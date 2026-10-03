"""Stage 7 — Validation: schema layer + L1 machine facts + L3 raster probe.

L2 layout gates run earlier, inside composition_planner (fail-fast).
L4 semantic / visual review is human-or-agent work and is NOT faked here —
the report carries an explicit `l4: PENDING` slot instead of a rubber stamp.
"""
import os

import jsonschema

import raster_renderer
from common import dump_json, ensure_dir, load_json

SCHEMA_FILES = {
    "srt-analysis.json": "srt-analysis.schema.json",
    "beat-plan.json": "beat-plan.schema.json",
    "visual-plan.json": "visual-plan.schema.json",
    "visual-dsl.json": "visual-dsl.schema.json",
    "render-plan.json": "render-plan.schema.json",
    "entrance-plan.json": "entrance-plan.schema.json",
}

STRATEGIES = {"single_focus", "left_to_right_flow", "cause_effect",
              "comparison", "center_cluster", "before_after"}
ROLES = {"primary", "secondary", "support", "ambient"}
ETYPES = {"text", "shape", "motif", "chart", "connector", "decor"}


def _schema_layer(project_root, work_dir, issues):
    docs = {}
    for fname, sname in SCHEMA_FILES.items():
        path = os.path.join(work_dir, fname)
        if not os.path.exists(path):
            issues.append({"layer": "schema", "code": "ARTIFACT_MISSING", "msg": fname})
            continue
        doc = load_json(path)
        docs[fname] = doc
        schema = load_json(os.path.join(project_root, "schemas", sname))
        for e in jsonschema.Draft7Validator(schema).iter_errors(doc):
            issues.append({"layer": "schema", "code": "SCHEMA",
                           "msg": "%s: %s" % (fname, e.message[:140])})
    return docs


def _l1(docs, issues):
    def err(code, msg):
        issues.append({"layer": "L1", "code": code, "msg": msg})

    need = ("srt-analysis.json", "beat-plan.json", "visual-plan.json",
            "visual-dsl.json", "render-plan.json", "entrance-plan.json")
    if any(n not in docs for n in need):
        return

    cues = docs["srt-analysis.json"]["cues"]
    beats = docs["beat-plan.json"]["beats"]
    dsl = docs["visual-dsl.json"]
    render = docs["render-plan.json"]
    entrance = docs["entrance-plan.json"]
    vplan = docs["visual-plan.json"]

    covered = []
    for b in beats:
        covered.extend(range(b["cue_range"][0], b["cue_range"][1] + 1))
    if covered != list(range(1, len(cues) + 1)):
        err("BEAT_COVERAGE", "cue coverage %s != 1..%d" % (covered[:12], len(cues)))

    ids = [b["beat_id"] for b in dsl["beats"]]
    if [b["beat_id"] for b in beats] != ids or \
       [b["beat_id"] for b in render["beats"]] != ids or \
       [b["beat_id"] for b in entrance["beats"]] != ids or \
       [b["beat_id"] for b in vplan["beats"]] != ids:
        err("BEAT_ID_MISMATCH", "beat ids differ across layers")

    for b in dsl["beats"]:
        if b["end_sec"] <= b["start_sec"]:
            err("TIME_INVERTED", b["beat_id"])
        if b["strategy"] not in STRATEGIES:
            err("STRATEGY_UNKNOWN", "%s: %s" % (b["beat_id"], b["strategy"]))
        prim = [e for e in b["elements"] if e["role"] == "primary"]
        if len(prim) != 1:
            err("PRIMARY_COUNT", "%s: %d" % (b["beat_id"], len(prim)))
        elids = {e["id"] for e in b["elements"]}
        for e in b["elements"]:
            if e["role"] not in ROLES:
                err("ROLE_UNKNOWN", "%s/%s" % (b["beat_id"], e["id"]))
            if e["type"] not in ETYPES:
                err("ETYPE_UNKNOWN", "%s/%s" % (b["beat_id"], e["id"]))
            if e.get("host") and e["host"] not in elids:
                err("HOST_MISSING", "%s/%s -> %s" % (b["beat_id"], e["id"], e["host"]))
        for r in b["relations"]:
            if r["from"] not in elids or r["to"] not in elids:
                err("RELATION_DANGLING", "%s: %s" % (b["beat_id"], r))

    rboxes = {b["beat_id"]: b["boxes"] for b in render["beats"]}
    for b in dsl["beats"]:
        elids = {e["id"] for e in b["elements"]}
        if set(rboxes[b["beat_id"]].keys()) != elids:
            err("RENDER_BOX_MISMATCH", b["beat_id"])
    for b in entrance["beats"]:
        elids = {e["id"] for e in dsl["beats"][ids.index(b["beat_id"])]["elements"]}
        for c in b["cues"]:
            for eid in c["elements"]:
                if eid not in elids:
                    err("CUE_ELEMENT_MISSING", "%s: %s" % (b["beat_id"], eid))
        # lifecycle 覆盖：每个元素都必须有入场规划（用户导演指令的机器护栏）
        life = b.get("lifecycle", {})
        missing = sorted(elids - set(life.keys()))
        if missing:
            err("LIFECYCLE_MISSING", "%s: %s" % (b["beat_id"], missing[:6]))
        for eid, lc in life.items():
            en = lc.get("enter")
            if not isinstance(en, dict) or "at" not in en or "motion" not in en:
                err("LIFECYCLE_ENTER", "%s: %s" % (b["beat_id"], eid))
                continue
            x = lc.get("exit")
            if x and x.get("at", 0) <= en.get("at", 0):
                err("LIFECYCLE_EXIT_ORDER", "%s: %s" % (b["beat_id"], eid))

    for b in vplan["beats"]:
        if not b.get("visual_claim"):
            err("CLAIM_MISSING", b["beat_id"])
        if not b.get("evidence"):
            err("EVIDENCE_MISSING", b["beat_id"])


def _l3(docs, preview_dir, issues):
    def err(code, msg):
        issues.append({"layer": "L3", "code": code, "msg": msg})

    report = raster_renderer.render_previews(
        docs["visual-dsl.json"], docs["render-plan.json"], docs["entrance-plan.json"],
        preview_dir)
    for bid, r in report.items():
        if not (0.005 <= r["ink_ratio"] <= 0.65):
            err("FRAME_INK_RATIO", "%s: %.4f" % (bid, r["ink_ratio"]))
        if r["distinct_colors"] < 12:
            err("FRAME_TOO_SIMPLE", "%s: %d colors" % (bid, r["distinct_colors"]))
    return report


def validate(project_root, work_dir, preview_dir, render=True):
    """Run schema + L1 (+ L3) and write validation-report.json. Returns it."""
    issues = []
    docs = _schema_layer(project_root, work_dir, issues)
    _l1(docs, issues)
    raster = None
    if render and not any(i["code"] == "ARTIFACT_MISSING" for i in issues):
        raster = _l3(docs, preview_dir, issues)

    status = "PASS" if not issues else "FAIL"
    report = {
        "status": status,
        "layers": {
            "schema": "PASS" if not [i for i in issues if i["layer"] == "schema"] else "FAIL",
            "l1": "PASS" if not [i for i in issues if i["layer"] == "L1"] else "FAIL",
            "l2": "see work/layout-audit.json (runs fail-fast inside composition_planner)",
            "l3": ("PASS" if not [i for i in issues if i["layer"] == "L3"] else "FAIL")
                  if render else "SKIPPED",
            "l4": "PENDING — semantic/visual review must be done by agent or human",
        },
        "issues": issues,
        "raster": raster,
    }
    ensure_dir(work_dir)
    dump_json(report, os.path.join(work_dir, "validation-report.json"))
    return report
