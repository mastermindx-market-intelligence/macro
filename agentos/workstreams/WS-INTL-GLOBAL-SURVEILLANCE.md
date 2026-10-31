---
key: INTL-GLOBAL-SURVEILLANCE
title: International Markets Global Surveillance observatory (Chairman masterplan 2026-10-21)
objective: Deliver a global market observatory above the existing country research cockpit — a 63-jurisdiction
  versioned universe with coverage as a capability vector, a four-clock qualified observation contract with the
  USD/local/FX return identity, a global scanner, market dossiers, dislocation research, typed transmission
  evidence into US exposure and replay/saved/watch lifecycle — each wave landed as reviewed PRs with served
  anonymous and entitled journeys proven on www.mastermind-x.com.
status: active
program: international-risk-intelligence
repos:
- macro
owner: Fable Meta-CEO seat (International Markets Global Surveillance)
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
- WS:PAPER-INTERNATIONAL-WAVES
owns_paths:
- research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md
- research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md
waves:
- id: IM-W0
  title: Wave 0 — access reconciliation and served journey verification
  status: done
  next_action: Done — PR 9920 merged at 898edecc (main 3217a6cc); anonymous 200 proven 2026-10-21T04:06Z on
    intl.html plus the nine assets, /intl_data.json still 401. PR 9596 reconciliation recorded
    (DEC:INTL-GS-9596-RECONCILIATION-2026-10-21); 9596 and the 8754 egress hold untouched.
- id: IM11
  title: Global coverage contract — versioned 63-jurisdiction universe, capability vector, source-rights matrix
  status: done
  depends_on:
  - IM-W0
  next_action: >
    MERGED. PR 9924 (lane/intl-gs-w1a-r1 @d7b22af3, fabric review PASS r2) → main 5d454fbeb43e;
    main-baseline watch is the combined-CI proof.
- id: IM12
  title: Qualified global observation contract — four clocks, basis, return identity, abstain states, adapters
  status: done
  depends_on:
  - IM-W0
  next_action: >
    MERGED. PR 9923 (lane/intl-gs-w1b-r1 @ed363c27, fabric review PASS r2) → main 0062e28f3d00;
    shared-ID reconciliation with IM11 rides the Wave 2 foundation lane.
- id: IM13
  title: Global scanner
  status: in_progress
  depends_on:
  - IM11
  - IM12
  next_action: >
    Foundation LANDED: W2F PR 9949 (lane/intl-gs-w2f-r2, squash at exact head
    b54f351806383325c54316805ce836dd1a96f918) MERGED by seat → main
    e6debbb05b47b518f0a39f4dbf9d26f95f9c7fa7 (2026-10-22T14:29:15Z) after the FX5→FX7 repair chain
    (r7 FIX_REQUIRED @0f7d22b1, r8 PASS @b5968661, r9 PASS @b54f3518). W2A (intl-gs-w2a-r1) running
    in the 14:3xZ burst under ORCH-2.
- id: IM14
  title: Market dossier
  status: in_progress
  depends_on:
  - IM11
  - IM12
  next_action: >
    Foundation LANDED with IM13 (PR 9949 → main e6debbb0, 2026-10-22T14:29:15Z). W2B (intl-gs-w2b-r1)
    running in the 14:3xZ burst under ORCH-2.
- id: IM15
  title: Dislocation research
  status: done
  depends_on:
  - IM13
  next_action: >
    MERGED (engine side). PR 9943 (lane/intl-gs-w3a-r1 @a7340535, fabric review PASS + confirmation lane)
    → main 63f3bc835ab23928899ff173994a1d1db48b161c (GitHub mergeCommit read 08:31:59Z).
    engine/intl_global_dislocation.py + 917-line suite registered in the international pack.
    Board 11 (dislocation view) UI rides W3U (templates/intl_workspace/dislocations.html.j2, R14 board 9),
    running in the 14:3xZ burst under ORCH-4.
