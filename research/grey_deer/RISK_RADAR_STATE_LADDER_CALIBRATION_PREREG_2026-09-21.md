# Risk Radar State-Ladder Calibration Study — Preregistration

Status: descriptive research protocol. Freeze this file in Git before inspecting the new outcome metrics.

Source base: `e9c6210959520c90fb12ad98632465b7e93909d8`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@74b475545e179a3256bfebe6b5226f54231cf1cb`, Skillpack 1.0.1/bootstrap 1.

## Product / model question

Risk Radar presents an ordered state ladder:
`calm < watch < caution < elevated < risk-off`.
The engine also ships state-conditional pullback probabilities. This study asks whether
the **current gated reconstructed states** still separate realized downside risk in that
same order, and whether the configured state-only probability surface remains directionally
consistent with the current historical reconstruction.

No score, state band, probability, gate, conjunction bump, policy, ranking, sizing,
ledger, or capital authority changes are permitted in this study.

## Frozen targets and windows

Target at each horizon is a SPY close-relative maximum loss of at least 5% within the
next native **5, 10, or 21** SPY closing observations. Use the corrected native-price
window semantics from `engine.risk_radar_backtest.state_accuracy`: no resampling to
forecast dates, no price forward fill, and only complete finite positive-price windows.

Report exactly three date windows:
1. full usable history;
2. 2006-01-01+ (the era named by the current probability-calibration provenance);
3. 2020-01-01+ (fixed modern slice).

Daily windows overlap and are not independent episodes. All counts must be printed.

## Frozen state analysis

Use the existing `state_series(subscore_series(leading_signals(), _calib()), _calib())`
with the shipped context gate. Unknown all-missing subscore rows are excluded exactly as
the corrected canonical evaluator excludes them.

For every horizon × date window × state, report:
- eligible observations and event observations;
- realized event rate;
- lift versus that window's unconditional base rate;
- the configured **state-only** probability from `_PROB_CAL` / current calibration overlay;
- observed minus configured probability.

Do not include the conjunction bump in the state-only comparison. It is a separate
conditioning variable and would make a state-ladder calibration test ambiguous.

The primary ordering diagnostic is point-estimate monotonicity of realized event rates
across the fixed state order. Report every adjacent difference explicitly; do not collapse
a violation into an average score.

## Frozen uncertainty method

Because daily forward windows overlap, calculate 90% moving-block bootstrap intervals for
each state event rate and each adjacent state-rate difference. Block length is fixed to the
target horizon (5, 10, or 21 observations), 1,000 draws, deterministic seed 260921.

A state with fewer than 100 eligible observations in a window is still printed but marked
`thin`; its interval is descriptive and cannot by itself support a calibration change.
No alternate confidence level, block length, state merge, threshold, horizon, or date
window may be selected after reading results.

## Interpretation ceiling

This is reconstructed historical calibration evidence, not genuinely issued forecast
history and not a license to rewrite the current probability table. A monotonic point
estimate does not prove calibration; a non-monotonic result does not automatically justify
merging states or changing bands. Any probability/state change needs a separate
preregistered candidate, prospective or accepted promotion evidence, and the existing
authority gates.

The current forward probability audit remains a distinct evidence class. Do not mix its
33 issued dates with reconstructed history or treat zero realized issued events as proof
for or against the historical ladder.

## Completion / evidence

The study requires:
- a deterministic research script;
- discriminating synthetic tests enrolled in an existing Risk Radar CI test lane;
- exact parity with canonical `state_accuracy` populations/outcome fingerprints;
- source, calibration, and input hashes;
- all state cells, adjacent differences, bootstrap intervals, and thin-cell flags;
- an explicit comparison to the configured state-only probabilities;
- a committed result/verification receipt.

No collector, calibration overlay, forward ledger, public probability, or production model
state may be written.
