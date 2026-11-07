# Intelligence Workspace 2.0 — Implementation Plan and Production Acceptance

> **For agentic workers:** Use the installed `superpowers:subagent-driven-development` or `superpowers:executing-plans` skill when available and applicable, together with current protected Mastermind procedure. Implement bounded tasks with failing tests first, evidence-backed verification and independent review. A named worker route is not runtime admission.

**Goal:** Deliver the complete question-centered investigation loop across Mastermind, with safe persistence, context, evidence, history, scenarios, sharing and responsive continuity—not merely a schema, new page or prototype.

**Architecture:** [Master architecture](03_MASTER_ARCHITECTURE.md): thin Investigation aggregate inside existing Terminal user services; immutable layout-owner revisions; references to existing Thesis, evidence, query, alert and domain-calculation owners; one typed context interpretation shared with Brain and replay adapters.

**Tech stack:** Current Terminal source declares Next 16.2.9, React 19.2.4, TypeScript, Supabase, Vitest and Playwright. Macro owns Python contracts/resolvers/projections. Use installed/current repository dependencies rather than upgrading unrelated infrastructure. [Terminal package manifest](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/terminal/package.json)

**Spec:** [03_MASTER_ARCHITECTURE.md](03_MASTER_ARCHITECTURE.md), [04_UX_JOURNEYS_AND_PAPER.md](04_UX_JOURNEYS_AND_PAPER.md), [source census](01_CENSUS_AND_SOURCES.md). The latter defines proof gaps and current source pins.

## 1. Global constraints and release meaning

The existing workstream is revived through its current owner; do not create a second organizational workstream or execution lifecycle. Astra owns program decisions/integration once lawfully assigned; builders own bounded work and independent reviewers do not acquire merge/release authority.

No duplicate fact cache, evidence graph, Thesis engine, research database/service, identity registry, alert scheduler, replay clock, collaboration plane or Brain-memory authority. New tables/contracts described in the spec are justified extensions inside current user services, not permission to bypass an existing owner.

Every fact/context/source assumption is typed and qualified. Reads never advance the reviewed baseline, alter a Thesis, create alerts or trade. Historical data is never silently replaced by current data. An uncertain write is reconciled, not retried as a new effect. Existing layout-only, guest, phone, EN/ZH, drawing and MTF behavior must remain intact.

**Completion is P9 acceptance of the full program**, not the first private slice. A blocked real-principal proof freezes its affected production claim, not all unrelated safe implementation. Any proposed reduction of the agreed end-state must be an explicit architecture/product ruling with residuals—not a renamed MVP presented as completion.

## 2. Review focus

Five cross-cutting risks deserve explicit independent review throughout:

1. A valid-looking historical view fetches a live-only source, and Brain includes it without disclosure.
2. Team access to an Investigation leaks private Thesis/Vault text or source identity through titles, counts, exports, forks or caches.
3. Layout/head CAS appears correct but immutable references point to mutable config, so old research changes retrospectively.
4. A timeout after commit is reported as failure and the next attempt duplicates the object or alert.
5. New context labels race with old data, creating an apparently coherent but wrong entity/time/scenario display.

Tests for these risks are assigned to P1/P2/P3/P5/P6 below and repeated in final acceptance.

## 3. Program topology and critical path

`P0 → P1 → P3 → P4 → P5 → P7 → P9` is the principal product path. P2 context work proceeds after P1 contract freeze and can overlap P3. P6 sharing/rights can proceed after P1 and the necessary authoring-reference contracts, but cannot announce production proof before actual principals are admitted. P8 query/alert/other consumers follows the shared contracts and can overlap final integration. Native Facts performance work starts during P0/P1 and remains in its existing owner.

Do not assign several workers overlapping edits to `TerminalShell.tsx`, layout storage or the same migration reservation. Freeze shared contracts and let distinct adapter/test/design tasks proceed independently. Use a small concurrency level determined by actual admitted capacity and review bandwidth; no fictional fleet availability or unlimited nested fanout.

## 4. Re-cut waves

### P0 — Recommission, resolve critical owner gaps and freeze contracts

**Owner:** Astra program principal, current organizational owner, Terminal user-services/layout maintainer and Macro contract maintainer. **Dependencies:** current live delivery and fresh source procedure. **Outcome:** exact existing workstream/custody and artifact pins recovered; architecture decision accepted; no conflicting active implementation; first vertical slice ready to execute.

