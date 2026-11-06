## Workspace and git

- The canonical tree is GitHub `origin/main`
  (`mastermindx-market-intelligence/macro`), never a local folder. The only local
  project root is `/Users/chriswong/Documents/Cluade/macro-main` (operator
  2026-08-15). Never open `/Users/chriswong/Documents/Cluade/Macro Dashboard` as a
  workspace — not as a session working directory, not as an editor root.
For fresh work, use an admitted isolated worktree from the observed remote default
revision. For a continuation, preserve the exact existing workspace, branch and
effect custody; refresh only facts material to the next action. Do not fast-forward
an occupied primary checkout as a session-start ritual. A rejected fast-forward
requires diagnosis on the owned source path, not a global stop or a forced update.
Preserve real writer conflicts, dirty work, explicit denials and uncertain effects;
an unstarted independent source task may acquire a new permitted workspace without
changing another session's checkout or waiting for a historical owner.
- `macro-main` is a linked worktree, not a second clone (verified 2026-08-15):
  `macro-main/.git` is a gitfile pointing at
  `Macro Dashboard/.git/worktrees/macro-main`, which still owns every object, ref,
  config, remote, reflog, and the worktree registry — which is why `git worktree
  list` run from `macro-main` prints `Macro Dashboard` first. Never delete, move,
  rename, or iCloud-relocate `Macro Dashboard`, and never run repo-wide destructive
  git operations from inside it: that would destroy `macro-main` and every sibling
  worktree at once. The clone is also blobless (`blob:none`, promisor), so history
  operations that need file contents fetch over the network.
- Never create project work in `~/.codex/worktrees`, `/private/tmp`, or another
  Codex-only location. Never use a `codex/` branch for these repositories.
- The primary checkout is shared and commonly dirty or detached. Do not change its
  files or git state. Fetch the remote default branch, then create a fresh worktree
  under this repository's `.claude/worktrees/<task>/` and use a `claude/<task>`
  branch.
- A merged PR does not update any folder until that folder fast-forwards. Merging
  is a GitHub-side event; every local checkout, worktree, runner workspace, and VPS
  clone keeps its old bytes until it pulls. Verify state against `origin/main`,
  never against the folder you are standing in.
- Macro branches start from fresh `origin/main`; Terminal branches start from fresh
  `origin/master`. Never reuse a squash-merged branch.
- Do not use the repo-global stash stack.
- Session worktrees are garbage-collected by `scripts/worktree_gc.py` per
  `research/WORKTREE_GC_POLICY.md` (report-first; deletion only while
  `config/worktree_gc.json` is `armed:true` — an operator ratification act). The
  sweeper honors `git worktree lock`, live process cwds, uncommitted/unpushed
  work, open PRs, and <7-day activity. To park a checkout long-term, lock it:
  `git worktree lock --reason "<why>" <path>`.
