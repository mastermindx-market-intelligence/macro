# Deep Research: Prophet All-Weather Indicator x Regime x Timeframe Research Program

**Research date:** 2026-10-03  
**Purpose:** durable scientific reference for the Astra CEO takeover of Prophet regime / indicator / timeframe / theme intelligence  
**Status:** RESEARCH ARCHITECTURE + SOURCE SYNTHESIS / NO NEW PRODUCTION AUTHORITY  
**Important evidence boundary:** this Deep Research run produced a detailed research architecture and source synthesis. It did **not** complete the planned broad historical backtest, regime-conditioned indicator tournament, or final implementation build. Those remain execution work for the receiving Astra programme.

## Executive conclusion

Astra should not begin by trying to prove that "3D stopped working," nor by searching for a replacement indicator. The problem should be decomposed into four distinct causal layers:

> **market clock -> filter memory -> market regime -> opportunity lifecycle**

This distinction matters because changing from 1D to 2D to 3D often changes more than the number printed on a chart. It can also change bar phase, session grammar, indicator memory, warmup behaviour, data plane, information availability, and the point in the opportunity lifecycle at which a signal becomes visible.

The appropriate Prophet question is therefore not:

> "Does 3D work in good markets and 1D work in bad markets?"

It is:

> **Does the incremental value of waiting for 2D/3D confirmation versus acting on faster 12H/1D evidence change predictably with rates, breadth, volatility, leadership persistence, rotation speed and theme state, after controlling for bar construction, indicator memory, candidate composition, opportunity age and multiple testing?**

That is a tractable scientific programme.

A second important correction concerns "24-hour trading." Nasdaq's published system hours still distinguish regular trading from extended sessions, and Nasdaq's planned nearly continuous overnight session remained prospective at the research date. At the same time, SEC staff documented rapidly growing but still small aggregate overnight NMS volume, with unusually high concentration in the most-active names. This makes overnight price discovery a plausible **security- and theme-specific interaction**, particularly in heavily traded AI/semiconductor names, but a weak universal explanation for all daily/3D indicator deterioration.

Primary external references:
- Nasdaq system hours: https://www.nasdaqtrader.com/content/TechnicalSupport/nasdaq_sys_hours.pdf
- Nasdaq Global Trading Hours FAQ: https://www.nasdaq.com/docs/nasdaq-global-trading-hours-faqs
- SEC staff memo on overnight trading: https://www.sec.gov/files/2026_TM_Overnight_Trading_Roundtable_Memo_090926.pdf
- FINRA extended-hours risk disclosure: https://www.finra.org/index.php/rules-guidance/rulebooks/finra-rules/2265

## 1. Existing Mastermind evidence that must constrain the research

### 1.1 Prophet's incumbent technical construction is not ordinary price MACD

The current Prophet research baseline uses an RSI-MACD construction rather than standard price MACD 12/26/9. The handoff census identified:

- RSI length: 14
- fast/base smoothing: 14 / 60
- signal smoothing: 5
- StochRSI: 14 / 3 / 3
- absolute-session multi-day anchoring era already present in current source

Therefore any new study that compares "Prophet MACD" against vanilla price MACD without reconstructing the actual incumbent would be testing the wrong baseline.

Relevant internal source:
- `engine/confluence_tiers.py`
- `engine/session_anchor.py`
- existing handoff source census in this directory

### 1.2 Temporal Grain already defines the correct causal decomposition

The existing Temporal Grain programme separates:

- **G — Grain:** the bar duration / sampling interval
- **A — Anchor / session:** how bars are phased and which sessions are included
- **K — Kernel memory:** the effective smoothing / filter-memory timescale
- **D — Data / instrument plane:** vendor, instrument, adjustment, venue and feed identity

This decomposition should be reused rather than recreated.

