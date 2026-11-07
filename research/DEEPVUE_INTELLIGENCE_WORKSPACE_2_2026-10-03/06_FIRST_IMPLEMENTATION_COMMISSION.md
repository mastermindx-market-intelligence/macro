# Intelligence Workspace 2.0 — First Implementation Commission

> **For agentic workers:** Execute this bounded plan with current protected Mastermind procedure and applicable test-driven-development/executing-plans skills. A worker consumes a lawful live assignment; discovering this document does not self-assign work.

**Goal:** A signed-in user can save a research question from an existing named chart layout, read back exactly what was committed, and reopen the same question and immutable layout reference on a second device—even when Brain is unavailable.

**Architecture:** Extend existing Terminal user services with a small Investigation head/revision contract; retain `chart_layouts` as layout owner and add immutable layout-owner snapshots. Use current authentication, tenancy, migrations and request-outcome patterns. No evidence bodies, Thesis duplication, automatic alerts or new database/service.

**Tech stack:** Current Terminal Next/React/TypeScript/Supabase/Vitest/Playwright; Macro Python/JSON schemas and shared golden vectors. Do not upgrade frameworks or install a new state-management/collaboration stack for this slice.

**Spec:** [03_MASTER_ARCHITECTURE.md](03_MASTER_ARCHITECTURE.md), [04_UX_JOURNEYS_AND_PAPER.md](04_UX_JOURNEYS_AND_PAPER.md), [05_BUILD_PROGRAM_AND_ACCEPTANCE.md](05_BUILD_PROGRAM_AND_ACCEPTANCE.md).

## Commission identity and boundary

Existing workstream: `WS:DEEPVUE-INTELLIGENCE-WORKSPACE`.

Suggested bounded task label: **IW2-P1 private-question-reopen**. This is not an allocated Executive Job/Attempt or a recorded START. At pickup, the current assignment/organization/runtime owners establish the actual operation identity and source custody. Reuse any existing matching admitted task rather than minting a duplicate.

Program principal: the Astra CEO to whom the Chairman deliberately delivers the launch prompt. Builder: current Terminal user-services/layout capability, selected through admitted capacity. Independent review: transactional/RLS and cross-owner contract review, separate from the builder. `WHY NOT FABLE`: this first slice is bounded after the principal freezes the ownership and transaction decision; scarce principal-builder capacity is unnecessary unless a concrete unresolved owner conflict emerges. No generic Codex/Work or metered route is authorized by this document.

## Global constraints

A question can exist without a Thesis or AI answer. Save must preserve exact question text and typed subject/reference meaning. Existing layout-only, `mm.ws`, saved RMS filters, Thesis history and team-layout behavior remain separate and usable.

Do not store the new payload under `rms_saved_view.*`; the current serializer only preserves four filters. Do not turn `workspace_layout.v1` into an Investigation object or loosen closed v1 validators. Do not use a mutable layout name or CAS integer as historical identity.

All writes use server identity, current CSRF/origin checks, bounded validation, expected-head CAS and operation identity. Unknown effect is not failure. Reopen and evidence reads perform zero Thesis/alert/portfolio/trade mutations. No production DDL or principal/team mutation without the current approved owner gate.

## Review focus

The critical negative cases are commit-success/response-loss; a layout being saved concurrently; a foreign principal attempting to attach/read a layout; old clients writing a reduced schema; and unsupported/oversized input being silently dropped. Every case has a test below.

## Entry gate — bounded P0 closure

Before code effects, re-pin current repositories/procedures and resolve source custody. Fresh-read the exact responsibility: the research run's Steward result was stale/degraded. Confirm no newer general-question owner invalidates the proposed aggregate. Freeze the owner decision and inspect the current migration reservations and existing route-group placement.

Reserve an isolated existing-owner workspace/branch through current procedure. Proposed file paths below may be adjusted once to the verified route/test conventions before implementation; record the exact final manifest. Do not create a parallel AppShell/navigation/auth flow. A missing production QA principal does not block safe local/schema work, but remains a production acceptance hold.

## Task 1 — Closed contracts and lossless reference vectors

**Create in Macro:**

```text
contracts/intelligence_workspace/investigation.v1.schema.json
contracts/intelligence_workspace/investigation_revision.v1.schema.json
contracts/intelligence_workspace/fixtures/investigation_vectors.json
tests/test_investigation_contract.py
```

