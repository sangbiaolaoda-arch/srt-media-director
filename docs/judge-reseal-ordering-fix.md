# Judge re-seal ordering fix (self-referential hash)

Scope: `runtime/verification/judge_guard.py` and `tests/phase0/test_judge_seal_attacks.py` only.
No production code, Motion, Renderer, Primitive, Anti-PPT, or quality metric was touched.

## The bug

`write_manifest()` sealed first and appended the reseal log afterwards:

```
data = seal()                 # hashes judge_files() NOW
write judge_manifest.json     # commits those hashes
append entry to reseal_log.json   # <-- the log changes AFTER it was sealed
```

If `reseal_log.json` is a sealed file, then the act of appending the reseal entry changes
its hash *after* the manifest already recorded the pre-write hash. The very next
`verify()` therefore reports the log as `changed` and returns `ok=false` — a re-seal that
"went through" still fails verification, and the guard can never reach a clean state.

### Ground truth at the base commit

At `a87e77c`, `JUDGE_PATTERNS` listed only `runtime/verification/**/*.py` — it did **not**
include `**/*.json`. So `reseal_log.json` was not actually in the sealed set, and the
symptom was **latent**, not yet observable. The existing `test_reseal_is_logged_when_authorized`
also masked it because it pointed `RESEAL_LOG` at a repo-external `tmp_path/log.json`, which
is never part of `judge_files()`.

We therefore fix the underlying flaw and make the log genuinely sealed, rather than dodging
by excluding it (which would lower audit integrity).

## The fix

1. `JUDGE_PATTERNS` now includes `runtime/verification/**/*.json`, so the reseal log is a
   sealed judge artifact (`judge_manifest.json` is still excluded by basename in
   `judge_files()` — a manifest cannot seal its own hash).
2. `write_manifest()` reordered to ensure the log is final *before* sealing:
   1. ensure the reseal log exists (so it is part of the sealed set);
   2. append this reseal entry and write the log;
   3. `seal()` — captures the log's final content;
   4. write `judge_manifest.json`.
   Result: `write_manifest(...)` followed by `verify()` is consistent (`ok=True`).

## The new test (proves the closed loop)

`test_write_manifest_then_verify_is_a_closed_loop` builds a faithful on-disk repo layout where
the log lives **inside** the sealed tree (`runtime/verification/reseal_log.json`), then asserts:

- `write_manifest()` then `verify()` → `ok is True`;
- the log really contains this reseal (`by == "p2-1-operator"`);
- the manifest seals the log's **final** (post-entry) hash.

`test_reseal_log_is_a_sealed_file_in_real_repo` asserts the real repo seals the log while the
manifest stays self-excluded. A companion demo was run against the old vs new order: the old
order gives `verify ok=False`, the new order gives `verify ok=True`.

## Why the guard is still red (pending operator re-seal)

`judge_guard.py` is itself a sealed file, and this change edits it (plus a new sealed
`reseal_log.json` appears). So `verify()` correctly reports changed/added sealed files and the
seal-guard tests stay red — that is the intended "a judge file changed; re-seal required"
state, not a defect. It clears only when the operator re-seals:

```bash
SMD_JUDGE_KEY=<secret> python -c "from runtime.verification import judge_guard; judge_guard.write_manifest(by='p2-1-operator')"
```

After re-seal, `write_manifest → verify` is a closed loop, so the guard returns `ok=true`.
