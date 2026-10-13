---
key: A-ONE-MINT-ROOT-IS-SHARED-BY-TWELVE-GIT-STORES
claim: >
  `/Volumes/Mastermind/worktrees` is a mint root shared by **12 distinct git stores**, and a
  per-clone sweeper is therefore structurally blind to most of it — a defect that NEITHER
  widening `config/worktree_gc.json` `roots` NOR repairing host detection can fix, because
  there is no registration to read from this checkout. The root measures **726.4 GiB** (`du`,
  2026-09-28) — larger than any per-root figure in `research/WORKTREE_GC_POLICY.md`, whose
  largest was 462 GiB. Measured 2026-09-28: 353 directories
  directly under that root — 336 linked worktrees, 11 standalone full clones, 6 plain trees,
  2 registrations whose gitdir target is already gone. Of the 336, only **140 belong to
  `Macro Dashboard`**, the clone every instrument in this repo reads; the other **196 (58%)
  are owned by 11 other stores** and cannot be enumerated from here at all:
  `/Volumes/Mastermind/repos/sol-biocatalyst-6389-recovery` (50),
  `~/Documents/Cluade/Mastermind` (38), `/Volumes/Mastermind/repos/mastermind-terminal` (35),
  `/Volumes/Mastermind/repos/Mastermind-r7-836` (27), `~/Documents/GitHub/macro` (25),
  `/Volumes/Mastermind/worktrees/sol-macro-turnarounds-7165-20260917` (10),
  `~/Documents/GitHub/Mastermind` (7), plus four singletons:
  `/Volumes/Mastermind/worktrees/gold-pr7596-review-da52fde396c6`,
  `/private/tmp/mm-pr834-recovery-writer`, and **two self-hosted GitHub Actions runner
  workspaces** (`~/actions-runner-2/_work/macro/macro`, `~/actions-runner-3/_work/macro/macro`).
  Two of the stores are themselves worktrees planted under the root they own trees in, and one
  is in `/private/tmp`. Multiple REPOSITORIES are mixed in one directory (macro, Mastermind,
  mastermind-terminal, sol-biocatalyst). This also corrects the reach of every per-root figure
  in `research/WORKTREE_GC_POLICY.md`: its "142 trees" for this root was always "trees OF THIS
  CLONE under this root" (measured 140 today) and was read as the root's population.
falsifier: >
  `python3` over `os.listdir('/Volumes/Mastermind/worktrees')` reading each entry's `.git`
  FILE and splitting its `gitdir:` line on `/.git/` recovers the owning store without
  consulting any registry; counting distinct owners yields 12. Cross-check: `git worktree
  list --porcelain` from this checkout lists only the 140 `Macro Dashboard` ones. Disproved by
  a single store owning every tree there, or by `worktree_gc.py` enumerating a tree owned by
  another store (it cannot — it reads one `git worktree list`).
so_what: >
  Stop treating `roots` as the thing that scopes fleet worktree governance for this root: a
  per-clone sweeper CANNOT govern a shared mint root, and the two scope defects already
  recorded (absent roots; the host-checkout belt, see
  `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`) are both downstream of this
  larger one. Anything that must actually govern this root has to enumerate the DIRECTORY and
  resolve each tree's owning store per entry, then run its removal against THAT store — which
  is exactly the `git -C <owning clone> worktree remove` shape a worktree-isolated session is
  forbidden to issue, so it belongs in a host-local daemon, not in a repo script invoked by a
  session. Two consequences for measurement: never quote a per-root tree count from a single
  clone's registry without saying whose registry it is (report the instrument's REACH beside
  its number), and expect orphaned registrations to accumulate in stores you are not standing
  in — the contract-delta reaper prunes only its own clone's, by design. Note also that two
  owners are self-hosted runner workspaces, so CI's own checkout plants trees in the shared
  human/Sol mint root. **That last sentence originally read "a sweeper that did govern this
  root could delete a live runner's tree" and is CORRECTED 2026-09-28, same day, by the
  follow-up measurement:** neither runner store owns a LIVE tree here — both runner-owned
  entries ARE the root's two already-orphaned registrations
  (`sol-flow-velocity-recovery-proof-20260920`, **7.2 GiB**, and
  `prophet-b4-session-policy-repair-20260922-a11`, 408 KiB), whose gitdir targets are gone.
  So the hazard is not a sweeper deleting a live runner tree; it is that CI leftovers
  accumulate here that NO store registers, so no `worktree prune` anywhere can see them —
  and being unregistered, `git` cannot run in the tree at all, so their landedness is
  UNPROVABLE and the completion-signal law fails them closed. They are the largest clean
  reclaim candidate found on this volume and still need an operator judgement, not an
  automated verdict.
kind: architecture
verified_at: 2026-09-28
verified_by: >
  os.listdir + per-entry `.git` gitdir resolution over /Volumes/Mastermind/worktrees
  (353 dirs, 336 linked, 12 distinct stores, 140 owned by `Macro Dashboard`; re-run twice,
  identical); corroborated independently by ~/.config/mastermind/worktree-storage.json
  `_why`, which recorded "279 live worktrees across 7 git stores" for the same root
scope:
  - macro
  - scripts/worktree_gc.py
  - config/worktree_gc.json
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---
