# RS Pullback Launch / Intraday Low-Detection Intelligence — Research Commission

**Date:** 2026-10-06  
**Commission type:** research + empirical design + architecture recommendation  
**Implementation authority of research commission:** none  
**Primary downstream owner:** Sol / Mastermind execution session  
**Research outcome:** COMPLETE; construction is recommended only as a bounded empirical program, not as a production signal.

## Source / procedure receipts

Protected Mastermind procedure pin used by the commission:

- `mastermindx-market-intelligence/Mastermind@6e82f9af41bf175c87e70f6a852f73b71eca80c8`
- `docs/sol_skills/INDEX.md` blob `38a18571229e487f525b1c9780f7993220a5da93`
- Skillpack: `mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap major 1`

Primary implementation evidence pins inspected during the research:

- Macro research evidence pin: `19a42078e4669916d9fd63bd7c5d27be204d0280`
- Terminal research evidence pin: `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`
- Mastermind research evidence pin: `6e82f9af41bf175c87e70f6a852f73b71eca80c8`

Persistence base observed immediately before this record was created:

- Macro `main@309f88c6c209bdc9fb611de0018fb619d9351b37`

These are evidence anchors. The implementation session must re-pin current protected Mastermind and re-census current Macro/Terminal heads before modifying code.

---

# 1. EXECUTIVE VERDICT

The proposed edge is **plausible, measurable, and worth a controlled study**, but it is **not established**.

The strongest version of the thesis is not “a 30-minute pivot predicts a rally.” It is:

> Among stocks already known to be durable relative-strength leaders, a controlled pullback may enter a point-in-time detectable state in which relative performance and selling-pressure evidence improves before absolute price visibly reverses. That state may improve downside control, launch forecasting, or both.

Three claims must remain separate:

1. **Low-in / downside claim** — material downside remaining is small.
2. **Launch claim** — absolute positive expansion occurs soon.
3. **Economic timing claim** — acting earlier improves net results versus a meaningful incumbent policy.

A setup can pass claim 1 and fail claim 2. It can pass claims 1–2 and still fail claim 3 because of whipsaws, costs, missed confirmations, or adverse tails.

**Recommendation:** build the research/data program. Do not grant ranking, sizing, gating, trade, or portfolio authority until prospective evidence passes pre-declared gates.

---

# 2. CURRENT MASTERMIND CAPABILITY CENSUS

## Existing components to reuse

### Macro — daily leader/pullback context

`engine/us_leader_pullback.py` already models:

- `LEADER`
- `PULLBACK`
- `RESET_TURN`
- `RESUMED`
- close-basis pullback depth
- daily StochRSI K/D
- daily RSI-MACD histogram
- PIT RS percentile input
- anchored close×volume / volume reference
- explicit null behavior

This is a material overlap with the proposal. It is **daily context**, not the desired intraday launch detector.

`engine/us_leader_pullback_coverage.py` publishes the daily context for consumers and carries source/freshness contracts. Its population definition and per-row freshness must be audited before historical use.

### Macro — Entry Radar infrastructure

Existing Radar already owns:

- typed detector readings;
- append-only entry-event identity;
- runtime episode lifecycle;
- PIT sampled intraday observations;
- detector registry/spec hashes;
- replay episode derivation;
- matched-control machinery;
- outcome attachment;
- transaction-cost mechanics;
- multiple-testing / prereg gates;
- live payload + research-priority projection.

Relevant paths include:

- `engine/entry_radar/readings.py`
- `engine/entry_radar/entry_events.py`
- `engine/entry_radar/detectors.py`
- `engine/entry_radar/challengers.py`
- `engine/entry_radar/live_eval.py`
- `engine/entry_radar/live_ledger.py`
- `engine/entry_radar/replay/*`
- `engine/trial_ledger.py`
- `engine/experiments_registry.py`

Do **not** create a second lifecycle, event store, replay ledger, trial ledger, scheduler, notification lifecycle, or research source of truth.

### Existing boundaries that remain binding

