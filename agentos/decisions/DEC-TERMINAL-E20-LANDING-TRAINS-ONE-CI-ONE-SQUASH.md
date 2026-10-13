---
key: TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH
question: >
  The terminal-enhancements20 program (WS:TERMINAL-ENHANCEMENTS20) has twenty reviewed
  feature pull requests converging on a master branch protected by strict up-to-date
  status checks (three required contexts, roughly 25-40 minutes per CI run, no merge
  queue). Landing them one at a time puts every other armed PR BEHIND after each squash
  and forces a fresh full CI cycle per survivor, with merge-on-green controller refreshes
  racing one another. How do accepted heads reach master?
answer: >
  Accepted heads land in LANDING TRAINS. A train is a fresh branch
  claude/e20-landing-train-N cut from origin/master into which each constituent head that
  has an ACCEPT review at that exact sha is merged with `git merge --no-ff <sha>` in
  dependency order. The train recaptures its evidence packets, runs tsc, the plain-language
  guard, the full vitest suite, pytest in PR mode and cold Playwright on the three
  viewports (1440x900, 820x1180, 390x844), opens ONE pull request, receives ONE independent
  read-only verify, is armed with the merge-on-green label plus native auto-merge, and
  squashes once. Its constituent PRs are then CLOSED, not merged, with the text "Landed via
  landing train #N (squash <sha>)", and the squash is deployed with
  `/opt/terminal/terminal-build.sh --target-sha <sha>` and verified live. Trains are
  pipelined: the next train assembles while the previous one waits on CI and folds the
  previous squash in with `git merge --no-ff origin/master` before its proofs and again
  before its push, so each train carries everything master landed. A pull request that
  carries a Supabase migration never rides a train
  (DEC:TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP). Trains so far: #930 squashed
  as 0e8de334d (E04 E06 E09 E11 E12; live), #936 (E10 E13 E15 E17; armed), train 3
  (E14 E18 E01 E03 E02 E08 E19 E16; assembling), train 4 (E07 E20; staged).
rationale: >
  The cost that dominates is CI wall-clock under strict up-to-date protection, not review
  or build time: with N armed PRs, serial landing costs on the order of N squared CI runs
  because every squash invalidates every other head. A train converts that into one CI
  run per train plus one verify, while keeping the per-feature independent review at an
  exact head (the train merges that exact sha, so the reviewed code is what lands) and the
  per-feature falsifier/AC evidence on each constituent PR. `--no-ff` merges keep each
  constituent's history and reviewed sha reachable from the train head for audit; the
  single squash keeps master linear as the house style expects. Closing constituents with
  the train and squash named keeps the paper trail from the feature PR to the master sha
  without a second merge. Folding origin/master mid-assembly removes the only race the
  pattern introduces (the previous train's squash landing while the next assembles).
alternatives:
  - option: "Serial merge with merge-on-green refreshing each BEHIND head."
    why_not: "Each squash reds every other armed PR's merge ref; the controller refreshes serially, so twenty PRs cost on the order of twenty-plus full CI cycles and the refreshes race each other for master."
  - option: "Enable the GitHub merge queue on master."
    why_not: "A branch-protection change outside the program's authority; AGENTS.md ties the merge-on-green controller and its tests to the exact current protection, so the change would need its own PR, tests and controller update first."
  - option: "One long-lived integration branch that builders commit to directly."
    why_not: "Loses the independent ACCEPT review at an exact per-feature head and the per-feature falsifier evidence; a red on the shared branch has no single owner."
  - option: "Merge each constituent PR itself after merging master into it."
    why_not: "Identical CI cost to serial landing; the merge commits also break the one-squash-per-feature expectation the evidence packets and the deploy marker rely on."
evidence:
  - >
    Terminal PR #930 (landing train 1) squashed as 0e8de334d carrying E04 E06 E09 E11 E12
    after one CI run and one read-only verify; the production marker d0973ef6e (read from
    /opt/terminal/terminal/.deployment-id 2026-10-11 21:07Z) is its descendant.
  - >
    Branch protection read 2026-10-11 via `gh api repos/<owner>/mastermind-terminal/branches/master/protection`:
    required contexts exactly "Quote Hub tests", "Terminal typecheck + tests",
    "Ingest + signal-layer tests"; strict up-to-date; no merge queue.
  - >
    Terminal PR #936 (train 2: E10 E13 E15 E17) armed with merge-on-green + auto-merge on
    a head refreshed onto d0973ef6e; its constituents #918 #923 #933 #938 stay open at
    their reviewed heads until the squash and are then closed with the squash sha.
  - >
    Train 3 assembly (eight constituents) started 2026-10-11 21:20Z on d0973ef6e with the
    mid-assembly `git merge --no-ff origin/master` step so the #936 squash folds in before
    its proofs and push.
affects:
  - "WS:TERMINAL-ENHANCEMENTS20"
  - "terminal-user-services"
  - ".github/workflows/merge-on-green.yml"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-11
---

## Notes for the next train operator

- A constituent joins a train only at the sha its ACCEPT review names. A later push to the
  feature branch needs a new review before the train takes it.
- The train's own verify is read-only and must describe the FINAL pushed head; if master
  moves after the push, refresh the head (merge origin/master, re-run the proofs) before
  arming rather than relying on the controller's refresh.
- Deploy only the squash on origin/master with `--target-sha`; an ancestor of the live
  marker is a rollback (see the Terminal memory `deploy-topology`).
- Taken by the program CEO session (Fable, Chairman-assigned 2026-10-11, Terminal issue 916).
