# Q15 — Microstructure-noise-aware realized variance: preregistration

Author: Opus 5.5 (model ID claude-opus-5-5), Q15 AUTHOR role. Research only: nothing is
wired, registered, scheduled, gated or promoted. Before this file was frozen, only the
schema, row count, dtypes and first/last timestamps of the input files were inspected.
No variance, return, autocorrelation, signature curve or label was computed on any
admitted data.

## 1. Question

Does a microstructure-noise-aware estimator, the non-flat-top Parzen realized kernel
(BNHLS 2008, L14), produce a more reliable weekly integrated-variance label than
fixed-interval realized variance on the only admitted intraday tape? That tape is
Coinbase BTC-USD hourly candles. Reliability is measured as the persistence the label
keeps after measurement error.

## 2. Non-duplication

The incumbent and collision check was run against the pristine snapshot `_base` (repo at
d252f919):

- **Command:** `grep -rliE "realized[_ ]kernel|bipower|pre-?averag|parzen|two[_-]scale|tsrv|signature[_ ]plot|microstructure noise" _base/{engine,scripts,lib,tests} --include=*.py`. It exited 0 with four hits, all incidental:
  - `scripts/basket_coherence_audit.py`: a comment saying "less microstructure noise".
  - `scripts/research/pss_f2_overnight.py`: prose about daily microstructure.
  - Two tests that match "two_scale" as a phrase about GEX/flow scales, not two-scale RV.
- **Command:** `grep -rlE "realized_variance|realised_variance" _base/engine --include=*.py` exited 1, with no hits.
- **Result:** no realized-kernel, pre-averaging, bipower, TSRV or signature-plot estimator exists in engine/scripts/lib.

Owners and seams:

- `engine/vol_forecast.py` (R04, blob e2354c5a): the incumbent equal-weight HAR-style daily close-to-close proxy. It is the **baseline** and is not modified. Its `forward_vol_ann` label is untouched. The labels produced here are separately versioned and are never spliced into its history (EXCLUSIONS volatility row).
- `engine/intraday_greeks.py`: intraday option-greek grids from option mids. It computes no realized variance, so there is nothing to reconcile beyond units. It is not modified.
- `engine/velocity.py`: a daily realized-variance velocity slope. That is a different estimand (a trend in daily RV); it is not duplicated.
- `engine/btc_intraday_cvd.py`: reads the same hourly tape for order-flow CVD. That is flow, not variance; it is not duplicated.
- **TP1 #8660** owns acquisition, NBBO and corrections. This brief captures no data, replays no NBBO and keeps no correction store. It reads only the already-retained Coinbase hourly parquet.
- **#8659** owns pressure-response. Not touched.
- **MAS-260** owns accepted variance/outcome studies and the accepted P5 estimator/ruler. These labels are `accepted_label=False` and replace nothing.
- **Q07** (daily-proxy volatility) and **Q16** (delayed calibration): sibling briefs, not read and not depended on. Changing the target estimator would change study identity, so nothing here feeds them.
- **DNR keys:** no standing kill or hold is touched. This is not an outcome audition (KILL-OUTCOME-AUDITION): one frozen comparison, no outcome search. It is not a fused composite or regime scorecard (KILL-FUSED-COMPOSITE, KILL-REGIME-SCORECARD, KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR). It involves no positioning or flow data (KILL-POSITIONING-FUSION, HOLD-PSS-AF1-FINRA, HOLD-PSS-CD1-CROWDING) and no causal DAG (KILL-CAUSAL-DAG-ALPHA). No language model originates anything (KILL-LLM-ORIGINATION).

## 3. Estimand and unit

- **Estimand:** the weekly integrated variance IV_w of the BTC-USD efficient log price over UTC week w. A week runs from Monday 00:00 to the following Monday 00:00 (168 hourly returns).
- **Units:** log-return squared. Not annualised, not percent.
- **Analysis scale:** the natural log of each weekly label.
- **Unit of analysis and honest N:** the distinct week. Rows (hours) are never counted as N.

## 4. Clocks

