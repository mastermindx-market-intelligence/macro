# Risk Radar Episode Warning-Path Preregistration — 2026-09-21

Status: descriptive research protocol, frozen before generating the new warning-path metrics.

## Question

Did the existing US Risk Radar merely flash risk sometime before a selloff, or did its actual gated headline state remain meaningfully elevated near the fixed reference peak?

## Frozen sample and anchors

Use exactly the five episode names and exact hint dates already committed in `scripts/research/risk_radar_episode_atlas.py`: 2018-09-20, 2020-02-19, 2022-01-03, 2023-02-02, 2024-07-16. These dates are the reference anchors. Do not replace them with the nearest `detect_events()` onset, optimize them to a better local peak, add/remove episodes after seeing the new metrics, or treat the five selected episodes as an unbiased population.

## Frozen measurements

For T-21, T-5, T-1, T0 and T+5, report the actual `state_series()` headline state, context-gate status as open/closed/unknown, signal/subscore coverage, and date. For T-21..T0 and T-5..T0 report sessions known, sessions at caution-or-higher, sessions at elevated-or-higher, each fraction, and the consecutive caution-or-higher run ending at T0.

A warning is `caution` or higher. A loud alert is `elevated` or `risk-off`. These are existing state labels, not new thresholds. “EARLY” leg classifications remain historical context only and are not evidence of persistence.

Forward outcomes at each fixed anchor use the canonical US grader semantics from `engine.risk_radar_audit._grade_entry` for h5/h10/h21. Strip wall-clock `graded_at` and classification prose; retain base price, forward drawdowns and hit booleans. The existing 63-observation drawdown remains descriptive and is not used as a tuning target.

## Interpretation ceiling

Selected episodes, overlapping state days, historical reconstructed signals and genuinely issued forward forecasts are distinct evidence classes. This study cannot validate today's probability calibration, authorize a weight/threshold/policy change, or claim out-of-sample skill. Missing inputs remain missing; closed/unknown context gates are not silently treated as open.

Primary result: whether warning persistence near T0 differs materially from the old “first elevated anywhere in T-63..T+5” story. Any model change requires a separate preregistered study and accepted promotion evidence.
