# Financial Intelligence Fabric
## End-to-end delivery masterplan: from filings to defensible accounting intelligence

**Commission:** `fif-e2e-masterplan-20261011` · October 11, 2026  
**Existing home:** `WS:FINANCIAL-INTELLIGENCE-FABRIC`, program `fundamental-forensics`  
**Current assignment:** select the next hardest eligible project, assess it, and prepare the execution handoff. This packet does not launch a fleet, transfer a live writer, approve a release, or complete the product.  
**Read with:** [selection and census](SELECTION_AND_CENSUS.md), [first vertical](FIRST_VERTICAL_PLAN.md), [Fable commission](FABLE_HANDOFF.md), [source index](SOURCES.md), and the machine-readable task/acceptance files.

## 1. Decision: finish the existing financial intelligence product

**Select Financial Intelligence Fabric (FIF).** The product should let an analyst ask a precise accounting question, inspect the statement or disclosure behind the answer, compare original and subsequently known information, understand material changes, and export the same answer with its evidence intact. It must work across genuinely different reporting structures, not merely display five companies using one hard-coded template.

This is the strongest eligible remaining project in the assessed set because the unresolved work crosses accounting semantics, source reconstruction, time-safe query execution, evidence security, domain-specific disclosure analysis, production ingestion, analyst experience and cross-surface exports. Difficulty comes from maintaining the same meaning all the way through those systems. It does not come from maximizing agent count. The candidate comparison and its limits are in the census. [S02–S04, S21–S26]

The scope is deliberately different from Single-Name Intelligence. FIF owns financial evidence, statements, comparative and revision semantics, accounting disclosures, findings, peer comparability, and analyst/API/export workflows. It does not build a company digital twin, stock forecast, investment-risk engine or market operating system. Shared issuer names are accounting test cases, not permission to revive excluded programs.

### Explicit scope exclusions

Do not implement Single-Name Intelligence, Grey Deer Risk, Market OS, Mastermind OS, Options Intelligence, Prophet, Market Ontology, GMI, Executive OS or Subagent Fabric as part of this commission. They can be existing owners or future consumers, but their improvement is not a delivery task here. In particular, the original FIF-10 **Prophet shadow** component is excluded by the current Chairman instruction. Record it as excluded from this commission, never as completed. The same applies to clinical prediction in BioCatalyst and new capital-risk or relationship engines.

### The product at acceptance

A user can answer: “What changed in this filing?”, “What was originally reported?”, “What could I have known at this cutoff?”, “Which statement or note supports this number?”, “Is this comparison economically valid?”, and “Can I reproduce this answer in the API and Excel?” The system gives either a supported answer or a specific absence/refusal. It never substitutes a confident narrative for missing evidence.

The reference release uses **AAPL, SNOW, CAT, BAC and GOOGL**, the existing five accounting stress issuers. The broader target remains **250 issuers with deep reviewed coverage and 1,000 with material core statement coverage**, with explicit field/period denominators. These are inherited targets, not observed capacity or current coverage. Scaling requires the proof defined below. [S03]

## 2. Starting reality: substantial code, incomplete production

The source census is pinned to Macro `44a45369617dbbd0afdcf161682679640352a554`, Terminal `8520e5d77e9f0b83973a988cf4f4adff300994cf`, and protected Mastermind procedure `85807cf48e29e2fe5df19534d6b181fc25b9746f`. Refresh only material action-time dependencies; do not restart the full census after unrelated merges.

The existing workstream still calls FIF-3A4 unbuilt. That statement is stale: #7518 merged on October 4, 2026. The current code already implements cutoff-visible cross-filing confirmation. Do not rebuild it from an old todo. However, its production claim remains explicitly narrow: the served query corpus is the two committed AAPL golden accessions, with `attested=false` and `production_issuer_service=false`. [S02, S04]

The direct API census is more revealing than an aggregate maturity label. `app/forensics.py` binds the financial query and statement routes to golden AAPL providers; its revision and packet provider factories return unavailable providers. There are **40 Python modules** under the existing forensics engine, but module count does not turn these factories into a broad issuer service. [S08–S12]

