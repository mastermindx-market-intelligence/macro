# Q17 — Stable factor whitening under collinearity and missing observations: pre-registration

Status: written and frozen BEFORE any evaluation outcome was computed. The only run so far is
`baseline_repro.py`, which reads support only: row counts, per-leg coverage, complete-case
counts and fallback eligibility. It also checks the incumbent restatement on synthetic
controls. It computes no whitening error, transform drift, instability or return
(RUNS.log record 1).

Never edit this file after the FREEZE.log entry. Later changes go only into
PREREG_AMENDMENT.md, written before any new outcome is read.

## 0. Question

The incumbent is `engine/factor_orthogonal.orthogonalize`, the symmetric (Löwdin) whitening
that Macro applies to its additive equity factor legs before the equal-weight composite
(consumers: `scripts/factor_ic_scorecard.py`, `scripts/stock_conviction_phase0.py`). It has
three weaknesses:

- It estimates the correlation matrix from **complete-case** rows only.
- It floors eigenvalues at **1e-6**, which allows up to 1000x amplification of a direction.
- It **zero-fills** missing legs, so a partially measured row comes out looking fully
  measured.

The challenger, `engine/factor_stable_whitening.stable_whiten`, makes four changes:

- available-case pairwise correlation
- PSD repair
- frozen elementwise Ledoit-Wolf-type shrinkage toward I
- an eigen floor of 0.05 (maximum amplification 4.47x)

It also fills missing legs by conditional expectation and returns explicit
measured/partial/unmeasured row status.

Question: on Macro's real point-in-time factor cross-sections, is the challenger's fitted
transform materially more stable month to month, without losing out-of-time decorrelation
or coverage?

This is a numerics and diagnostic question. It is not an alpha, weighting or ranking
question.

## 1. Non-duplication

Incumbents and exclusions that touch the brief (assessment EXCLUSIONS_AND_DEPENDENCIES,
line 16 Factor Atlas and line 36 Dependence; repository DNR registry):

