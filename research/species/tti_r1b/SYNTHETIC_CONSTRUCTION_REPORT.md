# R1-B v4 synthetic construction replay

**SYNTHETIC ONLY — not market data, trading results, or live signals.**

No edge or probability is estimated. Values are fabricated test inputs.
An earliest entry is a scheduled reference time, not an available quote or fill.
Times below are UTC; all session calculations use the existing exchange calendar.

## Reclaim

| Selector | Candidate | Confirmation / decision | Earliest entry | Candidate low | Episode low |
|---|---|---|---|---:|---:|
| BASE_FRESH_LOW | 13:45:00 | 13:45:00 | 13:50:00 | 98.60 | 98.60 |
| EXHAUSTION_FORMING | 13:45:00 | 13:45:00 | 13:50:00 | 98.60 | 98.60 |
| RECLAIM_ONLY | 13:45:00 | 13:50:00 | 13:55:00 | 98.60 | 98.55 |
| EXHAUSTION_RECLAIM | 13:45:00 | 13:50:00 | 13:55:00 | 98.60 | 98.55 |

First candidate: **RECLAIM**. Frozen reclaim level: 98.80; continuation level: 98.10.
Independent control anchors: 1. Future family labels never select the controls.

## Continuation

| Selector | Candidate | Confirmation / decision | Earliest entry | Candidate low | Episode low |
|---|---|---|---|---:|---:|
| BASE_FRESH_LOW | 13:45:00 | 13:45:00 | 13:50:00 | 98.60 | 98.60 |
| EXHAUSTION_FORMING | 13:45:00 | 13:45:00 | 13:50:00 | 98.60 | 98.60 |
| CONTINUATION_RISK | 13:45:00 | 13:50:00 | 13:55:00 | 98.60 | 97.90 |
| RECLAIM_ONLY | 13:50:00 | 13:55:00 | 14:00:00 | 97.90 | 97.80 |
| EXHAUSTION_RECLAIM | 13:55:00 | 14:00:00 | 14:05:00 | 97.80 | 97.80 |

First candidate: **CONTINUATION**. Frozen reclaim level: 98.80; continuation level: 98.10.
Independent control anchors: 1. Future family labels never select the controls.

## Expiry

| Selector | Candidate | Confirmation / decision | Earliest entry | Candidate low | Episode low |
|---|---|---|---|---:|---:|
| BASE_FRESH_LOW | 13:45:00 | 13:45:00 | 13:50:00 | 98.60 | 98.60 |
| EXHAUSTION_FORMING | 13:45:00 | 13:45:00 | 13:50:00 | 98.60 | 98.60 |

First candidate: **EXPIRED**. Frozen reclaim level: 98.80; continuation level: 98.10.
Independent control anchors: 1. Future family labels never select the controls.

## Still held

Empirical TrialLedger registration, market-outcome runs, independent review, deployment and live alert integration remain separate gates. This report unlocks review of executable mechanics; it establishes no accuracy or profitability.
