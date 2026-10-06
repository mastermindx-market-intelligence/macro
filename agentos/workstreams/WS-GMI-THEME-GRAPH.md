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
  - DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION
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
    status: done
    pr: 8432
    next_action: >
      MERGED 2026-10-06T09:50:19Z as squash 0b1fe8873054 at head f5b9a42b91fb, under Sol's
      HOLD-RELEASED (#8324 comment 6009049466; landing order #8417 -> #8486 -> #8455 ->
      #8432/#8435) on concluded checks: exact-head merge with --match-head-commit, then a bare
      git fetch origin main and a per-path blob comparison. Its CI block
      (tests/test_theme_graph_membership_lifecycle.py) is wired in main's
      .github/ci/legacy-jobs.yml. The ontology-action authority resolver is Chairman gate #5,
      carried separately by #8507 (wave G5). DO_NOT_REDO.
  - id: D2D
    title: "Ontology + probation breadth — gmi-theme-ontology-d2d-20260827-sol-001"
    status: done
    pr: 8435
    next_action: >
      MERGED 2026-10-06T10:42:10Z as squash 79b566f5c0cc at head 69a1aa7d90cb (ci.yml
      37447308219 success), second of the pair, so its legacy-jobs.yml block was composed over
      #8432's in the same carrier: both tests/test_theme_graph_membership_lifecycle.py and
      tests/test_theme_graph_structural_owner_binding.py are wired on main
      (DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML). Same HOLD-RELEASED,
      exact-head merge and blob verification as D2C. DO_NOT_REDO.
  - id: D2E
    title: "Rights / coverage / D2 acceptance — gmi-theme-accept-d2e-20260827-sol-001"
    status: in_progress
    pr: 8488
    depends_on: [D2C, D2D]
    next_action: >
      D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc), so acceptance is live as a
      seat-commissioned lane in three phases: P1 acceptance against current main; P2
      reconciliation of the D2B3 natural-proof clause against the 2026-10-07 nightly receipt
      (daily.yml crons 30 22 and 30 23 UTC); P3 an independent read-only review. Acceptance
      closes only on P2 natural evidence; the merged census #8488 (192a46de8be8) and green PRs
      are inputs, not acceptance. Gate #2 (rights class) is closed by #8509 (wave G2); gate #5
      (ontology-action authority) is #8507 (wave G5).
  - id: W3B
    title: "Sole local + canonical ThemeState — gmi-theme-state-w3b-20260827-sol-001"
    status: in_progress
    depends_on: [D2E]
    next_action: >
      Substrate landed without a third producer: #8455 (731a23fb64b9) recovered the sealed
      state owner and the accepted-generation reader. In flight: #8539 (gate #8 G1, DRAFT)
      makes the existing LEGACY publish also write the validated graph theme_state/v1 shadow
      through generation.write_atomic inside generation.family_lock, because the production
      nightly never calls publish_generation
      (DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION). Legacy
      neuralweb.theme_state.v1 and CTE consumers stay compatible during migration (gate #8
      ruling). W3B is accepted only after D2E acceptance and a nightly receipt showing the
      shadow state written.
  - id: W3C
    title: "Selection Cohort Intelligence — gmi-theme-cohort-w3c-20260827-sol-001"
    status: in_progress
    depends_on: [W3B]
    next_action: >
      Seams landed: #8417 (ef1f7db98cff, CTE state successor and W3C finalized-cohort
      readers), #8486 (072475fe21c2, selection-clock qualified_reads), #8524 (f255148cf9c7,
      gate #8 lane A read-only US/CN selection-cohort product projection), #8538
      (accd1db56f8d, gate #8 phase 2, qualified_reads wired into the US W3C read through a
      3-key adapter). In flight: #8539 (G1 shadow write), a reads-owner repair from the Wave G
      pass-1 audit (M1: a typed OWNER_UNAVAILABLE row instead of a raise; M2:
      instant-precision PIT visibility, so a fact computed after known_at stays invisible) and
      the Terminal US projection (gate #8 lane B on ubuntu1, per gate #6). Then a Wave G
      pass-2 read-only integrator audit over the landed tree, and production proof on the
      first nightly after the last landing. Invariant: source order and reasons preserved and
      the six authority flags in engine/theme_graph/selection_cohort.py stay False
      (authority_ceiling research_internal_only); no candidate insertion, ranking, readiness,
      sizing or board mutation.
  - id: W-A
    title: "ThemeState owner adapter + CTE-v3 lineage on the state carrier (#8455)"
    status: done
    pr: 8455
    next_action: >
      MERGED 2026-10-06T08:32:36Z as squash 731a23fb64b9 at head 615489e95d0f under Sol's
      HOLD-RELEASED; exact-head merge, blob-verified. DO_NOT_REDO; never push the stale local
      lineage branch anywhere.
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
    status: done
    pr: 8417
    next_action: >
      MERGED 2026-10-06T05:59:40Z as squash ef1f7db98cff at head d6ee81d9f536, first in Sol's
      landing order (HOLD-RELEASED 6009049466); blob-verified. DO_NOT_REDO; rights_use stays
      imported from main, never vendored.
  - id: W-D2
    title: "Selection-clock qualified reads engine/theme_graph/selection_cohort_reads.py (#8486)"
    status: done
    pr: 8486
    next_action: >
      MERGED 2026-10-06T07:30:55Z as squash 072475fe21c2 at head 7e18a73bbdd4, after #8417 in
      the landing order; blob-verified. DO_NOT_REDO. The Wave G pass-1 M1/M2 findings against
      selection_cohort_reads.py are carried by the W3C repair, not by reopening this wave.
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
    status: done
    pr: 8490
    next_action: >
      Read-only consumer census DELIVERED by a ubuntu1 cursor composer-2.5 lane (m1 refused auth;
      deviation recorded), judged by artifact against main 81eb0c9b3993 and Terminal
      2ca21c44718a (6 MATCH / 1 UNKNOWN: no Terminal consumer for v2/cohort). MERGED 2026-10-05
      14:46Z as squash d8f08cffd319 (refresh: visible disarm -> plain merge of healed main
      601f87f39924 -> head 6a21e2b302a1 -> re-arm; run 37323909239 green; merged by hand on the
      exact head); both census paths blob-verified on origin/main. DO_NOT_REDO.
      The v2/cohort Terminal consumer is a Sol/Chairman product decision,
      not a lane to spawn; re-census only if the Terminal pin or the C0 writer moves.
  - id: G2
    title: "Chairman gate #2: finviz_themes and ths_concepts retained internal_only (#8509)"
    status: done
    pr: 8509
    next_action: >
      MERGED 2026-10-06T05:57:12Z as squash 89f520972733. Ruling: both vendor families are
      internal-only, and an internal-only vendor input may never launder restricted structure
      into a house-owned output. DO_NOT_REDO.
  - id: G5
    title: "Chairman gate #5: read-only relation-action owner resolver in the probation owner (#8507)"
    status: done
    pr: 8507
    next_action: >
      MERGED 2026-10-06T11:28:40Z as squash cbfa20a45d84 at exact head 6d01445b12c1 after the
      stacking dependency on #8432 was met (#8432 merged as 0b1fe8873054). The seat that set
      the hold released it in comment 6015282302. All binding checks concluded green,
      including ci.yml run 37452837827. Scope landed as ruled: a READ-ONLY resolver inside the
      existing probation owner, typed OWNER_ACTION_AUTHORITY_UNAVAILABLE, with no new store,
      queue, lifecycle, curator, graph, rank, gate, size or trade authority, and no
      auto-ratification. tests/test_theme_graph_relation_action_resolver.py is wired in main's
      legacy-jobs.yml. Its first natural exercise is the 10-07 nightly theme-graph build,
      which the D2E acceptance reads.
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
  - >-
    The production nightly runs scripts/build_thematic_state.py with no --mode, so LEGACY never
    calls publish_generation: any state that must reach production is written through
    generation.write_atomic inside generation.family_lock in the LEGACY branch, and an audit
    that expects publish_generation there will mis-judge it
    (DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION).
next_action: >
  Seat 6f14c2da (Meta-CEO, Chairman handoff on #8324 comment 5991777960) carries the program;
  resume from agentos/handoffs/GMI-THEME-GRAPH-2026-10-06.md. Landed 2026-10-06: #8509, #8417,
  #8486, #8455, #8524, #8432, #8435, #8538, #8507. Next, in order: land #8539 (gate #8 G1) on
  concluded green at its exact head; land the reads-owner repair (Wave G pass-1 M1/M2) and the
  Terminal US projection (gate #8 lane B); run the Wave G pass-2 read-only integrator audit over
  that tree; then read the 2026-10-07 nightly as the natural receipt for D2E acceptance P2, the G1
  shadow state and the projection artifact. W3B and W3C close only on that production evidence.
  Remaining operator acts (mini4 credential install, mini2 disk) are never seat work.
---

## Current production substrate

Natural GMI receipt at current reconciliation (D2E pre-acceptance census, 2026-10-05, read from
origin/main 20eb503a09): data/theme_graph/_meta.json computed_at 2026-10-05T07:55:06Z, lane
nightly, 3,882 nodes, 505 measurement-candidate and 138 semantic-only local capability rows.
Rights families on main: mastermind_curated = direct_display_ok (emission yes); finviz_themes and
ths_concepts = internal_only since #8509
(2026-10-06, emission no). Two provenance strings have no SOURCE_PREFIX_FAMILY
mapping (data/theme_graph/probation/relation_events.v2.jsonl# and site/factordata/us_standouts.json).
The earlier reconciliation (belief_time 2026-08-27, 3,881 nodes, 18 canonical themes with 61 THS
mappings and 314 unmapped concepts) is predecessor context.

## Development closeout law

Mark the unfinished GMI development frontier complete only after D2C/D2D/D2E/W3B/W3C
are accepted with real producer/reader evidence, the Neural Web state authority is reconciled,
and downstream F04 can consume the canonical outputs. The parent F04 product program may remain
active after GMI development closes.
