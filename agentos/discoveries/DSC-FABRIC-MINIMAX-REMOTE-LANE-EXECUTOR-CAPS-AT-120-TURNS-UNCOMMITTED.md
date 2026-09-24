---
key: FABRIC-MINIMAX-REMOTE-LANE-EXECUTOR-CAPS-AT-120-TURNS-UNCOMMITTED
claim: >
  A `pool remote <mb|m1> minimax <brief> <worktree> --out <file>` construction lane runs the
  worker as `claude -p` with a hard 120-turn limit; on any brief that needs more than ~120 tool
  calls the executor stops with "Error: Reached max turns (120)" as the ONLY captured output,
  rc=1, no RETURN block, and every edit left uncommitted in the remote worktree even when the
  brief orders COMMIT EARLY / COMMIT PER ITEM. Three consecutive IAC-1 rounds (2026-09-24 mb
  lanes rs_20260924T100354Z_36984 and the two following, 7-11 minutes each) reproduced it with
  660-2310 line diffs sitting in `~/lanes/wt/<wt>` and `git log` unchanged.
falsifier: >
  Run `POOL_ORCHESTRATOR_ID=<id> pool remote mb minimax <brief-needing-more-than-120-tool-calls>
  /Users/chriswong/lanes/wt/<wt> --out /tmp/lane.out` and observe /tmp/lane.out ending with the
  brief's RETURN block, or `ssh mb 'cd ~/lanes/wt/<wt> && git log --oneline -1'` showing a new
  commit after an exit at the cap; either falsifies the claim. So does the executor exposing a
  turn budget above 120 for the minimax pool (Mastermind #959 rounds 3/4A/4B are the record).
so_what: >
  Treat the cap as the lane's real unit of work: size each brief to well under 120 tool calls
  (one or two items, tests-first), and always recover the uncommitted diff from the remote
  worktree with `git diff HEAD` before re-syncing it, because the diff is usually near-complete
  and the failing residue is small. Never read a capped lane as "no work done", and never
  re-run the same brief hoping for a return — the executor will spend the same budget the same
  way. A commit-per-item instruction is not honoured by the executor once the cap is reached.
kind: landmine
verified_at: 2026-09-24
verified_by: >
  Fable delivery principal, 2026-09-24 09:46Z-10:36Z, IAC-1 rounds 3, 4A and 4B on
  Mastermind PR #959: `--out` files remote_minimax_iac1_r3_mb.out / _r4a_mb.out / _r4b_mb.out
  each contain only "Error: Reached max turns (120)"; `ssh mb 'cd ~/lanes/wt/fable-iac1-20260924
  && git log --oneline -3 && git status --short && git diff --stat HEAD'` showed HEAD unchanged
  and 3/2/3 modified files per round; the recovered diffs passed the local gate after 3-4 line
  principal-side repairs each time (commits 95f5a87e, 42fe49d0, 884534eb).
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - ~/lanes/ext (mb, m1 remote construction lanes)
confidence: verified
---

# The MiniMax remote construction lane silently stops at 120 turns with everything uncommitted

Size briefs to the cap and always recover the remote worktree diff; the work is usually there,
the return and the commit are not.
