# T13 — FRED/ALFRED source-purpose qualification evidence

**Decision input prepared:** 2026-10-17 UTC. Official pages retrieved on that date; session clock confirmed 2026-10-17 14:08:50 UTC during review and 14:13:37 UTC at artifact validation. Individual source-call clock times were not separately captured; these are review-session timestamps, not invented per-page access times.

**Scope:** Existing retained initial-release values of `THREEFYTP10` and `STLFSI4`: (1) internal statistical fitting/evaluation and (2) subsequent customer publication of derived probabilities. Raw-data redistribution is a separate purpose. This is a bounded public-source review, not a rights grant or source-register amendment.

**Internal starting position, supplied by the parent:** FRED model use is `UNKNOWN`; original T13 initial-release metadata has been inspected; no fits or trials have run. The worker did not independently re-inspect retained data, acquisition contracts, credentials, or the internal register. The parent owns current protected-procedure reconciliation and persistence into the existing programme. This worker performed read-only public research and wrote this requested scratch handoff only.

**Procedure provenance:** Parent supplied protected Mastermind commit `ad125292b34f313924f9719b8de772027f0ea225` during this review. This worker did not independently reload that commit and claims no modifying company workflow.

## Recommended disposition

**Keep both proposed model-use purposes on HOLD / not qualified.** Evidence now includes a relevant express restriction, conflicting official descriptions, and an unresolved temporal question about retained acquisitions. Do not convert `UNKNOWN` to `ALLOWED` from copyright labels alone.

| Existing retained series | Internal statistical fitting/evaluation | Customer publication of derived probabilities | Raw-data redistribution |
|---|---|---|---|
| `THREEFYTP10` | HOLD: S1–S3 and acquisition-specific terms need reconciliation. | HOLD: no concrete probability-output permission established for this acquisition path. | Separate review. S6 provides a favorable underlying Board copyright basis; it does not settle retained FRED/ALFRED service obligations. |
| `STLFSI4` | HOLD: same service-purpose issue; preserve its distinct S5 copyright status. | HOLD: attribution-based reuse status does not answer the exact model/output question. | Separate review; no public-domain inference for this Bank-owned index or its components. |

`HOLD` is a proposed operating disposition, not a conclusion that every historical use is legally prohibited. It requires no deletion, new download, source switching, or modelling action.

## Official source register

Each source has at most 25 quoted words below. Page update dates are distinguished from retrieval time and from any effective date of terms.

### S1 — Consolidated FRED Services Terms

- **URL:** <https://fred.stlouisfed.org/legal/>
- **Version/date:** Current page retrieved 2026-10-17; no document effective/update date displayed in retrieved text.
- **Locator:** Summarized Terms II–IV; Full Terms introduction, General License, Services Prohibitions (p), Additional API Prohibitions (k)–(l).
- **Exact extract (prohibited-purpose language):** “in connection with the development or training of any software program or system or machine learning”
- **Observation:** Covers ALFRED. Summary II and API (k) contain this restriction. Summary IV permits internal commercial uses/client reports for the two relevant labels, subject to prohibitions and attribution. Full Services (p)/API (l) restrict storage and archives. General licensing language is narrower than the commercial summary. Continued service use accepts changed terms. No explicit conventional-statistics or probability-output exception was found.
- **Implication:** The contemplated purpose needs reconciliation; an accessible API or favorable copyright label supplies no exemption.

### S2 — Separately served FRED API Terms

- **URL:** <https://fred.stlouisfed.org/docs/api/terms_of_use.html>
- **Version/date:** Retrieved 2026-10-17; no effective/update date displayed.
- **Locator:** Property Rights; Prohibitions; Requirements.
- **Exact extract:** “This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.”
- **Observation:** The listed prohibitions lack S1’s training and storage clauses. Owner rights remain separate from API access. Requirements include the quoted prominent notice; a FRED API application serving other users must also address terms links, user agreement language, and privacy requirements. Changes are accepted through subsequent API use.
- **Limitation:** The text mismatch is observable; this review establishes neither historical precedence nor which version governed a particular retained acquisition. Do not select the more permissive page as a unilateral waiver.

