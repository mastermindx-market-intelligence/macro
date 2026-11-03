# D09 — Flows, dark pool and institutional ownership

**Copy this entire file into the receiving Astra Pro session.** Commission date: 2026-11-02; audit observations span November 2–3 UTC. Read the linked source package if supplied separately.

Your assignment is **D09** within the existing Mastermind whole-site design makeover. Help users distinguish reported transactions, inferred flow, position change and institutional holdings with comparable source clocks.

**Priority / starting decision:** Reuse current flow/dark-pool candidates and consolidate common evidence patterns.

**Dependencies:** F01 F02. **Named collaborators:** D03 D05 D07 D08. Source-level consultations in your route rows also apply.

**Proposed Paper location:** 30 Research; MM · Flows & Dark Pool, MM · Funds & Ownership. These names are proposals. Destination IDs are pending creation or verified reuse; no file has been moved by this audit. Separate reference archives from current working files.

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

Intraday flow, dark pool, flow desk/leaders/velocity, smart money, Congress trades and the full fund detail family. MASTERMIND PAGES p-1W-1 is an existing implementation reference, not complete coverage of all 59 assigned registry rows.

## Required improvements and decisions

Separate real-time-like feeds from delayed holdings and filings, and explain inference versus reported fact. Use one coherent fund detail archetype across named funds while preserving unique available data. Common filters, entity inspectors and source receipt patterns can be shared; alternative meanings of flow cannot be amalgamated into one misleading score.

## Complete these user journeys

1. Unusual flow → exact instrument and contract/venue context → company/sector evidence → compare with holdings history.
2. Fund index → fund detail → position change → source filing → return to original filters.

## Product, backend and build obligations specific to this assignment

Document transaction versus position timestamps, filing/reporting lags, amended filings, venue coverage, notional/quantity units, actor and instrument identity, inferred direction and uncertainty. Mark unsupported linkage explicitly. Resolve unknown fund templates via their actual generator rather than treating each name as a bespoke backend. flow_velocity is in product_nav.china; D19 must review its local semantics and navigation.

**Existing source starting points:** templates/darkpool.html.j2; flow_desk/flow_leaders/flow_velocity/intraday_flow/smart_money/congress_trades/fund_index templates and actual fund generator; use exact crosswalk builder evidence.

**Known work and boundaries:** Macro #10498 Intraday Flow and #10490 Dark Pool are existing drafts. D08 owns options-specific exposure/replay; D07 company ownership composition; D05 sector money context.

## Exact Paper starting references

| File / page | Exact identity | Boards | Observed role |
| --- | --- | --- | --- |
| [MASTERMIND PAGES — Macro · Dark Flow · Implementation · 2026-10-17](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1W-1) | 01M2WGNCX9475G79JRKJTCM08P / p-1W-1 | 2 | specification/reference; reconcile with current candidate |

The full artboard ID/name/dimension list is in [paper-artboards.json](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/design_candidates/production_design_20261102/census/paper-artboards.json). Board ownership overrides page custody for WTI references. These are observed inputs, not new RIG approvals. Re-read exact targets before modification.

## Assigned canonical routes

| Canonical ID | Route/family | Lifecycle / access | Source / common owner | Consult |
| --- | --- | --- | --- | --- |
| macro:congress_trades | /congress_trades.html | live / anonymous | templates/congress_trades.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:darkpool | /darkpool.html | live / anonymous | templates/darkpool.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:flow_desk | /flow_desk.html | live / anonymous | templates/flow_desk.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:flow_leaders | /flow_leaders.html | live / anonymous | templates/flow_leaders.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:flow_velocity | /flow_velocity.html | live / anonymous | templates/flow_velocity.html.j2; assigned session; inspect actual shared imports before implementation | D19, F01, F02, F03 |
| macro:fund_ako | /fund_ako.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_akre | /fund_akre.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_altarock | /fund_altarock.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_altimeter | /fund_altimeter.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_appaloosa | /fund_appaloosa.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_aquamarine | /fund_aquamarine.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_bakerbros | /fund_bakerbros.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_basswood | /fund_basswood.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_baupost | /fund_baupost.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_berkshire | /fund_berkshire.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_casdin | /fund_casdin.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_coatue | /fund_coatue.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_corvex | /fund_corvex.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_d1capital | /fund_d1capital.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_dorsey | /fund_dorsey.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_dragoneer | /fund_dragoneer.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_duquesne | /fund_duquesne.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_durable | /fund_durable.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_egerton | /fund_egerton.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_elliott | /fund_elliott.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_engaged | /fund_engaged.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_fairholme | /fund_fairholme.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_gates | /fund_gates.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_giverny | /fund_giverny.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_greenlea | /fund_greenlea.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_himalaya | /fund_himalaya.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_icahn | /fund_icahn.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_index | /fund_index.html | live / anonymous | templates/fund_index.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_jana | /fund_jana.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_kimmeridge | /fund_kimmeridge.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_lightstreet | /fund_lightstreet.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_lonepine | /fund_lonepine.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_mudrick | /fund_mudrick.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_oaktree | /fund_oaktree.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_pabrai | /fund_pabrai.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_perceptive | /fund_perceptive.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_pershing | /fund_pershing.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_polen | /fund_polen.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_punchcard | /fund_punchcard.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_racapital | /fund_racapital.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_rtw | /fund_rtw.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_sachem | /fund_sachem.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_scion | /fund_scion.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_soros | /fund_soros.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_starboard | /fund_starboard.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_tci | /fund_tci.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_thirdpoint | /fund_thirdpoint.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_tigerglobal | /fund_tigerglobal.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_trian | /fund_trian.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_valueact | /fund_valueact.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_viking | /fund_viking.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:fund_whalerock | /fund_whalerock.html | live / anonymous | unknown; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:intraday_flow | /intraday_flow.html | live / anonymous | templates/intraday_flow.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |
| macro:smart_money | /smart_money.html | live / anonymous | templates/smart_money.html.j2; assigned session; inspect actual shared imports before implementation | F01, F02, F03 |

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

A complete flow/ownership task model with editable flagships, fund detail archetype, truthful time/inference states and a source mapping covering every fund route without duplicated designs.

Return a concrete completed artifact and evidence package. If a necessary dependency remains, identify the exact blocked action, what you completed, the owner and the minimum next evidence needed; do not substitute a broad claim that the whole design task is blocked.
