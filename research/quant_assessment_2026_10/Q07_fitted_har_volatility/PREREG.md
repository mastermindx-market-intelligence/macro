# Q07 — Fitted, leakage-controlled HAR volatility challenger: PRE-REGISTRATION

Status: written and frozen BEFORE any evaluation outcome was computed or read. The freeze hash
is in `FREEZE.log`; `evaluate.py` refuses to run if this file's sha256 differs from it. This
file is never edited after the freeze; later changes go only to `PREREG_AMENDMENT.md`.

Author: Claude Opus 5.5 (model id `claude-opus-5-5`), Q07 author seat, research-only.
Reference module: `engine/vol_fitted_har.py` (RESEARCH_ONLY, not wired).
Procedure docs read (read-only, commit unknown):
`Mastermind/docs/sol_skills/INDEX.md` sha256 608aebc84a106f4e3c687f020a7f0e69af88f38e014d4664a376e2be2ddfa220;
`ACTIVE_EXECUTION.md` sha256 fb6a89101ad75512b971b2457f3f419704eae136afa28bac5a646ae69a6ed0dc;
`SESSION_RELIABILITY.md` sha256 817366c630abe31308a09c18caa5249ea4c39c83d74c130496079bb151283076.

## 0. Question

Does a fitted, parsimonious log-HAR forecast of forward daily close-to-close variance beat
the incumbent equal-weight trailing blend (`engine/vol_forecast.har_vol`) AND the simple
controls robustly out of sample, after leakage control, dependence-aware uncertainty and a
cost/complexity charge? If not, the incumbent blend is retained and the negative is published.

## 1. Non-duplication

Collision/incumbent refresh performed against the pristine snapshot `_base` (vintage
d252f919 clone) with `grep -rl -i "fitted_har|vol_fitted|log_har|loghar"` over
`engine/ scripts/ tests/` (no hits) and `ls _base/engine/vol_fitted_har.py`,
`_base/tests/test_vol_fitted_har.py` (both absent). The concept grep ("har_vol",
"vol_forecast", "QLIKE", "HAR-RV") found:

| Incumbent | What it is | Relation / exclusion |
|---|---|---|
| `engine/vol_forecast.py` (blob e2354c5a…, file sha256 bcd6ec2c…) | Unfitted equal-weight blend of trailing RV at lags 2/5/22/66; feeds `cone_vol_ann` (Anticipation cone), `risk_sizing`, `systematic_flows`, `vol_regime`, `index_direction`, `anticipation` | **Baseline under test. Not edited, not imported by the new module** (re-implemented and checked equal by `evaluate.py --mode reproduce-baseline`). |
| `research/PICK_FORWARD_DIST_PHASE1_HAR.md` + `scripts/pick_forward_dist_phase1_har.py` | Diagnostic: blend as a cross-sectional pick-return standardizer; X-4 found the blend no better than trailing 20d RV and biased low; states a fitted forecast is "the obvious untested candidate" | Q07 fills exactly that rung, narrowly: per-asset point forecast of forward variance. No pick standardization, no cell study, no re-run of Phase 1. |
| `engine/options_pilot_study_adapter.py` (QLIKE mention) | Options pilot adapter | Not touched; no implied-variance input used (Q14 owns that, after Q07). |
| `research/cycle_masterplan/PREREGISTRATION.md` §18 CN-HAR-2 | Cycle-pattern *analog* calibration ("HAR-1" is a cycle-analog pairlet, not volatility) | Unrelated estimand; not changed, not cited as evidence. |
| `engine/vol_managed, vol_regime, vol_sentiment, vol_shock_scorecard, vol_squeeze, vol_velocity` | Vol consumers/derived states | None fitted-HAR; none changed. |
| Crypto / Bitcoin R2 #8050 | Crypto scientific hardening | Excluded; no crypto asset in cohort. |
| Anticipation Engine (ANTICIPATION_ENGINE.md), Risk Radar / Grey Deer, dealer LOD/HOD | Architecture/products consuming vol | No architecture, cone, probability, or product change. |
| Q15 (noise-robust HF RV), Q16 (delayed calibration), Q14 (implied-variance economics) | Sibling briefs | Q07 uses the DAILY proxy only and never splices HF labels; Q14 runs after Q07 (dependency recorded as limitation). Sibling directories not read. |

Narrow relation kept: a research-only reference challenger + one frozen comparison. No
generic CQR/conformal program, no promotion controller, no trial-ledger write.

## 2. Estimand, unit, clocks

* **Unit:** asset × session (forecast origin `t`).
* **Return:** `r_t = log(close_t / close_{t-1})`, Yahoo `close` column (dividend/split
  adjusted; verified `close_price/close` → 1.0 at the last row and > 1 historically).
