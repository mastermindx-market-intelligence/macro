# Risk Radar Gate Latency / Suppression Results — 2026-09-21

Protocol commit: `5c40f881e1e3195b9dd171e078d3d1f211da4015`.

Descriptive research only. No live gate, threshold, probability, policy or capital authority changed.

## Daily 5% / 21-observation tradeoff

| Window | Raw precision | Gated precision | Raw recall | Gated recall | Raw fire rate | Gated fire rate | FP removed | TP lost | FP removed / TP lost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full usable history | 20.6% | 41.0% | 70.9% | 28.7% | 60.6% | 12.3% | 3344 | 610 | 5.48 |
| 2020+ | 23.2% | 39.3% | 90.8% | 36.7% | 69.0% | 16.5% | 716 | 159 | 4.50 |

Daily windows overlap; these counts are not independent episodes.

## Paired interpretation

- Full history: precision 20.6% → 41.0%, recall 70.9% → 28.7%, fire rate 60.6% → 12.3%.
- 2020+: precision 23.2% → 39.3%, recall 90.8% → 36.7%, fire rate 69.0% → 16.5%.
- The ungated state is too frequent to substitute for the loud gate. The relevant product question is how to preserve the quieter early-warning information while keeping loud confirmation selective; this study does not authorize a gate change.

## Distinct-event confirmation timing

- Complete 5%/21-observation event anchors: **110**.
- Events with a raw loud reading by T0: **103** (93.6% of anchors).
- Events with gated loud confirmation by T0: **42** (38.2% of anchors).
- Among raw-pre-T0 events: after T0 but before 5% breach **10**; after breach **11**; never through T+21 **40**.
- First-gated minus first-raw latency: median **3.0** sessions; 75th percentile **27.5** sessions (where both exist).

## Gate-leg attribution

Suppressed known raw-loud days: **3956** — price leg only closed 1077, breadth leg only closed 179, both closed 2700. Raw-loud days with unknown gate evidence: 0.

## Evidence ceiling

This is a current-code historical reconstruction, not genuinely issued forecast history. Daily observations overlap, event anchors are algorithmic labels, and the study is not a parameter search. Any gate/model change requires a separate preregistered candidate.

Method correction before acceptance: the first successful run included all-missing subscore warmup rows in the full-history denominator. A canonical state_accuracy parity check exposed the mismatch. The accepted run masks those rows exactly as the canonical evaluator does; no threshold, target, horizon or gate rule changed. The 2020+ result was unchanged by this warmup-only correction.
