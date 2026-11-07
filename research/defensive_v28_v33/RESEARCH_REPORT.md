# Defensive Nested Washouts V28–V33: Daily StochRSI, Two-Day RSI-MACD and the Cost of Confirmation
**October 13, 2026 — empirical research only; final historical equity prices through October 8, 2026**

## Executive adjudication

The user’s hypothesis is that **a deeply washed-out weekly plus two-week StochRSI establishes the long-term reversal opportunity**, and a **shorter two-day RSI-MACD bullish crossover** confirms an entry; a daily StochRSI bottom/crossover may improve conviction. Earlier Mastermind technical studies often tested unrelated price MACD/RSI2 rules and could not adjudicate this exact nested sequence. V11–V27 corrected those mechanics and produced real-stock data, but neither the high observed fixed-horizon positive fraction nor an account policy was selection-adjusted alpha.

**V28–V33 now explicitly test the user’s two-day RSI-MACD + daily StochRSI combination in two correct ways:**

1. **Same lower crossover (V28/V29):** On a given completed two-day RSI-MACD bullish crossover, condition on an already-observable daily StochRSI short-term washout and look forward from that fixed date.
2. **Same original long watch (V30–V33):** Fix all W+2W long-washout episodes **before** either shorter confirmation, then compare early daily StochRSI entry, first native two-day RSI-MACD entry, and *strict sequential daily StochRSI then two-day RSI-MACD confirmation*, retaining every missed opportunity and actual next-open entry delay.

**The key result:** Requiring the daily StochRSI confirmation **followed by** a qualifying two-day RSI-MACD confirmation was *not an empirically strong universal entry gate* in these tested examples. It could make accepted trades look excellent while suppressing a much larger set of profitable recovery opportunities and leaving most capital idle. Daily StochRSI as an independent earlier *trigger*, by contrast, remained competitive with first two-day RSI-MACD, but neither had a robust, selection-adjusted superiority result.

No real trade, live strategy, portfolio weight, broker fill, production setting or current buy/sell instruction is delivered. Stronger method clarity is not equivalent to validated alpha.

## Data, indicator and methodological custody