| Incumbent / exclusion | What it owns | Relation Q17 stays inside |
|---|---|---|
| `engine/factor_orthogonal.py` (orthogonalize, orthogonal_composite, overlap_diagnostics) | Production additive factor whitening | Q17 restates it only to reproduce it (diff ≤ 1e-10) and compares against it. Q17 does not edit or replace it, and nothing imports the new module. |
| Factor Atlas (#8680 S1, #8677 capital pressure, parallel Session 4) | Membership, index, rebalance, capital-pressure/BVC, catalyst graph | Out of scope. Line 16: "Q17 only challenges existing additive factor-whitening numerics." Q17 builds no membership, index, catalyst or capital-pressure object. |
| R-ORTH program (#1739, RUL-ORTH-1..8) and `DNR:KILL-OOS-DECAY-ORTHOGONALITY` | Orthogonality null law. A raw out-of-sample off-diagonal "decay" is a noise artifact. | Every off-diagonal statistic is reported as an **excess over the independent-column null** sqrt(2/(π(n−1))). Q17 does not re-claim OOS decay as a finding. |
| Q08 return-covariance estimation (line 36 Dependence) | Covariance of returns | A separate estimand. Q17 whitens the cross-section of factor legs within one month and does not estimate return covariance. It is not a second covariance owner. Q17 comes after Q08 in the dependency chain; it uses only the incumbent's own factor inputs, and the dependency is recorded as a limitation. |
| Composite / live ranking (`engine/equity_factors.py` composite, conviction scorecards) | Factor weights and ranks | No weight is chosen, no rank or gate is changed, and no forward return is read (`DNR:KILL-OUTCOME-AUDITION`, `DNR:KILL-FUSED-COMPOSITE`). |
| Other "whiten" code in the repo (marketing chart, lead-lag prewhitening, dispersion test, treasury PCA, canada_factor_beta, DISP_EIGEN) | Unrelated estimands | Not touched or compared. |

Standing kills respected: `DNR:KILL-OUTCOME-AUDITION`, `DNR:KILL-LLM-ORIGINATION`,
`DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-REGIME-SCORECARD`.

## 2. Estimand, unit and clocks

- **Unit:** one month-end point-in-time cross-section of the incumbent factor table,
  produced by `engine.equity_factors.compute_factors(asof=d, universe="broad")`. The
  table is rounded to 3 decimals by the incumbent.
- **Input clock:** `d` is the last trading day of each calendar month in the retained close
  panel. Fundamentals and EPS are as-of `d` through the incumbent's own PIT path, and
  closes run up to `d`. The final calendar month is dropped when its last bar is not a
  month end.
- **Output clock:** the transform W_t is fitted at d_t and applied to the cross-section
  at d_{t+1}, the next month end (a one-month out-of-time horizon).
- **Estimand:** for each method m ∈ {incumbent, challenger}, the month-to-month stability
  of the fitted whitening matrix W_t^m and its out-of-time decorrelation, on a fixed leg set.

## 3. Cohort and source vintages

- **Cohort:** every ticker in the incumbent broad table (breadth + midcap + smallcap
  constituents) with at least one measured leg. Current constituents are used, so the
  cohort is survivorship-biased; this is a stated limitation.
- **Data root:** `/Users/chriswong/Documents/Cluade/macro-main/data`, read-only, vintage
  cdab6268.
- **Input sha256 at freeze** (re-hashed by every run, which refuses on any change):

| Input | sha256 |
|---|---|
| data/edgar/fundamentals_panel.parquet | 9af85734e4e3ca64500aba8c61e3b5a7080e15f9912beba150e1bafd8b8bebc4 |
| data/edgar/eps_quarterly.parquet | 0330aa2e6f7518abdcad1e3ad063558480adaae6d6bbe6c6475efda6a307be9a |
| data/breadth/_closes_cache.parquet | ad37acc0a0d4881f7f3f777c247d3b68d6e395ec351cddd90684aa5862e27ae3 |
| data/midcap_breadth/_closes_cache.parquet | 5b7d0ab221fe9c04ea24401fe94a45e2caf6eda9ced250a538c743378c5db920 |
| data/smallcap_breadth/_closes_cache.parquet | eb40492c9f7dbb8a1ffc3ef353fcee281515630122abbe180223118d225c9135 |
| data/yahoo/SPY.parquet | 6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152 |
| data/breadth/constituents.parquet | ecdd7e77ac36198b45c4ff6b854e7a46281bd3504d82540853f29c09a1f64aaf |
| data/midcap_breadth/constituents.parquet | 0527370c62ee9a805228873bbaecd8bf8e33d86c18f28877a36b07fe70f2af5f |
| data/smallcap_breadth/constituents.parquet | c7461d5d2931ad0b746cd99206f63dd46a13d260c965ffa7c81029cab27ffd2e |
| config.yml | b8963682e5f2fe209cee1a604f19e51bbce232992d75c0b26c60a615600a310f |
| engine/equity_factors.py | 084745c4a6d5e42a01a04a49407a98300bf1cbbacc229aaceb51913a5ebcd681 |
| engine/factor_orthogonal.py | c0662c0aee92a337ba94ed98d03fb1a7c6d5ffe18f077711a692b6a084701f23 |
| engine/sue.py | 26ca53977e87ac00bef6593c6fd520802604f98bef55c41740467f63f081974c |
| lib/closes_panel.py | 70bc2c1bb6a15dc677e88c12ee78b1c492afb2bbf75846860cf9d13fc6518496 |
| lib/store.py | f69c9171babfb4453c10c9edab9b2b206ef86abd2e328637fcae61569753b61d |
| collectors/edgar.py | d6e3be060fc7ade17e31551795f25806ac414fe5ec7988c31039acc9c7dbba7c |
| collectors/edgar_eps.py | b1c7e02997ee41184994df618178eccd1179abcfa156ed8c118f5aadfb8efb50 |
| engine/factor_stable_whitening.py (normalized) | ac6d5098735f1616428b9c9fe9851b7584514e0939206e4ad78f7a18abf18cc7 |

The challenger module is frozen. The only edit permitted after the freeze is replacing
the docstring token `(recorded verdict: __VERDICT__)` with the verdict word.
`evaluate.py` hashes the module after normalizing that token back to `__VERDICT__` and
refuses on any other change.

Observed support, from the support-only pass:

- 37 month ends, 2023-09-29 … 2026-09-30, with about 1494–1529 rows each.
- `low_vol` has 0% coverage before 2024-04-30.
- `profitability` is below 50% coverage on every date.
- `sue` drops to 46.6% coverage on 2026-05-29.
- On the coverage-≥50% legs, complete-case rows jump from about 680–707 to about
  1034–1087 at 2025-10-31: a support-composition shift.
- The incumbent never falls back on these dates.

## 4. Leg set and chronological split (decided in training only)

- **Dates:** the 37 month ends in order, indexed 0..36.
- **Train:** the first floor(0.4 × 37) = 14 dates (indices 0..13).
- **Test:** indices 14..36 (23 dates). There is no gap rule because no label horizon
  exists. A pair is used only when both of its months are test months.
- **Leg-set rule (training only):** take the legs of the incumbent `FACTOR_LABELS` set
  {value, profitability, quality, investment, payout, low_vol, low_beta, short_interest,
  accruals, sue} that are present with coverage ≥ 0.50 on **every** training date. That
  set is then held **fixed** for every test month, so W_t and W_{t+1} live on the same
  legs. From the support pass this is expected to be {value, quality, investment, payout,
  low_beta, accruals, sue}, with p = 7; `low_vol` is excluded because it is absent before
  2024-04. The rule, not this expectation, governs: evaluate.py computes it from training
  dates only and records it.
- **Coverage dips stay in the test:** a test-month coverage dip (sue on 2026-05-29) is
  kept and is part of the missing-data stress being tested. Neither method drops a leg.
- **Hyperparameters:** no tuning anywhere. The challenger's constants (EIG_FLOOR 0.05,
  the frozen shrinkage formula, support rule max(30, 3p)) were fixed in the module before
  this freeze. The incumbent is used exactly as written (1e-6 floor, complete case,
  zero fill). Training data choose only the leg set. All preprocessing is within one
  cross-section (each month's z-scoring uses that month only).

## 5. Metrics

Notation:

- Z_t is the available-case z-scored (ddof 0) leg frame at month t.
- C_t is the subset of rows with all p legs measured at t.

For each test month t, fit W_t^inc (incumbent: complete-case corrcoef, eigenvalues
floored at 1e-6, inverse square root) and W_t^stb (challenger: `estimate_correlation` →
`whitening_matrix`).

For each adjacent test pair (t, t+1), 22 pairs in all:

- **M2 — transform drift (primary).** D_t^m = ||W_{t+1}^m − W_t^m||_F / ||W_t^m||_F.
- **M1 — out-of-time whitening error (guardrail).**
  - E_t^m = mean |offdiag corr( Z_{t+1}[C_{t+1}] · W_t^m )| − sqrt(2/(π(|C_{t+1}| − 1))).
  - This is the excess over the independent-column null (`DNR:KILL-OOS-DECAY-ORTHOGONALITY`).
  - Both methods are scored on the same rows C_{t+1}.
- **M3 — applied maximum amplification (descriptive).**
  - Incumbent: 1/sqrt(max(λ_min, 1e-6)) of its correlation matrix.
  - Challenger: `applied_max_amplification`.
  - Also reported: the raw minimum eigenvalue, the shrinkage intensity and floor binding.
- **M4 — coverage and labelling (guardrail).**
  - Coverage^m_t: the share of month-t rows that receive a finite output on every leg.
  - Also counted: the rows emitted with values on every leg while partially measured.
  - The incumbent zero-fills, so every partial row is presented as complete. The
    challenger emits a row_status label.
- **M5 — within-cross-section output instability (descriptive).**
  - `bootstrap_instability(frame, method=m, n_boot=50, seed=t)`.
  - Reported per test month: output_rel_change_median and the output_unstable flag.
- **Secondary (descriptive only, no decision):** the in-sample residual mean |offdiag|
  excess of each method's own full output, using each method's own fill rule.

## 6. Hypotheses, practical bar, decision and falsifier

**H1 (single primary hypothesis).** The challenger's transform drifts materially less
than the incumbent's, at no material cost.

Primary statistic: R = mean_t D_t^stb / mean_t D_t^inc over the 22 test pairs.

**KEEP** requires all three of:

1. R ≤ 0.80, **and** the moving-block bootstrap 95% percentile interval for R has an
   upper bound below 1.00.
2. The M1 guardrail: mean_t (E_t^stb − E_t^inc) ≤ +0.01, in absolute correlation units.
3. The M4 guardrail: the mean challenger coverage is at least the mean incumbent coverage
   minus 5 percentage points.

**REJECT** (falsifier): any of conditions 1–3 fails.

**INSUFFICIENT_DATA:**

- fewer than 12 valid test pairs, or
- either method falls back (support rule unmet) in more than 20% of test months, or
- the leg-set rule yields p < 2.

In that case the verdict names the exact missing input.

The M3, M5 and secondary metrics do not change the verdict. They are reported for
interpretation, including where the challenger's floor leaves residual correlation.

## 7. Uncertainty (dependence-aware) and honest N

- Adjacent pairs overlap: W_{t+1} enters pairs t and t+1. Uncertainty for R and for the
  M1 difference therefore comes from a **moving-block bootstrap** over the ordered 22
  pair indices.
- Block length 3, 2000 replicates, seed 17. Each replicate recomputes both R and the M1
  difference from resampled pairs.
- The 95% percentile interval is reported.
- Honest N: 22 test pairs and floor(22/3) = 7 non-overlapping blocks. That is about 7
  effectively independent units; the text reports it as such.
- Cross-sectional size (about 1500 names) is **not** the N of the comparison.

## 8. Trial family, outcome windows and stop rule

- **Trial family:** `Q17-whitening-numerics`. There is one trial: one challenger
  configuration against one incumbent, with one primary statistic.
- **No forward-return outcome window exists.** The only "outcome" is the next month's
  cross-section (the one-month output clock). `TRIAL_BUDGET_CHARGE = 0` because no
  alpha, rank or gate is tested.
- **Stop rule:** evaluate.py is run **once** against the frozen hash, with no repeated
  holdout search, no alternative floors, no alternative leg sets and no alternative
  splits after outcomes are seen. A run that raises before writing any metric may be
  re-run only after a PREREG_AMENDMENT.md records the defect and the fix, with its
  sha256, before the re-run. The fix may not alter metric or decision logic.
- **Attrition and support reporting:**
  - per test month: rows, complete rows, partial rows, per-leg coverage, pairwise minimum
    support and method status
  - the 2025-10 complete-row jump and the 2026-05-29 sue dip are called out explicitly

## 9. Baseline competitors

1. The incumbent orthogonalize, the production default. Its restatement is reproduced to
   ≤ 3.7e-13 on four synthetic controls (RUNS.log record 1).
2. Implicitly, "no whitening" (W = I, zero drift), reported only as the drift floor
   context. It is not a competitor for KEEP, because it does not decorrelate.

## 10. Known limitations recorded before outcomes

- **Survivorship:** the universe is current constituents.
- **Rounding:** the incumbent table is rounded to 3 decimals.
- **Q08 dependency:** this brief uses incumbent factor inputs rather than a Q08 return
  covariance.
- **Short sample:** 23 test months, about 7 honest blocks.
- **Disabled side reads:** two display-only side reads (insider block, IC scorecard
  badges) are patched out, because they do not affect the factor table.
- **Config stand-in:** a minimal stand-in replaces the real `lib.config` so that no local
  dotenv file is loaded. The data root and config.yml are the same.