**Surfaces:** existing workstream record, current architecture decision home, Terminal migration namespace/owner contracts, Macro `engine/intelligence_workspace` and `contracts/intelligence_workspace`, exact current Paper home. Do not hand-edit generated Agent OS state.

- [ ] Re-pin protected Mastermind, Macro and Terminal; read same-SHA applicable procedures. Compare only changes that can invalidate this report's owner map, write protocol or proof gates.
- [ ] Re-read fresh Steward/current responsibility. Resolve the stale evidence identified in the census through its owner; do not infer incumbent availability from the old parked record.
- [ ] Confirm no existing durable general-question owner already satisfies the target. Produce the storage/API/identity evidence that accepts or falsifies the new aggregate.
- [ ] Record decisions on Investigation ownership, layout history, versioned subject types, authoring/Scenario recipe placement and source-retention limits. Reconcile I24/I25 explicitly.
- [ ] Obtain an approved QA-principal/team plan for authenticated and two-principal proofs, without changing memberships or requesting secrets merely to unblock development.
- [ ] Benchmark current Native Facts owner path separately from the workspace shell. Capture cold/warm, single/multi-entity and provider-degraded cases.

**Acceptance:** exact decisions, scoped implementation/test plan, current owner boundaries, proof reservations and no duplicate owner. **Production gate:** no production effect in P0. **Unlocks:** P1/P2/P3 work packages; independent latency and rights-read audit.

### P1 — Private durable question, immutable layout reference, exact reopen

**Owner:** Terminal user-services/layout builder; Macro contract reviewer; independent transactional/security reviewer. **Dependencies:** P0 architecture freeze. **Outcome:** a signed-in user saves a question from an existing layout and reopens the exact question/reference state on another device without successful AI being required.

**Proposed files:** `terminal/lib/investigations.ts`, `terminal/lib/investigationContracts.ts`, `terminal/app/api/investigations/route.ts`, `terminal/app/api/investigations/[id]/route.ts`, revision/operation routes, `terminal/components/workspaces/InvestigationWorkspace.tsx`; extend existing `layouts.ts`, `workspaceMenuOps.ts`, LayoutMenu and route entry. Add an approved migration under the current reserved prefix, not a guessed number. Paired Macro schema/vectors live in existing intelligence-workspace contract directories.

**Tests:** exact manifest round trip, CAS/create idempotency, same-ID/different-body rejection, rollback, cross-account isolation, immutable layout revision, preservation of old layout/guest paths, unknown-write recovery and 320/390/820/1440 flows.

**Production gate:** approved signed-in create/readback/reopen/rename/duplicate/export/import/stale-edit/fork path tied to deployed source, plus no cross-account access. This also closes the old W2-A signed-in debt for the exercised operations. **Unlocks:** a real research object and stable reference foundation. Full details are in [the first commission](06_FIRST_IMPLEMENTATION_COMMISSION.md).

### P2 — General semantic context with existing-bus adapters

**Owner:** Terminal context/Chart Bus builder, Macro W1-C compiler maintainer, independent concurrency reviewer. **Dependencies:** P1 types and snapshot identity; can overlap evidence UI work. **Outcome:** deliberate typed linking across admitted widgets, with visible receipts and one Brain interpretation.

**Proposed files:** `terminal/lib/semanticContext.ts`, `terminal/lib/semanticContextAdapters.ts`, `terminal/lib/__tests__/semanticContext.test.ts`, `terminal/e2e/investigation-context.spec.ts`; extend current Chart Bus integration, `workspaceLayout.ts`, `workspaceMigrate.ts`, and existing Brain context provider; adapt `components/surface/replayBus.ts`/`replayContext.tsx`. Macro extends `context_compiler.py` and existing context contracts rather than a new Brain endpoint.

**Interfaces:** `applyContextDelta(snapshot, delta, portRegistry) -> {snapshot, receipt}` is pure; `resolvePortInputs(widget, snapshot) -> EffectiveWidgetContext` is typed; the server compiler produces the corresponding negotiated AI envelope. One input cannot follow two incompatible groups implicitly.

**Tests:** duplicate suppression, stale base, epoch remount, loop prevention, multiple groups, pinned/local behavior, read-only consumer, wrong type, old-result race, origin overflow, exact request precedence, duplicate-symbol/MTF preservation, keyboard/touch controls and zero alert/Thesis writes.

