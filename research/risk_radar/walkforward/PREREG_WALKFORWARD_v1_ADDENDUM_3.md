# Addendum 3 to PREREG_WALKFORWARD_v1 — 2026-11-12 (before any fold is scored)

Kept in a separate file so the frozen prereg's pinned SHA-256 (01e66c59…ca7e7ca) stays verifiable.
Principal ruling 2026-11-12 (point 2): the DEXJPUS caveat in addendum 2 may not stay open into a
scored fit. This addendum closes it. **Pre-fit correction of a look-ahead, not a design change**
(as ruled for addendum 2). No fold has been scored or looked at: the harness run on the
one-session inputs was compute only; its outputs were moved out of the tree unread
(`/tmp/rr_wf_unscored_lag1/`) and are discarded, not reported.

## Evidence (worker report, reviewed: `/tmp/rr_fred_lags/REPORT.md`; dates committed as
`FRED_FIRST_RELEASE_DATES_v1.csv`, ALFRED initial-release vintages, dates only)

| Leg | Source | Release | Evidence | Stale at the nightly run |
|---|---|---|---|---|
| `jpy_carry` | DEXJPUS (Fed H.10) | **weekly**, Monday 4:15 pm ET for the prior business week; next business day if Monday is a federal holiday | rule matches 1,711 / 1,712 ALFRED 2020+ values; lag 1–6 business days, median 3 | 1–5 sessions |
| `rates_realrate` | DFII10 (H.15) | next business day, 4:15 pm ET | rule matches 1,703 / 1,714 (residuals: holiday calendar) | 1 session |
| `credit_oas_roc` | BAMLH0A0HYM2 (ICE via FRED) | next business day | production store at the 2026-11-10 run held 2026-11-09; ALFRED stamps same-day (date-level only; archive starts 2023-11) | 1 session |

## Rule now applied (all series alike: walk-forward fit, shipped v2 comparator, challengers)

`engine/risk_radar_eval/availability.py`: for each session d, each FRED leg is **rebuilt exactly
as the production engine would at d's nightly run** (`leading_signals`: obs-dated transform,
reindex onto SPY sessions, forward-fill, 504-session percentile) from only the observations
released by d. Release date = the observed ALFRED first-release date where present (2019+,
including the one unexplained DEXJPUS anomaly, 2021-03-12 → 2021-03-22), else the rule above.
For DEXJPUS this is the as-of join on release date, not a shift. Proof:
`test_pit_replay_matches_production_engine_at_d` (four dates, exact equality against the live
engine fed a store cut to what was released by d). `inputs.incumbent_signals()` now returns this.

The HY OAS baseline keeps its one-session shift (= next business day). Effect of the replay versus
the one-session shift on 2020-01-02 → 2026-11-10: `jpy_carry` differs on 65% of sessions (mean
|Δ| 0.086 percentile); `credit_oas_roc` and `rates_realrate` differ on ≥99% but by mean |Δ| 0.002
and 0.004 (the shift was applied to the percentile, the replay to the input series).

## Not verified

- HY OAS intraday ingestion time (one night of store evidence plus the earlier repo note; ALFRED
  history for this series starts 2023-11).
- DFII10's 11 holiday-calendar residuals are handled by the observed dates, not the rule.

## Production input fault, for slice 3 (no live change now)

The live `engine/risk_radar.py` forward-fills DEXJPUS with no limit (`build_jpy_carry`, `:657`) and
applies no availability handling to any FRED leg. Its nightly read of the yen leg is therefore on a
value 1–5 sessions old (median 3), and it treats that as current. That is not look-ahead in
production (it uses what it has), but it is undeclared staleness. Slice 3 item: declare per-leg
staleness on the state row and decide whether a weekly leg belongs in a daily state.

## Order

Addendum 3 is committed before the walk-forward harness is run for scoring. The scored run uses
`run(signals=inputs.incumbent_signals())` at the commit that adds this file.
