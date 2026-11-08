# Q14 verdict: horizon-matched variance premium

**VERDICT: REJECT** the predictive upgrade (trial `Q14-T1`).

The clarified horizon-matched **measurement** is kept as research-only code:
- `engine/vol_horizon_variance_premium.py`
- the receipts in this directory

Nothing is wired, and no forecast, trade, ranking, sizing or short-volatility authority follows. This verdict comes from the single frozen comparison specified in `PREREG.md` (sha256 `97ec3b04…ff56`, frozen at 2026-10-09T10:14:37Z per `FREEZE.log`), run before any outcome was read.

## What was tested

- **Target:** `Y = RV_fwd`, the sum of squared S&P 500 close-to-close log returns over the next 30 calendar days, in horizon-variance units.
- **Controls C:** OLS on `[1, IV2_30, RV_trail]`.
  - `IV2_30 = (VIXCLS/100)^2 · 30/365` (strip kind, vendor-computed)
  - `RV_trail` is the trailing 30-calendar-day sum of squared returns.
- **Augmented A:** C plus `premium_hat = IV2_30 - F_30`.
  - `F_30` is the incumbent equal-weight HAR volatility from `engine/vol_forecast.py` with lags (2, 5, 22, 66), mapped to horizon variance as `har_vol^2 · 252 · 30/365`.
- **Split:**
  - Train on as-of dates 1990-01-02..2011-12-30 (5,544 rows).
  - Embargo the next 31 calendar days (18 rows).
  - Holdout 2012-01-30..2026-09-08 (3,673 rows), scored once.
- **Decision bar (all three required):**
  - relative MSE reduction of at least 5%
  - a moving-block-bootstrap 95% lower bound on `mean(L_C - L_A)` above 0
  - a positive reduction in at least 2 of the 3 chronological holdout thirds

## Result (T1 record `result_compare_T1_original.json`, sha256 `a865f22047c75e90c32e5083077c76bd34cb30fa2f4f25407ead19e011cb674e`; post-audit re-run `result_compare.json`, sha256 `4c1955107f24f94f791382fe2c9a5dfcb2b89df9f084f8075506f094f87cbcd8`, identical on every number)

| Quantity | Value | Bar | Pass |
|---|---|---|---|
| Holdout MSE, controls C | 2.6622e-05 | | |
| Holdout MSE, augmented A | 2.6083e-05 | | |
| Relative MSE reduction | **2.02%** | ≥ 5% | **no** |
| Block bootstrap of mean(d): 95% CI (block 63, B 2000, seed 14) | [-7.28e-08, 1.76e-06] | lo > 0 | **no** |
| Newey-West HAC t of mean(d), 42 lags | 1.10 | (reported) | |
| Relative reduction by holdout third | +0.55%, +2.29%, **-0.88%** | ≥ 2 of 3 positive | yes (2/3) |
| QLIKE C vs A (mean) | 0.3754 vs 0.3764; DM HAC t -0.27 | (reported) | A slightly worse |
| Non-positive OLS forecasts | 0 (C), 0 (A) | (reported) | |

Two of the three conditions fail, so the falsifier in PREREG §8 fires: the premium adds no stable information beyond the IV/RV controls.

A repeat invocation with the identical frozen spec reproduced byte-identical `result_compare.json` (RUNS.log, runs 2 and 3).

After the independent audit (PASS_WITH_FIXES), `PREREG_AMENDMENT.md` (A1, no spec change) was written before one more identical-spec re-run. That re-run matched the T1 record on every numeric field. The only differences were the pre-declared ones: the code hashes in `inputs_sha256` and the forecast-leg coverage receipt (RUNS.log, last two entries). The T1 record remains the decision-bearing file.

Adversarial reading:
- The only holdout third that went negative is the **most recent** one, about 2021–2026, which is the current regime. The motivating use case, "is implied variance expensive now", gets no support there.
- QLIKE, which down-weights crisis outliers, points the other way, so the 2% MSE gain is not robust to the loss.

## Honest N and support

- **Holdout:** 170 non-overlapping 30-calendar-day label windows and 58 blocks of 63 trading days.
- **Train:** 256 windows and 88 blocks.
- Rows overlap by about 21 trading days and are never presented as the effective N.
- INSUFFICIENT_DATA thresholds (36 holdout windows, 60 train windows) are cleared by a wide margin.
- **Attrition from 9,260 ^GSPC days on or after 1990-01-02:**
  - VIXCLS missing: 4
  - trailing window incomplete: 0
  - label incomplete (the last 30 calendar days): 21
  - `har_vol` NaN: 0
  - embargo gap: 18
- **Cohort:** 9,235 rows.
- `close` and `close_price` agree within a relative 1e-6 on 9,235 of 9,235 rows.

## Research-only decomposition (descriptive, not an earned return)

| | Train | Holdout |
|---|---|---|
| mean IV2_30 | 4.04e-03 | 2.93e-03 |
| mean F_30 (incumbent forecast leg) | 2.17e-03 | 1.68e-03 |
| mean RV_fwd (label) | 2.90e-03 | 2.29e-03 |
| mean premium_hat (ex ante) | 1.87e-03 | 1.25e-03 |
| mean ex-post premium IV2 − RV_fwd | 1.14e-03 | 6.38e-04 |
| same, annualized variance (×365/30) | 0.0138 | 0.0078 |
| share of rows with negative ex-post premium | 12.9% | 15.3% |

