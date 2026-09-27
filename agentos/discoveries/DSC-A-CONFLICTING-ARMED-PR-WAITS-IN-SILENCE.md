---
key: A-CONFLICTING-ARMED-PR-WAITS-IN-SILENCE
claim: >
  An armed `merge-on-green` pull request that becomes `mergeable: CONFLICTING` can sit OPEN
  indefinitely with NO `merge-blocked` label, NO comment and no new red check, so its
  outward state is indistinguishable from "armed and waiting for CI". Measured 2026-09-26 on
  macro PR #7930: READY and armed since 2026-09-24 20:50Z, head unmoved, labels exactly
  `[merge-on-green]`, zero comments, checks `ci-authority` + `ci-authority/main` pass with
  only the fleet-wide `ci-authority/codex/merge-queue-pilot` red — and
  `mergeStateStatus: DIRTY`, `mergeable: CONFLICTING` against a main that had grown 194
  files. The conflict was one additive list (`tests/test_ci_pack.py` CURATED_EXCLUSIVE).
  Separately, `merge-on-green.yml` run frequency is NOT evidence your PR was considered:
  the runs that fire every few minutes are `workflow_run`-triggered failure-marker passes
  that log `merge-on-green mark-only pass: no armed pull request sits at <sha>, so there is
  nothing to mark` and evaluate no arming decision at all.
falsifier: >
  `gh pr view <n> --json mergeable,mergeStateStatus,labels,comments` on an armed PR left
  unmerged for a day — a CONFLICTING/DIRTY answer with no `merge-blocked` label and no
  comment reproduces it. For the second half: `gh run view <latest merge-on-green run id>
  --log | grep "mark-only pass"`. It would be disproved by the sweeper labelling such a PR
  `merge-blocked` within a sweep, which scripts/merge_on_green.py's `reprove` docstring says
  happens when GitHub DECLINES its `update-branch` — a path #7930 evidently never reached.
so_what: >
  Never diagnose a stuck armed PR from the absence of a red or a label, and never from
  sweeper run frequency. Read `mergeable`/`mergeStateStatus` on your own PR first; if it is
  CONFLICTING, no number of sweeps will fix it and the session owns the merge of main into
  its own head. Expect the conflict in the shared registries every program appends to —
  `tests/test_ci_pack.py`'s CURATED_EXCLUSIVE list is the measured hot spot, where each
  sector program registers its exclusive job at the same position — and resolve those
  additively (keep main's text verbatim, append yours) rather than choosing a side.
kind: landmine
verified_at: 2026-09-26
verified_by: >
  direct observation — `gh pr view 7930 --json mergeable,mergeStateStatus,labels,comments`
  returned CONFLICTING/DIRTY, labels [merge-on-green], comments [] two days after arming;
  `git merge-tree --write-tree --name-only origin/main <head>` named exactly
  tests/test_ci_pack.py; `gh run view 36284220887 --log` is a 160-line mark-only pass;
  scripts/merge_on_green.py `reprove`/`refresh_deferred` docstrings
scope:
  - mastermindx-market-intelligence/macro
  - scripts/merge_on_green.py
  - tests/test_ci_pack.py
  - .github/workflows/merge-on-green.yml
confidence: verified
---
