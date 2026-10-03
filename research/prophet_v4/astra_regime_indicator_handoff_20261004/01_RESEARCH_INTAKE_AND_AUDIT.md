# Research intake, quantitative record and adversarial audit

## Evidence status

This document transfers the complete substantive findings of the supplied Deep Research report, the earlier discussion and the subsequent repository census. It consolidates repetition rather than presenting a byte-for-byte transcript. All supplied quantitative findings are retained below. A number quoted from that report is not a number recomputed by this handoff task.

The source report was titled **Prophet, Momentum-Timeframe Failure, and the New Regime Problem**, delivered 2026-10-02. Its report text was available in the conversation. Many internal file citations in its metadata were explicitly marked invalid; their source files cannot be recovered merely by reusing those citation IDs. This package replaces that apparent certainty with named repository sources, explicit verification levels and unresolved evidence tasks. The report's overall widget said completed even though its step state still showed regime segmentation and final-rule production pending. Treat the report as a substantial research synthesis, not proof of a freshly executed end-to-end backtest campaign.

Evidence classes used here:

- **Source-verified:** implementation or a research/decision document was read at an exact commit. This verifies what that source contains, not that production is running it or that its statistics were recomputed.
- **Externally checked:** a primary public source was inspected during handoff preparation.
- **Reported development evidence:** quantitative finding supplied by the earlier research; requires raw artifact/code/data reconstruction before a new empirical claim.
- **Hypothesis / proposal:** explanatory or architectural idea to test. It has no score, gate, size or trading authority.

## 1. What the Chairman is actually asking

The Chairman observed that previously useful indicator timeframes seem to have changed: daily momentum has become hard to trade, and 3D confirmations may arrive near the end of a fast daily cycle. He proposed that poor breadth, rising real yields and narrow AI/semiconductor leadership shorten the time during which an arbitrary stock receives persistent demand. In broader, liquidity-supportive environments, a daily turn may propagate into a 3D/weekly move; in a rotational market the capital may leave before this happens.

He wants this investigated across Prophet's actual record, the existing research library, the terminal indicator suite and the large technical catalog. The task is to expand well beyond MACD/RSI into regime-specific indicator families, sequences, confluences, timeframes, theme/subtheme leadership and management. The end product must be built, integrated and measured, not just planned.

Preserve two distinct ambitions: lower admission of severe losers while retaining large winners, and recognize when a longer-horizon cycle-capture strategy should remain active instead of redesigning everything for short rotations. Maximizing hit rate by removing difficult opportunities or reducing exposure to almost zero is not the requested outcome.

## 2. The source report's headline diagnosis

The report proposed four interacting explanations:

1. Overnight trading changes the information in some intraday series.
2. Legacy 2D/3D bar anchoring and research reproducibility defects can change signals.
3. Momentum continuation depends on market, participation and liquidity conditions.
4. Prophet sometimes admits a good company after most of the tradable price move has occurred.

Its main technical hypothesis was **older constructive 3D structure plus fresh 2D reacceleration**, rather than waiting for a new 3D cross. It rejected simply replacing every slow signal with a fast one, rejected a blanket daily-overbought veto, and proposed making theme/subtheme leadership and remaining opportunity explicit. It also proposed different holding behavior by environment.

These are useful mechanisms to investigate. The report overstated the strength of several conclusions and conflated some different implementations. The corrected assessment is in section 8.

## 3. Market context: claims and checks

### September real yields

The report gave the following 10-year real-yield observations: September 1, 2026: 2.44%; September 10: 2.55%; September 11: 2.60%; September 16: 2.68%; September 23: 2.76%; September 24: 2.85%; September 28: 2.90%; September 30: 2.93%. Its stated September 1-to-30 change is 49 basis points.

**Externally checked:** the Treasury's September 2026 Daily Treasury Par Real Yield Curve table contains those values. This establishes a descriptive move, not a causal explanation of individual Prophet outcomes. Treasury par real-curve observations and the exact DFII10 series required by an internal preregistration must not be silently substituted for each other.

Primary source: https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?field_tdr_date_value=202609&type=daily_treasury_real_yield_curve

### Nominal bonds and breadth

