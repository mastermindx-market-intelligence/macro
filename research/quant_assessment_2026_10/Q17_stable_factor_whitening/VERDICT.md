# Q17 — Stable factor whitening under collinearity and missing observations: VERDICT

**VERDICT: REJECT**

This follows the frozen rule in PREREG.md §6. Primary condition 1 fails narrowly:
R = 0.809, and the bar is R ≤ 0.80. Guardrails 2 and 3 pass. The challenger module
`engine/factor_stable_whitening.py` stays a **research reference — not wired**. The
incumbent `engine/factor_orthogonal.orthogonalize` is unchanged, and nothing imports the
new module.

## What was compared

- **Incumbent:** `factor_orthogonal.orthogonalize`. It uses the complete-case
  correlation, floors eigenvalues at 1e-6, and zero-fills missing legs in z-space.
- **Challenger:**
  - available-case pairwise correlation
  - PSD repair
  - frozen elementwise Ledoit–Wolf-type shrinkage toward I
  - eigenvalue floor 0.05
  - conditional-expectation fill of missing legs
  - a row_status label on every row
- **Data:** 37 month-end cross-sections (2023-09-29 … 2026-09-30) of the incumbent's
  own broad factor table. Licensed retained data was read only, at vintage cdab6268, and
  every input sha256 is recorded in PREREG.md §3 and RUNS.log.
- **Split:** chronological.
  - Train: 14 months (2023-09-29 … 2024-10-31). Training chose only the leg set.
  - Test: 23 months (2024-11-29 … 2026-09-30), giving 22 adjacent pairs.
  - No hyperparameter was tuned.
- **Leg set:** {value, quality, investment, payout, low_beta, accruals, sue}, p = 7.
  - Computed from training dates only, and it matches the pre-registered expectation.
  - `low_vol` was excluded (absent before 2024-04) and `profitability` was excluded
    (coverage below 50%).

## Pre-registered decision (single run, RUNS.log record 2, exit 0)

| Condition | Statistic | Bar | Result |
|---|---|---|---|
| 1. Transform drift | R = mean D_stb / mean D_inc = **0.809**. Block-bootstrap 95% CI [0.725, 0.896]. | R ≤ 0.80 **and** CI upper < 1.00 | **FAIL** (point estimate 0.009 above the bar) |
| 2. Out-of-time whitening error (excess over the independent-column null) | mean(E_stb − E_inc) = **+0.0075**. 95% CI [+0.0043, +0.0094]. | ≤ +0.01 | pass |
| 3. Coverage | challenger 1.000 vs incumbent 1.000 | ≥ incumbent − 5pp | pass |

Uncertainty for R and the M1 difference comes from a moving-block bootstrap over the
22 ordered test pairs: block length 3, 2000 replicates, seed 17, percentile interval.

## Honest reading

- **The drift reduction is real but smaller than the practical bar.**
  - Mean transform drift fell from 0.0298 to 0.0241, a cut of about 19%.
  - The whole bootstrap interval is below 1, so the challenger is steadier
    month-to-month.
  - The pre-registered bar was a 20% cut (R ≤ 0.80), and the point estimate misses it.
  - No alternative floor, leg set or split was tried after seeing this (PREREG §8 stop
    rule).
- **The out-of-time error costs about +0.0075 in absolute correlation units.** This is
  inside the tolerance, but it is a real cost: the incumbent's mean excess is −0.0073
  and the challenger's is +0.0003.
  - Part of the cost is structural. M1 is scored on next month's complete-case rows,
    which is the same row set and estimator the incumbent fits on.
  - The challenger fits on all jointly observed pairs and is shrunk toward I by about
    2–3%.
  - The incumbent's negative excess (residual correlation below the independent-column
    null) shows that adjacent cross-sections share most names. They are not independent
    samples, so the null is conservative here.
- **The data were never ill-conditioned.**
  - The incumbent's raw minimum eigenvalue on the test months is 0.22–0.28.
  - Its applied amplification is 1.88–2.13, against the challenger's 1.86–1.97.
  - The challenger's 0.05 floor never bound in any test month, and no month was flagged
    unstable.
  - So the 1e-6 floor's 1000× amplification risk (MATH witness "Whitening") never
    materialized on this leg set. The challenger's protection is insurance that was not
    exercised.
- **Missing-data labelling is the clearest qualitative difference, and it is not part of
  the decision.**
  - The incumbent zero-fills and presents 12,457 partially measured test-month rows as
    complete.
  - The challenger labels every one of them `partial` and presents 0 as complete.
  - Both methods emit finite values on every leg for every cohort row, which is why
    coverage is 1.000 vs 1.000.
