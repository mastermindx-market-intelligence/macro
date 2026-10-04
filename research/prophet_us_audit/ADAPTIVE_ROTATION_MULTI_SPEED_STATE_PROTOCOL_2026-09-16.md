# Adaptive Rotation Multi-Speed State Protocol — 2026-09-16

**Status:** research/architecture freeze only; zero ranking, admission, sizing, trade, Prophet, Oracle or portfolio authority.

**Parent:** Chairman-directed adaptive rotation / Prophet / sector-intelligence programme. Existing durable home remains the current Prophet/TOI/Temporal-Grain/Entry-Truth owners; this document does not create a new workstream, scheduler, event store, market-state authority, grader, trial ledger, plan identity or execution plane.

**Procedure pin for this continuation:** protected `mastermindx-market-intelligence/Mastermind@a78b8fe23d8e1ed129880ac47e97ebe96afa8aea`, Skillpack 1.0.1.

**Purpose:** replace the false abstraction “pick the right timeframe and wait for confirmation” with a continuously observed, multi-speed state representation that separates slow leadership/trend from fast entry phase, cycle duration, dependence regime, source quality and decision horizon. The desired machine capability is to estimate *remaining opportunity from the first attainable action time*, not to reward a crossover merely because more slow bars have confirmed.

## 1. Recovered evidence that motivates the redesign

This protocol is downstream of already-exposed research. It does not reclassify those studies as confirmatory evidence.

### RPH-0 — published leadership has long memory while strict-leader membership turns faster

Source carrier: Macro PR #7064 / operation `leadership-persistence-rph0-20260910-sol-001`, frozen result published from commit `aaab39e8a7f9` over the 2026-06-18 through 2026-09-09 published thematic archive.

Measured descriptive facts:

- recent whole-ranking Spearman persistence was `0.873 / 0.805 / 0.802 / 0.661 / 0.655` at 1/2/3/5/7 exact sessions;
- all-window rank half-life was about 14.15 sessions;
- strict top-quartile Kaplan–Meier median residency was 3 sessions;
- one-session movement was dominated by persistence or adjacent-quartile transitions; no measured Q1↔Q4 jump occurred in the exact-session pairs;
- recent published-score continuation pressure was negative at every measured 1–7-session horizon despite the persistent rank ordering;
- the frozen long-cell temporal-shape classifier was structurally unestimable and must remain so rather than being repaired post hoc.

Interpretation ceiling: this is published-output dynamics, not expected returns. The important architecture result is that **level, memory, boundary residency and score pressure can disagree without contradiction**.

### RPH-1 — the recent state was a dependence-regime shift, not simply “higher dispersion”

Source carrier: Macro PR #7095 / daily-sector control, result published from `c962235abf2c` over 2,067 common sessions through 2026-09-09.

Recent-versus-prior controls:

- dispersion mean difference: approximately `-0.0001`;
- dispersion mean ratio: `0.9864`;
- cross-sector correlation mean difference: `-0.1585`;
- cross-sector correlation mean ratio: `0.4361`.

At the fast five-session leadership ruler, recent rank persistence fell from `0.6423` at one session to `0.2132` at three and became negative around five to ten sessions. At the slower 21-session ruler, recent rank persistence remained `0.9036 / 0.7505 / 0.6100 / 0.5782 / 0.4632` at 1/3/5/7/10 sessions.

Interpretation ceiling: the descriptive state is consistent with **multi-timescale decoupling** — slow leadership can remain recognizable while short leadership rotates or mean-reverts and cross-sector co-movement collapses. A single dispersion scalar or a single “rotation speed” label destroys that information.

### MACD cycle continuation — timeframe, filter memory and intended holding horizon are different variables

Source carrier: existing MACD-context research PR #7177; measured research summarized in `CYCLE_EXTENSION_RESULTS_2026-09-15.md` and `HORIZON_EXIT_REVIEW_2026-09-15.md` on that carrier.

Descriptive observations from the exposed 2010–2025 current-universe panel include:

