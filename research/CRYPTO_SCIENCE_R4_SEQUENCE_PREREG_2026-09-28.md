# Crypto science R4 — frozen breakdown/reclaim experiment and implementation plan

**Goal:** test two transparent observable price-sequence hypotheses against simple and corrected-incumbent comparators, with explicit execution delays and costs. This is the first R4 experiment, not another repair of R1–R3 and not a deployable strategy.
**Architecture:** bounded offline research functions under existing research/crypto_science; reuse incumbent compute_all and stored Coinbase data. Existing Vector test owner tests pure research functions. No live engine/config/gate/alert/forecast-owner changes.
**Tech:** installed Python/pandas/NumPy and existing pytest.
**Spec:** R3 results/frontier at 017d3866eace58c4587bd7d2dc07a9320450bd77; Chairman explicitly says continue.

## Authority, sources and scope

Protected Mastermind: c719d1ec6dfffa278103134b5d719e1c1e672256; INDEX94d1af402598894372858793a5b1931019c5fa77; compatible1.0.1/bootstrap1; ACTIVE_EXECUTION, WEB_CEO_DELEGATION, CLOSEOUT loaded from same pin. Existing operation crypto-vector-r2-20260926-sol-001, PR8050, M2 Studio Direct sparse workspace; clean local/origin at017d3866. Direct work is PRINCIPAL_JUDGMENT: label, causal timing, counterfactual loss function and interpretation are coupled. No worker/reviewer commissioned or live policy accepted.

Observed main8f9995002da9e1c456c8dfa08c9b34292f5020df. #8050 is draft and currently mergeable=false; no merge/rebase attempted. R4 creates unique research paths and appends tests to the incumbent falsifier suite; it does not resolve unrelated merge conflicts or overwrite engine files. Bounded open-PR metadata found8050,7645 and7274 relevant;7274's exact changed paths are separate Terminal tactical research/tests (plus CI), so no R4 path collision. #7645 templates and #7849 themes stay untouched. Existing HTTP fixture servers are read-only and left alone; no active research writer was observed.

Prior knowledge before freeze: R1/R2 timing bugs repaired; R3 revealed weak/noisy current impulse evidence and delay sensitivity. BTC hourly metadata94063rows from2016-01-01; daily4087rows from2015-07-20; both currently end2026-09-26, hourly only through13:00. Metadata check found ordered unique dates and no OHLC-envelope violations; it did not compute this experiment's outcomes. No new outcome aggregate or parameter search precedes this plan commit.

## Exact data-time contract

Use only stored Coinbase BTC-USD OHLC for new price features, not the Yahoo splice, provider-derived funding or synthetic aggressor flow. Source index is bucket START. A bar at t becomes usable at t+duration, never at its opening timestamp. Coinbase official documentation confirms time=start, close=last trade and possible gaps: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles . Documentation was reviewed; no market API or account call is authorized here.

Daily signals use completed24h bars. Hourly feature windows require every calendar hour, finite positive OHLC and valid high/low enclosure. Missing hours/days remain missing. No interpolation, forward-fill of prices, nearest-time fills or selection of profitable data sources. Run all available source-observed dates starting2016-01-01; full and fixed slices2016–2019,2020–2023,and reused2024+ are reported. These periods are retrospective, not untouched holdouts. Period assignment follows the parent signal time; exclude endpoints crossing that slice's end from its mature comparisons and disclose censoring.

Issue time is the completed signal bar's end. Execution scenarios are issue+1h (primary) and issue+6h (sensitivity), using the stored hourly OPEN exactly at that timestamp. There is no zero-latency fill at the signal close. These are assumptions, not measured provider/order latency. Whole required future windows must be complete to score; censored/missing cases stay recorded and do not become failures. For first-passage targets, check opening gaps before each bar's high/low. If both barriers are touched inside one bar without known order, mark AMBIGUOUS; do not award a favorable order. Report conservative success treating ambiguous as non-success and the ambiguous count separately. An event label is not a stop-order fill.

