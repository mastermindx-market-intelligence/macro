---
key: EXECUTIVE-PROTECTED-RELEASE-IS-QUEUE-ONLY-AND-SQUASHES-TO-ONE-PARENT
claim: >
  On the Mastermind repository, `master` is merge-queue-enforced (queue `MQ_kwDOTotz3c4ABAiK`,
  `mergeMethod=SQUASH`, `maximumEntriesToBuild=1`, `minimumEntriesToMerge=1`,
  `checkResponseTimeout=3600`) while the repository allows only squash
  (`allow_merge_commit=false`, `allow_squash_merge=true`, `allow_rebase_merge=false`). The direct
  `PUT /repos/{owner}/{repo}/pulls/{n}/merge` endpoint is refused pre-effect with HTTP 405 for
  BOTH `method=merge` and `method=squash`; enqueueing with `--match-head-commit <head>` is the
  only lawful release path. Because the queue squashes, the protected commit it produces has
  exactly ONE parent (the previous protected head), the PR's own head SHA never appears on
  `master`, and the pre-merge `refs/pull/<n>/merge` two-parent shape `[base, head]` is discarded.
  The protected TREE is nevertheless byte-identical to the accepted candidate's tree whenever the
  candidate already contained the base.
falsifier: >
  Any of these refutes it: a successful direct `PUT /pulls/{n}/merge` (any method) on a PR
  targeting `master`; a protected-master release on this repo that lands a two-parent merge
  commit; or a queue release whose resulting `master^{tree}` differs from the accepted
  candidate's `<head>^{tree}` when `git merge-base --is-ancestor <base> <head>` already held.
so_what: >
  A 405 on the direct merge endpoint is a repository-policy refusal with zero effect, NOT a
  blocked release and NOT a reason to retry with another method, an admin bypass, a second
  carrier or a branch move: enqueue with `--match-head-commit` and let the queue own execution
  (`DURABLE_EXECUTION_RUNNING`, not completion). Then bind the release proof to the TREE and to
  blob-level readback — never to a commit SHA or a parent list. An owner who asserts "the merged
  commit must have parents [base, head]" or who greps `master` for the PR head SHA will wrongly
  conclude the wrong source was released, and an owner who trusts the pre-merge merge-ref parent
  shape as the post-merge shape is comparing two different objects.
kind: constraint
verified_at: 2026-09-25
verified_by: >
  Fable delivery principal, 2026-09-25 00:23Z-00:31Z, IAC-1 release of Mastermind PR #959.
  Read first-hand: repository merge flags via `gh api repos/.../Mastermind`; queue id and
  configuration via GraphQL `repository.mergeQueue(branch:"master").configuration`; queue entry
  `position=1 state=AWAITING_CHECKS enqueuedAt=00:08:48Z` on merge-group head `a29161fa…`; then
  after completion `master = a29161fa0a44cca9927afe042b5f7ea25aae1736` with a SINGLE parent
  `819abc8c…` and tree `17b55023edd3e08d0ad45575f8c8b88669ef33cc`, exactly equal to
  `cdbab793c93989aa5b320ca8ea82380d37e544ba^{tree}` and to the independently computed
  `git merge-tree --write-tree 819abc8c cdbab793`. The two direct-endpoint 405 refusals were
  recorded by the release owner in Mastermind #959 comments 5824381452 / 5824389860 / 5824595204;
  the surviving repository state after them was unchanged, so the refusals were pre-effect.
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - protected master release path
confidence: verified
---

# Protected release is merge-queue-only and squashes to a single-parent commit

Direct merge endpoints are refused pre-effect even for the repository's single allowed method.
Prove a queue release by tree and blob equality, never by commit SHA or parent shape.
