# China economy R11 — monotonic receipt repair

Source `56ae3b9b8af4b0137d1a6a01e08ee6a76db59380`; existing PR #8196 and operation
`china-macro-evidence-upgrade-20260929-sol-001`. Candidate only; not deployed.

## Independent finding and real-store falsifier

C2's core audit found that `old is None or old == new` skipped all prior receipt
checks. Normal column-wise upsert then allowed older metadata to replace newer
metadata. A stale value could even reactivate a later receipt-qualified null
withdrawal. Equality of the number is not equality of the publication evidence.

Three new tests reproduce this through actual `lib.store.upsert/read` and Parquet,
including the existing column-merge representation of a null withdrawal. Running
those exact final tests with the original511514 admission function fails all
three. No real production value was changed for the experiment.

## Bounded repair

Rows with prior receipt fields now undergo the same tuple-order checks regardless
of numerical equality or null value. Both value digests, catalog definition,
source lineage and publication/acquisition chronology must agree. Exact tuple
replay is idempotent; a changed tuple needs a genuinely later acquisition and
non-regressing publication (strictly later for the existing cross-URL SA exception).
Partial/corrupt prior receipts do not become unreceipted legacy data. Conflicts
withhold the whole incoming column, preserving the seasonal-history boundary.

The original same-value enrichment of genuinely unreceipted legacy rows remains.
Tests also retain zero/null exact replay, valid forward revisions and a genuinely
newer reactivation after withdrawal. No parser version bump or article re-fetch
is needed: this is admission order, not a new interpretation of publisher text.

## Verification and continuation

537 focused full-file tests pass, zero failures/errors/skips; four inherited
pytest temporary-Chromium cleanup warnings remain visible.172 acquisition/store/
property tests pass. The old function fails the three discriminating regressions.
Python compile and scoped diff-check pass. Unchanged page/browser evidence and
R10 actual serialization proof are reused, not recreated for a timestamp.

The independent core audit remains open for exact-head repair reassessment.
R10 property/serializer delta received scoped source PASS; its first-match
property ArticleTitle/PubDate metadata caveat is nonblocking and remains
unclaimed, not silently relabeled covered. Required new-head CI, full release
adjudication and installed-candidate live proof remain. No merge, deployment,
new source acquisition, trading authority, auth or control-plane change occurred.
