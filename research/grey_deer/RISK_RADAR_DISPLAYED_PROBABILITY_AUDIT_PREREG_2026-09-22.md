# Risk Radar Displayed-Probability Audit — Preregistration

Status: descriptive no-fit audit. Freeze this file in Git before inspecting new outcome metrics.

Source base: `912feaa2b13959a6cca4d3f1472188b4a4d702bb`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@4ca1b97e65de9d4ba8c868b9d708fb7620a8a76f`, Skillpack 1.0.1/bootstrap 1.
Replay prerequisite: merged parity repair #7632 and corrected evidence rerun #7666.

## Question

Risk Radar displays pullback probabilities from the shipped combination of:

1. the exact **gated live state**; and
2. the exact count of Tier-A scares whose sub-score is at or above the existing caution cut.

The engine then applies the existing state probability plus the fixed conjunction bump:
`p_h = state_probability_h + max(0, hot_tier_a_count - 1) * conjunction_bump_h`,
capped at 0.95.

This study asks whether that **complete displayed probability surface**, as currently shipped,
matches realized >=5% SPY downside frequencies well enough to describe honestly. It does not
fit, search, smooth, isotonic-regress, or change any probability.

## Frozen replay object

Use `leading_signals()` -> `subscore_series()` -> corrected
`risk_radar_backtest.state_series(..., sigs=sigs)`. The state transition must therefore use the
same validated armed+confirm conjunction, Tier-B exclusions, and broad-market gate as live
`compute()`.

For each eligible date:
- `state` = corrected gated state;
- `hot_tier_a_count` = number of Tier-A sub-scores >= the shipped caution cut;
- `displayed_probability` = `engine.risk_radar._drawdown_prob(state, hot_tier_a_count)`
  for the selected horizon.

No reconstructed probability formula is permitted outside that canonical function.

## Frozen targets and populations

Target: SPY close-relative maximum loss of at least 5% within the next native H closing
observations. Evaluate exactly H5, H10 and H21 using the corrected native-price semantics:
no resampling to forecast dates, no forward-fill of missing prices, and only complete finite
positive-price windows.

Report exactly:
1. full usable history;
2. 2006-01-01+;
3. 2020-01-01+.

Daily windows overlap and are not independent; all counts must be printed.

## Frozen diagnostics

For every horizon x date window report:

- n, event count, unconditional base rate;
- Brier score of the displayed probability;
- base-rate Brier score as the no-information comparator;
- Brier skill score = 1 - model_brier/base_brier when defined;
- mean displayed probability and observed event rate;
- calibration-in-the-large gap = mean_probability - observed_rate;
- weighted absolute calibration error over **exact displayed probability cells**;
- root weighted squared calibration error over exact cells.

For every exact displayed-probability cell report:
- probability;
- n;
- event count;
- observed event rate;
- observed-minus-displayed gap;
- 90% moving-block bootstrap interval for the observed event rate;
- constituent state x hot-count composition.

Cells with n < 100 are marked `thin`. Do not merge thin cells after seeing results.

## Frozen uncertainty

Use a deterministic circular moving-block bootstrap with block length equal to the evaluated
horizon, 1,000 draws, 90% intervals, seed root 220922. Bootstrap:
- each exact-cell observed rate;
- Brier score;
- calibration-in-the-large gap.

No alternate confidence level, binning, block length, population, target, or horizon may be
selected after outcome inspection.

## Frozen integrity checks

Before accepting results:

- population/outcome fingerprints must match corrected `state_accuracy` for each horizon/window;
- a synthetic test must prove the audit calls the canonical `_drawdown_prob` surface;
- a synthetic test must prove increasing hot-count changes the displayed probability exactly by
  the shipped conjunction bump until the cap;
- a synthetic test must prove the same probability cell aggregates dates without changing the
  state/output used to generate it;
- no collector, calibration overlay, forecast ledger, model state, public probability artifact,
  or policy artifact may be written.

## Interpretation ceiling

This is current-code historical reconstruction, not genuinely issued probability history.
It may identify over/under-confidence or thin cells, but it cannot authorize a retune.
Issued/prospective forecast evidence remains a separate and higher-authority evidence class.

A favorable historical calibration result does not validate current live probabilities by itself.
An unfavorable result does not license a fitted replacement. Any live probability change requires
a separately preregistered candidate, accepted promotion evidence, and the applicable authority gates.
