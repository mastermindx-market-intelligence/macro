---
key: GMI-THEME-GRAPH
title: Global Market Intelligence theme graph
objective: >
  Own one canonical theme/local-theme semantic graph with exact identity, PIT/correction,
  curated ontology/probation, measurement eligibility, one ThemeState authority and
  read-only U.S./China selection-cohort context. Development done = D2C/D2D/D2E/W3B/W3C
  are production-proven and downstream F04 can consume the canonical readers without a
  duplicate theme/state/graph truth plane.
status: active
program: gmi-theme-graph
repos: [macro]
owner: coo-fable
class: research
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - engine/theme_graph/
  - data/theme_graph/
  - config/theme_sources.yml
decisions:
  - DEC:GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING
  - DEC:GMI-F04-BOUNDED-CHILD-ROUTING-2026-08-28
artifacts:
  - research/theme_graph/THEME_GRAPH_END_TO_END_COMPLETION_FREEZE_2026-08-27.md
  - research/theme_graph/CEO_W3_CONTINUATION_DIRECTIVE_2026-08-14.md
  - research/prophet_v4/V4_D2_ONTOLOGY_AND_PROBATION_HANDOFF.md
  - research/prophet_v4/D1_D3_W3B_MERGE_ORDER_RECOMMENDATION.md
  - docs/superpowers/plans/2026-08-28-gmi-theme-f04-end-to-end-completion.md
  - research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md
  - research/theme_graph/GMI_COMPLETION_RULER_AUDIT_2026-10-05.md
  - research/theme_graph/D2E_PRE_ACCEPTANCE_CENSUS_2026-10-05.md
discoveries:
  - DSC:A-STACKED-PR-ON-A-NON-MAIN-BASE-GETS-NO-PULL-REQUEST-CI
  - DSC:GMI-D1-SEAMS-IMPORT-WAVE-C-RIGHTS-USE
  - DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML
