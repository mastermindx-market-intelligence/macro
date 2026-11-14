# Research Vault — Chunk 5: executable analyst-change contract

**Date:** September 16, 2026. **Overall customer capability:** SPEC_ONLY. **Research capability:** executable offline reference plus a deterministic answer preview. No original-source admission, automated extraction, model evaluation, production deployment, or account purchase is claimed.

Existing carrier: draft Macro PR #7182 / `sol/research-vault-intelligence-design-r2-20260915`. Starting head: `7324a70897e32ea4d60727d8e6c47f3a8e3b72b7`. Protected procedure: `Mastermind@0fe8074ff953b2ced9025ed40f0f66019c759967`, Skillpack 1.0.1/bootstrap 1; INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT loaded from that pin. Macro main inspected: `bb02c526c4809564338f2a7208e063dbe86bc476`. Direct work: PRINCIPAL_JUDGMENT for evidence and target semantics; LOWER_TOTAL_OVERHEAD for the bounded offline implementation. No Executive Job, worker assignment, registered workstream, or watcher created.

## 1. The substantive decision: useful answers do not all require a complete history

Earlier chunks placed a two-original-report comparison at the front of the product sequence. That remains necessary for an independently reconstructed revision, but it is too broad as the prerequisite for every useful answer.

A single admitted original report can support an attributed statement: “The institution says it changed its forecast from X to Y.” This does not establish that we independently hold the preceding report, know the immediate predecessor, or reconstructed the first announcement date. Those are separate evidence claims.

The proposed product should distinguish:

| Evidence task | Required source support | Honest output |
|---|---|---|
| Read one source | One permitted, source-bound report | The source states X for target T. |
| Describe a source-reported revision | One permitted, source-bound report explicitly stating old/new comparable values | The source reports changing X to Y. The old value is quoted within this report. |
| Reconstruct a change independently | Separately admitted earlier/later originals, matched metric, scope, period and basis | The captured original statements differ by D. |
| Establish complete chronology | Sufficient history and availability evidence | Immediate predecessor/first appearance only where actually supported. |

This is a refinement of the proposed implementation sequence, not a relaxation of the original-source, entitlement, licensing, correction or trading-authority boundaries. Provider summaries alone are not promoted into original evidence. The offline fixture does not satisfy any production admission requirement.

The first user-facing proof can therefore start with one current admitted report through the existing Brain/viewer. Paired-original comparison can deepen it rather than block every preliminary source-grounded answer. The portfolio and Prophet vision is preserved; a useful answer should not depend on completing an enormous archive first.

## 2. What was actually built and exercised

The existing research reference was extended rather than replaced. Its original issuer-guidance/actual behavior remains covered by the prior 53 tests. A new manually normalized five-observation analyst fixture and 58 additional tests exercise explicitly typed bank forecasts. The same comparator feeds a bounded JSON result packet and a deterministic Markdown answer preview.

The path is:

`manual research fixture -> existing offline comparator -> whitelisted case packet -> deterministic answer preview`

This is an executable producer/consumer demonstration within research, not the deployed Brain, an LLM-generated answer, a source parser or a new retrieval API. The fixture-specific preview is not a general answer renderer. It does not ingest PDFs, access accounts, publish content or send notifications.

The output keeps source-attributed changes separate from independently compared manual values, marks unresolved target conventions, and explicitly states that original PDF/body hashes, vault matching and customer access are not proved. It provides original publisher URLs, not counterfeit vault IDs or constructed source hashes. Local `allowed_for_assay` and `review_state` fields are test labels, not upstream licenses, authenticated entitlements or provenance attestations.

## 3. Real case behavior

The small institutional case remains ING's EUR/USD publications, documented in the preceding source-qualification record:

- June 19: earlier year-end 2026 level of 1.18.
- September 3: source explicitly reports the year-end change from 1.18 to 1.16.
- September 7: source repeats those same old/new endpoints.
- August and September tables: three-month figures of 1.17 and 1.16 respectively, with unresolved calendar anchors in this manual fixture.

June 19 and September 3 source text were revisited in this chunk; September 7 HTML and the first PDF page were revisited. The August observation is carried from the prior qualification, not newly reverified. The public numerical statements are not original PDF-byte bindings or a complete chronology. No full documents or screenshots are republished here. Sources are listed below.

