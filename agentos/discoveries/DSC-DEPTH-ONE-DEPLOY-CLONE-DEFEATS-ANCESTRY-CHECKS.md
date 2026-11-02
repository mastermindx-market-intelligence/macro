---
key: DEPTH-ONE-DEPLOY-CLONE-DEFEATS-ANCESTRY-CHECKS
claim: >
  The production checkout /opt/macro on the VPS (root@146.190.142.17) is a --depth 1 clone
  that app/deploy/update.sh refreshes every 3 minutes with `git fetch --depth 1 origin main`
  (line 263) followed by `git reset --hard FETCH_HEAD` (line 289). Its history is always
  exactly one commit deep: is-shallow-repository = true, .git/shallow carries 1,641 lines,
  `rev-list --count HEAD` = 1, and `git merge-base --is-ancestor HEAD@{1} HEAD` returns 1
  even when HEAD@{1} is the direct parent of HEAD on origin/main (seat-measured 2026-10-11
  16:5xZ: HEAD c50af4eb0421, HEAD@{1} a040596a32a4, rc=1; git 2.43.0). Any production check
  that asks "did the deploy move forward along main" through ancestry, reflog walks or
  `git log old..new` fails closed on EVERY pull, and `git log old..new --name-only` lists
  unrelated paths while the net tree diff between the two commits is empty.
falsifier: >
  On /opt/macro, `git merge-base --is-ancestor <previous deployed sha> HEAD` returning 0 for
  two consecutive deployed commits, or `git rev-list --count HEAD` greater than 1, or
  app/deploy/update.sh fetching without --depth 1. Any of those means the clone is no longer
  shallow and ancestry checks are admissible on the host again.
so_what: >
  A deploy-side check that must decide whether a run's inputs changed under it compares
  TREES, never history: `git diff --name-only --no-renames <deployed> <current> -- <input
  paths>` (the DIDC design in PR #8830 for scripts/ingest_market_memory_identity.py) works on
  a depth-1 clone because both commits exist as objects after the fetch. Never design a
  production check around merge-base, is-ancestor, reflog ancestry or `git log old..new`:
  the intermediate DIDC round that did exactly that failed closed on every run whose HEAD
  moved, which on a 140-168 s run against a 3-min pull cadence is most of them. The same
  rule binds any future unit that records a deployed_commit and later has to prove the
  deploy did not change what it read.
kind: runtime
verified_at: 2026-10-11
verified_by: >
  seat fd47d431 over ssh -i ~/.ssh/macro_dashboard_deploy_v2 -o BatchMode=yes
  root@146.190.142.17: `git -C /opt/macro rev-parse --is-shallow-repository` -> true;
  `wc -l /opt/macro/.git/shallow` -> 1641; `git -C /opt/macro rev-list --count HEAD` -> 1;
  `git -C /opt/macro merge-base --is-ancestor HEAD@{1} HEAD; echo $?` -> 1 with HEAD@{1}
  a040596a32a4 the direct parent of HEAD c50af4eb0421 on origin/main. update.sh lines read
  with `git show origin/main:app/deploy/update.sh` at c50af4eb0421 (lines 263 / 271 / 289).
  ORCH-OPS DIDC review record ubuntu3:~/lanes/wt/mi-didcr-8830.record.md: round 2 (history
  walk) failed closed on every moved run; round 3 (net tree diff) passed 13 scenarios, with
  T9 reproducing the host shape through a real --depth 1 file:// clone + fetch --depth 1 +
  reset --hard FETCH_HEAD.
scope:
  - macro
  - market-memory
  - app/deploy/update.sh
  - scripts/ingest_market_memory_identity.py
  - /opt/macro
confidence: verified
---

Why the shape is easy to miss: the reflog on the host looks like a normal linear history
(`HEAD@{1}` is the previous deploy), so an ancestry check reads as obviously correct and
passes any test written against a full clone. Only a fixture that is itself a depth-1 clone
(DIDC T9) reproduces the refusal. The residual window of the tree-diff design — two pulls
inside one run that change an input and restore it — is named in the #8830 body and is
measured at 59 of 1,630 pull gaps <= 170 s; it is the next DIDC question, not this record's.
