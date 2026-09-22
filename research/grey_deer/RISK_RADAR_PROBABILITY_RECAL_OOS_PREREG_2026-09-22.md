# Risk Radar Probability Recalibration — OOS Candidate Preregistration

Status: frozen candidate-study protocol. Commit this file before generating candidate probabilities or holdout metrics.

Source base: `9e9da53a671f3420b2cab9cca20b131c811a05df`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@0471cea4f891da1ec0c9fbeff10a9391f9cdd90f`, Skillpack 1.0.1/bootstrap 1.

## Question

Can a simple state-only probability surface fitted **without 2020+ outcomes** improve the actual displayed US Risk Radar pullback probabilities on the 2020+ holdout, while preserving the shipped state machine, conjunction bump, and Market-State authority partition?

This study changes no live probability, state, band, score, weight, conjunction rule, gate, policy, sizing, ranking, ledger, or capital authority.

## Frozen target and replay semantics

Use the merged post-#7632 exact live-state replay. Build `leading_signals()`, `subscore_series()`, and `state_series(..., sigs=sigs)` from the same causal signal frame.

Targets are the same as the accepted displayed-probability audit:
- >=5% maximum SPY close-relative loss;
- native SPY closing observations;
- horizons H5, H10, H21;
- no resampling to forecast dates;
- no forward-fill of missing prices;
- only complete finite positive-price windows.

Training population: all eligible dates strictly before 2020-01-01.
Holdout population: all eligible dates on/after 2020-01-01.
Daily windows overlap and are not independent episodes.

## Frozen candidate construction

Only the **state-only** surface may change. The existing `_CONJ_BUMP` is copied byte-for-byte into candidate evaluation.

For each horizon independently:

1. Count training events and observations for each shipped state in
   `calm < watch < caution < elevated < risk-off`.
2. Apply Jeffreys smoothing per state:
   `p = (events + 0.5) / (n + 1.0)`.
3. Apply weighted pooled-adjacent-violators (PAV) to those five smoothed state
   probabilities with weights `n + 1.0`, enforcing non-decreasing probability
   across the shipped state order.
4. Do not grid-search, tune a prior strength, merge states by hand, optimize the
   conjunction bump, or inspect holdout outcomes before the candidate is frozen.

Displayed candidate probability on a date is:
`min(0.95, candidate_state_probability + max(hot_tier_a_count - 1, 0) * existing_CONJ_BUMP[horizon])`.

The current comparator is the shipped `_PROB_CAL` plus the exact same existing conjunction bump.

## Hard authority constraint

The H21 candidate is **inadmissible** if it changes the current authority partition used by `_market_state_authority`:

- calm: below the shipped H21 unconditional base;
- watch: below base;
- caution: below base;
- elevated: above base;
- risk-off: above base.

The comparison base is the shipped `_PROB_BASE["h21"]`. Do not clamp a fitted candidate across this boundary to make it pass; record the candidate as authority-inadmissible.

All candidate values must also lie in [0, 0.60], matching the existing review-loop probability rail.

## Frozen holdout metrics

For current and candidate on the identical 2020+ population, report by H5/H10/H21:

- n, events, base rate;
- mean displayed probability;
- Brier score;
- Brier skill versus the holdout unconditional base;
- calibration-in-the-large gap;
- weighted absolute exact-cell calibration error;
- exact-cell counts and observed rates;
- population/outcome fingerprint.

Primary paired uncertainty: 1,000 horizon-length moving-block bootstrap draws on holdout dates, seed root 260922. Report the 90% interval for `Brier_candidate - Brier_current` at each horizon.

## Frozen promotion bar

This research candidate may be called **promotion-eligible** only if all are true:

1. authority partition is preserved;
2. candidate state surfaces are monotonic and inside [0, 0.60];
3. point Brier score is <= current at H5, H10, and H21;
4. H21 paired Brier-delta 90% interval has upper bound <= 0;
5. H5 and H10 paired Brier-delta 90% interval upper bounds are <= +0.002 absolute;
6. weighted absolute calibration error is not worse by more than 0.005 absolute at any horizon;
7. population and outcome fingerprints match the accepted corrected-replay population for the same horizon.

Passing this bar does **not** authorize a live write. It produces a bounded calibration candidate for separate review/promotion. Failing it means no probability change.

## Evidence boundary

Reconstructed historical replay, issued forward forecasts, and future prospective forecasts remain separate evidence classes. The current issued probability audit is immature and has zero qualifying events; it is not spliced into fitting or used to manufacture validation.

No `data/risk_radar/calibration.json`, review log, forward ledger, production data, or model runtime file may be written by the study.
