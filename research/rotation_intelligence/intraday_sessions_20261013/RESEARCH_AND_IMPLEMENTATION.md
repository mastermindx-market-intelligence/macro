# Intraday and overnight rotation: measurement research and bounded implementation

Date: 2026-10-13. Operation: `rotation-intraday-session-research-20261013`.
Existing program: `sector-rotation-intelligence` in `config/mastermind_programs.yml`; Rotation Command and Sector Pulse remain its existing components. This is an additive research/source slice, not a new program, detector authority, data store, work queue, or scored decision plane.

## 1. Outcome and present boundary

**Continuation:** [CONTINUATION_SOURCE_DELTA.md](CONTINUATION_SOURCE_DELTA.md) records the subsequently implemented source-clock repair, matched intraday comparisons and real grounding consumer, with 491 passing focused tests. The sections below preserve the initial research/publication evidence; the continuation is the current source frontier.

The user wants Sector Intelligence and Sector Cycles to recognize sector and theme leadership changes concealed by full-day returns. The useful outcome is an earlier, correctly timed, explainable observation of relative leadership, with separate overnight and regular-session contributions, not a promise that every rotation continues or should be traded.

This slice has implemented exact elapsed-time returns in the existing heatmap computation path and established reproducible controls for the next session-aware extension. It has not installed an intraday sector detector, acquired a new feed, altered Sector Cycles, enabled alerts, changed scoring, or deployed production code. Code/test completion is not parent-product completion.

Source pins:
- Protected procedure: Mastermind `54e8659730141fc130ebbeb214dbb50f3edb04a7`, Skillpack 1.0.1, bootstrap major 1. Reused compatible pin.
- Macro implementation baseline: `7f1e4ede020b53b1d86b39642e9c88f334f0d61a`.
- Terminal epoch source inspected: `2c16b32e64aa593f92addd2f8f2aa213d91e163f`.
- Adjacent leadership plan #9134: `4d7fb55e3f3c3674a55a10292cbd843640b7641b`.
- Adjacent October investigation #9035: `13648c7d0198f5726f08cd37b6a2adfc69b12306`.
- Separate in-flight source-clock repair #8923: `03b168ab9d74f0972c3669d0b430b7773f9b5f75`.

## 2. Findings that materially change the previous proposal

### A. A displayed hour was not necessarily an hour

At the Macro baseline, `engine/sp500_heatmap.py::intraday_returns` used row offsets: last row versus previous row for 1H, two rows back for 2H, four rows back for 4H. It did not verify timestamp distance. Three executed synthetic probes against that exact incumbent function returned `1H: 5.0` for price 100 -> 105 despite elapsed durations of 120 minutes, 4,020 minutes over a weekend, and only five minutes.

This is a verified source-level measurement defect, not evidence that a particular historical live screen or trade was wrong. Its production incidence is unmeasured.

The bounded repair uses actual timezone-aware timestamps and exact endpoints. The two-hour example now emits only 2H; the weekend emits no intraday return; the five-minute example emits only 5M. Existing hourly values are preserved when their timestamp geometry is valid. All seven already-declared intraday heatmap windows can now populate from suitable finer observations, without changing the hourly collector or fetching additional data.

The function does not forward-fill, use the nearest row, assume a timezone, choose among duplicate clocks, or silently rewind past an invalid latest close. It preserves exact zero returns; invalid prices and clocks remain unavailable. Observed endpoints do not prove uninterrupted path coverage.

### B. Terminal display epochs are not real UTC timestamps

The pinned Terminal `ingest/backfill_intraday.py` explicitly stores Eastern wall-clock time reinterpreted as a UTC epoch for chart display. It already has an inverse helper. An executed witness extracted and ran only the two inspected pure conversion functions, not the collector module. A real 13:30 UTC October open becomes 09:30 on the display epoch; treating it as real UTC is four hours wrong. The November example is five hours wrong. Both inverse round trips passed.

This is intentional chart formatting, not by itself a Terminal bug. The integration mistake would be feeding those display epochs directly into a UTC-aligned rotation comparison. The adapter must reuse the existing inverse and retain the source convention; never invent a second calendar or silently localize the epoch as genuine UTC. Evidence: `terminal_clock_witness.json`.

### C. A fresh build timestamp is not fresh market evidence

The pinned Macro configuration still sets `live.delayed_min: 15`, and its hourly accrual source retains a 15-minute delay constant. These are source/configuration facts, not independent confirmation of the account's present subscription or the deployed service configuration. The new hourly accrual code also emits exact-file source receipts; reuse those rather than replacing them with file modification times. The separate #8923 source-clock repair is still in flight on its own files and was not modified.

