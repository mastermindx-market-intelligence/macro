# Q06 verdict: REJECT (K1 failed)

**Scope.** This verdict covers the Q06 research reference and its continuous recalibration rule R_alt, as frozen in
PREREG.md (sha256 `23494b5254d5ddf6ef91d6b5835b9ecac47adbcbeed145b0c7895c88dcccc556`, FREEZE.log). It makes no
calibration claim about any FS-3 score. Nothing is wired, registered, scheduled, promoted or activated. FS-3 scoring
stays disabled and every bucket stays `building_history`.

**Served model.** Opus 5.5, model ID `claude-opus-5-5`. The author, the method reviewer of #8385 and the writer of
this file are the same session. An independent read-only audit later returned PASS_WITH_FIXES (0 blockers,
2 majors, 4 minors). Its fixes are recorded in §0 and in PREREG_AMENDMENT_2.md.

## 0. Chain of custody (PREREG_AMENDMENT_2.md)

The audit found that the four original runs used engine module bytes `0afd11f9…`, not the shipped
`0e0e302d…`. It also found that evaluate.py changed between e1 and s1 (`4a2a4018…` → `3e26516b…`) without a
declaration. The old bytes cannot be recovered. So every stage was rerun once under declared, pinned bytes:

- `PREREG_AMENDMENT_2.md` (sha256 `10b55ca013b341afb4e8fe11cde30114e56df095449d63da63b560a0cf7dcf90`) was written
  and hashed into FREEZE.log before the reruns. It fixed the outcome rule in advance: the rerun replaces the
  original, with no choice between them.
- `CODE_PIN.json` (sha256 `06b7bfb0e788780da0c2d0e5f5710af11832351fa72a4e1dcb221f1b4f73ee3a`) pins
  `engine/calibration_sparse_weighted.py` = `0e0e302d05f0d78fa758ab69b433e1559ab77f6ee081d0daa1bdbf23e01c8682`
  (the shipped module) and `evaluate.py` = `f7e2bd9441c2c9fc4a007606e16ae3e9f82e6d2fcb4aa73080c9df84fcfe4abd`.
  evaluate.py now refuses with exit 2 (`code_hash_mismatch`) if a pinned file differs or the pin is missing. That
  refusal is the only change from the audited `3e26516b…`. It also records the pin and amendment hashes in RUNS.log.
- RUNS.log records 5–8 hold the reruns (baseline, e1, s1, attrition), all exit 0, under the pinned bytes.
  **Every rerun output is byte-identical to the original:** baseline.json `6e1dfc39…`, e1.json `6f2718b1…`,
  s1.json `04d2bd64…`, verdict.json `05c9f7f4…` and attrition.json `444a5a70…`. So the unrecoverable edits did
  not change any published number. Every number below is now tied to the shipped code.

## 1. Decision

Under the precedence coded in evaluate.py before any run:

1. F0 false → REJECT.
2. K1 false → REJECT.
3. K2 false → REJECT.
4. K3 REJECT → REJECT.
5. K3 INSUFFICIENT_DATA, or F0 unknown → INSUFFICIENT_DATA.
6. Otherwise → KEEP.

`verdict.json` (sha256 `05c9f7f4fbf4036a63ba5e2092dc235cb4d708f7db99505e0dd7014aa845b3c1`):

```
{"verdict":"REJECT","reason":"K1 failed","f0_crosscheck_clear":true,"k1":false,"k2":true,
 "k3":"INSUFFICIENT_DATA","outcome_calibration":"INSUFFICIENT_DATA"}
```

| Falsifier | State | Evidence |
|---|---|---|
| F0 (reference defect) | CLEAR | The module's native weights match `lib.flow_score.uniqueness_weights_nyse_intervals` with max abs diff 0.0, on 1,636 (0_7) and 719 (8_90) eligible real rows. 7/7 focused tests pass. |
| K1 (R_alt operating characteristics) | **FAILED** | 2 of 48 supported cells exceed the 0.10 bar (table below). |
| K2 (draft gate feasibility vs R_alt) | HOLDS | R_inc reached ≥ 50% support in **no** grid cell for either bucket. R_alt reached it at T=252 (H=5) and T=756 (H=21). |
| K3 (E1 gate ratio on retained data) | INSUFFICIENT_DATA | 0_7 has a 1-session window, so the train/test split is not computable. 8_90 has a 2-session window (see §3). |
| OUTCOME_CALIBRATION | INSUFFICIENT_DATA | Two inputs are missing. (i) No FS-4 model artifact or predictions are present (`data/flow_signals/models` is R2-only and forbidden here). (ii) No FS-5 `calibration_eval` partition receipt exists. |

