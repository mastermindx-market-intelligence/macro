# Terminal Rotation & Pivot Intelligence
## Research, product and implementation specification — 3 November 2026

**Status: SPEC_ONLY / reviewable design proposal.** The source assessment and design are complete. No new market backtest, live forecast, acquisition, alert, deployment or trading authority is claimed.

**Existing programme homes:** WS:LIVE-ENTRY-RADAR for tactical episodes and pivot research; WS:LEADERSHIP-ROTATION-INTELLIGENCE for group leadership measurements. This is an additive specification in the existing Leader Pivot research package. It creates no new workstream or runtime.

**Commission:** The Chairman requested a Terminal system that tracks rapid sector/style rotation, recognizes the developing conditions around tops/bottoms, and explains differences across environments, horizons and leadership duration. “High latency” is interpreted as the intended low-latency monitoring.

**Direct principal work rationale:** PRINCIPAL_JUDGMENT. The unresolved work is product architecture, scientific target definition and reconciliation with existing negative evidence. One native conceptual adviser challenged the predictive contract; no native implementation/research worker, external Fabric run or watcher was commissioned.

**Bounded design DONE_WHEN:** source-grounded reuse map; an actionable Terminal journey; distinct observation, forecast and economic claims; causal time/data contracts; a falsifiable, owner-compatible research protocol; independent conceptual challenge; ordered implementation slices and precise proof requirements. Completing this document does not complete the production programme.

---

## 1. Executive decision

Build **Rotation & Pivots** as one coherent Terminal experience using the existing leadership, quote, research and event owners.

Its user promise is:

> Understand what is changing, where participation supports that change, which price levels matter next, and what evidence would confirm or disprove a prospective turn.

The design has three separately qualified capabilities:

1. **Observe:** current relative performance, leadership acceleration, participation, concentration and changes since a prior observation.
2. **Anticipate:** target-specific conditional estimates for a known level encounter or leadership transition, with a horizon and explicit competing outcomes.
3. **Validate:** show when a claim was issued, what was known, what happened next, and whether the model beat appropriate alternatives.

Do not make a universal bullish/bearish confidence number. An outperforming sector can still be falling; an improving five-minute view can coexist with a deteriorating daily view; an accurate forecast can be uneconomic after execution costs.

The commercial distinction should be an understandable market narrative linked to causal evidence and a reproducible decision history. Indicator count, visual complexity and apparent precision are not acceptance criteria.

### Initial scope

Start with qualified US sector ETFs, broad-market benchmarks and the existing eligible liquid-leader population. Extend to industries and GMI themes through their current membership owners. Extended hours, other countries and cross-asset execution require their own source/session qualification; they are not implied by the US implementation.

The user's current tech/defensive observation is the motivating hypothesis. This assignment did not acquire a current market tape or independently establish that today's market is in that state.

---

## 2. What already exists, and what must change

The assessment used Terminal master **2ded360882b9c721e690907ff363b553781fb920**, Macro source base **930f674ef08bb56ef2e7e0c08f27b93c19b63a22**, and protected Mastermind procedure **9f65957e29eba92245d78609f032aaea523b7cb4**. The latter supplies skillpack schema mastermind.sol_skillpack.v1, version 1.0.1, bootstrap major 1.

| Existing asset | Verified source finding | Reuse and boundary |
|---|---|---|
| Terminal RS × 30m Pivot Study | Local on-demand historical study; 65/260 aligned 30m relative-return lookbacks; confirmed two-left/two-right swing lows; later reclaim; next-bar-open entries | Preserve as a versioned comparator and research/replay experience. It does not become live merely through a UI rename. |
| Four study arms | RS+pivot, pivot, RS+EMA and EMA | Preserve the controls and their opportunity accounting. |
| Historical data preparation | Stored 5m history is resampled; only complete aligned sessions survive; clocks are ET display epochs | Reuse reviewed aggregation primitives where compatible. Introduce a separately qualified current-session consumer; do not remove research completeness checks to make a live screen move. |
| Historical evaluation | Adjustable assumed round-trip bps, descriptive 70/30 chronology, explicit non-PIT limitation | Not a sealed holdout, executable-cost model or accepted predictive result. |
| Macro Leader Pivot package | Merged #8649 contains separate completed rejection, confirmation, failure and expiry work, with a staged research protocol | Continue through the existing Radar/TOI/Evaluation seams. |
| Leadership Rotation | Existing group_measurement, transition_observation and research_estimate contracts | Retain those different meanings and evidence modes. |
| Sector Central participation candidate | Terminal #1232 was open at 448a42a29fee765bb01476a9e0b93459ced5a2d4; adds ranked participation and leadership changes | Integrate through its existing programme after its source is accepted; do not take over or edit its live carrier. |
| Quote Hub | Documented shared fan-out, delayed US and entitled real-time aggregate modes, freshness classification | Preferred existing transport. Entitlement and actual runtime latency were not tested here. |
| Chart intraday API | Documents delayed history and a 45-second ordinary cache; a distinct seconds lane has a different cache | Historical chart resolution is not proof of real-time monitoring. Use measured source evidence. |
| Existing environment chain | risk_radar → market_state → regime_vector remains the owner path | Consume its supported fields; do not build another fused regime scorecard or allocation router. |

Source references: [I1]–[I8].

### Two pivot constructions must remain distinct

Terminal's study and Macro's reference are not interchangeable:

- **Terminal research baseline:** a two-left/two-right low becomes knowable only after the confirming bars, then a later reclaim is evaluated.
- **Macro completed-rejection reference:** a completed 30m bar undercuts the low of the prior four full 30m bars, closes back above that reference and in at least the upper half of its range; a later qualifying one-minute close can confirm above its frozen high.

Keep separate species IDs, inputs and event clocks. A migrated UI must not silently rewrite one construction into the other or compare their metrics without aligning populations and information.