**Create in Terminal:**

```text
terminal/lib/investigationContracts.ts
terminal/lib/__tests__/investigationContracts.test.ts
```

These are proposed new files. Preserve current owner naming conventions when finalizing the manifest; do not duplicate an existing schema with a second name.

**Interface:**

```text
validateInvestigationManifest(raw: unknown)
  -> { ok: true, value: InvestigationManifest }
   | { ok: false, errors: ValidationError[] }
```

The manifest contains intent, typed owner references, exact layout revision reference, optional reviewed baseline reference and continuation. For the first slice, evidence state can be explicit `no_baseline`/`not_yet_qualified`; it must not display “no changes” or a completed synthesis. All broader fields remain versioned and closed under the master contract; no untyped `metadata` escape hatch.

- [ ] Write failing tests for exact Unicode round trip, 160-character title, 2,000-character question, 16 subjects, 4 layout refs, 128 active evidence refs and 64 KiB serialized manifest. Define character limits as Unicode scalar values and reject invalid surrogate sequences so Python/TypeScript agree.
- [ ] Add vectors for unknown fields, wrong types, malformed dates, forged privileged provenance/author/scope, duplicated refs, unsupported owner/kind, invalid digest and each limit plus one. A rejection leaves the supplied original bytes available for recovery.
- [ ] Run the new schema/vector tests and record expected failures before implementation.
- [ ] Implement pure validation and paired schema/vector conformance. Use owner-qualified fixture references; do not invent real source identities.
- [ ] Run both languages against the same vectors; compare canonical semantic output and reject mismatches. Commit the contract slice with its test evidence.

**Unlock:** a stable typed boundary for storage and UI, without a new runtime service.

## Task 2 — Transactional private save and immutable layout reference

**Modify:** existing `terminal/lib/layouts.ts` and current user-services write/RLS patterns. **Create:** `terminal/lib/investigations.ts`, `terminal/lib/__tests__/investigations.test.ts`, approved migration(s) under the freshly reserved prefix and database integration tests in the existing harness. No fixed migration number is assigned here.

**Interfaces:**

```text
commitInvestigation(command: InvestigationCommand, actor: ServerActor)
  -> Promise<CommitOutcome>
readInvestigation(id: UUID, actor: ServerActor, revisionId?: UUID)
  -> Promise<InvestigationReadResult>
readInvestigationOperation(operationId: UUID, actor: ServerActor)
  -> Promise<OperationReadResult>
```

Server outcomes are applied/replayed/conflict/rejected or an owner-supported pending result. `pending_unknown` is the client/transport state when the result is not known; it must not be written as a fabricated terminal database outcome.

- [ ] Write failing transactional tests: create commits exactly one identity/revision; same operation/payload replays the same result; same operation/different body rejects; stale expected head cannot overwrite; cross-actor operation lookup reveals nothing.
- [ ] Write the layout-history test: capture config A, save layout B, reopen the Investigation and obtain immutable A by revision UUID/digest. Add delete/recreate-same-name ABA protection and current layout-save race cases.
- [ ] Write RLS tests: user A cannot read or attach user B's private layout; client-supplied tenant/author is rejected; a private Investigation is not team-visible by default.
- [ ] Implement the same-owner transaction that captures/validates an immutable layout revision and commits the Investigation reference, or records a clear conflict. No read-before-write “probably unchanged” shortcut. The current `chart_layouts` head remains its owner.
- [ ] Test rollback after each transaction stage. No head may reference an uncommitted/missing revision. Enforce object caps transactionally. Keep future source rights checks at read time as well as attach time.
- [ ] Inject response loss after commit. Operation readback must recover the one committed result. A not-found/timeout that does not prove terminal non-application cannot authorize a blind new effect.
- [ ] Run actual PostgreSQL/RLS integration tests in the approved environment, not only in-memory fixtures. Obtain independent review of policies, atomicity and rollback before merge/deploy gates.

**Unlock:** actual persistence and historical visual identity, not only a serializer.

## Task 3 — Existing-BFF route and useful private UI

**Create proposed routes:** `terminal/app/api/investigations/route.ts`, `terminal/app/api/investigations/[id]/route.ts` and owner-consistent revision/operation-read routes. Add the Investigation page inside the verified existing authenticated shell route group.

