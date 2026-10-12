---
key: GMI-ENERGY-NUCLEAR
title: Energy — Nuclear Value Capture first vertical, stacked on the shared base
objective: >
  Land the nuclear theme-research vertical module (#8002) on the accepted #7870 base
  with one VerticalRegistration and mount for nuclear_power, served/browser/privacy
  proof and real admission. Done = #8002 reconciled, reviewed, merged, nuclear route
  and mount proven live.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
  - WS:GMI-SEMICONDUCTORS
  - WS:GMI-THEME-GRAPH
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
artifacts:
  - agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md
landmines:
  - "tests/test_nuclear_research_route.py line 27 on #8002 @508d8c206357 builds VerticalRegistration with the OLD 12-keyword signature; the #7870 shell has 14 fields (view_keys, build_query), so the test raises TypeError on rebase. The arity patch is packet Energy-1 and is mechanical."
  - "#8002 is stacked on an Energy-owned snapshot of #7870 (claude/energy-stack-base-b-6cd958e9); it is never merged or retargeted before #7870 is released (R-ENE-41/R-ENE-44)."
  - "The Theme-Graph record's ENE-1 wave (pr 7881, the T9 non-regression guard) is historical and lives under the Astra-held WS:GMI-THEME-GRAPH; do not edit it from this record."
  - "The generic private projection role in engine/earnings_narrative/private_publication.py (R-ENE-07, #7870 comment 5808374777) is to be authored by #8245 (CDV-1 Task 4, head b019f975, draft, under a REQUEST_CHANGES read, not landed), not by #7870 and not by Energy; Energy consumes it and registers no second role (#7870 comment 6112888232)."
do_not_redo:
  - "Audits of nuclear's module are paused while #8002 and #7870 are unchanged (R-ENE-41); no generic test-pin or docstring round."
  - "The registration writer is settled: Energy lands nuclear itself (Robotics seat agreed in #7870 comment 5866989985)."
waves:
  - id: ENE-W1
    title: "Nuclear vertical module #8002 (Draft/HOLD @508d8c206357) stacked on the base snapshot"
    status: in_progress
    pr: 8002
    wait:
      kind: external_dependency
      review_after: 2026-10-18
      condition: "#7870 released on main"
    next_action: >
      After #7870 is released: reconcile #8002 onto the accepted base, apply the
      12-to-14 keyword arity patch in tests/test_nuclear_research_route.py, re-point
      nuclear's semiconductor imports onto the kernel (R-ENE-45/46), re-run the
      REG-PACKET section-1c gates, then independent review.
  - id: ENE-W2
    title: "nuclear_power registration + mount, served/browser/privacy proof, real admission"
    status: todo
    depends_on: [ENE-W1]
    next_action: >
      ONE writer executes REG-PACKET-2026-09-25-nuclear_power.md sections 3, 3b, 4, 4b,
      5, 5b, 5c; then prove route, mount, scoped evidence, private/cache headers,
      unavailable/revoked behaviour, update and restart propagation.
next_action: >
  Hold until WS:GMI-SEMICONDUCTORS SB-W1 releases. Packet Energy-1 (arity patch +
  reconcile) is ready to dispatch that day. The prior Energy handoff (2026-09-24) is
  filed under WS:GMI-THEME-GRAPH because this record did not exist then; it stays there.
  R-ENE-07 was answered by the Semiconductors seat on 2026-10-11 (#7870 comment 6112888232): the
  additive REGULATORY_MILESTONE predicate value is outside SB-W1's approved scope and is queued
  under WS:GMI-SEMICONDUCTORS SB-W3 (V1.1) with Energy's admission terms; until it lands Energy
  records the milestone under limitations.establishes of the DEPLOYMENT_TARGET assertion
  (R-ENE-07(b)), and the generic private projection role is #8245's to author (Energy consumes).
---

## Carrier

- PR #8002, branch `claude/energy-nuclear-vertical-module`, head `508d8c206357`,
  Draft/HOLD, stacked, auto-merge null.
- Record created at consolidation (2026-10-11); the operation
  `gmi-energy-fable-ceo-e2e-20260923-chairman-001` previously tracked itself only
  through the Theme-Graph record's ENE-1 wave and the 2026-09-24 handoff.
- 2026-10-12: the seat's first post on #8002, comment 6115561519 (00:23:37Z), consumed Sol's
  Catalyst P8 packets 6010460068 + 6011568715: NUC-V1-01 (NuScale US460,
  PRODUCT_CAPABILITY / CATALOG_DESCRIPTION) and NUC-V1-02 (Centrus HALEU,
  REPORTED_OPERATING_MEASURE / REPORTED_FACT) are PREPARED_NOT_MINTED; the 2025-05-29 SDA and
  the Nov-2023 CFPP termination are HELD under `milestone_predicate_unavailable`;
  `REGULATORY_MILESTONE` stays the shared request at #7870 comment 5808374777;
  `nrc_official` / `doe_official` wait on the #7870 rights lane (QUEUED_NOT_STARTED); no
  source change; head `508d8c206357` unchanged; merge stacked behind #7870.
