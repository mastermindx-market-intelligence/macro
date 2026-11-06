# Intelligence Workspace 2.0 — execution and production acceptance

> For Astra CEO and agentic implementers: execute this plan with the existing Subagent Fabric and protected operating procedures. Use task-level test-first implementation and an independent reviewer where available. The task names below are proposed work packages, not created runtime jobs or assigned leases.

**Goal:** deliver the complete Investigation research loop, not merely a schema, Paper mockup, saved-layout wrapper or first MVP slice.

**Architecture:** [02_MASTERPLAN.md](02_MASTERPLAN.md). Existing TypeScript/React Terminal and its authenticated database/RPC owners; existing Python Macro contracts, deterministic owners and Brain gateway. No new application framework, universal graph store, vector-memory authority or orchestration plane.

**Evidence:** [01_AUDIT_AND_RECENSUS.md](01_AUDIT_AND_RECENSUS.md) and [05_SOURCE_LEDGER.md](05_SOURCE_LEDGER.md). All new module/schema/API names in this document are **proposals**, not claims that these files currently exist. Resolve nearer repository guides and active writers before creating or editing them.

## Global constraints and review focus

Preserve `workspace_layout.v1` and its import/export golden vectors. Keep published belief history in Thesis, facts and calculations in their owners, and AI context in the existing Macro compiler. Initial inquiry release is private-only. No automatic operational mutation on reopen. No historical claims without retained owner evidence. No duplicated schema namespace, migration prefix, fact cache, source graph, ACL service or retry plane.

Review focus: mutable references behind supposedly immutable history; a stale response for A arriving after A→B→A; same request ID with different payload or revoked authority; denied evidence leaking through AI prose/metadata; and incomplete evidence reads being mislabeled as removal. These are explicitly tested below, not left to generic integration coverage.

## 1. Commission governance and parallelism

Astra CEO owns the parent program, architecture decisions, consumer denominator, integration, independent review and final release evidence. Use the lowest-cost capable authorized worker for bounded implementation; Fable is not the automatic worker. Do not use `codex/work`. Do not invent current job IDs, worker availability or leases from this document. Every actual commission requires a real `PICKUP_ACK`, then `START` only after current gates clear.

Initial practical lanes after G0 contract freeze:

| Lane | Responsibility | Shared-surface fence |
|---|---|---|
| A — Persistence/integration | Inquiry mutations, layout retention, cross-repo compatibility | Sole writer for shared layout service and migration package |
| B — Context/temporal adapters | Existing bus bridge, compiler evolution, capability receipts | Sole compiler/schema integration writer; owners review adapters |
| C — Product/Paper | Canonical shell, journeys, responsive/locale/recovery states | Designs first; builders do not improvise global tokens/navigation |
| D — Proof/security | Auth identities, permission tests, mutation failure injection, performance and production receipts | Read/QA by default; no account/team/paid-seat creation without authority |

These are scope boundaries, not a requirement to consume four workers. Astra may execute a lane directly or combine disjoint work according to real capacity. Permit deeper delegation only within current fabric authority and bounded ownership. No two workers edit the same shared contract or carrier simultaneously.

Do not serialize the whole program behind CI. While one exact head is being checked, advance independent qualified design, adapters, tests and documentation. Never push into an armed merge race; retain actual carrier/hold semantics. A failed runtime projection blocks ungrounded worker-state claims or unauthorized dispatch, not independent read-only analysis or already-authorized isolated source work.

A durable checkpoint names parent/carrier, exact source and head SHAs, owned files, decision changes, test commands/results, open proof gates, next concrete action and verified continuation mechanism. A watcher is reported armed only after a real successful registration. Documentation publication is not worker acknowledgement.

## 2. Gate graph