A fresh isolated experiment also found a real evidence-validation defect. The normal golden query built 1,722 ledger events and 130 genuine confirmation receipts. Nine independently altered evidence fields were accepted and displayed after their receipt identifiers and hashes were recomputed. Five altered controls were refused or became not evaluable. This was a local in-memory experiment on pinned source, not a production exploit or deployed fix. The exact result and bounded remedy are in the first-vertical plan. [S05–S07, S28]

**The first critical path is therefore trust closure → real admitted production dataset → existing API → useful analyst journey.** Parallel source qualification, product design and domain gold work can advance, but no broad release should depend on the still-unrepaired evidence seam.

## 3. Preserve one owner for every kind of truth

| Fact or function | Existing owner | What FIF may do |
|---|---|---|
| Canonical issuer/security/listing identity | Data OS and its admitted master/bridge | Bind to owner identifiers; keep unresolved identities explicit. A CIK is not a new estate-wide ID allocator. |
| SEC discovery, capture and immutable source storage | Existing broad SEC/Filing Forensics source owners | Extend required coverage and package completeness; reuse scheduling, storage and request limits. |
| Raw fact occurrences | Existing forensics raw ledger | Preserve source occurrences, clocks and original identities; no parallel fact database. |
| Normalized metric meaning and formulas | Existing metric registry and query kernel | Add reviewed, versioned mappings and applicability; never a browser-only interpretation. |
| Statement presentation | Existing statement graph and service | Generalize supported source layouts while preserving economic and presentation distinctions. |
| Cross-filing lineage and revisions | Existing lineage/query owners | Repair full evidence binding and version later generalization; no second revision store. |
| Company/earnings events | Existing Company Event/Earnings owner | Link accepted events to source-backed metrics and disclosures; no rival event lifecycle. |
| Financing state | Capital Structure owner | Consume its state and supply source observations; accounting disclosure packs do not replace it. |
| User identity, entitlements, saved research | Existing Macro/Terminal user-service owners | Reuse their checks and user-state mechanisms; no new auth or user-data authority. |
| Publication, exports, notifications, retries | Existing accepted service owners | Add narrow content/adapters through them; do not build another queue or scheduler. |
| Finding accountability and outcome history | Existing research/evaluation owners | Register supported finding/quality outcomes, preserve original records; no trading promotion. |
| Runtime, worker admission and continuity | Executive/Fabric, Agent OS and existing carriers | Use them; this project does not improve or duplicate them. |

Source code, PRs and tests remain in GitHub; current organizational state belongs to the existing Agent OS workstream. Historical workstream prose is not evidence of a live writer. Reconcile current source custody and unresolved effects once before effects; do not displace a live modifier or wait indefinitely for a dead chat. [S01, S15–S16, S20, S24–S27]

## 4. Architecture decisions

### 4.1 Retain the semantic engine; replace missing production inputs, not the model

Three alternatives were assessed. A new universal financial platform would duplicate the hardest owners and obscure migration risk. A thin CompanyFacts dashboard would deliver quickly but cannot meet full filing, dimensional and historical evidence requirements. **Extend the existing occurrence/query/packet services with admitted production providers** is the selected approach. The engine already embodies difficult distinctions and has frozen golden witnesses; the missing production path and the trust defect are bounded, inspectable problems.

Keep demonstration delivery and production delivery separate. Do not widen `GOLDEN_AAPL_QUERY_ACCESSIONS`, edit frozen expected answers, or label a committed fixture as attested. A production provider should implement the existing `FinancialQueryProvider`, `FinancialPacketProvider` and `FinancialStatementProvider` contracts. It returns an accepted, immutable dataset or a typed failure. New implementation filenames are frozen by the owning child before coding; no speculative package in this document is claimed to exist. [S08–S14]

### 4.2 Source packages retain enough information to reverse an answer

A qualified package binds accession, document identity, CIK/owner identity, form, period, accepted time, observation/retention time, content hashes, parser version and required taxonomy/transform/role resources. Preserve original markup and parsed occurrence links. Acquisition runs through existing source owners, outside the request/render path. A partial package can be useful as explicitly partial evidence, but cannot be advertised as a complete statement or attested historical dataset.

