# China Risk Radar capital-policy validation — implementation plan

> Carrier: `sol/cn-risk-p4-capital-policy-20260923`; base `49ceebf8d1a14c044684abdbeeb5779875cf20fc`; operation `cn-risk-p4-capital-policy-20260923-solpro-001`.

**Goal:** Produce a reproducible, read-only capital-policy replay and a Draft/HOLD evidence PR that adjudicates exact gross authority without changing any live policy.

**Architecture:** One importable research module owns frozen policy definitions, PIT state reconstruction, replay mechanics, metrics, episode/crisis analysis, bootstrap uncertainty, deterministic adjudication, and artifact rendering. Tests exercise pure functions with synthetic data before the real dataset is evaluated. Compact generated artifacts are committed under the owned research directory.

### Task 1 — Freeze before outcomes

1. Commit the design, this plan, `PREREGISTRATION.md`, and machine-readable `preregistration.json` before running any policy return calculation.
2. Record the resulting commit as `PREREG_SHA` and do not amend or rewrite it.
3. Verify no live/no-edit path changed and checkpoint the clean branch.

### Task 2 — Test-first research core

1. Add `tests/test_cn_risk_capital_policy.py` with failing tests for exact mappings, lag semantics, transaction costs, exposure-matched constants, metrics, crisis windows, independent episodes, bootstrap determinism, and authority/UI adjudication.
2. Run the focused test and confirm failure for the missing module.
3. Implement `scripts/research/cn_risk_capital_policy.py` using only pandas/numpy and existing exact Radar/store readers.
4. Re-run focused tests until green; repair root causes rather than relaxing assertions.

### Task 3 — Reproduce and fingerprint the dataset

1. Reconstruct CN states from the exact pinned engine and gate; assert the current mapping read from source equals the preregistered mapping.
2. Load the primary Shanghai Composite series, secondary `510300.SS` proxy, and forward ledger without writing to `data/`.
3. Record SHA-256 hashes of source code and data inputs, date coverage, row counts, state counts, issued/matured forward counts, and a deterministic population fingerprint.

### Task 4 — Run the frozen replay once

1. Evaluate the current ladder first, then the fixed baselines, under lag/cost scenarios.
2. Compute full-sample, era, crisis, recovery, episode, LOCO, opportunity-cost, turnover, and bootstrap artifacts.
3. Apply the preregistered decision tree without changing mappings, thresholds, windows, or gates after observing results.
4. Emit `summary.json`, `metrics.csv`, `crisis_results.csv`, `episode_results.csv`, `loco_results.csv`, `bootstrap.json`, `shadow_candidate.json` only if earned, and `REPORT.md`.

### Task 5 — Verify containment and evidence

1. Run focused tests plus relevant Radar profile tests, syntax/import checks, deterministic rerun/diff, and the repository's applicable CI validation.
2. Confirm `git diff` touches only owned research/harness/test paths and that prohibited live paths are byte-identical to base.
3. Review the whole branch against the commission: no ladder shopping, no forward-performance overclaim, explicit opportunity cost/crisis concentration/effective N/UI semantics.

### Task 6 — Park one Draft/HOLD PR

1. Commit generated evidence, push the exact head, and open one draft PR with `[DRAFT/HOLD]` in the title.
2. State the hold authority and release condition; keep `merge-on-green` absent and native auto-merge null.
3. Observe CI to conclusion and fix genuine branch failures while preserving the frozen protocol.
4. Finish only when exact head is pushed/clean, binding checks conclude green, PR is draft, hold text is present, and no live policy has changed.