- unchanged 2D versus 3D bar-count parameters confound sampling grain with effective filter memory; matching 2D per-session decay toward the 3D construction materially narrowed the price-MACD contrast;
- on the common-follow-up price-fast deep-negative sample, 3D had a stronger short-horizon point estimate than weekly, while weekly looked materially different at one-year horizons;
- equal native bar counts did not equalize economic holding time or adverse excursion;
- waiting for an opposite crossover materially changed both positive-frequency and payoff shape;
- a higher endpoint-positive rate did not by itself establish incremental expected return, useful SPY-relative return, safe path risk, or a deployable entry policy.

Interpretation ceiling: this is exposed retrospective research with survivorship/price-vintage and multiple-look limitations. Its architecture contribution is nevertheless strong: **signal input, filter memory, sampling grain, entry phase, holding horizon and exit policy must remain separate coordinates**.

## 2. Core ruling — slow state chooses the hunting ground; fast state prices the entry

The adaptive system must not require every horizon to align before acting. That mechanically pushes entries later as more slow observations accumulate.

Instead keep four decisions separate:

1. **Structural eligibility / thesis:** Is this security, sector or theme still inside a slow persistent opportunity state?
2. **Entry economics:** Given that structural state, is the local path early, repaired, re-accelerating, extended, exhausted or ambiguous *now*?
3. **Position-management state:** For an already-held position, has the structural thesis weakened, or is only the tactical entry window poor?
4. **Exit/invalidation horizon:** What event or state actually invalidates the intended holding thesis? This cannot be inferred from the next opposite oscillator cross by default.

A slow bullish state plus a late fast cycle is therefore allowed to output “structural leader / unattractive new entry.” A fast reset inside a slow leader can output “structural leader / tactical repair candidate.” A short-term tactical downturn does not automatically liquidate a longer-horizon position.

## 3. Replace discrete timeframe identity with effective-time coordinates

“1D”, “2D” and “3D” are data aggregation labels, not invariant signal speeds. A 12/26/9 filter on 1D and the same bar-count filter on 3D have different per-session memory.

For every recursive filter, persist at least:

- source sampling grain;
- effective alpha or equivalent time constant in sessions/minutes;
- half-life in exchange sessions;
- normalization-history span in sessions;
- bar anchor and completion semantics;
- source/session basis.

When comparing grains, either hold effective-time memory constant or explicitly declare that memory changed. The already-used conversion

`alpha_target = 1 - (1 - alpha_reference)^(target_sessions / reference_sessions)`

is the minimum deterministic normalization for EMA-like filters. It does **not** make sampled information identical and must not be represented as doing so.

Production-facing intelligence should ultimately consume a **temporal basis vector** rather than a categorical timeframe winner. Example basis lengths are illustrative only until preregistered: fast tactical, intermediate swing, slow structural and long structural filters expressed in session-time constants. No per-name retrospective search for a preferred grain is allowed.

## 4. Multi-Speed Market State Frame

One observation should carry distinct axes; downstream consumers may not average them into one opaque “regime score.”

### A. Structural leadership state

Per market/sector/theme/security as appropriate:

- current rank/quantile or continuous relative-strength level;
- rank-memory surface across exact session horizons;
- strict-leader residency age and survival state;
- score level, velocity and acceleration;
- distance from prior peak/trough and structural invalidation;
- hierarchical parent/child agreement.

### B. Tactical phase state

Computed from source-qualified prices with effective-time-normalized filters:

- fast trend direction;
- fast oscillator/normalized deviation level;
- first derivative / velocity;
- second derivative / acceleration;
- time since last local turn/cross/reset;
- phase distance from recent tactical trough and peak;
- extension relative to volatility/range;
- local drawdown/rebound state;
- whether fast state is leading, coincident with or lagging the slow state.

The important output is not “cross=yes.” It is the path location at observation time.

### C. Cycle-duration state

Cycle length must be estimated with uncertainty, not treated as a fixed 1D/2D/3D choice. Candidate research methods should be compared under a common observation frame before any one is promoted:

- turning-point interval statistics using causal confirmed pivots;
- autocorrelation / partial-autocorrelation decay;
- spectral or wavelet energy over rolling causal windows;
- state-space oscillator / Kalman-style latent phase;
- hazard model for time-to-next tactical turn.

