# Pullback prospective lane — 14-ticker panel addendum (draft)

DRAFT — not frozen; no rule here is in force until the seat freezes it under a new prereg.

## 1. Status

This draft says how the existing SPY forward writer and grader would issue and grade prereg v1.1's 14-ticker panel. It changes no frozen rule. Retrospective prereg v1.1 is already frozen. That freeze does not arm a forward panel. The writer still refuses every ticker other than SPY (`engine/grey_deer_pullback_forward.py:698`).

The panel is QQQ, IWM, DIA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY. SPY stays out (`scripts/research/grey_deer_pullback_stage1b.py:72`).

## 2. Identity

Store identity is a source name, not a content hash. The nightly caller pins SPY as `collectors.massive_stock_day:SPY` (`scripts/grey_deer_pullback_nightly.py:39-40`) and passes it into `issue` (`engine/grey_deer_pullback_forward.py:622`). The digest stores that string beside the ticker (`engine/grey_deer_pullback_forward.py:337-338`). A per-night content hash would mark every later grade revised, and the readiness floor counts only unrevised grades (`scripts/grey_deer_pullback_nightly.py:12-16`).

A panel row uses the same form, one string per ticker:

- `collectors.massive_stock_day:QQQ`
- `collectors.massive_stock_day:IWM`
- `collectors.massive_stock_day:DIA`
- `collectors.massive_stock_day:XLB`
- `collectors.massive_stock_day:XLC`
- `collectors.massive_stock_day:XLE`
- `collectors.massive_stock_day:XLF`
- `collectors.massive_stock_day:XLI`
- `collectors.massive_stock_day:XLK`
- `collectors.massive_stock_day:XLP`
- `collectors.massive_stock_day:XLRE`
- `collectors.massive_stock_day:XLU`
- `collectors.massive_stock_day:XLV`
- `collectors.massive_stock_day:XLY`

SPY rows cite prereg blob `49a68b5e9c6543d662044b0aa391c4b6e6e6052e` (`scripts/research/grey_deer_pullback_stage1.py:243`). `_issue_row` writes that constant onto every issued row (`engine/grey_deer_pullback_forward.py:546`). The grader skips a row whose `prereg_blob` is not that constant (`engine/grey_deer_pullback_forward_grade.py:363-365`).

A panel row would cite prereg v1.1 blob `53837859164ab1d33785101dc0b464272acd5704` (`scripts/research/grey_deer_pullback_stage1b.py:117`). The matching manifest is v1.1.0, blob `c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7` (`scripts/research/grey_deer_pullback_stage1b.py:114-115`). The issued-row field is the prereg blob. The manifest blob stays the input pin on the runner.

The two families stay apart.

The SPY trial family is `grey_deer_pullback_v1`, budget 69 (`scripts/research/grey_deer_pullback_stage1.py:240-241`). The panel trial family is `grey_deer_pullback_v11`, budget 66 (`scripts/research/grey_deer_pullback_stage1b.py:94-99`). Manifest v1.1.0 records that split (`research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md:38-41`). A panel result does not revise the SPY verdict (`research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md:33`). Sharing a trial family would put panel nights on the SPY budget, or SPY nights on the panel budget.

The SPY ledger is one directory, `data/grey_deer_pullback/`, holding `forward_log.jsonl`, `forward_log_graded.jsonl`, and `forward_log_refusals.jsonl` (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:186-190`, `engine/grey_deer_pullback_forward.py:53-54`, `engine/grey_deer_pullback_forward.py:657`). That file is the v1 recipe. A new prereg blob is a new clock, and cohorts are not pooled (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:258`). Readiness already splits cohorts on `(prereg_blob, recipe_fingerprint)` (`scripts/research/grey_deer_pullback_readiness.py:89-90`). A shared file would still be one append log. A panel row stamped with the v1 blob would fall into the SPY cohort. A panel row stamped with the v1.1 blob and left in the SPY file is skipped by the grader as `prereg_mismatch` (`engine/grey_deer_pullback_forward_grade.py:363-365`). The design stored a ticker field so a later panel could reuse the file (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:70`). This draft reads that sentence as a row slot. The slot is not permission to share the file. The panel ledger is its own directory. The SPY forward lane also does not append nights to `data/trial_ledger.jsonl` (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:214`). The panel forward lane follows that rule for `grey_deer_pullback_v11`.

## 3. Calendar

Issue a panel night only when all 14 tickers have a closed session for that date. That date is on the D15 intersection (`research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md:108`). Horizons count sessions on the intersection.

