# Outcome-blind funding-source audit: October 6, 2026

**Disposition: accounting feasibility demonstrated; H3 pre-settlement prediction remains `INSUFFICIENT_PIT` and `NOT_TESTABLE_FROM_RETROSPECTIVE_RECEIPTS`.** The captured sources support a reconciled daily Treasury cash observation and identify a concrete error that would arise from treating gross debt accounting as private settlement cash. They do not supply a complete, prior-known private settlement ledger. `net_private_cash_usd`, `reserve_pressure`, and any predictive probability remain null.

Prepared for the existing Sovereign Auction and Funding Pressure Intelligence program under `WS:RATES-INFLATION-COMMAND`. This is a bounded source and accounting audit. It introduces no owner, data plane, scheduler, model, deployment, risk input, sizing rule, exit rule or live alert. The existing SLF006 **NO-GO**, D2 **FAIL**, and Terminal **KILL** conclusions remain in force. No new null reversal is claimed.

## 1. Scope and evidence custody

The audit uses twelve official source responses already captured on October 8, 2026, plus one previously captured Treasury auction response and an exact pinned copy of Macro's Treasury collector. It verifies the original response hashes and receipt clocks before doing arithmetic. No new source request or model fit was made for this report. Rate-response bytes are preserved, but the audit uses only schema, effective-date, unit and revision metadata; it constructs no market outcome series, measures no funding response, and estimates no prediction or causal effect.

The reproducible data product is [OUTCOME_BLIND_FUNDING_CASEBOOK.json](OUTCOME_BLIND_FUNDING_CASEBOOK.json), produced by [outcome_blind_funding_audit.py](outcome_blind_funding_audit.py). The casebook's accounting date is **2026-10-06**. Its illustrative S−1 decision cutoff is **2026-10-05 16:00 America/New_York**, or **20:00 UTC**. That cutoff is an audit design choice, not evidence that any model or collection process was running then.

All twelve new captures have separately recorded `request_started_at`, `body_received_at`, and `verified_present_at`. The script checks their causal ordering. For this audit, `known_at_upper_bound` is the original verified local availability timestamp. Every `published_at` remains null; HTTP `Date` and `Last-Modified` values are preserved as response metadata and are not promoted to verified first-publication timestamps. The source ledger below provides URLs, original hashes and receipt clocks. The earlier linked auction capture has no independently recorded response-completion clock; its original conservative `verified_present_at` is preserved without relabeling it as a body receipt.

## 2. Five distinct quantities, with exact units

All figures in this section are **USD millions**, as declared by the API metadata and the DTS report. The arithmetic is exact on the published rounded values. The DTS cautions that underlying detail is rounded; this is not a certification of dollar-level settlement cash.

| Quantity for October 6 | Calculation | Result, USD million | Admissible meaning |
|---|---|---:|---|
| Regular Bill issues less all Bill redemptions in the selected marketable slice | 283,770 − 272,735 | **11,035** | Net Bill face-value debt transactions for this day. CMB issues are a sourced zero. No private-holder attribution is established. |
| Marketable Table IIIA net debt accounting | 283,993 − 272,735 | **11,258** | Includes **223** of TIPS principal indexation. It is not equivalent to cash raised. |
| Restricted marketable cash-basis bridge | 11,258 − 223 − 2,010 | **9,025** | Bounded inference after removing TIPS indexation and Bill new-issue discount. It is not certified private proceeds or complete private net cash. |
| All public-debt cash issues less cash redemptions, Table IIIB | 291,668 − 280,670 | **10,998** | Wider Treasury public-debt cash scope, including nonmarketable categories. It is not the selected marketable cohort or a private-holder measure. |
| TGA closing less opening balance | 885,414 − 883,335 | **2,079** | Realized modified-cash accounting change after all reported Treasury deposits and withdrawals. It is not a pre-settlement feature or a standalone reserve-pressure estimate. |

