# Risk Radar Gate Latency / Suppression Preregistration — 2026-09-21

Status: descriptive research protocol. Freeze this file in Git before generating the new outcome metrics.

Source base: `4273786fa0c3a84efed2a793584f740fe110265a`.
Protected procedure: `mastermindx-market-intelligence/Mastermind@76f1ac50c3435fff9387b168286c38e7b07b076a`, Skillpack 1.0.1/bootstrap 1.

## Question

The current loud Risk Radar gate requires the raw state to be elevated-or-higher **and**
SPY below its 200-session average **and** breadth weakness at or below the existing
0.40 causal percentile. Prior research showed a strong precision/recall tradeoff.
The new question is narrower: **how much useful warning time does that gate delay
or remove, relative to how many false positives it suppresses?**

This study changes no live probability, band, leg weight, gate threshold, policy,
ledger, ranking or capital authority.

## Frozen target and populations

Primary product target: SPY close-relative maximum loss of at least 5% within the
next 21 native SPY closing observations. The price-window semantics must match the
corrected `engine.risk_radar_backtest.state_accuracy` path: no resampling to forecast
dates, no forward filling missing prices, and only complete positive-price windows.

Report the full usable history and a fixed 2020-01-01+ slice. Daily windows overlap
and are not independent episodes; both counts and that limitation must be printed.

## Frozen state definitions

Reconstruct the current **pre-gate** headline state from the existing state-machine
logic only: current calibration bands, Tier-A origin, conjunction escalation, and
Tier-B escalation. A regression must prove this helper equals the production
`state_series` when the production context gate is forced open. Do not invent a
second score or alter the scare composition.

`raw_loud` means pre-gate state is `elevated` or `risk-off`.
`gate_open` means both currently shipped gate legs are known and true.
`gated_loud = raw_loud AND gate_open`. Unknown gate inputs remain unknown and are
excluded from gate-performance denominators rather than silently treated as open.

For each daily population report raw versus gated precision, recall, F1, fire rate,
TP/FP/FN/TN, and the exact evaluated-population fingerprint. Also report:
`FP_removed`, `TP_lost`, and `FP_removed_per_TP_lost` (null if no finite
denominator). No alternate thresholds or parameter sweeps are allowed.

## Frozen event-latency analysis

Create severe-event anchors with the existing `detect_events` implementation using
`fwd=21`, `depth=0.05`, `min_gap=21`. This is a fixed secondary event view of
the same 5%/21-observation product target, not an optimization over event definitions.

For each complete event anchor, inspect T-21..T0 for the first `raw_loud` and first
`gated_loud`. If raw loud appears before or at T0 but gated loud does not, continue
the gated search through T+21. Separately record the first post-T0 session where SPY
is down at least 5% from the T0 close.

Primary event outputs, restricted to events with a raw loud reading by T0:
- raw and gated event recall by T0;
- first-gated minus first-raw latency in trading observations;
- counts where gated confirmation is before T0, after T0 but before the 5% breach,
  after the breach, or never arrives through T+21;
- median and 75th-percentile latency for events where both readings exist.

Also attribute suppressed raw-loud observations to the current gate components:
price leg closed, breadth leg closed, both closed, or unknown. This is attribution
of the shipped gate, not a screen for a replacement gate.

## Interpretation rules

The old `RISK_RADAR_TUNING.md` result is prior evidence, not a target to reproduce.
This run may compare current numbers with it descriptively, but must not tune until
they match. If the current result disagrees, preserve the disagreement and investigate
data/code/version causes.

A finding that the gate delays alerts does not by itself justify loosening it; a
finding that it removes false positives does not by itself justify keeping it.
Report the paired tradeoff. Any change to the gate, thresholds, probabilities or
authority requires a separate preregistered candidate and promotion review.

The five fixed warning-path exemplars from PR 7586 are motivational examples only;
they are not added to, removed from, or weighted in this broader population study.

## Completion / evidence

The research wave is complete only when a deterministic script and focused tests
produce a committed receipt with source commit, calibration identity, all input
hashes, date coverage, daily results, event-latency results, and explicit evidence
ceilings. No collector or forward ledger may be advanced during the study.
