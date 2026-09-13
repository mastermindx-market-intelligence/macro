# China A-share Dashboard — Calibration (Phase-2 checkpoint)

Honest, split-half measurement before any UI is built — the same gate used for the
US and Bitcoin Vector dashboards. House rule: a signal is shipped with its **measured**
forward-return record; no measured edge -> it ships as *context, not a signal*.

- Confident-regime sample: **2008-01-01 -> 2026-09-11** (4879 days, confidence>0).
- Ladder panel: **105 instruments** (curated constituents + indices + sector ETFs).
- Caveats: China macro history is monthly back to ~2006-08 (shorter + more regime-unstable
  than the US — 2007/2015 bubbles); the 16 sector ETFs are only ~5y so their RS is
  display-grade, while the ladder is calibrated on the DEEP stock/index panel.

## 1. Regime quad -> forward return of the market index (Shanghai Composite)

**Full sample**

| quad_name    |    n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|-----:|------------:|-----------:|------------:|-----------:|
| Goldilocks   | 1707 |        0.73 |       52   |        2.3  |       45.5 |
| Growth-scare |  687 |        1.46 |       55.7 |        6.69 |       73.5 |
| Reflation    | 1902 |       -0.7  |       49.8 |       -2.74 |       42.8 |
| Stagflation  |  583 |       -0.88 |       47.7 |       -1.46 |       51.2 |

**Split-half robustness** (a quad's edge is only trustworthy if it survives both halves)

_Pre-split_

| quad_name    |   n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|----:|------------:|-----------:|------------:|-----------:|
| Goldilocks   | 919 |        1.34 |       56.7 |        4.38 |       48.7 |
| Growth-scare | 171 |        1.21 |       49.7 |        9.2  |       70.1 |
| Reflation    | 946 |       -1.38 |       44.3 |       -4.92 |       36.8 |
| Stagflation  |  52 |      -10.93 |        2   |      -22.05 |        1.9 |

_Post-split_

| quad_name    |   n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:-------------|----:|------------:|-----------:|------------:|-----------:|
| Goldilocks   | 788 |        0.03 |       46.7 |       -0.13 |       41.8 |
| Growth-scare | 516 |        1.54 |       57.8 |        5.81 |       74.7 |
| Reflation    | 956 |       -0.01 |       55.3 |       -0.58 |       48.8 |
| Stagflation  | 531 |        0.13 |       52.3 |        0.83 |       56.6 |

## 2. Liquidity overlay (PBoC stance via M2 direction) -> forward return

| liquidity   |    n |   f21_mean% |   f21_hit% |   f63_mean% |   f63_hit% |
|:------------|-----:|------------:|-----------:|------------:|-----------:|
| contracting | 2300 |        0.22 |       50.4 |        0.49 |       47.8 |
| expanding   | 1740 |        0.48 |       54.7 |        1.71 |       53.5 |
| neutral     |  776 |       -0.22 |       49.3 |       -0.12 |       46.2 |
| unknown     |   63 |      -12.52 |        5.1 |      -25.24 |        0   |

## 3. Cycle ladder (deep A-share panel) — endpoint return + forward drawdown

|                          |     n |   hit_pct |   avg_fwd_pct |   dd_med_pct |   dd_p10_pct |   dd_bad_pct |
|:-------------------------|------:|----------:|--------------:|-------------:|-------------:|-------------:|
| DECLINE                  |  7171 |      52.9 |          1.78 |        -4.46 |       -14.6  |         21.3 |
| BOTTOM WATCH             |  3536 |      44.7 |          1.63 |        -3.56 |       -14.46 |         19.4 |
| TURN SIGNALED            | 11420 |      48.3 |          1.18 |        -4.55 |       -14.82 |         21.6 |
| FRESH BUY                |  2392 |      52.1 |          2.19 |        -4.45 |       -13.76 |         19.6 |
| RALLY ON                 |  2414 |      50.6 |          1.52 |        -4.28 |       -14.29 |         20.9 |
| TOP WATCH                |  6403 |      51.1 |          2.51 |        -4.92 |       -15.74 |         24.5 |
| ROLLING OVER             |   222 |      47.3 |          0.48 |        -4.49 |       -13.48 |         19.8 |
| COUNTERTREND BOUNCE      | 11056 |      51.8 |          1.37 |        -4.18 |       -14.92 |         21.2 |
| BOTTOM WATCH +early-bull |   148 |      45.9 |          1.79 |        -1.75 |       -13.17 |         18.9 |
| BOTTOM WATCH no-early    |  3388 |      44.7 |          1.63 |        -3.61 |       -14.51 |         19.5 |

## Reading this
- Quad rows whose sign/ranking flips between the two halves are **regime-unstable** ->
  frame as risk context, never a standalone allocation rule.
- The ladder's value is the DRAWDOWN columns (dd_*): scary states with shallow typical
  dips are the asymmetric setups; the avg_fwd alone is U-shaped/misleading (macro D43).
