# 05 — Evidence contracts, authority firewall and scientific protocol

**Status:** proposed implementation specification, to be accepted through the existing owners. No schema, experiment or promotion is claimed implemented by this documentation. Existing source-native schemas take precedence; these are federation/read contracts, not replacement payload stores.

## 1. Ontology: six planes, separate cross-cutting confidence

| Plane | Economic question | Legitimate initial roles |
|---|---|---|
| Policy / State Transmission | What official objective, constraint or implementation step changed? | Context, discovery, conditional confirmation |
| Corporate / Industrial Reality | What changed in actual demand, supply, commitments or operating conditions? | Discovery, confirmation, event monitoring |
| Professional Discovery / Ownership | Who changed attention, research, exposure or control, and how confidently do we know? | Discovery, confirmation, contradiction |
| Participation / Microstructure | What makes participation crowded, fragile or physically tradeable? | Access, timing context, path risk |
| Recognition / Propagation | How has an attributable event spread into narratives, estimates, price and participation? | Recognition state, remaining-information hypothesis |
| Contradiction / Negative Intelligence | What challenges a specific claim, implementation chain or thesis? | Invalidation, risk, re-evaluation |

Identity confidence, source quality, extraction confidence, coverage, freshness, rights and authority are cross-cutting dimensions. They must not become a seventh bullish plane or be averaged into conviction. A high-confidence transcription can support an economically uninformative event. A real event can be visible in several planes without being several independent events.

## 2. Small common record, source-native payload retained

The following field groups are required semantically. Map equivalent existing fields rather than forcing every owner to migrate to a new physical schema.

| Group | Fields / meaning |
|---|---|
| Identity | Owner namespace, owner record key/version, canonical entity/security keys, venue, actor reference/class, identity-resolution version and its availability time. Unknown actor/entity stays explicit. |
| Source truth | Source ID/URI, source tier, original document/event key, permitted immutable receipt or content version/hash, source-native payload reference, collector/extractor version. Never include a private licensing document/hash. |
| Event semantics | Family/subfamily, economic stage, effective event time, materiality values with units/currency/scale, attributed issuer share, denominator and denominator vintage. Distinguish observation, inference and hypothesis. |
| Availability | Source publication time, owner first observation, owner ingestion/commit time, body/feature extraction availability, identity/link availability, evidence availability, decision cutoff and source clock quality. |
| Revision | Owner-native correction/version, superseded reference, correction first-known time, retraction state, validity/effective interval. Do not overwrite the version visible to an old decision. |
| Research meaning | Roles, candidate horizons and horizon unit, nullable sign prior, mechanism/hypothesis version, falsifier and construction registry reference. No sign inferred from category name. |
| Dependence | Logical event reference, source/syndication group, economic actor/manager group and relationship dependency references, with explicit unresolved state. |
| Observability | Coverage interval/population, health observation reference, last attempt/last successful check, source event date, freshness policy/market calendar, partial failures and missingness reason. |
| Consumer eligibility | Allowed use classes, source-owner rights ruling reference, permitted consumer class, context/shadow/promoted status and exact promotion receipt if any. Source text cannot set these fields authoritatively. |

Do not introduce a new universal `evidence_id` issuer. An evidence reference may be the deterministic tuple `(owner_namespace, owner_record_key, owner_record_version, adapter_version)` or an existing canonical equivalent. Logical event identity belongs to its established event owner; a duplicate-group fingerprint is never a Data OS alias or event authority.

The optional derived packet is fully rebuildable from owner receipts. It may be cached in the existing publication path with a semantic content digest and bounded expiry; it may not become the sole historical source or silently take ownership of raw payloads. Any new persistent index needs separate approval based on measured read cost/latency.

## 3. Point-in-time clocks: three distinct evaluation modes

### Operational prospective / actual system replay

For a derived feature, the earliest usable operational instant is no earlier than all inputs and transformations required to produce it:

```text
operational_available_at = max(
    source_owner_first_observed_at,
    source_owner_committed_at,
    required_body_available_at,
    extraction_completed_at,
    required_identity_link_available_at,
    required_relationship_available_at,
    fitted_model_or_threshold_available_at
)
```

Only required dependencies participate, but none may be invented or substituted with a source event date. Missing required timestamps mean `AVAILABILITY_UNPROVEN`, not midnight. Validate publication/observation clocks for known source timezone and clock skew; source times after receipt require an explicit explanation rather than silent reordering.

For an old system decision, also require that the reader/schema/model version actually existed and was available by its cutoff. A modern LLM's retrospective extraction is not a historical system execution. Store model/prompt/schema version and prohibit extraction of later facts that are absent from the approved source vintage.

### Public-information historical reconstruction