## 2. S1 simulation (synthetic labels only; `s1.json` sha256 `04d2bd6401b0108a3a1fc4d6ce3f8395157f6dcf2946f6e7bd4c5e6bee3036b1`)

**Grid.** 200 replicates per cell, bootstrap R = 299 and block = H.

- **Power.** At the largest T, R_alt FAILs T1 (overconfident) and T2 (shifted) in 199–200 of 200 replicates. It
  PASSes T0 (calibrated) in 193–198 of 200.
- **False kill (T0).** At most 0.015 in every supported cell. The worst cell is H=5, T=252, bursty, at 3/200.

**K1 failures.** Both are R_alt false reassurance under T3, the local reversal `π = p − 0.15` on p ∈ [0.55, 0.75]:

| Cell | R_alt PASS / FAIL / NO_VERDICT | False reassurance | Wilson 95% | Mean true gap |
|---|---|---|---|---|
| H=5, T=1260, T3 steady | 21 / 102 / 77 | **0.105** | [0.070, 0.155] | 0.036 |
| H=21, T=1512, T3 steady | 21 / 15 / 164 | **0.105** | [0.070, 0.155] | 0.036 |
| (next worst) H=5, T=504, T3 steady | 17 / 11 / 172 | 0.085 | [0.054, 0.132] | 0.036 |

**Disclosures (they do not change the verdict):**

- **The bar is a point estimate, with no multiplicity control.** K1 is a per-cell point-estimate bar (§7), applied
  to 48 supported cells with no multiplicity correction, as frozen. Each failure exceeds it by one replicate in
  200, and both Wilson 95% intervals [0.070, 0.155] include 0.10. The one-sided binomial p-value of 21/200 against
  a true rate of 0.10 is 0.44 per cell (Bonferroni over 48 cells: 1.0). **So the K1 failure is not statistically
  significant, before or after multiplicity.** REJECT stands because the prereg froze a point-estimate rule and no
  rule is changed after seeing outcomes. It must not be read as significant evidence that R_alt gives false
  reassurance above 0.10.
- **The T3 steady gap is below the ECE bar.** Under T3 steady, the mean true weighted calibration gap is 0.036, which
  is below the 0.05 ECE bar. The prereg defines T3 as miscalibrated, so a PASS counts as false reassurance. Part of
  this failure is therefore a property of the frozen 0.05 implied-ECE threshold. The other part is the
  misfit flag's low power for a local dip at intermediate T.
- **R_alt is non-monotone in T under T3 steady.** At H=5, PASS goes 3 → 17 → 21 at T = 252 / 504 / 1260. At H=21,
  PASS goes 9 → 21 → 4 at T = 756 / 1512 / 4536. The global line absorbs the dip before the simultaneous band is
  tight enough to flag it.
- **T3 bursty.** Informative selection puts more mass in the dip (gap 0.061), and the rate stays at or below 0.02
  in every cell.
- **R_pool shows shrinkage-created reassurance, as H-S1 anticipated.** At H=21, T=4536, T3 steady, R_pool PASSes
  61/200 (0.305) while R_alt PASSes 4/200. The de-escalate-only law held: the proposed decision never exceeded R_alt's
  PASS count. For example, at H=21, T=756, T3 bursty, it lowered PASS from 4 to 2.
- **Requirement 2: Kish is not a dependence count.** Kish N is reported separately and is far larger than the
  native effective N. For example, at H=21, T=4536, Kish is 13,377 while Σw is 207 and there are 216 anchor blocks.
- **Requirement 4: the error report has no gaps.** The binned and implied ECE, with 90% intervals, were produced in
  200/200 replicates of every cell. That includes the 8 H=21, T=252 cells, where no rule has support (Σw ≈ 12.4 < 30).
- **R_inc never reached support.** This includes cells whose mean Σw is 207–211, above the 200 total floor. The
  per-replicate reason codes were not persisted in s1.json. The likely binding constraint is the per-bin floor:
  10 whole-tie bins × 20 = 200 leaves almost no slack on a 19-value tie grid. This is an inference, not a measurement.

## 3. E1, the one empirical comparison (`e1.json` sha256 `6f2718b11648b9390975d191bd63eebe32d286bbeabdfeace0349b717d8f797c`; geometry only, no outcome column read)

Inputs are macro-main data at vintage `cdab6268`, read-only:

- `ledger.parquet` `c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62`
- `grades.parquet` `3bb26d6440f262c2f8bac7cfd23313b466ce00091a397a17684cc8cc073e1d32`
- `gate.json` `92eec77adb20de9e8599435fda221a361fa24c8d4d7a6ddef99ce453a0f64682`

