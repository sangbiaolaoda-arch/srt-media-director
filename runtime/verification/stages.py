"""Stage state machine + stage receipts.

Every task moves through a strict sequence and may not skip.  Each stage leaves a
receipt carrying WHAT / EVIDENCE / VERDICT / NEXT.  Missing required evidence
blocks advancement (verdict stays UNRESOLVED); it is never assumed.
"""
from dataclasses import dataclass, field, asdict

STAGE_ORDER = ["PLANNED", "GENERATED", "VERIFIED", "RENDERED", "EVALUATED",
               "ACCEPTED"]

# Evidence kinds that must be PRESENT (non-empty) before a stage may be recorded.
REQUIRED_EVIDENCE = {
    "PLANNED": ["task_contract"],
    "GENERATED": ["artifact_path"],
    "VERIFIED": ["validator_report"],
    "RENDERED": ["render_report"],
    "EVALUATED": ["evaluation"],
    "ACCEPTED": ["verdict"],
}


class MissingEvidence(Exception):
    """A stage was submitted without its required evidence."""


class StageOrderError(Exception):
    """A stage was submitted out of order."""


@dataclass
class Receipt:
    stage: str
    what: str
    evidence: dict
    verdict: str = "UNRESOLVED"        # only an independent judge may set PASS/FAIL
    next: str = "REPAIR"

    def to_dict(self):
        return asdict(self)


@dataclass
class StageMachine:
    receipts: list = field(default_factory=list)

    @property
    def current(self):
        return self.receipts[-1].stage if self.receipts else None

    def expected_next(self):
        if not self.receipts:
            return STAGE_ORDER[0]
        idx = STAGE_ORDER.index(self.current)
        return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None

    def submit(self, stage, what, evidence):
        """Record a stage only if it is next AND all required evidence is present.

        Raises StageOrderError / MissingEvidence; on success returns the receipt
        with verdict UNRESOLVED (a judge must promote it).
        """
        if stage != self.expected_next():
            raise StageOrderError("expected %s, got %s" % (self.expected_next(), stage))
        missing = [k for k in REQUIRED_EVIDENCE[stage] if not evidence.get(k)]
        if missing:
            raise MissingEvidence("stage %s missing evidence: %s" % (stage, missing))
        nxt = STAGE_ORDER[STAGE_ORDER.index(stage) + 1] if \
            STAGE_ORDER.index(stage) + 1 < len(STAGE_ORDER) else "DONE"
        r = Receipt(stage=stage, what=what, evidence=dict(evidence),
                    verdict="UNRESOLVED", next=nxt)
        self.receipts.append(r)
        return r

    def promote(self, stage, verdict, by):
        """Promote a recorded stage's verdict — judge-only AND privileged.

        A PASS/FAIL requires the signing authority (see ``authority``); without it
        promotion to PASS/FAIL raises Unauthorized, so an agent cannot promote its
        own stage.  UNRESOLVED needs no authority.
        """
        from .claims import JUDGE_ROLES, Unauthorized, _authority_ok
        if by not in JUDGE_ROLES:
            raise Unauthorized("only %s may set a verdict, not %r" % (JUDGE_ROLES, by))
        for r in self.receipts:
            if r.stage == stage:
                if verdict in ("PASS", "FAIL"):
                    ok, why = _authority_ok(by, r.evidence)
                    if not ok:
                        raise Unauthorized(why)
                r.verdict = verdict
                return r
        raise StageOrderError("stage %s not recorded" % stage)
