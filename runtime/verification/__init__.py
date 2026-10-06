"""Anti-laziness verification framework for SRT Media Director.

Enforces one rule: an agent may not disguise "not done" as "done".

  - stages.py      PLANNED -> GENERATED -> VERIFIED -> RENDERED -> EVALUATED -> ACCEPTED
  - claims.py      agent may only emit proposal/artifact/agent_claim; verdicts come
                   from an independent judge (validator/observer/evaluator/gate)
  - judge_guard.py a sealed manifest of judge files; a change that touches a judge
                   fails the guard until deliberately re-sealed
  - defaults.py    missing info is UNRESOLVED (never silently defaulted); explicit
                   defaults must leave a DEFAULT_APPLIED + reason ledger entry
  - adversarial.py detectors for the cheapest lazy paths (all-same-composition,
                   all-fade, one motif, filler, wall-of-text, no-change, test-only)
  - threelayer.py  targeted tests -> full pytest -> real SRT -> render check
"""
from . import claims, stages, defaults, adversarial, judge_guard  # noqa: F401

__all__ = ["claims", "stages", "defaults", "adversarial", "judge_guard"]
