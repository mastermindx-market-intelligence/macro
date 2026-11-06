---
key: ADVERTISED-PR-BASE-LAGS-THE-TESTED-MERGE-PARENT
claim: >
  The base SHA GitHub advertises on a PR's check run / workflow run
  (`pull_requests[].base.sha`) is the lazily refreshed PR-object snapshot - main as
  of PR creation, re-stamped only when GitHub happens to refresh the PR object - and
  NOT the first parent of the synthetic merge commit the run actually tested. `ci.yml`
  seals semantic evidence `base_sha` as that first parent (main at run time). Whenever
  main moves between PR creation and the run the two differ while describing the same
  tested tree, and the older one is an ancestor of the newer one. Measured on PR #8844
  (2026-10-11): the sealed artifact carried `base_sha=3979e12c`, the ci-gate check run
  advertised `f1ae1e03`, 28 minutes older and an ancestor; the byte-equal identity
  check in `ci_semantic_proof.load_semantic_evidence` raised `semantic evidence
  base_sha mismatch`, the sweeper filed `merge-blocked` ("advertised semantic
  evidence is unusable and may not downgrade to legacy reasoning"), and `gh run rerun`
  could not cure it because a rerun re-seals the current main as first parent while the
  advertised base stays frozen. It bites only when a check is red, because evidence is
  loaded only to attribute a red.
falsifier: >
  A PR run whose check-run `pull_requests[].base.sha` equals its sealed evidence
  `base_sha` even though main advanced between PR creation and the run - i.e. GitHub
  refreshing the PR-object base eagerly on every push to main. Check with
  `gh api repos/{owner}/{repo}/check-runs/<id> --jq '.pull_requests[].base.sha'` against
  the `base_sha` inside `ci-semantic-evidence-<run_id>` and
  `git rev-parse <tested_tree_sha>^1`; equality under a moved main falsifies the lag.
  A sealed `base_sha` that is NOT the tested merge commit's first parent would falsify
  the other half (that `ci.yml` writes the first parent).
so_what: >
  Never compare an advertised PR base to sealed evidence by byte equality. The exact
  identity of PR-head evidence is its `subject_head_sha` (must equal the PR head); the
  advertised base is accepted when it equals the sealed base or is an ancestor of it
  (GitHub compare `status` in {identical, ahead}), and callers then bind the tested
  tree to the SEALED base - the real first parent - because `_bind_pr_tested_tree`
  requires GitHub's parents to read exactly `[base, head]`. `scripts/ci_semantic_proof.py`
  `resolve_pr_proof_base` is the shared rule; `scripts/merge_on_green.py` and
  `.claude/hooks/ship_loop_guard.py` both route PR-head evidence through it. A different
  head, a non-ancestor base (behind / diverged), a missing advertised base, or an
  unanswerable compare stays a hard refusal; a quota 403 on the compare stays a
  `RateLimited` deferral. If you see "semantic evidence base_sha mismatch" again it
  now names both SHAs and means a genuinely different base, not clock skew on main.
kind: landmine
verified_at: 2026-10-11
verified_by: >
  PR #8844 sweeper receipt (merge-blocked comment quoting the mismatch), the run's
  `ci-semantic-evidence` artifact `base_sha=3979e12c`, its ci-gate check run advertising
  `f1ae1e03` (28 min older, ancestor on main), and `.github/workflows/ci.yml` writing
  `base_sha` from the tested merge commit's first parent. Red-first reproductions:
  `tests/test_merge_on_green_semantic.py::test_pr_artifact_accepts_stale_advertised_base_that_is_an_ancestor`,
  `tests/test_ship_loop_semantic.py::test_ship_loop_accepts_stale_advertised_base_that_is_an_ancestor`,
  `tests/test_ci_semantic_proof.py::test_resolve_pr_proof_base_accepts_a_stale_ancestor_advertised_base`
  - each failed with the production message before the fix and passes after it.
scope:
  - macro
  - scripts/merge_on_green.py
  - scripts/ci_semantic_proof.py
  - .claude/hooks/ship_loop_guard.py
  - semantic CI evidence v1 identity binding
confidence: verified
---

The two SHAs describe the same tested tree from two clocks: GitHub stamps the PR
object's base when the PR is created and refreshes it lazily, while the Actions runner
checks out `refs/pull/<n>/merge`, whose first parent is main at the moment the run
starts. On a repository where main moves every few minutes those clocks disagree on
almost every run, so the byte-equal check was refusing exact proofs as a matter of
course and only looked rare because evidence is consulted only when a check is red.
Ancestry is the right relation: the advertised base being an ancestor of the sealed
base says exactly "main moved forward under this PR", and the sealed base is the one
GitHub's commit object will confirm as the merge's first parent.
