# Pullback power-floor projection (2026-10-13)

EXPLORATORY. This is a planning projection from already-inspected history.
It is not a forecast, and it is not evidence about skill.

Figures are the JSON at `research/grey_deer/pullback_floor_projection/FLOOR_PROJECTION_2026-10-13.json`. Seed `20261013`, 20,000 draws from `numpy.random.default_rng`. Input blobs: stage-1 `2727fb2c4645a001e0b160c69105b663f615ab2b`, stage-1b `57759d08796575f225861735cb995cdccff09cde`.

## Rates

Exposure is the date axis, in years of 252 sessions. Cohort A (SPY-only forward lane) has one ticker, so sessions equal the stage-1 origin count. Cohort B (hypothetical 14-ticker panel under prereg v1.1 D9) stores origins as ticker-date rows, so sessions = origins / 14. The prospective lane starts at zero. History supplies the rate only.

Count floors use a Jeffreys posterior `Gamma(shape = k + 0.5, rate = T years)` on a Poisson rate, then a `Gamma(shape = n, rate = λ)` wait. Event-months are a separate Poisson count of distinct months. That is an approximation: a year has at most 12 months, and months are not independent of events. A historical count of zero is not given a rate. That floor is `not reachable`, and no draw is taken.

Clock floors do not use the posterior. Issued sessions are 252 / 252 = 1 year, assuming the lane issues every cash session. Calendar span is 300 / 365.25 = 0.8214 years. Graded rows assume one gated binary config: 1 row per session on A, 14 on B, with the first grade `h` sessions after the first issue. Count floors add that same label lag, `h / 252` years. The binary family is the one projected.

On B, the events floor counts ticker-event rows (`ticker_events`). The stage-1b field `events` is the event-date count and is the input to the D9 gap check. Either series clears 20 events in a fraction of a year, so the choice does not pick the binding floor.

| Cohort | h | Origins | Sessions | Years | Episodes | Clusters | Months | Event rows | Event dates | Episodes / year |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 1001 | 1001 | 3.9722 | 4 | 4 | 5 | 11 | 11 | 1.007 |
| A | 10 | 996 | 996 | 3.9524 | 6 | 8 | 9 | 36 | 36 | 1.5181 |
| A | 21 | 985 | 985 | 3.9087 | 7 | 9 | 16 | 117 | 117 | 1.7909 |
| B | 5 | 14000 | 1000 | 3.9683 | 11 | 31 | 35 | 405 | 175 | 2.772 |
| B | 10 | 13930 | 995 | 3.9484 | 4 | 20 | 44 | 1168 | 395 | 1.0131 |
| B | 21 | 13776 | 984 | 3.9048 | 1 | 5 | 46 | 2726 | 625 | 0.2561 |

The h=21 panel episode rate is the rejected reading below. It is not the planning rate. On that same cell the event-month rate is 11.7805 per year, close to the cap of 12, so the Poisson month model is strained. The month floor still clears at median 0.9079 years, and it is not the binding floor.

## Years until each floor

Cell is median years [p10, p90] at rate scale 1. `All floors` is the median of the draw-wise maximum, which is the year when every floor holds. The binding floor is the one with the latest median. `Share` is the fraction of draws in which that floor is last. Issued sessions are 1.0 [1.0, 1.0] and calendar span is 0.8214 [0.8214, 0.8214] in every row.

| Cohort | h | Graded | Events | Non-events | Clusters | Episodes | Months | All floors | Binding (share) |
|---|---:|---|---|---|---|---|---|---|---|
| A | 5 | 0.8135 [0.8135, 0.8135] | 6.9979 [4.3949, 11.4363] | 0.219 [0.1841, 0.2584] | 4.4604 [1.9209, 10.5998] | 9.1977 [4.523, 20.2015] | 7.4446 [3.803, 15.4436] | 12.4813 [7.7955, 23.344] | episodes (0.4502) |
| A | 10 | 0.8333 [0.8333, 0.8333] | 2.1922 [1.5297, 3.1102] | 0.2442 [0.2082, 0.2845] | 2.3028 [1.0898, 4.7385] | 6.2521 [3.263, 12.3456] | 4.199 [2.3399, 7.5858] | 7.014 [4.2852, 12.7017] | episodes (0.6805) |
| A | 21 | 0.877 [0.877, 0.877] | 0.7396 [0.5586, 0.9711] | 0.3071 [0.2675, 0.3517] | 2.0787 [1.009, 4.1337] | 5.3755 [2.9191, 10.0768] | 2.422 [1.4557, 3.9654] | 5.5369 [3.296, 10.1185] | episodes (0.8429) |
| B | 5 | 0.0794 [0.0794, 0.0794] | 0.2119 [0.1615, 0.2751] | 0.0343 [0.0318, 0.0371] | 0.6178 [0.3224, 1.0848] | 3.4519 [1.9741, 6.0087] | 1.1151 [0.6936, 1.7299] | 3.4522 [1.9992, 6.0087] | episodes (0.9754) |
| B | 10 | 0.0992 [0.0992, 0.0992] | 0.1062 [0.0886, 0.1275] | 0.055 [0.0524, 0.058] | 0.9607 [0.4914, 1.7432] | 9.3242 [4.5422, 20.2975] | 0.9021 [0.5764, 1.3758] | 9.3242 [4.5422, 20.2975] | episodes (0.9992) |
| B | 21 | 0.1429 [0.1429, 0.1429] | 0.1116 [0.1042, 0.1204] | 0.1009 [0.0979, 0.1043] | 3.6095 [1.6448, 7.9508] | not reachable | 0.9079 [0.5943, 1.3409] | not reachable | episodes (not reachable) |

