---
key: GMI-THEME-GRAPH
title: Global Market Intelligence theme graph
objective: >
  Own one canonical theme/local-theme semantic graph with exact identity, PIT/correction,
  curated ontology/probation, measurement eligibility, one ThemeState authority and
  read-only U.S./China selection-cohort context. Development done = D2C/D2D/D2E/W3B/W3C
  are production-proven and downstream F04 can consume the canonical readers without a
  duplicate theme/state/graph truth plane. The 2026-10-16 Meta-CEO commission also
  requires a maintained, source-backed map of business activity, qualified exposure,
  economic relationships and actual Terminal explanations across an explicit universe.
  Original development acceptance alone does not complete that expanded mission.
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
  - engine/classification_axes/
  - contracts/classification_axes/
decisions:
  - DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19
  - DEC:GMI-INVESTABLE-ECONOMY-RECOVERY-ACCEPTANCE
  - DEC:GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING
  - DEC:GMI-MICRO-EXPANSION-2026-10-21-ADDITIVE-FROZEN-68
  - DEC:GMI-F04-BOUNDED-CHILD-ROUTING-2026-08-28
  - DEC:GMI-THEME-FABRIC-C0-CONVERGENCE
  - DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK
  - DEC:GMI-TAXONOMY-UPGRADE-V2
  - DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD
artifacts:
  - research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md
  - research/theme_graph/coverage_20261019/COVERAGE_REPORT.md
  - research/theme_graph/diagnostic_20261019/STRATA_DESIGN.md
  - contracts/theme_graph/activity_membership_history.v1.schema.json
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
  - DSC:GMI-THEME-GRAPH-SUPPLY-EDGE-TYPES-HAVE-ZERO-ROWS
  - DSC:GMI-MACRO-SENSITIVITY-AXIS-READS-GITIGNORED-STOCKDATA
  - DSC:GMI-THEME-GRAPH-STORE-NON-STRICT-READ-MASKS-CORRUPTION
  - DSC:GMI-CROSSWALK-ROW-DELETION-NEVER-CLOSES-PARENT-OF
  - DSC:GMI-THEME-GRAPH-SUITES-RUN-ONLY-IN-THE-DATA-HEALTH-LANE
  - DSC:GMI-NEURAL-WEB-THEME-STATE-REGISTRY-UNCHANGED-THROUGH-STEP-7
  - DSC:GMI-PRINCIPAL-ACTIVITY-COVERAGE-IS-ZERO-ON-2026-10-19
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
      Original #8540 selected-generation P2 and independent P3 are accepted and merged.
      Principal receipt 6103645886 accepts P2 for original workflow 37874656026/attempt 1
      and graph publication 48cf3140; incorporation 6120586132 is committed at e77e8430
      and #8540 merged October 12. The old P2 NOT_ASSESSED / P3 null next_action is stale:
      DO_NOT_REDO original selected-generation acceptance or refused publisher-log retrieval.
      Retain P1 and the specific historical GEN3 N4/N5 limitations. Scope does not confer
      blanket eligibility on later graph subjects or current-use purposes. Current-generation
      native identity, membership, rights and eligibility remain W3B dependencies; keep this
      broad rights/coverage wave open until those original production obligations are met.
      See the 2026-10-16 recovery record for evidence links and the separate acceptance boundaries.
  - id: W3B
    title: "Sole local + canonical ThemeState — gmi-theme-state-w3b-20260827-sol-001"
    status: in_progress
    depends_on: [D2E]
    next_action: >
      Retain accepted #8455/#8539 state-owner source and merged #8783 selection-clock repair.
      Original D2E selected-generation P2/P3 is already accepted; no replacement P3 is owed.
      Natural shadow writes are observed through October 16, but they do not prove qualified
      production state or W3B release. At census 9629927bfc7a4dad13b89590e86cd1b9be33573a,
      shadow blob 4b35213b43547906a34a0477d354eed081e722ae has 663 UNAVAILABLE subjects,
      all NOT_QUALIFIED/D2E_UNSEALED with missing identity, membership and current-use rights.
      The builder supplies no owner_readers; eligibility and qualified rights remain explicitly
      unsealed in incumbent production contracts. Bind authentic current-generation owner
      receipts and same-run effective-checkout/publication proof through those owners, then
      obtain the existing W3B acceptance. Preserve LEGACY default and GRAPH_SHADOW_STATE
      atomic generation/lock path, lag-one/PIT qualifications and historical receipts.
      No third producer, truth store or blanket flag promotion.
  - id: W3C
    title: "Selection Cohort Intelligence — gmi-theme-cohort-w3c-20260827-sol-001"
    status: in_progress
    depends_on: [W3B]
    next_action: >
      The incumbent Option A typed fail-closed projection remains the lawful unavailable
      outcome until an applicable capture-rights ruling and qualified producer proof.
      Historical US/CN source 36dc212939fc9926af5f529e12f8fd3eae04a05a has common blob
      533ad2e21f2154d49efda7196504dc64e88511b8: SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE,
      null generation and six false authority flags. October 8 anonymous Macro/Terminal 401
      observations prove authentication boundaries only, not served parity or signed-in proof.
      Terminal #868 has accepted exact-head source review/required CI at e199c9e5357427a2da4722e5ef3e2da326a6d0bd,
      but later OpenAI integration rejection 6075735969 is reaffirmed by 6103693287:
      EFFECT_NONE, hold retained, no retry through another tool/account/worker/branch/direct merge.
      Preserve the fix and obtain legitimate clearance of that specific effect before integration.
      After native qualification, prove authorized same-generation source, publication, API and
      actual EN/ZH human/machine parity for both U.S. and China with refusal reasons intact.
      No available CN card, capture enrollment, zero-measurement claim or board mutation is inferred.
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
      The original #8540 selected-generation P2/P3 acceptance is merged; the former
      prospective-only/P2 NOT_ASSESSED/P3 null projection is superseded by receipts
      6103645886 and 6120586132. Preserve the historical rule, evidence and narrower
      limitations; do not infer current-generation rights/eligibility or W3B acceptance.
      This records set uses #8635's ordinary review/validation/CI/merge/source gate. Apply
      DEC:GMI-THEME-FABRIC-C0-CONVERGENCE; preserve
      census originals, optional #8643 scope, R-J.10/R9, E1/A1, R-H.W2w gaps and all existing
      natural/qualification/owner gates. No K phase-2 release or mission-completion claim.
  - id: TAXONOMY-V2
    title: "Taxonomy V2: sub_theme tier and display-tier classification axes"
    status: done
    pr: [8940, 8941, 8942, 8945, 8948, 8961, 8974, 8975, 8999, 8969, 9000, 8968, 8973, 8976, 8987]
    next_action: >
      Seat 6f14c2da (DEC:GMI-TAXONOMY-UPGRADE-V2, DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD). All
      fifteen PRs are merged, and production is proven: the nightly-materialized
      data/theme_graph on main (commit 8ce9f3e9908d, 2026-10-14) holds 12 sub_theme nodes and
      132 PARENT_OF rows (93 + 39), as specified. Follow-ons, not part of this wave: the L12
      hierarchy-breadth and L13 micro RS-proxy display readers (no rank-like keys), F04
      consumption coordinated with the MarketOntology owner (no wiring without a new DEC), a
      hierarchy browse page through the design lane, and a human ratifier for the 27
      RELATION_WITHDRAW events that would retire the direct theme->micro_theme rows.
  - id: RECOVERY-S2
    title: "Recovery step 2: native issuer economic-context source repair (#9423)"
    status: done
    pr: 9423
    next_action: >
      DO_NOT_REDO. Squash 072822093ccd on main. Private economic-context API delivery with
      the C01 grain; no vendor-membership laundering (gate 2). Nothing left in this wave.
  - id: RECOVERY-S3
    title: "Recovery step 3: activity membership admission (#9645) and PIT history fold (#9644)"
    status: done
    pr: [9645, 9644]
    next_action: >
      DO_NOT_REDO. Squashes d47f5b14d246 (A1 admission: candidates land PROPOSED, never
      ratified by code) and b04a9d898b0d (A2: contracts/theme_graph/
      activity_membership_history.v1.schema.json plus the ACTIVITY_HISTORY_* fold in
      engine/theme_graph/materialize.py). The fold is a pure function no nightly job calls;
      wiring it into the build and the edges.v1 projection are owed to the ThemeState
      producer owner (DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19).
  - id: RECOVERY-S4
    title: "Recovery step 4: generation-specific ThemeState applicability readers (#9670)"
    status: done
    pr: 9670
    next_action: >
      DO_NOT_REDO. Squash cea783c92a86: engine/theme_graph/theme_state_owner_readers.py
      StateQualificationReader and the diagnostic-only publication_applicability in
      engine/theme_graph/theme_state.py. Read-only; the current shadow generation reads
      D2E_UNSEALED. Reader custody/auth, shadow-writer wiring and the t9 pin amendment are
      owed to the D2E/ThemeState owners, not to this wave.
  - id: RECOVERY-S5
    title: "Recovery step 5: API parity on the C01 grain (#9652)"
    status: done
    pr: 9652
    next_action: >
      DO_NOT_REDO. Squash 82e854321c8c. Terminal consumption stays behind the #868
      integration safety hold (Sol/Chairman); EFFECT_NONE retained, never bypassed.
  - id: RECOVERY-S6
    title: "Recovery step 6: cohort delivery contract (#9641)"
    status: done
    pr: 9641
    next_action: >
      DO_NOT_REDO. Squash e5d6f40157e2. Read-only cohort context; no selection or ranking
      authority.
  - id: RECOVERY-S7
    title: "Recovery step 7: measured coverage proof (#9745), diagnostic strata (7d) and operating-proof tests (7e)"
    status: done
    pr: [9745, 9754, 9753]
    next_action: >
      DO_NOT_REDO once merged. #9745 (scripts/gmi_coverage_proof.py, tests/
      test_gmi_coverage_proof.py, research/theme_graph/coverage_20261019/) measures the
      §7 thresholds: denominator honesty PASS, principal activity FAIL 0/[1926,1931] U.S.
      and 0/[1,1019] China, taxonomy FAIL on owner_reviewed
      (DSC:GMI-PRINCIPAL-ACTIVITY-COVERAGE-IS-ZERO-ON-2026-10-19). 7d holds research/
      theme_graph/diagnostic_20261019/; 7e holds tests/test_gmi_operating_proof.py with each
      property PASS or xfail(strict) naming its owner. Re-measure by re-running the proof
      script; never by editing the report.
  - id: RECOVERY-S8
    title: "Recovery step 8: descriptive-product acceptance records and Neural Web reconciliation"
    status: done
    pr: 9757
    next_action: >
      DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19 records the per-threshold verdicts
      and owner acts; DSC:GMI-NEURAL-WEB-THEME-STATE-REGISTRY-UNCHANGED-THROUGH-STEP-7
      records that no third ThemeState producer/store exists. MISSION_COMPLETE=false.