## H-D: observable breakdown plus shock, next24h continuation

D0 baseline: completed hourly close < minimum LOW of the preceding72 completed hours (exclude current bar).
D1 hypothesis: D0 AND current simple one-hour return <= -2 times sample standard deviation(ddof1) of the previous24 one-hour returns (exclude current return). Require positive finite sigma and complete74-hour input history for comparable D0/D1 cohorts. No thresholds are fitted.

Detect observed False→True onsets; first-observed positive after a gap is not an onset. Select the earliest onset strictly more than24h after the previously selected one, independently for D0/D1; preserve every excluded/onset/unknown count. All filters depend only on past data. Score24h from execution: -5% downside barrier reached before+3% upside barrier. Report downside-first, upside-first, ambiguous, neither and censored; worst/best excursion and terminal return. Also disclose how much price already fell in the preceding24h: this tests continuation after an observable breakdown, not pre-crash omniscience.

Marginal protective-policy experiment on the exact same24h window: start with the corrected incumbent exposure available under the same delayed daily publication convention; compare following its subsequent recorded target path versus holding cash for24h and restoring its terminal target. This is an event-level policy counterfactual, not a compound whole-portfolio backtest. Also compare constant full BTC and constant initial-incumbent-exposure references. Include all episodes with complete price and known incumbent targets, including initially zero exposure; separately identify positive-entry-exposure episodes. Never claim a new strategy's performance from conditional event returns.

## H-U: washout then observed stabilization/reclaim

Parent washout W: completed daily close / close five calendar days earlier -1 <= -10%, requiring complete valid six-day prices and enough known features. Take observed False→True onsets, spaced strictly more than14days to avoid overlap of the common parent windows. No future low is used to choose the washout date.

U0 immediate baseline: full research unit of BTC at washout issue+delay.
U1 candidate: within the next seven completed daily bars, take the FIRST day satisfying all three: two consecutive nonlower daily lows(low[t]>=low[t-1]>=low[t-2]); close[t]>high[t-1]; close[t]>the current-and-previous-four-day mean close. The five-day mean, two lows and prior high are fixed conventional baselines, not optimized. Confirmation may not occur: preserve that parent as NO_ENTRY, not delete it. Any missing intervening daily observation makes the confirmation path unknown; do not jump across it to find a later favorable reclaim.

Grade executed entry's next168h: +5% before-3%, same ambiguity/maturity rules as H-D. Also evaluate every parent on a COMMON terminal timestamp: washout execution+336h. Compare immediate full BTC, wait-then-full-BTC, cash and corrected incumbent from that parent entry through the common endpoint. All research paths begin in cash and liquidate at the common endpoint, with costs. NO_ENTRY retains cash. This intention-to-treat comparison prevents selecting only successful/confirmed survivors.

Add an explicitly EX_POST exposure-duration-matched immediate reference: constant starting BTC fraction=(common_end-confirmed_entry)/336h, or0 for no entry. It is a diagnostic control that uses realized waiting time and is NOT an executable strategy available at washout. Its role is to distinguish timing benefit from simply taking less risk. Report it under that label, never as causal policy.

## Accounting, baselines and no optimization

Recompute the corrected incumbent once via existing btc_inputs.load_all/ btc_signals.compute_all with store.read cached and store.upsert refused, exactly as R2. Do not rebuild historical P0A receipt provenance; the frame is a current stored-vintage counterfactual. Daily target indexed date d is available no earlier than d+1day+scenario delay. On hourly schedule use latest such target only within its next24h validity interval; missing targets make incumbent comparisons unknown, not0/cash. No funding augmentation, annualization change or flow extension in R4.