waves:
  - id: W0
    title: Graph scaffolding
    status: done
  - id: R1
    title: "Exposure decomposition R1 answered (#5402)"
    status: done
    pr: 5402
  - id: W3A
    title: >
      Local theme plane — rights-gated Finviz/THS local-theme nodes, PIT MEMBER_OF
      memberships, capability sidecar and probation substrate. No ThemeState or
      selection/ranking authority.
    status: done
    pr: 5718
  - id: D2C
    title: "PIT vintage completion — gmi-theme-pit-d2c-20260827-sol-001"
    status: in_progress
    pr: 8432
    next_action: >
      Delivered on PR #8432 (DRAFT, HOLD-FOR-SOL, head 54d17ebcb1c1, +2281/-71 over 12 files,
      ci.yml 37206291268 green on head). Wave E qualification 2026-10-05: git merge-tree against
      origin/main 20eb503a09 is CLEAN with zero path movement since the pin; no cosmetic ancestry
      join was made. Release is Sol's (one HOLD-RELEASED line on the carrier); never ready, arm or
      merge it from a worker seat. The ontology-action authority resolver stays UNWIRED per the
      carrier body (Chairman gate). Composition note: #8432 and #8435 conflict in
      .github/ci/legacy-jobs.yml — whichever lands second rebases its CI block
      (DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML).
  - id: D2D
    title: "Ontology + probation breadth — gmi-theme-ontology-d2d-20260827-sol-001"
    status: in_progress
    pr: 8435
    next_action: >
      Delivered on PR #8435 (DRAFT, HOLD-FOR-SOL, head 7429a3e5f6da, +5858/-43 over 6 files
      including tests/test_theme_graph_structural_owner_binding.py and its CI step; ci.yml
      37242875242 green on head). Wave E qualification 2026-10-05: merge-tree against origin/main
      CLEAN, zero path movement. Release is Sol's. It CONFLICTS with #8432 in
      .github/ci/legacy-jobs.yml (merge-base 4294fd498e8c, one content conflict, verified with
      git merge-tree --write-tree on 2026-10-05): the second carrier to land must rebase its
      legacy-jobs block, and a pack is one check so the heal is never split across two PRs.
  - id: D2E
    title: "Rights / coverage / D2 acceptance — gmi-theme-accept-d2e-20260827-sol-001"
    status: todo
    pr: 8488
    depends_on: [D2C, D2D]
    next_action: >
      Pre-acceptance census DELIVERED and seat-accepted on PR #8488
      (research/theme_graph/D2E_PRE_ACCEPTANCE_CENSUS_2026-10-05.md + d2e_precensus_2026-10-05.json):
      main+#8432 composition slice 524 passed / 1 skipped; #8435 could not be composed because of the
      legacy-jobs.yml conflict; contracts guard --selftest OK; natural store on main computed_at
      2026-10-05T07:55:06Z lane nightly, 3,882 nodes, 505 measurement_candidate / 138 semantic_only.
      D2B3 natural-proof reconciliation was NOT executed. Five DECISIONS REQUIRED are carried in
      research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md section 3 (finviz_themes and
      ths_concepts rights class, us_standouts.json family or exclusion, probation relation_events
      source_ref prefix, D2E release after Sol accepts #8432+#8435). The census PR #8488 is MERGED
      (squash 192a46de8be8). Acceptance closes only after D2C and D2D land and the D2B3
      clause is reconciled against the then-current nightly receipt.
  - id: W3B
    title: "Sole local + canonical ThemeState — gmi-theme-state-w3b-20260827-sol-001"
    status: todo
    depends_on: [D2E]
    next_action: >
      Held until accepted D2. Eligibility precedes state; named legs only; reconcile the
      existing Neural Web thematic-state lineage so one owner producer/truth remains.
  - id: W3C
    title: "Selection Cohort Intelligence — gmi-theme-cohort-w3c-20260827-sol-001"
    status: todo
    depends_on: [W3B]
    next_action: >
      Held until W3B. Read already-finalized U.S./China selections unchanged and attach
      PIT local memberships, ThemeState, canonical relations and descriptive overlap.
      Zero upstream selection/ranking authority.
  - id: W-A
    title: "ThemeState owner adapter + CTE-v3 lineage on the state carrier (#8455)"
    status: in_progress
    pr: 8455
    next_action: >
      Wave A 2026-10-05: lineage merge d3195488ef6 plus the data/site integrity remedy 61ed68e2078
      pushed as an ordinary merge onto #8455 (029fe5b17f0f), then the round-2 repair 4b38f2501a3b
      (legacy-jobs.yml path widenings for regime-outlook-mapping and nw-lobe-unfreeze, the
      contract-delta remedy). ci.yml 37307906336 on 4b38f2501a3b completed/success 12:45Z; the
      earlier reds are classified on the carrier (ci-pack-0 q06 inherited, healed by #8484;
      contract-delta own, closed). PARKED: Sol-held DRAFT, never ready/arm/merge; next act is Sol's
      release ruling. Never push the stale local lineage branch over the current head.
  - id: W-C
    title: "Current-use rights capture engine/theme_graph/rights_use.py (#8485)"
    status: done
    pr: 8485
    next_action: >
      MERGED 2026-10-05T12:44:43Z by the sweeper at head f0991eade1e6, squash fd2552813811;
      blob-verified on origin/main after a bare git fetch origin main (rights_use.py and its test
      SAME; legacy-jobs.yml carries the wiring). DO_NOT_REDO. #8417 was re-proved against it
      (DSC:GMI-D1-SEAMS-IMPORT-WAVE-C-RIGHTS-USE).
  - id: W-D1
    title: "W3C seams on the CTE successor — selection cohort publication (#8417)"
    status: in_progress
    pr: 8417
    next_action: >
      Lane result ACCEPTED at d02ebf451f1d. After #8485 merged, the seat re-read the carrier and
      pushed a plain merge of origin/main fd2552813811 (head 65ee41785e1c, no file edits; local
      test_first_party_import_names 15 passed); one seat comment classifies both prior reds
      (ci-pack-0 q06 inherited → #8484; ci-pack-10 import dependency → #8485). CI on 65ee41785e1c
      and on the path-widening repair head bddb73d9cb9e: ci.yml 37320358321 in flight at record time (expected: ci-pack-0 + contract-delta green; ci-pack-2 inherits main's readiness red until this PR lands, then a plain merge-of-main re-proof); seat classification comment 5995904316. PARKED: Sol-held DRAFT, never ready/arm/merge; release order
      #8417 → #8486. Never vendor rights_use into #8417.
  - id: W-D2
    title: "Selection-clock qualified reads engine/theme_graph/selection_cohort_reads.py (#8486)"
    status: in_progress
    pr: 8486
    next_action: >
      Lane result ACCEPTED at head 2e2bcd75ca62 (192 passed / 56 skipped locally; owner reads via
      store/identity_resolution/rights/theme_state/ontology). Stacked on #8417's branch, so it is
      PARKED by inheritance and carries a structural ci-authority unsupported_base_ref red with no
      pull_request ci/fences runs (DSC:A-STACKED-PR-ON-A-NON-MAIN-BASE-GETS-NO-PULL-REQUEST-CI).
      Do not retarget to main before #8417 lands. Release order: #8485 -> #8417 -> #8486.
  - id: W-G
    title: "Independent completion-ruler audit (#8487)"
    status: done
    pr: 8487
    next_action: >
      Read-only audit DELIVERED, accepted and MERGED (squash 625d0c71714d, blob-verified): 0 of 9
      ruler items PROVEN, items 2 and 3 HELD_BY_AUTHORITY, the rest PARTIAL or UNPROVEN at pin
      2026-10-05T11:27:09Z. Two seat caveats are recorded in the continuation handoff.
  - id: W-F
    title: "Terminal / R2 / human-consumer census (#8490)"
    status: awaiting_ci
    pr: 8490
    next_action: >
      Read-only consumer census DELIVERED by a ubuntu1 cursor composer-2.5 lane (m1 refused auth;
      deviation recorded), judged by artifact against main 81eb0c9b3993 and Terminal
      2ca21c44718a (6 MATCH / 1 UNKNOWN: no Terminal consumer for v2/cohort), armed merge-on-green at head b2de5314e76f and merge-blocked by the sweeper on main's ci-pack-2 red (tests/test_agentos_status.py readiness exemplar, healed in the records follow-up PR); merges on the next green sweep — then git fetch origin main ALONE and blob-compare its two paths.
      The v2/cohort Terminal consumer is a Sol/Chairman product decision,
      not a lane to spawn; re-census only if the Terminal pin or the C0 writer moves.
  - id: TRANSMISSION-FOLD
    title: "Legacy Transmission/Contagion frontier folded into current owners"
    status: done
    next_action: >
      NO GMI TRANSMISSION ENGINE BUILD. Theme-native semantic truth stays in GMI;
      Graph-1/2/3 propagation hypotheses stay with K3-D/current relationship owners;
      TXI/incorporation/dislocation stay with native owners; downstream Transmission Gap,
      second-order/opportunity and explanation product composition stays with canonical
      MarketOntology F04 operation marketontology-f04-ontology-transmission-20260826-fable-001.
  - id: ENE-1
    title: "Energy — Nuclear Value Capture first vertical (gmi-energy-fable-ceo-e2e-20260923-chairman-001)"
    status: in_progress
    pr: 7881
    next_action: >
      RE-SCOPED 2026-09-24 by Chairman ruling R-ENE-09 (relayed from Astra CEO): Semiconductors (#7870)
      builds the base and Energy integrates into it. The T9 nuclear non-regression guard is MERGED
      (#7881 -> 1a90944e) with production proof. 2026-09-25 wave 2, following the Robotics precedent
      (#7908): Energy builds its own nuclear theme-research vertical module on an Energy-owned snapshot
      of #7870's head (claude/energy-stack-base-b-6cd958e9 = 6cd958e9), importing B's shared types
      directly. It merges only after #7870 lands; one VerticalRegistration + mount for nuclear_power,
      served/browser/privacy proof and real admission then follow on an Energy carrier. Working
      checkpoint (section 9):
      agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md.
landmines:
  - >-
    The old next_action waiting for the 2026-08-15 scrape is superseded permanently.
    Natural graph data has accrued through belief_time 2026-08-27.
  - >-
    D2C/D2D/D2E were not completed as distinct waves. W3B must not leapfrog them.
  - >-
    Existing data/neuralweb/theme_state.json is useful predecessor context, not a second
    future authority. W3B must reconcile it; no third ThemeState producer/store.
  - >-
    K3-D PR #6514 is a separate held Graph-1/2/3 hypothesis-composition carrier. GMI
    cannot clone it or infer economic causality from theme membership/similarity.
  - >-
    MarketOntology PR #6504 is merged. F04 is now the canonical downstream ontology /
    transmission / opportunity product-composition lane. Do not mint a rival GMI W4/W5/W6.
  - >-
    The prior standalone GMI W4 relationship and W5 Sensorium commissions are
    REJECTED_BY_DESIGN as separate builds. Their useful jobs survive under current owners.
  - >-
    Logical F04/COO ownership is not a provider-session admission gate. Under current
    protected worker-routing law, architecture-frozen D2C/D2D prefer the least-scarce
    capable bounded avenue; Fable is reserved for genuine principal-level ambiguity,
    collision or continuity requirements.
  - >-
    A preferred avenue is not a RuntimeBinding. Under current protected organizational-
    continuity law, an architecture-frozen child with no lawful receiver is WAITING_CAPACITY /
    needs_placement with turn_owner=EXECUTIVE_PLACEMENT. Do not convert that into routine
    Chairman account selection, broad OPEN_PICKUP fanout or a child watcher with no receiver.
  - >-
    Watchers and Slack are attention/transport only. Once a lawful receiver/communication
    path exists, every watcher-enabled child requires explicit CONTINUE/STOP semantics;
    terminal STOP disarms both temporary watchers and does not authorize the next child.
next_action: >
  Seat 6f14c2da (Fable Meta-CEO, Chairman handoff 2026-10-05 on PR #8324 comment 5991777960)
  carries the program; resume from research/GMI_THEME_GRAPH_CONTINUATION_HANDOFF_2026-10-05.md
  section 4. Order: land #8485 on concluded green and blob-verify; re-prove #8417 against main
  after a freshness re-read (one comment, never merge); one result comment on #8455; seat
  checkpoint on #8324 (own fence >5991959730); Wave F macro-side CTE/R2 contract census (read-only,
  no Terminal writes; m1 Terminal host auth is refused and is a Chairman gate); then hand the
  section 3 gate list to Sol/Chairman last. D2C #8432 and D2D #8435 are delivered, CI-green and
  qualified against main; their release and composition order (legacy-jobs.yml conflict) is Sol's.
  D2E acceptance, W3B and W3C remain dependency-held behind those releases. The Terra /
  WAITING_CAPACITY placement text that stood here from 2026-08-28 is superseded: the children were
  placed and delivered through the subagent fabric (cursor composer-2.5 on ubuntu1/ubuntu2 with
  seat review; GLM host mini2 is disk-blocked, an operator act).
---

## Current production substrate

Natural GMI receipt at current reconciliation (D2E pre-acceptance census, 2026-10-05, read from
origin/main 20eb503a09): data/theme_graph/_meta.json computed_at 2026-10-05T07:55:06Z, lane
nightly, 3,882 nodes, 505 measurement-candidate and 138 semantic-only local capability rows.
Rights families on main: mastermind_curated = direct_display_ok (emission yes); finviz_themes and
ths_concepts = unresolved (emission no). Two provenance strings have no SOURCE_PREFIX_FAMILY
mapping (data/theme_graph/probation/relation_events.v2.jsonl# and site/factordata/us_standouts.json).
The earlier reconciliation (belief_time 2026-08-27, 3,881 nodes, 18 canonical themes with 61 THS
mappings and 314 unmapped concepts) is predecessor context.

## Development closeout law

Mark the unfinished GMI development frontier complete only after D2C/D2D/D2E/W3B/W3C
are accepted with real producer/reader evidence, the Neural Web state authority is reconciled,
and downstream F04 can consume the canonical outputs. The parent F04 product program may remain
active after GMI development closes.
