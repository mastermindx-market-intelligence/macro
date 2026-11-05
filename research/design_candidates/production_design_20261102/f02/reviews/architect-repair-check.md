# F02 Candidate 2 — Principal architect source repair check

**Disposition:** source repair check complete within the scope below; **not implementation accepted, not an independent critic pass, not RIG approval and not runtime/path proof**.

**Role:** bounded principal architect consultation. I authored `SOURCE_AND_DATA_CONTRACT.md`, read the original Product Regression Critic first-pass findings and rationale response, then reviewed the repaired source. This review is author-informed and must not be represented as the quarantined independent review required by the assignment.

**Final checked source time:** 2026-11-03 02:27:48.983 UTC. The author repaired issues during this consultation; the hashes below identify the final bytes this report covers.

| Input | SHA-256 |
| --- | --- |
| `pattern-lab.html` | `254be643794b4dff7d517c72ebeeda8b6a40cd93bde85aa4cae982b30e165c1b` |
| `evidence/check_reference_model.cjs` | `501668e81b76860e2f03818b9a8c2248f65104308fd796a8704622c25fa477f8` |
| `fixtures/company-history.json` | `75a50198c9adfe8f2592aba2d87addd01b17b9c812ef7a4e78d17da567ec7df6` |

The production source pins remain Macro `b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e`, Terminal `b79b1e136290978ff7675087de979bb1b42b3713`, assignment `6e1862867193ec6486a22001a0e4fb515da20448` and procedure `c57adacb338fe837c7d585f1e372c64d9b0118ec`. This review fetched no new production source and makes no new current-deployment claim.

## 1. Scope and actual checks

I read the repaired HTML/CSS/JavaScript, the Company fixture, the model checker and the original PRC findings relevant to state, evidence, chart geometry, focus, language and consumer preservation. I did not open a browser, instantiate a DOM, dispatch browser events, inspect pixels/fonts, execute account/service calls, mutate Paper or change `pattern-lab.html`.

I executed the author's checker unchanged with its intended JSON output write intercepted in memory. No candidate or existing evidence report was overwritten. That run reported **480 state combinations, 3,360 read-invariance transitions and 59 evidence records**, with `PASS_WITH_SCOPE_LIMITS`. This establishes only the extracted pure functions, fixture values, identity construction and generated SVG text that the checker actually exercises. It does not execute `render`, browser event bindings, native dialog behavior, layout, focus, scroll or services.

Additional read-only probes addressed concrete remaining risks:

| Check performed | Result | Boundary |
| --- | --- | --- |
| Embedded Company JSON versus `fixtures/company-history.json` | Deep-equal | The checker otherwise constructs its model from the external file, while the browser specimen reads the embedded JSON. This closes the inspected-input mismatch risk for the recorded bytes. |
| Company chart shape | 17 fiscal years, 2010–2026; five series; 85 numeric plotted values | Illustrative annual data only. |
| Company series versus comparison periods | Each of the five series' FY 2022–2026 values equals the corresponding five displayed statement inputs | Does not qualify a real statement producer or precision policy. |
| Company displayed arithmetic | Six displayed percentage-growth values agree after one-decimal rounding; five operating-margin values agree with operating income / revenue | Arithmetic only; not investment/model validation. |
| Four consumer overview mappings | Macro, Company, Options and editorial resolve to their own consumer/entity/metric identities; unsupported overview consumer rejects | Pure evidence construction; not a clicked inspector path. |
| Observation admission | **1,920** consumer/state decisions checked; **720 admitted**, matching the explicit local rule | Three analytical consumers admit member/guest with loaded/retained-error availability; editorial static content is exempt. This is not production authorization. |
| Event boundary/source action wiring | Source action and specimen primary action use admitted overview or coverage keys; `openEvidence` rejects noncoverage requests when observations are inadmissible | Source inspection of the guard and strings; no event dispatch. |
| Options trade classification | Four Buy-classified rows; summary derives the count from `side === 'Buy'`; no near-ask assertion remains | Actual NBBO/quote-location inference stays with D08. |
| Sort announcement | Separate descending-sort and original-order-restored messages are present | No live-region/assistive-technology execution. |
| Language metadata | English article main, English harness and English skip link are explicitly marked; translated component specimens have their own selected-language attribute | No CJK font or screen-reader pronunciation proof. |
| Source stability during final probe | HTML hash unchanged before/after checks | Later edits require an affected-scope refresh and new artifact digest. |

