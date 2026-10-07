# PB-C — Prospective acceptance contract

**Status: PROPOSED DESIGN ONLY.** This document does not authorize collection, implementation, provider procurement, production changes, trading, or promotion of a signal. Numerical choices inherited from the retrospective protocol are candidates for prospective locking; none are validated operating thresholds. The integration owner must resolve the open decisions below before declaring a new observation period prospective.

**Basis:** the PB-C commission as preserved in `PB_C_ANNOUNCEMENT_STUDY_PREREG.md`; `PB_C_METHODS_AND_DATA_REVIEW.md`; and `PB_C_SOURCE_AND_COVERAGE_MANIFEST.json`. Current limitations include partial announcement coverage, uncertain first-public clocks/scheduling, unresolved Nasdaq/VIX data admission, insufficient independently recurring stress variation, and unestablished matched controls. No additional source retrieval was performed for this design.

## 1. Research object and release gates

Lock a new, untouched observation window; issuer/legal-entity mappings; event species; source frame; linkage cutoff; calendar controls; instruments; hypotheses; missingness rules; and analysis code/version before capture begins. The frozen 36-issuer universe is a provisional starting population, not a validated matched sample. Preserve GOOG/GOOGL as one issuer and explicit TSM ADR/local-market mapping.

Every gate returns **PASS / FAIL / UNRESOLVED**, with evidence, responsible existing owner, timestamp and version. FAIL or UNRESOLVED blocks the dependent claim, not preservation of useful evidence.

| Gate | Required acceptance evidence |
|---|---|
| Source-frame completeness | Enumerated required sources and issuer-day coverage receipts; numerator and denominator use the same declared frame. |
| Market-data admission | Instrument identity, permitted research/derivative/publication use, lineage, calendars, adjustments and historical availability verified. |
| Temporal integrity | Reproducible pre-announcement joins; uncertain clocks cannot create precision or directional ordering. |
| Linkage/common support | Dated pre-exposure graph, defined comparison groups, overlap and balance assessed before outcome inspection. |
| Independent variation and precision | Episode feasibility review plus genuine power/precision analysis; issuer-day counts alone cannot pass. |
| Analysis lock | Separate C1–C5 estimands, nulls, exclusions, test family, error criterion and decision rules recorded. |
| Authorized execution | Existing canonical owner references and a separately authorized run; no research-document self-authorization. |

## 2. Complete issuer-day capture and zero semantics

Use the existing event/source owner. A versioned source manifest must map every issuer to required IR/newsroom archives, relevant product/deployment feeds, SEC filings, identified government channels and counterparty sources. Specify languages, legal names, aliases, pagination/date filters, eligibility rules and treatment of live conference disclosures. Unknown counterparties and newly discovered channels require a logged frame amendment; they must not silently enlarge only stress-period coverage.

Required logical fields, mapped onto existing records:

- **Coverage receipt:** issuer, calendar day, source-frame version, required/observed routes, archive bounds/pages, retrieval/acceptance times, content hashes or equivalent provenance, errors and completeness decision.
- **Event observation:** source/document ID, source family, atomic root, issuer roles, program/calendar cluster, publication evidence, eligibility decision and economic coding.
- **Day outcome:** coverage state, eligible root count, unresolved candidates and rejection reasons.

Set `NO_ELIGIBLE_EVENT_IN_FRAME` only when all required routes are enumerated, candidates resolved, and eligible count is zero. Partial, blocked, missing, delayed or unresolved coverage yields `UNKNOWN`; absence from search results is insufficient. A captured event on a partial day remains a valid event fact, but does not make that day's denominator complete.

Primary arrival estimation requires the declared issuer-period risk set to pass coverage certification. Do not repair it by dropping inconvenient days after inspecting stress or outcomes. Any narrower frame/period must have a prelocked admission rule, report exclusions and differential coverage by stress/calendar/issuer, and support only its narrower source-frame estimand. Retain weekend days and genuine negative evidence.

## 3. Pre-event graph and matched comparison

The relationship owner must supply typed, dated edges: procurement, subsidy, equity/warrant, financing, commercial supply, ownership and documented policy relationships. Each edge needs issuer/counterparty identity, effective interval, first publicly available evidence, strength/terms, source and uncertainty. A contract relationship is not political access or a coordination instruction.

