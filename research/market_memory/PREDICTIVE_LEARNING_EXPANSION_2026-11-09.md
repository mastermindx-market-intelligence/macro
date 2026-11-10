# Predictive learning expansion: market, sector and security memory

Date: 2026-11-09 (America/Vancouver; source work continued on 2026-11-10 UTC).
Operation: `predictive-learning-expansion-20261109-web-c1`.
Canonical programme: `WS:MARKET-MEMORY-W2C`, with the existing Data OS, Prophet, Sector Intelligence, QLedger/Eval OS and Research Factory owners.
Governing source: Mastermind `b975605771ab8d09994087babad0e9b9cf771288`.
Implementation census: Macro `f3a547cc09872d9aaa719759a6a2daa2832edad5`.

**Disposition:** implementation contract and executable synthetic integration witness. This document extends the existing programme. It does not claim that cross-engine collection, historical coverage, a new learner or predictive skill is deployed. The attached witness passed 13 checks against exact incumbent Data OS source; the existing temporal/read-contract suites separately passed all 175 tests. Operational acceptance remains the ruler in section 2.

## 1. Decision and intended outcome

Build a durable record of what happened, what the system could know, what it actually knew and predicted, and what was learned afterward. Use that record to compare successful anticipations with failures, missed opportunities and periods with no move. Develop better predictions through reproducible experiments and prospective evidence.

The primary implementation is an expansion of **Market Memory**, using Data OS publication and temporal contracts, QLedger/Eval OS claims and grades, and Research Factory experiments. There is no new memory platform, feature store, event bus, trial ledger, model registry, scheduler, automatic learner or trading controller in this design.

The highest-priority integration is **market participation → sector rotation → security selection**. Prophet must consume the exact qualified sector context that existed at its decision cutoff. Sector Intelligence must retain the context and membership that produced its rotation view. Subsequent stock outcomes must be compared with both the market and the contemporaneous sector. A stock rising with a strong market is a different result from a stock outperforming its own sector.

The ambition is cumulative predictive competence. It is not a promise that every pivot has an observable single cause or that unlimited data produces reliable foresight. The useful objective is measurable improvement in calibrated probabilities, timely warnings, opportunity selection and uncertainty handling, after costs and across unseen conditions.

## 2. Completion ruler and present delivery

The parent expansion is operationally complete only when:

1. A real, owner-produced market/sector/security context is captured before an outcome, with its eligible population, omissions and exact source lineage.
2. A real engine decision, abstention or candidate rejection references that context and retains its original output bytes and first registration time.
3. A later user or evaluator can reproduce the historical inputs under the declared reconstruction clock and separately replay the actual original output. A missing replay cannot silently become a reconstruction.
4. A matured outcome attaches without rewriting the earlier evidence. Evaluation measures market contribution, sector-relative contribution, security-specific contribution and feasible timing against preregistered baselines.
5. The same path is demonstrated for every enrolled predictive engine and declared market. Coverage gaps and uninspected cases remain in the denominator.
6. A real consumer uses the record in an investigation or governed research study, and prospective shadow evidence supports any claimed improvement. Source merge, green CI, retained files and attractive retrospective examples are insufficient on their own.

This source delivery provides the detailed contracts, enrollment sequence, acceptance matrix and a runnable synthetic witness. The witness does not invoke a collector, production store, outcome loader, training process or authority mutation. The original programme's 28 tasks, 49 cases and 11 waves remain the canonical plan; this is an additive implementation specification, not a replacement lifecycle.

## 3. What already exists and what must change

The following is a source census at the implementation pin. Source support is not a claim of production coverage.

| Existing owner | Source capability | Necessary expansion or qualification |
|---|---|---|
| Data OS | `lib/dataos/read_contract.py`: explicit CURRENT, RECONSTRUCT and REPLAY; dependency and generation selection; retained-byte digest checks; coverage dispositions | Use these APIs. Enroll concrete producers with authentic publication evidence and complete dependencies. Do not add a competing read-mode abstraction to `temporal.py`. |
| Market Memory context | `engine/neuralweb/market_memory.py`: exact as-known-at context, source bases and fourteen canonical domains | Introduce a versioned successor context profile containing independently attributable Sector Intelligence evidence. Preserve the frozen v1 domain set. |
| Retained generations | `engine/neuralweb/market_memory_pit.py`: immutable objects and exact context/query receipts | Qualify additional source captures and exact references through this owner. Preserve original capture identities and refusals. |
| Forward experience | `market_memory_forward.py`: state/trial/forecast/outcome contracts; `market_memory_experience_accrual.py`: bounded prospective experience | The registered experience population is a finite 126-session SPY pilot. Additional universes require an explicit successor registration, not an in-place expansion of that pilot. |
| Population | `market_memory_population.py`: expected opportunities and disposition accounting | Extend through the existing registration owner to market, sector and security populations, including abstained, missed and unrecorded cases. Existing fit eligibility is false. |
| Actual output admission | `market_memory_production_records.py`: typed capture of `options.signal_episode/v1` | Add producer-specific, versioned adapters for approved sector and Prophet outputs. Arbitrary JSON and reconstructed narratives cannot qualify as actual production outputs. |
| Prophet earnings bridge | `engine/prophet_lab/intelligence_vector.py`: structured earnings evidence and temporal/identity checks | Reuse its evidence discipline. Its current published-event discovery is not proof of complete historical event-set coverage. Add the sector reference to the exact Prophet decision path. |
| QLedger/Eval OS | `engine/qledger.py` and evidence-clock/desk adapters: claims, first-registration clocks and grades | Reuse for issued forecasts and evaluation. Keep no-call population accounting outside directional scores; do not encode no-call as a directional forecast of zero. |
| Research Factory | `adapter_market_memory.py` and `adapter_market_memory_evidence.py`: bounded candidate and retained-reference joins | Extend accepted joins through existing study admission. Existing source access does not grant training or promotion. |
| Readiness and scientific audit | `market_memory_promotion_audit.py`, Factory E0 domain contracts and contextual registration | Reuse existing source-coverage, interval split and promotion audit functions. No new readiness registry or automatic permission switch. |
| Retrospective dossiers | `market_memory_history_dossier.py`: exploratory historical context with explicit gaps | Useful for discovery. Preserve the distinction between retrospective reconstruction and evidence available before a decision. |

