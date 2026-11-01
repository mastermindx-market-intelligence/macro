# Q08 — Regularized covariance and uncertainty-aware independent-bet counts — PREREGISTRATION

Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), Q08 author lane.
Status: written BEFORE any evaluation outcome was computed or read. Frozen by
`FREEZE.log` (sha256 of this file + `date -u` timestamp). Any later change goes
only to `PREREG_AMENDMENT.md`, written before new outcomes are read.

What was looked at before writing this file (disclosed, not outcomes): the
column names, row count, date span, NaN pattern and complete-case row count of
the primary input (below); the incumbent code path; the module's synthetic tests.
No correlation, loss, participation ratio or contrast on the real data has been
computed.

## 1. Question

The incumbent factor block of `engine/neuralweb/covariance_spine.py`
(`_build_factors_block`) reports `effective_factor_bets_pr` — the participation
ratio (PR) of the plain sample correlation matrix of daily factor returns over
the trailing ≤252 complete-case rows — as an un-intervalled point number. Q08
asks:

1. Does a regularized correlation estimator (Ledoit-Wolf linear-to-identity,
   Ledoit-Wolf constant-correlation, or Ledoit-Wolf 2022 quadratic-inverse
   nonlinear shrinkage), fitted on training rows only, forecast the next block's
   realized correlation better than the incumbent sample estimator, out of
   sample, by a practically meaningful margin and with dependence-aware
   uncertainty that excludes zero?
2. Independently of (1): how wide is the dependence-aware uncertainty of the PR
   ("independent bets") — i.e. is a point PR defensible at all?

## 2. Non-duplication

Collision check (commands logged in `RUNS.log`):
`grep -rn "covariance_shrinkage" _base` → no hits; `engine/covariance_shrinkage_diagnostics.py`
and `tests/test_covariance_shrinkage_diagnostics.py` absent from `_base`.

Incumbents grepped (`ledoit|shrink|participation_ratio|effective.*bets|corrcoef`
over `_base/engine` and `_base/scripts`) and the narrow relation kept:

| Incumbent | What it owns | Q08 relation |
|---|---|---|
| `engine/neuralweb/covariance_spine.py::_build_factors_block` | the descriptive factor-block PR on `site/factordata/factor_series.json` | **the baseline**. Q08 reproduces its arithmetic and proposes estimator + interval + basis guard as a research reference. Q08 does NOT edit it, wire into it, or replace it. |
| `engine/risk_sizing.py` | book-risk approximation for sizing ("full Ledoit-Wolf cov is overkill here") | EXCLUSION — no sizing, no book risk. |
| `engine/dispersion.py` (`effective_universe_bets_pr`) | universe-level PR via SVD of standardized stock returns | EXCLUSION — different unit (stocks), not touched. |
| `engine/reflexivity.py` (`n_eff_participation_ratio`) | PR on a narrative-similarity matrix | EXCLUSION — not a return covariance. |
| `engine/pooling.py`, `engine/neuralweb/kernel.py` | hierarchical empirical-Bayes shrinkage of WEIGHTS/estimates | EXCLUSION — shrinks means/weights, not covariance. |
| `scripts/build_factor_panel.py` | Vasicek beta shrinkage | EXCLUSION — betas, not correlation. |
| `engine/personality_crowding_hazard.py` | frozen PSS-CD1 (DNR:HOLD-PSS-CD1-CROWDING) | EXCLUSION — untouched, not imported, no reference. |
| `engine/validation.py::newey_west_tstat` | HAC t-stat | REUSED in `evaluate.py` only as the HAC cross-check (in place of the Q18 brief, which is sequenced after Q08 and is not read). |
| Brief exclusions: #8664 cross-asset unknown-data display; Factor Atlas #8680/#8677; GMI network discovery | — | EXCLUSION — no display, no atlas, no network discovery, no allocation, no fused regime classifier (DNR:KILL-FUSED-COMPOSITE, DNR:KILL-REGIME-SCORECARD). |