No method may use future-confirmed pivot locations without charging their confirmation delay. “Dominant cycle” can be null or multimodal when the evidence is weak.

### D. Dependence / dispersion state

Keep at least:

- cross-sectional dispersion;
- average pairwise / factor-conditioned correlation;
- first eigenvalue or concentration of common movement where source-qualified;
- sector/theme breadth and participation;
- leadership concentration / entropy;
- cross-sectional transition intensity;
- volatility and liquidity context.

RPH-1 demonstrates why correlation and dispersion must remain separate. The same raw dispersion can occur under very different dependence structures.

### E. Shock and information state

Attach, through existing source/event owners rather than a new event plane:

- macro-data shock state;
- rates/inflation/liquidity state;
- policy/public-administration event state with exact observation/publication clocks;
- geopolitical/supply/weather event state where a lawful source and testable exposure link exist;
- earnings/company-event state;
- options/market-structure state;
- overnight/pre/post-market information state.

These are explanatory/conditioning axes until independently validated; they do not become trading authority because an LLM summarized them.

### F. Evidence state

Every state frame must preserve:

- event time;
- actual information-availability time when known;
- feature-computation time;
- publication/consumer time;
- source and price basis;
- source coverage and missingness;
- correction/revision state;
- point-in-time eligibility;
- model/version identity;
- explicit unknowns.

A missing fine-grain source is an evidence-quality state, not evidence that the asset lacks an opportunity.

## 5. Primary forecast target — remaining opportunity

The first serious challenger should not predict “will this MACD cross be right?” It should estimate conditional outcomes from the first attainable action after the observation became available.

For each declared decision horizon, target a distribution over:

- attainable forward return;
- benchmark/sector-relative return;
- maximum adverse excursion and favorable excursion using the best source legitimately available;
- probability and time of a declared target being reached before declared invalidation;
- time-to-invalidation;
- time-to-next tactical turn;
- usable opportunity lifetime / decay;
- path ambiguity when target and invalidation ordering cannot be resolved at available granularity.

Open/censored outcomes, no-data outcomes, ambiguous intrabar ordering and actual losses must be separate states.

A slow bullish confirmation that arrives after most of the expected remaining opportunity has already been consumed should be allowed to produce low entry utility even while the structural thesis remains bullish.

## 6. Continuous state, not crude regime switching

Initial research should model the state as continuous features and uncertainty, not labels such as `RISK_ON`, `RISK_OFF`, `HIGH_DISPERSION` or `FAST_CYCLE` with hard handoffs.

The eventual controller may use posterior or mixture weights over *already approved* model families, but model/capital policy changes remain versioned and separately validated. Observation state can update frequently; production model approval must not mutate on every tick.

Required separation:

- **observation update:** event/source change;
- **opportunity reconsideration:** affected security/sector dependency change;
- **forecast update:** same approved model, new state/input;
- **uncertainty recalibration:** only matured prior outcomes;
- **model-policy revision:** separately approved version;
- **capital-policy revision:** separately approved and forward validated.

This preserves mobility without turning the platform into an unbounded online self-modifying trading system.

## 7. The first falsifiable multi-speed experiment

### Research question

Among opportunities that already satisfy the same slow structural eligibility, does conditioning entry on fast tactical phase and dependence state improve *remaining-opportunity* outcomes relative to waiting for additional slow confirmation?

### Frozen comparison families

Before reading new outcome tables, register these conceptually distinct policies against the same eligible opportunity set:

**P0 — Slow-confirmation baseline.** Existing eligible opportunity, first action after the declared slow confirmation. No tactical-phase filter.

**P1 — Slow eligibility + fast reset.** Structural eligibility is unchanged; entry occurs only when the fast state satisfies a preregistered repair/re-acceleration condition. If no qualifying reset occurs before structural invalidation, the episode abstains.

**P2 — Slow eligibility + continuous phase.** No binary cross gate. Use preregistered phase/extension features to forecast remaining opportunity at each eligible observation; the decision threshold itself is frozen before the evaluation fold.

**P3 — Memory-normalized grain control.** Repeat the relevant filter comparison with effective per-session memory matched across sampling grains. This isolates part of the “2D versus 3D” question from bar-count memory.