The earlier arithmetic probe ran against HTML `63a64861e226b25006d7faac3762c06b10b352f758e1811d9d2484fa6bf71b89`; the Company fixture hash and inline equality were rechecked in the final probe. The subsequent source repairs affected admission, wording and language annotations, not those fixture values.

## 2. Defects found during this consultation and author repairs

These are concrete source findings I sent to the author. The author owned every HTML repair. The original independent reports remain unchanged.

| ID | Finding in the evolving repair | Observed final correction | Disposition |
| --- | --- | --- | --- |
| ARC-01 | Editorial component specimen emitted `overview:editorial`, but the overview branch defaulted non-Macro/non-Company consumers to Options chart evidence. | Explicit overview map includes editorial → `article`; unsupported consumers throw. Four-consumer mapping is checked. | Corrected in the recorded source; runtime untested. |
| ARC-02 | Source details and component overview actions exposed loaded fixture values while loading/unsupported/denied/expired masks hid the analytical content. | `canInspectObservations` admits only the specified analytical read/access states; both action sites route otherwise to coverage; `openEvidence` independently guards all noncoverage keys. | Corrected as a local observation-admission rule; no real access-control claim. |
| ARC-03 | “Classified near ask” was asserted from rows that had estimated Buy/Sell/Mixed side but no quote-location/NBBO field. | Wording is “Estimated buy side” and its count derives from the side field. | Corrected source semantics. |
| ARC-04 | Toggling sort off announced numeric sorting/unknowns-last while restoring original order, where Macro's unknown Energy row precedes valid rows. | Original-order restoration has its own announcement. | Corrected source message. |
| ARC-05 | English-only harness labels and skip-link text inherited `zh-Hans` after changing the document language. | Explicit `lang="en"` on harness and skip link. Article already had its English override. | Corrected metadata in source; AT behavior untested. |

I did not find another blocker in the specific repaired functions and branches checked after these corrections. That is not a completeness claim for the application or the consumer tasks below.

## 3. Assessment against the original PRC findings

| Original finding | Source repair assessment | What remains open |
| --- | --- | --- |
| PRC-001: saving changes read truth | `availability`, `freshness`, `coverage`, `access` and `write` are separate. Write transitions leave the read snapshot unchanged; pending access loss becomes uncertain. Combined stale/partial warnings survive pending and saved. Observation admission is separately guarded. | Full event/render sequence, actual service/readback and uncertainty reconciliation. Model coverage is not 3,360 browser transitions. |
| PRC-002: evidence identity | Evidence identity now contains consumer/entity/field/period meaning. Company record includes EXM; chart evidence contains all five series for its fiscal year; overview aliases intentionally point to the same observation. | Real producer identity and citation precision at consumer integration; actual row-to-inspector path. |
| PRC-003: expiry substituted for observation | Options chart evidence records the observation window separately from expiry and contributor IDs. The two buckets retain their five/seven contributing print identities. | Real source clock/cohort/coverage receipt. The common fixture observation window is not evidence of continuous session coverage. |
| PRC-004: focus return after rerender | `closeEvidence` can resolve a visible current trigger by evidence key when the old element is detached; comparison update preserves its scroll offsets and selected key. This addresses the original detached-node-only fallback. | The focus/scroll visibility risk in section 4, modal/docked transition behavior, Escape and keyboard/touch execution. |
| PRC-005: unreadable scaled mobile labels | Macro/Options SVG width and viewBox are generated from measured container width. Company retains minimum 840px geometry inside a scoped scroll region, preserving source text size instead of shrinking 17 groups. | Actual pixel/text measurement, width/zoom/CJK/forced-color rendering and overflow behavior. |
| PRC-006: English article mislabelled | Article main uses `lang="en"`; bilingual component specimens override appropriately; English harness and skip labels are explicitly marked. No translated body or `/zh/` route is claimed. | Effective language/reading-order/AT check on an actual served page. |
| PRC-008: dividend delta unit | Comparison/evidence use `0.00 USD/share` and disclose undefined percentage growth from a zero base. | Real field/currency/absence mapping. |
| PRC-009: Options task priority | `analytical` puts the Options comparison/filter region before its aggregate chart and uses the compact summary treatment. | Same-viewport rendered task-priority review and real view/filter integration. Source ordering alone cannot prove the final visual result. |
| PRC-007: consumer preservation | Company fixture now adds 17 fiscal years, five income series and five displayed statement periods. This is a meaningful specimen repair. | **OPEN consumer integration gap.** It does not establish annual/quarterly switching, all statement families, transcript/history paths, Options saved/share/export/filter workflows, Macro linked desks, access recovery or the existing virtualized chart engine. |

