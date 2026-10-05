"""Anchor provenance & lifecycle — Final Engineering Directive v5 §8-13.

An anchor is the human-adjudicated ground truth the whole pipeline derives from.
A provenance *declaration* ("we did dual annotation, agreement=true") is NOT
evidence. Evidence requires that the two annotations be **independently
reproducible and mutually invisible**, and that agreement be computed, not
asserted.

This module provides:
  * two independent annotators (A: connective-split, B: ontology-scan) that read
    only the source and cannot see each other;
  * computable agreement + adjudication (agree -> LOCKED, disagree -> AMBIGUOUS);
  * a lifecycle: LOCKED / CHALLENGED / SUPERSEDED;
  * versioned supersession that never mutates the prior anchor in place (§13).

The annotators are deliberately *different implementations* (different code and
lookup tables) so their agreement is informative.
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional

# --- lifecycle states (§11) -------------------------------------------------
LOCKED = "LOCKED"
CHALLENGED = "CHALLENGED"
SUPERSEDED = "SUPERSEDED"

# Triggers that force a LOCKED anchor into CHALLENGED (§12).
CHALLENGE_TRIGGERS = (
    "annotation_disagreement",
    "source_span_mismatch",
    "semantic_inversion",
    "new_evidence",
    "human_adjudication_correction",
)

_PREDICATE_TO_CONTRACT = {
    "CAUSES": "causes.v1",
    "FOLLOWS": "follows.v1",
    "CONNECTS": "connects.v1",
}


def contract_for(predicate: str) -> str:
    try:
        return _PREDICATE_TO_CONTRACT[predicate.upper()]
    except KeyError:
        raise ValueError("no entailment contract for predicate %r" % (predicate,))


# --- Annotator A: split on the causal connective ----------------------------
_A_CONNECTIVES = (("导致", "CAUSES"), ("随后", "FOLLOWS"), ("连线", "CONNECTS"))
_A_LEXICON = {
    "压力增加": "pressure",
    "系统失稳": "stability_failure",
    "警报响起": "alarm",
    "人群撤离": "evacuation",
    "传感器": "sensor",
    "指挥中枢": "command_hub",
}


def annotate_a(source: Dict[str, Any]) -> Dict[str, Any]:
    """Annotator A — causal-connective split, lexicon keyed by the full span."""
    text = source["srt"].rstrip("。.")
    mark, predicate = None, None
    for m, p in _A_CONNECTIVES:
        if m in text:
            mark, predicate = m, p
            break
    if mark is None:
        raise ValueError("annotator A: no connective in %r" % text)
    left, right = text.split(mark, 1)
    left = left.strip().rstrip("，,")
    right = right.strip().rstrip("，,")
    subj = _A_LEXICON.get(left)
    obj = _A_LEXICON.get(right)
    if subj is None or obj is None:
        raise ValueError("annotator A: unmapped span %r/%r" % (left, right))
    return {
        "annotator": "A",
        "method": "causal_connective_split",
        "sees_only": "source.json",
        "case_id": source["case_id"],
        "claim": {"subject": subj, "predicate": predicate, "object": obj},
    }


# --- Annotator B: ontology term scan (different code + table) ----------------
_B_TERMS = (
    ("压力", "pressure"),
    ("失稳", "stability_failure"),
    ("警报", "alarm"),
    ("撤离", "evacuation"),
    ("传感器", "sensor"),
    ("指挥中枢", "command_hub"),
)
_B_MARKERS = (("导致", "CAUSES"), ("随后", "FOLLOWS"), ("连线", "CONNECTS"))


def annotate_b(source: Dict[str, Any]) -> Dict[str, Any]:
    """Annotator B — ontology term scan, first/last term become subject/object."""
    text = source["srt"]
    hits = sorted((text.index(t), cid) for t, cid in _B_TERMS if t in text)
    predicate = None
    for m, p in _B_MARKERS:
        if m in text:
            predicate = p
            break
    if len(hits) < 2 or predicate is None:
        raise ValueError("annotator B: insufficient terms in %r" % text)
    return {
        "annotator": "B",
        "method": "ontology_term_scan",
        "sees_only": "source.json",
        "case_id": source["case_id"],
        "claim": {"subject": hits[0][1], "predicate": predicate, "object": hits[-1][1]},
    }


# --- agreement + adjudication (§9) ------------------------------------------
def claim_key(ann: Dict[str, Any]) -> tuple:
    c = ann["claim"]
    return (c["subject"], c["predicate"], c["object"])


def agrees(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return claim_key(a) == claim_key(b)


def adjudicate(a: Dict[str, Any], b: Dict[str, Any], *,
               adjudicator: str = "phase0-adjudicator",
               source_span: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if a["case_id"] != b["case_id"]:
        raise ValueError("annotations are for different cases")
    agree = agrees(a, b)
    out: Dict[str, Any] = {
        "case_id": a["case_id"],
        "adjudicator": adjudicator,
        "method": "independent_dual_annotation",
        "annotation_a": {"annotator": a["annotator"], "method": a["method"], "claim": a["claim"]},
        "annotation_b": {"annotator": b["annotator"], "method": b["method"], "claim": b["claim"]},
        "agree": agree,
        "outcome": LOCKED if agree else "AMBIGUOUS",
        "source_span": source_span,
    }
    if not agree:
        out["disagreement"] = {"a": claim_key(a), "b": claim_key(b)}
    return out


def final_anchor(source: Dict[str, Any], adj: Dict[str, Any], *,
                 anchor_version: str = "1.0") -> Dict[str, Any]:
    """Lock the anchor only when the independent annotations agreed (§13)."""
    if adj["outcome"] != LOCKED:
        raise ValueError("cannot lock an anchor while annotations disagree")
    c = adj["annotation_a"]["claim"]  # a == b at this point
    return {
        "case_id": source["case_id"],
        "anchor_version": anchor_version,
        "locked": True,
        "provenance": {
            "annotation_a": adj["annotation_a"],
            "annotation_b": adj["annotation_b"],
            "adjudication": {
                "method": adj["method"],
                "adjudicator": adj["adjudicator"],
                "agree": True,
            },
        },
        "claims": [{
            "id": "c1",
            "subject": c["subject"],
            "predicate": c["predicate"],
            "object": c["object"],
            "contract": contract_for(c["predicate"]),
        }],
    }


# --- lifecycle (§11-§13) ----------------------------------------------------
def state(anchor: Dict[str, Any]) -> str:
    lc = anchor.get("lifecycle") or {}
    if lc.get("state") in (CHALLENGED, SUPERSEDED):
        return lc["state"]
    return LOCKED if anchor.get("locked") else CHALLENGED


def is_locked(anchor: Dict[str, Any]) -> bool:
    return state(anchor) == LOCKED


def challenge(anchor: Dict[str, Any], *, trigger: str, evidence: str, by: str,
              ) -> Dict[str, Any]:
    """Move a LOCKED anchor to CHALLENGED (§12). Never mutates the input."""
    if trigger not in CHALLENGE_TRIGGERS:
        raise ValueError("unknown challenge trigger: %r" % (trigger,))
    out = copy.deepcopy(anchor)
    out["locked"] = False
    out["lifecycle"] = {
        "state": CHALLENGED,
        "trigger": trigger,
        "evidence": evidence,
        "challenged_by": by,
        "previous_version": anchor.get("anchor_version"),
    }
    return out


def supersede(previous: Dict[str, Any], *, new_version: str, reason: str,
              evidence: str, adjudicator: str,
              new_claims: Optional[List[Dict[str, Any]]] = None,
              ) -> Dict[str, Any]:
    """Produce a NEW anchor version; record why/who/previous (§13).

    Returns the new anchor. The caller should persist it as a new version file
    (e.g. anchor-v2.json); the previous anchor is not modified in place.
    """
    out = copy.deepcopy(previous)
    out["anchor_version"] = new_version
    out["locked"] = True
    if new_claims is not None:
        out["claims"] = copy.deepcopy(new_claims)
    out["lifecycle"] = {
        "state": LOCKED,
        "supersedes": previous.get("anchor_version"),
        "reason": reason,
        "evidence": evidence,
        "adjudicator": adjudicator,
    }
    return out


def mark_superseded(previous: Dict[str, Any], *, reason: str, evidence: str,
                    adjudicator: str, superseded_by: str) -> Dict[str, Any]:
    out = copy.deepcopy(previous)
    out["locked"] = False
    out["lifecycle"] = {
        "state": SUPERSEDED,
        "reason": reason,
        "evidence": evidence,
        "adjudicator": adjudicator,
        "superseded_by": superseded_by,
    }
    return out