### Source facts versus production facts

Merged source was verified for Terminal #879 and Macro #8649. Current signed-in production behavior, live quote entitlement, measured latency, admitted historical cohort and prospective predictive qualification remain unverified in this assignment. Earlier handoff claims are retained as historical evidence, not fresh production certification.

---

## 3. Non-negotiable reuse and negative evidence

The current kill registry contains these exact boundaries:

| Existing boundary | Effect on this design |
|---|---|
| DNR:KILL-ROTATION-CYCLE-CONFLUENCE | No rotation × cycle-position entry-confluence construction or experiment. Displaying distinct context does not authorize combining it into a trading gate. |
| DNR:KILL-REGIME-SCORECARD | No duplicate gamma/vol/flow/breadth composite regime verdict and allocation surface. Reuse the existing environment chain. |
| DNR:KILL-FUSED-COMPOSITE | No new composite risk/health authority in score, rank, size or escalation. Any target-specific forecast still needs its own accepted construction and promotion route. |
| DNR:KILL-OUTCOME-AUDITION | No per-ticker “best timeframe” selected from historical outcomes. |
| DNR:KILL-PSS-F3-RESIDUAL | Do not revive the killed standalone residual-reset timing construction under a new name. |

The earlier Leader Pivot work also records failed or unearned peer-recovery, synchronization and bottom-localization constructions. Keep these as explicit negative controls and evidence, rather than deleting them from the story. [I5, I7]

This new Chairman request authorizes assessment and design. The document does not silently repeal the above scientific dispositions. A genuinely different future hypothesis must state the construction difference and clear the existing admissibility process before outcome access. Ordinary volatility, trend and time-of-day variables already permitted in the primitive baseline remain useful; they do not create a new regime authority.

---

## 4. Market observation model

### 4.1 A hierarchy the user can navigate

The drill-down is:

**Market → sector/style → industry/theme → eligible stocks → prospective level encounter.**

Every group needs a point-in-time membership version, benchmark, weighting rule and coverage. A group label must not disguise overlap: QQQ, XLK and a semiconductor basket can share large exposures, while a stock can belong to multiple themes.

Start with stable groups and a clear benchmark. Dynamic GMI themes enter when their historical membership and availability are supported. Never reconstruct yesterday's theme using today's winners.

### 4.2 Relative strength has several distinct meanings

For asset i versus benchmark b over horizon h, use the existing exact relative-wealth interpretation:

\[
RW_{i,b}(t,h)=\frac{P_i(t)/P_i(t-h)}{P_b(t)/P_b(t-h)}-1
           =\exp(r_i(t,h)-r_b(t,h))-1.
\]

Preserve the return basis, corporate-action basis and currency. The difference of two simple returns is not the same quantity.

Show separately:

- Absolute return.
- Relative wealth versus market.
- Relative performance versus sector or qualified peers.
- Cross-sectional percentile within a named eligible universe.
- Change in that percentile.
- Trend/acceleration in relative performance.
- Breadth and concentration.
- Time spent in a leadership state.

A percentile is not a probability of rising. Residual return is not investor-flow attribution.

For within-group comparisons exclude the subject from its peer benchmark, using known weights and sufficient remaining support. Require a support floor; a one-stock “theme” cannot independently confirm that stock.

### 4.3 Leadership is a trajectory

An observable trajectory can be described as:

- Emerging.
- Strengthening.
- Established.
- Weakening.
- Lost.
- Unavailable or contested.

The exact transition rules are versioned measurements with persistence and hysteresis. They must show what delay the stability requirement introduces. Do not claim that groups move around a fixed clockwise cycle.

Useful measurements include rank persistence, top-cohort retention, leadership age, pairwise overtakes, breadth change, dispersion and the contribution of dominant members. Cross-sectional rank turnover describes rotation speed; it does not itself establish exploitable predictability.

For the technology/defensive use case, compare:

1. Relative performance of explicitly defined baskets.
2. Their absolute returns.
3. The participation within each basket.
4. Their rate/yield and market-beta exposures, when those measurements are supported.
5. Whether the lead persisted across multiple completed observations.

“Defensives outperform while both groups fall” and “defensives rise with expanding participation” must produce different explanations. Relative-price movement does not prove dollars moved directly from one basket to the other.

### 4.4 Rolling-window artifacts

A trailing return can improve because an old negative observation leaves the window. Decompose newly observed performance from the disappearing-window contribution where the existing contracts support it. A rank jump caused by stale peers or a changing universe is not a clean leadership transition.

Compare groups at a synchronized decision cutoff, carrying freshness and missingness. A newly updated sector must not appear to beat a lagging sector solely because its timestamp is later.

---

## 5. Multiple horizons and changing environments

### 5.1 Keep the horizons visible

A proposed initial display matrix is:

| Horizon | Role | Publication rule |
|---|---|---|
| Quotes / eligible second aggregates | Current price context and source health | Provisional/live status according to actual source |
| 1m / 5m | Fast relative change and participation | Closed observations for durable events; forming separately labeled |
| 15m | Optional early-warning research | Separately qualified candidate; never a relabeled 30m confirmation |
| 30m | Existing structural reference | Preserve causal confirmation and reference definitions |
| 60m / 120m | Fixed higher context | Compare against matched-memory and information-age controls |
| Daily / weekly | Structural leadership and broader environment | Last actually available completed record; developing context explicitly distinct |

The first launch need not populate every row. Unsupported horizons stay unavailable.

An improving five-minute view alongside a weak daily trend should read “intraday repair inside a daily decline.” An aligned recovery can read differently. Do not average away the disagreement.

US session anchors, holidays, daylight-saving changes and shortened sessions come from the existing exchange-calendar owner. A 120m grid leaves a remainder in a normal US session; freeze how partial terminal buckets are represented and exclude them from full-bar claims.

### 5.2 Environment is context with an owner

