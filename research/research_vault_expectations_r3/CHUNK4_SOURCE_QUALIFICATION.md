# Research Vault — Chunk 4: original-source qualification and revision identity

**Product state: SPEC_ONLY. Research finding and contract refinement, not a production release.**

Carrier: existing draft Macro PR #7182, branch `sol/research-vault-intelligence-design-r2-20260915`; starting head `b73ab1588bf0efc4c68b31c2700daf9f00a258e8`. Procedure: protected Mastermind `f590c068880dbb848bda90b80b73dbcb6688d6fc`, Skillpack 1.0.1 / bootstrap 1, including the newly enrolled Web CEO delegation companion. Implementation/data inspection: Macro `112eba2036fd1186e67b914e194f4fa541cfc4df`.

## 1. What changed in this chunk

We now have a **public-original institutional forecast sequence**, not only the earlier issuer-guidance control. The sequence demonstrates an earlier fixed-year target, a later explicitly reported reduction, and another publication repeating that reduction. It also supplies a real negative case: matching relative-tenor columns does not establish matching calendar targets. These observations come from the publisher's own articles/PDFs, not summaries in another aggregator. [P1–P4]

We also recovered a current committed vault snapshot and found an arithmetic inconsistency in one displayed summary. Finally, we found conflicting website-level and report-level reuse language. These three findings determine how the first useful product should admit evidence.

What remains unproven: original PDF/body bytes within the Mastermind vault, their matching catalog identities, a simultaneous live four-set census, source-specific commercial permissions, an authenticated Brain/viewer journey, and automated extraction/model quality. Public originals do not substitute for those proofs.

The unchanged R3 reference was rerun: 53 tests passed. The new 12 qualification questions are **analyst-prepared expected answers**, not independently human-reviewed gold labels, model results, or additions to a 65-test product benchmark. No production code or R3 oracle behavior was changed.

## 2. The catalog is populated; its summaries are not source certification

The inspected committed catalog declares 2,204 records, generation `2026-09-16T04:24:32.098110+00:00`. This is a snapshot observation, not a live reconciliation of catalog, PDFs, searchable corpus and processing receipts. [I1]

The eight complete leading rows visible in the bounded response all had empty `tickers`, `tags` and `desk`, while `needs_metadata` was false. This is a purposive eight-row sample, not a whole-corpus failure rate. The masterplan explicitly describes the narrower metadata flag; it does not certify analytical completeness or numeric correctness. Do not redefine that existing flag silently. [I1–I2]

One `Daily Asia` summary, document `marketdesk-hlh6q8259ev-dcffbd`, displayed institution `UBS`, combines a new amount of **$1.2 trillion**, a baseline of **$90 billion**, and a **33% increase**. Taken as written, these cannot all describe that same growth relationship. Converting the new amount to billions gives 1,200; `(1200 / 90 - 1) × 100` is approximately **1,233.33%**, while `90 × 1.33` is **119.70 billion**. [I1; arithmetic reproduced in the local receipt]

This establishes an internal inconsistency in the published summary. It does not establish the correct original figure, identify the component that introduced the problem, or show that the original bank research is wrong. Changing 90 to 900 might look plausible; it would still be an invented repair without original evidence.

**Proposed treatment:** preserve the received text, flag the precise relationship as unresolved, and retrieve the underlying evidence when authorized. Do not generate a numerical revision card or derived portfolio assertion from that inconsistent relationship. Other supported information need not disappear. A failed analytical check is not permission to delete a source or rewrite its record.

**Product implication:** acquisition, source verification, entity linking and useful analysis are separate bottlenecks. More accounts do not automatically fix missing entity mappings or defective summaries. Conversely, a larger original-source corpus can help resolve questions the summaries cannot answer.

## 3. A real institutional sequence: change versus repeated change

The relevant observation is EUR/USD at **year-end 2026**, expressed as USD per EUR. This is a bank research forecast, not company management guidance, a market forward, an observed actual or a Mastermind signal.

| Original publication | Limited observation | Research interpretation |
|---|---|---|
| ING, 19 June 2026, FX Daily | An explicit year-end target of 1.18. | Independently located earlier source evidence for the old level. [P1] |
| ING, 3 September 2026, Yield curve dynamics | Explicitly changes the year-end 2026 target from 1.18 to 1.16. | Source-reported fixed-target revision; earlier level corroborated by another original. [P2] |
| ING, 7 September 2026, G10 FX Talking | Carries the same stated 1.18-to-1.16 year-end change. | Another publication of the inspected numerical change, not evidence of a second reduction. Other content may still be new. [P3] |

The arithmetic difference is -0.02 USD per EUR. That is a difference between stated targets, not a forecasted stock return, a return measured from spot, or evidence of investment skill.

The June source is **not established as the immediate predecessor** of the September revision. September 3 is the earliest revision located in this bounded search, not a proven first-ever announcement. We do not know that the target remained unchanged between the located documents. Current public renderings are not immutable captures from their historical publication dates.

This corrects an intermediate limitation of the investigation: the old figure no longer rests only on retrospective quotation in the later report. A separate earlier original has been located. It does **not** upgrade the result to an authenticated, byte-bound Mastermind-vault pair or a complete historical timeline.

