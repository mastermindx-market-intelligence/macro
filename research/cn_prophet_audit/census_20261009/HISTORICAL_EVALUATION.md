# China Prophet historical evaluation — 9 October 2026

## Decision

**The current V4 record has not demonstrated a dependable stock-selection advantage. The evidence supports repairing the evaluation and publication record before promoting a new ranking formula.** A reconstruction using the stored entry latches reproduces 133 benchmark-relative winners out of 289 matured V4 episodes, or **46.02%**, with mean excess **−0.2221 percentage points** over the production H10 window. Its descriptive date-cluster 95% interval is **[−1.2233, +0.6719] percentage points**, over only **21 admission dates**. This does not establish statistically significant underperformance, equivalence to zero alpha, or a future investment return.

Several defects in the evidence are independently demonstrated: the V4 and V3 shadow samples are identical; candidate and board snapshots disagree on some dates; entry re-derivation changes recorded outcomes; issuance records lack publication timestamps; historical features have material missingness; and a missing-price denominator could produce an invalid comparison if not explicitly retained. The attached diagnostics now preserve those limitations and do not replace any production grader, recorded fill, selection algorithm, or existing research carrier.

All source and data are pinned to Macro commit `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The parent supplied the current protected Mastermind procedure pin `326c8469a21d7f50fc9ecb1848196bf1c6e66685`. Inspection used immutable Git objects from `/Users/chriswong/Documents/Cluade/macro-main`; writes were restricted to this analytical directory and the unique remote temporary directory.

Throughout the tables, “CSI300” means the stored **510300.SS ETF proxy**, and “CSI500” means the stored **510500.SS ETF proxy**, rather than the index's own total-return series.

## 1. What history exists

| Instrument | Records | Recorded dates | Important boundary |
|---|---:|---|---|
| Board ledger | 5,108 | 60 dates, 2026-06-30–2026-10-09 | Eight board definitions; never pool them into one performance result |
| Candidate ledger | 67,731 | 42 dates, 2026-07-30–2026-10-09 | V2, V3 and V4; every field is a recorded snapshot, not independently proven first-publication information |
| Entry latch | 1,948 | 59 board dates, 2026-06-30–2026-10-08 | Earliest latch timestamp is 2026-08-10T09:33:21Z; 756 latch rows refer to earlier board dates |
| Ops forward log | 270 | 39 dates, 2026-08-04–2026-10-09 | Definition-specific aggregate telemetry, not 270 independent experiments |
| `cn_prophet_live/forward.parquet` | **0** | None | Schema only; it cannot supply a separate live-performance record |
| Per-name OHLC files inspected | 1,875 | Oldest stored bar 1990-12-19 | Long price histories do not create long point-in-time recommendation histories |

The board record contains 584 legacy episodes, 53 V2, 96 V3, 431 V4, 459 V2-shadow, 431 V3-shadow, 407 V4-more-actionable, and 267 reversal-watch episodes. These use the production `build_episodes` contiguous-membership rule, extracted directly from the pinned source. The historical V2 and V3 samples cover different market dates from V4; their aggregate outcomes cannot establish a causal version improvement.

V4 starts on 2026-08-18 and has 683 board rows, 431 episodes, and 359 distinct tickers through October 9. The public-data header discussed by the parent was as of October 8: excluding October 9's 18 new episodes explains the 413 versus 431 episode count, while the matured count remains 289.

Source: [board ledger](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_standout_track/board.parquet), [candidate ledger](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_prophet_rank/candidates.parquet), [episode construction](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/track_scoring.py#L94-L126).

## 2. Reconcile the outcome instruments before comparing them

### Production H10: latched entry versus current re-derived entry

Both rows below use the same 289 matured V4 episodes and current-at-pin exit closes. They differ only in the stock entry value used.

| Entry treatment | Positive CSI300 excess | Mean excess | Median excess |
|---|---:|---:|---:|
| Stored entry latch | **133/289 = 46.02%** | **−0.2221 pp** | −0.7312 pp |
| Current OHLC re-derivation, matching ops telemetry | **129/289 = 44.64%** | **−0.2131 pp** | −0.7312 pp |

The direction of win/loss changes for **16/289 episodes**; the latch convention has four more winners than current re-derivation after netting opposite sign changes. This exactly explains the superficially inconsistent 46.0% public-data header and 44.64% current ops reconstruction. It is not a rounding discrepancy. Neither calculation retroactively replaces an original recorded entry.

Across all definitions, current re-derivation disagrees with the latch by more than 0.0001% on **933 of 2,632 latch-bearing episode rows**, covering **656 distinct (date, ticker) pairs**. The median absolute discrepancy among changed episode rows is **0.9190%**; 446 exceed 1%, 23 exceed 5%, and the largest is 31.0345%. Definitions can share the same date/ticker, so 933 must not be described as 933 independent trades.

Example: 300803.SZ, board date 2026-07-21, has a latched entry of 83.00 while the current July 22 open is 57.2413788. The current `china_stocks_raw` file also carries that revised value on the inspected dates. This proves a basis/vintage disagreement; it does not establish its corporate-action or vendor cause. A field or directory named “raw” does not independently certify the original entry basis.

The public entry resolver uses latches, while the ops telemetry path and `china_standout_track._fwd_excess` call the current `_t1_fill` path. `grade()` also refreshes outcome columns. Therefore “append-only board” does not imply immutable outcome labels. Source: [entry resolver and forward calculation](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/china_standout_track.py#L1270-L1373), [ops episode telemetry](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/engine/cn_prophet_audit.py#L438-L564).

### Separate matched close-to-close observations

To provide the requested 1/3/5/10/20/60-session view without assuming a benchmark opening price, a second **offline diagnostic** uses the close of the first CSI300 session after the recorded board date as entry, then the close **h benchmark sessions after that entry** as exit. Stock and benchmark require those exact dates. This is a different entry/window definition from production H10, whose tenth stock close includes the entry session. It is not a clock-only repair or a proposed production replacement.

| V4 elapsed sessions after next-session-close entry | Observed episodes | Admission dates | Mean stock return | Mean CSI300 excess | Positive excess | Direct rank IC |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 398 | 28 | −0.0261% | +0.2014 pp | 48.49% | +0.0534 |
| 3 | 365 | 26 | −0.7286% | −0.0223 pp | 45.21% | +0.1561 |
| 5 | 345 | 25 | −0.7807% | +0.2332 pp | 47.54% | +0.1031 |
| 10 | 288 | 21 | −1.3820% | +0.1637 pp | 49.31% | +0.0778 |
| 20 | 158 | 11 | −2.0490% | +1.0607 pp | 46.84% | +0.1043 |
| 60 | 0 | 0 | Unavailable | Unavailable | Unavailable | Unavailable |

**Direct rank IC correlates numerical board rank with subsequent excess: rank 1 is best, so a negative IC is favorable.** The positive estimates above point in the wrong direction, but do not themselves establish a statistically reliable negative ranking effect. These cohorts differ by maturity; the table cannot establish an optimal horizon.

On the **same 158 episodes across 11 dates** that mature through 20 sessions, mean CSI300 excess at 1/3/5/10/20 sessions is respectively **+0.1615, +0.3233, +0.7002, −0.1584, +1.0607 pp**. Every date-cluster interval crosses zero. This common-cohort view also fails to demonstrate dependable horizon superiority.

Using the stored 510500.SS comparator instead of 510300.SS reduces the matched H10 mean excess to **+0.0168 pp**, with **135/288 = 46.875%** positive outcomes and a descriptive interval **[−0.7134, +0.7576] pp**. The corresponding H20 mean is +0.5204 pp. Current constituent information cannot establish a historically size-matched benchmark assignment.

### The benchmark-clock question has an exact missing-data gate

The sole pinned 510300.SS file contains **3,491 rows and only `close` and `volume`**. It has no open/high/low fields. Consequently a same-trade experiment replacing the benchmark entry-session close with a verified opening price has **zero eligible benchmark-open observations**. Its effect cannot be quantified here. HL2 stock entries additionally have no uniquely known intraday entry time.

The −0.2221 pp production result and +0.1637 pp matched diagnostic must never be subtracted and described as “benchmark bias”: entry, holding window and maturity cohort all change.

## 3. Controlled ordering comparisons and negative results

The retrospective baselines use only recorded issuance fields. Their fixed six-name selections are formed **before looking at outcome availability**. A selected name with no usable outcome remains unresolved; another name is never substituted. Baselines retain the existing four-per-sector cap. These are six-name research comparisons, not the complete 24-name board, portfolio allocations, or executable strategies.

The cap-qualified pool contains recorded `featured` rows plus `more_actionable` rows whose sole reason is `featured_cap` or `sector_cap`. Dates with any board/candidate featured-set or score disagreement are quarantined. The comparison also records feature missingness, incomplete outcomes, and unmatched dates.

A tempting broad comparison suggested a reversal advantage: on its own 14 supported dates, reversal top-six averaged +1.6401 pp and exceeded the same-date score selection by +2.2509 pp. However, feature coverage and the date/cohort composition are consequential. On an **identical pool of names with all compared features present**, over **11 common dates and 66 selected observations per arm**, results are:

| Ordering in the common feature-complete pool | Mean CSI300 excess | Delta versus score ordering | Descriptive paired date-cluster 95% interval for delta |
|---|---:|---:|---:|
| Current score | −0.3162 pp | Reference | — |
| Stored intelligence score | −0.5631 pp | −0.2469 pp | [−2.9316, +2.5478] |
| Trailing momentum | −0.0030 pp | +0.3132 pp | [−2.3039, +2.9634] |
| Trailing reversal | +0.5177 pp | +0.8339 pp | [−1.1930, +2.6146] |
| Stored quality z-score | −0.5851 pp | −0.2689 pp | [−3.1329, +2.4673] |

**No stable advantage is demonstrated on this comparable cohort.** This is not proof that the methods have no alpha. The complete-feature cohort is itself conditional on data coverage and does not represent the whole product universe. Reversal and intelligence ordering remain hypotheses for an independently instrumented prospective comparison.

Review found and corrected a future-conditioned selection error in the draft diagnostic. Selecting after filtering to observed returns would have replaced a top-ranked common-feature name on one of 12 candidate dates. The final comparison leaves that selection unresolved and uses 11 complete common dates. The actual featured top-six selections were unaffected across their 17-date diagnostic. Old/new selection counts and affected records are retained in `selection_before_outcome_summary` and `selection_changed_examples`; rejected calculations are not evidence of improvement.

Exact sector/liquidity-matched alternative slots exist for **82/102** top-six slots over 17 dates, with all six slots matchable on **9/17 dates**, excluding the original six and requiring the same recorded sector and 0.5–2 times recorded ADV. This is coverage evidence only: an independent, distinct-name matched-random portfolio was not demonstrated. Equal-weighting the larger eligible pool is not a matched-random control.

## 4. Proven record-integrity problems

1. **The V4/V3-shadow experiment has no distinct treatment.** All **683/683** date/ticker rows, ranks and stored Prophet scores are identical between V4 and V3-shadow. Their identical outcome tables are not independent validation of an intelligence-ordering upgrade.

2. **The candidate and recommendation records disagree.** **39/683 V4 board rows** are not featured in the same-date candidate record: 28 are more-actionable, nine not-raw-eligible, and two late-or-unfillable. There are also **21 score disagreements**. On September 4, all 24 board recommendations disagree with the candidate featured set. The other affected dates are August 26, August 27, September 15 and September 18. A board row cannot safely inherit every candidate feature from a different snapshot just because its date and ticker match.

3. **No original publication timestamp is recorded on the 5,108 board or 67,731 candidate rows.** Date-only clocks cannot prove whether the record was available before an assumed next-session entry. Reachable Git history is shallow; the first locally reachable board/candidate commit is August 23 and cannot independently establish June/July publication chronology. The earlier rows may be legitimate, but that has not been reconstructed from the accessible history.

4. **Missing features materially affect comparisons.** Among the H10 cap-qualified V4 comparison records, quality z-score is present on only 520/784 name observations; intelligence supports 15 of 17 dates and trailing returns support 14 of 17. These denominators include unavailable subsequent outcomes. In the underlying V4 candidate record, `ret_3m` and reversal percentile are entirely null on September 10, 11, 14 and 15. Missing values must not silently become zero, a ticker sort, or a replacement candidate. The final feature-complete comparison resolves this ambiguity only on its smaller supported cohort.

5. **The price denominator needs explicit missing records.** Four tickers lack the inspected per-name OHLC files: 000069.SZ, 600038.SS, 600606.SS and 603899.SS. They contribute 168 candidate records, nine raw-eligible records, and zero cap-qualified records. The final diagnostics include `no_price_file` placeholders for applicable observations. This is an absence in the inspected OHLC substrates, not a claim that no quote exists anywhere. `raw_eligible` has zero nulls in the pinned candidate ledger.

6. **Data age and independent market information are different clocks.** No tested recorded date field exceeds its candidate stamp date, but this is not proof against look-ahead. `signal_bar_asof` is over seven calendar days old on 3,197 rows. `micro_batch_asof` predates the board date on 67,711/67,731 rows; 5,060 of 5,063 rows labeled micro-fresh have an older batch date. These discrepancies need their original clock contracts before they can be classified as accepted lag or false freshness.

7. **Current OHLC consistency and survivorship remain limitations.** There are 597 open-outside-high/low bars in 126,185 stored bars since June 30; no closes fail that range check. 1,864/1,875 inspected names end on October 9; seven stop more than 20 benchmark sessions earlier, and none of those seven is in the current members file. This does not certify delisting retention, terminal recovery proceeds, historical constituents, or absence of survivorship bias. The older W5 claim of zero terminal-stale names is not a current census result.

8. **Dependence is substantial.** V4 changes an average 62.04% of names between recorded board snapshots. Its 431 episodes include 72 readmissions; 53 occur within ten market sessions of the preceding admission for the same issuer. These are not 431 independent trades. Date-cluster intervals retain same-day names together but do not fully correct overlapping horizons, repeat issuers, selection over many experiments, or regime dependence. Of the 288 matched H10 V4 episodes, 269 across 19 dates carry the same recorded own-market label, `Q4`; 19 across two dates have no label. Broad regime adaptation is not tested by that history.

## 5. Four selected extreme candidate autopsies

The script deliberately selects the two largest losses and two largest gains in the current-fill V4 H10 record; these are illustrative extremes, not a representative sample of recommendations. The features below come from matching definition/date/ticker candidate snapshots. They are not independently proven first-publication features. Current bar paths and stored entry latches support the numerical outcomes; no contemporaneous company-event archive was joined here, so no corporate, policy, or news cause is asserted.

| Candidate | Board date and rank | Recorded selection snapshot | Latched entry | Current re-derived entry | Production H10 exit | Latched-entry excess | Current-fill excess |
|---|---|---|---:|---:|---|---:|---:|
| 001896.SZ — 豫能控股 / Henan Yuneng | 2026-09-14, rank 1 | Score 76.73; T1/pending; `bounce_wait`; intelligence score 0; quality −0.61; input bar Sep 11 | 13.0050 | 13.4500 | Sep 29 | −18.5109 pp | −21.1287 pp |
| 301371.SZ — 敷尔佳 / Fuerjia | 2026-08-18, rank 18 | Score 73.42; T1/pending; `bounce_wait`; reversal membership true; trailing 3m −15.8%; intelligence/quality unavailable; input bar Aug 13 | 26.4500 | 26.6800 | Sep 1 | −19.1701 pp | −19.8725 pp |
| 000739.SZ — 普洛药业 / Apeloa | 2026-09-16, rank 21 | Score 54.31; T1/pending; `buy_now`; intelligence 0; quality −0.02; trailing 3m +38.0%; input bar Sep 16 | 22.7000 | 22.5863 | Oct 8 | +23.2434 pp | +23.8482 pp |
| 301216.SZ — 万凯新材 / Wankai | 2026-08-20, rank 16 | Score 75.70; T1/pending; `bounce_wait`; intelligence 43.6; reversal membership true; trailing 3m −38.4%; input bar Aug 18 | 16.6800 | 16.4100 | Sep 3 | +25.2415 pp | +27.2814 pp |

For 001896.SZ, the current stored admission-day return is +9.9915%, followed by a +3.5412% current-derived entry gap, and a −23.4944% stock return under the current-fill H10 calculation. This is a concrete timing and entry-basis case for investigation; it does not establish the applicable legal price limit or that the price path caused all other losses. The large winner at rank 21 and loser at rank 1 illustrate why examples cannot substitute for the full ranking test.

## 6. Existing research that must not be treated as new validation

- The historical feature battery used 407 matured legacy episodes across 12 dates and 186 continuous feature/outcome tests, without multiplicity correction. It reports 34 nominal hits, while 9.3 are expected at a 5% threshold under the global null before accounting for correlated tests. The study itself calls this exploratory evidence. Its strongest feature rows are not permission to fit a new production ranker to the same period.
- The V3 era-retro reports attractive V3-versus-V2 results but explicitly says the rules were fitted on that era, the effective sample is eight dates, memberships and some gates are approximate, and the comparison is close to circular. It cannot validate the current V4 intelligence ordering.
- The W5 reversal record explicitly describes its returns as an upper bound on a survivor-limited substrate. Its post-2024 subperiod has only 29 observations, mean −0.772%, and reported Sharpe −0.97. Do not quote only its full-period positive statistic.
- The separate divergence radar has 50 events on 23 dates, only 44 sector events, and at most six events on a date. Its daily-HAC requirement of six dates with at least ten events per date is unmet: **zero qualifying dates**, and the governor remains dormant. Its provisional pooled IC is not a stock-level Prophet validation. Seventeen events fall on dates absent from the stored CSI300 session calendar; this reinforces the need to distinguish event timestamps from trading-session horizons.

Sources: [feature battery](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/cn_prophet_audit/rank_feature_battery_results.json), [V3 retrospective limitations](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/cn_prophet_audit/V3_ERA_RETRO.md), [W5 stored statistics](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/research/china_alpha/w5/w5a_rederive_stats.json), [radar IC](https://github.com/mastermindx-market-intelligence/macro/blob/3d90aad6d83152dfeeaf8345bc995826ac9d3139/data/china_hub/radar_ic.json).

## 7. Minimum evidence required next

Extend the existing candidate/board/latch owners and the existing R0 safety-replay carrier. Do not create another grader or revive rejected R0 fill-independence claims.

Required evidence is a jointly identified publication snapshot containing exact source/code/schema versions, UTC issue/availability time, board and complete eligible candidate set, input clocks and missingness, and immutable links between candidate, rank and published recommendation. Market data needs original bar vintages, consistent corporate-action basis, benchmark OHLC, historical security and membership status, and explicit terminal/suspension outcomes. Fill records need the actual basis and feasible time; historical latches must never be silently overwritten.

Then freeze comparator membership on pre-outcome information, preserve all unavailable/indeterminate selections, use identical date/sector/liquidity/control populations, reserve untouched chronological periods, and preregister the primary horizon and hypotheses. Prospective shadow comparison must demonstrate an actual difference between treatments. Costs, taxes, slippage, price limits, T+1 constraints and legal exit feasibility must be evaluated on authoritative inputs before any result is called executable.

The present close-only adverse-excursion measure is clamped at zero and uses subsequent closes only. It is not intraday MAE, portfolio maximum drawdown, or a tradeable stop-loss path. A portfolio Sharpe or drawdown would require a defined position/accounting policy that handles overlapping recommendations and verified execution assumptions; none is manufactured here.

## 8. Reproduction and verification

```bash
python3 autopsy.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --out /tmp/mmx-cn-prophet-historical-20261009/results
python3 extend_audit.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --out /tmp/mmx-cn-prophet-historical-20261009/results
python3 verify_diagnostic.py
```

Dependencies: Python, pandas, numpy and pyarrow, plus the pinned Git objects. No production Python module is imported. Reviewed pure functions for episode construction and entry derivation are extracted from the pinned source by AST. No generator, publisher, vendor collection, live ranking or deployment is invoked.

Focused unit checks passed for entry/session ordering, exact matched benchmark subtraction, nonpositive close-based MAE, missing-session refusal, horizon maturity, flat/zero-volume indeterminacy, and frozen selections without outcome-based replacement. Independent local review recomputed the primary 289-row reconciliation and the five-arm, 11-date, 66-selection comparison from the provided row matrices. These checks validate the reported arithmetic and scope; they do not validate alpha or recover missing publication evidence.

Final data and code hashes are in `SOURCE_MANIFEST.json`. `historical_evidence.json` contains every definition/horizon result, coverage and negative experiment; `v4_review_rows.json` supplies column/data matrices for independent recomputation; `selected_case_records.json` carries all four case records and their horizon observations. The full intermediate CSVs remain reproducible in the unique remote analytical output directory. No shared repository source, production data, recorded fills, rankings, configuration or deployment was changed.