- `C4_MTF_TURN@1` is stratification-only and cannot fire.
- `F1_FUSION` is reserved, not a placeholder available for reuse.
- Entry Radar records deliberately separate descriptive/research outputs from authority.
- Existing W5 outcomes are daily / multi-session and do not answer the proposed 30–120 minute question.
- Prophet B4 entry availability remains deterministic and consumes owner facts; this research must not bypass or overwrite its authority model.

### Terminal — intraday substrate

Terminal has existing intraday storage, qualification and chart/resampling machinery. The October source census inspected by the commission documented a substantial 5-minute inventory but explicitly did **not** admit it as a research-quality historical plane.

Therefore: **data qualification is Phase 0/1, not a clerical step**.

### Capability-state summary

| Capability | Research census |
|---|---|
| Daily leader/pullback context | BUILT_NOT_PROVEN for this intraday thesis |
| Entry Radar event/lifecycle primitives | BUILT_NOT_PROVEN as reusable infrastructure |
| Existing W5 replay/outcome framework | PROVEN for its registered daily questions; not for the new intraday target |
| Canonical 1m→15m/30m historical research plane | PARTIAL |
| Point-in-time historical availability/revision plane | PARTIAL |
| Intraday RS Pullback Launch detector | NOT_BUILT |
| Calibrated low-in probability | NOT_BUILT |
| Calibrated 30/60/120m launch probability | NOT_BUILT |
| Production ranking/gating/sizing authority | REJECTED_BY_DESIGN until evidence + separate admission |
| Human-facing intraday launch explanation | SPEC_ONLY |

---

# 3. RESEARCH LITERATURE SYNTHESIS

The literature supports studying the constituent mechanisms, but not assuming the exact proposed sequence is already proven.

Key implications:

- Medium-horizon cross-sectional momentum supports conditioning on established leadership, but does not prove next-hour continuation.
- Intraday return behavior is highly clock-time dependent; same-time-of-day continuation and adjacent-interval behavior are distinct phenomena.
- Volume contraction is ambiguous unless interpreted jointly with price, range, liquidity and clock time.
- Empirical support/resistance research supports pre-specified location tests; it does not justify hindsight-selected anchors.
- Order-flow imbalance can explain contemporaneous moves, but OHLCV proxies are not equivalent to order-book events and contemporaneous explanation is not a future-launch forecast.
- Public practitioner “30-minute pivot”, first-green-bar, undercut/reclaim and failed-breakdown mechanics are valuable as testable primitives, not proof.

The MRVL example named in the commission was not independently verified because the exact chart/timestamp/source was not available. No MRVL entry, stop, probability or outcome is asserted by this research.

---

# 4. MECHANISM MODEL

The plausible causal chain is:

1. Durable leader enters a controlled pullback.
2. Absolute price remains weak while market/sector-relative performance stops deteriorating.
3. Downside impulse, range or selling activity decelerates.
4. Price tests a pre-existing location/support region.
5. Short-horizon relative performance and momentum derivatives improve.
6. A completed 30m structure defines a fixed pivot.
7. A later price print confirms or rejects the pivot.
8. If the mechanism is real, forward downside and/or launch outcomes should improve relative to controls.

Competing explanations must be measured:

- broad-market beta rebound;
- sector rebound;
- mean reversion after temporary pressure;
- catalyst/news repricing;
- simple support effect;
- generic leader resilience;
- time-of-day seasonality;
- volatility compression;
- selection bias from choosing future successful pivots.

---

# 5. HYPOTHESIS TREE

## H1 — incremental launch information

Conditional on the same PIT-qualified leader/pullback risk set, adding intraday RS / divergence / pressure evidence improves 120-minute upper-before-lower barrier forecasts beyond a primitive-price/market/sector baseline.

**Falsifier:** no out-of-sample Brier improvement, unstable sign, or improvement disappears when primitive stock + market + sector returns are already included.

## H2 — downside / low-in information

The proposed anticipation state reduces forward MAE at equal selection coverage.

**Falsifier:** MAE does not improve, tail MAE worsens materially, or benefit exists only after future pivot selection.

## H3 — economic timing value