**Production gate:** real authenticated two-widget security and multi-subject/time journeys with receipt agreement between UI and Brain. **Unlocks:** reusable semantic integration instead of page-specific hidden synchronization.

### P3 — Qualified evidence, reviewed baseline, diff and deterministic-first Brain

**Owner:** Macro evidence-projection/Native Facts maintainers, Terminal evidence UI, existing Brain owner. **Dependencies:** P1; P2 before generalized-context acceptance. **Outcome:** save a reviewed evidence basis, return later, see qualified changes and ask Brain with inspectable inputs.

**Proposed files:** `engine/intelligence_workspace/evidence_projection.py`, `engine/intelligence_workspace/evidence_diff.py`, associated contracts and `tests/test_investigation_evidence.py`; `terminal/lib/investigationEvidence.ts`, Evidence/Change/BrainScope components. Existing Company Intelligence/Vault/other domain BFFs provide data through bounded adapters.

**Interfaces:** `qualify_references(refs, actor, temporal_scope) -> QualifiedReferenceSet`; `compare_evidence(baseline, current, comparison_spec) -> EvidenceDiff`; pure comparison receives already admitted owner data and never fetches providers.

**Tests:** no baseline, missing comparator, unit mismatch, wrong entity, source correction, rights loss, stale vs absent, stable unchanged, receipt-only lineage, delayed facts, deeper AI failure and source expansion disclosure. Insert an untrusted source instruction and prove it cannot modify scope/rights or cause a write.

**Production gate:** real retained baseline plus a controlled qualified source/update difference; source/field receipts open; old human belief is unchanged; historical or unavailable evidence is not silently current. **Unlocks:** the core research-resumption value and reliable Brain integration.

### P4 — Competing hypotheses, historical authoring and research closure

**Owner:** Existing Thesis/research-authoring maintainer with Terminal research UI; independent semantic/domain reviewer. **Dependencies:** P1/P3. **Outcome:** preserve and compare multiple attributed hypotheses, their supporting/weakening evidence and the analyst's historical decisions.

**Surfaces:** extend `theses.ts`, `ThesisWorkspace.tsx`, current Thesis schemas/RPCs and existing amendment pathways where applicable; add typed argument-relation projection in Investigation contract. Do not duplicate `theses`/`thesis_versions` or misuse timed `claimAuthoring.ts`.

**Tests:** old Thesis version immutable, same Thesis in two investigations, revise one reference without replacing another, AI proposal requires explicit acceptance, false “contradiction” for incomparable metrics, unresolved interpretations, user-stated confidence attribution, close/archive/reopen without alert or execution mutation.

**Production gate:** authenticated create/link/revise/compare/close journey with readback of both old and new owner versions. **Unlocks:** “what did I believe and why?” and meaningful history instead of an answer cache.

### P5 — Scenario and honest temporal reconstruction

**Owner:** Existing replay and domain-calculator owners; Macro historical-data qualification; Terminal temporal UX. **Dependencies:** P2/P3 and relevant P4 authoring contract. **Outcome:** inspect then-known versus current evidence and compare explicit assumption recipes without present-day contamination.

**Surfaces:** existing replay owner plus `terminal/lib/investigationTemporal.ts`, `terminal/lib/investigationScenarios.ts`, `engine/intelligence_workspace/temporal_projection.py`; existing `marketStructure.ts` is an initial calculator, not a new scenario engine. Owner schemas declare historical capability.

**Tests:** late release, late ingestion, revised old period, missing vintage, archived last frame not live, live-only withdrawal, explicit current side-by-side group, method-version unavailable, assumption/fact distinction, fractional/percent/bp handling and -3.0→-2.5 pp signed/absolute delta example. Freeze a then-known fixture before introducing a later correction and prove its historical answer does not change.

**Production gate:** at least one actual retained historical owner source and one controlled unavailable-source case; do not call all widgets replayable. **Unlocks:** replay and scenario continuity with bounded truthful coverage.

### P6 — Team sharing, fixed revisions, forks and revocation

**Owner:** Existing tenancy/resource-grants and user-services/layout owners; independent adversarial rights reviewer. **Dependencies:** P1 and stable reference contracts; P4 for Thesis sharing cases. **Outcome:** explicitly share layout versus Investigation, live head versus fixed revision, with correct source-rights handling and attribution.

