# Primary-source fixture acquisition follow-up

**Completed locally: 2026-10-20. No production observation was admitted.**

## India: original artifact acquired and verified

- Source: https://www.mospi.gov.in/uploads/latestReleases/latest_release_1788172583113_d65a77cf-240e-4491-82ee-59f78618fa41_Press_Note_on_GDP_Estimates_for_Q1_2026-27.pdf
- Artifact: `primary_artifacts/mospi_q1_fy2026_27_20260831.pdf`.
- HTTP 200; final URL equals requested official URL; no redirects.
- Retrieved: `2026-10-20T21:04:50.418704+00:00`.
- Original bytes: **821,560**.
- SHA-256: `152d9020853769fe4fe4433bec038a558aae1312bbb13ec072058e8dd5b0bc49`.
- Content-Type: `application/pdf`; Content-Length: `821560`.
- Last-Modified: `Mon, 31 Aug 2026 10:36:23 GMT`; ETag: `W/"c8938-1a057644119"`.
- Full selected response identity and acquisition clock are in `primary_artifacts/in_acquisition_receipt.json`. The receipt records acquisition, not admission.

### Native evidence

The 12-page PDF's physical page 2 / printed page 1 identifies Q1 FY 2026–27 as April–June, constant prices at base 2022–23, and the 2026-08-31 publication. Physical page 3 / printed page 2 says: **“Real GDP has been estimated to grow by 7.8%”**. The source status is **“Quarterly Estimates”**; the release discusses subsequent revisions. It is a completed historical quarter, not an annual forecast.

Physical page **9 / printed page 8** contains Statements 1 and 2 at constant prices. The column label is **“Percentage Change Over Previous Year”**. Unit wording: **“(in ₹ Crore)”**. Both GDP rows agree:

| Native period | Constant-price level |
| --- | ---: |
| Q1 FY 2024–25 | 7,061,843 |
| Q1 FY 2025–26 | 7,546,230 |
| Q1 FY 2026–27 | 8,136,153 |

The published current rate is **7.8%**; previous-year rate is **6.9%**. The current/prior level ratio rounds to 7.8%. Use the published rate and its one-decimal precision, retaining the native levels as a cross-check.

The normalized calendar period is **2026-Q2**, with dates 2026-04-01 through 2026-06-30. The native display remains **Q1 FY 2026–27**. Physical page 10 contains current-price/nominal statements and must not be substituted.

No explicit seasonal-adjustment designation was found in the complete extracted text or the visually reviewed constant-price table. The local parser therefore returns `seasonal_adjustment=not_stated`, not SA or NSA. The next quarter's scheduled release is 2026-11-30, as stated on physical page 8 / printed page 7.

Physical page 9 was rendered and visually checked against the extracted rows. The correct browser fragment is **#page=9**. The earlier handoff's web-reader P8 is printed-page/web-index evidence, not a physical page number.

### Executable local verification

- `india_fixture_parser.py`: one-release, original-byte-hash-pinned parser prototype. It performs no requests and does not write product inputs.
- `india_fixture_probe.py`: actual PDF + receipt check and 17 targeted rejection cases.
- Actual execution: **18 checks passed, exit 0**, tool chunk `c9099b`, run clock `2026-10-20T21:09:35.562357+00:00`.
- `primary_artifacts/in_fixture_probe_receipt.json` records the cases, actual source hash and parser/probe hashes.
- `primary_artifacts/in_parser_result_research_only.json` contains the parsed candidate, with `research_only=true`, `production_admitted=false` and no first-production-admission clock.

The first prototype run exposed PDF text-order interleaving in the multi-row table headers. The parser was corrected to accept the observed bounded interleavings while continuing to reject sequential-growth headings. The subsequent real-fixture run passed.

This remains a research prototype. Production integration still requires the collector/quarterly-admission/revision-selection/view/template changes described in the original handoff.

## Taiwan: actual source bytes unavailable through this route

Three bounded public GETs in approved network-enabled local executions completed with HTTP 503 and the same 98-byte upstream connection-failure response:

1. English release: https://eng.dgbas.gov.tw/News_Content.aspx?n=4438&s=236587
2. Official Chinese release: https://www.stat.gov.tw/News_Content.aspx?n=2677&s=236591
3. Official Chinese PDF, newly discovered in an indexed publisher result: https://ws.dgbas.gov.tw/001/Upload/463/relfile/10980/236591/news11508.pdf

The third URL is observed from the official-domain search result, not guessed. The web reader independently returned 502 for these resources. Neither path returned the release itself.

Failure receipts are preserved at:

- `primary_artifacts/tw_acquisition_receipt.json`
- `primary_artifacts/tw_chinese/tw_acquisition_receipt.json`
- `primary_artifacts/tw_pdf/tw_acquisition_receipt.json`

They retain HTTP clocks/headers and an **error-response** hash while keeping `source_artifact`, `source_sha256` and `source_bytes` null. Their body hash is `33fbc61ad080ef68dd7a6479f8c53f1bf864dba2930567dbbc4ceb47490a1909`; it is not a GDP artifact hash.

No Taiwan parser fixture was invented. The previous indexed-source findings remain research-only. Next useful action is a working authorized network route to the identified DGBAS PDF or retrieval of the same original artifact from established project evidence storage.

## Artifact and permission boundary

All files are under the shared scratch directory `intl_gdp_coverage_20261020`. No remote Mac process, production/config/source-repository mutation, or Firecrawl job was used. The initial ordinary-sandbox socket denials are retained separately under `primary_artifacts/sandbox_denied/`; subsequent network-enabled executions were approved. All acquisition processes finished. No unknown or pending request was retried.

See `PRIMARY_FIXTURE_MANIFEST.json` for exact local paths, byte lengths and hashes.