A registered early policy improves common-budget net R per eligible episode versus registered wait-for-confirmation and incumbent-assessor comparators.

**Falsifier:** whipsaws/costs remove the benefit, tail loss worsens, or higher hit-rate comes only from lower participation.

## H4 — leadership conditioning

The effect strengthens monotonically as prior leadership quality increases.

**Falsifier:** no monotonicity, or result exists mainly in ordinary/non-leader names.

## H5 — meaningful location

The effect is stronger near pre-specified support/location than for turns anywhere.

**Falsifier:** location adds no incremental information after pullback geometry and volatility are controlled.

## H6 — 15m/30m role separation

15m evidence is useful for anticipation; 30m completion is useful for structural confirmation.

**Falsifier:** duplication adds no information, or the reverse assignment consistently dominates out of sample.

---

# 6. FEATURE TAXONOMY

All features are candidate research inputs, not granted signal authority.

## Prior leadership

- 5/10/20/60/120-session returns
- market-relative / sector-relative return
- cross-sectional rank
- persistence of rank
- proximity to rolling high
- daily trend integrity
- theme/sector leadership where PIT membership exists
- liquidity / ADV

## Pullback quality

- depth / ATR
- retracement versus prior impulse
- age since high
- slope of decline
- realized-volatility contraction
- downside-range contraction
- close-location value
- number of failed lows
- preserved higher-TF trend
- market/sector-relative drawdown

## Location

- 9/10 EMA
- 20/21 EMA
- 50 DMA
- session VWAP
- pre-specified AVWAP anchors
- prior breakout/high/gap edge
- registered entry/invalidation geometry
- optional later options levels as an independent evidence family

All location distances should be normalized by a declared volatility scale.

## 15m anticipation candidates

- price equal/lower low + RS higher low
- prior-15m-high reclaim
- residual-return turn
- K/D or RSI-MACD derivatives where incremental
- ROC slope / acceleration
- close-location improvement
- failed breakdown
- sampled higher low
- time-of-day normalized volume / range
- VWAP/EMA reclaim

## 30m confirmation candidates

- completed reversal bar
- fixed pivot high/low
- lower-wick / close-location structure
- downside impulse exhaustion
- maintained RS divergence
- later break through completed pivot high
- confirmation activity / relative volume

## Redundancy law

Many momentum indicators are transformations of the same price path. Test correlation, incremental contribution, and ablations. Prefer a compact interpretable set.

---

# 7. RS ARCHITECTURE

Use several representations, but force them to compete against primitive returns.

1. **Market relative**
   `log(P_stock / P_market)`
2. **Sector relative**
   `log(P_stock / P_sector)`
3. **Residualized return**
   rolling PIT regression removing market and sector components
4. **Cross-sectional intraday RS**
   percentile within the eligible PIT universe / sector
5. **Derivatives**
   slope, acceleration, drawdown, recovery, higher-low, local-high, disagreement

Critical tests:

- price lower/equal low + RS higher low;
- price below prior swing high + RS local high.

Important methodological point: RS transformations contain no magical new raw information if the baseline does not already include stock/market/sector returns. The baseline must be strong enough to prevent a weak-control illusion.

---

# 8. 15m / 30m ARCHITECTURE

Recommended registered V1 decomposition:

### 15m = ANTICIPATION / ARMED candidate evidence

Uses only fully knowable 15m data and earlier information. It may describe “pivot developing” but may not use the eventual unfinished 30m high/low/close.

### 30m = PIVOT FORMATION

A pivot becomes `PIVOT_FORMED` only after the full 30m interval is available. Its high and low become fixed after availability.

### PIVOT CONFIRMATION

A later completed 1m observation crosses the fixed pivot high plus a registered buffer.

The 30m interval must end after pullback onset. An interval containing the onset may qualify only after it completes.

Every armed episode remains in the denominator even if no pivot or confirmation ever occurs.

---

# 9. LABEL / TARGET CONTRACT

Do not label success as “identified the exact candle containing the future minimum.”

## Volatility unit

Let:

- `E` = prescribed hypothetical entry-reference price available at decision time;
- `A` = pre-declared ATR/volatility scale frozen for the episode.

## Primary launch target

Within the next 120 regular-session minutes:

- upper barrier: `E + 1.0 A`
- lower barrier: `E - 0.5 A`

Primary launch label:

> upper barrier reached before lower barrier.

Same-minute/bar ambiguity must be handled pessimistically or marked ambiguous under a pre-registered rule.

## Low-in / MAE

`MAE_ATR = max(0, E - min(future_low)) / A`

Primary low-in label:

`MAE_ATR <= 0.25`

Low-in and launch are independent labels.

## Secondary outcomes

- launch at 30/60/90m
- session remainder
- next-session diagnostic
- MFE_ATR
- MAE_ATR
- MFE/MAE with a declared zero-denominator treatment
- +1R before -1R
- +1.5R before -1R
- +2R before -1R
- time-to-positive
- time-to-MFE
- time-to-launch
- low-capture distance

No policy comparison may gain extra horizon simply because it waits longer. Early-vs-wait economic policies share a fixed common endpoint.

---

# 10. DATA PLAN

## Minimum viable

- canonical 1m stock bars;
- synchronized SPY/QQQ;
- sector ETF bars;
- PIT eligible-universe identity;
- corporate-action / basis lineage;
- trading calendar and RTH boundaries;
- daily leader/pullback context;
- required incumbent Entry Engine inputs;
- timestamped catalyst coverage;
- representative bid/ask samples for cost validation.

## Ideal

Add only if incremental value warrants cost:

- direct quote/spread history;
- trade imbalance;
- order-book imbalance;
- deeper theme membership history;
- stronger catalyst/news coverage.

## Data law

- Build canonical 15m/30m bars from 1m.
- Separate bar end from `known_at`.
- Preserve first-seen/revision observations prospectively.
- Do not use final daily high/low during the day.
- Do not use future volume totals for intraday normalization.
- Declare adjustment basis explicitly.
- Do not infer “no news” from missing event data.

The existing Terminal intraday inventory is a starting point, not automatic research admission.

---

# 11. EXPERIMENT PLAN

## Risk set

Primary study population:

- liquid US equities;
- already qualified by a PIT leadership ruler;
- controlled pullback in progress;
- sufficient daily + intraday history;
- healthy required context.

Run leadership bands (50/30/20/10/5% plus persistent leaders) as registered analyses.

## Controls

- random timestamp in qualified leaders
- any pullback in qualified leader
- RSI turn
- MACD-histogram turn
- first green 15m
- first green 30m
- completed 30m pivot + high break
- common moving-average pullback
- faithful incumbent Entry Engine assessment

## Strong baseline B0

B0 must include primitive stock, market and sector returns plus:

- leadership features;
- pullback depth/age;
- pre-existing location;
- time of day;
- volatility;
- liquidity;
- catalyst context;
- faithful incumbent assessment.

Then add RS/divergence/residual/pressure blocks individually.

## Ablations

A — vanilla 30m pivot  
B — A + leadership  
C — B + location  
D — C + 15m turn  
E — D + market-relative divergence  
F — E + sector-relative divergence  
G — F + residualized alpha  
H — G + sell-pressure exhaustion  
I — H + time-of-day normalization  
J — I + regime/context

Also perform block-removal ablations from the full model.

## Validation

- chronological development / validation / evaluation;
- purging around overlapping labels;
- embargo where appropriate;
- session-block resampling;
- cross-ticker analysis;
- quarterly/yearly stability;
- no threshold choice on test;
- no random shuffled split.

A “recent period” is holdout only if it has genuinely remained unused. Otherwise final validation must move forward prospectively.

---

# 12. FAILURE-MODE ANALYSIS

Explicit families:

- falling knife;
- leadership regime ended;
- sector rollover;
- market liquidation;
- earnings/news shock;
- failed breakout;
- post-gap distribution;
- midday low-volume bounce;
- dead-cat bounce;
- pivot without expansion;
- repeated 15m whipsaw before 30m confirmation;
- meme/high-volatility distortion;
- illiquid spread;
- options-expiration distortion;
- overnight gap invalidating geometry.

