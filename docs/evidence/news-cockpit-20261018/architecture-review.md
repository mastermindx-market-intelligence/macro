# Macro News Intelligence: architecture and acceptance review

**Review date:** 2026-10-18
**Reviewer:** `/root/news_architecture_adjudicator`
**Mission:** `news-cockpit-rebuild-20261018-astra-01`
**Implementation and release owner:** `/root`

## Decision

No concrete release blocker remains from the three company-client findings in the final verification below. The review accepts the existing-owner architecture and the corrected client behavior within the stated limitations. Production deployment, live source evidence, CI results, and visual acceptance belong in the implementation owner's release record.

This final pass examined `source/templates/news_company.js` and `source/tests/test_news_company_mounted.cjs` read-only. The implementation owner reported **12 mounted company tests passing**. The reviewer inspected the corresponding assertions and implementation; this pass did not rerun the suite or inspect production.

## Final company-client verification

| Finding | Accepted correction | Evidence |
| --- | --- | --- |
| Corrections disrupted story order and expanded groups. | Retained stories keep their visible order while receiving authoritative corrections and removals. Explicit “Show latest” restores snapshot order. Corrected groups retain their expanded state, reload members, restore logical focus, and preserve the visible story anchor. | `news_company.js`: `render()` lines 118–152, `accept()` lines 154–159, update action line 222; mounted tests lines 84–98. |
| A superseded member request could purge a newer feed. | Per-group request ownership fences both completion paths. Card removal/replacement aborts its request. Incidental detached failures are ignored; current-generation access denials still clear protected content. | `abortGroups()` line 49, `members()` lines 105–116, card reconciliation lines 126–139; mounted test lines 90–98. |
| Stream recovery overrode HTTP 429/404 policies. | The generic transport recovery excludes 401, 403, 404 and 429. Rate limiting retains the 60-second wait; terminal missing-resource responses have no automatic retry. | `errorState()` lines 51–59, `openStream()` lines 186–190; mounted tests lines 99–107. |

The mounted assertions verify ordering, group continuity, stale-request isolation, and retry timing. Actual pixel geometry and assistive-technology behavior remain part of browser acceptance.

## Accepted architecture

- **Aggregate delivery:** The FastAPI adapter reads the incumbent atomic intelligence artifact and sends full replacement snapshots, including an initial snapshot on reconnect. Existing `IntelligenceStore` and the fastlane daemon remain the state and scheduling owners. This avoids a competing aggregate store or delta-log owner.
- **Company delivery:** Existing authenticated, source-rights-gated ticker APIs remain authoritative. Their change stream triggers snapshot refreshes. Browser generation fences protect ticker/page transitions and auth changes; protected company reporting is cleared on access loss, workspace closure, and background suspension. Earlier pages pause live delivery and recheck authorization.
- **Research intake:** RSS and bounded GDELT discovery reuse existing collectors and scheduling. Research packets remain `reported`, preserve source identity and revision evidence, and are excluded from marketing drafts/routes. Durable feed validators advance only after successful downstream acceptance. Bounded subprocesses contain slow body reads and incumbent GDELT throttle waits.

## Material limitations to carry into release claims

1. **Coverage is bounded by configured sources, discovery queries, accessible rights and retained projection windows.** Worldwide completeness and MarketOntology parity have not been established by this review. Held Tiingo activation and existing source-rights ownership remain outside this rebuild's authorization to change.
2. **Transport freshness and news freshness use separate clocks.** The aggregate stream observes artifact changes on a one-second loop; upstream collection runs through the existing approximately 75-second daemon cycle and per-source cadences. Company notifications are coalesced into snapshot refreshes. Publisher-to-screen tick latency requires live measurement across that entire path.
3. **Grouping and activity are descriptive.** Syndicated reports can share a group; group size establishes neither independent corroboration nor claim confirmation. GDELT indexing/receipt times and supplied publication/update times retain their distinct meanings. Activity comparisons depend on the accessible source history and coverage.
4. **Delivery is bounded and recoverable.** Aggregate connections reauthorize on a bounded connection lifetime; company delivery renews at 45 seconds and can fall back to 10-second polling. Full snapshots and finite history windows have bandwidth and coverage limits. Production latency percentiles and concurrent-reader capacity were not measured in this independent pass.
5. **Operational proof remains a separate release receipt.** Public fixtures provide presentation/testing evidence. The release record must identify the deployed revision, authorized live routes, actual source freshness/health, and applicable CI/deployment checks before attributing those outcomes to production.

## Outstanding orchestration accounting

Paid audit run `news-cockpit-protocol-audit-20261018-01` produced no worker start or result receipt. Its last reconciled state remains `NOT_FOUND`, `root_verified: false`, `execution_absence_proven: false`, `retry_allowed: false`; the effect remains unknown. No retry or new commission was made during these final reviews. The implementation owner's separate `news-desk-read-delivery-01` attempt must retain its own accounting. Neither unresolved attempt supplies acceptance evidence for this review.

## Reviewed file identity

SHA-256 at final verification:

```text
4bda25bfb4b4db863896f79f37158e9b7de4114609c2af8375e4fba90b2fdb9b  source/templates/news_company.js
178171dab553370fb1958e2b96e3b7a78fcf38c6abb1fbc48017a30416975d78  source/tests/test_news_company_mounted.cjs
```

Earlier architecture judgments used protected Mastermind law pin `ebe2de8f0d94310241362874ec9262ba572a63d2` and original Macro source baseline `a1fe765f08975c786ae74119dce1f04859502105`. The hashes above identify the final local company changes reviewed here.