- 18 originally selected survivor equities: **MCD, WMT, WM, COST, PG** (core five) plus RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS, KR (heterogeneous peers). Nominal sample 2018–October8 2026, with accepted 2010+ history for native RSI-MACD/2W warmup.
- No new vendor acquisition in V28–V33. Inputs remain the **previously accepted V11/V12 original-window, same-vendor adjusted OHLC** and derived event/position ledgers. The separately acquired October13 V27 provider vintage and its future observations are expressly excluded from the V28–V33 historical performance tests.
- Original main references: [V11 merged PR #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034), [independently owned V12 PR #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064), [V13–V20 PR #9129](https://github.com/mastermindx-market-intelligence/macro/pull/9129), [V21–V23 PR #9174](https://github.com/mastermindx-market-intelligence/macro/pull/9174), [V24–V26 phase/multiplicity PR #9176](https://github.com/mastermindx-market-intelligence/macro/pull/9176), [V27 first paper freeze PR #9180](https://github.com/mastermindx-market-intelligence/macro/pull/9180).
- Native working indicator: **Wilder RSI14 → EMA14(RSI)-EMA60(RSI), EMA5 signal**, with completed daily/two-day candles; slow and daily **StochRSI14/14/3/3**. W context: K touched20 or lower within last3 completed W bars; 2W context: K touched20 or lower within last2 completed 2W bars, current2W K <60; 200 completed native bar warmup; native phase0. Original 42-session watch with10 cleared sessions to rearm.
- The user’s precise TradingView RSI-MACD indicator species and 2W candle anchor **remain UNVERIFIED**. V25 showed 9.5–20.6% of the core crossover labels can change with phase/developing-bar semantics. Never choose a chart phase by posthoc return ranking.
- V28–V29 *conditioning* outcomes are **126 trading sessions after lower crossover entry**, while V30–V33 *fixed-watch* outcomes end **arm+126 completed daily sessions**. These different estimands must NEVER be combined as if the windows matched.
- Transaction convention: signal becomes available on a completed native bar, purchase at next stock open, approximately 10 basis points per round trip (0.05% each side). Intraday +8% target versus −5% stop comparisons give a diagnostic **stop-first** outcome if both touched on the same observed OHLC candle, not executable bracket-order proof.
- Hundreds/thousands of prior configurations and repeated review of 2018–2026 make ALL numerical comparisons **exploratory**. Event clusters share market crises; daily and two-day sources overlap; selected stocks are not a survivor-free neutral universe.

## V28 — Original two-day bullish crossover conditioned on recent daily StochRSI bottom

Predefined "recent daily washout": **daily StochRSI K <=20 sometime in the last five completed daily sessions through the two-day RSI-MACD crossover close**. Strict subvariant requires an actual daily K>D bullish crossover observed during those five sessions, daily K>=D at the two-day trigger, and the recent daily washout.

Out of **899** total two-day RSI-MACD cross observations across18 names, **65 core-five observations** occurred under JOINT W+2W long-washout context. Among these, **14** had a recent daily washout, **51** did not.

| Core-five, JOINT W+2W on completed 2D crossover | Recent daily short washout (n14) | No recent daily short washout (n51) |
|---|---:|---:|
| Positive net after126 **owned** sessions | **14/14 (100%)** | **39/51 (76.5%)** |
| Mean126-entry-session net return | **+13.16%** | **+9.78%** |
| Average beta-adjusted selected stock minus four-peer log recovery during sessions20–63 | **+0.05%** | **+1.95%** |

These are real historical observations, not a validated100% trade probability. The short filter missed39 eventually positive comparator trades while avoiding12 nonpositive comparator trades. The accepted group’s relative recovery versus peers was **not** better; its high absolute return may reflect broad common risk-factor repair.

**Additional timing concern:** of those14 accepted trades, **9 had daily StochRSI K already >70** at the two-day RSI-MACD entry and **6 exceeded K80**. Median current daily K was ~75.1. A washout five sessions ago does **not** mean entry is still near its short-term momentum bottom. A multi-timeframe strategy can buy well after the initial short-cycle recovery.

In PEERS13, the same daily condition was not favorable: JOINT-W+2W accepted n44 had mean126 return **+6.42%**, versus rejected n137 **+7.01%**. The strict daily KD-in-force subvariant shrank accepted core observations to12, all eventually positive, but its narrow selection and retrospective origin are not extra validation.

## V29 — Execution path, stop-first and independent-entry challenge

V29 recalculated each real stock’s 20-, 63- and 126-session entry path using the same originally accepted V12 OHLC. **Nine mechanical tests passed**, 899/899 original two-day event rows retained, zero +8%/−5% V11 barrier outcome mismatches and original126-session non-overlap status reconciled identically. Original V28 126-session net returns reproduced within ~1×10^-6, within the independently disclosed adjusted-price vendor-vintage tolerance.

The 14 accepted core examples were not uniformly easy to trade:
- Only **8/14 (57.1%)** hit an intraday **+8% target before a −5% stop**.
- **6/14** breached the five-percent stop before that target.
- **4/14** experienced at least a five-percent adverse low during their first20 owned sessions.
- At63 owned sessions, accepted mean was **+6.54%** versus rejected **+5.81%**; accepted same-date gain versus other four was only **+0.25 percentage points**, versus rejected **+1.96 points**.
- Exploratory shared-quarter interval for the accepted-minus-rejected **126-session mean**: approximately **−1.66pp to +10.34pp**. For **63-session excess versus other core stocks**: approximately **−5.50pp to +2.16pp**. Both include zero.
- A sixty-three-session per-stock crossover embargo reduced core JOINT accepted count from14 to **5**. A126-session embargo left **2**; their mean63-session return was negative. Neither tiny subset supports an independent win-rate claim.

## V30 — Fixed master-watch comparison, including every missed recovery

To remove the hidden selection advantage of waiting for a confirmatory second indicator, V30 begins with **198 unique original long W+2W washout episodes** (57 core-five,141 peers) from the accepted V11/V12 fixed watch inventory. Daily, two-day and sequential signal dates are then determined *within that exact original watch* and never use future price returns to decide whether to enter.

Four study entry policies:
1. **WATCH_IMMEDIATE:** enter the next open after the long watch arms.
2. **FIRST_2D_MACDRSI:** enter the next open after the first completed two-day RSI-MACD bullish crossover.
3. **FIRST_DAILY_STOCH:** enter the next open after the first daily K>D cross with daily K having touched20 or below within five completed daily bars.
4. **DAILY_STOCH_THEN_2D:** enter the next open after the earliest completed two-day RSI-MACD bullish cross for which a daily K>D cross occurred since watch arming during the latest five completed daily bars, daily K>=D now and the five-bar daily washout remains observable.

At most one first candidate per original watch; no pyramiding, no later successful entry substituted for a failed earlier one. **10 tests passed**; all198 master watch arms and first original2D signals reconciled with the frozen V12 records. Last watches without126-session outcomes remain INCOMPLETE (six core, ten peers); they are not losses.

**Five core stocks, 51 completed W+2W opportunities with identical arm+126 endpoints:**

| Policy | Qualified entries | Mean return across ALL 51 watches (zero cash if skipped) | Mean delay |
|---|---:|---:|---:|
| Arm immediately | 51 | **+11.09%** | 0 sessions |
| First two-day RSI-MACD | 50 | +9.29% | 8.66 sessions among entries |
| First daily StochRSI recovery | 46 | +9.40% | 14.61 sessions |
| Strict daily StochRSI then two-day RSI-MACD | **15** | **+3.89%** | **21.27 sessions** |

Strict sequencing had 80% eventual positive outcomes among15 trades, but **skipped36 watches**, including **31 where arm-immediate entry would have finished positive**. Nine of the15 strict entries reached +8% before −5%. In the13-peer panel, it filled32/131 complete watches with only +1.12% mean all-watch return versus immediate +9.05%.

### Critical interpretation

The long W+2W context can carry useful evidence while mandatory short-timeframe confluence generates severe **delayed-entry and missed-opportunity cost**. This does not establish that buying every long washout immediately is safe. Immediate entry retained more fixed-horizon profit but hit the −5% barrier before +8% in more events. Risk-control, size, market drawdown and objective remain separate decisions.

## V31 — Actual single-position account replay, not just averaged signals

The accepted **V12 account executor was reused unchanged**, including next-open entry, gap-aware fixed initial ATR stops, one active position per stock, no automatic year liquidation and sample-end marked open positions. No new trade broker was implemented. All **54 matching first-two-day V12 account cases** (18 names ×3 exits) matched the prior accepted V12 account results to numerical precision (**maximum discrepancy 2.22×10^-16**). This is strong code/evidence reconciliation, not predictive proof. **Six new tests passed**; 216 individual account variants (18×4 entries×3 exits), 476,064 daily account rows.

Five-core, equal initial cash sleeves, no rebalancing, no cash interest, 2018–October8 2026:

| Entry (exit at original common endpoint without initial stop) | CAGR | Portfolio maximum close-to-close drawdown | Mean stock exposure |
|---|---:|---:|---:|
| Arm immediately | 6.52% | −19.81% | 43.2% |
| First two-day RSI-MACD | 6.71% | −20.26% | 39.4% |
| **First daily StochRSI** | **8.15%** | −19.49% | 38.9% |
| Strict daily StochRSI→two-day RSI-MACD | 4.45% | −4.21% | **13.7%** |
| Same five stocks continuously held | **14.25%** | −20.51% | 100% |

The strict policy’s small drawdown is largely a **low-exposure** artifact. A hypothetical 1%-stop-risk sizing normalization would show still different returns; no capital weights are recommended from this chart. The favorable daily StochRSI entry CAGR is not robust validation because the source historical years and policy family were examined extensively and entry timing differs across overlapping episodes.

## V32 — Corrected SPY reserve overlay

Reuse the previously audited **V14 SPY reserve overlay engine** without altering its market-timing logic: stay in SPY when flat, exchange out of SPY at the observed eligible stock-entry open, and reenter SPY **at the close of the stock-exit day** rather than receiving SPY intraday return before an unknown stock exit. This corrects the earlier diagnosed SPY open-to-close lookahead. Model a 5bp ETF buy/sell fee plus existing stock fees. **Five mechanical tests passed** and all 216 existing stock paths were preserved.

Five-core, fixed equal starting sleeves, SPY reserve while idle, no rebalancing:

| Entry (fixed original watch endpoint exit) | Historical CAGR | Maximum drawdown |
|---|---:|---:|
| First two-day RSI-MACD | **16.66%** | −20.64% |
| First daily StochRSI | 16.40% | −21.26% |
| Arm immediately | 14.86% | −20.10% |
| Strict daily then two-day confirmation | **15.30%** | **−29.52%** |
| SPY buy/hold, same period | 14.59% | −33.72% |

Thus, keeping capital invested when no washout is active repairs some absolute return loss, but **strict sequencing remains behind the simpler two-day and daily approaches**, and its left-tail exposure approaches SPY in some episodes. In the13-peer panel, first-daily-Stoch endpoint overlay was about **14.53% CAGR**, slightly under SPY. No variant is verified SPY-beating prospective alpha; SPY factor exposure is the majority of risk in these overlays.

## V33 — Paired watch-level uncertainty and independent-cycle embargo

Compare every completed identical core long watch under alternative first entry versus the original first2D. Keep rejected watches in cash; use the SAME arm+126 endpoint. A second sensitivity accepts the earliest original master watch per stock, then suppresses all other watches for **126** market sessions regardless of their future outcomes. Resample **consecutive four-calendar-quarter blocks across common market episodes**, 4,000 times, retaining ticker correlations. This remains exploratory, not selection-adjusted for all V1–V33 research.

| Core-five, alternative minus first2D | All51 watches | Earliest-per-126-session n35 |
|---|---:|---:|
| Arm immediate | **+1.80pp** | +1.12pp |
| First daily StochRSI | **+0.11pp** | +1.85pp |
| Strict daily StochRSI then two-day RSI-MACD | **−5.39pp** | **−3.21pp** |

Core daily-Stoch versus2D exploratory shared-quarter interval for all51: **−2.32 to +2.26pp**, including zero. With 126-day spacing, also includes zero (**−0.55 to +3.48pp**). No one should choose daily StochRSI over2D on those point differences alone.

The strict sequential policy’s all-watch disadvantage versus2D retained a negative exploratory interval (**−8.31 to −2.88pp**) and remained negative after 126-day spacing (**−6.51 to −0.18pp**). In thirteen peers, similarly negative. This is evidence against making the specific, unusually strict **sequential** condition mandatory in the tested historical portfolio; it does NOT refute the wider multi-timeframe washout thesis, all other daily Stoch interpretations, or profitable conditional trades in different regimes.

## Final scientific verdict and needed next proof

**Supported as exploratory:** W+2W relative oscillator exhaustion is a useful historical context to research in some defensive compounders; short daily Stoch recovery and first native2D RSI-MACD are competitive entry-clocks; the strict cumulative sequential rule discards a large fraction of potential recoveries at the tested common126-session horizon.

**Not supported as proven:** a 100% future hit rate because14/14 historical filtered entries later finished positive; an automatic stop size inferred from that fraction; 2D vs1D precision alpha; robust transfer across peers; a universal regime gate; a beta/sector-neutral predictive probability; an implementable live sizing/trading policy.

**High-leverage next actions:** verify the user’s **exact RSI-MACD species and actual 2W candle-phase/developing-bar convention** against timestamped chart-native exports; preserve the October13 already-frozen [paper-only observation #9180](https://github.com/mastermindx-market-intelligence/macro/pull/9180), and subsequently collect truly future outcomes without rewriting definitions; add causal, release-time issuer guidance, revisions, actual volume/transaction and profitability/vintage data and effective rates/credit conditions. Avoid a new watcher or allocation control plane; existing Mastermind Entry Radar/market-data consumers should own prospective integration when admitted.

### Related research and source authority

- V11 historical corrected empirical study: https://github.com/mastermindx-market-intelligence/macro/pull/9034
- V12 independently owned exit-policy research: https://github.com/mastermindx-market-intelligence/macro/pull/9064
- V13–V20 portfolio, beta and earlier interval work: https://github.com/mastermindx-market-intelligence/macro/pull/9129
- V21–V23 dated historical watch/conditional context: https://github.com/mastermindx-market-intelligence/macro/pull/9174
- V24–V26 simultaneous model-selection and two-week phase stress test: https://github.com/mastermindx-market-intelligence/macro/pull/9176
- V27 October13 paper-only snapshot: https://github.com/mastermindx-market-intelligence/macro/pull/9180
