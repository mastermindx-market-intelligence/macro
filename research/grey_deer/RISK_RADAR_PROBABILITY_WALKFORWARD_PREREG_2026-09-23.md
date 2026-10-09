# Risk Radar Probability Walk-Forward Calibration — Preregistration

Status: frozen research protocol. Commit this file before generating candidate outcomes.

Source base: `668237947e016f679782e41e61c91c9133a5ea99`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@7084d7c436a991c3a9d445a1afc6bc0f0642dc62`, Skillpack 1.0.1/bootstrap 1.

## Question

The existing static US Risk Radar probability surface has useful Brier skill and
risk-gradient separation, but exact cells are not precision-grade. A single
pre-2020 state-only refit failed on the 2020+ holdout. The next question is not
"what probabilities best fit 2020+"; that holdout has already been inspected.

The question is:

> Does a strictly causal, expanding-origin annual recalibration rule improve the
> displayed probability surface out-of-fold, year after year, versus the shipped
> static surface on the same dates?

This study is research only. It cannot change `prob_cal`, conjunction bump,
state/gate logic, policy, sizing, ranking, ledger, or capital authority.

## Frozen state and outcome machinery

Use the current production-equivalent Risk Radar replay:
- `engine.risk_radar.leading_signals()`
- `subscore_series()`
- `engine.risk_radar_backtest.state_series(..., sigs=sigs)`
- native SPY close observations from `_spy(drop_missing=False)`
- the shipped Tier-A hot-count definition: sub-score >= current caution band
- target = >=5% SPY close-relative maximum loss within H native future observations
- horizons H = 5, 10, 21

No forecast-date resampling, no forward-filled prices, no partial forward windows.

## Frozen folds

Annual expanding-origin test folds: calendar years **2010 through 2025 inclusive**.

For test year Y:
- test rows are eligible observation dates in Y;
- training rows may use only labels whose **forward-window end date is strictly
  before the first eligible test observation of Y**;
- therefore H21 labels supply the binding embargo geometry; shorter horizons still
  obey their own end-date-before-test rule;
- minimum training history = all available eligible history satisfying that rule;
- no 2026 partial-year fold participates in the primary verdict.

A 2026 partial-year shadow may be reported only after the primary verdict and must
not affect it.

## Frozen calibration candidate

One candidate only. No parameter sweep.

For each fold and horizon:
1. fit a state-only event rate for the five shipped states using Jeffreys
   smoothing: `(events + 0.5) / (n + 1)`;
2. apply weighted isotonic / pooled-adjacent-violators over
   calm <= watch <= caution <= elevated <= risk-off, weights = state training n;
3. leave the shipped conjunction bump **byte-for-byte unchanged**;
4. displayed test probability = fitted state probability +
   `max(0, hot_count-1) * _CONJ_BUMP[h]`, capped exactly as production.

No hot-count coefficient, smoothing prior, first test year, fold geometry, or
monotonic rule may be changed after outcome inspection.

## Authority preservation constraint

The H21 fitted state-only surface must preserve the current Market-State authority
partition relative to the shipped unconditional H21 base:
- calm/watch/caution: not above base;
- elevated/risk-off: above base.

Enforce this as a fitting constraint, not a post-hoc exclusion. If a fold cannot
produce a finite monotone surface satisfying that partition, that fold/candidate
is invalid and the promotion verdict is FAIL.

This constraint exists because Risk Radar binding authority uses the state-only
H21 above-base flag. A probability research candidate may not silently rewrite
who can receive veto authority.

## Frozen comparator

Comparator = the currently shipped static displayed probability on the exact same
test rows:
`engine.risk_radar._drawdown_prob(state, hot_count, current_calib)[h]`.

The current and candidate arms must have identical date/outcome population
fingerprints within each fold/horizon.

## Primary metrics

For each H5/H10/H21 across all concatenated 2010-2025 out-of-fold rows:
- Brier score;
- paired candidate-current Brier delta;
- 90% circular moving-block bootstrap CI of that paired delta, block length = H;
- weighted absolute calibration error over exact displayed-probability cells;
- mean displayed probability and observed base rate;
- date/outcome population SHA-256.

Also report per-year Brier deltas and the count of test years in which candidate
beats current.

Daily windows overlap and are not independent episodes; the block bootstrap is the
uncertainty view, not an independence claim.

## Promotion bar

This research candidate earns only "promotion-worthy for a separate implementation
decision" if **all** hold:

1. identical test populations for candidate/current at every fold/horizon;
2. authority partition preserved in every H21 fold;
3. aggregate paired Brier delta < 0 at H5, H10 and H21;
4. 90% paired block-bootstrap CI upper bound <= 0 at H5, H10 and H21;
5. aggregate WACE is non-worse at all three horizons;
6. candidate beats current in at least 10 of the 16 annual folds at each horizon.

Anything else is NOT promotion-eligible. No second candidate may be fit to these
observed fold results in this wave.

## Evidence / durability

The implementation must produce:
- deterministic research script;
- separate dedicated test file, path-disjoint from active Risk Radar guard PRs;
- source/input hashes;
- per-fold training/test date ranges and population hashes;
- candidate surfaces by fold;
- aggregate + annual metrics;
- committed result and verification receipt;
- Agent OS discovery for the material verdict.

No collector, calibration overlay, review log, forward ledger, runtime model, UI,
or policy state may be written.