On SPY at h=5 the episode median is latest, but episodes are last in only 0.4502 of draws. Event-months are last in 0.2734 and events in 0.1774, so the all-floors median (12.4813) sits above the episode median (9.1977). On the panel at h=5 and h=10, episodes are last in nearly every draw.

## D9, and panel h=21

D9 clusters event dates on the date axis. A new episode starts only when the next window does not overlap the previous one. The window runs from 21 sessions before the first event through `h` sessions after the last, so the inter-event gap must be at least `h + 22` sessions. The whole panel has to be quiet for `h + 21` sessions. Per-ticker episodes do not count.

At h=21 the committed stage-1b file has one window, `[294, 1319]`, length 1026 sessions. That is the whole stored episode history. The longest inter-event gap is 38 sessions. A new episode needs 43. The longest quiet run is 37 sessions. The rule needs 42. Separating gaps are 0 of 624. The episode count does not grow while the panel keeps producing gaps like the ones already stored.

A Jeffreys `Beta(0.5, 624.5)` model of those 0 successes has no finite mean wait. Nine separating gaps are required to reach 10 episodes after the first episode opens. The quantiles of that wait are 23.4098 [p10], 148.4185 [median], and 4329.0043 [p90] years. Treating the single window as one Poisson renewal instead gives 32.0509 [11.1894, 135.2143] years to 10 episodes. That reading is stored as `rejected_independent_poisson` and is not used. The planning cell is not reachable. Rate scales 0.5 and 2 do not create a gap that was not observed, so both stay not reachable.

At h=10 there are four windows: `[294, 645]`, `[666, 805]`, `[808, 977]`, `[994, 1315]`. A new episode needs a gap of 32 sessions (a quiet run of 31). The history has 3 such gaps, and the longest gap is 52. The episode count grows only when the whole panel goes quiet for that long. It did so three times in 3.9484 years, which is why the Poisson projection is slow: median 9.3242 years, p90 20.2975. At h=5 the same file has 11 windows and 10 separating gaps, and the episode median is 3.4519 years.

## Sensitivity

Clocks do not move. Poisson rates are multiplied by 0.5 and by 2. Binding stays episodes in every cell. The all-floors median [p10, p90] is:

| Cohort | h | ×0.5 | ×2 |
|---|---:|---|---|
| A | 5 | 24.9327 [15.5828, 46.54] | 6.2552 [3.9079, 11.7375] |
| A | 10 | 14.0089 [8.5214, 25.3179] | 3.5305 [2.1459, 6.3896] |
| A | 21 | 10.8683 [6.5354, 20.2123] | 2.8141 [1.6927, 5.1394] |
| B | 5 | 6.8989 [3.9884, 12.1164] | 1.7387 [1.0001, 3.0161] |
| B | 10 | 18.3992 [9.0942, 40.1791] | 4.6058 [2.2691, 10.1798] |
| B | 21 | not reachable | not reachable |

Halving the historical rates roughly doubles the reachable waits. Doubling them roughly halves those waits. At ×2 the panel h=5 10th percentile sits on the one-year session clock (1.0001). Panel h=21 does not become reachable.

## What this means for the program

The SPY-only lane is waiting on episodes at every horizon: at the historical rate the median time until every floor holds is 12.4813 years at h=5, 7.014 years at h=10, and 5.5369 years at h=21, with 90th percentiles 23.344, 12.7017, and 10.1185 years. The 14-ticker panel clears the row floors in a few months, reaches the h=5 episode floor at a median of 3.4522 years, and at h=10 still needs a median of 9.3242 years because D9 merged the history into four episodes. At h=21 the same rule leaves one episode on window [294, 1319], with 0 of 624 gaps long enough to start another, so that floor is not reachable on any planning horizon unless the rule changes: the mean wait for nine separating gaps is infinite, the median is 148.4185 years, and the 90th percentile is 4329.0043 years.
