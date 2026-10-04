# China Risk Radar Revalidation Implementation Plan

> **Operation:** `cn-risk-p1-radar-revalidation-20260923-solpro-001`
> **Spec:** `research/cn_risk_revalidation/PREREGISTRATION.md`
> **Repository:** `mastermindx-market-intelligence/macro`
> **Branch:** `sol/cn-risk-p1-revalidation-20260923`
> **Frozen base:** `8db6896dab2199a4b7fc61a005c225380cac7cd6`
> **Protected Skillpack:** `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`

## Goal

Produce a reproducible, research-only adjudication of the exact current China external-driver Risk Radar. The package must establish which historical hazard, current probability, state-ordering, band, and context-gate claims survive; it must not change production behavior or silently substitute a different construction or benchmark.

## Global constraints

- Do not edit `engine/risk_radar_intl.py`, `engine/risk_radar_intl_audit.py`, UI/templates, Market State weights/cuts, gross-factor policy, `can_force`, current forward-log historical rows, or downstream consumers.
- Freeze and verify the exact production construction before reading outcomes.
- Keep reconstructed historical evidence and genuinely issued forward evidence separate.
- Use Shanghai Composite for the canonical production construction and CSI300 only with exact disclosed provenance.
- No post-hoc threshold search, candidate tuning, or multiple-testing promotion.
- Every new implementation function is developed RED → GREEN under focused tests.
- Commit immutable, small result artifacts; never commit regenerated market source data.
- Stop at an exact-head Draft/HOLD PR. Do not merge.

## Interfaces

- `engine.risk_radar_intl.composite_series(CN_PROFILE)` produces the exact causal production benchmark, sub-leg percentiles, composite percentile, and context gate consumed by the research harness.
- `scripts/research/cn_risk_radar_revalidation.py` consumes those exact series and produces a versioned JSON result plus a Markdown adjudication.
- `tests/test_cn_risk_radar_revalidation.py` exercises pure outcome, episode, bootstrap, calibration, baseline, provenance, and verdict logic without relying on mutable network data.
- `research/cn_risk_revalidation/PREREGISTRATION.md` is the binding statistical contract; later code and interpretation may not weaken it.
- `research/cn_risk_revalidation/results.json` is machine-readable; `REPORT.md` is its human-readable rendering. Both must identify the exact source/data hashes used.

## Task 1 — Freeze scientific and source contract

**Files**
- Create `research/cn_risk_revalidation/PREREGISTRATION.md`.
- Create `.superpowers/sdd/2026-09-23-cn-risk-radar-revalidation/progress.md`.

**Steps**
1. Record base SHA, Skillpack SHA, production blobs/SHA-256 values, current CN profile parameters, benchmarks, outcomes, horizons, eras, crises, bootstrap/permutation procedures, baselines, evidence thresholds, and claim-verdict rules.
2. Confirm no historical result file or forward-log row was inspected before the freeze.
3. Commit the plan and preregistration as a standalone preregistration commit. This commit is `PREREG_SHA`.

**Verification**
- `git diff --check`
- a source-protection check confirms no forbidden path changed.

## Task 2 — Build tested causal primitives

**Files**
- Create `tests/test_cn_risk_radar_revalidation.py`.
- Create `scripts/research/cn_risk_radar_revalidation.py`.

**RED → GREEN steps**
1. Write failing tests for forward maximum drawdown using future sessions only, maturity exclusion, and threshold labels for 5%/21 and 10%/42.
2. Implement the minimum pure functions needed to pass.
3. Write failing tests for emitted-state reconstruction, including the context-gate cap from elevated/risk-off to caution.
4. Implement the minimum state reconstruction.
5. Write failing tests for contiguous/horizon-separated episode IDs and effective-N ceilings.
6. Implement episode accounting.

**Verification**
- `python3 -m pytest -q tests/test_cn_risk_radar_revalidation.py`

## Task 3 — Add dependence-aware metrics and calibration

**RED → GREEN steps**
1. Add failing deterministic tests for lift, average precision, ROC AUC, Brier score, Brier skill, and state calibration tables.
2. Implement the metrics with explicit empty/degenerate behavior.
3. Add failing tests for circular moving-block bootstrap and block permutation reproducibility.
4. Implement deterministic seeded uncertainty and p-values.
5. Add failing tests for calibration intercept/slope qualification and probability-bin inversion detection.
6. Implement qualified calibration diagnostics and monotonicity checks.
7. Add failing tests for split-half, post-2016, and leave-one-crisis-out embargo behavior.
8. Implement the stability slices.

