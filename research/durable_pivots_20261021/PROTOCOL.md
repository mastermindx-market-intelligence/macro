# Durable pivot confluence research — protocol frozen before outcome rankings

Date: 21 October 2026. Historical data cutoff: 8 October 2026.
This is retrospective exploratory research with a chronological selection/test
separation, not prospective trading validation or trading admission.

## Outcome and scope

Identify substantial lows/highs that have already formed, arrive close enough to
them to be useful, and remain unbroken. Forward returns are secondary. Fixed
50-instrument cohort: 22 US stocks; 4 US index ETFs; 12 sector/industry ETFs;
3 commodity proxies; 3 rates/credit ETFs; 4 international equity ETFs; and BTC/ETH.
The 48 exchange-traded instruments form the primary pool. Crypto is reported
separately because its daily bars and 63-day horizons use calendar days. This is
a surviving liquid cohort, not a historical all-stock universe.

## Data

Existing company snapshots have long histories but most ETF files retain closes
only. Do not manufacture intraday highs/lows or ATR from closes. Acquire and retain
a private full OHLCV snapshot from the existing Yahoo source family. Primary price
basis is split-adjusted, dividend-unadjusted OHLC (chart price structure). Use the
provider's adjclose/close factor applied consistently to all OHLC only for a named
dividend-adjusted sensitivity. Record raw response and normalized-file hashes.
No missing values are replaced with zero. Invalid OHLC rows are excluded and
reported. Large moves are audited, not winsorized. No production data is altered.

## Indicators and availability

RSI14 uses Wilder smoothing, seeded with the first 14 changes. Stoch RSI uses
RSI14, a 14-bar stochastic window, 3-bar K and 3-bar D smoothing, on a 0–100 scale.
A zero RSI range is undefined. MACD uses EMA12 minus EMA26, EMA9 signal; histogram
is MACD minus signal. MACD signal-line cross and MACD zero-line cross are distinct.
This study's MACD cross means histogram crossing zero.

Use completed bars only. US weekly bars end at the final exchange session of the
Friday-ending week. Two-week bars have a fixed alternating-week anchor; test both
phases. Two-/three-day bars mean two/three exchange sessions on the common SPY
calendar, not elapsed calendar days; test every three-session phase. Crypto uses
UTC days and Sunday-ending weeks. Never present this custom anchoring as verified
TradingView parity. Higher-timeframe states become available only at bar close.

Stoch curl: K recently at/below20 within 3 completed bars, K rising, current K<60;
top mirror: recent K>=80, K falling, K>40. Alternative K/D cross: a matching cross
within 2 completed bars after that washout, with current K>D (top K<D).

High timeframe grid: Stoch timeframe 1W/2W independently crossed with MACD
timeframe 1W/2W. MACD branches: deep; deep and improving; deep and deteriorating;
recent signal-line crossover; recent deep followed by crossover; deep OR crossover.
Stoch-only is a baseline. Deep means normalized histogram/ATR14 lies in the prior
three-year lower20% (upper20% for tops), with the appropriate negative/positive
sign. Quantiles are shifted one bar and require the full 156 weekly or78 two-week
observations. Recent cross means at most2 completed bars and current sign retained;
deep-before-cross looks back6 bars. No full-history threshold fitting.

Lower timeframe grid: 1D/2D/3D, plus1W when both high components use2W. Same-time
filters: histogram improving; favorable histogram sign; recent matching MACD
cross; Stoch K improving; both histogram and K improving. Explicit contrary
histogram slope/sign/cross are retained for conflict comparisons. Lower filters
are evaluated on the SAME high-timeframe trigger date, not allowed to silently
change trigger timing. Waiting up to10 sessions is a separate analysis.

Extra technicals are one-at-a-time ablations: price versus EMA10; daily RSI14
recovering with suitable level; weekly RSI level; daily ADX14 easing; relative
volume>=1.5 with reversal direction; and price versus SMA200. They are not a full
cross-product with every lower filter and are not called independent evidence.

