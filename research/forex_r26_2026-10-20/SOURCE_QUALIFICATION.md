# Forex R26 source qualification — 21 October 2026

Status: actual research capture and offline diagnostics completed. **No finalized 4H feed is admitted.** This extends the existing Tiingo archive/materializer/reader; it does not introduce a collector, store, evaluator, activation or delivery lane.

## Actual acquisition and receipt verification

The existing `scripts.tiingo_ingest` owner executed the fixed nine-pair plan for 19–20 October 2026 at requested frequency `1min`. The plan digest is `e74695a22d465b40c0bac61a84d79c97deb5251f32f8124e6506a24326f80d16`. A bounded scan of the configured FX receipt namespace found no prior receipt before collection.

One bounded invocation completed: **9 attempted, 9 HTTP-success responses, 9 newly retained responses, 0 failed requests, 17,011 row hints, 1,973,450 raw bytes**. Every exact response was then verified against its original receipt and raw digest. Eight nonempty responses materialized through the existing research owner and were read back by exact receipt identity. USDBRL returned a valid empty response; it remains in the denominator.

No API key or key fingerprint was exposed, copied, rotated or committed. Raw price rows remain in the existing external archive. Repository evidence contains request dimensions, counts, clocks and hashes.

| Requested pair | Verified rows | First vendor timestamp, UTC | Last vendor timestamp, UTC | Observed timestamp steps >60s | Largest step |
| --- | ---: | --- | --- | ---: | ---: |
| EURUSD | 2,159 | Oct 19 11:52 | Oct 20 23:59 | 7 | 180s |
| GBPUSD | 2,145 | Oct 19 12:00 | Oct 20 23:59 | 9 | 300s |
| USDJPY | 2,082 | Oct 19 13:15 | Oct 20 23:59 | 2 | 180s |
| USDCHF | 2,136 | Oct 19 11:33 | Oct 20 23:59 | 12 | 480s |
| AUDUSD | 2,153 | Oct 19 11:56 | Oct 20 23:59 | 6 | 360s |
| USDCAD | 2,103 | Oct 19 12:33 | Oct 20 23:59 | 15 | 240s |
| USDMXN | 2,096 | Oct 19 11:30 | Oct 20 23:56 | 61 | 300s |
| USDBRL | **0 — empty response** | Not present | Not present | Not applicable | Not applicable |
| USDCNH | 2,137 | Oct 19 12:05 | Oct 20 23:59 | 13 | 300s |

For the eight nonempty responses, returned ticker identities matched the requested lowercase vendor symbols, timestamps carried UTC offsets, and the readback found no duplicate timestamps, out-of-order rows, invalid positive OHLC/bounds, subminute timestamps, or rows outside the requested UTC dates.

These are observed vendor timestamps, not qualified bar-end or publication clocks. The late starts and larger timestamp steps are concrete qualification questions. An omitted minute may reflect sparse updates or vendor boundary semantics; the report does **not** equate every omission with transport loss, fill missing observations, or claim full session coverage.

## Reusable diagnostic bridge

`lib/dataos/tiingo_forex.py::read_forex_watch_source` selects an exact receipt through `read_research_view(... purpose="INSPECTION")`. Raw/manifest/Parquet integrity and reader admission refusals propagate. The pure `diagnose_forex_view` preserves original row order, vendor timestamps, OHLC and receipt context as diagnostic candidates.

The report separates duplicate instants from conflicting values, recognizes equal instants across timezone representations, preserves nanoseconds, diagnoses invalid values without zero-filling, and reports observed spacing against an explicitly labeled minute reference. It never chooses a correction winner or aggregates 4H bars.

**`eligible_observations` is unconditionally empty.** Apparently dense data and caller-supplied finality flags cannot admit a feed. No candidate is given evaluator-ready bar-end, availability, expiry, sequence, revision, feed or calendar assertions. Rights, identity, PIT and monitoring admission remain false.

The actual receipt-bound run processed all **17,011** retained rows with **zero eligible final-4H observations**. The USDBRL empty response is reported separately from a missing or failed reader.

The existing required `dataos-prospective-reference` CI lane now owns the new test file. No job, gate ceiling, collector, dataset registration or acquisition schedule was added. Forex registry entries remain PROPOSED.

## Evidence and tests