The marketable API slice contains ten rows and reports one complete page, with no next-page link. That supports completeness of **this query**, not completeness of the private cash ledger. The six issue rows total 283,993: regular Bills 283,770, CMBs 0, Notes 0, Bonds 0, TIPS principal increment 223, and Federal Financing Bank 0. The four redemption rows total 272,735: Bills 272,735 and the other displayed marketable categories zero. These are direct source observations. [S3, S4, S12]

### TGA reconciliation

The four uniquely identified operating-cash rows reconcile:

`883,335 opening + 299,916 deposits − 297,837 withdrawals = 885,414 closing`.

The reconciliation difference is zero on the published values; the daily change is 2,079 million, or 2,079,000,000 USD at the source's rounding precision. In this API schema, the amounts for all four current TGA rows, including the row labeled closing balance, reside in `open_today_bal`. Choosing the column by its name alone would misread this response. [S3]

Table II supplies a separate check: non-debt deposits of 8,248 minus non-debt withdrawals of 17,167 are −8,919; adding the broader public-debt cash net of 10,998 yields the same **2,079** TGA change. This agreement does not identify which banking-system balance-sheet accounts absorbed the change. The DTS describes a modified cash basis, with deposits recognized as received and withdrawals as processed. [S12, PDF pages 2–3]

### Why 9,025 is an inference with a restricted scope

Table IIIA explicitly states that debt transactions are at face value except for the specified savings/retirement securities. The **223 TIPS principal increment** is recorded on the issue side of that debt table and then explicitly subtracted in Table IIIB's conversion to cash. Table IIIB also subtracts **2,010 of Bill discounts on new issues**. Premium on new issues and discount on new Notes/Bonds are reported as zero in the day's Table IIIB column. Removing the two nonzero adjustments from the selected marketable net produces **9,025**. [S12, PDF page 3]

This bridge does not contain a verified allocation between private holders and SOMA, a security-level cash-proceeds ledger, a complete private maturity ledger, or separately certified funded buyback cash. A zero in the Table IIIB buyback premium/discount adjustment is not proof that there was no buyback principal cash flow. Accordingly, the bridge is labeled `bounded accounting adjustment inference; not private cash certification`. It cannot be renamed `net_private_cash_usd`.

The **10,998** broader public-debt cash net is directly reported by Table IIIB's two total cash rows. Its difference from the inferred restricted marketable bridge is **1,973**, which merely demonstrates a scope difference here. The audit does not assign that residual to a particular investor category or reserve channel. [S12]

## 3. The auction-to-funding link is a date link, not payment proof

A previously captured TreasuryDirect row for **CUSIP 912797VP9**, auctioned **2026-10-01**, reports issue date **2026-10-06** and competitive deadline **11:30 AM**. The casebook links that episode to the October 6 accounting day using the reported issue date. It does not allocate aggregate DTS flows to that CUSIP, assert observed purchaser payment, or convert passage of the issue date into confirmed settlement. `individual_settled_payment_observed` and the episode's private net cash remain null. [A1]

The separate lifecycle implementation may preserve scheduled issue dates and result observations. H3 still needs a settlement cohort that reconciles the entire admissible private cash universe by S. Repeating the same aggregate funding outcome once for every CUSIP would create false independent observations; the adopted H3 candidate's unit is one settlement-day cohort.

## 4. Public release rules constrain point-in-time eligibility