Relevant internal sources:
- `agentos/workstreams/WS-TEMPORAL-GRAIN-INTELLIGENCE.md`
- `research/signal_engine/temporal_scale/CHARACTERISTIC_MARKET_TIME_SIGNAL_GRAIN_ARCHITECTURE_FREEZE_2026-09-03.md`
- merged Temporal Grain W0 PR #6790

### 1.3 Prior broad regime-conditioning evidence is a scoped null

Existing Mastermind work reported a broad regime-reliability study over roughly 57k matured signals. In that construction, signal-family main effects were larger than regime interactions, and the interaction results were not sufficiently stable for promotion.

That result does **not** prove regime conditioning is useless. It does prove Astra must not treat "regime matters" as already established merely because recent tape behaviour is intuitive.

Relevant internal source:
- `research/REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md`

### 1.4 Phase-21 is development evidence, not untouched validation

The earlier Prophet forensic population had already been inspected. It contained useful clues about:

- worse outcomes in some rising-real-yield / weak-breadth periods;
- old versus fresh multi-timeframe turns;
- late entry and opportunity consumption;
- severe-loss and large-winner asymmetry.

But because the population was already inspected and macro relationships were often calculated over only a small number of decision blocks, it is hypothesis-generating rather than independent confirmation.

### 1.5 Phase-22 must remain prospective and frozen

The existing Phase-22 preregistration should remain separate from any retrospective tuning introduced by this research. Its exact population and no-peek requirements must not be weakened to accelerate a preferred conclusion.

Relevant internal source:
- `research/prophet_v4/US_PROPHET_PHASE22_FAST_CYCLE_REGIME_PROSPECTIVE_PREREG_2026-09-19.md`

### 1.6 Simple anti-chase fixes have already failed or remained unproven

The existing 1.5-ATR extension challenger did **not** validate the intuitive "extended = reject" rule as an entry gate. The source ruling preserved extension as descriptive texture, not authority.

Likewise, the existing RS .75 threshold was not established as a validated protective boundary. Evidence suggested the .75-.85 band should not simply be discarded, while the hottest >=.85 region showed a stronger continuation-failure warning.

Relevant internal sources:
- `research/prophet/cpu_leadership/ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md`
- `research/prophet/cpu_leadership/ENTRY_DIRECT_EXTENSION_CHALLENGER_FINDINGS_2026-09-21.md`

The core implication is:

> **leadership != extension != signal age != confirmation cost != remaining opportunity**

Prophet must measure these separately.

## 2. Temporal-grain research Astra should execute

### 2.1 Separate grain from filter memory

A 60-period smoother on 1D bars and a 60-period smoother on 3D bars do not represent the same elapsed market memory.

For a simple EMA:

```text
alpha = 2 / (N + 1)
half_life_bars = ln(0.5) / ln(1 - alpha)
```

To approximately preserve elapsed memory when changing bar duration:

```text
alpha_new = 1 - (1 - alpha_old)^(d_new / d_old)
```

This is only an approximation for nonlinear constructions such as RSI-MACD, but it provides a useful robustness control.

Each timeframe study should therefore compare:

1. **native periods / native timeframe**
2. **matched elapsed-memory variant**
3. **same grain, alternative kernel**
4. **same kernel memory, alternative grain**

If performance changes under (1) but not under matched-memory controls, the apparent "timeframe effect" may really be filter memory.

### 2.2 Phase-offset robustness for 2D and 3D

A non-overlapping 2D bar has two possible phase offsets. A non-overlapping 3D bar has three.

Astra should test all valid absolute-session phases and report the dispersion of results across phase choices. Never select the winning phase after seeing outcomes.

A robust multi-day effect should survive reasonable phase perturbation. If "3D alpha" disappears under another equally valid offset, the result may be calendar phasing rather than economic structure.

### 2.3 Warmup invariance is different from anchor invariance

Identical bar boundaries do not guarantee identical indicator values if two calculations begin from different history lengths. EMA/Wilder initialization can differ materially.

Required controls:

- shared sufficient warmup window;
- explicit initial-state convention;
- tolerance-based parity checks;
- no false attribution of initialization differences to bar anchoring.

### 2.4 Session grammar

For intraday horizons, exact session definition is part of the signal identity.

At minimum distinguish:

- RTH only;
- premarket + RTH;
- RTH + after-hours;
- registered extended/overnight trade-date construction;
- exact vendor-native daily bars.

Do not assume that two 12H bars algebraically equal one vendor daily candle.

### 2.5 Timeframe set

Where source data supports it, the empirical matrix should include:

- 4H
- 8H
- 12H
- 1D
- 2D
- 3D
- 1W
- Monthly structural context

The first priority is not exhaustive coverage. It is making the clock identity explicit enough that a result can be reproduced.

## 3. The central 3D / fast-rotation hypothesis

The user's proposed mechanism can be expressed causally:

> **narrow breadth + fast leadership turnover -> shorter stock follow-through -> fast daily impulse completes before slow 3D confirmation -> buying on 3D confirmation occurs later in the local opportunity lifecycle**

This is plausible, but it must be tested as an **interaction**, not a story.

### 3.1 Required measurable quantities

For every eligible occurrence:

- first fast signal time;
- 1D trigger time;
- 2D confirmation time;
- 3D confirmation time;
- weekly structure state;
- price paid for each additional confirmation;
- ATR-normalized confirmation cost;
- fraction of eventual MFE consumed before each confirmation;
- false starts avoided by waiting;
- severe losses avoided;
- large winners excluded because slow confirmation never arrived;
- time to positive;
- time to MFE;
- continuation failure;
- signal invalidation;
- leadership persistence;
- theme/sector participation.

### 3.2 The decisive interaction statistic

For a family (F) and regime (R), define:

```text
Delta_3D_1D(R, F) = Performance_3D(R, F) - Performance_1D(R, F)
```

Then compare:

```text
Delta_3D_1D(narrow breadth + fast rotation)
-
Delta_3D_1D(broad breadth + persistent leadership)
```

Repeat for:

- 3D vs 2D;
- 2D vs 1D;
- 1D vs 12H.

A bad regime lowering all returns is not evidence that timeframe selection improves. The hypothesis requires the **relative value of waiting** to change.

### 3.3 Confirmation-cost curve

A key output should be:

> **rotation speed x fraction of favourable excursion consumed before confirmation**

with separate curves for 1D / 2D / 3D.

If 3D cost rises sharply as leader half-life falls, while 3D still materially reduces false starts in slow/persistent regimes, that would provide a rigorous version of the user's intuition.

## 4. Regime reconstruction

The research should create continuous point-in-time state variables first and coarse labels only second.

### 4.1 Macro / rates layer

Candidate features:

- 5y and 10y TIPS real-yield level;
- 5 / 20 / 63-session real-yield impulse;
- nominal Treasury level and curve;
- inflation expectations / breakevens where appropriate;
- Fed policy path proxies;
- source-vintage macro surprises rather than current revised values.

Primary sources:
- Federal Reserve H.15: https://www.federalreserve.gov/releases/H15/default.htm
- FRED 10Y TIPS constant maturity: https://fred.stlouisfed.org/series/DFII10
- FRED real-time-period documentation: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

### 4.2 Financial conditions / liquidity layer

Candidate features:

- Chicago Fed NFCI / ANFCI;
- OFR Financial Stress Index;
- credit spreads;
- Treasury market liquidity metrics;
- reserves / Fed assets / ON RRP where economically justified.

Primary sources:
- Chicago Fed NFCI: https://www.chicagofed.org/research/data/nfci/current-data
- OFR FSI: https://www.financialresearch.gov/financial-stress-index/
- NY Fed Treasury liquidity research: https://www.newyorkfed.org/research/staff_reports/sr827

### 4.3 Market-state layer

Candidate features:

- index trend;
- realized volatility;
- VIX / term structure;
- cross-sectional dispersion;
- correlation;
- breadth;
- equal-weight vs cap-weight;
- new highs / lows;
- advance/decline;
- percentage above 20/50/200D;
- index concentration.

VIX methodology:
- https://cdn.cboe.com/resources/vix/VIX_Methodology.pdf

### 4.4 Rotation / leadership layer

This is one of the highest-value new layers.

Measure:

- top-N leader overlap from t to t+k;
- leader rank autocorrelation;
- leader half-life;
- sector rank turnover;
- theme rank turnover;
- dispersion of theme returns;
- share of positive names inside the leading theme;
- concentration of market return contribution.

These measures can directly test whether "quick-rotation regime" is a measurable state rather than a subjective label.

### 4.5 Theme / subtheme state

Required characteristics:

- point-in-time membership;
- membership version;
- historical taxonomy changes;
- within-theme breadth;
- theme relative strength;
- theme acceleration;
- leader persistence;
- earnings/catalyst density;
- peer propagation;
- theme concentration.

Do not backfill today's theme taxonomy into history without a versioned historical-membership rule.

### 4.6 Decision-time semantics

For every regime feature retain:

- `observation_time`
- `economic_reference_time`
- `source_publish_time`
- `source_available_time`
- `system_ingested_time`
- `system_known_time`
- `decision_cut`
- `vintage_id`
- `revision_status`

A feature is available only if:

```text
system_known_time <= decision_cut
```

This is especially important for macro series with revisions.

## 5. Indicator families to evaluate

Do not treat hundreds of indicator names as independent evidence. Test dependency families.

### 5.1 Incumbent Prophet family

- RSI-MACD
- StochRSI
- existing confluence cascade

### 5.2 Trend / smoothing

- SMA / EMA families
- trend ribbons
- Ichimoku
- adaptive trend
- ATR-adaptive trend
- state-space / Kalman challengers

### 5.3 Trend quality / efficiency

- ADX / DMI-like directional strength
- Aroon / recency
- Kaufman efficiency ratio
- path efficiency / directional persistence

### 5.4 Standard momentum

- price MACD
- ROC
- RSI
- stochastic
- multi-horizon momentum
- residual / benchmark-relative momentum
- cross-sectional momentum

### 5.5 Compression / breakout

- Bollinger compression
- ATR / range compression
- Donchian / breakout channel
- volatility expansion
- squeeze / release constructions

### 5.6 Volume / participation

- money flow
- volume participation
- VWAP context
- volume profile where causal and source-qualified
- theme / peer breadth

### 5.7 Structure / reversal

- causal pivots
- confirmed fractals
- HH/HL and LH/LL sequences
- break/retest/reclaim
- divergence
- gap / imbalance
- fakeout / failure state

### 5.8 Cycle / adaptive challengers

Candidates worth testing, not assuming:

- existing cycle transform;
- double-smoothed momentum;
- Ehlers-style cycle filters where formula and lag are explicit;
- Hilbert/phase diagnostics;
- wavelet / multiscale decomposition;
- changepoint detection;
- HMM / regime-switching;
- state-space filters.

These should enter as **challengers** with strong anti-overfitting controls. Indicator folklore should not be promoted merely because it has an appealing narrative.

## 6. Indicator redundancy and confluence

The confluence problem should be reframed from "how many indicators agree?" to:

> **How many independent information families contribute incremental information at this stage of the opportunity?**

Recommended analyses:

- pairwise and conditional correlation;
- partial correlation after market/sector controls;
- mutual information;
- conditional mutual information;
- ablation;
- feature-attribution stability across eras;
- dependency-family clustering;
- signal overlap / event coincidence;
- temporal lead-lag;
- redundancy after conditioning on price path.

If RSI, StochRSI and MACD all fire because the same recent price path turned upward, counting three votes can create false confidence.

Astra should preserve interpretability by using the existing technical-catalog dependency-family metadata rather than collapsing everything into an opaque universal score.

## 7. Theme restriction experiment

