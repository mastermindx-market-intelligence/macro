# Options Alpha Flow-Score Evaluation Amendment — 2026-09-19

**Operation:** `options-alpha-fs-evaluation-contract-20260919-sol-001`  
**Parent:** `mastermindx-market-intelligence/mastermind-terminal#599` / `options-alpha-product-integration-20260917-sol-001`  
**Authority:** `ceo-sol`, under current Chairman instruction to take over the parent and continue the program.  
**Protected procedure:** `Mastermind@880e377cfa9d3fbdc921e931a55cc8c4143dc119`, Skillpack `mastermind.sol_skillpack.v1` / `1.0.1` / bootstrap `1`.  
**Macro base:** `6f35b67d4a2655f2e8409406646f88adf852c2b6`.  
**Decision:** `DEC:OPTIONS-ALPHA-FS-EVALUATION-CONTRACT`.  
**Status:** records/source law only. No model fit, calibration fit, score enablement, promotion, production data mutation, deployment or trade authority.

## 0. Why this amendment exists

Packet B did not find a "better signal." It found that the existing FS statistical implementation can violate or ambiguously implement parts of its own frozen evaluation contract before a model is ever judged.

The current repository still reports:

- `data/flow_signals/gate.json` as of 2026-09-18;
- `scored=false`;
- `model_versions={}`;
- `n_scored_total=0`.

That makes this a prospective method correction. It does **not** rewrite a promoted live model or use outcomes to tune a winning construction.

This amendment narrows and clarifies the already-registered FS family. It does not create a new score, new ledger, new lifecycle or new authority plane.

## 1. The target is exact and narrower than current prose implies

For the existing FS family, the machine target is the binary label already implemented by the frozen config/grader path:

```text
Y_H = 1[spy_excess_H > 0]
```

where `H` is the registered DTE-routed horizon:

- 0–7 DTE -> 5 sessions;
- 8–90 DTE -> 21 sessions;
- 90+ DTE -> 63 sessions primary;
- 126 sessions remains the registered secondary long-bucket ruler when its own embargo/maturity requirements are satisfied.

Therefore the existing family estimates a conditional probability that the **underlying outperforms SPY over the registered horizon**, conditional on a detector-fired options-flow event and its lawful features.

It does **not** estimate:

- absolute movement of any size;
- volatility or realized variance;
- a call thesis succeeding;
- a put thesis succeeding;
- option-contract return;
- package return;
- expected value;
- execution quality;
- profitability;
- direction inferred from customer intent.

"Unsigned" means only **not conditioned on option right**. Calls and puts may enter the same target population only under the existing family because the label does not flip with right.

Any future right-conditioned or absolute-move target is a **new registered family/version**. It cannot silently replace this label.

### 1.1 Product copy consequence

Until a separately accepted family says otherwise, a calibrated FS output may be described only in language equivalent to:

> "Conditional probability that the underlying outperforms SPY over the registered horizon, among eligible detector-fired events."

It may not be called "bullish probability," "bearish probability," "option success probability," "probability of a large move," or "expected return."

## 2. Benchmark-self observations are structurally ineligible for this target

If the underlying is SPY and the benchmark is the identical SPY series over the identical horizon:

```text
spy_excess_H = SPY_return_H - SPY_return_H = 0
```

The resulting label is one-class by construction.

Therefore:

1. The current **SPY-only `tape_recon` cohort is ineligible for fitting, calibration or verdicts for this SPY-excess family**.
2. It remains lawful as measurement/diagnostic evidence and for source-quality work.
3. It must not be pooled with live_feed to manufacture class variation.
4. A future non-SPY tape reconstruction may become eligible only if it independently satisfies the same source, detector, clock and split contract.
5. Existing registered cells are not deleted post-hoc. A cell whose only available source is structurally ineligible remains registered-but-unfilled / building history.

This is a source-contract correction, not an empirical null.

## 3. Population identity is one artifact, one source and one detector version

Every fit/evaluation artifact is keyed at minimum by:

```text
(
  evaluation_spec_version,
  source,
  detector_version,
  model_bucket
)
```

The following are prohibited:

- concatenating `tape_recon` and `live_feed` into one fit or calibrator;
- mixing detector versions in one fitted artifact;
- defaulting a missing source field to `live_feed`;
- treating unknown detector version as the current version;
- allowing a wrapper/build date to define source era or detector identity;
- silently adding `eod_proxy` to fit/calibration/OOS.

`eod_proxy` remains priors/pre-training only under its existing law. If pre-training is ever used, its influence must be versioned and it may not substitute for a serving-distribution verdict.

A source or detector field that is missing/ambiguous makes the row ineligible for the fitted population. Missing identity is not a weak positive or neutral.

## 4. The existing positive monotonic constraints are removed for this target

Current `config/flow_score.yml` constrains:

- `at_ask_share` upward;
- `vol_gt_oi_ratio` upward.

The stated mechanism is "stronger flow conviction" / "more notable signal." That does not establish a monotonic relationship with **future SPY outperformance**, especially while option right is pooled and opening/customer intent is unobserved.

