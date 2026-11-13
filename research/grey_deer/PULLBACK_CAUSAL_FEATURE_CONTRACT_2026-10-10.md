# Pullback ongoing: causal depth/velocity/volatility feature contract

**Operation:** `risk-radar-pullback-20261009` · 2026-10-10 continuation.
**Status:** inert research component with synthetic tests, **not** a trained model, market-data admission receipt, production Risk Radar API, investment decision, or numerical remaining-downside forecast.

## Why the next candidate cannot use the pullback phase alone

The previously preregistered **exploratory** fixed-fit SPY study (`PULLBACK_OOS_BASELINE_RESULT_2026-10-09.md`) found worse Q25–Q75 coverage for phase-only stratification (39.6% on 96 matched origins versus 42.7% for unconditional). It also had current-vintage vendor history and no true independent episode clustering. This does not prove phase is useless; it rejects promoting the simple phase-only conditional forecast.

**Mechanism upgrade:** treat **observed damage, decline speed and contemporaneous volatility** as separate causal covariates before attempting a bounded conditional-minimum model. Later add qualified breadth/credit/rates signals only with first-known/source clocks. A recovery-type label is not an entry decision.

## Pure feature read model

`research/grey_deer/pullback_causal_features.py::extract_causal_features(rows, asof, observation, is_session, market, price_basis)`

The caller supplies an already-owner-qualified daily settled-close observation from the **existing** `lib.pullback_observation` contract, matched source price basis and digest, exact as-of session, and an owner exchange calendar callback. This function does **not** fetch data, infer a new episode, issue a warning, size positions or publish a forecast.

The output is explicitly `pullback_causal_features.research.v1`. It computes only:

| Feature | Contemporaneous calculation |
|---|---|
| Current observed drawdown | `1 - P(t)/H`, with the **retained** episode peak `H` |
| Worst observed episode drawdown | `1 - T/H` with retained trough `T` |
| Rebound since worst trough | `P(t)/T - 1` — not recovery odds |
| 5-session decline velocity | `1 - P(t)/P(t-5)` |
| 10-session decline velocity | `1 - P(t)/P(t-10)` |
| Realized trailing 20-return volatility | `engine.vol_forecast.realized_vol(..., win=20) * sqrt(252)` |
| Episode age | The original observer's `observed_closes_since_onset` — never inferred from eventual trough |

All windows are **backwards** from a settled as-of close. The observed price input must be coherent, finite, split-adjusted/dividend-unadjusted and sourced under the same contracted basis. Calendar gaps and missing/invalid values return named `unavailable` states, not zero. The original observed episode (peak/trough/phase) remains untouched; future rows are excluded before reading values. In active production, without independent original-observer, source-rights and price-basis admission, this helper is inert. Its `publication_authorized` is always `false`.

The helper deliberately reuses the existing `engine.vol_forecast.realized_vol` implementation rather than creating a competing volatility model; it has no new data plane, feature store or publish path.

## Verification and method frontier

27 synthetic focused tests run GREEN after expected missing-module RED. Tests cover exact arithmetic and volatility parity, prefix causality despite invalid future prices, missing sessions, stale/current mismatch, wrong market/source basis, per-episode peak retention, invalid prices/duplicate closes, insufficient history, and negative proof for model confidence/position sizing. They prove code behavior only, not actual source coverage or predictive accuracy.

**Next empirical study (not yet run):** Use a licensing-cleared point-in-time price, breadth and cross-asset feature archive with historically available timestamps and market-specific calendars. Freeze history-vintage rules and holdout/episode-count thresholds before any new fitting. Compare an unconditional and volatility-matched conditional baseline first; then preregister an incremental depth/velocity model with 5/10/21-session minimum loss quantiles. Report blocked rolling-origin holdouts, episode-balanced errors, stress-era tail exceedances, Q25–Q75 coverage/width, calibration by depth/age/volatility and abstention rates. Do not reuse the ineligible Yahoo archive for commercially oriented model fitting. For China, verify domestic price basis and separate calibration; no US transfer authorization.

**Do not ship:** the old design's illustrative `2.4–5.6%` downside range, converted `97/100` risk intensity, or an untested historical cohort probability. The UI remains **measured-only + estimate unavailable** until the exact market/basis/horizon scientific receipt, source rights and independently reviewed deployment are accepted.

## Source/custody

Protected Mastermind Skillpack `326c8469a21d7f50fc9ecb1848196bf1c6e66685`. Macro code integration carrier `#8721`; original China observer/integration `#8188` remains DRAFT/HOLD and is never copied or modified by this research component. No new market feed, history ledger, authorization plane or runtime lifecycle is introduced.