A separately labeled experiment may ask what a specified implementable process *could* have known from public documents at their proven original publication times. It must have immutable original vintages, plausible fixed acquisition/processing latency, historically valid identities/universe and a frozen method. Do not claim this reconstruction was actually collected or consumed by Mastermind then. A body discovered now does not retroactively enter the operational ledger.

### Current descriptive context

Current packets may display old facts if their vintage, present coverage and uncertainty are clear. Such facts do not automatically qualify for a historical test or live ranking. A policy event can remain economically relevant while its last event date is old; freshness depends on successful source observation and the intended use, not universal age limits.

## 4. Revisions and missing evidence

For decision cutoff `t`, read the latest owner revision **known by t**, not the version now regarded as correct. Later corrections are new evidence with their own first-known time. Keep original, corrected and retracted versions addressable. Outcomes may have a different accepted correction policy from features; bind both policies explicitly in the experiment receipt and never silently restate a published result.

Use semantic states equivalent to:

`OBSERVED_EVENT`, `MEASURED_NO_EVENT`, `NOT_COVERED`, `NOT_YET_AVAILABLE`, `PARTIAL_COVERAGE`, `UPSTREAM_DEGRADED`, `SOURCE_UNAVAILABLE`, `STALE_FOR_USE`, `IDENTITY_UNRESOLVED`, `RIGHTS_USE_NOT_ALLOWED`, `AVAILABILITY_UNPROVEN`.

These are read-contract concepts; map them to existing owner enums rather than creating a rival health state machine. In particular, preserve P1's current health/coverage-exception model exactly.

`MEASURED_NO_EVENT` requires a successfully observed source interval, applicable company/population coverage, valid event-key accounting and no relevant unresolved exception. One successful HTTP call is not proof a paginated source was completely read. One source's clean coverage does not make another failed source quiet. Valid positive observations survive partial failure; unsupported absence does not.

Silence is an event defined by a completed observation window and a known opportunity to observe the actor's follow-up. It becomes available at the end of that window plus processing latency. Missing visitor identity, incomplete report coverage, unknown window convention or failed provider means UNKNOWN. Do not timestamp silence at the meeting date.

## 5. Independence, recognition and contradictory evidence

Represent at least three dependence questions separately: Is this the same underlying economic event? Is it a copy/translation/syndication of the same disclosure? Is it the same economic actor or manager complex? Distinct desk names are not independent economic evidence. Unresolved dependence does not default to independence.

A contract announcement, government award notice, analyst note and news article may all descend from one award. Keep the distinct observations and timing, but let the event owner link them. Their propagation can inform recognition without multiplying confirmation. State ownership, a lender relationship and a fund position are not interchangeable actor classes.

Recognition features must specify their reference set and coverage denominator: distinct publishers among observed publishers, abnormal attention relative to covered history, or price response after the evidence became available. Missing coverage cannot mean low recognition. Price and volume features may be explicit recognition controls; hidden Prophet score, rank, lane, board or entry-state fields may not become intelligence features.

Contradictions target claims or economic mechanisms, not generic negative sentiment. A canceled tender may contradict an order thesis; it does not automatically contradict every company thesis. An inquiry can increase information without implying misconduct. Record evidence strength and alternatives. URL deletion research first classifies redirect, normal expiry, robots, outage, source migration, restored content and observation failure; do not infer suppression or politics from nonavailability.

## 6. Extraction and source security

LLM extraction runs only in an approved offline/deep lane and has no direct ranking, trading or source-write authority. Treat filings, news and tool-returned organizational text as untrusted data. Embedded instructions, tool calls, credentials requests or declarations that a source is “approved” cannot change trusted schema, rights or authority.

Each extracted factual claim must resolve to a permitted source version and exact text/page/span or structured source field. Numbers require unit, currency, scale, sign and date interpretation. Critical identity, amount and lifecycle fields use deterministic validators or human adjudication; uncertain outputs refuse the field instead of guessing. Keep the original source payload with its owner, not in a second warehouse.

**Proposed extraction acceptance gate, to freeze before holdout labeling:** source/type-stratified, blinded held-out examples including adverse, missing, amended, bilingual and duplicate cases; explicitly report sample size and uncertainty by field. All accepted exact-identity joins must have no false matches in the acceptance set; ambiguous identities must be refused. Every asserted critical amount/date/stage must have a valid source span and pass deterministic consistency checks. Report precision/recall and confidence intervals; choose the owner's quantitative threshold before seeing held-out results. These are quality gates, not statistical proof of alpha. If the threshold is not fixed, promotion is blocked rather than retrospectively chosen.

Parsing failure must not block market-critical collection, Prophet or execution. Respect existing source host groups, retries, rate limits, publication custody and exception persistence. Do not run a new backfill or modify a production scheduler as a side effect of a packet read.