Implied variance exceeded subsequent realized variance on average in both periods. This is a spread between a risk-neutral price and a physical outcome. It ignores option bid/ask spreads, variance-swap convexity and the VIX strip's truncation and discretization, and its losses are concentrated in crashes. **It is not an expected profit, a probability or a reason to sell volatility** (requirement 6).

## Fixed diagnostics (same trial, not extra trials)

Single-variable holdout MSE:
- IV2 only: 2.364e-05
- F only: 2.712e-05
- RV_trail only: 3.154e-05

The IV2-only fit beats both C and A out of sample. Pairing a backward-looking variance term with IV2 does not help on this holdout. This is reported, not acted on: choosing IV2-only after seeing the holdout would be holdout search, which PREREG §6 forbids.

## Baseline reproduction (`result_baseline.json`, sha256 `a2adc80fc602bae87be1c60016d09761f0831f734ecc9b937d394cee6925a25e`)

- **Incumbent `vrp = VIX - cone_vol_ann·100`** (`engine/vol_regime.py`), in volatility points, over the full cohort:
  - mean 6.26 points, median 6.13 points
  - positive on 95.9% of rows
- **Incumbent `cone_vol_ann` vs `forward_vol_ann(21)`:** R² 0.456 (squared Pearson correlation, descriptive).
- **Unit-mismatch receipt, vol-point spread vs horizon-variance premium:**
  - Correlation is 0.847.
  - Sign disagreement is 0.0%. This is an algebraic consequence of using the same HAR leg: `IV2 - F ∝ (σ_I - σ_P)(σ_I + σ_P)`, so the signs always match.
  - The magnitudes differ. The variance premium scales with the level of volatility, so the same vol-point spread means a much larger variance premium in a high-volatility regime. The incumbent vol-point number is therefore a different estimand, not a mislabelled sign.
- **VIXCLS vs Yahoo ^VIX:** 9,235 rows compared, max absolute difference 2.61 points, 9 rows above 0.05 points. This is a data-quality receipt and not part of the decision.

## Limitations

- **Implied leg:**
  - It is the vendor VIX strip, which is truncated and discretized, with no jump correction. No local full option-strip history exists, so it depends on Q01.
  - The brief's "ATM IV" control is replaced by VIX strip variance, because local ATM-IV history covers only months.
  - The ATM-proxy kind is supported in code but not studied.
- **Forecast leg:** it is the incumbent equal-weight HAR, not a fitted HAR (Q07 dependency).
  - Its basis differs from the label's. `har_vol` is a rolling `std(ddof=0)` of **demeaned simple percent** returns, scaled by 252·30/365. The label is a **non-demeaned sum of squared log** returns over the realized calendar window. Both are in horizon-variance units, but they are different estimators.
  - Every record now carries its own forecast-leg receipt (`demeaned: true`, `returns: simple_pct`, plus an estimator line). The T1 record predates that fix and shows the label receipt (`demeaned: false`) on the forecast leg.
  - Over 30 days, demeaning and the pct-vs-log difference are second-order relative to the 2% vs 5% gap. Even so, they belong to the forecast leg's definition, and they are disclosed rather than corrected.
  - With IV2 in the controls, the information in premium_hat equals the information in F. A better forecast could change the answer.
  - That would be a **new trial identity**, not a re-run of Q14-T1.
- **Label:**
  - It uses daily close-to-close sampling, so jumps and overnight moves are included and the intraday path is unobserved (Q15 dependency).
  - It is price-only with no dividends.
  - VIX settles at 16:15 ET and SPX at 16:00 ET, a 15-minute session offset that is acknowledged in every record.
- **Scope:** one underlying (S&P 500), one horizon (30 calendar days) and one split. Squared-error loss is dominated by crisis windows.
- **Procedure docs:** the Mastermind procedure docs were read at an unknown commit, with hashes recorded in PREREG §4.
- **Post-freeze code history (audit M1/M2, disclosed in RUNS.log):**
  - `evaluate.py` changed after the freeze, from `793d1c…` (13,850 B) to `6b65b3b6…` (13,936 B). The earlier bytes cannot be recovered, so neither the diff nor the reason can be reconstructed. No run of `793d1c…` is recorded, so it produced no outcome.
  - The earlier module edit `149d83b6…` → `c7906612…`, logged as docstring-only, cannot be checked byte for byte. The T1 numbers came from `149d83b6…`. The post-audit re-run of `42a7039e…` reproduced every one of them, which is the empirical check that no numeric behaviour moved.
  - All post-audit edits are kept as a unified diff in `POST_AUDIT_EDITS.diff`.
- **`trading252` day count (audit M4):** it now means expected trading days, 252·h/365, throughout. Year fraction, ATM-proxy variance and the annualized view are consistent with `calendar365`, and a test pins this. The study uses only `calendar365`.

## Owner decision requested

Keep the module as a research reference only. Do not wire it, and do not promote the premium as a forecast input. Any follow-up needs its own pre-registration:
- after Q07, a fitted-HAR F
- after Q01, a strip-based implied leg
