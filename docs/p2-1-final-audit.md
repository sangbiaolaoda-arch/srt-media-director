# P2-1 Final Audit

> **Status (current): `P2-1 ACCEPTED`.** META-0 Judge Seal is complete and passing; the staleness in
> §6/§7 below is historical (captured before the operator re-seal). Process evidence §1–§5 is
> preserved unchanged — only the current Status/Verdict is updated.

Scope: verify `c511b4b` (P2-1 core) and correct its evidence; no new features, templates,
grammar operations, motifs, motion types, anti-cheat, validators, or test cases were added.
Files touched in this audit: `tools/compare_quality.py`, `runtime/visual_director.py` (dead-code
removal), `docs/p2-1-implementation.md`, and comparison artifacts.

## 1. Evidence correction — the mean-delta bug was real

`tools/compare_quality.py` computed `metric_deltas_mean` as `sum(case deltas) / len(deltas)` where
`deltas` only contained cases whose value **changed**. So every mean was divided by the number of
*changed* cases instead of all comparable cases. For `distinct_strategies`: 11 cases changed with a
summed delta of 16 → reported `16/11 = 1.4545`, but the true mean is `16/21 = 0.7619`.

Fix: the denominator is now the number of cases where the metric is present in **both** versions
(unchanged and non-comparable cases contribute 0). Comparison evidence regenerated from the fixed
tool. Corrected values:

| metric (mean over 21) | baseline | candidate | Δ (corrected) |
|---|---|---|---|
| `distinct_strategies` | 2.3333 | 3.0952 | **+0.7619** |
| `elements` | 28.6667 | 29.3333 | +0.6667 |
| `ink_mean` | 0.0603 | 0.0725 | +0.0121 |
| `colors_mean` | 47.8238 | 47.9286 | +0.1048 |
| `anti_ppt.template_repeat` | 0.5169 | 0.3770 | −0.1399 |
| `anti_ppt.encoding_repeat` | 0.5169 | 0.3770 | −0.1399 |
| `anti_ppt.text_ratio` | 0.4167 | 0.3726 | −0.0441 |

Case-level headline is unchanged: **improved 15 / regressed 0 / unchanged 6**.

## 2. Dead `ROTATION` — removed

`runtime/visual_director.py` defined a module-level `ROTATION` tuple that no longer participated in
`_direct_beat` after P2-1. Repository-wide search shows no remaining runtime/production reference
(only two historical comments describing it). It was deleted; **nothing replaces it**. The decision
path remains *grammar candidates → semantic validity → continuity → diversity tie-break*.

## 3. Honesty — L4 is not complete

Nine L4 dimensions (`semantic_expression`, `composition`, `hierarchy`, `motion`, `continuity`,
`visual_richness`, `repetition`, `ppt_feeling`, `overall`) remain **PENDING** in both reports and
were **not** auto-scored. `distinct_strategies` is an observation metric and is **not** used as a
proxy for visual quality. The implementation doc was corrected to state machine-level results only.

## 4. Minimal, real L4 Composition Review (semantic_expression / composition / ppt_feeling)

Reviewed the 21 before/after contact sheets (baseline renders vs candidate renders), with focus
sheets per category at `docs/real-srt-quality-eval/p2-1-comparison/focus/` (left column = baseline,
right column = candidate).

- **adversarial_repetition** (r01/r02/r03): baseline reused a shape-mark + badge rhythm across beats;
  candidate introduces genuinely different spatial relations (directional flow chains, clock→flag
  redirect, concentric target, filled-gauge metric). Improvement is spatial, not just a renamed
  strategy.
- **longform** (l01/l02/l03): baseline repeated hourglass / arrow rows; candidate adds calendar→clock
  progression, ring gauges, and two-card contrasts. More varied hierarchy placement.
- **narrative_emotion** (n01–n04): baseline leaned on repeated flag/hourglass/arrow/lightbulb rows;
  candidate adds radial 50% gauges with tick marks, balance-scale, two-card contrast (red-rose vs
  wall), and concentric-target→flag chains.

Observations held honestly:
- Composition richness does increase and different strategies do produce different spatial
  relations (not label-only changes).
- No case showed content clearly forced into an unusable layout for diversity; acceptable-candidate
  filtering (fit ≥ best − margin) keeps choices semantically reasonable.
- No obvious new PPT/card-stacking regression was observed; where cards appear they encode a real
  contrast relation.
- Hierarchy and cross-shot continuity remained readable in the reviewed sampling.
- **These are the auditor's qualitative notes on a sampled visual review, not scored L4 grades.**
  L4 scoring is still PENDING and is the operator/human-reviewer's call.

