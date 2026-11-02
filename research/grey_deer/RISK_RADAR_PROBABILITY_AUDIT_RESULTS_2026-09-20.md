# US Risk Radar — issued-probability diagnostic

## Finding: the forward record cannot yet establish downside discrimination

Protocol was committed at `9659c1b7b41efc6c54e32c3cd79ba91c060e287b` before outcome
inspection. The immutable source is macro `9a481ef520e397853c9f5a8edd120cfff528ce16`.
Ledger SHA-256: `612c4ecb5cfe1d794b42953ca0d0c8c9d5f43a294e7b03e60d10f74e5fc468a6`.
The source contains 51 recorded forecast dates, 2026-06-23 through 2026-09-17.
33 have usable recorded grades; 18 have no recorded grade. This audit neither
imputes those outcomes nor assumes all 18 are immature.

| Horizon | Eligible forecast days | Mean issued probability | Recorded >=5% events | Paired baseline days |
|---|---:|---:|---:|---:|
| 5 sessions | 33 | 2.8727% | 0 | 29 |
| 10 sessions | 33 | 7.6970% | 0 | 29 |
| 21 sessions | 33 | 15.5455% | 0 | 33 |

The 33 dates cover 2026-06-23 through 2026-08-18. These are overlapping daily
forecasts, not 33 independent crises. No positive target event appears in the
eligible observations. Therefore this sample does not demonstrate crash detection,
early-warning discrimination, or successful calibration of today's model.
Zero observed events also does NOT establish zero future risk or disprove every
positive probability. This is a limited realized sample, not a population theorem.

## Recorded-base comparison — same rows, no backfilled baselines

| Horizon | Model squared error | Recorded-base squared error | Model minus baseline |
|---|---:|---:|---:|
| 5 sessions, paired 29 | 0.000804 | 0.001296 | -0.000492 |
| 10 sessions, paired 29 | 0.005779 | 0.007396 | -0.001617 |
| 21 sessions, paired 33 | 0.024500 | 0.031684 | -0.007184 |

Lower Brier loss is better **on these observed rows**. Because every eligible
outcome is negative, merely issuing smaller probabilities reduces this loss.
The negative deltas must NOT be presented as validated predictive skill. Four early
rows have no recorded 5-/10-session baseline; the diagnostic retains their model
forecasts but excludes them from paired comparisons. No modern baseline is substituted.

## What the new capability does

`engine.risk_radar_scorecard.probability_audit` extends the existing scorecard
producer with horizon-specific forecast/outcome comparison, fixed reliability bins,
matched baseline error, event-coverage flags, and typed exclusions. The existing
Market State reader passes this block to the Risk Radar view-model unchanged.
Existing alert, recovery, monitoring and international scorecard fields are preserved.
The same inputs reproduce the same diagnostic; all ledger bytes remain unchanged.

This does not install a new score, retune weights, authorize trades, change a policy,
regrade history, or release held PR6989/7236 work. No model promotion is issued.
Publication and model-version histories are not proven by ledger receipt chronology.

## Next research and the actual UI boundary

Use the existing risk_radar_backtest and episode-atlas owners for a separately frozen,
version-specific evaluation with real adverse episodes and held-out windows. Preserve
raw issue-time definitions and first-publication clocks; evaluate recall/lead time and
false reassurance alongside probability loss. Do not tune on the zero-event slice above.
The immediate consumer remains the existing scorecard machine projection, not a new monitor.

The proposed compact Method & track record UI partial was platform-blocked before
creation. The original path was checked absent; it was not retried, renamed or inlined
as a workaround. Thus no new probability-audit UI is claimed here. That lane remains
blocked; the independent diagnostic, tests and this real-input analysis proceeded.
Evidence and exact values: `evidence/probability-audit-20260920/result.json`.
