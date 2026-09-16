# SPY 0DTE Credit-Spread Forensic + Falsification Prereg

**Date:** 2026-09-16  
**Status:** FROZEN RESEARCH SPEC — **NO TRADE / SCORE / SIZING AUTHORITY**  
**Chairman scope:** continue the Caleb Gregory / OPG daily-SPY-credit-spread investigation and determine whether a reproducible, correction-safe Mastermind strategy exists.  
**Base revision:** `e729d0fd9d48868b49a1911d4098c689b3d373bd`  
**Relationship to canonical programs:** this is a bounded falsification study. It does **not** amend `research/OPTIONS_ALPHA_MASTERPLAN.md`, does not create a 0DTE production desk, and does not bypass validate-before-score doctrine. Existing GEX, option-surface, chain-snapshot, event, ledger, and validation planes are reused; duplicate stores/engines are a build error.

---

## 0. Decision question

Can the publicly described OPG/Caleb process — same-day SPY vertical credit spreads selected after the open using gap/price action, implied-volatility richness, gamma context and conservative strike placement — be translated into a deterministic point-in-time rule that has **positive expectancy after executable costs**, survives strict out-of-sample testing, and retains acceptable left-tail behavior across regimes?

A 95%+ win rate is **not** the success criterion. The strategy passes only if net expectancy, drawdown, expected shortfall, robustness and execution realism pass together.

### Falsifier

The thesis is rejected for production use if any of the following remains true after the frozen test:

1. net expectancy is non-positive after executable quote + fee assumptions;
2. apparent edge disappears out of sample or is concentrated in one short regime;
3. gamma features do not add material incremental value over price/IV/event controls;
4. tail losses erase the carry under plausible stop/fill mechanics;
5. point-in-time data cannot reproduce the decision state without leakage;
6. strategy requires discretionary hindsight that cannot be frozen before outcome observation.

---

## 1. What the public record actually supports

### 1.1 Self-reported results

OPG's 2026-08-14 retrospective states that the experiment sells same-day SPY credit spreads, mainly bull puts and bear calls, and uses evolving GEX to position the short strike beyond areas believed likely to influence price. It reports 21 profitable days / 1 losing day through day 22, net realized profit $12,959.53, gross winning P&L $15,359.53 and about $2,400 gross losses. The sole loss was a bear-call session in which SPY continued higher by more than 1.75%; the article explicitly identifies strong directional order flow overwhelming the gamma structure as the primary danger.

By the 2026-09-15 newsletter, OPG reports a 755/753 bull put closed for $0.02, +$1,067.36 for the prior session, 30 consecutive profitable counted sessions, 41 wins in the latest 42 counted sessions, and cumulative net profit of $30,298.39. OPG separately states that the experiment began with $10,000.

These are **self-reported trading results from a commercial trading-alert publisher**, not independently audited broker records. They are useful for reconstructing the hypothesis, not for establishing external validity.

### 1.2 Reconstructed public mechanics

High-confidence features repeated across OPG posts:

- underlying: SPY;
- expiry: same day / 0DTE;
- structure: defined-risk vertical credit spread, mostly bull put or bear call;
- common width in explicit examples: $2;
- common target credit in explicit examples: roughly $0.10 / $10 per spread;
- live decision after the open rather than a fixed pre-open direction;
- uses live GEX as context for volatility/containment and strike placement;
- wants the short strike outside the perceived action / major gamma zone;
- on red opening gaps/flushes, often looks for a bull put below the move when reversal/containment is plausible;
- on green gaps/spikes, often looks for a bear call above the move when overhead containment/fade is plausible;
- seeks rich opening IV, then benefits from IV contraction + theta decay + possible mean reversion;
- can wait until later in the session when the opening state is unclear;
- uses a standard-deviation / projected-move concept as another strike-location input;
- takes profit early when the spread collapses in value; public examples include $0.10 entry credit and ~$0.02 buyback roughly two hours later;
- generally avoids FOMC-style binary-event conditions;
- public risk discussion recognizes runaway directional flow as the main failure state, but does **not** publish a deterministic stop-loss / sizing algorithm.

