# Index-reconstitution forced-flow event study

_Generated 2026-10-01 16:11 UTC. Effective-date events 2019-01-01→ from S&P 500/400/600 PIT membership; SPY-relative; month-clustered HAC-t._

- Adds: **1541** · Deletes: **952** (price-covered subset)
- **Verdict: display-only context (effect decayed)**

## ADD events — SPY-relative abnormal return

| Window | n | mean | hit | HAC-t |
|--|--:|--:|--:|--:|
| pre run-up [-10,-1] | 1215 | 0.0203 | 0.56 | 4.36 |
| post [0,5] | 1273 | -0.0005 | 0.474 | 1.3 |
| post [0,10] | 1273 | -0.0065 | 0.411 | 0.57 |
| post [0,21] | 1273 | -0.0088 | 0.436 | -0.3 |

## DELETE events — SPY-relative abnormal return

| Window | n | mean | hit | HAC-t |
|--|--:|--:|--:|--:|
| post [0,5] | 545 | 0.0059 | 0.497 | 1.85 |
| post [0,10] | 545 | 0.0028 | 0.486 | 1.51 |
| post [0,21] | 545 | 0.0068 | 0.501 | 0.97 |

## ADD post-[0,21] by index

| Index | n | mean | HAC-t |
|--|--:|--:|--:|
| sp500 | 152 | -0.0066 | -0.09 |
| sp400 | 281 | 0.0152 | 1.04 |
| sp600 | 840 | -0.0173 | -1.15 |

## ADD announcement-capture window [-5, 0] — pure vs migration, gross vs net

_Buy at announcement (~5 td before effective), hold through the effective close. Cohorts: {'pure': 1140, 'migration': 381, 'readd': 20}. **announce_gross_scored=True · announce_net_scored=False** (net cost assumed {'sp500': 0.002, 'sp400': 0.006, 'sp600': 0.012})._

| Cohort / index | n | mean | median | hit | HAC-t |
|--|--:|--:|--:|--:|--:|
| PURE gross | 873 | 0.0166 | 0.011 | 0.589 | 4.68 |
| PURE gross recent (2023-01-01+) | 266 | 0.0199 | 0.0198 | 0.662 | 5.02 |
| MIGRATION gross (control) | 337 | 0.0017 | 0.0005 | 0.507 | 1.07 |
| pure sp500 gross | 77 | 0.0115 | 0.0088 | 0.571 | 1.18 |
| pure sp400 gross | 162 | 0.017 | 0.0163 | 0.636 | 2.39 |
| pure sp600 gross | 634 | 0.0171 | 0.0103 | 0.579 | 5.33 |
| pure sp500 NET (−0.2%) | 77 | 0.0095 | 0.0068 | 0.545 | 0.99 |
| pure sp400 NET (−0.6%) | 162 | 0.011 | 0.0103 | 0.593 | 1.86 |
| pure sp600 NET (−1.2%) | 634 | 0.0051 | -0.0017 | 0.483 | 4.22 |

_PURE/net-new ADD announcement→effective [-5,0] run-up is real & recent (+0.0166, t=4.68; recent t=5.02); migrations are ~0 (t=1.07) — so screen to PURE adds. BUT net of small-cap cost the TYPICAL name loses (sp600 net median=-0.0017, hit=0.483) → a NET-OF-COST MIRAGE. Leg ships DISPLAY-ONLY context (fresh pure-add catalysts), scoring gate CLOSED; the net edge lives only in the announcement-overnight gap, which needs intraday opens to validate.._