A five-minute analytical horizon remains useful on delayed bars, but cannot be described as five-minute-fresh detection. Measure market endpoint -> first availability -> compute -> publication -> display separately.

### D. Current production inventory is not established

The read-only attempt to inspect the known production Terminal store through its documented SSH host failed with `Permission denied (publickey)`. No alternate credential, account, or carrier was tried to obtain that same denied access. The expected local intraday directories were absent, and no `data/intraday` files were tracked at the Macro baseline. Therefore current 5m universe coverage, production latency, venue coverage and historical bar completeness remain unknown. Prior source descriptions and historical inventories must not be promoted to a current data census.

### E. The canonical daily sector stores do not retain opening prices

An independent schema-only read of the committed daily SPY and all 11 sector ETF histories at the Macro baseline found 12 readable files, all ending 2026-10-12, and zero opening-price columns. Each holds close_price, close and volume. The existing collector's _extract method does not retain Open even in its high/low branch. Per-file digests, columns and date ranges are in daily_store_census.json; no market-price rows were exported.

This makes opening anchors an explicit implementation dependency, not an assumption: the exact daily stores cannot supply the overnight/open-to-close split. Reuse another already-qualified source or extend the existing data owner under its normal gates. Do not reconstruct an open from a daily close, or pair an unadjusted open with a total-return-adjusted close. This does not claim that every company store lacks opening observations. It is independent of the denied production Terminal read, which remains unresolved.

## 3. The actual hidden-rotation quantity

Keep close-to-close, prior-close-to-open, and open-to-current returns separately. With consistent price basis and common anchors:

`log(P_current/P_previous_close) = log(P_open/P_previous_close) + log(P_current/P_open)`.

Apply the same split to the benchmark and subtract corresponding intervals. This gives exact additive relative-return contributions; averaging constituent log returns is not automatically the return of an equal-weight investable basket. Existing basket-index methodology remains the owner of group levels and weights.

Executed synthetic control: group A follows 100 -> 102 -> 100; group B follows 100 -> 99 -> 100. Both daily returns are zero. A outperforms B by about 298.53 log basis points in the gap and underperforms by the same amount during the regular session. The daily ranking erases that complete reversal.

A descriptive cancellation measure is `1 - abs(sum(segment_log_returns))/sum(abs(segment_log_returns))`. It is undefined, not zero or one, when every segment is flat. It measures information hidden by netting, not return predictability. For market/benchmark comparisons use matching segments, and retain absolute performance beside relative performance.

The most useful product states distinguish: relative improvement while falling, absolute recovery with relative improvement, broad participation, concentrated leader-only movement, session reversal, failed rotation, and persistent leadership. These are descriptive distinctions; no new trading permission follows.

## 4. Do not mistake a rolling-window exit for acceleration

For `X(t) = log(group_level / benchmark_level)`, define `RS_h(t)=X(t)-X(t-h)`. Then:

`RS_h(t)-RS_h(t-d) = [X(t)-X(t-d)] - [X(t-h)-X(t-h-d)]`.

The apparent improvement is the entering interval minus the expiring interval. It can be positive solely because an old loss rolled out, even when nothing improved during the arriving interval. The executed control produces a 200-log-basis-point improvement with an arriving return of exactly zero.

Therefore expose new interval performance and expired-window contribution separately. Compare disjoint 5m/15m intervals as well as overlapping rolling windows. Do not count 5m, 15m and 30m measurements of substantially the same price path as three independent votes. Session-anchored and catalyst-anchored changes answer different questions from generic rolling windows.

## 5. Coverage and composition are part of the measurement

A group's numerator and membership denominator must refer to the same frozen cohort and same observation endpoints. Report eligible membership, members observed at both endpoints, covered portfolio weight, stale members, maximum or distributional source age, and the membership version. A median age alone can hide unobserved heavyweights.

Executed synthetic control: member A remains +4% since its base and member B remains -4%. If one snapshot observes only B and the next only A, an available-member average jumps eight percentage points although neither price changes. The common cohort is empty, so the comparable change is unavailable.

Separate full-house basket performance from a qualified liquid intraday sleeve. A sleeve may provide useful early evidence but must not silently stand in for the entire theme. Common-cohort comparisons reduce composition drift but create a selected population; disclose exclusions instead of presenting a complete-market claim.

Use both equal-weight and cap-weighted views where the existing owners can provide consistent levels. Their disagreement identifies concentration, not necessarily bad data. Report top contributors and distinct issuers. Theme overlap should be measured with common weights; the control's two baskets share 70% exposure, so their agreement is not independent confirmation. Effective member count from portfolio weights is a concentration diagnostic, not a statistical sample size or proof of independent observations.

