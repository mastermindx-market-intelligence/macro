# Q06 PREREG: feasible sparse-data calibration for the existing FS-3 study

Status: research reference only. Nothing here is wired, registered, scheduled, promoted
or used as a gate. FS-3 (`research/OPTIONS_ALPHA_FLOW_SCORE_AMENDMENT.md`, frozen) and
the held decision draft PR #8385 are the owners. Q06 is a contribution to that held
decision. It is not a competing calibration project.

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), in the Q06 workflow AUTHOR role.
The PR #8385 draft was read at head `0234ea19cb8fee75750f8c387b2fe4a3cf358a25`; the local copy has
sha256 `15a1ff0abc201e128fbf846233e6fe1beb993d5d4caab538bcda8fd2077ac34c`.

## 0. Pre-outcome state at freeze

No outcome column (`spy_excess_*`, `fwd_*`, `terminal_state_*`, `prem_touch_50`) has been
read. Only schemas, row counts, `source`/`detector_version`/`dte_bucket` counts and file
hashes are known. Ledger facts:

- 92,574 rows, all `live_feed` / `live_feed_v1`.
- `dte_bucket` counts: 1_7d 36,059; 8_30d 21,254; 31_90d 19,464; 0d 15,797.
- There are no 90p rows.

No support or weight number has been computed on real data.

## 1. Non-duplication

**Incumbents (not rebuilt, not replaced, not imported by the new module):**

| Incumbent | What it owns | Q06 relation |
|---|---|---|
| PR #8385 (UNRATIFIED draft, REVISE) | FS-3 weighted-bin, tie, support and monotonicity decision | Q06 evaluates its open clauses and returns a bounded proposed amendment to the same owner. No competing rule is adopted. |
| `lib/flow_score.py`: `uniqueness_weights_nyse_intervals`, `uniqueness_weights`, `ece`, `reliability_table`, `is_reliability_monotone`, `weighted_binary_metrics`, `strict_weighted_binary_inputs` | The frozen native weight law and the unweighted/weighted metric helpers | The reference reproduces the native weight law exactly, cross-checked by evaluate.py. It never redefines or replaces the law. |
| `lib/flow_score_geometry.py`: `canonical_intervals`, `validate_population_partition` | FS-5 interval geometry and population partition | Used read-only by evaluate.py for the cross-check. Populations are never partitioned or relabelled. |
| `scripts/ops_train_flow_score.py`: `train_bucket`, `_weighted_calibration_diagnostics` | The FS-4 trainer. Its current state is `CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable`. | This is the baseline. Q06 changes no trainer behaviour. |
| `engine/validation.py`: `platt_fit`, `expected_calibration_error`, `isotonic_calibration` | Generic unweighted calibration helpers | Not duplicated. Q06's recalibration is weighted, takes block-bootstrap uncertainty, and is research-only. |
| `engine/seasonality/calibration.py`: `calibration_slope_intercept`, `cluster_bootstrap_ci`, `cluster_bootstrap_difference_ci`, `fit_calibrator`, `forward_chained_calibration` | Seasonality-program calibration | Not imported. Concepts are cited. |
| `engine/seasonality/event_study.py` | Kish effective-cluster count | Cited. Q06 keeps Kish separate from dependence (requirement 2). |
| `engine/calibration_hub.py`, `engine/trial_ledger.py` | Calibration and promotion reporting, trial accounting and DSR | Not rebuilt. No promotion controller, trial family or threshold is created. |

The EXCLUSIONS row reads: "FS-3 calibration decision | #8385 | Q06 is an explicit contribution to this existing held
decision, not a competing calibration project". It also says: "No new promotion controller."

**Narrow relation.** Q06 provides a research-only reference that evaluates #8385's open decisions under the FS-3
native weight law, with NYSE anchor-block uncertainty. Specifically:

- whole-tie bins
- weighted ECE and Brier
- support feasibility
- the monotonicity test
- a parsimonious continuous recalibration alternative
- a de-escalate-only partially pooled bin diagnostic

It adds no number beyond those already frozen in FS-3 §5 and §7 or drafted in #8385:

- FS-3 §5: ECE 0.05, 10 bins
- FS-3 §7: 30 per bucket, 20 per era cell
- #8385 draft: 20 per bin, 200 total, `floor(T/b) >= 20`, 95% valid replicates

It changes no frozen weight, sample membership, registration, horizon or outcome window.

**DNR boundaries kept:** DNR:KILL-OUTCOME-AUDITION, DNR:KILL-LLM-ORIGINATION, DNR:KILL-FUSED-COMPOSITE,
DNR:KILL-POSITIONING-FUSION, DNR:KILL-REGIME-SCORECARD,
DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR, DNR:KILL-CAUSAL-DAG-ALPHA, DNR:HOLD-PSS-AF1-FINRA
and DNR:HOLD-PSS-CD1-CROWDING. No outcome is auditioned and no signal is originated.

## 2. Estimands

**E1 (the one empirical comparison, on licensed retained data, pre-outcome geometry only).**

For each FS-3 model bucket b that has eligible rows:

- ρ_b is the native-law effective-N accrual rate, measured in effective observations per NYSE anchor session.
- From ρ_b, project the calibration-window length (in NYSE sessions) that each candidate support gate needs:
  - **G_inc** (#8385 draft as written): `Σw ≥ 200`, `B = min(10, G)` whole-tie bins each with
    `W_j ≥ 20`, and `floor(T/H) ≥ 20` anchor blocks. The projected length is
    `T_inc = max(200/ρ, 20·H)`.
  - **G_alt** (Q06 proposal; uses only existing numbers): `Σw ≥ 30` (the FS-3 §7 bucket floor) and
    `floor(T/H) ≥ 20` (the draft's own block floor). The projected length is `T_alt = max(30/ρ, 20·H)`.
- The primary contrast is `Q_b = T_inc / T_alt`.
- Also reported: years to feasibility (252 sessions per year) and the current retained-support state.

ρ is decomposed exactly. `a_t = Σ_{units covering t} (1/c_t) / L_unit`, so `Σ_units u = Σ_t a_t`. ρ is then the
mean of the per-anchor-session series `s_t = Σ_{units anchored at t} u_unit` over the window's anchor sessions.

**S1 (simulation, synthetic labels only, no licensed data).** S1 gives the operating characteristics of three
decision rules on correlated sparse data under the native weight law:

- **R_inc**: the #8385 draft.
- **R_alt**: Q06 continuous weighted logistic recalibration with an anchor-block bootstrap, and a
  simultaneous bin-residual misfit flag.
- **R_pool**: a partially pooled (empirical-Bayes) bin ECE with shrinkage toward the recalibration
  line, re-estimated inside every bootstrap replicate.

Each rule returns PASS, FAIL or NO_VERDICT.

**Outcome-based calibration of real FS-3 scores (not run).** This is INSUFFICIENT_DATA by construction unless the
runtime check finds both of the following:

- (i) a retained FS-4 fitted model artifact or predictions under `data/flow_signals/models` (the directory is
  gitignored and R2-only; R2 is forbidden here)
- (ii) an admitted FS-5 population partition receipt naming `calibration_eval` membership

The FS-3 temporal holdout and final OOS block are never read.

## 3. Unit, clocks, cohort

- **Unit.** A native uniqueness unit is the pair (fill NYSE session, ROOT). Its inclusive interval runs over NYSE
  positions `[fill_position, end_position]`, with `end = outcome_end_session_H` from grades. This is exactly the
  frozen law in `lib/flow_score.uniqueness_weights_nyse_intervals`. Concurrency c_t counts units globally across
  roots within the bucket population.
- **Input clock.** The ledger `session_date` (event session) and the grades `fill_date`.
- **Output clock.** `outcome_end_session_H`. This is used only as a geometry boundary; the outcome value is never read.
- **Cohort.** The ledger joined to grades on `event_id`, with:
  - `source = live_feed`, `detector_version = live_feed_v1`
  - `root != SPY` (benchmark self excluded; no other index exclusion is applied, so support is an
    upper bound)
  - `model_bucket = map_model_bucket(dte_bucket)`
- **Buckets and horizons.** Buckets 0_7 (H=5), 8_90 (H=21) and 90p (H=63, secondary 126). 90p is expected to
  have zero rows and is reported as such.
- **Eligibility (attrition reported per step).** Each step is counted:
  1. a grade row exists
  2. `graded_ok` is true
  3. `fill_date` is present and is an NYSE session
  4. `outcome_end_session_H` is present and is an NYSE session
  5. `fill >= event session` and `end >= fill`
  6. the unit boundaries are consistent

  Pending, failed, missing and excluded are counted separately. None is treated as zero.
- **Era.** Every fill session's era is reported (2017-19 / 2020-22 / 2023+).

## 4. Source vintages (sha256)

macro-main data vintage `cdab6268` (read-only):

- `data/flow_signals/ledger.parquet`: `c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62`
- `data/flow_signals/grades.parquet`: `3bb26d6440f262c2f8bac7cfd23313b466ce00091a397a17684cc8cc073e1d32`
- `data/flow_signals/gate.json`: `92eec77adb20de9e8599435fda221a361fa24c8d4d7a6ddef99ce453a0f64682`

Q06 clone sources (identical to _base):

- `config/flow_score.yml`: `f372519b5b41f9c175c1cd044ab0289da464b97963dda8b61e53bea73d53502c`
- `lib/flow_score.py`: `e697a9a06f430ee9496e757b67f4cb3d6fc8b5db3376385afd88f261ba096102`
- `lib/flow_score_geometry.py`: `1960d0589c76cd2a6a3ecfeb685714357c7ac4997c98ca8d55b202b771469cdf`
- `lib/nyse_calendar.py`: `7c9167fd416babb64c3067ae7e6237615011ad79e26d826e57005486496410ce`
- `research/OPTIONS_ALPHA_FLOW_SCORE_AMENDMENT.md`: `1c8ac33e0b189d080f41ef74b3e029f91777ad3e9043f5d8eb0ab6e937496d40`
- `scripts/ops_train_flow_score.py`: `a174315ab9917f9733a995843452c5cd7590f3b3a9c74e5c8b40f794e9e3469e`

evaluate.py re-hashes every input at run time. A mismatch aborts the run.

## 5. Hypotheses

- **H-E1.** Under the native law the accrual rate is capped at `ρ ≤ (1 + (L−1)/T)/L`, so G_inc
  needs roughly `200·L` anchor sessions. On real retained geometry, `Q_b ≥ 2` for every bucket with
  rows. G_inc is practically infeasible (more than 2,520 sessions, i.e. 10 years) for 8_90.
- **H-E1-proj.** The accrual rate estimated on the chronological training window predicts realized
  test-window accrual. The ratio realized/predicted has a 90% interval that intersects [0.5, 2.0].
- **H-S1.** R_alt keeps false reassurance (PASS under a miscalibrated truth) at or below 0.10 and false kill
  (FAIL under the calibrated truth) at or below 0.10 in every supported cell. R_inc reaches support only at
  roughly `200·L` sessions. R_pool, because shrinkage pulls toward the fitted line, can show
  shrinkage-created reassurance on local reversals. This is reported, not assumed.

## 6. Baseline competitors

1. **Incumbent trainer state.** `train_bucket` returns
   `calibration_insufficient` / `CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable` with
   `ece=None` and writes no artifact. This is reproduced by evaluate.py stage `baseline`, which
   checks the source strings, the `scoring.enabled: false` config and the absence of a models dir.
2. **#8385 draft rule** (R_inc / G_inc).
3. **Partially pooled bins** (R_pool).

## 7. Practical effect bar

- E1: `Q_b ≥ 2` (point estimate), with block-bootstrap 5th percentile `≥ 2`.
- A gate is "practically infeasible" when its projected T exceeds 2,520 NYSE sessions (10 years).
- S1: false-reassurance and false-kill rates of at most 0.10 (point estimate; Wilson 95% interval reported).

## 8. Trial family

There is exactly one empirical comparison (E1). Both gates are evaluated on both buckets that have rows, and every
cell is reported; there is no selection among them, no hyperparameter search and no repeated holdout.

S1 is a fixed simulation grid that is not chosen by data:

- Buckets: H=5 (L=6) at T ∈ {252, 504, 1260}; H=21 (L=22) at T ∈ {252, 756, 1512, 4536}.
- Truths: T0 calibrated `π=p`; T1 overconfident `logit π = 0.5·logit p`; T2 shifted
  `logit π = logit p − 0.6`; T3 local reversal `π = p − 0.15` for p in [0.55, 0.75], `π = p`
  elsewhere.
- Regimes:
  - steady: units per session ~ Poisson(3)
  - bursty-selected: λ_t ~ Gamma(shape 0.5, scale 6), with informative selection where sessions
    with λ_t above its median draw p from Beta(3,2) instead of Beta(2,3)
- p is rounded to a 0.05 grid (ties) and clipped to [0.05, 0.95].
- Labels use a Gaussian copula. A window shock `ε = Σ_{s in window} e_s / sqrt(L)` with
  `e_s ~ N(0,1)` iid gives latent `z = 0.5·ε + sqrt(0.75)·η`, and `y = 1{Φ(z) < π(p)}`. This
  gives exact marginal `π` with dependence across overlapping windows.
- Replicates: 200 per cell. Simulation bootstrap R = 299; the module default stays 9,999 as in the
  draft. The reduced R is for compute only.

Seeds come from the SHA-256 of `"q06-s1\0{bucket}\0{T}\0{truth}\0{regime}"` mapped to PCG64.

## 9. Outcome windows

FS-3 horizons are frozen: 5 (0_7), 21 (8_90), 63/126 (90p). Q06 reads no outcome value in any window.
`outcome_end_session_H` is used as an interval boundary only.

## 10. Chronological split (E1)

Per bucket:

1. Let the eligible distinct NYSE anchor (fill) sessions run from F0 to F1.
2. Let `T_all` be the number of NYSE sessions in `[F0, F1]`.
3. Training covers the first `floor(2·T_all/3)` sessions; test covers the remainder.
4. Units are assigned by fill session.

All preprocessing happens inside each window separately: unit construction, concurrency and native weights.
ρ_train is estimated on training only. The prediction is `Σu_test_pred = ρ_train · T_test`, scored against the
realized `Σu_test`. There are no hyperparameters. The block length is fixed by H, as stated below.

## 11. Dependence-aware uncertainty

- **E1.** A circular moving-block bootstrap over the anchor-session series `s_t` in the training window.
  - Block length is `b = L` (= H + 1).
  - R = 9,999 with a SHA-256-derived PCG64 seed.
  - Honest N is `floor(T_train / b)` blocks. Sensitivity runs at `b = 2L` and `b = 4L` are reported.
  - The test ratio's interval bootstraps both windows independently (block length L).
- **S1.** R_inc uses the draft's circular moving-block bootstrap over anchor sessions with `b = H`.
  R_alt and R_pool use the same bootstrap with `b = H`. Native weights stay fixed inside resamples.
- Kish `N = (Σw)²/Σw²` is reported as a separate weight-concentration field. It is never used as a
  dependence count.

## 12. Decision rules (frozen)

**R_inc** follows the draft.

- Support requires all of:
  - `Σw ≥ 200`
  - the DP whole-tie partition into `B = min(10, G)` bins with every `W_j ≥ 20`
  - `floor(T/H) ≥ 20`
  - at least 20 distinct anchors per bin
  - at least 95% valid bootstrap replicates
- **PASS:** weighted ECE `< 0.05`, AND weighted Brier `<` base-rate Brier, AND the max-stat
  monotonicity test is not broken.
- **FAIL:** support holds but any of those three fails.
- **NO_VERDICT:** otherwise.

**R_alt** (Q06).

- Support requires all of:
  - `Σw ≥ 30`
  - `floor(T/H) ≥ 20`
  - at least 95% valid replicates (IRLS converged and both label values have positive weight)
- Fit `logit π = a + b·logit p` by weighted maximum likelihood.
- **Implied ECE** is `I = Σ_i (w_i/W)·|σ(a + b·logit p_i) − p_i|`. Its percentile bootstrap gives the
  bounds `I_lo` (5th percentile) and `I_hi` (95th percentile).
- **Brier difference** is `D = Brier_w(p) − Brier_w(base)`, with the same bootstrap.
- **Misfit flag.** Use whole-tie DP bins (B = min(10, G), no floor). The bin residual is
  `r_j = rate_j − mean_w σ(a + b·logit p)` within bin j. A bin j is flagged when all three hold:
  - `W_j ≥ 20`
  - `|r_j| > c` (c is the 95th percentile of `max_j |r*_j − r_j|`, a simultaneous band)
  - `|r_j| ≥ 0.05`
- **PASS:** `I_hi < 0.05`, `D_hi < 0`, and no misfit flag.
- **FAIL:** `I_lo ≥ 0.05`, or any misfit flag, or `D_lo ≥ 0`.
- **NO_VERDICT:** otherwise, and also whenever support fails. The point estimate and interval are
  still reported.

**R_pool.**

- Support is the same as R_alt.
- Bin deviations from identity are `d_j = rate_j − pred_j`.
- The line prediction is `m_j = mean_w σ(a + b·logit p) − pred_j`.
- `v_j` is the bootstrap variance of `d_j`.
- `τ² = max(0, mean_W((d_j − m_j)²) − mean_W(v_j))`.
- `d̃_j = m_j + (τ²/(τ² + v_j))·(d_j − m_j)`.
- Pooled ECE is `Σ (W_j/W)·|d̃_j|`. It is re-estimated per replicate, including τ².
- **PASS** when the 95th percentile is `< 0.05` and `D_hi < 0`. **FAIL** when the 5th percentile is `≥ 0.05`.
  **NO_VERDICT** otherwise.

**Shrinkage law.** In the proposed amendment, pooled estimates are display and de-escalation only. They can never
turn NO_VERDICT into PASS.

## 13. Falsifiers and verdict

These verdicts concern the Q06 reference: the proposed amendment, to be returned to #8385.

- **F0 (reference defect).** The module's native weights differ from
  `lib.flow_score.uniqueness_weights_nyse_intervals` by more than `1e-12` (max absolute) on the real
  cohort, or the module fails its own tests. Result: **REJECT**.
- **K1.** In every S1 cell where R_alt support holds in at least 50% of replicates:
  - R_alt false reassurance `≤ 0.10` (T1, T2, T3)
  - R_alt false kill `≤ 0.10` (T0)

  Failure means **REJECT**.
- **K2.** In S1, the first grid T at which R_inc support holds in at least 50% of replicates is at least
  2× the first such T for R_alt (or R_inc never reaches support on the grid), for both buckets. Failure
  means **REJECT**.
- **K3.** E1 requires `Q_b ≥ 2`, with 5th percentile `≥ 2`, for every bucket with eligible rows.
  - Failure on the ratio means **REJECT**: the incumbent gate is not materially less feasible.
  - If H-E1-proj fails (the interval misses [0.5, 2.0]), the projection is not reliable and the
    result is **INSUFFICIENT_DATA**.
- If E1 cannot be computed (no eligible rows in any bucket, or the inputs are missing), the result is
  **INSUFFICIENT_DATA**, naming the missing input.
- **KEEP** requires F0 clear and K1, K2 and K3 all holding. KEEP means only that the research reference
  and proposed amendment are kept for the #8385 owner. It is not a calibration claim about FS-3 scores, it
  activates nothing, and the bucket stays `building_history`.
- **Separately and always reported:** `OUTCOME_CALIBRATION = INSUFFICIENT_DATA`. The record names the
  missing FS-4 model artifact or predictions and the missing FS-5 `calibration_eval` partition receipt,
  unless the runtime check finds them; in that case they are still not read without an amendment.
- **Current estimability per bucket.** The retained data is reported as `NOT_YET_ESTIMABLE` or
  `SUPPORT_UPPER_BOUND_MET` under G_alt and G_inc. This uses total retained support, which is an
  upper bound on any `calibration_eval` share.

## 14. Stop rule

- Each evaluate.py stage (`baseline`, `e1`, `s1`) runs once. A rerun is allowed only after a crash or
  a code defect that did not depend on observed results. Every run is logged in RUNS.log.
- No parameter, threshold, cohort or grid changes after any result is seen. Any change goes in
  PREREG_AMENDMENT.md, written and hashed before the rerun.
- No run reads outcome columns. evaluate.py reads grades with an explicit geometry-only column list,
  and asserts that list.
- Each run stays under 10 minutes, with thread-limited BLAS and `nice -n 10`.