```text
G0 owner/contract/proof admission
  -> G1 private retained inquiry vertical
       -> G2 general evidence/resume
       -> G3 semantic context + versioned composition/Brain evolution
G2 + owner retention -> G4 temporal replay
G2 + Thesis/calculator admission -> G5 beliefs/contradictions/scenarios
G2 + G3 + G4 input semantics -> G6 durable Brain artifacts
G1 retention + early rights design -> G7 sharing/forking
G2..G7 contracts -> G8 complete domain integrations
all required outcomes -> G9 production, recovery and final acceptance
```

Design, threat modeling and QA-resource qualification start in G0 and continue in parallel; they are not postponed to G7/G9. G1 is a complete small user outcome. It is not the parent completion condition.

## G0 — Source/owner freeze and first-vertical preparation

**Owner:** Astra CEO with persistence and QA reviewers. **Inputs:** the existing workstream, this packet, fresh exact protected procedures and actual current repository heads.

**Work:** re-read `docs/sol_skills/INDEX.md` and applicable source/commission procedures from the exact Mastermind commit. Reconcile current Macro/Terminal heads, open PR changed paths, active writers and holds. Obtain the required bounded current Steward/Executive projection when making operational responsibility claims. Preserve the existing workstream identity rather than spawning a duplicate program.

Create an adapter card for each first-vertical owner: canonical namespace/ID, current interface, authorization, version retention, clock semantics, correction behavior, response completeness, cost and exact active carrier. Prioritize layout, Thesis, W1-C, one real evidence owner and user-state mutation responsibility. Complete the remaining domain cards in their G8 tasks; they remain visibly unqualified until then.

Freeze ADR-01, inquiry/reference schema, owner-native retained layout interface, mutation result/error contract, evidence baseline completeness and permission policy. Qualify one approved authenticated principal and the later two-principal team proof without creating identities or privileges.

Read the actual migration authority at `supabase/migrations/RESERVATIONS.json`, its README and `scripts/check_supabase_migration_namespace.py`; reserve legal prefixes under that mechanism before creating SQL. This path is independently confirmed by the namespace guard, not an inferred location. Source: [namespace guard](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/scripts/check_supabase_migration_namespace.py).

**Done when:** signed owner/adapter matrix, contract fixtures, first-vertical Paper/reference packet, collision disposition and explicit production QA status exist. Unknown runtime means `SOURCE_ADMISSION_INCOMPLETE` for those claims; do not declare the field clear. Unavailable QA gates production acceptance but does not forbid safe source/test progress. Do not restart a broad research pass.

## G1 — Exact first commission: private retained Investigation and authenticated resume

**Product outcome:** a real user starts from Analysis or a named layout, records a question, attaches an admitted subject/layout and one owner-backed evidence baseline, leaves, and resumes the same inquiry through a fresh authenticated path without losing intent or confusing old and current evidence.

**Existing surfaces to inspect/reuse:** `terminal/lib/layouts.ts`, `workspaceLayout.ts`, `workspaceMigrate.ts`, `workspaceMenuOps.ts`, `terminal/components/LayoutMenu.tsx`, `TerminalShell.tsx`, `components/workspaces/AnalysisWorkspace.tsx`, `terminal/lib/theses.ts`, `savedViews.ts`, existing authentication and database/RPC patterns. Macro `engine/intelligence_workspace` and its schema/golden-vector discipline. S07–S16 document what was actually read in this audit; execution must inspect every touched file fully.

**Proposed new files:**

- Macro `contracts/intelligence_workspace/investigation_manifest.v1.schema.json`, `engine/intelligence_workspace/investigation_contracts.py`, `tests/test_investigation_contracts.py` for pure shared-contract validation if the existing contract authority confirms Macro ownership.
- Terminal `terminal/lib/investigations/contracts.ts`, `references.ts`, `repository.ts`, `mutations.ts`; `terminal/app/api/investigations/route.ts` and `[id]/route.ts`; `terminal/components/investigations/InvestigationLibrary.tsx` and `InvestigationShell.tsx`.
- Terminal `terminal/lib/__tests__/investigationsContract.test.ts`, `investigationsMutation.test.ts`, `investigationLayoutRetention.test.ts`; `terminal/e2e/investigations.spec.ts`.
- Prefix-reserved additive migration(s) for the admitted inquiry head/revision/receipt representation and layout-owner retention. The exact table/RPC names are frozen in G0; do not claim them as already existing.