## 6. Session and market-structure contract

Reuse the existing exchange calendar and actual-close helpers. Do not let the slow cycle engine ingest unclosed intraday bars as completed daily observations. A tactical reversal can coexist with a structural uptrend and should be displayed as that split.

Preserve at least these separate facts: instrument identity, venue/source, price basis, true market timestamp, bar start/end convention, first available timestamp, source revision/digest, session ID, trade date, membership version and evaluation cutoff. Missing is not zero; missing aggregates can reflect no qualifying trades rather than a failed feed. Do not bridge gaps without identifying what was unobserved.

Keep premarket, regular session and after-hours contributions distinct. An overnight gap is not an observed overnight trajectory. A private-venue overnight tape is not automatically consolidated market coverage. Future US extended-hour changes also make a hardcoded 20:00-04:00 universal session unsafe: Nasdaq and Massive currently describe a planned December 6, 2026 move to a 21:00-04:00 overnight session with a 20:00-21:00 maintenance interval. That is a future rollout, not proof it is available today or included in our entitlement. Source-specific session versions and trade-date rollover must remain explicit.

## 7. Research evidence and its limits

The following original-source records were inspected on 2026-10-13. The literature inspection here is abstract/author-summary level, not a full-text systematic review or a reproduced trading study.

1. Lou, Polk and Skouras, *A tug of war: Overnight versus intraday expected returns*, JFE 2019. Author research page describes within-period continuation and cross-period reversals. It supports separating return periods, not a claim of current sector alpha. https://personal.lse.ac.uk/polk/research/work.htm ; DOI 10.1016/j.jfineco.2019.03.011.
2. Heston, Korajczyk and Sadka, *Intraday Patterns in the Cross-Section of Stock Returns*, Journal of Finance 2010. Primary university/publisher summaries distinguish same-time-of-day continuation from short-lived reversal/microstructure effects. It motivates time-of-day-conditioned baselines and cautions against treating every short reversal as durable rotation. https://www.kellogg.northwestern.edu/academics-research/research/detail/2010/intraday-patterns-in-the-cross-section-of-stock-returns/ ; DOI 10.1111/j.1540-6261.2010.01573.x.
3. Massive Custom Bars specification. Bars use qualifying trades; empty intervals need not be feed failures; the adjusted flag addresses splits. https://www.massive.com/docs/rest/stocks/aggregates/custom-bars.
4. Massive 23/5 announcement, dated 2026-08-26. Product-specific support and outstanding cutover details remain separate from an announcement. https://www.massive.com/blog/us-equities-move-to-23-5-trading.
5. Nasdaq Newsroom, 2026-09-22, *Inside the SEC's 24-Hour Trading Roundtable*. Primary exchange statement on the planned 2026-12-06 session change. https://www.nasdaq.com/newsroom/sec-24-hour-trading-roundtable-chuck-mack-on-resilient-overnight-market.

Existing negative studies remain construction-specific. Do not revive the killed rotation x cycle-position entry confluence, or recast old daily heat-tier nulls as proof that no useful intraday detection exists. Neither a past null nor a synthetic control establishes live forecasting performance.

## 8. Concrete next experiment, without consuming held outcomes

This is a prospective protocol proposal for the incumbent owner, not enrollment in a new trial registry. No held #8299 outcomes or other restricted study outputs were opened.

Primary question: does a session-separated, common-clock leadership observation reveal persistent changes sooner than the current daily/5-day display at the same tolerated false-alert rate?

Start with 11 sector ETFs plus SPY and a qualified liquid subset of existing house baskets. Establish bar-duration, actual UTC, adjustment and availability receipts first. Do not manufacture an all-micro-theme population from navigation taxonomy. Retain current and historical membership with their own evidence.

Compare four nested constructions: the existing daily-only read; latest return since prior close; session-separated/common-cohort relative returns; and those returns plus non-overlapping interval persistence and participation. Keep the information set and publication delay matched. Include a time-of-day-conditioned baseline, market-wide beta/common-move controls, and absolute-return disclosures. Add complexity only when it improves the declared outcome.

Measure detection latency from the first eligible observation, not from an ex-post local turning point. Separately report market-time, arrival-time and screen-time delays. Count every initial alert, including failures and repeated reversals; do not evaluate only episodes that later confirmed. Match candidate events one-to-one to independently defined later leadership intervals and disclose unmatched events.