The report described September as the worst U.S. government-bond month in four years and quoted a roughly 5.3% nominal 10-year yield after a rise exceeding 50 basis points. It quoted September S&P 500 performance near +0.2%, equal-weight S&P performance around -4.4%, and Nasdaq performance around +2.4%. These were media-sourced figures in the supplied report, not values recomputed during this handoff.

**Required repair:** rebuild exact endpoint, price/total-return and benchmark definitions from approved price/index sources. Distinguish the S&P equal-weight index from an RSP ETF return; distinguish intraday commentary from final month-end marks. The source report also included contemporary articles with slightly different September endpoint descriptions. Do not paper over those differences.

Report source URLs, retained for audit:
- https://www.ft.com/content/39de7709-7b5b-42f6-ad90-df50f1308ea2
- https://www.barrons.com/livecoverage/stock-market-news-today-093026/card/the-s-p-500-is-up-in-september-but-market-breadth-has-been-terrible-V4CTWLdzn650rabk6Vrs
- https://www.barrons.com/articles/divided-stock-market-sp-500-rally-6be5575e
- https://www.marketwatch.com/story/the-stock-market-is-anything-but-normal-right-now-and-these-charts-show-it-91ea187d

### Overnight activity

**Externally checked:** the SEC September 2026 roundtable memorandum, executive summary on printed page 2 and concentration table/takeaway on printed page 23, reports August overnight activity at 0.9% of total NMS share volume on an average trade date. Overnight volume was up 359% year over year but down 27% month over month. The session-specific ten most active stocks accounted for 43.4% of overnight share volume versus 10.3% during regular hours. The most-active sets are not identical across sessions.

Primary source: https://www.sec.gov/files/2026_TM_Overnight_Trading_Roundtable_Memo_090926.pdf

The original inference that such a small volume share cannot materially affect a 3D signal is too strong. Volume share is not price-discovery share, and price changes in one session can propagate into later closes. The appropriate conclusion is that aggregate volume alone neither proves nor rules out the proposed mechanism. A 3D candle can be economically affected by overnight information even when its arithmetic bar clock is unchanged.

The report also cited TradingView's 24-hour intraday series behavior. Recheck the exact current symbol, venue, session setting, daily-feed definition, timezone and bar anchor before comparing a 12H chart with a daily chart. A vendor's daily candle is not necessarily two user-selected 12H candles joined together.

Source carried from the report: https://www.tradingview.com/support/solutions/43000790593-how-to-view-the-24-hour-market-and-overnight-trading-sessions/

## 4. Prophet track-record figures from the supplied report

### The small live plan ledger

The report's clean aggregate was an **August 12 audit**, not a current October lifetime performance calculation. It reported:

| Statistic | Reported result |
|---|---:|
| Closed plans | 28 |
| Positive outcomes | 9 |
| Positive-return rate | 32.1% |
| Mean stock return | +0.51% |
| Median stock return | -4.60% |
| Winners' mean | +19.73% |
| Losers' mean | -8.59% |
| Approximate payoff ratio | 2.30x |
| t-statistic of mean | +0.178 |
| Approximate 95% interval around mean | -5.14% to +6.17% |

An earlier 16-closed-plan reading reportedly had a 12.5% win rate, -5.03% mean and -5.51% median. The report correctly emphasized that neither small sample proves skill. Its confidence interval and t-statistic must be reproduced from the exact returns and stated estimator, not copied as independently validated calculations.

It said the headline plan ledger lacked a benchmark field even though a board grader used SPY and sector ETFs. Resolve whether this was repaired after August; do not infer the current schema from the old audit. A board admission, a plan, a displayed opportunity and an executed trade are different populations.

Examples copied from the report's later ledger inspection were VSEC -17.44%, UEC -10.48%, ADAM -9.17%, XPEL -9.11%, WT +11.62%, DAN +5.45% and FCX +3.65%. These are illustrative rows, not a representative aggregate and not verified realized user P&L.

**Interpretation to retain:** large-winner asymmetry may make admission quality and severe-loss avoidance more valuable than a raw hit-rate target. **Interpretation not earned:** that any proposed filter preserves the winners while removing the losers.

### Phase-21 development population

The report described 209 matured V3 episodes, eight admission dates and 181 tickers. It explicitly said this set had already been inspected and was development evidence. The current Phase-22 preregistration confirms the outcome-contamination boundary and cites the Studio Phase-21 synthesis SHA-256:

`37b5ac78bd93c6d8ebc9b7effb260eb00c0fb77ef8c3259ecd29c231bd124ed6`

This hash is a retrieval/checksum lead from a source document; the underlying file was not recovered and rehashed by this handoff task.

The report supplied these date-block relationships:

| Relationship across the eight admission blocks | Reported Spearman correlation |
|---|---:|
| Mean original outcome versus realized real-yield rise during hold | -0.595 |
| Benefit from truncating near five sessions versus realized yield rise | +0.762 |
| Mean original outcome versus later RSP-SPY relative performance | +0.762 |
| Benefit of shorter hold versus later RSP-SPY relative performance | -0.762 |

These use future realized conditions and only eight date blocks. They can motivate a holding-period mechanism; they are not decision-time predictors, causal estimates or a validated day-five exit.

### Opportunity consumption and cycle age

Reported development findings:

- Entries within approximately 5% of their previous high contained zero major winners and six severe losers, with mean outcome near -4.25%.
- Severe losers had mean daily bullish-cross age near seven sessions and StochRSI K near 77.
- Large winners had mean daily bullish-cross age near 13 sessions and StochRSI K near 82.
- Severe losers' most recent 2D bullish cross averaged about 25 sessions old, median about 18.
- Large winners' 2D cross averaged about 11 sessions old, median about three.
- Winners with constructive 2D and 3D structure often appeared to have a renewed 2D acceleration inside a substantially older 3D structure.

Do not mine a 5%-from-high threshold, cross-age cutoff, oscillator veto or new hold optimum from these already-inspected episodes. The report's term bullish cross is insufficiently precise: recover the exact indicator implementation for each table. In particular, the prospective same-cut 2D StochRSI event is not automatically the same variable as an old 2D RSI-MACD cross-age statistic.

### Mechanical earlier-entry replay

The supplied table was:

| Entry rule applied to stocks Prophet eventually selected | Mean lead versus original entry | Change in mean return | Severe losses | Large winners |
|---|---:|---:|---:|---:|
| Existing Prophet entry | baseline | baseline approximately -2.0% | 17 | 8 |
| Previous 1D cross | about 7 sessions earlier | about +0.9 percentage points | 26 | 19 |
| Previous 2D cross | about 30 sessions earlier | about +2.2 percentage points | 42 | 31 |
| Previous 3D cross | about 48 sessions earlier | about +5.2 percentage points | 38 | 48 |

The retrospective stock universe is conditioned on later Prophet selection. That is a serious selection/look-ahead problem for an implementable early-entry strategy. Even under that favorable conditioning the loss tail expanded. The table does not establish that early entry has negative value either; it establishes that a real earlier-entry policy must be tested on all eligible names at the earlier decision time.

### The old admission-sequence defect

The report stated that 5,926 of 7,973 episodes, about 74%, entered a branch in which the daily cross was already in force before the 3D leg, despite a verbal label implying 3D washout followed by fresh daily confirmation. Preserve this as a reported historical semantic audit. Recover its era, exact branch and subsequent fix before treating it as a current implementation defect.

## 5. Earlier bar-clock and implementation findings

The earlier research correctly identified a historical problem: pandas business-day resampling could phase 2B/3B bins to a caller's first timestamp, and Monday-Friday calendars are not actual exchange-session calendars. But the continuation census found the repair already present.

Current source, read at Macro `f5c2e829fef0a9891df0527a4bf74f280aaa0813`, explicitly states:

- absolute session-calendar anchoring is used;
- the anchor era is `abs-session-2026-08-06`;
- the technical cascade is RSI-MACD, not price MACD;
- RSI length is 14; fast/base/signal lengths are 14/60/5;
- StochRSI is 14/3/3;
- T1/T2 have immutable native event dates; projected T3/T4 have null event dates and their own observation semantics;
- T2 already carries weight 1.00 versus T1 0.90 in the documented cascade, reflecting an earlier operator preference for earlier entries.

The historical `session_anchor.py` inspected in the preceding continuation explains a fixed US calendar from 1950-01-03, non-US reference-index calendars, and caveats for unsupported markets or observations beyond reference coverage. These deserve audit, not wholesale replacement. The current calibration and actual deployed callers still need verification.