**Surfaces:** extend current resource type/grant handling, layout team flows, Investigation BFF and share UI. Keep DDL0022; inspect the live schema before any additive migration. No new collaboration service or role vocabulary.

**Tests:** private default, team member read-only, owner/admin permitted edits, stale writes, foreign-team scope, revoked access, missing private Thesis rights, licensed Vault denial, title/count/search/export/Brain/fork leaks, attribution, private fork and no duplicated active alerts.

**Production gate:** **two real approved authenticated principals** in an explicitly approved test team, named by safe evidence identities: A creates/shares, B reads; B's prohibited write is denied; A unshares/revokes the test resource, B loses access; private fork behavior is proven only while allowed. Actual foreign-team/role-change cases require an approved matching setup; fixtures cannot be relabeled as those real proofs. Restore/delete only approved test resources. This closes the exact #555/#720 real share/read debt, not by creating memberships without authorization.

**Unlocks:** legitimate collaboration rather than whole-config permission assumptions.

### P7 — Cross-product integration and complete responsive continuity

**Owner:** Terminal integration lead plus current Company Intelligence, Theme/Market Ontology, Prophet, Options and macro view owners. **Dependencies:** P2–P6 as required by each journey. **Outcome:** all seven journeys in the UX document can start, investigate, leave, resume, compare and close through owner-native data.

**Surfaces:** `AnalysisWorkspace.tsx`, Company Intelligence BFF/view, `ThesisWorkspace.tsx`, Discover/Theme surfaces, Options/Prophet displays, macro templates and existing Brain entry/return links. Use reusable adapters/widgets; avoid copying whole pages into TerminalShell.

**Tests:** all J1–J7 subject/temporal/source cases, exact return links, wrong-event reset, missing owner/unsupported subject, template contains no personal data, cross-device state, 320/390/820/1440, EN/ZH, focus/keyboard, reduced motion, text resize and accessible source/history views.

**Production gate:** authenticated representative security/company, theme, macro, Prophet and Options journeys, with unsupported capabilities labeled and excluded. An adapter cannot be called complete merely because a button opens an unrelated page. **Unlocks:** universal research continuity rather than an isolated research island.

### P8 — Research consumers: screens, explicit watches, templates and capture

**Owner:** Existing query/screener, alert, watchlist, Vault/capture, rating and Neural Web owners as applicable. **Dependencies:** common reference/context/rights contracts. **Outcome:** research connects to reusable queries and deliberately created watches without duplicating their lifecycle.

**Surfaces:** current `ScreenerView.tsx` and its data pipeline, alert-owner APIs/outbox, watchlist owner, Vault ingestion/reader, existing prompt/template homes. A typed screener compiler/executor is a bounded query-owner commission before natural-language proposals. Ratings/analyst-action sources need actual owner and license evidence before an adapter is enabled.

**Tests:** NL proposal preview cannot execute arbitrary code; saved query and evaluated membership vintage differ; static list vs dynamic query distinct; source data unavailable is visible; explicit alert creation idempotent and never triggered by reopen; capture respects rights, deduplicates through content owner, preserves attribution; templates contain no active alert or private-source payload.

**Production gate:** at least one real saved-query/reference journey and explicit owner-created watch journey using approved test resources. Any independently unbuilt data product remains a named owner dependency with disabled/unavailable UI, not a fake metric. Astra must distinguish Workspace integration completion from unrelated algorithm delivery; an agreed required consumer cannot silently be dropped.

**Unlocks:** research-to-observation continuation, not automatic trading.

### P9 — Integrated acceptance, controlled rollout and durable closeout

**Owner:** Astra integrator; independent cross-system/security reviewer; existing release and product acceptance owners. **Dependencies:** P0–P8 required outcomes and all open critical/important review findings. **Outcome:** complete, production-proven investigation experience with current evidence and rollback readiness.

**Tests/gates:** whole matrix below; exact-head CI; independent review on the integrated immutable head; actual deployed source mapping; real authenticated/two-principal receipts; migration/export/fork/replay/performance/a11y evidence; formative reasoning/resumption evaluation. Reconcile release drift before acceptance. Roll out through existing flag/deployment owners, not a new release mechanism.

