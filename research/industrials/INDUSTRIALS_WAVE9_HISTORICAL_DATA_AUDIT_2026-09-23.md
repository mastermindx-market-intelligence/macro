# Industrials Wave 9 - Historical earnings snapshot: recovery is not comparison eligibility

Research cutoff: 23 September 2026. Operation: `gmi-industrials-sector-research-20260923-sol-001`. Carrier: Macro Draft/HOLD PR #7789, `sol/industrials-sector-research-20260923`. Entry head: `3fb9e782e52d867a10fdcc91d1e5315cd8dc2492`. Protected Mastermind procedure: `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1.

Principal research only. This note contains aggregate diagnostics and four selected editorial examples, not a republished data feed. It establishes no current production defect, fresh consensus, security binding, source-rights admission, backtest or trade. Final Fable handoff remains withheld.

## 1. Exact result

The historical file identified in Wave 8 was recovered through the native GitHub connector with `fetch_file`, explicit commit and base64 encoding. Decoded bytes match the previously identified Git blob exactly. The file could then be inspected, but the selected estimate rows do not qualify for a fresh pre-event consensus comparison.

| Provenance | Verified value |
|---|---|
| Repository path | `mastermindx-market-intelligence/macro:data/earnings/earnings.parquet` |
| Containing historical commit | `ba368abe90542c82ae2267575f739b251dac1263` |
| Recorded commit time | `2026-07-28T03:27:50Z` |
| File length | 18,581 bytes |
| Calculated and native Git blob | `01a732f8e4d5db94011957797b9df9ba1c865aa3` |
| Calculated SHA-256 | `4392e814502723b988629ea759311192fb1c7d77eb2274c654c0a6d4bde1425e` |
| Rows / unique source ticker labels | 1,364 / 1,364 |
| Columns | `next_date`, `next_time`, `eps_forecast`, `surprises_json`, `as_of`, `ticker` |

Native source: https://github.com/mastermindx-market-intelligence/macro/blob/ba368abe90542c82ae2267575f739b251dac1263/data/earnings/earnings.parquet . The containing commit's date is repository metadata, not an independently attested analyst-publication clock.

A current-cache writer does not imply that all history was lost: this exact historical object exists. Conversely, an old Git object is not automatically a complete historical expectations dataset. Preserve both findings.

## 2. What the rows actually contain

| Row `as_of` | Number of rows |
|---|---:|
| `2026-07-28T03:27:22.828710+00:00` | 3 |
| `2026-06-19T02:36:58.649552+00:00` | 1,361 |

There are 1,261 non-null `eps_forecast` values and 103 nulls. Only four rows contain non-empty surprise histories. This historical schema has no separate `surprises_as_of` column. These are findings about one retained snapshot, not the current deployed cache.

Four selected rows all have `time-not-supplied`, empty surprise history, and the June 19 `as_of` above:

| Source label | Stored next date | Stored `eps_forecast` | Permitted interpretation |
|---|---|---:|---|
| EXPO | 2026-07-30 | 0.55 | Historical calendar-associated value with unresolved basis/vintage |
| PNR | 2026-07-28 | 1.48 | Historical value predating a material preliminary announcement |
| ULS | 2026-08-04 | 0.52 | Historical calendar-associated value, not certified latest consensus |
| ROK | 2026-08-05 | 3.31 | Same limitation; no current price or identity join performed |

The five exact labels `SGSN`, `SGSN.SW`, `SGSOY`, `RANJY`, and `RAND.AS` were absent. That does not resolve canonical security aliases or establish that SGS/Randstad data is absent elsewhere. Do not broaden an exact-label result into organization-wide data unavailability.

There are 39 calendar days between June 19 and July 28 and 41 between June 19 and Exponent's July 30 result date. These intervals describe the stored clock; they do not establish when an analyst last changed a forecast. A June-stamped estimate might coincidentally remain correct, but this file does not prove it remained the latest pre-event estimate.

## 3. Why the Exponent result is not a certified beat

Exponent's July 30 issuer release reports $0.60 diluted EPS for the quarter ended July 3, 2026. The recovered cache has 0.55 under `eps_forecast`, but does not supply GAAP/adjusted basis, diluted/basic basis, explicit forecast fiscal endpoint, contributor set, original estimate timestamp or estimate-revision sequence. Its row is not freshly observed immediately before the result.

