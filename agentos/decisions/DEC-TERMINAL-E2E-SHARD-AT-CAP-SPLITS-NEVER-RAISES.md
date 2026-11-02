---
key: TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES
question: >
  The Terminal CI e2e matrix in `.github/workflows/ci.yml` ran Playwright as whole
  `tablet` and `mobile` shards (desktop was already split in two) under a job
  `timeout-minutes: 60`. On recent green runs those two shards took 44-59 minutes, and
  during the terminal-enhancements20 program four heads (landing train 3's first head and
  its current head 7733e1b58, E07 #954, and #959 round 2 at 06299948f) were cancelled at
  the cap with zero failed tests, which reds every armed PR and stalls the merge-on-green
  controller. Raise the cap, or split the shards?
answer: >
  Split, never raise. Terminal PR #963 splits `tablet` and `mobile` into halves
  (`--shard=1/2`, `--shard=2/2`), mirroring the existing desktop split, so the matrix is
  desktop-1/2, tablet-1/2, mobile-1/2 and serial (check-run names "Terminal e2e <key>
  (shard)"); the shard test `tests/test_ci_e2e_shards.py` is parametrised over the new
  keys (29 passed); `timeout-minutes` stays 60; the aggregate required context
  "Terminal typecheck + tests" keeps its exact name because branch protection pins it.
  On #963's refreshed head 12a78fa3c the split shards finished in 13-32 minutes each.
rationale: >
  The cap is a guard against hung runs and a budget signal, not a tuning knob: raising it
  hides suite growth, lets one wedged run burn the whole runner slot, and the workflow's own
  comment says to split a shard that approaches the cap rather than raise the number. Halves
  run in parallel on separate runners at no added cost and halve the wall-clock, which also
  shortens every landing train's critical path under strict up-to-date protection. Cold
  full-matrix reruns of the cancelled heads on Linux hosts showed no deterministic red
  (every failure passed its serial rerun), so the reds were the cap, not defects, and no
  test needed to be touched.
alternatives:
  - option: "Raise `timeout-minutes` to 90 for the e2e jobs."
    why_not: "ci.yml's own rule is to split a shard that nears the cap and never just raise the number; it hides growth and a hung run then costs 90 minutes of runner time per occurrence."
  - option: "Drop CI workers to more than 1 or reduce retries to finish faster."
    why_not: "Workers are 1 in CI for determinism and retries are what absorb the e2e flake rotation (memory ci-e2e-flake-roulette); both changes trade a wall-clock cap for new nondeterminism."
  - option: "Run tablet and mobile only on master pushes, not on pull requests."
    why_not: "AGENTS.md requires every user-facing Terminal change verified at 1440x900, 820x1180 and 390x844 before merge; moving the proof after the merge breaks the gate."
  - option: "Delete or skip the slowest specs."
    why_not: "They are evidence gates for shipped features; weakening a test to make CI fit the cap is forbidden by the program's acceptance standard."
evidence:
  - >
    Runs 38197231252 (#959 at 06299948f) and 38199198159 (#960 at 7733e1b58): the tablet
    job concluded `cancelled` at the 60-minute cap with no failing test line in its log.
  - >
    #963 head 12a78fa3c per-shard completion (started ~04:11Z 2026-10-12): serial
    04:24:32Z, mobile-2 04:24:46Z, tablet-1 04:40:10Z, desktop-2 04:41:08Z, mobile-1
    04:41:46Z, tablet-2 04:43:37Z; unit + typecheck 04:15:36Z; Quote Hub 04:11:48Z;
    Ingest 04:12:24Z.
  - >
    Cold Linux full-matrix reruns of the train-3 head 7733e1b58 (ubuntu2) and the E07
    head 03054a695 (ubuntu0): no deterministic failure; every red case passed its
    `--last-failed` serial rerun.
  - >
    scripts/merge_on_green.py `sweep()` lines 407-409: a red verdict is marked
    merge-blocked and skipped, never refreshed, so a cap-cancelled head needs a manual
    `update-branch` once the split is on master.
affects:
  - "WS:TERMINAL-ENHANCEMENTS20"
  - ".github/workflows/ci.yml"
  - "tests/test_ci_e2e_shards.py"
  - "scripts/merge_on_green.py"
  - "terminal/e2e/**"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-12
---

## Notes for the next CI operator

- When a split half again approaches 45 minutes on green runs, split it further
  (`--shard=k/N`) and extend `tests/test_ci_e2e_shards.py`; do not touch
  `timeout-minutes`.
- A head cancelled at the cap reads as red to the observer and to the controller. After
  the split lands, refresh that PR's head by hand (`gh api -X PUT
  repos/<owner>/mastermind-terminal/pulls/<n>/update-branch -f expected_head_sha=<head>`,
  or merge origin/master into the branch and push); the controller removes
  `merge-blocked` once the fresh run is green.
- Branch protection names the aggregate job, not the shards; renaming the aggregate or
  changing the required contexts requires updating `merge-on-green.yml`, its tests and
  AGENTS.md in the same PR.
- Landing vehicle (2026-10-12 05:38Z): #963's head b1ee4676c was folded into landing
  train 3 (#960, fold head f810a5ca9) so one squash lands the split together with the
  train's eight features; #963 itself was disarmed to avoid a race under strict
  protection and stays open as the fallback until #960 squashes. Its own refreshed heads
  were held in `action_required` by the controller refresh
  (DSC:TERMINAL-CONTROLLER-REFRESH-RUN-IS-HELD-FOR-APPROVAL), which is why the fold was
  faster than waiting for it.