Each failure family must map to one of:

- deterministic veto;
- confidence reduction;
- separate model/stratum;
- accepted irreducible noise.

Do not convert every observed failure into a new after-the-fact filter.

---

# 13. RECOMMENDED MODEL ARCHITECTURE

Start interpretable.

Recommended sequence:

1. deterministic candidate/state construction;
2. logistic / regularized linear models;
3. calibrated classifier if probability claims earn support;
4. gradient boosting as a challenger;
5. hazard/survival model only if time-to-launch adds clear value;
6. sequence models only after simpler models demonstrably fail.

Do not build a 0–100 LaunchPivotScore first.

Likely useful output family if data supports it:

- `P_low_in`
- `P_launch_30`
- `P_launch_60`
- `P_launch_120`
- expected MAE
- expected MFE

If calibration is weak, publish descriptive state / ordinal research priority rather than false probability.

---

# 14. MASTERMIND INTEGRATION DESIGN

## Owner

Extend the existing Entry Radar / canonical entry evidence architecture. Do not create another entry authority.

Proposed conceptual evidence family:

`intraday_pullback_launch`

But identity/schema/version must be minted through the incumbent owner’s contract/versioning process. Do not overload frozen v1 records with prohibited `score`, `confidence`, or probability fields.

## Consumer relationship

- Daily leader/pullback organ supplies higher-timeframe context.
- Qualified intraday substrate supplies PIT 1m→15m/30m observations.
- Entry Radar owns observation/event/episode lineage.
- Experimental outcomes flow through existing TrialLedger / evaluation infrastructure.
- Prophet / Entry Engine consumers may read accepted evidence later; they do not inherit authority from research.

No duplicate canonical sink.

---

# 15. PRODUCT DESIGN

Until calibrated, user-facing output should emphasize:

- current state;
- what changed;
- when it became known;
- evidence that is improving;
- fixed confirmation level, once formed;
- invalidation geometry;
- data freshness / missing evidence;
- reason codes;
- research maturity.

Do not display fake probabilities.

Candidate surfaces:

- Entry Radar scanner;
- ticker dossier;
- chart overlay;
- watchlist re-arm;
- held-position add-opportunity context;
- alerts on meaningful transitions only.

Alert candidates:

- PULLBACK → EXHAUSTION
- EXHAUSTION → ARMED
- ARMED → PIVOT_FORMED
- PIVOT_FORMED → PIVOT_CONFIRMED
- ARMED/PIVOT → INVALIDATED

Reuse the existing notification lifecycle. Apply dedupe/cooldown there rather than creating a new notifier.

---

# 16. BUILD ROADMAP

## Phase 0 — source recovery + ownership recensus

**Goal:** current source and owner map.  
**Done when:** current Mastermind/Macro/Terminal pins, exact owners, collision scan and non-goals are written into the implementation packet.  
**Falsifier:** required source/custody cannot be established.  
**Consumer:** Phase 1.

## Phase 1 — data admission + pilot panel

**Goal:** prove a PIT-safe dataset is constructible.  
**Dependencies:** 1m stock/benchmark data, daily context, identity, basis, calendar.  
**Outputs:** data contract, coverage census, refusal census, pilot episodes including nonfires/failures.  
**Done when:** exact admission verdict is reproducible and leakage tests pass.  
**Falsifier:** coverage/basis/timestamp/revision deficiencies make the target untestable.  
**Consumer:** Phase 2.

## Phase 2 — baseline pivot study

Implement controls and the vanilla 30m pivot without new RS logic.

## Phase 3 — leadership conditioning

Test monotonicity across predeclared leadership strata.

## Phase 4 — 15m anticipation

Add PIT 15m anticipation without looking into unfinished 30m bars.

## Phase 5 — location / pullback quality

Add pre-existing location and controlled-pullback features.

## Phase 6 — compact calibrated model

Only after incremental evidence exists.

## Phase 7 — shadow owner integration

Attach research-only evidence to the incumbent Entry Radar/entry architecture.