Consume separate supported measurements of trend, volatility, liquidity, dispersion, participation and cross-asset conditions from their current owners. Retain each field's update clock and evidence class.

An initial product can describe:

- Persistent directional movement.
- Range-like movement.
- Broadening participation.
- Concentrated leadership.
- Abrupt volatility expansion.
- Mixed or insufficient evidence.

These are explanations of supported measurements, not a newly authoritative fused market state. If the existing owner supplies a qualified posterior or state vector, preserve its version and scope.

For research, test predeclared interactions between the target and admitted context. An oversold observation near support during an orderly range is a different conditional question from the same oscillator reading during a high-volatility decline.

### 5.3 Duration and adaptation

The correct question is “how stable has this leadership been, and how often have comparable supported states persisted?” A turn is not due simply because a timer has elapsed.

Candidate research tools include:

- Run-length distributions for leadership.
- Survival/transition-hazard models with censoring handled explicitly.
- Online change-point detection.
- Owner-approved Temporal Grain measurements.
- A fixed multiscale feature vector before any adaptive selector.

Adams and MacKay provide a causal online change-point method; they do not establish a profitable market-pivot model. [E6]

Use change-point evidence initially to flag uncertainty or drift under the existing model-health owner. It must not trigger unrestricted retraining, new strategy search or changed trade authority.

An adaptive temporal challenger is optional and last. It must beat the strongest fixed and memory-matched alternatives, retain the existing temporal owner, and never use ticker-specific outcome audition. Fixed designs remain the champion if adaptation fails. [I5]

Spectral/wavelet cycle work, if ever admitted, stays research-only with causal endpoint handling, uncertainty, and a clear distinction from the forbidden rotation × cycle-position construction.

---

## 6. Pivot anticipation: define something we can test

### 6.1 The central target

At a decision time t, for a level already known by t, estimate the chance that a specified favorable barrier is reached before a specified adverse barrier within horizon H.

\[
p_{\mathrm{up}}(t,H)
 =P(\tau_U<\tau_L,\ \tau_U\le H\mid\mathcal I_t).
\]

For the same origin and barriers, estimate lower-first and neither-hit as well. The three probabilities sum to one. Source loss is not the same as neither-hit, and lower-first is not harmless censoring.

Mirror the construction for downside turns only through a separately validated bearish species. Top warnings, long-position risk reduction and an executable short strategy are different products; borrow, locate, costs and authority do not carry over automatically.

The system can seek warning before a confirmed pivot or large breakout. It cannot know the ultimate high/low before any informative evidence exists.

### 6.2 Prospective population

Define candidates from every qualifying encounter with known levels. Include failures and no-turns.

Candidate levels may include:

- Prior session/week high or low.
- Opening-range boundaries after their measurement interval finishes.
- Session VWAP and supported deviation bands.
- Anchored VWAP from an event anchor actually known then.
- Previously confirmed structure.
- Qualified volume-profile or options-related levels from existing owners.

A level constructed from the eventual session low cannot be used to “predict” that low. A symmetric ZigZag, centered filter, full-sample decomposition or future-smoothed regime is unsuitable as a live feature.

A level is a zone with a construction version, not an exact price guaranteed to hold. Normalize distance with a volatility measure frozen at the relevant origin.

### 6.3 Lifecycle

Use the existing Radar event lifecycle and owner-approved species extensions to express:

**Watching → forming evidence → confirmed reclaim/rejection → failed, expired or completed outcome.**

These names describe a proposed UI projection, not new Runtime or event enums. Exact implementation must use the current accepted schemas or an explicit compatible extension.

Keep the original watch, its source inputs, initial level and invalidation. Confirmation creates a later event; it does not move the original marker backward. Failure does not erase the watch.

Separate:

- Early level approach.
- Observed rejection.
- Later structural confirmation.
- Subsequent favorable outcome.

### 6.4 Six output questions

Preserve the prior Leader Pivot target separation:

| Output | User question |
|---|---|
| Downside distribution | How much adverse movement remains plausible within the horizon? |
| Launch / continuation | How likely is the specified favorable barrier before invalidation? |
| False start | Once reclaimed, how often does this construction fail under the stated condition? |
| Confirmation cost | How much price/time does waiting consume, including non-confirmations? |
| Remaining opportunity | How much potential movement remains under a qualified conditional estimate? |
| Economics | Did a specified policy improve net common-budget outcomes after execution assumptions? |

Before qualification show observed geometry or UNESTIMATED, never invented percentages.

### 6.5 Wide confluence without repeated votes

Organize evidence into families:

| Family | Examples | Interpretation limit |
|---|---|---|
| Leadership | Market-relative and sector-relative performance, persistence | Outperformance is not necessarily a gain |
| Participation | Ex-self breadth, equal-weight agreement, concentration | Coverage and membership matter |
| Location | Known levels, VWAP distance, structural context | Geometry is not a guaranteed support mechanism |
| Momentum | Slope, deceleration, asymmetry, divergence, volatility-scaled stretch | RSI/MACD/stochastic variants often reuse the same price information |
| Activity/liquidity | Time-of-day-adjusted volume, spread and qualified trade/quote measures | OHLCV cannot identify institutional intent |
| Environment/events | Existing regime-vector fields, event calendar, volatility/liquidity state | Mixed clocks or missing events cannot be silently treated as confirmation |

The UI exposes supportive, opposing and unavailable evidence. There is no “8 of 10 indicators agree” probability.

Regularized target-specific models and shallow-tree challengers may test incremental information under the accepted research protocol. A derived family must beat a strong baseline with the same primitive data, memory and coverage. More complex representations receive no credit for being given more information.

Actual order-book imbalance needs qualified trade/quote or book observations. Cont, Kukanov and Stoikov studied short-interval price impact; their result is not evidence that signed candle volume predicts future pivots or proves who traded. [E5]