Use SEC APIs and bulk datasets for their actual roles. CompanyFacts aggregation is not a complete source of custom or dimensional disclosures. Conversely, the SEC's reprocessed Financial Statement Data Sets use rendered primary statements and include a `segments` field; do not incorrectly apply CompanyFacts' whole-entity restriction to all bulk data. Neither shortcut replaces retained filing-level evidence where that evidence is required. [E01, E02]

Respect the SEC's shared fair-access budget across all workers and machines through the incumbent limiter. No child gets an independent copy of that budget. Prefer supported bulk/cached acquisition for scale; a rate refusal is not permission to change identities, hosts or accounts to evade it. [E03]

### 4.3 Four clocks must never collapse into one

Keep economic period, public/source availability, system admission/observation, and applicable mapping/rule availability distinct. Publication time is another recorded event, not a substitute for source time. Each historical query must explicitly bind both data cutoffs and the policy versions allowed at those cutoffs.

A filing downloaded today can support an as-filed reconstruction. It does not prove the house retained or used those bytes at a past decision time. Later corrections and semantic rules must not repair the historical view silently. Keep original source occurrences and prior publications immutable, with explicit supersession or correction relationships.

Preserve the three named selections: **as reported**, **latest known as of**, and **latest restated**. A comparative reprint is not a reported restatement. A filing amendment is not evidence that every number changed. If a relation cannot be established, return not evaluable rather than choosing the newest value. [S06, S07, S13]

### 4.4 Full semantic evidence validation precedes scale

The existing receipt hash checks internal self-consistency. It does not prove that its source fields match the current eligible ledger. The repair must reconstruct expected positive evidence using the existing canonical builder and require semantic equality after the existing identity, namespace and cutoff checks. Test independently corrupted fields with recomputed hashes. A valid digest over invented evidence must fail. [S05–S07, S28]

After this repair, retain the current two-accession v1 boundary. Wider filing chains require a versioned accepted rule, conflict/cycle behavior, cutoff visibility and independent review. Do not delete the size guard merely because a thousand issuers are desired. Within-document precision consistency, cross-filing confirmation and explicit reported revision remain different relations. Rounded numeric consistency is not a general transitive equivalence relation. [S13, E04, E05]

### 4.5 As-reported statements and standardized metrics are separate views

Reconstruct what the company presented without collapsing repeated rows, dimensional tables, financing subsidiaries, eliminations or instant balances embedded in duration columns. Presentation order, calculation roles and economic comparability are related but not identical. A technically valid XBRL document may still require qualified economic mapping.

A standardized observation carries issuer, concept/metric, period boundaries, unit/currency, dimensions and scope, accounting basis, source occurrence, mapping/formula version, coverage, and correction state. A ratio may be evaluated only when its operands share the accepted basis. Unknown dimensions are not empty dimensions; dimensional confirmation does not make a consolidated-only metric eligible. Missing, non-applicable, incomparable, failed extraction and stale are distinct results. [S10–S13]

Use a version-pinned independent validator such as Arelle where it helps challenge parsing and XBRL conformance. Treat it as an oracle for its stated validation question, not as a new canonical financial model or proof that a business metric means what the analyst thinks. [E06]

### 4.6 Accounting intelligence must remain useful and epistemically honest

Findings distinguish reported facts, reproducible arithmetic, source-supported classifications and hypotheses. Materiality includes the absolute amount, denominator, reporting basis and business context—not just a large percentage or one universal score. A receivables increase may deserve review without proving fraud. A model must not produce fabricated audited figures, legal conclusions or investment probabilities.

Models may propose extraction candidates and summarize admitted evidence. Source spans, units, period and definition checks decide admission. Keep document instructions inert. Repeated boilerplate, moved tables, formatting changes and true content removal require different classifications. Preserve alternative explanations and the user-visible reason for abstention. [S17]