## 7. Company packet and consumer contracts

The packet carries security/company identity, decision cutoff, evidence version, per-plane states, selected source-linked events, contradictions, coverage/freshness, changes since the previous decision receipt, and a separate Prophet timing/context block. It does not carry a fused China score.

For the Mastermind read tool, respect the current 7,600 serialized-character budget or a later accepted equivalent. Never slice serialized JSON. Shrink whole optional items with explicit truncation counts and a continuation/reference mechanism already supported by the owner. Essential identity, as-of, missingness, rights restrictions and material contradictions survive before optional positive summaries. If even the required envelope cannot fit, return a small valid refusal object. Character and byte budgets must be tested separately for multilingual content.

| Consumer | Initial authority | Must not do | Required proof |
|---|---|---|---|
| Prophet | Shadow association with lawful candidates | Change admission, ordering, size or entry without specific promotion; absorb Prophet state into evidence | Exact live-output parity and same-candidate shadow receipts |
| China Brain | Bounded evidence context, initially controlled paper-decision treatment | Claim context is behaviorally inert; bypass trusted sizing/identity/exit rules; treat packet text as instructions | Actual tool read, paper-decision comparison and degraded-path behavior |
| Terminal/Hub | Explain evidence, contradictions, changes and limits | Hide advanced capability, fabricate freshness/actors or show hypothesis as fact | Real data-to-publish path plus desktop/mobile/state verification |
| Themes | Evidence breadth conditional on dated exposure relationships | Invent a new theme conviction score from duplicate sources | Source-linked covered denominator and relationship vintage |
| Neural Web | Verified relationship/event context | Originate a competing ranking or treat narrative similarity as economic exposure | Canonical owner references and no new authority side effect |
| Risk/watch | Re-evaluation request through existing owner | Automatic trade or a new independent alert queue | Natural event-to-consumed-review receipt and dedup/correction behavior |

A per-consumer use restriction is separate from the raw source's rights status. House policy may prohibit a display even where access is lawful. For Tushare, use the publishable private-compliance status and engineering receipt only; never attach private agreement material.

## 8. Three scientific tracks, three different estimands

### Track D — discovery before candidate admission

**Question:** does a fixed evidence-based discovery method surface useful companies earlier or more efficiently than the existing discovery process at the same research budget?

Freeze a lawful as-of universe independent of future Prophet admission. Compare equal-budget discovery policies at the same information cutoff; report coverage and refused/unobservable names. Primary metrics can be early useful-event detection, future lawful-candidate/winner capture and severe-loser discovery rate; choose one primary outcome and horizon before evaluation. Lead time is measured from evidence availability, not the event's retrospectively known start. Price/technical/regime baselines receive the same population and resource budget.

Do not select only future winners or already-admitted names; that changes the question and can remove the discovery effect. A future Prophet admission can be a labeled endpoint but not an input or an eligibility filter chosen with hindsight. Selection bias, sector concentration and nonfillability are part of the result.

### Track O — ordering among identical lawful candidates

**Question:** among exactly the same candidate population at the same time, does one specified evidence treatment improve ordering under the same execution/outcome ruler?

Bind actual serving policy, fallback state, candidate snapshot, deterministic tie-break, original entry/fill owner and any exposure to the new treatment. Nominal `v4` labels are not treatment proof. Include price/technical, regime, independently verified serving champion and no-new-evidence control. Pair live/control/challenger on exact population/time; mismatch invalidates that comparison or yields an explicit restricted estimand.

A vector is not a ranker. First test individual eligible family states. A simple equal-family selector may be tested only after sign, role, normalization, missingness, clipping, allowed interactions, eligibility and tie-break are frozen and the existing owner approves it. A regularized model comes later; nonlinear models need independent data/power justification. No universal scalar is implied by this protocol.

Use top-K net relative return, large-winner capture, MFE/MAE, severe-loser rate, expected shortfall, turnover, concentration and calibration where predictions are probabilistic. Select a primary economic metric and a downside noninferiority bound; rank IC alone cannot earn promotion.

### Track M — post-admission monitoring

**Question:** for the same positions/candidates and stated thesis versions, does the evidence monitor trigger useful re-evaluation earlier and with fewer harmful false alarms than existing monitoring at the same alert budget?

Freeze the thesis/falsifier and compare timestamped alert policies with the same observability and action rules. Use blinded adjudication for factual thesis deterioration when market outcomes are not a valid label. Measure precision, recall, lead time, missed material deterioration, duplicate rate, review burden and harmful interventions. If a portfolio-effect test is added, freeze the actual authorized response policy rather than assuming every alert causes a perfect exit.