Important correction to the proposed invariant: identical bar boundaries and completed-session cutoffs should be guaranteed for a shared calendar/version. Indicator values from arbitrarily short histories need not be identical because Wilder/EMA initialization differs. Tests must use a shared seed/state or sufficient common warmup with a declared tolerance. Do not fail a correct anchoring repair because a newly initialized EMA differs.

Weekly is a calendar-week object, not necessarily a fixed five-session bar; 2D/3D phase choices are model choices. Preserve incumbent semantics, compare alternate phases as registered robustness checks and never select the best phase after seeing outcomes.

## 6. Contrary evidence the source report omitted

The existing `REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md` records a scoped null for a broad per-family reliability table conditioned on a market label and graded on forward drawdown. Its August analysis reported:

| Term | Reported magnitude |
|---|---:|
| Signal-family main effect | 3.59 percentage points |
| Regime main effect | 0.95 percentage points |
| Largest single interaction | 1.49 percentage points |

The source reports 57,642 matured signals across 763 months, only five of 15 interaction confidence intervals excluding zero, large effects in thin cells, and 8/13 era-split sign stability. It also reports rich regime coverage at roughly 0.4% of a 58,149-row record, and an older board sample of 2,282 rows spanning only 18 sessions with no useful contrast on several regime variables.

These are a source-verified historical research result, not a fresh re-run. Their population and targets differ from a Prophet-specific entry/holding interaction. They nevertheless prevent claiming that broad regime-conditioned ranking has already been proven.

The same source introduced `engine/regime_conditioning_coverage.py` with coverage, number-of-states and distinct-months-per-state checks. Reuse and remeasure it. Thousands of same-day names do not create thousands of independent macro episodes.

The August 14 decision on earned conditional authority subsequently clarified that an old construction's failure does not permanently ban an information family. The correct path is a genuinely different, preregistered construction with adequate point-in-time data and an earned promotion. It is not an indefinite zero-authority doctrine and not a license to revive a killed composite under a new name.

## 7. What Phase 22 actually freezes

The current preregistration was read directly. Operation: `prophet-phase22-fast-cycle-regime-prereg-20260919-sol-001`. Parent: `WS:PROPHET-US-V4-RECOVERY`; expert owner: `WS:LIVE-ENTRY-RADAR`; evaluation owners: Evaluation OS / QLedger / W5.

Population: every future LIVE_FORWARD primary `C2_1D_TURN@1` event after an explicit start receipt, not only names later selected by Prophet. Conditioner: same-cut `C4_MTF_TURN@1.d2.turn`, a strict confirmed 2D StochRSI K/D bullish cross. C4 cannot fire independently and does not get a new directional family.

The start requires accepted private evidence transport; a real RTH event through spool, existing forward.parquet and QLedger; same-cut C4 durability without changing C2 identity; owner-qualified DFII10 availability/first-known clocks; TrialLedger registration before any target outcome read; and a recorded live-forward epoch. A frozen document does not prove these prerequisites are complete.

Q1 primary outcome is existing W5 H10 `excess_net`. Estimate the difference of within-decision-date arm means, then block-bootstrap by decision week. Missing C4 stays separate and never becomes false.

Q2 is a prespecified interaction. Real-yield change uses the latest qualified observation available before the event relative to five completed market sessions earlier. Breadth uses RSP/SPY over the prior five completed sessions ending at T-1. Hidden fragility is positive yield impulse with negative relative breadth; relief/broadening is nonpositive yield impulse with nonnegative relative breadth. Mixed and unavailable remain distinct. The difference-in-differences direction is explicitly NOT assumed.

Per-arm confirmatory floors: at least 30 episodes, 12 distinct decision months and name effective-N of at least eight. No return/statistic peek before the applicable floor. At the first qualified read use 5,000 decision-week bootstrap draws with seed 20260919. Fixed diagnostics include H10 absolute net, H5 excess/net, false starts, <=-10% loss incidence, >=+10% winners and payoff contribution, MAE/MFE, time-to-positive, C4 3D/recent-washout states and B3 maturity/failure paths.

Historical latest-revised FRED rows cannot be retroactively labeled first-known DFII10 observations. No threshold rescue, alternate lookback or new horizon can be added after results are visible. No supportive result automatically becomes a live gate.