**DONE:** one canonical Investigation identity; old layout/Thesis/saved-view workflows preserved; seven journey classes supported through admitted owners; qualified evidence and honest unavailable states; context/Brain agreement; historical belief preserved; no unauthorized side effects; rights-safe sharing/forking; operational SLOs measured and met or an explicit owner-approved residual ruling; docs, capability ledger and existing organizational state updated truthfully. A safety-critical data-loss, entitlement or temporal-contamination defect is not waivable as “UI polish.”

## 5. Migration and backward compatibility

### M0 — Inventory before change

Sample actual saved `chart_layouts`, legacy exports, current `workspace_layout.v1`, named/team/private layouts, unnamed `mm.ws`, Thesis histories, private RMS presets and any owner-supported scenario recipes. Record counts, schema distributions, validation failures and payload sizes without exporting private content into public evidence. Back up through the existing owner and record recoverability, not just a successful backup command.

### M1 — Additive schema and immutable layout history

Reserve the next current Terminal migration prefix; do not reuse 0022 or guess the next number from this report. Add owner-scoped tables/policies and transactional write paths behind existing feature flags. Preserve old reads and menus. The first retained snapshot of an existing layout records its actual capture time and original config digest; do not invent pre-migration history.

Current layout-name uniqueness and row-UUID/ABA protection remain. Deletion must preserve or remove retained revisions according to existing retention/privacy policy, not accidentally cascade away research history or illegally retain deleted data. An authorized tombstone can preserve link meaning without retaining forbidden content.

### M2 — Explicit promotion, not bulk reinterpretation

“Start investigation from layout” creates a new question referencing the existing layout revision. It does not convert every layout into an Investigation. `mm.ws` remains local until explicit save. Analysis remains a route; Thesis remains its owner; RMS saved filters remain filters. Existing saved-view fields that were never persisted cannot be recovered by migration. Ask for or clearly reconstruct missing intent with user confirmation; do not manufacture it from today's evidence.

Any legacy scenario inputs are mapped through an explicit typed recipe adapter and verified value/unit-for-value/unit before research-only content is lifted from layout configuration. Unknown fields remain recoverable in the original export and block lossy save, rather than disappearing.

### M3 — Version negotiation and export

Old v1 clients continue to read supported old layouts. They must refuse unsupported new contracts safely and offer original export, not overwrite them with a reduced payload. New Investigation export is a rights-filtered owner-supported manifest/revision bundle with version references and checksums, not a provider-data dump. A legacy layout export remains a layout export. Import validates schema, actor, identity mapping, rights and size before any atomic write; repeated import operation identity cannot duplicate effects.

### M4 — Rollout and rollback

Enable staff/approved test users, then a controlled cohort through existing rollout owners. Monitor error/unknown-write/conflict rates, incorrect-context reports, source latency and unauthorized read attempts. A rollback disables new creation/consumer surfaces but preserves already stored new revisions and a supported read/export path. Do not drop new tables or transform all new records back into a lossy v1 format. Restore from verified owner backups only through the approved incident/release path.

Zero-loss means **all previously persisted user information is preserved or explicitly recoverable**, not that unavailable source vintages or fields that were previously dropped can be recreated.

## 6. Performance architecture and proposed budgets

The historical W1-B receipt reported warm n=5 p95 first value 3,999 ms and completion 4,006 ms; local multi-entity resolution p95 525.716 ms exceeded its 300 ms target. These are dated measurements, not current telemetry. P0 must remeasure them. No new canonical cache is authorized as a shortcut. [I04]

| Metric | Proposed acceptance target | Measurement boundary |
|---|---|---|
| Saved question/orientation usable | p95 ≤1.0 s desktop, ≤1.5 s representative mobile | Authenticated navigation through manifest render; source evidence pending is visible |
| Warm qualified Native Fact first value / completion | ≤1.5 s / ≤3 s, preserving the historical target | Actual request to useful qualified value/completion, not placeholder tokens |
| Context computation | p95 ≤16 ms desktop, ≤32 ms mobile | Pure accepted-delta computation; does not hide network time |
| Context render commitment | ≤50 ms desktop, ≤100 ms mobile | Target labels and pending states coherent; old data never relabeled |
| Manifest size | ≤64 KiB new Investigation revision | Serialized bytes, measured before write; current layout limit remains its existing validator |
| Default heavy widgets | 2–3 desktop; 1 visible heavy widget on narrow mobile | Saved configurations may contain more, but hydration is lazy |
| Concurrent owner reads | Initial ceiling 6 desktop / 2 mobile | Tune only with measured capacity; cancellation and dedupe required |
| History paging | 50 revisions per page | No full-history hydration on reopen; test a 10,000-reference historical fixture |

