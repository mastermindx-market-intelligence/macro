# D02 — Macro regimes, breadth, risk and market events

**Copy this entire file into the receiving Astra Pro session.** Commission date: 2026-11-02; audit observations span November 2–3 UTC. Read the linked source package if supplied separately.

Your assignment is **D02** within the existing Mastermind whole-site design makeover. Explain the current macro regime, its supporting evidence and what would invalidate it, with clear paths into affected assets.

**Priority / starting decision:** High-impact flagship redesign and source-truth cleanup; preserve the existing analytical depth.

**Dependencies:** F01 F02. **Named collaborators:** D01 D10 D15 D19 D21 D25. Source-level consultations in your route rows also apply.

**Proposed Paper location:** 20 Markets; MM · Macro Overview, MM · Macro Systems, MM · Risk & Events. These names are proposals. Destination IDs are pending creation or verified reuse; no file has been moved by this audit. Separate reference archives from current working files.

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

Live /macro.html includes regime score, 60-session path, market strip, actions, calendar, policy and sentiment. Preserve the trend-versus-stress-versus-positioning distinction in Risk Radar; use Market Dashboard Popups and p-13-1 breadth as existing references. The current mobile first fold is dominated by gauge/metadata while the path chart falls below it.

## Required improvements and decisions

Make the main regime answer and its evidence visually connected; compress status scaffolding and reveal deeper mechanisms progressively. Recompose for actual shell content width. The observed Fed panel says both “Cut expectations rising now” and “Market prices ~2 hikes over next 12m”; identify producer/clock/wording conflict, not merely restyle it. A Paper Risk Radar prominently shows 13% model probability while calibration is unverified: specify qualified versus unqualified presentation and route the validity dependency to the model owner. Never cosmetically certify a number.

## Complete these user journeys

1. Macro change → supporting indicator/history → affected asset/sector → exact company/chart evidence.
2. Risk alert → understand which risk axis changed → inspect missing/stale/calibration status → save a condition through D23.
3. Read the same regime on a phone without losing access to the time-series context.

## Product, backend and build obligations specific to this assignment

Map every metric to producer, source clock, unit, normalization and model status. Specify mixed-frequency data, revisions, weekend/holiday handling, null/zero/partial and incompatible snapshots. Popups must preserve anchor, scroll and focus; limit simultaneous overlays. Own the shared dashboard.html.j2 integration contract; D02 governs body.page-macro and D03 governs body.page-stocks. Preserve these selectors and avoid cross-region style leakage.

**Existing source starting points:** templates/dashboard.html.j2 and each assigned macro template/builder from the route ledger. Reconcile macro_signals internal access status with the newer candidate rather than automatically promoting it.

**Known work and boundaries:** Macro #10485 is an existing US Macro Signals candidate. D10 owns news/event reading, D15 transmission details, D19 China semantics, D25 explanatory guide. Keep these seams explicit.

## Exact Paper starting references

