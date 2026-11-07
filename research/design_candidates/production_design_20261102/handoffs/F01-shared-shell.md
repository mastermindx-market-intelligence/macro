# F01 — Shared shell, navigation and investor information architecture

**Copy this entire file into the receiving Astra Pro session.** Commission date: 2026-11-02; audit observations span November 2–3 UTC. Read the linked source package if supplied separately.

Your assignment is **F01** within the existing Mastermind whole-site design makeover. Give users one elegant, legible way to move between market workspaces while preserving exact instrument, region, research and return context.

**Priority / starting decision:** Foundation. Deliver a small frozen shell contract early so product designers can compose concurrently.

**Dependencies:** P00 for edits; F02 handshake. **Named collaborators:** D01 D06 D23 D25 D26 D27. Source-level consultations in your route rows also apply.

**Proposed Paper location:** 01 Foundations; MM · Shared Shell. These names are proposals. Destination IDs are pending creation or verified reuse; no file has been moved by this audit. Separate reference archives from current working files.

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

Retain Today, Discover, Analysis, Monitor, Research and Portfolio as the current job-based IA baseline pending a task-based evaluation. Retain separate region/market context, global search, All Tools, account/preferences and focused Terminal mode. Reuse the completion/state work on MASTERMIND PAGES p-23-0, including Today 6NMP-0, Monitor 6NR1-0, Research 6NTA-0, Search 6NVJ-0, focused Terminal 6O5H-0 and state contracts 6PNC-0. p-18-0 contains investor-overview candidates. Mastermind OS p-F-0 is a moved notice, not a competing investor-shell owner.

## Required improvements and decisions

Create a much more refined product identity and navigation hierarchy, with deliberate spacing, typography, interaction feedback and content width. The live All Tools drawer has 291 entries, long machine-like labels, duplicate-looking labels and 182 ungrouped entries in the source projection. Define short names, aliases, groups, breadcrumbs and a distinction among navigation, entity search and actions. Show one unambiguous selected destination plus region context; do not recreate the live Today/US simultaneous emphasis. Resolve rail versus expanded navigation using complete tasks, not icon aesthetics alone. Compare two bounded visual directions against existing strong work, then freeze one. Do not make every child workspace redesign the shell.

## Complete these user journeys

1. Today → US market → Company → focused Terminal → return to the exact prior page, query, selection and scroll.
2. Open All Tools → search by user term or alias → distinguish same-label destinations → open a deep link.
3. Switch US to China while research is open → show actual regional availability → retain correct listing identity and avoid relabeling old cached data.
4. Open account/help/search/inspector by keyboard → close with Escape → restore focus; repeat on a phone and at zoom.

## Product, backend and build obligations specific to this assignment

Publish versioned shell geometry, content-container breakpoints, header/rail/drawer variants, local-tab and inspector slots, focus/scroll/history ownership, route/region identity, auth/access states, theme/locale persistence and inter-frame handshakes. Context selection must not save preferences or alter holdings/watchlists. Preserve exact URL query bytes and release-generation consistency. State whether each element is shell-owned, domain-owned or a public/internal variant.

**Existing source starting points:** Terminal: terminal/components/chrome/AppShell.tsx; terminal/lib/sharedShellNavigation.ts; terminal/components/chrome/shared-shell/ShellDirectory.tsx; terminal/lib/sharedShellContracts.ts; terminal/components/chrome/shared-shell/SharedShellPresentation.tsx; terminal/lib/sharedShellRoutes.generated.json. Preserve the focused /terminal chart chrome and Brain singleton instead of nesting AppShell around it.

**Known work and boundaries:** Terminal #1188, #1191, #1226, #1228 and #1236 are existing overlap candidates. #7949 is merged historical work. Preserve active effects; open PR does not prove a live writer. Route admission remains the existing registry/export owner’s responsibility.

## Exact Paper starting references

| File / page | Exact identity | Boards | Observed role |
| --- | --- | --- | --- |
| [MASTERMIND PAGES — Shared Shell · Completion & Integration · R1](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-23-0) | 01M2WGNCX9475G79JRKJTCM08P / p-23-0 | 17 | candidate/workspace; approval evidence not inferred |
| [MASTERMIND PAGES — Shared Market · Search + Comparison · Reference](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1S-0) | 01M2WGNCX9475G79JRKJTCM08P / p-1S-0 | 18 | reference; approval evidence not inferred |
| [MASTERMIND PAGES — Shared Market · All Tools + Research Launcher · Reference](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1R-0) | 01M2WGNCX9475G79JRKJTCM08P / p-1R-0 | 16 | reference; approval evidence not inferred |
| [MASTERMIND PAGES — Investor Shell · Market Overview · Design Candidates](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-18-0) | 01M2WGNCX9475G79JRKJTCM08P / p-18-0 | 3 | candidate/workspace; approval evidence not inferred |
| [MASTERMIND PAGES — Mastermind · Shared Shell · Review 01 · 2026-09-24](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-D-0) | 01M2WGNCX9475G79JRKJTCM08P / p-D-0 | 11 | candidate/workspace; approval evidence not inferred |
| [Terminal — 10 · Retained Shared Shell · Stocks + Setups](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-E-0) | 01M3NSZGE8JWN2EZCSF0DT05RM / p-E-0 | 8 | candidate/workspace; approval evidence not inferred |
| [Mastermind OS — ARCHIVE · Market Shell References · Not for OS Build](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-G-0) | 01M3NRCX55B452A12819WNE1RH / p-G-0 | 37 | historical archive label; verify lineage before moving |
| [Mastermind OS — 14 · Investor Shell · Production Candidate · 2026-10-08](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-F-0) | 01M3NRCX55B452A12819WNE1RH / p-F-0 | 1 | move/redirect notice; preserve successor linkage |

The full artboard ID/name/dimension list is in [paper-artboards.json](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/census/paper-artboards.json). Board ownership overrides page custody for WTI references. These are observed inputs, not new RIG approvals. Re-read exact targets before modification.

## Assigned canonical routes

| Canonical ID | Route/family | Lifecycle / access | Source / common owner | Consult |
| --- | --- | --- | --- | --- |
| terminal:legacypath | /<legacyPath> | live / unknown | terminal/app/(shell)/[...legacyPath]/page.tsx; assigned session; inspect actual shared imports before implementation | F02, F03 |
| terminal:dev_workspaces | /dev/workspaces | dev_only / unknown | terminal/app/dev/workspaces/page.tsx; assigned session; inspect actual shared imports before implementation | F02, F03 |

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

A reviewed shell v1 with desktop/compact/phone/focus/public/internal compositions, complete navigation taxonomy, measured content slots, state contracts and at least three demanding domain compositions (Macro, Company, Options). It must be usable by D01–D27 without inventing local global headers.

Return a concrete completed artifact and evidence package. If a necessary dependency remains, identify the exact blocked action, what you completed, the owner and the minimum next evidence needed; do not substitute a broad claim that the whole design task is blocked.
