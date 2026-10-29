# Forex R26 source qualification — 21–22 October 2026

Status: actual research capture and offline diagnostics completed. **No finalized 4H feed is admitted.** This extends the existing Tiingo archive/materializer/reader; it does not introduce a collector, store, evaluator, activation or delivery lane.

## Current authority and technical continuation — 22 October 2026

**Licensing and product use are COMPLETE.** The Chairman confirmed that special approval already covers the intended Forex R26 product use and directed that no licensing/product-use email be sent to Tiingo. Canonical authority: [Macro #9996 comment 6331071428](https://github.com/mastermindx-market-intelligence/macro/pull/9996#issuecomment-6331071428). This records the Chairman's attestation, not a newly received provider response. Do not reopen this gate or require another purchase.

Technical source admission remains separate. The generic research reader's false `redistribution_admitted` / row-admission flags describe its unpromoted execution boundary; they must not be presented as a missing licensing approval. The two Forex registry entries remain PROPOSED pending technical qualification, with their licensing field updated to the Chairman-approved basis.

Provider support is not the default next step. The former unsent request is now an internal technical checklist; its product-use question is removed. Continue through existing archive, materializer, reader and evaluator owners. A specific technical question may be escalated only if indispensable and unresolved by the available evidence; no message has been sent.

The accepted signed-in save/reload/edit/delete proof, Macro #9996 merge, original render 39688064251 SUCCESS and migration 0038 applied-once receipt are preserved in [6330961048](https://github.com/mastermindx-market-intelligence/macro/pull/9996#issuecomment-6330961048). Terminal #1106 remains Draft/HOLD under its original review condition. No source admission, activation, notification or replacement review follows from this authority correction.

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

The report separates duplicate instants from conflicting values, recognizes equal instants across timezone representations, preserves nanoseconds, diagnoses invalid values without zero-filling, and reports observed spacing against an explicitly labeled minute reference. This single-view projection never chooses a correction winner or aggregates 4H bars. The interval-comparison extension below performs explicitly labelled diagnostic aggregation only.

**`eligible_observations` is unconditionally empty.** Apparently dense data and caller-supplied finality flags cannot admit a feed. No candidate is given evaluator-ready bar-end, availability, expiry, sequence, revision, feed or calendar assertions. Technical reader, identity, PIT and monitoring admission remain false; the Chairman-approved licensing/product-use decision above is complete.

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

The previously unrendered Request table was also verified in Tiingo's public documentation JavaScript, inside the `tiingo-forex` component. It documents `resampleFreq` with a `1min` minimum, minute/hour units, a `4hour` example and a `5min` default. Date parameters use `YYYY-MM-DD` and describe inclusive start/end filters. This resolves request syntax only: it does not establish UTC bucket anchors, interval labels, completeness or finality. The rendered page also contains a `1day` example, so the table is not treated as an exhaustive backend-support contract. Exact asset/excerpt hashes, offsets and component binding are in `source_evidence/tiingo-documentation-request-syntax.json`; no additional market-data request was made.

Remaining technical requirements are an explicitly named observable/price basis; interval labels and bucket anchors; date-boundary and sparse-minute behavior; conservative complete-bucket rules; a prospective closure and correction policy; and actual availability/freshness. Unknown vendor first-publication times must stay unknown. A local capture-based policy can be considered through the existing source/evaluator owners without pretending that the vendor guarantees immutability. Licensing and product use are complete under the current Chairman instruction.

A separate, bounded one-request USDBRL top-of-book probe also returned HTTP success with an empty array (0 rows, 2 verified raw bytes). Its exact raw receipt and the existing materializer's RAW_ONLY/NO_REVIEWED_L1_PROJECTOR disposition are retained in `source_evidence/tiingo-usdbrl-top-receipt.json`. The historical window and this contemporaneous quote request both failed to establish usable USDBRL observations; they do not prove global vendor non-support. No retry or replacement pair was used.

USDBRL is unproven for these exact requests. Offshore CNH still needs the intended literal spot-identity admission. No futures substitution, daily synthetic OHLC, reciprocal fallback, or elapsed-time finality inference has been made.

## Acceptance boundary

Source acquisition is real; current finalized-4H capability remains unavailable. Account storage and Terminal API/UI are separately reviewed in Terminal PR #1100. Genuine signed-in inactive-condition save/reload/edit/delete was subsequently accepted on 22 October. Evaluated conditions, delivered notifications and final program release remain distinct unaccepted steps. The original R26 design and separate carry/COT holds remain unchanged.


## Independent review and concrete provider handoff

Exact implementation `509583b08e689a159fb8079bb6f27e26a9d2d958` received a scoped independent PASS. The reviewer independently verified the two implementation/test hashes, reviewed the incumbent reader/materializer/archive context and CI edits, and passed eight independent unittest methods with parameterized subcases in 0.011 seconds. The reviewer runtime lacked pytest/PyArrow; the author's 84-test and real-Parquet integration suite was not rerun independently. External raw archives were not independently reread. See source_evidence/independent-review-509583b0.json and its retained harness.

Preserve the reader boundary: EMPTY_NORMALIZED creates no materialized Parquet view. Actual empty USDBRL raw responses are accounted for separately; a missing view or failed read must not become a successful empty result.

The remaining technical questions and their implementation consequences are retained in TIINGO_PROVIDER_QUALIFICATION_REQUEST.md as an internal checklist. That packet is UNSENT and must not be dispatched as a licensing/product-use inquiry. Current policy is to resolve technical questions from existing evidence and owners before considering indispensable technical support.


## Native four-hour request observed — 21 October 2026, 22:45 UTC

One previously prepared EURUSD `4hour` research request was executed through the existing `scripts.tiingo_ingest.collect` owner after an exact request-hash receipt scan proved no earlier capture. The one-request budget produced one successful new response, **7 rows / 809 raw bytes**, and no failure or retry. Exact request: `/tiingo/fx/eurusd/prices?endDate=2026-10-20&resampleFreq=4hour&startDate=2026-10-19`. Original receipt identity: `148ee86d4fec717d8d5c4e4214cbbb8cdd4703ac8260ef42ca31c2efaba524ba`; original capture clock `2026-10-21T22:45:21.025233+00:00`.

The retained raw digest is `7c58219d4866e1d7aef2ab0da9c8f52e3ba9d4ca9a1ca1e6896b4fbb31c7e934`. Exact gzip/raw bytes, length, receipt identity and count were verified locally without another HTTP request. All seven rows carry ticker `eurusd`, explicit UTC date labels and finite positive OHLC values within their bounds. The vendor labels run from **19 October 20:00 UTC through 20 October 20:00 UTC**, with six observed steps of exactly 14,400 seconds and no duplicate instants. These are observed labels, not an authoritative interval-start/end or finality contract. The requested 19 October date starts earlier than the first returned label; this probe does not establish full-window coverage.

**Zero finalized-4H observations were admitted at this checkpoint.** That earlier single-view implementation introduced no local aggregation, gap filling, replacement pair, correction winner, historical availability backdating, source registry promotion, activation, evaluator or notification. Raw prices and credentials remain in the incumbent archive; committed evidence contains counts, labels, clocks and hashes only. Public documentation supports the request shape; observed labels alone cannot settle OHLC basis, completeness, market calendar or correction/finality. Licensing/product-use approval is now complete under the current Chairman instruction above.

Evidence: `source_evidence/tiingo-eurusd-native-4hour-{plan,preflight,collect,receipt}.json`. The collection/receipt JSONs disclose the exact source head and the local owner-only execution scope. This is additional research evidence, not a re-run of the accepted minute-data diagnostic implementation or an independent source review.

## Closed-day native/minute reconciliation — 22 October 2026

One bounded EURUSD pair of requests and one bounded remaining-eight-pair cohort ran through the existing `scripts.tiingo_ingest.collect` owner. Their fixed request day was **21 October 2026**, frequencies `1min` and `4hour`. Exact preflight scans found no prior receipt for those request identities. In total: **18 attempted, 18 successful, 18 newly retained responses, zero failures or retries**. The 16 nonempty responses contain **11,467 minute rows and 48 native four-hour rows**; both BRL responses are verified empty arrays.

Original response-observation clocks for each minute/native pair are 1.551–1.904 seconds apart. Exact raw SHA256/length/receipt identities were verified, nonempty views materialized through the incumbent owner and read back as `INSPECTION / RESEARCH_ONLY_VENDOR_SOURCE`. Empty BRL responses produce `EMPTY_NORMALIZED`, not fabricated empty Parquet views or successful reader calls.

A separate raw-JSON comparison used Decimal values and four explicit label hypotheses. For all eight nonempty pairs, native OHLC equals the minute-window aggregate under **[vendor label, vendor label + 4h)**. Each of the three alternative label/inclusion hypotheses produced zero exact OHLC matches. These are cohort observations, not a universal vendor contract.

| Pair | Minute rows | Native rows | Exact OHLC matches | Complete 240-minute matches | Sparse exact matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| EURUSD | 1,440 | 6 | 6 | 6 | 0 |
| GBPUSD | 1,434 | 6 | 6 | 5 | 1 |
| USDJPY | 1,438 | 6 | 6 | 5 | 1 |
| USDCHF | 1,435 | 6 | 6 | 5 | 1 |
| AUDUSD | 1,435 | 6 | 6 | 5 | 1 |
| USDCAD | 1,435 | 6 | 6 | 5 | 1 |
| USDMXN | 1,412 | 6 | 6 | 3 | 3 |
| USDBRL | **0** | **0** | Not established | 0 | 0 |
| USDCNH | 1,438 | 6 | 6 | 4 | 2 |
| **Total** | **11,467** | **48** | **48** | **38** | **10** |

Sparse equality does not establish completeness. The eight-pair result does not erase BRL or independently settle offshore-CNH identity, every underlying quote, market closures or physical start/end semantics of both label types.

The older EURUSD receipts, observed more than nine hours apart, remain unchanged. Their start-label comparison gave 6/7 OHLC matches and 7/7 close matches; five windows were dense, one was sparse, and the first bar differed in O/H/L. The first native bar matched exactly one shorter suffix of retained minutes, **19 October 21:56–23:59 UTC, 123 rows**. This is observed tail-window equality; clipping versus corrections or another cause is not established.

Evidence:

- `source_evidence/tiingo-eurusd-20261021-paired-{plan,preflight,collect,receipts}.json`.
- `source_evidence/tiingo-remaining-20261021-paired-{plan,preflight,collect,receipts}.json`.
- `source_evidence/tiingo-nine-pair-20261021-raw-crosscheck.json`: exact receipt-bound four-hypothesis comparison, with no raw prices published.
- `source_evidence/tiingo-retained-4hour-crosscheck.json` and `tiingo-retained-first-bucket-tail.json`: original-receipt diagnostic and its exceptional-window check.
- `source_evidence/registry-chairman-approval-validation.json`: existing registry/produced-contract tests, **62 passed**, with technical statuses preserved.


### Actual incomplete-window control at 02:49 UTC

A separate exact-date EURUSD pair of requests observed 22 October's current candidate 00:00–04:00 UTC interval once through the same ingestion owner: two successful new responses, no failure or retry. The minute response contained **170 rows from 00:00 through 02:49**; the native response contained **one row labeled 00:00**, observed at **02:49:05.200350 UTC**. Its OHLC matched the observed minute aggregate exactly even though the candidate 04:00 end was still in the future.

This is a concrete negative control: a successful native `4hour` response and exact OHLC equality can coexist with an unfinished interval. Neither is a finality flag. The 70 remaining reference-grid minutes must not be filled or counted as historical transport loss. All observations remain ineligible. Physical time mapping and post-boundary behavior still require qualification; this control does not certify future immutability.

Exact plan, absence preflight, one-shot collection and hash/reader-verified receipts are retained in `source_evidence/tiingo-eurusd-open-20261022-{plan,preflight,collect,receipts}.json`. Original response-observation clocks remain separate from the verification receipt's later `verified_at_utc`.

## Prospective source-policy candidate — internal qualification route

The recovery owner accepts the following as the **candidate to qualify**, not an admitted feed or an activation decision. The next work uses the incumbent source, account, evaluator and delivery owners. No support contact, new collector schedule, evaluator, queue, watch or publication plane is required to take these steps.

1. **Name the observable:** Tiingo-reported historical FX close, in the literal pair's quote units per base unit. Do not call it midpoint, transaction or executable price without evidence. Use native returned close; minute values validate a selected interval.
2. **Qualify time mapping:** candidate native start label `L` maps to `[L,L+4h)`, with UTC anchors 00/04/08/12/16/20. Exact native/minute equality is relative-label evidence. A real natural-boundary check must establish the physical interval mapping before admission.
3. **Conservative coverage:** require the complete expected minute-label grid, valid OHLC/lineage, both edges and native/minute agreement for a supported window. Never fill missing minutes. Withhold sparse, conflicting, partial or unsupported windows; keep all nine requested pairs visible.
4. **Local closure:** qualify a bar as closed under the explicit source policy only after its interval ends and its checks pass. Do not assert vendor immutability. Full DST/holiday coverage is not implied; initially withhold across unsupported closures or gaps rather than invent them.
5. **Separate clocks:** `Archive.store_response` samples `observed_at_utc` before raw/receipt publication, and identical same-day request/content reuses the original receipt clock. Preserve it as original response-observation provenance. A future adapter needs a separate conservative post-publication/readback eligibility time, never backdated to the bar label. Re-reading an old receipt is not evidence of a fresh provider observation.
6. **Bound freshness:** if adopted, expire the most recent supported closed slot at the next UTC four-hour boundary. Verification after that expiry cannot make old data current. Do not extend expiry merely because an archive was read again. Actual boundary latency remains unproved.
7. **Preserve corrections:** retain source vintages and withhold when conflicting values for one admitted slot are discovered. Stable observation/revision selection and any effect on prior evaluation must use existing owners; no silent latest-wins choice or new revision store.
8. **Bind conditions explicitly:** current `forex_watch_client.js::canonicalRule` requires `feed:null`, and current storage rejects activation. A future source-binding/activation change must explain the named feed, UTC convention and local-closure/correction meaning, preserve threshold/direction/consecutive count/expiry, and use the normal rule revision. Do not inject a feed into an evaluator-only copy or silently reinterpret saved “finalized 4H” conditions.

The existing `engine/forex_alerts.py::evaluate_price_condition` already checks convention agreement, UTC boundaries, availability, expiry, sequence and ambiguous revisions. It trusts source assertions and does not fetch, aggregate, select revisions, persist or activate; satisfying its input shape alone cannot qualify a source.

Read-only policy consultation inspected the existing evaluator/archive/watch-client functions and ran a bounded synthetic AST contract experiment: synthetic assertions satisfying the evaluator's input contract evaluated; null feed, pre-availability, duplicate endpoint revisions, nonconsecutive slots and expiry withheld. This is neither a live feed proof nor the Terminal #1106 review. Exact reviewed SHA256s: evaluator `c77b9cd6736cbe2b4aa519d87f4d63d7f88480270eab109170fa20a50f7923fd`; archive `54b694af53a940f8ea1148215b0a3ccfcfa5313270286b04a99c72d7dc004fa6`; watch client `0e1e908c6db5a3eb685e747b867a8e25e0d5e0c2759a7e702716063fbb87bd6d`.

**Current boundary: zero eligible observations; no finalized-source admission, activation, evaluated live condition or delivered notification. Licensing/product use remains complete.**

## Reusable interval reconciliation and actual-receipt validation — 22 October 03:11 UTC

`lib/dataos/tiingo_forex.py::reconcile_forex_intervals` now compares exact `1min` and `4hour` inspection views under the four explicit label/inclusion hypotheses. This is a pure extension of the existing diagnostic owner, with no collection, storage, scheduling or evaluator authority. It preserves original candidates and ordinals, distinguishes invalid/uncompared windows from numerical mismatches, reports compressed unobserved-slot ranges and boundary witnesses, and compares each original response clock against the candidate interval end. Invalid timestamps, subminute labels, duplicates and invalid OHLC cannot yield a clean numerical comparison. No missing label is filled or called transport loss.

Comparison equality is exact equality of normalized `TiingoView` numeric values. The retained raw-JSON Decimal comparisons are separate evidence; the normalized path does not claim arbitrary-precision raw equality. Native rows are capped at 128 and all emitted per-window row references at 100,000, with refusal rather than truncation. The Chairman-approved product-use status is explicit; technical eligibility and all admission flags remain false.

The final focused source/reader/additional-history suite completed **138 passed in 7.71 seconds** at 03:15:41 UTC (process exit 0). Six warnings came from pytest attempting cleanup of older, unrelated Chromium fixture directories; no source test failed. The two registry/produced-contract suites separately passed **62 tests** after the licensing-field correction. Exact commands, timestamps and before/after source hashes are retained in `source_evidence/interval-reconciliation-validation-qualified.json` and `registry-chairman-approval-validation.json`.

At **03:11:07.574212 UTC**, the new implementation read the existing exact receipts through the incumbent reader. It reproduced all three distinct cohort outcomes:

| Cohort | Native windows | OHLC-equal | Dense equal | Sparse equal | Distinct limitation |
|---|---:|---:|---:|---:|---|
| 21 October closed day, eight nonempty pairs | 48 | 48 | 38 | 10 | Sparse equality is not completeness; BRL's two raw responses remain explicit empty results |
| Original retained EURUSD captures | 7 | 6 | 5 | 1 | First window differs in O/H/L while all seven closes match; captures were separated by more than nine hours |
| 22 October open EURUSD candidate interval | 1 | 1 | 0 | 1 | Only 170 minute rows; candidate 04:00 end remains after both original response clocks |

Every alternate hypothesis produced zero exact OHLC matches in the closed-day cohort. **84 archive/receipt/manifest/Parquet files were verified unchanged**, with **zero new API requests and zero materializer calls** during this integration. Actual BRL empty responses were verified directly from retained raw bytes; no fake reader view was created. The committed report contains metadata, clocks, counts, hashes, row references and equality booleans, with no raw prices.

Evidence: `source_evidence/interval-reconciliation-integration.json` (SHA256 `1c9ad5c7a93513c766cff83e42de067cecdac8920dad6e40758eb936e53c9e65`) and its exact retained command. That first integration is retained as immutable evidence. Final source hash `7d30b518225222eac431877bb9f71e5e78454cb5056dfd7f44fe24aace171796` and test hash `d90967b778b0ee05b40b1f1476dd5df69d2dfa8c8431defc9fb72308b2737dd1` were verified at **03:16:24.888404 UTC** against the same exact receipts: every projected cohort outcome and all 84 archive hashes match the first report. See `interval-reconciliation-integration-qualified.json` (SHA256 `b80343ab3665ea612d15dccf8b52d1a26f81f76f075f9b33e54363dc7bb116ca`).

Independent native source-code review found a real output-budget gap, which was repaired and tested before final qualification. Parent investigation also found pandas silently losing comma-fraction timestamp precision; those unsupported forms now refuse while valid dot-fraction nanoseconds remain exact. The final exact-hash review returned **NO BLOCKING FINDINGS**. Its scoped receipt is `interval-reconciliation-source-review.json`; it grants no source admission or Terminal/Fabric review authority. Earlier test/integration snapshots are preserved with their original hashes.

This advances technical qualification without support contact. It does not admit the candidate policy or supply a live feed. The next source evidence must address actual post-boundary behavior, prospective verified availability/freshness and preserved correction vintages through the existing owners. Licensing is complete and is not part of that remaining work.

## Actual post-boundary observation — 22 October 04:41 UTC

After the 04:00 UTC boundary, the recovery owner used the same existing ingestion owner for **one bounded pair of prospective observations**. Preflight found only the two successful 02:49 responses and no covering post-boundary receipt. Two requests succeeded at **04:41:18–04:41:20 UTC**, with no failures, retries, provider/account changes or new schedule. Both original vintages remain intact. The code/test hashes above are unchanged.

| Candidate UTC interval | Minute rows | Native/minute raw-Decimal equality | Relation to original response clocks |
|---|---:|---|---|
| 00:00–04:00 | 240 distinct aligned labels; no reference-grid gap | All four OHLC fields equal | Candidate end precedes both clocks |
| 04:00–08:00 | 42 labels through 04:41; 198 reference slots still unobserved | Open/high/low equal; close differs | Candidate end remains after both clocks |

The minute response was observed at **04:41:18.569937 UTC** and the native response at **04:41:20.112509 UTC**. Exact receipt/hash checks, incumbent materialization, reader verification, normalized comparison and a separate raw-Decimal comparison completed at **04:41:54.742181 UTC**. That later time is a verification receipt, not backdated vendor publication. This sample was obtained about 41 minutes after the boundary and establishes neither first availability nor low-latency service.

The two retained minute vintages share 170 prior labels: **169 are unchanged**, while the original latest 02:49 row has changed low/close values. The original 00:00 native bar has changed high/close values. Those earlier rows were observed while their candidate intervals were still open. This is evidence of changing open observations; it does not identify a vendor correction policy for closed bars. The 04:00 native close also differs from the partial minute aggregate despite a response separation of only **1.542572 seconds**; timing is a plausible explanation, not an established cause.

New exact receipts:

- Minute: `2bc9f93e5870b780582da71dc5bfb75de8990032e4d11b2982c9d247eb311865`, raw SHA256 `b0f06ffc93a6e71afddc88e2cd7c3745aabaea7e8335c5fa760727a5c2cee872`.
- Native four-hour: `241f4315a507983d70306d7159bccf2c61ebede61ba0ebc5cfc38aa5cd3114cb`, raw SHA256 `23d9b142f21463c6fe396b04d2038bd8682dd5bc429343de00be503e76435e07`.

Evidence: `source_evidence/tiingo-eurusd-post-boundary-20261022-{preflight,collect,qualification}.json` and exact retained commands. The qualification report SHA256 is `0c74bd6c78d22faa31045c6d8c62f9e6554b4d47d101ce3fd3832d1ca7eaefd9`. These two new responses bring this continuation's bounded capture total to **22 successful requests with zero failures**.

This closes the factual question of whether the previously open EURUSD interval can later appear as a dense, matching local four-hour bucket, while the following interval remains open. It is one observed rollover, not a universal vendor-finality contract. The remaining work is to qualify prospective runtime availability, expiry and correction handling through existing owners, then explicit source binding and the separate activation/evaluation/delivery gates. **Eligible observations remain zero; licensing/product use remains complete.**

## Executable candidate-policy checks — 22 October 2026

`assess_forex_source_candidate` in the existing `lib/dataos/tiingo_forex.py` now executes `tiingo-forex-local-close-candidate/1` without changing the accepted four-hypothesis reconciliation. It accepts exact verified reader views, explicit original receipt identities, caller readback/assessment clocks and at most eight supplied additional native vintages. Dense valid UTC slots, normalized OHLC agreement, both response clocks after the candidate end, verification and assessment before the next four-hour boundary, and consistency of supplied closed native vintages are separate checks. Passing checks yields `checks_satisfied_policy_unadopted`, never a finalized bar. Sparse, invalid, duplicated, off-grid, stale or conflicting evidence withholds; a reread cannot extend expiry. UTC slot indices preserve gaps.

The native-vintage census is explicitly limited to supplied receipts. It does not examine all archive corrections or minute vintages. Known open-window changes are disclosed but are not asserted to be post-close corrections. Duplicate identical evidence is idempotent and supplied inventory order cannot choose a winner. The pure function cannot authenticate disk bytes or attest a caller's clock; the existing reader remains the file-integrity owner. Normalized numeric equality is not raw arbitrary-precision equality.

The focused source suite passed **128 tests** in4.26s, process37644 exit0;14 warnings concerned older unrelated pytest temporary-directory cleanup. The first run's two failures were test-fixture issues (the incumbent archive refusal type and a malformed raw clock rejected before the pure boundary); they and its118 passes are retained in `source_evidence/candidate-policy-validation.json`. The corrected run is `candidate-policy-validation-qualified.json`. No vendor request, archive materialization, account mutation or runtime activation occurred. Principal performed the small pure addition directly for LOWER_TOTAL_OVERHEAD using already inspected contracts; source review and normal publication remain separately recorded.

All nine pairs remain in the candidate inventory, including explicit empty outcomes. Policy adoption still needs the existing owner's exact pair/calendar/observable/precision decision, conservative durable-readback availability, correction inventory and stable observation/revision contract. The helper emits no production feed, finality status, observation revision or eligible observation; all admission flags remain false. See [MASTER_PLAN.md](MASTER_PLAN.md) for ordered integration and recovery. Licensing/product use remains COMPLETE by Chairman attestation, with no outreach.
