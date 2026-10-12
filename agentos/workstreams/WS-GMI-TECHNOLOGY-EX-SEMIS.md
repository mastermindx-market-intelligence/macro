---
key: GMI-TECHNOLOGY-EX-SEMIS
title: Technology ex-Semiconductors Economic Change — implementation carrier
objective: >
  Serve the Technology ex-Semis economic-change vertical on the shared theme-research
  foundation (company_profile entries over the #7870 shell) without a parallel base.
  Done = #7891 reconciled onto the accepted base with Option A's entry_kind, reviewed,
  merged and served with browser proof.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
  - WS:GMI-SEMICONDUCTORS
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
  - DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE
landmines:
  - "#7891 constructs VerticalRegistration in production code with entry kind company_profile and anchor None; on the #7870 shell that is a grammar refusal, so it cannot rebase until Option A lands."
waves:
  - id: TEC-W1
    title: "Implementation carrier #7891 (Draft/HOLD @861d4049ae4c) held for the shared base and Option A"
    status: in_progress
    pr: 7891
    wait:
      kind: external_dependency
      review_after: 2026-10-18
      condition: "#7870 merged AND the Option A registry carrier (WS:GMI-SEMICONDUCTORS SB-W2) open"
    next_action: >
      No edit until Option A exists. First act after it lands: exact-head read of
      #7891, rebase onto the accepted base, replace the anchor-None construction with
      the admitted company_profile entry, then independent review.
next_action: >
  Hold. Packet Tech-1 (rebase + entry_kind adoption + review) is ready to dispatch the
  day Option A opens; dispatch through the fabric, builder never reviewer.
---

## Carrier

- PR #7891, branch `claude/ssd-technology-ex-semis-impl-c887181119dd2aaf`, head
  `861d4049ae4c`, Draft/HOLD, unmoved since 2026-10-01.
- Record created at consolidation (2026-10-11); no prior WS record existed for this
  vertical.
