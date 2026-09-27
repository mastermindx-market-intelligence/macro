---
key: GMI-MINING-M1-INTEGRATION
title: "GMI Mining — M1 integration: Freeport copper (W-C) and MP Materials rare-earth (W-R) economic dossiers (Fable Meta-CEO program)"
objective: >
  Deliver the first bounded Mining release inside the existing GMI Themes experience on the
  Semiconductor-led shared foundation: an investor can explain a copper operating change
  (Freeport, theme:copper_steel_electrify) and a rare-earth processing/economic change
  (MP Materials, theme:rare_earth_critical_min) from real permitted sources, correctly bound
  companies, useful signed economics and an explicit counter-thesis. Done means both real-source
  journeys W-C and W-R pass with all forty MGD obligations executed on the integrated candidate,
  independent review, exact-head CI and the authorized release path - never a merged slice alone.
  M1 acceptance is recorded separately from the full Mining sector mission.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: specified
owns_paths:
  - engine/company_intelligence/mining_issuer_profiles.py
  - engine/market_ontology/mining_theme_research.py
  - contracts/market_ontology/mining_theme_research.v1.schema.json
  - tests/mining_casebook.py
  - tests/test_mining_*.py
  - tests/fixtures/mining_economic_dossier/**
  - research/mining/m1_integration_program/**
depends_on:
  - WS:GMI-THEME-GRAPH
  - WS:EARNINGS-INTELLIGENCE-OS
waves:
  - id: MIN-W1
    title: "T01' consumption harness: synthetic casebook, dependency-binding validator, typed route_unbound client, gate:code job mining-economic-dossier"
    status: done
    next_action: "DONE 2026-09-24 12:52Z — PR #7932 merged at ee908cb8f0b5 after the Opus R1 red-team (REJECT -> probes frozen RED -> seat repair, R-MIN-29/30); 67 tests verified on origin/main."
  - id: MIN-W2
    title: "T02 FCX/MP native profile factories + byte receipts (after CDV-1 #7905 merges) || T04a closed Mining definitions, own schema, synthetic composition"
    status: in_progress
    next_action: "T04a is DONE and at PRODUCTION_PROOF 2026-09-27: PR #7950 merged aff8b76cba6afa6ed03298a1814b059e317070a0 at 03:33:28Z on CONCLUDED green (run 36288053731 completed/success at head c05368b31a6; 26 checks, 0 pending, sole red the sanctioned ci-authority/codex/merge-queue-pilot), the merge is an ancestor of origin/main, and Audit B's frozen GREEN gate re-run against main's own bytes gives 53 passed. mining_theme_research.py, its v1 schema, mining_casebook.py and test_mining_composition.py resolve on main; mining_issuer_profiles.py correctly does NOT (T02 mints it). Three fabric rounds were consumed by freeze-then-repair (R1 REJECT 3B/6M; R2 REJECT 1B/5M letter-gaming - leg values synthesised from period_kind; R2 probes + the R-MIN-31 truth table frozen RED at a848ad54 before round 3 ran). Round 3 delivered real numeric legs and derived polarity and the letter-gaming class is verified dead. ROUND-3 REVIEW TACTIC CHANGED (R-MIN-33e): two Opus red-team spawns returned NO verdict, each exhausting its turn budget on discovery, so the SEAT ran the adversarial battery itself and delegated only scoping/severity to a READ_ONLY auditor with the code excerpt and measured outputs INLINE - 0 tool calls, 65k tokens, complete rulings, three seat severities upgraded and two defects the seat had missed. Four defects fixed under R-MIN-33/33a/33b/33c: duplicate pair names published contradictory rows; a source-declared range shipped as a point estimate the schema pins const false; unit/perimeter/period were carried and never read, so 1700 Mlbs vs 1680 kt published an INVERTED polarity; NaN passed the numeric gate. Receipt: reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md. THE WAVE IS NOT DONE: T02 is still ahead of it and still gated on #7905, which another seat holds DRAFT under its own R7 audit - do not poll it and do not arm a watcher on it. T02 dispatch is SYNTHETIC-ONLY; its packet excludes plan §4 bullet 1 (Audit A F1's unauthorized source-acquisition act), which cannot be deleted at source because the plan is reachable only from carrier #7795."
    depends_on: [MIN-W1]
  - id: MIN-W3
    title: "T03 definition-safe economic inputs (signed blocks, missing_derivation, IR-01/IR-02 consumer rules) -> T04b integrated positive witnesses"
    status: todo
    depends_on: [MIN-W2]
  - id: MIN-W4
    title: "T07 corrections, replay, version identity and unchanged-incumbent proofs"
    status: todo
    depends_on: [MIN-W3]
  - id: MIN-W5
    title: "T05 private route registration, T06 real theme entry + company workflow, T08 two real-source acceptance runs and release"
    status: todo
    depends_on: [MIN-W4]
    next_action: "Wait for Semiconductor B's shared route/client/mount on main and the incumbent-intake G2 source admission; never build against #7870's branch."
next_action: >
  MIN-W2 IS PARTLY DELIVERED AND STILL OPEN. T04a is at PRODUCTION_PROOF (#7950 merged
  aff8b76cba6, 53 passed against origin/main). The wave's other half, T02, has not started.
  DISPATCH POSITION, stated explicitly because two successive handoffs got it wrong in opposite
  directions: #7950's merge unblocks NO plan TASK. R-MIN-05 orders
  T01' -> (T02 || T04a) -> T03 -> T04b -> T07, so T03 needs BOTH #7950 merged AND T02 delivered,
  and T04b comes after T03. T02 itself waits on CDV-1 #7905 reaching main - another seat's DRAFT,
  never polled, never watched. What #7950's merge actually unblocked was this program's records
  lane, deferred only because tabling a ruling required a push to #7950 while its proof was in
  flight.
  CHECK THE T02 GATE AGAINST MAIN, NEVER AGAINST #7905: if `fiscal_scope` does not appear in
  engine/company_intelligence/issuer_profiles.py, #7905 has not landed and T02 is not
  dispatchable. Measured 2026-09-27 - it occurs ZERO times, and profile_for_ticker at :1293 has
  no private/public branch and cannot raise, so T02's own truth table describes the POST-#7905
  shape. A T02 lane must NOT build that split itself; it is #7905's hunk in a shared file its
  incumbent owns.
  The next four tasks have SEAT-AUTHORED freeze packets committed beside the rulings
  (T02/T03/T04b/T07 _FREEZE_PACKET.md), so no lane needs to re-derive a spec. T04b's packet is
  seat-authored of necessity: neither audit ever froze a T04b spec, because Audit B wrote ONE
  spec for all of T04 and the a/b split is R-MIN-05's. T02's packet is SYNTHETIC-ONLY and
  deletes the plan's unauthorized live-fetch checkbox from the build packet; real-byte
  acquisition stays held behind G2 + IR-05 as an owner/intake act.
  Per R-MIN-33e every commission carries its binding evidence INLINE rather than naming an
  artifact by path, or the worker spends its whole budget on discovery and returns no verdict
  (measured twice, 166k and 150k tokens, zero verdicts).
  Per R-MIN-33g a watcher's expected check set is the ci.yml RUN's own job list for the exact
  head sha and completion is that run's status == completed - never a constant pack floor, and
  zero ci-pack-* in the rollup is NOT proof that no packs will come, because ci-plan computes
  the set and takes about four minutes to publish it. Your own push invalidates your own
  evidence.
  MGD_EXECUTION_STATUS.json is the program's execution record against the forty obligations and
  is the thing a wave UPDATES, not a thing a wave re-derives. Status is never inferred from a
  test name. When T04b lands it MUST carry the two-armed MGD-08 clause 2 pin (R-MIN-34) and the
  two-armed MGD-10 pin, because T04b carries `period` onto native blocks and that is exactly
  what makes MGD-10 falsifiable.
  T05/T06 stay held for #7870's route/client/mount on main plus the answer to comment
  5811889498; T08 is last; G2 real-source admission remains an incumbent/operator act.
  Standing operator items: mini2 has no WAN (a bridge0 default route shadows the real gateway;
  the fix needs mini2 sudo and is an OPERATOR act), mini2 MiniMax provisioning, mini2 keychain
  unlock for cursor-agent. Never copy the fleet token to another host.

artifacts:
  - agentos/handoffs/GMI-MINING-2026-09-24-m1-integration.md
  - agentos/handoffs/GMI-MINING-2026-09-26-m1-integration.md
  - agentos/handoffs/GMI-MINING-2026-09-27-m1-integration.md
  - research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json
  - research/mining/m1_integration_program/T02_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T03_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T04B_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T07_FREEZE_PACKET.md
  - research/mining/m1_integration_program/T08_FREEZE_PACKET.md
  - research/mining/m1_integration_program/reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md
  - research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md
carrier:
  operation: gmi-mining-fable-ceo-m1-integration-20260924-chairman-001
  research_pr: 7795
do_not_redo:
  - "The eight research passes, design (blob 33d94481), plan (a2fca1c5), addendum (053a59e2), witness qualification and forty-row trace on #7795 @ eb6f05c0 are frozen - never re-research Mining or recreate the packet."
  - "Shared requests 5809132661 / 5809893850 and the accepted R4/R12 architecture answers on #7870 are consumed - never repeat them; an acknowledgment is not interface delivery."
  - "Original plan T01 (generic kernel extraction) is a shared-owner proposal, not Mining work; never create or copy engine/market_ontology/theme_research.py, a generic response schema, route, publisher, client or page shell."
  - "Canonical P05 blob is 42c90b46; the excluded local blob 587ee020 is never republished. Healthcare #7787 stays settled and separate."
  - "T04a is spent: #7950 is merged and proven green on main (53 passed). Three fabric rounds and three Opus reviews are consumed and R-MIN-31/32/33/33a-33g are tabled - never re-spec or re-review it."
  - "Never re-derive the MGD partition by grepping test names. Planned names resolve 0/40 on main and 2/40 at #7950, so a name audit reports 38 false gaps. MGD_EXECUTION_STATUS.json is keyed by obligation id for exactly that reason."
landmines:
  - "Shared files (issuer_profiles.py, event_workspace_build.py, receipts.py, legacy-jobs.yml, test_ci_pack.py, config/theme_sources.yml, the shared theme-research client/mount) stay owned by their incumbents and are touched only at named seams."
  - "Sparse worktrees truncate data/ and site/ on write."
  - "A new test wired into a gate:code run line without its paths: entry reds contract-delta fleet-wide."
  - "The sec_edgar public-domain rationale is not blanket clearance to republish issuer-authored bodies (addendum IR-05)."
  - "No live Freeport/MP figure may become a fixture or a native receipt before G2; a wrong-host 404 is not a privacy proof."
  - "An --admin merge on a docs-only diff is NOT sanctioned by a rollup showing zero packs. ci-plan computes the pack set and takes minutes; a docs diff gets a REDUCED set, not an empty one. This seat merged #8060 mid-flight over three in-flight checks on exactly that mistake (R-MIN-33g)."
  - "The T02/T04b packets are seat-authored, not audit-frozen. Audit B wrote ONE spec for all of T04 and the a/b split is R-MIN-05's, so a lane told to find 'the T04b spec' in the audits will find nothing and invent one."
---

# GMI Mining — M1 integration

Seat program record. Continuity lives in the handoff above; rulings in
`research/mining/m1_integration_program/rulings/`. Modified shared files are owned by their
incumbent workstreams (`WS:GMI-THEME-GRAPH`, `WS:EARNINGS-INTELLIGENCE-OS`) and are touched only
at named seams. All rank/gate/size/originate/entry authority stays literal false.