## Phase 8 — product presentation

Build scanner/dossier/chart/alert surfaces around the accepted contract.

## Phase 9 — prospective validation

Capture first-seen observations, revisions, latency and actual cost proxies.

## Phase 10 — binding-use review

Only after prospective gates pass and the canonical decision/sizing owners explicitly admit the evidence.

---

# 17. OPEN QUESTIONS

Genuine unresolveds:

1. Can existing 1m history meet PIT/revision requirements over enough years/names?
2. What exact PIT universe should be the confirmatory population?
3. Does daily leader-pullback context have sufficient row-level historical freshness/provenance?
4. Which benchmark assignment (SPY/QQQ/sector ETF) is the stable primary law?
5. Which ATR/volatility unit is best for intraday barrier labels?
6. Is full catalyst coverage sufficient to support “no blocking event observed,” or must this remain unknown for many episodes?
7. Do quote/spread samples materially change economic conclusions?
8. Does 15m anticipation improve downside only, launch only, both, or neither?
9. Can probabilities calibrate well enough to publish, or should V1 remain state + descriptive risk?
10. What current Entry Engine policy is the correct prospective incumbent for real decision comparison?

---

# 18. FINAL BUILD SPECIFICATION — V1 RESEARCH IMPLEMENTATION

## State machine

`ELIGIBLE_LEADER → PULLBACK → EXHAUSTION → ARMED → PIVOT_FORMED → PIVOT_CONFIRMED → LAUNCH`

Every nonterminal state can transition to:

- INVALIDATED
- DISTRIBUTION
- TREND_BREAK
- EXPIRED

### ELIGIBLE_LEADER

Daily context satisfies the registered PIT leadership law. No intraday claim yet.

### PULLBACK

Price retraces from a previously observable anchor within the registered depth/age/trend bounds.

### EXHAUSTION

Downside impulse/range/activity decelerates under PIT-safe features. Descriptive; not reversal confirmation.

### ARMED

15m anticipation condition passes. Strong enough for attention/optional research probe, but no claim that reversal is confirmed.

### PIVOT_FORMED

A fully completed/available 30m reversal structure exists. Fixed pivot high/low become addressable.

### PIVOT_CONFIRMED

A later completed observation crosses the fixed pivot high + registered buffer.

### LAUNCH

Outcome state only; it must not feed backward into the detector.

## Episode law

- one active research episode per registered unit;
- all eligible episodes retained;
- no future pivot required for inclusion;
- no silent removal of nonconfirmations;
- registered expiry/cooldown;
- missing required input = unavailable, not false.

## Timing law

Every interval records:

- market session;
- interval start;
- interval end;
- source timestamp;
- `known_at`;
- basis/vintage;
- revision/receipt where available.

Decision reference is the first eligible completed interval at/after the signal clock under the registered latency rule.

## Outputs before calibration

- ticker / episode id
- state
- observed_at / known_at
- leader context
- pullback geometry
- support/location context
- market/sector relative measures
- registered anticipation reason codes
- fixed pivot high/low when formed
- confirmation state
- invalidation geometry
- freshness / availability
- provenance
- all authority false

No probability / confidence / composite score until calibration and contract admission.

---

# 19. SOURCE LEDGER — KEY IMPLEMENTATION SOURCES

The rendered research artifact contains the larger literature/source ledger. The most important implementation sources for the Sol phase are:

## Mastermind

- Protected Skillpack INDEX at `Mastermind@6e82f9af41bf175c87e70f6a852f73b71eca80c8`
- `bot/phase2.py` — inspected as archived; do not revive as active owner
- current portfolio / technical packet owners — re-census before code

## Macro

