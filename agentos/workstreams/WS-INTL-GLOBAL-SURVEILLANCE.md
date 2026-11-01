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
  status: done
  depends_on:
  - IM11
  - IM12
  pr: 10288
  next_action: >
    DONE. W2A #10288 IM13 global scanner + coverage view (Wave 2): head
    74e28ce960bfe2608de1aeeeba8221f75a73e4a2; reviews r4b PASS_WITH_NOTES, r4c2 PASS_WITH_NOTES, r6 PASS
    at head, r5 PASS_WITH_NOTES at 39b40490 (canonical reviews/INTL-GS-W2A.md) — MERGED to main
    92881169bb888435ab84b40740212a1fb0876a77 at 2026-10-31T21:54:40Z (verified: gh pr view 10288
    --json state,mergeCommit,mergedAt,headRefOid → MERGED, mergeCommit 92881169bb8…, 2026-10-31T21:54:40Z).
    Carried the CI budget raise international-workspace-browser 12→20 plus its tests/test_ci_pack_semantic.py
    pin update under DEC:INTL-GS-W2A-CI-BUDGET-RAISE-IS-W2A-SCOPE-20261031 (c1); main #10341 raised
    international-dislocation-explorer 8→15 separately (verified same command on 10341 → MERGED
    dbaf1e07bc…, 2026-10-31T20:08:34Z). The Transmission tab stays not_built by design (no
    emission-permitted candidate source).
- id: IM14
  title: Market dossier
  status: done
  depends_on:
  - IM11
  - IM12
  pr: 10278
  next_action: >
    DONE. W2B #10278 IM14 market dossier (head c2a3de654b843924dbc95f7a5b0c8b47382d4d69, review delta r5
    PASS_WITH_NOTES, CI 27 green; carries the DEC:INTL-GS-FOUNDATION-TESTS-ENCODE-WORLD-STATE-NOT-INVARIANT
    foundation transition) → main a99b539578003e7dfd32394dc1e839cba7f8bb0a at 2026-10-31T15:05:04Z
    (verified: gh pr view 10278 --json state,mergeCommit,mergedAt,headRefOid → MERGED a99b5395…).
    Follow-up lane intl-gs-w2b-gb1-r1 named (graph-boundary chip + R-14 sha256 pin + R-11 B8 AST scan,
    DEC:INTL-GS-GB1-GRAPH-BOUNDARY-CHIP).
- id: IM15
  title: Dislocation research
  status: done
  depends_on:
  - IM13
  next_action: >
    MERGED (engine side). PR 9943 (lane/intl-gs-w3a-r1 @a7340535, fabric review PASS + confirmation lane)
    → main 63f3bc835ab23928899ff173994a1d1db48b161c (GitHub mergeCommit read 08:31:59Z).
    engine/intl_global_dislocation.py + 917-line suite registered in the international pack.
    Board 11 (dislocation view) UI landed via W3U #10265 (head d7c1e9170d26dd10a8ab3907b9350dbc340111ef,
    review delta r7 PASS_WITH_NOTES, CI 27 green) → main 281e21c600ab5031805c33fa32711b8e02f3e53c at
    2026-10-31T12:49:14Z (verified: gh pr view 10265 --json state,mergeCommit,mergedAt,headRefOid → MERGED
    281e21c6…).
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
  status: done
  depends_on:
  - IM15
  - IM16
  next_action: >
    DONE. Engine #9960 → main 5c6fdb2ed1f013ffc008fde904e3be72b4524873 (verified: gh pr view 9960
    --json state,mergeCommit,mergedAt → MERGED 2026-10-21T11:26:07Z); presenter #10258 (head
    37d5f9b22329a16586734b7748e5f9bde7ea4c1e, review r3 PASS_WITH_NOTES) → main
    949c6adac4bc48ca7f1198b189effa86871829b2 at 2026-10-31T09:33:22Z (verified: gh pr view 10258
    --json state,mergeCommit,mergedAt,headRefOid → MERGED 949c6ada…). Presenter = lib/intl_gs_transmission_present.py
    + templates/intl_workspace/transmission.html.j2 + CI job. The production Transmission tab stays not_built
    BY DESIGN: no lib/intl_gs_transmission_view.py exists because the frozen rights matrix has no
    emission-permitted candidate source, so no admitted edge producer exists.