| Input | What the captured official source establishes | Consequence for the first H3 version |
|---|---|---|
| DTS | Its footnote says the statement is available by 4 p.m. on the following business day; the captured footnote does not specify a timezone. Weekends and federal-holiday transactions are included in the next business-day statement. [S12, PDF page 3] | S-day DTS is a later descriptive accounting observation. The publication policy is not an observed release timestamp or an S−1 feature license. |
| Treasury repo reference rates | SOFR is normally published at approximately 8 a.m. ET for the prior business day's value date. Same-day affected TGCR/BGCR/SOFR releases can be revised at about 2:30 p.m. ET under the described conditions, with rate revisions requiring a change greater than one basis point. Lagged quarterly summary statistics may differ from originally published data. [S10] | Preserve effective date, first observed print, revision flag, receipt time, and exact version separately. Final or quarterly statistics cannot silently replace the original decision-time input. |
| Primary dealer statistics | The page states Thursday updates at approximately 4:15 p.m. with the preceding week's statistics; the displayed sentence does not specify a timezone. It also notes historical schema periods. [S9] | Use only a captured, released weekly vintage at the decision cutoff. Do not interpolate from a later report or treat the observation week as the release time. |
| QRA / borrowing estimates | The August 3 page distinguishes privately held borrowing from SOMA rollovers and financing related to SOMA redemptions. Its buyback statement describes expected replacement issuance. [S7] | The convention is useful for the definition; it does not supply a daily private cash ledger or prove cash-basis settlement terms. |
| Refunding announcement | The August 5 page describes planned auction sizes, settlement dates, approximate new cash, and prospective buyback capacity. [S8] | Plan, announced terms, realized allocation, and funded buyback cash need distinct observations. A quarterly cap or expectation is not an S-day realized cash amount. |
| SOMA page | The capture identifies the official holdings source page. [S11] | This HTML capture provides no audited security-level SOMA dataset, release clock, or forecast-eligible daily adjustment. Such coverage remains unverified. |

For the specific S−1 cutoff of October 5 at 20:00 UTC, **zero of the twelve new source receipts is eligible**: they were first recorded locally on October 8, from 22:27:29.795684 to 22:27:39.028795 UTC at body completion. This is a statement about this evidence collection, not a claim that every item was unavailable anywhere on October 5. Some underlying plans had earlier document dates, but their exact historical bytes and first release times have not been certified here. The October 6 DTS and funding result observations are also post-S−1 quantities by their economic dates and stated publication conventions.

`record_date`, `effectiveDate`, an auction's issue date, the date printed in a document, HTTP metadata, and retrieval time are separate clocks. The audit uses none as an interchangeable substitute for another.

### Coverage sampled, not a certified history

The ascending one-row DTS request returned **2005-10-03**, using the older `Federal Reserve Account` row and `close_today_bal`. The descending one-row request returned **2026-10-07**, specifically a TGA **opening** row; that request alone does not establish the latest complete closing-balance day. The TGCR first-week query returned five observations with effective dates April 2–6, 2018. The latest rate response contains five overnight-rate types with effective date October 7, 2026, plus a SOFR averages/index record with effective date October 8. These are bounded coverage and schema observations. Full intervening history, first-release archives, and revision completeness were not audited. No rate level is used to evaluate H3. [S1, S2, S5, S6]

## 5. Current Macro collector is not a private cash input

