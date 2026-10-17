# Defensive nested washouts V12: failure, harvest clocks and re-entry

**Research date: October 12, 2026. Equity data through October 8, 2026. Evaluation begins January 2018.**

This is a continuation of the corrected V11 real-stock study. It does not retest unrelated price-MACD or RSI(2) entry families. All principal entry signals remain the original completed W/2W StochRSI washout followed by the first daily or two-day RSI-MACD-on-RSI bullish cross. The question is whether management can distinguish a failed recovery from ordinary noise without discarding the larger move.

**Conclusion:** there is no universal failure/exit rule in these tests. A two-week-aware harvest retained substantially more return for MCD and WMT than a weekly-only harvest. WM favored the earlier weekly harvest on the inspected history. Tight fixed stops, structural exits and automatic re-entry each introduced significant costs elsewhere. The positive setup evidence from V11 does not establish the optimal holding or risk policy.

This remains exploratory research, not a trading recommendation, calibrated success probability, optimal allocation or production acceptance. The history and some V11 outcomes were already inspected. The slow-clock and re-entry extensions were specified after the first V12 results, not on a fresh blind holdout.

## 1. Data and inherited entry contract

The core five are MCD, WMT, WM, COST and PG. The separate peer panel comprises RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS and KR. The original 2010+ final-vintage adjusted-price snapshots and V11 native-indicator caches were reused, with no new price acquisition and no modification of the original inputs or V11 source.

The research reference is RSI(14), SMA-seeded Wilder smoothing, recursive EMA14 minus EMA60 on RSI, and an EMA5 signal. StochRSI is 14/14/3/3. A weekly K<=20 in the latest three completed weekly bars and a two-week K<=20 in the latest two completed two-week bars, with current two-week K<60, define the long watch. The first fresh lower cross within the original watch supplies the entry at the next daily open. Exact user-chart settings, corporate-action conventions and candle-origin parity are not established.

The primary event comparison retains the same endpoint 126 sessions after the original watch arm. It therefore does NOT hold every delayed entry for 126 days. There are 340 filled event slots across 18 names and two trigger frames: 50 core daily, 50 core two-day, 120 peer daily and 120 peer two-day. These are not independent economic observations. Original skipped/immature watches remain separately recorded.

Prices are adjusted-price proxies, not audited broker/dividend-accounting returns. Costs are 0.05% on entry and exit, applied multiplicatively. Cash earns zero. No taxes, stock borrow, leverage, user portfolio, optimized position size or liquidity model is supplied.

## 2. A deliberately small management family

All entries are fixed. A setup-low reference is the minimum completed daily low from 20 sessions before watch arming through the signal, less one-half of the signal-known daily ATR. It is frozen for the trade; later lower lows cannot move it downward. This numerical definition is a research convention, not an established optimal support measure.

| Policy | Rule |
|---|---|
| HOLD | Hold to the common endpoint; no stop. Reference, not a recommendation. |
| ATR3 | Fixed initial stop three signal-known daily ATR below the actual entry. |
| ATR6 | Fixed initial stop six ATR below entry; matched wider-risk comparator. |
| STRUCTURE_ATR6 | Same six-ATR stop plus a completed daily close below the frozen setup floor; sell next open. |
| STRUCTURE_MOMENTUM_ATR6 | Same six-ATR stop; require BOTH a close below the floor and negative last-completed lower-frame RSI-MACD histogram. |
| STAGED_ATR6 | Same structural/momentum failure; harvest after a NEW completed weekly K>=80 during the trade and a completed weekly K/D bearish cross. |
| SLOW_STAGE_ATR6 | Same failure/risk rule; use a NEW completed two-week K>=80 before the weekly bearish-cross harvest. Same-close arming and rollover are allowed if both are observed at that close. |

Six ATR is not a suggested live stop. It exists to distinguish a rule's incremental contribution from simply allowing more risk than the three-ATR benchmark. Stop width and recommended capital size are different questions.

Opening gaps fill at the open, not a fictional stop price. Entry-day stops are possible. A close-observed failure or harvest fills next open. Post-sale high/low values are excluded; high-before-stop chronology is not invented. These distinctions accord with the general order/fill separation described in TradingView's strategy documentation [1].

## 3. Fixed-entry results: many apparent improvements are just wider stops

Core daily triggers; identical 50 filled events and common arm+126 endpoint:

| Policy | Positive outcomes | Mean net outcome | Mean entry-relative adverse excursion | Worst adverse excursion |
|---|---:|---:|---:|---:|
| HOLD |86.0%|+10.06%|-7.17%|-38.66%|
| ATR3 |50.0%|+5.66%|-4.12%|-10.41%|
| ATR6 |72.0%|+7.68%|-5.50%|-15.85%|
| Structure + ATR6 |60.0%|+6.26%|-4.80%|-15.85%|
| Structure + momentum + ATR6 |64.0%|+6.73%|-4.83%|-15.85%|
| Weekly harvest + ATR6 |64.0%|+4.61%|-3.81%|-11.30%|
| Two-week-aware harvest + ATR6 |66.0%|+6.06%|-4.68%|-15.85%|