Define held-out quality protocols before evaluating candidate extraction or finding families. The known AAPL calibration cases are not held-out generalization evidence. Report precision, recall where the label population is defined, source-fidelity errors, abstention and analyst relevance by family, with uncertainty and disagreement. Do not modify the denominator or labeling rule after seeing a bad result. No market alpha claim is required for a valuable accounting product.

## 5. User experience and real reference coverage

Keep the current Filing Forensics route and existing design system. The default view answers **what changed, why it is worth reviewing, and where the evidence is**. Statements, original/latest/restated comparison, disclosures, peers and source details are drilldowns. A crowded grid of equally weighted metrics fails the intent even if every cell is correct.

The minimum complete user journeys are:

1. Open a new filing and inspect its largest supported accounting/disclosure changes.
2. Open a displayed metric, reach the exact source occurrence or permitted document span, and inspect its basis.
3. Rewind the query cutoff and observe the correct historical answer or absence.
4. Compare a valid peer cohort, understand excluded peers and recover the exact saved comparison.
5. Export and refresh the same values/policies/source references through API and Excel.

These are acceptance tasks, not a requirement to put every control in the first viewport. Use simple explanatory copy and optional technical receipts. EN/ZH, keyboard focus, mobile/tablet layout, direct links and back navigation are mandatory where the existing product promise applies.

The current Terminal path census found no dedicated forensics-named integration. Investigate the existing Company Intelligence composition rather than inventing that a FIF Terminal page already exists. Any new adapter belongs to the accepted platform seam; it must not become an alternative company-research product. [S18, S19]

### Five accounting stress packs

| Issuer | What this pack must prove |
|---|---|
| AAPL | End-to-end source/statement/query/lineage behavior, with the old golden pair preserved and a separate real production package. |
| SNOW | RPO, stock compensation, non-GAAP and issuer KPI definitions without confusing targets or changing definitions with recognized revenue. |
| CAT | Industrial versus financing/segment scopes, inventory/backlog context and eliminations without invalid consolidation. |
| BAC | Bank-native statements, credit/capital/liquidity definitions and applicability; no industrial gross-margin/FCF logic imposed blindly. |
| GOOGL | Correct issuer binding across multiple securities, segment/capex evidence and no duplicated issuer weight in peers. |

The company must supply the actual disclosures; this table does not assert any current business result. Each pack includes exact approved accessions, recent annual/interim reporting, a valid comparative period, accepted source traces, applicable core metrics, one meaningful disclosure family, and an existing-owner earnings link when supported. Required coverage gaps block that pack's acceptance; optional unavailable lenses do not block the whole program.

## 6. Execution organization and token economics

Use the requested hierarchy: **Fable → native Opus suborchestrators → existing Fabric task operators → direct operator execution or admitted workers**. The inspected route is `orchestrator`, `ROUTE: orchestration`, explicit `model: opus`, with the canonical fable-mode loader and the current required sections. Verify the installed route and the child’s actual operator access; source configuration is not proof that the runtime supports the whole nesting. [S20]

| Domain | Native Opus responsibility |
|---|---|
| O1 Trust and contracts | Existing-owner recovery, full evidence closure, lineage/query policy and cross-domain contract integration. |
| O2 Source and production | Filing qualification, ingestion/attestation, immutable datasets and production coverage. |
| O3 Accounting and disclosures | Statements, metric semantics, the five stress packs and twelve specialist packs. |
| O4 Product and distribution | Existing analyst UI, API, saved research, exports, Python client and real Excel workflow. |
| O5 Discovery and quality design | Material changes, peer comparability, preregistered quality protocols and accountable context. |
| O6 Independent verification | Adversarial tests, domain review, reproduction, production acceptance, reliability and closure. |

These are six charters, not six permanently active agents. Start O1 and O2, while O4 can assess the existing experience and O5 can freeze evaluation protocols independently. Admit the remaining work only when dependencies and review capacity justify it. Operators execute bounded outcomes, not a long command-by-command dialogue. Routine extraction or coding uses the least-scarce capable admitted route. A coherent small task should be performed directly by its operator rather than delegated for the sake of another level.