Account initialized with wealth1 and stated initial exposure. Trades occur only when requested target changes (not every hour to force constant mix); between changes holdings drift with price. Charge cost * absolute change in portfolio weight on pretrade wealth, then set target fraction on after-cost wealth; this is declared proportional-cost bookkeeping, not exchange execution proof. At terminal close/restore, charge corresponding liquidation/restoration cost. Costs0/10/25bp one-way, all retained; zero cash yield, no leverage/shorting, no market-impact claim. Include mark-to-market trough and terminal return; do not annualize isolated events or multiply them as if one portfolio. Intrabar risk extrema are reported separately from hourly-open account drawdown.

Raw/final incumbent targets, simple references and candidates use the same source execution prices/windows where comparable. Baseline missingness is separate from price-signal eligibility. No slippage-optimized fills, funding history merge, probability calibration or statistical promotion. Candidate conclusions can be rejected, insufficient or worth further testing; no PASS as a live strategy in this experiment.

## Statistical reporting fixed before outcomes

Save every selected episode, missing-window reason, confirmation/no-entry, issue/entry/terminal times, barrier category, pre-signal move, costed counterfactuals and unmatched cases. Summary by full and three fixed periods, both delays and three costs; no outcome-dependent subgroup construction. For recoveries, pair differences at common parent endpoints. For downside, compare both independently selected D0/D1 sets; report their overlap, not a fake paired test of different events.

Uncertainty:90-calendar-day block bootstrap of event records,1000replicates,seed20260928, for hit fractions and paired mean wealth differences. With fewer than two event-bearing blocks, withhold intervals. Intervals are retrospective diagnostics under one dependence assumption, not current-event probabilities or multiple-testing-adjusted evidence. Report per-year counts and omit-one-calendar-year paired means as robustness, not an optimization. No p-value acceptance gate. The primary directional hypotheses are that shock confirmation improves downside discrimination and that recovery confirmation improves common-endpoint net outcome without destroying recovery participation; report contrary findings fully.

## Files, implementation and verification

- New research/crypto_science/r4_sequence_study.py: pure feature/onset, barrier, confirmation, accounting and fixed study runner.
- New research/crypto_science/r4/: derived JSON/CSV, logs, source/input/output hashes, verification, interpretation. No raw market data publication.
- Existing tests/test_btc_impulse_falsifier.py: synthetic contract tests importing the research functions, enrolled already by existing Vector CI command. Do not touch shared CI or Terminal7274 tests.
- Existing Agent OS decision/workstream: cumulative progress and exact continuation; no new lifecycle/memory store.

Task1 RED/GREEN: completed-bar features/prefix invariance/gaps/onsets; exact delayed entry; first-passage upper/lower/ambiguous/opening gap/censored cases; confirmation cannot look beyond the chosen date or skip missing days; no-entry retained; fee/wealth/holdings conservation and exposure-drift toy cases. Tests before implementation.
Task2: commit source/plan before market outcome execution. Run one frozen study on pinned stored data, cache/hash every input and protected gate/source before/after; reuse actual corrected incumbent, no external writes.
Task3: independent arithmetic/evidence checks over every result and all scenario keys; combined existing tests; compile/diff checks; verify no engine/config/data/gate changes and original R1–R3 evidence intact. Correct implementation defects if they violate the frozen specification, retaining original results/amendment receipts; do not tune hypotheses based on outcomes.
Task4: publish decision-ready results and exact source refs with readback. Independent code/science review remains owed before any policy promotion. A disappointing hypothesis is useful progress if it resolves this named question; do not loop over arbitrary parameters to make it green.

## Deferred/non-goals and continuation boundary

Funding semantics, provider historical release/vintages, independent review, live integration and parent UI remain open. True-flow extension will use only supported actual history in a later preregistration, not hidden inside the price-only study. No new orders, alerts, forecasts, collectors, paid calls, Paper edits, merge/deployment or recurring execution. Complete the two frozen comparisons plus interpretation; the next unit depends on these results rather than another denominator audit.