## 4. Remaining source/integration risks

### Focus restoration may target an offscreen element

The current source restores the pre-open table scroll offsets and calls `trigger.focus({preventScroll:true})`. After sorting/filtering, a retained identity may occupy a different position; the stored offset need not make that position visible. `getClientRects().length` establishes that an element has layout boxes, not that those boxes are inside the visible scrollport or viewport. Page scroll is not captured by the current table snapshot. This is an identifiable source-level risk, **not an observed browser failure**.

Before interaction acceptance, exercise a retained row that moves out of the prior visible range, then close evidence. Pass only if focus lands on that row's current evidence action and the action is visibly reachable. If the row is removed, pass only if the deliberate fallback is visible and announces the loss of context. Include horizontal scroll and dock-to-overlay changes. The builder may preserve scroll when it keeps the target visible, otherwise reveal the target deliberately; it must not claim both behavior and proof from the current source alone.

### Fixture controls are not consumer/service integration

The local access, save and retry controls demonstrate states. They do not call actual authentication, plan, saved-screen, export, share or data services. The source is candid about simulated saves and no account write. Maintain that disclosure. “Check save status” is a local fixture transition, not a reconciled readback receipt. A fixed Options cohort and an ordinary comparison table do not replace the existing observed-statistics producer or DataInspector.

### Rendered consistency is unqualified

The pure-model checker does not assess the static sheets against repaired source, CJK glyphs, effective contrast in rendered contexts, focus visibility, native-dialog behavior, touch, 400% zoom, reduced motion, forced colors or actual table/chart overflow. The root must bind regenerated sheets/captures and all corrected source to the final immutable manifest before delta review. An earlier image or hash must not silently accompany the repaired HTML.

## 5. Closed-form implementation acceptance for PRC-007

The gap is closed only when **all applicable conditions below are satisfied by the existing consumer owners at the same implementation revision**. An explicit owner disposition is required for a nonapplicable case. These are finite acceptance witnesses, not a request to rebuild domains inside the specimen.

| Owner | Required conjunctive witness |
| --- | --- |
| D02/D03 Macro | Actual field/universe/unit/clock/null/access mapping for one chosen metric/table/chart **and** a composed regime/risk/calendar/linked-desk path **and** regression proof for the sibling US-stock region of the shared template. |
| D07 Company | One actual entity through annual/quarterly, all three statement families, earlier-period/definition and evidence/transcript paths **and** missing/zero/non-comparable/currency mappings **and** a second entity switch with correct parser, route/return context and no stale relabeling. |
| D08 Options | Real print/contract identity and side/exposure/expiry/observation meaning **and** current tabs plus premium/DTE/moneyness/symbol filter paths **and** existing saved-screen/share/export scope/precision **and** producer/served coverage/stale receipt **and** denied/service-unavailable distinctions. |
| Existing chart/DataInspector owner | Existing grid row-time identity through sort/prepend/filter/replay **and** mounted active descendant/count/index **and** actual keyboard/selection behavior **and** CSV/replay scope and row-limit refusal. Reuse the current engine. |
| Public editorial owner | Actual emitted page from the current builder/templates **and** original canonical/hash/TOC/body/date/related/CTA preservation **and** English content/bilingual chrome language proof **and** a narrow reading/calculation/table/source path. |
| Domain lifecycle/count owners | Actual labels and partition meaning **and** one meaningful transition/return condition **and** retained authority/source provenance; generic accepted status is insufficient. |
| D23/current mutation owner | Actual callback/endpoint and immutable owner/object identity **and** failure-versus-uncertain/reconciliation policy **and** confirmed readback **and** valid sign-in/plan/session return paths retaining context. No navigation/theme/language mutation. |

P00 writer qualification, editable Paper objects/readback, the joint F01/F02 freeze, source-to-reference binding, admitted independent review, authority decision and served-production proof remain separately required. This principal source check closes none of them.

## 6. Documents changed by this reviewer

- Added this report, `reviews/architect-repair-check.md`.
- Appended section 11 to `SOURCE_AND_DATA_CONTRACT.md`: exact 17-year/five-series/five-period fixture scope, independent state/admission boundary and the finite PRC-007 integration criteria.

No HTML, fixture, checker, existing report, production code or Paper object was changed by this reviewer. The original source pins and prior independent findings remain preserved.
