---
key: MACRO-CI-LINUX-POOL-IS-THREE-RUNNERS-AND-STARVES-AT-FLEET-SCALE
claim: >
  macro ci.yml packs run only on the org-level `ci-linux` runners pc-ci-1/2/3 (3 runners);
  a pack job takes 3-10 min, a PR run needs 12 packs (~72 runner-minutes), so the pool
  clears at most ~2.5 PR runs/hour with nothing else running; measured 2026-09-07 05:15Z:
  58 ci.yml runs QUEUED (oldest live one queued since 2026-09-06 09:17Z, 20 h), 1 in
  progress, 29 PRs armed merge-on-green, and 13 green main-ref `workflow_dispatch`
  baselines in the prior 12 h (sweeper/session proof refreshes) plus 20 fences.yml runs
  competing for the same three runners. #6903's 12 packs sat queued 4 h+ at head e74a7dbd.
  Superseded-head runs were already auto-cancelled (0 stale of 58), so cancelling buys
  nothing.
falsifier: >
  Disprove with `gh run list --workflow ci.yml --status queued` and
  `gh api orgs/mastermindx-market-intelligence/actions/runners`: if a queued PR run
  starts within ~30 min while 3 runners are busy, or if packs are scheduled on a label
  other than ci-linux, the pool size is not the limit.
so_what: >
  at fleet scale (both Meta-CEO seats + Sol + Warp lanes) merges are gated by
  runner-minutes, not by review; adding ci-linux runners (or throttling baseline
  dispatches) is the lever, and it is an operator/Chairman act (runner registration),
  not a session act; sessions must stop polling and expect 12-24 h from push to
  concluded packs while the queue is this deep.
kind: constraint
verified_at: 2026-09-07
verified_by: >
  Meta-CEO B session 7cd4fae1 2026-09-07 05:15Z: gh api orgs/.../actions/runners;
  gh run list --workflow ci.yml --status queued; jobs of run 34071647355 (12 packs
  queued/ci-linux since 01:09Z) and run 34027781786 (packs spread 12:48Z..05:13Z).
scope:
  - macro
  - ".github/workflows/ci.yml"
  - WS:MARKET-OS
confidence: verified
related:
  - "DSC:SHARED-CLONE-PACK-STORM-STALLS-THE-FLEET"
  - "WS:MARKET-OS"
---

Macro `ci.yml` pack jobs run only on the three org-level `ci-linux` runners. At fleet
scale the queue, not review, is the merge gate. Adding runners or throttling main-ref
baselines is a Chairman act; sessions should stop polling and expect 12-24 h to
concluded packs while the queue is this deep.
