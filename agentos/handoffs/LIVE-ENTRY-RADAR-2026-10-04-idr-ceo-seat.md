---
workstream: WS:LIVE-ENTRY-RADAR
session: claude/idr-records-20261004
model: fable
ended_because: ci_handoff
prs: [808, 797, 8392, 8436, 8437, 7274]
discoveries: ["DSC:GITHUB-UPDATE-BRANCH-MERGE-PUTS-THE-OLD-HEAD-FIRST", "DSC:BLOBLESS-CLONE-OBJECT-LOOKUP-ON-AN-UNKNOWN-SHA-LAZY-FETCHES"]
mission: >
  Fable CEO seat for Intraday Dislocation + Reclaim (Chairman handoff on mastermind-terminal issue 784,
  recovered 2026-10-04 from the m2 seat). This record covers the Terminal screen wave (W1 T-SCREEN),
  the EDGAR/event-prior merges, the S5 study-runner diagnosis, and the records needed for a cold
  stranger to continue without re-asking the Chairman or re-doing accepted work.
state_before: >
  D0 merged; R1-A independently accepted; R1-B v4 60-cell grid registered (never re-register).
  Terminal /dislocations screen did not exist. Macro PR 8436 (same-day 8-K collapse) and 8437
  (P-SCALE-3 stream substrate) were open; PR 8392 (EDGAR accession backfill) open; Terminal PR 797
  (intraday refresh wrapper) open. S5 study runner work-in-progress 5b1203e3d18f on ubuntu1
  lanes/wt/idr-r1b carried an eager-import fix plus a deepcopy memoization of heavy stages whose
  effect was unmeasured.
changed:
- path: research/IDR_DISLOCATIONS_SCREEN_DESIGN_SPEC_V1.md
  what: >
    Section 7 CSS amended from the first crops - .wrap takes width 100 percent, rail columns widened
    (6.25rem / 5.75rem / 4.75rem), .when/.age nowrap, new .tz micro suffix, .status wraps as a row,
    .badge nowrap, .dot and .asof defined; section 4 time markup splits digits from the zone suffix.
    Amendment paragraph dated 2026-10-04 records why (the spec, not the lane, was wrong).
- path: agentos/discoveries/DSC-GITHUB-UPDATE-BRANCH-MERGE-PUTS-THE-OLD-HEAD-FIRST.md
  what: GitHub update-branch merge commits carry the old PR head as parent 1 - re-arm checks must test parent 1.
- path: agentos/discoveries/DSC-BLOBLESS-CLONE-OBJECT-LOOKUP-ON-AN-UNKNOWN-SHA-LAZY-FETCHES.md
  what: Unknown 40-hex ids lazy-fetch and hang on blobless clones; GIT_NO_LAZY_FETCH=1 is the remedy.
verified:
- claim: Terminal PR 808 code head de2156fc368d passes the focused screen suite and type-check
  command: >
    npx vitest run components/dislocations lib/__tests__/dislocationsDisplay.test.ts
    lib/__tests__/dislocationsRoute.test.ts; npx tsc --noEmit -p tsconfig.json (ubuntu1
    lanes/wt/idr-t-screen/terminal, re-run by the seat after the repair lane returned)
  result: 47 passed (47); tsc rc=0. Full suite was 440 files / 7220 passed at bd7d6f47 before the review round.
- claim: All ten PR 808 crops are captured at the pushed head 8c5f497d2ef2
  command: TERMINAL_E2E_PORT=3311 TERMINAL_CROPS=1 npx playwright test e2e/dislocations.spec.ts --workers=1 --project=desktop --project=mobile
  result: 10 passed (16.0s); 10 PNGs changed and committed by explicit path; desktop-populated, desktop-unavailable and mobile-stale opened and judged by the seat.
- claim: The S5 runner memoization is net-negative by roughly ten times
  command: >
    python /tmp/s5_nomemo_probe.py t5d (memo disabled) versus python /tmp/s5_memo_probe.py t5d
    (memo enabled) in ubuntu1 lanes/wt/idr-r1b at 5b1203e3d18f; then the four-test subset
    "t5d or t6e or t9a or t9g" with memo disabled
  result: 38.8 s versus 384.9 s for t5d; subset 95.3 s (4 passed) against the 150 s target; one in-process s.main costs about 19 s.
