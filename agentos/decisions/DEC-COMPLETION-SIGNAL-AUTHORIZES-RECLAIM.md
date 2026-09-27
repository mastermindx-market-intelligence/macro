---
key: COMPLETION-SIGNAL-AUTHORIZES-RECLAIM
question: >
  May a storage sweeper infer that a worktree is finished from the ABSENCE of
  activity -- an idle window, no process holding its cwd, a stale reflog -- and
  on that basis delete, sparsify, or otherwise destructively alter it?
answer: >
  No. Absence of a signal may never authorize a destructive act on a shared
  worktree. Only a POSITIVE completion signal may.

  AMENDED 2026-09-27 -- this record originally named `HEAD` being an ancestor of
  `origin/main` as THE canonical signal. That test is WRONG for this repository:
  every PR is squash-merged and a squash rewrites the commit, so a cleanly merged
  branch's tip is not an ancestor of main. Measured on PR #8086 -- squash commit
  `f9425697` is an ancestor of origin/main, branch tip `0a47bc1f` is not. An
  ancestry-only gate fires for almost nothing but trees that never committed, and
  misfiles finished work as abandoned. The corrected signal is any ONE of, in the
  order `scripts/worktree_gc.py` already applied them before this record existed:
  (1) `HEAD` an ancestor of `origin/main`; (2) a MERGED PR whose `headRefOid`
  equals this tree's HEAD -- the load-bearing case, originally omitted; (3) `HEAD`
  contained in `refs/remotes/origin/<branch>` with no open PR. Unknown PR state
  fails CLOSED. A DETACHED HEAD satisfies none of the three and this law
  structurally cannot reach it -- a real gap, not a conservative default. The
  PRINCIPLE (positive signal only, never an absence) is unchanged; only its
  implementation was wrong.

  Whichever proof holds, the commits have landed, so the checkout is pure
  reproducible cache and removing it cannot lose work. The signal authorizes
  reclaiming the BYTES and nothing more: it protects the WORK,
  not the SESSION, so reclaim additionally requires that nothing is attached to
  the directory, and roots that host human-driven web conversations are never
  auto-reclaimed at all because attachment there is undetectable. Idle windows,
  live-cwd scans and
  reflog ages may be REPORTED for a human, and may narrow an already-authorized
  action, but may never be the authorization. Any sweeper that cannot establish
  the positive signal must fail closed and refuse.
rationale: >
  Idleness means two incompatible things depending on who owns the session, and a
  sweeper cannot tell them apart. A Claude Code session's shell exits between
  tool calls, so 24h of silence genuinely means dead. A ChatGPT web CONVERSATION
  (Sol review sessions, desktop-commander / studio-direct-mcp on the chatgpt1
  tunnel) resumes the instant its human replies, so silence of ANY length says
  nothing -- there is no threshold that is safe for that population.

  Measured cost of getting this wrong: on 2026-09-26 at 05:31 local, an
  idle-gated sparse sweep (`sparse_retrofit_sweep.py --apply`, host-local)
  converted 59 FULL worktrees, stripping `data/`, `site/`, `mockups/` and
  `verify_shots/` off disk. 34 were under the ungoverned mint root
  `/Volumes/Mastermind/worktrees/` -- 12 named `sol-*`, 13 `review-*`/`pr*`.
  The operator reported that essentially every ChatGPT web session died in the
  early AM and most were unrecoverable: a web session hits a path that is
  suddenly absent, cannot diagnose it, wedges, and errors cascade across the
  fleet. No commits were lost (omitted paths stay tracked in the index), but the
  SESSIONS were, which is the more expensive asset.

  The tempting wrong lesson is "the idle window was too short" -- that invites
  72h and the outage repeats. The defect is the class of signal, not its
  threshold.

  The positive signal is also strictly cheaper. It arrives for free when a PR
  squash-merges, needs no TTL, no polling, no du, and no process scan; and it
  collapses a step, because a landed tree needs no `refs/salvage/*` ref at all --
  `origin/main` already references its commits. Durability is automatic rather
  than purchased.

  Scale context that makes the mechanism necessary rather than merely correct:
  this host mints 54 worktrees/day sustained (380 in 7 days) and removes
  approximately none, because sessions do not close their own worktrees and that
  is not fixable by instruction. 93% are already born sparse (~0.45 GiB vs ~7.5
  GiB full), so birth cost is largely solved and the residual problem is pure
  accumulation. A re-measured, correctly-gated sparse sweep yields 0.0 GiB across
  the 27 remaining FULL trees, confirming sparsification was a one-time backlog
  drain and never an ongoing lever.
