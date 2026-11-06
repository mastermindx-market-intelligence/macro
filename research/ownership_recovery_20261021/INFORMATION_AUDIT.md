# Information availability and forward-outlook research

Observed 2026-10-21. This audit qualifies the specific bindings inspected, not the entire company's possible data inventory. It does not admit any new production feature.

## Retained data

The installed Data Workspace capability receipt identified implementation revision `e5e84272bc9128e2577f907de4d4960e84950a9b`. Advertised actions included bounded dataset search/read/describe, history dossiers and Tiingo statement comparison. The current capability list did not advertise a transcript-history action; a transcript file was nevertheless found. Tool absence and dataset absence are different claims.

| Observed binding | Evidence | Permitted interpretation |
|---|---|---|
| `macro_snapshot:earnings/earnings.parquet` | 2,315 rows; `as_of` is 2026-09-30T03:23:30.310911Z; columns include next date/time, EPS forecast, surprises JSON and its as-of clock | Current snapshot containing historical-looking observations. Original consensus vintage is unproven. |
| `fundamental_history:us_fund/A.json` and bounded fundamental-root inventory | 4,502 JSON filenames; inspected schema includes fetched time, annual/quarterly statements, estimates, EPS trend, calendar and errors | Available fields can guide source research. A current file does not establish historical availability. |
| `fundamental_history:transcripts/stock_earning_call_transcripts.parquet` | Presence and metadata verified; 2,278,710,963 bytes | Corpus exists. Body completeness, event clocks, revisions and point-in-time eligibility were not tested. |
| Current stock price binding | 251 files; WMT columns include close, high, low, volume and Date, but no open | Insufficient for this next-open reconstruction. No open was synthesized from close. |
| History filing capability | Item 2.02 metadata requires retained manifest/hash and accession identity | A filing roster is not automatically a release clock or complete earnings calendar. |
| Tiingo comparison capability | Explicit retrospective/exploratory status and PIT false | Suitable for labeled retrospective comparisons; not a point-in-time trading gate. |

The earnings snapshot's surprises-as-of values span August through September 2026. Example historical EPS surprises inside an MCD row were available in that snapshot, but this audit found no proof that their current values and definitions existed at the historical decision dates. The relevant original availability remains unknown. No private earnings or transcript body is reproduced in the publication.

## Two illustrative original-disclosure cases

The four primary documents below were read on 2026-10-21. Historical release dates are known; an automated first-publication timestamp contract has not been built. The examples are purposive measurement cases, not a blind sample, a prevalence estimate or a return test.

| Case | Comparable evidence | Classification and limit |
|---|---|---|
| Walmart, 2022-07-25 to 2022-08-16 | FY23 adjusted-EPS growth guidance improved from a decline of 11-13% to a decline of 9-11%; August explicitly maintained the back-half outlook | Annual headline improved; realized-period information changed; remaining-period outlook explicitly unchanged. Do not infer a new forward operating upgrade. |
| Clorox, 2021-11-01 to 2022-02-03 | FY22 adjusted-EPS range changed from $5.40-$5.70 to $4.25-$4.50; margin outlook worsened while sales outlook improved | Preserve mixed metric directions. Revenue improvement is insufficient evidence of profitability repair. |

The Walmart releases both already included the specified Chile insurance and JD.com dividend items. Their appearance in August is not evidence that new exceptional income caused the entire guidance revision. The issuer's own remaining-period statement is the decisive classification evidence. The Clorox case does not by itself isolate how much of the annual revision concerned completed versus remaining periods.

Original sources:

- [Walmart July release](https://corporate.walmart.com/news/2022/07/25/walmart-inc-provides-update-for-second-quarter-and-fiscal-year-2023)
- [Walmart August release](https://stock.walmart.com/sec-filings/all-sec-filings/content/0000104169-22-000065/earningsreleasefy23q2.htm)
- [Clorox November remarks](https://s204.q4cdn.com/178752512/files/doc_financials/2022/q1/Q1FY22-Clorox-CEO_CFO-prepared-consolidated-remarks.pdf)
- [Clorox February release](https://investors.thecloroxcompany.com/news/news-details/2022/Clorox-Reports-Q2-Fiscal-Year-2022-Results-Updates-Outlook/default.aspx)

## Candidate feature contract

Each record should preserve issuer/security identity, original release identifier and content hash, first verifiable public timestamp with timezone and precision, retrieval timestamp, fiscal period, metric and units, accounting/currency/perimeter basis, prior forecast source and availability, current range, directly stated remaining-period forecast, realized-performance bridge, other effects, and the explicit unresolved residual.

Use separate directions for annual headline, remaining-period operations, sales, margins and profit. Allowed directions are improved, unchanged, deteriorated, mixed and unknown. Evidence status is direct quantified, direct qualitative, reconstructed or unavailable. Forecast age, supersession and expiry are part of the feature. Do not turn missing guidance into unchanged guidance or an issuer update into a consensus surprise.

For additive amounts, a valid bridge can separate completed-period contribution from remaining expectations. EPS and margin percentages need special handling: weighted-average shares, adjustments and revenue weights can prevent simple subtraction. Comparability failures remain unknown.

The first acceptance gate is a blinded extraction/reconciliation exercise on original disclosures, with adjudication independent of subsequent returns. Only after availability and reproducibility are demonstrated should the feature be tested against reference-low survival, adverse excursion and entry utility. Unknown and no-guidance cases must remain in the census.

## Filing clock limits

[SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf) generally allows four business days for the report. [SEC Question 106.04](https://www.sec.gov/rules-regulations/staff-guidance/compliance-disclosure-interpretations/exchange-act-form-8-k) addresses an earnings release attached to a 10-Q. Accordingly, original release time, filing time and research retrieval time must remain separate. Failure to retrieve an Item 2.02 record is not proof that no relevant news existed.