---

## 7. Live data and latency architecture

### 7.1 Reuse the current transport

Extend the accepted quote/Data OS path:

- Existing provider connectors and Quote Hub supply observations.
- Existing identity/calendar/corporate-action owners qualify them.
- Existing measurement owners compute incremental group/structure context.
- Existing Radar owns tactical episodes and permitted event delivery.
- Existing Evaluation OS / TrialLedger owns research records and promotion.
- Terminal consumes a versioned projection and renders the experience.

No browser-side source authority, new collector, parallel cron, duplicate queue, event ledger or provider connection per viewer.

Do not copy the historical study's full-session filter into the live path. Current-session processing must accept eligible completed intervals before the close while explicitly reporting the incomplete session. Keep historical baseline behavior unchanged.

### 7.2 Clock contract

For each material observation/decision retain, where actually available:

- Market event time.
- Bar start/end and finality.
- Provider publication time.
- Mastermind first receipt.
- Feature computation cutoff.
- Decision issue time.
- Consumer render time.
- Revision identity and correction time.
- UTC clock basis plus exchange-local presentation.
- Source-age and cross-input skew.

Unavailable clocks remain null with a reason. Do not reconstruct first receipt from a later download.

The legacy study's ET wall-clock display epoch is not a UTC instant. Convert at an explicit typed boundary; do not compare it directly with real UTC for latency or causal ordering.

The relevant age is the age of the underlying observation, not the time the cache response was assembled. A fresh response can contain old prices.

### 7.3 Proposed performance targets

These are engineering objectives pending a qualified feed, not measurements from this assignment.

| Metric | Initial target | Qualification |
|---|---|---|
| Accepted source receipt → updated projection | p95 ≤ 2 seconds | Named liquid US scope; measure compute/queue time |
| Projection received → visible UI | p95 ≤ 1 second | Representative browser and device |
| Eligible final one-minute bar receipt → event | p95 ≤ 3 seconds | Excludes upstream delay, which remains visible |
| Source event → visible quote/measurement | Aim p95 ≤ 5 seconds on an entitled supported live path | Verify per source and representative symbols; publish observed percentiles |
| Failure/degradation | Immediate visible stale/delayed/unavailable state once contractual threshold is exceeded | No successful-response timestamp laundering |

Measure p50/p95/p99, missed/deadline-late updates, coverage and disconnect recovery. Do not grade a whole universe from only its freshest liquid symbol.

The historical API's documented cache and the hub's documented fallback cadence mean these targets cannot be assumed for the present route. Entitlement already approved in policy and actual runtime serviceability are separate questions; no repeated commercial approval should be requested where the standing attestation applies. [I3, I4, I9]

### 7.4 Operational failure cases

| Condition | Required behavior |
|---|---|
| Missing peer or denominator | Unavailable/partial coverage; no fabricated zero return |
| Sparse breadth | Show observed count and uncertainty/identification bounds; withhold unstable ranking |
| Delayed feed | Preserve useful delayed observations with conspicuous age; suppress claims requiring faster availability |
| Mixed source clocks | Synchronize cutoff or withhold comparisons beyond the skew allowance |
| Halt or no trading | Explicit halt/quiet status; no synthetic activity |
| Late/out-of-order events | Deterministic ordering and versioned corrections |
| Corporate action | Requalify basis and identity; do not interpret a split as a price collapse |
| Reconnection | Recover through existing owners; no duplicate event issuance |
| Missing optional features | Use only a preregistered supported fallback, otherwise abstain |
| Model out of supported scope | Describe observations; probability is unavailable |
| Market closed | State the relevant session and last supported observation |
| Benchmark stale | Do not publish fresh-looking relative leadership against it |

---

## 8. Terminal product design

### 8.1 Navigation and composition

Retain the shared Terminal shell. Use the existing Discover/Sector Central and RS-pivot entry points, joined through canonical instrument and group identities. Preserve old deep links with appropriate navigation compatibility.

Working product label: **Rotation & Pivots**.

Four views:

1. **Market now:** concise interpretation, strongest supported changes, freshness and timeframe.
2. **Leadership:** sectors, industries and themes; table/map plus trajectories and participation.
3. **Pivot watch:** selected eligible names near known levels, evidence and lifecycle.
4. **Replay & evidence:** as-issued observations, outcomes, model qualifications and research controls.

Do not build another global menu or a standalone tactical app.

### 8.2 First-screen hierarchy

The first viewport should answer:

- What changed?
- Which groups are strengthening or weakening?
- Is participation broad or concentrated?
- Which timeframe owns the claim?
- Is this a developing watch, a confirmed event or a forecast?
- What would disprove it?

Use a short deterministic headline, a compact horizon matrix, a leadership table and a few explainable watches. Methodology and raw provenance belong in an inspectable drawer, while freshness and validity remain visible.

A hypothetical description, not a live market finding:

> Technology's intraday relative performance is improving while its daily trend remains weak. Defensive participation has stopped expanding. Treat this as a developing intraday repair; a durable leadership change is unconfirmed.

### 8.3 Leadership table

Suggested columns:

- Group and benchmark.
- Absolute move.
- Relative performance over selected horizon.
- Rank and rank change.
- Participation and coverage.
- Leadership persistence.
- Emerging/established/weakening state.
- Observation age.

A user can choose one declared metric for sorting. Do not insert an unqualified hidden score into ordering. Ties, unchanged states, missing groups and sparse support remain distinct.

The trajectory chart uses an explicitly defined relative level and change measure with recent timestamped path. It must not suggest a deterministic rotation cycle or pretend price comparisons are fund-flow measurements.

### 8.4 Pivot detail

Each detail view shows:

- Instrument and inherited sector/theme context.
- A chart with the known level/zone, invalidation and supported horizon.
- Watch issuance, later confirmation and actual outcome as distinct markers.
- Supportive evidence and the strongest opposing evidence.
- Forming versus closed observations.
- Data age and source coverage.
- Forecast qualification and relevant base rate, if qualified.
- Link back to the original leadership context.

