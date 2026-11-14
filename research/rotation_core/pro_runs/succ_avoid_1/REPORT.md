PRO-RUN SUCC-AVOID-1 part 1

**Total parts: 8.** Run `SUCC-AVOID-1`; ledger row `successor-avoid-1`.

## 1. Plain answer

I did not find a qualified successor. In the permitted 2013–2023 history, requiring the absolute and relative oscillators to turn down together gave a small reduction in fake breakdowns **at the same measured lateness**, but its raw fake rate was higher than the old rule, it did not beat the matched volatility dates, and it did not demonstrate the required extra drawdown avoidance. The opposite-moving partner was the other finalist under the fixed ranking, but its benefit was not stable and its FF12 damage-capture result was worse than the controls. Weekly/two-week state confirmation, proxy breadth, rising volatility and macro stress supplied no rule that cleared every test. A roll-over can interrupt strong continuing leadership: several supposed tops preceded very large relative gains. These findings apply to the common **2016-01-08 to 2023-09-15 scored panel**, with later starts for XLRE/XLC; 2013 onward supplies in-block warm-up. They are discovery results, not proof that every year in the permitted block was scored or that an exit improves wealth.

## 2. Every candidate and both comparator families

Run **SUCC-AVOID-1**; ledger **successor-avoid-1**. Eight rules were fixed in [the immutable protocol](https://github.com/mastermindx-market-intelligence/macro/blob/2a1924f0092a4bb0f4a3f4d85d129b9eaf2c3c6e/research/rotation_core/pro_runs/succ_avoid_1/PROTOCOL.md) before outcome inspection. Code and derived evidence: [reproduction package](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/README.md).

| Rule | Definition fixed before the test |
|---|---|
| OLD | Completed 3-day absolute K crosses below D from previous K>80; RSI-MACD histogram falls. |
| C1 REL | The identical top rule applied to group/SPY alone. |
| C2 BOTH | OLD and REL top fire on the same completed 3-day bar. |
| C3 WEEK | OLD; completed weekly K<D, histogram falling, previous K≥50, weekly close ≥90% of its 26-week high. |
| C4 TWO_WEEK | OLD; completed 2-week K<D, histogram falling, previous K≥50, close ≥90% of its 13-bar high. |
| C5 BREADTH | FF12 only: OLD and ≥40% of proxy children fired OLD in the last 9 sessions, or ≥60% are below their 50-session average. |
| C6 PARTNER | OLD; minimum prior-126-session relative-return correlation ≤−0.25; that same-cohort partner fired a relative bottom in the last 6 sessions. |
| C7 VOL_RISE | OLD; RV21 ≥1.25× its value 21 sessions earlier; that earlier value ≤40th percentile of the preceding 252 RV21 readings; lagged VIX≥20 or five-session rise≥2. |
| C8 MACRO | OLD and ≥2 of: curve<0; 10Y 63-session rise≥0.50pp; broad dollar 63-session rise≥2%; HY OAS 21-session rise≥0.25pp. All four inputs available. |
| VOL33 | RV63 at/above own discovery-block 2/3 quantile. Raw state plus exact per-group count-matched versions. |
| −10 / +10 | The original rule/candidate flags moved exactly ten SPY sessions earlier/later. Placebos, not executable forecasting rules. |

### How to read the tables

All rates and drawdowns are percentages unless labelled otherwise. **On-share is flagged group-days / eligible group-days**, with each flag lasting one event day. Flags/group-year uses eligible group-days/252; actual annual counts follow. Lateness uses the most recent maximum in the **prior 63 sessions, excluding the flag day**. OLD's pooled lateness terciles are **T1=1–6, T2=7–48, T3=49–63 sessions**; boundary ties stay together. Each tercile cell gives fake21 rate and number of flags. N=10 and 45 are sensitivities only (¹), never selection targets. DD63 is average member peak-to-trough drawdown over close t and the next 63 closes.

A fake is a strict new rolling relative high over the preceding 63 sessions on any of the next 21 sessions. This can occur when an older peak rolls out; it is not a requirement to regain a fixed flag-date peak. Group/SPY uses total-return indices.

The raw VOL33 state flags about 41% of the **scored** panel because its cutoff is set on the longer permitted discovery distribution, including low-volatility warm-up dates. Each `VOL matched to X` is sampled from that state using a frozen date hash, matching X's total count separately within every group. No outcome enters this sampling. Thus the top-third predicate is retained and the actual event on-share matches; the raw state is shown without falsely claiming it has the same share.

### FF12 — primary reporting/ranking cohort

FF12 member statistics use a fixed **economic FF49 proxy mapping**, not literal nested French constituents. FF49 and FF12 are not nested partitions. Child counts and the full map appear with the reproduction rules.

| Rule/control | Flags | Flags/group-year | On-share % | Median late | Fake21 % | T1 % (n) | T2 % (n) | T3 % (n) | Mean member DD63 % | Fake10 %¹ | Fake45 %¹ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | 455 | 4.94 | 1.960 | 24.0 | 32.97 | 50.4 (141) | 28.0 (164) | 22.0 (150) | 10.96 | 20.88 | 52.53 |
| C1 REL | 419 | 4.55 | 1.804 | 6.0 | 39.62 | 47.2 (216) | 42.5 (73) | 25.4 (130) | 10.89 | 26.25 | 53.70 |
| C2 BOTH | 123 | 1.33 | 0.530 | 5.0 | 34.96 | 42.3 (71) | 46.7 (15) | 16.2 (37) | 12.10 | 20.33 | 50.41 |
| C3 WEEK | 73 | 0.79 | 0.314 | 16.0 | 39.73 | 52.4 (21) | 32.4 (34) | 38.9 (18) | 11.68 | 19.18 | 56.16 |
| C4 TWO_WEEK | 6 | 0.07 | 0.026 | 12.5 | 16.67 | 0.0 (2) | 33.3 (3) | 0.0 (1) | 8.09 | 0.00 | 66.67 |
| C5 BREADTH | 350 | 3.80 | 1.507 | 22.0 | 35.14 | 48.7 (113) | 33.3 (120) | 23.9 (117) | 11.24 | 21.71 | 55.43 |
| C6 PARTNER | 66 | 0.72 | 0.284 | 7.5 | 36.36 | 37.5 (32) | 58.8 (17) | 11.8 (17) | 9.01 | 22.73 | 56.06 |
| C7 VOL_RISE | 18 | 0.20 | 0.078 | 8.0 | 44.44 | 75.0 (8) | 40.0 (5) | 0.0 (5) | 15.03 | 44.44 | 55.56 |
| C8 MACRO | 58 | 0.63 | 0.250 | 33.0 | 34.48 | 46.7 (15) | 34.8 (23) | 25.0 (20) | 9.48 | 27.59 | 63.79 |
| VOL33 raw state | 9532 | 103.45 | 41.051 | 32.0 | 33.71 | 68.0 (1801) | 24.0 (4674) | 28.4 (3057) | 11.54 | 22.80 | 50.47 |
| VOL matched to OLD | 455 | 4.94 | 1.960 | 35.0 | 32.53 | 60.5 (76) | 24.3 (235) | 31.2 (144) | 11.25 | 21.54 | 49.23 |
| OLD −10 sessions | 455 | 4.94 | 1.960 | 36.0 | 44.62 | 78.1 (114) | 36.4 (162) | 30.7 (179) | 10.93 | 35.82 | 58.90 |
| OLD +10 sessions | 455 | 4.94 | 1.960 | 20.0 | 35.16 | 63.9 (83) | 32.4 (238) | 22.4 (134) | 11.34 | 22.86 | 52.53 |
| VOL matched to C1 | 419 | 4.55 | 1.804 | 35.0 | 33.41 | 64.7 (68) | 24.4 (217) | 32.1 (134) | 11.40 | 22.43 | 48.69 |
| C1 −10 sessions | 419 | 4.55 | 1.804 | 42.0 | 65.63 | 97.0 (133) | 62.9 (105) | 44.2 (181) | 11.09 | 57.76 | 75.42 |
| C1 +10 sessions | 419 | 4.55 | 1.804 | 14.0 | 39.86 | 66.3 (98) | 33.6 (223) | 27.6 (98) | 10.92 | 28.16 | 49.40 |
| VOL matched to C2 | 123 | 1.33 | 0.530 | 34.0 | 29.27 | 69.2 (13) | 24.0 (75) | 25.7 (35) | 12.82 | 17.89 | 42.28 |
| C2 −10 sessions | 123 | 1.33 | 0.530 | 43.0 | 65.04 | 97.6 (42) | 57.1 (28) | 43.4 (53) | 11.93 | 60.98 | 74.80 |
| C2 +10 sessions | 123 | 1.33 | 0.530 | 14.0 | 34.15 | 47.8 (23) | 32.5 (77) | 26.1 (23) | 12.72 | 22.76 | 44.72 |
| VOL matched to C3 | 73 | 0.79 | 0.314 | 39.0 | 27.40 | 33.3 (9) | 27.5 (40) | 25.0 (24) | 11.12 | 17.81 | 38.36 |
| C3 −10 sessions | 73 | 0.79 | 0.314 | 11.0 | 47.95 | 71.0 (31) | 39.1 (23) | 21.1 (19) | 11.61 | 39.73 | 65.75 |
| C3 +10 sessions | 73 | 0.79 | 0.314 | 20.0 | 39.73 | 50.0 (12) | 36.4 (44) | 41.2 (17) | 11.93 | 30.14 | 61.64 |
| VOL matched to C4 | 6 | 0.07 | 0.026 | 40.5 | 33.33 | — (0) | 25.0 (4) | 50.0 (2) | 14.95 | 33.33 | 50.00 |
| C4 −10 sessions | 6 | 0.07 | 0.026 | 28.0 | 66.67 | 100.0 (1) | 66.7 (3) | 50.0 (2) | 8.77 | 50.00 | 83.33 |
| C4 +10 sessions | 6 | 0.07 | 0.026 | 20.0 | 66.67 | — (0) | 66.7 (6) | — (0) | 8.05 | 16.67 | 66.67 |
| VOL matched to C5 | 350 | 3.80 | 1.507 | 34.0 | 32.00 | 64.4 (59) | 22.7 (181) | 30.0 (110) | 11.70 | 21.71 | 48.00 |
| C5 −10 sessions | 350 | 3.80 | 1.507 | 36.5 | 47.14 | 82.0 (89) | 39.3 (122) | 31.7 (139) | 11.30 | 38.29 | 62.86 |
| C5 +10 sessions | 350 | 3.80 | 1.507 | 17.0 | 37.14 | 61.2 (67) | 34.3 (181) | 26.5 (102) | 11.62 | 24.57 | 54.57 |
| VOL matched to C6 | 66 | 0.72 | 0.284 | 38.5 | 24.24 | 33.3 (3) | 22.0 (41) | 27.3 (22) | 12.05 | 10.61 | 36.36 |
| C6 −10 sessions | 66 | 0.72 | 0.284 | 30.0 | 59.09 | 95.2 (21) | 60.0 (20) | 28.0 (25) | 8.84 | 48.48 | 71.21 |
| C6 +10 sessions | 66 | 0.72 | 0.284 | 14.0 | 37.88 | 61.5 (13) | 39.0 (41) | 8.3 (12) | 9.88 | 21.21 | 57.58 |
| VOL matched to C7 | 18 | 0.20 | 0.078 | 36.5 | 27.78 | — (0) | 26.7 (15) | 33.3 (3) | 11.97 | 16.67 | 38.89 |
| C7 −10 sessions | 18 | 0.20 | 0.078 | 7.0 | 66.67 | 87.5 (8) | 80.0 (5) | 20.0 (5) | 15.52 | 66.67 | 72.22 |
| C7 +10 sessions | 18 | 0.20 | 0.078 | 11.0 | 27.78 | 37.5 (8) | 33.3 (6) | 0.0 (4) | 14.20 | 16.67 | 33.33 |
| VOL matched to C8 | 58 | 0.63 | 0.250 | 35.0 | 24.14 | 40.0 (5) | 21.6 (37) | 25.0 (16) | 12.23 | 13.79 | 36.21 |
| C8 −10 sessions | 58 | 0.63 | 0.250 | 41.0 | 50.00 | 82.4 (17) | 43.8 (16) | 32.0 (25) | 9.20 | 32.76 | 65.52 |
| C8 +10 sessions | 58 | 0.63 | 0.250 | 18.5 | 43.10 | 69.2 (13) | 41.4 (29) | 25.0 (16) | 9.42 | 25.86 | 65.52 |

Underlying exact values: [results/summary.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/summary.csv) and [results/coverage.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/coverage.csv).


---

PRO-RUN SUCC-AVOID-1 part 2

## 2. Tables continued — ETF, FF49 and descriptive pooled results

ETF DD refers to the ETF itself. FF49 DD refers to each FF49 portfolio itself, not its underlying stocks. The pooled table repeats overlapping economic exposures and is **not independent corroboration**. C5 is N/A outside FF12; its pooled row still uses only the FF12 denominator. All other definitions and tercile boundaries are unchanged.

### Sector ETFs

| Rule/control | Flags | Flags/group-year | On-share % | Median late | Fake21 % | T1 % (n) | T2 % (n) | T3 % (n) | Mean member DD63 % | Fake10 %¹ | Fake45 %¹ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | 372 | 4.91 | 1.949 | 29.0 | 35.75 | 55.5 (110) | 27.3 (139) | 27.6 (123) | 9.38 | 21.77 | 51.88 |
| C1 REL | 361 | 4.77 | 1.892 | 7.0 | 43.77 | 53.7 (177) | 41.1 (73) | 29.7 (111) | 9.11 | 28.81 | 59.83 |
| C2 BOTH | 95 | 1.25 | 0.498 | 5.0 | 37.89 | 44.2 (52) | 31.6 (19) | 29.2 (24) | 9.29 | 21.05 | 52.63 |
| C3 WEEK | 52 | 0.69 | 0.272 | 25.5 | 38.46 | 54.5 (11) | 33.3 (27) | 35.7 (14) | 11.62 | 23.08 | 44.23 |
| C4 TWO_WEEK | 8 | 0.11 | 0.042 | 41.5 | 25.00 | 0.0 (1) | 25.0 (4) | 33.3 (3) | 13.75 | 0.00 | 37.50 |
| C5 BREADTH | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| C6 PARTNER | 59 | 0.78 | 0.309 | 20.0 | 32.20 | 43.8 (16) | 28.0 (25) | 27.8 (18) | 9.33 | 16.95 | 49.15 |
| C7 VOL_RISE | 21 | 0.28 | 0.110 | 6.0 | 57.14 | 72.7 (11) | 20.0 (5) | 60.0 (5) | 15.66 | 42.86 | 71.43 |
| C8 MACRO | 53 | 0.70 | 0.278 | 29.0 | 33.96 | 50.0 (12) | 23.8 (21) | 35.0 (20) | 8.03 | 24.53 | 58.49 |
| VOL33 raw state | 7799 | 102.99 | 40.869 | 33.0 | 33.56 | 69.5 (1462) | 28.1 (3706) | 21.3 (2631) | 9.90 | 22.87 | 49.53 |
| VOL matched to OLD | 372 | 4.91 | 1.949 | 34.5 | 36.29 | 67.9 (81) | 29.4 (160) | 25.2 (131) | 9.47 | 25.00 | 52.42 |
| OLD −10 sessions | 372 | 4.91 | 1.949 | 37.0 | 43.28 | 78.7 (89) | 39.3 (135) | 25.7 (148) | 9.33 | 34.41 | 59.14 |
| OLD +10 sessions | 372 | 4.91 | 1.949 | 22.0 | 35.22 | 63.0 (73) | 29.7 (195) | 26.0 (104) | 9.47 | 24.46 | 52.69 |
| VOL matched to C1 | 361 | 4.77 | 1.892 | 35.0 | 34.63 | 68.0 (75) | 28.3 (152) | 23.1 (134) | 9.63 | 23.55 | 51.25 |
| C1 −10 sessions | 361 | 4.77 | 1.892 | 38.0 | 64.27 | 96.2 (106) | 64.0 (111) | 41.0 (144) | 9.37 | 57.06 | 76.18 |
| C1 +10 sessions | 361 | 4.77 | 1.892 | 14.0 | 42.11 | 62.8 (94) | 36.2 (185) | 31.7 (82) | 8.84 | 29.92 | 53.19 |
| VOL matched to C2 | 95 | 1.25 | 0.498 | 28.0 | 35.79 | 70.0 (20) | 42.1 (38) | 10.8 (37) | 9.38 | 28.42 | 48.42 |
| C2 −10 sessions | 95 | 1.25 | 0.498 | 29.0 | 65.26 | 100.0 (32) | 67.9 (28) | 31.4 (35) | 9.03 | 61.05 | 76.84 |
| C2 +10 sessions | 95 | 1.25 | 0.498 | 14.0 | 37.89 | 63.2 (19) | 32.1 (56) | 30.0 (20) | 9.69 | 27.37 | 49.47 |
| VOL matched to C3 | 52 | 0.69 | 0.272 | 22.0 | 38.46 | 77.8 (9) | 48.0 (25) | 5.6 (18) | 8.08 | 30.77 | 46.15 |
| C3 −10 sessions | 52 | 0.69 | 0.272 | 27.5 | 40.38 | 75.0 (12) | 30.4 (23) | 29.4 (17) | 11.55 | 30.77 | 53.85 |
| C3 +10 sessions | 52 | 0.69 | 0.272 | 26.0 | 28.85 | 50.0 (12) | 20.7 (29) | 27.3 (11) | 11.21 | 23.08 | 46.15 |
| VOL matched to C4 | 8 | 0.11 | 0.042 | 16.0 | 62.50 | 100.0 (1) | 66.7 (6) | 0.0 (1) | 7.20 | 37.50 | 62.50 |
| C4 −10 sessions | 8 | 0.11 | 0.042 | 43.0 | 12.50 | 50.0 (2) | 0.0 (3) | 0.0 (3) | 12.99 | 12.50 | 37.50 |
| C4 +10 sessions | 8 | 0.11 | 0.042 | 37.5 | 25.00 | — (0) | 20.0 (5) | 33.3 (3) | 13.87 | 25.00 | 50.00 |
| VOL matched to C5 | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| C5 −10 sessions | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| C5 +10 sessions | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| VOL matched to C6 | 59 | 0.78 | 0.309 | 35.0 | 33.90 | 70.0 (10) | 50.0 (22) | 7.4 (27) | 8.59 | 25.42 | 45.76 |
| C6 −10 sessions | 59 | 0.78 | 0.309 | 36.0 | 40.68 | 61.5 (13) | 36.4 (22) | 33.3 (24) | 9.20 | 38.98 | 59.32 |
| C6 +10 sessions | 59 | 0.78 | 0.309 | 21.0 | 37.29 | 80.0 (10) | 32.4 (34) | 20.0 (15) | 9.67 | 22.03 | 49.15 |
| VOL matched to C7 | 21 | 0.28 | 0.110 | 49.0 | 33.33 | 100.0 (4) | 33.3 (6) | 9.1 (11) | 7.79 | 19.05 | 42.86 |
| C7 −10 sessions | 21 | 0.28 | 0.110 | 19.0 | 66.67 | 88.9 (9) | 40.0 (5) | 57.1 (7) | 15.30 | 57.14 | 80.95 |
| C7 +10 sessions | 21 | 0.28 | 0.110 | 10.0 | 47.62 | 60.0 (10) | 33.3 (9) | 50.0 (2) | 14.67 | 33.33 | 57.14 |
| VOL matched to C8 | 53 | 0.70 | 0.278 | 30.0 | 32.08 | 70.0 (10) | 42.9 (21) | 4.5 (22) | 9.17 | 22.64 | 43.40 |
| C8 −10 sessions | 53 | 0.70 | 0.278 | 40.0 | 41.51 | 68.8 (16) | 23.1 (13) | 33.3 (24) | 7.70 | 28.30 | 60.38 |
| C8 +10 sessions | 53 | 0.70 | 0.278 | 21.0 | 41.51 | 81.8 (11) | 29.2 (24) | 33.3 (18) | 8.17 | 24.53 | 58.49 |

### FF49 industries

| Rule/control | Flags | Flags/group-year | On-share % | Median late | Fake21 % | T1 % (n) | T2 % (n) | T3 % (n) | Mean member DD63 % | Fake10 %¹ | Fake45 %¹ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | 1878 | 4.99 | 1.981 | 19.0 | 39.03 | 56.4 (654) | 32.1 (607) | 27.4 (617) | 10.94 | 25.19 | 56.23 |
| C1 REL | 1748 | 4.65 | 1.844 | 7.0 | 44.11 | 52.2 (836) | 47.3 (355) | 30.0 (557) | 10.82 | 28.95 | 59.38 |
| C2 BOTH | 598 | 1.59 | 0.631 | 6.0 | 41.47 | 49.2 (309) | 44.4 (90) | 28.1 (199) | 11.75 | 26.09 | 56.86 |
| C3 WEEK | 299 | 0.79 | 0.315 | 11.0 | 40.47 | 57.0 (107) | 31.7 (145) | 29.8 (47) | 12.04 | 28.09 | 59.20 |
| C4 TWO_WEEK | 35 | 0.09 | 0.037 | 29.0 | 31.43 | 42.9 (7) | 31.6 (19) | 22.2 (9) | 10.79 | 28.57 | 57.14 |
| C5 BREADTH | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| C6 PARTNER | 365 | 0.97 | 0.385 | 8.0 | 34.52 | 44.8 (165) | 28.2 (78) | 24.6 (122) | 11.00 | 19.18 | 57.81 |
| C7 VOL_RISE | 81 | 0.22 | 0.085 | 8.0 | 48.15 | 62.2 (37) | 26.1 (23) | 47.6 (21) | 13.83 | 32.10 | 64.20 |
| C8 MACRO | 232 | 0.62 | 0.245 | 14.0 | 36.64 | 55.7 (79) | 27.8 (79) | 25.7 (74) | 10.61 | 26.72 | 56.90 |
| VOL33 raw state | 39117 | 103.97 | 41.256 | 33.0 | 35.49 | 71.0 (7520) | 28.5 (18806) | 24.8 (12791) | 11.43 | 24.07 | 52.52 |
| VOL matched to OLD | 1878 | 4.99 | 1.981 | 32.0 | 33.44 | 70.3 (377) | 25.5 (881) | 22.3 (620) | 11.48 | 23.38 | 50.16 |
| OLD −10 sessions | 1878 | 4.99 | 1.981 | 37.0 | 50.27 | 84.5 (485) | 43.5 (692) | 33.2 (701) | 10.89 | 40.42 | 64.64 |
| OLD +10 sessions | 1878 | 4.99 | 1.981 | 17.0 | 38.98 | 70.7 (392) | 33.1 (998) | 25.6 (488) | 11.19 | 26.46 | 54.63 |
| VOL matched to C1 | 1748 | 4.65 | 1.844 | 32.0 | 33.87 | 71.1 (360) | 25.5 (819) | 22.3 (569) | 11.56 | 23.74 | 51.03 |
| C1 −10 sessions | 1748 | 4.65 | 1.844 | 41.0 | 64.30 | 96.4 (533) | 65.0 (494) | 40.1 (721) | 10.90 | 54.81 | 75.74 |
| C1 +10 sessions | 1748 | 4.65 | 1.844 | 14.0 | 43.48 | 70.7 (420) | 36.7 (926) | 30.6 (402) | 10.84 | 30.61 | 56.58 |
| VOL matched to C2 | 598 | 1.59 | 0.631 | 33.0 | 34.62 | 78.2 (124) | 25.2 (262) | 20.8 (212) | 12.53 | 23.75 | 53.68 |
| C2 −10 sessions | 598 | 1.59 | 0.631 | 43.0 | 65.38 | 98.3 (174) | 64.4 (174) | 43.2 (250) | 11.87 | 56.69 | 75.59 |
| C2 +10 sessions | 598 | 1.59 | 0.631 | 14.0 | 41.47 | 68.9 (132) | 36.4 (330) | 27.2 (136) | 12.06 | 28.43 | 54.85 |
| VOL matched to C3 | 299 | 0.79 | 0.315 | 32.0 | 32.11 | 77.4 (62) | 21.4 (145) | 18.5 (92) | 11.39 | 23.75 | 48.83 |
| C3 −10 sessions | 299 | 0.79 | 0.315 | 11.0 | 57.86 | 81.5 (119) | 44.7 (123) | 36.8 (57) | 11.87 | 46.82 | 69.90 |
| C3 +10 sessions | 299 | 0.79 | 0.315 | 16.0 | 38.46 | 59.7 (72) | 31.1 (193) | 35.3 (34) | 12.06 | 25.42 | 57.86 |
| VOL matched to C4 | 35 | 0.09 | 0.037 | 32.0 | 28.57 | 77.8 (9) | 21.4 (14) | 0.0 (12) | 10.11 | 14.29 | 48.57 |
| C4 −10 sessions | 35 | 0.09 | 0.037 | 25.0 | 42.86 | 85.7 (7) | 35.3 (17) | 27.3 (11) | 11.51 | 25.71 | 60.00 |
| C4 +10 sessions | 35 | 0.09 | 0.037 | 24.0 | 31.43 | 50.0 (8) | 23.8 (21) | 33.3 (6) | 10.86 | 8.57 | 48.57 |
| VOL matched to C5 | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| C5 −10 sessions | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| C5 +10 sessions | N/A | — | — | — | — | — (0) | — (0) | — (0) | — | — | — |
| VOL matched to C6 | 365 | 0.97 | 0.385 | 33.0 | 32.60 | 79.1 (67) | 24.0 (179) | 19.3 (119) | 12.36 | 23.84 | 51.78 |
| C6 −10 sessions | 365 | 0.97 | 0.385 | 42.0 | 54.52 | 85.7 (98) | 52.7 (112) | 36.1 (155) | 11.33 | 49.86 | 68.49 |
| C6 +10 sessions | 365 | 0.97 | 0.385 | 15.0 | 40.55 | 73.3 (60) | 36.9 (206) | 28.3 (99) | 11.13 | 24.38 | 56.71 |
| VOL matched to C7 | 81 | 0.22 | 0.085 | 32.0 | 28.40 | 72.2 (18) | 15.2 (33) | 16.7 (30) | 12.30 | 20.99 | 44.44 |
| C7 −10 sessions | 81 | 0.22 | 0.085 | 31.0 | 67.90 | 92.9 (28) | 73.9 (23) | 40.0 (30) | 14.32 | 56.79 | 80.25 |
| C7 +10 sessions | 81 | 0.22 | 0.085 | 13.0 | 41.98 | 64.0 (25) | 35.6 (45) | 18.2 (11) | 13.01 | 28.40 | 53.09 |
| VOL matched to C8 | 232 | 0.62 | 0.245 | 34.0 | 31.03 | 76.1 (46) | 20.6 (107) | 19.0 (79) | 12.07 | 23.28 | 47.41 |
| C8 −10 sessions | 232 | 0.62 | 0.245 | 39.0 | 49.57 | 77.8 (63) | 45.6 (79) | 33.3 (90) | 10.56 | 40.95 | 63.36 |
| C8 +10 sessions | 232 | 0.62 | 0.245 | 18.0 | 37.93 | 70.4 (54) | 28.3 (113) | 27.7 (65) | 10.65 | 25.43 | 56.47 |

### All eligible group series, descriptive only

| Rule/control | Flags | Flags/group-year | On-share % | Median late | Fake21 % | T1 % (n) | T2 % (n) | T3 % (n) | Mean member DD63 % | Fake10 %¹ | Fake45 %¹ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | 2705 | 4.97 | 1.973 | 20.0 | 37.56 | 55.4 (905) | 30.7 (910) | 26.5 (890) | 10.73 | 23.99 | 55.01 |
| C1 REL | 2528 | 4.65 | 1.844 | 7.0 | 43.31 | 51.5 (1229) | 45.7 (501) | 29.2 (798) | 10.59 | 28.48 | 58.50 |
| C2 BOTH | 816 | 1.50 | 0.595 | 6.0 | 40.07 | 47.5 (432) | 42.7 (124) | 26.5 (260) | 11.52 | 24.63 | 55.39 |
| C3 WEEK | 424 | 0.78 | 0.309 | 14.0 | 40.09 | 56.1 (139) | 32.0 (206) | 32.9 (79) | 11.92 | 25.94 | 56.84 |
| C4 TWO_WEEK | 49 | 0.09 | 0.036 | 29.0 | 28.57 | 30.0 (10) | 30.8 (26) | 23.1 (13) | 10.94 | 20.41 | 55.10 |
| C5 BREADTH | 350 | 3.80 | 1.507 | 22.0 | 35.14 | 48.7 (113) | 33.3 (120) | 23.9 (117) | 11.24 | 21.71 | 55.43 |
| C6 PARTNER | 490 | 0.90 | 0.357 | 8.0 | 34.49 | 43.7 (213) | 32.5 (120) | 23.6 (157) | 10.53 | 19.39 | 56.53 |
| C7 VOL_RISE | 120 | 0.22 | 0.088 | 8.0 | 49.17 | 66.1 (56) | 27.3 (33) | 41.9 (31) | 14.33 | 35.83 | 64.17 |
| C8 MACRO | 343 | 0.63 | 0.250 | 17.0 | 35.86 | 53.8 (106) | 28.5 (123) | 27.2 (114) | 10.02 | 26.53 | 58.31 |
| VOL33 raw state | 56448 | 103.74 | 41.167 | 33.0 | 34.92 | 70.3 (10783) | 27.7 (27186) | 24.9 (18479) | 11.24 | 23.69 | 51.76 |
| VOL matched to OLD | 2705 | 4.97 | 1.973 | 33.0 | 33.68 | 68.5 (534) | 25.8 (1276) | 24.1 (895) | 11.16 | 23.29 | 50.31 |
| OLD −10 sessions | 2705 | 4.97 | 1.973 | 37.0 | 48.35 | 82.7 (688) | 41.8 (989) | 31.7 (1028) | 10.68 | 38.82 | 62.92 |
| OLD +10 sessions | 2705 | 4.97 | 1.973 | 18.0 | 37.82 | 68.6 (548) | 32.5 (1431) | 25.1 (726) | 10.98 | 25.58 | 54.01 |
| VOL matched to C1 | 2528 | 4.65 | 1.844 | 33.0 | 33.90 | 69.8 (503) | 25.7 (1188) | 24.0 (837) | 11.26 | 23.50 | 50.67 |
| C1 −10 sessions | 2528 | 4.65 | 1.844 | 41.0 | 64.52 | 96.5 (772) | 64.5 (710) | 40.9 (1046) | 10.72 | 55.62 | 75.75 |
| C1 +10 sessions | 2528 | 4.65 | 1.844 | 14.0 | 42.68 | 68.8 (612) | 36.1 (1334) | 30.2 (582) | 10.57 | 30.10 | 54.91 |
| VOL matched to C2 | 816 | 1.50 | 0.595 | 32.5 | 33.95 | 76.4 (157) | 26.7 (375) | 20.1 (284) | 12.21 | 23.41 | 51.35 |
| C2 −10 sessions | 816 | 1.50 | 0.595 | 43.0 | 65.32 | 98.4 (248) | 63.9 (230) | 42.0 (338) | 11.55 | 57.84 | 75.61 |
| C2 +10 sessions | 816 | 1.50 | 0.595 | 14.0 | 39.95 | 65.5 (174) | 35.2 (463) | 27.4 (179) | 11.88 | 27.45 | 52.70 |
| VOL matched to C3 | 424 | 0.78 | 0.309 | 32.0 | 32.08 | 72.5 (80) | 25.7 (210) | 17.9 (134) | 10.94 | 23.58 | 46.70 |
| C3 −10 sessions | 424 | 0.78 | 0.309 | 12.0 | 54.01 | 79.0 (162) | 42.0 (169) | 32.3 (93) | 11.79 | 43.63 | 67.22 |
| C3 +10 sessions | 424 | 0.78 | 0.309 | 17.5 | 37.50 | 57.3 (96) | 30.8 (266) | 35.5 (62) | 11.93 | 25.94 | 57.08 |
| VOL matched to C4 | 49 | 0.09 | 0.036 | 32.0 | 34.69 | 80.0 (10) | 33.3 (24) | 6.7 (15) | 10.23 | 20.41 | 51.02 |
| C4 −10 sessions | 49 | 0.09 | 0.036 | 28.0 | 40.82 | 80.0 (10) | 34.8 (23) | 25.0 (16) | 11.42 | 26.53 | 59.18 |
| C4 +10 sessions | 49 | 0.09 | 0.036 | 25.0 | 34.69 | 50.0 (8) | 31.2 (32) | 33.3 (9) | 11.01 | 12.24 | 51.02 |
| VOL matched to C5 | 350 | 3.80 | 1.507 | 34.0 | 32.00 | 64.4 (59) | 22.7 (181) | 30.0 (110) | 11.70 | 21.71 | 48.00 |
| C5 −10 sessions | 350 | 3.80 | 1.507 | 36.5 | 47.14 | 82.0 (89) | 39.3 (122) | 31.7 (139) | 11.30 | 38.29 | 62.86 |
| C5 +10 sessions | 350 | 3.80 | 1.507 | 17.0 | 37.14 | 61.2 (67) | 34.3 (181) | 26.5 (102) | 11.62 | 24.57 | 54.57 |
| VOL matched to C6 | 490 | 0.90 | 0.357 | 34.0 | 31.63 | 76.2 (80) | 26.0 (242) | 18.5 (168) | 11.86 | 22.24 | 48.98 |
| C6 −10 sessions | 490 | 0.90 | 0.357 | 41.0 | 53.47 | 84.8 (132) | 51.3 (154) | 34.8 (204) | 10.74 | 48.37 | 67.76 |
| C6 +10 sessions | 490 | 0.90 | 0.357 | 15.5 | 39.80 | 72.3 (83) | 36.7 (281) | 25.4 (126) | 10.78 | 23.67 | 55.92 |
| VOL matched to C7 | 120 | 0.22 | 0.088 | 34.0 | 29.17 | 77.3 (22) | 20.4 (54) | 15.9 (44) | 11.46 | 20.00 | 43.33 |
| C7 −10 sessions | 120 | 0.22 | 0.088 | 26.0 | 67.50 | 91.1 (45) | 69.7 (33) | 40.5 (42) | 14.67 | 58.33 | 79.17 |
| C7 +10 sessions | 120 | 0.22 | 0.088 | 13.0 | 40.83 | 58.1 (43) | 35.0 (60) | 17.6 (17) | 13.48 | 27.50 | 50.83 |
| VOL matched to C8 | 343 | 0.63 | 0.250 | 34.0 | 30.03 | 72.1 (61) | 23.6 (165) | 17.1 (117) | 11.65 | 21.57 | 44.90 |
| C8 −10 sessions | 343 | 0.63 | 0.250 | 40.0 | 48.40 | 77.1 (96) | 42.6 (108) | 33.1 (139) | 9.89 | 37.61 | 63.27 |
| C8 +10 sessions | 343 | 0.63 | 0.250 | 18.0 | 39.36 | 71.8 (78) | 30.7 (166) | 28.3 (99) | 10.06 | 25.36 | 58.31 |



---

PRO-RUN SUCC-AVOID-1 part 3

## 2. Tables continued — matched comparisons and the 50 bp gate

Cells are **candidate minus comparator**, with a calendar-month bootstrap 90% interval. For fake rates, negative is better. For event drawdown captured/avoided, positive is better. The OLD comparison matches exact `(group, integer lateness)` cells, then uses candidate counts as weights. It is not just a tercile adjustment. Different candidates therefore target different OLD mixtures; the unconditional OLD row is not the adjusted counterfactual.

The volatility comparison is matched on per-group event on-share. Shifts preserve each original event and group; both members of a pair are resampled using the original flag's month. We used 2,000 month draws, seed 1101401, with the entire cross-section resampled jointly. The same month multiplicities apply to all rules/controls. Exact-cell means and supported cells are recomputed within each draw. Undefined draws are omitted and counted in the machine-readable effects.

Usable bootstrap draws range from **1984 to 2000** across the displayed estimates; sparse two-week rows account for missing draws. Intervals are not adjusted for choosing among eight candidates and may be too narrow when 63-session windows overlap across months.

### FF12: fake21 differences, percentage points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | +0.44 [-6.17, +7.11] | -11.65 [-15.49, -7.79] | -2.20 [-5.43, +1.06] |
| C1 REL | 80.0% | +1.79 [-3.30, +8.10] | +6.21 [+0.07, +12.63] | -26.01 [-30.77, -20.98] | -0.24 [-3.74, +3.08] |
| C2 BOTH | 100.0% | -3.94 [-5.45, -0.01] | +5.69 [-5.67, +16.95] | -30.08 [-39.22, -20.93] | +0.81 [-5.74, +7.30] |
| C3 WEEK | 100.0% | -0.85 [-5.39, +3.47] | +12.33 [-1.02, +24.06] | -8.22 [-18.75, +2.35] | +0.00 [-9.52, +8.89] |
| C4 TWO_WEEK | 100.0% | -9.52 [-25.00, +0.00] | -16.67 [-60.00, +31.59] | -50.00 [-87.50, +0.00] | -50.00 [-85.71, -20.00] |
| C5 BREADTH | 100.0% | +0.18 [-0.75, +1.00] | +3.14 [-4.35, +10.46] | -12.00 [-16.67, -7.38] | -2.00 [-5.90, +1.98] |
| C6 PARTNER | 100.0% | -3.20 [-7.28, +1.34] | +12.12 [-2.42, +26.12] | -22.73 [-33.85, -11.11] | -1.52 [-12.07, +8.22] |
| C7 VOL_RISE | 100.0% | +4.54 [-3.67, +13.50] | +16.67 [-12.12, +44.44] | -22.22 [-38.46, -7.14] | +16.67 [+0.00, +35.71] |
| C8 MACRO | 100.0% | -0.15 [-5.62, +4.72] | +10.34 [-5.78, +25.91] | -15.52 [-27.17, -3.33] | -8.62 [-24.33, +4.55] |

### ETF: fake21 differences, percentage points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | -0.54 [-6.71, +5.64] | -7.53 [-12.76, -2.91] | +0.54 [-3.31, +4.30] |
| C1 REL | 75.3% | +4.64 [-3.08, +11.15] | +9.14 [+3.53, +14.74] | -20.50 [-25.07, -16.03] | +1.66 [-2.31, +5.57] |
| C2 BOTH | 100.0% | -1.89 [-5.41, +2.06] | +2.11 [-8.37, +12.68] | -27.37 [-37.50, -17.20] | +0.00 [-6.82, +7.07] |
| C3 WEEK | 100.0% | +2.44 [-3.17, +7.64] | +0.00 [-15.29, +15.92] | -1.92 [-14.29, +10.20] | +9.62 [+1.75, +18.42] |
| C4 TWO_WEEK | 100.0% | -6.25 [-23.81, +10.92] | -37.50 [-76.62, +11.11] | +12.50 [-25.00, +50.00] | +0.00 [+0.00, +0.00] |
| C5 BREADTH | N/A | N/A | N/A | N/A | N/A |
| C6 PARTNER | 100.0% | -5.14 [-8.17, +0.09] | -1.69 [-14.90, +11.75] | -8.47 [-20.69, +3.57] | -5.08 [-14.29, +3.34] |
| C7 VOL_RISE | 100.0% | -5.95 [-12.50, +6.78] | +23.81 [+0.00, +45.00] | -9.52 [-26.92, +5.88] | +9.52 [-10.00, +25.00] |
| C8 MACRO | 100.0% | -1.16 [-5.54, +4.74] | +1.89 [-12.34, +20.58] | -7.55 [-20.83, +5.13] | -7.55 [-18.46, +3.57] |

### FF49: fake21 differences, percentage points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | +5.59 [+1.82, +9.35] | -11.24 [-14.14, -8.70] | +0.05 [-2.05, +2.18] |
| C1 REL | 81.1% | +1.22 [-1.98, +3.99] | +10.24 [+7.17, +13.39] | -20.19 [-22.91, -17.41] | +0.63 [-1.39, +2.57] |
| C2 BOTH | 100.0% | -1.61 [-2.57, +0.02] | +6.86 [+1.40, +12.59] | -23.91 [-29.07, -19.27] | +0.00 [-3.68, +3.70] |
| C3 WEEK | 100.0% | +0.50 [-1.87, +2.64] | +8.36 [+0.30, +16.38] | -17.39 [-23.79, -11.89] | +2.01 [-2.68, +6.82] |
| C4 TWO_WEEK | 100.0% | -5.46 [-10.21, +1.95] | +2.86 [-16.53, +22.12] | -11.43 [-23.53, +0.00] | +0.00 [-12.51, +14.29] |
| C5 BREADTH | N/A | N/A | N/A | N/A | N/A |
| C6 PARTNER | 100.0% | -1.04 [-2.69, +1.57] | +1.92 [-4.57, +8.56] | -20.00 [-27.14, -12.77] | -6.03 [-9.97, -1.98] |
| C7 VOL_RISE | 100.0% | +3.11 [-3.45, +6.53] | +19.75 [+4.20, +34.47] | -19.75 [-33.77, -8.76] | +6.17 [-3.70, +13.79] |
| C8 MACRO | 100.0% | -1.34 [-4.37, +1.99] | +5.60 [-4.02, +16.16] | -12.93 [-19.39, -6.45] | -1.29 [-10.81, +10.96] |

### ALL: fake21 differences, percentage points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | +3.88 [+0.17, +7.67] | -10.79 [-13.75, -8.13] | -0.26 [-2.51, +1.88] |
| C1 REL | 80.1% | +1.78 [-1.23, +4.44] | +9.41 [+6.47, +12.40] | -21.20 [-24.08, -18.28] | +0.63 [-1.28, +2.48] |
| C2 BOTH | 100.0% | -2.00 [-2.76, -0.22] | +6.13 [+0.92, +11.53] | -25.25 [-30.51, -20.10] | +0.12 [-3.36, +3.76] |
| C3 WEEK | 100.0% | +0.50 [-1.66, +2.37] | +8.02 [+1.19, +14.97] | -13.92 [-20.13, -8.23] | +2.59 [-2.01, +7.06] |
| C4 TWO_WEEK | 100.0% | -6.08 [-10.01, +0.40] | -6.12 [-21.71, +10.97] | -12.24 [-26.67, +1.72] | -6.12 [-17.81, +6.25] |
| C5 BREADTH | 100.0% | +0.18 [-0.75, +1.00] | +3.14 [-4.35, +10.46] | -12.00 [-16.67, -7.38] | -2.00 [-5.90, +1.98] |
| C6 PARTNER | 100.0% | -1.82 [-3.13, +0.49] | +2.86 [-3.07, +9.12] | -18.98 [-25.49, -12.31] | -5.31 [-9.47, -1.31] |
| C7 VOL_RISE | 100.0% | +1.74 [-2.88, +5.52] | +20.00 [+6.54, +32.96] | -18.33 [-29.57, -9.25] | +8.33 [-0.79, +16.01] |
| C8 MACRO | 100.0% | -1.11 [-4.01, +2.05] | +5.83 [-3.53, +16.36] | -12.54 [-19.94, -5.33] | -3.50 [-13.10, +8.22] |

### What the drawdown contrast actually means

For each flag, the counterfactual holds a unit exposure through the **next session's close**, then stays flat at zero return through t+63: 62 post-exit return intervals. It assumes no same-close fill. `Event avoidance = hold-through-63 MDD − delayed-exit MDD`, averaged across members. The following table compares this amount across rule/control events. A benefit must have a 90% lower bound **strictly greater than +50 bp**, alongside better fake21 discrimination against matched OLD, matched VOL and both shifts.

This event quantity is structurally nonnegative before taking the comparator difference: the exit path is a prefix of the held path. It can credit avoidance of a fall from a much higher future peak while the exit gives up the intervening gain. Accordingly it measures **event-level damage capture**, not validated portfolio improvement. Continuous-path and missed-return diagnostics follow.

### FF12: incremental event drawdown avoidance, basis points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | -2.01 [-166.33, +188.84] | -7.78 [-38.00, +24.84] | -24.06 [-79.70, +22.69] |
| C1 REL | 80.0% | +36.22 [-49.04, +129.93] | -31.22 [-152.43, +96.16] | -21.72 [-64.41, +16.68] | +9.41 [-32.75, +48.02] |
| C2 BOTH | 100.0% | +15.03 [-19.15, +44.11] | -40.39 [-245.08, +174.98] | +8.30 [-43.86, +62.06] | -40.90 [-100.94, +14.26] |
| C3 WEEK | 100.0% | +81.05 [-32.95, +177.16] | +91.96 [-250.24, +505.92] | -0.16 [-46.62, +52.55] | +30.42 [-51.96, +98.16] |
| C4 TWO_WEEK | 100.0% | -108.75 [-246.88, +26.15] | -689.19 [-1490.34, +46.14] | -91.25 [-180.31, -23.29] | +93.20 [+26.12, +158.45] |
| C5 BREADTH | 100.0% | -0.93 [-12.58, +8.97] | -24.32 [-195.94, +170.99] | -17.99 [-52.12, +18.28] | -24.91 [-80.67, +22.27] |
| C6 PARTNER | 100.0% | -61.53 [-88.17, -3.98] | -263.23 [-440.17, -102.74] | -0.68 [-43.88, +41.70] | -73.59 [-177.51, +6.82] |
| C7 VOL_RISE | 100.0% | +274.98 [-28.69, +505.81] | +315.78 [-491.14, +1149.33] | -79.44 [-221.86, +61.39] | +155.63 [+40.70, +342.28] |
| C8 MACRO | 100.0% | -107.96 [-165.05, -15.02] | -236.03 [-485.25, +53.15] | +10.90 [-52.22, +60.08] | +12.63 [-34.23, +75.86] |

### ETF: incremental event drawdown avoidance, basis points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | +27.81 [-117.41, +196.66] | -15.65 [-47.55, +15.94] | +1.83 [-41.48, +39.20] |
| C1 REL | 75.3% | +31.82 [-76.78, +123.65] | -11.06 [-94.44, +76.03] | -35.39 [-81.07, +6.79] | +35.86 [-5.39, +78.03] |
| C2 BOTH | 100.0% | +20.85 [-29.10, +52.35] | +23.34 [-171.06, +236.88] | +0.57 [-61.41, +62.09] | -39.00 [-107.37, +16.93] |
| C3 WEEK | 100.0% | +108.63 [-1.46, +155.31] | +383.77 [+13.47, +793.99] | -9.10 [-58.28, +34.26] | +102.99 [+29.51, +183.91] |
| C4 TWO_WEEK | 100.0% | +206.75 [-14.55, +322.35] | +640.12 [-247.90, +1479.44] | +79.25 [-27.36, +165.21] | +43.83 [-65.80, +167.95] |
| C5 BREADTH | N/A | N/A | N/A | N/A | N/A |
| C6 PARTNER | 100.0% | +23.70 [-48.54, +67.67] | +82.74 [-126.06, +298.06] | -12.27 [-67.88, +44.99] | -37.99 [-168.16, +58.92] |
| C7 VOL_RISE | 100.0% | +280.40 [-18.54, +599.25] | +818.17 [+235.85, +1387.56] | -24.45 [-198.43, +120.70] | +221.44 [+42.51, +471.05] |
| C8 MACRO | 100.0% | -68.69 [-131.62, +16.65] | -71.30 [-320.49, +187.03] | +18.93 [-14.87, +51.97] | -14.21 [-40.88, +18.55] |

### FF49: incremental event drawdown avoidance, basis points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | -24.30 [-157.20, +127.21] | -13.77 [-49.87, +24.46] | -8.56 [-59.57, +36.75] |
| C1 REL | 81.1% | -20.64 [-64.14, +47.73] | -52.44 [-138.67, +36.97] | -26.30 [-62.08, +13.22] | +5.02 [-32.98, +41.10] |
| C2 BOTH | 100.0% | +5.11 [-13.28, +25.64] | -53.68 [-200.09, +105.02] | -32.95 [-72.39, +5.20] | -8.00 [-55.13, +38.93] |
| C3 WEEK | 100.0% | +38.18 [-23.08, +76.44] | +90.22 [-193.08, +432.26] | +0.83 [-44.71, +48.05] | +36.98 [-13.23, +84.80] |
| C4 TWO_WEEK | 100.0% | +15.59 [-64.26, +81.46] | +89.70 [-378.39, +663.05] | -91.54 [-189.88, -8.75] | +16.07 [-51.04, +79.76] |
| C5 BREADTH | N/A | N/A | N/A | N/A | N/A |
| C6 PARTNER | 100.0% | +14.40 [-25.50, +40.08] | -110.91 [-247.11, +24.90] | -34.71 [-110.19, +37.45] | +9.91 [-50.47, +64.17] |
| C7 VOL_RISE | 100.0% | +120.68 [-53.09, +272.26] | +155.11 [-242.91, +618.59] | -94.08 [-187.31, -8.06] | +132.86 [-4.52, +346.81] |
| C8 MACRO | 100.0% | +1.54 [-60.37, +58.81] | -132.86 [-386.30, +137.88] | -17.30 [-84.76, +57.85] | +1.94 [-37.77, +49.13] |

### ALL: incremental event drawdown avoidance, basis points

| Rule | Exact-lateness support | vs OLD, exact lateness | vs VOL, same on-share | vs own −10 days | vs own +10 days |
|---|---|---|---|---|---|
| OLD absolute top | 100.0% | +0.00 [+0.00, +0.00] | -13.39 [-150.67, +146.65] | -13.02 [-46.76, +22.68] | -9.74 [-58.80, +34.12] |
| C1 REL | 80.1% | -4.18 [-50.20, +61.96] | -43.01 [-128.87, +47.12] | -26.84 [-62.43, +10.64] | +10.15 [-27.31, +45.67] |
| C2 BOTH | 100.0% | +8.44 [-8.76, +23.90] | -42.71 [-191.06, +115.31] | -22.83 [-64.83, +17.00] | -16.57 [-64.10, +27.91] |
| C3 WEEK | 100.0% | +54.20 [-13.55, +92.22] | +126.52 [-158.90, +471.66] | -0.56 [-41.19, +42.05] | +43.94 [-7.27, +89.87] |
| C4 TWO_WEEK | 100.0% | +31.58 [-57.71, +87.94] | +84.19 [-359.34, +628.30] | -63.62 [-148.00, +2.78] | +30.05 [-24.23, +78.76] |
| C5 BREADTH | 100.0% | -0.93 [-12.58, +8.97] | -24.32 [-195.94, +170.99] | -17.99 [-52.12, +18.28] | -24.91 [-80.67, +22.27] |
| C6 PARTNER | 100.0% | +5.29 [-25.30, +26.22] | -108.11 [-235.01, +16.54] | -27.43 [-91.24, +33.59] | -7.10 [-77.13, +50.67] |
| C7 VOL_RISE | 100.0% | +171.78 [-33.67, +321.62] | +295.25 [-166.73, +804.07] | -79.70 [-176.18, +12.71] | +151.77 [+16.76, +354.99] |
| C8 MACRO | 100.0% | -27.83 [-82.32, +33.32] | -140.79 [-366.33, +120.39] | -6.93 [-62.45, +52.96] | +1.25 [-33.48, +43.01] |

### Adjudication

**No candidate passes all the gates.** C2 and C6 are the two finalists under the pre-fixed FF12 rank: at least 30 flags in at least four FF12 groups, then smallest matched-lateness fake21 difference, then larger VOL-relative avoidance, then ID. C4 (6 FF12 flags) and C7 (18) fail that ranking floor; they remain fully reported, not dropped.

| Candidate | Reading |
|---|---|
| C1 | Relative roll-over alone has more pooled fakes; no replacement. |
| C2 | **Fewer fake breakdowns, nothing avoided** applies to its small matched-lateness FF12 result, not its raw rate. Raw FF12 fakes rise from 32.97% to 34.96%; median lateness falls from 24 to 5. The adjusted −3.94pp interval barely excludes zero. Incremental avoidance versus matched OLD is +15.0bp [−19.2,+44.1], below the required 50bp even at the upper endpoint. |
| C3 | Higher weekly bearish state does not produce a stable fake-rate improvement. |
| C4 | **Fewer fake breakdowns, later** describes the pooled comparison (28.57% vs 37.56%; median 29 vs 20 sessions). The matched result is uncertain, and only six FF12 flags exist. No qualified win. |
| C5 | Proxy breadth leaves the matched FF12 fake rate essentially unchanged (+0.18pp). |
| C6 | Some lower pooled fake rates outside FF12; no stable matched OLD improvement. FF12 avoidance is worse than OLD (−61.5bp [−88.2,−4.0]) and matched VOL (−263.2bp [−440.2,−102.7]). |
| C7 | It selects larger subsequent drawdowns, but fake breakdowns are more frequent; this is not the requested solution. |
| C8 | The macro filter supplies no stable matched improvement or joint win. |

Exact estimates, all six outcomes and valid-draw counts are in [results/effects.json](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/effects.json). Full matching support does not mean independent comparisons: C2 has an additional OLD event in only 94/123 FF12 cells' flag observations, 65/95 ETF and 444/598 FF49; the remainder compare a flag largely or entirely with itself. C6's corresponding counts are 42/66, 37/59 and 251/365. See [results/matching_information.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/matching_information.csv).


---

PRO-RUN SUCC-AVOID-1 part 4

## 2. Tables continued — actual annual flag counts

`—` means no eligible observations, not zero signal frequency. Counts for shifted controls are assigned to the original flag's calendar year so numerator and eligible-source denominator remain aligned. Matched VOL dates retain their own years; total counts match per group over the scored block, not within each year. Rates with annual eligible group-day denominators are also supplied in the CSV.

### FF12

| Rule | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | — | — | — | 60 | 50 | 59 | 58 | 73 | 58 | 52 | 45 |
| C1 REL | — | — | — | 50 | 48 | 52 | 53 | 59 | 51 | 70 | 36 |
| C2 BOTH | — | — | — | 18 | 17 | 16 | 13 | 17 | 21 | 8 | 13 |
| C3 WEEK | — | — | — | 15 | 4 | 7 | 10 | 18 | 8 | 3 | 8 |
| C4 TWO_WEEK | — | — | — | 1 | 0 | 0 | 1 | 1 | 3 | 0 | 0 |
| C5 BREADTH | — | — | — | 44 | 31 | 44 | 46 | 58 | 43 | 46 | 38 |
| C6 PARTNER | — | — | — | 14 | 11 | 12 | 8 | 5 | 4 | 3 | 9 |
| C7 VOL_RISE | — | — | — | 0 | 3 | 1 | 2 | 6 | 4 | 2 | 0 |
| C8 MACRO | — | — | — | 17 | 5 | 6 | 0 | 0 | 2 | 17 | 11 |
| VOL33 raw state | — | — | — | 870 | 0 | 854 | 756 | 2451 | 895 | 2702 | 1004 |
| VOL matched to OLD | — | — | — | 50 | 0 | 47 | 45 | 106 | 26 | 135 | 46 |
| OLD −10 sessions | — | — | — | 60 | 50 | 59 | 58 | 73 | 58 | 52 | 45 |
| OLD +10 sessions | — | — | — | 60 | 50 | 59 | 58 | 73 | 58 | 52 | 45 |
| VOL matched to C1 | — | — | — | 47 | 0 | 44 | 42 | 98 | 23 | 120 | 45 |
| C1 −10 sessions | — | — | — | 50 | 48 | 52 | 53 | 59 | 51 | 70 | 36 |
| C1 +10 sessions | — | — | — | 50 | 48 | 52 | 53 | 59 | 51 | 70 | 36 |
| VOL matched to C2 | — | — | — | 17 | 0 | 11 | 9 | 32 | 8 | 32 | 14 |
| C2 −10 sessions | — | — | — | 18 | 17 | 16 | 13 | 17 | 21 | 8 | 13 |
| C2 +10 sessions | — | — | — | 18 | 17 | 16 | 13 | 17 | 21 | 8 | 13 |
| VOL matched to C3 | — | — | — | 11 | 0 | 11 | 6 | 19 | 1 | 18 | 7 |
| C3 −10 sessions | — | — | — | 15 | 4 | 7 | 10 | 18 | 8 | 3 | 8 |
| C3 +10 sessions | — | — | — | 15 | 4 | 7 | 10 | 18 | 8 | 3 | 8 |
| VOL matched to C4 | — | — | — | 2 | 0 | 0 | 0 | 2 | 0 | 1 | 1 |
| C4 −10 sessions | — | — | — | 1 | 0 | 0 | 1 | 1 | 3 | 0 | 0 |
| C4 +10 sessions | — | — | — | 1 | 0 | 0 | 1 | 1 | 3 | 0 | 0 |
| VOL matched to C5 | — | — | — | 40 | 0 | 34 | 31 | 83 | 19 | 110 | 33 |
| C5 −10 sessions | — | — | — | 44 | 31 | 44 | 46 | 58 | 43 | 46 | 38 |
| C5 +10 sessions | — | — | — | 44 | 31 | 44 | 46 | 58 | 43 | 46 | 38 |
| VOL matched to C6 | — | — | — | 11 | 0 | 9 | 3 | 17 | 4 | 14 | 8 |
| C6 −10 sessions | — | — | — | 14 | 11 | 12 | 8 | 5 | 4 | 3 | 9 |
| C6 +10 sessions | — | — | — | 14 | 11 | 12 | 8 | 5 | 4 | 3 | 9 |
| VOL matched to C7 | — | — | — | 4 | 0 | 3 | 1 | 3 | 0 | 3 | 4 |
| C7 −10 sessions | — | — | — | 0 | 3 | 1 | 2 | 6 | 4 | 2 | 0 |
| C7 +10 sessions | — | — | — | 0 | 3 | 1 | 2 | 6 | 4 | 2 | 0 |
| VOL matched to C8 | — | — | — | 7 | 0 | 6 | 6 | 17 | 1 | 16 | 5 |
| C8 −10 sessions | — | — | — | 17 | 5 | 6 | 0 | 0 | 2 | 17 | 11 |
| C8 +10 sessions | — | — | — | 17 | 5 | 6 | 0 | 0 | 2 | 17 | 11 |

### ETF

| Rule | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | — | — | — | 39 | 42 | 44 | 51 | 64 | 50 | 46 | 36 |
| C1 REL | — | — | — | 50 | 39 | 42 | 40 | 46 | 50 | 59 | 35 |
| C2 BOTH | — | — | — | 14 | 15 | 11 | 14 | 13 | 14 | 7 | 7 |
| C3 WEEK | — | — | — | 7 | 6 | 7 | 5 | 14 | 5 | 3 | 5 |
| C4 TWO_WEEK | — | — | — | 0 | 1 | 1 | 0 | 4 | 2 | 0 | 0 |
| C5 BREADTH | — | — | — | — | — | — | — | — | — | — | — |
| C6 PARTNER | — | — | — | 6 | 11 | 9 | 11 | 7 | 2 | 7 | 6 |
| C7 VOL_RISE | — | — | — | 1 | 3 | 1 | 0 | 9 | 7 | 0 | 0 |
| C8 MACRO | — | — | — | 13 | 6 | 5 | 0 | 0 | 6 | 14 | 9 |
| VOL33 raw state | — | — | — | 611 | 27 | 733 | 556 | 2003 | 620 | 2424 | 825 |
| VOL matched to OLD | — | — | — | 35 | 1 | 35 | 26 | 102 | 32 | 99 | 42 |
| OLD −10 sessions | — | — | — | 39 | 42 | 44 | 51 | 64 | 50 | 46 | 36 |
| OLD +10 sessions | — | — | — | 39 | 42 | 44 | 51 | 64 | 50 | 46 | 36 |
| VOL matched to C1 | — | — | — | 36 | 1 | 34 | 25 | 95 | 32 | 95 | 43 |
| C1 −10 sessions | — | — | — | 50 | 39 | 42 | 40 | 46 | 50 | 59 | 35 |
| C1 +10 sessions | — | — | — | 50 | 39 | 42 | 40 | 46 | 50 | 59 | 35 |
| VOL matched to C2 | — | — | — | 11 | 0 | 6 | 8 | 27 | 13 | 13 | 17 |
| C2 −10 sessions | — | — | — | 14 | 15 | 11 | 14 | 13 | 14 | 7 | 7 |
| C2 +10 sessions | — | — | — | 14 | 15 | 11 | 14 | 13 | 14 | 7 | 7 |
| VOL matched to C3 | — | — | — | 9 | 0 | 5 | 2 | 10 | 5 | 7 | 14 |
| C3 −10 sessions | — | — | — | 7 | 6 | 7 | 5 | 14 | 5 | 3 | 5 |
| C3 +10 sessions | — | — | — | 7 | 6 | 7 | 5 | 14 | 5 | 3 | 5 |
| VOL matched to C4 | — | — | — | 1 | 0 | 1 | 1 | 2 | 1 | 2 | 0 |
| C4 −10 sessions | — | — | — | 0 | 1 | 1 | 0 | 4 | 2 | 0 | 0 |
| C4 +10 sessions | — | — | — | 0 | 1 | 1 | 0 | 4 | 2 | 0 | 0 |
| VOL matched to C5 | — | — | — | — | — | — | — | — | — | — | — |
| C5 −10 sessions | — | — | — | — | — | — | — | — | — | — | — |
| C5 +10 sessions | — | — | — | — | — | — | — | — | — | — | — |
| VOL matched to C6 | — | — | — | 8 | 0 | 4 | 6 | 13 | 6 | 10 | 12 |
| C6 −10 sessions | — | — | — | 6 | 11 | 9 | 11 | 7 | 2 | 7 | 6 |
| C6 +10 sessions | — | — | — | 6 | 11 | 9 | 11 | 7 | 2 | 7 | 6 |
| VOL matched to C7 | — | — | — | 3 | 0 | 2 | 1 | 5 | 4 | 2 | 4 |
| C7 −10 sessions | — | — | — | 1 | 3 | 1 | 0 | 9 | 7 | 0 | 0 |
| C7 +10 sessions | — | — | — | 1 | 3 | 1 | 0 | 9 | 7 | 0 | 0 |
| VOL matched to C8 | — | — | — | 6 | 0 | 4 | 2 | 16 | 5 | 7 | 13 |
| C8 −10 sessions | — | — | — | 13 | 6 | 5 | 0 | 0 | 6 | 14 | 9 |
| C8 +10 sessions | — | — | — | 13 | 6 | 5 | 0 | 0 | 6 | 14 | 9 |

### FF49

| Rule | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | — | — | — | 247 | 238 | 204 | 277 | 316 | 206 | 224 | 166 |
| C1 REL | — | — | — | 243 | 223 | 216 | 229 | 233 | 182 | 267 | 155 |
| C2 BOTH | — | — | — | 80 | 99 | 53 | 85 | 88 | 85 | 52 | 56 |
| C3 WEEK | — | — | — | 50 | 33 | 34 | 41 | 65 | 37 | 11 | 28 |
| C4 TWO_WEEK | — | — | — | 4 | 2 | 1 | 9 | 6 | 7 | 0 | 6 |
| C5 BREADTH | — | — | — | — | — | — | — | — | — | — | — |
| C6 PARTNER | — | — | — | 55 | 43 | 34 | 45 | 82 | 39 | 32 | 35 |
| C7 VOL_RISE | — | — | — | 2 | 5 | 10 | 8 | 21 | 24 | 9 | 2 |
| C8 MACRO | — | — | — | 56 | 20 | 18 | 2 | 0 | 5 | 90 | 41 |
| VOL33 raw state | — | — | — | 3794 | 142 | 2977 | 3743 | 9742 | 4346 | 10985 | 3388 |
| VOL matched to OLD | — | — | — | 184 | 5 | 147 | 163 | 478 | 188 | 550 | 163 |
| OLD −10 sessions | — | — | — | 247 | 238 | 204 | 277 | 316 | 206 | 224 | 166 |
| OLD +10 sessions | — | — | — | 247 | 238 | 204 | 277 | 316 | 206 | 224 | 166 |
| VOL matched to C1 | — | — | — | 176 | 4 | 135 | 148 | 438 | 185 | 513 | 149 |
| C1 −10 sessions | — | — | — | 243 | 223 | 216 | 229 | 233 | 182 | 267 | 155 |
| C1 +10 sessions | — | — | — | 243 | 223 | 216 | 229 | 233 | 182 | 267 | 155 |
| VOL matched to C2 | — | — | — | 57 | 2 | 43 | 37 | 149 | 66 | 182 | 62 |
| C2 −10 sessions | — | — | — | 80 | 99 | 53 | 85 | 88 | 85 | 52 | 56 |
| C2 +10 sessions | — | — | — | 80 | 99 | 53 | 85 | 88 | 85 | 52 | 56 |
| VOL matched to C3 | — | — | — | 23 | 2 | 25 | 22 | 74 | 26 | 91 | 36 |
| C3 −10 sessions | — | — | — | 50 | 33 | 34 | 41 | 65 | 37 | 11 | 28 |
| C3 +10 sessions | — | — | — | 50 | 33 | 34 | 41 | 65 | 37 | 11 | 28 |
| VOL matched to C4 | — | — | — | 2 | 0 | 3 | 2 | 9 | 4 | 9 | 6 |
| C4 −10 sessions | — | — | — | 4 | 2 | 1 | 9 | 6 | 7 | 0 | 6 |
| C4 +10 sessions | — | — | — | 4 | 2 | 1 | 9 | 6 | 7 | 0 | 6 |
| VOL matched to C5 | — | — | — | — | — | — | — | — | — | — | — |
| C5 −10 sessions | — | — | — | — | — | — | — | — | — | — | — |
| C5 +10 sessions | — | — | — | — | — | — | — | — | — | — | — |
| VOL matched to C6 | — | — | — | 28 | 1 | 29 | 17 | 100 | 40 | 105 | 45 |
| C6 −10 sessions | — | — | — | 55 | 43 | 34 | 45 | 82 | 39 | 32 | 35 |
| C6 +10 sessions | — | — | — | 55 | 43 | 34 | 45 | 82 | 39 | 32 | 35 |
| VOL matched to C7 | — | — | — | 4 | 1 | 5 | 8 | 20 | 7 | 25 | 11 |
| C7 −10 sessions | — | — | — | 2 | 5 | 10 | 8 | 21 | 24 | 9 | 2 |
| C7 +10 sessions | — | — | — | 2 | 5 | 10 | 8 | 21 | 24 | 9 | 2 |
| VOL matched to C8 | — | — | — | 16 | 2 | 16 | 14 | 62 | 17 | 73 | 32 |
| C8 −10 sessions | — | — | — | 56 | 20 | 18 | 2 | 0 | 5 | 90 | 41 |
| C8 +10 sessions | — | — | — | 56 | 20 | 18 | 2 | 0 | 5 | 90 | 41 |

### ALL

| Rule | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OLD absolute top | — | — | — | 346 | 330 | 307 | 386 | 453 | 314 | 322 | 247 |
| C1 REL | — | — | — | 343 | 310 | 310 | 322 | 338 | 283 | 396 | 226 |
| C2 BOTH | — | — | — | 112 | 131 | 80 | 112 | 118 | 120 | 67 | 76 |
| C3 WEEK | — | — | — | 72 | 43 | 48 | 56 | 97 | 50 | 17 | 41 |
| C4 TWO_WEEK | — | — | — | 5 | 3 | 2 | 10 | 11 | 12 | 0 | 6 |
| C5 BREADTH | — | — | — | 44 | 31 | 44 | 46 | 58 | 43 | 46 | 38 |
| C6 PARTNER | — | — | — | 75 | 65 | 55 | 64 | 94 | 45 | 42 | 50 |
| C7 VOL_RISE | — | — | — | 3 | 11 | 12 | 10 | 36 | 35 | 11 | 2 |
| C8 MACRO | — | — | — | 86 | 31 | 29 | 2 | 0 | 13 | 121 | 61 |
| VOL33 raw state | — | — | — | 5275 | 169 | 4564 | 5055 | 14196 | 5861 | 16111 | 5217 |
| VOL matched to OLD | — | — | — | 269 | 6 | 229 | 234 | 686 | 246 | 784 | 251 |
| OLD −10 sessions | — | — | — | 346 | 330 | 307 | 386 | 453 | 314 | 322 | 247 |
| OLD +10 sessions | — | — | — | 346 | 330 | 307 | 386 | 453 | 314 | 322 | 247 |
| VOL matched to C1 | — | — | — | 259 | 5 | 213 | 215 | 631 | 240 | 728 | 237 |
| C1 −10 sessions | — | — | — | 343 | 310 | 310 | 322 | 338 | 283 | 396 | 226 |
| C1 +10 sessions | — | — | — | 343 | 310 | 310 | 322 | 338 | 283 | 396 | 226 |
| VOL matched to C2 | — | — | — | 85 | 2 | 60 | 54 | 208 | 87 | 227 | 93 |
| C2 −10 sessions | — | — | — | 112 | 131 | 80 | 112 | 118 | 120 | 67 | 76 |
| C2 +10 sessions | — | — | — | 112 | 131 | 80 | 112 | 118 | 120 | 67 | 76 |
| VOL matched to C3 | — | — | — | 43 | 2 | 41 | 30 | 103 | 32 | 116 | 57 |
| C3 −10 sessions | — | — | — | 72 | 43 | 48 | 56 | 97 | 50 | 17 | 41 |
| C3 +10 sessions | — | — | — | 72 | 43 | 48 | 56 | 97 | 50 | 17 | 41 |
| VOL matched to C4 | — | — | — | 5 | 0 | 4 | 3 | 13 | 5 | 12 | 7 |
| C4 −10 sessions | — | — | — | 5 | 3 | 2 | 10 | 11 | 12 | 0 | 6 |
| C4 +10 sessions | — | — | — | 5 | 3 | 2 | 10 | 11 | 12 | 0 | 6 |
| VOL matched to C5 | — | — | — | 40 | 0 | 34 | 31 | 83 | 19 | 110 | 33 |
| C5 −10 sessions | — | — | — | 44 | 31 | 44 | 46 | 58 | 43 | 46 | 38 |
| C5 +10 sessions | — | — | — | 44 | 31 | 44 | 46 | 58 | 43 | 46 | 38 |
| VOL matched to C6 | — | — | — | 47 | 1 | 42 | 26 | 130 | 50 | 129 | 65 |
| C6 −10 sessions | — | — | — | 75 | 65 | 55 | 64 | 94 | 45 | 42 | 50 |
| C6 +10 sessions | — | — | — | 75 | 65 | 55 | 64 | 94 | 45 | 42 | 50 |
| VOL matched to C7 | — | — | — | 11 | 1 | 10 | 10 | 28 | 11 | 30 | 19 |
| C7 −10 sessions | — | — | — | 3 | 11 | 12 | 10 | 36 | 35 | 11 | 2 |
| C7 +10 sessions | — | — | — | 3 | 11 | 12 | 10 | 36 | 35 | 11 | 2 |
| VOL matched to C8 | — | — | — | 29 | 2 | 26 | 22 | 95 | 23 | 96 | 50 |
| C8 −10 sessions | — | — | — | 86 | 31 | 29 | 2 | 0 | 13 | 121 | 61 |
| C8 +10 sessions | — | — | — | 86 | 31 | 29 | 2 | 0 | 13 | 121 | 61 |

Source: [results/annual_counts.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/annual_counts.csv). The nine original sector ETFs, all FF12 and all FF49 series begin common scoring on 2016-01-08. XLRE starts on 2018-10-12; XLC starts on 2021-06-18. All stop on 2023-09-15. There are 137,118 eligible group-days. The input calendar has 2,768 sessions.


---

PRO-RUN SUCC-AVOID-1 part 5

## 2. Tables continued — continuous exit diagnostics

These are **averages of per-group full-path statistics**, not an investable portfolio and not annualized returns. Every scored warning holds through next close, then removes return exposure on t+2..t+63. A later warning extends the flat window. Each group's diagnostic runs over its common eligible interval. Cash return and transaction costs are zero. The FF12 continuous path uses the actual FF12 group index; the event member-DD tables above use its proxy children.

Event-count matching does not match time outside the group. For example, FF12 C2 is flat 29.35% of the time versus 22.50% for its matched VOL dates. Its mean full-path MDD reduction is 8.73pp versus 1.02pp, but its total-return gap versus holding is −23.40pp. The +10-session version reduces MDD by 9.54pp at a similar 29.18% flat share. These facts do not establish superior timing under the frozen gate. FF12 C6 reduces MDD by −0.09pp—effectively none—while giving up 36.77pp of total return.

### FF12

| Rule | Flat days % | Hold MDD % | Exit MDD % | MDD reduction pp | Total-return gap pp |
|---|---|---|---|---|---|
| OLD absolute top | 78.05 | 40.81 | 19.85 | 20.96 | -93.02 |
| C1 REL | 74.91 | 40.81 | 26.14 | 14.67 | -116.69 |
| C2 BOTH | 29.35 | 40.81 | 32.09 | 8.73 | -23.40 |
| C3 WEEK | 17.90 | 40.81 | 36.55 | 4.27 | -42.00 |
| C4 TWO_WEEK | 1.43 | 40.81 | 40.81 | -0.00 | -5.01 |
| C5 BREADTH | 65.47 | 40.81 | 27.26 | 13.55 | -92.16 |
| C6 PARTNER | 16.05 | 40.81 | 40.90 | -0.09 | -36.77 |
| C7 VOL_RISE | 4.74 | 40.81 | 37.88 | 2.93 | 2.77 |
| C8 MACRO | 11.56 | 40.81 | 40.76 | 0.05 | -10.11 |
| VOL33 raw state | 61.44 | 40.81 | 25.55 | 15.26 | -135.17 |
| VOL matched to OLD | 46.66 | 40.81 | 38.91 | 1.90 | -141.92 |
| OLD −10 sessions | 78.54 | 40.81 | 19.93 | 20.89 | -76.79 |
| OLD +10 sessions | 77.54 | 40.81 | 19.37 | 21.44 | -105.97 |
| VOL matched to C1 | 45.64 | 40.81 | 39.03 | 1.79 | -139.11 |
| C1 −10 sessions | 75.34 | 40.81 | 25.82 | 14.99 | -116.20 |
| C1 +10 sessions | 74.43 | 40.81 | 27.52 | 13.30 | -119.24 |
| VOL matched to C2 | 22.50 | 40.81 | 39.80 | 1.02 | -85.86 |
| C2 −10 sessions | 29.50 | 40.81 | 33.54 | 7.28 | -21.15 |
| C2 +10 sessions | 29.18 | 40.81 | 31.27 | 9.54 | -28.18 |
| VOL matched to C3 | 16.78 | 40.81 | 39.17 | 1.65 | -51.50 |
| C3 −10 sessions | 18.07 | 40.81 | 36.94 | 3.87 | -16.80 |
| C3 +10 sessions | 17.68 | 40.81 | 35.81 | 5.00 | -54.55 |
| VOL matched to C4 | 1.60 | 40.81 | 40.81 | -0.00 | -0.67 |
| C4 −10 sessions | 1.43 | 40.81 | 40.81 | -0.00 | -4.82 |
| C4 +10 sessions | 1.43 | 40.81 | 40.81 | -0.00 | -6.30 |
| VOL matched to C5 | 41.66 | 40.81 | 38.93 | 1.89 | -123.94 |
| C5 −10 sessions | 65.92 | 40.81 | 26.88 | 13.94 | -69.65 |
| C5 +10 sessions | 65.00 | 40.81 | 26.89 | 13.93 | -94.38 |
| VOL matched to C6 | 15.02 | 40.81 | 40.02 | 0.79 | -69.36 |
| C6 −10 sessions | 16.24 | 40.81 | 40.68 | 0.13 | -40.99 |
| C6 +10 sessions | 15.84 | 40.81 | 39.39 | 1.42 | -40.74 |
| VOL matched to C7 | 4.77 | 40.81 | 39.49 | 1.32 | 7.05 |
| C7 −10 sessions | 4.74 | 40.81 | 37.46 | 3.36 | 14.09 |
| C7 +10 sessions | 4.74 | 40.81 | 39.11 | 1.70 | -0.26 |
| VOL matched to C8 | 13.34 | 40.81 | 39.20 | 1.61 | -40.92 |
| C8 −10 sessions | 11.85 | 40.81 | 40.12 | 0.69 | -22.36 |
| C8 +10 sessions | 11.25 | 40.81 | 40.05 | 0.76 | -2.29 |

### ETF

| Rule | Flat days % | Hold MDD % | Exit MDD % | MDD reduction pp | Total-return gap pp |
|---|---|---|---|---|---|
| OLD absolute top | 78.02 | 39.72 | 15.19 | 24.53 | -67.70 |
| C1 REL | 75.71 | 39.72 | 24.68 | 15.05 | -94.90 |
| C2 BOTH | 27.00 | 39.72 | 32.71 | 7.01 | -12.43 |
| C3 WEEK | 14.61 | 39.72 | 33.12 | 6.60 | 3.60 |
| C4 TWO_WEEK | 2.25 | 39.72 | 37.62 | 2.11 | 6.44 |
| C6 PARTNER | 18.62 | 39.72 | 36.25 | 3.48 | -12.43 |
| C7 VOL_RISE | 5.92 | 39.72 | 36.61 | 3.11 | -0.58 |
| C8 MACRO | 13.40 | 39.72 | 39.44 | 0.28 | -18.62 |
| VOL33 raw state | 61.85 | 39.72 | 22.54 | 17.18 | -109.78 |
| VOL matched to OLD | 50.61 | 39.72 | 34.74 | 4.98 | -109.95 |
| OLD −10 sessions | 78.60 | 39.72 | 14.77 | 24.96 | -51.27 |
| OLD +10 sessions | 77.41 | 39.72 | 16.71 | 23.01 | -85.73 |
| VOL matched to C1 | 49.80 | 39.72 | 34.70 | 5.02 | -106.74 |
| C1 −10 sessions | 76.15 | 39.72 | 23.89 | 15.83 | -93.93 |
| C1 +10 sessions | 75.09 | 39.72 | 27.57 | 12.15 | -104.31 |
| VOL matched to C2 | 22.54 | 39.72 | 39.05 | 0.67 | -73.53 |
| C2 −10 sessions | 27.07 | 39.72 | 33.24 | 6.49 | -20.64 |
| C2 +10 sessions | 26.90 | 39.72 | 30.33 | 9.40 | -21.53 |
| VOL matched to C3 | 12.89 | 39.72 | 40.38 | -0.66 | -50.01 |
| C3 −10 sessions | 14.78 | 39.72 | 32.93 | 6.80 | 37.41 |
| C3 +10 sessions | 14.44 | 39.72 | 34.00 | 5.73 | -9.03 |
| VOL matched to C4 | 2.33 | 39.72 | 39.72 | 0.00 | -17.98 |
| C4 −10 sessions | 2.25 | 39.72 | 37.62 | 2.11 | 20.90 |
| C4 +10 sessions | 2.25 | 39.72 | 37.62 | 2.11 | 2.12 |
| VOL matched to C6 | 16.78 | 39.72 | 39.19 | 0.54 | -51.46 |
| C6 −10 sessions | 18.74 | 39.72 | 36.18 | 3.54 | -15.06 |
| C6 +10 sessions | 18.48 | 39.72 | 35.58 | 4.14 | -10.48 |
| VOL matched to C7 | 5.77 | 39.72 | 41.50 | -1.78 | -34.14 |
| C7 −10 sessions | 5.92 | 39.72 | 36.50 | 3.23 | 14.10 |
| C7 +10 sessions | 5.92 | 39.72 | 37.43 | 2.30 | -9.92 |
| VOL matched to C8 | 13.44 | 39.72 | 40.70 | -0.97 | -49.93 |
| C8 −10 sessions | 13.75 | 39.72 | 39.35 | 0.38 | -21.71 |
| C8 +10 sessions | 13.05 | 39.72 | 39.26 | 0.47 | -14.61 |

### FF49

| Rule | Flat days % | Hold MDD % | Exit MDD % | MDD reduction pp | Total-return gap pp |
|---|---|---|---|---|---|
| OLD absolute top | 77.86 | 46.13 | 25.49 | 20.64 | -113.82 |
| C1 REL | 74.62 | 46.13 | 30.53 | 15.60 | -130.70 |
| C2 BOTH | 33.27 | 46.13 | 40.28 | 5.85 | -57.52 |
| C3 WEEK | 17.63 | 46.13 | 41.70 | 4.43 | -29.66 |
| C4 TWO_WEEK | 2.08 | 46.13 | 45.99 | 0.14 | -3.47 |
| C6 PARTNER | 20.69 | 46.13 | 44.06 | 2.07 | -65.09 |
| C7 VOL_RISE | 4.95 | 46.13 | 44.41 | 1.72 | -11.37 |
| C8 MACRO | 12.14 | 46.13 | 45.66 | 0.48 | -3.66 |
| VOL33 raw state | 61.67 | 46.13 | 31.60 | 14.54 | -148.99 |
| VOL matched to OLD | 47.75 | 46.13 | 41.78 | 4.35 | -138.90 |
| OLD −10 sessions | 78.32 | 46.13 | 25.03 | 21.11 | -93.91 |
| OLD +10 sessions | 77.38 | 46.13 | 24.42 | 21.71 | -113.52 |
| VOL matched to C1 | 46.85 | 46.13 | 41.90 | 4.24 | -138.44 |
| C1 −10 sessions | 74.96 | 46.13 | 29.59 | 16.54 | -115.52 |
| C1 +10 sessions | 74.19 | 46.13 | 29.46 | 16.67 | -122.56 |
| VOL matched to C2 | 26.71 | 46.13 | 44.31 | 1.82 | -96.37 |
| C2 −10 sessions | 33.46 | 46.13 | 39.92 | 6.22 | -47.49 |
| C2 +10 sessions | 33.04 | 46.13 | 39.82 | 6.32 | -53.86 |
| VOL matched to C3 | 16.51 | 46.13 | 46.01 | 0.12 | -63.84 |
| C3 −10 sessions | 17.78 | 46.13 | 41.80 | 4.33 | -12.35 |
| C3 +10 sessions | 17.47 | 46.13 | 41.46 | 4.68 | -31.77 |
| VOL matched to C4 | 2.29 | 46.13 | 46.25 | -0.11 | -4.26 |
| C4 −10 sessions | 2.11 | 46.13 | 45.61 | 0.52 | -0.40 |
| C4 +10 sessions | 2.05 | 46.13 | 46.16 | -0.02 | -4.68 |
| VOL matched to C6 | 18.89 | 46.13 | 45.19 | 0.94 | -75.51 |
| C6 −10 sessions | 20.88 | 46.13 | 43.13 | 3.00 | -56.06 |
| C6 +10 sessions | 20.47 | 46.13 | 44.10 | 2.03 | -65.49 |
| VOL matched to C7 | 5.20 | 46.13 | 46.12 | 0.02 | -17.85 |
| C7 −10 sessions | 4.95 | 46.13 | 43.95 | 2.18 | 3.93 |
| C7 +10 sessions | 4.95 | 46.13 | 45.12 | 1.02 | -16.95 |
| VOL matched to C8 | 13.84 | 46.13 | 46.48 | -0.35 | -53.15 |
| C8 −10 sessions | 12.44 | 46.13 | 45.44 | 0.70 | -6.65 |
| C8 +10 sessions | 11.83 | 46.13 | 45.45 | 0.68 | 3.94 |

No confidence-qualified portfolio claim is made from this diagnostic. Underlying per-group numbers: [results/continuous_policy.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/continuous_policy.csv). The event return-gap contrasts, including bootstrap intervals, are retained in [results/effects.json](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/effects.json).


---

PRO-RUN SUCC-AVOID-1 part 6

## 3. Exact reproduction of the two finalists

The two finalists are **C2 BOTH** and **C6 PARTNER**, selected for detailed reporting, not accepted successors. The complete implementation is linked below; the following fixes their economic inputs, arithmetic, clocks and tie-breaks.

### Common arithmetic and clocks

```text
Allowed observation dates = 2013-01-02 through 2023-12-29, inclusive.
Calendar = actual SPY trading sessions in that interval, ordered ascending.
Group price P = compounded daily FF value-weighted total returns,
                or Yahoo adjusted close for the ETF where it exists.
Benchmark = SPY adjusted close. Relative price R = P / SPY.
Never fill a group price backward or invent ETF prehistory.

3-day bars = calendar indices [0,1,2], [3,4,5], ...
Only the last session of a complete block supplies a bar close.
No yearly reset. A flag is known at that session's close.

RSI14(X):
  changes = consecutive completed-bar price changes
  gain = max(change,0); loss = max(-change,0)
  first gain/loss averages = arithmetic means of first 14 changes
  later averages = (13*prior_average + current_value)/14
  RSI = 100 - 100/(1+average_gain/average_loss)
  zero loss and positive gain ->100
  zero gain and positive loss ->0; both zero ->50

EMA_n(x):
  seed = arithmetic mean of first n consecutive finite observations
  thereafter EMA += 2/(n+1) * (x-EMA)
  missing input resets initialization; no implicit zero

MACD = EMA14(RSI14) - EMA60(RSI14)
Signal = EMA5(MACD)
H = MACD - Signal

StochRaw = 100*(RSI14 - min(last14 RSI14))
                 /(max(last14 RSI14)-min(last14 RSI14))
zero range ->missing
K = arithmetic SMA3(StochRaw)
D = arithmetic SMA3(K)

TOP(X):
  previous K >80
  AND previous K >= previous D
  AND current K < current D
  AND current H < previous H

BOTTOM(X):
  previous K <20
  AND previous K <= previous D
  AND current K > current D
  AND current H > previous H

No refractory period, hysteresis, veto or tuning after a flag.
Each qualifying completed bar creates one event-day warning.
```

### C2 BOTH

```text
For every group g, on every completed 3-day bar ending session t:
  absolute_top = TOP(P[g])
  relative_top = TOP(R[g])
  C2[g,t] = absolute_top AND relative_top

Both crosses must occur on this exact bar.
No earlier cross is carried into the rule.
Equal K and D on the current bar is NOT a below-cross.
The flag does not authorize blocking or sizing a trade.
```

### C6 PARTNER

```text
Peer universe = other groups in the same cohort:
  FF12 peers for FF12; FF49 peers for FF49; listed ETF peers for ETFs.
Do not mix these overlapping classifications into one peer pool.

At close t:
  for each peer h with 126 complete paired daily relative log returns:
    corr[h] = Pearson correlation(
      log(R[g,s]/R[g,s-1]), log(R[h,s]/R[h,s-1]),
      s = t-126,...,t-1)
  Exclude g itself and any peer lacking the paired history.
  h* = peer with smallest corr
  Ties within 1e-12 -> lexicographically smallest group code.

  Require h*'s completed 3-day K, prior K, D, prior D, H and prior H
  to be finite over each of the last six sessions' available bar states.
  Preserve an explicit NaN on a completed source bar; it is not the
  previous finite reading. No initialized selected peer ->ineligible.

  partner_up = any BOTTOM(R[h*]) flag on sessions t-5,...,t inclusive
  C6[g,t] = TOP(P[g]) AND corr[h*] <= -0.25 AND partner_up

No recomputation with t's return in the correlation window.
No alternative peer is chosen because the minimum peer has no up-turn.
```

### Scoring mask, not an additional production rule

For the common comparison, every required feature for all eight non-breadth specifications must be ready: absolute/relative 3-day indicators; completed weekly and two-week states; 26-week/13-biweek close highs; the volatility lookbacks; the selected peer's history; and all lagged macro values. This is why the scored history begins in 2016. The raw signal tape retains earlier/later observable C2/C6 flags, marked unscored, rather than pretending the common mask is part of the signal's economic claim.

Weekly bars close on the final trading session of each calendar week. Two-week bars use pairs anchored to the calendar week beginning 2012-12-31; the first observed prices are in January 2013, and no prior price/return is used. An unfinished trailing higher bar is excluded. Completed higher states are carried between bar closes, preserving explicit missing source readings. Each group needs 73 subsequent sessions for scoring, ensuring the +10 shift still has a full 63-session outcome. OLD-relative-high and −10 outcomes also need complete prior windows.

VIX, Treasury and HY states use one prior-session lag, forward-filled at most five sessions. Dollar uses five prior sessions, also with at most five-session fill. Before 2020, its 63-session change is measured inside DTWEXB; from 2020, inside DTWEXBGS. No percentage change crosses the different index levels. These are conservative release-lag assumptions, not a complete vintage database.

### Labels, controls and uncertainty

```text
fake_N(g,t) = exists u in [t+1,t+N] such that
              R[g,u] > max(R[g,u-63],...,R[g,u-1])
Primary N=21; only sensitivities N=10,45.

prior_high_date = latest argmax of R[g,t-63],...,R[g,t-1]
lateness = t-prior_high_date

RV63 = sample SD(ddof=1) of last63 daily log absolute returns *sqrt(252)
VOL33[g,t] = RV63[g,t] >= linear 2/3 quantile of that group's
             finite discovery-block RV63 values

For target rule Q and each group g:
  k = number of eligible Q flags in g
  order eligible VOL33 dates by ascending hex SHA256 of exact UTF-8:
    "SUCC-AVOID-1|VOL|" + group_code + "|" + ISO_date
  choose first k dates; print them in calendar order
  if fewer than k are available, comparison is infeasible (none here)

Shifts = (g,t-10), (g,t+10) for each original (g,t).
Exact matched OLD cells = (group_code, integer_lateness).
Weights = candidate flag counts within cells containing both rules.
No extrapolation for REL-only cells lacking OLD support.

Bootstrap = 2,000 calendar-month multinomial resamples,
NumPy default_rng(seed=1101401), same draw across every group/rule.
Point interval = empirical 5th and 95th percentiles of finite draws.
Shift pairs keep their original-event month.
```

FF group codes in hashing include `FF12_` or `FF49_`; ETF group codes are the tickers. This matters for reproducing the exact matched VOL sample. There is no minimum-count tie chosen by a favorable outcome. The two final reporting candidates were ranked only under the pre-fixed FF12 count/group floor and matched-lateness fake difference described above.

### The FF12 proxy map

This is an explicit economic approximation. French's static SIC definitions show that FF49 portfolios cross FF12 boundaries; a true FF12-child reconstruction cannot be derived from aggregate FF49 returns alone. No constituent weights are inferred from the number of SIC codes. Average member DD means the mean of individual proxy-child maximum drawdowns; it is not the maximum drawdown of their combined basket.

| FF12 group | Proxy child count | FF49 proxy codes |
|---|---|---|
| NoDur | 8 | Agric Food Soda Beer Smoke Hshld Clths Txtls |
| Durbl | 2 | Toys Autos |
| Manuf | 10 | BldMt Steel FabPr Mach ElcEq Aero Ships Guns Paper Boxes |
| Enrgy | 2 | Coal Oil |
| Chems | 2 | Chems Rubbr |
| BusEq | 4 | Hardw Softw Chips LabEq |
| Telcm | 1 | Telcm |
| Utils | 1 | Util |
| Shops | 3 | Whlsl Rtail Meals |
| Hlth | 3 | Hlth MedEq Drugs |
| Money | 4 | Banks Insur RlEst Fin |
| Other | 9 | Fun Books Cnstr Gold Mines PerSv BusSv Trans Other |

Reproduce from [run_study.py](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/run_study.py), [acquire.py](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/acquire.py), and [verify_study.py](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/verify_study.py). Runtime: Python 3.12.14, NumPy 2.3.5, pandas 2.2.3. The current-vintage inputs are identified by [results/input_manifest.json](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/input_manifest.json); exact replay requires matching those hashes. No raw vendor or FRED series is published in the branch.


---

PRO-RUN SUCC-AVOID-1 part 7

## 3. Flag dates and groups — complete OLD and finalist tapes

All **5,084 observable flags** for OLD (3,474), C2 (1,029) and C6 (581) are printed below. **4,011** are in the common scored panel (2,705 / 816 / 490). A trailing `*` marks an unscored flag: warm-up/feature availability or insufficient forward support. Years and MM-DD tokens together give full dates. The CSV gives the precise unscored reason. These dates are signals, not trade instructions.

Full all-candidate tape: [results/flags_all_observable.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/flags_all_observable.csv). Scored OLD/C2/C6 events with labels and outcomes: [results/old_and_finalist_flags.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/old_and_finalist_flags.csv).

### OLD absolute top

```text
FF12_BusEq | 2013: 12-12*; 2014: 01-06*,03-17*,06-24*,07-29*,09-15*; 2015: 03-09*,05-07*,11-09*,12-09*; 2016: 03-24,04-07,04-25,06-15,08-02,08-10,08-18; 2017: 02-28,03-21,05-19,11-13,11-30; 2018: 02-06,06-20,07-30; 2019: 02-07,03-06,03-27,04-26,11-22; 2020: 01-27,05-13,06-12,07-14,09-08; 2021: 01-04,02-22,04-30,07-19,08-17,09-08,11-29; 2022: 04-07,08-09,11-29; 2023: 04-05,04-24,05-23,06-09,06-23,12-05*
FF12_Chems | 2014: 03-20*,05-15*,06-16*,09-10*,10-01*,12-01*; 2015: 03-09*,11-09*,12-14*; 2016: 03-16,04-28,06-15,09-09,12-16; 2017: 02-06,02-28,07-28,09-22,10-18; 2018: 01-10,06-20,08-10,09-11,09-27; 2019: 03-01,03-22,04-23,08-05,12-30; 2020: 05-13,06-12,08-17,09-08,12-07,12-23; 2021: 04-09,04-30,05-13,08-20,09-08,11-18; 2022: 04-18,08-22; 2023: 04-27,07-17,08-07,12-05*
FF12_Durbl | 2014: 01-28*,03-12*,06-16*,07-08*,09-10*,12-01*; 2015: 01-06*,02-24*,03-25*,09-28*,11-12*,12-04*; 2016: 03-24,05-03,08-02,08-26,12-16; 2017: 06-20,07-07,10-13; 2018: 01-19,01-29,05-30,06-20,11-21,12-06; 2019: 03-01,04-26,07-10,07-26; 2020: 01-03,01-27,05-13,06-12,07-27,09-08,12-23; 2021: 01-21,05-05,07-09,08-17,09-21,11-10; 2022: 04-07,08-09; 2023: 02-13,03-02,06-23,07-20
FF12_Enrgy | 2014: 03-17*,04-07*,05-02*,06-24*,12-01*; 2015: 02-19*,05-07*,09-23*,10-19*,11-12*; 2016: 03-24,05-03,10-18,12-16; 2017: 08-07,10-10,11-16; 2018: 01-10,01-29,05-03,05-24,10-10; 2019: 02-07,03-06,04-26,09-25,11-19; 2020: 06-12,08-20,12-02,12-15; 2021: 01-21,03-15,06-17,10-28; 2022: 02-10,03-14,04-04,08-30,11-10; 2023: 04-24,07-17,08-15,09-19*
FF12_Hlth | 2014: 01-28*,03-07*,06-16*,07-08*,09-15*,12-12*; 2015: 03-09*,03-25*,06-29*,07-24*,11-12*,12-04*; 2016: 04-28,08-05,12-30; 2017: 01-19,03-08,06-28,09-27; 2018: 02-01,06-25,07-20,08-15,09-06,10-05; 2019: 06-26,07-15,09-25,12-03,12-30; 2020: 05-08,05-21,07-27,11-23,12-23; 2021: 01-29,04-30,07-14,08-12; 2022: 01-06,04-12,08-01,08-17,11-29; 2023: 04-27,05-15,08-02,12-18*
FF12_Manuf | 2014: 01-09*,03-17*,06-16*,09-15*,11-20*,12-01*; 2015: 02-27*,05-29*,11-09*,12-04*; 2016: 03-24,04-28,08-26,11-30,12-16; 2017: 03-08,06-12,07-25,10-31; 2018: 01-24,06-04,06-15,08-10,09-27; 2019: 03-06,07-10,07-31,09-25,11-22; 2020: 01-22,06-12,08-20,09-08,10-28,12-02,12-18; 2021: 01-21,03-23,08-20,11-18; 2022: 04-04,06-13,08-09,11-23,12-07; 2023: 02-13,06-23,07-07,08-02
FF12_Money | 2014: 01-14*,06-16*,07-08*,09-15*,09-23*,12-01*,12-12*; 2015: 03-25*,05-26*,06-29*,11-12*,12-09*; 2016: 03-24,04-28,06-10,09-06,11-30,12-13; 2017: 06-23,07-17,07-28,10-13,11-08,12-27; 2018: 02-01,05-30,06-20,08-10,09-06; 2019: 02-07,03-06,05-09,07-31,11-14,12-03; 2020: 01-03,01-27,06-12,08-20,09-08,10-20,12-10; 2021: 01-15,03-23,08-20,10-28,11-18; 2022: 01-20,06-13,08-22,12-07; 2023: 02-16,06-23,07-28
FF12_NoDur | 2014: 04-07*,05-15*,06-11*,09-23*,12-04*; 2015: 03-09*,08-14*,10-30*; 2016: 03-21,04-12,07-25,12-30; 2017: 01-10,02-01,03-08,03-29,06-12,10-26,12-21; 2018: 02-01,06-28,07-30,11-16; 2019: 02-21,04-04,05-09,07-31,12-03; 2020: 01-03,01-27,05-13,05-21,06-12,08-04,08-20,09-08,12-23; 2021: 04-30,05-13,11-18; 2022: 01-20,04-26,08-09,08-22,11-29; 2023: 05-10,08-02,12-08*
FF12_Other | 2014: 03-17*,06-11*,09-10*,12-01*; 2015: 03-04*,12-04*; 2016: 03-24,07-25,08-26,11-30,12-21; 2017: 06-20,07-28,10-10; 2018: 01-29,06-20,09-24; 2019: 02-07,03-01,05-01,07-18,11-14,12-03; 2020: 01-03,01-22,06-12,08-17,09-08; 2021: 01-04,01-15,04-22,05-13,09-13,11-10; 2022: 04-04,08-09,11-23,12-07; 2023: 02-08,05-02,05-23,06-23,08-02,12-05*
FF12_Shops | 2014: 03-25*,06-16*,07-16*,12-09*; 2015: 01-06*,03-25*,08-11*,11-09*,12-09*; 2016: 04-28,07-28,08-23,11-30,12-21; 2017: 03-03,05-16,06-07,09-22,10-13; 2018: 02-01,06-25,09-06; 2019: 02-07,02-21,05-01,07-18,11-22; 2020: 01-27,02-21,05-08,06-04,09-08; 2021: 01-04,01-29,04-22,05-05,07-19,11-23; 2022: 07-27,08-22,11-29,12-07; 2023: 02-08,05-02,05-23,07-07,07-28,11-30*
FF12_Telcm | 2014: 01-09*,03-17*,05-20*,06-11*,07-24*,12-04*; 2015: 03-12*,03-25*,05-07*,11-04*,12-01*; 2016: 03-24,04-07,05-03,07-20,12-30; 2017: 08-10; 2018: 01-02,02-06,06-25,07-17,08-23,08-31,09-27; 2019: 03-06,04-23,05-31,07-23; 2020: 01-27,05-13,06-12,08-20,09-08,12-10; 2021: 03-18; 2022: 01-14,02-24,04-18,06-13,08-01,08-09,08-22,11-07,12-07; 2023: 02-08,04-24,07-17,08-07,08-18,12-05*,12-21*
FF12_Utils | 2014: 02-05*,02-27*,05-02*,09-15*,11-12*; 2015: 05-04*,08-24*,10-27*; 2016: 01-20,02-10,04-07,07-07,07-28,12-30; 2017: 01-10,06-12,08-31,11-21; 2018: 03-26,04-12,05-08,07-09,07-25,08-23,12-19; 2019: 03-19,06-26,10-03; 2020: 01-08,02-04,02-26,05-13,06-12,08-17,11-23; 2021: 01-29,04-27,08-25,09-13,11-18,12-23; 2022: 01-11,04-12,08-22,12-15; 2023: 01-18,04-14,07-28,12-18*
FF49_Aero | 2014: 01-14*,06-16*,09-05*,09-23*,12-01*; 2015: 02-27*,11-09*,12-04*; 2016: 03-24,08-02,08-23,11-21,12-16; 2017: 03-08,05-16,06-07,08-10,10-26; 2018: 02-06,06-15,08-02; 2019: 02-21,03-06,07-10,07-26,09-25,12-03; 2020: 02-21,05-13,06-12,09-08,10-28,12-10; 2021: 03-18,06-14,10-20,11-18; 2022: 01-20,02-18,04-04,08-22,11-15,12-07; 2023: 01-18,06-23,07-17,12-18*
FF49_Agric | 2013: 12-09*; 2014: 01-09*,03-25*,06-11*,07-11*; 2015: 02-27*,05-29*,10-27*,11-12*,12-09*; 2016: 01-06*,03-24,05-06,06-07,12-21; 2017: 02-01,03-08,10-10,10-26; 2018: 03-16,04-25,06-25; 2019: 01-25,02-07,02-26,06-26,07-05,08-16; 2020: 01-03,01-22,02-21,05-13,06-12,09-08,10-20,12-02,12-29; 2021: 01-21,08-20,11-23; 2022: 02-24,03-30; 2023: 04-27,07-12,08-07,09-27*
FF49_Autos | 2014: 01-28*,03-12*,06-16*,07-08*; 2015: 01-06*,02-24*,03-25*,09-28*,10-27*,11-12*,12-04*; 2016: 03-24,05-03,08-02,08-26,12-16; 2017: 02-01,02-23,06-20,07-07,10-13; 2018: 05-30,06-20,12-06; 2019: 02-12,03-01,04-26,07-26,11-14; 2020: 01-03,01-27,05-13,06-12,07-27,09-08,12-23; 2021: 01-21,04-30,07-09,08-17,09-21,11-10; 2022: 04-07,08-09; 2023: 02-13,03-02,06-23,07-20
FF49_Banks | 2014: 01-14*,06-16*,07-08*,09-23*,11-20*,12-01*,12-12*; 2015: 03-25*,05-26*,06-19*,11-12*,12-09*; 2016: 03-24,05-03,06-10,09-06,11-30,12-13; 2017: 06-23,07-17,07-28,10-13,11-08,12-27; 2018: 02-06,05-30,09-06; 2019: 02-04,03-06,03-22,05-09,07-31,11-14,12-03; 2020: 01-08,01-27,06-12,08-20,09-08,10-20,12-10; 2021: 01-15,03-23,06-09,08-20,10-28; 2022: 01-20,06-13,08-04,08-22,11-18,12-07; 2023: 02-08,06-23,07-28
FF49_Beer | 2014: 01-31*,04-10*,05-02*,05-15*,06-16*,11-20*; 2015: 03-04*,07-24*,10-30*; 2016: 04-15,05-16,07-28; 2017: 03-08,04-03,04-28,06-07; 2018: 01-02,06-28,07-30,11-21; 2019: 02-21,03-14,05-01,09-17; 2020: 01-08,01-27,02-26,05-21,08-04,09-08,12-10; 2021: 04-09,04-30,06-09,10-25,11-15,11-29,12-23; 2022: 01-11,08-09,08-25,12-07; 2023: 05-10,08-02,12-08*
FF49_BldMt | 2014: 01-06*,03-12*,06-24*,09-15*,11-17*,12-01*; 2015: 02-27*,04-29*,05-29*,08-24*,11-12*,12-04*; 2016: 03-24,04-25,08-02,08-18,11-30,12-16; 2017: 07-25,10-05,10-31,12-13; 2018: 01-16,01-29,06-15,08-15,09-24; 2019: 02-07,03-01,04-26,07-15,08-05,09-25,11-11; 2020: 01-27,05-13,06-12,08-20,09-08,12-02,12-29; 2021: 01-26,03-23,08-20,09-08; 2022: 06-13,11-29; 2023: 02-08,05-23,07-07,07-25,08-10,12-27*
FF49_Books | 2014: 01-09*,03-25*,07-08*,12-12*; 2015: 01-06*,02-27*,11-09*,12-04*; 2016: 05-03,07-28,09-09; 2017: 01-19,02-28,07-12,08-02,10-13,12-21; 2018: 02-01,06-25,10-10,10-26,11-16; 2019: 03-06,07-18,08-05,11-11; 2020: 01-03,05-13,06-01,06-12,08-20,12-15; 2021: 01-29,02-25,03-23,10-28; 2022: 04-04,08-04,08-17,11-18,12-07; 2023: 02-13,06-20,07-20,08-23
FF49_Boxes | 2014: 01-09*,03-12*,06-11*,07-08*,09-18*,11-20*,12-09*; 2015: 01-06*,02-27*,08-24*,10-27*,12-09*; 2016: 03-30,04-25,08-23,09-09,12-21; 2017: 02-09,06-12,07-20,10-13,11-03; 2018: 01-29,04-30,08-10,09-24,12-11; 2019: 03-01,03-22,04-09,06-26,07-15,11-06; 2020: 01-30,02-26,05-08,06-12,08-04,08-20,09-08,10-28,12-02; 2021: 05-13,09-08; 2022: 02-24,03-30,08-04,11-29; 2023: 02-08,06-23,07-17,08-02,12-21*
FF49_BusSv | 2014: 01-06*,06-16*,07-11*,07-29*,09-10*,11-20*; 2015: 03-04*,03-25*,11-12*,12-04*; 2016: 03-16,03-24,04-07,04-25,06-10,08-02,12-05,12-27; 2017: 01-27,02-28,05-19,06-12,08-02,10-18,10-31,12-05; 2018: 02-01,06-25,09-19; 2019: 02-07,03-06,04-17,06-26,07-23,11-06,12-03; 2020: 01-27,02-21,05-13,06-12,07-14,08-12,09-08,12-10,12-23; 2021: 02-25,04-30,07-19; 2022: 01-11,04-07,08-09,11-23,12-07; 2023: 02-08,05-02,05-26,06-23,07-28,12-21*
FF49_Chems | 2014: 01-09*,03-17*,06-16*,09-10*,12-01*; 2015: 02-27*,11-09*,12-04*; 2016: 05-03,12-13; 2017: 03-08,07-28,10-10,11-08; 2018: 01-16,05-30,06-20,08-10,09-11; 2019: 02-04,03-01,04-23,07-10,08-05,09-30; 2020: 05-13,06-12,07-30,08-20,09-08,12-07,12-29; 2021: 01-21,04-09,05-13,06-09,11-18; 2022: 04-07,04-26,08-22,11-18,12-07; 2023: 02-08,06-23,07-17,08-02,12-05*
FF49_Chips | 2013: 12-12*; 2014: 04-07*,05-15*,06-24*,07-21*,12-01*; 2015: 02-27*,06-03*,09-28*,10-27*,11-09*; 2016: 03-24,04-07,06-15,08-23,10-13,12-30; 2017: 03-08,08-18,10-23,11-13; 2018: 03-21,06-12,09-06; 2019: 03-06,03-27,04-26,07-31,11-14; 2020: 05-13,07-27,09-08; 2021: 01-04,01-29,07-19,09-13,12-02,12-20; 2022: 04-07,08-09,11-07,11-29; 2023: 06-23,11-27*,12-21*
FF49_Clths | 2013: 12-09*; 2014: 03-25*,06-16*,07-11*,09-10*,12-01*; 2015: 04-02*,04-16*,07-16*,07-24*,08-14*; 2016: 03-11,03-24,08-31,11-30,12-16; 2017: 03-03,03-24,06-20,07-12,08-10,11-03,12-27; 2018: 01-16,02-01,06-20; 2019: 02-21,05-01,07-18,10-08,10-24; 2020: 01-08,01-27,05-13,06-12,09-08,10-20,12-10; 2021: 01-15,07-14,08-17,11-10; 2022: 04-29,08-09,08-22,11-29,12-07; 2023: 01-26,04-27,10-26*,12-27*
FF49_Cnstr | 2014: 01-09*,03-12*,06-19*,07-11*,09-10*,12-01*; 2015: 02-27*,04-13*,07-02*,12-04*; 2016: 03-24,04-25,06-10,08-02,11-30,12-16; 2017: 03-21,07-20,10-13,11-03,11-27,12-05; 2018: 06-15; 2019: 01-22,03-01,04-26,10-03,10-29; 2020: 02-04,02-26,05-13,06-01,08-20,10-23; 2021: 01-29,02-22,04-19,05-13,08-17,09-08,11-29,12-20; 2022: 06-13,08-04,11-23,12-20; 2023: 02-08,05-23,07-07
FF49_Coal | 2014: 03-12*,05-07*,11-20*; 2015: 02-27*,05-15*,09-15*,10-22*; 2016: 01-06*,02-10,03-16,04-25,05-03,10-18,12-13; 2017: 04-17,07-28,09-11,09-19,10-10; 2018: 01-05,06-15,09-24; 2019: 02-04,10-29; 2020: 01-16,04-27,06-04,06-12,08-25,09-24,12-18; 2021: 01-21,05-21,06-14,08-20,09-16; 2022: 01-20,02-24,03-14,08-30,11-10; 2023: 07-17,08-15,12-13*
FF49_Drugs | 2014: 01-28*,03-07*,06-16*,07-08*,09-15*,12-12*; 2015: 03-09*,03-25*,06-29*,07-24*,11-09*,12-04*; 2016: 04-28,08-05,11-30,12-30; 2017: 01-19,03-08,06-28,09-22,10-18; 2018: 02-01,06-25,07-20,08-15,09-06,10-05; 2019: 03-06,06-26,09-25,11-06,12-03,12-30; 2020: 05-05,05-21,07-27,11-23,12-23; 2021: 01-29,05-05,06-01,06-22,07-14,08-12; 2022: 01-03,04-12,07-14,12-07; 2023: 04-19,05-18,08-02,08-28,12-18*
FF49_ElcEq | 2014: 01-23*,07-08*,09-15*,11-17*,12-01*; 2015: 02-27*,04-24*,05-29*,11-09*,12-09*; 2016: 01-06*,03-24,04-28,08-26,12-13; 2017: 02-23,07-28,10-10,11-03; 2018: 01-10,06-20,08-10,09-27; 2019: 02-07,03-01,04-26,07-31,09-25,12-24; 2020: 01-22,05-13,06-12,07-30,08-20,09-08,12-02; 2021: 07-06,11-10; 2022: 04-04,06-16,08-09,11-29; 2023: 02-08,06-23,07-17,07-25
FF49_FabPr | 2014: 03-12*,06-24*,11-17*; 2015: 03-04*,04-13*,07-08*,11-20*,12-04*; 2016: 03-08,04-04,04-28,05-06,08-31,11-30,12-16; 2017: 01-05,02-17,05-19,08-07,09-06,10-31; 2018: 02-01,04-25,08-15; 2019: 02-07,02-26,03-22,08-05,09-25; 2020: 01-08,05-13,06-12,08-17,10-28,12-02,12-18; 2021: 08-17,09-08; 2022: 03-30,08-17,11-10; 2023: 02-13,03-10,07-07,07-25
FF49_Fin | 2014: 01-09*,07-08*,08-01*,09-10*,09-23*,12-12*; 2015: 03-25*,06-16*,11-12*,12-09*; 2016: 03-24,04-07,04-28,06-07,09-06,12-13; 2017: 06-23,07-28,10-13,10-31,12-18; 2018: 01-29,05-30,06-20; 2019: 01-30,03-06,05-01,05-09,07-31,12-03; 2020: 01-27,05-13,06-12,09-08,10-28,12-10; 2021: 01-15,03-23,06-09,08-20,11-10; 2022: 04-04,06-13,11-18; 2023: 02-16,06-23,07-28
FF49_Food | 2013: 12-12*; 2014: 03-20*,04-07*,05-20*,06-11*,09-23*,11-25*; 2015: 04-13*,05-26*,10-30*; 2016: 01-06*,03-21,04-12,05-19,07-20,12-30; 2017: 02-01,02-28,06-15,08-28,12-08; 2018: 01-02,06-28,07-20; 2019: 02-26,05-06,05-22,07-31,09-25,12-16; 2020: 01-03,05-05,05-21,06-12,08-20,09-08; 2021: 01-04,05-21,06-09,11-18; 2022: 01-20,04-26,08-22,11-10,12-07; 2023: 04-14,05-10,08-07,11-30*,12-18*
FF49_Fun | 2014: 01-06*,01-28*,03-12*,07-08*,12-01*; 2015: 02-24*,04-29*,07-24*,11-12*,12-09*; 2016: 03-30,04-20,08-23,09-27,10-13,11-03; 2017: 02-01,04-11,05-08,10-02,10-18,11-16,12-05,12-27; 2018: 06-07,06-25,10-05; 2019: 01-22,02-15,03-01,04-17,05-06,07-18,11-14,12-03; 2020: 01-03,01-22,02-26,05-13,06-12,07-22,09-08,12-10; 2021: 07-09,09-13,11-05; 2022: 04-07,07-14,08-09,11-02,11-23,12-15; 2023: 02-08,05-23,06-23,11-30*
FF49_Gold | 2014: 01-31*,03-20*,07-08*,08-22*,12-12*; 2015: 01-14*,02-05*,03-04*,05-26*,10-19*,11-04*; 2016: 03-08,03-24,07-20; 2017: 01-19,02-14,06-12,08-07,09-11; 2018: 01-19,04-25,10-26,11-30,12-19; 2019: 01-16,04-17,07-01,07-23; 2020: 01-03,05-21,11-18; 2021: 01-15,04-30,05-26,10-28,11-23; 2022: 01-06,01-28,03-14,04-12,04-21,09-26,10-12,12-07; 2023: 01-18,02-03,04-14,10-26*,12-08*
FF49_Guns | 2014: 08-06*,09-02*,09-23*; 2015: 03-04*,06-29*,07-24*,08-19*,11-04*,12-01*; 2016: 03-11,03-24,04-15,05-19,07-25,08-10,12-08; 2017: 03-16,06-07,08-18; 2018: 01-24,02-06,07-30,09-11,10-10; 2019: 02-21,05-17,06-18,07-10,12-03; 2020: 02-04,05-13,06-12,09-08,12-02; 2021: 04-22,10-28; 2022: 02-02,03-14,08-22,11-15,12-07; 2023: 03-10,04-24,07-20,10-26*,11-08*,12-18*
FF49_Hardw | 2014: 01-23*,04-07*,06-24*,08-01*,09-15*,12-09*,12-31*; 2015: 05-12*,06-08*,10-22*; 2016: 04-04,06-10,08-02,09-09,10-10; 2017: 02-28,05-11,07-28,10-18,12-05; 2018: 01-02,02-01,09-06; 2019: 03-01,03-22,04-26,07-23,11-14; 2020: 01-22,05-13,06-12,08-07,10-23,12-23; 2021: 01-21,02-22,08-17,09-08,11-18; 2022: 01-03,04-04,08-30,11-29; 2023: 02-22,04-14,06-20,07-28
FF49_Hlth | 2014: 01-23*,03-07*,06-11*,08-11*,09-05*,12-17*; 2015: 01-06*,04-02*,04-29*,12-04*; 2016: 05-03,10-13,10-26,12-30; 2017: 01-19,03-08,07-07; 2018: 01-05,02-01,06-25,09-06; 2019: 02-21,05-14,07-10,07-31,12-03; 2020: 01-03,01-27,02-26,06-04,08-07,08-28,10-28,12-15; 2021: 01-29,07-14; 2022: 01-06,04-04,08-17,11-18,12-07; 2023: 02-22,05-02,07-07,07-28,12-18*
FF49_Hshld | 2014: 03-20*,05-02*,10-01*,11-17*,12-12*; 2015: 07-24*,10-30*,12-09*,12-31*; 2016: 02-29,06-28,07-28,08-23; 2017: 01-10,02-01,03-03,03-24,06-23,09-22; 2018: 01-02,06-20,07-25,08-10,08-31,09-27,11-21,12-11; 2019: 03-01,04-23,07-23,12-30; 2020: 01-27,02-18,05-13,06-12,08-17,09-08; 2021: 04-14,04-27,05-18,08-09,08-25,12-23; 2022: 01-11,04-26,07-14,08-09,08-22,11-29,12-15; 2023: 01-12,08-10,12-05*,12-27*
FF49_Insur | 2014: 06-16*,07-08*,07-29*,09-15*,12-01*,12-12*; 2015: 03-25*,06-29*,11-09*,12-09*; 2016: 03-24,04-07,04-28,06-10,08-26,12-16,12-30; 2017: 06-23,07-17,08-10,11-08,12-05; 2018: 02-01,05-03,05-30,06-20,08-23,09-11; 2019: 02-21,05-28,06-26,07-23,12-03; 2020: 05-08,06-12,08-20,10-20,11-23,12-15; 2021: 03-23,05-13,08-30,11-02; 2022: 01-06,04-04,04-26,07-14,08-22; 2023: 04-24,10-23*,12-08*
FF49_LabEq | 2014: 01-06*,01-28*,03-12*,06-16*,09-15*,12-01*; 2015: 03-04*,12-04*; 2016: 03-24,04-07,06-10,08-18,10-10,12-21; 2017: 01-24,02-28,05-19,06-12,09-22,10-18,10-31; 2018: 02-01,06-20,08-10,09-11,09-27,10-05; 2019: 03-06,04-17,07-10,09-30,12-03,12-30; 2020: 01-27,05-08,05-21,06-12,08-07,08-20,09-08,11-18; 2021: 01-26,04-30,07-14,08-20,09-13; 2022: 04-04,04-12,06-13,08-09,12-15; 2023: 01-26,04-27,06-28,08-02
FF49_Mach | 2014: 01-06*,03-17*,04-07*,06-24*,07-08*,11-20*; 2015: 03-04*,05-07*,05-26*,11-09*,12-09*; 2016: 03-24,05-03,06-15,08-26; 2017: 06-07,07-28,10-31; 2018: 01-24,06-04,08-15,10-02; 2019: 02-07,03-01,04-26,07-10,07-31,09-30,11-14; 2020: 01-22,06-01,06-12,08-17,10-28,12-02,12-23; 2021: 01-21,03-23,08-20,11-23; 2022: 04-04,06-13,08-09,11-18; 2023: 02-08,06-23,07-07,08-07
FF49_Meals | 2014: 03-17*,06-16*,07-08*,12-09*; 2015: 03-09*,08-11*,11-04*; 2016: 03-24,04-12,04-25,07-28,11-30,12-21; 2017: 04-28,06-07,10-23,11-13,12-21; 2018: 01-29,05-21,06-20,09-14,10-02,11-21; 2019: 03-06,04-17,05-09,07-23; 2020: 01-27,06-12,09-08,12-02,12-23; 2021: 03-23,04-27,08-09; 2022: 04-12,06-13,08-09,11-29; 2023: 02-08,02-22,05-05,07-28,11-30*,12-21*
FF49_MedEq | 2014: 01-28*,06-16*,07-08*,09-15*,12-12*; 2015: 08-24*,11-12*,12-04*; 2016: 03-16,05-03,05-19,07-25,08-18; 2017: 01-19,03-08,04-06,05-08,06-12,12-05; 2018: 02-01,06-20,10-05; 2019: 02-07,02-26,06-26,07-18,07-31,11-11,12-03,12-30; 2020: 01-27,05-13,06-04,06-12,08-04,09-08; 2021: 01-04,01-12,01-29,02-22,04-30,07-14,08-09,09-13; 2022: 01-06,04-12,11-29; 2023: 04-27,07-07,07-28,12-05*
FF49_Mines | 2014: 01-09*,04-15*,05-07*,12-01*; 2015: 02-24*,05-12*,09-23*,10-19*; 2016: 03-24,05-03,11-03; 2017: 02-06,10-31,11-16; 2018: 01-10,02-01,10-05; 2019: 01-25,02-12,03-01,03-22,04-23,07-10,09-30,11-14,12-03; 2020: 01-03,05-13,06-12,07-30,08-25,09-08,12-10; 2021: 01-15,05-21,08-17,10-28,11-23; 2022: 01-20,03-14,04-07,08-22,11-18,12-07; 2023: 01-26,02-03,07-07,08-02
FF49_Oil | 2014: 03-17*,04-07*,05-02*,06-24*,12-01*; 2015: 01-06*,02-19*,05-07*,09-23*,10-19*,11-12*; 2016: 03-24,05-03,10-18,12-16; 2017: 08-07,10-05,11-16; 2018: 01-10,01-29,05-03,05-24,10-10; 2019: 02-07,03-06,04-26,09-25,11-19; 2020: 06-12,08-20,12-02,12-15; 2021: 01-21,03-15,06-17,10-28; 2022: 02-10,03-14,04-04,08-30,11-10; 2023: 04-24,07-17,08-15,09-19*
FF49_Other | 2014: 03-20*,04-07*,05-07*,06-16*,09-10*,12-01*; 2015: 10-30*,12-01*; 2016: 03-16,04-04,07-25,12-21; 2017: 03-13,06-23,10-10,12-27; 2018: 01-19,05-24,09-24; 2019: 02-07,03-06,03-22,05-06,07-15,09-25,11-14; 2020: 01-22,05-08,06-12,07-30,08-17,09-08,12-02; 2021: 01-15,03-15,05-13,08-20,11-15; 2022: 01-20,04-04,08-22,11-29; 2023: 04-27,05-23,06-23,07-28,12-05*,12-27*
FF49_Paper | 2014: 06-11*,12-01*; 2015: 03-04*,11-09*,12-04*; 2016: 03-24,04-25,09-09,12-27; 2017: 02-06,03-08,06-28,10-23,12-08; 2018: 02-01,06-20,08-10,09-14,12-14; 2019: 03-01,04-17,04-26,07-10,07-31,09-25,10-03,11-11,12-03,12-11; 2020: 01-03,01-22,05-08,06-12,08-25,09-08,10-23,12-02,12-29; 2021: 04-27,11-18; 2022: 01-20,04-12,05-12,08-17,11-23; 2023: 01-18,04-27,06-28,07-07,08-02
FF49_PerSv | 2014: 01-28*,03-12*,06-24*,09-02*,12-01*; 2015: 06-16*,06-29*,08-24*,10-22*; 2016: 03-16,03-24,06-10,06-28,07-28,11-30,12-21,12-30; 2017: 03-21,05-16,07-28,12-21; 2018: 01-29,06-04,08-31,11-21; 2019: 05-01,06-26,07-31,12-30; 2020: 01-22,05-13,06-12,08-20,09-08,10-28,12-02,12-23; 2021: 02-25,03-18,07-14; 2022: 04-07,04-26,08-04,08-22,11-29,12-07; 2023: 02-13,05-23,06-23,07-28,11-30*
FF49_RlEst | 2013: 12-12*; 2014: 01-09*,03-12*,06-16*,07-08*,09-05*,11-20*,12-09*; 2015: 07-24*,11-09*; 2016: 03-24,04-25,07-28,08-26,11-30,12-16; 2017: 02-28,05-11,10-23,12-18; 2018: 02-06,11-21,12-11; 2019: 02-07,02-26,07-18,08-05,11-22,12-11; 2020: 01-03,05-13,06-12,09-08,10-20,12-29; 2021: 02-25,06-14,08-17,11-02; 2022: 06-13,08-04,08-17,12-07; 2023: 02-08,06-20,07-28
FF49_Rtail | 2014: 03-25*,06-16*,07-16*,07-29*,12-09*; 2015: 01-06*,03-25*,08-06*,11-09*,12-09*; 2016: 04-04,04-28,06-15,08-02,08-18,12-21; 2017: 03-03,05-11,09-22,10-18,12-05; 2018: 01-16,01-29,06-25,09-06; 2019: 02-07,02-26,05-01,07-18,10-29,11-19; 2020: 01-27,02-21,05-08,06-12,07-17,09-08; 2021: 01-04,01-29,04-22,05-05,07-19,11-23; 2022: 07-27,08-22; 2023: 02-08,05-02,05-23,07-07,08-02,11-30*
FF49_Rubbr | 2014: 01-06*,06-24*,07-11*,09-15*,11-17*,12-12*; 2015: 01-06*,02-27*,10-27*,11-12*,12-04*,12-22*,12-31*; 2016: 04-07,04-25,09-09,12-05,12-21; 2017: 05-19,06-15,10-18; 2018: 04-30,06-25,08-15,09-24; 2019: 02-04,02-26,03-22,04-17,07-15,07-31,11-06; 2020: 01-03,01-27,05-13,06-12,08-20,12-29; 2021: 05-13,06-04,09-08; 2022: 04-04,07-14,08-09,11-29,12-07; 2023: 02-08,04-27,07-07,07-28,08-18,12-05*
FF49_Ships | 2014: 01-06*,01-28*,03-17*,06-24*,09-05*,12-01*; 2015: 03-30*,08-24*,10-22*,11-12*,12-04*; 2016: 02-24,04-25,07-25,08-31,11-30; 2017: 02-23,06-23,07-17,10-10; 2018: 01-05,02-01,06-04,06-20,08-31; 2019: 02-21,04-26,07-10,08-05,09-25,11-19; 2020: 05-13,06-01,06-12,08-20,12-02,12-18; 2021: 01-21,04-30,08-20,09-08,10-28; 2022: 01-20,04-04,06-13,12-07; 2023: 07-07,08-02
FF49_Smoke | 2014: 04-21*,05-15*,06-24*,10-09*,11-07*; 2015: 03-04*,05-26*,08-11*,10-27*; 2016: 03-24,04-15,07-20,11-11; 2017: 01-10,02-14,03-08,03-24,06-12,10-23,12-21; 2018: 02-01,07-03,07-25,08-10,10-15,11-13; 2019: 03-27,07-31,11-01,12-30; 2020: 01-27,05-08,06-12,07-30,09-08; 2021: 03-05,03-23,09-13; 2022: 01-20,02-10,02-24,05-04,08-22,12-07; 2023: 07-17,12-08*,12-27*
FF49_Soda | 2013: 12-12*; 2014: 04-02*,05-15*,06-11*,07-08*,10-14*,12-04*; 2015: 07-24*,08-14*,10-30*,12-09*; 2016: 03-24,04-07,07-25,12-30; 2017: 03-08,03-29,04-28,06-07; 2018: 02-06,04-20,06-25,08-23,11-21,12-11; 2019: 02-15,05-09,05-31,06-18,07-15,07-31; 2020: 01-03,02-26,06-12,08-04,08-20,09-08,11-27,12-23; 2021: 04-27,11-18; 2022: 01-11,04-26,08-09,11-29; 2023: 05-10,08-02,11-16*,12-08*
FF49_Softw | 2013: 12-12*; 2014: 01-09*,01-28*,03-12*,06-24*,07-08*,08-01*,09-15*,12-01*,12-09*; 2015: 01-06*,03-09*,05-07*,07-29*,11-09*,12-09*; 2016: 04-07,04-25,06-10,08-18,09-09; 2017: 02-01,02-28,03-21,05-11,06-12,10-23,11-13,11-30; 2018: 02-06,06-25,07-30,12-14; 2019: 03-06,03-22,04-17,05-01,07-23; 2020: 01-27,02-21,05-13,06-04,07-14,09-08; 2021: 01-04,02-22,05-05,07-09,08-17,09-08,11-23; 2022: 04-07,07-14,08-09,11-29,12-07; 2023: 04-24,05-23,06-09
FF49_Steel | 2014: 04-07*,07-29*,09-10*,12-01*; 2015: 02-27*,05-07*,10-22*,12-09*; 2016: 01-06*,03-24,04-25,07-25,11-30; 2017: 02-23,07-28,10-10,10-31; 2018: 01-19,05-30,06-15; 2019: 02-07,03-01,07-10,07-31,09-25,11-14,12-16; 2020: 05-13,06-12,08-20,09-08,10-28,12-15; 2021: 03-23,05-21,08-20,11-18,11-29; 2022: 01-14,03-09,04-04,08-17,12-07; 2023: 02-08,07-07,07-28,12-05*
FF49_Telcm | 2014: 01-09*,03-17*,05-20*,06-11*,07-24*,12-04*; 2015: 03-12*,03-25*,05-07*,11-04*,12-01*; 2016: 03-24,04-07,05-03,07-20,12-30; 2017: 08-10; 2018: 01-02,02-06,06-25,07-17,08-23,08-31,09-27; 2019: 03-06,04-23,05-31,07-23; 2020: 01-27,05-13,06-12,08-20,09-08,12-10; 2021: 03-18; 2022: 01-14,02-24,04-18,06-13,08-01,08-09,08-22,11-07,12-07; 2023: 02-08,04-24,07-17,08-07,08-18,12-05*,12-21*
FF49_Toys | 2014: 04-07*,07-16*,11-17*,12-04*; 2015: 02-19*,04-29*,09-28*,11-09*; 2016: 03-08,03-24,04-28,11-30; 2017: 02-28,04-06,06-15,07-25,10-23,11-30; 2018: 02-28,05-30,06-20,07-17,08-31,09-27; 2019: 02-07,03-14,05-14,06-21,07-31; 2020: 04-30,06-12,09-08,10-20,12-29; 2021: 07-09,11-05; 2022: 02-24,04-07,06-13,07-11,12-07; 2023: 02-08,06-23,07-20
FF49_Trans | 2014: 03-20*,06-11*,09-15*,09-23*,11-20*; 2015: 08-14*; 2016: 03-24,07-28,08-26,11-30; 2017: 05-19,06-20,07-17,10-10; 2018: 01-24,06-20,08-31,09-24; 2019: 02-26,04-26,07-31,11-11,12-03; 2020: 01-22,06-12,08-20,09-08,12-10; 2021: 03-23,04-19,05-13,11-02; 2022: 04-04,11-23,12-07; 2023: 01-26,02-13,06-23,07-07,07-25,12-21*
FF49_Txtls | 2014: 05-15*,06-11*,07-08*,09-10*,12-09*; 2015: 01-06*,01-28*,03-09*,03-30*,06-29*,11-12*; 2016: 03-24,04-04,04-25,08-10,11-30,12-27; 2017: 02-06,03-13,05-03,07-03,07-20,11-03,12-05; 2018: 12-11; 2019: 02-07,05-14,05-31,06-21,07-15,07-26,10-08; 2020: 05-13,06-01,06-12,09-08,09-21,10-15,12-02; 2021: 01-04,01-21,03-18,11-02; 2022: 01-11,05-12,08-04,11-23; 2023: 01-18,02-13,05-10,06-23,07-20
FF49_Util | 2014: 02-05*,02-27*,05-02*,09-15*,11-12*; 2015: 05-04*,08-24*,10-27*; 2016: 01-20,02-10,04-07,07-07,07-28,12-30; 2017: 01-10,06-12,08-31,11-21; 2018: 03-26,04-12,05-08,07-09,07-25,08-23,12-19; 2019: 03-19,06-26,10-03; 2020: 01-08,02-04,02-26,05-13,06-12,08-17,11-23; 2021: 01-29,04-27,08-25,09-13,11-18,12-23; 2022: 01-11,04-12,08-22,12-15; 2023: 01-18,04-14,07-28,12-18*
FF49_Whlsl | 2014: 03-17*,06-16*,09-15*,12-01*; 2015: 03-04*,10-22*,11-12*,12-04*; 2016: 03-16,03-24,04-07,04-25,07-25,08-26,12-16; 2017: 02-28,06-07,10-10,10-26; 2018: 02-01,09-06,12-11; 2019: 02-21,05-01,07-18,09-25,11-19,12-03; 2020: 06-12,08-20,09-08,10-23,11-23,12-18; 2021: 05-13,09-08,11-18; 2022: 04-04,04-26,08-22,11-29; 2023: 05-23,07-07,07-28,11-30*
XLB | 2014: 01-09*,03-17*,06-11*,12-01*; 2015: 02-27*,11-09*,12-04*; 2016: 03-24,05-03,12-13; 2017: 02-06,06-23,07-28,10-18; 2018: 01-10,02-01,05-30,06-20,09-11,09-27; 2019: 02-04,03-01*,03-22,04-17*,07-10,07-31,10-03,11-19; 2020: 01-03,05-13,06-12,07-30,08-25,09-08,12-07,12-23; 2021: 01-15,04-09,05-13,08-20,09-08,11-18; 2022: 04-26,08-22,12-07; 2023: 02-08,04-27,07-07,08-02,12-05*
XLC | 2019: 07-18*,11-22*,12-30*; 2020: 01-27*,05-13*,06-04*,07-27*,09-08*,12-10*; 2021: 02-22*,03-26*,06-17*,07-14,09-13; 2022: 04-07,08-09,08-17,11-29,12-07; 2023: 02-08,04-19,06-09,07-20,11-30*
XLE | 2014: 03-17*,04-07*,05-02*,06-24*,12-01*; 2015: 02-19*,05-07*,09-23*,10-19*,11-12*; 2016: 03-24,05-03,12-16; 2017: 08-07,10-10,11-16; 2018: 01-19,05-03,05-24,10-10; 2019: 02-07,03-06,04-26,09-25,11-19,12-30; 2020: 06-12,08-20,12-02,12-15; 2021: 01-21,03-15,06-17,10-28; 2022: 02-10,03-17,04-04,08-30; 2023: 04-24,07-17,08-15,09-19*
XLF | 2014: 01-14*,06-16*,07-08*,07-29*,09-10*,12-12*; 2015: 03-25*,11-12*,12-09*; 2016: 03-24,04-28,06-07,12-13; 2017: 06-23,07-17,07-28,10-13,11-03; 2018: 02-01,05-30,08-02,09-06; 2019: 03-06,03-22,05-09*,07-18,07-31,11-14,12-03; 2020: 01-27,06-12,08-20,09-08,12-10; 2021: 01-15,03-23,08-20,11-02; 2022: 01-20,06-13,08-22,11-23; 2023: 02-16,06-23,07-28,12-21*
XLI | 2014: 03-17*,06-16*,09-23*,11-17*,12-01*; 2015: 03-04*,11-12*,12-04*; 2016: 03-24,07-28,08-26,11-30,12-16; 2017: 03-08,05-19,07-20,10-10,10-26; 2018: 01-24,06-04,06-20,08-10,09-24; 2019: 03-06*,04-26,07-18,07-31,09-25,11-19; 2020: 01-22,06-12,08-20,09-08,12-02,12-23; 2021: 04-22,05-13,11-18; 2022: 04-04,11-23; 2023: 06-23,07-28
XLK | 2013: 12-12*; 2014: 04-07*,06-16*,07-29*,12-09*; 2015: 03-09*,05-07*,11-09*; 2016: 04-07,08-18,12-30; 2017: 02-01,02-28,03-21,05-19,10-23,11-13,11-30; 2018: 02-06,06-15,07-30; 2019: 02-07,03-01,03-27,04-26,07-31; 2020: 01-27,05-13,06-12,07-14,09-08; 2021: 01-04,02-22,04-22,07-19,09-08,12-02,12-20; 2022: 04-07,08-09,11-07,11-29,12-15; 2023: 02-16,04-05,05-23,12-27*
XLP | 2014: 03-20*,04-07*,05-15*,09-23*,12-04*; 2015: 08-11*,10-30*; 2016: 01-06*,03-24,04-07,07-20,12-30; 2017: 02-01,03-08,03-24,06-12,12-21; 2018: 02-01,06-28,07-25,08-10,11-16; 2019: 02-26,04-04,05-09; 2020: 01-03,01-27,05-08,05-21,06-12,08-20,09-08,12-23; 2021: 04-09,04-27,05-18,08-25,11-18; 2022: 01-11,08-22,11-29; 2023: 04-14,05-05,08-02,12-05*
XLRE | 2016: 12-21*; 2017: 01-10*,03-03*,04-25*,07-07*,09-14*,11-27*; 2018: 03-26*,04-12*,05-16*,06-15*,07-17*,11-21,12-11; 2019: 02-26,03-19,04-17,06-26,09-09; 2020: 01-30,02-26,05-13,06-12,08-20,09-08,11-27; 2021: 02-22,03-31,05-05,06-17,12-02,12-20; 2022: 01-06,04-12,08-22,12-07; 2023: 02-08,05-02,05-18,06-23,07-28,12-08*
XLU | 2014: 02-05*,02-27*,04-21*,09-15*,11-12*; 2015: 05-07*,07-21*,08-24*,10-30*; 2016: 01-20,02-16,03-24,04-07,07-07,12-30; 2017: 01-10,01-27,03-03,06-12,08-31,11-21; 2018: 03-26,04-12,05-08,07-09,07-25,08-23,11-21,12-19; 2019: 03-19,06-26,09-09,10-03; 2020: 01-08,02-04,02-26,05-21,06-12,08-17,11-18; 2021: 04-27,08-25,12-02,12-20; 2022: 01-06,04-12,08-22,12-07,12-15; 2023: 01-18,04-14,07-28,12-05*,12-18*
XLV | 2014: 03-07*,06-11*,07-08*,09-15*,12-12*; 2015: 03-09*,03-25*,07-24*,11-12*,12-09*; 2016: 01-06*,03-16,04-28,06-15,08-05,12-30; 2017: 01-13,03-08,06-28; 2018: 02-01,06-20,07-20,09-06,10-05; 2019: 02-21,06-26,07-15,09-25,11-06,12-03,12-30; 2020: 01-27,05-08,05-21,06-12,07-30,08-20,09-08,11-23,12-23; 2021: 01-29,04-27,07-19,08-12,11-23; 2022: 01-03,04-04,07-14,08-04,08-17,12-07; 2023: 04-19,07-07,08-02,12-18*
XLY | 2014: 03-17*,06-16*,07-16*,09-10*,12-09*; 2015: 01-06*,03-09*,03-25*,08-06*,11-09*,12-04*; 2016: 03-24,04-28,08-02,08-23,11-30,12-21; 2017: 02-28,03-21,10-18,12-27; 2018: 02-01,06-25; 2019: 02-07,03-06,05-01,07-18; 2020: 01-27,02-21,06-12,08-04,09-08; 2021: 01-15,04-22,07-14,11-10; 2022: 04-07,08-09,08-22,11-29,12-07; 2023: 02-08,05-23,06-23
```

### C2 BOTH

```text
FF12_BusEq | 2014: 06-24*; 2016: 04-07,08-18; 2017: 05-19,11-13,11-30; 2019: 03-27,11-22; 2020: 07-14; 2021: 01-04,04-30; 2022: 04-07,08-09,11-29
FF12_Chems | 2014: 03-20*,10-01*; 2015: 11-09*; 2016: 09-09; 2017: 09-22; 2018: 08-10; 2021: 11-18
FF12_Durbl | 2014: 03-12*,07-08*; 2015: 03-25*; 2016: 03-24,05-03,08-02; 2017: 06-20,07-07,10-13; 2018: 01-19,06-20; 2019: 07-26; 2020: 01-27,05-13,07-27,12-23; 2021: 01-21,07-09,08-17,11-10; 2022: 04-07,08-09; 2023: 02-13,03-02,06-23,07-20
FF12_Enrgy | 2015: 05-07*,10-19*; 2016: 03-24,05-03,10-18,12-16; 2017: 08-07,11-16; 2018: 01-10,05-24; 2019: 02-07,09-25; 2020: 06-12,12-02; 2021: 01-21,06-17; 2022: 11-10; 2023: 07-17
FF12_Hlth | 2014: 01-28*,07-08*,09-15*; 2015: 12-04*; 2018: 02-01,07-20,10-05; 2019: 06-26,12-30; 2021: 08-12; 2023: 04-27,05-15
FF12_Manuf | 2014: 01-09*; 2015: 02-27*,05-29*; 2016: 03-24,11-30; 2017: 10-31; 2018: 01-24,08-10,09-27; 2019: 07-10; 2020: 06-12,08-20,10-28,12-02; 2021: 03-23
FF12_Money | 2014: 01-14*,07-08*,09-23*; 2015: 12-09*; 2016: 03-24,09-06,12-13; 2017: 06-23; 2019: 11-14,12-03; 2020: 06-12; 2021: 01-15,08-20,10-28
FF12_NoDur | 2017: 02-01,06-12; 2019: 04-04; 2020: 01-03; 2023: 05-10
FF12_Other | 2014: 03-17*; 2016: 03-24,07-25,11-30; 2017: 06-20,10-10; 2018: 09-24; 2020: 01-22,08-17; 2023: 06-23
FF12_Shops | 2015: 08-11*; 2017: 05-16; 2018: 02-01; 2021: 05-05,07-19,11-23; 2022: 07-27; 2023: 02-08,05-23
FF12_Telcm | 2014: 05-20*,07-24*; 2015: 05-07*; 2018: 01-02; 2019: 05-31; 2020: 08-20; 2021: 03-18; 2022: 02-24; 2023: 07-17,08-18
FF12_Utils | 2017: 08-31; 2018: 05-08,07-09; 2019: 03-19; 2020: 02-04; 2021: 04-27,08-25,12-23
FF49_Aero | 2014: 09-23*; 2015: 11-09*; 2017: 06-07,08-10; 2019: 02-21; 2020: 02-21,06-12; 2021: 03-18,06-14; 2022: 11-15; 2023: 12-18*
FF49_Agric | 2013: 12-09*; 2014: 01-09*,03-25*,07-11*; 2015: 05-29*; 2016: 05-06; 2019: 01-25; 2020: 01-03,10-20,12-02; 2021: 01-21,08-20,11-23
FF49_Autos | 2014: 03-12*; 2015: 02-24*,03-25*; 2016: 03-24,05-03,08-02,12-16; 2017: 06-20,07-07,10-13; 2018: 06-20; 2019: 04-26,07-26,11-14; 2020: 01-27,05-13,07-27,09-08,12-23; 2021: 01-21,07-09,08-17,11-10; 2022: 04-07,08-09; 2023: 02-13,03-02,06-23,07-20
FF49_Banks | 2014: 01-14*,09-23*; 2015: 05-26*,06-19*; 2016: 05-03,09-06,12-13; 2017: 06-23,07-17; 2019: 02-04,11-14; 2020: 06-12; 2021: 01-15,08-20
FF49_Beer | 2014: 01-31*; 2017: 03-08,04-28,06-07; 2018: 07-30; 2021: 04-30,12-23
FF49_BldMt | 2014: 01-06*,03-12*,09-15*,11-17*; 2015: 02-27*,12-04*; 2016: 08-18,11-30; 2017: 10-31,12-13; 2018: 06-15,08-15,09-24; 2020: 05-13,08-20,12-02; 2021: 09-08; 2023: 05-23,07-07
FF49_Books | 2014: 03-25*; 2015: 01-06*; 2016: 05-03,07-28; 2017: 07-12,08-02,10-13; 2018: 10-26,11-16; 2019: 03-06; 2020: 06-01,08-20,12-15; 2022: 08-04,11-18; 2023: 02-13,07-20,08-23
FF49_Boxes | 2014: 09-18*,11-20*; 2015: 02-27*; 2016: 08-23,09-09; 2017: 06-12,11-03; 2018: 04-30,09-24; 2020: 06-12,10-28; 2021: 09-08; 2022: 02-24; 2023: 08-02
FF49_BusSv | 2014: 01-06*,07-11*; 2015: 03-25*; 2016: 04-25; 2017: 02-28,08-02,10-18; 2018: 06-25,09-19; 2019: 03-06; 2021: 02-25; 2022: 08-09; 2023: 06-23
FF49_Chems | 2014: 01-09*; 2015: 02-27*; 2016: 05-03; 2017: 10-10; 2019: 02-04,04-23,07-10,08-05; 2020: 05-13,07-30; 2021: 01-21,11-18; 2022: 11-18; 2023: 07-17
FF49_Chips | 2014: 05-15*; 2015: 02-27*,06-03*,10-27*; 2016: 04-07; 2018: 03-21,06-12,09-06; 2019: 03-27,04-26,11-14; 2021: 01-29,07-19,12-20; 2022: 08-09,11-29; 2023: 11-27*
FF49_Clths | 2013: 12-09*; 2014: 03-25*; 2016: 08-31,12-16; 2017: 07-12,11-03,12-27; 2019: 02-21,10-24; 2020: 01-08; 2021: 01-15,07-14,11-10; 2022: 12-07; 2023: 04-27
FF49_Cnstr | 2014: 01-09*,12-01*; 2016: 03-24,04-25,06-10,11-30; 2017: 03-21,10-13,11-03,12-05; 2019: 04-26; 2020: 02-04,02-26,06-01; 2021: 05-13,08-17,09-08,11-29; 2022: 12-20; 2023: 02-08,05-23
FF49_Coal | 2014: 05-07*; 2015: 05-15*,10-22*; 2016: 02-10,03-16,04-25,05-03,10-18,12-13; 2017: 04-17,07-28,09-11,10-10; 2018: 01-05,06-15; 2019: 02-04,10-29; 2020: 01-16,04-27,09-24,12-18; 2021: 01-21,05-21,06-14,08-20,09-16; 2022: 01-20,02-24; 2023: 07-17,08-15
FF49_Drugs | 2014: 01-28*,07-08*,09-15*; 2015: 06-29*,07-24*,12-04*; 2016: 08-05; 2018: 07-20; 2019: 06-26,11-06,12-30; 2020: 12-23; 2022: 07-14; 2023: 05-18
FF49_ElcEq | 2014: 01-23*; 2015: 02-27*,04-24*,05-29*; 2016: 01-06*,03-24,12-13; 2018: 01-10,08-10; 2019: 09-25; 2020: 05-13,07-30,08-20; 2021: 07-06; 2022: 06-16,08-09; 2023: 06-23,07-25
FF49_FabPr | 2014: 03-12*,06-24*,11-17*; 2015: 04-13*,07-08*,11-20*,12-04*; 2016: 03-08,05-06,11-30; 2018: 08-15; 2019: 08-05,09-25; 2020: 05-13,08-17,12-02,12-18; 2021: 08-17,09-08; 2022: 08-17,11-10; 2023: 02-13,03-10,07-25
FF49_Fin | 2014: 08-01*,09-23*; 2015: 12-09*; 2016: 03-24,06-07,09-06,12-13; 2017: 06-23,12-18; 2019: 01-30,07-31,12-03; 2020: 05-13,06-12,10-28; 2021: 01-15,03-23,08-20; 2023: 06-23
FF49_Food | 2014: 06-11*,09-23*,11-25*; 2015: 04-13*; 2016: 05-19; 2017: 02-01,08-28,12-08; 2019: 05-22; 2021: 05-21; 2023: 05-10,12-18*
FF49_Fun | 2014: 01-28*,03-12*,07-08*; 2015: 02-24*; 2016: 04-20,08-23,11-03; 2017: 04-11,05-08,10-02; 2018: 06-07,06-25,10-05; 2019: 01-22,02-15,05-06,07-18,11-14,12-03; 2020: 01-03,01-22,02-26; 2022: 04-07; 2023: 05-23,11-30*
FF49_Gold | 2014: 01-31*,03-20*,07-08*; 2015: 01-14*,02-05*,03-04*,05-26*,10-19*; 2016: 03-08,03-24; 2017: 02-14,08-07,09-11; 2018: 04-25,11-30; 2019: 07-01; 2021: 01-15,04-30,10-28,11-23; 2022: 01-06,01-28,03-14,04-21; 2023: 01-18,04-14,10-26*
FF49_Guns | 2014: 08-06*,09-02*,09-23*; 2016: 05-19,12-08; 2017: 03-16,06-07,08-18; 2019: 05-17; 2021: 10-28; 2022: 02-02,03-14
FF49_Hardw | 2014: 04-07*,06-24*,12-09*,12-31*; 2016: 04-04,06-10,10-10; 2017: 02-28,05-11,07-28; 2018: 02-01,09-06; 2019: 03-01,11-14; 2020: 01-22,12-23; 2021: 01-21,08-17,09-08,11-18; 2022: 01-03,08-30
FF49_Hlth | 2014: 01-23*,06-11*,08-11*,09-05*; 2016: 05-03; 2017: 01-19,07-07; 2018: 01-05; 2019: 02-21,07-10; 2020: 02-26; 2022: 08-17; 2023: 07-28,12-18*
FF49_Hshld | 2017: 03-03,03-24; 2018: 01-02,08-10; 2021: 12-23
FF49_Insur | 2017: 06-23,11-08; 2018: 05-03,09-11; 2020: 06-12,08-20; 2021: 03-23; 2022: 01-06,07-14; 2023: 10-23*
FF49_LabEq | 2014: 01-06*,09-15*; 2016: 10-10; 2017: 01-24,05-19; 2018: 08-10; 2019: 03-06; 2020: 01-27; 2021: 01-26,04-30,09-13; 2022: 04-12,08-09; 2023: 01-26
FF49_Mach | 2014: 01-06*,07-08*,11-20*; 2015: 03-04*; 2016: 03-24; 2017: 10-31; 2018: 01-24,08-15; 2019: 02-07,03-01,04-26,07-10; 2020: 06-12,10-28; 2021: 11-23; 2022: 11-18; 2023: 06-23
FF49_Meals | 2014: 12-09*; 2017: 04-28,06-07,10-23; 2018: 10-02; 2021: 03-23,08-09; 2023: 05-05
FF49_MedEq | 2014: 01-28*,07-08*; 2016: 05-03,05-19; 2017: 03-08,05-08,06-12; 2018: 10-05; 2019: 02-26; 2020: 08-04; 2021: 08-09; 2022: 01-06; 2023: 04-27,12-05*
FF49_Mines | 2014: 05-07*; 2015: 02-24*,05-12*,10-19*; 2016: 03-24,05-03; 2017: 02-06; 2018: 10-05; 2019: 01-25,02-12,03-22,04-23,09-30; 2020: 05-13,07-30; 2021: 01-15,05-21,10-28; 2022: 03-14,11-18; 2023: 07-07,08-02
FF49_Oil | 2015: 01-06*,05-07*,10-19*; 2016: 03-24,05-03,10-18,12-16; 2017: 08-07,11-16; 2018: 01-10,05-24; 2019: 02-07,09-25; 2020: 06-12,12-02; 2021: 01-21,06-17; 2022: 11-10; 2023: 07-17
FF49_Other | 2014: 03-20*; 2017: 06-23; 2018: 01-19,09-24; 2019: 09-25,11-14; 2020: 07-30,08-17,12-02
FF49_Paper | 2016: 09-09,12-27; 2017: 02-06,06-28,12-08; 2018: 06-20,08-10; 2019: 10-03,11-11; 2020: 08-25; 2023: 01-18
FF49_PerSv | 2014: 01-28*; 2016: 06-28,07-28,11-30; 2017: 07-28; 2020: 01-22,06-12,08-20,10-28,12-02; 2021: 02-25,03-18; 2022: 08-04; 2023: 02-13,07-28,11-30*
FF49_RlEst | 2013: 12-12*; 2014: 01-09*,06-16*,07-08*,09-05*,11-20*; 2016: 04-25,07-28,11-30; 2017: 02-28,05-11,10-23; 2019: 02-26,07-18,08-05; 2020: 01-03,05-13,06-12,10-20,12-29; 2021: 02-25,08-17; 2023: 06-20
FF49_Rtail | 2021: 05-05,07-19,11-23; 2022: 07-27; 2023: 02-08,05-02,05-23
FF49_Rubbr | 2014: 01-06*,06-24*,11-17*; 2016: 04-07,09-09; 2017: 06-15; 2018: 04-30,09-24; 2019: 04-17; 2022: 07-14,08-09; 2023: 08-18
FF49_Ships | 2014: 01-28*,03-17*,09-05*; 2015: 08-24*; 2016: 04-25,11-30; 2017: 06-23; 2019: 07-10,09-25,11-19; 2020: 06-01,08-20; 2021: 01-21,08-20
FF49_Smoke | 2014: 04-21*,05-15*; 2015: 08-11*; 2017: 02-14,03-24,06-12,10-23,12-21; 2019: 07-31,11-01; 2021: 03-23; 2022: 02-24,05-04; 2023: 07-17
FF49_Soda | 2013: 12-12*; 2014: 07-08*; 2017: 06-07; 2020: 08-04; 2023: 05-10
FF49_Softw | 2014: 01-28*,07-08*,09-15*; 2015: 01-06*,05-07*,07-29*; 2016: 06-10; 2017: 02-01,06-12,11-13; 2018: 07-30; 2019: 05-01; 2020: 01-27; 2021: 05-05,09-08; 2022: 04-07; 2023: 06-09
FF49_Steel | 2014: 07-29*,09-10*; 2015: 05-07*; 2016: 01-06*,03-24,04-25,07-25,11-30; 2017: 02-23,07-28,10-10,10-31; 2019: 02-07,07-10,09-25,11-14,12-16; 2020: 05-13,06-12,08-20,10-28,12-15; 2021: 03-23,05-21,08-20; 2022: 03-09,08-17; 2023: 02-08,07-07
FF49_Telcm | 2014: 05-20*,07-24*; 2015: 05-07*; 2018: 01-02; 2019: 05-31; 2020: 08-20; 2021: 03-18; 2022: 02-24; 2023: 07-17,08-18
FF49_Toys | 2014: 04-07*; 2015: 02-19*,04-29*; 2017: 04-06,06-15,11-30; 2018: 07-17,08-31; 2019: 02-07,03-14,06-21; 2020: 04-30,10-20; 2022: 04-07; 2023: 02-08,06-23
FF49_Trans | 2014: 09-23*,11-20*; 2015: 08-14*; 2019: 04-26; 2022: 11-23; 2023: 01-26
FF49_Txtls | 2014: 05-15*; 2016: 08-10,11-30; 2017: 02-06,11-03; 2019: 05-31,06-21; 2020: 05-13,06-01,06-12,10-15; 2021: 01-21,11-02; 2022: 05-12,11-23; 2023: 01-18,02-13
FF49_Util | 2017: 08-31; 2018: 05-08,07-09; 2019: 03-19; 2020: 02-04; 2021: 04-27,08-25,12-23
FF49_Whlsl | 2014: 06-16*,09-15*; 2015: 12-04*; 2017: 06-07,10-10,10-26; 2018: 02-01; 2019: 02-21,09-25; 2020: 08-20; 2021: 11-18
XLB | 2014: 01-09*; 2016: 03-24,05-03,12-13; 2017: 02-06,10-18; 2018: 05-30; 2019: 04-17*,11-19; 2020: 05-13,07-30; 2021: 11-18; 2022: 04-26
XLC | 2020: 01-27*,06-04*,09-08*; 2021: 02-22*,03-26*; 2023: 02-08,04-19
XLE | 2015: 02-19*,05-07*,10-19*; 2016: 03-24,05-03,12-16; 2017: 08-07; 2018: 05-24; 2019: 02-07,09-25,12-30; 2020: 06-12,12-02; 2021: 01-21,06-17; 2022: 03-17; 2023: 04-24,07-17
XLF | 2014: 01-14*,09-10*; 2015: 03-25*,12-09*; 2016: 03-24,06-07,12-13; 2017: 06-23,11-03; 2019: 11-14; 2020: 06-12,08-20; 2021: 08-20; 2023: 12-21*
XLI | 2014: 09-23*,11-17*; 2017: 07-20; 2018: 08-10,09-24; 2019: 11-19; 2020: 06-12,08-20,12-02
XLK | 2015: 05-07*; 2016: 04-07,08-18; 2017: 05-19,11-13,11-30; 2019: 03-27,04-26; 2020: 01-27,07-14; 2021: 01-04,07-19; 2022: 04-07,08-09,11-29
XLP | 2015: 08-11*; 2017: 02-01,03-24,06-12; 2018: 07-25,08-10; 2019: 04-04
XLRE | 2017: 07-07*,09-14*,11-27*; 2018: 04-12*; 2019: 09-09; 2021: 03-31,05-05,06-17; 2023: 05-18,12-08*
XLU | 2014: 02-27*,04-21*; 2015: 05-07*; 2016: 02-16; 2017: 06-12,08-31; 2018: 05-08,07-09; 2019: 03-19; 2020: 02-04; 2021: 04-27,08-25
XLV | 2014: 09-15*; 2016: 08-05; 2017: 06-28; 2018: 07-20; 2019: 06-26,11-06,12-30; 2022: 07-14
XLY | 2014: 07-16*; 2015: 08-06*; 2016: 11-30; 2018: 02-01,06-25; 2020: 08-04; 2021: 04-22,07-14,11-10; 2022: 04-07; 2023: 02-08,06-23
```

### C6 PARTNER

```text
FF12_BusEq | 2014: 06-24*; 2015: 12-09*; 2016: 04-07,08-18; 2017: 11-30; 2020: 07-14; 2021: 04-30; 2022: 11-29; 2023: 06-23
FF12_Chems | 2014: 05-15*; 2018: 01-10; 2023: 07-17
FF12_Durbl | 2014: 01-28*; 2016: 05-03,12-16; 2018: 06-20; 2021: 07-09; 2023: 02-13,06-23,07-20
FF12_Enrgy | 2015: 11-12*; 2016: 05-03,10-18,12-16; 2017: 10-10; 2018: 01-10; 2019: 11-19; 2021: 01-21; 2022: 11-10; 2023: 07-17
FF12_Hlth | 2014: 06-16*,07-08*; 2016: 04-28; 2018: 07-20,10-05
FF12_Manuf | 2014: 06-16*,12-01*; 2015: 02-27*; 2016: 12-16; 2018: 06-04; 2019: 07-31; 2020: 06-12; 2021: 01-21
FF12_Money | 2014: 01-14*,06-16*,12-12*; 2015: 11-12*,12-09*; 2016: 04-28,09-06,12-13; 2017: 10-13,11-08; 2018: 06-20,09-06; 2019: 11-14
FF12_NoDur | 2014: 05-15*; 2017: 02-01,03-08,06-12,12-21; 2020: 08-04; 2023: 05-10
FF12_Other | 2014: 06-11*; 2016: 11-30; 2017: 10-10; 2019: 03-01,05-01,11-14; 2020: 06-12,09-08
FF12_Shops | 2015: 03-25*; 2017: 06-07; 2019: 05-01; 2023: 05-23
FF12_Telcm | 2018: 07-17; 2022: 12-07; 2023: 07-17
FF12_Utils | 2014: 02-27*; 2015: 05-04*; 2016: 01-20; 2017: 06-12; 2018: 03-26,04-12,05-08; 2019: 10-03
FF49_Aero | 2016: 12-16; 2020: 05-13,06-12; 2021: 11-18; 2022: 11-15; 2023: 07-17
FF49_Agric | 2017: 02-01,10-10; 2020: 05-13,06-12,12-02; 2023: 08-07
FF49_Autos | 2014: 01-28*,06-16*,07-08*; 2016: 03-24,05-03,08-26,12-16; 2018: 05-30,06-20; 2019: 11-14; 2020: 05-13; 2022: 08-09; 2023: 03-02,07-20
FF49_Banks | 2014: 01-14*,06-16*,12-12*; 2015: 06-19*,11-12*,12-09*; 2016: 05-03,09-06,11-30,12-13; 2017: 10-13; 2018: 02-06,05-30,09-06; 2020: 06-12; 2021: 03-23
FF49_Beer | 2014: 05-15*; 2017: 03-08,04-28,06-07
FF49_BldMt | 2014: 01-06*,12-01*; 2016: 03-24,12-16; 2017: 07-25; 2019: 08-05; 2020: 05-13,06-12,12-02; 2021: 01-26,03-23; 2023: 02-08,08-10
FF49_Books | 2015: 02-27*; 2016: 05-03; 2017: 12-21; 2019: 07-18,11-11; 2020: 06-12,08-20; 2021: 03-23,10-28; 2023: 08-23
FF49_Boxes | 2014: 09-18*; 2020: 08-20,12-02; 2023: 07-17
FF49_BusSv | 2014: 06-16*; 2016: 03-24,06-10; 2017: 06-12; 2019: 02-07; 2020: 02-21,05-13,06-12; 2022: 04-07,11-23; 2023: 06-23
FF49_Chems | 2015: 11-09*; 2016: 05-03,12-13; 2020: 05-13,06-12; 2021: 01-21; 2023: 07-17
FF49_Chips | 2014: 12-01*; 2016: 03-24,06-15,10-13; 2018: 09-06; 2019: 03-06,04-26,07-31,11-14; 2021: 07-19,09-13; 2022: 08-09,11-29
FF49_Clths | 2015: 08-14*; 2016: 11-30,12-16; 2019: 10-24; 2020: 05-13,06-12,09-08; 2023: 01-26
FF49_Cnstr | 2014: 12-01*; 2016: 06-10,12-16; 2020: 02-04,05-13,08-20; 2021: 11-29,12-20; 2023: 02-08
FF49_Coal | 2016: 03-16,05-03,10-18,12-13; 2018: 01-05; 2020: 06-12,09-24; 2021: 01-21,08-20; 2023: 07-17,08-15
FF49_Drugs | 2014: 01-28*,03-07*,06-16*,07-08*; 2016: 04-28
FF49_ElcEq | 2014: 12-01*; 2016: 12-13; 2017: 10-10; 2019: 03-01,04-26,07-31; 2020: 05-13,06-12,12-02; 2022: 04-04,06-16,08-09,11-29; 2023: 06-23,07-17
FF49_FabPr | 2016: 04-28,11-30,12-16; 2019: 08-05; 2020: 05-13,06-12,12-02; 2021: 08-17,09-08; 2022: 08-17; 2023: 07-07
FF49_Fin | 2014: 07-08*,12-12*; 2015: 11-12*,12-09*; 2016: 04-07,04-28,12-13; 2017: 12-18; 2018: 05-30,06-20; 2020: 05-13,06-12; 2021: 03-23; 2022: 06-13
FF49_Food | 2021: 05-21; 2022: 11-10; 2023: 08-07
FF49_Fun | 2014: 01-28*,07-08*; 2016: 03-30; 2019: 01-22,03-01,07-18,11-14; 2020: 05-13,09-08; 2022: 04-07,08-09,11-02
FF49_Gold | 2017: 02-14,06-12; 2018: 11-30; 2022: 01-28,09-26
FF49_Guns | 2019: 06-18; 2020: 02-04,12-02; 2022: 02-02,11-15; 2023: 07-20
FF49_Hardw | 2014: 12-31*; 2016: 06-10; 2017: 07-28; 2018: 02-01,09-06; 2019: 03-01,07-23,11-14; 2020: 01-22; 2021: 01-21,09-08; 2022: 08-30
FF49_Hlth | 2016: 05-03; 2020: 06-04; 2021: 07-14
FF49_Hshld | 2017: 02-01; 2018: 08-31,09-27; 2021: 04-27; 2023: 01-12
FF49_Insur | 2016: 04-28,12-16; 2017: 06-23,07-17; 2018: 05-03; 2020: 06-12
FF49_LabEq | 2014: 01-28*,06-16*; 2015: 03-04*; 2016: 08-18; 2017: 06-12; 2018: 06-20,10-05; 2019: 03-06,07-10; 2020: 08-07; 2021: 04-30; 2022: 04-12
FF49_Mach | 2014: 01-06*,07-08*; 2015: 11-09*; 2016: 05-03,06-15; 2017: 07-28; 2018: 06-04,10-02; 2019: 03-01,04-26,07-31,11-14; 2020: 06-12,12-02; 2021: 01-21,03-23; 2023: 08-07
FF49_Meals | 2017: 06-07; 2020: 12-02; 2022: 06-13; 2023: 05-05
FF49_MedEq | 2014: 01-28*,06-16*,07-08*; 2015: 12-04*; 2017: 06-12; 2018: 10-05; 2020: 08-04
FF49_Mines | 2014: 12-01*; 2016: 05-03; 2018: 10-05; 2019: 03-01; 2020: 05-13,06-12,09-08; 2021: 08-17; 2022: 08-22
FF49_Oil | 2015: 11-12*; 2016: 05-03; 2017: 10-05; 2018: 01-10; 2019: 09-25; 2020: 06-12,12-02; 2021: 01-21,03-15; 2022: 11-10; 2023: 07-17,08-15
FF49_Other | 2014: 04-07*; 2017: 06-23,10-10; 2018: 09-24; 2020: 12-02
FF49_Paper | 2019: 11-11; 2020: 08-25,12-02
FF49_PerSv | 2014: 01-28*,12-01*; 2016: 03-24; 2017: 05-16; 2020: 05-13,06-12,08-20,09-08,12-02
FF49_RlEst | 2016: 12-16; 2017: 05-11; 2019: 11-22; 2020: 01-03,05-13,06-12,09-08; 2021: 08-17; 2022: 06-13; 2023: 02-08,06-20
FF49_Rtail | 2015: 03-25*; 2017: 12-05; 2018: 06-25; 2019: 05-01; 2020: 01-27; 2023: 05-23
FF49_Rubbr | 2018: 09-24; 2019: 11-06; 2023: 08-18
FF49_Ships | 2014: 01-06*; 2015: 03-30*; 2016: 02-24,08-31; 2017: 10-10; 2019: 09-25; 2020: 05-13,06-12,08-20,12-02; 2021: 01-21
FF49_Smoke | 2014: 05-15*; 2017: 03-08,06-12; 2019: 07-31,11-01; 2021: 03-05,03-23; 2023: 07-17
FF49_Soda | 2017: 03-08,04-28,06-07; 2018: 04-20; 2019: 06-18; 2020: 08-20
FF49_Softw | 2014: 12-09*; 2015: 12-09*; 2016: 06-10,08-18,09-09; 2017: 02-01,06-12,11-30; 2019: 03-06; 2021: 05-05,07-09,11-23; 2022: 08-09,11-29; 2023: 06-09
FF49_Steel | 2014: 12-01*; 2015: 05-07*; 2017: 07-28,10-10; 2018: 01-19,05-30; 2019: 03-01,07-31,11-14; 2020: 05-13,06-12,08-20,09-08; 2021: 03-23,05-21; 2022: 01-14
FF49_Telcm | 2017: 08-10; 2018: 07-17,08-31,09-27; 2019: 05-31; 2021: 03-18
FF49_Toys | 2019: 03-14; 2022: 02-24,04-07; 2023: 06-23,07-20
FF49_Trans | 2017: 10-10; 2019: 04-26; 2020: 06-12,08-20,09-08; 2021: 03-23
FF49_Txtls | 2016: 03-24,11-30; 2020: 05-13,06-12,09-08; 2021: 01-21; 2022: 05-12; 2023: 02-13,06-23,07-20
FF49_Util | 2015: 05-04*; 2017: 06-12,11-21; 2018: 07-09,08-23; 2020: 02-04
FF49_Whlsl | 2014: 06-16*; 2015: 03-04*; 2016: 12-16; 2017: 10-10; 2018: 12-11; 2020: 06-12
XLB | 2014: 12-01*; 2016: 12-13; 2018: 01-10,02-01; 2020: 12-07; 2023: 08-02
XLC | 2020: 01-27*; 2021: 07-14; 2022: 04-07,08-17; 2023: 04-19
XLE | 2015: 05-07*,10-19*; 2016: 05-03; 2017: 10-10; 2019: 11-19; 2020: 06-12,12-02; 2022: 03-17; 2023: 08-15
XLF | 2014: 09-10*; 2016: 04-28,12-13; 2017: 10-13; 2018: 02-01,05-30,08-02; 2019: 07-31,11-14; 2021: 03-23
XLI | 2016: 03-24,12-16; 2017: 10-10; 2019: 04-26,09-25,11-19; 2020: 12-02
XLK | 2014: 07-29*; 2017: 02-01,11-30; 2022: 04-07
XLP | 2014: 05-15*; 2017: 02-01,06-12,12-21; 2018: 02-01; 2020: 09-08; 2023: 05-05
XLRE | 2017: 04-25*; 2018: 03-26*,04-12*,06-15*; 2020: 01-30
XLU | 2015: 05-07*; 2017: 01-27,06-12; 2018: 03-26,04-12,07-09; 2019: 10-03
XLV | 2015: 03-25*; 2017: 01-13; 2019: 02-21
XLY | 2014: 06-16*; 2019: 02-07,03-06,05-01; 2020: 09-08; 2022: 04-07,08-22,11-29; 2023: 02-08,06-23
```



---

PRO-RUN SUCC-AVOID-1 part 8

## 4. What the best-ranked candidate still gets wrong

### Ten worst C2 fake breakdowns

Ranked by maximum group/SPY relative-index appreciation over the following 21 sessions, then larger absolute appreciation, group code and date. A fake label is retained even if a later 63-session drawdown exists. These are scored warnings; five rows are Coal, so they are not ten independent mechanisms.

| Flag date | Group | Lateness | First new high, sessions | Max relative gain21 % | Member DD63 % | Event DD capture pp | Exit−hold return63 pp |
|---|---|---|---|---|---|---|---|
| 2016-02-10 | FF49_Coal | 3 | 15 | 45.30 | 12.89 | 12.81 | -92.07 |
| 2022-02-24 | FF49_Coal | 1 | 3 | 45.28 | 21.41 | 21.41 | -49.91 |
| 2021-08-20 | FF49_Coal | 4 | 2 | 41.44 | 30.59 | 30.59 | -6.44 |
| 2022-01-20 | FF49_Coal | 60 | 10 | 32.23 | 15.33 | 10.64 | -83.58 |
| 2020-05-13 | FF49_FabPr | 61 | 17 | 25.59 | 16.70 | 16.70 | -85.49 |
| 2020-12-23 | FF49_Autos | 3 | 6 | 25.42 | 26.05 | 26.05 | -1.39 |
| 2018-11-30 | FF49_Gold | 6 | 7 | 25.30 | 10.49 | 10.49 | -0.61 |
| 2016-03-24 | FF49_Gold | 10 | 9 | 24.47 | 11.56 | 11.56 | -43.66 |
| 2022-02-02 | FF49_Guns | 4 | 7 | 23.43 | 8.43 | 8.43 | -11.76 |
| 2021-09-16 | FF49_Coal | 4 | 11 | 23.14 | 33.61 | 29.88 | 8.33 |

Coal on **2016-02-10** is the sharpest illustration: the relative index subsequently gained **45.30%**, and the event calculation still credits **12.81pp** of avoided peak-to-trough drawdown. The same hypothetical exit gave up **92.07pp** of 63-session return. Avoiding a later dip from a much higher peak does not establish a good top call.

### Ten largest real-top episodes without a fresh timely C2 warning

The independent audit starts from every observable strict 63-session relative high in the permitted dates with 63 future sessions, requires an absolute decline of at least 10% from that high to the next-63-session trough, keeps the latest high for a shared trough, then removes overlapping same-group episodes in descending severity order. It does not start from OLD's rejected warnings. A fresh timely catch is a C2 flag from the high through `min(high+21, trough−1)`; raw observable C2 flags count even outside the common scored panel.

| Relative-high date | Group | Trough date | High→trough decline % | Member DD63 % | Earlier exit active at high? | Exit active at trough? | Peak in scored panel? |
|---|---|---|---|---|---|---|---|
| 2020-02-04 | FF49_Autos | 2020-03-18 | 50.17 | 50.27 | yes | yes | yes |
| 2020-02-04 | FF12_Durbl | 2020-03-18 | 47.56 | 50.45 | yes | yes | yes |
| 2019-12-18 | FF49_Mines | 2020-03-18 | 46.73 | 47.54 | yes | no | yes |
| 2022-09-19 | FF49_Autos | 2022-12-16 | 42.30 | 42.30 | yes | no | yes |
| 2020-02-19 | FF49_BusSv | 2020-03-23 | 40.61 | 40.61 | no | no | yes |
| 2020-01-30 | FF49_Fin | 2020-03-23 | 40.36 | 41.47 | yes | no | yes |
| 2022-09-19 | FF12_Durbl | 2022-12-16 | 39.90 | 31.30 | yes | no | yes |
| 2014-08-12 | FF49_Gold | 2014-11-05 | 37.79 | 37.84 | yes | no | **no — warm-up** |
| 2022-04-18 | FF49_Steel | 2022-07-05 | 37.26 | 37.95 | yes | no | yes |
| 2019-12-12 | FF49_Banks | 2020-03-16 | 36.82 | 37.93 | yes | no | yes |

**These are fresh-warning misses, not ten unprotected crashes.** Nine already had a prior exit active at the high; only the first two remained flat at the trough. Earlier warnings can be labelled fake because another relative high follows, yet still protect part of a subsequent fall; protection can also expire before the trough. Autos and Durbl overlap economically in the same episodes. Gold on 2014-08-12 is in the permitted audit block but outside the common scored panel and is explicitly tagged. There are 502 independent-by-this-deduplication top episodes and 369 fresh-warning misses, not 502 independent market regimes.

Full failure records: [results/worst_fakes.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/worst_fakes.csv), [results/largest_missed.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/largest_missed.csv), [results/real_top_episodes.csv](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/real_top_episodes.csv).

## 5. What to test next, and how this could be fooling us

**First, fix the economic target before adding more filters.** Separate a harmless relative new high from material continued leadership, and distinguish avoiding a decline below an executable exit price from avoiding a later decline after a large missed gain. Those would be new outcomes, not retroactive changes to this run's fixed fake label. Retain the original label alongside them so a prettier answer cannot replace the practitioner's complaint.

**Then test a small, separately frozen successor set with comparable exit exposure.** C2's simultaneous absolute/relative turn is a weak research clue, not an accepted rule. Any new combination or threshold needs a new run ID and must count as a new test. Match flat-day exposure as well as event on-share, specify re-entry, costs and cash return, and check net outcomes. Do not simply lengthen the warning until every drawdown is captured.

**Obtain exact membership and release vintages, then seek genuinely untouched evidence under a new commission.** The proxy map cannot establish exact constituent breadth. Current French, ETF and dollar histories can differ from those available at the time. Longer calendar blocks, such as 3–6 months, would challenge the required month-bootstrap intervals. The same already-examined discovery period cannot become a fresh confirmation sample by renaming it; no additional historical block or post-2023 outcomes were tested here.

The main way this could fool us is **measuring damage concentration and calling it economic protection**. Rare filters can pick different dates/groups or spend more time flat; a later peak-to-trough drop can look 'avoided' while the exit misses a much larger rise. Exact lateness and on-share matching remove some easy advantages, but not selection among eight rules, repeated sector exposure, changing classification, data revisions or multi-month dependence. The small C2 FF12 interval barely excluding zero is particularly fragile: ETF and FF49 matched intervals include zero, and the pooled series are not independent replications.

### Complete test and repair ledger

| Item | Count / disposition |
|---|---|
| Candidate hypotheses | 8 fixed before outcomes; 0 discarded or replaced; 0 threshold sweeps; 0 post-result signal changes. |
| Signal/control tapes | 37: OLD + 8 candidates, 1 raw VOL33, 9 per-target matched VOL tapes, 18 ±10 shifted tapes. |
| Descriptive cells | 4 cohort views ×37 tapes =148 rows; 8 rows N/A because C5 and its controls do not apply to ETF/FF49; 140 nonempty cells. |
| Horizons | N=21 primary; N=10 and45 sensitivities. All three printed, none silently selected. |
| Contrast estimates | 136 nonempty rule/cohort/control contrasts ×6 metrics =816 reported estimates, including OLD self-comparisons; these are dependent outputs, not 816 independent ideas. |
| Metrics | fake10, fake21, fake45, member DD63, next-close event avoidance, and exit-minus-hold return63. |
| Estimation repetitions | 2,000 joint calendar-month bootstrap draws, one seed; undefined sparse draws disclosed. |
| Candidate result executions | 1 complete outcome run. No dropped failed economic run. |
| Ranking exclusions | C4 and C7 below the FF12 reporting floor; their outcomes remain in every applicable table. |
| Implementation repairs before first run | Preserved explicit source-bar NaNs; initialized the selected partner; restored all-observable missed-top/catch universes; restricted C5 applicability; fixed shift annual attribution. |
| Post-outcome reporting changes | Renamed the days22–63 warning field accurately; removed a misleading count/11 frequency column; added matching-information and trough-coverage diagnostics. No candidate statistic or selection changed. |
| Verification | Synthetic RSI/EMA/bar/NaN tests; exact per-group control counts and shift support; scalar reconstruction of 12 fixed-spaced events; zero OLD-vs-OLD effects; full/prefix signal invariance through 2019-12-18. |
| Extra descriptive audits | Matching-information counts and exit-active-at-trough flags, added after results to prevent overclaiming. No new candidate or threshold. |
| Other history / deployment | No out-of-block market observation in calculations; no earlier warm-up; no untouched-period claim; no deployment or trade sizing. |

Verification and exact runtime/source hashes: [results/verification.json](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/verification.json). Metadata: [results/run_metadata.json](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/run_metadata.json).

### Source and data qualifications

- [French 12-industry construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_12_ind_port.html) and [49-industry construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html); daily value-weighted return files, not ex-dividend files. [French's data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) states that histories are reconstructed and can change.
- Static [SIC12 definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes12.zip) and [SIC49 definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes49.zip) establish the non-nesting limitation. For example, LabEq spans the FF12 BusEq/Manuf boundary.
- Public Yahoo chart data for SPY and the specified sector tickers, restricted by observation date. Adjusted closes account for splits and distributions. No pre-existence history for XLRE/XLC was filled.
- FRED DGS2, DGS10, DTWEXB, DTWEXBGS, BAMLH0A0HYM2, VIXCLS. [The Federal Reserve's 2019 H.10 change](https://www.federalreserve.gov/releases/h10/h10_technical_qa.htm) explains why the older goods-only and newer goods/services dollar series are treated separately. [Cboe VIX history](https://www.cboe.com/tradable-products/vix/vix-historical-data) is the underlying VIX series provenance.
- The official high-yield endpoint returned only the allowed block's late tail. A public, commit-pinned FRED-origin archive supplied the missing history; 2,760 values match a public archive saved in 2023 exactly, and 33 match the available official FRED overlap exactly. This does not independently validate the intervening archive-only tail or prove point-in-time release vintages. See [the exact archive sources and cross-checks](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/hy_archive_verification.json).
- All 20 retained input files have observation bounds and SHA-256 hashes in [results/input_manifest.json](https://github.com/mastermindx-market-intelligence/macro/blob/7a020ce5ce50b5329d6dddbb01016e8b2e2453b7/research/rotation_core/pro_runs/succ_avoid_1/results/input_manifest.json). Retrieval/vintage dates are separate from observation dates: this is a current-vintage retrospective calculation with a strict permitted observation block, not an assertion that the downloaded files themselves were published before 2024. Bulk French dates were filtered before numeric conversion.

**Research ruling for ledger successor-avoid-1:** completed discovery self-test; **no accepted avoid-side successor**. Keep the distinction between a warning, a missed fresh warning, event drawdown capture and a verified economic improvement. This return supplies research evidence and grants no live blocking, sizing or execution authority.
