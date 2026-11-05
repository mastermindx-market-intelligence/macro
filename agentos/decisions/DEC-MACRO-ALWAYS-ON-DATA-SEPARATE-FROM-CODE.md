---
key: MACRO-ALWAYS-ON-DATA-SEPARATE-FROM-CODE
question: >
  How should the Chairman's November 5 assignment make the Macro Dashboard
  continuously current while adopting beta.mastermind-x.com's shared shell?
answer: >
  Extend the existing live runtime, domain stores, API/BFF and shared shell.
  Separate source collection, display materialization, coherent publication and
  browser revalidation from GitHub checkout, generated-data commits and HTML
  rendering. Qualify Sector first, then migrate the existing registry families.
  Preserve nightly canonical ledger/grade authority and existing account owners.
rationale: >
  Normal-TLS production reads showed November 5 HTML carrying November 3 Sector
  inputs. The existing origin validator additionally found missing action-board
  source metadata and incompatible publication hashes. A Sector refresh run failed
  at Git checkout before computation, while existing quote/breadth/basket runtime
  lanes continued. Shell migration alone cannot repair those producer/publication
  dependencies. Existing live orchestration and monitoring can be extended without
  introducing another scheduler, state authority or data platform.
alternatives:
  - option: Rebuild all pages more often in GitHub Actions
    why_not: >
      The observed failure is before data computation, and rebuilding can still
      re-publish old inputs. Higher frequency preserves the failing dependency.
  - option: Move the current HTML pages into a new frontend without changing data delivery
    why_not: >
      The shell would continue consuming frozen artifacts. Source-to-browser
      acceptance must be independent of frontend deployment.
  - option: Replace the current runtime with a new event bus, database and scheduler
    why_not: >
      Existing persistent publication, domain stores, systemd lanes and BFF are
      sufficient for the first canary. No measured requirement justifies duplicate
      control or data owners.
  - option: Run the existing full Sector builder every five minutes
    why_not: >
      Current entry points render HTML and include research/score/ledger side
      effects. First extract bounded display computation and transfer one writer.
evidence:
  - research/market_os/ALWAYS_ON_MACRO_MIGRATION_2026-11-05.md
  - research/market_os/ALWAYS_ON_MACRO_EVIDENCE_2026-11-05.json
  - https://github.com/mastermindx-market-intelligence/macro/issues/10779
  - https://github.com/mastermindx-market-intelligence/macro/actions/runs/42099034826
  - "Macro e39ec45902c1a2bb28507beb851593be6e422167: scripts/build_site.py bare action_board writer; scripts/build_sector_intelligence.py; docs/VPS_LIVE_ORCHESTRATION.md"
  - "Terminal f9d3280a2a3ff28dd925b128231702b836c8a247: existing private/no-store Sector BFF and Discover revalidation"
affects:
  - WS:MARKET-OS
  - WS:BREATHING-PLATFORM
  - scripts/freshness_sentinel.py
  - scripts/check_sector_intelligence_freshness.py
confidence: high
reversibility: easy
decided_by: "macro-always-on-shared-shell-20261105-c3; Chairman-commissioned architecture"
decided_at: 2026-11-05
---

This is a scoped implementation extension. It does not replace MARKET-OS's broader
adopted product plan, accepted direction, family carriers, runtime admission or
release rules. It creates no new trade, research, account or ledger authority.

The first implementation is an external Sector observation in the existing sentinel.
Accurate stale/unknown reporting is useful delivery, but it is not independent live
Sector production. The master plan's L4b-L7 and authenticated browser proofs remain
open. Reconsider the transport/capacity choices only after measured scale or recovery
limits, or a changed source contract, establish a concrete need.


## Input ownership and publication ruling, November 5

The source census and parent qualifications are recorded in
[the input/runtime audit](../../research/market_os/ALWAYS_ON_MACRO_INPUT_RUNTIME_AUDIT_2026-11-05.md).
The current `compute()` reads global inputs and time and must not be called pure merely
because it has no direct output write. Extract declared inputs and an explicit effective
date before runtime use; keep builder ledger, grade, research-log and notification effects
with their existing writers.

The first independent daily canary must advance named close-derived fields from an
accepted completed-session history, preserving adjustment, revision and coverage semantics.
Fresh close-derived values do not refresh unrelated research/context. Fence all old
collection writers for a transferred lineage; Git builders may consume a selected immutable
snapshot as compatibility transport but may not silently become a second producer.

Where free/paid representations must agree, extend the existing publisher with immutable
generation artifacts and one atomic current-manifest promotion. Per-file renames alone are
insufficient. Resolve one manifest per request and use explicit tier projections through
existing auth/BFF controls. A new `/live/` path is not evidence of correct entitlement.
Do not create a redundant quote/basket-pulse wrapper or a parallel publication owner.

The existing `DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD`
explicitly reserved off-Git publication for a pipeline decision. The current Chairman
assignment authorizes this transition, while its fixed shallow-history, issuer ancestry,
pull guard and maintenance rules remain. No re-shallowing, clone replacement, new queue,
unqualified storage owner or infrastructure purchase follows from this ruling.

Source delivery now includes Macro #10780 and Terminal #1311. They do not establish
installation or acceptance. The native Brief/Watches/action-board gaps, independent
producer path and authenticated beta open-tab proof remain required.
