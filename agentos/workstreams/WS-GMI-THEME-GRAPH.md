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
  - DEC:GMI-THEME-FABRIC-C0-CONVERGENCE
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
  - DSC:DAILY-ENGINE-RESULT-IS-FAILURE-AFTER-ITS-COMMIT
  - DSC:GMI-D1-SEAMS-IMPORT-WAVE-C-RIGHTS-USE
  - DSC:GMI-D2C-AND-D2D-CARRIERS-CONFLICT-IN-LEGACY-JOBS-YML
  - DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION
  - DSC:LEGACY-THEMATIC-COMPOSE-AGES-FIXTURES-ON-THE-WALL-CLOCK
  - DSC:W3C-COHORT-CAPTURE-IS-REFUSED-BY-THE-RIGHTS-GATE-BY-DESIGN
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
    pr: 8540
    depends_on: [D2C, D2D]
    next_action: >
      D2E #8540 remains the sole acceptance carrier at published rule head 03462ef689a5bbb4c4254c48db34713efd731876.
      The prospective window and adoption.status are ADOPTED_PROSPECTIVE_RULE_ONLY, awaiting
      production evidence; composition.d2e is HOLD_AWAITING_SELECTED_GENERATION_PROOF. Formal comment 6071188794
      (GitHub created_at 2026-10-08T23:38:32Z). Use exactly workflow_run.run_started_at >
      designated_formal_adoption_comment.created_at; engine/witness start is no substitute.
      Historical P1 remains accepted; GEN3 N4/N5 remain UNPROVEN. Q4 established only five known
      GEN3 tuples and did not recover the original unnamed a–e. All new N/Q replacement statuses
      remain NOT_RUN with null observations; P2 is NOT_ASSESSED and P3 null (both unassessed). No replacement generation
      is selected. Observe ordered original
      schedule attempts with immutable workflow/upload and effective-checkout proof. Apply the
      no-producer exception only with complete successful-gate/literal run=false/terminal skipped/
      no-engine-execution proof. Unknown evidence cannot justify skipping; upload success is not
      eligibility. A selected missing/failed archive is HOLD, with no rollover. Collect same-run
      evidence and independent P3 acceptance before D2E completion or W3B release. Continue from
      agentos/handoffs/GMI-THEME-GRAPH-2026-10-08.md; preserve historical receipts.
  - id: W3B
    title: "Sole local + canonical ThemeState — gmi-theme-state-w3b-20260827-sol-001"
    status: in_progress
    depends_on: [D2E]
    next_action: >
      Existing #8455 and #8539 source remains accepted; the sole graph shadow path remains
      GRAPH_SHADOW_STATE through the incumbent owner bundle, atomic generation write and lock.
      W3B is DRAFT_NOT_RELEASED. Merged witness retention and adopted #8540 window rules do not
      release it: require accepted same-run natural shadow/publication evidence and independent
      D2E P3. Historical GEN3 N4/N5 remain UNPROVEN. Preserve LEGACY engine default, lag-one/PIT
      qualifications and the October 6 handoff; no third producer or state store.
  - id: W3C
    title: "Selection Cohort Intelligence — gmi-theme-cohort-w3c-20260827-sol-001"
    status: in_progress
    depends_on: [W3B]
    next_action: >
      Use the incumbent Option A typed fail-closed projection as the lawful acceptance outcome
      until a separate capture-rights ruling. Source US/CN at 36dc212939fc9926af5f529e12f8fd3eae04a05a
      both have blob 533ad2e21f2154d49efda7196504dc64e88511b8:
      SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE, null generation and six false authority flags.
      At 2026-10-08T21:47:06Z anonymous Macro US/CN URLs returned 401 authentication_required,
      no-store/Vary: Cookie; Terminal /api/nw?f=market_plane returned 401 sign_in_required,
      private,no-store/Vary: Cookie. This proves only the auth boundary, not served JSON parity
      or signed-in human proof. Preserve auth; obtain authorized same-generation source,
      publication, gateway and human/machine evidence with refusal reasons intact.
      No zero-measurement claim, available CN card, capture enrollment or board mutation is inferred.
      D2E/W3B remain held; use agentos/handoffs/GMI-THEME-GRAPH-2026-10-08.md.
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
  - id: W-G3
    title: "F04 consumability census and the store_meta provenance fix (#8552)"
    status: done
    pr: 8552
    next_action: >
      A read-only census (grok pool, run-1791323013, checked head 04514a2c51a0) asked whether
      F04 can consume the canonical readers with no duplicate theme, state or graph truth
      plane. It found no duplicate writer, a consistent Neural Web registry, and that the
      shadow ThemeState is not an authority. B1 was confirmed as a latent gate #2 blocker:
      engine/market_ontology/exposure_map.py copied the whole data/theme_graph/_meta.json into
      provenance.store_meta, so internal-only finviz/ths structure would leave in any F04
      emission (no production emitter exists today). M1 was refuted: the strict store reader
      raise is deliberate and typed at the publication seam, so F04 consumes selection cohorts
      only through read_finalized_cohort and consume_*_source, never raw qualified_reads. m1
      was confirmed: config/synapse.yml omitted scripts/correct_gmi_identity_lineage.py as a
      known extra writer. #8552 (authored commit 950de975eb01, a ubuntu1 cursor composer-2.5 lane) fixes
      B1 with an allowlist projection (_STORE_META_PUBLIC_KEYS, _public_store_meta) and m1;
      MERGED 2026-10-07T01:31:36Z as squash 02ad6fee4cc5 at exact head 7d2cf2a9b180 (950de975eb01 plus three update-branch merges of main; ci-gate SUCCESS; blob ok=4; tree-verified: _STORE_META_PUBLIC_KEYS and _public_store_meta in origin/main engine/market_ontology/exposure_map.py, known_extra_writers in config/synapse.yml). The fix is latent until an F04 emitter exists, so it has no production
      proof to read. DO_NOT_REDO the census.
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
  - id: TF-CONVERGENCE
    title: "Theme Fabric research, source convergence and C0 records"
    status: in_progress
    pr: [8646, 8650, 8631, 8651, 8629, 8653, 8635]
    next_action: >
      Research #8646, breadth #8650, C8 #8631, M1 #8651 and C4 #8629 are merged with accepted
      source receipts. Witness #8653 accepted head ebd4382fdafdfecf55029305baddfa95b60f863a merged as
      c44aae5f131a59571ad0afcd7197e3d8696bc2b9 after binding CI and post-merge source conservation proof.
      The #8540 rule window at 03462ef689a5bbb4c4254c48db34713efd731876 is
      ADOPTED_PROSPECTIVE_RULE_ONLY, awaiting production evidence; composition.d2e is
      HOLD_AWAITING_SELECTED_GENERATION_PROOF. N/Q NOT_RUN/null; P2 NOT_ASSESSED; P3 null (both unassessed).
      This records set uses #8635's ordinary review/validation/CI/merge/source gate. Apply
      DEC:GMI-THEME-FABRIC-C0-CONVERGENCE; preserve
      census originals, optional #8643 scope, R-J.10/R9, E1/A1, R-H.W2w gaps and all existing
      natural/qualification/owner gates. No K phase-2 release or mission-completion claim.

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
    The engine job runs scripts/build_thematic_state.py with no --mode, so LEGACY never calls
    publish_generation, and the engine step stays LEGACY byte for byte. The graph shadow
    reaches production only through the separate --mode GRAPH_SHADOW_STATE step in the
    off-render oracle_offrender job (generation.write_atomic inside generation.family_lock).
    A new nightly artifact gets its own narrow mode in an off-render job; never flip the
    default mode, and an audit that expects publish_generation in production will mis-judge
    it (DSC:GMI-LEGACY-THEMATIC-STATE-NEVER-CALLS-PUBLISH-GENERATION).
  - >-
    The daily engine job concludes failure on every recent nightly, and only on its final OIP
    integrity step, which runs after "commit engine outputs" has succeeded. A step or job
    gated on needs.engine.result == 'success' is therefore skipped every night. Use needs
    plus the job-level if: always() && needs.et_gate.outputs.run != 'false' idiom
    (DSC:DAILY-ENGINE-RESULT-IS-FAILURE-AFTER-ITS-COMMIT).
next_action: >
  Continue operation theme-fabric-e2e-20261008-sol-001 from
  agentos/handoffs/GMI-THEME-GRAPH-2026-10-08.md under incumbent coo-fable/seat 6f14c2da.
  C4 and witness sources are merged and verified; #8540 prospective rules are
  ADOPTED_PROSPECTIVE_RULE_ONLY, awaiting production evidence, at 03462ef689a5bbb4c4254c48db34713efd731876.
  composition.d2e remains HOLD_AWAITING_SELECTED_GENERATION_PROOF.
  Next critical path: observe the first eligible original natural daily run using the exact
  designated formal-adoption created_at boundary, freeze and assess same-run evidence, then
  independent P3 and any lawful W3B release. N/Q remain NOT_RUN/null; P2 NOT_ASSESSED; P3 null (both unassessed).
  Continue W3C authorized payload/human proof and retained F04, qualified-micro, owner and E1
  gates. This records set follows #8635's ordinary PR gate; close #8633 as folded only after
  actual records merge/source proof. CHECKPOINTED_CONTINUATION; mission completion is false.
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