The six-ATR comparator retained 2.03 percentage points more average return than three ATR, with worse average adverse excursion. That is partly a wider-risk trade-off, not proof of better prediction.

Structural failure plus negative lower momentum improved average return by 0.46 percentage points relative to price-only structural failure. **Only two of the fifty events changed; 48 were identical.** Removing the most influential stock leaves almost no average contribution. The second indicator is therefore not broad independent confirmation in this sample.

Relative to the matched six-ATR baseline, structure-plus-momentum gave up approximately 0.96 percentage points; its exploratory shared-quarter interval included zero. Weekly harvest gave up 3.07 points on the same event set, while two-week-aware harvest gave up 1.62 points. The slower harvest retained about 1.45 points more than weekly-only, but with worse average adverse excursion. These event averages are not account CAGR or portfolio drawdown.

The peer panel also paid substantial exit costs. No winning-stock-only subset was used to make a rule appear universal.

## 4. Account results reveal different trade opportunities and risks

A second experiment creates one separate fractional-share model account per stock and trigger frame. It admits the original first signals chronologically, holds at most one position, discards signals occurring while busy, and never resurrects a missed signal later. Open sample-end positions stay marked with the eventual exit fee still unpaid. There is no forced annual liquidation. These are research normalizations, not user allocations.

Principal daily-trigger accounts with the 126-session arm cap:

| Stock | Six-ATR baseline CAGR / max drawdown | Weekly-harvest CAGR / max drawdown | Two-week-aware harvest CAGR / max drawdown |
|---|---|---|---|
| MCD |3.46% / -18.32%|2.59% / -14.78%|5.44% / -11.60%|
| WMT |9.90% / -28.53%|4.49% / -13.14%|9.38% / -13.14%|
| WM |10.53% / -26.19%|9.69% / -11.74%|6.43% / -26.19%|
| COST |6.46% / -29.28%|5.14% / -20.09%|5.51% / -29.28%|
| PG |2.79% / -20.27%|0.47% / -19.64%|-0.54% / -21.44%|

CAGR is calendar-time compounded model-account return. Maximum drawdown in this table is close-marked. A conservative intraday-low mark is separately exported. Results are not annualized event averages, and HOLD elsewhere means the selected-entry account, not continuous stock buy-and-hold.

MCD's two-week-aware and structural-only variants merit further examination; WMT's slow harvest retained far more return than weekly-only at the same observed drawdown. WM presents the opposite clock preference. COST and PG do not acquire an attractive universal failure policy from this family.

Selecting those preferences after seeing the table would be strategy selection. They are research candidates, not validated ticker-specific prescriptions. All seven policies and both frames are retained in the source/results, with cost and chronological sensitivities.

## 5. Longer horizon: six months cannot settle a slow-cycle thesis

The additional arm+252 analysis changes only the endpoint/maximum holding window, not entries or numerical indicators. For event comparisons, both horizons use the SAME original observations with a full 252-session outcome available. That leaves 48 core daily events.

On that fixed cohort, mean HOLD outcomes were +10.31% at arm+126 and +18.65% at arm+252. Six-ATR outcomes were +7.84% and +14.14%; structural/momentum outcomes +6.90% and +12.31%; weekly harvest +4.62% and +4.67%; two-week-aware harvest +6.13% and +7.15%. Longer exposure naturally changes expected return; this is not proof that later exits have better risk-adjusted value.

Account examples under the 252-session cap:

- MCD two-week-aware harvest: 8.68% CAGR, -13.05% drawdown, versus six ATR 4.61% and -28.47%.
- WMT structural/momentum, without a harvest: 17.72% CAGR, -17.05% drawdown; two-week-aware harvest 12.29% and -13.97%. The decision is a return/risk/exposure trade-off, not a single best cell.
- WM weekly harvest: 9.69% CAGR, -11.74% drawdown, essentially unchanged because the policy generally exited before either cap. The slower harvest returned 6.87% with -26.19% drawdown.
- COST selected-entry HOLD returned 12.79% with -31.40% drawdown, while several protective versions lost much of that recovery. This is not a recommendation to remove stops.
- PG remained weak under the structural/harvest definitions despite better long-horizon unstopped recoveries.

The account paths can differ markedly from overlapping-event averages: a longer hold can block later entry opportunities. Fixed-event and account results must both remain visible.

## 6. Bounded reclaim: keep the first loss in the arithmetic

A separately frozen exploratory extension permits at most ONE reentry after a STOP or STRUCTURE exit. It requires a fresh lower bullish crossover at least one complete daily decision later and within 20 sessions, a close above the ORIGINAL setup floor, and completed weekly K<80. Execution is next open; the floor remains fixed; the six-ATR stop uses ATR known at the retry decision. Both round trips and the first loss compound into the final result.