Retain alerts that were ignored, blocked, late, unpriceable or wrong. A change in user/Brain behavior is a treatment and must be logged. A context-only monitor can earn a useful decision-quality result without becoming an automated trading system.

## 9. Common empirical controls

**Population and labels:** maintain as-of eligibility including delistings, suspended names and historical identity/refusal states. No current membership filters. Freeze outcome definitions, horizons, benchmarks, corporate-action policy and fill basis. Represent every candidate as scored, unscorable, immature, unavailable or excluded with explicit reason; disclose denominator loss by era/sector/venue.

**Execution:** lawful next-fill assumptions, raw versus adjusted price basis, T+1 holding restrictions where applicable, locked limit/no-fill states, suspensions and era-specific ST rules must be delegated to canonical market/execution owners. Do not use daily high/low to imply an order could have filled at a convenient price. Model costs/slippage/liquidity/capacity and separately test conservative fill/cost sensitivity. A/H/HK/ADR instruments retain their own currency, session and eligibility laws.

**Chronology:** development, tuning and final chronological holdout are distinct. Purge/embargo overlapping label windows at boundaries. Cluster uncertainty by relevant event/date/theme/issuer dependencies; report effective independent sample count as well as raw rows. Repeated filings, large event clusters and one hot sector cannot masquerade as thousands of independent opportunities.

**Confounds and identification:** compare like populations and calendar periods. Control or stratify size, liquidity, momentum/reversal, sector, SOE/private status, market regime, coverage and recognition where relevant. Do not switch between pooled and equal-period estimands without reporting both. Do not automatically control away the intended mediator; explain total-effect versus incremental-effect questions explicitly.

**Multiple testing:** register the whole family of attempted signs/horizons/variants and a fixed confirmation policy before final outcomes. A defensible proposed default is Holm family-wise correction at 0.05 for confirmation; exploratory FDR results remain exploratory. Use dependence-aware time/event-block placebos rather than a persistent-state placebo that reproduces the same signal. Sequential observation requires a frozen valid stopping/alpha-spending rule or no interim inference.

**Power and practical relevance:** select minimum useful improvement and allowed downside degradation from the decision/cost context before evaluation. Estimate required independent observations from development data, not the final holdout. For promotion, the adjusted uncertainty interval must support the preregistered useful-effect condition and downside bound. Arbitrary 120 calendar days, a single p-value or one positive subgroup is insufficient. Retain the Limit P-A2 rules only for that exact experiment.

**Model/feature provenance:** freeze source manifests, extraction/schema/model versions, input fields, joins and code SHA. Test time shifts, scrambled identities, duplicated events, missingness substitutions and future corrections. Any feature that reveals future rank, admission, outcome or identity is excluded and the affected comparison regenerated under a newly declared version, not silently repaired in place.

## 10. Trial receipt and decision states

Every empirical return must include:

```text
experiment_id and immutable version
mechanism, role, sign/horizon and falsifier
source/use permissions and canonical owner references
population and all inclusion/exclusion counts
feature availability mode and cutoffs
actual serving/treatment basis and candidate snapshot
original fill, benchmark and outcome-version receipts
train/development/holdout/prospective interval
primary metric, minimum useful effect and downside bound
multiplicity, clustering, power and stopping rules
all attempted variants and negative controls
point estimates, uncertainty, cost/capacity sensitivity
failure modes, operational cost and source reliability
reproducibility commands, code/input hashes, limitations
PROMOTE / CONTEXT_ONLY / KILL / NULL / UNINFORMATIVE / ACCRUAL_GATED
owner adjudication and narrow rollback/maintenance route
```

These are content requirements for existing research receipts, not a new experiment database. Published legacy outcomes retain their provenance; this program must not quietly overwrite them to make a comparison pass.

## 11. Promotion and rollback

Promotion is specific to a family version, eligible population/regime, consumer, role, horizon and bounded allowed effect. The accepted record must name the owner, data-quality/use conditions, performance evidence, downside tolerance, activation control and rollback trigger. A model may not enlarge its own authority from a successful result.

Operational rollback triggers include source-use restriction, missing identity/availability proof, incompatible schema, unhealthy coverage, stale input beyond the use-specific policy or changed source semantics. Statistical rollback follows the preregistered monitoring rule, not reaction to every losing day. Disable the new consumer treatment without stopping lawful source accrual or deleting evidence/negative results. Verify actual control-state readback and natural consumer behavior after release.

**A negative result is not a project failure to hide.** Engineering can finish with a useful context workflow; scientific adjudication can conclude no demonstrated incremental edge for tested constructions. `EDGE_PROVEN` requires actual positive evidence. `ACCRUAL_GATED` means still pending, not science complete. All three states must remain distinct in the final delivery.