The generated case produces five distinct results:

| Request | Offline result | Interpretation limit |
|---|---|---|
| What change does the later source report? | `source_reported_revision`, delta -0.02 USD/EUR | Earlier value quoted in current source; no fabricated prior document. |
| Compare separately captured manual year-end observations | `revision`, delta -0.02, approximately -1.69% for display | Captured original statements were manually read, but PDF identity, immediate predecessor and complete history remain unproved. |
| Compare September 3 and September 7 claims | `repeated_reported_revision`, delta 0 | Same quoted endpoints in the inspected statements; no claim of zero new information in the whole report or no intervening uncaptured change. |
| Compare August/September 3M as a fixed-date revision | `not_comparable: unresolved_relative_target` | Same tenor label does not establish the same calendar target. |
| Explicitly compare the two 3M outlook profiles | `constant_horizon_profile_change`, delta -0.01 | A profile comparison, not a fixed-target revision. |

The numbers are comparison outputs at the source's stated precision, not current exchange-rate quotes, calibrated forecasts, recommendations or performance evidence. Unknown fixing conventions are disclosed. A match on a publisher-named year-end target is not proof of a specific market fixing.

## 4. Contract behavior now covered

Analyst forecasts are no longer mislabeled as issuer guidance to fit an older interface. They require a forecast-source role, explicitly typed target and bounded valid numeric representation. A market forward cannot pass as a publisher forecast. Reported actuals remain a separate class.

A fixed year-end target and a relative tenor use different representations. There is no automatic “add three months” transform. Explicitly resolved target dates need an explicit source-resolution basis and cannot precede the publication or their supplied anchor. Conflicting legacy period fields and typed targets are rejected rather than silently choosing whichever fits the desired comparison.

Same current values with different quoted prior values are not the same reported revision. A newly captured source assertion is not automatically a newly occurring market event. Matching repeated endpoints do not establish a complete intervening history. Whole-report novelty is not inferred from a single metric.

Shared numerical arithmetic uses sufficient decimal precision for the bounded supported inputs; the test suite includes large exact numbers whose difference is one. Range differences are arithmetic bounds, not probability intervals. Identical ranges remain unchanged rather than generating a spurious negative-to-positive interval.

The existing historical-selection probe deliberately does not admit analyst series into operational point-in-time processing. Unknown real availability stays unknown; even synthetic known analyst timestamps do not make this offline extension a Market Memory adapter.

The answer packet projects only explicit fields. Caller body text is not copied into it. Denied cases carry no source projections or numerical preview. URL validation is a narrow fixture-specific structural check, not a general browser or authorization mechanism.

## 5. Actual test evidence

Final matched-source local run: `2026-09-16T05:26:54.008915+00:00`, Python 3.13.5, **111 tests, zero failures/errors/skips**: 53 prior cases plus 58 new cases. Commands:

```sh
cd research/research_vault_expectations_r3
python run_analyst_assay.py --out /tmp/rv-r5-proof
```

Use a fresh output directory. The reference generates the receipt, test log, JSON case packet and preview. These local outputs are not committed by the runner.

Tests-first observations: 93 cases initially produced 36 assertion failures. The first implementation passed 93. A further adversarial set produced 11 failures across 108 cases, and three additional target-conflict checks produced three failures across 111 cases. The final run above passes. These numbers describe development iterations, not independent out-of-sample research-answer accuracy.

Six targeted local mutations were also tested and all six were rejected by the selected assertion: removing relative-target refusal; removing repeated-change classification; admitting forwards as forecasts; inventing original-pair proof; ignoring conflicting target representations; and granting trading authority. The mutation recipe and receipt are in the companion package. This was direct local challenge, not an independent external reviewer or an additional six passing production tests.

Four new/changed reference files were compared by Git blob identity against `87bac51b44378cf033683bd85b2e53e9e3e81b52`: comparator `57b6a630a32938fd64791c362244bc06b9f84e28`, analyst tests `37c057f0ccbf499f00f0eeda9d659d4ec8716e48`, analyst fixture `e309fb02b18ee7da8f35d0cf0a1f195ea9482415`, runner `6a1490cd87d0a435f17988bc3532798d284a5e95`. Local bytes match those repository identities. Retained receipt records SHA-256 for the exact test inputs/code. Earlier R3/R4 verification files remain historical receipts for their respective code revisions.

