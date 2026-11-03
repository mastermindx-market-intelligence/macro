# Ownership, recovery timing, and risk geometry — frozen continuation

Date: 2026-10-21. Status: exploratory research; the motivating histories and prior results have already been inspected. This registration limits new researcher discretion. It does not create an untouched holdout or correct historical selection.

## Questions and falsifiers

1. Does the defensive V11 nested context improve entry outcomes beyond owning the same selected businesses at comparable times? A weak same-asset increment, or an advantage confined to the original five names, contradicts a general timing claim.
2. Does a usable capital policy preserve the attractive event statistics? Idle cash, overlapping opportunities, mark-to-market losses, and skipped signals are part of the outcome.
3. Does a fixed 3-ATR stop frequently sit above the price low motivating the setup, and does it stop eventual winners before that low breaks? Compare the same diagnostic on ordinary entries. This diagnoses a mismatch; it does not authorize a wider stop.
4. Does the favorable sector-RSI subgroup select sectors, or mainly select dates on which diversified market exposure recovers? Use the same accepted dates, holding intervals, and sleeve capital for selected-sector, equal-sector-basket, and SPY alternatives.

## Inputs and populations

The defensive universe is the original V11 list, frozen without additions or deletions: core MCD, WMT, WM, COST, PG; peers RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS, KR. All are surviving, retrospectively selected securities, not a point-in-time defensive universe. SPY is a market comparator. The original V11 archive is SHA256 `97966f72ea15cb34e0f5453252eef683411c894b7ca4432de4ce7c540d1ffaf0`. Its documented temporary raw-input paths are absent at continuation; any re-created price calculation must be identified as a new current-vintage reconstruction, not byte-identical original-input replication. Reuse verified retained October-21 public Yahoo inputs where available. Any additional public inputs are separately receipted, have no credential use, and stop at 2026-10-08. No production source or feed changes.

Defensive features start with 2010-01-04 history to preserve V11 warmup. Evaluation is 2018-01-01 through 2026-10-08, with descriptive splits 2018–2022 and 2023–cutoff. Comparisons requiring a complete 126-session outcome exclude immature events, retain their count, and do not use an outcome beyond a split boundary.

Sector universe: XLK, XLF, XLE, XLI, XLY, XLP, XLU, XLV, XLB, XLRE, XLC, SOXX. The event input is the already published daily RSI30-recovery roster from `entry_mechanisms_20261021`; do not recompute or select a new threshold. Primary capital evaluation is 2020-01-01 through 2026-10-08, when all 12 have history. It is a post-selection follow-up, not independent confirmation.

Keep raw public input bytes private, with source URL, acquisition time, content hashes, adjusted-close factors, and corporate-action limitations. No private earnings/transcript corpus is published. Missing fields stay unknown. Do not synthesize an open price from a close-only store. Source absence in one binding is not global absence.

## Defensive signal reconstruction

Reuse the archived V11 `NativeState`, completed-candle aggregation, and episode mechanics. RSI14 uses the archived SMA-seeded Wilder recurrence. RSI-MACD is EMA14(RSI) minus EMA60(RSI), with EMA5 signal; bullish cross means its histogram crosses from nonpositive to positive. This is not ordinary price MACD.

Stoch RSI is 14/14/3/3 on the adjusted price proxy. W condition: K <=20 in the last three completed weekly bars. 2W condition: K <=20 in the last two completed two-week bars and current K <60. Both native counts must reach 200. Week origin is 2000-01-03; 2W phase zero. Only completed bars may update state; known future session-calendar dates identify completion without supplying future prices.

Classify every eligible daily bullish crossover as JOINT, WEEKLY_ONLY, TWO_WEEK_ONLY, or NEITHER. Preserve all classes, not just favorable ones. Entry is next session's open; endpoint is signal index +126, inclusive. Compare reconstructed event dates and returns with the archived Study A ledger, reporting unmatched dates and deviations rather than silently forcing parity.

Also preserve V11 watches: joint context, maximum 42 daily decisions, clearance at 2W K >=60, and 10 clear decisions before rearming. Classify joint crosses as first or repeated within a watch, or outside an active watch; this is a diagnostic stratum, not a return-selected entry replacement. Reconcile the archived context-cross and first-watch cohorts without treating their 74 and 50 observations as the same population.

## Event attribution and uncertainty

Primary returns use adjusted OHLC as a dividend-return proxy, with 5bp each side as in V11. Same-entry price-only returns and 25bp each-side friction are sensitivities. Adjusted-price paths do not supply an exact cash-dividend/pay-date ledger or historical corporate-action vintage.

Ordinary-date comparator: same asset, calendar half-year, own close above/below its 200-session average, and SPY above/below its 200-session average. Remove the focal date; require at least 10 other complete outcomes in the same period. Report unmatched events and coverage. These are retrospective descriptive controls, not causal or executable matched trades.