### 1.3 Sample arithmetic

At 41 wins / 1 loss over 42 counted sessions:

- observed winning-session rate: **97.619%**;
- Wilson 95% interval for the underlying win probability: **87.68%–99.58%**;
- cumulative net: **$30,298.39**;
- if the one disclosed loss remains approximately $2,400, implied gross winning P&L is **$32,698.39**;
- mean winning-session P&L: **$797.52**;
- mean P&L per counted session: **$721.39**;
- observed profit factor: **13.62**;
- disclosed loss / mean winning session: **3.01×**.

The observed streak is not enough to infer a true win probability above the economic break-even rate of a low-credit spread. If true session win probability were 95%, observing at least 41 wins in 42 occurs with probability about **37.2%**. Even with a true 93% win probability it occurs about **19.7%** of the time. The streak is therefore compatible with several underlying hit rates that may or may not be profitable depending on loss size and costs.

### 1.4 The structural payoff problem

For a $2-wide vertical sold for $0.10:

- maximum credit = $10/spread;
- maximum expiration loss = $190/spread;
- binary hold-to-settlement break-even hit rate = **95.0%** before costs;
- if the typical winner is closed at $0.02, gross captured profit is $8/spread;
- full-loss / typical captured-win ratio = **23.75×**;
- corresponding break-even hit rate = **95.96%** before commissions/slippage.

One explicit OPG example says a 759/757 bull put was sold at 9:35 for $10 credit, repurchased near $2 about two hours later, with $1,500 profit. Purely arithmetically, ~$1,500 / $8 implies about 187–188 spreads before fees/rounding; a 188-spread $0.10-credit, $2-wide position has ~$35,720 of defined maximum expiration loss. That does **not** prove the account actually carried that exact risk — fills, fees, size, account semantics and reported rounding are not independently verified — but it creates a material reconciliation question before any sizing model may be copied.

**Ruling:** treat OPG's position sizing as **unknown**. Reconstruct entry/exit logic first; Mastermind must derive its own tail-risk budget from validated evidence.

---

## 2. External evidence that changes the design

### 2.1 0DTE carry is not automatically monetizable

Vilkov's 2026 paper studies S&P 500 0DTE structures from 2016 through early 2026 and argues that same-day variance carry is state-dependent and tail-risk dominated. The March 2026 paper/abstract reported some strict-OOS 10:00 ET conditional rules with positive net results.

However, the author's August 2026 public replication package now records a **transaction-cost unit-scale correction**: the bid/ask half-spread had been charged at roughly 1/100 of its correct size, and after correction **no strategy or basket retains a positive net Sharpe ratio**. This newer correction supersedes the old net-cost conclusion for this program's evidence ledger.

**Implication:** transaction costs and executable fills are a primary gate, not a sensitivity appendix. A strategy earning only a few dollars per vertical cannot be validated on midpoint fantasy fills.

### 2.2 Gamma is more defensible as a regime variable than a magic wall

Recent public research supports a gamma/variance relationship but weakens the claim that the single largest GEX strike is special:

- Ardia & Vaudescal (2026): public-OI non-0DTE net gamma predicts lower next-half-hour realized variance; the result reproduces on SPY/QQQ, but public-OI reconstruction correlates much less strongly with a dealer-inventory benchmark for 0DTE (0.53) than non-0DTE (0.99).
- Popovici (2026), preregistered SPY test: the largest open-defined GEX wall is statistically indistinguishable from rank-2–5 GEX nodes on break resistance, pinning/dwell and volatility dampening; consistent with gamma being a broader regime influence rather than a uniquely powerful strike-local wall.
- Existing Mastermind research already weakens standalone GEX alpha and requires validation before scoring.

**Implication:** the study separates `gamma_regime` from `exact_wall`. Exact walls must prove incremental value; they do not receive privileged status by construction.

