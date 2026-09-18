# Hong Kong / Hang Seng Dashboard — Calibration

Honest, split-half measurement before any UI is built — the same gate used for the
US, China and Bitcoin Vector dashboards. House rule: a signal is shipped with its **measured**
forward-return record; no measured edge -> it ships as *context, not a signal*.

- Confident-regime sample: **2000-04-21 -> 2026-09-11** (6757 days, confidence>0).
- Ladder panel: **162 instruments** (curated constituents + indices + ETF proxies).
- Caveats: the HK macro read piggybacks on China fundamentals (PMI/CPI/PPI/M2), monthly
  back to ~2006-08 (shorter + more regime-unstable than the US); HSI itself is the regional
  risk-on/off proxy, so the THREE-LEG engine here is quad (growth×inflation) + dual liquidity
  (PBoC + Fed-via-peg) + the global risk overlay — the third leg is the one to scrutinise.

## 1. Regime quad -> forward return of the market index (Hang Seng Index)

**Full sample**

| quad_name    |    n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|-----:|------------:|-----------:|------------:|-----------:|
| Goldilocks   | 1482 |        1.39 |       57.1 |        4.11 |       65   |
| Growth-scare | 1130 |        0.2  |       55.2 |        2.28 |       56.2 |
| Reflation    | 1644 |        0.23 |       52.8 |       -0.51 |       46.9 |
| Stagflation  | 1038 |       -0.76 |       45.6 |       -2.07 |       43.3 |

**Split-half robustness** (a quad's edge is only trustworthy if it survives both halves)

_Pre-split_

| quad_name    |   n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|----:|------------:|-----------:|------------:|-----------:|
| Goldilocks   | 817 |        1.95 |       59.2 |        6.21 |       71.6 |
| Growth-scare | 523 |       -0.11 |       52.6 |        3.05 |       63.1 |
| Reflation    | 807 |        0.05 |       54.2 |       -1.53 |       42.5 |
| Stagflation  | 362 |       -1.89 |       43.4 |       -6.49 |       40.9 |

_Post-split_

| quad_name    |   n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|----:|------------:|-----------:|------------:|-----------:|
| Goldilocks   | 665 |        0.68 |       54.4 |        1.43 |       56.6 |
| Growth-scare | 607 |        0.47 |       57.5 |        1.6  |       50.2 |
| Reflation    | 837 |        0.4  |       51.5 |        0.48 |       51.1 |
| Stagflation  | 676 |       -0.15 |       46.7 |        0.4  |       44.7 |

## 2. Liquidity overlay (dual: PBoC stance + Fed-via-peg + southbound flow) -> forward return

| liquidity   |    n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:------------|-----:|------------:|-----------:|------------:|-----------:|
| contracting |  883 |       -0.75 |       45.1 |       -3.58 |       34.4 |
| expanding   | 3053 |        0.76 |       57.2 |        1.62 |       56.6 |
| neutral     | 2385 |        0.17 |       51.4 |        1.91 |       56.6 |
| unknown     |  436 |        0.86 |       60.3 |        0.84 |       56   |

## 3. Global risk overlay (risk-on/off) -> forward return

_The KEY HK test: HK is the regional risk-on/off proxy, so does the global risk state
differentiate HSI forward returns?_

| risk_state   |    n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|-----:|------------:|-----------:|------------:|-----------:|
| Neutral      | 2491 |       -0.11 |       49.9 |        0.34 |       50.1 |
| Risk-off     | 1616 |        0.42 |       54.8 |        0.8  |       53.5 |
| Risk-on      | 2650 |        0.79 |       56.9 |        1.83 |       57.6 |

## 4. Cycle ladder (deep HK panel) — endpoint return + forward drawdown

|                          |     n |   hit_pct |   avg_fwd_pct |   dd_med_pct |   dd_p10_pct |   dd_bad_pct |
|:-------------------------|------:|----------:|--------------:|-------------:|-------------:|-------------:|
| DECLINE                  | 10306 |      53.9 |          1.44 |        -4.83 |       -18.26 |         26.9 |
| BOTTOM WATCH             |  5221 |      47.9 |        124.86 |        -3.93 |       -15.69 |         21.3 |
| TURN SIGNALED            | 18034 |      50.8 |          1.47 |        -4.34 |       -14.5  |         21   |
| FRESH BUY                |  3951 |      52.8 |          1.54 |        -4.09 |       -13.97 |         19.4 |
| RALLY ON                 |  3798 |      53.9 |          1.77 |        -3.95 |       -14.04 |         19.1 |
| TOP WATCH                | 10418 |      52   |          1.72 |        -4.37 |       -14.84 |         21.7 |
| ROLLING OVER             |   348 |      51.7 |          1.53 |        -4.6  |       -15.64 |         23.3 |
| COUNTERTREND BOUNCE      | 17020 |      51   |          1.04 |        -4.52 |       -16.08 |         23.8 |
| BOTTOM WATCH +early-bull |   192 |      45.8 |          0.73 |        -3.64 |       -12.99 |         18.8 |
| BOTTOM WATCH no-early    |  5029 |      47.9 |        129.6  |        -3.94 |       -15.75 |         21.4 |

## Reading this
- Quad rows whose sign/ranking flips between the two halves are **regime-unstable** ->
  frame as risk context, never a standalone allocation rule.
- The ladder's value is the DRAWDOWN columns (dd_*): scary states with shallow typical
  dips are the asymmetric setups; the avg_fwd alone is U-shaped/misleading (macro D43).