- **Input clock:** hourly Coinbase candles. The index is the candle-start epoch as naive UTC. The price is `close`, the last trade in the hour, observed at candle start + 1h. A return between two consecutive available candles is assigned to the week containing the later candle's start.
- **Missing hours:** a missing hour means no candle was published. The return across it is kept as one multi-hour increment, with no interpolation. A return spanning more than `max_gap` = 6 hours is a gap return. It never enters an intraday label, and its week is ineligible (see section 6).
- **Daily clock for L0:** the daily close is the close of the 23:00 candle, i.e. the price at 24:00 UTC. A missing 23:00 candle makes that day's close missing.
- **Output clock:** the weekly label is stamped at the week end (Monday 00:00 UTC). It is known as of the input vintage below. A corrected future vintage produces new label version ids and never overwrites these.

## 5. Source vintages (read-only, licensed, vintage cdab6268)

| Input | Path | sha256 |
|---|---|---|
| BTC-USD hourly candles (primary) | `macro-main/data/coinbase/btc_hourly.parquet` | `1c1b02fd8cd6b0b7d2aec6563abe896694b27659dcb6fed17cf84bf6b450a34d` |
| BTC-USD daily candles (baseline reproduction and consistency check only) | `macro-main/data/coinbase/btc_daily.parquet` | `4ddd11111becf7540788f39934377418dde69e73a4ddfa6eca99828b3a5cfc95` |
| Incumbent baseline code | `Q15/engine/vol_forecast.py` | `bcd6ec2cc8c116b469173ab475dc495be7e024b4ea452b9d1cf6de58301e06c0` |

`evaluate.py` re-hashes every input at run time. It refuses to run if the two parquet hashes differ from this table.

