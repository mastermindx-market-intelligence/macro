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
    next_action: "T04a is PR #7950, READY and merge-on-green armed at head 64a0b1dd, watcher at 600s. Three fabric rounds were consumed by freeze-then-repair (R1 REJECT 3B/6M; R2 REJECT 1B/5M letter-gaming - leg values synthesised from period_kind; R2 probes + the R-MIN-31 truth table frozen RED at a848ad54 before round 3 ran). Round 3 delivered real numeric legs and derived polarity, and the letter-gaming class is verified dead - reversed legs flip the polarity, so no per-pair lookup table is hiding in it. ROUND-3 REVIEW TACTIC CHANGED (R-MIN-33e): two Opus red-team spawns returned NO verdict, each exhausting its turn budget on discovery, so the SEAT ran the adversarial battery itself and delegated only scoping/severity to a READ_ONLY auditor with the code excerpt and measured outputs INLINE - 0 tool calls, 65k tokens, complete rulings, three seat severities upgraded and two defects the seat had missed. Verdict ACCEPT_AFTER_NAMED_FIXES; the seat repaired directly. Four defects fixed under R-MIN-33/33a/33b/33c: duplicate pair names published contradictory rows; a source-declared range shipped as a point estimate the schema pins const false; unit/perimeter/period were carried and never read, so 1700 Mlbs vs 1680 kt published an INVERTED polarity and a proportionate figure was relabelled consolidated; NaN passed the numeric gate and slipped the equality withhold. Probes committed RED first (9 of 13 failing at that commit), then repaired: seven Mining suites 173 passed / 0 failed with the prior 160 all still passing, pyflakes clean, contract-delta 0 introduced / 0 inherited, ci_pack curated+exclusive+mining 7 passed. Receipt: reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md. T02 (args pre-minted) stays gated on #7905, which another seat holds DRAFT under its own R7 audit - do not poll it."
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
  MIN-W2: own PR #7950 to MERGED. It is READY at head 64a0b1dd with merge-on-green armed and
  one watcher at 600s; the independent round-3 review is consumed and its named fixes are in
  that head, so the only remaining gate is concluded green (excluded reds: the spurious
  'Workers Builds: macro', ci-authority/codex/merge-queue-pilot). Verify the module on
  origin/main after the merge - a merge is not production proof.
  MIN-W3 (T03) DISPATCHES ONLY AFTER #7950 MERGES, not merely delivers: its preflight needs
  engine/market_ontology/mining_theme_research.py to resolve on origin/main, and it appends to
  the SAME mining-economic-dossier CI block, so two PRs editing that block would conflict. Its
  args are pre-retargeted to minimax/MiniMax-M3 rounds 1 (the GLM engine collapsed 3/3 on
  09-24). Then T04b integrated, then T07. Every task takes an Opus red-team under
  freeze-then-repair, and per R-MIN-33e that commission must carry its evidence INLINE rather
  than name an artifact by path, or it spends its whole budget on discovery and returns
  nothing.
  T02 waits for #7905's content to reach main (another seat's PR - never poll it). T05/T06
  stay held for #7870's route/client/mount on main plus the answer to comment 5811889498; T08
  is last; G2 real-source admission remains an incumbent/operator act.
  Standing operator items: mini2 has no WAN (a bridge0 default route shadows the real gateway;
  the fix needs mini2 sudo and is an OPERATOR act), mini2 MiniMax provisioning, mini2 keychain
  unlock for cursor-agent. Never copy the fleet token to another host.
artifacts:
  - agentos/handoffs/GMI-MINING-2026-09-24-m1-integration.md
  - agentos/handoffs/GMI-MINING-2026-09-26-m1-integration.md
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
landmines:
  - "Shared files (issuer_profiles.py, event_workspace_build.py, receipts.py, legacy-jobs.yml, test_ci_pack.py, config/theme_sources.yml, the shared theme-research client/mount) stay owned by their incumbents and are touched only at named seams."
  - "Sparse worktrees truncate data/ and site/ on write."
  - "A new test wired into a gate:code run line without its paths: entry reds contract-delta fleet-wide."
  - "The sec_edgar public-domain rationale is not blanket clearance to republish issuer-authored bodies (addendum IR-05)."
  - "No live Freeport/MP figure may become a fixture or a native receipt before G2; a wrong-host 404 is not a privacy proof."
---

# GMI Mining — M1 integration

Seat program record. Continuity lives in the handoff above; rulings in
`research/mining/m1_integration_program/rulings/`. Modified shared files are owned by their
incumbent workstreams (`WS:GMI-THEME-GRAPH`, `WS:EARNINGS-INTELLIGENCE-OS`) and are touched only
at named seams. All rank/gate/size/originate/entry authority stays literal false.