**Interfaces:** `validateInvestigationManifest(input)` returns a typed manifest or explicit field errors. `applyInvestigationRevision(principal, action, id, expectedRevision, clientRequestId, content)` implements masterplan mutation semantics. `resolveInvestigationReference(principal, ref, temporalRequest)` returns a typed authorized resolution receipt. The layout owner exposes an admitted retain/read-by-version interface; Investigation never reads arbitrary database rows or stores layout config itself.

### Task G1.1 — Contract and negative vectors

- [ ] Add failing tests for strict keys, subject-owner mismatches, limits, unsupported versions, invalid pinned references and forbidden evidence/layout/AI blobs.
- [ ] Run the targeted suites and record the expected failures on the unimplemented contract.
- [ ] Implement pure validators and shared canonical golden vectors; keep existing v1 layout vectors unchanged.
- [ ] Run tests in both languages, compare the same fixture normalization/results, then commit only owned contract paths. Proof T01/T06.

### Task G1.2 — Atomic private mutation

- [ ] Add failing same-key replay, different-payload conflict, concurrent stale-write, rollback-between-steps and lost-response tests.
- [ ] Implement the existing-owner transaction/RPC path for authority, revision, head and receipt atomically; never a read-then-write correctness assumption.
- [ ] Preserve local drafts and the original operation identity during ambiguous outcomes; distinguish unavailable from empty.
- [ ] Prove unauthenticated/foreign reads and mutation receipt replay cannot cross ownership; commit. Proof T02–T05/T22.

### Task G1.3 — Retained layout and one real evidence baseline

- [ ] Add failing tests that mutate the live layout after capture and still recover the retained revision; reject nonexistent or unretained pins.
- [ ] Qualify or extend the layout owner's retention API, keeping its current row/config/revision unchanged on attach/open. Preserve strict/tolerant legacy migration behavior.
- [ ] Bind one admitted evidence owner with real version/clock/permission semantics. Capture a disclosed baseline vector, not copied fact payloads. An owner without retained evidence cannot serve as the supposedly retained positive-control baseline.
- [ ] Prove current layout updates cannot rewrite history; unavailable current evidence does not destroy the capture; commit. Proof T06–T08/T16.

### Task G1.4 — Small complete user path

- [ ] Use the accepted canonical Paper/reference design to build create, library, selected inquiry, revision/retention inspector, draft conflict and unavailable states.
- [ ] Wire actual Analysis/named-layout entry points with resolved subject context and correct return navigation. Reuse mobile Workspaces mechanisms; do not rebuild them.
- [ ] Run native tests with declared fixtures, then the authorized production create→readback→close→fresh-session reopen path. Verify exact question, subject, owner IDs, capture and retained layout revision.
- [ ] Capture responsive/locale/accessibility evidence, zero hidden operational writes, existing layout/Thesis/saved-view regressions and deployed identities. Proof T28–T30.

**G1 production DONE_WHEN:** T01–T08, T16, T22, T28–T30 pass for the slice; real principal receipt exists; the attached current layout remains unchanged; historical source capability is honestly displayed; the existing v1 migration/golden suite passes; no new alert, watchlist membership, portfolio mutation, Thesis publication, AI run or Prophet action occurs on reopen. Feature remains private-only. If production QA is unavailable, return `BUILT_NOT_PROVEN` with the exact remaining gate—not parent completion.

**Excluded from G1:** generalized bus, v2 composition, team collaboration, universal replay, automatic AI on reopen, universal evidence ingestion and new calculators. These exclusions sequence the work; they do not remove later program obligations.

## G2 — General resume and evidence change review