These are proposed program budgets to validate before rollout, not promises already achieved or universal device guarantees. Define representative hardware/network/data distributions and sample size before benchmarking. Report p50/p95, cold/warm, failure rate and confidence/variability; do not infer a reliable p95 from five trials.

Implementation strategy: render intent first; resolve only visible/necessary widgets; deduplicate identical owner/entity/version/temporal/entitlement requests through existing owner-native caches; propagate context deltas; cancel superseded reads; use generation fences on results; prefetch only safe likely-next owner reads; virtualize lists; pause offscreen charts; page research history and receipts; avoid re-fetching every widget after an unrelated scenario or note change.

Cache keys include temporal mode/vintage and authorization scope; revocation invalidates permitted cached projections. Client memoization and mounted request sharing are not new canonical caches. Existing quote/Native Facts bottlenecks are repaired at their owner, not hidden behind stale workspace data. Background evidence refresh is a bounded read; it creates no standing monitor or durable refresh scheduler without separate owner authorization.

## 7. Security and entitlement model

All commands use authenticated server identity, existing CSRF/origin protections, input limits and current RLS/resource grants. The client cannot select its tenant, author, source license, provenance or privileged context. Foreign IDs must not leak existence through inventory, error details, counts or source titles. Body digests are computed/validated server-side and are not authorization.

Authorize at list, detail, revision, reference resolution, Brain assembly, share preflight, export/import and fork. A layout's team visibility does not grant private Thesis/Vault access. Rights changes affect retained revisions and cached projections. A fixed revision can resolve to a permitted tombstone when content is revoked. Preserve license/retention requirements rather than promising permanent access to a copied document.

Treat external documents, saved notes and model outputs as untrusted content. Sanitize rendering through existing safe components; never evaluate arbitrary scenario/query code from a prompt or imported manifest. Tool-capable AI writes require explicit owner-native proposals/actions, not source instructions. Redact secrets/internal paths from receipts and telemetry. Tests must include malicious source instructions, overlong IDs, forged owner namespaces, malformed dates, cyclic references and dangerous HTML.

## 8. Red-team and test matrix