Freeze linkage classification **before the stress episode's information cutoff**, not using a later announcement. Unknown evidence remains UNKNOWN rather than becoming an unlinked control. New support creates a new edge; it cannot retroactively change exposure.

Use a prespecified matching/weighting plan with pre-exposure sector/business model, size, volatility, liquidity, fiscal calendar and baseline announcement intensity where admitted data support them. Report common support, balance, effective comparison size and attrition. Calipers, balance thresholds and estimand population are open design choices to lock; no numerical criterion is claimed validated here. If overlap is inadequate, C2 remains descriptive/not estimable rather than forcing a tech-versus-consumer comparison.

## 4. Market-data admission and exposures

For each dataset record provider/original source, exact series, units, timezone, market calendar, adjustment/vintage policy, warmup, missing/stale observations, retrieval hashes, and evidence permitting the intended use. An unresolved rights/access route stays unadmitted; a public download link alone does not settle reuse. Do not acquire a substitute to evade a blocked source.

Provisional candidates retained from the historical protocol:

- **Primary:** Nasdaq Composite closing drawdown from a trailing 60-session high at or below −10%.
- **Separate sensitivities:** Composite 20-session drawdown at or below −5%; spot VIX close at or above 30; VIX five-session rise at or above 10 points.
- **Issuer sensitivities:** appropriately adjusted closes with 60-session drawdown at or below −20% and 20-session drawdown at or below −10%.
- **Rates sensitivities:** exact two-year nominal and ten-year real series, separately; five-session increases of at least 25 basis points. These cannot replace unmeasured primary equity stress.

Admit the Composite itself, not NDX/QQQ; spot VIX, not a futures proxy. Issuer/benchmark admission additionally requires consistent split/dividend treatment, corporate actions, benchmark identity and return conventions. No silent zero filling or forward filling; any stale-observation rule must retain source age and be locked by instrument.

Provisionally retain prior-five-session exposure, prior-ten-session sensitivity, and an episode reset after at least ten nonstress sessions. Warmup must cover every lookback, lag and reset. Stress inputs must have been available before the event information cutoff; conservative prior-calendar-date joins are acceptable for a separately defined date-level analysis. Keep instruments separate and preserve contemporaneous vintages.

## 5. Publication clocks and economic terms

Store publisher time/timezone, first-observed time, feed/filing acceptance time, retrieval time, revision history, earliest-known evidence and any uncertainty interval separately. A court filing date, publisher date, call time and global first-public time are not interchangeable. For date-only events, C1 may use a locked conservative day-level lag; C3 may establish proximity without direction. C4 requires an event-time fence sufficient to choose the first tradable reaction interval; otherwise return persistence is unmeasured.

One economic agreement is one root across issuer/counterparty mirrors. New milestones require a documented change in economics; republication alone cannot create an event. Preserve broader programs and shared issuer involvement.

Before seeing subsequent returns—and, where feasible, stress labels—code direction, materiality, attention content, and stage: plan, authorization, conditional commitment, definitive agreement, funding/closing, delivery or recognized revenue. Record amount/currency, horizon, incremental-versus-repackaged scope, conditions, cancellation rights, dilution, minimum volumes, price-floor/offtake terms and counterparties. Unknown terms remain null. Disputed coding requires adjudication or exclusion from the strict quality subset.

A scheduled earnings release containing a discretionary business decision stays scheduled for announcement timing. `UNKNOWN` scheduling is excluded from the strict freely timed subset. The prospective owner should also lock an operational date-eligibility rule based on complete calendar capture and known disclosure constraints; that permits an explicitly named calendar-eligible-announcement estimand without pretending to observe management intent. Such a proxy must remain distinct from certified timing freedom, and its performance should be shown alongside the strict subset.

## 6. Episode feasibility is not power

**Provisional operational gate: at least ten plausibly independent stress episodes for the instrument under study before attempting population-level inference.** This is a feasibility floor, not a validated sample size, power result or significance entitlement. Ten reset-defined onsets are not automatically independent: inspect overlapping exposure windows, common macro shocks and serial dependence. Multiple issuers, days or instruments responding to one shock do not create new independent episodes.

