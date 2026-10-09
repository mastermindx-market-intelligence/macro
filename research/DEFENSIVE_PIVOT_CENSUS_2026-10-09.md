# Defensive compounder pivot census — 2026-10-09

## Decision and scope

**COST daily failed-breakdown/reclaim** and **PG daily below-zero MACD crossover** are the strongest primary research candidates among the five requested stocks. MCD and WM have positive but inconclusive candidate results. WMT has no daily candidate passing the development/validation screen. None is accepted as an exact advance pivot detector, universal optimum, or production-qualified trading strategy.

Status: **CENSUS COMPLETE / LIVE QUALIFICATION NOT ESTABLISHED**. This assignment produced research and evidence only. No orders, position sizing, live alerts, production parameters, deployment, merge or installation were performed.

## 1. Data, evaluation and final audit

The 18-stock universe is MCD, WMT, WM, COST, PG, RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS and KR. SPY, XLP, XLI and XLY were acquired as benchmarks. Daily snapshots begin in January 2010; intraday snapshots begin October 14, 2024. The last included session is **October 8, 2026**, not a claim about currently executable quotes.

The 44 successful Yahoo chart snapshots contain 92,774 daily and 76,494 raw hourly observations. OHLC is adjusted using vendor adjusted-close/close; intraday uses the corresponding daily factor. Results are adjusted-price event-return proxies, not audited executable total-return portfolio accounting. The universe is survivor-selected. Raw vendor prices are not republished.

Primary development: 2011–2018. Validation: 2019–2022. Held-out evaluation: 2023–October 8, 2026. Signals use completed bars and enter at the following open. Closing outcomes are measured over 5/10/20-session holding windows, with 10 basis points deducted for round-trip cost. Events are nonoverlapping within stock/rule/horizon/period; different policies, stocks and horizons remain dependent.

Seven entry rules cover price breaks, RSI recovery, MACD recovery, 20EMA pullbacks, 50SMA resets, stressed price reclaims and failed breakdowns. Four top warnings cover RSI 70, ATR extension, extension followed by price failure, and loss of the 50SMA. Wilder RSI(14), ATR(14), MACD(12,26,9) and StochRSI(14,14,3,3) use fixed conventional parameters rather than a massive optimized search.

Selection requires at least 12 development and eight validation events, and positive matched excess in both periods. Eligible candidates are ranked on validation excess with an uncertainty penalty; primary test rankings are not used. The matched comparator is the same stock's all-date return in the same calendar year and daily trend state. It is a retrospective reference, not an investable forecast. Approximate intervals resample calendar-quarter blocks.

**Final boundary correction:** the initial all-date comparator could include a year-end control outcome that exited in the next evaluation period. The old influence was reproduced using unchanged 2018 inputs and perturbed 2019 prices. Controls now require signal, next-open entry and exit all within one evaluation period. Supplemental ladder signal-date eligibility is also aligned. All dependent comparisons, selection, intervals and exit/robustness outputs were recomputed on unchanged snapshots without tuning parameters or selection criteria. **All 18 primary selections and the core held-out results remained unchanged.** The new regression test checks both 2018/2019 and 2022/2023 boundaries.

Later multiday/weekly, paired intraday and exit extensions are exploratory analyses specified after observing primary results, not a fresh blind holdout. Final scenario counts are 54,545 primary daily rows, 17,511 longer-timeframe rows, 788 paired intraday rows and 530 exit-policy rows. These are scenario rows, NOT independent trades.

## 2. Stock price personalities

Uptrend means close above the 200-day SMA and the 50-day SMA above its value 20 sessions earlier. Retrospective pivots are extrema within a 21-session window, including ten subsequent sessions. These future-dependent labels are descriptive ONLY, never trading-signal inputs.

| Stock | Sessions above 200SMA | Median daily ATR/price | Median RSI at uptrend low | Median pullback from prior 20-session high |
|---|---:|---:|---:|---:|
| MCD | 73.5% | 1.41% | 45.4 | -5.23% |
| WMT | 78.0% | 1.47% | 44.8 | -6.05% |
| WM | 79.7% | 1.39% | 44.3 | -5.08% |
| COST | 81.5% | 1.58% | 44.1 | -6.55% |
| PG | 71.1% | 1.36% | 44.3 | -4.62% |