**Create UI:** `terminal/components/workspaces/InvestigationWorkspace.tsx`, a bounded save-question dialog and resume header. **Modify:** current LayoutMenu/Workspace menu operation seam and Analysis entry, not a new navigation system.

**Interfaces:** the client only consumes `InvestigationReadResult`, `CommitOutcome` and qualified owner display adapters. Server actor/provenance/rights never come from client input.

- [ ] Write route tests for auth/CSRF, size, exact request ID, unknown-write recovery, error versus empty and unsupported schema. Confirm fixture bypasses cannot be enabled in production.
- [ ] Write the first browser test before UI code: open an existing layout → Start investigation → enter question → Save → exact readback shows the same text/subject/layout revision → navigate away → reopen.
- [ ] Add Brain-unavailable and source-qualification-pending cases. The saved question remains useful; “No reviewed baseline yet” is explicit. No generated answer is required for saving.
- [ ] Implement the dialog, saved/readback status, question/resume frame and existing owner-backed chart view. Preserve original source/return links. Do not show generalized linking, scenarios or sharing as working before their waves land.
- [ ] Add conflict UI with compare/reload/fork choices and a separate uncertain-write recovery panel. Never dismiss an unknown result as “nothing saved.”
- [ ] Add 1440/820/390/320 layouts, EN/ZH/long text, keyboard/focus return and non-hover actions. Existing Save layout remains distinct from Save investigation.
- [ ] Run route/unit/browser/build tests and commit the integrated private vertical slice.

## Task 4 — Authenticated acceptance and return to the program

**Create:** `terminal/e2e/investigation-reopen.spec.ts` and current evidence-home receipts. Fixture and real authenticated modes must be separately labeled.

- [ ] Prove approved principal A creates, exact-reads and reopens on a distinct authenticated client/device context. Record source head, deployed identity, safe principal identity and actual actions.
- [ ] Prove legacy named-layout save/rename/duplicate/export/import/stale-write/fork remains intact for the exercised paths; original-byte export is recoverable for unsupported legacy input.
- [ ] Prove principal B cannot read A's private Investigation/reference. This negative isolation test does not substitute for P6's actual team share/read journey.
- [ ] Spy/inspect zero alert/portfolio/trade/Thesis writes during create-question, open, refresh and reopen. Only the explicit Investigation/layout transaction is allowed.
- [ ] Exercise response-loss recovery and concurrent layout/head edits. Confirm the persisted question/reference vector is exact, not merely visually similar.
- [ ] Obtain independent exact-head review; resolve critical/important findings; perform approved release and re-pin served identity before claiming live proof.
- [ ] Return the evidence packet to Astra with the next P2/P3 dependencies. Do not close the whole Workspace 2.0 program after this slice.

## Verification commands

```sh
# Terminal; these are proposed new tests to be implemented, not existing passing tests.
cd terminal
npm test -- lib/__tests__/investigationContracts.test.ts lib/__tests__/investigations.test.ts
npm run test:e2e:responsive -- e2e/investigation-reopen.spec.ts
npm run build

# Macro, from its repository root and approved environment.
python -m pytest tests/test_investigation_contract.py -q
```

Also run current mandatory migration/namespace, lint and CI checks. Capture actual failures and results, not only command names. Do not spend the turn claiming completion from tests that were never executed.

## Exact DONE_WHEN

The first commission is done only when the new capability exists in its approved deployment and the following are evidenced:

1. The saved question, subject refs and immutable layout revision survive exact readback and a second authenticated device/client reopen.
2. Saving/reopening works with Brain unavailable and without a Thesis; absent baseline/qualification is disclosed.
3. Same operation does not duplicate, stale head does not overwrite, uncertain effect is recoverable, and the layout/history transaction is atomic.
4. Cross-account access and privileged-client field injection are denied; old layout/guest/menu behavior and original recovery exports are preserved.
5. Reopen has no alert, portfolio, trade or Thesis effects; responsive/EN/ZH/keyboard paths pass their scoped tests.
6. Exact source/deploy/test/review evidence and remaining program dependencies are returned and read back through the existing continuation owner.

If real production authentication is unavailable, report **BUILT_NOT_PROVEN**, the precise missing principal/environment gate and completed independent evidence. Do not rewrite DONE_WHEN, claim guest/fixture proof as authenticated proof, or block unrelated safe P2/P3 contract work. This is the critical first product outcome, not the end of the project.
