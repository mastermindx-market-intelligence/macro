# Q14 — Horizon-matched variance-risk-premium: pre-registration

Study ID: `Q14-T1` (one trial). Author: Claude Opus 5.5 (model ID `claude-opus-5-5`), brief Q14.
Status: RESEARCH ONLY. No wiring, ranking, sizing, alerting, selling or promotion authority.
This file is frozen by `FREEZE.log` before any evaluation outcome is read. Any later change
goes only into `PREREG_AMENDMENT.md`.

## 1. Question

Does a horizon-matched ex-ante variance premium, `premium_hat(t) = IV2_30(t) - F_30(t)`, both
legs measured in 30-calendar-day horizon-variance units, carry information about the realized
forward 30-calendar-day variance beyond simple implied-variance and trailing-realized-variance
controls? The identity behind it: when IV2 is already a control, the information in
`premium_hat` is exactly the information in its forecast leg `F`. So the test asks whether the
incumbent forecast leg adds anything beyond `[IV2, RV_trailing]`. Predicting the ex-post premium
`IV2 - RV_forward` is the same problem as predicting `RV_forward`.

## 2. Non-duplication

Collision check: `grep` of `_base/` for `vol_horizon_variance_premium` returned nothing, and
none of `variance_risk_premium`, `horizon_variance` or `forward variance premium` names an
existing module. The module name `engine/vol_horizon_variance_premium.py` is absent from
`_base/engine`. The incumbent VRP-like numbers below stay untouched. This study neither
replaces them, feeds them nor re-labels them.