- `engine/us_leader_pullback.py`
- `engine/us_leader_pullback_coverage.py`
- `engine/leader_lifecycle.py`
- `engine/residual_alpha.py`
- `engine/residual_momentum.py`
- `engine/entry_primitives.py`
- `engine/entry_radar/readings.py`
- `engine/entry_radar/entry_events.py`
- `engine/entry_radar/detectors.py`
- `engine/entry_radar/challengers.py`
- `engine/entry_radar/live_eval.py`
- `engine/entry_radar/live_ledger.py`
- `engine/entry_radar/replay/episodes.py`
- `engine/entry_radar/replay/outcomes.py`
- `engine/entry_radar/replay/confirmatory.py`
- `engine/entry_radar/replay/costs.py`
- `engine/entry_radar/replay/gates.py`
- `engine/entry_radar/replay/prereg.py`
- `engine/trial_ledger.py`
- `engine/experiments_registry.py`
- `engine/prophet_entry_availability.py`
- `research/prophet_us_audit/LEADER_PULLBACK_REPLAY_2026-08-08.md`
- `research/live_entry_radar/W5_CONFIRMATORY_RESULTS_2026-08-17.md`
- `research/live_entry_radar/INTRADAY_DISLOCATION_CATALYST_CONTEXT_R0_PREREG.md`
- `research/live_entry_radar/INTRADAY_DISLOCATION_CATALYST_SOURCE_CENSUS_2026-10-02.md`

## Terminal

- current intraday storage / qualification paths — re-census current head
- `docs/research/INTRADAY_DISLOCATION_R0_DATA_CENSUS_2026-10-02.md` at the research evidence pin

## Primary external evidence families reviewed

- medium-horizon cross-sectional momentum / residual momentum;
- intraday return continuation/reversal and time-of-day structure;
- price/volume interaction;
- order-flow imbalance;
- empirical support/resistance;
- public 30m pivot / first-green / undercut-reclaim practitioner mechanics;
- provider documentation on aggregates, corporate-action basis and late bar revisions.

These sources support hypotheses and experiment design, not a production trade rule.

---

# 20. SOL IMPLEMENTATION HANDOFF

## RECOMMENDED BUILD

Build an **Entry Radar-owned, research-only RS Pullback Launch evidence family** that tests whether 15m anticipation adds incremental information before a completed 30m pivot in PIT-qualified leader pullbacks.

Start with data qualification and a reproducible offline pilot. Do not start with UI or a score.

## DO_NOT_BUILD

- no second entry engine;
- no second episode/event/trial ledger;
- no generic “AI confidence” score;
- no 0–100 LaunchPivotScore before calibration;
- no production rank/gate/size/order behavior;
- no C4 firing path;
- no F1 shortcut;
- no deep-learning sequence model in V1;
- no expensive L2/L3 dependency before OHLCV/L1 incremental value is measured;
- no “no news” classifier from incomplete coverage;
- no hindsight-selected support or pivot;
- no use of unfinished 30m high/low/close.

## EXISTING COMPONENTS TO REUSE

Daily leader/pullback context, Entry Radar detector/event/episode primitives, PIT sampling law, replay/outcome utilities where compatible, TrialLedger, experiments registry, cost model, Prophet deterministic availability boundaries, Terminal intraday storage/qualification.

## NEW COMPONENTS REQUIRED

1. research data-admission adapter for canonical 1m→15m/30m observations;
2. versioned RS Pullback Launch research detector/state spec under Entry Radar ownership;
3. feature extraction for leader/pullback/location/RS/pressure evidence;
4. short-horizon label/outcome module that is distinct from existing H=10-session outcomes;
5. registered control/ablation runner;
6. calibration/evaluation module if the initial deterministic study passes;
7. prospective first-seen/revision capture integration;
8. display-only projection after the research contract is accepted.

## EXACT FIRST ENGINEERING PHASE

**Phase 1: Data Admission + Pilot Episode Panel**

1. Re-pin protected Mastermind and load same-commit procedures.
2. Re-census current Macro and Terminal heads.
3. Recover current Entry Radar and Prophet/Entry Engine owner boundaries.
4. Inventory exact 1m stock/benchmark/sector history, row counts, dates, missing intervals, basis and revision semantics.
5. Define the canonical research clock and 1m→15m/30m bucketing.
6. Build a small pilot across representative names/sessions including:
   - valid anticipated launches;
   - valid nonlaunches;
   - pivot never forms;
   - pivot forms but never confirms;
   - confirmation fails;
   - stale daily context;
   - missing interval;
   - catalyst coverage unknown;
   - same-bar barrier ambiguity;
   - early-close session.