The amended construction therefore freezes:

```text
monotone_constraints = {}
```

for the existing SPY-excess family.

This is **not** an invitation to run both constrained and unconstrained variants and choose the better result. The constrained form is retired **before a lawful fit under this amendment**. It contributes no extra selection branch.

If a future family can justify a monotone mechanism to its exact target, that constraint must be registered in that family before fitting.

## 5. Time is NYSE-session time, not row position or calendar-day approximation

Every accepted row must have a valid canonical session.

No fit/evaluation path may fall back to row position when `session_date` is missing or malformed.

### 5.1 Session-atomic block assignment

All events from one NYSE session belong to exactly one time block.

A row-count partition that can split the same session across train and validation is invalid.

### 5.2 Exact label interval

For each observation, define the label interval using the actual grader entry/fill session and the registered horizon:

```text
label_interval_i = [fill_session_i, outcome_end_session_i]
```

where `outcome_end_session_i` is the H-th eligible trading session under the canonical NYSE calendar.

### 5.3 Purge

For an evaluation block, remove every training row whose label interval intersects any session in the evaluation block.

This is the binding leakage rule. It is stronger and more exact than comparing calendar-day distances around block boundaries.

### 5.4 Embargo

After purging, enforce an embargo in **eligible trading sessions**, not calendar days.

Minimum embargo by primary bucket:

- 0_7: 5 eligible trading sessions;
- 8_90: 21;
- 90p primary: 63;
- 90p secondary verdict: 126.

The implementation may use a more conservative fixed geometry only if it is frozen before outcome inspection and is not chosen by result.

## 6. Preserve the registered root-generalization claim or fail closed

The registered FS contract says a root must not appear in both train and validation within a fold.

That claim remains binding for this family.

Therefore:

- if the eligible cohort has fewer than two roots, the fold is not silently weakened to time-only;
- if root exclusion yields an empty train or validation set, emit `INSUFFICIENT_ROOT_DIVERSITY`;
- SPY-only `tape_recon` cannot use a special fallback to become an OOS verdict source;
- changing the family to "future observations of already-seen roots" would require an explicit new amendment and a new claim.

The implementation may report additional within-root temporal diagnostics, but they do not replace the registered root-disjoint verdict.

## 7. Model selection must execute the trial structure it reports

The current trainer reports:

```text
N_trials = grid_cardinality × interaction_variants × C(n_groups, k_test)
```

while the inspected selection loop uses ordinary generated folds and does not enumerate the reported combinatorial CPCV paths.

Under this amendment, the implementation must choose one of two lawful routes **before fitting**:

### Route A — execute the registered CPCV design

Actually enumerate the frozen combinatorial purged paths, apply the registered purge/embargo/root rules to every path, and use the executed path count in trial accounting.

### Route B — amend the registration again

If CPCV is intentionally abandoned, freeze the replacement model-selection geometry and its trial accounting in source law **before** any fit.

It is prohibited to count CPCV paths in `N_trials` without executing them and then cite that count as selection-bias correction.

No "we were conservative because the number was larger" substitution is allowed: trial-counting and selection geometry are distinct claims.

## 8. Calibration has three disjoint stages plus final OOS

The accepted sequence is:

```text
development / model selection
-> calibration-fit
-> calibration-evaluation
-> final untouched OOS
```

All four regions are ordered by canonical session and separated under the label-window purge/embargo law.

### 8.1 Calibration-fit

Fit the calibrator only on `calibration-fit`.

### 8.2 Calibration-evaluation

Compute ECE, Brier-vs-base-rate and reliability diagnostics only on a disjoint `calibration-evaluation` slice.

If calibration-fit has one class, insufficient effective N, insufficient bins or any required identity/clock failure:

```text
CALIBRATION_INSUFFICIENT
```

No fallback may fit the calibrator on the evaluation rows.

### 8.3 Final untouched OOS

The final OOS block participates in neither model selection nor calibrator fitting nor calibration-go/no-go tuning.

It is the only place a final registered discrimination/effect verdict may be produced.

No retry on the same final OOS block after inspecting failure is a fresh OOS test.

## 9. Effective N must be a real statistical quantity

Raw row count may be reported as `n_rows`.

A manifest field named `effective_n` must contain the actual accepted effective-N quantity for the relevant population/slice, not `len(frame)`.

At minimum preserve:

- raw rows;
- unique roots;
- unique sessions;
- unique root-sessions;
- uniqueness-weight sum;
- per-cell effective N under the registered inference method.

Repeated prints and same-session bursts cannot multiply support merely because they are rows.

A sparse cell remains `ERA_SPARSE` / building history. It is not rescued by smoothing or by borrowing neighboring bucket observations.

## 10. Artifact readiness, statistical acceptance and authority are different states

A machine-readable evaluation artifact must keep at least these concepts separate:

### `ARTIFACT_VALID`

The model/calibrator bytes and manifest are internally valid for the frozen population/spec. No statistical success implied.

### `CALIBRATION_GATE_PASS`

On disjoint calibration-evaluation data:

- ECE < 0.05;
- Brier beats the predeclared base-rate baseline;
- reliability monotonicity requirement passes;
- required effective-N/bin support passes.

This does **not** imply signal acceptance.

### `STATISTICAL_GATE_PASS`

Requires all applicable registered FS-5 evidence, including:

- final untouched OOS;
- newest-era discrimination above the registered kill boundary;
- required era/cell effective N;
- time/root-preserving inference;
- correct 36-family BH-FDR accounting for filled verdict cells;
- no unregistered horizon/target;
- no failed kill criterion.

A local calibration pass is insufficient.

### `PROMOTION_ELIGIBLE`

Requires a separate current DNR/promotion adjudication after statistical evidence passes.

### `SCORING_ENABLED`

May become true only under the accepted promotion/release owner. This amendment does not authorize it.

Current `flow_score.model_manifest/v1.deployable` is therefore **not accepted as a synonym for statistical or promotion authority**. The implementation owner must either version the manifest or fail-close its semantics so downstream code cannot interpret local calibration readiness as full acceptance.

## 11. Proper scoring and economic metrics

For the existing binary SPY-outperformance family:

- primary probabilistic metrics: Brier score and log loss against declared baselines;
- calibration: ECE plus reliability table with effective support;
- discrimination: AUC only under the exact registered newest-era rule and support;
- inference must preserve time/root dependence.

No option-contract economic metric is available from this family.

Underlying SPY outperformance is not option P&L.

Exact-option economics remain OA-3 and require the separately accepted exact-contract executable-NBBO ruler, costs, null/censor law and instrument lifecycle.

## 12. Multiple testing

The existing 36-cell family remains the family of record for the currently registered FS tests.

This amendment does not shrink it because some cells are currently unfillable.

Rules:

1. registered-but-unfilled/ineligible cells remain visible as unfilled;
2. no p-value exists below the support/eligibility floor;
3. when verdict p-values exist, use the frozen family law;
4. any new target, horizon, era, moneyness stratum or right-conditioned family requires an explicit enlargement/amendment before outcomes;
5. model/hyperparameter selection accounting and BH-FDR verdict accounting remain separate.

## 13. Implementation acceptance tests

The implementation child must add discriminating tests that fail on the current implementation for at least:

1. SPY self-benchmark rows cannot enter an FS SPY-excess fit/verdict.
2. `tape_recon` and `live_feed` cannot be pooled in one artifact.
3. two detector versions cannot be pooled.
4. missing source or detector version fails closed.
5. one NYSE session cannot be split across time blocks.
6. missing/invalid session date cannot fall back to row ordering.
7. five **trading-session** embargo differs correctly from five calendar days across a weekend/holiday.
8. a training label interval overlapping an evaluation block is purged.
9. single-root data does not disable root exclusion; it produces an insufficient-root state.
10. calibrator-fit and calibration-evaluation are disjoint and chronologically ordered.
11. a one-class calibration-fit slice fails closed without fitting on evaluation rows.
12. calibration slices are separated by the registered label-window rule.
13. final OOS rows are absent from model selection and calibrator fit.
14. reported CPCV path count equals paths actually evaluated, or CPCV is not claimed.
15. `effective_n` is not a raw row-count alias.
16. a deterministic example can pass local ECE/Brier/monotonicity while failing AUC<=0.55, and the artifact must remain statistically unaccepted.
17. all authority/scoring fields remain false until separate promotion.
18. `monotone_constraints` for this evaluation-spec version are empty and cannot be toggled as a hidden trial.

Mutation/discrimination tests should demonstrate that each fence is load-bearing.

## 14. Non-goals / do not redo

This amendment does not:

- fit any model;
- inspect outcomes to choose a winning model;
- enable the score;
- change detector thresholds;
- change the target label;
- revive DOI, skew-deceleration, signed-charm or tick-rule direction;
- add OI/GEX/positioning fusion;
- create a new candidate, campaign, outcome or evaluation ledger;
- claim exact-option return;
- alter OA-1C candidate formation;
- alter the incumbent #7290 carrier;
- alter #6691's workstream-continuity carrier;
- alter #7279/#7265/#7263/#7193 incumbent writer scopes.

## 15. Exact continuation after this amendment is accepted

The first implementation child should be a **repair-and-test wave over the existing FS trainer/evaluation paths**, not a model-fit wave.

Owned paths should be narrowly limited to the existing FS implementation and tests, expected to include:

- `scripts/ops_train_flow_score.py`;
- `lib/flow_score.py`;
- `config/flow_score.yml`;
- `tests/test_fs4_flow_trainer.py`;
- only directly necessary existing schema/manifest tests.

The child must:

1. reproduce the current failures test-first;
2. implement this frozen population/time/calibration/acceptance contract;
3. run the complete affected suite;
4. prove `scoring.enabled=false`;
5. produce **zero fitted production model artifacts** and no promotion claim;
6. return exact-head evidence for independent review.

Only after that repair is accepted may OA-2 run a separately authorized fit/evaluation gauntlet.