---

## 3. Product thesis: turn the discretionary story into a containment engine

The useful machine job is **not** “predict SPY's closing direction.” It is:

> At a fixed decision timestamp, evaluate a candidate 0DTE credit spread and estimate whether time/IV decay is likely to pay the profit target **before** the spread enters a defined loss state, using only information known at that timestamp.

This converts Caleb's own strongest insight — gamma may tell us where **not** to sell — into a falsifiable survival/containment problem.

### Proposed research output per candidate spread

- `p_tp_before_stop` — probability take-profit occurs before loss stop;
- `ev_net` — expected dollars after executable fills and fees;
- `expected_shortfall_net` — tail loss metric;
- `containment_state` — stable / uncertain / runaway-risk;
- `abstain_reason` — event, poor payoff, negative EV, insufficient quote quality, regime instability, data null, etc.;
- provenance of every feature at decision time.

No model output may size or originate a live trade during this prereg.

---

## 4. Frozen experiment design

### 4.1 Instrument and session

Primary instrument: **SPY same-day-expiry options**.  
Primary structure: **$2-wide vertical credit spread**.  
Bull-put and bear-call families are evaluated separately and together only after family-level results are visible.

### 4.2 Decision clocks

Evaluate exactly three frozen decision clocks:

- 09:35 ET — close to the public OPG examples;
- 09:45 ET — enough opening path to estimate early continuation/reversal;
- 10:00 ET — literature benchmark and materially more stable opening information.

No best-time selection is allowed on the final holdout. Time-family selection occurs inside train/validation only and is then frozen.

### 4.3 Point-in-time feature families

Every feature must be observable by the decision timestamp. Unknown remains null; no later-day reconstruction may leak into the row.

**Price / opening-state baseline**

- overnight gap vs prior close;
- gap normalized by prior realized volatility and prior-day implied move where available;
- return from open to decision time;
- 5m/15m opening-range high/low and location inside range;
- distance from VWAP and VWAP slope known at timestamp;
- short-horizon realized volatility / range expansion;
- reversal vs continuation flags frozen from only elapsed bars.

**Volatility / payoff state**

- same-day ATM IV / integrated implied variance when PIT data supports it;
- IV change from first valid post-open snapshot to decision time;
- skew / term state only if timestamp-valid;
- candidate spread executable credit and reward/risk;
- expected move / standard-deviation envelope known at timestamp.

**Gamma state**

- aggregate gamma sign / magnitude;
- distance to zero-gamma / flip;
- front-expiry concentration where trustworthy;
- exposure gradient near spot;
- exact top call/put/net-GEX nodes as a **separate ablation family**, never silently fused into regime gamma;
- T-1 OI only where same-day OI publication timing would otherwise leak.

**Scheduled event state**

Frozen high-impact exclusions/flags: FOMC rate decision / press conference, CPI, PPI, Employment Situation/NFP, and other predeclared scheduled U.S. macro events already represented by a canonical Mastermind event owner. No retrospective “news was scary” filter.

**Optional later family: live tape / flow**

May enter only if the exact historical PIT source, signing reliability and timestamp provenance are already production/research approved. It is not required for the first falsification wave.

### 4.4 Candidate strike construction

For each clock and direction family, enumerate feasible $2-wide spreads from the observed same-day chain. Primary credit band:

- **$0.08–$0.15 net executable entry credit**.

A candidate may be selected only from strikes outside the frozen safety envelope for that arm. The envelope is computed without seeing future path.

Primary selection objective inside each arm:

1. satisfy the arm's containment envelope;
2. maximize conservative net expected value after costs;
3. tie-break by greater distance from spot, then tighter executable spread.

No candidate satisfying the rules => **abstain**.

### 4.5 Strategy arms — incremental-value test

Run these arms in order. Later arms must beat the prior arm out of sample, not merely look profitable alone.