- id: IM18
  title: Replay, saved investigations and watch lifecycle
  status: in_progress
  depends_on:
  - IM17
  pr:
  - 10274
  - 10275
  - 10276
  - 10286
  next_action: >
    IN PROGRESS — engine half on main: #10274 watch evaluator → c784d045f3a76dd944a7cd8af2936bd505b02fa5
    (09:34:05Z, engine/intl_global_watch.py), #10276 correction receipts → cd195298c0748e06c80c11614c7b47c78a7e2835
    (09:34:28Z, engine/intl_global_correction.py), #10275 replay builder → 6c13414f379941be2806de2a6bf839d0b2c8f62a
    (09:34:43Z, engine/intl_global_replay.py), #10286 §14 closures → d444ae6713b008aede6197f01989d44fa5122e4c
    (10:45:49Z, engine/intl_global_graph_boundary.py + §14 closure tests); #10296 killed review mutants H1–H8
    (test-only, → b3330f3cdd29ffef0260769c73764c9ce11f4a52). All verified: gh pr view <n>
    --json state,mergeCommit,mergedAt,headRefOid → MERGED at each sha. Remaining: the view surfaces plus
    IM08/IM09 custody per ORCH-5 DEFERRED F1/F2/F6 (custody #8754, never touched); §14 rows 18/19/21 stay
    PARTIAL pending the nightly render + served-journey proof.
next_action: >
  Seat merges gb1 (lane intl-gs-w2b-gb1-r1) after its review; then served-journey proof on
  www.mastermind-x.com/intl.html after the nightly renders the views (Scanner / Dossier / Dislocations
  enabled; Transmission disabled-by-design); then §14 PARTIAL rows closure (rows 18/19/21). Standing:
  never re-spawn ORCH-5/ORCH-6 (message only); never relaunch a used lane run id;
  DEC:INTL-GS-FRED-GOVERNMENT-SERIES-RIGHTS asked once, never re-ask; #8754 never touch; #9596 never push;
  Opus cap 2.
artifacts:
- research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md
- research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md
- research/INTL_GLOBAL_SURVEILLANCE_W5_CENSUS_2026-10-31.md
- agentos/handoffs/WS-INTL-GLOBAL-SURVEILLANCE-2026-10-31.md
- agentos/decisions/DEC-INTL-GS-FOUNDATION-TESTS-ENCODE-WORLD-STATE-NOT-INVARIANT.md
- agentos/decisions/DEC-INTL-GS-GB1-GRAPH-BOUNDARY-CHIP.md
- 'Merged PRs 2026-10-31 (heads → mergeCommits, all gh-verified): #10258 37d5f9b22329a16586734b7748e5f9bde7ea4c1e → 949c6adac4bc48ca7f1198b189effa86871829b2; #10274 1137a84d6c4467a936126271df55c52de8101e8e → c784d045f3a76dd944a7cd8af2936bd505b02fa5; #10276 f2c1d55fc1142515fe1cff448ae34c401b88b349 → cd195298c0748e06c80c11614c7b47c78a7e2835; #10275 673f8d333cd7bbbfb776e1517e20b245e6b7910f → 6c13414f379941be2806de2a6bf839d0b2c8f62a; #10286 92a211e1d4e07d0d1e65d76f3044f1ca210968d5 → d444ae6713b008aede6197f01989d44fa5122e4c; #10265 d7c1e9170d26dd10a8ab3907b9350dbc340111ef → 281e21c600ab5031805c33fa32711b8e02f3e53c; #10296 466243a5e11fef1b7fe743377fcebc8a804cd7ef → b3330f3cdd29ffef0260769c73764c9ce11f4a52; #10278 c2a3de654b843924dbc95f7a5b0c8b47382d4d69 → a99b539578003e7dfd32394dc1e839cba7f8bb0a; #10288 74e28ce960bfe2608de1aeeeba8221f75a73e4a2 → 92881169bb888435ab84b40740212a1fb0876a77; #10341 51b16608d57592b52d6c4b93877d65b2590a7c95 → dbaf1e07bcccf689a740ad3f1281c59ff1b9d946'
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

## Current result (2026-10-31, records lane intl-gs-rec7-r2)

| Wave | Carrier | State | Evidence |
| --- | --- | --- | --- |
| W0 asset access | PR 9920 @898edecc | PRODUCTION_PROOF (2026-10-21T04:06:24Z) | anonymous 200 on intl.html + nine assets; /intl_data.json still 401 |
| W1 IM11/IM12 | ORCH-1 → lanes W1A/W1B | MERGED (#9923 → 0062e28f, #9924 → 5d454fbe) | records under the seat kit `orch/fabric/reviews/INTL-GS-W1*.md` |
| W2 IM13/IM14 UI | W2F/W2A/W2B | MERGED: #9949 → e6debbb0; #10278 (W2B dossier, carries ruling-A transition) → a99b5395; #10288 (W2A scanner+coverage) → 92881169 | gh-verified mergeCommits (see wave next_actions); follow-up lane gb1 pending |
| W3 IM15/IM16 + UI | W3A/W3B (+ W3A-CONFIRM PASS @a7340535, W3B-REREVIEW PASS @37c10fc6), W3U | MERGED: #9943 → 63f3bc83; #9944 → 2d50943e; #10265 (dislocation explorer) → 281e21c6 | records `orch/fabric/reviews/INTL-GS-W3A.md`, `INTL-GS-W3B.md`, `INTL-GS-W3U.md`; IM16 gaps recorded above |
| W4 IM17 engine+UI | W4A/W4B | MERGED: #9960 → 5c6fdb2e; #10258 (presenter; production tab not_built by design) → 949c6ada | no emission-permitted candidate source |
| W5 IM18 engines + §14 closures | ORCH-5 → engine lanes | MERGED: #10274 → c784d045; #10276 → cd195298; #10275 → 6c13414f; #10286 → d444ae67; #10296 (mutant kills) → b3330f3c | W5 census 2026-10-31: 14 DONE / 6 PARTIAL / 1 GAP at base 6e721225; DEFERRED F1–F9 custody in the continuation handoff |
| Design R14 | ORCH-D → Paper file 01M3P1TW5Y3XWQC37ADDS8K5AG | FROZEN + MERGED #9937 → 556d3333 (amended A1/A1.1/A1.2 2026-10-22) | design spec path above |
