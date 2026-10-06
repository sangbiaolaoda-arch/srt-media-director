"""Agent-claim vs judge-verdict separation.

An agent may emit a proposal / artifact / agent_claim.  It may NOT self-declare a
verdict (verified / approved / PASS / accepted / done).  Verdicts are issued only
by an independent judge role.
"""
from dataclasses import dataclass, field

AGENT_KINDS = ("proposal", "artifact", "agent_claim")
JUDGE_ROLES = ("validator", "observer", "evaluator", "gate")
VERDICT_VALUES = ("PASS", "FAIL", "UNRESOLVED")

# Status words an agent must never use to certify its own output.
FORBIDDEN_SELF_STATUS = {"verified", "approved", "pass", "accepted", "done",
                         "complete", "completed", "success", "succeeded"}
_STATUS_KEYS = {"verdict", "status", "result", "outcome", "state", "decision"}


class AgentSelfCertification(Exception):
    """Agent tried to declare its own output verified / approved / PASS."""


class Unauthorized(Exception):
    """A non-judge role tried to issue a verdict."""


def _walk(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + (str(k),), v
            yield from _walk(v, path + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield path + ("[%d]" % i,), v
            yield from _walk(v, path + ("[%d]" % i,))


@dataclass
class AgentOutput:
    kind: str
    summary: str
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in AGENT_KINDS:
            raise ValueError("agent kind must be one of %s" % (AGENT_KINDS,))
        self._reject_self_certification()

    def _reject_self_certification(self):
        for path, value in _walk(self.data):
            key = path[-1].lower()
            if key in _STATUS_KEYS and isinstance(value, str) and \
                    value.strip().lower() in FORBIDDEN_SELF_STATUS:
                raise AgentSelfCertification(
                    "agent output %s self-declares %r at %s" % (self.kind, value, "/".join(path)))
            if key in ("verified", "approved") and value is True:
                raise AgentSelfCertification(
                    "agent output flags itself %r at %s" % (key, "/".join(path)))

    def to_dict(self):
        return {"kind": self.kind, "summary": self.summary, "data": self.data}


@dataclass
class JudgeVerdict:
    subject: str
    verdict: str
    by: str
    evidence: list = field(default_factory=list)

    def __post_init__(self):
        if self.by not in JUDGE_ROLES:
            raise Unauthorized("role %r may not issue a verdict (judges: %s)" % (self.by, JUDGE_ROLES))
        if self.verdict not in VERDICT_VALUES:
            raise ValueError("verdict must be one of %s" % (VERDICT_VALUES,))
        if self.verdict in ("PASS", "FAIL") and not self.evidence:
            raise ValueError("a %s verdict requires evidence pointers" % self.verdict)

    def to_dict(self):
        return {"subject": self.subject, "verdict": self.verdict,
                "by": self.by, "evidence": self.evidence}


def issue_verdict(subject, verdict, by, evidence):
    """The ONLY sanctioned way to produce a verdict (parks it as a JudgeVerdict)."""
    return JudgeVerdict(subject=subject, verdict=verdict, by=by, evidence=list(evidence))