### Consequence for the information graph and alerts

A publication identity and a change identity are different. One change can be discussed in several publications, formats or desks. Preserve both source records, link the shared numerical change where supported, and let the existing publication/alert owner decide whether there is genuinely new information worth delivering.

Do not deduplicate entire reports just because one forecast repeats. A later report may add a counterargument, change an assumption or discuss other instruments. Deduplicate supported claim/change relationships at the relevant granularity, while retaining permitted source evidence.

This is one concrete way to turn high collection volume into intelligence rather than notification volume.

## 4. The rolling-horizon trap and the forecast contract

The August 6 and September 7 ING tables both contain `3M` EUR/USD forecasts; the displayed values are 1.17 and 1.16 respectively. [P3–P4] The shared column label does not establish an identical calendar target. The precise anchor and end-date convention were not verified, so neither should be manufactured.

A **constant-tenor profile comparison** may be useful and can be labeled as such. It is not automatically a **fixed-calendar-target revision**. This distinction also applies to next-twelve-month earnings, rolling price targets and forecasts whose fiscal-year labels shift.

The existing R3 oracle supports issuer `guidance` and `actual` examples. It is not a generic analyst-forecast engine. Relabeling bank forecasts as issuer guidance to make an example pass would hide the missing contract. The R3 code remains unchanged; its refusal of an unsupported claim kind is retained as a boundary, not worked around.

### Additive contract to freeze with the existing Vault/Brain owners

| Concept | Required distinction |
|---|---|
| Claim kind | Analyst forecast, issuer guidance, reported actual, valuation output and market-implied forward remain separate. |
| Target | Fixed year/quarter/date versus relative tenor/next-twelve-month window; source convention and anchor remain explicit or unknown. |
| Measure | End-of-period point, period average, range, approximation and annual total are different quantities. |
| Earlier evidence | Prior value quoted by the later source; independently observed earlier value; verified immediate predecessor; and complete history are progressively different evidence claims. |
| Change | Numerical revision, repetition of a known revision, reaffirmation, changed assumption and source correction are different events. |
| Availability | Printed source date, system acquisition, extraction and product availability must not collapse into one timestamp. |

These are proposed domain fields/results under existing owners, not a new identity service, lifecycle, datastore or public tool schema. Exact field names and migrations must be accepted with incumbent interfaces before runtime work.

## 5. Visual semantics need evidence too

The original forecast table uses directional arrows, while a neighboring graph labels publisher forecasts separately from market forwards. [P3–P4] An arrow is not automatically a revision from a prior report. Its meaning must come from a source legend or attested convention. Until then, preserve the glyph as a glyph and keep the inferred meaning unknown.

A graph line representing market forwards is not another independent institutional forecast. The system must preserve the legend, source role and units before using either line. This chunk did not extract exact numerical values from chart pixels.

For the product, that means a source-inspection link is necessary but insufficient: the evidence object also needs the table header, target period, units, series role and relevant footnote. A correct page number can still point to a misunderstood figure.

## 6. Rights diligence found an actual conflict

ING's website terms conditionally allow reuse of website material expressly identified as ING-owned, with attribution, and exclude third-party material without applicable permission. [P5] The September report's own disclaimer, printed page 14, separately requires prior express consent for reproduction, distribution or publication. [P3]

This document does not decide which clause legally controls. It records an unresolved source-specific conflict requiring qualified or rightsholder clarification. No conclusion that Mastermind has infringed a right is made. No commercial permission is inferred from public accessibility, a general website clause, a subscription, or a Pro entitlement.

A procurement inquiry therefore needs to reference the exact source and intended uses, not ask vaguely whether AI is permitted. Seek clarification for automated storage/processing, internal retrieval, generated customer analysis, original-report access, third-party charts, retention and withdrawal. Keep text, charts, photographs, forecasts and embedded external datasets distinct where their rights differ.

No ING reports or screenshots are republished in this package. It contains our analysis, a few numerical observations, locators and links. No source-specific commercial grant, account expansion, vendor contact or customer publication was performed.

## 7. The revised first vertical: a useful answer with an explicit evidence level

The first user job remains: **understand what changed and inspect why**. The product should not wait for a giant graph, nor should it pretend that every citation is equally verified.

The existing Brain/Vault path should be able to give a bounded answer such as:

> The source reports a reduction for the same target period. An earlier original supports the old level. The immediate prior report and complete change history are not established. This later publication repeats the same numerical change; it may contain other new analysis.

That is useful without claiming more than the evidence supports. Customer use still requires the appropriate source grant and actual product entitlement.

### Implementation order after source and interface admission

1. **Original-source binding:** existing catalog ID and admitted source version, actual PDF/body hashes, extraction coverage and locators at a recorded generation. A hash must be measured from bytes, never filled from a filename or synthetic fixture. Reuse the existing census; do not force its four sets equal or call exit 0 a clean verdict.
2. **Comparable claim representation:** preserve type, entity, metric, units, basis, scenario and target convention. If needed, expose a source-reported revision before independently reconstructing its predecessor; label that limitation.
3. **One real consumer:** existing Brain response opens the same evidence in the existing viewer. Then place the explanation in the existing Prophet research surface without changing signal artifacts. No separate chatbot, viewer or score service.
4. **Correction and repetition proof:** repair one source/extraction change through the existing owner; only dependent outputs change. A repeated numerical revision must not cause another identical alert, while unrelated new information remains retrievable.

