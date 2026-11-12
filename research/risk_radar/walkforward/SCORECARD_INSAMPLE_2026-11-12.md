# Risk Radar scorecard — in-sample reference, 2020-01-02 → 2026-11-10

**Label: IN-SAMPLE.** The shipped v2 constants were chosen on data that includes this window. This
is the reference column the walk-forward results will sit beside. It is not out-of-sample evidence.
2024 onward is the Radar's own already-seen history (direction ruling 2026-11-12, point 6).

Produced by `engine/risk_radar_eval/scorecard.py` on SPY total-return closes from the committed
store (data through 2026-11-10). Raw output:
`research/risk_radar/walkforward/INSAMPLE_SCORECARD_v2_2020-2026.json`. States come from
`engine.risk_radar_backtest.state_series`, the parity-fixed replay owner, with the live calibration.

## 1. The event definition behind "43.8% against 17.6%"

Day-level, not episode-level. For each session d: the event is true if the **lowest SPY close in
the next 21 sessions is at least 5% below d's close**. The 43.8% is the share of risk-off days
followed by such a loss; 17.6% is the share of all 2020+ days
(`research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_PREREG_2026-09-21.md`, "Frozen targets").

Reproduced with today's data: risk-off 44.8% (n=239 days) vs base 17.5%. The 239 risk-off days
form **28 separate runs**. Days overlap heavily: one 2022 bear market contributes many of them.

Elevated measures **3.2% (n=31)** here against 30.3% (n=33) in the September study. **Reconciled:**
the September figures reproduce exactly with the `global_breadth` leg absent. The live
configuration includes the leg. The September elevated figure is withdrawn and 43.8% is superseded
by 44.8% (n=239). See `ELEVATED_CELL_RECONCILIATION_2026-11-12.md`.

## 2. Episodes in the window (SPY total return, onset = session after the peak, merge within 21
sessions of recovery)

| Depth | Episodes | Onsets |
|---|---:|---|
| ≥5% | 9 | 2020-02-20, 2021-09-03, 2022-01-04, 2024-03-28, 2024-07-17, 2025-02-20, 2025-10-30, 2026-01-28, 2026-10-07 (open) |
| ≥7% | 5 | 2020-02-20, 2022-01-04, 2024-07-17, 2025-02-20, 2026-01-28 |
| ≥10% | 3 | 2020-02-20, 2022-01-04, 2025-02-20 |

## 3. Scorecard at h = 21 sessions

| Series | Budget (share of days on) | Day P(≥5% in 21) | Lift | ≥5% eps caught before onset | ≥5% caught by breach (median lead to breach) | ≥10% caught by breach (lead) | Alert runs: in-episode / early-true / false | False alarms/yr (≥5%) |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Radar loud (elevated+) | 15.7% | 40.0% | 2.29 | **0 / 9** | 0 / 9 | 3 / 3 (3) | 25 / 0 / 0 | 0.0 |
| Radar risk-off | 13.9% | 44.8% | 2.56 | 0 / 9 | 0 / 9 | 3 / 3 (3) | 28 / 0 / 0 | 0.0 |
| Radar caution+ | 78.0% | 21.5% | 1.23 | 9 / 9 | 9 / 9 (36) | 3 / 3 (36) | 33 / 14 / 24 | 3.5 |
| SPY < 200-day avg | 19.3% | 34.5% | 1.97 | 0 / 9 | 0 / 9 | 3 / 3 (3) | 18 / 0 / 0 | 0.0 |
| VIX ≥ 20 | 41.2% | 24.8% | 1.42 | 4 / 9 | 8 / 9 (16) | 3 / 3 (10) | 39 / 8 / 18 | 2.6 |
| VIX ≥ 25 | 20.3% | 26.2% | 1.49 | 2 / 9 | 6 / 9 (8.5) | 3 / 3 (3) | 33 / 2 / 10 | 1.5 |
| HY OAS 21d change, top decile | 11.0% | 42.2% | 2.41 | 3 / 9 | 5 / 9 (20) | 3 / 3 (17) | 32 / 3 / 1 | 0.15 |

Definitions (`engine/risk_radar_eval/scorecard.py`): an episode is *caught before onset* if the
alert is on in the h sessions before onset. It is *caught by breach* if the alert is on at any point
from onset−h to the session the loss first reaches the depth. An alert run that starts inside an
active episode is *in-episode* (confirming); otherwise it is early-true if an onset follows within
h, else a false alarm.

