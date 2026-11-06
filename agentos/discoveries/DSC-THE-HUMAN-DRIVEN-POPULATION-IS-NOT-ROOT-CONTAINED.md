---
key: THE-HUMAN-DRIVEN-POPULATION-IS-NOT-ROOT-CONTAINED
claim: >
  The `human_driven_roots` deny-list is root-based, and the human-driven checkouts on this host
  are NOT all root-contained: measured 2026-09-29 over 790 registrations, `/Volumes/Mastermind/
  agent-workspaces` holds `claude` (292 registrations — the planned widening target), `sol` (29)
  and `review` (16) as sibling directories, plus at least 8 LOOSE `*-sol` trees and one `web`
  tree registered as DIRECT children of the parent, interleaved with the widening target. No root
  contains those loose trees without also containing `claude`, so no deny-list entry can exclude
  them. Widening `roots` to `…/agent-workspaces/claude` puts 292 registrations in scope; widening
  to the PARENT `…/agent-workspaces` puts 352 in scope and pulls in 45 deny-listed registrations
  plus the 9 that no deny-list can cover.
falsifier: >
  `git worktree list --porcelain | awk '/^worktree /{print substr($0,10)}' | grep
  "^/Volumes/Mastermind/agent-workspaces/" | awk -F/ '{print $5}' | sort | uniq -c | sort -rn`.
  If every entry is one of `claude`, `sol`, `review`, the population is root-contained and this is
  false. Measured 2026-09-29: 292 claude, 29 sol, 16 review, 4 proof, 1 web, 1 maintenance,
  1 macro, and 8 individually-named `*-sol` trees.
so_what: >
  "Widen by subtree, never by parent or volume" is not a stylistic preference for these 9 trees —
  it is the ONLY thing protecting them, because the deny-list structurally cannot. Treat the
  subtree rule as load-bearing on its own evidence and never relax it on the grounds that "the
  deny-list will catch it": for the loose trees it cannot, and the difference between the safe
  widening and the dangerous one is a single path segment. Two further measurements that bear on
  the same decision: `…/agent-workspaces/tmp`, named in the current widening proposal, holds 32
  directory entries and ZERO registrations, and `scan_orphans` skips any root not under a host
  checkout, so an absolute root contributes no orphans either — naming `tmp` is fully inert, with
  neither yield nor risk, and the widening proposal can drop it without loss.
kind: constraint
verified_at: 2026-09-29
verified_by: >
  `git worktree list --porcelain` over 790 registrations of the macro clone; per-root counts via
  `grep -c "^<root>/"`; `scripts/worktree_gc.py` `scan_orphans` (`if not any(_under(root, h) for h
  in hosts): continue`) and `human_driven_protection`/`expand_roots`; `config/worktree_gc.json`
  `human_driven_roots` = the three absolute roots, `include_orphans: false`.
scope:
  - macro
  - config/worktree_gc.json
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---

## The shape, which is the whole point

```
/Volumes/Mastermind/agent-workspaces/
├── claude/      292 registrations   ← the planned widening target
├── sol/          29                 ← deny-listed
├── review/       16                 ← deny-listed
├── proof/         4
├── web/           1                 ← human-driven, NOT deny-listed
├── maintenance/   1
├── macro/         1
├── us-sector-membership-reconcile-20260917-sol        ← loose, human-driven,
├── sol-seasonality-watch-repair-20260915                 NOT deny-listed, and
├── sol-seasonality-watch-noread-20260916                 NOT coverable by any
├── sol-daily-engine-precode-recovery-20260915            root that also contains
├── sector-intelligence-freshness-20260917-sol            `claude/`
├── prophet-turn-watch-row-evidence-v2-sol-20260916
├── prophet-four-market-recovery-sol-20260915
└── family-b-b0-row-repair-20260916-sol
```

A deny-list is a list of ROOTS. To exclude a loose sibling of the widening target you would need
a root that contains the sibling and not `claude/` — and the only such root is the sibling's own
full path, one entry per tree, re-derived every time the fleet mints another one. That is not a
deny-list; that is a second registry, and it would go stale the same day.

## Why this is easy to get wrong in exactly one keystroke

The safe widening and the dangerous one differ by one path segment:

| written as | registrations in scope | human-driven pulled in |
|---|---:|---:|
| `/Volumes/Mastermind/agent-workspaces/claude` | 292 | 0 |
| `/Volumes/Mastermind/agent-workspaces` | 352 | 45 deny-listed + 9 uncoverable |

The shorter string is the one a person writes when they are thinking "add the SSD workspaces",
and it reads as obviously correct. The deny-list turns 45 of those 54 into refusals. It cannot
help with the other 9.

Related: `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT` (why the widening buys
reporting rather than deletion until the belt is repaired — which is also why the belt repair and
the widening must not land in the same commit).