During an unsupported forecast state, “Watching support; confirmation pending” is useful. A made-up probability is not.

Do not display a purchase instruction or position size from a summary, sentiment output or unqualified forecast.

### 8.5 Alert discipline

Use the existing alert owner only after exact alert-type admission. Observed transitions and predictive watches have different labels and permissions.

Deduplicate by the incumbent episode identity. Use tested persistence/hysteresis and an explicit expiry to limit chattering. Measure false alerts per session, missed changes and actionable lead time. A five-second render cadence is not a five-second alert cadence.

User-facing alerts should be tied to an observable change and explain its invalidation. No volume spike is automatically “institutional buying.”

### 8.6 Visual and accessibility contract

Use the existing design system and Noir direction:

- Neutral surfaces, even borders, strong typography and semantic chart ink.
- No colored left edges or relocated accent stripes on containers.
- Dark treatment: restrained depth, legible hierarchy, calm instrumentation.
- Light treatment: deliberate research canvas, white surfaces and hairline separation.
- English/Chinese content parity, including long labels and degradation copy.
- Desktop 1440px and phone 390px proof.
- Keyboard navigation, visible focus, semantic tables and non-color status cues.
- Reduced-motion handling; live data must not constantly reorder a row under the pointer or steal focus.
- Phone layout prioritizes the interpretation, selected horizon and watch detail; dense secondary columns move into disclosure.

Before implementation, produce the editable design in the currently accepted Paper project after verifying its exact file/custody. This assignment did not inspect or modify Paper and does not claim an approved visual artifact.

---

## 9. Research evidence and its limits

The literature motivates experiments. It does not validate this Terminal system.

| Primary source | Supported finding | Consequence for the build |
|---|---|---|
| Moskowitz & Grinblatt, 1999 | Industry components matter to documented stock momentum | Test industry context beyond market/stock primitives; do not transfer the finding to minute-scale pivots automatically. |
| Heston, Korajczyk & Sadka, 2010 | Intraday continuation and short-horizon reversal have different time patterns | Include time-of-day and microstructure controls; adjacent half hours are not interchangeable. |
| Gao et al., 2018 | Historical first-half-hour information predicted the last half-hour for their market/ETF study | A limited motivation for intraday context; not validation of RS leader pullbacks or every 30m period. |
| Rosa, 2022 | An intraday momentum study lost predictability out of sample; conditional regimes mattered in its analysis | Test stability and conditional support; never install a published effect as a permanent rule. |
| Nagel, 2011 working paper / 2012 publication | Short-term reversal compensation varies with liquidity conditions | A mean-reversion opportunity and hazardous execution can occur together; test both. |
| Cont, Kukanov & Stoikov, 2010/2011 working paper | Order-book imbalance relates to short-interval price impact | Use real eligible microstructure data for such claims; contemporaneous impact is not automatically predictive lead. |
| Adams & MacKay, 2007 | Causal online change-point/run-length inference | Method candidate for drift/transition research; no financial-edge result. |
| Daniel & Moskowitz, 2016 | Momentum strategies can suffer severe reversals in rebound/panic environments | Test environment dependence; this is not direct evidence for a long-only leader watch. |
| Bailey et al.; Bailey & López de Prado | Selection across many backtests inflates apparent performance | Retain all attempted variants and apply selection/dependence-aware evidence. |

See [E1]–[E10]. Publication dates refer to the papers, not later webpage migration dates. No performance number from another study is used as a forecast for this product.

### Important counterevidence already inside Mastermind

The original Leader Pivot report explicitly found no admitted evidence establishing its full leader × group × 30m conjunction. It names failed constructions and keeps adaptive clocks unearned. The rotation programme distinguishes measured product completion from predictive qualification, and records an earlier statistical sizing failure. These are reasons to retain strong controls and the current science gate. They are not evidence that all useful live observation is blocked. [I5]–[I7]

---

## 10. Backtest and prospective validation contract

### 10.1 Distinguish three research questions

1. **Observation utility:** Does the product accurately and promptly describe leadership and participation?
2. **Forecast utility:** Do its conditional estimates improve on a strong baseline?
3. **Economic utility:** Does an explicit decision policy improve outcomes after executable costs and constraints?

Passing one does not pass the next.

### 10.2 Data requirements

Use point-in-time security identity, group membership, corporate actions, sessions and source availability. Preserve delisted and changed instruments where the admitted panel supports them; disclose missing ones. Do not use today's index or leader constituents throughout history.

Distinguish:

- Corrected historical reconstruction.
- Historically available information under an accepted availability contract.
- Actual retained as-issued Mastermind observations.

A current retrieval timestamp cannot prove historical availability. A long corrected-price panel can support limited descriptive research while remaining insufficient for a strong live-timing claim.

Seek multi-year coverage across materially different environments. Coverage, source authority and statistical power determine the final window; this document does not invent an available 2015–2026 panel or authorize a data purchase.

### 10.3 Preserve the original first experiment

The existing preregistration proposes a strong primitive B0 versus B0 plus completed 30m structure, each in a regularized and shallow-tree form. That first four-model comparison remains the starting experiment after source admission and actual registration. This design does not substitute a large confluence grid.

Keep Terminal's four-arm lab as an engineering/research comparator, with its different species and limitations. It is not automatically the canonical market trial.

Later additions are independently admitted:

- Measured rotation/participation source increment.
- Industry or qualified theme information.
- Fixed higher-horizon context.
- Earlier level-encounter/15m warning.
- Separately admitted duration/adaptive-temporal challenger.

A rejected or unadmitted family stays recorded. “Not tested” does not mean zero value; it also does not mean earned inclusion.

### 10.4 Strong controls

Require:

- Same eligible opportunity population and decision timestamps.
- Raw price/history baseline with the same data and dependency closure.
- Same universe, memory, observation age and coverage.
- All level encounters, including no pivot and failed turns.
- Fixed-timeframe and matched-memory controls.
- Time-of-day controls.
- Leave-one-family-out and add-one-family comparisons.
- Sensitivity to source lag, costs, bar anchors and coverage.
- Existing named negative constructions as constraints or approved controls, never unauthorized reruns.
- Perturbed future data producing no change to past issued outputs.

No best-stock or best-regime selection after seeing the final results.

### 10.5 Chronology

Use chronological training, separate calibration, validation and a sealed final test. Fit scalers, thresholds, feature selection, groups where estimated, regime models and hyperparameters using only eligible past data.

Purge overlapping outcomes/episodes around split boundaries. An embargo covers the registered maximum outcome horizon and finalization lag. Keep correlated names together in calendar blocks; random row splitting is inappropriate.

If a hidden-state model is ever admitted, replay filtered states available at the time. Full-sample smoothed states are future-informed.

The prior protocol specifies dependence-aware block uncertainty, eight quarterly OOS folds for its cross-era claim, and prespecified power. Shorter data can support a narrower development result, not a claim that the requirement has disappeared. [I5]

### 10.6 Event labels and economics

Freeze the existing reference targets before reveal. For the original Macro launch target, the proposed reference is upper +1 A0 before lower −0.5 A0 over 120 RTH minutes, with A0 known and frozen. This document does not overwrite that definition with a new threshold.

A prospective top-watch species needs a separate target and registration. Do not assume symmetric performance.

For barrier ties unresolved by OHLC, retain ordering uncertainty and paired bounds. An adverse barrier is a competing event; missing source is censoring; an observed quiet horizon is neither-hit. These cannot be collapsed.

Evaluate earliest executable action after issuance, including:

- Bid/ask and fees.
- Slippage and price impact.
- Measured publication/processing delay.
- Halts and gap-through-stop risk.
- Order assumptions and supported size.
- Overnight exposure where applicable.
- Borrow/locate only if separately evaluating shorts.

An early-entry policy and a confirmation policy share the original episode budget and terminal horizon. A later entry cannot buy more shares with a tighter stop or receive extra future time merely to improve reported R. Include missed entries and abstentions in the opportunity denominator.

### 10.7 Metrics

**Rotation measurement:** freshness, coverage, synchronized comparisons, transition delay, false transition/churn rate and accurate reconstructed-versus-observed labels.

**Forecasts:** Brier/log loss, calibration with uncertainty, precision/recall at a fixed alert budget, competing-risk coherence and risk–coverage curves.

**Anticipation:** first actionable lead time; fraction of the subsequent move already completed at that time; false watches per session; never-confirmed watches; missed turns; conditional confirmation delay and full-population opportunity cost.

**Economics:** net common-budget expectancy, tails/drawdown, turnover, capacity, time in exposure and results under higher admitted costs.

**Robustness:** distinct episodes, days, names, environments and folds; concentration of contribution; optional-data and latency sensitivity.

A high win rate alone is not a release criterion.

### 10.8 Existing proposed promotion thresholds

The earlier Leader Pivot proposal includes a relative Brier improvement of at least 2%, common-budget economic improvement of at least 0.10 R, robustness under doubled admitted costs, positive direction in at least 70% of eligible quarterly folds, and at least 90 supported prospective sessions after the exact champion is frozen. It also proposes power, tail and calibration requirements. [I5]

These are existing proposed scientific policy values to be ratified through the owner, not results, universal financial constants or a new shortcut. Retain the complete originating protocol; do not cherry-pick only one threshold.

Actual registration still needs source/cohort manifests, untouched cutoff, inspected-history exclusions, implementation/version pins and independent reveal custody. No full trial was registered or run in this assignment.

### 10.9 Research factory and monitoring

Use the existing TrialLedger/Evaluation OS, not a new experiment database. Record all feature, horizon, cost, seed and selection variants. Multiple-testing controls and deflated performance diagnostics supplement chronology and prospective validation; they do not repair unavailable inputs. [E9, E10]

Start with small interpretable models. Large sequence models, unconstrained RL and automatic daily parameter search are optional research only if a demonstrably better accepted experiment justifies them.

After a model is qualified, the existing model-health owner monitors calibration, coverage, drift, alert burden and failure rate by supported cohort. An alarm may reduce claims or abstain under an accepted policy. It must not silently retune the strategy on the same evidence used to grade it.

---

## 11. Interface and ownership contract

The following is a design sketch, not a drop-in schema amendment. Bind it to the current strict owners before implementation.

~~~text
Observation
  identity: security/group ID, membership version, benchmark, return basis
  clock: event/end/received/available/issued, clock basis, finality
  coverage: expected, observed, missing, source age, skew, eligibility
  measurements: absolute return, relative wealth, rank, breadth, concentration
  context_refs: current owner-supplied environment and group measurements
  construction: version, source references, evidence mode

PivotWatch projection
  incumbent episode/event identity and species
  level construction, known_at, zone, frozen volatility unit
  watched_at, latest state, confirmed_at, invalidated_at, expiry
  supporting/opposing/unavailable feature families
  target definitions and model version
  estimates: qualified value or typed UNESTIMATED/UNAVAILABLE
  research/evidence references

Evaluation reference
  source manifest and input revision
  trial/model/target version
  issue time and original feature snapshot
  opportunity denominator and abstention reason
  observed outcome / censoring / ordering uncertainty
  qualification scope and expiry
~~~