Do not add P4/P5 after seeing results. New policy forms require a fresh registered family.

### Common opportunity identity

All policies must share one canonical opportunity/episode identity from the existing owner. They may differ in action time, but not in which historical universe or thesis became eligible. Ticker/date proximity is not episode linkage.

This makes the core paired estimand:

`outcome(policy_variant, same_episode) - outcome(baseline, same_episode)`

with abstentions and unavailable actions preserved, not deleted.

### Chronology

- information available at time `t` can only use data known by `t`;
- action is the first attainable execution after `t` under the declared market/session policy;
- model/calibration parameters for a fold are frozen using only outcomes matured before that fold;
- observations sharing a market date/episode are dependent and cannot be counted as independent regime evidence;
- later source corrections never rewrite which state/version a historical decision actually consumed.

## 8. Dependence-regime contrasts to preregister

The first regime interaction should be deliberately small, motivated by the recovered RPH evidence rather than a broad search.

At minimum compare the continuous interaction of:

1. slow leadership persistence;
2. fast tactical phase / score pressure;
3. cross-sector correlation/dependence;
4. dispersion;
5. breadth/participation.

The primary failure mode to test is:

> slow structural leader + weakening fast pressure + late tactical phase + low common correlation / high idiosyncrasy → extra slow confirmation arrives after favorable short-cycle entry economics deteriorate.

The corresponding repair hypothesis is:

> slow structural leader + recently reset/re-accelerating tactical phase + improving local breadth + non-extended entry → remaining opportunity is better than at a later slow-confirmation action time.

These are hypotheses, not current system behavior or investment recommendations.

## 9. Sector rotation implication

Sector selection and security entry must become two coupled but distinct layers.

**Sector/Theme layer:** persistent leadership, score pressure, breadth, member participation, dependence regime, macro/exposure context, evidence quality.

**Security layer:** same structural parent state plus company-specific relative strength, fast phase, extension, liquidity, event hazard, invalidation and source availability.

A sector can remain the strongest structural opportunity while individual members have poor entry economics. Conversely a tactical bounce in a weak structural sector need not become a strategic allocation.

The system must retain opportunity denominator and source-qualified denominator separately so sectors with weaker fine-grain coverage do not silently disappear.

## 10. Overnight / 24-hour shadow lane

Observation and execution are separate experiments.

Current Terminal candle policy only represents regular and 04:00–20:00 ET extended sessions. The existing Quote Hub separately contains a true overnight quote seam. Current provider/source qualification must therefore be explicit before any “24h candle” claim.

The first overnight experiment should:

- preserve regular-hours execution policy;
- add only legitimately observed pre/post/overnight information features;
- assign cross-midnight overnight prints to an explicit trading-session identity rather than a naive calendar date;
- keep source/feed identity and timestamp basis visible;
- never forward-fill a missing overnight aggregate as though a trade occurred;
- compare forecast/timing utility with and without the overnight-information features over the exact same opportunities.

Only if that survives does an overnight-execution arm begin, with separate spread, liquidity, quote, venue and fill assumptions.

## 11. Event-driven compute architecture

Nightly builds remain reconciliation/reproducibility, not the sole decision clock.

Reuse the existing event/source and publication planes. Add dependency declarations, not a new queue:

`source/event change -> affected state features -> affected opportunity episodes -> shadow forecast -> existing publication/admin projection`

Examples:

- a new price/session bar updates only dependent fast/phase features and affected opportunities;
- a sector breadth change updates its sector state and member opportunities;
- a macro/policy/company event updates only exposures that declare that dependency;
- a source correction produces a new versioned observation and correction event; it does not silently rewrite an old decision receipt.

Universe-wide nightly jobs can then reconcile drift, complete delayed labels, validate source coverage and materialize reproducible snapshots.

## 12. Ordered implementation waves

### Wave A — source-qualified temporal basis

Extend existing input owners to expose effective-time filter metadata, exact session basis, source lineage, correction state and common-calendar coverage. Do not create a second price store. Terminal PR #594 is a prerequisite for distinguishing finer-history construction from provider-hourly fallback on its existing API path; it is not by itself research admission.