**Owner:** product/evidence adapter lane. **Depends:** G1 reference/capture contract.

**Surfaces:** proposed `terminal/lib/investigations/evidenceDiff.ts`, `capture.ts`; `components/investigations/EvidenceReview.tsx`, `ResumeSummary.tsx`; actual owner adapters and R10 projection. No new source corpus.

Build independent membership/version/qualification/availability/interpretation states. Bind diff generation to exact query/cohort, completeness and temporal policy. Implement changed-first library navigation, historical/current views, explicit baseline advancement and paginated history. Preserve current Paper's inventory/evidence/write separation and analytical-readiness guard.

Red-first tests include incomplete page versus real tombstone, different top-K query, stale/null versus zero, rights loss, same content/new transport timestamp, correction versus release, and failed refresh preserving the old baseline. **Done:** T14–T16, J01/J07 initial resume paths and real owner-backed change receipts pass. Ordinary outages cannot create a false “removed” or “unchanged” claim. Rollback hides new diff views, not saved history.

## G3 — Semantic linking and explicit contract evolution

**Owner:** context lane; one compiler/schema integrator. **Depends:** G0 frozen ownership; may progress in parallel with G2 after stable G1 contracts.

**Existing surfaces:** `terminal/lib/aiContext.ts`, `useChartBus.ts`, `chartBus.ts`, actual widget/TerminalShell adapters; Macro `engine/intelligence_workspace/context_compiler.py`, existing envelope schemas and gateway tests. Re-read exact current files and consumer registry before naming edits.

**Proposed surfaces:** `terminal/lib/investigations/contextSession.ts`, `contextAdapters.ts`, context inspector tests; `contracts/intelligence_workspace/workspace_context_session.v1.schema.json`. A negotiated Brain client/envelope successor extends the same compiler; names frozen with its owner. A layout composition successor, expected `workspace_layout.v2`, is introduced only for required new widget kinds/saved declarations through the existing layout owner and explicit migration.

Test first: loops, duplicates, old epochs, late subscribers, A→B→A, atomic underlying/expiry validity, pinned widget exceptions, duplicate symbols/multiple timeframes, localize preserving values, no receive→emit cycle, unsupported type refusal and request-aware receipt dedupe. Preserve all v1 security precedence results, including explicit prompt override and widget-owned pin semantics. Current inquiry subject never silently becomes a pin.

**Done:** T06/T10–T13 pass; actual UI receipts match effective state; v1 readers/export unchanged; new-version clients negotiate or refuse correctly; mobile needs no hover. Production proof demonstrates one security group and a materially different admitted domain group without a competing compiler/bus. Rollback disables new-version emission while preserving retained records and old readers.

## G4 — Temporal baselines, corrections and replay

**Owner:** temporal/domain lane. **Depends:** retained owner references and G2 evidence semantics.

**Proposed surfaces:** `terminal/lib/investigations/temporal.ts`, owner capability adapters, temporal inspector and replay tests; existing source/vintage readers remain canonical.

Implement capability negotiation and explicit knowledge-policy cutoffs. Use a fixture where a source observation is later corrected: replay before release excludes it, before correction uses the original vintage, after correction uses the revised vintage. Distinguish public availability from platform-known and user-captured state. Missing retained snapshots and current-only sources refuse honestly. Multi-owner captures carry version/coverage vectors, not an invented global timestamp.

**Done:** T17–T19 pass with fixtures and at least one real retained-vintage owner; the relevant J03/J04/J07 historical paths work. All unsupported owners remain explicit gaps on the adapter ledger. No alert, order, watchlist or live-only query is silently activated by replay. Rollback disables replay while leaving live/baseline/history readable.

## G5 — Formal hypotheses, contradiction and scenario reasoning

**Owner:** Thesis/domain-calculation owners with product lane. **Depends:** G2 evidence and admitted subject/calculate/retain interfaces; G4 where historical comparison is offered.

