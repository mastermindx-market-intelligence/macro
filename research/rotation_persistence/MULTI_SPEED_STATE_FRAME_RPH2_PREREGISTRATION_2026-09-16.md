# RPH-2 Multi-Speed State Frame — corrected preregistration

**Program owner:** `WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE`
**Carrier:** stacked on RPH-1 (`sol/rotation-persistence-horizon-rph1-20260916`)
**Operation:** `multi-speed-state-rph2-20260916-sol-001`
**Authority:** research/context only. No ranking, gating, sizing, Prophet mutation, execution, or capital authority.

## 1. Mission and why it matters

RPH-1 established that sector rotation is multi-speed: short-horizon leadership can decay quickly while slower leadership persists, and dependence can change without raw dispersion moving in the same way. RPH-2 therefore produces a **causal state frame at every completed daily session** rather than choosing a single “best timeframe.”

The machine job is to make each historical decision date joinable to the state that was knowable from closes through that date. A later, separately preregistered experiment may test entry policies against outcomes. RPH-2 itself must never read those outcomes.

## 2. Canonical input and provenance

RPH-2 reuses RPH-1's existing `load_price_panel` source owner. It does not create a price loader, archive, calendar, identity plane, or receipt system.

Required complete-date close panel, in this exact order:

`XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY, SPY`

The eleven sector ETFs are the fixed cross-section. `SPY` is retained as the common benchmark/source-basis control, but RPH-2 does not use SPY to manufacture a scalar “leadership correlation.” Persisted output requires the RPH-1 byte-bound source receipt: exact common row count, first/last session, symbol list, and SHA-256 for every input file.

A missing sector is not silently dropped. The complete-date loader excludes a date missing from any required file before RPH-2 sees it. The receipt records that common-date basis. A current file hash proves bytes read now; it does **not** prove point-in-time historical availability or correction timing.

## 3. Output grain

`state_frame.sector_rows` has one row per `(session, sector)` and is directly joinable by historical session and ticker. `state_frame.market_rows` has one row per session.

This date-keyed shape is a required capability. Window summaries alone are insufficient because a later entry-policy experiment must recover the state at the decision date without recomputation or future leakage.

## 4. Structural state — 21 completed sessions

For every sector and session with at least 21 prior completed sessions:

- `structural_return_21`: simple close-to-close return from `t-21` through `t`.
- `structural_rank_21`: cross-sectional rank of that 21-session return, descending; rank 1 is strongest. Ties use average rank.
- `structural_percentile_21`: `(N - rank)/(N - 1)` over the fixed eleven-sector panel. Top = 1, bottom = 0.
- `structural_rank_velocity_21`: yesterday's rank minus today's rank; positive means improving.
- `structural_return_velocity_21`: change in the trailing 21-session return from the prior session.
- `structural_top3_residency_21`: consecutive completed sessions through `t` that the **same sector** has remained rank <= 3. Non-top-three = 0. Insufficient history = null.

Absolute ETF price levels never enter leadership ranks.

## 5. Tactical state — 5 completed sessions

The same six fields are computed using a five-session trailing return and emitted as the `tactical_*_5` family. This is a faster descriptive state, not an entry signal and not a claim that five sessions is optimal.

## 6. Daily MACD phase and cycle state

For every sector, standard daily MACD uses EMA spans 12/26/9 with `adjust=False` and explicit warm-up periods:

`MACD line = EMA12(close) - EMA26(close)`
`signal = EMA9(MACD line)`
`histogram = MACD line - signal`

RPH-2 emits the histogram, sign, causal three-session slope, causal three-session acceleration, bars since the latest **true opposite-sign** histogram cross, current half-cycle age, and latest completed positive/negative half-cycle lengths.

Leading zero -> first non-zero is **not** a cross. On a genuine `+ -> -` or `- -> +` flip, the prior half-cycle completes on the session immediately before the flip and the new half-cycle begins on the flip session.

## 7. 3D decay-matched comparison basis

RPH-2 does not pretend a daily series contains completed 3D information. It only constructs a daily filter whose exponential **memory decay** matches each component of a 3D 12/26/9 EMA.

For each completed-3D component span `s`:

`alpha_3d = 2/(s+1)`
`retention_3d = 1 - alpha_3d`
`alpha_daily = 1 - retention_3d^(1/3)`
`equivalent_daily_span = 2/alpha_daily - 1`

This transformation is applied independently to fast=12, slow=26, and signal=9. The resulting histogram is labeled `macd_histogram_3d_decay_matched`, never “actual 3D MACD” or information-equivalent 3D confirmation.

## 8. Market-state rows

For each completed session:

- `dispersion_daily`: sample standard deviation (`ddof=1`) of the eleven same-session daily simple returns. First return row is null.
- `mean_pairwise_correlation_20`: mean of all 55 unique pairwise Pearson correlations over the trailing 20 **completed daily return observations**, null until all 20 exist.
- `participation_positive_5`: fraction of the fixed eleven sectors with positive trailing five-session return.
- `participation_positive_21`: fraction with positive trailing 21-session return.
- `participation_denominator`: always 11 because the input contract requires the complete panel.

