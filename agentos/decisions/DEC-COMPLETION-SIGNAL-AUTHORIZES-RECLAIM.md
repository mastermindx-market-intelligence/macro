---
key: COMPLETION-SIGNAL-AUTHORIZES-RECLAIM
question: >
  May a storage sweeper infer that a worktree is finished from the ABSENCE of
  activity -- an idle window, no process holding its cwd, a stale reflog -- and
  on that basis delete, sparsify, or otherwise destructively alter it?
answer: >
  No. Absence of a signal may never authorize a destructive act on a shared
  worktree. Only a POSITIVE completion signal may, and the canonical one is
  `HEAD` being an ancestor of `origin/main`: the commits have landed, so the
  checkout is pure reproducible cache and removing it cannot lose work. That
  signal authorizes reclaiming the BYTES and nothing more: it protects the WORK,
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
  - "Landed-pool census over 811 trees (landed_reaper.py, report-only): strict pool 48 trees / 73.2 GiB; 638 REFUSED as UNLANDED; 87 landed-but-dirty; 26 not on disk; 7 tracked-only-gate; 4 fail-closed -- i.e. 79% of worktrees never land their work, so the bloat is unmerged WORK and no completion-signal sweeper can reach most of it"
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

**Absence of a signal never authorizes a destructive act on a shared worktree; only
`HEAD` contained in `origin/main` does.**

## For sweeper authors

Three enforcement points manage worktree storage, and none of them asks "is anyone still
there":

1. **At birth — cheap by default.** The `WorktreeCreate` / `SessionStart` sparse hooks
   already cover 93% of mints. The ChatGPT-web path drives raw shell and has no hook
   surface; do not chase it with instructions, let point 2 absorb it.
2. **At merge — reclaim the landed checkout.** Gate: `HEAD ⊆ origin/main` **and**
   `git status --porcelain` empty **and nothing attached to the directory**. No TTL, no idle
   window, no salvage ref. Measured pool: 48 trees / 73.2 GiB — necessary, and nowhere near
   sufficient, because 638 of 811 trees are UNLANDED. That bucket belongs to
   `refs/salvage/*` (which decouples preserving commits from freeing checkouts for ~40 bytes
   each), and ultimately to reducing how many lanes open that never merge.
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