The user's low-breadth hypothesis should be tested directly.

### Control

All Prophet-eligible securities at the decision cut.

### Challenger cohorts

- leading sectors only;
- leading themes only;
- leading subthemes only;
- top-k names inside point-in-time leading themes.

### Required outputs

Do not report only hit rate.

Report:

- net excess return;
- MFE;
- MAE;
- severe-loss incidence;
- large-winner incidence;
- winner-payoff contribution;
- opportunity recall;
- excluded future winners;
- turnover;
- theme concentration;
- name concentration;
- effective independent decision dates.

The key question is:

> **Does restricting Prophet to the leading alpha complex in narrow, fast-rotation regimes improve economics after accounting for the winners that the restriction excludes?**

If the result only works because today's researcher already knows AI semiconductors were the winners, it fails.

## 8. Entry versus management

A strategy can fail for different reasons:

1. bad candidate;
2. good candidate, bad timing;
3. valid timing, already unavailable price;
4. valid entry, regime deteriorates after entry;
5. correct entry and regime, but hold law is wrong.

These must be separated.

### 8.1 Survival / hazard framing

For each episode model competing events:

- positive continuation;
- invalidation;
- severe drawdown;
- target attainment;
- theme-leadership loss;
- stop / exit;
- regime deterioration.

Useful methods:

- Kaplan-Meier descriptive survival;
- Cox / stratified Cox if proportionality is defensible;
- discrete-time hazard models;
- competing-risk cumulative incidence;
- survival forests / boosted survival only as challengers.

A high-quality question is:

> **How does the hazard of continuation failure change with signal age, confirmation delay, breadth, leader half-life and real-rate impulse?**

This can distinguish "3D was too late" from "the market deteriorated after the entry."

## 9. Statistical design

A large matrix can easily manufacture attractive results.

### 9.1 Dependency-aware inference

The raw stock-event row is not the independent unit.

Use:

- decision-date clustering;
- decision-week or month block bootstrap;
- Newey-West / HAC for overlapping time-series aggregates;
- theme/sector clustering where relevant;
- effective name count;
- effective date count.

### 9.2 Purged temporal validation

For overlapping forward horizons:

- walk-forward splits;
- purge observations whose label windows overlap the test boundary;
- embargo where leakage risk remains;
- nested model selection for parameter tuning.

### 9.3 Multiple testing

For broad exploratory families:

- Benjamini-Hochberg FDR;
- familywise control for confirmatory primaries;
- White Reality Check / Hansen SPA for strategy/model universes;
- Romano-Wolf style stepdown where appropriate;
- Deflated Sharpe Ratio as a search-adjusted strategy diagnostic.

References:
- White, "A Reality Check for Data Snooping": https://www.jstor.org/stable/2999444
- Hansen, "A Test for Superior Predictive Ability": https://www.jstor.org/stable/27638834
- Romano & Wolf, stepwise multiple testing: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=563209
- Bailey & Lopez de Prado, Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

### 9.4 Minimum regime-cell support

A regime interaction should not become policy because it has many same-day stock rows.

Require meaningful counts of:

- independent time blocks;
- independent names;
- regime episodes;
- distinct eras;
- sufficient state contrast.

### 9.5 Development versus validation

Maintain a contamination ledger including:

- Phase-21 episodes;
- earlier-entry replays;
- RS-threshold study;
- 1.5-ATR study;
- manually discussed ticker/date examples;
- previous technical tournaments.

Prospective Phase-22 evidence remains outside retrospective tuning.

## 10. Backtest result design

For every occurrence, calculate both **bar-normalized** and **elapsed-session-normalized** outcomes.

Required horizons:

- +1 / +2 / +3 / +5 / +10 bars
- matched elapsed-session horizons

Required metrics:

- forward absolute return;
- benchmark/sector/theme-relative return;
- MFE;
- MAE;
- time to positive;
- time to MFE;
- false-cross / false-start rate;
- continuation failure;
- signal persistence;
- trend efficiency;
- severe-loss incidence;
- large-winner incidence;
- large-winner contribution;
- turnover;
- costs;
- confirmation delay;
- confirmation cost;
- fraction of MFE consumed before confirmation.

Do not compare 1D +10 with 3D +10 as if both had the same elapsed opportunity horizon.

## 11. Prioritized experimental portfolio for Astra

### Priority A — baseline and clock truth

**Question:** Are we measuring Prophet correctly?

Deliverables:
- exact incumbent formula reproduction;
- eligible universe reproduction;
- 1D/2D/3D bar parity;
- event-known-time parity;
- era/version map;
- anchor and warmup tests.

Falsifier:
- inability to reproduce historical candidate/signal identity.

No strategy research should be promoted before this is green.

### Priority B — 3D phase and matched-memory experiment

**Question:** Is perceived 3D deterioration a true slower-timescale effect?

Test:
- all 3D phase offsets;
- native period vs matched-memory;
- same data/session across grains;
- same eligible population.

Falsifier:
- effect disappears under equally valid phase or memory controls.

### Priority C — rotation-speed / confirmation-cost interaction

**Question:** Does 3D become uneconomic when leadership half-life shortens?

Primary variables:
- leader half-life;
- breadth;
- real-rate impulse;
- 1D->2D and 1D->3D delay;
- fraction of MFE consumed.

Falsifier:
- confirmation cost does not increase relative to protection as rotation accelerates.

### Priority D — theme restriction in narrow regimes

**Question:** Should Prophet restrict candidate generation to leading alpha themes during narrow markets?

Primary comparison:
- all eligible names vs point-in-time leading-theme universe.

Falsifier:
- gains come mostly from hindsight membership or exclusion of too many eventual large winners.

### Priority E — family x regime tournament

**Question:** Do different dependency families add incremental value in different states?

Families:
- trend;
- momentum;
- compression;
- participation;
- relative strength;
- structure;
- risk;
- adaptive/cycle challengers.

Falsifier:
- family main effects dominate and interaction signs are unstable across eras.

### Priority F — entry vs management decomposition

**Question:** Are recent losses caused primarily by bad entry selection or post-entry state deterioration?

Use hazard / competing-risk framework.

Falsifier:
- regime-at-entry explains little but post-entry deterioration explains more, implying management rather than candidate selection needs change.

## 12. Product implications if the hypotheses survive

A robust positive result would **not** imply one universal dynamic indicator score.

A better Prophet architecture would retain independent planes:

- candidate identity;
- technical occurrence;
- maturity;
- current entry availability;
- theme/subtheme leadership;
- regime/environment context;
- evidence/ranking;
- management/hold state;
- evaluation.

Potential bounded policy behaviours, only after validation:

### Broad / persistent leadership environment
- slower confirmation can carry more value;
- 2D/3D/weekly structure may serve stronger confirmation and hold functions;
- broader candidate universe may remain acceptable.

### Narrow / fast-rotation environment
- leading-theme restriction may become more important;
- fresh 12H/1D/2D lifecycle states may deserve higher research priority;
- slow confirmation may be context rather than front-door trigger;
- hold law may shorten if post-entry continuation hazard deteriorates.

### Disorder / low-estimability environment
- abstention;
- fewer candidates;
- lower confidence;
- no forced timeframe mapping.

The final architecture should be **all-weather through differentiated behaviour and abstention**, not through one score claimed to understand every market.

## 13. Recommended execution order

1. Reconcile current Prophet version and candidate populations.
2. Validate data, clocks, sessions, anchors and warmup.
3. Build point-in-time regime and rotation-state variables.
4. Complete technical method/equivalence census.
5. Run 3D phase and matched-memory falsification tests.
6. Run rotation-speed / confirmation-cost interaction.
7. Run theme-restriction test.
8. Run family x regime tournament under multiplicity control.
9. Decompose entry versus management with hazard models.
10. Freeze challenger policies.
11. Independent reproduction from immutable artifacts.
12. Prospective shadow.
13. Separate authority ruling before any live rank/gate/size change.
14. Product/Terminal integration only after semantics are stable.