Prespecify the persistence horizon, minimum effect relative to noise/spread, liquidity/coverage policy and grouping before reading held-out outcomes. Use a chronological development/validation/holdout split and purge overlapping outcome intervals. Cluster uncertainty by session/event/market shock rather than treating correlated tickers or repeated 5m rows as independent samples. Report precision/recall, alert burden, time-to-detection distributions, magnitude captured before recognition, and coverage/latency by session. Do not combine these into an uncalibrated universal confidence score.

Stratify gap continuation, gap reversal, regular-session handoff, late-day auction-driven moves, earnings-concentrated themes, market-wide deleveraging, and sparse extended-hours cases. Separate diagnostic detection from net-of-cost tradable performance. Promotion to ranking, sizing, B4, Plan, or live trade actions remains outside this slice.

## 9. Consumer integration sequence

1. Exact source clocks and qualified minute coverage through current Data OS/Terminal/hourly receipt owners. Consume #8923 rather than re-editing its source-clock files.
2. Extend the existing Sector Pulse/Rotation Command output with common-clock interval and session evidence. Reuse the existing basket levels, membership and retained-history owners. No second state or snapshot service.
3. In the existing Sector Intelligence workspace show a session ribbon and current 15m/30m/60m relative changes, the structural/tactical disagreement, onset time and source delay. Preserve the existing long-cycle display rather than making it flicker with each intraday price.
4. Drill down to participating stocks, concentration and missing coverage. Retained originally-issued history and retrospective price reconstruction must remain different views.
5. Route measured observation changes through existing alert triage only after notification-specific noise, deduplication and freshness policies have been qualified. No repeated alert merely because the page refreshed.

The immediate useful UI question is: 'This group is still red for the day, but has it been persistently outperforming since the open or the last catalyst, and is participation broadening?' That is different from 'which group is greenest since yesterday?'

## 10. Executed verification and exact remaining work

- Baseline regression: 18 failing / 6 passing cases before the source change.
- Candidate focused source suite: 49 passed across the new clock tests, existing heatmap-cap tests and regional heatmap regressions.
- Actual `build_heatmap` consumer tested: genuine 5M availability enabled; unsupported 1H unavailable; daily value unchanged; strict JSON serialization succeeds.
- Eleven synthetic measurement controls pass. They cover cancellation, zero denominators, rolling expiry, cohort swaps, overlap, both-down relative strength, actual helper time windows, existing calendar DST/early-close/holiday handling, and feed-delay separation.
- Two exact Terminal pure-function clock round trips pass; four/five-hour false-UTC errors reproduced.
- None of these are a financial backtest, current market-data census, independent review, authenticated browser acceptance or production proof.

Before release: independent exact-head review, required hosted checks, source compatibility and actual consumer/runtime verification. Before the session detector: current minute-history/venue/rights/price-basis/source-delay qualification; its production read remains blocked by the observed SSH authentication failure. Do not change keys or retry that denied path to clear it.

Reproduce locally:
```
python3 -m pytest -q tests/test_sp500_heatmap_intraday_clock.py tests/test_sp500_heatmap_caps.py tests/test_market_heatmap.py
python3 research/rotation_intelligence/intraday_sessions_20261013/measurement_controls.py
```

The first command proves bounded source behavior, the second synthetic arithmetic and helper behavior. Neither installs or runs a production rotation service.

## 11. Recoverable continuation

Current source operation: rotation-intraday-session-research-20261013; branch sol/web-rotation-intraday-session-research-20261013; baseline 7f1e4ede020b53b1d86b39642e9c88f334f0d61a. The publication PR/commit is the immutable carrier of this report and its source/tests. No worker, external notification, automation or production process was started. No effect is unresolved.

Two source-local findings are recorded through the existing Agent OS discovery schema: DSC:HEATMAP-INTRADAY-ROW-COUNT-ALIASES-TIME and DSC:SECTOR-DAILY-STORES-OMIT-OPEN. No approximate WS record is created: the program exists in the canonical program map, while the related Technical Opportunity workstream has a distinct mandate and is not reassigned here.

Do not redo the baseline counterexamples, the 49-test source proof, or the synthetic controls unless the relevant code changes. Do not replace #9134's leadership plan, adopt #9035's October candidate operation, edit #8923's active clock-repair files, open held empirical outputs, or retry the failed production SSH read through another identity/carrier.

The next source step is independent exact-head review and required hosted checks for the bounded heatmap fix. The next product step is opening-anchor/minute-history and source-clock qualification through the existing data owners, followed by one Sector Pulse/Rotation Command producer extension and the existing Terminal consumer. Live acceptance requires a real source-to-screen example; synthetic controls and GitHub publication cannot satisfy it. The broader session-aware rotation product is incomplete.