- id: IM16
  title: EM credit and dollar context
  status: done
  depends_on:
  - IM13
  next_action: >
    MERGED (engine side). PR 9944 (lane/intl-gs-w3b-r1 @37c10fc6, fabric review PASS r2) → main
    2d50943eb154430efda02ffc117bb37b5addc242 (GitHub mergeCommit read 08:42:08Z). Board 12 UI rides a later UI wave. Engine-side only: engine/intl_global_dollar_credit.py + engine/intl_global_acceptance_matrix.py
    (counts-only matrix). Honest gaps (no invented coverage): cds_5y no_admitted_source for all 63;
    DTWEXBGS/DFII10/ICE-BofA series have no rights-matrix row → rights_unconfirmed
    (DEC:INTL-GS-FRED-GOVERNMENT-SERIES-RIGHTS proposed); dollar_funding_external and
    us_exposure_transmission unavailable for all 63; local_rates_credit partial 5 / unavailable 58;
    im16_complete=False by fact.
- id: IM17
  title: Typed transmission evidence and US exposure
  status: in_progress
  depends_on:
  - IM15
  - IM16
  next_action: >
    Engine half LANDED: W4A PR 9960 (lane/intl-gs-w4a-r1 @8aa58025, fabric review PASS r4, 0 blocking / 5 NITs)
    MERGED by seat at the exact head → main 5c6fdb2ed1f013ffc008fde904e3be72b4524873 (GitHub mergeCommit read 11:26:07Z):
    engine/intl_transmission_evidence.py, config/intl_transmission_channels_v1.json, NEW exclusive CI job
    international-transmission-evidence (+ its tests/test_ci_pack.py curated pin). Frozen 11-market links graph and
    14-ETF VAR unchanged (empty diff; AST scan finds no import). Gaps by fact: every documented-exposure value is
    null (withheld, never 0) because bis.statistics / imf.data / ishares / licensed_feed rights are unresolved and
    us_treasury_tic / us_census_trade / usda_fas have no rights row; broad_usd / us_rates ride IM16 keys with null
    rights_ref; leverage_liquidity abstains; only the two frozen house models can display. W4B UI
    (templates/intl_workspace/transmission.html.j2, 8 crops) RUNNING — launched in the 14:3xZ burst after the
    seat messaged "W2 ON MAIN e6debbb05b47b518f0a39f4dbf9d26f95f9c7fa7" (ORCH-4 fires W4B, then W3U).
- id: IM18
  title: Replay, saved investigations and watch lifecycle
  status: todo
  depends_on:
  - IM17
  next_action: Commission after Wave 4.