Exact source evidence is linked in section 20. The decisive gap is qualified **producer enrollment and consumer joins**, especially a first-class sector context, rather than absence of temporal primitives.

A subsequent bounded overlap check found an active, unmerged Sector owner in [Macro #10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780), head `91add9613ad29dcfb82ff75036dd6519cfc6c06f`. It already implements coherent input capture and retained publication of five Sector documents. Its current release dependencies and original denied CI-registration effect remain on that carrier. Treat this as a source dependency to consume when qualified, not deployed evidence and not an invitation to duplicate its capture system.

## 4. Three records that must never be collapsed

### 4.1 Observations and as-known state

Retain source observations, source revisions, identity and membership generations, normalized features and the dependency manifest used at a cutoff. This record answers: “What information was available under this declared clock, and what was actually received by our system?”

A record needs the incumbent stable security/listing/issuer identifiers; market, currency and calendar; producer and dataset version; raw object or source reference and content hash; relevant clocks; revision and supersession lineage; source basis; units and adjustment convention; code/configuration/model versions; and missingness/freshness information. Use existing fields and receipts where available rather than creating duplicate identities.

### 4.2 Actual reasoning, decisions and forecasts

Retain the emitted output, its publishing receipt and digest, exact context reference, issue/serve/first-registration times, eligible candidate population, forecast horizon, probability or confidence semantics, abstention/veto reason, competing hypotheses and known limitations. Retain decisions even when no trade or no directional call follows.

An engine's published rationale is an observation of its reasoning at that time. A later model-generated explanation cannot replace it. Prompt/model/version references help reproduce a computation, but they do not guarantee byte-identical regenerated output; actual output bytes are the replay authority.

### 4.3 Outcomes and later explanations

Attach realized outcomes, label maturity, pivot confirmation, later data corrections and causal hypotheses as separately timestamped records. Never write a later confirmed pivot, realized return, revised consensus or retrospective explanation into an earlier feature vector.

The later explanation must say when it became known. It may inform a future decision after that time, subject to research qualification. It remains unavailable to a historical training row or evaluation decision before its knowledge cutoff.

## 5. Time and provenance contract

Reuse the incumbent temporal vocabulary. The semantic distinctions are:

| Time | Question answered | Rule |
|---|---|---|
| Economic event or effective time | When did the event occur, or when did membership/terms apply? | This is not automatically when an observer could know it. |
| Publisher availability | When was this specific vintage publicly released? | Require a defensible source timestamp or conservative availability bound. |
| First system observation/ingestion | When did our system actually receive this vintage? | Preserve the original receipt; never backdate a historical import. |
| Computation/readiness | When did this exact derived feature become usable? | A source being available does not prove a feature was computed then. |
| Issue/serve/registration | When did this forecast or output actually exist and reach its declared surface? | Retain exact output and receipt; QLedger first registration remains distinct. |
| Outcome observation and maturity | When was a later outcome available for evaluation or training? | Enforce the training cutoff and complete horizon; immature is unresolved, not negative. |

Data OS already distinguishes publisher-availability reconstruction from system-observation reconstruction. Both are labeled reconstruction. REPLAY requires retained output bytes and matching evidence; absent output refuses. The lower-level coalescing helper in `temporal.py` is not a substitute for this read contract.

Use the existing Market Memory source bases: `live_captured`, `source_vintage`, `public_reconstructed`, `recomputed_history`, `current_snapshot_backfill`, and `unknown`. Qualification is per field/dependency, not a blanket “PIT clean” label on a mixed record. A dataset assembled from genuine vintages and present-day aggregates must expose both.

An announced future earnings date can legitimately be known before the event. Therefore do not impose a blanket `event_at <= cutoff` condition. The announcement vintage must be available by the cutoff; the future result must not. Conversely, a fiscal period ending in March does not make a filing released in May available in March.

Where a source supplies only a date, retain that precision and use a conservative upper availability bound appropriate to the source and market. Do not synthesize a midnight timestamp and claim intraday availability. Unknown publication time means the affected intraday claim is unqualified.

Corrections append a new vintage with a supersession link. Frozen query receipts and pinned dataset generations remain reproducible. A newly executed publisher-time reconstruction can legitimately differ after an authentic older vintage is discovered and imported today; expose the new reconstruction generation and its current acquisition time, and never relabel it as original replay or historical system observation. Clock skew, delayed publication, out-of-order arrival and late corrections are explicit conditions. User-visible freshness and capture completeness must be measured from receipts, not inferred from a file's current modification time.

## 6. First implementation: Sector Intelligence context and Prophet join

The current fourteen-domain context profile is frozen. Add a successor version through the existing Market Memory owner; retain the old reader and registration identities. The proposed producer payload name below is descriptive until the owner registers it: **`sector_intelligence_context/v1`**. It is not a new authority or a currently deployed API.

The successor context must refer to exact owner-emitted sector evidence, not recompute a second sector engine inside Market Memory.

| Field group | Required retained information |
|---|---|
| Identity | Stable sector/industry identifier, taxonomy/provider and version, region, market calendar, currency and benchmark identity |
| Historical membership | Exact membership generation, effective interval, availability/ingest evidence, additions/removals, weights and weight basis; listing/issuer distinctions |
| Market context | Exact market/beta context reference, risk/regime state as emitted, underlying breadth/participation context and its cutoff |
| Sector state | Owner-emitted leadership/rank, relative-strength horizons, breadth, dispersion, participation, liquidity and flow context; missing fields remain missing |
| Rotation/pivot view | Owner-emitted phase/transition/hazard or pivot output, horizon, uncertainty and qualification state; no conversion of prior/unqualified cells into current model claims |
| Comparability | Raw/adjusted/total-return basis, benchmark generation, FX convention, session boundary and observation window |
| Evidence | Producer/schema version, code/config/model reference, exact output digest, publishing receipt, dependency hashes, source bases and all required clocks |
| Denominator | Sectors/members considered, excluded/unavailable/stale/uninspected members, decision or no-call dispositions, explicit exclusion reasons |
| Joins | Market Memory context identifier, retained sector output reference, Prophet decision reference when issued, and QLedger claim reference when applicable |

The sector owner publishes one immutable qualified snapshot for its normal update. Prophet requests that exact snapshot under its decision cutoff and stores the reference beside the stock/issuer evidence. The join requires compatible identity, membership generation, return basis, currency, clock, horizon and freshness. It does not use an undated `latest` sector file as historical evidence.

If required sector evidence is unavailable, the configured decision path must emit an explicit degraded or abstained disposition. It may continue using an already authorized sector-independent path only if that path is explicitly identified and evaluated separately. Missing context cannot be silently replaced with future data or a current reconstruction.

Reuse the existing Sector Intelligence completion programme and its Macro analytical ownership. Preserve the Shared Shell consumer plan, original B/P/J capability commitments, historical source acceptance and outstanding served/natural-update proof. Existing hazard/lead-lag/scientific restrictions remain binding. This addendum does not revive closed carriers or edit another writer's live source branch.

### 6.1 Compose with the active captured-generation owner

At #10780 head `91add9613ad29dcfb82ff75036dd6519cfc6c06f`, `lib/sector_generation_contract.py` binds the five exact Sector documents through the existing generation publisher; `lib/sector_input_capture.py` supplies captured inputs; the native view uses the verified generation receipt. The learning adapter should reference these retained bytes and receipts after their own release qualification. It must not recompute or copy the whole bundle into another per-stock history.

An examined alternative was to enlarge `sector_central_grader.append_central_log()` with full JSON per row. That legacy writer retains only a score subset, but duplicating every full context there would overlap the active migration, repeat generation bytes and grow a Parquet history that the new auxiliary reader bounds at 64 MiB decoded. No such writer change is made in this source slice.

There is a distinct linkage requirement: a published sector generation is not proof that a particular first daily call was registered. The active composition grades the captured existing call log and explicitly reports `calls_appended=False`. A future learning adapter must consume an explicit decision/call-to-generation reference retained by the actual issuing writer, or report the link as absent. Matching a date, sector name or identical score is not sufficient authentication of that relationship. The generation's publication time, original call observation/registration time and later capture time remain separate.

The first source implementation therefore consists of the versioned Market Memory reference profile plus an exact, producer-owned decision linkage. It should integrate with the existing retained-generation and call/QLedger owners once their affected source and custody are reconciled. The active writer is not displaced, its unmerged modules are not silently treated as main, and its original denied effects are not retried through this branch.

The pending owner's exact read seam is `read_retained_generation(generations_root=..., domain=..., generation_id=..., content_id=..., members=...)` in `scripts/vps_live_orchestrator.py`. It verifies a pinned generation without consulting or changing the current pointer. This API is absent at the main census pin; do not import it from main or copy its implementation. The successor adapter should carry small explicit decision/generation/member references, the original observation/registration clocks and digest, verify the subject and source qualification, and refuse an unrecorded association. Legacy daily rows remain unlinked unless contemporaneous evidence actually establishes the link.

## 7. Capture requirements across predictive engines

Every producer uses the same evidence discipline while retaining domain-specific semantics. The coverage target is the declared predictive inventory, including engines that currently abstain or lack a qualifying source. It is not an unsupported claim to capture every market fact.

| Engine or domain | Retain before the decision | Retain afterward and evaluate |
|---|---|---|
| Market/beta and macro regime | Market/index prices with correct vintages, breadth, cross-asset context, rates/credit, scheduled events, release expectations and published vintages, issued regime probabilities | Market participation and direction/calibration by horizon; release revisions separate; regime definitions fixed before evaluation |
| Sector/industry rotation | Section 6 context, dated membership and weights, relative strength, breadth/dispersion, leadership transitions, flow source vintages | Sector excess return over the declared market, lead time, rotation persistence, false alerts and alternative sectors |
| Prophet/security selection | All eligible candidates, exact market/sector context, feature values/missingness, ranks, probability semantics, original rationale, vetoes/abstentions, code/model/prompt versions | Stock excess over its contemporaneous sector and market, calibrated event probabilities, selection utility, missed opportunities and failed analogues |
| Earnings/fundamentals | Original filing/accession, fiscal period and release/acceptance clocks, consensus vintages available before release, guidance versions, event schedule changes, estimates dispersion, valuation context | Actuals as first released and later restated; surprise against the retained consensus; post-event returns/volatility; transcript fragments only after publication |
| Options/flow/positioning | Contract identity and adjustment terms, quote/trade timestamps, underlying synchronization, bid/ask/spread/liquidity, IV/Greek calculation inputs and model, open-interest publication vintage, classification assumptions | Subsequent underlying/IV/term-structure changes and executable outcomes; inferred aggressor or opening/closing classifications stay labeled inference |
| Technical/intraday | Raw and adjusted price vintages, corporate-action version, closed versus incomplete bars, session/calendar, indicator recipe/warmup, volume/liquidity, detection time | Forward returns, adverse/favorable excursion, confirmed pivots at their confirmation time, spread/slippage and false breakouts |
| News/narrative/sentiment | Original item and revisions, publication/first-seen clocks, source and syndication lineage, entity resolution, extracted claims, model/prompt version, uncertainty | Later corroboration/retraction, novelty and price response; correlation and narrative plausibility do not become causal proof |
| Breadth/factors/credit/rates | Constituent populations, factor recipe and estimation window, release vintages, instrument terms and curve construction, data-quality gaps | Incremental utility beyond market/sector baselines, stability across regimes, exposure attribution and calibration |
| Other existing predictive surfaces | Same contract applied to their actual instruments, issuer identities, calendars, funding/roll and benchmark conventions | Domain-appropriate outcomes; no unqualified transfer of equity/session/transaction-cost assumptions to FX, commodities, crypto or derivatives |
| System health | Collector availability, stale/missing fields, retries/late arrivals, model/feature version, actual served state and coverage denominator | Whether apparent predictability or missed calls came from data outages or version changes; health retained as evidence, not a market explanation by default |

Keep source observation, vendor inference and our inference distinct. A trade print does not by itself disclose the trader's intent. An explanation of an earnings move cannot use a consensus number revised after the release.

## 8. Broad collection and event-focused depth

Collect a minimum comparable baseline across the entire declared eligible universe, not only names that are already moving or selected by the current model. This supplies quiet periods, rejected candidates, eventual losers and missed winners. Record the universe manifest before selection and keep entries for suspended, delisted or unavailable securities.

Use richer event capture around earnings, unusual flow, leadership change, volatility changes and candidate pivots. An event trigger must reference previously retained context; it cannot manufacture pre-trigger data after the move. Event selection itself is versioned and retained, because changing triggers changes the study population.

Cadence follows the producer and information horizon. Retain economic releases and document revisions on arrival; sector and daily strategies at each real decision/update; intraday features at their actual calculation cadence; raw high-frequency feeds only where entitlement, storage and prospective usefulness justify them. “Real time” means a measured source-to-ingest-to-feature-to-serve delay for a declared feed, not a generic millisecond promise.

Operational metrics use existing observability: expected versus captured members, capture delay distributions, missing/stale/revised data, decision coverage, exact-replay success, unresolved outcome rate and cost per qualified unit. Alert through existing owners; do not create another watcher or scheduler.

## 9. Historical reconstruction and backfill

Historical data is valuable immediately, but it has several different uses. Import it with the original source vintage and an honest current ingestion time. Preserve which facts can support a historical availability claim and which support only exploratory reconstruction.

For each source/field, publish a coverage manifest with date range, markets, universe definition, granularity, timestamp precision, vintages retained, revisions, licensing/retention rights, missingness, known survivorship/selection risks, identity/corporate-action coverage and permitted research basis. Reuse existing Data OS dataset registration and Market Memory coverage audits.

Priority order is:

1. Official vintages and original filings/releases with defensible availability evidence; historical price/volume with reproducible corporate-action treatment; historical listings, delistings, membership and benchmarks.
2. Historical earnings calendars, estimates/consensus and guidance where actual vintage archives exist; news/document archives with version/first-publication evidence; option contracts/quotes/OI with correct publication clocks.
3. Recomputed features from qualified historical inputs, explicitly labeled recomputation with the current recipe and code version. They can support controlled strategy research but are not proof that the old production model issued them.
4. Present-day snapshots projected backward, ambiguous release dates and retrospectively curated stories, retained for exploration with their limitations. They cannot silently enter an operational PIT training/evaluation set.

ALFRED's vintage and real-time-period model is a useful source precedent for revisable macro releases. SEC submissions and filings provide source identifiers and publication evidence, while current aggregated facts still require careful vintage handling. These external sources inform adapters; they are not a decision to replace existing data providers or acquire a new commercial feed.

Historical membership must reflect the correct classification available at the cutoff. Avoid rebuilding old sector indices using today's survivors. Corporate actions, symbol changes, mergers, spin-offs, ADR/dual listings and delistings preserve identity lineage rather than becoming new unrelated securities. A delisting return or trading halt is not automatically zero or missing without a disposition.

Apply the same principles to US, Hong Kong, mainland China and Canada where in scope. Their local sessions, holidays, listing identities, currencies, announcement conventions, execution restrictions and benchmark definitions must be explicit. The first operational vertical can be bounded; other markets remain visible as unenrolled or partially qualified until proven.

## 10. Storage and retention design

Use existing Data OS publication/storage ownership. Store immutable source objects once by content identity, retain normalized append-only records or versioned columnar projections as appropriate, and retain exact output/manifests in the established Market Memory path. Some incumbent ledgers currently reside under repository `data/`; preserve their ownership and semantics. Do not expand that pattern into storing every market tick, raw document or growing training table in Git. Any migration follows the existing data/publication owner, including the active always-on migration, rather than a bulk move invented here.

Separate high-volume raw retention, normalized research data, frozen experiment manifests and exact decision evidence. Derived indices and caches are rebuildable; original observations and emitted decisions often are not. Deduplicate by source content and revisions while preserving distinct observation/serve receipts. Compaction must preserve semantics, superseded generations and any dataset pinned by an experiment or replay.

Set source-specific retention periods after measuring bytes, replay/research needs and source rights. Do not apply a rolling deletion policy to the only copy of pre-pivot evidence or to a frozen experiment's dependencies. An explicit permitted expiry must leave a truthful unavailable/tombstone disposition; it must not claim exact replay remains possible. Retain material corrections and provenance for as long as dependent scientific claims are retained, within applicable rights.

Capacity planning precedes broad high-frequency enrollment. As an illustrative lower bound, 10,000 securities × 390 minute slots × 100 numeric fields × 8 bytes is 3.12 GB per session before identifiers, quotes, documents, revisions, metadata, replication and indices. This is arithmetic, not measured throughput or a purchase estimate. Actual storage and egress must come from a bounded representative capture and existing budget authority.

Avoid a new data warehouse or streaming service unless a measured incumbent limitation establishes the need and its owner admits the change. This programme starts by qualifying existing publication, retention and replay paths.

## 11. Pivot and outcome definitions

Define a family of falsifiable targets before comparing models: market drawdown/recovery, sector leadership transition, breakout/reversal, earnings-driven repricing or another economically specified event. A visually attractive chart inflection chosen after seeing the full path is not a live detection rule.

For each target, distinguish:

- **Occurrence time:** the retrospectively identified economic turning point, if the target uses one.
- **Confirmation time:** when the definition becomes decidable using permitted subsequent observations.
- **Forecast issue time:** when the system actually anticipated the event.
- **Feasible action time:** the earliest execution/response time under the strategy's latency, market and liquidity constraints.
- **Outcome maturity:** when the declared evaluation horizon and necessary source data are complete.

An event confirmed several days after the trough cannot be credited as a trough-time forecast. A scheduled earnings date known in advance is not evidence of knowing the surprise. Track lead time to confirmation and to the economically meaningful move separately.

Outcome records include target/label version, horizon, benchmark, return basis, MFE/MAE where appropriate, volatility/liquidity, costs, censoring and data-quality status. Keep overlapping outcomes connected by episode/date/issuer so they are not counted as thousands of independent successes. Distinguish temporarily immature outcomes, right- or interval-censored outcomes, permanently unobservable outcomes and economically terminal events. Preserve all in the registered denominator with explicit reasons; none automatically means “no pivot.” Completed-label metrics disclose their evaluated population and missingness. Where missing outcomes may be informative, use appropriate censoring methods, sensitivity bounds or an explicitly limited claim. Delisting, suspension or a missing terminal return cannot improve apparent performance by disappearing.

Label revisions append a new outcome version. A training job at cutoff T can use only labels available and mature by T, even if the underlying prediction occurred much earlier.

## 12. Explanations and causal evidence

“Why did it move?” is an investigation, often with incomplete evidence. Retain multiple candidate explanations with supporting/refuting references, when the explanation was formed, the analyst/model version and what would falsify it.

Keep these meanings separate in existing evidence metadata:

| Explanation class | Permitted conclusion |
|---|---|
| Documented catalyst | A release, filing or observable event happened; its timing and contents are sourced. |
| Statistical association | A feature or event covaried with an outcome under a stated sample/model. |
| Mechanism hypothesis | A plausible transmission path is proposed with alternatives and uncertainty. |
| Causal study | A specified identification strategy supports a bounded causal claim, with assumptions and limitations. |
| Unresolved | Available evidence does not support a reliable explanation. |

Feature importance, an LLM narrative and an event occurring near a price move do not establish cause. Preserve contradictory cases: the same catalyst without a move, a similar move without that catalyst, competing events, changed regime and different liquidity. This comparison is how the system can learn when an apparent signal matters and when it does not.

When later-discovered explanations become candidate features, timestamp that knowledge and test their prospective use. Do not retrofit a story into the old production reasoning. Preserve “unknown” rather than rewarding explanatory confidence.

## 13. Learning and evaluation path

Use the existing Research Factory and evaluation owners for this sequence:

Designate evaluation periods or cohorts before exploration and record prior inspection. Feature discovery, hypothesis selection, hyperparameter tuning, calibration and stopping decisions belong within training/validation. A repeatedly inspected evaluation set becomes development data; later claims require a fresh reserved set or prospective records. Chronological splitting alone does not remove researcher or model exposure to evaluation outcomes.

1. **Explore:** search qualified historical episodes and matched controls; formulate candidate mechanisms/features. Exploration is not a performance claim.
2. **Register:** freeze population, features, cutoff rules, targets, horizons, preprocessing, baselines, metrics, cost assumptions, search budget and decision rule before evaluation.
3. **Evaluate chronologically:** train only on information and matured labels available at each training cutoff. Fit normalization, missing-value handling and feature selection on training data only. Purge overlapping outcome windows across splits and apply an embargo/dependence policy appropriate to the target. Group related issuer/date/sector episodes where needed.
4. **Replicate and stress:** assess distinct periods, regimes and eligible populations, alternative source coverage and plausible costs. Record every tried model/feature configuration and failed result, not only the best backtest.
5. **Shadow prospectively:** emit and retain forecasts before outcomes without granting new trading authority. Compare with the incumbent on the same population, data and clocks.
6. **Promote only through existing governance:** demonstrated incremental utility, stable data health, current model/source qualification, actual required controls and rollback evidence. No automatic model replacement because a retrospective metric increased.

Start with interpretable baselines and small feature sets. Historical nearest-episode retrieval can be useful before complex training if its controls, distances, temporal admissibility and uncertainty are clear. A larger model is justified by incremental out-of-sample evidence, not by the size of the archive.

For each historical retrieval query, restrict the analogue library to evidence available by that query cutoff. An episode may supply its outcome, success/failure class or later explanation only after that item's own availability time. Qualify similarity features and retrieval weights at the applicable cutoff too. Appending a later outcome or explanation must not change an earlier frozen retrieval result; an unresolved episode cannot appear as a known successful precedent.

Current foundation-model weights may already encode later events or outcomes. PIT-clean retrieved inputs alone cannot prove that a present-day LLM is ignorant of historical outcomes. Tag historical LLM experiments for this contamination risk, use suitable controlled comparisons and rely on actual prospective shadow results for live predictive claims. This is a methodological constraint, not a claim that any particular model did memorize an event.

Backtest selection over many variants creates overfitting risk. Keep the experiment/search history, confidence intervals and dependence-aware uncertainty. A fixed number of days or trades is not a universal adequacy threshold; predeclare required independent episodes and regime coverage for the specific claim.

## 14. Market, sector and stock evaluation

Report the hierarchy explicitly. For the same interval, currency and arithmetic return convention, the descriptive identity is:

`stock return = market return + (sector return - market return) + (stock return - sector return)`.

This accounting identity is useful explanation, not proof of factor-neutral alpha. For model attribution, estimate exposures only from pre-decision data and use a properly specified joint or orthogonalized factor model; avoid double-counting correlated market and sector exposures. Freeze benchmark identity, methodology and decision-time membership context. State whether the outcome benchmark is a frozen constituent basket or a rule-governed index that can rebalance. Retain relevant membership/weight generations and subsequent rule-governed changes; do not silently substitute one return series for the other.

| Layer | Main question | Essential comparisons |
|---|---|---|
| Market | Did the system correctly anticipate when market exposure was favorable/unfavorable? | Declared passive/constant exposure, simple regime baselines, same availability/cost assumptions |
| Sector | Did it anticipate leadership changes and choose better sectors than the market or incumbent? | Market, eligible sector population, current-leader/momentum baseline, stable sector weights |
| Security | Did it select stocks that added value within the selected sector and beyond known risk exposures? | Contemporaneous sector, eligible peer universe, simple selection baseline and incumbent Prophet |
| Timing and execution | Was the warning early enough to act on realistic terms? | First feasible price, spread/slippage/fees, latency, turnover and applicable borrowing/funding constraints |

For event forecasts, report precision/recall, missed events, false-alert rate, lead-time distribution, probability calibration and proper scoring rules. For selection/return forecasts, report incremental performance, uncertainty, drawdown, turnover and exposure. For retrieval, report whether analogues improve a predeclared downstream decision compared with controls. Useful intelligence and profitable execution are separate claims.

Keep results by cohort, source coverage and model vintage. Show performance deterioration, data gaps and rejected hypotheses. Do not pool unrelated horizons, markets or correlated observations into an impressive but uninterpretable average.

## 15. Product experience

Extend existing Prophet, Sector Intelligence and investigation surfaces. A user should be able to open a security or sector at a past date and see:

1. What information was available under the stated historical basis.
2. What the system actually said or declined to say, with its original confidence and context.
3. What subsequently happened and when that outcome became evaluable.
4. What explanations were formed later, with evidence and uncertainty.
5. Similar previous episodes, including failures and relevant controls, and the limits of their relevance now.

The product should clearly distinguish an actual retained output from a reconstructed historical view. Missing evidence is visible. Keep internal implementation details in evidence/debug surfaces unless they change the user's interpretation. Preserve Sector Intelligence → stock/Prophet → research navigation and exact return to the original investigation, following the current Shared Shell programme.

The system can suggest a research hypothesis or an uncertainty-qualified analogue. It cannot turn a persuasive narrative into a trade recommendation, position size or promotion authority without the existing independent validation and execution controls.

## 16. Implementation sequence in the existing programme

These are acceptance slices within existing tasks, not a new scheduler or independent wave state machine.

| Existing task anchors | Concrete work | Exit evidence |
|---|---|---|
| C0/P8.T1; G0/P8.T2 | Inventory predictive producers/fields, existing sources, clocks and coverage; specify the versioned sector profile and source basis | Owner-approved schema/contract through ordinary source workflow, unchanged v1 registrations, explicit gaps and exact source refs |
| C1/P9.T1; P0/P9.T2; G1/P8.T3 | Enroll exact sector and Prophet output adapters; qualify publication/capture; register successor population and identities | Authentic before-outcome captures, full dispositions, revision/late-arrival proof, no duplicate writer or changed old pilot |
| P1/P10.T1; R2/P10.T3 | Join label-free market → sector → stock contexts; expose exact replay and qualified historical/control retrieval | Actual Prophet consumer references exact sector context; replay/miss/corruption/degraded paths behave as specified |
| L0/P10.T4; P2/P10.T2; E0/P14.T1 | Attach matured outcomes; reconstruct qualified historical cohorts; preregister chronology and train-only transformations | Future-label contamination refused; fixed universe with delistings/no-calls; reproducible manifests and proper split evidence |
| N2/P12.T1; E1/P14.T3; E2/P14.T4 | Extend existing Factory joins; run controlled historical and prospective comparisons | Baseline-relative utility, negative results, calibration/cost/coverage evidence; existing admission and promotion decisions |
| U2/P15.T3; A1/P16.T1 | Deliver product investigation and repeat enrollment for remaining engines/markets | Real served workflow, exact historical interpretation, natural-update proof where owed and whole-programme acceptance |

The first operational slice is a bounded market-sector-stock chain with a declared US universe and horizons selected by the existing owners. This adds a successor cohort; it does not repurpose the SPY pilot or change its original registered sample. Subsequent enrollment covers earnings, options, technicals and the remaining predictive inventory using the same contracts, with market-specific qualification rather than assumed parity.

Neither this document nor a merged PR changes existing E0 captures, the original 109-capture membership/protocol, source refusals, private-research restrictions, promotion holds or false fit/training eligibility. Those original effects and governing dispositions remain attached to their original carriers.

## 17. First implementation brief and acceptance cases

**Inputs:** this addendum; exact current Market Memory/Data OS contracts; current Sector and Prophet producer schemas and output receipts; original programme continuity; current writer/custody and release state. Refresh affected source facts before editing live producer paths.

**Owned changes:** a versioned successor Market Memory context registration; typed adapters for exact sector and Prophet output schemas; joins to existing immutable output/context references; successor population registration; focused integration tests; existing surface consumer hooks. Exact paths follow current owners. Do not turn `options.signal_episode/v1` admission into a generic arbitrary-JSON writer.

**Excluded side effects:** no automatic dataset purchase, broad raw-feed backfill, schedule dispatch, source-runtime activation or training/promotion-bit change merely from schema merge. Actual rollout uses existing admission, rights, budget and release authority. This is a boundary on effects, not a new human approval ceremony.

| Case | Required behavior | Current evidence |
|---|---|---|
| Late arrival | Public reconstruction can differ from system-observed reconstruction; both are labeled reconstruction | Synthetic Data OS witness passed |
| Later correction | Adding a future revision does not change earlier selected inputs or their digest | Synthetic witness passed |
| Revision activation | Correction becomes available only at its own permitted cutoff | Synthetic witness passed |
| Scheduled event | Known future schedule is allowed; future result remains excluded | Schedule mechanic passed; real producer integration outstanding |
| Clock precision | Explicit requested clock never falls back; naive timestamps refuse; ambiguous dates conservatively qualified | Missing-clock/naive-time mechanics passed; source precision enrollment outstanding |
| Identity/membership | Later identity generation cannot substitute for an earlier one; sector membership follows exact dated generation | Identity mechanic passed; actual sector generation integration outstanding |
| Missing dependency | Required context refuses/degrades explicitly; no latest-data substitution | Missing dependency refusal passed; engine behavior outstanding |
| Actual replay | Exact retained bytes and digest preserved; no output refuses; tampering refuses | Synthetic mechanics passed; authentic producer receipts outstanding |
| Population | Uninspected, unavailable, abstained, rejected and delisted members remain accounted for | Data-coverage mechanic passed; forecast population integration outstanding |
| Input integrity | Reader does not mutate input or expose mutable returned evidence | Synthetic witness passed |
| Label maturity | Future/immature labels excluded from historical training; censored is not negative | Required future integration proof |
| Censoring | Unobservable/delisted outcomes stay visible; evaluated and registered denominators plus sensitivity are disclosed | Required experiment proof |
| Evaluation isolation | Reserved evaluation data and prior inspection recorded; configuration selection stays within training/validation | Required experiment proof |
| Analogue timing | Later-known outcomes/explanations cannot alter earlier frozen retrieval or create a known-success precedent | Required retrieval integration proof |
| Engine provenance | Actual emitted Prophet/sector output distinguished from recomputation or later narrative | Required future integration proof |
| Decision-generation link | Producer-recorded association required; same-date/score matching and latest fallback refused | Required integration with the existing Sector owner |
| Historical LLM risk | Historical results disclose model-knowledge contamination limits; prospective claims use forward records | Required experiment protocol and prospective proof |
| Baseline hierarchy | Market, sector and security contribution separately evaluated with pre-cutoff exposures | Required experiment proof |
| Consumer usefulness | User can inspect known-then/output-then/outcome/later-explanation without mixing them | Required served product proof |

Successful source validation does not convert the outstanding rows into passes. The next source implementation should begin with the versioned sector output reference and exact Prophet join, because those are the missing consumer links with the highest cross-engine reuse.

## 18. Executed witness and its limits

Artifacts in `research/market_memory/predictive_learning_20261109/`:

- `verify_incumbent_contracts.py`: standard-library executable integration witness importing the real Data OS reader.
- `incumbent_contract_proof.json`: actual 13-case result and SHA-256 digests of tested owner modules.
- `owner_test_proof.json`: actual result of the 175 existing temporal/read-contract tests and the tested source hashes.
- `README.md`: reproduction instructions and scope.

Executed from the repository-shaped source snapshot with `PYTHONPATH=.` using exact Git-blob-verified source at the census pin. Result: **13 tests, 13 passed, exit 0**. No Data OS runtime module was modified. Fixture publishing-receipt hashes are synthetic and do not authenticate a real producer or prove collector coverage.

The environment initially lacked `pytest`. This was repaired by installing test dependencies into a task-local scratch directory, without changing repository dependency files. The first owner-suite run then exposed two omitted modules in the selected source snapshot (172 passes and three import failures); fetching the exact pinned modules resolved that environment incompleteness. The final run of `tests/test_dataos_temporal.py` and `tests/test_dataos_read_contract.py` passed **175 tests, zero failures/errors/skips**. This is the two named suites, not the full repository test suite. Hosted repository checks remain separate release evidence. Earlier attempts are retained as validation history, not added to the passing count.

The result explicitly keeps `production_capture_proven`, `sector_producer_enrolled`, `historical_coverage_proven`, `training_or_promotion_authorized`, and `predictive_skill_measured` false. This protects the distinction between contract mechanics and operational/scientific acceptance.

## 19. Continuity, ownership and routing

The recovery anchor remains [FULL_PROGRAMME_CONTINUITY_2026-11-03.md](FULL_PROGRAMME_CONTINUITY_2026-11-03.md) and `agentos/workstreams/WS-MARKET-MEMORY-W2C.md`. Prophet and Sector Intelligence keep their existing source/product owners and current workstreams. This assignment adds a shared contract; it does not evict live writers or reopen original refused or uncertain operations.

The assigned principal retained this source design and synthetic proof for `PRINCIPAL_JUDGMENT` and `LOWER_TOTAL_OVERHEAD`. Two native reasoning advisers reviewed temporal methodology and incumbent ownership; neither authored runtime changes, owned production effects or supplied a GitHub approval. WHY NOT FABLE: this bounded cross-system source synthesis and direct witness were cheaper than a new labor handoff and did not require displacing an active principal. No Fabric dispatch, external message, background runner or runtime lifecycle transition is claimed.

Publication uses one operation branch and expected-head updates. One source PR carries the complete contract and proof. Actual repository checks and release controls govern it. The Macro `merge-on-green` controller is the ordinary opt-in release route after qualifying checks; native GitHub auto-merge is not a substitute. Source release remains distinct from runtime collection and programme acceptance.

**Next operational action:** reconcile current sector/Prophet producer schemas and active source custody; implement the versioned sector context and exact retained-output join through incumbent owners; then prove one real before-outcome capture and replay before broader enrollment. Preserve all accepted work and original holds. A pending source release or unrelated blocked lane does not authorize stopping other safe work or replaying refused effects.

## 20. Evidence and references

### Pinned project sources

All Macro source links below use census commit `f3a547cc09872d9aaa719759a6a2daa2832edad5`; refresh only affected facts when implementing.

- [Data OS read contract](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/lib/dataos/read_contract.py), [temporal vocabulary](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/lib/dataos/temporal.py), [dataset registry](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/lib/dataos/registry.py).
- [Market Memory context](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory.py), [retained generations](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_pit.py), [forward objects](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_forward.py).
- [Prospective experience](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_experience_accrual.py), [population](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_population.py), [typed production records](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_production_records.py).
- [History dossiers](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_history_dossier.py), [scoring scope](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_scoring.py), [promotion audit](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/neuralweb/market_memory_promotion_audit.py).
- [Prophet earnings evidence](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/prophet_lab/intelligence_vector.py), [QLedger](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/qledger.py).
- [Factory Market Memory adapter](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/research_factory/adapter_market_memory.py), [Factory evidence adapter](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/research_factory/adapter_market_memory_evidence.py), [E0 domain checks](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/engine/research_factory/market_memory_e0_domains.py).
- [Original Market Memory workstream](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/agentos/workstreams/WS-MARKET-MEMORY-W2C.md), [full programme continuity](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/research/market_memory/FULL_PROGRAMME_CONTINUITY_2026-11-03.md), [Sector Intelligence completion](https://github.com/mastermindx-market-intelligence/macro/blob/f3a547cc09872d9aaa719759a6a2daa2832edad5/agentos/workstreams/WS-SECTOR-INTELLIGENCE-COMPLETION.md).
- Active unmerged dependency at its own exact head: [#10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780), [Sector generation contract](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/lib/sector_generation_contract.py), [input capture](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/lib/sector_input_capture.py), [bounded auxiliary reader](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/lib/sector_auxiliary_capture.py). This head is evidence of proposed source, not accepted runtime deployment.
- [Pending Sector document composition](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/engine/sector_basket_documents.py) distinguishes captured pre-append grading from actual call registration; [pending retained-generation reader](https://github.com/mastermindx-market-intelligence/macro/blob/91add9613ad29dcfb82ff75036dd6519cfc6c06f/scripts/vps_live_orchestrator.py) owns exact generation verification.
- [Protected Mastermind delivery law](https://github.com/mastermindx-market-intelligence/Mastermind/blob/b975605771ab8d09994087babad0e9b9cf771288/docs/DELIVERY_WORKFLOW.md), [reuse-first law](https://github.com/mastermindx-market-intelligence/Mastermind/blob/b975605771ab8d09994087babad0e9b9cf771288/docs/REUSE_FIRST_ENGINEERING.md).

### Primary methodological sources

- [ALFRED download and vintage documentation](https://alfred.stlouisfed.org/help/downloaddata) and [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html): vintage-aware reconstruction of revisable economic information.
- [SEC EDGAR application programming interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): submissions and XBRL access; preserve original filing availability separately from reporting period and present aggregated facts.
- [Feast point-in-time join documentation](https://github.com/feast-dev/feast/blob/master/docs/getting-started/concepts/point-in-time-joins.md): event time alone can admit later-created/backfilled values; availability-aware cutoffs matter. This is a methodological comparison, not a proposal to install Feast.
- [Bailey et al., The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253): multiple strategy trials and selection can produce misleading backtest success.
- [Janzing, Minorics and Blöbaum, Feature relevance quantification in explainable AI: A causal problem](https://proceedings.mlr.press/v108/janzing20a.html): predictive feature relevance and causal interpretation require care.

The design choices and acceptance criteria above are project-specific synthesis. External references support methodology; they grant no source rights, budget, deployment or trading authority.
