# Risk Radar Replay-Parity Rerun — Preregistration

Status: frozen rerun protocol. Commit this file before generating corrected historical outcomes.

## Material invalidator

Merged PR #7632 (7c6e35163c9f67087ffe174a7ab3810f47ce6a45) proved that the historical US Risk Radar replay did not reproduce the shipped live escalation state machine. The old replay used rejected count-only Tier-A conjunction and permissive Tier-B escalation. The corrected replay now calls the same canonical row-level transition as live compute() with the original causal signal row.

This invalidates replay-derived state buckets from #7586, #7599, #7608, and closed-unmerged #7611 for any state/probability/gate change. Recorded issued-forecast evidence is separate and is not rerun here.

## Frozen rerun rule

Rerun the four existing studies with their prior target definitions, episode anchors, horizons, windows, bootstrap settings, and fixed thresholds unchanged. The only permitted semantic change is the merged #7632 production-parity evaluator.

1. Warning-path study: same five fixed anchors, T-21/T-5/T-1/T0/T+5 reads, same h5/h10/h21 forward grader.
2. Gate selectivity/latency: same >=5% / 21-native-observation target, same current production broad-market gate, same full and 2020+ populations, same fixed event view.
3. Caution persistence: same five consecutive caution-or-higher sessions, same >=5% / 21-native-observation target, same full and 2020+ populations; no streak-length sweep.
4. State ladder: same H5/H10/H21 >=5% native-observation targets, full / 2006+ / 2020+ windows, 1,000-draw horizon-length moving-block bootstrap, 90% intervals, seed root 260921, thin-cell n<100 rule, and configured state-only comparison.

No probability, conjunction bump, band, score, weight, gate threshold, policy, ranking, sizing, ledger, or capital authority may change in this wave.

## Evidence comparison

For every rerun, report corrected result and the delta versus the pre-parity result where comparable. Distinguish changed historical state composition caused by evaluator parity; unchanged forward price-outcome populations/fingerprints; any prior product interpretation that survives; and any prior interpretation that must be weakened or reversed.

Do not cherry-pick a window or horizon after seeing the corrected results.

## Provenance / supersession

Pre-parity results remain historical provenance in their merge commits: #7586 warning persistence, #7599 gate selectivity/latency, #7608 caution persistence, and #7611 state-ladder calibration (closed unmerged after invalidation).

The current corrected receipts must name #7632 as the invalidator and this rerun protocol as the recovery authority. Old evidence must not be silently presented as current.

## Completion

Require focused method tests green before outcome inspection; all relevant Risk Radar owning suites green after regeneration; no collector run and no data mutation; committed input hashes and result hashes; Agent OS discovery/handoff updating the corrected scientific frontier; and an explicit statement that live model parameters remain unchanged.
