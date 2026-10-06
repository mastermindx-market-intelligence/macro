# Leadership Persistence RPH-0

**Operation:** `leadership-persistence-rph0-20260910-sol-001`

**Produced at:** `2026-09-10T21:00:00Z`

**Authority:** research/display context only; no rank, gate, size, trade, Prophet or Oracle authority.

## Result

**Published-output temporal shape:** `INSUFFICIENT_HISTORY`

**Structural estimability:** `STRUCTURALLY_UNESTIMABLE` (minimum recent window: 23 sessions).

Long-horizon maximum matured anchors: 10→10, 15→5, 20→0.

Short-horizon published-score continuation median: **-0.234**.

Long-horizon published-score continuation median: **—**.

This label describes the dynamics of the existing published theme scores. It is not a return forecast or a holding-period instruction.

## Source and quality

- Source: `data/signal_archive/baskets.parquet`
- SHA-256: `b2f45d79e3e506a2a1aec21a117046859d8677acc2da46865579ad52c7fecc21`
- Valid archive dates: 2026-06-18 through 2026-09-09 (41 rows)
- Exchange-session coverage: 0.719 (41 of 57)
- Theme count: min 25, median 46.0, max 49
- Missing sessions inside range: 16

## Persistence surface

| Horizon | Recent rank rho | Recent score continuation | Recent top-Q survival | Recent eligible anchors | All eligible anchors |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.873 | -0.198 | 0.775 | 14 | 30 |
| 2 | 0.805 | -0.236 | 0.712 | 12 | 24 |
| 3 | 0.802 | -0.232 | 0.686 | 12 | 25 |
| 5 | 0.661 | -0.295 | 0.629 | 11 | 18 |
| 7 | 0.655 | -0.190 | 0.623 | 10 | 20 |
| 10 | — | — | — | 7 | 19 |
| 15 | — | — | — | 3 | 14 |
| 20 | — | — | — | 0 | 14 |

## Honest half-life assessment

| Window | State | Half-life, sessions | Starting rho | Half target |
|---|---|---:|---:|---:|
| recent | `NO_HALF_CROSSING` | — | 0.873 | 0.436 |
| prior | `MEASURED` | 13.63 | 0.875 | 0.437 |
| all | `MEASURED` | 14.15 | 0.874 | 0.437 |

## Top-quartile residency

- Episode rows: 202
- KM state: `MEASURED`
- KM eligible episodes: 92 (44 observed exits; 48 right-censored)
- Left-censored episodes excluded from KM: 110
- Median survival: 3 sessions

## One-session quartile transition probabilities

| From \ To | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| Q1 | 0.760 | 0.210 | 0.030 | 0.000 |
| Q2 | 0.232 | 0.527 | 0.226 | 0.015 |
| Q3 | 0.029 | 0.224 | 0.538 | 0.209 |
| Q4 | 0.000 | 0.012 | 0.220 | 0.768 |

## Boundaries

- Measures persistence of published theme ranks, scores and breadth; it is not an economic-return backtest.
- The source archive is keep-first point-in-time model output; RPH-0 does not claim historical raw-membership reconstruction.
- Exact TradingView/MACD timeframe usefulness remains owned by WS:TEMPORAL-GRAIN-INTELLIGENCE and Prophet Entry Truth.
- A null half-life or insufficient cell is an honest successful result, not a pipeline failure.