## 5. Verification results

| check | result |
|---|---|
| targeted pytest (`test_golden`, `test_grammar_owns_strategy`, `test_quality_metrics`, `test_anti_laziness`, `test_production_canonical_boundary`) | PASS (except the judge-seal guard, below) |
| full pytest (`tests/`) | **593 passed, 3 skipped, 3 failed** |
| 21-case Real SRT Production Path | **21/21 PASS** |
| `compare_quality` baseline vs candidate | improved 15 / regressed 0 / unchanged 6 |
| Judge Guard `verify()` | **ok=False** (see §6) |

The 3 failures are exclusively the judge-seal guard tests
(`test_anti_laziness.py::test_judge_guard_has_no_unsealed_changes`,
`test_judge_seal_attacks.py::test_manifest_exists_and_verifies_clean`,
`test_judge_seal_attacks.py::test_editing_a_judge_file_fails_the_guard`). They fail **because** judge
files were intentionally edited and have not been re-sealed — this is the guard working as designed,
not a code defect.

## 6. Sealed-judge-file accounting (before operator re-seal)

`judge_guard.verify()` currently reports:

```
changed: ["tests/golden/01-minimal/hashes.json", "tests/golden/02-numeric/hashes.json"]
added:   ["docs/real-content-eval.json"]
removed: []
```

| file | status | why it must change | is it only a legitimate oracle/contract update? | any weakened test / lowered threshold / deleted failing condition? |
|---|---|---|---|---|
| `tests/golden/01-minimal/hashes.json` | changed | The golden oracle hashes the 5 plan layers. P2-1 legitimately changes `visual-plan.json` / `visual-dsl.json` / `render-plan.json` content (per-beat `strategy` and the new `composition_decision`). | Yes — regenerated with `UPDATE_GOLDEN=1` from real pipeline output of the new behavior. | No. The golden test still enforces all 5 layers and volatile-key normalization; nothing was relaxed. |
| `tests/golden/02-numeric/hashes.json` | changed | Same reason (numeric fixture path). | Yes — same regeneration. | No. |
| `docs/real-content-eval.json` | added | **Not a P2-1 change.** This file has existed since commit `72da390` ("P0: Real Content Evaluation harness + dataset"); it only appears "added" because the local sparse checkout did not materialize `docs/`. | N/A — pre-existing. | No. On a full checkout it is already in the sealed manifest. |
| `tests/phase0/test_grammar_owns_strategy.py` | modified | Updated routing contract (director now calls `composition_candidates`) + added candidate-set/decision assertions. | Yes — contract update for the new behavior. | No. It **adds** assertions (candidates ≥ 2, ordering by fit, decision record, no ROTATION in the body); nothing was deleted or weakened. |

**Important precision:** `tests/phase0/test_grammar_owns_strategy.py` is **not currently covered by
`judge_guard.JUDGE_PATTERNS`**, so it does **not** appear in `verify()` output. It constrains the
director through the pytest suite but is outside the judge-seal manifest. (If it should be sealed,
that is an operator decision about `JUDGE_PATTERNS`, out of P2-1 scope.)

The golden updates come from the real, expected P2-1 behavior change, **not** from regeneration to
hide a regression: the same code produces 21/21 Production Path PASS and 0 machine-level
regressions.

Re-seal (operator only):

```bash
SMD_JUDGE_KEY=<secret> python -c "from runtime.verification import judge_guard; judge_guard.write_manifest(by='p2-1-operator')"
```

The key is not present in this sandbox (by M2 design); the agent did **not** fabricate or brute-force
it to bypass the boundary.

## 7. Status

```
evidence numbers correct ....... YES (compare_quality fixed; means corrected to +0.7619 etc.)
dead ROTATION cleaned ......... YES
21-case Production Path PASS ... YES (21/21)
no machine-level regression .... YES (0 regressed; per-case scan none)
L4 composition/semantic/ppt
  review ..................... DONE at minimal qualitative level; L4 scores remain PENDING
Judge Seal PASS ................ YES — re-sealed by operator (META-0 complete)
```

**Verdict: `P2-1 ACCEPTED`.** P2-1 core is preserved and verified at the machine level, and the two
golden oracles were re-sealed by the operator after META-0 completed. `judge_guard.verify()` now
reports a clean seal, and the judge-portability CI job passes on Linux/macOS/Windows. The historical
process evidence above (§1–§6) is preserved unchanged; only the current Status/Verdict is updated.
The prior `ENGINEERING BLOCKED ON JUDGE RE-SEAL` verdict is superseded. P2-2 (Execution Layer) is now
unblocked.