No negative indexing, tail wrapping, forward fill, or denominator shrinkage is permitted.

## 9. Null, correction, and determinism behavior

Insufficient history is represented as JSON `null`, never a value borrowed from the end of the frame. All calculations are prefix-causal: appending or mutating sessions after date `t` must not change any row at or before `t`.

The producer emits strict JSON through the existing atomic writer. NaN and Infinity are forbidden. Re-running the same panel/receipt and `produced_at` must be byte-semantically deterministic.

If source parquet bytes are corrected later, a new run legitimately changes affected historical state; the receipt identifies the new source bytes. RPH-2 does not claim to reconstruct when the correction was first knowable.

## 10. Explicitly forbidden in RPH-2

RPH-2 may not compute or ingest forward returns, payoff labels, hit rates, realized exits, optimal horizons, policy scores, model promotion decisions, Prophet admission, ranking, position size, or execution actions. It may not import those authority planes merely to “prepare” for the next experiment.

## 11. Rejected candidate record

The first candidate on commit `e18d5924912068517022979a81ee2c5e7a4a39f4` is **rejected evidence**, not a baseline to preserve. Parent review found semantic defects its tests did not discriminate:

- cross-sectional “leadership” ranked absolute ETF price levels rather than horizon returns;
- the purported leadership percentile used a one-element Spearman calculation and therefore collapsed to null;
- top-tier residency was calculated once for the whole panel and returned identically for every sector;
- the early 21-session participation loop used negative positional indexing and read future tail rows;
- MACD signal math was applied to the fast EMA rather than to the MACD line;
- the 3D comparison normalized only part of the filter and converted alpha to span with the wrong formula;
- leading zero-to-nonzero histogram transitions were counted as crosses;
- output collapsed state into summaries, leaving no historical date-keyed frame for the next experiment;
- no canonical atomic CLI producer existed.

No conclusion, metric, or “COMPLETE” label from that candidate has authority.

## 12. Acceptance battery

RPH-2 is source-acceptable only if tests discriminate all of the following:

1. Exact prefix invariance for every overlapping sector row and market row when future sessions are appended or mutated.
2. Leadership rank follows trailing return even when absolute ETF price levels are deliberately reversed.
3. Top-three residency differs by symbol on a sustained leader/laggard control.
4. Participation-21 is null before 21 prior sessions and never reads tail rows; fixed denominator is 11.
5. Dispersion and trailing-20 mean pairwise correlation match independent formulas.
6. Daily MACD histogram matches an independent 12/26/9 reference calculation.
7. All three 3D decay-matched components satisfy `(1-alpha_daily)^3 = 1-alpha_3d`, with `span = 2/alpha - 1`.
8. First non-zero histogram state is not a cross; opposite-sign flips complete the prior half-cycle with correct length.
9. Persisted output is strict JSON, byte-bound to the exact RPH-1 source receipt, and authority remains context-only.
10. CLI reuses the RPH-1 loader and existing atomic writer and writes only under a research-safe output directory.
11. Existing RPH-0/RPH-1 rotation-persistence tests remain green.

## 13. Actual-source producer proof and current freshness limit

A local real-input producer run on 2026-09-16 reused the canonical RPH-1 `data/yahoo` loader and source receipt revision `8d198b42f6bff491a49b1f3467b56ca4bb673f80`. It produced 2,067 common sessions from 2018-06-19 through 2026-09-09, 22,737 date-sector rows, and 2,067 market rows through the actual CLI and strict atomic JSON writer. The temporary proof output was removed after inspection; no product/runtime artifact was published.

Every one of the twelve required source files currently reports last session `2026-09-09`. Therefore this proof establishes the historical producer path, **not current September 16 rotation state**. A future current-state consumer must first recover/qualify the source refresh lane; RPH-2 must not paper over the gap with another loader or a different unreceipted feed.

The common panel has 2,067 rows because XLC begins in 2018 while older files contain longer histories. This is an explicit common-basis choice, not evidence that earlier sector state is unavailable from every source.

## 14. Next experiment boundary

The next wave, not this one, may preregister a paired **remaining-opportunity / entry-phase** evaluation using the frozen date-keyed frame. That experiment must define labels, horizons, treatment/control timing, exit policy, multiple-testing control, and walk-forward/holdout rules before reading outcome results. It must keep trend horizon, entry phase, and exit horizon separate rather than treating “higher timeframe” as inherently safer.

## 15. Stop condition and continuation

Stop RPH-2 at an immutable reviewed source head with green discriminating tests and the atomic research producer. Do not merge through RPH-1's existing HOLD, deploy, or connect the state to Prophet/trading paths. The continuation action is to run the separately preregistered paired outcome experiment on a point-in-time-qualified/common-basis corpus once its source owner has met that gate.