Not admitted, and named as the missing input for higher-frequency work: tick trades, quotes, NBBO or minute bars (owner TP1 #8660). The commodity hourly files are futures with session gaps. Their history is 4 months, so they are not used.

## 6. Cohort and eligibility

- **Cohort:** BTC-USD on Coinbase only, one instrument.
- **Eligible week:** at least 152 of 168 hourly candles present (90% coverage), AND no gap return longer than 6 h, AND all 8 daily closes needed for L0 present (previous Sunday plus Monday through Sunday).
- **Attrition:** ineligible weeks are excluded and counted by reason.
- **Partial weeks:** the first partial week and the final incomplete week are dropped.

## 7. Labels (competitors)

- **L0, the baseline coarse proxy:** the sum of the 7 squared daily close-to-close log returns in the week. This is the incumbent daily-close information set behind `engine/vol_forecast.py`.
- **L1, the simple control:** fixed-interval hourly RV, the sum of the squared hourly log returns in the week (about 168).
- **L2, the noise-aware candidate:** the Parzen realized kernel on the same hourly returns, computed with `engine.vol_noise_robust_realized.realized_kernel`.
  - Bandwidth: H_w = ceil(3.5134 · (ξ²_train)^{0.4} · n_w^{0.6}), floored at 1.
  - ξ²_train is the **median over eligible TRAINING weeks** of ω̂²_w / RV6_w.
  - ω̂²_w = max(RV1_w − RV6_w, 0)/(2 n_w), where RV6_w is the 6-hour subsampled RV averaged over the 6 offsets (`sparse_realized_variance(step=6)`).
  - ξ²_train is the only hyperparameter. It is fixed on training and applied unchanged to the holdout.

## 8. Hypotheses

- **H0:** Δρ = ρ1(log L2) − ρ1(log L1) ≤ 0 on the holdout.
- **H1:** Δρ ≥ 0.05, which is the practical effect bar.
- **Expectation recorded before data:** at hourly sampling, BTC bid/ask noise (about 1 bp) is tiny next to hourly return variation. The prior expectation is therefore no gain, i.e. REJECT of the noise-aware upgrade at this resolution.

ρ1 is the Pearson lag-1 autocorrelation of the log weekly label, computed over consecutive pairs of eligible holdout weeks (w−1, w). Independent measurement error attenuates ρ1, so a less noisy label of the same persistent IV shows a higher ρ1.

## 9. Practical effect bar

Δρ ≥ 0.05 in lag-1 autocorrelation units.

## 10. Trial family

Exactly one confirmatory trial, **Q15-T1**: the primary contrast L2 vs L1 above. Everything else is descriptive and cannot change the verdict. That includes L1 vs L0, the signature curve, noise shares, bias ratios, block-length sensitivity and split halves. No other contrasts, estimators or windows are tried on the holdout.

## 11. Outcome windows

Weekly (7-day) labels, with persistence measured at a 1-week lag. No forecast horizon is involved, because this is measurement, not forecasting.

## 12. Chronological split

- **Training:** weeks starting 2016-01-04 through 2021-12-27. Used only to estimate ξ²_train and for descriptive design diagnostics.
- **Holdout:** weeks starting 2022-01-03 through the last complete week in the vintage, i.e. the week starting 2026-09-28. The holdout is evaluated exactly once.

## 13. Dependence-aware uncertainty

- **Method:** a moving block bootstrap over holdout weeks.
  - Block length 8 consecutive weeks; 2000 replicates; seed 1515.
  - Each replicate draws ceil(N_weeks/8) block start positions uniformly with replacement.
  - Only pairs (w−1, w) that are both eligible and lie inside the same drawn block contribute. A replicate's ρ1(L2) and ρ1(L1) are computed on the same pairs, so the comparison is paired.
  - The 95% CI is the percentile interval of Δρ.
- **Honest N reported:** eligible holdout weeks, eligible consecutive pairs, and the number of non-overlapping 8-week blocks.
- **Descriptive sensitivity only:** block lengths 4 and 13.

## 14. Minimum support

At least 104 eligible holdout weeks AND at least 13 non-overlapping 8-week blocks. Otherwise the verdict is INSUFFICIENT_DATA, naming the missing input.

## 15. Decision rule

| Condition | Verdict |
|---|---|
| Support below minimum | **INSUFFICIENT_DATA** |
| Δρ ≥ 0.05 AND CI lower > 0 | **KEEP** (the noise-aware label is admissible as a separately versioned research label at hourly resolution) |
| Otherwise | **REJECT** (retain fixed-interval RV / the coarse proxy with its limitation; labelled "REJECT (clear)" if CI upper < 0.05, else "REJECT (inconclusive)") |

## 16. Falsifier

If history is too coarse, or the estimator's assumptions fail, the simple proxy is retained with its limitation rather than manufacturing high-frequency precision. Concretely, either of the following triggers it:

- the confirmatory trial does not meet the KEEP rule; or
- the training noise-share diagnostic shows that the i.i.d.-noise model has nothing to remove: median ω̂²-implied noise share of RV1 below 1%, or ξ²_train = 0.

In either case no noise-aware label is put forward. KEEP additionally requires that ξ²_train > 0.

## 17. Stop rule

- The confirmatory stage of `evaluate.py` runs once.
- A rerun is allowed only for a crash or a code defect that does not touch this specification. Each such rerun is logged in RUNS.log, with the defect named in PREREG_AMENDMENT.md, and the first result is kept.
- Any change to the specification goes into PREREG_AMENDMENT.md before the rerun. This file is never edited after freeze.
- No holdout search, no re-splitting, no re-tuning on holdout.

## 18. Synthetic controls (requirement evidence, not empirical)

- **Simulation:** `monte_carlo_bias_table` with n = 4680 returns, IV = 1e-4 and 500 replicates per regime, for both the U-shaped and the stochastic-vol path. Roll bid/ask bounce noise with ξ² = ω²/IV ∈ {0, 1e-5, 1e-4, 1e-3}.
- **Estimators:** tick RV, subsampled sparse RV (step 60), Parzen RK (feasible BNHLS bandwidth) and pre-averaging.
- **Reported per cell:** relative bias, SD and RMSE.
- **Pass criteria:**
  - Under zero noise, |relative bias| < 3% for tick RV and RK.
  - Under ξ² ≥ 1e-4, RMSE of RK < RMSE of tick RV and of sparse RV.
  - Under zero noise, RMSE of tick RV ≤ RMSE of RK.

## 19. Outputs

All outputs go to this directory and are small:

- `labels_weekly.csv`: versioned weekly L0/L1/L2 labels with eligibility, split, H and a version id equal to sha256(input sha256s + PREREG sha256 + estimator spec).
- `result_confirmatory.json`
- `mc_bias_table.json`
- `baseline_reproduction.json`
- `RUNS.log`

These labels are `research_only`, `accepted_label=False`, and never replace or splice into an incumbent history.