These medians are not buy limits or promised pullback sizes. Among hindsight-known uptrend lows, RSI had been below 30 during the preceding five-session window in only 2.6%–5.4% of the five stocks' cases. Thus RSI 30 focuses on an unusually stressed subset rather than the typical uptrend reset; RSI 44 is not an automatic buy signal either.

Waiting for a daily close above the preceding high and entering next open had a median delay of two sessions from those retrospectively known lows. Conditional median premiums above the low were MCD 2.15%, WMT 2.40%, WM 2.49%, COST 2.69% and PG 2.56%. This is the cost of confirmation conditional on successful hindsight lows, NOT live bottom-detection accuracy.

RSG, ADP and CTAS spent approximately 81.6%, 80.7% and 85.4% of sessions above their 200SMAs. CTAS still had no qualifying primary entry. KR had higher median daily ATR/price, 2.06%, and a deeper median uptrend pullback, 7.04%. Trend persistence and a defensive-company label do not themselves establish an entry edge.

## 3. Primary daily candidates

Net outcome means next-open entry to the close at the end of a 20-session holding window, less 10 basis points. Excess is in percentage points, not a multiplicative percentage improvement.

| Stock | Locked rule | Events | Positive closing outcomes | Mean net outcome | Matched excess | Approx. 95% excess interval |
|---|---|---:|---:|---:|---:|---|
| MCD | Failed breakdown/reclaim | 13 | 61.5% | +0.95% | +1.40 points | -0.80 to +3.64 points |
| WMT | No candidate qualified | — | — | — | — | — |
| WM | Below-zero MACD crossover | 15 | 60.0% | +2.45% | +0.97 points | -0.42 to +2.93 points |
| COST | Failed breakdown/reclaim | 12 | 83.3% | +3.42% | +1.87 points | +0.61 to +3.90 points |
| PG | Below-zero MACD crossover | 18 | 72.2% | +1.76% | +1.57 points | +0.13 to +3.50 points |

COST's 83.3% is ten positive outcomes from twelve events, with an approximate Wilson interval of 55.2%–95.3%. PG's interval is 49.1%–87.5%. A conservative 18-name Bonferroni diagnostic applied to the block-bootstrap tail measure gives approximately 0.060 for COST and 0.480 for PG; neither clears 0.05. This diagnostic is not a fully specified universally valid multiple-testing procedure. Dependence and selection still constrain inference.

At 20 rather than 10 basis points cost, mean COST and PG outcomes remain approximately +3.32% and +1.66%. Removing the single best event leaves +2.78% and +1.21%. These checks are encouraging, not live qualification.

### Exact tested buy definitions

**COST and MCD — daily failed breakdown/reclaim:** current low below the lowest low of the preceding 20 completed sessions; close recovers above that earlier low; close in the upper 35% of the current high-low range; RSI(14) below 50. Entry is the following session's open. This combines support failure, rejection of lower prices, closing strength and a momentum-state restriction. It does not buy the first support touch or predict the intraday low.

**PG and WM — daily MACD recovery:** the MACD(12,26,9) histogram crosses above zero while the MACD line itself remains below zero. Entry is the following session's open. Adding weekly trend, RSI, volume, earnings or intraday filters creates a different strategy that cannot inherit these statistics.

**WMT:** no rule qualified. This is retained rather than weakening the validation screen. No qualified candidate does not mean the stock cannot be traded; it means the tested primary family did not establish a preferred entry.

The other primary candidates have the following held-out 20-session net means: RSG MACD +0.45%; KO MACD +1.31%; CL 50SMA reset -0.92%; CHD MACD +0.28%; KMB 50SMA reset -1.08%; MDLZ stressed reclaim -0.28%; HSY 20EMA pullback -0.19%; CLX stressed reclaim -0.38%; JNJ 50SMA reset -2.58%; ADP failed breakdown +1.25%; KR 20EMA pullback +0.93%. PEP and CTAS had no qualified candidate. These means do not establish statistically reliable edges; negative findings remain visible.