Required negative cases: different or unresolved targets, wrong claim kind, arithmetic mismatch, earlier-source gap, duplicated change, ambiguous arrow/series, corrupted source identity, stale version, missing permission, quota denial and private-context isolation. EN/ZH display and actual browser inspection are production acceptance, not inferred from source links.

## 8. What this means for additional subscriptions

The thesis remains worthwhile: original research can support several useful products. The new evidence favors **selective depth before indiscriminate multiplication**, not abandoning broader coverage.

An extra account may add missing continuity, genuinely distinct evidence or faster access. It may also add another digest repeating a known change. The acquisition-value experiment should track those contributions separately. A missing original that resolves an important ambiguity can be more valuable than several generic summaries.

Three total accounts remains a capacity hypothesis, not a purchase decision. Four accounts on the same source do not remove provider or rights concentration. Ask whether a provider-approved commercial/bulk arrangement better matches the intended use, but do not contact or buy under this research record.

The next meaningful purchasing evidence is whether the expanded *permitted original corpus*, after the same quality checks, answers more important questions or resolves them sooner than the existing corpus. Raw acquired-note count, raw institutional labels and summary volume are not sufficient.

## 9. Verification, scope and exact remaining gate

`source_qualification_r4.json` preserves four publisher-original document references, five small normalized observations, the catalog arithmetic case, source-specific rights conflict, 12 prepared questions and proposed contract additions. It stores no full report, source-byte digest, fabricated vault identity or historical acquisition timestamp.

The unchanged R3 reference was rerun locally; its receipt and source digest are recorded in `verification_r4.json`. This is regression on the earlier control/fixture suite, not automated ING extraction or new customer functionality. The 12 cases are prepared expected answers; independent grading and the larger 120-task evaluation are still outstanding.

**Access boundaries:** Opera reported no connected browser. The previous blocked M1 command was not retried. Original PDF downloads into the sandbox failed, so full byte identities remain unknown. Public source inspection is not a substitute for current private vault access. A failed title search does not establish absence from the vault.

**Exact next gate:** the existing Vault/Brain source owner needs to admit a bounded original pair through an approved read-only path, with existing IDs, source/body hashes and locators, plus the appropriate source-use decision. After that, exercise the existing Brain/viewer journey with the actual pair and the new target/repetition cases. No new credentials should be pasted into chat and no blocked command should be retried through another actor or carrier.

All production/runtime changes remain held. This chunk resolves source-semantic uncertainties and strengthens the first vertical; it does not close the entire program or transfer the incumbent #7079/#7045 work.

## Source register

I1. Committed catalog snapshot, immutable repository pin: https://github.com/mastermindx-market-intelligence/macro/blob/112eba2036fd1186e67b914e194f4fa541cfc4df/data/research_vault/catalog.json

I2. Existing metadata contract and census ownership: https://github.com/mastermindx-market-intelligence/macro/blob/112eba2036fd1186e67b914e194f4fa541cfc4df/research/RESEARCH_VAULT_MASTERPLAN.md ; https://github.com/mastermindx-market-intelligence/macro/blob/112eba2036fd1186e67b914e194f4fa541cfc4df/scripts/research_vault_census.py

P1. ING, 19 June 2026, FX Daily. Original PDF printed page 2, EUR section; date printed in the PDF. HTML/PDF text read; requested screenshot failed. https://think.ing.com/articles/fx-daily-us-holiday-offers-japan-intervention-window/ ; https://think.ing.com/downloads/pdf/article/fx-daily-us-holiday-offers-japan-intervention-window

P2. ING, 3 September 2026, Yield curve dynamics drive the dollar. Original PDF printed page 1; visually inspected. https://think.ing.com/articles/fx-monthly-yield-curve-dynamics-drive-the-dollar/ ; https://think.ing.com/downloads/pdf/article/fx-monthly-yield-curve-dynamics-drive-the-dollar

P3. ING, 7 September 2026, G10 FX Talking. Original PDF pages 1–2 visually inspected; disclaimer text on page 14. https://think.ing.com/articles/g10-fx-talking-september-2026/ ; https://think.ing.com/downloads/pdf/article/g10-fx-talking-september-2026

P4. ING, 6 August 2026, G10 FX Talking. Original PDF pages 1–2 visually inspected. https://think.ing.com/articles/g10-fx-talking-august-2026/ ; https://think.ing.com/downloads/pdf/article/g10-fx-talking-august-2026

P5. ING THINK Terms of use, use-of-content and third-party-content clauses. https://think.ing.com/about/terms-of-use/

These are current inspected renditions of dated sources, not immutable historical captures. Forecast statements are attributed to the source, not adopted as investment advice. All proposed architecture, product behavior and purchasing rules are recommendations; actual verification is bounded as stated.