## Event and outcome definitions

At signal close t, freeze the most recent occurrence of the low (top: high) in the
last63 daily bars as candidate p. Use ATR14 known at p. Measure:

* age: t-p in observed daily bars;
* distance: directional close-to-pivot distance / ATR_p;
* approach depth: prior63-bar opposite extreme to pivot / ATR_p;
* strict and 0.25-ATR-tolerant pivot survival over t+1..t+H;
* future adverse breach, favorable excursion and return, separately.

Primary timely-washout qualifier: age<=21, distance<=2 ATR_p, approach depth>=4
ATR_p. Primary outcome: this qualifier AND tolerant survival over the NEXT63
daily bars from the signal. Report conditional survival among qualified events
and unconditional timely durable precision; never mix their denominators.
H=21/126, tolerance0, distance1/3ATR, age10/42 and depth3/5ATR are named
sensitivities, not a new search for the best outcome definition.

Each high rule uses first false-to-true activation, with at least21 sessions
between events. Lower filters retain that same base event set. Independent pivot
catalogue: unique local63-left/63-right extreme, >=4ATR approach and >=4ATR
rejection. These future-dependent labels are OUTCOMES ONLY. Recall counts first
signal at p..p+21 within2ATR; denominator requires enough history and p+84 followup.
No pre-pivot signal counts as proof that the pivot had already formed.

## Selection, comparison and uncertainty

Development: 1995–2013. Selection: 2014–2019. Final test: 2020–2026 (only fully
observable horizon windows). Purge events whose labels cross a split boundary.
Earlier history may supply warmup. Select finalists using validation only, write
their exact identities and hash BEFORE final test summaries. Include fixed
user-hypothesis rules and simple price/Stoch baselines regardless of ranking.
Do not revise thresholds after viewing final rankings. Any later changes driven
by outcomes must be labeled exploratory.

Rank the precision–recall tradeoff using the harmonic mean of timely durable
precision and reference-pivot recall (a descriptive balance score, not a formal
single-target classification F1),
with minimum100 validation events and coverage across12 assets where feasible;
also retain an early and a crossover finalist per side to expose timing tradeoffs.
Final claims require approximately60 episodes,12 assets,3 instrument groups and
20 distinct quarter clusters; otherwise label sparse. These are reporting floors,
not proof of statistical power. Report asset/group/regime and crisis dependence.

Cross-sectional signals in one selloff are dependent. Confidence intervals use
whole-cross-section six-month calendar block resampling. Candidate-minus-baseline
differences use the same resampled blocks. Report individual asset/group
sensitivities, including yearly blocks. Intervals are pointwise, approximate and
not selection-adjusted or simultaneous; six-month bins can remain serially
dependent. Conditional survival percentages need at least40 qualified episodes
for even a preliminary broad interpretation, separately from total event counts.
The full config catalog is logged through the existing
engine.trial_ledger owner into a study-local ledger before evaluation; no second
production ledger and no invented deflated Sharpe test for a non-return estimand.
Validation ranking is exploratory; final test is retrospective, not live.

## Verification and falsifiers

Test indicator arithmetic, closed-bar availability, tail truncation/prefix
invariance, future perturbation invariance of signals, and label boundary handling.
The low/high survival label must fail on a constructed post-signal undercut.
An apparent winner is rejected as universal if it reverses by asset class, regime
or anchor, disappears outside validation, is too late, misses nearly all pivots,
or has no meaningful incremental benefit over the simpler rule.

## Execution and ownership

Protected source: Mastermind@d010b161386853586198a43f9ea9f535bbebb377.
Macro research workspace base:35321d4c07e6e6e321269a01d34339f5d18d4c7e.
Scope is research artifacts only; no live signal changes, capital sizing, provider
configuration or production deployment. Independent native methodological review
is advisory. Paid Fabric data audit returned terminal pre-task admission failure
canonical_source_unreadable (rc78), with no audit artifacts; direct permitted
research continues, without replaying or changing that denied worker route.