- claim: Macro PR 8436 landed on main
  command: git fetch origin main; per-path blob comparison against origin/main for the four changed files
  result: SAME for engine/earnings_release/announcement_days.py, scripts/backtest_event_priors.py, engine/group_earnings.py, tests/test_event_priors.py (merge a918da3a32c8).
- claim: Macro PR 8437 merged
  command: state/watch_macro2.sh 8437 18fb72aed8ca (seat watcher, one read per 180 s)
  result: CONCLUDED_GREEN then POST_MERGE state=MERGED merge=74846b5cf731 at 2026-10-04T19:38:03Z.
- claim: Agent OS store validates with these records
  command: python3 scripts/agentos.py validate
  result: 0 error(s) (80 pre-existing review-overdue warnings).
unverified:
- claim: Terminal PR 808 is green on its update-branch head and merged
  what_would_verify: state/watch_terminal.sh 808 <head> reporting CONCLUDED_GREEN and gh pr view 808 state MERGED.
- claim: /dislocations is served live behind the shell gate
  what_would_verify: bash /opt/terminal/terminal-build.sh --target-sha <master head> on 146.190.142.17, then an anonymous GET of https://app.mastermind-x.com/dislocations returning the gate (never sign in).
- claim: The whole S5 test module runs under 240 s once the memo is removed
  what_would_verify: python /tmp/s5_nomemo_probe.py test_ on ubuntu1 lanes/wt/idr-r1b printing NOMEMO_PROBE wall under 240 s.
- claim: The P-SCALE-3 service runs with --stream-substrate on the VPS
  what_would_verify: systemctl cat macro-entry-radar-pack.service on the Macro VPS showing --stream-substrate in ExecStart after the 3-minute pull.
unresolved:
- Catalyst producer wiring (episode.catalyst from acceptance_datetime through catalyst_context/catalyst_adapters; producer episodes key in entry_radar.json) is not started - the packet freezes after PR 8392 merges.
- Macro PR 8392 (EDGAR accession backfill) open at ae96a7f264df under watcher v3.
- Terminal PR 797 open at f09ac75d483b under watcher r2 after a GitHub update-branch.
- LER-C1 PR 6625 remains EXACT_HUMAN_GATE on its own carrier.
next_actions:
- Merge Terminal PR 808 on concluded green, deploy with --target-sha, verify the anonymous gate on /dislocations.
- Commission the S5 lane to delete _memoize_heavy_stages and its four call sites while keeping the eager-import fix, commit on top of 5b1203e3d18f (never amend), then outcome-blind review, DEC, push onto the PR 7274 branch, one PR comment, run the registered study once.
- On PR 8392 merge, blob-verify the three data files plus collector and tests, then freeze the catalyst producer packet.
- On PR 797 merge, deploy with --target-sha and verify the INTRADAY_REFRESH status line.
- Prove the P-SCALE-3 service ExecStart on the VPS.
do_not_redo:
- Never re-register the R1-B v4 60-cell grid or retune it; never edit the preregs.
- Do not re-review PR 808 round 1 - the eight findings are repaired and recorded on the PR.
- Do not re-add stage memoization to scripts/research/terminal_tactical_r1b_study.py; it was measured ten times slower.
- Do not re-post the pickup or START on mastermind-terminal issue 784.
- Do not take over LER-C1 PR 6625.
- Do not rebuild the empirical consumer or create a second Radar, event, ledger, market-data or control plane.
danger_areas:
- Any edit to terminal lib/i18n.tsx breaks the sixteen EVIDENCE.yml sha pins; recapture the sha last, and the f12_9 record's capturedAtHead must point at a commit whose layout bytes carry the new hash.
- Terminal master refuses merges from a head behind master; after update-branch the head moves and the watcher must be re-armed.
- Blobless clones hang on object lookups of unknown 40-hex ids; use refs or GIT_NO_LAZY_FETCH=1.
- Sparse worktrees truncate committed artifacts on a write under data/ or site/.
- ubuntu1 admits two cursor lanes at most; a third launch is refused.
---

## Notes for the stranger

The screen branch is `claude/idr-dislocations-screen-20261004` in the Terminal repo, checked out on
ubuntu1 at `lanes/wt/idr-t-screen/terminal` (repo root one level up, so `git show <sha>:terminal/<path>`).
Lane packets live in the seat's scratchpad under `pkts/` and returns under `lanes/`; both are session-local,
so the durable facts are on the PR, in this record, and in the discoveries cited above.