Inside the frozen window, the common axis is the intersection of the 14 session sets. The only pinned gap is `2026-08-18`. Any other symmetric difference is `CALENDAR_MISALIGNED`. The expected count is 1320 sessions, from 2021-07-06 through 2026-10-07 (`scripts/research/grey_deer_pullback_stage1b.py:112`, `scripts/research/grey_deer_panel_adjust.py:47`). `prepare_panel` intersects after the split adjustment. On a mismatch it returns no frames (`scripts/research/grey_deer_panel_adjust.py:241-271`, `scripts/research/grey_deer_panel_adjust.py:59-61`). Stage 1b calls that function and refuses the run (`scripts/research/grey_deer_pullback_stage1b.py:492-500`). It does not forward-fill.

A later night is the same intersection rule on that night. One ticker with no closed bar produces one refusal row and zero issued rows. The other 13 do not issue. Prior nights stay as written. This is the writer's whole-night shape: one failing gate appends one refusal and issues nothing (`engine/grey_deer_pullback_forward.py:626-634`). The writer has no panel-gap check today. It issues the last bar of the one series it was given, and it refuses a non-session asof as `NOT_A_SESSION` (`engine/grey_deer_pullback_forward.py:709-711`).

The historical pin of 1320 sessions is the training prefix. A new one-night gap does not edit that pin and does not reopen the frozen window.

## 4. Corporate actions

The D14 table is a 2-for-1 on 2025-12-05 for XLB, XLE, XLK, XLU, and XLY (`scripts/research/grey_deer_panel_adjust.py:34-40`). Stage 1b adjusts. It does not drop the ticker because the split sits inside a feature window.

`prepare_panel` runs before any feature or label (`scripts/research/grey_deer_pullback_stage1b.py:490-500`). `apply_pinned_splits` checks the observed pre/post close ratio against `[0.9 × ratio, 1.1 × ratio]` (`scripts/research/grey_deer_panel_adjust.py:416-442`). On a pass, rows strictly before the effective date have open, high, low, and close divided by the ratio, and volume multiplied by the ratio (`scripts/research/grey_deer_panel_adjust.py:446-455`). Transactions are left unchanged. A failed check returns `SPLIT_TABLE_MISMATCH` and no frames (`scripts/research/grey_deer_panel_adjust.py:129-134`). After the intersection, a remaining absolute-log break above `log(1.25)` on adjusted closes is `SPLIT_DISCONTINUITY`, again with no frames (`scripts/research/grey_deer_panel_adjust.py:276-281`). An unpinned split is never inferred (`scripts/research/grey_deer_panel_adjust.py:152-156`). Dividends stay unadjusted (`scripts/research/grey_deer_panel_adjust.py:12-13`).

The longest feature windows are 63 sessions: `rv63`, `sma_gap63`, and `dd63` (`scripts/research/grey_deer_pullback_stage1.py:641-653`, `lib/observed_moves.py:34`). The forward writer does not adjust. `_prepare_close` only drops dates before `WINDOW_START` (`engine/grey_deer_pullback_forward.py:97-130`), and `score_asof` builds features on that series (`engine/grey_deer_pullback_forward.py:254`).

The panel writer calls `prepare_panel`. It does not reimplement the ratio. A pinned split inside a 63-session lookback stays in the sample after adjustment. A failed confirmation, or a remaining break, refuses the whole panel night: one refusal row, no issued rows, no partial panel. The other names do not issue without the split names, and the split names do not issue alone.

## 5. Episode rule

D9 merges on the common date axis (`research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md:102`, `research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md:576-590`).

An event date is a date where at least one ticker has `Y = 1`. Several names on the same date are one event date. `panel_event_dates` does that collapse (`scripts/research/grey_deer_pullback_stage1b.py:989-1000`). Clusters then merge event dates whose date-index gap is at most `h` (`scripts/research/grey_deer_pullback_stage1.py:1474-1486`). The gap is a difference of date indices. It is not a count of ticker-rows. The episode window runs from 21 sessions before the cluster's first event through `h` sessions after its last (`scripts/research/grey_deer_pullback_stage1.py:237-239`, `scripts/research/grey_deer_pullback_stage1.py:1489-1491`). Overlapping windows become one calendar episode (`scripts/research/grey_deer_pullback_stage1.py:1494-1504`). `panel_honest_n` calls those two stage-1 functions (`scripts/research/grey_deer_pullback_stage1b.py:1003-1017`). The power floor is at least 10 calendar episodes and at least 10 event months (`scripts/research/grey_deer_pullback_stage1.py:237-238`). Per-ticker episode counts are stored beside the floor and never enter it (`scripts/research/grey_deer_pullback_stage1b.py:1010-1011`). Leave-one-episode-out removes that episode's dates from every ticker (`scripts/research/grey_deer_pullback_stage1b.py:1051-1056`).

