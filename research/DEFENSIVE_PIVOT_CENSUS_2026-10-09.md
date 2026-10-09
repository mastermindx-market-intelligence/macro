# Defensive compounder pivot census — 2026-10-09

## Decision

The strongest primary research candidates among the five requested stocks are **COST daily failed-breakdown/reclaim** and **PG daily below-zero MACD crossover**. MCD and WM have positive but inconclusive candidate results. WMT has no daily candidate that passes the prespecified development/validation screen. None is accepted as a production-qualified strategy, an exact advance pivot detector, or a proven universal optimum.

The evidence supports stock-specific treatment of pullback depth and trend persistence, but not assigning each stock an arbitrary magic timeframe. Daily RSI at hindsight-identified uptrend lows clusters around 44–46 across this universe. RSI 30/70 alone is not a satisfactory entry/exit system. Slower charts and more oscillator confirmations do not automatically improve results.

Status: **CENSUS COMPLETE / LIVE QUALIFICATION NOT ESTABLISHED**. This assignment produced research and evidence only. No orders, position sizing, live alerts, production parameters, deployment, merge or installation were performed.

## 1. Universe and method

The 18-stock universe is MCD, WMT, WM, COST, PG, RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS and KR. SPY, XLP, XLI and XLY were acquired as benchmarks. Daily snapshots begin in January 2010; intraday snapshots begin October 14, 2024. The last included session is **October 8, 2026**, not a claim about currently executable quotes.

The 44 successful public Yahoo chart snapshots contain 92,774 daily and 76,494 raw hourly observations across stocks and benchmarks. OHLC is adjusted using the vendor adjusted-close/close factor; intraday prices use the corresponding daily factor. Results are adjusted-price event-return proxies, not audited total-return portfolio accounting. Raw vendor data is not republished.

Primary daily development is 2011–2018, validation 2019–2022, and held-out testing 2023–October 8, 2026. Signals use completed bars and enter at the following open. Closing-price outcomes are measured at 5, 10 and 20 trading sessions after entry, with 10 basis points deducted for round-trip cost. Events are nonoverlapping within stock/rule/horizon/period. Different rules, horizons and stocks remain dependent. Outcomes crossing period boundaries are purged.

Seven daily entry rules cover price breaks, RSI recovery, MACD recovery, 20EMA pullbacks, 50SMA resets, stressed price reclaims and failed breakdowns. Four top warnings cover RSI 70, ATR extension, extension followed by price failure, and loss of the 50SMA. Wilder RSI(14), ATR(14), MACD(12,26,9) and StochRSI(14,14,3,3) use fixed conventional parameters rather than a massive optimized parameter search.

A candidate qualifies for selection only with at least 12 development and eight validation events, and positive excess return against a matched comparator in both periods. Among qualifiers, the validation excess return receives an uncertainty penalty; test rankings are not used for primary selection. The matched comparator is the same stock's all-date forward return in the same calendar year and daily trend state. It is a retrospective reference, not an investable expected-return forecast. Approximate confidence intervals resample calendar-quarter blocks.

The multiday/weekly, paired intraday and exit extensions were specified after observing the primary results. They are supplemental exploration, not a new blind holdout. Full scenario counts are 54,545 primary daily rows, 17,516 multiday/weekly rows, 788 paired intraday rows and 530 exit-policy rows. These are scenario rows, NOT independent trades or independent validation samples.

## 2. What the five stocks' price personalities show

Uptrend means close above the 200-day SMA and the 50-day SMA above its level 20 sessions earlier. A retrospective pivot is an extreme within a 21-session window, with ten sessions on each side. These future-dependent labels are used ONLY for description, never as trading inputs.

| Stock | Sessions above 200SMA | Median daily ATR/price | Median RSI at uptrend low | Median pullback from prior 20-session high |
|---|---:|---:|---:|---:|
| MCD | 73.5% | 1.41% | 45.4 | -5.23% |
| WMT | 78.0% | 1.47% | 44.8 | -6.05% |
| WM | 79.7% | 1.39% | 44.3 | -5.08% |
| COST | 81.5% | 1.58% | 44.1 | -6.55% |
| PG | 71.1% | 1.36% | 44.3 | -4.62% |

