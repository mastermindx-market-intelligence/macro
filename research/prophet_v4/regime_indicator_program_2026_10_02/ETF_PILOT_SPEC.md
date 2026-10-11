# Fixed ETF mechanism pilot -- pre-analysis specification

Status: EXPLORATORY / RETROSPECTIVE / NO PRODUCTION AUTHORITY. This is a bounded sanity test of the proposed market mechanism, not a Prophet replay, a registered production trial, or a replacement for R1-R4 qualification. Freeze this file before the pilot outcome calculation. Save every result, including nulls; do not pick the best rule afterward.

## Question and scope

Does prior-session rising-real-yield plus weak equal-weight participation coincide with worse forward outcomes after slow momentum crosses, and is that difference more adverse for 3D than 1D? A broad ETF test cannot establish stock/theme selection alpha or explain individual Prophet losses. It can reject an overly universal timeframe story and expose sample/implementation problems before a larger experiment.

The input is an immutable SAVED Git snapshot, macro `b4f95f98ef80b8cbb4636afbd723b5091658e1f1`. A saved adjusted-price/current-vintage historical series is not a contemporaneous capture, a full-vintage macro panel or proof of delivered recommendations. Outcome columns from Prophet, Phase-21, Phase-22, W3 and subtheme replay are out of scope; do not read them. No external data collection, credential use, held-outcome access, model fit, policy/ranker change or deployment.

## Frozen inputs

Candidate instruments: QQQ, IWM and SOXX. SPY is the market benchmark and calendar-grid diagnostic. RSP is only a participation proxy. This fixed small, survivor-selected ETF panel does not represent the historical stock universe or all sectors; SOXX is not a point-in-time AI theme basket.

Read only `data/yahoo/{SPY,RSP,QQQ,IWM,SOXX}.parquet`, `data/fred/DFII10.parquet`, and the exact owner source needed for the primitive/calendar calculations. Hash the buffers. Print column, date, missingness and common-support coverage. If essential fields or suitable data are missing, report that instrument/period as unavailable; do not switch symbols or data providers to improve the result.

Use the existing source's US session anchor and aggregation functions. Do not change production or re-anchor the frozen oracle. No intraday/12H result may be manufactured from daily data.

## Fixed policies, not a pure-grain experiment

Families are evaluated separately:

1. Raw price MACD histogram, the native `engine.technicals.macd_hist` 12/26/9 definition.
2. Raw RSI-MACD histogram, the native `engine.confluence_tiers._rsi_macd` definition: RSI14, EMA14 minus EMA60, signal EMA5.

A bullish event is histogram > 0 after a finite prior histogram <= 0. Warm-up/NaN values cannot fire. Daily, 2-session, 3-session and completed weekly bars are considered where the existing owner functions can be reused and audited. A missing owner-qualified weekly function is an explicit omission, not an excuse to invent a new weekly clock.

This is a comparison of NATIVE-PARAMETER SIGNAL POLICIES. Changing bar size changes filter memory. Do not describe any result as the isolated causal effect of timeframe. These raw events are not the validated signal_quality/signal_gate take policy, Conditional Fusion ranking or live provisional board.

Calculate on full available history for warm-up and then restrict events. Use COMPLETED buckets; a finalized-history raw event must not be presented as the exact observation of a historical live provisional decision. Preserve the unchanged live owner rules.

## Regime, outcome, and periods

At the signal close, use inputs ending one prior SPY session:
- real-rate direction = change in DFII10 over five SPY sessions, both endpoints strictly prior to the event session;
- participation direction = trailing five-session RSP return minus SPY return, ending the prior session.

Missing real-yield observations may carry forward at most three SPY sessions, never backward. Missing input or unresolved timestamp alignment means UNKNOWN, not benign. The lag is a conservative mathematical convention, NOT certification of source release/vintage availability.

States: `hidden_fragility` for real-rate change > 0 and participation < 0; `relief_broadening` for real-rate change <= 0 and participation >= 0; `mixed` otherwise when both are known; `unknown` otherwise. Do not optimize thresholds or add a regime score.

Primary outcome: enter at the NEXT SPY session's close and exit ten SPY sessions after that entry close. An event without exact entry/exit asset and benchmark prices is ungraded. Report asset return, return minus SPY, and both after a declared 20 basis point round-trip cost. This cost is an ASSUMPTION, not a spread estimate. No same-close executable fill is assumed.

Event periods: 2006-01-03..2014-12-31 and 2015-01-01..2025-12-31, plus their combined descriptive view. These are fixed historical splits, not a claim that either is an untouched organizational holdout. Do not inspect September 2026 outcomes in this pilot or select parameters from its recent failures. The available forward window may use January 2026 only to mature December 2025 events.

## Reporting and dependence

Report every family x grain x state x period cell: event count, unique signal dates, distinct entry months/quarters, mean and median net asset and net SPY-excess returns, net-asset positive fraction, and ungraded/missing-state counts. Unknown-state events stay visible but do not enter a known-state interaction.

Primary interaction display: within each family/grain, hidden-fragility mean excess minus relief/broadening mean excess. Then compare that difference for 3D versus 1D. This contrast compares policy-specific event populations, not paired identical entry dates; explicitly disclose that selection difference.

Use a joint entry-quarter block bootstrap across instruments/policies (1,000 draws, seed 20261003) for descriptive 95% intervals where both states have at least twelve distinct entry months and at least four distinct quarters. Apply the same sampled quarter weights to both policies in an interaction contrast. Sparse cells return insufficient contrast, never zero variance or a fabricated significance result. Overlapping horizons, within-quarter dependence and only a small number of independent regimes remain limitations. No multiple-cell winner selection, p-value promotion or calibrated allocation is authorized.

No Sharpe ratio, portfolio drawdown, intraday MFE/MAE, trading recommendations or optimal holding-period claim is inferred from this event study. If the mechanism is unsupported or sign-unstable, retain that result and move the larger project toward stock/theme-level, point-in-time evidence rather than forcing the ETF result to fit the theory.

## Acceptance for this pilot only

Executable source and synthetic known-answer tests; exact input/source hashes; fixed-policy output; handling of missing states and exact next-session close alignment; paired bootstrap implementation; explicit limitations and a falsification-oriented interpretation. This closes only the preliminary ETF mechanism question at the evidence level available. It grants no source, signal, ranking, trade, sizing, or production authority and does not replace the existing owners' stronger qualification requirements.