| Responsibility | Existing owner |
|---|---|
| Feed acquisition, identity, availability, basis | Data OS / Terminal capture / Quote Hub |
| Group membership and themes | Sector/group owners and GMI |
| Group measurement and transitions | Leadership Rotation |
| Pattern semantics | Technical Opportunity Intelligence |
| Tactical episode lifecycle | Live Entry Radar |
| Environment context | risk_radar → market_state → regime_vector |
| Temporal measurement | Temporal Grain |
| Trials, labels, selection and qualification | Evaluation OS / TrialLedger |
| Entry permission and sizing | Existing Entry Engine and portfolio authority |
| UI and navigation | Terminal shared shell and existing workspaces |

Each link preserves source version, null behavior and custody. A convenient display projection owns no competing lifecycle.

---

## 12. Delivery plan: useful slices with proof

This is an editorial task graph under the existing programme plans. It does not change workstream waves or admit Jobs.

| Node | Dependencies | Bounded outcome | Required proof |
|---|---|---|---|
| D1 | Current code, rules and literature | Reviewable product/research specification | This document, exact source links, conceptual challenge and byte readback |
| R1 | D1 review; current source/access custody | Qualify existing quote and historical seams for one supported universe | Real source-age/clock/coverage receipts; explicit delayed/unavailable cases; no new collector |
| R2 | R1; existing leadership contracts | Measured intraday leadership and participation in current Terminal route | Accurate current-session observations; synchronized benchmarks; dark/light EN/ZH desktop/phone browser evidence |
| R3 | R1; Radar/TOI species contract | Causal pivot watch with known-at-time levels and replay | Future-mutation invariance, confirm/fail/expire behavior, no repaint, non-duplication |
| R4 | Source admission; existing prereg/TrialLedger | Original B0/P1 test, followed only by earned additions | Frozen manifest, chronology, controls, complete results and independent scientific adjudication |
| R5 | R4 and prospective/calibration gates | Target-specific forecasts and permitted alerts | Actual as-issued shadow history, calibrated support, user burden, production-path proof |
| R6 | Temporal Grain acceptance and admissible new comparison | Optional duration/adaptation improvement | Increment beyond best fixed/memory-matched references, sufficient cost/data support; omit on failure |

R1 and editable UX preparation can proceed independently once each has its actual access and source custody. Observation R2 need not wait for predictive R5. A dataset lacking historical availability can still be assessed for a narrower measured display; it cannot be silently promoted to timing evidence.

### First concrete implementation slice

Qualify and expose the existing Quote Hub's source-age, basis and current-session coverage for a small supported sector/benchmark universe, then render a measured intraday rotation strip in the current Terminal leadership surface. Reuse existing identity and measurement contracts. The acceptance demonstration must show a normal update, delayed source, missing benchmark, partial group and reconnect without invented leadership.

This is the highest-value first build because it resolves whether the desired fast monitoring is actually supportable. It also produces useful observations before any predictive claim.

### Verification focus

Use meaningful tests where behavior can fail:

- Prefix invariance under appended/changed future data.
- DST, shortened sessions and partially elapsed current sessions.
- Same underlying UTC instant across display conversions.
- Stale-symbol and mixed-clock comparison refusal.
- Point-in-time group membership and ex-self benchmark support.
- Event correction/reconnect idempotency.
- Missing optional inputs and calibration abstention.
- Barrier ordering/censoring cases and common-budget comparisons.
- Real browser keyboard, mobile and theme journeys.

Avoid adding tests that merely mirror descriptive prose or launching broad suites for this document-only change.

---

## 13. Completion, open evidence and exact next action

### What this assignment established

- The intended 30-minute RS feature was located and inspected at a pinned source revision.
- Reusable group, quote, pivot and scientific owners were identified.
- The historical/live clock incompatibility and complete-session limitation were identified.
- Distinct Terminal and Macro pivot constructions were reconciled at design level.
- Existing prohibited constructions and negative evidence were preserved.
- Primary research and counterevidence support a conditional, falsifiable architecture.
- A native principal adviser challenged candidate selection, causality, confluence, adaptation and validation; the design incorporates those findings.

### What remains unproven

- Actual runtime real-time entitlement and source-to-screen latency.
- Current production behavior of the audited code paths.
- Complete current source admission and historical/PIT cohort availability.
- Predictive lift, calibrated pivot probabilities and net economics.
- An accepted Paper design and implemented browser journey for this extension.
- Formal independent source review or scientific acceptance of this proposal.

### Continuity and source custody

This document is a draft source proposal, not an accepted Agent OS decision. Existing workstream records and handoffs are unchanged: **PLAN_NOT_ORG_LINKED** for this additive proposal until reviewed and linked through the incumbent record writer. The original programme plans remain canonical.

Observed adjacent open carriers include Terminal #1232 and Macro leadership/risk work. They are references, not assignment or permission to edit their branches. Historical unknown/refused RS audit/publication effects remain untouched with their original carriers.

No external worker, acquisition, market experiment, watcher or deployment was started. No portfolio/trading permission or existing held-PR state was changed.

**Next implementation action:** R1 source/clock qualification on the existing Quote Hub and Data OS path, after this proposal's technical/source review and current writer/effect check. Do not begin with an adaptive model, new collector or all-indicator score.

**Bounded assessment disposition:** PROVEN_OUTCOME for the source assessment and reviewable design deliverable only. **Production programme complete: false.**

---

## Source register

### Internal immutable sources