Extend the existing Thesis subject contract for required additional subjects through its canonical owner. Preserve user-only publication and immutable versions. Support multiple competing Thesis refs, attributed supporting/weakening/contradicting relations, unresolved interpretations, falsifiers and next-evidence requirements. Inquiry notes remain clearly authored notes, not a shadow Thesis lifecycle.

Bind scenario specs to concrete calculator/model versions, explicit assumption units and baseline references. Use existing valuation/options calculation owners; do not turn a scenario shell into a new financial engine. Persist result retention in the named owner, or show result reconstruction unavailable. Differentiate source fact, assumption, deterministic output, AI interpretation and decision.

**Done:** T20–T21 pass, including model-domain boundaries and source-column realistic fixtures; J03/J04/J05/J06 can compare the required hypotheses/scenarios or carry explicit unclosed owner work. No invented probability, confidence, ranking or investment authority. Rollback preserves existing Thesis and inquiry history, disables only unsupported new actions.

## G6 — Brain research artifacts and why-analysis-changed

**Owner:** existing Brain gateway/artifact owner. **Depends:** G2/G3 input semantics and G4 historical semantics.

Extend durable artifact retention beyond any insufficient run-buffer lifetime. Record actual used evidence and server context receipt, source versions, assumptions, omissions/degraded providers and observable run metadata. Keep old outputs dated; explicit current analysis creates a new artifact. Compare input manifests before prose and distinguish model variation from new evidence.

Red-first tests: deep provider down, truncated context, denied source, malicious instruction in retrieved evidence, changed evidence with unchanged user belief, old result opened without rerun and user-only proposal publication. **Done:** T12/T23/T25/T29 pass; J01 and J07 demonstrate current versus historical synthesis and a truthful change explanation. Existing deterministic facts and research history remain useful during AI outage. Rollback stops new artifact generation, not access to lawful existing history.

## G7 — Live/fixed sharing and safe forks

**Owner:** user-state/tenant owner with security reviewer. **Depends:** G1 retention and rights contracts; source/derived rights test designs start in G0.

Reuse teams/membership. Implement distinct actions for live inquiry, fixed manifest, fork and layout duplication. Fork exact source revision and detach mutable layout before editing. Check permission for references and derived artifacts at read/export/fork. Apply policies to revisions, heads, captures and mutation receipts; do not let old owner permissions bypass role demotion.

**Done:** T09/T22–T24/T31 pass on two approved real principals on a real team, plus foreign-user, role-change, revocation and entitled-source tests. Preserve existing #720 mobile/team workflow. No new paid account/team/invite is created solely to satisfy a test without explicit authority. Rollback disables sharing and invalidates access routes under current authorization without deleting private research.

## G8 — Complete all domain and downstream integrations

**Owner:** Astra integration with domain owners. **Depends:** the contracts each consumer actually needs; do not wait for unrelated waves.

Create one integration card per J01–J07 and D01–D16. Each card names the actual entry route, owner identity, contract/version, active carrier, evidence clocks/rights, source binding, saved/reopen behavior, Brain scope, scenario constraints, no-side-effect test and production gate. Refresh current Company Intelligence, Market Ontology, Prophet, Options, Vault, Theme, query, rating and alert surfaces; code-search absence is not global absence.

Integrate existing Analysis/Thesis/R10 first, then the remaining distinct domains. Preserve query/operator/threshold/units/cohort when saving a screen; do not silently filter them through savedViews. Licensed analyst-action data remains financial data, not user click history. Maintain all authority ceilings around ratings, Stage, Neural Web and Prophet. Preserve original sibling PR/carrier ownership, including Options #780/#686/#723 where still relevant.

**Done:** every journey executes its complete script, each downstream item has accepted implementation/consumer disposition or an explicitly authorized rights/scope decision, and no orphaned required feature is hidden under “adapter later.” Source-correct unavailable states are necessary but do not count as building a promised capability that remains unimplemented.

## G9 — Production hardening and end-to-end closeout