Narrow relation: a pure research-reference module of correlation estimators,
validity checks, PR intervals and held-out losses for ONE incumbent number,
with no authority (no risk/gate/rank/sizing), nothing importing it.

## 3. Data, cohort, unit, clocks

* Primary input: `/Users/chriswong/Documents/Cluade/macro-main/data/breadth/_factor_legs.parquet`
  at macro-main vintage `cdab6268`, sha256
  `cc3476e61b50e8eda312b11393fa2231fde587a821d011a8dd58d32987fe94bd`.
  Repository-built daily long-short factor leg returns from retained local
  price data (no vendor download, no network). Read-only.
* Columns (cohort, fixed): `size`, `value`, `quality`, `low_vol` (N = 4).
* Basis `long_short`, unit decimal daily return, clock daily close. Declared via
  `SeriesSpec` and checked by `check_compatible`; a mismatch is a refusal.
* Unit of analysis: one 4×4 correlation matrix per evaluation block.
* Support: 777 rows; `low_vol` begins later, so complete-case rows = 626, with no
  interior gaps. Data end at the last available row (stale relative to today —
  a limitation, not fixed here).
* Input clock: the estimator at origin t uses rows [t−W, t) only (complete-case
  index). Output clock: the realized correlation of rows [t, t+21).
* Not used: `data/french/factors.parquet` (sha256 `7e16cc74…b47b57`) — inspected
  only for schema; reserved as possible future work, NOT a second test.
* Code vintages: `engine/neuralweb/covariance_spine.py` sha256
  `61a556894986e1c91d6dff8beffd21536a554b0e3a044eace6bd41e73d1705a3`;
  `engine/validation.py` sha256 `9680d00241fa58ccb504b679d1ee19d64b52b6f46b6bf87a5149969bc7ec4e3b`;
  `engine/covariance_shrinkage_diagnostics.py` sha256 at freeze
  `93fa59944845560797eb0d2826cd8c11a53acbb882275aa7108b2536380789f5`
  (after evaluation only the module docstring's VERDICT text may change;
  `evaluate.py` logs the module sha actually used).
* Procedure docs consulted (headings only, commit unknown): Mastermind
  `docs/sol_skills/INDEX.md` `608aebc8…ddfa220`, `ACTIVE_EXECUTION.md`
  `fb6a8910…ed0dc`, `SESSION_RELIABILITY.md` `817366c6…283076`.

## 4. Estimand and hypotheses

Estimand: the 4×4 correlation matrix of the next 21 trading days of daily
long-short factor returns (and its PR = (Σλ)²/Σλ²).

* Baseline (incumbent): `sample` — Pearson sample correlation of the trailing
  W = 252 training rows.
* Challengers (trial family, exactly three): `lw_identity`, `lw_constant_corr`,
  `lw_nonlinear`, each fitted on the same training rows; intensities are
  analytic functions of the training rows only (no tuning, no holdout search).
* H1 (per challenger c): E[D_k(c)] > 0 where D_k(c) = L_k(sample) − L_k(c).
* H0: E[D_k(c)] ≤ 0 for every c.

## 5. Losses, split, outcome windows

* Chronological rolling origins on the complete-case index: t_k = 252 + 21k,
  training [t_k−252, t_k), evaluation [t_k, t_k+21), k = 0..16 → K = 17
  non-overlapping evaluation blocks (357 evaluation days; the final 17
  complete-case rows are unused). Training windows overlap; evaluation blocks
  do not. No row of an evaluation block is ever used to fit its estimator.
* All preprocessing (standardization) and all shrinkage intensities come from
  training rows only. The realized block correlation is the sample correlation of
  the 21 evaluation rows (an evaluation-only transform, identical for every
  estimator).
* Primary loss: Gaussian/Stein loss `0.5·[tr(R̂⁻¹ C_k) + log det R̂]` (proper:
  minimized in expectation by the true correlation).