[I1] Terminal study engine and component, source 2ded360882b9c721e690907ff363b553781fb920:
- [rsPivotStudy.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/rsPivotStudy.ts)
- [RSPivotStudy.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/workspaces/RSPivotStudy.tsx)
- [Merged Terminal #879](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/879)

[I2] [Intraday route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/app/api/intraday/route.ts).

[I3] [Quote Hub architecture and freshness contract](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/hub/README.md).

[I4] [Live Entry Radar workstream](https://github.com/mastermindx-market-intelligence/macro/blob/930f674ef08bb56ef2e7e0c08f27b93c19b63a22/agentos/workstreams/WS-LIVE-ENTRY-RADAR.md) and [latest dated RS-leader handoff](https://github.com/mastermindx-market-intelligence/macro/blob/930f674ef08bb56ef2e7e0c08f27b93c19b63a22/agentos/handoffs/LIVE-ENTRY-RADAR-2026-10-11-rs-leader.md).

[I5] Leader Pivot package, source originally read at b8f14e308b57cd772e1464217e1e2becc1286086; the executive-ruling and owning-workstream blobs were rechecked unchanged at 930f674ef08bb56ef2e7e0c08f27b93c19b63a22:
- [Executive ruling](https://github.com/mastermindx-market-intelligence/macro/blob/b8f14e308b57cd772e1464217e1e2becc1286086/research/live_entry_radar/rs_pullback_launch/leader_pivot_2026-10-08/chapters/01_EXECUTIVE_RULING.md)
- [Empirical preregistration proposal](https://github.com/mastermindx-market-intelligence/macro/blob/b8f14e308b57cd772e1464217e1e2becc1286086/research/live_entry_radar/rs_pullback_launch/leader_pivot_2026-10-08/chapters/08_EMPIRICAL_PREREGISTRATION.md)
- [Model architecture](https://github.com/mastermindx-market-intelligence/macro/blob/b8f14e308b57cd772e1464217e1e2becc1286086/research/live_entry_radar/rs_pullback_launch/leader_pivot_2026-10-08/chapters/09_MODEL_ARCHITECTURE.md)
- [Ownership map](https://github.com/mastermindx-market-intelligence/macro/blob/b8f14e308b57cd772e1464217e1e2becc1286086/research/live_entry_radar/rs_pullback_launch/leader_pivot_2026-10-08/chapters/11_OWNERSHIP_AND_INTEGRATION.md)
- [Merged Macro #8649](https://github.com/mastermindx-market-intelligence/macro/pull/8649).

[I6] [Leadership Rotation workstream](https://github.com/mastermindx-market-intelligence/macro/blob/930f674ef08bb56ef2e7e0c08f27b93c19b63a22/agentos/workstreams/WS-LEADERSHIP-ROTATION-INTELLIGENCE.md) and [latest dated handoff](https://github.com/mastermindx-market-intelligence/macro/blob/930f674ef08bb56ef2e7e0c08f27b93c19b63a22/agentos/handoffs/LEADERSHIP-ROTATION-INTELLIGENCE-2026-10-14.md).

[I7] [Kill registry, selected exact keys above](https://github.com/mastermindx-market-intelligence/macro/blob/930f674ef08bb56ef2e7e0c08f27b93c19b63a22/research/DO_NOT_REBUILD.md).

[I8] [Terminal #1232, open candidate at observed head 448a42a29fee](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1232). PR state is time-sensitive; this is a source-assessment observation, not a perpetual status assertion.

[I9] [Macro AGENTS.md, including standing commercial-rights attestation](https://github.com/mastermindx-market-intelligence/macro/blob/930f674ef08bb56ef2e7e0c08f27b93c19b63a22/AGENTS.md).

[I10] [Protected Mastermind skillpack index](https://github.com/mastermindx-market-intelligence/Mastermind/blob/9f65957e29eba92245d78609f032aaea523b7cb4/docs/sol_skills/INDEX.md).

### External primary evidence

[E1] Moskowitz, T. J., and Grinblatt, M. (1999), “Do Industries Explain Momentum?”, Journal of Finance 54(4), 1249–1290. [Publisher](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00146). Publisher metadata shows a later digital posting; the article is 1999.

[E2] Heston, S., Korajczyk, R., and Sadka, R. (2010), “Intraday Patterns in the Cross-Section of Stock Returns.” [Kellogg primary publication page](https://www.kellogg.northwestern.edu/academics-research/research/detail/2010/intraday-patterns-in-the-cross-section-of-stock-returns/) and [author working paper](https://www.bauer.uh.edu/departments/finance/documents/Heston_Korajczyk_Sadka_paper_UH.pdf).

[E3] Gao, L., Han, Y., Li, S. Z., and Zhou, G. (2018), “Market intraday momentum,” Journal of Financial Economics 129(2), 394–414. [WashU primary publication page](https://profiles.wustl.edu/en/publications/market-intraday-momentum/).

[E4] Rosa, C. (2022), “Understanding intraday momentum strategies,” Journal of Futures Markets 42(12), 2218–2234. [Publisher abstract and data statement](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375). The inspected abstract supplies the out-of-sample and regime statements; no full-paper replication is claimed.

[E5] Cont, R., Kukanov, A., and Stoikov, S., “The Price Impact of Order Book Events.” [Author paper](https://arxiv.org/abs/1011.6402). This source supports short-interval impact and the importance of actual order-book events, not an automatic future-prediction claim.

[E6] Adams, R. P., and MacKay, D. J. C. (2007), “Bayesian Online Changepoint Detection.” [Author paper](https://arxiv.org/abs/0710.3742).

[E7] Nagel, S. (2011 working paper; journal publication 2012), “Evaporating Liquidity.” [NBER working paper](https://www.nber.org/system/files/working_papers/w17653/w17653.pdf).

[E8] Daniel, K., and Moskowitz, T. (2016), “Momentum Crashes.” [Columbia primary research page](https://business.columbia.edu/faculty/research/momentum-crashes) and [AQR publication page](https://www.aqr.com/insights/research/journal-article/momentum-crashes).

[E9] Bailey, D., Borwein, J., López de Prado, M., and Zhu, Q., “The Probability of Backtest Overfitting.” [Author revised working paper, February 2015](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). This is the inspected version, not a claim to a newer result.

[E10] Bailey, D., and López de Prado, M. (2014), “The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality.” [Author paper](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).

External evidence was inspected on 3 November 2026. The proposed design and engineering targets are synthesis, not claims those papers tested this exact system.
