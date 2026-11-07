# Defensive Nested Washout V34–V35: Ex-Ante Regime Adjudication and Frozen Dual-Timeframe Paper Observation

**Research date:** October 13, 2026. **Historical backtest cutoff:** October 8, 2026. **New paper observation cutoff:** October 13, 2026. **No orders, live signals, allocations, deployment or autonomous watcher.**

## Main findings

The user’s strategy combines unusually deep weekly/two-week StochRSI exhaustion with an earlier shorter-period RSI-MACD recovery confirmation, potentially sharpened by a daily StochRSI bottom and K/D crossover. The V11–V33 research repeatedly found attractive historical recovery context, but no selection-adjusted proof of a reliable entry-day alpha or universally optimal stop. V28–V33 specifically adjudicated the **native two-day RSI-MACD + daily StochRSI** setup: a recent daily washout selected14/14 eventually positive126-owned-session core entries, but6/14 hit a5% stop before8% target; a strict daily-then-two-day mandatory sequence substantially reduced the all-original-watch payoff because of missed winners and idle cash. The daily-only and2D-only entry clocks were comparable rather than decisively superior.

**V34** tests whether that failure/benefit is regime-conditional when regime is assigned **using only data available at the original W+2W watch arm**, not future recession/market labels. **V35** freezes the exact multi-timeframe *paper* status as of October13 using already-acquired provider observations, before the next equity-market session’s outcomes.

### Scientific verdict

- A prior SPY-based stress label does **not** establish a simple "avoid all bear-market washout buys" rule. Some stress entries recovered strongly, but broad SPY also recovered, and core stress subsamples were thin.
- The original long-cycle W+2W watch plus first2D or first-daily-Stoch entries remain research hypotheses. Requiring daily Stoch confirmation followed by2D RSI-MACD remains substantially too restrictive on the tested fixed-episode payoff objective.
- The October13 paper freeze establishes a legally timestamped forward reference, **not evidence that October14 or later returns are profitable**. No source contains future outcomes or a real broker fill.

## Evidence custody