## 8. Adjudication of the original recommendations

| Original recommendation or interpretation | Handoff ruling |
|---|---|
| 24h trading explains the change in indicators | Plausible for some session-sensitive measurements; not identified as the principal cause. Test exposure and price-discovery alternatives. |
| 3D is broken and must be replaced | Not established. Different strategies can legitimately use different clocks. |
| Fix the 2D/3D anchor first | Verify and extend the existing repair; do not build a second calendar or claim it is absent. |
| Fresh 2D acceleration is the strongest challenger | Worth testing, but split RSI-MACD freshness, StochRSI same-cut turns and other reacceleration definitions into distinct registered hypotheses. |
| Remove 3D as a universal gate now | Audit whether it is universal at all in current source, then compare alternatives under existing promotion law. No immediate production deletion is justified by this report. |
| Only use leading themes in narrow markets | Test incremental value versus simple stock RS, sector controls, unfiltered same-date selection and cash/exposure controls; preserve emerging themes and non-theme idiosyncratic catalysts. |
| Daily overbought should be vetoed | Contradicted by the reported winner tail; no blanket veto. |
| Real rates up implies poor momentum | Not universal. Separate growth, inflation, term-premium, credit, financing and earnings channels. |
| Multiplicative quality Q = theme x catalyst x opportunity x regime x impulse | Conceptual checklist only. Uncalibrated inputs are not probabilities and multiplication can make missing data silently annihilate a candidate. No such universal score is approved. |
| Theme Persistence Score as weighted sum of RS/breadth/revisions/flow minus crowding | A proposed feature family, not an earned formula. GMI/ThemeState remains owner. |
| Hold five days in bad regimes | An outcome-inspected diagnostic, not an optimized or validated exit rule. |
| Academic momentum research proves Prophet's 3D rule | False transport. Portfolio momentum and long-only short-horizon RSI-MACD setups are not the same strategy. |

The NBER abstract for Daniel/Moskowitz was checked. It describes momentum crashes following declines in high-volatility states, contemporaneous with market rebounds, and a dynamic momentum strategy. In particular, rebound behavior of prior losers and a long-short momentum portfolio need not transfer to Prophet's long-only entry problem. Use it as motivation, not an effect-size prior imported into the product.

Primary reference: https://www.nber.org/papers/w20439

Other literature carried from the report for targeted review, not freshly reproduced here:
- Cooper, Gutierrez and Hameed, Market States and Momentum: https://rogutierrez.net/files/Market-states-momentum_2004.pdf . The source report quotes +0.93% monthly after positive states and -0.37% after negative states for its six-month strategy over 1929-1995. Verify definitions and portfolio construction before reuse.
- Moskowitz and Grinblatt, Do Industries Explain Momentum?: https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146 . Industry momentum motivates group controls; it does not validate current AI subtheme membership or a hot-theme gate.

## 9. The scientific questions that survive the audit

The central question is not which timeframe wins. It is whether additional information about state, group participation, technical sequence and elapsed price response changes the conditional distribution of future outcomes enough to improve a practical decision after cost.

Separate five estimands: (a) baseline market effect; (b) family/setup main effect; (c) family-by-state interaction; (d) value of selecting a different clock after accounting for different memory lengths and signal frequency; (e) value of a complete deployed selection/management policy at comparable exposure.

A confirmation-lag mechanism is supported only if the observed process really runs out of favorable follow-through before slow confirmation, and a pre-decision observable identifies the vulnerable cases. A future market collapse explaining a loss is not an available entry veto. A regime label associated with generally low returns is not automatically useful for choosing one indicator over another.

The architecture should keep structural context, fresh impulse, remaining-opportunity descriptors, catalyst evidence, current entry availability and hold policy separately inspectable. This is a proposed modeling decomposition, not an assertion that all its variables are independently informative.

## 10. What was not done

No fresh multi-decade Prophet replay, new 12H/1D/2D/3D/weekly cross-indicator battery, updated full live-track-record recomputation, production cutover, worker execution or prospective Phase-22 verdict is established by the visible continuation. Source reads and the external checks above are the verified work. The next owner must obtain exact data/code/config artifacts, execute the experiments and produce a reproducible result bundle before making stronger claims.