**Owner:** Astra CEO and independent acceptance reviewer. **Depends:** all required predecessor outcomes.

Run applicable repository broad checks, native contract/e2e/visual suites, authorized production journeys, cross-device continuation, source revocation, large-history/resource tests and rollback/restore rehearsal. Verify exact merged/deployed source identities and source-schema compatibility. Keep fixture, hosted CI and real production receipts separate.

Feature exposure advances private QA→controlled pilot→approved general release only on its actual gates. Record baseline metrics before claiming improved resumption. Failed human-task results reopen product design; no financial-outperformance claim follows from usability success. Operational runbook covers schema compatibility, broken references, retention expiry, unauthorized reads, ambiguous writes, source outages, data deletion, feature disabling and restoration without loss of immutable user history.

**Done:** T01–T32 applicable results and J/D coverage are independently accepted; zero hidden operational writes; no unowned critical blocker; current user-visible behavior matches the retained Paper/design contract. Update the original workstream and canonical capability/disagreement records. Do not close the parent on a first slice, pending PR, fixture green, unverified deploy or a supposed watcher.

## 3. Test and proof matrix

All rows below are required tests/receipts to be implemented or executed; **none is asserted newly passed by this audit**.

| ID | Discriminating test and required outcome | Primary gate |
|---|---|---|
| T01 | Strict manifest/shared vectors: unknown keys, wrong subject owner, excessive counts/bytes and forbidden fact/layout/AI blobs fail explicitly; valid Python/TS vectors agree | G1 |
| T02 | Same principal/op/key/payload repeated after success returns the exact original revision/result, including after head advances | G1 |
| T03 | Same key with different content/target/action returns idempotency conflict; cannot mutate or disclose another principal's result | G1 |
| T04 | Fault injection between revision/head/receipt steps leaves either the whole mutation committed or none; concurrent CAS has one valid advance | G1 |
| T05 | Lost response uses original-operation readback; stale edit preserves draft and current head; failed read is not empty and failed write is not success | G1 |
| T06 | Existing v1 import/export/golden vectors remain unchanged; invalid tolerant-read rows cannot be silently truncated on save; future-version writer fails safely | G1/G3 |
| T07 | Save/capture layout N, update live layout N+1, recover exact retained N; nonexistent/unretained pin rejected, not replaced by head | G1 |
| T08 | Inquiry attach/open changes no existing current layout config/revision; stale capture cannot be mislabeled with an older version | G1 |
| T09 | Fork source revision, edit fork layout, verify original inquiry/layout unchanged; denied dependencies remain denied | G7 |
| T10 | Cyclic ports/duplicate events/read-only subscribers/old epochs never loop; late subscriber starts from consistent current state | G3 |
| T11 | Rapid A→B→A and expiry changes cannot apply an older generation; pinned/local/multiple-timeframe exceptions remain stable | G3 |
| T12 | Existing v1 explicit→pin→active→ambient fixtures unchanged; new types negotiated by same compiler; receipt equals actual effective context and actual used inputs | G3/G6 |
| T13 | Saved inquiry subject does not auto-pin Brain; pin owner and unpin/localize semantics preserved; repeat requests at same context revision still update request-specific receipt | G3 |
| T14 | Incomplete/paginated/top-K/failed evidence reads never prove global removal; tombstone/complete comparable census can; scope changes disclosed | G2 |
| T15 | Null/stale/denied/not-applicable distinct from zero; qualified coverage cannot answer an under-specified comparison; incompatible units/cohorts refuse | G2 |
| T16 | Refresh failure/current source update does not mutate saved capture or baseline; explicit review creates a new capture/revision with completeness | G1/G2 |
| T17 | Known-at fixture excludes future release and future correction; public-known, platform-known and user-seen policies do not collapse | G4 |
| T18 | Current-only owner in replay shows historical unavailable; no hidden fallback to today's value; disclosed live comparison stays outside replay receipt | G4 |
| T19 | Corrected source history and retained layout/evidence vectors reconstruct the stated version or explicitly fail; hash-only reference cannot claim retention | G4 |
| T20 | Formal hypothesis uses current/extended Thesis subject contract; prior versions/falsifiers survive; AI proposal never publishes; conflicting hypotheses remain distinct | G5 |
| T21 | Scenario assumptions are unit-typed and versioned; output uses exact real owner field/model schema; no scenario→fact, no fabricated missing output or confidence | G5 |
| T22 | Direct foreign/anonymous head/revision/capture/receipt reads and writes denied; authorization is checked again on idempotent replay | G1/G7 |
| T23 | Revoked source rights cannot leak through AI prose, preview, title/count, export, cache or fork; metadata only where policy permits | G6/G7 |
| T24 | Live share advances appropriately; fixed manifest stays fixed but rights remain current; demotion/removal/revocation and private/team isolation proven | G7 |
| T25 | Retrieved prompt injection cannot change precedence, grant rights, issue operations or expose secrets; token truncation and filtered inputs are visible | G6 |
| T26 | Benchmarks state device/network/sample/warm-cold/size; bounded manifest, large history, 12-widget case, cancellation and local fanout meet accepted budgets or expose measured blockers | G9 |
| T27 | Cache/query dedupe partitions principal/rights, owner/query/context/time/version; logout, account switch and revoked access cannot reuse unauthorized entries | G2/G9 |
| T28 | Actual host themes, EN/ZH, desktop/tablet/390 and 320 CSS-pixel reflow, 200% text resize, keyboard/screen-reader/touch and recovery/focus tested; no hover-only provenance | All UI gates |
| T29 | Reopen/refresh/replay/history/AI-artifact read produce no alert, trade, portfolio/watchlist mutation, Thesis publication, scenario execution or Prophet promotion | All gates |
| T30 | Real approved principal creates, reads back, closes and resumes in fresh browser/session and second-device path; exact inquiry/capture/owner identity restored | G1/G9 |
| T31 | Two approved real principals on one real team prove share/read/fork and current role/entitlement changes; fixtures cannot discharge this receipt | G7 |
| T32 | Exact merge/deploy identity and contract floors, additive migration, backup/restore/feature-off recovery and canonical workstream closeout proven | G9 |

