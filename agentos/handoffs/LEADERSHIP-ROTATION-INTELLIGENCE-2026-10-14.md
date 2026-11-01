---
workstream: WS:LEADERSHIP-ROTATION-INTELLIGENCE
session: claude/ssd-leadership-rotation-fable-ea1aa1-e607a9aeaf45c29e (seat 135304d0, SSD tree)
model: fable
ended_because: complete
mission: >-
  Programme completion for Rotation Command / Sector Central (Chairman masterplan zip
  2026-10-13, task graph T01–T26). Updated 2026-10-14 ~20:00Z: waves 1–4 MERGED+LANDED
  (contracts, evidence modes, replay isolation, science protocol + prereg V1/V2, measured read,
  journey, counter-cases, challenge repair packets A–D with Terminal D in production); wave 5
  (harness repair under prereg V2.1) MERGED+LANDED 2026-10-14 (#9380 → c55b54dab056); T26 four states
  recorded in research/LEADERSHIP_ROTATION_T26_CLOSEOUT_2026_10_14.md.
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
  DONE 2026-10-14: ORCH-REPAIR return consumed; #9380 merged exact-head → c55b54dab056; baseline 38627611213
  SUCCESS → MEASURED_PRODUCT_COMPLETE = COMPLETE; T12R SIZED 42/42; T13R all NOT_EXECUTABLE; V3 not
  triggered by V2 rules. The #9380 merged head is CI-authority-frozen until one green main ci.yml run on a
  descendant (baseline 38648008782 @51865d51 completed SUCCESS 2026-10-14T23:20:01Z — freeze CLEARED); never re-dispatch over a live run.
- >-
  Follow-on LR-W6 (not in this masterplan): author PREREG V3 (own blob pin) re-registering H1 (statistic
  not T_a ≡ 5 by construction) and H2/H3 effect scales vs margins; re-run size+power; only SIZED+POWERED
  authorises a P1 read. Until then P1/P2/P3 stay unread (DEC:LEADERSHIP-ROTATION-P1-WITHHELD-UNTIL-STATISTICS-REREGISTERED).
- >-
  Terminal D visual acceptance: crop matrix + `qualify_sector_rotation.cjs` not executed (lane-only
  claims); signed-in visual pass is a human gap — never call D visually accepted.
- >-
  T18 natural-consumption proof waits on the first nightly publishing `measured_read` and
  `meta.rs_history` (never dispatch daily.yml). T24 conditional; T25 release/operator readback
  (human). Final comment on Mastermind #1194 with the four T26 states.
- >-
  Latent nonblocking repair candidates from ORCH-REVIEW (route as ordinary follow-ups): negative-count
  guard in `from_leadership_receipt` (no production caller), unhashable member-id TypeError,
  vacuous `groupsOk` on `groups:[]`, no test pinning D's 128-row cap, B README/receipt A44 wording.
- Lab cleanup report-first on ubuntu1 (`~/lanes/wt/lr-rev-d/` hardlinked node_modules) — no deletions while lanes may be active.
do_not_redo:
- >-
  T01 frontier, T02 qualification of #8412/#8476/#881 (recorded in the seat's judge files).
- >-
  Waves 1–4 are MERGED+LANDED (SHAs in the WS record do_not_redo): never re-ACK, re-START or re-spec;
  a fresh session is not a material invalidator.
- >-
  Terminal D #1003 → 73a935e0 on master has PRODUCTION_PROOF (VPS terminal-build.sh identity check,
  served data-dpl-id at edge 18:52Z). Never relaunch terminal-build.sh; Vercel deployment failures are
  the known spurious surface, production is the VPS.
- >-
  ORCH-SRC/MEAS/SCI/PROD/CHAL/FIX/REVIEW are COMPLETE and ORCH-REPAIR is RUNNING (a1122618ebecf481a):
  never re-spawn any of them; SendMessage only. Returns under the seat scratchpad `returns/`.
- >-
  C #9368 attempt-1 red was hosted-runner slowness (DSC:A-SIX-MINUTE-JOB-BUDGET-SITS-INSIDE-HOSTED-RUNNER-VARIANCE),
  not a defect; attempt 2 green. Do not open a heal for it.
- >-
  Never push to merged branches; never touch sol/* carriers (#8299, #7976, #9035, #9256, #9134),
  #7455, holds #7060/#8713.
danger_areas:
- Every lane PR is a CI-authority edit (legacy-jobs.yml / scripts/**) so candidate-era proof cannot
  excuse an inherited red; the clearing lever is a green main baseline postdating the red. Edit a
  CI-authority PR body ONCE per run (combine with the ready act).
- Any PR adding a module into the LRS/countercases import closure must add it to the job's `paths:`
  in `.github/ci/legacy-jobs.yml` in the same PR, or the job silently stops running those tests.
- >-
  `tests/test_rotation_early_context.py::test_registry_contains_separate_explicit_context_groups`
  fails in a SPARSE tree (data/ omitted) — artifact, not a regression; CI full checkout is green.
- >-
  `unrun-grading-board` has a 6-minute budget inside hosted-runner variance (3x between VMs):
  compare step wall time with a sibling before attributing a timeout red to the PR; remedy = re-run.
- Writes into data/ or site/ in a sparse tree truncate committed artifacts; builders must redirect to
  scratch art_dir.
- F1/F3 are settled by V2 §3/§5 per V2.1 §5 (blob 8f48509b); never edit V1/V2/V2.1 in place — any change is a dated V3 with its own blob pin.
prs: [9224, 9225, 9240, 9245, 9288, 9250, 9251, 9258, 9293, 9327, 9332, 9345, 9257, 9271, 9368, 9371, 9372, 9205, 9380, 9386]
---

# LEADERSHIP-ROTATION-INTELLIGENCE — handoff 2026-10-14 (wave 1 at CI rung)

Wave 1 delivered three DRAFT→READY PRs from two Opus orchestrators (ORCH-SRC: T02/T06/T16;
ORCH-MEAS: T03–T05/T08) over M2 fabric lanes. Seat judged each diff against the acceptance matrix
and the contracts spec before arming. Wave 2 (science) and wave 3 (product) orchestrators are
running; the challenge wave is drafted and waits for an Opus slot.

## Update 2026-10-14 ~20:00Z — waves 1–4 landed, wave 5 in flight

Waves 1–3 merged and landed blob-for-blob (SHAs in the WS record). The independent challenge
wave (ORCH-CHAL, T19/T23) ruled H1 **P0 DEVELOPMENT_FAIL: MIS-SIZED** under prereg V1 and produced
a BLOCKING set that ORCH-FIX repaired as packets A–D; all four are merged and landed, and Terminal D
is in production on the VPS (deployment identity verified at the edge). An independent fabric
re-review (ORCH-REVIEW, four M2 lanes, no native reviewer) returned ACCEPT_WITH_NONBLOCKING_GAPS on
every packet, so MEASURED_PRODUCT_COMPLETE is supportable on code pending main baseline
38627611213. The science side is a recorded FAIL plus a repair protocol (prereg V2, blob
1fcd151c; DEC:LEADERSHIP-ROTATION-PREREG-V2-NOISE-REFERENCED-H1); ORCH-REPAIR is building the
harness repair (F9 size gate, real look_count, PREREG V2.1) — no P1/P2 read until it lands and
re-size passes. PREDICTIVE_CAPABILITY_QUALIFIED = NO. ORIGINAL_PROGRAMME_COMPLETE = NOT COMPLETE.
