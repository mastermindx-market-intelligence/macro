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
    DEC:INTL-GS-GB1-GRAPH-BOUNDARY-CHIP). Landed: gb1 #10354 (head ecbd01fb8cfb36b4972fca4b1b183249a0759d50,
    review INTL-GS-W2B-GB1 FAIL on the fenced-file class → seat ruling
    DEC:INTL-GS-GB1A-CLOSURE-WIDENING-ACCEPTED-20261031 → SEAT_ACCEPT) → main
    aba326f385ea19672e1a87f47e97c25e01c3b6d1 at 2026-11-01T01:03:18Z; pin1 #10355 (head
    89d7be656c772cd051f31269a749df9b2a11684f, review INTL-GS-PIN1 PASS_WITH_NOTES; chip in the Typed-edges head
    row, W2A CSS pin, specimen-scan defaults) → main 4e1ae041040e638028f9b189fe6dfe932f4eb5b1 at
    2026-11-01T02:32:05Z (verified_by: gh api graphql, aliases pullRequest(number:10354|10355) → state,
    headRefOid, mergeCommit.oid, mergedAt, 2026-11-01). §14 row 4 Graph boundary DONE: 640 data-graph-boundary
    chips served on www.mastermind-x.com/intl.html (Last-Modified 2026-11-01 03:12:25 GMT, seat curl); the pin1
    head-row wrapper was not yet served at that probe (render queued); served at the 06:1xZ probe
    (Last-Modified 05:21:32 GMT, intl-gs__edges__head = 640, chips = 640) — row 4 PRODUCTION_PROOF in full.
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
  Records r8 (2026-11-01) closed the view programme: every view/hardening lane is MERGED (W4B #10258, W3U #10265,
  W2B #10278, W2A #10288, gb1 #10354, pin1 #10355; records #10353) and §14 row 4 is served (640 chips on
  intl.html at 03:12:25 GMT); §14 recount 15 DONE / 6 PARTIAL / 0 GAP (census addendum 2026-11-01). Records r8
  merged (#10362 → f2a7fe74, 06:03:02Z); pin1 served at 05:21:32 GMT (intl-gs__edges__head = 640, r9 addendum);
  F10 state: PR #10367 MERGED → main c133b698b4960f5a2a8b4540e6b164c3c7c23e1b at 2026-11-01T07:40:51Z (head 5ac89fd395432d688e13e583d1c15591adba58b8 on claude/intl-gs-f10-canonical-main, follow-up to the reviewed 8f1b1d5e; review INTL-GS-F10 PASS_WITH_NOTES with one SHOULD-FIX fixed in the follow-up; INTL-GS-F10-AUDIT-2 PASS_WITH_NOTES at 5ac89fd3 with test-hygiene NITs N5/N6 → #10376; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed). Test-hygiene follow-up: PR #10376 MERGED → main bacc2d765488de853291dc0f8d7c545d3b3ca29a at 2026-11-01T08:29:37Z (squash commit time; GitHub's `mergedAt` field reports 09:29:37Z, one hour late — see the r11 erratum in the census; squash pinned d50f5839; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed). R2-01: PR #10384 MERGED → main 3d8ad3eb4c027126174fc2bf9f75c74f5bb04709 at 2026-11-01T08:36:34Z (squash commit time; GitHub's `mergedAt` field reports 09:36:34Z, one hour late — see the r11 erratum in the census; squash pinned ee5ce58a; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed; review INTL-GS-R2-01 PASS). §14 after records r10 (AUDIT-1 findings applied): 17 DONE / 4 PARTIAL (rows 14, 16, 18, 19) / 0 GAP; after records r11 (row 19 closed below): 18 DONE / 3 PARTIAL (rows 14, 16, 18) / 0 GAP. Remaining:
  row 18 entitled-browser journey proof on the served URL (human sign-in); row 19 — CLOSED (DONE in records r11, no longer remaining): Render run 41273744480 on the unrelated main push 886ab694 (Grey Deer risk-radar EW-P4; no intl paths; a scope=all re-render that landed as commits d3ed8141 + a68544cd) completed `success`; the served `https://www.mastermind-x.com/intl.html` (HTTP 200, Last-Modified Sun, 01 Nov 2026 09:27:22 GMT, 22,689,745 bytes) retains the Graph-boundary chip with its source-qualification split — `data-graph-boundary` 640 = 530 `structural_research` + 110 `structural_graph_member`, `intl-gs__edges__head` 640, the same figures as the 03:12:25Z proof — and the GS views: scanner (`intl-gs__table--scanner` ×10, `intl-gs__mcards` ×20), dislocations (`intl-dislocations__table` ×1) and coverage (`view=coverage` links ×60). This is the "normal subsequent publisher cycle" r8 named (a publisher run that shipped no change to the feature), so the row reads DONE. Probe: one read after run completion by the seat watcher `seat_served_proof_watch.sh` (marker `data-graph-boundary`), counts taken from the saved response. (publisher inventory: render.yml is path-filtered (templates/** with exclusions + builder/sweep scripts) and is not the only publisher: daily.yml nightly, closing-bell.yml, asia-close.yml, public-render.yml (dispatch + filtered main pushes), engine-render.yml; no pages.yml exists); rows 14/16 per
  their listed owners; dislocation job re-measured on the F10 `ci` run 41280629630 (pull_request, success, #10367 head 5ac89fd3; tested tree 92c10bd5 = that head merged into c31b2526; canonical main dd24759e), job `ci-pack-11` (id 124772193350; the entry sits in pack 11 of the plan — confirmed by a local `--plan-only` re-plan of the same manifest and by the job log). Within the pack the entry ran 06:58:09.7Z → 07:07:21.2Z = 9 min 11 s (its last group, the Chromium TAP, closes at 07:07:21.2; the dependency-environment group that follows, 07:07:24.5 → 07:07:36.0, belongs to the next entry, `international-workspace-foundation` — in this log a dependency-environment group always precedes its own entry): install browser test dependencies 13 s; the F10 canonical-main step (blob-filtered `prepare_canonical_main`) 06:58:22.9 → 06:58:52.5 = 30 s, replacing the ~4-min unrestricted fetch measured on 2026-10-31; pytest "Dislocation explorer view contracts" 27 passed in 256.84 s (4 min 17 s); Chromium "DOM and selection" TAP 10 tests / 10 pass / 0 fail, 07:03:09 → 07:07:21 (4 min 12 s). Against the entry's `timeout-minutes: 15` (raised from 8 on 2026-10-31, "kept until the job's PR-side time is re-measured") the measured PR-side time is ≈9.2 min: 15 holds with margin, 8 would still not; no budget change is proposed here. Read discipline: the job list came in ONE unpaginated page and the pack log in ONE read, both saved to the seat scratchpad; the paginated shape refused by the shared-quota guard was not repeated.; IM18 view surfaces
  + IM08/IM09 custody #8754 (never touched); Transmission tab not_built by design. R2-01, F10 and the F10 test hygiene are CLOSED (merged). Records r10: PR #10388 MERGED → main 24cea4f7dc48e33c6b103567c7813160b093d110 (GitHub mergedAt 2026-11-01T09:28:14Z; squash pinned d2ac0c56; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed; review chain INTL-GS-REC10 AUDIT-1 `FAIL` → AUDIT-2 `FAIL` (wording) → AUDIT-3 `FAIL` (one clause) → confirmation `PASS` at d2ac0c56, all read-only and non-authoring). It carries the served row-21 pack `mockups/evidence/intl-gs-r21-served/` and the r10 addendum (17/4/0). Standing: never re-spawn
  ORCH-5/ORCH-6 (message only); never relaunch a used lane run id (incl. rec8-r1, admission-refused);
  DEC:INTL-GS-FRED-GOVERNMENT-SERIES-RIGHTS asked once, never re-ask; #8754 never touch; #9596 never push;
  Opus cap 2; the 16-child grant is spent.
artifacts:
- research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md
- research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md
- research/INTL_GLOBAL_SURVEILLANCE_W5_CENSUS_2026-10-31.md
- agentos/handoffs/WS-INTL-GLOBAL-SURVEILLANCE-2026-10-31.md
- agentos/decisions/DEC-INTL-GS-FOUNDATION-TESTS-ENCODE-WORLD-STATE-NOT-INVARIANT.md
- agentos/decisions/DEC-INTL-GS-GB1-GRAPH-BOUNDARY-CHIP.md
- agentos/handoffs/WS-INTL-GLOBAL-SURVEILLANCE-2026-11-01.md
- agentos/decisions/DEC-INTL-GS-W2A-CI-BUDGET-RAISE-IS-W2A-SCOPE.md
- agentos/decisions/DEC-INTL-GS-GB1A-CLOSURE-WIDENING-ACCEPTED.md
- 'Merged PRs 2026-10-31/11-01 (heads → mergeCommits, gh-verified 2026-11-01 in one batched graphql read): #10353 ed9b641d62ab35ef997307a34a31a6d555ce6905 → 83a77d8533c6f885f6b061207d017f27cf485a78 (2026-10-31T22:57:30Z); #10354 ecbd01fb8cfb36b4972fca4b1b183249a0759d50 → aba326f385ea19672e1a87f47e97c25e01c3b6d1 (2026-11-01T01:03:18Z); #10355 89d7be656c772cd051f31269a749df9b2a11684f → 4e1ae041040e638028f9b189fe6dfe932f4eb5b1 (2026-11-01T02:32:05Z)'
- 'Merged PRs 2026-10-31 (heads → mergeCommits, all gh-verified): #10258 37d5f9b22329a16586734b7748e5f9bde7ea4c1e → 949c6adac4bc48ca7f1198b189effa86871829b2; #10274 1137a84d6c4467a936126271df55c52de8101e8e → c784d045f3a76dd944a7cd8af2936bd505b02fa5; #10276 f2c1d55fc1142515fe1cff448ae34c401b88b349 → cd195298c0748e06c80c11614c7b47c78a7e2835; #10275 673f8d333cd7bbbfb776e1517e20b245e6b7910f → 6c13414f379941be2806de2a6bf839d0b2c8f62a; #10286 92a211e1d4e07d0d1e65d76f3044f1ca210968d5 → d444ae6713b008aede6197f01989d44fa5122e4c; #10265 d7c1e9170d26dd10a8ab3907b9350dbc340111ef → 281e21c600ab5031805c33fa32711b8e02f3e53c; #10296 466243a5e11fef1b7fe743377fcebc8a804cd7ef → b3330f3cdd29ffef0260769c73764c9ce11f4a52; #10278 c2a3de654b843924dbc95f7a5b0c8b47382d4d69 → a99b539578003e7dfd32394dc1e839cba7f8bb0a; #10288 74e28ce960bfe2608de1aeeeba8221f75a73e4a2 → 92881169bb888435ab84b40740212a1fb0876a77; #10341 51b16608d57592b52d6c4b93877d65b2590a7c95 → dbaf1e07bcccf689a740ad3f1281c59ff1b9d946'
do_not_redo:
- Do not re-extract the nine-asset access repair; it is PR 9920 (reviewed PASS at 898edecc).
- Do not re-diagnose PR 9596's red packs; the classification is in the continuation handoff (DEC:INTL-GS-9596-RECONCILIATION-2026-10-21 pending as a record).
- Do not mint new rights or evidence vocabularies; extend the incumbent GMI/Semiconductors base.
- Do not re-do gb1 (#10354 → aba326f3) or pin1 (#10355 → 4e1ae041); the seat rulings DEC:INTL-GS-GB1A-CLOSURE-WIDENING-ACCEPTED-20261031 and DEC:INTL-GS-W2A-CI-BUDGET-RAISE-IS-W2A-SCOPE-20261031 are decided — re-open only on a material invalidator.
landmines:
- PR 8754 carries an egress / NO-FURTHER-REQUESTS hold and IW2 custody — never touch.
- PR 9596 is another author's draft — never push to it.
- Fabric lanes run remotely only (local sub.sh on the seat host is refused); glm-5.3 is refused for leaf labor without the honest escalation env.
- Never relaunch a used lane run id (w2a-fx5/fx6/fx7/fx7b/um1, w2a review r4/r4b/r4c/r4c2/r5/r6, rec7-r1/r2, rec7-review-r1/r2, w2b-gb1-r1/r2, w2b-gb1a-r1, w2b-gb1b-r1, w2b-gb1-review-r1, pin1-r1, pin1-review-r1, rec8-r1); an rc=75 admission refusal burns the id. Never reclaim disk on any host to clear a staging-reserve refusal (Chairman 2026-10-31).
---

# International Markets Global Surveillance

Chairman commission 2026-10-21: build the global observatory above the country cockpit (mastermind-x.com/intl.html).
Six ordered questions, three independent layers (market observations / research context / validated scoring
authority), 63-jurisdiction roster, coverage as a capability vector, four-clock observation contract and the
return identity `1+r_USD = (1+r_local)(1+r_FX)`. Roadmap and 21 hard acceptance tests live in
`research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md` (§14, §15); the running frontier lives in
`research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md`.

## Current result (2026-11-01, records r8 seat-direct; previous write 2026-10-31 by records lane intl-gs-rec7-r2)

| Wave | Carrier | State | Evidence |
| --- | --- | --- | --- |
| W0 asset access | PR 9920 @898edecc | PRODUCTION_PROOF (2026-10-21T04:06:24Z) | anonymous 200 on intl.html + nine assets; /intl_data.json still 401 |
| W1 IM11/IM12 | ORCH-1 → lanes W1A/W1B | MERGED (#9923 → 0062e28f, #9924 → 5d454fbe) | records under the seat kit `orch/fabric/reviews/INTL-GS-W1*.md` |
| W2 IM13/IM14 UI | W2F/W2A/W2B | MERGED: #9949 → e6debbb0; #10278 (W2B dossier, carries ruling-A transition) → a99b5395; #10288 (W2A scanner+coverage) → 92881169 | gh-verified mergeCommits (see wave next_actions); follow-up lane gb1 landed: #10354 → aba326f3 (2026-11-01T01:03:18Z) and pin1 #10355 → 4e1ae041 (02:32:05Z); graph-boundary chip SERVED on intl.html (640 spans, Last-Modified 2026-11-01 03:12:25 GMT) — PRODUCTION_PROOF for §14 row 4, pin1 head-row wrapper not yet served at that probe; pin1 wrapper SERVED at the 06:1xZ probe (Last-Modified 05:21:32 GMT, 640 wrappers) — row 4 served in full |
| W3 IM15/IM16 + UI | W3A/W3B (+ W3A-CONFIRM PASS @a7340535, W3B-REREVIEW PASS @37c10fc6), W3U | MERGED: #9943 → 63f3bc83; #9944 → 2d50943e; #10265 (dislocation explorer) → 281e21c6 | records `orch/fabric/reviews/INTL-GS-W3A.md`, `INTL-GS-W3B.md`, `INTL-GS-W3U.md`; IM16 gaps recorded above |
| W4 IM17 engine+UI | W4A/W4B | MERGED: #9960 → 5c6fdb2e; #10258 (presenter; production tab not_built by design) → 949c6ada | no emission-permitted candidate source |
| W5 IM18 engines + §14 closures | ORCH-5 → engine lanes | MERGED: #10274 → c784d045; #10276 → cd195298; #10275 → 6c13414f; #10286 → d444ae67; #10296 (mutant kills) → b3330f3c | W5 census 2026-10-31: 14 DONE / 6 PARTIAL / 1 GAP at base 6e721225; addendum 2026-11-01: 15 DONE / 6 PARTIAL / 0 GAP (row 4 DONE via #10354/#10355 + served proof; row 16 GAP→PARTIAL via #10276); DEFERRED F1–F9 custody in the continuation handoff |
| Design R14 | ORCH-D → Paper file 01M3P1TW5Y3XWQC37ADDS8K5AG | FROZEN + MERGED #9937 → 556d3333 (amended A1/A1.1/A1.2 2026-10-22) | design spec path above |