- **A0 — unconditional payoff baseline:** eligible $0.08–$0.15 two-wide spread at fixed clock with no gamma feature; documents how much apparent win rate comes from selling remote convexity.
- **A1 — price + IV + event baseline:** gap/opening path, implied-vol state, expected-move envelope, scheduled-event state.
- **A2 — + gamma regime:** aggregate gamma sign/magnitude, flip distance, near-spot gradient/concentration.
- **A3 — + exact GEX wall topology:** adds exact high-ranked GEX nodes. This arm exists specifically to falsify the “wall” narrative; it must show incremental net value over A2.
- **A4 — + approved live-flow features:** only if PIT source/reliability gates are satisfied before the dataset is unblinded for this arm.

If A2 fails to improve A1, gamma does not earn decision authority. If A3 fails to improve A2, exact walls remain display/context only.

### 4.6 Direction policy

Do **not** encode “red gap => automatically sell bull put” or “green gap => automatically sell bear call.” Those are hypotheses.

Freeze three direction modes:

1. **contrarian-gap mode:** red-gap/flush permits bull-put candidates; green-gap/spike permits bear-call candidates;
2. **price-confirmed containment mode:** direction is permitted only after elapsed bars show rejection/reversal from the opening extreme;
3. **dual-candidate mode:** score the safest bull-put and bear-call candidates independently and trade only the side with positive lower-bound EV; both can be rejected.

Direction mode selection is train/validation-only and then frozen.

---

## 5. Exit / loss mechanics — the missing public rule is the core test

### 5.1 Take profit

Primary OPG-like take profit:

- enter within $0.08–$0.15 credit;
- target buyback at **$0.02** when executable.

Secondary robustness checks: 70%, 80%, 90% of entry credit captured.

### 5.2 Loss rules

Because OPG does not publish a deterministic stop, no single invented stop may be labeled “Caleb clone.” Evaluate predeclared alternatives:

- **R0:** no intraday mark stop; settle/close at 15:55 ET — tail-risk benchmark, not proposed production policy;
- **R1:** exit when executable spread debit reaches **3× entry credit**;
- **R2:** exit at **5× entry credit**;
- **R3:** structural breach — exit after the underlying crosses the short strike by the frozen confirmation tolerance;
- **R4:** combined — earliest of 3× mark stop or structural breach.

All exits use executable quote logic and include slippage/fees. The final holdout receives only the risk rule selected in train/validation.

### 5.3 Time/event stop

Any candidate still open at 15:55 ET is closed using executable quotes unless settlement modeling has been separately qualified. No holding through a scheduled intraday high-impact event that was known at entry if the event-exclusion arm forbids it.

---

## 6. Execution-cost law

Primary fill simulation must use **leg-level executable quotes** where available:

- opening credit: short leg sold at bid, long leg bought at ask;
- closing debit: short leg bought at ask, long leg sold at bid;
- apply actual recorded fee schedule if the intended venue/account is known; otherwise publish a conservative per-contract fee sensitivity grid;
- reject crossed/stale/zero quotes under a frozen quote-quality rule;
- no midpoint primary results.

Sensitivity results may include midpoint, half-spread and adverse-slippage cases, but only the executable/conservative result can pass the production gate.

This requirement is binding because corrected 2026 replication evidence shows a transaction-cost scaling error can reverse an entire 0DTE strategy conclusion.

---

## 7. Data / authority map — reuse, do not rebuild

Use the existing canonical owners after verifying current schema/version at execution time:

- `engine/gex_engine.py` — gamma/flip calculations;
- `engine/options_surface.py` / `engine/options_entry_state.py` — existing option-state features;
- `scripts/chain_snapshot_poller.py` and existing historical option stores — PIT chain/quote evidence where coverage exists;
- existing event-calendar owner for scheduled macro flags;
- existing validation / research-ledger conventions — no new general signal ledger;
- corrected GEX history only; legacy bad flip / degenerate-IV snapshots must not be silently consumed.

