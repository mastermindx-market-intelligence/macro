# Defensive Nested Washouts V24–V26 — Independence, Candle Phase and Simultaneous-Inference Audit
**October 13, 2026 — research only. Market observations end October 8, 2026. No trade, allocation, deployment or live trigger.**

## Executive adjudication

The user observed that deeply washed-out **weekly plus two-week StochRSI**, followed by a shorter **RSI-MACD-on-RSI bullish crossover**, frequently precedes large recoveries in selected defensive compounders. Corrected V11 real-price analyses verified that this combination defined historically favorable crossover groups in MCD, WMT, WM, COST and PG. Follow-on V12–V23 studies showed substantial interim drawdowns, poor precision of a first fresh lower crossover, modest same-date peer selection effects, stronger relative appreciation in the **20th–63rd owned-session window**, and an apparent **+2.31 percentage-point beta-adjusted log-recovery advantage** for jointly oversold weekly+2W signals versus two-week-only signals.

**V24–V26 expose three important inferential weaknesses** in that last apparent advantage:

1. Multiple daily crossovers share the same longer market cycles. A 63-trading-session nonoverlap restriction reduces the core-five daily comparison from **74 joint versus 48 two-week-only observations** to **18 versus 10**, so the evidence count is much smaller than raw events imply. With a 126-session embargo there are just **5 versus 6**.
2. The result is sensitive to how the **two-week candle's absolute phase and developing-versus-completed values** are defined. Under identical lower cross dates and unchanged outcomes, the core-five daily joint-versus-two-week-only point difference ranges from **+1.60pp to +2.76pp** across four plausible conventions. At least 9.5–20.6% of the original core-five daily crossover labels change under nonbaseline conventions.
3. A shared-calendar-bootstrap approximate simultaneous interval across eligible present-family comparisons **includes zero under every convention**. No result has selection-adjusted qualification across the whole earlier research program.

**Verdict:** **historical contextual association = supported as exploratory**; **independent predictive alpha, parameter transfer, trade profitability, sizing and deployment = NOT PROVEN**. The strongest useful next step is to match the user's actual chart convention and freeze a prospective, dated observation cohort with point-in-time issuer and rates covariates. An apparent positive retrospective lower CI from a single selected configuration is insufficient.

## Provenance and specific tested rule