Before confirmatory analysis, perform and archive a design-specific simulation/power or interval-precision study using baseline arrival rates from separate/prespecified calibration data, plausible effect sizes, episode spacing, issuer/program/day dependence, overdispersion, capture loss, linkage prevalence, matched overlap and multiplicity. Lock the minimally meaningful effect, error criterion, desired power/precision and stopping horizon before outcomes are inspected.

If the ten-episode floor is unmet, retain descriptive/prospective-only status. If it is met but precision is inadequate, extend only under a predeclared rule or commission a new locked window. Do not loosen stress thresholds, pool unlike instruments or stop on favorable estimates to manufacture feasibility.

## 7. Separate C1–C5 acceptance outcomes

| Claim | Prospective result and required interpretation |
|---|---|
| **C1: stress changes positive freely timed arrival** | Estimate source-frame absolute rate difference and rate ratio using certified issuer-day risk sets and admitted lagged stress. Report episode-level uncertainty and dependence. Missing coverage or no strict freely timed sample means NOT_ESTIMABLE, not a zero effect. |
| **C2: stronger effect with prior linkage** | Estimate the prespecified stress-by-linkage contrast only after graph timing and common-support gates. Separate association from causal interpretation; inadequate overlap means NOT_ESTIMABLE. |
| **C3: unusual cross-firm sequences** | Count distinct roots with disjoint issuer sets; separate same-day proximity from ordered sequences. Report joint-source dedup and common-program/conference coarsening. A sequence result does not identify a coordinating actor. |
| **C4: economic quality and persistence** | Compare preclassified economic groups at H1/H5/H21 using admitted issuer, broad-market and sector returns, verified event fences and corporate actions. Separate announcement plans from execution. Missing admission means NOT_MEASURED; return-defined quality is rejected. |
| **C5: ordinary behavior/calendar explanation** | Evaluate a prespecified calendar/base-rate alternative with complete scheduled-event capture, out-of-sample calibration where feasible, and contrary cases. Strong explanatory performance weakens a timing-orchestration reading; residuals alone do not prove coordination. |

Lock a limited primary test family and multiplicity treatment before analysis; report estimates, intervals, denominators, exclusions and null informativeness. Statistical support, rejection, insufficient precision and unmeasured outcomes are distinct. No aggregate “coordination probability” or smallest-p-value disposition.

## 8. Calendar nulls, negative cases and ownership

Preserve scheduled events on actual dates in the freely timed arrival null. Separately define the C5 earnings-calendar diagnostic, where moving scheduled dates asks a different question. Month/weekday permutations are provisional diagnostics, not comprehensive calendar adjustment. Document fiscal earnings weeks, conferences, investor days, regulatory deadlines, macro releases and holidays where supported. Nontrading-day announcements need a declared calendar-day null or descriptive treatment, never an automatic Monday shift.

For arrival tests, do not condition on observed daily event totals. A separate C3 issuer-label/null design may preserve daily intensity to test which firms coincide; label the changed estimand. Preserve root/program bundles in the relevant sensitivity. Lock random seeds, simulation counts and tail/tie rules; report Monte Carlo uncertainty and immovable-event counts.

Capture adverse, mixed, delayed/cancelled, nonstress-positive, stress-with-zero, and ordinary scheduled cases by the same rules. Select source-frame negative-window audits mechanically before inspecting their announcements. Retain falsifying cases and locked leave-issuer/species/program-out sensitivities.

Reuse existing **event/claim**, **News-to-Business-Impact economic interpretation**, **Policy Watch**, **relationship graph**, and **evaluation/Prophet research** responsibilities as applicable; the integration owner must bind these logical roles to actual canonical owner references. The contract proposes fields and acceptance checks, not a competing schema or store. No new event store, live watcher, trading rank, score, sizing rule, timing oracle, deployment or after-turn continuation is authorized.

**Acceptance package:** locked protocol and owner map; source/data rights manifests; coverage ledger; deduplicated event/relationship records; clock/coding audit; episode and power report; analysis/null specification; reproducible gate results; separate C1–C5 dispositions. A research acceptance decision cannot confer trading authority.