### S3 — ALFRED Help and its forecasting purpose

- **URL:** <https://alfred.stlouisfed.org/help>
- **Version/date:** Retrieved 2026-10-17; no update date displayed.
- **Locator:** “What is ALFRED?”; Legal footer link.
- **Exact extract:** “reproduce past research, build more accurate forecasting models”
- **Observation:** The Research Division explicitly describes forecasting-model research as an intended ALFRED use. Its Legal footer points to FRED’s legal page.
- **Limitation:** This is affirmative explanatory evidence, not an explicit exception for the exact proposed fitting process or customer delivery. Preserve the disagreement with S1.

### S4 — `THREEFYTP10` series identity and status

- **URL:** <https://fred.stlouisfed.org/series/THREEFYTP10>
- **Version/date:** Retrieved 2026-10-17. Series metadata updated October 13, 2026, 2:03 PM CDT; that is not a terms effective date.
- **Exact extracts:** “Public Domain: Citation Requested”; “Data in this graph are copyrighted.”
- **Observation:** The series-specific tag is the former; the page also renders the latter generic graph warning. Notes identify the Board of Governors as source and link the Three-Factor Nominal Term Structure Model release. The notes’ citation identifies the Board, series title and ID, FRED retrieval, and URL.
- **Limitation:** Preserve the banner/tag inconsistency. The current tag is not proof of the legal state at an earlier acquisition. Underlying Board notices are examined in S6–S7.

### S5 — `STLFSI4` series identity and status

- **URL:** <https://fred.stlouisfed.org/series/STLFSI4>
- **Version/date:** Retrieved 2026-10-17. Series metadata updated October 14, 2026, 11:58 AM CDT; not a terms effective date.
- **Exact extract:** “Copyrighted: Citation Required”
- **Observation:** The Federal Reserve Bank of St. Louis is identified as source. The index combines 18 weekly series; its notes reference CME’s forward-looking 90-day SOFR. The suggested citation identifies the Bank, series title and ID, FRED retrieval, and URL.
- **Limitation:** This status pertains to the published index. It does not establish licenses to redistribute, rebuild, or otherwise use each underlying third-party input separately. No such inputs were fetched.

### S6 — Federal Reserve Board copyright and disclaimer

- **URL:** <https://www.federalreserve.gov/disclaimer.htm>
- **Version/date:** Last Update August 02, 2024; retrieved 2026-10-17.
- **Locator:** Copyright/trademark; Disclaimer regarding Non-Board Information; model-specific headings.
- **Exact extract:** “information on Board's website is in the public domain and may be copied and distributed without permission.”
- **Observation:** The default applies unless otherwise indicated. Board citation is requested; identified non-Board material requires the source’s permission. General accuracy/noninfringement warranties are disclaimed. Seals/logos have separate restrictions. This notice contains no general prohibition specifically on statistical fitting or publication of derived probabilities.
- **Scope caution:** Its restrictive FRB U.S./EDO model disclaimer explicitly names those models. Do not automatically apply that subsection to Kim–Wright merely because S7’s “Model disclaimer” link reaches this page. Conversely, a general copyright permission does not determine a separate FRED acquisition agreement.

### S7 — Board’s Three-Factor Nominal Term Structure Model source page

- **URL:** <https://www.federalreserve.gov/data/three-factor-nominal-term-structure-model.htm>
- **Version/date:** Last Update November 05, 2019; retrieved 2026-10-17.
- **Locator:** Introduction; Q&A 4–7; Model disclaimer link.
- **Exact extract:** “this model is a staff research product and not an official statistical release.”
- **Observation:** The page identifies Kim–Wright implementation, supplies data links, and warns of revisions/method changes without advance notice. It distinguishes the older working-paper parameter estimate from the newer implementation.
- **Implication:** A future direct-Board acquisition would require its own provenance and vintage match. Current revised values cannot simply replace retained initial-release observations. No data links were downloaded in this review.

### S8 — St. Louis Bank’s own legal notice

