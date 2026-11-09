---
key: CI-CONSUMER-MAPPING-GAP-20261109
claim: >
  Mastermind smoke-scoped PR and merge-group CI selects tests by changed
  path (same-stem tests only; pytest shards skip unless mode is full), so a
  change to a source pinned by the frozen identity-review registries can be
  certified green without running the pin tests that consume it, and master
  then fails those pins on its full push run.
falsifier: >
  Find a smoke-scoped Mastermind merge group for a change to a
  REVIEWED_FILES source that executed the identity-review owner tests, e.g.
  gh run view 42592403849 --repo mastermindx-market-intelligence/Mastermind
  showing shard jobs executed; or show .github/workflows/ci.yml:152 running
  pytest_shards for mode smoke.
so_what: >
  A scoped merge group is not full-suite proof. Scoped selection must add
  the identity-pin owner tests whenever a changed path is a registry key
  (Mastermind #2380); until then a pinned-source change can redden master.
kind: landmine
confidence: verified
verified_at: 2026-11-09
verified_by: >
  Mastermind #2365 merge group run 42592403849 had the scoped 4-job shape
  with shards skipped and passed; master push runs 42597437028 and
  42611479873 then failed tests/test_executive_reviewed_site_identity_tokens.py
  and tests/test_hermes_fabric_native_identity_review.py on
  integrations/hermes_attended_fabric/native.py; shard gating at
  .github/workflows/ci.yml:152 (Mastermind #1607 lane C analysis).
scope:
  - Mastermind
  - .github/workflows/ci.yml
  - scripts/ci_pr_smoke.py
---

# DSC: Scoped PR CI does not map identity-review test consumers to the files they pin

**Record ID:** DSC-CI-CONSUMER-MAPPING-GAP-20261109
**Date:** 2026-11-09
**Author:** mastermind-ceo
**Status:** Open (process-gap card to follow)

## Observation

PR #2365 (merge 6696153d, 2026-11-09 08:40Z) changed the review-gated file `integrations/hermes_attended_fabric/native.py` without re-pinning `tests/executive_fabric_release_identity_review.py` (and its consumer `tests/test_hermes_fabric_native_identity_review.py`). Its PR-scoped checks passed (`PR test scope` = changed-path fence over the PR's own files) and it merged; master's full-collection CI at the very next tip run then failed the four identity-review tests (run 42626302968), jamming every test-touching merge-queue entry behind it for ~5 hours until the pin-drift fix (#2377, sha 7b6d14ea re-pin) cleared it.

## Root cause

The PR-scope fence selects tests by the PR's changed FILES, but the identity-review tests are consumers of PRODUCTION-file content by sha-pinning — they break when a *different* file changes, exactly the class of dependency a changed-path filter cannot see. Evidence: #2365's own checks green on a head whose merge reddened master; the four failing tests sit in files #2365 never touched.

## Impact

- Red master between merges (multiple hours, org-wide runner starvation amplifying)
- Merge-queue jams: test-touching entries evicted (UNMERGEABLE) behind the red; scoped-only entries merged through, deepening drift
- Two evicted-but-CLEAN rescues and one convergence round needed to recover lanes (#1892 et al.)

## Direction (candidate, unconfirmed)

Map test CONSUMERS to pinned files at the fence: when a changed file appears in any identity-review registry (REVIEWED_FILES / pinned sha consumer test), the scoped run must include those tests regardless of changed-path scoping. Alternative: queue-side pre-merge full-collection gate on any PR touching review-gated files.

## Related

- Fix that cleared this instance: Mastermind PR #2377 (re-pin to 7b6d14ea, sites 57/280)
- Throughput ruling thread: t_b5022936; DEC-MERGE-ARM-EXPIRY-14D-20261109
- Session lessons: consumer-enumeration-by-symbol law (mastermind-x-operations skill)