The inspected source is [`collectors/treasury.py` at `d2eec4732abee359ebb578b245fa7359b3c01a7d`](https://github.com/mastermindx-market-intelligence/macro/blob/d2eec4732abee359ebb578b245fa7359b3c01a7d/collectors/treasury.py). The preserved copy's Git blob is `a79b9d373baef7c94d9ce2e096b59a211825c7d3`, independently recomputed from its bytes. It was read, not executed or modified.

`_fetch_issuance` requests marketable Table IIIA rows, retaining `record_date`, transaction type, marketability and amount. It omits the security-type fields required to distinguish Bills, nominal coupons, TIPS accounting increments and other categories. It coerces nonnumeric amounts and applies `fillna(0)`, aggregates by issue/redemption type, then subtracts with zero defaults for entirely absent transaction-type columns. Its output has the legitimate narrow meaning described in that collector: net marketable debt transactions. It is not a completeness-certified private cash ledger.

On this complete captured slice, those operations would produce **11,258 million**, including the 223 TIPS increment; they do not produce the inferred 9,025 bridge, the broader 10,998 public-debt cash net, or a certified private cash result. This numerical consequence is derived from the audited source and captured rows; the live collector was not invoked.

The collector's emitted frames also contain no per-observation receipt clock, immutable raw response hash, source revision identifier, investor allocation, price/discount convention, or completeness certificate. Its incremental date backfill cannot itself prove which vintage was available at an earlier decision. `_fetch_tga` correctly contains separate selectors for the two observed schema eras, but the returned dated series still lacks the required vintage metadata. This audit does not alter the collector or its existing consumers. The new H3 ledger must not relabel its `net_issuance_mn` output as private cash or infer zero from missing records.

## 6. Executable data gate for H3

The adopted research design defines the primary target as the S-to-S−1 change in **TGCR minus IORB**, after actual subsequent publication, with separately declared SOFR and later-horizon secondary endpoints. This audit does not calculate those targets or start the prospective evaluation window. [Program reference: H1_H5_PREREGISTRATION_CANDIDATE.md, H3]

The next admitted acquisition should produce the following receipts in the existing source owner. This is a precise acquisition frontier, not a claim of ongoing unattended collection:

1. **Cohort terms available by cutoff.** Preserve every original and amended announcement/result used to establish S-day issue and maturity terms, stable episode identity, class, amount, auction/issue dates, source timestamps and first local availability. Separate scheduled terms known at S−1 from later confirmations. A partial cohort remains incomplete.
2. **Private issue cash by security and settlement day.** Acquire source-qualified proceeds or the complete inputs required to compute them, including the applicable discount/premium, accrued-interest and TIPS/FRN conventions. Store amount basis and units. Distinguish an explicitly labeled pre-cutoff estimate from post-result actual proceeds; do not backfill actuals as forecasts.
3. **Explicit SOMA treatment.** Reconcile rollovers/add-ons, redemptions and the investor universe using dated source observations. Apply the chosen private-proceeds convention exactly once. A holdings webpage or a SOMA stock level alone does not establish the cash adjustment.
4. **Complete private redemptions and funded buybacks.** Acquire cash redemptions for the same universe and S, plus funded buyback cash outlays and settlement dates. Record a sourced explicit zero when appropriate. Missing inventory is null. Do not subtract a buyback twice if it is already part of the redemption measure.
5. **Lagged funding baseline vintages.** Preserve the actual prior-known TGCR/SOFR and policy-rate observations, relevant reserves/ON-RRP state, canonical liquidity state, and known tax/month/quarter/Fed-operation calendars. Capture dealer statistics and, only when entitled and admitted, government-MMF AUM with release receipts; never fill a weekly input using the future endpoint. The audited twelve-response set contains no IORB series or complete baseline ledger.
6. **Outcome versions kept outside the feature cutoff.** Retain the next actual TGCR/SOFR publications and any same-day revisions with original bytes and receipt clocks. Freeze the outcome-version policy before measuring performance. Preserve the distinction between a daily rate, its published percentiles/volume, SOFR averages/index and lagged quarterly statistics.
7. **Freeze and independent acceptance.** Emit a column-level eligibility/completeness manifest proving `max(input_known_at) <= decision_cutoff` for every admitted cohort and canonical baseline. Obtain independent raw-source/accounting/PIT review, then freeze exact model, dataset and evaluation specification digests before statistical execution. A prospective timer begins only at the first successfully logged cutoff after that freeze and collector readiness; it cannot be backdated to this report.

Only a complete, same-currency, same-cohort ledger can evaluate the proposed formula: **private proceeds excluding SOMA − private cash redemptions − separately funded buyback cash not already included in redemptions**. Bill/CMB and coupon channels remain separately identified. The formula alone is not a source or a completeness certificate. Until the listed inputs qualify, H3 is not executable as an S−1 forecast and the product remains descriptive context. A TGA rise, net par issuance, or deterministic attention rank does not create a predictive probability or change risk authority.

## 7. Verification and reproduction

Run `python3 outcome_blind_funding_audit.py --check` from this directory (Python 3 with `pdftotext` available). The script reads only local captured bytes and compares the exact recomputation to the existing casebook; it does not fetch data. It supports the original sibling `research_source/` layout and the canonical evidence-bundle sibling `source_audit/` layout. The verification receipt records a successful check in both layouts.

Checks cover all twelve original response hashes/lengths, causal ordering of receipt clocks, USD-million metadata, complete queried pages, unique accounting rows, exact TGA reconciliation, the reported PDF cash-adjustment lines, the linked auction's original hash and fixture equality, and the explicit distinction between a sourced zero and a missing amount/category. An independent arithmetic check also verifies the five displayed quantities. The collector source is checked against its recorded Git blob. [OUTCOME_BLIND_FUNDING_VERIFICATION.json](OUTCOME_BLIND_FUNDING_VERIFICATION.json) records commands, versions, source and output hashes, and the bounded acceptance results.

No historical predictive test, new model, prospective start, production health claim, release publication, or live decision effect is established by these checks.

## Source ledger

The following identifiers refer to exact captured bytes. Every listed request returned HTTP 200. `body_received_at` is actual recorded body completion; `verified_present_at` is the conservative local availability upper bound used by this audit. Neither is asserted to be the official publication timestamp. Full response metadata remain in [SOURCE_RECEIPTS.json](SOURCE_RECEIPTS.json).

### S1. dts_tga_earliest.json

- Official URL: <https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?sort=record_date&page[size]=1>
- Preserved file: [raw/dts_tga_earliest.json](raw/dts_tga_earliest.json)
- SHA-256: `fbfc9a92a2e209227fa4dc1c5df76422d223f686ce89d0a1128a2696d2982337`
- `body_received_at`: `2026-10-08T22:27:30.099869+00:00`
- `verified_present_at`: `2026-10-08T22:27:30.100106+00:00`

### S2. dts_tga_latest.json

- Official URL: <https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?sort=-record_date&page[size]=1>
- Preserved file: [raw/dts_tga_latest.json](raw/dts_tga_latest.json)
- SHA-256: `c388e2f5b145b487886bf8f22ef83fd7a7549be6d0ad0870d20c470c68bc5657`
- `body_received_at`: `2026-10-08T22:27:29.911015+00:00`
- `verified_present_at`: `2026-10-08T22:27:29.911271+00:00`

### S3. dts_oct6_cash.json

- Official URL: <https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?filter=record_date:eq:2026-10-06&page[size]=100>
- Preserved file: [raw/dts_oct6_cash.json](raw/dts_oct6_cash.json)
- SHA-256: `62ffe3fd20b6be16bf9032c610bc6519a4c67a306e2abfdd01efb310930110a0`
- `body_received_at`: `2026-10-08T22:27:29.942455+00:00`
- `verified_present_at`: `2026-10-08T22:27:29.942677+00:00`

### S4. dts_oct6_marketable.json

- Official URL: <https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/public_debt_transactions?filter=record_date:eq:2026-10-06,security_market:eq:Marketable&page[size]=100>
- Preserved file: [raw/dts_oct6_marketable.json](raw/dts_oct6_marketable.json)
- SHA-256: `b0b94aa828bbccdb3569cfe4d7da73bc875ce7566fe714c426be4bdc4e4047c2`
- `body_received_at`: `2026-10-08T22:27:29.795684+00:00`
- `verified_present_at`: `2026-10-08T22:27:29.795981+00:00`

### S5. nyfed_latest_rates.json

- Official URL: <https://markets.newyorkfed.org/api/rates/all/latest.json>
- Preserved file: [raw/nyfed_latest_rates.json](raw/nyfed_latest_rates.json)
- SHA-256: `be758c3a876678ae5e4e9994b3d2f590a4b4aca4d27b25e8bd4b8877dd68584d`
- `body_received_at`: `2026-10-08T22:27:35.418604+00:00`
- `verified_present_at`: `2026-10-08T22:27:35.418811+00:00`

### S6. tgcr_first_week.json

- Official URL: <https://markets.newyorkfed.org/api/rates/secured/tgcr/search.json?startDate=2018-04-02&endDate=2018-04-06>
- Preserved file: [raw/tgcr_first_week.json](raw/tgcr_first_week.json)
- SHA-256: `bc9257917b9d0679efda838cb0564b2705253110352d29bc0fad96273606960c`
- `body_received_at`: `2026-10-08T22:27:35.199528+00:00`
- `verified_present_at`: `2026-10-08T22:27:35.199773+00:00`

### S7. borrowing_aug3_2026.html

- Official URL: <https://home.treasury.gov/news/press-releases/sb0584>
- Preserved file: [raw/borrowing_aug3_2026.html](raw/borrowing_aug3_2026.html)
- SHA-256: `e6cb93ff233da9b54f85c73c54f9bb80a7fe6f04dd954d52449ab92e97670eb7`
- `body_received_at`: `2026-10-08T22:27:33.785355+00:00`
- `verified_present_at`: `2026-10-08T22:27:33.785920+00:00`

### S8. refunding_aug5_2026.html

- Official URL: <https://home.treasury.gov/news/press-releases/sb0590>
- Preserved file: [raw/refunding_aug5_2026.html](raw/refunding_aug5_2026.html)
- SHA-256: `72631461826a85f2acc0f3ef782559daee51a0e562cb9c6ad6c6326909e18684`
- `body_received_at`: `2026-10-08T22:27:33.860009+00:00`
- `verified_present_at`: `2026-10-08T22:27:33.860501+00:00`

### S9. dealer_publication.html

- Official URL: <https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics>
- Preserved file: [raw/dealer_publication.html](raw/dealer_publication.html)
- SHA-256: `4946c072e4aa907c7ea59ecac754aeee0eb38dd875a1c550e94c1ae9ff568c65`
- `body_received_at`: `2026-10-08T22:27:37.315779+00:00`
- `verified_present_at`: `2026-10-08T22:27:37.316377+00:00`

### S10. reference_rates_policy.html

- Official URL: <https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates>
- Preserved file: [raw/reference_rates_policy.html](raw/reference_rates_policy.html)
- SHA-256: `8504d51f3c946d17adb9d398bfd9fd5d2937d479e853cb7cb51d408aaf9a0ae6`
- `body_received_at`: `2026-10-08T22:27:37.633851+00:00`
- `verified_present_at`: `2026-10-08T22:27:37.634438+00:00`

### S11. soma_holdings.html

- Official URL: <https://www.newyorkfed.org/markets/soma-holdings>
- Preserved file: [raw/soma_holdings.html](raw/soma_holdings.html)
- SHA-256: `a96c3af46677f3dc8a82dddf11fd7c088c35f50c1c1811674e0065dd1e346ab9`
- `body_received_at`: `2026-10-08T22:27:37.468277+00:00`
- `verified_present_at`: `2026-10-08T22:27:37.468966+00:00`

### S12. dts_oct6.pdf

- Official URL: <https://fiscaldata.treasury.gov/static-data/published-reports/dts/DailyTreasuryStatement_20261006.pdf>
- Preserved file: [raw/dts_oct6.pdf](raw/dts_oct6.pdf)
- SHA-256: `9a6157f2e09e77a6c4cb067e3c59a2feb1991aad33b31df96dd95f1b8d3b3a2e`
- `body_received_at`: `2026-10-08T22:27:39.028795+00:00`
- `verified_present_at`: `2026-10-08T22:27:39.029475+00:00`

### A1. Linked auction source

- Official URL: <https://www.treasurydirect.gov/TA_WS/securities/search?auctionDate=2026-10-01,2026-10-08&format=json>
- Preserved canonical source: `../source_audit/raw/treasury_october_search.json`
- SHA-256: `6bfd4be850a178cbad2462d38dec71fe6583315d79f65aa4a9c8bc9613cd26ab`
- `request_started_at`: `2026-10-08T22:08:49.746266+00:00`
- `verified_present_at`: `2026-10-08T22:12:22.414829+00:00`
- Original body receipt: unrecorded; not reconstructed.