landmines:
  - >-
    The old next_action waiting for the 2026-08-15 scrape is superseded permanently.
    Natural graph data has accrued through belief_time 2026-08-27.
  - >-
    D2C/D2D source and original D2E selected-generation P2/P3 are accepted. W3B still
    owes current-generation qualified owner binding and natural producer/reader proof;
    do not replay accepted original D2E evidence or promote later subjects by inheritance.
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
  2026-10-21 Chairman completion commission is RUNNING under seat 6f14c2da (live checkpoint:
  agentos/handoffs/GMI-THEME-GRAPH-2026-10-21-completion-commission.md). Micro expansion
  ratified additively (303 micros, DEC:GMI-MICRO-EXPANSION-2026-10-21-ADDITIVE-FROZEN-68);
  integration PR #10017 merged (cf6fd11f) and proven by main baseline 39736520949; every
  ORCH-PIPE wave merged (last #10025 -> e6f6088e) with M3 recorded NOT MET on the frozen
  proof; the coverage proof reads the activity ledger by default (#10029); the first M1
  activity witness is receipt-bound on main (#10026 -> 61f82f58) and MEMBER_OF waits on a
  Chairman graph_membership_use ruling; ORCH-REL still runs (#9986); ORCH-DESIGN delivered
  draft #10054 and is in seat-requested repair round 2; UI and verification orchestrators
  follow the design acceptance. The prior remainder below still
  states the incumbent-owner acts. Recovery steps 2 through 8 of research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md
  §9 are merged and recorded (waves RECOVERY-S2..S8); the seat lane is complete and
  DO_NOT_REDO. The descriptive product is accepted as a MEASURED, OPEN record
  (DEC:GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19): only denominator honesty is
  closed; principal activity is 0 on both markets and the taxonomy has no owner review.
  Each remainder is an incumbent-owner act, in this order: (1) ThemeState producer owner
  wires the A2 activity-membership history fold into the nightly build under its own
  narrow --mode in an off-render job and emits the edges.v1 projection, after which the
  first nightly measures freshness and corrections for real; (2) the named GMI curator
  ratifies PROPOSED activity memberships one evidenced row at a time (gate 5) and the
  taxonomy owner records a disposition per micro; (3) Data OS supplies China issuer
  resolution and listed counts and U.S. identity qualification; (4) #7870 adds the C01
  rights row in config/theme_sources.yml; (5) the D2E owner seals the current shadow
  generation and takes reader custody/auth with the t9 pin amendment; (6) the Terminal
  #868 hold is released by its holding authority before any actual-explanation proof.
  W3B/W3C current-generation owner binding and D2E sealing remain the original open
  development frontier. Predictive candidates (micro RS proxy L13, transmission,
  opportunity) go to the existing evaluator, F04 MarketOntology and K3-D owners; no
  promotion from this acceptance. Preserve the explicit #8793 and Terminal #868 denied
  effects, API524 EFFECT_UNKNOWN on its original carrier, immutable C01 generation 040b
  and all current-use rights. Re-measure coverage by re-running
  scripts/gmi_coverage_proof.py, never by editing a report. MISSION_COMPLETE=false.

---

## Current production substrate

Current census at Macro 9629927bfc7a4dad13b89590e86cd1b9be33573a: graph computed
2026-10-16T17:12Z contains 3,975 nodes, 25,643 edges and 13,349 latest-belief edges.
Taxonomy V2 contains 10 categories, 18 themes, 12 subthemes and 68 microthemes.
All 103 original micro candidates and 46 addendum activities are still unadmitted;
none establishes a qualified canonical micro membership or economic magnitude.
The current shadow generation bd084373e896ac0bd192b4eb3766c81f contains 663
UNAVAILABLE / NOT_QUALIFIED subjects. These are measured source facts, not qualified
coverage or completed U.S./China consumer proof. Full count denominators, owner gaps,
primary research, acceptance thresholds and next implementation sequence are in
research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md.

Historical predecessor receipt (retained evidence):

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
