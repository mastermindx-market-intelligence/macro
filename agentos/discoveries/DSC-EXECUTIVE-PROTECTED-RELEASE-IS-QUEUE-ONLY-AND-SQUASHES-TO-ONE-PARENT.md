---
key: EXECUTIVE-PROTECTED-RELEASE-IS-QUEUE-ONLY-AND-SQUASHES-TO-ONE-PARENT
claim: >
  During the recorded 2026-09-25 release of Mastermind PR #959, protected master used queue
  MQ_kwDOTotz3c4ABAiK with mergeMethod=SQUASH, maximumEntriesToBuild=1,
  minimumEntriesToMerge=1 and checkResponseTimeout=3600. Repository flags then allowed only
  squash. The recorded direct-merge requests were refused with HTTP 405 and reconciled
  pre-effect. The queue entry initially proved admission only: position=1, state=AWAITING_CHECKS.
  The later actual release landed a29161fa0a44cca9927afe042b5f7ea25aae1736 with one parent
  819abc8c... and tree 17b55023edd3e08d0ad45575f8c8b88669ef33cc, equal to the accepted
  candidate tree for that recorded integration. Queue admission was not execution START or
  proof of that later merge. These are dated configuration and source receipts, not a current
  configuration guarantee or a promise that every future queue result equals an earlier PR
  head tree. A changed integration base requires qualification of the actual integrated source.
falsifier: >
  The historical Mastermind #959 queue/PR/commit receipts showing a different entry state, landed commit,
  parent or tree would refute the corresponding historical observation. A later legitimate
  configuration or integration-base change limits reuse; it does not erase the dated receipt.
  Use existing canonical readbacks to assess this record. It does not authorize a direct-merge
  probe, retry of a refused action, alternate method/account/carrier, or bypass.
so_what: >
  Record queue admission as QUEUED or AWAITING_CHECKS, not DURABLE_EXECUTION_RUNNING.
  That lifecycle classification needs actual STARTED/RUNNING evidence plus a return path.
  Completed checks and an actual merged PR/commit are separate receipts. Follow the currently
  qualified release path for the exact repository; a refused action is not permission to retry
  by another method or carrier. After a real merge, retain the actual landed commit SHA and
  its actual parent or parents alongside complete tree/blob readback against the qualified
  integrated candidate. A squash may replace the PR head SHA and the virtual merge ref's
  two-parent shape; neither is a required post-merge identity. An ancestry check alone does
  not establish tree equality if the queue integrated a different base.
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

# Dated protected-queue receipt: admission, execution and landed source are distinct

The `verified_at` and `verified_by` fields retain the original September 25 evidence.
The record describes **Mastermind/master**, not a release command for Macro/main.

## 2026-11-06 source correction

This correction resolves Macro #7885 finding
[6665767403](https://github.com/mastermindx-market-intelligence/macro/pull/7885#issuecomment-6665767403)
under the current Chairman backlog assignment and compatible Mastermind protected pin
`49c2e1d93e5e080b1671c98087a845e5beb09dd5`.

The original `AWAITING_CHECKS` receipt proves queue admission. It does not prove a started
worker or durable running execution. The later landed SHA/parent/tree receipt proves that
later source release and must remain part of provenance; it cannot retroactively upgrade
the admission receipt.

Compare the actual landed tree and blobs with the accepted integrated candidate at its
qualified base. Retain the landed commit and its real parent list. Do not require the PR
head SHA or virtual two-parent merge-ref shape to survive a squash, and do not infer tree
equality for a later integration merely because the PR once contained an earlier base.

No live configuration, queue, runtime, provider or release action was probed or changed for
this records correction. The other ten discovery records and incumbent #7223 workstream/fold
custody remain outside its source delta. A records merge is not new E1/E2 or installed-service
acceptance.
