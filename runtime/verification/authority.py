"""Judge signing authority — the trust boundary between agent and verdict.

In one OS process with arbitrary code execution, no in-process check is
un-defeatable.  What we CAN do is make a *PASS verdict unusable unless it is
signed by an authority the agent does not possess*.

The signing key is read ONLY from the environment variable ``SMD_JUDGE_KEY`` and
is never stored in the repo.  The agent's sandbox does not set it, therefore:

  - the agent can still construct a JudgeVerdict object, but
  - any PASS/FAIL it mints carries no valid signature, and
  - ``acceptance.evaluate()`` downgrades unsigned/tampered verdicts to UNRESOLVED.

A trusted operator / CI runs
``SMD_JUDGE_KEY=<secret> python tools/verify_change.py``
to produce a verifiable verdict.

Residual risk (honest, not disguised): an agent that can READ the key (e.g. it
is exported into the same environment the agent already runs in) or that can
patch these modules AND re-seal the manifest could still forge.  True isolation
requires OS-level process / credential separation (a separate verifier host).
We do not claim otherwise — see ``judge_guard.audit()``.
"""
import hashlib
import hmac
import json
import os
import uuid

from . import claims

KEY_ENV = "SMD_JUDGE_KEY"


def _key():
    raw = os.environ.get(KEY_ENV)
    if not raw:
        return None
    return hashlib.sha256(raw.encode("utf-8")).digest()


def signing_available():
    return _key() is not None


def key_fingerprint():
    k = _key()
    return None if k is None else hashlib.sha256(k).hexdigest()[:16]


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class JudgeSession:
    """Only the judge execution path should enter here.

    Opening a session does not require the key; *signing* a PASS/FAIL does. That
    split is deliberate: an agent can open a session, but without SMD_JUDGE_KEY
    it still cannot sign a promotable verdict.
    """

    _current = None

    def __init__(self, by, run_id=None):
        if by not in claims.JUDGE_ROLES:
            raise claims.Unauthorized(
                "role %r cannot open a judge session (judges: %s)" % (by, claims.JUDGE_ROLES))
        self.by = by
        self.run_id = run_id or uuid.uuid4().hex
        self.signed = signing_available()

    def __enter__(self):
        JudgeSession._current = self
        return self

    def __exit__(self, *exc):
        JudgeSession._current = None
        return False


def current_session():
    return JudgeSession._current


def sign(payload):
    k = _key()
    if k is None:
        raise claims.Unauthorized("no %s in environment; cannot sign a verdict" % KEY_ENV)
    return hmac.new(k, canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(payload, signature):
    k = _key()
    if k is None or not signature:
        return False
    try:
        expected = hmac.new(k, canonical(payload).encode("utf-8"),
                            hashlib.sha256).hexdigest()
    except Exception:  # noqa: BLE001
        return False
    return hmac.compare_digest(expected, signature)
