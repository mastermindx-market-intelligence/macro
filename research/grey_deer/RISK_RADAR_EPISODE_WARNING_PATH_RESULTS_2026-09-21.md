# Risk Radar Episode Warning-Path Results — 2026-09-21

Protocol: `RISK_RADAR_EPISODE_WARNING_PATH_PREREG_2026-09-21.md`, committed as `31b05b7dda4be22be2ee55217aecfd475d2ed569` before the new warning-path metrics were generated.

This is reconstructed historical research under current committed code and stored inputs. It is not a record of what was actually published on those dates, not an unbiased episode sample, and not authority to retune the live model.

## Main result

The old atlas's “EARLY” label often overstates persistence near the peak. The actual gated headline path is more informative.

| Fixed reference | T-21 | T-5 | T-1 | T0 | Gate at T0 | caution+ in T-21..T0 | elevated+ in T-21..T0 | caution+ run into T0 | h21 max loss |
|---|---|---|---|---|---|---:|---:|---:|---:|
| 2018-09-20 | caution | calm | calm | watch | closed | 8/22 | 0/22 | 0 | -6.87% |
| 2020-02-19 | caution | caution | caution | caution | closed | 22/22 | 0/22 | 22 | -29.11% |
| 2022-01-03 | caution | caution | caution | caution | closed | 22/22 | 0/22 | 22 | -9.73% |
| 2023-02-02 | risk-off | caution | caution | caution | closed | 18/22 | 2/22 | 10 | -5.29% |
| 2024-07-16 | caution | caution | caution | caution | closed | 22/22 | 0/22 | 22 | -8.41% |

Four of five fixed anchors therefore carried persistent caution into T0; 2018 did not. None carried an elevated-or-higher gated headline at T0 because the broad-market context gate was closed at all five anchors.

## Interpretation

The research does **not** show that the context gate is wrong. It shows a sharper model question: the current engine often detects deterioration at the caution tier well before the selected loss windows, while the broad-market gate suppresses escalation to elevated. The next study must measure whether that suppression removes mostly false positives or also delays useful escalation into selloffs. That question must be answered on a broader event/non-event population before any threshold or gate change.

2018 is the important counterexample to a simplistic “early signal = good warning” story: several component legs first elevated months earlier, but the actual headline had faded to calm by T-5/T-1 and only watch at T0. The new persistence fields prevent that early flash from being presented as a warning that remained active into the peak.

COVID, 2022 and Aug-2024 are the opposite pattern: caution persisted through every known session in the final 21-session window. SVB shows a third shape: a brief risk-off state earlier in the window, then a ten-session caution run into the fixed reference date.

## Evidence and limits

The run used the same committed 17-input set as the corrected replay, with the current committed breadth file additionally refreshed on main; no collector ran and no input file was modified. The causal bubble-extension spot-check still matches exactly on the truncated and full frames.

The five fixed anchors were not selected to estimate a population average. Daily states overlap heavily. The forward h5/h10/h21 losses use the existing canonical grader semantics. The 63-observation drawdown remains descriptive only.

No probability, calibration, leg weight, band, context-gate threshold, policy, ledger, ranking or capital authority changed. A gate-latency/false-positive study is the next research dependency, not a live-model retune.