- **URL:** <https://www.stlouisfed.org/about-us/legal-information>
- **Version/date:** Retrieved 2026-10-17; no update date displayed.
- **Locator:** Appropriate Use; Research Publications.
- **Exact extract:** “The Information provided on this site may be used for research and informational purposes only.”
- **Observation:** This Bank has its own terms, reserves copyrights in authored Research content, and distinguishes full unmodified article reprints from abstracts/excerpts/derivative publication requiring written permission. Its name may not be used as advertising or endorsement. Other owners’ copyrighted material needs their permission.
- **Limitation:** The article provision does not itself classify every numerical statistical transformation of `STLFSI4` as a derivative publication. It also supplies no explicit model-probability permission. Board public-domain treatment must not be generalized to the Bank.

### S9 — Creator’s `STLFSI4` explanation

- **URL:** <https://fred.stlouisfed.org/blog/2022/11/the-st-louis-feds-financial-stress-index-version-4/>
- **Version/date:** Posted November 10, 2022; retrieved 2026-10-17. Older `fredblog.stlouisfed.org` URL redirects here.
- **Exact extract:** “using the forward-looking SOFR better captures financial market expectations”
- **Observation:** The official explanation confirms the version-four benchmark change and rationale. It offers methodology context, not an additional purpose-specific license.

## Interpretation boundaries and unresolved evidence

1. **Existing retention is the actual object of review.** Acquisition dates, accepted terms, any written consents, and the exact retained manifests were outside this worker’s evidence. No grandfathering or retroactive enforceability conclusion is justified. Retention compliance itself needs the owner’s review; this note does not order deletion.
2. **Internal evaluation needs a precise specification.** A model-selection/evaluation process is not automatically exempt because it is called research, conventional statistics, or non-generative modelling. The method, software-development relationship, audience, and output need to be described for a defensible purpose decision.
3. **Derived probabilities are distinct from raw observations, but that distinction is not an automatic license.** Define exactly what clients receive, whether observations could be reconstructed, whether index values/charts are included, and whether users interact with a FRED API application. A lawful model-development path and a publication path each need support.
4. **Source acquisition and copyright are different questions.** A favorable underlying notice may support a genuinely separate, authorized source route. It does not retroactively relabel retained ALFRED data or establish identical initial-release vintages. No route change is proposed as a bypass.
5. **Attribution is a condition, not approval.** On any later qualified release, identify the appropriate Board/Bank source, series ID, actual FRED/ALFRED provenance, actual retrieval/vintage dates, and source URL; retain applicable notices and clearly identify Mastermind’s own analytical output. Apply S2’s application notice if that implementation is within its scope. Do not fabricate historical dates or imply Fed endorsement.

## One bounded next action

Have the existing source-purpose owner reconcile the retained acquisition record and the exact proposed operations against S1–S3, S6, and S8. The falsifier for this HOLD is an authoritative, acquisition-and-purpose-specific basis that permits retention plus fitting/evaluation and specifies whether the proposed customer output is covered. A general public-domain tag or a functioning API is insufficient.

Concrete question for that internal review (not sent externally):

> For the retained initial-release `THREEFYTP10` and `STLFSI4` observations identified by the existing manifest and acquisition dates, what applicable terms or written consent permit internal classical statistical fitting/evaluation, continued retention, and paid-client publication of only non-reconstructive probabilities? Do the software/machine-learning clauses apply to this exact operation, and what attribution/application conditions apply?

## Actions actually performed

- Read the bootstrap and research-analyst craft instructions; no company action or rights authority inferred from them. The bootstrap’s external authority-reference resource was unavailable to this worker, so no modifying workflow was claimed.
- Retrieved the nine official pages above and inspected relevant text/links. An initial search returned irrelevant results; no non-primary search result supports this note.
- Inspected no keys or account identifiers, made no authenticated data requests, hydrated no time series, performed no model calculations, and sent no external inquiries.
- Made no Git, Linear, Studio, source-register, or execution-state mutations. The only artifact is this requested evidence handoff.