- `source_evidence/tiingo-nine-pair-plan.json`: exact offline request plan.
- `source_evidence/tiingo-archive-preflight.json`: bounded, untruncated pre-capture receipt scan.
- `source_evidence/tiingo-nine-pair-collect.log`: actual acquisition result; exit 0, 19.93 seconds.
- `source_evidence/tiingo-nine-pair-receipts.json`: exact selected receipts, raw hashes, materialization and verified reader outcomes.
- `source_evidence/tiingo-forex-source-diagnostics.json`: actual source diagnostic summaries and code hashes; no raw prices published.
- `source_evidence/diagnostics-tests-final.log`: **84 passed in 3.85 seconds** across the new bridge, incumbent reader and additional-history suites.
- `source_evidence/ci-curation.log`: **3 passed in 162.79 seconds**; the existing exclusive-job declaration, import-closure and narrowing checks.

The diagnostic tests include apparently perfect data still withheld; empty versus failed reads; equal instants/different offsets; same-instant conflicts; distinct nanoseconds; disorder and gaps; null, boolean, zero, negative, nonfinite and textual prices; invalid OHLC bounds; naive/malformed time; wrong pair/mixed lineage; attempted admission promotion; caps; and exact-reader corruption/refusal propagation.

## Supported provider facts and remaining owner questions

Primary documentation inspected on 21 October 2026:

- [Tiingo REST Forex documentation](https://www.tiingo.com/documentation/forex) identifies historical OHLC and top-of-book fields separately. Its historical date description does not establish start/end or publication semantics.
- [Tiingo Forex product](https://www.tiingo.com/products/forex-api) describes historical minute bars and an aggregated bid/ask product. That does not specify the historical OHLC construction basis.
- [Tiingo symbology](https://www.tiingo.com/documentation/appendix/symbology) defines currency symbols as base followed by quote. Naming convention and an actual returned ticker do not themselves complete Data OS spot-identity admission.

Remaining concrete requirements are historical OHLC basis/filtering; timestamp start/end and bucket anchors; date-boundary and sparse-minute behavior; closure/DST and complete-bucket rules; finalization and correction-selection policy; prospective availability and freshness; and the existing rights owner's product-use mapping. Preserve the Chairman's plan attestation: this evidence does not imply another purchase is needed.

A separate, bounded one-request USDBRL top-of-book probe also returned HTTP success with an empty array (0 rows, 2 verified raw bytes). Its exact raw receipt and the existing materializer's RAW_ONLY/NO_REVIEWED_L1_PROJECTOR disposition are retained in `source_evidence/tiingo-usdbrl-top-receipt.json`. The historical window and this contemporaneous quote request both failed to establish usable USDBRL observations; they do not prove global vendor non-support. No retry or replacement pair was used.

USDBRL is unproven for these exact requests. Offshore CNH still needs the intended literal spot-identity admission. No futures substitution, daily synthetic OHLC, reciprocal fallback, or elapsed-time finality inference has been made.

## Acceptance boundary

Source acquisition is real; current finalized-4H capability remains unavailable. Account storage and Terminal API/UI are separately reviewed in Terminal PR #1100. Deployed account acceptance, evaluated conditions, delivered notifications and final program release are still distinct acceptance steps. The original R26 design and separate carry/COT holds remain unchanged.


## Independent review and concrete provider handoff

Exact implementation `509583b08e689a159fb8079bb6f27e26a9d2d958` received a scoped independent PASS. The reviewer independently verified the two implementation/test hashes, reviewed the incumbent reader/materializer/archive context and CI edits, and passed eight independent unittest methods with parameterized subcases in 0.011 seconds. The reviewer runtime lacked pytest/PyArrow; the author's 84-test and real-Parquet integration suite was not rerun independently. External raw archives were not independently reread. See source_evidence/independent-review-509583b0.json and its retained harness.

Preserve the reader boundary: EMPTY_NORMALIZED creates no materialized Parquet view. Actual empty USDBRL raw responses are accounted for separately; a missing view or failed read must not become a successful empty result.

The concrete remaining questions and their implementation consequences are prepared in TIINGO_PROVIDER_QUALIFICATION_REQUEST.md. That packet has not been sent and contains no token or raw prices. It requests authoritative semantics and the existing account rights mapping; it makes no new-purchase assumption.
