# Defect note: Risk Radar history replays read FRED values before they were published

Dated 2026-11-12. Found by the Risk Radar leader while checking claim 2 on #11137. Status:
**reported, not fixed.** The Risk Radar team has not re-scored these paths and has not changed
them. This note records the defect. It does not fix it.

## The defect

`engine/risk_radar.py` `leading_signals()` (line 665) takes FRED series by observation date and
fills them forward onto the SPY calendar (line 678, `series.reindex(idx).ffill()`). This applies
to HY OAS (line 681), the 10-year real yield DFII10 (line 691) and USD/JPY DEXJPUS (line 746). A
value observed on day t therefore appears in day t's row, but FRED publishes it on the next
business day, and later still after a federal holiday. That is right for the live nightly run,
which only ever uses the latest row. It is wrong for a replay over history: each past day reads a
value that was not yet public at that close. The leg most exposed is `rates_realrate`, a
five-session change.

`engine/risk_radar_eval/availability.py` `pit_signals()` (line 125) rebuilds these three legs
from only what had been released by each session. It uses ALFRED first-release dates where they
exist and the release rule otherwise. The callers below do not use it.

## Callers that replay history without the release lag

| File | Lines | Evidence that rests on it |
|---|---|---|
| `engine/risk_radar_backtest.py` | 154 (`state_series` fallback), 190 (`state_accuracy`), 264 (`probability_quality_report`), 496 (`gate_report`) | **The CI evidence gate.** `tests/test_risk_radar.py` lines 93–117 call `leading_signals()` and `gate_report`. The `lift_2020` / `lift_full` values in `engine/risk_radar.py` `_LEG_CALIB` (lines 96–110) come from `gate_report`, and they decide which legs count as VALIDATED. `compare_calib` (used by `engine/risk_radar_review.py`) reaches it through `state_accuracy` and `probability_quality_report`. |
| `scripts/research/risk_radar_state_ladder_calibration.py` | 231 | `research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_RESULTS_2026-09-21.md` |
| `scripts/research/risk_radar_probability_walkforward.py` | 356 | `research/grey_deer/RISK_RADAR_PROBABILITY_WALKFORWARD_RESULTS_2026-09-23.md` |
| `scripts/research/risk_radar_displayed_probability_audit.py` | 253 | `research/grey_deer/RISK_RADAR_DISPLAYED_PROBABILITY_AUDIT_RESULTS_2026-09-22.md` |
| `scripts/research/risk_radar_gate_latency.py` | 51, 338 | `research/grey_deer/RISK_RADAR_GATE_LATENCY_RESULTS_2026-09-21.md` |
| `scripts/research/risk_radar_caution_persistence.py` | 199 | `research/grey_deer/RISK_RADAR_CAUTION_PERSISTENCE_RESULTS_2026-09-21.md` |
| `scripts/research/risk_radar_episode_atlas.py` | 219 | `research/grey_deer/RISK_RADAR_EPISODE_WARNING_PATH_RESULTS_2026-09-21.md` |
| `scripts/research/grey_deer_pullback_stage1.py` | 2341 | Pullback stage-1 study (`research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md`) |

The four named in the commission are the first four rows. The last three were found by the same
search (`leading_signals()` called outside `engine/risk_radar_eval/`) and are listed so the owner
has the full set. How much any published figure moves is **not known**: nobody has re-scored
these paths.

## Not affected

- **The walk-forward** (`engine/risk_radar_eval/walkforward.py` line 405) uses
  `inputs.incumbent_signals()`, which goes through `pit_signals`. This covers
  WALKFORWARD_FOLDS_v1 and WALKFORWARD_SCORECARD_OOS_v1.
- **The catalogue reads** (`research/risk_radar/catalogue_read/run_read.py` line 77, and every
  ledger row from v2 on) also use `incumbent_signals()` / `pit_signals`.
- **Partly affected, already restated:** the main tables of the Risk Radar team's own in-sample
  reads were built from the unlagged replay:
  - `SCORECARD_INSAMPLE_2026-11-12.md` §1–§5;
  - `PIVOT_SCORECARD_INSAMPLE_2026-11-12.md` (runner `scripts/research/risk_radar_pivot_insample.py`,
    states from `bt.state_series`).

  Both are labelled in-sample. `SCORECARD_INSAMPLE` §6 (`INSAMPLE_READS_LAG1_v2.json`, through
  `incumbent_signals()`) restates the scorecard, pivot and insurer reads with the release lag:
  87 of 1,724 state rows change. The pivot scorecard file does not yet point to that restatement.
  A cross-reference line is owed there in the follow-up PR.
- **The live nightly state** reads only the latest row. The engine (`engine/risk_radar.py`) is
  unchanged and stays so.

## What a fix would be

The owner routes each caller above through `engine.risk_radar_eval.availability.pit_signals`.
Equivalently, `inputs.incumbent_signals()` with `availability_lag=True`. The fix does three
things:

1. It passes that same frame to `subscore_series` and `state_series(..., sigs=)`. This means the
   `state_series` fallback at line 154 never reloads the unlagged panel.
2. It sets `pit_signals(start=...)` to the start of each study's history. The default 2019-06-03
   lags earlier rows by only one session, so the gate's 1994+ full-history lift needs either an
   earlier start or a stated one-session approximation.
3. The owner then re-runs the gate and the listed studies and states which published figures
   move, including `_LEG_CALIB`'s `lift_2020`. Changing the VALIDATED set is a live-engine decision
   for the owner. The Risk Radar team does not make it.

## Owner

There is no CODEOWNERS file in the repository. Every commit to each listed file is authored as
`dashboard-bot`, an automation identity and not an owner. **Owner not recorded.**