- **Only a POSITIVE completion signal authorizes reclaim** (`DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`;
  incident 2026-09-26). Absence of a signal — an idle window, no process holding the cwd, a
  stale reflog — may NEVER authorize deleting, sparsifying, or otherwise destructively
  altering a shared worktree. Only a positive completion signal may: the commits landed, so
  the checkout is reproducible cache and removing it cannot lose the WORK — **but it does
  destroy the working directory of any session still attached, so landed is never on its own
  a licence to delete** (see the WORK-not-SESSION rule below).
  **CORRECTED 2026-09-27 — the signal is the MERGED PR, not `HEAD ⊆ origin/main`.** This repo
  squash-merges and a squash REWRITES the commit, so a cleanly merged branch's tip is NOT an
  ancestor of main (measured, PR #8086: squash `f9425697` is an ancestor, tip `0a47bc1f` is
  not); an ancestry-only gate fires for almost nothing but trees that never committed. The
  proof is any ONE of — the order `scripts/worktree_gc.py` already applies, and it was right
  before this prose existed — (1) `HEAD` ancestor of `origin/main`, (2) **a MERGED PR whose
  `headRefOid` equals this tree's HEAD** (the load-bearing case, originally omitted), (3)
  `HEAD` contained in `refs/remotes/origin/<branch>` with no open PR. Unknown PR state fails
  CLOSED. **A DETACHED HEAD satisfies none of them and this law structurally cannot reach
  it** — 318 such trees, 150 being `mo-ext-*` orchestrator labour lanes whose output ships
  from the SEAT's carrier branch; they need a lane-exit receipt, not a merge.
  **Idleness means two incompatible things** — a Claude
  Code/Codex session's shell exits between tool calls, so 24 h of silence means dead; a
  **ChatGPT web conversation has no shell and resumes the instant its human replies, so
  silence of any length means nothing.** Measured cost of ignoring this: an "idle ≥ 24 h"
  sparse sweep stripped `data/`, `site/`, `mockups/`, `verify_shots/` from 59 worktrees at
  05:31 — 34 of them `sol-*`/`review-*` web-review trees — and essentially every ChatGPT
  session died unrecoverably, because a web session hits a suddenly-absent path, wedges, and
  the errors cascade. No commits were lost (omitted paths stay tracked in the index), but
  sessions are the costlier asset. "Use 72 h instead" is the wrong fix: the defect is the
  CLASS of signal, not its threshold. The positive signal is also cheaper — free on
  squash-merge, no TTL/polling/`du`/process scan, and **no `refs/salvage/*` ref needed**
  because `origin/main` already references the commits. Manage storage at three points, none
  of which asks whether anyone is there: **cheap at birth** (93% of the 380 trees born in 7
  days are already sparse, ~0.45 GiB vs ~7.5 GiB), **reclaim at merge** (any one of the three
  proofs above, `git status --porcelain` empty, nothing attached, **and the tree under a
  configured root** — 580 of 807 trees are not, which is why an armed correct sweeper freed
  1.5 of 308 GiB; `/Volumes/Mastermind/agent-workspaces` alone holds 354 trees / 462 GiB and
  is *mandated* by the SSD placement policy, and widening `roots` is its own operator
  ratification act — a nearly INERT one, see the 2026-09-28 correction below), and **a hard per-root population cap**
  evicting landed-and-clean trees oldest-first — the org-enforced-retention pattern, because
  per-user cleanup discipline does not hold at fleet scale (54 trees minted/day, ~0
  removed). Retrofit-to-sparse is a one-time backlog drain, NOT an ongoing lever: correctly
  gated it yields 0.0 GiB across the 27 remaining FULL trees. Idle ages and live cwds may be
  REPORTED for a human, or narrow an action the positive signal already authorized — never
  authorize one. **And the signal protects the WORK, not the SESSION:** deleting a checkout
  destroys the working directory of anything attached exactly as thinning it did, so reclaim
  requires landed AND nothing attached, and because a resumable web conversation is
  undetectable by construction (no process, no shell, no reflog — it lives in a browser tab),
  **roots hosting web sessions are never auto-reclaimed at all.** **Pool RE-DERIVED 2026-09-27
  over 807 trees — the 09-26 figure quoted here was wrong.** It read "only 48 / 73.2 GiB are
  landed-and-clean while 638 are UNLANDED, so the bloat is unmerged WORK, not uncollected
  garbage, and no completion-signal sweeper can reach most of it"; that came from the
  ancestry-only gate, which a squash-merge breaks. Under PR state: **real abandonment is 8–14%,
  not 79%**, the fleet ships ~61 PRs/day against ~54 trees/day minted, and this IS uncollected
  garbage — so a completion-signal sweeper is the right instrument. **What limited it was SCOPE,
  not judgment:** 580 of 807 trees (72%) sit outside `config/worktree_gc.json` `roots`
  (`/Volumes/Mastermind/agent-workspaces`, 354 trees, `…/claude` alone 462 GiB and **mandated**
  by the SSD placement policy; `/Volumes/Mastermind/worktrees`, 142), and a further 285 trees /
  221.6 GiB are verdicted `LOCKED` on nothing but the SSD helper's content-free
  `removable volume protection` stamp, which short-circuits landedness entirely. Widening
  either is its own **operator ratification act**, exactly as flipping `armed` was.
  **Widen `roots` by SUBTREE, never by volume.** `…/agent-workspaces` holds both the
  agent-driven Claude seat lanes (`claude/<seat>/…`) and the ChatGPT-web family (`sol/`,
  `review/`, loose `*-sol` trees); `/Volumes/Mastermind/worktrees` is entirely the web/Sol mint
  root whose trees died on 09-26. Measured: **49.6 GiB across 31 of the 41 trees the report
  verdicted SAFE is HUMAN-class**, and a valid landed proof there is NOT permission — reclaim
  needs landed AND nothing attached, and a web conversation's attachment is undetectable.
  Safe to arm: `…/agent-workspaces/claude`, `…/agent-workspaces/tmp`. **Never**
  `/Volumes/Mastermind/worktrees`, `…/agent-workspaces` itself, `…/sol`, `…/review`.
  **CORRECTED 2026-09-28 — widening `roots` arms almost nothing, and the reason matters more
  than the number** (`DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`). This file said
  from 09-27 that widening "widens an armed deleter from 227 to 807 trees". Measured over the
  live 804-registration registry: `in_scope` moves 225 → 721 but the belt-reachable population
  moves 225 → **226**. `worktree_gc.py` never decides "session tree vs host checkout" from
  `roots` — `rel_roots` (~line 861) drops every absolute and `~`-prefixed entry, and
  `path_under_session_root` (line 165) segment-matches only `.claude/worktrees` and its six
  siblings, so every `/Volumes/Mastermind/…` path (nameable only absolutely) is classified a
  **host checkout** and refused by the belt at ~line 688 (`refused — host checkout`). Widening
  therefore buys +496 trees of REPORTING and +1 of deletion, and is inert without a companion
  CODE change making session-tree detection follow the configured roots. **The corollary is the
  danger and it runs opposite to the relief:** the 527 human-driven SSD checkouts — `sol/`,
  `review/`, the whole of `/Volumes/Mastermind/worktrees` — are protected today by that naming
  heuristic ALONE, not by any decision, so the obvious repair that makes widening work is the
  same commit that silently deletes them. A `human_driven_roots` deny-list honoured ahead of
  every verdict is therefore the FIRST thing to ratify, not the last: it is purely protective
  and can delete nothing. Two further facts for anyone touching this code: an absolute-only
  `roots` list empties `rel_roots` and disables deletion ENTIRELY (fails closed, but silently —
  the refusals go to `summary["errors"]`, which line 949 counts and never prints, so
  `deleted=0 errors=N` with no messages is this); and `expand_roots` is ALREADY at 4,047 sweep
  roots (7 relative × 578 hosts + 1), a pre-existing cost that widening raises by 2, not 4,000.
  The genuinely unreachable remainder is DIRTY + UNPUSHED (~308 GiB of real work, whose commits
  `refs/salvage/*` preserves for ~40 bytes each) and the 318 detached lanes, which need a
  lane-exit receipt rather than a merge. The durable fix is still upstream of storage: how many
  lanes get opened that never merge. See `research/WORKTREE_GC_POLICY.md` §9.