| Bucket | Cohort rows | Eligible rows | Window (fill sessions) | ρ (= cap) | G_inc / G_alt state | K3 |
|---|---|---|---|---|---|---|
| 0_7 (H=5) | 49,564 | 1,636 | 2026-09-28, 1 session | 1.00 | NOT_YET_ESTIMABLE / NOT_YET_ESTIMABLE | not computable (empty train window) |
| 8_90 (H=21) | 40,092 | 719 | 2026-09-03..09-04, 2 sessions | 0.523 | NOT_YET_ESTIMABLE / NOT_YET_ESTIMABLE | Q = 1.0; ratio fails literally; projection interval intersects [0.5, 2] |
| 90p | 0 | 0 | — | — | EMPTY | — |

**Degenerate-window disclosure.** Taken alone, the 8_90 ratio fails K3 (Q = 1.0 < 2). That number is an artifact
of a 2-session window.

- At T = 2, the rate cap is `(1 + 21/2)/22 = 0.523`. At that rate, both 200/ρ (383) and 30/ρ (57) fall below the
  20H block floor of 420 sessions, so both gates project to 420 and Q = 1.
- At the long-run cap of 1/22, the same formula gives T_inc = 4,400 and T_alt = 660, so Q ≈ 6.7.

The precedence coded before the e1 run resolves the aggregate K3 to INSUFFICIENT_DATA, because 0_7 is not computable.

**The E1 split has no embargo, and it does not need one.** The PREREG §10 chronological split masks on fill
position only, so a train unit whose interval ends up to H sessions inside the test window is kept. E1 reads
geometry columns only and no outcome column. The split tests how well the support accrual rate projects forward.
It is not an outcome-prediction split, so no label can leak through it. The split is unchanged, as frozen.
The verdict is REJECT on K1 in any case.

**Attrition (PREREG_AMENDMENT.md, a descriptive stage with no verdict effect; `attrition.json` sha256
`444a5a707d5a612d531b39e89fce8cc276728c97594fcc0a8cb18e4ecb7a3006`).** The e1 counter
`step4_end_missing_pending` is a misnomer for most of its rows: they are `graded_ok`, but
`outcome_end_session_H` is null.

- **0_7:** 47,910 graded_ok rows have no end boundary. Their event sessions run 2026-07-13..09-24
  (Jul 33,134 / Aug 5,252 / Sep 9,524). Only the 1,636 rows from session 09-25 (fill 09-28) carry it. 18 rows have
  `no_price_data`.
- **8_90:** 30,633 graded_ok rows have no end boundary (sessions 07-13..08-31). 719 rows carry it (sessions
  09-02..09-03). 8,700 rows are `not_yet_matured` and 40 have `no_price_data`.

**Exact missing input for E1.** The first gap is the `outcome_end_session_H` boundary in `data/flow_signals/grades.parquet`
for those 47,910 (0_7) and 30,633 (8_90) graded_ok rows. The column exists only on the most recently graded rows, so
older rows were not backfilled.

A complete backfill would still give only about 2.5 months (≈ 53 sessions) of retained geometry. That is below:

- the 20H block floor: 100 sessions for H=5, 420 for H=21
- the S1 R_alt support point: 252 / 756 sessions

So the second missing input is calendar time: an eligible fill window of at least 20H anchor blocks. The draft gate
never reached support on the grid even at 1,260 sessions (H=5) and 4,536 sessions (H=21), i.e. 5 and 18 years.
Under the native law that is decades-long infeasibility at the current cohort shape (requirement 3).

**Baseline (`baseline.json` sha256 `6e1dfc3974b429029ebd522871e0733dbf3896d9f3c99d197a5a733c6d80098d`).** Reproduced: `train_bucket` returns
`CALIBRATION_INSUFFICIENT:weighted_bin_method_unavailable` with `ece=None`, `scoring.enabled: false`, and no models
directory.

## 4. Method review of PR #8385 (Opus 5.5)

The review was read from #8385 head `0234ea19cb8fee75750f8c387b2fe4a3cf358a25`, sampled once (see DEVIATIONS in the
PR body). The draft's direction is sound:

- whole-tie bins
- native weights kept fixed inside resamples
- an anchor-session circular block bootstrap
- a max-statistic monotonicity test
- refusal on low support

Five clauses are under-specified. Each needs exact text before ratification, whatever support gate is chosen:

| # | Open clause | Finding | Q06 test evidence |
|---|---|---|---|
| A1 | Ties | "Equal-mass bins" are undefined when a tie group straddles a quantile. Q06 specifies an exact contiguous DP on whole-tie groups: minimise Σ(W_j − W/B)², B = min(10, G), lexicographically smallest cut vector on equal cost, and refusal (not a silent fallback) when the floor is infeasible. | req1 (DP optimal vs brute force; tie-break; B = min(10, G); infeasible → None) |
| A2 | Unequal weights | Weighted ECE, Brier and rates must use the frozen native uniqueness weights. Zero-weight rows are dropped and counted. They are neither a measured zero nor an empty cell. Negative or non-finite weights are refused. | req1, req5 (brute-force oracle ≤ 1e-12; inputs never mutated) |
| A3 | Empty cells | An empty bin cannot form, because bins carry exact positive weight sums. Support has four distinct states: UNKNOWN (no weights), EMPTY (no rows), MEASURED_ZERO (rows, zero weight) and MEASURED. A replicate in which any bin has zero resampled weight is invalid, not zero-error. | req1, req2, req4 |
| A4 | Monotonicity tolerance | The draft names no point tolerance. Q06 reuses the incumbent `is_reliability_monotone` default of 1e-3 (inclusive) as the point check, and the max-statistic bootstrap as the inferential test. A test with zero valid replicates returns undetermined (None), never "not broken". | req1 |
| A5 | Support counting | Support must be counted as native Σw plus anchor blocks `floor(T/H)`. Kish N is a weight-concentration index and must never be used as a dependence count. | req2, s1.json Kish vs Σw |

**Support gate (draft example: 200 total, 20 per bin).** Under the native law, ρ ≤ (1 + (L−1)/T)/L, so the draft
gate needs about 200·L anchor sessions at a minimum. In S1 it was never met on the grid. In E1 the current retained
geometry is 1–2 sessions per bucket. The gate is therefore an indefinite `NOT_YET_ESTIMABLE` at the current cohort
shape.

That outcome is honest, but it is a ratifier's choice, not a statistical necessity. The alternative Q06 tested, a
continuous logistic recalibration at the FS-3 §7 floor of 30, failed K1 narrowly on a local reversal. **It is not
recommended as a replacement gate.**

## 5. Review states (requirement 6; three separate fields, none derived from another)

| Item | opus_recommendation | statistical_acceptance | fable_ratification |
|---|---|---|---|
| A1–A5 clause text (PROPOSED_AMENDMENT.md §A) | PROPOSE_AMENDMENT | NOT_REVIEWED | UNRATIFIED |
| R_alt as a replacement support or decision gate | RECOMMEND_REJECT | NOT_REVIEWED | UNRATIFIED |
| Q06 research reference overall | RECOMMEND_REJECT (frozen K1) | NOT_REVIEWED | UNRATIFIED |

The exact amendment text for the ratifier is in PROPOSED_AMENDMENT.md.

## 6. Limitations

- **Simulation fidelity.** S1 is synthetic: a Gaussian-copula window shock, a 0.05 prediction grid and two
  regimes. It is not a model of real FS-3 score distributions, which do not exist yet.
- **Bootstrap size.** The simulation bootstrap is R = 299 instead of the draft's 9,999, for compute. Quantile noise
  at R = 299 is a plausible contributor to a one-replicate exceedance. It was not tested. The custody rerun used the
  same frozen R and seeds, and no rerun with a larger R was made.
- **E1 power.** E1 rests on 1–2 sessions of eligible geometry per bucket. It shows feasibility state, not a
  measured long-run accrual rate.
- **Inclusive support.** The cohort excludes only SPY, so support is an upper bound on any `calibration_eval` share.
- **Untested remedies.** Any remedy for K1, such as a stronger local-misfit flag or a threshold on the misfit
  magnitude, needs a fresh preregistration. Tuning it on these S1 outcomes would be outcome audition
  (DNR:KILL-OUTCOME-AUDITION).
- **Independent review is limited.** One independent read-only audit returned PASS_WITH_FIXES. The fixes are in §0.
  That audit is not the ratifier's statistical acceptance, so `statistical_acceptance` stays `NOT_REVIEWED`.
- **Restrictions preserved.** No LLM originates any signal or score (DNR:KILL-LLM-ORIGINATION). No fused composite,
  positioning fusion, regime scorecard, reliability monitor or causal DAG is built (DNR:KILL-FUSED-COMPOSITE,
  DNR:KILL-POSITIONING-FUSION, DNR:KILL-REGIME-SCORECARD, DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR,
  DNR:KILL-CAUSAL-DAG-ALPHA). The held FINRA/crowding families are untouched (DNR:HOLD-PSS-AF1-FINRA,
  DNR:HOLD-PSS-CD1-CROWDING).