**Do not** create a second GEX engine, option-chain store, event calendar, identity plane, or trade ledger for this study.

---

## 8. Sample / split law

Before observing final strategy outcomes, the execution worker must publish exact availability by date for:

- same-day SPY option quotes at each frozen clock;
- underlying minute bars;
- PIT GEX/IV inputs;
- event flags;
- executable close-path quotes needed for TP/stop simulation.

Then freeze contiguous calendar partitions. Preferred structure where coverage permits:

- development/train: earliest ~60%;
- validation/model/rule selection: next ~20%;
- final one-shot holdout: latest ~20%.

Minimum requirements:

- holdout must span multiple volatility regimes and include material directional trend sessions;
- no random row split across dates;
- no future-day feature normalization;
- no final holdout parameter tuning;
- report familywise/multiple-testing controls for the finite arm/risk-rule grid.

If PIT intraday chain coverage is too young to support an honest holdout, the correct output is **INSUFFICIENT_HISTORY**, not a synthetic historical GEX backfill marketed as equivalent live state.

---

## 9. Pass / fail metrics

### Primary economic gates

A candidate can advance only if, on the untouched holdout:

1. net mean expectancy after executable costs is > 0 and its block-bootstrap 95% interval excludes 0;
2. expected shortfall / worst-session loss remains inside the separately declared research risk budget;
3. drawdown does not depend on one omitted crisis/event regime;
4. results remain positive under at least one adverse-slippage sensitivity beyond the primary fill assumption;
5. no single calendar quarter supplies a majority of total net P&L;
6. trade count is sufficient for the registered inference method; otherwise status remains accruing.

### Incremental-information gates

- A2 must improve A1 on net expectancy and/or containment calibration without materially worsening tail loss;
- A3 must improve A2 to grant exact-wall utility; otherwise exact walls are rejected as decision features;
- any ML model must beat a transparent regularized/logistic or monotonic baseline on OOS calibration and economic value.

### Report every time

- number of eligible sessions / trades / abstentions;
- win rate **and** confidence interval;
- average win, average loss, payoff ratio;
- gross and net P&L;
- commissions, spread cost and slippage separately;
- profit factor;
- maximum drawdown;
- 95% / 99% expected shortfall;
- max adverse excursion / max favorable excursion;
- TP-before-stop frequency;
- P&L by year, VIX/IV regime, gap bucket, gamma regime, event/non-event, bull-put/bear-call;
- sensitivity to 09:35/09:45/10:00 clocks;
- calibration of containment probability.

No headline may lead with win rate alone.

---

## 10. Position sizing is explicitly downstream

The public challenge's sizing is not copied. During research all results are normalized per spread and by defined maximum risk.

Only after a strategy passes may a separate sizing study evaluate fixed-fraction risk (e.g. 0.25% / 0.50% / 1.00% of NAV at defined stop/max loss). No Kelly sizing, compounding claim, or live capital recommendation is part of this prereg.

---

## 11. Disagreement / uncertainty ledger

| Claim | Evidence A | Evidence B / limitation | Current ruling |
|---|---|---|---|
| OPG has a durable 97%+ edge | 41/42 self-reported counted sessions, +$30,298.39 | small sample; commercial publisher; one disclosed tail loss; no audited broker dataset | **UNPROVEN** |
| Same-day variance carry is broadly monetizable | positive 0DTE VRP in literature | Vilkov Aug-2026 cost correction says no tested strategy/basket retains positive net Sharpe | **WEAKENED; COST GATE PRIMARY** |
| Exact GEX wall predicts support/resistance | OPG practitioner use / common narrative | prereg control-matched SPY study finds top wall indistinguishable from rank 2–5 nodes | **UNPROVEN; A3 ABLATION ONLY** |
| Gamma regime affects volatility | multiple dealer-hedging studies + recent public-OI evidence | 0DTE public-OI proxy is diluted vs dealer inventory; existing Mastermind research weakens incremental alpha | **PLAUSIBLE CONTEXT; MUST ADD VALUE OVER A1** |
| OPG risk can be copied | public loss commentary and early exits | deterministic stop / exact sizing unpublished; explicit trade arithmetic raises buying-power/risk questions | **UNKNOWN; DO NOT COPY** |
| 41/42 implies win probability > structural break-even | observed 97.62% | Wilson interval wide; P(>=41 wins | p=.95) ≈37.2% | **NOT ESTABLISHED** |