| Failure / test ID | Required defense and negative test | Layer / owner wave |
|---|---|---|
| T01 God-object growth | Reject source bodies/series/transcripts and oversize manifests; verify original remains | Schema/unit P1 |
| T02 Duplicate persistence | Architecture review maps every field to one owner; no new DB/service/cache/config silo | Static review P0/P1 |
| T03 Duplicate Evidence graph | Argument edges carry interpretation, evidence refs resolve to domain owner | Contract P3/P4 |
| T04 Duplicate Thesis | Same canonical Thesis version referenced in two investigations; edits retain lineage | Contract/e2e P4 |
| T05 Hidden AI state | Reopen with Brain history unavailable still restores question/baseline/refs | e2e P1/P3 |
| T06 Stale appears current | Re-render old receipt; freshness unchanged, stale shown | Unit/e2e P3 |
| T07 Inference becomes fact | AI-produced value cannot enter Native Fact channel or overwrite owner data | Contract/security P3 |
| T08 Propagation loop | Consumer receipt/data arrival never emits; repeated mutation applied once | Unit/property P2 |
| T09 Surprise cross-widget update | Pinned/local port and unrelated group unchanged | Unit/e2e P2 |
| T10 Collision | Two stale-base emitters produce explicit conflict, not silent overwrite | Concurrency P2 |
| T11 Layout corrupts research | Drag/reorder/rename does not revise Thesis or reviewed baseline | Integration P1/P4 |
| T12 Fragile migration | Golden legacy fixtures, unknown fields, invalid layouts, rollback/original export | Migration P1/M0–M4 |
| T13 Payload explosion | Boundary-size and 10k-history fixtures; paged history, no eager source bodies | Performance P1/P9 |
| T14 Slow reopen | Throttled sources/deep-provider failure still yields useful question/orientation | Performance/e2e P3/P9 |
| T15 Widget overload | Default templates bounded; offscreen heavy widgets suspend | Visual/performance P7 |
| T16 Feature soup/blank canvas | Save a free question with no required graph/Thesis; guided templates usable | UX evaluation P1/P7 |
| T17 Mobile failure | 320/390/820/1440; long EN/ZH; keyboard/focus/text resize | e2e/a11y P7 |
| T18 Collaboration conflict | Two real or isolated authenticated clients CAS; no lost update, compare/fork offered | Integration/prod P6 |
| T19 Rights leak | Cross-account/team, private reference, metadata/count/export/Brain/fork/cached paths | RLS/adversarial P6 |
| T20 Entitlement loss | Old revision readable only within current rights; tombstone or explicit denial | Contract/prod P6 |
| T21 Temporal contamination | Historical mode rejects live-only data, late releases and future corrections | Property/integration P5 |
| T22 Reopen activates actions | Spy/assert zero alert/portfolio/trade/Thesis writes on open/refresh/replay | e2e P1–P9 |
| T23 Noun ambiguity | UI/API labels distinguish layout, question, Thesis, filter, source and alert | Product review P7 |
| T24 False empty inventory | Timeout/403/server failure never render successful empty list | Route/e2e P1 |
| T25 Unknown write duplicate | Commit then drop response; exact operation lookup/replay returns one object/revision | Transaction/integration P1 |
| T26 Fake idempotency | Same operation ID different body rejected; cross-actor reuse cannot read result | Unit/security P1 |
| T27 Lost historical layout | New head save leaves old version digest/config intact | Database/migration P1 |
| T28 False contradiction | Different period/unit/definition is incomparable, not contradictory | Unit P3/P4 |
| T29 Scenario overwrites reality | Assumption change leaves source/baseline unchanged; output attributed | Unit/e2e P5 |
| T30 Incorrect spread direction | -3→-2.5 pp: signed +50 bp, absolute narrows 50 bp | Unit P3/P5 |
| T31 False production proof | Receipt must state principal/environment/source/deploy and actual path, no fixture relabel | Acceptance P9 |
| T32 Reader/writer version skew | Old client refuses new unsupported data without destructive rewrite | Contract/migration P1/P9 |
| T33 Recreated layout ABA | Delete/recreate name gives new UUID; stale writer cannot mutate it | Database P1 |
| T34 Model variability disguised as evidence | Unchanged input receipt + different synthesis is not reported as a source change | Contract/AI eval P3 |
| T35 Poisoned reference/HTML | Untrusted content cannot escape rendering or trigger owner actions | Security P3/P6 |
| T36 Insufficient evidence called answerable | Readable cards without required comparator remain incomplete | Unit/e2e P3 |

## 9. Verification commands and evidence format

For proposed Terminal test files, use the existing scripts after installing dependencies through the repository's approved workflow:

```sh
cd terminal
npm test -- lib/__tests__/investigationContracts.test.ts lib/__tests__/investigations.test.ts
npm test -- lib/__tests__/semanticContext.test.ts
npm run test:e2e:responsive -- e2e/investigation-reopen.spec.ts e2e/investigation-context.spec.ts
npm run build
```

Macro contract/projection tasks add scoped pytest tests under the existing test tree, for example:

```sh
python -m pytest tests/test_investigation_contract.py tests/test_investigation_evidence.py tests/test_investigation_temporal.py -q
```

These new test filenames are proposed and must be created by their tasks; commands are not claims that they currently pass. Run current required repository CI and migration namespace guards as well. Browser test setup must distinguish fixture mode, local authenticated integration and actual production; do not switch on a production preview bypass.

Every wave returns: exact source head(s), changed files, schema/vector identities, actual commands/results, independent review disposition, deployed identity if applicable, safe principal/environment proof, remaining limitations, rollback state and exact next dependency. Preserve full logs in the existing evidence owner; parent summaries are bounded. Source merge, deploy success, a successful screenshot and production user acceptance are separate facts.

## 10. End-to-end proof pack

The final pack must contain authenticated create/save/exact-readback/cross-device-reopen; legacy migration/export/import/rename/duplicate/stale-fork; real two-principal share/read/deny/revoke; retained historical Thesis and layout versions; qualified source diff and missing-baseline cases; context/Brain receipt agreement; scenario and historical contamination negatives; all seven journey classes; current performance and accessibility results; independent exact-head review; release/rollback identity and truthful residuals.

Close through the current organizational and release owners. Preserve the original workstream's history and cite this recommissioning packet. Do not declare the whole project done while a mandatory real-principal proof is merely queued, while a critical owner is unbound, or while a later wave is represented only by Paper or a contract.
