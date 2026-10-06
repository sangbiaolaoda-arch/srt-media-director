"""Signed, evidence-bound verdicts — the ONLY way a change is accepted.

A verdict is a plain dict::

    {subject, verdict, by, evidence[], evidence_digest, run_id, issued_at, signature}

  * evidence[] items: {"path": <real file>, "observed": <what it shows>}
  * evidence_digest: sha256 over the sorted (path, sha256-of-file) pairs
  * signature: HMAC (see authority) over the dict minus the signature field

``acceptance.evaluate(doc)`` is what consumers must call:

  1. re-hash every evidence path from disk — a missing/changed artifact makes the
     digest mismatch -> UNRESOLVED ("evidence vanished/changed");
  2. verify the HMAC — unsigned/forged -> UNRESOLVED;
  3. only then return the verdict.

Consequences (the machine teeth behind facts 1-3):
  * an agent cannot keep a stale PASS after deleting the artifacts it claimed;
  * an agent cannot mint a PASS without the signing authority;
  * signing authority lives outside the agent sandbox (SMD_JUDGE_KEY unset).
"""
import datetime
import hashlib
import os

from . import authority, claims


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def evidence_digest(evidence):
    items = []
    for e in evidence or []:
        p = (e or {}).get("path")
        items.append({"path": p, "sha256": _sha256_file(p) if p else None})
    items.sort(key=lambda x: (x["path"] or ""))
    digest = hashlib.sha256(authority.canonical(items).encode("utf-8")).hexdigest()
    return digest, items


def issue(subject, verdict, by, evidence, *, run_id=None):
    """Build a verdict dict.

    A PASS/FAIL requires BOTH an active judge session matching ``by`` AND signing
    authority; otherwise it is downgraded to UNRESOLVED. UNRESOLVED needs no key.
    """
    if verdict not in claims.VERDICT_VALUES:
        raise ValueError("verdict must be one of %s" % (claims.VERDICT_VALUES,))
    if by not in claims.JUDGE_ROLES:
        raise claims.Unauthorized("role %r may not issue a verdict" % by)

    digest, _ = evidence_digest(evidence)
    sess = authority.current_session()
    doc = {
        "subject": subject,
        "verdict": verdict,
        "by": by,
        "evidence": list(evidence or []),
        "evidence_digest": digest,
        "run_id": run_id or (sess.run_id if sess else "no-session"),
        "issued_at": _now_iso(),
        "signature": "",
    }
    if verdict in ("PASS", "FAIL"):
        signed = bool(sess) and sess.by == by and authority.signing_available()
        if not signed:
            doc["verdict"] = "UNRESOLVED"
            doc["reason"] = ("no signing authority: SMD_JUDGE_KEY absent or no judge "
                             "session; agent cannot promote its own work")
            return doc
        doc["signature"] = authority.sign({k: v for k, v in doc.items() if k != "signature"})
    return doc


def evaluate(doc):
    """Return (verdict, reasons). A forged/stale verdict is always UNRESOLVED."""
    if not isinstance(doc, dict):
        return "UNRESOLVED", ["verdict is not a dict"]
    v = doc.get("verdict", "UNRESOLVED")
    if v not in ("PASS", "FAIL"):
        return "UNRESOLVED", ["verdict is %s" % v]

    digest, _ = evidence_digest(doc.get("evidence", []))
    if digest != doc.get("evidence_digest"):
        return "UNRESOLVED", ["evidence binding broken (missing or changed artifact)"]

    payload = {k: val for k, val in doc.items() if k != "signature"}
    if not authority.verify_signature(payload, doc.get("signature", "")):
        return "UNRESOLVED", ["signature invalid (unsigned or forged verdict)"]

    return v, []
