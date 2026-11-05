# Always-on Macro and Shared Shell migration

Date: 2026-11-05.
Status: IN PROGRESS — Chairman-commissioned architecture and implementation; not production acceptance.
Operation: `macro-always-on-shared-shell-20261105-c3`.
Principal: current assigned ChatGPT Web architecture/integration session.
Product continuity: existing `WS:MARKET-OS`; data, publication, release and shell owners retain their existing authority.
Source carrier: `sol/web-macro-always-on-shared-shell-20261105-c3`.
Protected procedure: Mastermind `49c2e1d93e5e080b1671c98087a845e5beb09dd5`, skillpack v1.0.1, bootstrap-major 1 compatible.
Initial Macro base: `e39ec45902c1a2bb28507beb851593be6e422167`.
Initial Terminal observation: `f9d3280a2a3ff28dd925b128231702b836c8a247`.

## Chairman outcome

Make the entire Macro product continuously current at each source's legitimate cadence, independently of HTML builds, GitHub availability and code-release success, while adopting the existing shared shell at beta.mastermind-x.com. Sector Intelligence showing November 3 data on November 5 is the first traced consumer. Architecture, durable plan and initial implementation are explicitly assigned; original scope remains open until real production paths satisfy the acceptance below.

## Governing predecessor plans

This is an implementation extension, not a competing scheduler, registry, data plane or shell:

- `research/LIVE_INTRADAY_DASHBOARD_MASTERPLAN_2026-07-29.md`: runtime contracts for facts whose acceptable staleness is shorter than a day; same-origin API/SSE; one canonical writer.
- `research/NIGHTLY_RESILIENCE_AND_LIVE_TRANSITION_MASTERPLAN_2026-08-06.md`, Part B: independent collectors, incremental display computation, nightly reconciliation and removal of migrated render dependencies.
- `docs/VPS_LIVE_ORCHESTRATION.md`: existing systemd lane owner, external atomic live publication and sentinel.
- `research/MASTER_PRODUCT_SHELL_MAKEOVER_MIGRATION_2026-10-08.md`: existing shared-shell, page-registry and product design migration owners.
- `research/BREATHING_PLATFORM_MASTERPLAN_BY_FABLE.md` is a proposal/evidence source, not blanket runtime activation.

Current Chairman intent adopts the existing shared-shell web application. The July rejection of a blanket SPA rewrite remains a useful boundary against replacing working domain engines; it is not a prohibition on this expressly assigned shell migration. Forward ledgers, research validation and canonical vintage advancement remain single-writer and separately governed.

## Initial established facts and unknowns

- The supplied screenshot visibly labels Sector Intelligence as of 2026-11-03; it does not alone prove a failed build or collector.
- Current source already contains a VPS live orchestrator and an external freshness sentinel. Existing contracts retain bounded live overlays alongside canonical daily baselines.
- `daily.yml` and `render.yml` invoke `scripts.build_sector_central`; the current failure must be traced through producer, published object, serving cache and browser consumer.
- Shared-shell adoption and data continuity are independent acceptance dimensions.
- Live production source clocks, service health, beta access and active overlapping work are still to be measured.

## Architecture decisions to qualify

1. Keep GitHub for code review, CI and versioned releases; steady-state data collection and publication must not require a Git commit, PR or full-site render.
2. Extend existing Data OS/domain producers and VPS orchestration; use the current persistent artifact/object stores and atomic generation publication.
3. Expose owner-backed read contracts through existing Macro API and Terminal/shared-shell BFF; preserve auth, entitlement and source rights.
4. Separate source observation/session, successful collection, computation, publication and browser receipt clocks. Fresh file timestamps never make stale source facts current.
5. Use one source-owned generation per coherent product snapshot. Retain last known good data with explicit stale/degraded state, never fabricated zeros or a silent healthy fallback.
6. Browser updates are visible-tab/visibility-aware and generation-based; begin with bounded conditional revalidation, use existing SSE capability only where verified. Reconnection requires a canonical snapshot.
7. External semantic freshness checks must observe the same consumer contract, not just process liveness or CI status.
8. Migrate route families incrementally through the incumbent registry and beta; preserve existing design journeys, daily authority, rollback and single-writer ownership.

## Editorial task tree

These task labels are planning labels, not Executive Jobs or Agent OS wave state.

| Node | Dependency | Output and acceptance | Initial label |
|---|---|---|---|
| L0 | none | Pin this plan and recover current producer/consumer/ownership facts | in_progress |
| L1 | L0 | Sector source-to-screen trace; separate source stall, publish stall, cache and UI causes | ready |
| L2 | L0 | Current beta/shell/API/data-owner map and collision census | ready |
| L3 | L1, L2 | Freeze exact contracts, cadence/SLO matrix, phased migration and rollback | proposed |
| L4 | L3 | Small Sector freshness/runtime vertical with discriminating tests on this carrier | proposed |
| L5 | L4 | Qualify normal release; prove source advance visible without a site build | proposed |
| L6 | L5 | Migrate remaining domain families through existing owners | proposed |
| L7 | L6 | Failure drills, retirement of obsolete render/data coupling, complete consumer acceptance | proposed |

## First consumer acceptance and falsifiers

Sector Intelligence must show separately dated daily research and any qualified intraday overlay, with real coverage and explicit unavailable/stale state. A new accepted sector data generation must become visible in an already-open beta tab without rebuilding HTML or redeploying frontend code. A source that stops advancing must become stale even if the process, API and page remain HTTP 200. Invalid or partial generation must not overwrite the accepted generation; late responses must not regress the UI. Hiding/reopening a tab, connection loss, authentication revocation and recovery must behave honestly.

Whole-program completion additionally requires a source-cadence contract for every admitted Macro family; bounded fault isolation; independent operational monitoring; proved recovery; migration of live freshness out of GitHub's critical path; and canonical source-linked evidence for production, responsive browser journeys and remaining exceptions.

## Current continuation

Next: verify committed plan readback, dispatch bounded read-only Sector and shell/data-owner audits through the existing Fabric, then integrate findings into this same plan and implement the first noncolliding runtime/freshness slice. Preserve incumbent feature PRs and active/uncertain writers. No source branch, service, queue, provider, auth, ledger or release control is replaced by this plan.