---

## 12. Source register

### OPG / Caleb public evidence — self-reported

- OPG, “A Daily Cashflow Experiment: $12,959.53 in 22 Trading Days,” 2026-08-14: https://www.opgtradingservice.com/p/a-daily-cashflow-experiment-12-959-53-in-22-trading-days
- OPG, “OPG Order Flow - Tuesday 9/15,” 2026-09-15: https://www.opgtradingservice.com/p/opg-order-flow-tuesday-9-15
- OPG, “OPG Order Flow - Wednesday 8/12,” 2026-08-12: https://www.opgtradingservice.com/p/opg-order-flow-wednesday-8-12
- OPG, “OPG Order Flow - Tuesday 8/25,” 2026-08-25: https://www.opgtradingservice.com/p/opg-order-flow-tuesday-8-25
- OPG, “OPG Order Flow - Friday 8/7,” 2026-08-07: https://www.opgtradingservice.com/p/opg-order-flow-friday-8-7
- OPG, “OPG Order Flow - Friday 9/4,” 2026-09-04: https://www.opgtradingservice.com/p/opg-order-flow-friday-9-4

### External research

- Grigory Vilkov, “0DTE Trading Rules,” SSRN 4641356, last revised 2026-03-18: https://ssrn.com/abstract=4641356
- Vilkov replication package, **August 2026 transaction-cost correction / known issue**: https://github.com/vilkovgr/0dte-strategies
- Rees Popovici, “Do Gamma-Exposure Walls Exhibit Strike-Local Effects? A Pre-Registered, Control-Matched Test of Strike-Local Dealer-Gamma Effects in SPY,” SSRN 7082418, posted 2026-07-25: https://ssrn.com/abstract=7082418
- David Ardia & Thomas Vaudescal, “The Intraday Gamma-Variance Channel with Public Options Data,” SSRN 7202999, posted 2026-08-07: https://ssrn.com/abstract=7202999

### Existing Mastermind authority / infrastructure

- `research/OPTIONS_ALPHA_MASTERPLAN.md` — validate-before-score; canonical 1–20D options-alpha program, explicitly not a 0DTE desk.
- `research/OPTIONS_CONFLUENCE_PROGRAM_BY_FABLE.md` — point-in-time options data/measurement and epistemic laws.
- `research/RIC_DOMAIN_RESEARCH_PACK_2026-07-13.md` — existing gamma evidence review / weakened standalone gamma-alpha claim.
- `engine/gex_engine.py`
- `engine/options_surface.py`
- `engine/options_entry_state.py`
- `scripts/chain_snapshot_poller.py`

---

## 13. Exact next action

**Data-availability + replay probe:** on the canonical options-data host/worktree, resolve the exact PIT SPY chain/quote/GEX coverage for 09:35, 09:45 and 10:00 ET; identify the earliest continuous date where leg-level executable entry **and close-path** quotes can be reconstructed without leakage. Produce a compact coverage manifest and run only the preregistered **A0/A1** baseline first. Do not add gamma until the price/IV/cost baseline is known.

Stop and return to Sol if:

- usable PIT quote history is insufficient for a holdout;
- the corrected GEX lineage cannot be distinguished from known-bad legacy snapshots;
- transaction-cost inputs cannot be represented honestly;
- another current owner is actively modifying the same source paths.

The first meaningful result is not “backtest green.” It is a **cost-correct, point-in-time A0/A1 baseline** against which gamma can earn or fail incremental authority.