| Incumbent | What it computes | Relation kept by Q14 |
|---|---|---|
| `engine/vol_regime.py` (sha256 `67c8e9eb…cc6d`) | `vrp = VIX - cone_vol_ann*100`, in **volatility points**; equal-weight multi-scale std of demeaned pct returns; vrp_pctile / vrp_chg_21d; judged by `scripts/validate_vol_regime.py` against forward **equity returns** | Not re-gated or replaced. Q14 does no equity-return timing. Its number appears here only as a reproduced baseline and in a unit-mismatch receipt. |
| `engine/conditions.py` (sha256 `2a19896a…797b`) | `vrp = VIX - trailing std*sqrt(252)*100`, vol points; vrp_state | Untouched; not reused as an input. |
| `engine/options_hub.py` | `vrp = atm_iv_30 - rv20` (IV minus trailing RV) | Untouched. Q14 is explicitly not a renamed IV-minus-trailing-RV number. |
| `engine/btc_signals.py` | crypto `DVOL - rv` | Excluded (crypto, #8050 boundary). |
| `engine/risk_radar.py` | VRP judged "noise" as a drawdown-risk timer | Negative evidence retained. Q14 makes no drawdown or risk-probability claim. |
| `engine/vol_forecast.py` (R04, sha256 `bcd6ec2c…06c0`) | equal-weight HAR-set trailing vol `har_vol` | Used read-only as the incumbent forecast leg `F`. Q07 (fitted HAR) is a sibling brief; Q14 does not read or depend on it, and records that dependency as a limitation. |
| PRs #8577 / #8578 (relative options-pricing maps) | scatter/percentile pricing comparison | Excluded: no map, plot, percentile or compare-page work. |
| OA-3 exact-option outcome policy; Q05 | option execution economics | Frozen and excluded. Q14 computes no option P&L and no short-volatility return. |
| Dealer pressure / options-matrix lanes (#8555, #7861, #7293, #7327) | dealer book / snapshot retention | Excluded. |
| Volatility dependency row ("never splice new variance labels into an old benchmark history silently") | — | Q14 defines its own label (sum of squared log returns over (t, t+30cd]) and never splices it into any incumbent history. |

`research/DO_NOT_REBUILD.md` has no VRP row. Respected standing keys:
- KILLs: DNR:KILL-OUTCOME-AUDITION, DNR:KILL-LLM-ORIGINATION, DNR:KILL-FUSED-COMPOSITE,
  DNR:KILL-POSITIONING-FUSION, DNR:KILL-REGIME-SCORECARD,
  DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR, DNR:KILL-CAUSAL-DAG-ALPHA.
- HOLDs: DNR:HOLD-PSS-AF1-FINRA, DNR:HOLD-PSS-CD1-CROWDING.

Q14 builds no composite and no regime scorecard. It runs no outcome audition: there is one
pre-registered comparison and no search.

**Narrow relation I stay inside:** horizon-matched, variance-unit measurement of the premium,
plus ONE test of incremental information for forward realized variance.

## 3. Estimand, units, clocks

- **Unit of observation:** one US trading day `t` (an as-of date) on which both the ^GSPC close
  and the FRED VIXCLS close are finite.
- **Horizon:** `h = 30` calendar days, day count `calendar365`, units `horizon_variance`.
- **Implied leg (measure kind `strip`):** `IV2_30(t) = (VIXCLS(t)/100)^2 * 30/365`.
  - VIX is CBOE's 30-calendar-day discretized log-contract strip. Its vendor biases are
    disclosed, not corrected:
    - zero-bid tail truncation (biases it down)
    - discrete strikes
    - no jump correction
    - methodology backfilled before 2003
    - weekly expiries added from 2014
  - Coverage receipt: `tail_strikes = "strip_truncated"`, `overnight = "included"` (as a
    risk-neutral expectation).
- **Forecast leg `F_30(t)`:** `daily_variance_to_horizon_variance(har_vol(close)(t)^2, 30)`,
  that is `har_vol^2 * 252 * 30/365`.
  - `har_vol` is the incumbent `engine.vol_forecast.har_vol` with lags (2, 5, 22, 66), computed
    on ^GSPC closes `<= t`.
  - Disclosed basis gap: the incumbent uses demeaned percent-return std, while the label uses
    non-demeaned log returns. OLS intercept and slope absorb the level difference. The gap is
    disclosed, not hidden.
- **Trailing control `RV_trail(t)`:** the sum of squared daily log returns of ^GSPC realized on
  trading days in `(t-30cd, t]`. NaN when the window is incomplete or has a missing return.
- **Label `Y(t) = RV_fwd(t)`:** the sum of squared, non-demeaned, close-to-close daily log
  returns of ^GSPC on trading days in `(t, t+30cd]`.
  - Overnight is included. The intraday path is not observed (daily sampling; better
    high-frequency labels are Q15's job).
  - NaN when `t+30cd` is beyond the last close, or when any return in the window is missing.
- **Input clock vs output clock:**
  - Every feature uses data `<= t`.
  - The label uses only returns strictly after `t`.
  - The VIX close (16:15 ET) and the SPX close (16:00 ET) differ by 15 minutes. This is an
    acknowledged session offset (`acknowledge_session_offset=True`); those 15 minutes are in
    neither leg.
- **Price basis:** a price index without dividends. Daily dividend drift is negligible for
  squared returns, and this is disclosed.
- **Ex-post premium (descriptive):** `IV2_30 - RV_fwd`.

## 4. Cohort and source vintages

Read-only licensed retained data at `/Users/chriswong/Documents/Cluade/macro-main/data`,
vintage `cdab6268`:

| Input | sha256 | Use |
|---|---|---|
| `yahoo/_GSPC.parquet` | `35570905ff8d16c2284cd02cc32ebcfa7f67f025638e00783a7390ecb0358ac1` | column `close` → returns, `har_vol`, trailing RV, label |
| `fred/VIXCLS.parquet` | `9c2cf59813a9415be7c657f1a312f5e86673a82de6e99dab65d882946b85a25a` | column `vix_close` → implied leg |
| `yahoo/_VIX.parquet` | `cc85989435aecf3c24fd4ca24fac8979e771577543a4a73c609e4e903b57228e` | reported only: agreement with VIXCLS (data-quality receipt; not an input to the decision) |

Returns are computed on the full ^GSPC trading calendar. As-of rows are then restricted to dates
where VIXCLS is finite; there is no forward fill.

Cohort is every as-of date from 1990-01-02 through the last date with a complete label (about
2026-09-08) that also has finite `IV2`, `F`, `RV_trail` and `Y`.

Procedure docs, read-only, commit unknown (protected Git read unavailable):
- Mastermind `docs/sol_skills/INDEX.md`: `608aebc84a106f4e3c687f020a7f0e69af88f38e014d4664a376e2be2ddfa220`
- `ACTIVE_EXECUTION.md`: `fb6a89101ad75512b971b2457f3f419704eae136afa28bac5a646ae69a6ed0dc`
- `SESSION_RELIABILITY.md`: `817366c630abe31308a09c18caa5249ea4c39c83d74c130496079bb151283076`

Brief: `Q14_forward_variance_premium.md` sha256 `89cd423e5e03482254ea08dca2a6923c6b228dd9288ac4775c0a55020248e657`.

Reference module at freeze: `engine/vol_horizon_variance_premium.py` sha256
`149d83b67615e2566c8abc2da8bfb5a8079e139507d14ee8571493007737cb68`. After the run, only the
docstring verdict line may change. Any change is logged in RUNS.log.

## 5. Hypotheses, competitors, decision

- **H0:** adding `premium_hat` (equivalently `F`) to the controls does not reduce out-of-sample
  MSE of `Y` by a practically material and stable amount.
- **H1:** it does.
- **Controls C (baseline competitor):** OLS of `Y` on `[1, IV2_30, RV_trail]`.
  - This is the brief's "simple existing IV/RV controls". The IV control is the strip-kind VIX
    variance because no long ATM-IV history exists locally (options_skew `atm_call_iv` covers
    only 2026-06-21..2026-09-30). The ATM-proxy kind is supported by the module but not studied
    (req4: no mixing).
- **Augmented A:** OLS of `Y` on `[1, IV2_30, RV_trail, premium_hat]`.
- **Reported, not decision-bearing:**
  - single-variable fits (`IV2` only, `RV_trail` only, `F` only) on the same split
  - QLIKE for C and A, with the count of non-positive OLS forecasts floored at 1e-8
  - a Diebold-Mariano-style HAC t on the loss differential
- **Primary loss:** squared error in horizon-variance units, `L = (Y - f)^2`. The loss
  differential is `d = L_C - L_A` (positive means A is better).
- **Practical effect bar:** KEEP the predictive upgrade if and only if ALL of:
  1. relative MSE reduction `(MSE_C - MSE_A)/MSE_C >= 0.05` on the holdout
  2. the moving-block-bootstrap 95% percentile lower bound of `mean(d)` is `> 0`
  3. the relative reduction is `> 0` in at least 2 of 3 equal chronological thirds of the
     holdout rows
- **Otherwise REJECT the predictive upgrade.** The clarified horizon-matched measurement (the
  module plus receipts) is retained as research-only measurement either way. A result of
  INSUFFICIENT_DATA is declared only if the holdout has fewer than 36 non-overlapping 30cd label
  windows, or the training set has fewer than 60.

## 6. Trial family, windows, split

- **Trial family:** exactly one trial, `Q14-T1` (C vs A above).
  - No alternative horizon, lag set, feature, transform, loss, split or sample is tried.
  - The single-variable fits and QLIKE are fixed diagnostics of the same trial, not extra
    trials.
- **Chronological split:**
  - Training as-of dates: from the cohort start through 2011-12-31 (the last as-of `<=`
    2011-12-31).
  - Embargo: the holdout starts at the first as-of date `>= last_train_date + 31` calendar
    days, so no training label overlaps a holdout label.
  - Holdout: from that date through the last complete-label as-of date.
- **Preprocessing:**
  - All of it is fixed formulas (no scaling, no winsorizing, no outlier removal).
  - The only fitted parameters are the OLS coefficients, fit on training rows only.
  - No hyperparameter is tuned: HAR lags are the incumbent's (2, 5, 22, 66); block length, HAC
    lags, bootstrap draws and seed are fixed below.
- **Outcome window:** each row's label window is `(t, t+30cd]`. The holdout is scored once.

## 7. Dependence-aware uncertainty and honest N

- Labels overlap (about 21 trading days), so rows are not independent.
- **Moving block bootstrap** of `mean(d)` over holdout rows: block 63 trading days, B = 2000,
  seed 14, 95% percentile interval.
- **Newey-West HAC** (Bartlett kernel) t on `mean(d)` with 42 lags (about 2x the label
  overlap).
- **Honest N, reported for train and holdout:**
  - the number of non-overlapping 30cd label windows (greedy, from the first row)
  - the number of 63-trading-day blocks
  - Rows are reported but never presented as the effective N.
- **Attrition/support:** row counts dropped at each stage:
  - VIX missing on a ^GSPC day
  - incomplete trailing window
  - incomplete label
  - `har_vol` NaN
  - embargo gap
- **Support also reports:** first and last as-of of train and holdout, and the
  `close`/`close_price` agreement count.

## 8. Falsifier and stop rule

- **Falsifier:** if the bar in §5 fails (no material, bootstrap-positive, stable reduction),
  then the premium adds no stable information beyond the controls. The predictive upgrade is
  rejected and only the clarified measurement is retained.
- **Stop rule:**
  - `evaluate.py` runs the comparison once.
  - If it crashes before any outcome number is printed or written, a mechanical bug fix that
    leaves this specification unchanged is allowed. It is recorded in RUNS.log, and in
    PREREG_AMENDMENT.md if it touches anything specified here.
  - Once holdout outcomes are written, no specification change and no re-run with altered
    choices is permitted.
  - Repeat invocations with the identical frozen spec are allowed and must reproduce the
    identical result (deterministic seed).
- **Baseline reproduction (`evaluate.py --mode baseline`):** runs after the freeze and before
  the comparison. It reproduces on the full cohort, as a descriptive receipt:
  - the incumbent vol-point `vrp = VIX - cone_vol_ann*100`
  - the incumbent `cone_vol_ann` vs `forward_vol_ann(21)` R²
  - a unit-mismatch receipt between the vol-point spread and the horizon-variance premium:
    correlation, sign-disagreement rate, and the rate at which a positive vol-point spread
    coexists with a negative horizon-variance premium
  It is not decision-bearing.

## 9. Disclosed limitations, fixed in advance

- **Vendor strip:** VIX biases (§3). No local full option-strip history exists (the Q01
  dependency), so the module's `strip_variance` is exercised only synthetically in tests.
- **Forecast leg:** the forecast leg is the incumbent equal-weight HAR set, not a fitted HAR
  (the Q07 dependency, not consumed).
- **Daily sampling:** close-to-close, so jumps and overnight returns are in the label and the
  intraday path is unobserved (the Q15 dependency).
- **Loss sensitivity:** squared-error loss in variance units is dominated by crisis windows
  (for example 2020-03). This is disclosed, and QLIKE is reported as the scale-robust
  secondary.
- **Holdout status:** the 2012–2026 public holdout is untouched only by this brief. Other repo
  research has seen these years, so it is not fresh data in the global sense.
- **No authority:** no expected-profit, risk-probability, trade-selection or short-volatility
  authority is inferred from any number here (req6). An implied variance above expected
  variance is a price of insurance, not an earned return.
