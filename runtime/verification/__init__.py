"""Anti-laziness verification framework for SRT Media Director.

Enforces one rule: an agent may not disguise "not done" as "done".

  - stages.py      PLANNED -> GENERATED -> VERIFIED -> RENDERED -> EVALUATED -> ACCEPTED
  - claims.py      agent may only emit proposal/artifact/agent_claim; verdicts come
                   from an independent judge (validator/observer/evaluator/gate)
  - authority.py   the signing boundary: PASS/FAIL needs SMD_JUDGE_KEY, which the
                   agent sandbox does NOT hold -> an agent cannot sign a promotion
  - acceptance.py  signed + evidence-bound verdicts; deleting/forging evidence or
                   the signature downgrades to UNRESOLVED
  - judge_guard.py a sealed manifest of judge files; changing a judge fails the
                   guard until deliberately re-sealed (logged in reseal_log.json)
  - defaults.py    missing info is UNRESOLVED (never silently defaulted); explicit
                   defaults must leave a DEFAULT_APPLIED + reason ledger entry
  - adversarial.py detectors for the cheapest lazy paths, checking *behaviour*
                   (real semantic participation / motion / continuity), not field
                   presence (all-same-composition, all-fade, one motif, filler,
                   wall-of-text, no-change, meaningless-elements, fake-motion,
                   fake-continuity, test-only / test-pollution)
  - threelayer.py  the single acceptance chain: targeted -> full pytest -> real SRT
                   -> render -> adversarial -> judge_guard -> evaluation
"""
from . import (acceptance, adversarial, authority, claims, defaults, judge_guard,  # noqa: F401
               stages, threelayer)

__all__ = ["claims", "stages", "defaults", "adversarial", "judge_guard",
           "authority", "acceptance", "threelayer"]