- **A session worktree is planted under the checkout the SESSION was launched in**
  (2026-08-20). `.claude/hooks/worktree_create_sparse.py` used to derive its
  destination from `git rev-parse --git-common-dir`, which answers with the MAIN
  working tree's `.git` from every checkout of a clone — a per-clone CONSTANT — so
  every Claude worktree landed under `Macro Dashboard/`, the one folder sessions are
  told never to open, whichever folder the operator actually opened. Placement now
  follows `--show-toplevel`, climbed out of any session root so a spawn from inside a
  session tree makes a SIBLING, never a nested child; `MACRO_LOCAL_ROOT` overrides.
  Only the BYTES moved — the clone is one clone, so every worktree stays registered in
  `Macro Dashboard/.git/worktrees/` and that folder stays undeletable.
  `scripts/worktree_gc.py` expands its repo-relative roots under EVERY host checkout
  for the same reason: a tree the sweeper cannot see it can never reclaim. Pinned by
  `tests/test_worktree_placement.py`.
- **Session worktrees are SPARSE by default** (`research/WORKTREE_GC_POLICY.md`
  §0 R8). Claude's `.claude/hooks/worktree_create_sparse.py` mints a worktree
  off fresh `origin/main` sparsely before file checkout. Codex uses the checked-in
  `.codex/environments/environment.toml` setup plus the `.codex/hooks.json`
  `SessionStart` fallback; Cursor IDE uses `.cursor/hooks.json`
  `sessionStart` and `workspaceOpen`; Cursor CLI / Agents Window uses
  `.cursor/worktrees.json` `setup-worktree-unix`; Grok Build / AionUi uses
  `.grok/hooks/session_start_sparse.py` on `SessionStart` (project-local
  `.grok/hooks/sparse-worktree.json`, plus the always-trusted
  `~/.grok/hooks/` copy so an AionUi `grok-temp-*` workspace still runs it).
  Codex/Cursor call `python3 scripts/worktree_sparse.py auto` after their
  harness has created a linked worktree. Grok's hook does the same when the
  session already sits in one, and otherwise mints a sparse tree under
  `.grok/worktrees/<name>/` with `git worktree add --no-checkout` (Claude's
  pre-checkout shape) so an AionUi session never materializes the heavy trees.
  Warp/Oz has no SessionStart or WorktreeCreate event. `.warp/hooks/session_start_sparse.py`
  plus `.agents/skills/macro-sparse-worktree` are the analog: a Warp session must
  run the mint itself (the skill auto-discovers), then `cd` to the printed
  `WORKSPACE=` path. The hook reuses only a carrier positively bound to the
  current Warp conversation/task identity; terminal/session IDs are not proof.
  Its branch/path use a SHA-256 digest of the complete identity, never the raw
  value, and an identity-less start mints a collision-resistant carrier rather
  than reusing `warp-session`. New carriers mint from freshly fetched
  `origin/main` under `.warp/worktrees/<name>/` with `git worktree add
  --no-checkout`; failed fetches and path/branch collisions fail closed without
  taking over a foreign carrier. It never writes
  `.session-worktree` into a git checkout.
  `auto` acts only on a linked worktree sitting under a session root
  (`.claude/worktrees/` and siblings — never the occupied primary, and never the
  operator's designated local root, which is itself a linked worktree), and preserves
  an existing sparse selection. Codex/Cursor expose setup/`SessionStart` only
  after Git creates the worktree, so they reach the same standing size but may
  incur one transient full-checkout write during creation. Project-local Codex
  and Grok hooks require one-time review/trust when their exact definition
  changes; the AionUi path is the global hook and needs no project trust.
  Grok and Cursor default a new worktree to the current HEAD — pass
  `--ref origin/main` / `--worktree-base origin/main`. All of these harnesses use
  each tracked top-level directory EXCEPT the heavy
  generated ones listed in `config/sparse_worktree.json` — `data/`, `site/`,
  `mockups/`, `verify_shots/` — because those are 87 % of a 3.8 GiB checkout
  (measured 2026-08-13: data 2.3 + site 0.73 + mockups 0.23 + verify_shots 0.05
  GiB) and a typical session never reads them. A tree costs ~0.35-0.57 GiB
  instead of 3.8. This is the other half of the 2026-08-13 disk-pressure
  incident: the Studio sat at 1.7 Ti / 1.8 Ti (~100 GiB free) after two
  receipted runner ENOSPC crashes, and arming the GC (#5502) only drains
  FINISHED trees — at ~40 new worktrees/day the ~330 GiB active window is
  structurally out of the sweeper's reach, so only a thinner per-tree footprint
  shrinks it. **Opt in whenever you need those trees** — any render, `site/`,
  paired plain-copy asset, or `data/` task — with `python3
  scripts/worktree_sparse.py full` (worktree-scoped; siblings are untouched), or
  take one tree with `python3 scripts/worktree_sparse.py add site`. `python3
  scripts/worktree_sparse.py status` says what is missing. Nothing is hidden by
  this: omitted paths stay tracked, `git status` stays clean, and a write into
  an omitted path is still reported — so `ship_loop_guard.py`'s dirty snapshot
  keeps working. **A write into an omitted tree TRUNCATES the committed
  artifact**, because the real content was never on disk for the writer to
  extend: measured 2026-08-13, a test run with the `MM_DATA_GUARD` tripwire
  disabled left `data/hk_southbound/holdings.parquet` at 45,157 bytes against
  7,295,941 committed, and `data/trial_ledger.jsonl` short by 1,411 lines. Never
  `git add -A` a diff you did not expect under `data/` or `site/`; run `python3
  scripts/worktree_sparse.py clean` (report-first; `--force` deletes) to put the
  omitted trees back. Nothing is silently greened either:
  `scripts/check_template_site_sync.py` REFUSES on a sparse tree rather than
  reporting "sync OK (0 pairs checked)", and pytest prints the omitted trees and
  the opt-in command, skipping only tests explicitly marked
  `needs_full_checkout`. **Do not run the full test suite in a sparse worktree** —
  measured 2026-08-13 it produces 1,281 failures and 419 errors across 247 files
  (against 68,776 passes) purely as artifacts of the missing trees. Opt into a
  full checkout first; marking all 247 files was considered and rejected because
  it would permanently mask real regressions in a tenth of the suite. Do not detect sparseness with `Path.is_dir()` — `data/`
  survives `git reset --hard` as a 0-byte husk; ask
  `scripts/worktree_sparse.missing_dirs()`.

<!-- Repository-root-relative paths and controls are unchanged by relocation. -->