## 14. Research governance

Astra should keep principal responsibility for:

- research architecture;
- disputed causal interpretation;
- experiment-family budgets;
- cross-repository owner reconciliation;
- final promotion/adjudication.

Use the existing subagent fabric for bounded implementation, data census, literature review, backtest shards and independent review. Per the Chairman's standing instruction, suborchestrators may use eligible Grok, Cursor, GLM 5.3 and Sol 6.1 routes through the existing fabric; no ChatGPT-native subagent spawning.

The research programme should preserve this rule:

> **No indicator, regime label, theme restriction, threshold, timeframe or model earns authority from narrative plausibility. It earns authority from reproducible point-in-time evidence against the incumbent under frozen evaluation rules.**

## 15. Bottom line

The user's observation should be taken seriously, but not literally encoded as "3D is broken."

The strongest working synthesis is:

> **The economic value of a technical signal is a function of its information family, its filter memory, where it lands in the opportunity lifecycle, how quickly leadership is rotating, how broad participation is, and what macro/market state constrains persistence.**

That view explains why 1D can feel too noisy, 3D can feel too late, and 2D/12H can appear more useful in a narrow, fast-moving tape without assuming any timeframe is permanently superior.

The most important immediate scientific goal is to determine whether the **cost of slow confirmation rises systematically as leadership persistence falls**, while preserving evidence on the false starts that slow confirmation avoids.

If that interaction survives phase, memory, population, regime and out-of-sample robustness checks, it can become one of the central design principles for an all-weather Prophet. If it fails, Prophet should not be rearchitected around the recent tape.

---

## Internal source map for Astra

Read these current Mastermind sources alongside this report:

- `research/prophet_v4/astra_regime_indicator_handoff_20261004/00_ASTRA_CEO_ASSIGNMENT.md`
- `research/prophet_v4/astra_regime_indicator_handoff_20261004/01_RESEARCH_INTAKE_AND_AUDIT.md`
- `research/prophet_v4/astra_regime_indicator_handoff_20261004/02_SOURCE_CENSUS_AND_REUSE_MAP.md`
- `research/prophet_v4/PROPHET_US_V4_RECOVERY_AND_INTELLIGENCE_GRAPH_OS_MASTERPLAN_BY_SOL_2026-08-17.md`
- `agentos/workstreams/WS-PROPHET-US-V4-RECOVERY.md`
- `agentos/workstreams/WS-TECHNICAL-OPPORTUNITY-INTELLIGENCE.md`
- `agentos/workstreams/WS-TEMPORAL-GRAIN-INTELLIGENCE.md`
- `research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W1_EVIDENCE_CENSUS_HANDOFF_2026-08-27.md`
- `research/TECHNICAL_OPPORTUNITY_INTELLIGENCE_W2_DATA_CLOCK_HANDOFF_2026-08-27.md`
- `research/REGIME_RELIABILITY_FACTOR_CROWDING_ADJUDICATION.md`
- `research/SP500_NASDAQ_REGIME_ROTATION_ATLAS_2013_2026.md`
- `research/prophet/cpu_leadership/ENTRY_RS_THRESHOLD_FINDINGS_2026-09-21.md`
- `research/prophet/cpu_leadership/ENTRY_DIRECT_EXTENSION_CHALLENGER_FINDINGS_2026-09-21.md`
- `engine/tech_catalog.py`
- `engine/confluence_tiers.py`
- `engine/session_anchor.py`

## Evidence status

This report is a **research programme and synthesis**. It incorporates Deep Research source work and previously verified internal evidence, but it does not claim that the requested broad backtests, regime reconstruction, family tournament, or product changes have been completed.

That distinction is intentional and should remain visible to every downstream worker.
