# Index-reconstitution forced-flow event study

_Generated 2026-11-01 12:42 UTC. Effective-date events 2019-01-01→ from S&P 500/400/600 PIT membership; SPY-relative; month-clustered HAC-t._

- Adds: **1541** · Deletes: **952** (price-covered subset)
- **Verdict: display-only context (effect decayed)**

## ADD events — SPY-relative abnormal return

| Window | n | mean | hit | HAC-t |
|--|--:|--:|--:|--:|
| pre run-up [-10,-1] | 1206 | 0.02 | 0.561 | 4.39 |
| post [0,5] | 1267 | -0.001 | 0.476 | 0.99 |
| post [0,10] | 1267 | -0.0072 | 0.41 | 0.34 |
| post [0,21] | 1267 | -0.0097 | 0.434 | -0.47 |

## DELETE events — SPY-relative abnormal return

| Window | n | mean | hit | HAC-t |
|--|--:|--:|--:|--:|
| post [0,5] | 542 | 0.0051 | 0.496 | 1.5 |
| post [0,10] | 542 | 0.0017 | 0.483 | 1.08 |
| post [0,21] | 542 | 0.0052 | 0.498 | 0.64 |

## ADD post-[0,21] by index

| Index | n | mean | HAC-t |
|--|--:|--:|--:|
| sp500 | 150 | -0.0082 | -0.21 |
| sp400 | 281 | 0.0152 | 1.04 |
| sp600 | 836 | -0.0184 | -1.23 |

## ADD announcement-capture window [-5, 0] — pure vs migration, gross vs net

_Buy at announcement (~5 td before effective), hold through the effective close. Cohorts: {'pure': 1140, 'migration': 381, 'readd': 20}. **announce_gross_scored=True · announce_net_scored=False** (net cost assumed {'sp500': 0.002, 'sp400': 0.006, 'sp600': 0.012})._

| Cohort / index | n | mean | median | hit | HAC-t |
|--|--:|--:|--:|--:|--:|
| PURE gross | 865 | 0.0162 | 0.0108 | 0.588 | 4.73 |
| PURE gross recent (2023-01-01+) | 265 | 0.0208 | 0.0201 | 0.664 | 5.13 |
| MIGRATION gross (control) | 336 | 0.0016 | 0.0005 | 0.506 | 1.03 |
| pure sp500 gross | 75 | 0.0147 | 0.0119 | 0.587 | 1.43 |
| pure sp400 gross | 162 | 0.017 | 0.0163 | 0.636 | 2.39 |
| pure sp600 gross | 628 | 0.0161 | 0.0099 | 0.576 | 5.07 |
| pure sp500 NET (−0.2%) | 75 | 0.0127 | 0.0099 | 0.56 | 1.27 |
| pure sp400 NET (−0.6%) | 162 | 0.011 | 0.0103 | 0.593 | 1.86 |
| pure sp600 NET (−1.2%) | 628 | 0.0041 | -0.0021 | 0.479 | 3.95 |

_PURE/net-new ADD announcement→effective [-5,0] run-up is real & recent (+0.0162, t=4.73; recent t=5.13); migrations are ~0 (t=1.03) — so screen to PURE adds. BUT net of small-cap cost the TYPICAL name loses (sp600 net median=-0.0021, hit=0.479) → a NET-OF-COST MIRAGE. Leg ships DISPLAY-ONLY context (fresh pure-add catalysts), scoring gate CLOSED; the net edge lives only in the announcement-overnight gap, which needs intraday opens to validate.._
