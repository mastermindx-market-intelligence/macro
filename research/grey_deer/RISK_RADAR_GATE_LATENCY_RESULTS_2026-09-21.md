# Risk Radar Gate Latency / Suppression Results — 2026-09-21

Protocol commit: `5c40f881e1e3195b9dd171e078d3d1f211da4015`.

Descriptive research only. No live gate, threshold, probability, policy or capital authority changed.

## Daily 5% / 21-observation tradeoff

| Window | Raw precision | Gated precision | Raw recall | Gated recall | Raw fire rate | Gated fire rate | FP removed | TP lost | FP removed / TP lost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full usable history | 21.0% | 41.9% | 68.1% | 28.3% | 57.1% | 11.9% | 3132 | 576 | 5.44 |
| 2020+ | 24.5% | 42.0% | 88.1% | 36.7% | 63.4% | 15.4% | 648 | 151 | 4.29 |

Daily windows overlap; these counts are not independent episodes.

## Paired interpretation

- Full history: precision 21.0% → 41.9%, recall 68.1% → 28.3%, fire rate 57.1% → 11.9%.
- 2020+: precision 24.5% → 42.0%, recall 88.1% → 36.7%, fire rate 63.4% → 15.4%.
- The ungated state is too frequent to substitute for the loud gate. The relevant product question is how to preserve the quieter early-warning information while keeping loud confirmation selective; this study does not authorize a gate change.

## Distinct-event confirmation timing

- Complete 5%/21-observation event anchors: **110**.
- Events with a raw loud reading by T0: **103** (93.6% of anchors).
- Events with gated loud confirmation by T0: **41** (37.3% of anchors).
- Among raw-pre-T0 events: after T0 but before 5% breach **9**; after breach **12**; never through T+21 **41**.
- First-gated minus first-raw latency: median **3.0** sessions; 75th percentile **23.0** sessions (where both exist).

## Gate-leg attribution

Suppressed known raw-loud days: **3710** — price leg only closed 964, breadth leg only closed 177, both closed 2569. Raw-loud days with unknown gate evidence: 0.

## Evidence ceiling

This is a current-code historical reconstruction, not genuinely issued forecast history. Daily observations overlap, event anchors are algorithmic labels, and the study is not a parameter search. Any gate/model change requires a separate preregistered candidate.

Method correction before acceptance: the first successful run included all-missing subscore warmup rows in the full-history denominator. A canonical state_accuracy parity check exposed the mismatch. The accepted run masks those rows exactly as the canonical evaluator does; no threshold, target, horizon or gate rule changed. The 2020+ result was unchanged by this warmup-only correction.