Same-date comparators: equal-weight other core names; equal-weight peer names excluding the focal name if relevant; and SPY. Require at least two available names for a basket. Report raw returns, positive fraction, positive excess fraction, mean paired difference, and distinct signal dates. Compare the core timing increment with the peer increment; do not interpret that interaction as a causal estimate of business quality.

For uncertainty, resample the entire cross-section jointly in consecutive two-half-year circular calendar blocks, 2,000 draws, seed 20261021. Preserve empty half-years. Report pointwise 95% intervals, not multiplicity-adjusted significance. Show equal-signal-date weighting, per-stock/year influence, and chronological splits without refitting. History, cohort selection, and new diagnostic multiplicity remain limitations.

## Frozen-low and stop diagnostics

For each crossover or ordinary entry, freeze L = lowest adjusted low in the 63 sessions through signal close, and A = signal-close Wilder ATR14. Record reference age, entry distance (E−L)/A, and whether the fixed stop E−3A lies above L. The reference is an observable candidate low, not a retrospectively confirmed durable bottom.

Include the entry session in stop evaluation. A gap through a stop fills at min(open, stop). Preserve the same predetermined endpoint and no replacement entry after a stop. A stop is demonstrably above an intact reference only if every low through the stop day remains above L; if both levels are touched that day, their intraday ordering is unknown. Record future reference breaks separately, eventual positive outcomes converted to stopped losses, and losses avoided on eventual losers. Compare the same quantities on ordinary entries. No tuned stop width or target is introduced.

## Defensive capital policies

For each cohort, give every stock an equal initial capital sleeve. Capital cannot move between sleeves; there is no leverage or borrowing. Evaluate:

1. Continuous ownership from the common first tradable session.
2. Every eligible daily RSI-MACD bullish crossover, fixed 126-session endpoint.
3. Only joint-context daily crossovers, same fixed endpoint.
4. Exactly policy 3's accepted entry roster with a fixed initial 3-ATR stop. After an early stop, the sleeve stays in cash until its original scheduled endpoint.

One active scheduled interval per stock; ignore subsequent signals during it and retain their count. Filtering can change the accepted roster between policies 2 and 3; the event audit supplies the separate same-roster information comparison. No outcome-based entry replacement. A new signal on a scheduled exit close can nominate the following open. Open cutoff positions remain marked to market; immature entries remain in the capital path. Costs are assessed on actual entry/exit, and terminal wealth includes a liquidation-fee adjustment for unsold holdings. Show zero-cash-yield primary results and one declared constant 3%-annual cash scenario, which is a scenario, not realized Treasury performance.

Report terminal wealth, CAGR, maximum close-marked drawdown, annualized volatility, time under water, average invested fraction, gross turnover, accepted/rejected entries, closed-trade hit rate, open-position count, and annual returns. Do not infer a stable investment win probability from either event or account summaries.

## Sector capital and common-date experiment

Use 12 equal initial sleeves, one per nominating ETF, and accept that ETF's first published RSI30-recovery event when its sleeve is free. Hold through signal+63; exclude new events while that scheduled interval is occupied. For identical accepted events and sleeve occupancy compare:

- selected ETF;
- equal initial shares-value basket of all 12 sectors at that same next open, held without rebalancing to the same endpoint;
- SPY at that next open and endpoint;
- selected ETF with 3-ATR stop, cash through its original scheduled endpoint.

Continuous equal-sleeve ownership is a reference. Primary sector costs remain 10bp each side as in the prior study; 25bp each side is a stress. Use the same cash scenarios and complete capital accounting as defensive policies. For same-date event comparisons, additionally exclude the focal ETF from its peer basket so the information diagnostic does not partly compare an asset with itself. Capital comparisons deliberately use the whole 12-ETF basket as an executable alternative.

## Information mechanism and qualitative work

Audit the actually retained earnings and fundamental schemas and their availability clocks. Current snapshots, fiscal dates, and Item2.02 filing dates are not automatically archived consensus or original publication times. A presently stored surprise can motivate future research but cannot be backdated into a historically knowable signal.

Primary-source case analysis may investigate original issuer guidance revisions as an alternative to unavailable historical consensus: same fiscal year, metric, accounting basis, and previous published range. Distinguish an issuer-outlook revision from a consensus surprise. Any outcome-stratified cases are diagnostic, not prevalence estimates. Publish exact source dates and what was knowable by the decision time. No news-retrieval absence is coded as no news.

## Acceptance and scope

Verify completed-bar chronology, original-archive signal parity where data permit, next-open execution, stop gaps/entry-day ordering, shared entry roster, no capital reuse before scheduled release, daily account identities, and terminal open-position treatment. Review decisive code and counterexamples independently. Publish adverse results and source limitations. All output is research; there is no live signal, ranking, sizing, broker action, deployment, or new data service.
