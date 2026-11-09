---
key: CI-CONSUMER-MAPPING-GAP-20261109
claim: >-
  A reported changed-path CI consumer-mapping gap may omit SHA-pinning
  identity-review consumers; the historical incident-resolution claim remains
  unverified.
falsifier: >-
  Read https://github.com/mastermindx-market-intelligence/Mastermind/pull/2365
  and https://github.com/mastermindx-market-intelligence/Mastermind/actions/runs/42626302968:
  evidence that the exact changed production-file bytes selected and passed
  all affected identity-review consumers would contradict the reported gap.
so_what: >-
  Verify consumer coverage and exact-source full-suite evidence before
  adopting the candidate CI direction or treating the incident as resolved;
  preserve the existing Mastermind pin-repair and release holds.
kind: architecture
verified_at: 2026-11-09
verified_by: >-
  Source-only inspection of Macro commit d59a58ac73855075cef41a25fbeb870a5a9da5fc,
  this original record, and scripts/agentos.py:1748-1791;
  https://github.com/mastermindx-market-intelligence/Mastermind/issues/917#issuecomment-6747773590
  records a source disagreement. A native read of Mastermind PR #2377 during
  this inspection found it OPEN and unmerged at
  34cf357d3f9ea99ed4d092c5c98a7eaf4dc55259. The preserved body's claim that
  #2377 cleared the incident is not independently verified; no incident test
  execution or resolution acceptance is added by this metadata repair.
scope:
  - mastermindx-market-intelligence/Mastermind
  - mastermindx-market-intelligence/macro/agentos/discoveries
  - integrations/hermes_attended_fabric/native.py
  - tests/executive_fabric_release_identity_review.py
  - tests/test_hermes_fabric_native_identity_review.py
confidence: suspected
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
