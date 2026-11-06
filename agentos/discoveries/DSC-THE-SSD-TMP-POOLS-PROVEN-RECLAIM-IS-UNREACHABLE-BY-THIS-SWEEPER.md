---
key: THE-SSD-TMP-POOLS-PROVEN-RECLAIM-IS-UNREACHABLE-BY-THIS-SWEEPER
claim: >
  Adding `/Volumes/Mastermind/tmp` to `config/worktree_gc.json` `roots` would free **zero bytes**,
  for two independent reasons that are both about the sweeper's SUBJECT SET rather than its
  permissions. (1) The 44.19 GiB that §9 proved landed, clean and unattached there is not made of
  worktree REGISTRATIONS: `pr979-macro-88804-proof` (41.76 GiB) and `prophet-7187-proof-clone-
  20260920` (2.43 GiB) are STANDALONE CLONES — each `.git` is a directory, not a gitfile — so they
  appear in no `git worktree list` output and `worktree_gc.py` has no handle on them. Its only
  route to an unregistered directory is `scan_orphans`, which at line 682 skips any root not under
  a host checkout, and `/Volumes/Mastermind/tmp` is not under one. (2) Every directory there that
  IS a registration of the macro clone — measured 2026-09-29, **17 trees / ~41 GiB** — is on a
  **DETACHED HEAD**, and a detached HEAD satisfies none of the three proofs in
  `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`, so each one fails closed no matter which root it
  sits under. About 11 GiB of those 17 is additionally HUMAN-class by marker
  (`prophet-b4-owner-archeology-20260921-sol-001` alone is 7 GiB).
falsifier: >
  `git worktree list --porcelain | grep -c '^worktree /Volumes/Mastermind/tmp'` = 17, and
  `... | grep -c 'pr979-macro-88804-proof'` = 0. `test -d
  /Volumes/Mastermind/tmp/pr979-macro-88804-proof/.git` succeeds, proving a standalone clone
  rather than a linked worktree. Per-tree state from the same porcelain stream: all 17 print
  `detached` and none prints `locked`. `scripts/worktree_gc.py:672-683` is the `scan_orphans`
  host-containment test. If any of the 17 ever reports a branch instead of `detached`, or if
  either proven candidate ever appears in the registration list, the corresponding half of this
  is false. Sizes via `du -sg` on the 17 registered paths (upper bounds — cloned blocks counted
  once per path — so treat ~41 GiB as ranking, not accounting).
so_what: >
  Do NOT propose widening `roots` to `/Volumes/Mastermind/tmp` in order to capture the 44.19 GiB.
  §9 says that reclaim "is still NOT taken, because the final clause requires the tree to sit under
  a configured root", which reads as though the root is the only thing missing; it is not, and
  ratifying that widening would spend an operator decision on a change measured to free nothing.
  The general rule is the reusable part and it is the same shape as
  `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT` one level out: **`roots` governs which
  paths a sweeper may ACT on, never which objects it can SEE.** A tool built on the worktree
  registry has no handle on a standalone clone however it is configured, and the completion-signal
  law has nothing to say about a detached HEAD however reachable it is. Before asking for a scope
  ratification, ask what the sweeper's subject set actually contains — reclaiming these two clones
  is a DIFFERENT act, needing a different tool and its own operator decision, and it should be put
  that way rather than smuggled in as a roots entry.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  `git worktree list --porcelain` over the macro clone's 789 registrations (17 under
  `/Volumes/Mastermind/tmp`, all `detached`, none `locked`); `test -d <path>/.git` on both proven
  candidates (both directories, i.e. standalone clones); `du -sg` over the 17 registered paths
  (~41 GiB, largest `prophet-b4-owner-archeology-20260921-sol-001` at 7 GiB);
  `scripts/worktree_gc.py:672-696` (`scan_orphans` and its `_under(root, h)` host-containment
  guard); `research/WORKTREE_GC_POLICY.md` §"The SSD `tmp` pool" for the 44.19 GiB figures this
  corrects the consequence of.
scope:
  - macro
  - scripts/worktree_gc.py
  - config/worktree_gc.json
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---

## Two refusals, and neither one is about permission

| candidate | bytes | why `worktree_gc.py` cannot take it |
|---|---:|---|
| `pr979-macro-88804-proof` | 41.76 GiB | standalone clone — not in any registration list; `scan_orphans` skips the root because it is not under a host checkout |
| `prophet-7187-proof-clone-20260920` | 2.43 GiB | same |
| 17 registered worktrees | ~41 GiB | all DETACHED — `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` has no proof shape that a detached HEAD can satisfy |

The first row is the one that misleads, because it is the only reclaim in that pool anyone has
*proved*. A proven-reclaimable directory and a sweepable directory are different properties, and
§9's sentence put them in the same clause.

## The registered subset, and why it is a population and not a backlog

All 17 are detached because of what they are for: integration and review snapshots minted at a
specific commit to reproduce a state, never to author one. That is the same structural class as
the 318 detached trees §9 already records on the seat roots — they ship their output from
somewhere else, so no merge will ever name them, and no amount of waiting turns them into
reclaimable trees. They need a **lane-exit receipt**, which does not exist, not a wider root.

At least five of the 17 (~11 GiB) additionally carry a `sol` or `review` marker, so the
`human_driven_roots` deny-list would have to grow a NAME rule to cover them — the gap §9 already
states for the loose `*-sol` trees at the top of `…/agent-workspaces`, present here too and for
the same reason.

Related: `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT` (the same lesson about `roots`
one level in), `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` (the proof shapes a detached HEAD
cannot meet).
