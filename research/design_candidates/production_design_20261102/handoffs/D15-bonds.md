# D15 — Bonds, credit and cross-asset transmission

**Copy this entire file into the receiving Astra Pro session.** Commission date: 2026-11-02; audit observations span November 2–3 UTC. Read the linked source package if supplied separately.

Your assignment is **D15** within the existing Mastermind whole-site design makeover. Explain yield-curve and credit moves, their competing mechanisms and their transmission into other markets.

**Priority / starting decision:** Retain Bonds/Transmission R32 and reconcile stale labels and shell styling.

**Dependencies:** F01 F02. **Named collaborators:** D02 D12 D16. Source-level consultations in your route rows also apply.

**Proposed Paper location:** 20 Markets; MM · Bonds & Transmission. These names are proposals. Destination IDs are pending creation or verified reuse; no file has been moved by this audit. Separate reference archives from current working files.

## Read these source-bound instructions

- [Programme / draft PR](https://github.com/mastermindx-market-intelligence/macro/pull/10617)
- [Audit report and current index](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/README.md)
- [Common session requirements](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/COMMON_SESSION_BRIEF.md)
- [Organization and archival rules](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/ORGANIZATION_RULES.md)
- [Shared-shell contract requirements](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/SHARED_SHELL_CONTRACT.md)
- [Product/build contract template](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/templates/PRODUCT_BUILD_CONTRACT.md)
- [Re-audit acceptance checklist](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/RE_AUDIT_CHECKLIST.md)

The audit pins are Mastermind `7f1242bfa90f0f0448e66e400e054bd5aa5fa15a`, initial Macro `5234bf95bfe8cf0b72ed5da29afec1fb43f0f4e0`, fresh Macro source delta `143bdfe08ac2444fde9fcb2263aa0c1d3d03dcc0`, and Terminal `e0ae63e43965ec1d1c93405ee903fd92b63e3470`. Refresh only relevant drift at launch. Record the exact source/package revision you actually use.

## Preserve and reuse

Main p-1H-0 contains Bonds R32 despite R18–R25 title; 63GL-1 Bonds Desk and 6885-1 start. p-1E-0 Transmission R32 includes 64G1-1. Preserve chart-led interpretation, what-next conditions and competing mechanisms; old p-O-1/pre-R30 archive supply retention evidence.

## Required improvements and decisions

Compose the strong content inside the new shell and align local navigation. Remove legacy global header and colored accent stripes through the current system. Explain bond/credit mechanisms and uncertainty without surrounding every answer with equal-weight diagnostics. The internal credit-desk mockup stays an input, not an automatically published product.

## Complete these user journeys

1. Yield/credit move → inspect curve or spread → compare mechanisms → follow FX/equity transmission → return.
2. Open a stale or mismatched yield/credit snapshot → preserve evidence clocks and explain uncertainty.

## Product, backend and build obligations specific to this assignment

Map instrument/maturity/curve definitions, yields versus prices, basis points versus percent, benchmark conventions, spread methodology, source calendars and revision times. Transmission claims need source-backed causal qualification; juxtaposition is not proof.

**Existing source starting points:** templates/bonds.html.j2, templates/transmission.html.j2 and actual builders; assigned credit mockup source must be resolved.

**Known work and boundaries:** D02 owns macro summary, D16 FX pair investigations, D12 strategy evidence. Keep one owner for the shared transmission schema.

## Exact Paper starting references

| File / page | Exact identity | Boards | Observed role |
| --- | --- | --- | --- |
| [MASTERMIND PAGES — ARCHIVE · Bonds + Transmission · pre-R30](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1Y-1) | 01M2WGNCX9475G79JRKJTCM08P / p-1Y-1 | 28 | historical archive label; verify lineage before moving |
| [MASTERMIND PAGES — Bonds · Advanced Mechanism & Decision Studies · R18–R25](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1H-0) | 01M2WGNCX9475G79JRKJTCM08P / p-1H-0 | 12 | candidate/workspace; approval evidence not inferred |
| [MASTERMIND PAGES — Cross-Asset · Bonds × Forex Transmission & Confluence · Studies](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1E-0) | 01M2WGNCX9475G79JRKJTCM08P / p-1E-0 | 11 | candidate/workspace; approval evidence not inferred |
| [MASTERMIND PAGES — Bonds · Decision Workspace · R1 · 2026-09-26](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-O-1) | 01M2WGNCX9475G79JRKJTCM08P / p-O-1 | 29 | candidate/workspace; approval evidence not inferred |

The full artboard ID/name/dimension list is in [paper-artboards.json](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/census/paper-artboards.json). Board ownership overrides page custody for WTI references. These are observed inputs, not new RIG approvals. Re-read exact targets before modification.

## Assigned canonical routes

| Canonical ID | Route/family | Lifecycle / access | Source / common owner | Consult |
| --- | --- | --- | --- | --- |
| macro:mockup_ccw_credit_desk | /_mockup_ccw_credit_desk.html | internal / unknown | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:bonds | /bonds.html | live / anonymous | templates/bonds.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:transmission | /transmission.html | live / anonymous | templates/transmission.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |

For exact builders, source evidence, governed regions, known gaps and route-specific access dispositions read [route-ownership.json](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/census/route-ownership.json). A family row covers generated instances. Preserve their exact identity/URL contracts and qualify representative edge cases; do not create one redesign session per generated document.

## Execution and return contract

Use bootstrap-mastermind and paper-design-workflow at launch. Read the current protected INDEX and required procedures at one verified SHA; record it. This is a Chairman-authorized **design and specification** assignment. The user will launch these sessions and later request re-audit before product implementation. Work through the entire assigned scope; do not stop at a desktop mockup or a plan. Do not launch other product sessions, implement or roll out product code, or merge this wave's documents as a substitute for review. P00 may prepare an existing-adapter repair and carry its original-owner review/deployment path only where current authority and runtime admission actually cover that action; otherwise return the concrete fix and named dependency.

The audit's Paper reads worked, but writer qualification was false. P00 must resolve that exact original-owner schema gate before edits. Continue useful reading, retention analysis and source/specification work while it remains blocked. Never bypass a denied or uncertain action through another tool/carrier. Coordinate known writers at exact board/node scope, not with an invented file-wide lock. Re-read your assigned source/Paper targets and overlaps for drift; do not repeat the entire census.

Resolve the package branch once at launch and read this brief, COMMON_SESSION_BRIEF, ORGANIZATION_RULES, crosswalks and acceptance checklist from that same immutable commit. Record it; do not mix moving branch revisions. F01/F02 later contract releases are separately versioned inputs. Foundation sessions develop/freeze their joint contract without waiting for their own unpublished output; domain sessions consume it for final compositions. You can begin source/product/data work beforehand. Use existing domain workstreams and the whole-estate charter; do not invent a new umbrella programme. Preserve actual review/worker admission rules, holds and rejection evidence.

Required outputs for product/design sessions:

1. Product description, primary user/job and complete normal-data journey; new feature proposals labeled separately.
2. A feature ledger covering the existing site and Paper: RETAIN, IMPROVE, RELOCATE, REMOVE or BLOCKED_DATA. Relocations need reachable destinations; removals need a valid product decision; blocked data needs an actual owner and interim behavior.
3. Editable, shell-composed references with intentional typography, meaningful charts/tables, deliberate mobile hierarchy and all primary tasks. Preserve strong existing work. Every materially changed shell, hierarchy or interaction needs an editable Paper composition; source captures only support evidence. Unchanged actually approved references can be reused. Screen names/counts and captured screenshots are not approval.
4. Interaction and state contracts with actual copy, route/query/hash behavior, keyboard/touch/focus/scroll, loading/empty/partial/stale/error/access and pending/failed/uncertain saves. No silent mutation on navigation/context change.
5. Backend/data/structure instructions identifying real producer/API/schema and source files; entity/listing keys, units/currency, observation/publication clocks, cache/refresh, null/zero/unknown, access, write owner and readback. Mark proposed/unresolved interfaces honestly; never invent a live endpoint or validated model claim.
6. Builder plan: source templates/components, reuse/replacement, shared-template boundaries, migration compatibility, implementation sequence, acceptance cases, performance/accessibility targets, rollout/rollback and unresolved dependencies.
7. In-Paper Read me / Build contract page plus concise annotations adjacent to important controls; full durable contract in the source package. Return exact Paper IDs/URLs, source commit/PR, shell/system versions, before/after evidence, feature dispositions, review findings and remaining owners.

Evaluate 320/390/tablet/narrow/wide content classes using the real shell and inspector widths, not only standalone 1440px screens. Show light/dark, EN/ZH, meaningful focus/keyboard/touch and zoom/reflow coverage. Use a 44px house target for important mobile controls; do not misstate it as WCAG AA's 24px minimum/spacing rule. Avoid colored container borders/accent stripes under current doctrine. Future performance targets are LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 at p75; no current measurements are asserted.

Freeze the candidate by recording exact Paper IDs/time and committing supported exports/captures, annotations/specifications and verification screenshots as an immutable source artifact set with the required SHA/digests. A Paper snapshot guard or token hash is not a document revision or approval identity. Review the committed set; later canvas changes require affected evidence and review to be refreshed.

Seek independent product-regression and visual/taste critique. The first pass receives ONLY user/business job, production-before artifact, proposed-after artifact and capability/task manifest. Reveal rationale, constraints and data limitations only after first-pass findings freeze, then record amendments. Use actual RIG states and receipts; a designer cannot self-approve their reference. Close each inherited blocker/condition with the existing RIG continuity disposition. Reference acceptance, implementation, deployment and served-production proof remain separate. P00/F03/QA01 apply relevant requirements to their capability/organization/review deliverable rather than manufacturing screens. BLOCKED_RETURN/PARTIAL is recoverable progress, never successful qualification or applied organization.


## Done means

A qualified R32 successor, full shell/phone/tablet/state compositions and a precise bond/credit/transmission build contract with all useful mechanisms retained.

Return a concrete completed artifact and evidence package. If a necessary dependency remains, identify the exact blocked action, what you completed, the owner and the minimum next evidence needed; do not substitute a broad claim that the whole design task is blocked.
