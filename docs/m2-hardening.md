# M2 Hardening — turning the anti-laziness library into a real acceptance system

> This stage adds **no new visual/feature surface**. It hardens the existing
> `runtime/verification/*` machinery so that "being lazy" is the *hardest* path
> and "doing the work" is the *easiest* path to PASS. `UNRESOLVED` is the correct
> resting state, not a failure.

Truth model: an agent may submit **proposals / artifacts / evidence**; only an
independent, **cryptographically-signed** judge may issue **PASS / FAIL**.

## P0-1 — Verdict authority is really isolated

Before: `claims.issue_verdict(..., by="validator")` only checked a *string*, so any
caller (including an agent) could mint `JudgeVerdict("PASS")`.

Now:
- `runtime/verification/authority.py` — a signing authority whose key is read only
  from the environment (`SMD_JUDGE_KEY`). The agent sandbox does **not** hold it.
- `runtime/verification/acceptance.py` — signed, evidence-bound verdicts. `evaluate()`
  re-hashes every evidence file from disk and verifies the HMAC.
- `claims.JudgeVerdict` / `claims.issue_verdict` — a `PASS/FAIL` requires an active
  `JudgeSession(by=...)` **and** signing authority; otherwise `Unauthorized`.
- `stages.StageMachine.promote` — same rule (judge role **and** authority).

Consequence (facts 1 & 2): an agent can *call* the judge API, but without the key it
**cannot** promote its own work — the verdict stays `UNRESOLVED`.

**Residual risk (not disguised):** in one process with arbitrary code execution and
the key present, an agent could still forge. True isolation needs a separate
verifier process/host that holds the key. See `judge_guard.audit()`.

## P0-2 — One acceptance entrypoint, one data model

`verification/threelayer.LAYERS` is now the **single** chain, and `tools/verify_change.py`
records into exactly it:

```
targeted      did the edit break its own module?
full_pytest   did it break the rest of the system?
real_srt      does real input still generate deterministically?
render        did an actual render happen (not just JSON)?
adversarial   did the agent take a cheap lazy path?
judge_guard   was the judge system modified?
evaluation    is the new version BETTER?  (human/agent; never auto-passed)
```

This removes the old mismatch where the runner did 7 checks but the ledger modelled 3.
A layer counts only if its evidence pointer is a **real file on disk** (delete it and
the layer is missing again). Any missing layer → `UNRESOLVED`; no layer can be skipped.

## P0-3 — Real SRT *quality* evaluation (not just regression)

`legacy == canonical` only proves "we did not break it". Quality needs its own record.

- `tools/build_real_corpus.py` → `tests/corpus/real-content/` (**21 realistic SRTs**,
  6 categories: explanation / narrative_emotion / data_comparison /
  abstract_philosophy / longform / adversarial_repetition).
- `schemas/quality-eval-report.schema.json` + `tools/real_srt_quality_eval.py` → runs the
  full production path per case and writes render + contact sheet + machine metrics +
  a 9-dimension record (`semantic_expression, composition, hierarchy, motion,
  continuity, visual_richness, repetition, ppt_feeling, overall`) whose scores **all
  start PENDING**. No automatic aesthetic model is wired to fill L4.

**What real content immediately found:** case `d01-gdp` fails the production path with
`LayoutIntentIncomplete: text '×0.308824' (230x44) does not fit region delta` — a
genuine `composition_planner` bug (an unbounded `×<ratio>` annotation overflows its
region). This is exactly the gap regression tests cannot see.

## P0-4 — Adversarial detectors check *behaviour*, not field presence

Preserved: `all_same_composition`, `all_fade`, `single_motif`, `filler_decorations`,
`wall_of_text`, `no_meaningful_change`, `test_only_change`.

Added (behaviour-level):
- **A. `meaningless_elements`** — empty-shell elements with no semantic payload and no
  geometry (the real check behind "do these elements participate in expression?").
- **B. `fake_motion`** — illegal time/duration, or a long beat whose only motion is
  instantaneous (not just `motion != null`).
- **C. `fake_continuity`** — carry-over with no real identity continuity, or a
  persisted element that re-enters for no reason.
- **D. `test_pollution`** — judge/threshold/golden/validator edits with no impl change.

## P1 — Judge seal attack-surface audit

`judge_guard` now: seals matching files, **requires the signing authority to re-seal**,
logs every re-seal to `reseal_log.json` (who / when / key id / count), and `audit()`
answers the six attack questions. Machine-detectable: editing a judge file FAILs; a
new judge-named file shows as `added` → FAIL; an agent without the key cannot re-seal.

**Residual gaps (explicitly not claimed as covered):** moving judge logic to a
non-judge-named file, or swapping an import path, is *not* machine-detected — flagged
for human review in `audit()`.

## P1 — Evidence is bound to real files

Verdicts carry each artifact's path **and** sha256 digest. Deleting or changing an
artifact breaks the digest → the verdict no longer verifies (`acceptance.evaluate` →
`UNRESOLVED`). Real evidence now means: concrete file, concrete command, concrete
output, and a hash binding (fact 3).

## Facts now provable

1. Agent cannot self-declare PASS/verified/approved — `AgentSelfCertification`.
2. Agent cannot impersonate a judge for a verdict — needs `SMD_JUDGE_KEY`.
3. Delete/forge evidence → verdict invalid → `UNRESOLVED`.
4. Edit judge/evaluator/threshold/golden → `Judge Guard` FAIL, not auto-recoverable
   without the signing key.
5. Skip any of the seven layers → no PASS.
6. Cheapest lazy paths are machine-caught (behaviour-level detectors).
7. Real-SRT evaluation separates "code not broken" from "film got better".

## Honest boundaries

- No OS-level isolation in-process; an agent with the key or a separate verifier can
  forge. Documented, not hidden.
- L4 human review stays PENDING by policy VAL-01.
- Corpus is repo-authored content (21 cases); user-supplied material can extend it.