Give each child only the needed task contract, source refs, allowed paths, acceptance cases and return target. Keep logs, whole filing corpora and intermediate reasoning out of Fable's context. Fable resolves material ambiguity and accepts results; it does not redo every operator command. Keep one integration writer for shared query/registry/API paths.

Global accounting includes the principal, coordinators when the runtime counts them, workers, reviewers and repair reserves. There is no per-coordinator multiplication of concurrency or budget. A missing eligible Fabric route is a lane-local blocker, not permission for native labor substitution or provider/account bypass. An earlier queued or effect-unknown worker cannot be duplicated through another adapter.

Track total accepted-outcome cost, including cache/context, review and repairs, through existing accounting. This hierarchy is a strategy for reducing wasted premium context, not a proven percentage saving. Finish returned work before generating an unreviewable backlog. [S01, S20]

## 7. Phases and dependency law

The exact 39-task graph is in [TASK_GRAPH.json](TASK_GRAPH.json). These are documentary task references, not runtime Job IDs or a new queue. Every implementation task must bind a real carrier, current source, allowed write paths, acceptance evidence and return mechanism before START.

### Phase I — recovery, trust closure and a real AAPL product

R0 recovers current custody, effects, source pins and scope. T1 repairs the evidence-validation seam; T2 seals compatibility and corrects stale capability projection. In parallel, D0 qualifies the five-issuer source contract, P0 freezes the existing-product journey, and Q0 freezes quality evaluation. D1 acquires through existing owners, D2 resolves the exact production-attestation lane, D3 supplies admitted production datasets. S0/S1 qualify statements and metric semantics; S2 addresses the versioned later lineage law without silently widening v1. E0/E1 produce supported findings and disclosure changes; P1/P2 connect the accepted data to the existing private API and analyst route. A0 requires a real source-to-browser proof.

Do not let a legacy attestation credential question block offline gold/contract work. Do not release an attested historical service without the required attestation. Those are compatible rules. When necessary, the first current-data slice can be separately accepted at the precision its owner permits; it cannot masquerade as the blocked historical capability. D3’s required admission must be explicitly decided, not deleted to make the schedule look unblocked.

### Phase II — five-issuer generalization and useful discovery

G1–G4 deliver the SNOW/CAT/BAC/GOOGL accounting packs after A0. A1 proves the five real journeys. C0 extends the incumbent incremental discovery path; C1 delivers valid peer comparisons. E2 links financials, non-GAAP, KPIs and guidance to the existing Earnings owner. X0/X1/X2 deliver API/export/Excel and saved research without duplicate user-state or async owners.

Gold source packaging may progress independently before A0, but a completed source pack is not production acceptance. Fable may consume one ready issuer return without waiting for all siblings. A shared schema change must still return to its single integrator.

### Phase III — twelve specialist packs and evidence quality

K1–K4 organize twelve existing roadmap packs. Each pack separately requires schema, lawful source/gold corpus, independent domain review, held-out evaluation, coverage/refusal behavior and real source-linked output. They are not twelve new platforms. The complete list is in [SPECIALIST_PACKS.json](SPECIALIST_PACKS.json): debt; SBC; segments; revenue/contract balances; tax; leases; M&A/goodwill; contingencies; controls/auditor/going concern; proxy compensation; bank disclosures; and biotech accounting disclosures. [S03]

Q1 adjudicates each extraction/finding family under Q0. A failed or underpowered family remains unavailable/research-only until an explicit scope decision; do not relabel it done. Q2 exposes accountable current/historical financial context through existing evaluation and reader owners. It does not implement the excluded Prophet shadow, risk or SNI consumers.

### Phase IV — depth tiers, reliability, exports and independent closure

C2 accrues the declared 250-deep/1,000-core coverage. V0 qualifies latency, error isolation and recovery. V1 proves coverage economics and serviceability, including the specialist and distribution paths. Z0 independently audits all included requirements; Z1 reconciles active children, effects, release evidence and excluded legacy obligations.

The full original roadmap is not completed merely because an AAPL demonstration works. The new commission is completed only against its explicit included scope, with any change to a target approved before acceptance. Never silently waive the last difficult pack, real Excel refresh, production attestation or an unresolved source correction.