Core daily structure/momentum events: only seven reentries qualified. Mean all-event return fell from 6.73% to 6.25%. No losing episode became positive; the one positive improvement began from an already slightly positive first attempt. Weekly-harvest reentries similarly lowered core average return. The peer panel showed a small positive average and eight rescued episodes, so this is not a universal assertion that retries fail.

The sharpest core counterexample is the PG episode with a November 18, 2019 initial signal. After an approximately 9.78% first-attempt loss, a March 4, 2020 retry signal resulted in an approximately 24.46% compounded episode loss under the tested policy. The first loss was NOT deleted. The Fed had announced an emergency half-percentage-point cut on March 3, citing coronavirus risks [3]. That dated fact was available before the retry; it illustrates why a rebound after easing need not mean an ordinary recovered regime. It does not establish a tested emergency-cut veto.

These reclaim results are isolated-watch counterfactuals, NOT a single-position account. Competition from another original watch during the cash waiting interval is unmodeled. No reclaim allocation policy is promoted.

## 7. What the research now supports

The V11 setup condition and V12 exit problem must remain separate. Long washout context can identify promising recovery populations while subsequent management is highly sensitive to stock behavior and changing conditions. A mechanical support break plus negative oscillator is often redundant rather than two independent warnings. A weekly overbought cycle may be a local pause in a still-developing two-week recovery, but waiting for two-week completion is not universally better.

Risk controls need an objective: sacrificing expected return may be worthwhile for lower drawdown, but a lower hit rate does not by itself make a control useless, and a high endpoint hit rate does not make wide/no stops acceptable. The stop-loss literature explicitly treats their effects on expected return and volatility as strategy/process-dependent rather than automatic value addition [2]. Its futures evidence is not validation for these particular stocks.

Prospective priorities are therefore limited hypotheses: test slower recovery management for MCD/WMT; earlier weekly harvest for WM; and keep COST/PG risk design unresolved. Freeze choices before new forward observations. Do not keep optimizing the same history or turn per-name retrospective winners into live model-originated sizes.

## 8. Audit, uncertainty and reproducibility

Thirty-five targeted tests passed. They cover fee arithmetic, next-open decisions, entry-day and gap stops, immutable setup levels, prior-known momentum, completed weekly/two-week freshness, stale overbought rejection, pending sample-end states, busy signals and loss-preserving reentry.

A test exposed a final-day account-state bug: a still-open position could incorrectly report another pending entry on the final bar. It was repaired and its regression passes. This affected state reporting, not a new executed trade. The earlier V12 default event source is retained as a comparison snapshot.

The HOLD replay reconciled to 340 V11 event outcomes with maximum error below 5e-16. Seven hundred final-source core event replays matched their stored outcomes within 1e-16. V11 source hashes remained unchanged. The study produced 2,380 primary event-policy rows, 322 principal/cost account scenarios, 252 longer-horizon account scenarios, 680 reclaim rows and 4,648 matched-horizon rows. These counts are dependent scenarios, NOT independent tests or independent trades.

Paired uncertainty uses the previously tested four-consecutive-calendar-quarter resampler, keeping contemporaneous stocks together. Intervals are descriptive, unadjusted for eight contrasts, per-stock selection and the preceding research history. Leave-year and leave-stock diagnostics are retained. Small sample sizes, overlap, survivor selection, final-vintage adjusted prices, zero cash yield and no broker liquidity/dividend-ledger model remain limitations.

The source package contains code, tests, specifications, derived CSV/JSON and integrity digests, not original vendor OHLC or raw FRED files. Reproduction requires the existing V11 native caches and their original source environment. No denied V3 result-table or V4 earlier-price acquisition was retried. No production indicator, trading, runtime or account permission was changed.

V11 publication PR #9034 remained open at this continuation's read. Its main CI gate passed; no completed review was present. This V12 research does not bypass that review/merge boundary.

## Primary references

[1] TradingView strategies and broker-emulator execution semantics: https://www.tradingview.com/pine-script-docs/concepts/strategies/

[2] Kaminski and Lo, When Do Stop-Loss Rules Stop Losses?, Journal of Financial Markets, 2014. MIT repository: https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee

[3] Federal Reserve, March 3, 2020 policy statement: https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm

V11 exact research precursor: https://github.com/mastermindx-market-intelligence/macro/blob/3fd72eaf53990b88b5073f59f04c37dfba8f7d4b/research/DEFENSIVE_NESTED_V11_EMPIRICAL_2026-10-11.md

## Current result boundary

This V12 historical comparison and source delivery are complete once publication and artifact checks are verified. The broader strategy is not live-qualified. Still required are user-chart parity, point-in-time issuer/consensus and macro vintages, independent vendor checks, a genuinely new frozen forward sample, explicit portfolio risk constraints and observed execution. No automatic background run, accepted merge or calibrated allocation is implied.