These are descriptive medians, not buy limits or guaranteed pullback sizes. Waiting for RSI below 30 would focus on an unusually stressed subset, not the typical uptrend reset. Among hindsight-known uptrend lows, RSI had been below 30 during the preceding five-session window in only 2.6%–5.4% of the five stocks' cases.

Waiting for a daily close above the preceding day's high and then entering at the next open incurred a median delay of two trading sessions from these retrospectively known lows. Conditional median entry premiums above the low were approximately MCD 2.15%, WMT 2.40%, WM 2.49%, COST 2.69% and PG 2.56%. This describes the cost of confirmation conditional on successful hindsight lows; it is NOT live signal accuracy or a probability of identifying a bottom.

Peer characteristics matter too. RSG, ADP and CTAS spent approximately 81.6%, 80.7% and 85.4% of sessions above their 200SMAs, but CTAS still had no qualifying primary entry rule. A persistent trend is not automatically an entry-timing edge. KR had a higher median ATR/price of 2.06% and a deeper median uptrend pullback of 7.04%. Negative held-out candidate means for CL, KMB, MDLZ, HSY, CLX and especially JNJ must not be concealed by the defensive-company label.

## 3. Primary daily candidates: actual held-out evidence

Net outcome means next-open entry to the close 20 trading sessions later, less 10 basis points. Excess is measured in percentage points, not a relative percentage improvement.

| Stock | Locked rule | Events | Positive closing outcomes | Mean net outcome | Matched excess | Approx. 95% excess interval |
|---|---|---:|---:|---:|---:|---|
| MCD | Failed breakdown/reclaim | 13 | 61.5% | +0.95% | +1.40 points | -0.80 to +3.64 points |
| WMT | No candidate qualified | — | — | — | — | — |
| WM | Below-zero MACD crossover | 15 | 60.0% | +2.45% | +0.97 points | -0.42 to +2.93 points |
| COST | Failed breakdown/reclaim | 12 | 83.3% | +3.42% | +1.87 points | +0.61 to +3.90 points |
| PG | Below-zero MACD crossover | 18 | 72.2% | +1.76% | +1.57 points | +0.13 to +3.50 points |

COST's raw 83.3% positive fraction is ten of twelve events, with an approximate Wilson interval of 55.2%–95.3%. PG's corresponding interval is 49.1%–87.5%. Dependence can further limit inference. A conservative 18-name Bonferroni diagnostic applied to the block-bootstrap tail measure gives about 0.060 for COST and 0.480 for PG. Neither clears 0.05. This diagnostic is not a substitute for a fully specified, uniformly valid multiple-testing procedure.

Increasing cost from 10 to 20 basis points leaves mean COST and PG outcomes approximately +3.32% and +1.66%. Removing the single best event leaves approximately +2.78% and +1.21%, respectively. These checks are encouraging but do not overcome small samples, survivor selection or regime uncertainty.

### Exact candidate entry definitions

**COST and MCD — daily failed breakdown/reclaim:** the current low falls below the lowest low of the preceding 20 completed sessions; the close recovers above that prior low; the close lies in the upper 35% of the current day's range; daily RSI(14) is below 50. The tested entry is the following session's open. This combines support failure, rejection of lower prices, closing strength and a momentum-state restriction. It does not mean buying the first touch of support or predicting the session low.

**PG and WM — daily MACD recovery:** the MACD(12,26,9) histogram crosses above zero while the MACD line itself remains below zero. The tested entry is the following session's open. Adding a weekly uptrend gate, a new RSI threshold, a volume filter, or another intraday confirmation creates a different rule and must not inherit the reported statistics.

**WMT — no admitted trigger from this family:** ordinary pullbacks may still be investable, but the research does not justify presenting an optimized WMT buy rule. No candidate is a valid result, not a reason to relax the validation screen.

Structural invalidation, earnings/event checks, spread and gap handling, and position sizing require separate qualification. No model-originated live trade size or claimed optimal stop is supplied.

## 4. Timeframes: slower is not automatically better