alternatives:
  - option: "Lengthen the idle window (72h, 7d) and keep the idleness gate"
    why_not: >
      A human-driven conversation can resume after any interval, so no threshold
      is safe. This preserves the defect and merely lowers its firing rate, which
      makes the next occurrence harder to attribute.
  - option: "Ask sessions to clean up their own worktrees"
    why_not: >
      Observed not to happen at fleet scale, and unenforceable across Claude,
      Codex, Cursor, Grok, Warp and ChatGPT-web fleets. Per-user discipline is
      the pattern GitHub explicitly replaced with org-enforced Codespaces
      retention periods and maximum idle timeouts.
  - option: "Gate on a live-process cwd scan instead of idle time"
    why_not: >
      An agent session's shell exits between tool calls, so an actively-worked
      tree frequently has no process holding its cwd and reads as dead. This was
      the original gate and it is why the idle gate was added on top.
  - option: "Push unpushed commits to GitHub, then delete the checkout"
    why_not: >
      The shared store is a blobless promisor clone, so pushing can trigger
      multi-GiB lazy fetches. `refs/salvage/*` already buys durability for ~40
      bytes per tree, and a LANDED tree needs no ref at all.
evidence:
  - "Incident receipt: ~/.local/state/mastermind/storage-cleanup/sparse-retrofit-1790425898.json -- applied=true, min_idle=None, CONVERTED 59, and the run predates the idle gate entirely"
  - "Population shape: 810 worktrees registered; 380 born in 7d = 54/day; 359 of 380 born sparse (93%)"
  - "Correctly-gated re-measure: 27 FULL trees remain, 0.0 GiB reclaimable (20 dirty, 5 unlanded, 1 active, 1 human-root)"
  - "SUPERSEDED, wrong test -- kept as the receipt of the error: 'Landed-pool census over 811 trees (landed_reaper.py, report-only): strict pool 48 trees / 73.2 GiB; 638 REFUSED as UNLANDED ... i.e. 79% of worktrees never land their work, so the bloat is unmerged WORK and no completion-signal sweeper can reach most of it.' Its only proof was HEAD-ancestry, which a squash-merge breaks; landed_reaper.py now refuses to run"
  - "Corrected census, 807 trees, PR state instead of ancestry: 318 detached / 107 open PR / 69 MERGED (misfiled by the ancestry gate) / 7 closed / 60 no-PR-in-window / 43 undecidable / 154 zero-ahead / 47 squash-matched -- real abandonment 8-14%, and the fleet ships ~61 PRs/day against ~54 trees/day minted"
  - "Squash-vs-ancestry measurement, PR #8086: `git merge-base --is-ancestor f9425697 origin/main` exit 0 (squash commit), same test on branch tip 0a47bc1f exit 1"
  - "Scope, not judgment: 580 of 807 trees (72%) sit outside config/worktree_gc.json `roots`, where worktree_gc.py refuses any target 'outside configured roots' -- /Volumes/Mastermind/agent-workspaces (354 trees, .../claude alone 462 GiB, mandated by the SSD placement policy) and /Volumes/Mastermind/worktrees (142)"
  - "Second scope defect: report-only run verdicted 364 trees / 305.2 GiB LOCKED, but 285 / 221.6 GiB carry only the content-free stamps ('mastermind-external-storage: removable volume protection' x282, 'initializing' x3); LOCKED short-circuits at worktree_gc.py:501 so landedness is never computed, and re-running the skipped checks by hand found 41 trees / 26.6 GiB clean, unoccupied and provably landed. worktree_gc.py has NO lock-reason config key, and its `worktree remove --force` at line 706 refuses a locked tree outright"
  - "Report-only run over widened roots (armed:false scratch config): SAFE_MERGED 34 / 47.9 GiB + SAFE_REMOTE 7 / 12.8 GiB = 41 trees / 60.8 GiB; kept LOCKED 364 / 305.2, DIRTY 107 / 221.3, RECENT 66 / 122.4, UNPUSHED 100 / 86.7, OPEN_PR 19 / 33.1, LIVE_PROC 7 / 27.6, ORPHAN 8 / 4.9"
  - "Reflog entry epochs of the 59: 5 had git activity within 6h of conversion; 33 were 1-3d idle; 21 were >3d"
  - "Preservation verified on a converted tree: data 62071 / site 19511 / mockups 6573 / verify_shots 445 files still tracked in the index, git status clean"
  - "Gate fix: ~/.local/lib/mastermind/storage-cleanup/sparse_retrofit_sweep.py now requires landed() and refuses HUMAN_DRIVEN_ROOTS; launchd job booted out and --apply stripped from the plist"
  - "GitHub Codespaces org-enforced retention period and maximum idle timeout: https://docs.github.com/en/codespaces/managing-codespaces-for-your-organization/restricting-the-retention-period-for-codespaces"