next_action: >
  W2 foundation MERGED (#9949 @b54f3518 → main e6debbb05b47b518f0a39f4dbf9d26f95f9c7fa7, 2026-10-22T14:29:15Z,
  after the FX5→FX7 repair chain); DEC R14 amended A1/A1.1/A1.2 (pure theme derivations, radius fallbacks,
  light series inks). Burst launched 14:3xZ on the signal "W2 ON MAIN e6debbb0… + ISSUE GRANT": ORCH-4
  (Opus suborchestrator a93f43c8031ad627a) fires W4B (templates/intl_workspace/transmission.html.j2, IM17 UI)
  then W3U (templates/intl_workspace/dislocations.html.j2, R14 board 9); ORCH-2 (a700b1ec0d7c6f480) fires W2A
  (intl-gs-w2a-r1) and W2B (intl-gs-w2b-r1). All four are fabric OPERATOR lanes (glm-5.3 domain_orchestration)
  that delegate C0/C1 leaves to fabric WORKERS under ONE shared root child grant (child-limit 16, ttl 7200 s,
  issuable once per root d7c4f490 for the programme's life). Each lane returns one draft PR; the seat reviews
  verdict files, arms one watcher per PR and merges pinned to the full sha. Then the §14 acceptance matrix
  (21 tests) and the served-journey proof on mastermind-x.com/intl.html; Wave 5 after Wave 4 merges.
artifacts:
- research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md
- research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md
do_not_redo:
- Do not re-extract the nine-asset access repair; it is PR 9920 (reviewed PASS at 898edecc).
- Do not re-diagnose PR 9596's red packs; the classification is in the continuation handoff (DEC:INTL-GS-9596-RECONCILIATION-2026-10-21 pending as a record).
- Do not mint new rights or evidence vocabularies; extend the incumbent GMI/Semiconductors base.
landmines:
- PR 8754 carries an egress / NO-FURTHER-REQUESTS hold and IW2 custody — never touch.
- PR 9596 is another author's draft — never push to it.
- Fabric lanes run remotely only (local sub.sh on the seat host is refused); glm-5.3 is refused for leaf labor without the honest escalation env.
---

# International Markets Global Surveillance

Chairman commission 2026-10-21: build the global observatory above the country cockpit (mastermind-x.com/intl.html).
Six ordered questions, three independent layers (market observations / research context / validated scoring
authority), 63-jurisdiction roster, coverage as a capability vector, four-clock observation contract and the
return identity `1+r_USD = (1+r_local)(1+r_FX)`. Roadmap and 21 hard acceptance tests live in
`research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md` (§14, §15); the running frontier lives in
`research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md`.

## Current result (2026-10-22 14:3xZ)

| Wave | Carrier | State | Evidence |
| --- | --- | --- | --- |
| W0 asset access | PR 9920 @898edecc | PRODUCTION_PROOF (2026-10-21T04:06:24Z) | anonymous 200 on intl.html + nine assets; /intl_data.json still 401 |
| W0 #9596 diagnosis | read-only lane intl-gs-w0b-r1 | DIAGNOSED 5 | packs 2/3 base-stale, pack 9 PR_CAUSED (theme.css receipt), pack 0 unknown, gate downstream |
| W1 IM11/IM12 | Opus orchestrator ORCH-1 → fabric lanes W1A/W1B | MERGED (#9923 → 0062e28f, #9924 → 5d454fbe) | records under the seat kit `orch/fabric/reviews/INTL-GS-W1*.md` |
| W2 IM13/IM14 UI | Opus orchestrator ORCH-2 → fabric lanes W2F/W2A/W2B | foundation MERGED (#9949 @b54f3518 → e6debbb0, 2026-10-22T14:29:15Z); W2A/W2B running in the 14:3xZ burst | frozen spec R14 + seat amendments A1/A1.1/A1.2 (DEC:INTL-GS-R14-DESIGN-FREEZE); evidence under `mockups/evidence/intl-gs-w2f/{shell,states}/` |
| W3 IM15/IM16 engine | Opus orchestrator ORCH-3 → fabric lanes W3A/W3B (+ W3A-CONFIRM, W3B-REREVIEW) | RETURNED + LANDED; #9943 → 63f3bc83; #9944 → 2d50943e; W3U dislocations UI (R14 board 9) running in the burst | records `orch/fabric/reviews/INTL-GS-W3A.md`, `INTL-GS-W3B.md`; IM16 gaps recorded above |
| W4 IM17 engine+UI | Opus orchestrator ORCH-4 → fabric lanes W4A/W4B | W4A RETURNED + LANDED (#9960 → 5c6fdb2e); W4B RUNNING in the 14:3xZ burst (ORCH-4 fires W4B, then W3U) | NEW exclusive CI job; frozen models read-only |
| Design R14 | Opus orchestrator ORCH-D → Paper file 01M3P1TW5Y3XWQC37ADDS8K5AG | FROZEN + MERGED #9937 → 556d3333 (DEC:INTL-GS-R14-DESIGN-FREEZE, PR 9937; amended A1/A1.1/A1.2 2026-10-22) | design spec path above |
