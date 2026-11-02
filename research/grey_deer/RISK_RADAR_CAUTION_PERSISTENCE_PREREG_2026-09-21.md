# Risk Radar Caution-Persistence Display Study — Preregistration

Status: descriptive research protocol. Freeze this file in Git before inspecting the new outcome metrics.

Source base: `1dc11fb3eb326393c803bc2eff408db89bb91bc1`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@0f4aeae4d25f3770474a7ac70e0ce12af6e2d075`, Skillpack 1.0.1/bootstrap 1.

## Product question

Risk Radar already distinguishes `watch`, `caution`, `elevated`, and `risk-off`.
The warning-path study showed that selected selloffs often carried caution for many
sessions even while the loud-alert gate remained closed. The next question is
whether **persistent caution** is meaningfully different from a transient caution
reading, enough to justify a display-tier “risk building persists” cue.

This study may inform presentation only. It cannot change the live state machine,
probabilities, weights, bands, gate thresholds, policy, ranking, sizing, or capital authority.

## Frozen construction

`caution_plus` = the existing shipped gated headline state is `caution`,
`elevated`, or `risk-off`.

`persistent_caution_5` = caution_plus is true for **five consecutive known SPY
sessions ending on the observation date**. Five is fixed as one trading week for
product readability, not selected from a performance sweep. Unknown/missing state
breaks the streak and is excluded from the eligible denominator for the affected date.

## Frozen target and populations

Primary target: SPY close-relative maximum loss of at least 5% within the next
21 native SPY closing observations. Use the corrected native-price semantics:
no resampling to forecast dates, no forward-filling missing prices, and only
complete finite positive-price windows.

Report full usable history and a fixed 2020-01-01+ slice. Daily observations
overlap and are not independent episodes.

Compare three pre-specified states on the exact same eligible population:
1. all eligible sessions (base rate);
2. `caution_plus`;
3. `persistent_caution_5`.

For caution_plus and persistent_caution_5 report event rate/precision, recall,
fire rate, F1, lift versus the all-session base rate, TP/FP/FN/TN, population
fingerprint, and count of eligible observations. Do not test alternate streak
lengths.

## Fixed event view

Use `detect_events(fwd=21, depth=0.05, min_gap=21)` for a secondary distinct-event
view. For every complete anchor report whether caution_plus and
persistent_caution_5 occurred by T0, first occurrence offset from T0, and whether
persistent caution began before the first 5% breach.

Report event recall and median lead only; do not optimize the event definition,
anchor date, or streak length from the observed results.

## Interpretation ceiling

This is a display-tier study, not a promotion gate. A favorable result may justify
surfacing duration/persistence context in Risk Radar, but not escalating caution to
elevated, changing drawdown odds, or altering any trading response. A null result
means the persistence badge should not imply extra predictive edge.

The gate-latency study and the five warning-path exemplars are prior motivation only;
they are not added as weighted observations or used to choose the five-session rule.

## Completion / evidence

The wave requires a deterministic script, discriminating synthetic tests, canonical
state/output parity, input/source hashes, date coverage, exact population fingerprints,
and a committed result receipt. No collector, calibration overlay, forward ledger, or
production model state may be written.

Any user-facing implementation is a separate subsequent capability slice. Its copy
must distinguish duration (“has persisted”) from predictive validation (“more likely”)
unless the latter is independently supported.
