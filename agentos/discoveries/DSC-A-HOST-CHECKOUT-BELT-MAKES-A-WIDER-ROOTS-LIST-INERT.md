---
key: A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT
claim: >
  `scripts/worktree_gc.py` decides "session tree vs host checkout" from repo-RELATIVE path
  segments, never from the configured `roots`, so no path on the external SSD can ever be
  deleted no matter what `roots` says. `rel_roots` (line ~861) keeps only the entries that are
  neither absolute nor `~`-prefixed, `path_under_session_root` (line 165) matches those as
  path-segment TUPLES (`.claude/worktrees`, `.claire/worktrees`, `.codex/worktrees`,
  `.codex-worktrees`, `.cursor/worktrees`, `.grok/worktrees`, `.warp/worktrees`), and
  `host_checkouts` (line 177) calls every registration matching none of them a HOST — which
  the deletion belt at line ~688 refuses by identity ("refused — host checkout"). Since
  `/Volumes/Mastermind/...` can only be named ABSOLUTELY, every tree there is a host.
  Measured 2026-09-28 on 804 registrations: adding `/Volumes/Mastermind/agent-workspaces` and
  `/Volumes/Mastermind/worktrees` to `roots` moves `in_scope` 225 -> 721 (+496 REPORTED) and
  the belt-reachable population **225 -> 226**: exactly ONE newly deletable tree,
  `/Volumes/Mastermind/agent-workspaces/maintenance/.claude/worktrees/ssd-worktree-policy-20260906`,
  which is reachable only because it carries a `.claude/worktrees` segment of its own. This
  FALSIFIES the figure this repo's law files carried from 2026-09-27, "widens an armed deleter
  from 227 to 807 trees". The corollary is the trap: an absolute-only `roots` list empties
  `rel_roots`, making EVERY registration a host and disabling deletion entirely — it fails
  closed, which is the safe direction and also a silent one.
falsifier: >
  `python3 -c "import sys; sys.path.insert(0,'scripts'); import worktree_gc as g;
  print(g.path_under_session_root(__import__('pathlib').Path('/Volumes/Mastermind/worktrees/x'),
  ['.claude/worktrees']))"` -> False. End to end: run `worktree_gc.py --apply --dry-run`
  against a scratch config whose `roots` names only `/Volumes/Mastermind/worktrees` and read
  the summary — `deleted` is 0 and every `errors` row reads "refused — host checkout" (the
  errors list is COUNTED but never printed, `scripts/worktree_gc.py:949`, so read the JSON
  receipt, not stdout). Disproved by a receipt showing a non-zero `deleted` for any path
  outside a repo-relative session root, or by a `roots` entry that reaches an SSD tree while
  `rel_roots` stays empty.
so_what: >
  Widening `roots` by subtree is NOT the operator ratification act the law said it was: on its
  own it buys +496 trees of REPORTING and +1 tree of deletion, so it is close to inert and
  cannot cause the mass deletion the earlier text warned of. Ratifying it is cheap; ratifying
  it is also nearly pointless unless a companion CODE change makes session-tree detection
  follow the configured roots. That reframing cuts BOTH ways and the second half is the
  important one: the SSD web-session population (`/Volumes/Mastermind/worktrees`, `sol/`,
  `review/`) is protected today only by an accidental naming heuristic that a future
  "fix host detection so widening works" commit would silently delete — so the explicit
  `human_driven_roots` deny-list, honoured ahead of every verdict, becomes MORE necessary,
  not less. Anyone touching `host_checkouts`, `path_under_session_root`, or `rel_roots` is
  editing the load-bearing safety belt for 527 human-driven checkouts and owes the deny-list
  in the same PR. Note also that `expand_roots` already balloons to 4,047 sweep roots today
  (7 relative x 578 hosts + 1) — that cost is pre-existing, not a consequence of widening.
kind: landmine
verified_at: 2026-09-28
verified_by: >
  scripts/worktree_gc.py:165,177,233,251,688,861-864; measured over
  `git worktree list --porcelain` (804 registrations) — TODAY hosts=578 sweep_roots=4047
  in_scope=225 deletable=225; WIDENED hosts=578 sweep_roots=4049 in_scope=721 deletable=226
scope:
  - macro
  - scripts/worktree_gc.py
  - config/worktree_gc.json
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---
