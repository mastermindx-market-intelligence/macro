# Defensive Nested Washouts V21–V23: Dated Paper Watches and Incremental Slow-Context Research
**Research completed October 13, 2026. Historical equity cutoff October 8, 2026. No current trading signal, order or allocation.**

## Purpose and connection to earlier findings

The V11 W/2W StochRSI washout combined with shorter RSI-MACD-on-RSI bullish crossover was a useful historical *recovery-context feature* for MCD/WMT/WM/COST/PG, not an established universal high-return trading policy. V13–V20 showed idle capital, execution-clock bias, modest same-date stock-selection alpha, unexceptional first-cross timing, and possible additional beta-neutral relative recovery in sessions20–63. This stage addresses the actual next two needs: **a causal dated watch ledger** and **the incremental value of requiring both W and 2W washouts rather than either alone on all eligible lower crosses**.

Publication lineage: [V11 merged #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034), [separately owned V12 PR #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064), and [V13–V20 review PR #9129](https://github.com/mastermindx-market-intelligence/macro/pull/9129). The current work uses the previously accepted V12 2010–October8 2026 same-window adjusted-price snapshot, not a new vendor or proprietary original OHLC redistribution. The two recent comparison cohorts are **not untouched**: nearly all history has been previously inspected, and outcomes overlap.

## Method contract

Indicator conventions: native RSI14 with Wilder smoothing, RSI-MACD EMA14(RSI)-EMA60(RSI) with EMA5 signal, and StochRSI14/14/3/3. Exact user-chart species, source adjustment convention, 2W phase and developing-bar parity have **not** been independently proved.

Primary long watch: W K<=20 within the latest3 completed weekly native candles AND 2W K<=20 within latest2 completed two-week candles (2W K<60); native warmup200 W and2W bars, watch42 daily observations, reset after10 clear sessions, one first fresh completed1D/2D bullish RSI-MACD cross. Signal known at completion, modeled entry only at following open. See original V11 source, retained without changes.

For signal-condition analysis, define four **mutually exclusive observed categories at the same completed lower crossover**: JOINT, WEEKLY_ONLY, TWO_WEEK_ONLY and NEITHER. This state-at-cross design is **not** identical to a persistent watch followed by a delayed cross; it uses all eligible 1D/2D crosses with full prior context and outcome data.

The specific intermediate recovery outcome is **selected-stock residual logarithmic return during the 20th-to-63rd owned-session close interval**, relative to the equal-weight corresponding residual of its four original core peers (or twelve other peer-panel companies). Per-name market beta is estimated from **252 completed daily return pairs ending before signal** with at least200 finite observations; no future beta or regime labels are used for entry. Outcomes after signal are solely evaluation labels, not decisions to trade at their realized extrema.

## V21 — dated watch ledger (NOT live)

All 18 named stock daily and two-day watcher states were reconstructed as-of **Thursday October8, 2026**, using complete/native W+2W candles and a separate developing-bar sensitivity. All **396 original V12 watch arms and first cross indices exactly reconciled**. Native session count was 4,217; the ledger comprises72 symbol/frame/mode rows. Nothing from October9–13 is in the price inputs; publication on October13 cannot backdate this as an October8 prospective freeze.

Confirmed W/2W as of that stale October8 dataset:

| Frame | Final-bar cross with next open UNOBSERVED | Active but untriggered | Already signaled earlier in active watch | No active watch |
|---|---:|---:|---:|---:|
| Daily | 2 | 0 | 4 | 12 |
| Two-day | 0 | 3 | 3 | 12 |

The two daily **historical** last-bar cross labels were **MCD and PEP**, both dated October8. Their following opens are not available from this price snapshot, and no fill or current state is claimed. The historical two-day untriggered names were **MCD, PEP and HSY**. WM's active watch had already seen crosses on earlier days; it is not a fresh new order. A developing higher-frame convention changed final watch labels for **CLX and COST**, emphasizing native period alignment and real-time chart parity.

All watch rows carry dataset cutoff, as-of timestamp, final K values, signal date, explicit fill-observed marker, and a warning that the published report is **stale for contemporary trading**. This document gives no buy/sell/size instruction.

## V22 — all eligible lower crossovers, not only one per long washout

Source: V11's already accepted **2,771 all-crossover event ledger** (2018+ source window). Both 1D and 2D sources are analyzed; episodes overlap and are not independent. All of them were evaluated over exactly the same 20-to-63 owned-session beta-adjusted residual window. Core5 and peers13 are separate; their underlying businesses are not treated as exchangeable.

| Group and trigger | JOINT W+2W mean | NEITHER mean | Joint-minus-neither |
|---|---:|---:|---:|
| **Core five / daily** | **+1.56%**, 74 events | +0.16%, 308 | **+1.39 percentage points** |
| Core five / 2D | +1.54%, 65 | +0.69%, 120 | +0.85 points |
| Other 13 / daily | +0.03%, 218 | +0.04%, 771 | -0.01 points |
| Other 13 / 2D | -0.33%, 181 | +0.33%, 308 | -0.65 points |

Unit is **percentage points of logarithmic beta-adjusted selected-minus-panel-peer return**, not portfolio CAGR or success probability. The core daily joint-versus-neither four-quarter-block descriptive interval is approximately **-0.40 to +3.04 points**, including zero. A matched stock-year comparison retains31 strata and yields ~+0.99 points; these are not causal estimates. The peer groups do not replicate the overall core effect.

Two-week-only context tells a different story than in the original six-month holding analysis. Over the slower 20-to-63-session residual interval, **core daily TWO_WEEK_ONLY mean was -0.75%** over48 events and WEEKLY_ONLY +0.10% over84, against JOINT +1.56%. In PEERS13 daily, TWO_WEEK_ONLY instead averaged **+1.86%**, substantially above JOINT +0.03%. These contradictory patterns prevent a universal indicator gate.

## V23 — isolate the incremental WEEKLY washout condition

Compare JOINT against TWO_WEEK_ONLY **at the same family of completed daily crossovers**, preserving the original four-state group distinctions. No parameters, dates, names or outcomes were optimized here; these are still posthoc comparisons from repeatedly inspected history.

| Cohort / daily RSI-MACD | JOINT minus TWO_WEEK_ONLY intermediate beta-adjusted excess | Four-quarter-block exploratory interval |
|---|---:|---:|
| **Five core compounders** | **+2.31pp** | **+0.22 to +4.74pp** |
| Thirteen other stocks | **-1.83pp** | -3.72 to +0.25pp |

Within the core panel, a common **stock+year** contrast uses only16 matched strata and averages +2.32pp. A stock+year+entry-market-state subset uses15 and averages +2.28pp. The outside peer panel has the **opposite conditional effect**: -2.43pp across50 matched stock-year strata. These are stratified descriptions, not randomized treatment effects.

Compared with WEEKLY_ONLY the core daily point effect is +1.46pp, but its exploratory interval crosses zero. Compared with NEITHER the core daily point effect is +1.39pp, also with interval crossing zero. Core 2D and other cross-sectional strata remain nonindependent secondary views.

Most importantly, **a positive lower confidence bound in one retrospectively compared group is not selection-adjusted proof**. Thousands of earlier policy comparisons, reused evaluation years, nonrandom survivor stocks and arbitrary category aggregation can generate apparent significance. The result is a precisely specified new *hypothesis*, not an investable execution rule.

## What these findings mean

The technically interesting claim is no longer just that oversold stocks go up. The discriminating conjecture is:

> **In a subset of fundamentally resilient compounders, both weekly and two-week relative momentum exhaustion may identify a recovering *relative* return process over weeks four–thirteen better than either two-week washout alone. That relationship does not appear uniform across other defensive businesses.**

The opposite effect in peers could arise from operating economics, market-beta/industry exposures, differing factor sensitivity, events, prices or chance; these tests do **not** identify which. Do not fit ticker-specific filters to this same inspected history.

The next useful economic investigation should use **pre-signal point-in-time** issuer factors: guidance revision timing, recurring-unit demand versus nominal price/FX, customer volumes and ticket, margin outlook, cash yield/valuation multiples, effective commodity cost lag and issuer-specific M&A status. Rates should separate real yields from credit widening and distinguish stress level from stress direction. Entire contemporaneous recovery episodes should be clustered; missing or revised fundamental history should be UNKNOWN rather than retrospective confirmation.

For a true qualification, separately verify live TradingView indicator species/2W calendar/developing bars, independent OHLC/adjustment vendor, genuine untouched later market periods, trade fills/slippage, and portfolio opportunity cost. Start a timestamped **paper-only** observation ledger at the time it is actually frozen; do not claim the October8 reconstruction was prospective.

## Verification and state

- V21: **7 passing mechanical tests**, 396/396 confirmed primary watch arms and first signal positions equal to accepted V12;18 stocks ×2 frames ×2 long-bar modes =72 dated rows.
- V22: **8 passing tests**, all2,771 original eligible daily/2D crossovers represented; ex-ante beta series checked against the direct scalar calculator and future-perturbation invariance.
- V23: **6 additional tests**, 12 descriptive two-panel/two-frame/three-control contrasts, missing matches retained as absent rather than filled zeros.
- No new original vendor bars, no refusals rerun, no trading, production source mutation or calculated live capital sizes.
- Preserve existing V11, V12 and V13–20 evidence, their hashes and independent owners. There is **no accepted live alpha/entry filter** yet.

**Research status: empirical evidence expanded; production and prospective qualification remain UNPROVEN.**