### Command and evidence discipline

For newly proposed suites, task-level commands are: in Macro, `python -m pytest tests/test_investigation_contracts.py`; in `terminal/`, `npx vitest run lib/__tests__/investigationsContract.test.ts lib/__tests__/investigationsMutation.test.ts lib/__tests__/investigationLayoutRetention.test.ts`, then `npx tsc --noEmit`, and `npx playwright test e2e/investigations.spec.ts` with the repository's current required project/environment configuration. These are future commands for proposed files, not results from this audit. Read current package scripts, test discovery and nearer guides before running; register tests in the canonical CI owner rather than a new workflow.

Each implementation task records RED evidence, minimal source repair, GREEN evidence, independent review and the exact tested head. Run current required broader suites and legacy regressions, not only new tests. For SQL, test actual RLS/RPC paths in an isolated approved database as well as application adapters; fixtures that bypass policy cannot prove policy. For production, record authorized identity scope without credentials, time, route, exact deployed sources, owner/capture versions and discriminating readback.

## 4. Final acceptance packet

Astra's final return contains: updated capability and disagreement ledgers; all admitted owner cards; source/contract/migration versions; J01–J07 and D01–D16 coverage; T01–T32 proof index; independent review decisions; actual merged and deployed identities; real authenticated and two-principal receipts; current performance/resumption findings with limits; rollback/retention/rights runbook; and exact residuals with authorized disposition.

`PROVEN_LIVE` is scoped to the tested capability and route. A remaining rights-gated domain, absent historical retention or unavailable QA principal is stated plainly and never converted into a fake green. Keep the parent program active until its agreed outcomes are accepted or the actual authority explicitly changes the scope.
