---
workstream: WS:LEADERSHIP-ROTATION-INTELLIGENCE
session: claude/ssd-leadership-rotation-fable-ea1aa1-e607a9aeaf45c29e (seat 135304d0, SSD tree)
model: fable
ended_because: ci_handoff
mission: >-
  Programme completion for Rotation Command / Sector Central (Chairman masterplan zip
  2026-10-13, task graph T01–T26). This handoff records wave 1 (source qualification, contract
  projection, evidence modes, replay isolation) at the CI/merge rung and the state of waves 2–3.
state_before: >-
  #8470 merged; carriers #8412 (replay isolation), #8476 (rs_history.v1) and Terminal #881
  (journey) were unmerged prior drafts on stale bases; no contracts module existed; `build_rotation_events`
  could publish a scratch art_dir run into the live site tree; `sector_cycles` carried no evidence-mode
  metadata for reconstructed leadership history.
changed:
- path: engine/leadership_rotation_context.py
  what: >-
    New pure-stdlib contracts module (PR #9240) — group_measurement / transition_observation /
    research_estimate as distinct objects; relative wealth (1+R_g)/(1+R_b)-1; breadth k/n with coverage
    and identification bounds [k/N,(k+N-n)/N]; cohort z with non_finite state; overlap/concentration;
    observation clock, confirmation maturity, rolling-window carry decomposition; reads
    sector_cycles.SECTORS only; no I/O, LLM or network. 51 exports pinned by test.
- path: tests/test_leadership_rotation_contract.py
  what: >-
    Contract suite for the module (PR #9240); wired into .github/ci/legacy-jobs.yml pack 7.
- path: engine/sector_cycles.py
  what: >-
    PR #9225 — rec["rs_history"] with schema sector_cycles.rs_history.v1, mode
    reconstructed_price_history, naturally_observed=false, as_of, min_history_sessions, source_cohort.
- path: tests/test_rotation_evidence_modes.py
  what: >-
    PR #9225 — evidence-mode assertions for reconstructed leadership history.
- path: scripts/build_rotation_events.py
  what: >-
    PR #9224 — a scratch art_dir run publishes into art_dir/site, never the live site tree;
    events load/write take data_root.
- path: engine/subsector_rotation_alerts.py
  what: >-
    PR #9224 — load_events/write_events accept data_root.
- path: tests/test_rotation_replay_isolation.py
  what: >-
    PR #9224 — replay isolation suite (A39 never invokes the real builder on the live tree).
- path: agentos/workstreams/WS-LEADERSHIP-ROTATION-INTELLIGENCE.md
  what: >-
    LR-W1 marked done with its PRs; LR-W2 and LR-W3 in_progress.
verified:
- claim: >-
    The PR files are clean under the path-prune lint; the merge-blocked red on #9224/#9225 was MAIN's.
  command: >-
    python3 - (import tests/test_no_absolute_path_part_prunes.absolute_part_prunes; run on
    `git show origin/<lane>:<file>` for every changed .py) ; git log --oneline 4f303e07..origin/main
  result: >-
    every changed file reports []; main's own failure at base 4f303e07 was healed by #9227 and
    #9234; both PRs were refreshed via `gh pr update-branch` under disarm→update→re-arm with a comment.
- claim: >-
    The lint itself passes on current main.
  command: >-
    python3 -m pytest -q tests/test_no_absolute_path_part_prunes.py
  result: >-
    3 passed.
- claim: >-
    Contracts module is stateless and import-light.
  command: >-
    grep -n "^import\|^from" engine/leadership_rotation_context.py
  result: >-
    stdlib only plus `from engine import sector_cycles` (reader of SECTORS).
unverified:
- claim: >-
    Wave-1 PRs #9224 / #9225 / #9240 are merged and landed on origin/main.
  what_would_verify: >-
    git fetch origin && per-path blob compare of each PR's files against origin/main
    (squash-tolerant); then ONE main ci.yml baseline (preflight for an in-flight run first).
unresolved:
- >-
  Terminal #881 journey re-port carries 7 conflicts against master #856 (risk feed); assigned to the
  wave-3 T18 Terminal lane, keeping both feeds.
- A26/A27 partial — no corrected-mode writer exists; assigned to the wave-4 T20 countercase lane.
- ubuntu0–3 fabric routing policy is stale (fingerprint cfe1c970 vs mb 30b5856f); GLM lanes are placed
  on mb by hand until the fabric-policy owner republishes.
next_actions:
- >-
  After the sweeper merges #9224/#9225/#9240, blob-verify each file set against origin/main.
- Dispatch ONE main ci.yml baseline only over a clear field (`gh run list --workflow ci.yml --branch main
  --json databaseId,status` shows nothing queued/in_progress).
- >-
  Close #8412 and #8476 as superseded, naming #9224 and #9225; reclaim judge trees
  lr-orch-src-judge-feb0c5f1875a112b and lr-meas-judge-f9831580b40f167b.
- Consume ORCH-SCI (T07, T09–T14) and ORCH-PROD (T17, T18, T21, T22) returns; then ORCH-CHAL
  (T19/T20/T23), T24 conditional, T25 release/natural-consumption proof, T26 four-state closeout.
do_not_redo:
- >-
  T01 frontier, T02 qualification of #8412/#8476/#881 (recorded in the seat's judge files).
- >-
  T03–T05/T08 contract projection (#9240), T06 (#9225), T16 (#9224) — accepted at CI rung.
- >-
  Never push to #9224/#9225/#9240 branches; never touch sol/* carriers, #7455, holds #7060/#8713.
danger_areas:
- All three wave-1 PRs edit .github/ci/legacy-jobs.yml in different hunks — a later one can conflict
  after an earlier merge; rebase under disarm→push→re-arm, never push into an armed PR.
- Every lane PR is a CI-authority edit (legacy-jobs.yml) so candidate-era proof cannot excuse an
  inherited red; the clearing lever is a green main baseline postdating the red.
- Writes into data/ or site/ in a sparse tree truncate committed artifacts; builders must redirect to
  scratch art_dir.
prs: [9224, 9225, 9240, 9205]
---

# LEADERSHIP-ROTATION-INTELLIGENCE — handoff 2026-10-14 (wave 1 at CI rung)

Wave 1 delivered three DRAFT→READY PRs from two Opus orchestrators (ORCH-SRC: T02/T06/T16;
ORCH-MEAS: T03–T05/T08) over M2 fabric lanes. Seat judged each diff against the acceptance matrix
and the contracts spec before arming. Wave 2 (science) and wave 3 (product) orchestrators are
running; the challenge wave is drafted and waits for an Opus slot.