Acceptance: two nominally identical 4h responses with different construction paths are distinguishable, and an unavailable fine-grain path remains an explicit evidence state.

### Wave B — deterministic Multi-Speed State Frame

Build one pure, replayable research producer over existing price/sector inputs. No model first. It emits structural level/memory, tactical phase/extension, dependence/dispersion, breadth and evidence fields with explicit nulls.

Acceptance: deterministic as-of replay, no future pivot leakage, effective-time normalization tests, source/correction tests, and exact same-day dependency behavior.

### Wave C — remaining-opportunity labels

Extend the existing Entry Truth / grading owner rather than creating another grader. Add only the declared target-before-invalidation, time-to-event, MAE/MFE and ambiguity outputs needed by the protocol.

Acceptance: first attainable action time, censored/null/ambiguous states, no same-close fill when unavailable, no outcome leakage, and exact episode linkage.

### Wave D — paired shadow comparator

Execute P0–P3 on one frozen common opportunity population. Use chronological folds and date/episode-aware uncertainty. Keep all attempted cells in the canonical TrialLedger/evaluation owner.

Acceptance: paired coverage, abstention, return, excess, adverse excursion, turnover/action delay and opportunity lifetime. No single positive-frequency metric can promote the challenger.

### Wave E — event-driven shadow updates

Wire the accepted deterministic state producer and fixed shadow model through existing source/event/publication owners. Nightly remains reconciliation. No capital or ranking authority.

Acceptance: a real source change updates only its declared dependencies, produces a versioned shadow output, and is recoverable/replayable after correction.

### Wave F — overnight-information arm

Add source-qualified cross-midnight observation features on the same eligible episodes, regular-hours execution fixed.

Acceptance: with/without overnight feature comparison, explicit source/session identity, gap/sweep handling without fabricated bars, and no overnight fill assumptions.

### Wave G — approved adaptive model routing

Only after earlier waves survive forward evidence may the controller weight among approved forecast families using continuous state. Capital/rank/admission remain separate owners.

## 13. Required metrics

Forecast quality:

- calibration / coverage by horizon;
- proper scoring loss where probabilistic;
- interval width and abstention rate;
- calibration lag after state changes;
- error by source/evidence state.

Decision-policy quality:

- paired remaining return/excess;
- target-before-invalidation and time-to-event;
- MAE/MFE;
- realized action delay versus first eligibility;
- fraction of structural opportunities abstained;
- turnover and policy churn;
- common-opportunity coverage;
- sector/member concentration;
- dependence on a few dates, episodes or regimes.

Operational quality:

- state-update latency from source availability;
- correction replay success;
- source-qualified denominator;
- stale/missing/unknown rates;
- exact model/state/source receipt on every shadow decision.

## 14. Failure / stop conditions

Stop or hold a lane when:

- point-in-time availability cannot be reconstructed for the promised experiment;
- price basis or universe membership is mixed without a declared stratum;
- the candidate only improves after per-name or per-regime outcome-driven parameter selection;
- a cycle estimator requires future-confirmed pivots without charging confirmation delay;
- a regime cell is structurally unestimable;
- a policy's advantage disappears on paired common opportunities or realistic execution timing;
- improvement is only positive-frequency while expected return/path risk/turnover deteriorate materially;
- results are concentrated in a tiny number of dates/spells without surviving dependence-aware analysis;
- source coverage differences are accidentally treated as economic opportunity differences;
- a new component duplicates an existing identity/event/queue/grade/plan/publication authority.

## 15. Product end-state

The premium user experience should eventually answer four questions simultaneously rather than flash one signal:

- **Where is durable leadership?**
- **Where inside that durable state is the asset now?**
- **How much opportunity appears to remain at my intended horizon, with what uncertainty and invalidation?**
- **What changed since the prior decision, and which source/state caused the update?**

Sector Intelligence should show structural leadership and participation, tactical pressure/phase and dependence regime separately. Prophet should consume the same state frame to distinguish thesis quality from entry quality. Terminal should let the user inspect the exact temporal/source context without implying that a slower cross is inherently safer.

This protocol freezes the architecture and the first bounded falsifiable comparison. It does not choose a winning model, timeframe or trade.