**Verification**
- focused test file green with deterministic seeds.

## Task 4 — Bind exact production inputs and honest baselines

**RED → GREEN steps**
1. Add failing tests that reject source-hash drift and prohibit an unexpected CN calibration overlay.
2. Implement source/data manifests with Git blob, SHA-256, rows, date range, columns, and role.
3. Add failing tests for the preregistered baselines: breadth-only, rates-only, below-200DMA context, baked unconditional base, and delayed expanding base.
4. Implement fixed, causal baseline scores without fitting thresholds on inspected outcomes.
5. Add failing tests that the CSI300 replication reuses the canonical production signal rather than silently rebuilding a different model.
6. Implement benchmark alignment and explicit unavailable/insufficient provenance states.

**Verification**
- focused tests green.
- production files remain byte-identical to frozen hashes.

## Task 5 — Build one-command research run and claim adjudication

**RED → GREEN steps**
1. Add failing CLI tests over deterministic synthetic fixtures for one-command execution and stable schema.
2. Implement CLI arguments: `--repo-root`, `--output-dir`, `--bootstrap-reps`, `--permutation-reps`, `--seed`, and `--check-only`.
3. Add failing tests for all seven claim verdicts and the preregistered evidence hierarchy.
4. Implement verdict logic that returns only `KEEP`, `KEEP_BUT_RELABEL`, `RECALIBRATION_CANDIDATE`, `FAIL / REMOVE`, or `INSUFFICIENT_EVIDENCE`.
5. Render `results.json`, `REPORT.md`, and `data_manifest.json` atomically.

**Verification**
- synthetic fixture run is reproducible byte-for-byte except explicitly timestamped metadata (prefer no wall-clock field).

## Task 6 — Execute the frozen study

**Steps**
1. Re-pin `origin/main` and protected Skillpack; perform one bounded collision check on owned paths.
2. Record the exact frozen source/data manifest.
3. Only now inspect reconstructed outcomes and the committed CN forward ledger.
4. Run the exact production construction on Shanghai Composite.
5. Run the outcome-only CSI300 replication if a lawful exact series exists; otherwise record the exact insufficiency.
6. Run primary 5%/21 and historical 10%/42 targets, secondary h5/h10 diagnostics, split-half, post-2016, LOCO, calibration, dependence-aware uncertainty, and baseline comparisons.
7. Interpret the forward ledger separately and preserve unresolved rows as unresolved.
8. Commit immutable result artifacts and the report.

**Verification**
- repeat the command and confirm stable result hashes.
- compare report values against machine JSON.

## Task 7 — Adversarial review, CI, and Draft/HOLD PR

**Steps**
1. Run focused tests, source-protection checks, syntax/format checks, and the relevant CI pack or repository contract checks.
2. Generate a whole-branch review package from the frozen base to exact head.
3. Obtain one fresh adversarial review where the available fabric permits; otherwise perform and disclose a separate self-review against the package.
4. Fix Critical/Important findings in one RED → GREEN pass; ledger minor deferrals and rulings.
5. Re-pin before final modification, reconcile only owned-path collisions, and rerun exact-head verification.
6. Push branch and create one Draft PR whose title/body explicitly say HOLD, research-only, no production behavior changes, and no merge.
7. Verify PR exact head, draft state, no auto-merge, no merge-on-green label, and clean local worktree.

**Completion evidence**
- exact-head Draft/HOLD PR
- green focused tests and relevant CI
- immutable preregistration and result commits
- explicit claim-by-claim adjudication
- no forbidden production-path diff

## Review focus

- Any leakage from future benchmark bars into signals or baselines.
- Any use of revised/full-sample outcomes to fit a purportedly causal forecast.
- Any daily-row confidence interval presented as independent-N evidence.
- Any benchmark substitution, especially FXI for A-share indexes.
- Any conflation of reconstructed history with issued forward evidence.
- Any verdict that bypasses the preregistered thresholds because the point estimate looks attractive.
- Any change to production model behavior, thresholds, logs, UI, or consumers.