Still zero: authenticated customer journeys, actual vault-original pairs bound, automated extraction evaluation, new LLM answer evaluations and independent human labeling in this chunk. The broader 120-task benchmark remains unexecuted.

## 6. Integration and acquisition consequences

The contract gives the existing Brain three useful response modes before any universal graph is needed: source-attributed reading, source-reported change, and independently reconstructed comparison. These are evidence distinctions, not a new tool registry, entitlement tier or lifecycle.

A candidate first production slice is one selected entitled report with a source-reported numerical change, precise locator, relevant period/unit and an existing-viewer link. It should disclose the old value's evidence origin. If the old original is later admitted, the same response can gain an independent comparison without rewriting the earlier answer as if that evidence always existed.

The next Prophet slice adds the business interpretation and genuine source-backed counterevidence to the existing company journey. No research-derived score, ranking, sizing or trading decision is introduced. The existing portfolio owner can compose the same evidence privately. Existing news/alert and press owners retain notification and publication authority; comparator output never authorizes a notification by itself.

Account expansion should consequently be evaluated against the specific evidence gap. A current report may unlock an attributed answer; its predecessor may unlock a reconstructed change; an independent report may unlock supported disagreement. These increments have different user value. A raw document count cannot distinguish them.

This does not establish a new subscription ROI result or change the proposal of three total accounts as a hypothesis. No prices, allowed pooled usage, commercial rights, source retention, marginal customer benefit or capacity need were newly established.

## 7. Current dependencies and blocked lane

Fresh #7079 read showed candidate head `8271ae320732997be4553957e3e2773d1b9e9f1b`, a history-preserving R10 CI-ownership repair. It remains draft, unmerged and BUILT_NOT_PROVEN. Its recorded release requires current hosted checks, release adjudication and real deployed-consumer proof. It still does not implement viewer fragment positioning or multi-document synthesis. No source paths owned by that PR were changed here. #7045's source-type/rating repair remains an incumbent dependency; no new release claim is made.

The large current catalog request was rejected as too large/unsupported. No fresh catalog count or clean census is asserted. Original-source acquisition/binding and browser access remain unresolved. The previously OpenAI-blocked M1 command was not retried or routed through another actor. Public-source reading does not establish commercial processing or redistribution permission.

Only research reference/files and continuity on draft #7182 changed. No app, engine, site, template, configuration, workflow, private source store, customer publication, account or production process changed. No automatic merge is requested.

## 8. Exact continuation

First, the existing Vault/Brain source owner qualifies **one permitted current report** at a recorded publication generation, with canonical catalog ID, actual source/body identity, locator and a source-use decision. The original two-report requirement remains for independently reconstructed change, not for an accurately attributed single-source statement.

Then, after the incumbent evidence work's own release gates clear, prove one source-reported change through the real Brain/viewer, including the actual access/quota behavior and a mismatched target refusal. Preserve source-version drift and correction handling. Only that source-bound real journey is product proof. A staged stock-facing explanation must leave Prophet signal artifacts unchanged.

Parallel work is the actual source-rights clarification and evaluation-labeling plan already recorded; another generic feature brainstorm or re-running unchanged tests is not the next dependency. The primary unresolved gate is not a missing arithmetic function. It is admitted source evidence through the existing consumer.

## Source register

- Prior R4 source qualification: `source_qualification_r4.json` and `CHUNK4_SOURCE_QUALIFICATION.md` at the starting head.
- June original: https://think.ing.com/articles/fx-daily-us-holiday-offers-japan-intervention-window/
- September 3 original: https://think.ing.com/articles/fx-monthly-yield-curve-dynamics-drive-the-dollar/
- September 7 original: https://think.ing.com/articles/g10-fx-talking-september-2026/
- September 7 PDF, page 1 visually revisited: https://think.ing.com/downloads/pdf/article/g10-fx-talking-september-2026
- August original, prior-chunk manual qualification: https://think.ing.com/articles/g10-fx-talking-august-2026/
- Existing Brain candidate/current metadata inspected: https://github.com/mastermindx-market-intelligence/macro/pull/7079

These links attribute the small source observations; they are not permissions, stored-byte hashes, complete chronology, live market measurements or proof that the source exists in the Mastermind vault.