Earlier studies preserve original accepted source: [V11 merged #9034](https://github.com/mastermindx-market-intelligence/macro/pull/9034), independently owned [V12 #9064](https://github.com/mastermindx-market-intelligence/macro/pull/9064), [V13–V20 #9129](https://github.com/mastermindx-market-intelligence/macro/pull/9129), [V21–V23 #9174](https://github.com/mastermindx-market-intelligence/macro/pull/9174), [V24–V26 #9176](https://github.com/mastermindx-market-intelligence/macro/pull/9176), [V27 Oct13 after-close initial paper freeze #9180](https://github.com/mastermindx-market-intelligence/macro/pull/9180) and [V28–V33 exact daily/2D test #9195](https://github.com/mastermindx-market-intelligence/macro/pull/9195). These were not edited by this continuation.

Historical outcomes in V34 come from exactly the preexisting **198 W+2W master episodes** with four frozen entry policies and common arm+126-session outcome; 57 watches were in the five core stocks and141 in the thirteen other original equities, with 51 and131 complete historical opportunities. Source prices are the original accepted V12 final-vintage adjusted-price proxies ending October8 2026. No V3 previously refused result, V4 earlier-history operation or alternate carrier bypass was used.

V35 is a **different observation class**, computed without recomputing a historical strategy winner: it reuses the V27 after-close **October13** vendor snapshot of19 original symbols, originally acquired approximately **2026-10-13T21:38–21:40Z**. V35's study definitions were frozen at **2026-10-14T01:15:57Z (9:15 p.m. Eastern on October13)**; the derived status ledger was frozen at **2026-10-14T01:17:50Z (9:17 p.m. Eastern)**. The next Oct14 U.S. session was still unobserved.

No independent price vendor comparison, user-chart parity, SEC release-time fundamental join, options/live execution or full dividend-cashbook exists. No raw vendor bar bytes are included in this publication; they remain on the authorized M2 Studio.

## V34: ex-ante market conditions at the original watch

The existing V11 regime code defines market stress using SPY's **prior observed trailing126-session drawdown at or below−10%** or annualized **trailing20-session volatility at or above30%**. Stress is split by whether the known trailing10-session SPY return is positive (repair) or not (worsening). Outside stress, SPY above trailing200SMA is SUPPORTED; otherwise TRANSITION. This is an observable, coarse statistical label **at the long-washout arm close**; it is not a causal macro shock decomposition or a future NBER label.

**Core-five, all original W+2W opportunities, same arm+126 endpoint and following-open costs:**

| Entry-time market context | Complete long watches | First two-day RSI-MACD (cash on skips) | SPY holding on same watch interval | Strict daily StochRSI→2D |
|---|---:|---:|---:|---:|
| **SUPPORTED** | 35 | +7.50% | +6.33% | +4.10% (12/35 entries) |
| **STRESS_WORSENING** | 10 | +17.45% | +17.94% | +4.14% (2/10 entries) |
| **STRESS_REPAIR** | 2 | +5.50% | +3.83% | 0% (no entries) |
| **TRANSITION** | 4 | +6.43% | +3.89% | +3.45% (1/4 entry) |

The STRESS_REPAIR and TRANSITION groups are far too small for independent conclusions. Even the ten stress-worsening watches are correlated. The large positive stressed absolute return largely tracks a simultaneous broad-market rebound; **the two-day rule did not materially beat SPY in that group**. Hard-ban stressed entries could miss gains, but accepting them is not necessarily a unique stock-selection edge.

V34 additionally records whether SPY entered STRESS_WORSENING **after** the arm date, but this is explicitly an **outcome label only**. It cannot become a contemporaneous or allegedly predictive entry feature after seeing those paths. Seven V34 source/mechanical tests passed, including invariance of prior regime labels to subsequent price changes, same-window SPY benchmarks and right-censored future intervals. All 792 original event-policy rows were retained; incomplete endpoints remain UNKNOWN, not automatic losses.

## V35: exact daily StochRSI/two-day RSI-MACD paper freeze

Using the previously accepted V27 snapshot through **October13**, V35 independently evaluates the following three prospective paper-only entry definitions **inside the same original W+2W watch**:

1. **FIRST_2D_MACDRSI:** first confirmed native2D RSI-MACD bullish crossover, observed at native close and followed by an as-yet-unobserved next-open candidate.
2. **FIRST_DAILY_STOCH:** first native1D StochRSI K>D bullish crossover after W+2W watch arming with K having reached <=20 within the latest five completed daily readings.
3. **DAILY_STOCH_THEN_2D:** earliest confirmed native2D RSI-MACD bullish crossover after an in-force daily K>D crossover since the watch arm, within five completed daily sessions, with daily K>=D and recent K<=20.

Slow contexts use completed W/2W and a separately marked **daily-close developing W/2W** view, both with original V11 study’s 14/60/5-on-RSI species, StochRSI14/14/3/3, phase0, 200 completed W/2W warmup and a42-session watch/10-clear-session rearm. Exact user chart species and phase remain UNVERIFIED.

**Frozen at October13 2026 9:17 p.m. Eastern:** 18 companies ×3 entry methods ×2 long-state conventions = **108 paper ledger rows**. No October14 quote/return was present, and all signal state rows explicitly say **broker_filled=False** and **live_recommendation=False**.

The confirmed W+2W core-five status:

| Stock | Relevant historical status at October13 cutoff | New strict cross on October13? |
|---|---|---|
| MCD | W+2W watch armed Sep11; daily Stoch short cross occurred Sep14; two-day RSI-MACD confirmation **not yet observed** | No |
| WM | W+2W watch armed Sep18; daily Stoch recovery occurred Sep24; strict combined confirmation had occurred Oct7 | No |
| WMT | No currently active long watch | No |
| COST | No currently active long watch | No |
| PG | No currently active long watch | No |

Across all18 stocks, **zero new confirmed-bar strict-sequence entries** were observed on October13. A **CLX two-day crossover arose only under the developing W+2W view**; it is not equivalent to final completed W+2W confirmation, chart parity or a real fill.

V35 was **not** launched as a watcher, scheduled job or production Entry Radar source. It is a one-time observation whose future dated outcomes will become eligible for study only when those dates occur and an authorized owner collects genuinely new data. An old modeled signal date remains **EARLIER_SIGNAL_NOT_POSITION**, never an inferred open portfolio holding.

Seven fresh V35 tests passed: no-future signal classification, last-bar next-open-unobserved distinction, no automatic broker receipt, out-of-watch confirmation exclusion and future price perturbation invariance. Verified market data came from V27’s19/19 accepted same-vendor 4,220-session source; V35 issued **zero new market vendor requests**.

## Research decision and exact continuation

**No setting change to Macro, Terminal or Bot is justified.** The stronger interpretation is to treat deep W+2W StochRSI exhaustion as a *long-cycle recovery hypothesis*, and the daily Stoch/2D RSI-MACD as competing/optional short-term execution clocks whose required order must be justified by all-watch and capital-account comparisons.

Near-term legitimate next empirical proof: obtain user's actual native chart export and confirm RSI-MACD species, two-week candle phase, developing-bar behavior and 1D/2D session boundaries. Without that parity, the study is a pinned **house-method proxy**. Future already-frozen Oct13 paper entries should be measured only as truly future outcomes, using predeclared 20/63/126-session and stop-first metrics, while preserving empty/no-signal watches and original observed market/fundamental context. Complete issuer/credit/real-yield interpretations only with original filing/vintage timestamps and separate causal hypotheses, not retrospective return-selected vetoes.

Status: **historical exploratory research completed, prospective observation baseline frozen, live trading and statistically qualified alpha NOT PROVEN.** No automatic background monitoring is claimed.
