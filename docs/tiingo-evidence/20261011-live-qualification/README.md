# Tiingo live qualification, 2026-10-11

These are actual vendor-request, receipt, materialization and read-only audit results
from producer head `bddd8da1f5c5225b258ff4d6d35ce72fca5a09fb` on Macro PR #8698.
They include counts, clocks, request paths and content/receipt hashes; licensed
market rows, credentials and BOATS subscription-ID values are excluded.
`evidence-manifest.json` binds the retained files. This is bounded qualification,
not full backfill, production runtime admission or canonical/PIT enrollment.

The 500-history batch completed 500 requests with HTTP 200, returning 1,103,194
records and 250,573,134 response bytes in 1,268.838 seconds. Two responses were
empty. Existing corpus audit inspected all 565 receipts and verified the exact
500 planned responses: 498 RAW_RECORDS_CAPTURED, 2 EMPTY_CAPTURED. Materialization
reported 498 written, 61 existing, 2 RAW_ONLY metadata/definitions, 4 empty (including
BOATS control-only segments), and zero refusals. The entire snapshot has 553 nonempty
EOD histories and 1,233,237 distinct bars; AMD's annual pilot and whole-history
response agree across their 252 overlapping economic rows.

The 500 request selections are acquisition candidates from the previously captured
catalogue, not canonical aliases or a survivorship-safe historical universe. The
same catalogue ZIP was reused by its exact SHA-256. Dates are requested/returned
bounds; no gap-free market-calendar coverage is inferred.

BOATS historical qualification verifies 1,407 distinct native bar timestamps across
AMD/AAPL, all between 20:00 and 03:59 ET, with explicit volume on every returned bar.
The 30-second WebSocket probe received actual H/200 and I/200 subscription controls,
with an ID present, but zero Q/T/B during Sunday daytime. Its control-only raw
segments are EMPTY_NORMALIZED rather than manufactured market-event views.

Signed-in account observations show Organization active, BOATS active, allocations
of 20,000 requests/hour, 150,000/day and 100 GB/month. The displayed API key matched
the provisioned collector key without exposing either value. A valid AMD permanent-ID
fundamentals request returned HTTP 400 with free/Dow 30/limit terms. AAPL's three-year
asReported=true/false statements and daily metrics returned 200. Full fundamentals
access therefore remains unverified despite the Chairman's activation attestation;
no support message or subscription change was made.

Reproduction uses the existing source functions, not a replacement collector:

- `scripts.tiingo_ingest.collect` with `Task` instances exactly matching the
  retained candidate dates, cap 500 and pause 1.25 seconds; safe batch totals are
  retained. Do not re-download accepted responses merely to reproduce the report.
- `python3 -m scripts.tiingo_materialize --max-receipts 1000` for the immutable
  archive; its actual result is `live-materialization-500.log`.
- `scripts.tiingo_corpus_audit.audit_corpus` for the exact 500 tasks, cutoff
  2026-10-11 UTC, max_receipts=1000, read_budget=1073741824, detail_limit=500.
- `verified_raw`, `validate_receipt` and `read_research_view` verify each raw hash,
  exact receipt and nonempty projection. The snapshot lists every retained REST
  receipt, original observation clock and projection count. Empty JSON arrays are
  verified as empty source responses, not missing publication artifacts.

PIT eligibility, canonical identity and production-consumer acceptance remain false.
All 24 Tiingo registry contracts remain PROPOSED. Terminal draft PR #945 preserves
Hub source/basis through its thin proxy; it does not activate a BOATS Hub provider.
