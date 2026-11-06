# Actual Tiingo history expansion, 2026-10-11

The existing collector completed 1,000 additional exact catalogue requests:
1,000 HTTP 200 responses, 1,918,012 rows, 439,264,113 bytes,
2,596.673 seconds, zero failures. The existing corpus audit
inspected all 1,565 source receipts and verified the exact 1,000 request paths:
999 RAW_RECORDS_CAPTURED and 1 EMPTY_CAPTURED. Empty responses stay in the
denominator. These are acquisition candidates, not admitted historical identities.

The complete current snapshot has **1,552 nonempty EOD histories /
3,151,249 distinct daily bars**, with 3 additional empty EOD responses.
Every raw checksum, exact receipt identity and nonempty projection lineage was
verified. Raw/adjusted prices and action fields remain separate. The materializer's
actual return is retained in `live-materialization-1000.log`. Archive storage was
208,107,760 bytes; free space 272.666 GiB; the enforced
reserve stays 35 GiB. This observation is not a reservation against other SSD users.

Verification uses the existing content-digest selector for an unambiguous retained
content path, or the exact receipt selector for a receipt-specific path. Every row
is still checked against its expected source receipt ID and raw digest. The earlier
slow receipt-ID scan was interrupted as a read-only performance diagnosis; it did
not establish an integrity failure or qualify a partial result.

Qualification ran against documentation head fa2580e1615db9cf5bade13ca8c8667f08d3ff6b, whose producer
logic is unchanged from independently reviewed bddd8da1f5c5225b258ff4d6d35ce72fca5a09fb.
`evidence-manifest.json` binds every retained safe artifact. Licensed market rows,
credentials and subscription-ID values remain outside GitHub.

Actual research consumer reads joined AMD's two captures into 10,976 dates with
252 identical overlap dates, kept AAPL original/revised statements separate,
and read 3,810 daily fundamental metric rows. Mixed statement dimensions,
pre-observation capture cutoffs and PIT admission were all refused against actual
captured data. See `real-research-consumer-proof.json`; this proves retrospective
research use, not historical known-at availability or canonical issuer/listing joins.

The bounded incumbent comparison used the described and version-bound real
`macro_snapshot:stocks/AMD.parquet` through the installed read-only Data Workspace
adapter. Its registry declares Yahoo total-return close. All 27 dates in
2026-09-01..2026-10-08 matched; one close differs beyond 0.0001 absolute tolerance,
maximum absolute difference 0.00497558594. All 27 stored volumes differ, maximum
relative difference 0.00273601632. Only aggregate differences are published.
This unqualified local snapshot is not evidence of current production freshness;
cross-vendor agreement does not prove completeness or PIT availability.

The reused SHA-bound catalogue has 47,689 US-exchange USD Stock/ETF acquisition
candidates, including 17,256 whose catalogue histories end before 2026-10-08.
This remains the explicit full-backfill denominator; current membership is not a
survivorship-safe historical universe. The 500-response throughput extrapolation
is about 33.6 hours and 23.9 GB for the full candidate set. Those are estimates
from a non-random alphabetic pilot, not quota/storage reservations or execution proof.

Terminal PR #945 head 7506ef1539c8646e7bf52b65b697a102fd549942 passed the hosted
aggregate typecheck/tests and all desktop/mobile/tablet/serial shards on run
38161624995. It preserves existing Hub source/basis; it does not activate BOATS.
Independent consumer review, admitted runtime/provider publication, approved VPS
release and responsive live browser acceptance remain open. Source repair CI passed
at bddd8da1; each later documentation-head CI is observed separately.

The signed-in account and collector keys match; Organization/BOATS are active.
Chairman-attested full fundamentals activation is preserved. Actual AMD requests
still returned HTTP 400 with free/Dow 30/limit terms, while allowed AAPL history
returned 200. No support message, subscription change or credential switch was made.
Actual BOATS controls/history remain the prior bounded proof; Q/T/B live-session
traffic and gap/break/condition retention still need genuine captures.

Reproduction uses the existing producer and readers with no network re-download:

- `python3 -m scripts.tiingo_materialize --max-receipts 3000`.
- `scripts.tiingo_corpus_audit.audit_corpus` with exact Tasks from
  `eod-1000-candidates.json`, original request dates, observed cutoff from the
  audit artifact, max_receipts=3000, read_budget=1073741824, detail_limit=1000.
- `verified_raw`, `validate_receipt`, and `read_research_view` for all source
  receipt hashes and nonempty projections; exact IDs/clocks/row counts are in the
  snapshot. Empty arrays are qualified as empty responses, not missing files.
- Existing `read_research_history` and `read_research_statement_timeline` with
  the exact source IDs/clocks and declared statement dimensions in the consumer proof.
- Data Workspace `describe` then version-bound `read`, columns Date/close/volume,
  time column Date, bounds 2026-09-01..2026-10-08, limit 100. Source version and
  adapter revision are in the comparison artifact; stored row values are excluded.

No merge, deployment, recurring capture, later wake or end-to-end completion is
claimed. All 24 Tiingo contracts remain PROPOSED and research PIT admission false.