| File / page | Exact identity | Boards | Observed role |
| --- | --- | --- | --- |
| [MASTERMIND PAGES — Market Breadth · Command Center · R1 · 2026-09-29](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-13-1) | 01M2WGNCX9475G79JRKJTCM08P / p-13-1 | 3 | candidate/workspace; approval evidence not inferred |
| [Mastermind · Market Dashboard Popups · Redesign — RISK RADAR SYSTEM](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-1-0) | 01M38EVF74SJWG1GANN5VP380Z / p-1-0 | 11 | candidate/workspace; approval evidence not inferred |
| [Mastermind · Market Dashboard Popups · Redesign — 01B · Risk Radar · Pullback Underway · US + China](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-6-0) | 01M38EVF74SJWG1GANN5VP380Z / p-6-0 | 10 | candidate/workspace; approval evidence not inferred |
| [Mastermind · Market Dashboard Popups · Redesign — 00 · Popups + Risk Radar · Start Here · Design Families](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-5-0) | 01M38EVF74SJWG1GANN5VP380Z / p-5-0 | 1 | candidate/workspace; approval evidence not inferred |
| [Mastermind · Market Dashboard Popups · Redesign — Program Handoff · Popup Upgrade Sequence](https://app.paper.design/file/01M38EVF74SJWG1GANN5VP380Z/p-2-0) | 01M38EVF74SJWG1GANN5VP380Z / p-2-0 | 1 | candidate/workspace; approval evidence not inferred |

### Shared inputs — coordinate before editing

| Reference | File / page | Custodian |
| --- | --- | --- |
| [Shared Shell · Completion & Integration · R1](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-23-0) | 01M2WGNCX9475G79JRKJTCM08P / p-23-0 | F01 |

The full artboard ID/name/dimension list is in [paper-artboards.json](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/census/paper-artboards.json). Board ownership overrides page custody for WTI references. These are observed inputs, not new RIG approvals. Re-read exact targets before modification.

## Assigned canonical routes

| Canonical ID | Route/family | Lifecycle / access | Source / common owner | Consult |
| --- | --- | --- | --- | --- |
| macro:anticipation | /anticipation.html | live / anonymous | templates/anticipation.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:crossasset | /crossasset.html | internal / unknown | templates/crossasset.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:cycle | /cycle.html | live / anonymous | templates/cycle.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:demand | /demand.html | live / anonymous | templates/demand.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:impulse | /impulse.html | live / anonymous | templates/impulse.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro | /macro.html | live / anonymous | templates/dashboard.html.j2; D02 common-template integration; D02 body.page-macro; D03 body.page-stocks | D03, F01, F02, F03 |
| macro:macro_family | /macro/<id>.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_business_activity | /macro_business_activity.html | live / anonymous | templates/macro_business_activity.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_capital_structure | /macro_capital_structure.html | live / anonymous | templates/macro_capital_structure.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_consumer_payments | /macro_consumer_payments.html | live / anonymous | templates/macro_consumer_payments.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_context | /macro_context.html | live / anonymous | templates/macro_context.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_financial_conditions | /macro_financial_conditions.html | live / anonymous | templates/macro_financial_conditions.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_growth_real_economy | /macro_growth_real_economy.html | live / anonymous | templates/macro_growth_real_economy.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_housing_real_estate | /macro_housing_real_estate.html | live / anonymous | templates/macro_housing_real_estate.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_inflation_system | /macro_inflation_system.html | live / anonymous | templates/macro_inflation_system.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_labor_markets | /macro_labor_markets.html | live / anonymous | templates/macro_labor_markets.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_liquidity_central_banks | /macro_liquidity_central_banks.html | live / anonymous | templates/macro_liquidity_central_banks.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_liquidity_regime | /macro_liquidity_regime.html | live / anonymous | templates/macro_liquidity_regime.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_monetary | /macro_monetary.html | live / anonymous | templates/macro_monetary.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_monetary_policy | /macro_monetary_policy.html | live / anonymous | templates/macro_monetary_policy.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_national_debt_liabilities | /macro_national_debt_liabilities.html | live / anonymous | templates/macro_national_debt_liabilities.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_rates_curves | /macro_rates_curves.html | live / anonymous | templates/macro_rates_curves.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_signals | /macro_signals.html | internal / unknown | templates/macro_signals.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:macro_trade_flows | /macro_trade_flows.html | live / anonymous | templates/macro_trade_flows.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:odds | /odds.html | live / anonymous | templates/odds.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:radar | /radar.html | live / anonymous | templates/radar.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |

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

A shell-composed macro overview plus grouped deep-dive archetypes, complete chart/indicator drilldowns, responsive risk/event overlays and a data-conflict register with truthful interim states.

Return a concrete completed artifact and evidence package. If a necessary dependency remains, identify the exact blocked action, what you completed, the owner and the minimum next evidence needed; do not substitute a broad claim that the whole design task is blocked.