Probability calibration (h21, ≥5%, loud-state probabilities): Brier skill +7.2% vs base. Cells:
13% shown → 3.7% observed (n=380); 16% → 16.7% (n=1,053); 25% → 3.2% (n=31); 33% → 44.8% (n=239).

## 3b. Breach lead, loss avoided and cost (h = 21; episode counts beside every figure)

90% intervals are exact binomial intervals (Clopper-Pearson). Nine cases support no tighter
interval.

| Series | Budget | ≥5% caught by breach | ≥7% caught by breach | ≥10% caught by breach (lead) | Median share of decline after first alert (≥7%) | Net per year (≥5% basis) | Median trough → all-clear |
|---|---:|---|---|---|---:|---:|---:|
| Radar loud | 15.7% | 0/9 [0, .28] | 3/5 [.19, .92] | 3/3 [.37, 1] (3) | 0.55 | −2.8% | 0 |
| Radar risk-off | 13.9% | 0/9 [0, .28] | 3/5 [.19, .92] | 3/3 [.37, 1] (3) | 0.55 | +0.1% | 0 |
| Radar caution+ | 78.0% | 9/9 [.72, 1] | 5/5 [.55, 1] | 3/3 [.37, 1] (36) | 0.78 | −9.6% | 18 |
| SPY < 200-day avg | 19.3% | 0/9 [0, .28] | 3/5 [.19, .92] | 3/3 [.37, 1] (3) | 0.55 | −4.4% | 0 |
| VIX ≥ 20 | 41.2% | 8/9 [.57, .99] | 5/5 [.55, 1] | 3/3 [.37, 1] (10) | 0.76 | −11.5% | 6 |
| VIX ≥ 25 | 20.3% | 6/9 [.35, .90] | 5/5 [.55, 1] | 3/3 [.37, 1] (3) | 0.63 | −6.6% | 2 |
| HY OAS 21d top decile | 11.0% | 5/9 [.25, .83] | 4/5 [.34, .99] | 3/3 [.37, 1] (17) | 0.60 | −3.0% | 1 |

How the columns are defined (paper accounting only, never a trading rule):

- An alert at day d's close counts as out of SPY for session d+1.
- *Net* = return avoided during declines (onset to trough), minus rebound given up (trough to
  recovery), minus return given up outside episodes. It is summed over alert sessions and divided
  by years in the window.
- *Trough → all-clear* = sessions after the trough before the alert turns off.

**No series, including every baseline, avoids more loss than it gives up in the rebound plus
outside costs over 2020–2026.** On this sample the risk-off state roughly breaks even, at +0.1% a
year. It switches off promptly (all-clear 0 sessions after the trough), but it switches on late,
so it captures about half the decline.

## 4. What this says (in-sample, so an upper bound)

1. **The loud Radar is a confirmation signal, not an early warning.** Every one of its 25 loud runs
   since 2020 started after a ≥5% decline was already under way. It caught none of the 9 episodes
   before onset. Its high day-level hit rate comes from switching on inside drawdowns. The same is
   true of the plain "SPY below its 200-day average" baseline, which it does not clearly beat.
2. **At a matched budget, credit-spread velocity alone looks as good or better.** HY OAS 21-day
   change in its top decile fires on 11% of days (Radar loud: 15.7%). It has a similar day-level hit
   rate (42% vs 40%) and earlier lead to the 10% breaches (17 vs 3 sessions). It flags 3 of 9
   episodes before onset, at 0.15 false alarms per year.
3. **The early tier is too broad to be a warning.** Caution or above flags every episode early, but
   it is on 78% of days and produces 3.5 false alarms per year.

So "world-class accuracy" is not reachable by refitting the current constants. The scorecard already
gives the research desk the bar any challenger has to clear at the same budget. Walk-forward refit
(slice 1) will show whether the procedure's out-of-sample numbers are worse than these.

## Not verified

- The elevated discrepancy (§1).
- Episode counts at h = 3, 5 and 10 are in the JSON file but are not summarised here.
- Breadth input history: present from 1962 in the store, but not re-audited for point-in-time
  membership.