- Source authority: V11 merged via [Macro PR #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034). Research follow-ups remain separately owned: [V12 PR #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064), [V13–V20 PR #9129](https://github.com/mastermindx-market-intelligence/macro/pull/9129), and [V21–V23 PR #9174](https://github.com/mastermindx-market-intelligence/macro/pull/9174). This work does **not** rewrite or merge those candidates.
- Calculations use accepted **V22 derived all-crossover ledger: 2,771 complete lower crossovers** across 18 already-selected equities (2018–October 8 2026). The V24 and V25 event studies reuse the exact same future-return labels, no retuned indicator parameters, no newly acquired vendor bars and no unapproved V3/V4 operation.
- Indicator species: native RSI14, recursive EMA14(RSI)-EMA60(RSI), EMA5 line, StochRSI14/14/3/3. Source prices are final-vintage adjusted OHLC proxies; exact user chart output not independently reproduced.
- Four exclusive context states evaluated at each **completed 1D or 2D RSI-MACD bull cross**: JOINT (weekly K touched20 in latest3 completed W bars, two-week K touched20 in latest2 completed 2W bars and current two-week K<60); TWO_WEEK_ONLY; WEEKLY_ONLY; NEITHER. Require200 native completed weekly and2W warmup bars. UNKNOWN is not reclassified as NEITHER.
- Outcome is a *diagnostic difference*, not a new backtested trade: during **20th-owned-session close to63rd-owned-session close**, take each selected stock's log return minus its pre-signal trailing252-session SPY-beta times the same SPY segment log return, then subtract an equal-weight mean of the other four core or twelve peer residuals. Signal-time beta uses only information previously available.
- Co-occurring 1D and2D events are dependent and never treated as independent confirmation. Returns in adjacent 63-session windows overlap, and past stock prices have been repeatedly examined.

## V24: independent-entry challenge

To avoid choosing events based on their future profitability, sort all original RSI-MACD bull crosses by **(stock, lower frame, session)**. Accept the chronologically first lower cross and suppress *all* subsequent crosses in that stock/frame for a fixed **63** or **126** completed trading-session embargo, regardless of their W/2W context. This is a sensitivity test, **not** an optimized or advocated trading rule. The original 2,771 event rows become **904** (63-session) and **519** (126-session) globally.

**Core-five daily JOINT minus TWO_WEEK_ONLY:**

| Which observations count | JOINT events | TWO_WEEK_ONLY events | Mean beta-neutral recovery contrast |
|---|---:|---:|---:|
| All eligible crossovers | 74 | 48 | **+2.31pp** |
| Earliest entry / 63-session embargo | 18 | 10 | +1.68pp |
| Earliest entry / 126-session embargo | 5 | 6 | +0.63pp |

Under the predeclared requirement of at least eight separate event-active calendar quarters for **both** conditions, neither spaced core comparison qualifies for an interval. Results cannot be read as strong independent replication. The exact slope is vulnerable to a handful of original longer-cycle recoveries.

**Multiplicity check at the original 2W phase0 confirmed setting:** 12 contrast definitions = two panels × two lower entry frames × three context controls. Eleven met the basic quarterly coverage rule; core daily JOINT minus TWO_WEEK_ONLY retained +2.31pp point mean but its approximate 95% **simultaneous centered standardized bootstrap interval was -0.90 to +5.52pp**, crossing zero. This is **not** a correction for the hundreds of V1–V23 hypotheses investigated historically.

## V25: exact candle phase and developing-bar sensitivity

Recalculate only the **W and2W context state**, not lower triggers or future outcomes, for the fixed 2,771 original crossover dates. Four conventions: confirmed W+2W with phase0 or1; daily-close developing W+2W with phase0 or1. Absolute two-week phase anchored to a calendar Monday; 200 native complete-bar warmup retained. Developing observations start from preceding committed native state and the daily-close provisional native candle, never from the later finalized 2W value.

**Critical audit:** The phase0 completed convention recovered **all 2,771 original V22 classifications with ZERO mismatches**, providing identity between the old and new calculation. Other variants change status because of candle construction, not new trade selection.

For the **514 core-five daily lower crossover records**, comparison with the original phase0 completed labels:

| Long-bar method | Changed labels | JOINT events | TWO_WEEK_ONLY events | JOINT minus 2W-only relative log recovery |
|---|---:|---:|---:|---:|
| Confirmed, 2W phase0 | 0% | 74 | 48 | +2.31pp |
| Confirmed, 2W phase1 | 9.53% | 70 | 61 | +1.76pp |
| Developing, phase0 | 16.15% | 88 | 40 | +2.76pp |
| Developing, phase1 | 20.62% | 93 | 45 | +1.60pp |

The positive core point estimates do **not** license picking the chart convention with +2.76pp. Actual TradingView/terminal candle origins and the user's intended bar-close semantics must govern that decision. A developing daily-close state cannot be mistaken for an intraday tick signal or a final completed native 2W signal.

Peers13 daily had **negative JOINT minus 2W-only** point estimates under all four modes: approximately **-1.58 to -1.88pp**, with wide intervals. This heterogeneity is a competing explanation for the chosen core cohort's apparent edge, not an argument for universal defensive/sector rules.

## V26: common-shock adjustment across 48 contemporary hypotheses

Treat **4 two-week conventions × 2 panels × 2 lower frames × 3 non-joint controls = 48** possible audited contrasts as one explicit family. Of these, **46** met the rule of at least eight active calendar quarters per treated/control cell and at least95% bootstrap-valid draws. The remaining two are UNKNOWN, not negative results.

Resample **four consecutive calendar quarters**, 4,000 replicates, with the **same calendar-quarter resample indices applied to all stocks, contexts, frames and phase conventions**. Form each contrast's centered standardized deviations and obtain the 95th percentile of the maximum absolute deviation across the eligible family. Expand individual percentile intervals to include the resulting simultaneous bound. This is an approximate bootstrap **within this specifically defined family**, not a full data-snooping or causal inference correction for all earlier attempts.

| Core-five daily phase/mode | Point difference | Approximate simultaneous 95% interval (48 family, 46 eligible) |
|---|---:|---:|
| Confirmed, phase0 | **+2.31pp** | **-1.33 to +5.95pp** |
| Confirmed, phase1 | +1.76pp | -2.13 to +5.66pp |
| Developing, phase0 | +2.76pp | -1.97 to +7.49pp |
| Developing, phase1 | +1.60pp | -2.43 to +5.64pp |

**Every interval crosses zero**. The familywide standardized critical value is approximately **3.134** on these observations; the bootstrap construction does not assume independent ticker crossovers. A user-selected model mode, longer research run, larger pool of tests or different phase cannot substitute for an unexamined, prospectively fixed sample.

## Why this matters for the strategy

The core-five long-washout context is promising enough to make a **paper-only prospective research hypothesis**, but it is not qualified for a new live entry gate. Specifically:

- A double W/2W washout may describe a **common market repair** rather than an independent repeatable stock-specific turning-point predictor.
- **Two-week calendar phase and developing-bar semantics are first-order scientific inputs**, not harmless UI preferences.
- The recovery phase can mature over several weeks despite difficult interim price action and stop breaches; earlier V13–V20 analyses show that holding-period, risk budget and idle-capital economics dominate attractive fixed-endpoint win rates.
- The failure to transfer the core effect to thirteen peers makes **point-in-time economic drivers** the next priority: issuer earnings revisions and their publication timestamps; actual recurring unit demand, effective cost/input lags, cash generation; changes in real yields, credit spreads and risk premia; sector/peer participation and genuine business events.
- Do **not** retrospectively discover per-stock vetoes from the same already examined sample or fit year labels using future recession/earnings data.

## Verification, artifact law and unfinished qualification

**V24:** 9 mechanical tests pass; **V25:** 7; **V26:** 6; **22 total tests in newly delivered source**. V25 phase0 baseline classification identity: **2,771/2,771**. Event-count integrity across V25: **11,084 rows** (4 × 2,771). Shared-quarter 4,000-bootstrap family output: 48 contrasts, 46 eligible. Earlier V11/V12/V13–V23 accepted tests/results were reused and not rerun without a relevant change.

Full source/tests/specifications and derived CSV/JSON include SHA-256 member digests; archive contains **no vendor raw OHLC, original FRED records, credentials or live brokerage integrations**. Reproduction requires the original V11/V12 accepted data and source. The current research publication in GitHub is still a PR until separately merged under normal CI and review.

**DONE_FOR_THIS_PHASE:** V24–V26 original historical robustness questions are answered and verified. **NOT_DONE:** user-chart setting parity, prospectively timestamped future events, unbiased delisted-stock universe, independent price vendor, issuer/consensus release vintages, validated beta/factor benchmark, regime-dependent payoff qualification, account-level executable slippage/tax and portfolio sizing, and risk-bounded live entry adoption. No unseen future result, order or continuation daemon is claimed.

### Canonical source links

- V11 publication: https://github.com/mastermindx-market-intelligence/macro/pull/9034
- V12 independent follow-up: https://github.com/mastermindx-market-intelligence/macro/pull/9064
- V13–V20 study: https://github.com/mastermindx-market-intelligence/macro/pull/9129
- V21–V23 dated watch and conditional context: https://github.com/mastermindx-market-intelligence/macro/pull/9174