* **Target (label `DAILY_CC_MSR`):** `y_t(h) = mean(r_{t+1}^2 … r_{t+h}^2)`, the forward mean
  squared daily close-to-close log return — a DAILY close-to-close variance PROXY, explicitly
  NOT high-frequency integrated variance. No other label is admitted (module raises).
* **Estimand:** the holdout mean QLIKE loss difference (control − challenger), averaged per
  session across assets, and its relative form `1 − mean QLIKE(challenger)/mean QLIKE(control)`.
* **Input clock:** information through the session-`t` close. **Output clock:** forecast
  stamped at `t` for window `t+1..t+h`. Fit clock: refit every 21 sessions on a fixed
  position grid `c = 0, 21, 42, …`; a forecast at `s` uses the latest fit with `c ≤ s`.
* **Primary horizon:** `h = 21` sessions (one month; the medium Anticipation horizons span
  21–63).

## 3. Cohort and source vintages

Cohort (13 ETFs, the Anticipation Phase-0 ETF set): SPY, QQQ, XLB, XLC, XLE, XLF, XLI, XLK,
XLP, XLRE, XLU, XLV, XLY from `/Users/chriswong/Documents/Cluade/macro-main/data/yahoo/`
(read-only licensed retained data, macro-main vintage `cdab62686e79`). File sha256:

| file | sha256 |
|---|---|
| SPY.parquet | 6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152 |
| QQQ.parquet | 5e851c16c54a1bfe190cdc454cf88b17b2a23601d6e15897f74be2ad19bebf0c |
| XLB.parquet | cd763ad4b83cc832a5a58a62959eb0ff547c46d3ef103a83b06c977ef9407ab3 |
| XLC.parquet | b3d5e72afd435545b7aa894c7dfeaf9edb5d41a26fb37711a45ad13a26c911b7 |
| XLE.parquet | eab5678e5a69f8b3bb1af61ecf469c3ecd235544e054b00a65bbecbaae1ad17e |
| XLF.parquet | f6a5a43d2b1c2124c6d80067f7effd612273864d6ce40813e1196b003be0b707 |
| XLI.parquet | d8a4fdf3405fe8c2538d5c19c3567c7284f26181c066b5fb4f616f9cf73f507a |
| XLK.parquet | 3e24eab5f93be8a5de354bf25e5fe3142328a62c37ab47f0c8445f218de7ad33 |
| XLP.parquet | d765ac7968609bb6fc0f0d8ec5b14594cd03f07e6ebc592cef7915247186fde5 |
| XLRE.parquet | 2a4eaef85fd4af868fd2b70ce5d04e0828cb0df1d9e255ba14be3c39bd7b7581 |
| XLU.parquet | d2eb4a95c202b2982af2ce6ebf3ca47c9bc24b03c80445bfea46e7bec7a93f41 |
| XLV.parquet | 57b5a45c1c91754dc03d78ab44b6df7317de2ad86c73f513520278c4cfe0a07c |
| XLY.parquet | 1f7c6916dbc04436b5bbfebdd4fa00a66d6f8e26982c789881fd0094f1fb1514 |

Data qualification done before freeze (structure only, no forecasts/losses): no NaN closes,
no duplicate dates, one >5-day gap per long series (Sept-2001 closure), max |r| ≤ 0.225.
`data/stocks/` (251 names) is EXCLUDED: 54 files show |log return| > 0.4 days (e.g. 22 such
days in one name), i.e. unverified split/adjustment status; using them would contaminate the
variance target. This is attrition by data qualification, declared before outcomes.
Evaluate.py re-hashes every input and refuses on mismatch.

## 4. Models (one challenger, four simple controls)

* **H (challenger):** per-asset OLS of `log(max(y_t, floor))` on `[1, log max(RV1_t,floor),
  log max(RV5_t,floor), log max(RV22_t,floor)]`, `RVk_t` = trailing mean of `r^2` over k
  sessions ending at t. Expanding window, training rows restricted to `t + h ≤ c` (forward
  window closed by the cutoff — the embargo), minimum 504 training rows, refit every 21
  sessions. Back-transform `ŷ = exp(Xβ) · mean(exp(training residuals))` (Duan smearing,
  training residuals only). 4 fitted parameters + 1 smearing factor per asset per refit.
* **C0 incumbent blend:** `har_vol(close)^2` exactly as served (simple returns, ddof=0,
  lags 2/5/22/66; variance = sd²). 0 fitted parameters.
* **C1 persistence:** `RV22_t`. 0 parameters.
* **C2 EWMA:** RiskMetrics λ = 0.94 on `r^2`, seeded with the first 22-session mean. λ fixed
  a priori (not tuned). 0 fitted parameters.