## 8. Precise coverage, quality and latency acceptance

“Deep issuer” means the declared annual/interim periods have complete admitted source packages, faithful primary statements, qualified core mappings, applicable specialist coverage, a source-linked packet and accepted analyst journeys. “Core issuer” means the frozen core metric/statement field list and period windows meet the reviewed completeness standard. Print both numerator and denominator and reasons for exclusions. An empty field with a truthful refusal is a valid response but does not automatically count toward positive coverage.

The first action in C2 is to freeze the exact counts, time windows and required fields behind those terms, with current source economics. The inherited 250/1,000 target is not editable by a worker simply because acquisition is hard. On a genuine rights/capacity shortfall, return a measured tier proposal to the principal/decision owner; preserve the original target and the reason for revision.

Use the existing original latency targets as targets unless the current owner accepts a justified amendment before testing: discovery p95 under two minutes after evidenced SEC availability; capture under five; statements under ten; initial packet under fifteen; normal warm company query under two seconds; cold and bounded peer queries under five seconds. Define corpus, burst rate, network/cache conditions, concurrency and observation window before reporting percentiles. Do not report p95 from a handful of happy examples. [S03]

Every displayed numeric cell needs exact trace or explicit absence. Request-time SEC fetches, implicit-current-time historical queries, unauthorized source leakage and silent stale-green states must be zero in the accepted tests. Track incomplete/excluded cases honestly rather than dropping them from the denominator.

## 9. Distribution, privacy and operational acceptance

The Python client, API, browser, CSV, JSON, Parquet and Excel must preserve value, precision, unit, period, policy/cutoff and provenance. Format-specific representation differences are documented and roundtrip-tested. Protect exports against spreadsheet formula injection and reject ambiguous coercion of missing values or large decimals.

The Excel requirement means **source-linked formulas and refresh in an explicitly supported real Excel environment**. A static workbook is not equivalent. Test authorized and signed-out states, source corrections, pinned versus current policies, and source links. Use the existing approved client/distribution/auth mechanism; a new add-in installation, deployment or certification gate must be explicit. Do not promise Windows/Mac/web parity without testing each claimed environment.

Authorize before opening private datasets. Cache keys and responses respect tenant, entitlement, query policy and source generation. User notes or watchlists do not mutate company facts. Async exports and notifications use existing job/service owners and reconcile cancellation, entitlement changes and source-version binding. No copied lifecycle or polling daemon is introduced for convenience.

Failure/recovery tests cover missing source components, malformed content, digest mismatch, unknown or corrected identity, publisher response loss, delayed commits, repeated requests, restart and restoration. Unknown modifying effects remain on the original target until reconciled. A successful health endpoint does not prove the analyst’s source-to-answer path; show the actual installed version, input package, query/response and browser witness. [S08, S15, S16]

## 10. Exact completion and continuation contract

Fable owns cross-domain decisions and integration, subject to current release and custody law. Task operators return reviewed artifacts and proof; they do not self-promote to release authority. Each coherent milestone is verified and saved to existing GitHub/Agent OS/runtime owners. Then start the next safe ready task in the same healthy session. A PR, a checkpoint or a review request is not a reason to stop.

Do not rely on an old owner name as liveness. Do not infer a transfer from a new chat or from this handoff being posted. Never retry or move an effect-unknown modification through another actor. Long source/review/natural-run waits require an existing durable owner and real return path; no implied background Web reasoning.

**Scope-complete acceptance requires** the repaired trust boundary, production five-issuer product, included original roadmap features and twelve individually accepted packs, qualified discovery/peers/depth tiers, real API/Excel parity, quality dispositions, latency/recovery evidence, and an independent closure audit. Every required natural-time or human-reserved obligation must be resolved or explicitly retained under an approved scope decision. The original excluded Prophet/risk/OS/ontology work is not marked done.

**This authoring assignment has a different boundary:** publish a verified assessment/masterplan/handoff that a receiving Fable can execute. No product implementation, full regression suite, production/browser proof or fleet dispatch is claimed by this packet’s publication.