## 4. Timeframe assessment

The recovered `reports/mwr_timeframe_personality.md` at macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139` was a descriptive 1,623-name StochRSI ladder. Its volatility/best-rung ordinal correlation of +0.035 did not support a universal slower-stock/higher-timeframe law. The current extension tests completed 1D, 2D, 3D, weekly, two-week and monthly bars, next-open entries and 20/63-session horizons.

MCD's weekly StochRSI crossover mean 63-session return was +4.71% in development, +3.87% in validation and -1.17% in the latest six-event test sample. Corrected matched excess was +0.79, -0.31 and -4.42 percentage points. Its older weekly advantage did not persist.

WMT's three-day crossover looked attractive in the latest period: ten events, nine positive, mean +10.62%, matched excess +3.78 points. Corrected matched excess was negative in BOTH earlier periods: -0.19 points in development and -0.90 points in validation. It is a hypothesis, not a validated best timeframe. Monthly latest-period observations are often only one to three per core stock; apparent winners are not reliable optimization evidence.

### Matched intraday experiment

The public hourly feed contained malformed early-close records and incomplete regular sessions. Entire affected sessions were excluded. Each stock and SPY use identical accepted timestamps; outcome windows cannot cross missing sessions. Indicators can still bridge excluded dates.

The setup is an uptrend stock whose daily RSI crosses below 50. Each grid gets the same five-session confirmation window and a common exit ten sessions after the setup. Confirmation requires a completed-bar close above the prior high, rising MACD histogram and recent RSI at or below 45. Results below use the 41 latest-period opportunities where ALL grids triggered.

| Grid | Paired opportunities | Mean net return | Difference versus immediate next-open entry |
|---|---:|---:|---:|
| 1-hour | 41 | -1.02% | -0.16 points |
| 2-hour | 41 | -1.19% | -0.33 points |
| 3-hour | 41 | -1.23% | -0.37 points |
| 4-hour | 41 | -1.37% | -0.51 points |

Coverage before restricting to the common set was 49/49, 48/49, 43/49 and 41/49. Excluding shortened tail bars from indicator construction left only ten common opportunities, still no robust positive finding. Reject this particular confirmation system, not all intraday timing; one hour is not established as universally best.

NYSE's core session is 6.5 hours. The 1/2/3-hour grids finish with a 30-minute bar; the 4-hour grid finishes with a 150-minute bar. None is a uniform 24-hour series. No 15-minute, 30-minute or overnight winner is claimed. The original unpaired 7,090-row hourly output is superseded for inference.

## 5. Tops, targets and exits

Across the full 18-stock panel, the first RSI crossing above 70 was followed by a mean +0.89% net 20-session outcome, positive in 56.7% of 171 latest-period events. RSI 70 is not an automatic top. Conversely, a positive closing-return fraction is not a tight-stop trade win rate.

COST reached a +2 ATR target before a -1.5 ATR stop within 20 sessions in 58.3% of the twelve primary events, despite 83.3% finishing positive. PG's corresponding figures were 66.7% and 72.2%. Target-not-first can include an unresolved timeout, not necessarily a stop. Same-bar ambiguity is resolved conservatively except where an opening gap establishes boundary order.

The exploratory exit table uses the SAME entries across policies, separated by 63 sessions. Cohorts are smaller and DIFFERENT from the primary table. Returns are not annualized or adjusted for different time in the market.

| Stock | Common entries | Hold 20 sessions | Hold 63 sessions | RSI >=70 next open | Extension + failure next open | Prior-close 3ATR trail |
|---|---:|---:|---:|---:|---:|---:|
| MCD | 7 | +1.98% | +1.05% | +1.81% | +2.79% | -0.83% |
| WM | 9 | +2.70% | +3.14% | +5.25% | +2.41% | +1.84% |
| COST | 7 | +3.84% | +5.53% | +5.18% | +4.70% | +3.17% |
| PG | 9 | +1.67% | +1.93% | +2.58% | +1.88% | +1.22% |

Extension plus failure requires price at least two ATR above the 20EMA within the preceding five bars, followed by close below the previous low and a falling histogram; execute next open. The trailing stop uses only prior completed closes and ATR, with opening-gap handling. These are exit hypotheses, not proof that each row's highest number identifies the optimal exit.

## 6. Operating interpretation and remaining qualification

The proposed workflow is weekly structural context, daily candidate setups and intraday timing ONLY where incremental entry quality is demonstrated. It is not an already validated three-timeframe combined rule. Keep ordinary trend pullbacks separate from stressed reversals. RSI/MACD/StochRSI are related price transformations, not three independent votes.

Prioritize prospective paper evaluation of the exact COST reclaim and PG MACD rules. Keep MCD/WM uncertain and WMT unqualified. RSG/ADP warrant continued trend research; CTAS's persistence alone did not qualify an entry. Negative CL, KMB, MDLZ, HSY, CLX and JNJ results must not be hidden behind the defensive-company label.

Anchored VWAP, volume profile, order flow, subjective divergences, point-in-time valuation and earnings filters were not validated here. Structural invalidation, spreads, gaps and sizing need separate qualification. No live model-originated size or optimal stop is supplied.

Next qualification requires continuous licensed intraday/overnight history where relevant, second-vendor and corporate-action checks, point-in-time/event controls, stability across regimes and neighboring parameters, and a frozen prospective paper test with observed fills. The present bounded study does not establish that every possible indicator combination has been exhausted.

## 7. Verified evidence and continuity

**Fourteen implementation tests passed on both research and delivery runtimes**, including zero next-period influence in the matched comparator. Other tests cover Wilder seeding, RSI extremes/flat prices, prefix invariance, period purging, nonoverlap, barrier ordering, daylight-saving dates, multiday grouping and incomplete weekly bars. Tests establish these mechanics, not profitability.

Delivery source copies match recorded hashes. The 58 core event records reconcile with summary counts, positive fractions and mean returns. The portable acquisition wrapper is syntax-checked; it was not used to replace the frozen snapshot. Deliverables comprise a nine-sheet workbook, nine rounded/subset CSV tables including the core event ledger, report/README, audit note, analysis/test source, frozen specifications and provenance hashes. Raw vendor data is excluded; later re-fetches may be revised or unavailable. Rounded exports do not share the original full-precision-result hashes.

- Protected source: Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack 1.0.1/bootstrap 1.
- Research base: macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139`.
- Snapshot manifest SHA256: `69703435b594cca35ea7f8e26673dc719c0ec9b3db3dc802df9ca531e0ce6ed3`.
- Corrected primary source SHA256: `b2e0ba1b891aee625fbe90e818b3f646a7386f9ad7b92935a0537f51b30e123e`.
- Corrected extension SHA256: `70be0f30cbeddd60ad58a8409b7ea382bab54969f1c6521c0064370ed2091d59`.
- Corrected ladder summary SHA256: `2c5a5920ae8c3f280a8b01bf60067db419175d5a3dde6d03dc9c1fecfffb89c1`.
- Matched intraday summary SHA256: `7b2400fe66c42b2efb7ab66413906ee2b2b17866f6f6b971a7359672efd2846d`.
- Exit-policy summary SHA256: `2f96434443de225641e72fe8f68267a2e2f203a05bfe1e828c621076b000c66d`.
- Robustness summary SHA256: `de4745057273be05ef5e58192c11604324c4f0def3e8db5e6f6fde886cf60ad7`.

No active child, watcher, uncertain remote write, trade or live consumer remains. Final research stop reason: requested census, candidate assessment, timeframe challenge and exit/risk assessment are delivered; live qualification is explicitly separate and unproven. Accepted data and calculations should not be rerun without a relevant invalidator.

## Primary public references

- RSI: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI
- ATR: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr
- Exchange hours: https://www.nyse.com/trade/hours-calendars
- Adjusted prices: https://in.help.yahoo.com/kb/adjusted-close-sln28256.html
- Backtest overfitting: https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