- **Drift spikes are support-composition events, and both methods show them.**
  - 2025-02-28→2025-03-31: complete rows on the fixed 7-leg set jump from 684 to 1071 as
    value/payout/low_beta coverage widens. Drift was 0.087 for the incumbent and 0.049
    for the challenger.
  - 2025-03-31→2025-04-30: drift 0.084 / 0.087, the one pair where the challenger is
    worse.
  - 2026-03-31→2026-04-30: drift 0.079 / 0.078.
  - The 2026-05-29 sue dip (complete rows 523) gave drift 0.053 / 0.030 into the dip and
    0.055 / 0.033 out of it. The challenger's available-case estimate is visibly steadier
    there.
  - PREREG §3 described the complete-row jump at 2025-10-31; that observation came from
    the support pass's date-varying ≥50% leg set. On the fixed training-chosen leg set,
    the jump is at 2025-03-31. This is recorded here, not re-analysed.
- **Descriptive M5** (within-cross-section bootstrap, median output relative change):
  incumbent 0.044, challenger 0.038. Neither method was flagged unstable in any month.
- **Secondary:** the in-sample residual off-diagonal excess (median) is −0.0021 for the
  incumbent and −0.0057 for the challenger. Both are at or below the noise floor.

## Honest N, attrition and support

- **N:** 22 test pairs, which is 7 non-overlapping blocks of 3, so about 7 effectively
  independent units. The roughly 1,500-name cross-section is not the N.
- **Attrition:** 0 incumbent fallbacks and 0 challenger fallbacks in 23 test months.
  All 22 possible pairs are valid.
- **Support (per test month, in `results/per_month.csv`):**
  - rows: 1511–1529
  - complete rows: 523–1087
  - challenger minimum pairwise count: 557–1104
- **Restatement:** the incumbent reference restatement matched `orthogonalize` to
  8.9e-15 on every test month.

## Limitations

- **Survivorship:** the cohort uses current constituents.
- **Rounding:** the incumbent table is rounded to 3 decimals.
- **Q08 dependency:** Q17 uses the incumbent's factor inputs, not a Q08 return
  covariance.
- **Disabled side reads:** two display-only side reads (insider block, IC scorecard
  badges) were patched out. They do not touch the factor table.
- **Config stand-in:** a minimal `lib.config` stand-in was used so that no local dotenv
  file is loaded.
- **Short sample:** 23 test months, about 7 honest blocks.
- **The M1 scoring rows favour a complete-case estimator** (see above).
- **No forward-return or alpha claim is made or tested** (`DNR:KILL-OUTCOME-AUDITION`).
- **Trial accounting:** one trial in family `Q17-whitening-numerics`, with
  `TRIAL_BUDGET_CHARGE = 0`.

## What would change this

- Only a new pre-registration would change it. A re-run of this one with a different
  bar would not.
- A plausible future question: whether a leg set that includes the thin legs
  (`profitability`, `low_vol` after 2024-04) is in fact ill-conditioned. That is where
  the challenger's floor and conditional fill would be exercised.
- That is a separate trial and is not authorized here.

## Evidence

- **RUNS.log record 1:** `baseline_repro.py`, exit 0. It ran the synthetic restatement
  controls (≤ 3.6e-13) and the real support pass.
- **RUNS.log record 2:** `evaluate.py`, exit 0. PREREG sha256 51c58c37…6fb0 matches
  FREEZE.log, all 18 inputs match the frozen table, and the input bytes and data listing
  were unchanged during the run. Runtime 230 s.
- **RUNS.log record 3:** `evaluate.py`, exit 0. This is the single re-run authorized by
  `PREREG_AMENDMENT.md` (sha256 bd513397…77a8, recorded in FREEZE.log before the
  re-run). It followed the independent-audit fixes to diagnostic code only: the unused
  composite helper was removed, the degenerate-aware amplified-subspace sine was added,
  and bootstrap support was matched to each method. The amended normalized module hash
  is 499f71fe…dbd3. Runtime 215 s.
  - The verdict and every primary, guardrail, attrition and honest-N number reproduced
    exactly.
  - `per_month.csv` and `per_pair.csv` are byte-identical to record 2.
  - `primary_results.json` differs only in three fields: the module hash, the new
    `prereg_amendment_sha256` field, and `runtime_seconds`.
- **Result files and their sha256** (record 3, also in RUNS.log):
  - `results/primary_results.json` bcc8b540afd923362fd72d87269af51502b4abe278db60a6e8d757df472a0b9c (record 2: faf3f6ac…5f8d)
  - `results/per_month.csv` 63f5db0077569ae39ba43850a9a66786faef5024073b4e14035058582349d461
  - `results/per_pair.csv` 60269729a8aca5f3c63ebd6ac744c9f2b75ceb32451c16fa7256b7e06c7dc482