* Secondary loss: off-diagonal squared Frobenius distance `Σ_{i<j} (R̂_ij − C_k,ij)²`.
* Honest N = 17 distinct non-overlapping 21-day blocks (NOT 357 rows).

## 6. Dependence-aware uncertainty, effect bar, decision rule

* Primary: circular moving-block bootstrap of the 17 block contrasts D_k(c),
  block length 3, B = 10 000, seed 20261008 (an integer seed, not a date in
  logic). Two-sided Bonferroni interval over the 3 challengers:
  level 1 − 0.05/3 (percentiles 0.833 / 99.167).
* Cross-check (reported, not decisive): Newey-West HAC t on D_k(c), lag 3,
  via the incumbent `engine.validation.newey_west_tstat`.
* Practical effect bar: mean D(c) ≥ 0.005 nats per evaluation day on the Stein
  loss.
* **KEEP** a challenger iff ALL hold: mean D(c) ≥ 0.005; Bonferroni lower bound
  > 0; mean Frobenius contrast (baseline − challenger) ≥ 0. If several qualify,
  the one with the largest mean D is named. KEEP means "keep as a research
  reference estimator for the descriptive context number" — it confers no
  authority and wires nothing.
* **REJECT** otherwise (the falsifier): the regularized estimators do not beat
  the incumbent sample estimator by the bar; the incumbent estimator is
  preserved and only the PR-uncertainty diagnostic + basis/support guards are
  published as the research reference.
* **INSUFFICIENT_DATA** if K < 12 evaluable blocks, the basis/support checks
  fail, or any estimator is unavailable on more than 2 blocks.

## 7. Attrition and support reporting

Report rows_total, rows_complete, per-column missing counts, K, the number of
blocks where any estimator returned `unavailable` and why, and the number of
failed bootstrap resamples.

## 8. Non-decision readouts (descriptive only; cannot change the verdict)

1. Sensitivity: the same 17 evaluation blocks with a W = 60 training window
   (incumbent `_FACTOR_MIN_OBS`), same losses and bootstrap.
2. PR uncertainty: at each of the 17 origins, a stationary block bootstrap
   (mean block 10, B = 200, seed fixed) of the training rows for each estimator;
   at the final origin (trailing 252 complete-case rows) B = 1000, 90% interval.
   Report point PR, interval, width and failed resamples.
3. PR stability across origins: min/max/std of each estimator's point PR.
4. Incumbent reproduction: real `_build_factors_block` vs the module replica on
   the trailing 252 rows (expected exact equality to 4 dp).

## 9. Stop rule

One evaluation run. A rerun is allowed only after a crash, with identical
specification, and every run is logged in `RUNS.log`. No repeated holdout
search: no alternative windows, horizons, losses, block lengths or estimators
are tried for the decision. Any change requires `PREREG_AMENDMENT.md` before
reading new outcomes.

## 10. Prior expectation (stated so it can be checked)

With N = 4 and T = 252 (N/T ≈ 0.016) estimation noise in the sample correlation
is small, so the most likely outcome is REJECT: shrinkage gains are expected to be
tiny relative to non-stationarity of factor correlations between blocks. The
uncertainty of the PR is nonetheless expected to be material, which is the
part of Q08 that does not depend on the estimator contest.

## 11. Standing restrictions honoured

DNR:KILL-OUTCOME-AUDITION (single pre-declared contest, no audition of
outcomes), DNR:KILL-LLM-ORIGINATION (no language model originates any number),
DNR:KILL-FUSED-COMPOSITE, DNR:KILL-POSITIONING-FUSION, DNR:KILL-REGIME-SCORECARD,
DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR, DNR:KILL-CAUSAL-DAG-ALPHA,
DNR:HOLD-PSS-AF1-FINRA, DNR:HOLD-PSS-CD1-CROWDING — none touched.