> **CAUTION.** Stage 1b showed that D9 collapses h21 to one episode across 2022-2026. A forward panel lane under D9 may never reach the §8 floor at h21. PR #9122 writes `research/grey_deer/pullback_stage1b/PULLBACK_STAGE1B_RESULTS.json` (`scripts/research/grey_deer_pullback_stage1b.py:100-101`). The field `episodes.h21.binary.episode_windows` is the list `panel_honest_n` stores (`scripts/research/grey_deer_pullback_stage1b.py:1040`) and the payload places under `episodes.h21.binary` (`scripts/research/grey_deer_pullback_stage1b.py:1436-1450`). On that PR the field holds one window, and the cell's episode count is 1. The floor is 10. Event months in that cell run from 2022-10 through 2026-09. This draft does not propose a new episode rule. The rule question is open for v1.2.

## 6. Readiness

Design §5 applies to one cohort, one horizon, and one gate family. A cohort is `(prereg_blob, recipe_fingerprint)` (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:218`, `scripts/research/grey_deer_pullback_readiness.py:89-90`). The floors are not per ticker. A ticker that abstains does not get its own floor. The gate configs are `M3-ALL@C=1.0` and `Q3-ALL` (`scripts/research/grey_deer_pullback_readiness.py:43-46`).

Per panel date:

- Issued sessions, floor 252. One distinct `asof` with at least one genuinely issued row in the cell (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:224`, `research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:232`). The code uses a set of `asof` (`scripts/research/grey_deer_pullback_readiness.py:333`, `scripts/research/grey_deer_pullback_readiness.py:353`). Fourteen tickers on one night are one session. Ten configs at three horizons are also one session.
- Calendar span, floor 300 days, from the first issued `asof` to the last (`scripts/research/grey_deer_pullback_readiness.py:285-289`).

Per ticker-row in the current reporter:

- Graded rows, floor 200 (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:234`). The counter appends every joined row (`scripts/research/grey_deer_pullback_readiness.py:347`).
- Events, floor 20 (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:235`). The counter sums rows with `Y = 1` (`scripts/research/grey_deer_pullback_readiness.py:349`).
- Non-events, floor 50 (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:236`). The counter sums rows with `Y = 0` (`scripts/research/grey_deer_pullback_readiness.py:350`).

On SPY a cell has at most one row per date, because the cell keeps one horizon and one config (`scripts/research/grey_deer_pullback_readiness.py:332`). On the panel that cell can hold 14 rows per date. Those three counters would then move 14 times faster than the session counter. That is the manufacture risk. The §5 distinct-session rule has to hold per panel date. A panel date adds one to issued sessions. It must not be read as 14 sessions. This draft does not retune 200, 20, or 50. Whether those three stay row counts is an open question for the seat.

Per panel, on the D9 date axis:

- Clusters, floor 5, and calendar episodes and event months, floors 10 and 10 (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:237-239`). The reporter currently calls `s1.honest_n` on NYSE ordinals of every graded row (`scripts/research/grey_deer_pullback_readiness.py:292-322`). That is the single-series rule. A panel cohort has to call `panel_honest_n` so the event date is "any ticker has `Y = 1`" and the index is the intersection (`scripts/research/grey_deer_pullback_stage1b.py:1003-1018`). Per-ticker episode counts stay descriptive (`research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md:589`).