The recovered prior Mastermind report `reports/mwr_timeframe_personality.md` at macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139` is a descriptive 1,623-name StochRSI ladder. Its volatility/best-timeframe ordinal correlation is +0.035, not evidence for a universal slower-stock/higher-timeframe law. The present extension evaluates completed 1D, 2D, 3D, weekly, two-week and monthly bars with next-open entries and 20/63-session horizons.

Two important counterexamples emerged. MCD's weekly StochRSI crossover had a mean 63-session outcome of +4.71% in development, +3.87% in validation and -1.17% in the latest test period (six test events). Its matched excess was +0.79, -0.36 and -4.42 percentage points. The older descriptive weekly advantage did not persist.

WMT's three-day crossover looked attractive in the latest period: ten events, nine positive, mean +10.62%, matched excess +3.78 points. But matched excess was negative in BOTH earlier periods: -0.39 points in development and -0.94 points in validation. This is a research hypothesis to investigate, not a validated best timeframe. Monthly observations are often only one to three events per core stock in the latest period; apparent monthly winners are not credible optimization evidence.

### Paired intraday comparison

The public hourly feed contained malformed early-close rows and some incomplete regular sessions. Entire affected sessions were excluded. In the final comparison each stock and SPY use identical accepted timestamps, and an outcome window cannot cross a missing session. Indicators can still bridge excluded days; this limitation remains.

The common setup is an uptrend stock whose daily RSI crosses below 50. Each grid gets the same five-session confirmation window and the same exit date ten sessions after the setup. Confirmation requires a completed-bar close above the previous high, rising MACD histogram, and RSI at or below 45 recently. Results below use the 41 latest-period opportunities where ALL four grids triggered.

| Grid | Paired events | Mean net outcome | Difference versus immediate next-open entry |
|---|---:|---:|---:|
| 1-hour | 41 | -1.02% | -0.16 points |
| 2-hour | 41 | -1.19% | -0.33 points |
| 3-hour | 41 | -1.23% | -0.37 points |
| 4-hour | 41 | -1.37% | -0.51 points |

All-timeframe opportunity coverage was 49/49, 48/49, 43/49 and 41/49, respectively, before restricting to the common 41. Excluding shortened tail bars from indicator construction leaves just ten common latest-period opportunities, still no robust positive result. Reject this particular confirmation system; do not conclude that all intraday timing is useless or that one hour is universally best.

NYSE's core session is 6.5 hours. The 1/2/3-hour grids have a 30-minute final bar; the 4-hour grid has a 150-minute final bar. None is a uniform 24-hour series. No 15-minute, 30-minute or overnight winner is claimed. The initial 7,090-row unpaired hourly output is superseded for inference, not silently treated as accepted evidence.

## 5. Tops, profit taking and risk

Across all 18 stocks, the first RSI crossing above 70 was followed by a mean +0.89% net 20-session outcome, positive in 56.7% of 171 latest-period events. RSI 70 is therefore not an automatic top in this panel. Conversely, a good closing-return fraction is not a tight-stop strategy's win rate.

For COST, only 58.3% of the twelve primary events reached a +2 ATR target before a -1.5 ATR stop within 20 sessions, despite 83.3% ending positive. PG's corresponding figures are 66.7% and 72.2%. A failure to reach the target first can include an unresolved timeout; it must not automatically be labeled a stop loss. Same-bar target/stop ambiguity is resolved conservatively, except where an opening gap establishes which boundary was encountered first.

An exploratory exit comparison used the same entries across policies, separated by 63 sessions. This creates smaller cohorts, DIFFERENT from the primary table. Returns are not annualized or adjusted for different time in the market.

| Stock | Common entries | Hold 20 sessions | Hold 63 sessions | Exit next open after RSI >=70 | Exit after extension + price failure | Prior-close 3 ATR trailing stop |
|---|---:|---:|---:|---:|---:|---:|
| MCD | 7 | +1.98% | +1.05% | +1.81% | +2.79% | -0.83% |
| WM | 9 | +2.70% | +3.14% | +5.25% | +2.41% | +1.84% |
| COST | 7 | +3.84% | +5.53% | +5.18% | +4.70% | +3.17% |
| PG | 9 | +1.67% | +1.93% | +2.58% | +1.88% | +1.22% |

The extension-plus-price-failure rule requires price at least two ATR above the 20EMA sometime in the preceding five bars, followed by a close below the previous low and a falling histogram; execution is at the next open. The trailing stop uses only prior completed closes and ATR, with opening-gap handling. These are exit hypotheses, not proof that the highest value in each row is the optimal exit.

For further paper testing, maintain separate states for an extension warning and a confirmed structural exit. Do not mechanically sell a long-term compounder because a short-timeframe oscillator is high, and do not mistake holding through a business/valuation breakdown for a harmless technical pullback.

## 6. Research playbook and next qualification gate

Use weekly charts to describe broad structure, daily charts to define candidate setups, and intraday charts only where incremental entry quality is separately demonstrated. This is a proposed workflow, not a validated three-timeframe confluence. Keep trend continuation separate from stressed mean reversion. RSI/MACD/StochRSI are related transformations of price, not three independent votes.

Prioritize prospective paper evaluation of the exact COST reclaim and PG MACD rules. Keep MCD and WM in an uncertain-candidate lane. Keep WMT unqualified rather than forcing a winning parameter. RSG and ADP warrant continued trend research; CTAS's trend persistence alone did not qualify an entry. Do not promote negative candidates for CL, KMB, MDLZ, HSY, CLX or JNJ merely because the companies are called defensive.

The next qualification work is licensed continuous intraday/overnight history where applicable, corporate-action and point-in-time vintage reconciliation, historical earnings/event controls, second-vendor checks, stability across regimes and neighboring parameters, and a frozen prospective paper evaluation with observed fills. A 15/30-minute study is not complete from hourly data. New filters or exits need new validation rather than inheriting a parent rule's win rate.

## 7. Evidence and continuity

Thirteen implementation tests passed on both the research runtime and the delivery runtime. They cover Wilder seeding, RSI extremes/flat prices, prefix invariance, period purging, nonoverlap, barrier ordering, daylight-saving dates, multiday grouping and exclusion of incomplete weekly bars. Tests establish these mechanics, not profitability. The delivery source copies match their recorded hashes. The portable acquisition wrapper is syntax-checked; it was not used to replace the frozen snapshot.

- Protected source: Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack 1.0.1/bootstrap 1.
- Research base: macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139`.
- Snapshot manifest SHA256: `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3`.
- Primary source SHA256: `cf118b1d0af16fd88b696ece100aad754281d00ec2186dea5d2baf1738f00bb1`.
- Final extension SHA256: `3b5cfe0f660a6e21c785239bafda0e3de35609a1ece48e7fa24945183e5fa2a1`.
- Matched intraday summary SHA256: `7b2400fe66c42b2efb7ab66413906ee2b2b17866f6f6b971a7359672efd2846d`.
- Exit-policy summary SHA256: `2f96434443de225641e72fe8f68267a2e2f203a05bfe1e828c621076b000c66d`.
- Final robustness summary SHA256: `de4745057273be05ef5e58192c11604324c4f0def3e8db5e6f6fde886cf60ad7`.

Delivery includes a nine-sheet research workbook, rounded derived CSV tables, methodology notes, original analysis/test source, the frozen research specifications and provenance hashes. Rounded/subset delivery CSVs do not share the full-precision originals' hashes. Raw vendor bars are excluded; re-fetching public history may produce revisions and older intraday windows may cease to be available.

No active child, watcher, pending remote write, trade or live consumer remains from this assignment. Final research stop reason: the requested census, candidate assessment, timeframe challenge and exit/risk assessment are delivered; production qualification is explicitly a separate unproven gate, not silently claimed. Existing research results and their rejected alternatives should not be rerun without a relevant data, method or authority change.

## Primary public references

- RSI: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI
- ATR: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr
- Adjusted prices: https://in.help.yahoo.com/kb/adjusted-close-sln28256.html
- Exchange hours: https://www.nyse.com/trade/hours-calendars
- Backtest overfitting: https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- Walmart corporate-action example: https://corporate.walmart.com/news/2024/01/30/walmart-announces-3-for-1-stock-split
- Costco corporate-action example: https://www.sec.gov/Archives/edgar/data/909832/000090983223000062/cost-20231213.htm