affects:
  - "research/WORKTREE_GC_POLICY.md"
  - "scripts/worktree_gc.py"
  - "config/worktree_gc.json"
  - "~/.local/lib/mastermind/storage-cleanup/** (host-local, not in this repo)"
confidence: high
reversibility: easy
decided_by: "session f71c3451-edd7-4e88-93d8-1fe483eac293"
decided_at: 2026-09-26
---

## The rule, in one line

**Absence of a signal never authorizes a destructive act on a shared worktree; only a positive
completion signal does — and in this squash-merge repo that signal is a MERGED PR at this
tree's exact head, NOT `HEAD` contained in `origin/main` (see AMENDED 2026-09-27 above).**

## For sweeper authors

Three enforcement points manage worktree storage, and none of them asks "is anyone still
there":

1. **At birth — cheap by default.** The `WorktreeCreate` / `SessionStart` sparse hooks
   already cover 93% of mints. The ChatGPT-web path drives raw shell and has no hook
   surface; do not chase it with instructions, let point 2 absorb it.
2. **At merge — reclaim the landed checkout.** Gate: any ONE of the three proofs in the
   AMENDED paragraph above **and** `git status --porcelain` empty **and nothing attached to the
   directory** **and the tree under a configured root**. No TTL, no idle window, no salvage
   ref. **Pool re-derived 2026-09-27 over 807 trees** — the original figure here ("48 trees /
   73.2 GiB landed-and-clean, 638 of 811 UNLANDED, so the bloat is unmerged WORK no sweeper can
   reach") came from the ancestry-only gate and was wrong: under PR state, real abandonment is
   **8–14%, not 79%**, and a report-only run over the widened roots classifies **41 trees /
   60.8 GiB reclaimable now**, plus **41 trees / 26.6 GiB clean-and-landed behind a
   content-free lock stamp** the tool short-circuits on. This IS uncollected garbage, so this
   enforcement point is the right instrument — what limited it was SCOPE (`roots`, and the
   blanket lock), not judgment. The genuinely unreachable remainder is DIRTY + UNPUSHED
   (~308 GiB of actual work) and the 318 detached lanes, which belong to `refs/salvage/*` and
   to a lane-exit receipt respectively.
3. **At a ceiling — a hard per-root population cap**, evicting landed-and-clean trees
   oldest-first. This is what converts unbounded growth into a bounded steady state.

Reporting an idle age, a live cwd, or a reflog epoch remains useful and is encouraged —
for a human reading a report, or to narrow an action the positive signal has already
authorized. It is never the authorization itself.

## Not covered by this record

267 unregistered plain `cp -r` repo snapshots holding ~806 GiB are invisible to every
control here, because all of them enumerate `git worktree list`. They are a separate
mechanism (a TTL on the snapshot roots) and are report-only today via the host-local
`orphan_copy_census.py`.