Source W9-S01: https://investors.exponent.com/investors/news-events/news-details/2026/Exponent-Reports-Second-Quarter-2026-Financial-Results/ . Locator: release date, financial-results paragraph and statement of income. Source-reported actual and stored historical value can be displayed with their limits, but this research does not certify their comparison or label it a consensus beat.

The July 9 issuer announcement planned results after market close on July 30 and a 4:30 p.m. Eastern conference call. It can independently enrich a planned session field. The call time is not an exact publication timestamp, and neither fact repairs the forecast's missing basis or vintage.

Source W9-S02: https://www.globenewswire.com/news-release/2026/07/09/3325252/0/en/exponent-to-announce-second-quarter-of-fiscal-year-2026-results-and-host-quarterly-conference-call-on-july-30-2026.html . This is an issuer-distributed scheduling announcement, not independent analyst evidence.

## 4. Pentair demonstrates intervening-event risk

Pentair's July 14 preliminary release reported approximately $1.12 adjusted EPS against its earlier $1.47-$1.50 guidance, and separately identified preliminary GAAP EPS. It anticipated finalizing the quarter for a July 28 release. The cache's June-stamped 1.48 must not be described as the latest external expectation on July 28 without additional retained revisions and basis evidence.

Source W9-S03: https://investors.pentair.com/news-releases/news-release-details/pentair-announces-chief-financial-officer-transition-and . Locator: preliminary Q2 financial-results paragraph, July 14 publication and July 28 planned final release.

Do not replace the stored analyst-associated value with management's preliminary figure and call that consensus. The correct research view shows the management information sequence and independently qualifies any external estimate. A final-result event study must consider the preliminary disclosure rather than allocate all newly observed information to the final release.

The official Pentair page was directly readable in this turn. This resolves only the earlier direct-open source-access gap; it does not establish native immutable retention, reuse rights, intraday publication proof or estimate lineage.

## 5. Decoding method and verification limits

Network download attempts did not yield the file. The successful path was the connected GitHub read returning base64, followed by local decoding and exact hash reconciliation. There was no credential extraction, purchase, raw-provider mutation or replacement data carrier.

No standard Parquet engine was available locally. A one-file, hash-bound inspection helper was written against Apache's primary format definitions using the installed Thrift compact-protocol reader and system Snappy library. It accepts only this blob and the observed flat optional BYTE_ARRAY/DOUBLE, dictionary/plain data-page-v1 layout. It is not a general reader, new ingestion service or proposed production dependency.

Primary format references: https://parquet.apache.org/docs/file-format/data-pages/encodings/ and https://github.com/apache/parquet-format/blob/master/src/main/thrift/parquet.thrift . These document the encoding and metadata conventions; they do not independently verify this helper.

Six component tests first failed against empty implementations and then passed after implementation. Repeated complete runs remained six passed, zero failed. All six decoded columns matched the file's footer row counts, null counts, minimum/maximum statistics and page boundaries; the source ticker index was unique. Hash identity checks validate the recovered bytes, not the truth or freshness of estimates.

A standard-engine cross-check remains desirable before using decoded rows in a production decision. The authored tests and self-describing footer checks are not an independent implementation review. The raw snapshot, its base64 and full decoded rows remain local inspection inputs and are excluded from this public research publication and the portable package. No new licensed dataset is represented as acquired.

## 6. Consequence for research and product planning

There are three separately resolved questions: the historical artifact exists; selected rows can be inspected with explicit decoding limits; those rows do not yet establish fresh, basis-matched external expectations. Successful retrieval must not automatically produce an investment verdict.

The integrated catalog must retain source-row clocks rather than substitute file modification, maximum timestamp or display-build time. Unknown forecast basis blocks beat/miss, not the separately supported actual-result panel. An intervening preliminary release is visible even when the external estimate panel is unavailable. Source labels without validated listing identity do not acquire stock returns or portfolio relevance.

Next data action: the incumbent earnings/Data OS owner should confirm this exact file with its existing standard reader, then seek actual retained estimate revisions and basis for EXPO/PNR. If those do not exist, preserve this as a useful historical-data quality case and use a separately qualified event cohort; do not invent missing revisions or build another collector. Price identity, corporate actions, permissible use and publication availability still need independent qualification before a return study.
