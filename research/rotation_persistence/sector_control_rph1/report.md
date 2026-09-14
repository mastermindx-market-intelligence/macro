# Leadership Persistence RPH-1 — Daily Sector Control

**Operation:** `leadership-persistence-sector-control-rph1-20260912-sol-001`

**Produced at:** `2026-09-12T21:00:00Z`

**Authority:** research/display context only; no rank, gate, size, trade, Prophet or Oracle authority.

## Source and quality

- Source revision: `8d198b42f6bff491a49b1f3467b56ca4bb673f80`
- Common sessions: 2067
- Retained range: 2018-06-19 through 2026-09-09
- History state: `MEASURED`

## Leadership surface

| Lookback | Horizon | Recent rank rho | Recent predictive rho | Recent top-three retention |
|---:|---:|---:|---:|---:|
| 5 | 1 | 0.6423 | -0.1436 | 0.6833 |
| 5 | 3 | 0.2132 | -0.1845 | 0.4667 |
| 5 | 5 | -0.1891 | -0.1891 | 0.2833 |
| 5 | 7 | -0.1932 | -0.1727 | 0.2667 |
| 5 | 10 | -0.1777 | -0.1973 | 0.2833 |
| 5 | 20 | 0.1186 | -0.1200 | 0.4167 |
| 21 | 1 | 0.9036 | 0.0077 | 0.7667 |
| 21 | 3 | 0.7505 | -0.0395 | 0.5833 |
| 21 | 5 | 0.6100 | 0.0405 | 0.5000 |
| 21 | 7 | 0.5782 | 0.1682 | 0.5833 |
| 21 | 10 | 0.4632 | 0.0582 | 0.5667 |
| 21 | 20 | 0.1091 | 0.0464 | 0.4667 |

## Dispersion and correlation controls

- Dispersion recent-minus-prior mean: -0.0001
- Dispersion recent/prior mean ratio: 0.9864
- Correlation recent-minus-prior mean: -0.1585
- Correlation recent/prior mean ratio: 0.4361

## Phase-robust MACD hierarchy

| Forward horizon | All | Recent 20 signal dates | Recent 60 signal dates |
|---:|---|---|---|
| 1 | `MIXED_PHASES` | `ONE_DAY_ABOVE_ALL_SLOWER_PHASES` | `MIXED_PHASES` |
| 3 | `MIXED_PHASES` | `MIXED_PHASES` | `ONE_DAY_BELOW_ALL_SLOWER_PHASES` |
| 5 | `MIXED_PHASES` | `MIXED_PHASES` | `ONE_DAY_BELOW_ALL_SLOWER_PHASES` |
| 10 | `MIXED_PHASES` | `ONE_DAY_ABOVE_ALL_SLOWER_PHASES` | `ONE_DAY_BELOW_ALL_SLOWER_PHASES` |

## Boundaries

- Daily repository Yahoo closes are an archive control, not exact vendor-chart parity.
- MACD marks use signal-session closes and ignore execution, spread, slippage and latency.
- Sector ETF behavior does not prove current theme or constituent behavior.
- Every result is research/display context only and cannot rank, gate, size or trade.

The hierarchy is archive-specific descriptive evidence. It does not choose a production timeframe or create an entry instruction.
