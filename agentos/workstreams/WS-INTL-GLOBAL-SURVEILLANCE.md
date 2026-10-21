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
  status: todo
  depends_on:
  - IM11
  - IM12
  next_action: Freeze the Paper R14 design spec, then commission the Wave 2 orchestrator with scanner packets.
- id: IM14
  title: Market dossier
  status: todo
  depends_on:
  - IM11
  - IM12
  next_action: Commission with IM13 under the frozen R14 design spec.
- id: IM15
  title: Dislocation research
  status: todo
  depends_on:
  - IM13
  next_action: Commission after Wave 2 lands; market-by-capability acceptance matrix is mandatory.
- id: IM16
  title: EM credit and dollar context
  status: todo
  depends_on:
  - IM13
  next_action: Commission with IM15.
- id: IM17
  title: Typed transmission evidence and US exposure
  status: todo
  depends_on:
  - IM15
  - IM16
  next_action: Commission after Wave 3; the frozen 11-market links graph and 14-ETF VAR stay unchanged.
- id: IM18
  title: Replay, saved investigations and watch lifecycle
  status: todo
  depends_on:
  - IM17
  next_action: Commission after Wave 4.
next_action: >
  Wave 1 MERGED (#9923 → 0062e28f, #9924 → 5d454fbe); R14 FROZEN and MERGED (#9937 → main 556d3333). Consume ORCH-2 (Wave 2 IM13+IM14 UI) and
  ORCH-3 (Wave 3 engine-side IM15+IM16) returns; seat verifies and merges; then Wave 4–5 and the §14 hard acceptance tests.
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

## Current result (2026-10-21 04:0xZ)

| Wave | Carrier | State | Evidence |
| --- | --- | --- | --- |
| W0 asset access | PR 9920 @898edecc | ready, awaiting ci-pack-0 | independent review PASS (fabric lane intl-gs-w0a-review-r1); pre-merge baseline intl.html 200, nine assets 401 |
| W0 #9596 diagnosis | read-only lane intl-gs-w0b-r1 | DIAGNOSED 5 | packs 2/3 base-stale, pack 9 PR_CAUSED (theme.css receipt), pack 0 unknown, gate downstream |
| W1 IM11/IM12 | Opus orchestrator ORCH-1 → fabric lanes W1A/W1B | MERGED (#9923 → 0062e28f, #9924 → 5d454fbe) | records under the seat kit `orch/fabric/reviews/INTL-GS-W1*.md` |
| W2 IM13/IM14 UI | Opus orchestrator ORCH-2 → fabric lanes W2F/W2A/W2B | running (spawned 05:2xZ) | frozen spec R14; evidence under `mockups/evidence/<packet>/` |
| W3 IM15/IM16 engine | Opus orchestrator ORCH-3 → fabric lanes W3A/W3B | running (spawned 05:2xZ) | engine/config/tests only; matrix counts-only |
| Design R14 | Opus orchestrator ORCH-D → Paper file 01M3P1TW5Y3XWQC37ADDS8K5AG | FROZEN + MERGED #9937 → 556d3333 (DEC:INTL-GS-R14-DESIGN-FREEZE, PR 9937) | design spec path above |