Both bars still have to hold before a claim is assessable: the §5 table and the §8 episode and event-month floors (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:220`). `floors_met` only records that the sample-size floors hold (`scripts/research/grey_deer_pullback_readiness.py:33-39`).

## 7. Writer and grader changes

No code in this draft. Until the seat freezes a new prereg, `issue` keeps refusing non-SPY tickers with `UNFROZEN_PANEL`.

Call, and do not edit:

- `prepare_panel` (`scripts/research/grey_deer_panel_adjust.py:241`). The panel loader uses it for D14 and D15. The writer must not recode the ratio or the intersection.
- `fit_configurations_on_block` (`scripts/research/grey_deer_pullback_stage1b.py:660`). It already pools the training union and calls `training_fold_is_thin` on ticker-date rows (`scripts/research/grey_deer_pullback_stage1b.py:676-680`). The thin-fold thresholds stay 20 rows and 2 events (`research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md:474`, `scripts/research/grey_deer_pullback_stage1.py:234-235`).
- `panel_honest_n` (`scripts/research/grey_deer_pullback_stage1b.py:1003`). Readiness uses it for a v1.1 cohort.

Minimal edits:

- `load_close`, `_run_issue`, `_run_grade`, and `main` (`scripts/grey_deer_pullback_nightly.py:50`, `scripts/grey_deer_pullback_nightly.py:83`, `scripts/grey_deer_pullback_nightly.py:99`, `scripts/grey_deer_pullback_nightly.py:115`). Load the 14 source names. One joint issue call writes the panel directory. One grade call per ticker follows, on that ticker's adjusted intersection close. The SPY job stays a separate invocation with `collectors.massive_stock_day:SPY`.
- `issue` (`engine/grey_deer_pullback_forward.py:618`). After a freeze, accept the 14 names only, require all 14 closes, and write the panel directory. A gap or a split refusal appends one refusal and returns `issued` 0. The SPY branch and the `UNFROZEN_PANEL` branch for any other name stay. One `OBSERVER_NOT_ON_MAIN` refusal still follows a successful night (`engine/grey_deer_pullback_forward.py:766-778`), once per call.
- `_prereg_matches` (`engine/grey_deer_pullback_forward.py:379`). The panel check compares the v1.1 file with `PREREG_BLOB_SHA`. The SPY check keeps `s1.PREREG_BLOB`.
- `recipe_fingerprint` (`engine/grey_deer_pullback_forward.py:364`). The panel fingerprint appends the v1.1 blob. Its closed list adds `scripts/research/grey_deer_panel_adjust.py`. It must differ from the SPY fingerprint (`engine/grey_deer_pullback_forward.py:59-66`).
- `_issue_row` (`engine/grey_deer_pullback_forward.py:546`). Panel rows store the v1.1 blob and the v1.1 prereg path.
- `_prepare_close` (`engine/grey_deer_pullback_forward.py:97`). The panel index is the intersection calendar from `prepare_panel`, not one ticker's raw length.
- `score_asof` (`engine/grey_deer_pullback_forward.py:230`). For a panel night, score tonight's date through `fit_configurations_on_block` on the adjusted frames. Keep `_prospective_block` (`engine/grey_deer_pullback_forward.py:133`) so a short tail stays its own block. Pass each ticker's store identity into `inputs_digest` (`engine/grey_deer_pullback_forward.py:343`). The digest formula stays.
- `grade` (`engine/grey_deer_pullback_forward_grade.py:301`). Point it at the panel directory. Accept `prereg_blob == PREREG_BLOB_SHA`. Keep the per-ticker filter (`engine/grey_deer_pullback_forward_grade.py:358-359`). Labels stay that ticker's own close (`engine/grey_deer_pullback_forward_grade.py:136-142`).
- `_window_close` (`engine/grey_deer_pullback_forward_grade.py:117`). No new math. The caller passes the adjusted intersection series. This function only cuts at `WINDOW_START`.
- `_cell` and `_session_power` (`scripts/research/grey_deer_pullback_readiness.py:325`, `scripts/research/grey_deer_pullback_readiness.py:292`). For a v1.1 cohort, issued sessions stay the set of panel dates, and episodes come from `panel_honest_n`. Numeric floors stay the `FLOORS` table (`scripts/research/grey_deer_pullback_readiness.py:49-58`).

`inputs_digest_payload` (`engine/grey_deer_pullback_forward.py:307`) needs no formula change.

## 8. Open questions

1. What directory name holds the panel ledger? It is a different directory from `data/grey_deer_pullback/`. This draft does not choose the path. Heartbeat and audit registration stay out of scope (`research/grey_deer/PULLBACK_PROSPECTIVE_LANE_DESIGN_2026-10-12.md:212`).
2. Which refusal reason marks a one-ticker gap on the issue night? The shape is one row and zero issues. The historical 1320-session pin stays as it is.
3. Do the graded, event, and non-event floors stay per ticker-row, or move to per panel date? Issued sessions and span stay per panel date. The numbers 200, 20, and 50 are not retuned here.
4. Does the seat still want a forward h21 cell under D9, given one calendar episode in the PR #9122 field? Any rule change waits for v1.2. This draft leaves D9 as written.
5. Confirm the forward panel keeps the unmerged prospective block on the intersection index, while stage-1b historical folds keep their own short-block merge.
6. Confirm one `OBSERVER_NOT_ON_MAIN` row per panel night, rather than one per ticker.
7. A later unpinned break refuses the night as `SPLIT_DISCONTINUITY` and does not edit `PINNED_SPLITS`. Confirm that a new pin would be a new prereg.
8. Does the panel recipe list include `grey_deer_pullback_stage1b.py` and `grey_deer_panel_adjust.py`? If the panel fingerprint also hashes `engine/grey_deer_pullback_forward.py`, a SPY-only edit of that module rotates the panel cohort.
9. Confirm the panel forward lane does not append nights to `data/trial_ledger.jsonl` for `grey_deer_pullback_v11`, matching the SPY lane's rule for `grey_deer_pullback_v1`.
10. Confirm dividends stay unadjusted on the forward panel, with the same disclosure as D14.