7. Prove PIT mutation tests: changing any future bar/revision must not alter earlier detector state.
8. Produce coverage/refusal census and an admission verdict.
9. Stop before outcome-driven threshold tuning.

**DONE_WHEN:** a fresh session can reproduce the exact pilot population and every feature/clock/label from immutable inputs, and can name every refusal; or the phase produces a defensible NOT_ADMITTED result explaining why the target cannot yet be tested.

## DATA DEPENDENCIES

Required:

- 1m RTH stock bars;
- synchronized SPY/QQQ and sector ETFs;
- stable security identity;
- explicit adjustment basis + corporate actions;
- session calendar;
- daily leader/pullback context;
- incumbent Entry Engine inputs;
- catalyst coverage state.

Useful later:

- quotes/spreads for cost validation;
- trade/order-flow only if incremental evidence warrants it.

## EXPERIMENT ACCEPTANCE THRESHOLDS

Freeze before outcome access.

Primary proposed gates:

- **Launch information (H1):** ≥2% relative Brier-score improvement over strong B0 and positive-effect evidence under registered inference.
- **Downside information (H2):** ≥0.10 ATR-unit reduction in mean MAE at equal coverage with an explicit adverse-tail non-deterioration bound.
- **Economic timing (H3):** ≥0.10 common-budget R improvement per eligible episode versus registered comparator, positive absolute expectancy under doubled costs, and controlled adverse tail.
- **Stability:** positive direction in ≥70% of quarterly folds plus adequate name/period diversity.
- **Prospective promotion review:** ≥90 sessions and adequate statistical support with actual availability/latency/cost observations.

These are predeclared research hurdles, not measured effects and not universal industry standards.

## MAJOR RISKS

- stale/final-bar historical data masquerading as decision-time data;
- survivorship / changing-universe bias;
- daily-context freshness mismatch;
- duplicate information sold as “RS edge” against a weak baseline;
- selecting only episodes that later form pivots;
- time-of-day confounding;
- news/catalyst contamination;
- adjustment-basis seams;
- whipsaw cost of early probes;
- publication of uncalibrated probabilities;
- accidental authority widening.

## OPEN DECISIONS

Sol should make these only after Phase 1 evidence:

- exact confirmatory universe;
- primary market benchmark assignment;
- volatility unit;
- final episode expiry/cooldown;
- whether catalyst-unknown is excluded or stratified;
- whether early probe policy is worth testing economically;
- whether probability output is justified or state/ordinal output is the ceiling.

## RECOMMENDED FILE / MODULE TOUCHPOINTS

Prefer additive paths under existing owners, for example:

- `engine/entry_radar/` — new versioned research detector/spec + shared PIT record integration;
- `engine/entry_radar/replay/` or a clearly adjacent research outcome namespace — intraday-specific labels, without changing frozen W5 semantics;
- `research/live_entry_radar/rs_pullback_launch/` — prereg, data-admission receipt, study outputs;
- `scripts/` — bounded research dataset / replay entrypoint;
- `tests/` — PIT, timing, basis, population and ambiguity mutation tests;
- Terminal qualification modules only if current owner census confirms they are the canonical data boundary.

Do not alter production consumption paths in Phase 1.

## DONE_WHEN FOR THE TOTAL PROGRAM

The total program is done only when:

1. source/data law is accepted;
2. registered historical experiment is complete with controls/ablations;
3. claimed incremental effects pass the frozen gates;
4. prospective first-seen validation passes;
5. calibration is demonstrated for any probability surfaced;
6. research evidence is integrated through the existing canonical owner with all authority still false until separately admitted;
7. Entry Radar / Terminal / dossier consumers render the same canonical evidence;
8. a paired prospective comparison establishes whether the evidence improves the actual incumbent Mastermind decision process;
9. only then does the existing decision/sizing owner make a separate promotion/admission decision.

A negative empirical result is a valid completion: document the falsified hypothesis and do not ship a signal.