* **C3 scaled blend:** `k_c · C0`, `k_c = Σy/ΣC0` over matured training rows at each cutoff
  (same grid, same 504 minimum). 1 fitted parameter. Included so a pure level-bias fix of the
  incumbent cannot be mistaken for HAR skill.

No hyperparameter is searched. Floor, components, λ, refit cadence, min-train, window are fixed
here.

## 5. Chronological split, support, attrition

* **Development segment:** sessions before 2008-01-02. Used only as training history for the
  expanding fits (and for the baseline-reproduction equality check). No losses are computed
  or read on it.
* **Holdout:** forecast origins from 2008-01-02 through the last origin whose 21-session
  target has matured in the vintage. Single holdout, evaluated once; no repeated holdout
  search.
* **Common support:** an (asset, origin) enters only if H, C0–C3 and the target are all
  finite. Per session, losses are averaged across available assets (unbalanced panel: XLRE
  and XLC enter when their own 504-row training minimum is met). Reported: rows per asset,
  drops by reason (no forecast / no target / incomplete model), sessions with < 13 assets,
  and a balanced-panel diagnostic over the 11 assets present throughout.

## 6. Losses

* **Primary:** QLIKE `y/f − log(y/f) − 1` with `y, f` floored at `1e-8` (daily variance,
  i.e. 0.01% daily sd). Zero/near-zero handling: floor on both target and forecast; the
  same floor floors HAR log-features.
* **Floor sensitivity (requirement 4):** the full pipeline (fit + loss) recomputed at floors
  {1e-10, 1e-8, 1e-6}; plus the count of holdout targets below each floor.
* **Secondary (descriptive):** squared log error, absolute error on the vol scale
  `|√y − √f|`, and 80% variance-scale interval coverage (`f · exp(q10/q90 of training
  log(y/f))`, matured training rows only) for every model.

## 7. Uncertainty (dependence-aware) and honest N

Per-session cross-sectional mean losses form one date-ordered series per model. Paired
circular block bootstrap over sessions (dates resampled jointly for both members of a pair),
block length 126 sessions (= 6h, covering the 20-session target overlap and cross-asset
common shocks), B = 2000, seed 20261008, two-sided 95%. **Honest N = number of
non-overlapping 126-session blocks in the holdout** (also reported: number of
non-overlapping 21-session target windows). Confirmatory HAC: Newey–West (Bartlett, lag 42)
Diebold–Mariano t-stat on the per-session differential.

## 8. Hypotheses, practical bar, trial family, decision rule, falsifier

* **H1:** H improves holdout mean QLIKE relative to EACH of C0, C1, C2, C3.
* **H0 / falsifier:** H fails to beat at least one simple control by the bar with block
  uncertainty excluding zero → **REJECT**: retain the incumbent blend and publish the negative.
* **Practical effect bar (cost/complexity charge):** relative QLIKE improvement ≥ **3%**
  versus every control AND the 95% block-bootstrap interval of the mean differential has
  lower bound > 0. The 3% charge prices H's fitted parameters, monthly refits and model risk
  against 0–1 parameter controls.
* **Robustness condition:** the KEEP/REJECT outcome must be identical at all three floors;
  a KEEP at the primary floor that does not hold at every floor becomes REJECT.
* **INSUFFICIENT_DATA:** fewer than 30 honest blocks, or fewer than 5 assets with holdout
  support.
* **Trial family:** exactly ONE confirmatory trial — {log-HAR(1,5,22), per-asset,
  expanding, embargoed, monthly refit} × {h = 21} × {QLIKE, floor 1e-8} vs {C0..C3}. Everything
  else is descriptive and cannot change the verdict: rolling 1260-row HAR variant, h = 5 and
  h = 63 (block length max(63, 6h)), secondary losses, coverage, per-asset, per-year, balanced
  panel, HAC t-stat.
* **Verdict words:** KEEP | REJECT | INSUFFICIENT_DATA (VERDICT.md).
* Even KEEP changes nothing: no cone probability, model promotion, portfolio budget or live
  forecast default changes on research success alone (requirement 6); any adoption is a
  separate owner decision.

## 9. Stop rule

`evaluate.py --mode reproduce-baseline` runs first (equality of the module's incumbent with
`engine/vol_forecast.har_vol` on all 13 assets, max abs diff ≤ 1e-12, else stop). Then
`evaluate.py --mode evaluate` runs ONCE. A crash or a demonstrable code defect may be fixed
and re-run only with the defect and fix recorded in `PREREG_AMENDMENT.md` before the rerun;
no specification change after any outcome is read. Every run is appended to `RUNS.log`.
