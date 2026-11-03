# F02 Product Regression Critic — rationale pass

**Original-set verdict after rationale: BLOCK.**  
**Disposition:** 8 findings upheld; 1 finding amended in scope; 0 withdrawn.  
**Rationale-pass freeze time:** 2026-11-03 02:20:55 UTC

This is a separate advisory rationale review. It is not an admitted Opus RIG receipt, a design-authority verdict, or approval of a repaired candidate. The first-pass report is preserved unchanged.

## 1. Review identities and permitted inputs

### Frozen first pass

- First-pass report: /workspace/scratch/55964f568673/f02/reviews/product-first-pass.md.
- First-pass freeze: **2026-11-03 02:08:11 UTC**.
- First-pass SHA256, rechecked unchanged: **dc49d84c50d250a0616079372d5e3f5508edc66acc9c634f1a5b53a8ed62051b**.
- Original artifact-set SHA256: **2823e06343b79f47474657310a9301f22e25b8051e0cd168db60150d6ece97a0**.
- Original artifact commit supplied by the coordinator: **6ee221069deba909b0f1eceee53869d4f4569ac9**.
- Original artifact copy: /workspace/scratch/55964f568673/f02-review-freeze-1/.
- All **32 original frozen members** were rechecked against the original manifest and still matched their recorded sizes and individual hashes.

All references to original HTML behavior or static compositions below refer to that frozen set and the unchanged first-pass findings. I did not inspect the evolving replacement HTML or sheets.

### Author rationale read after reveal

These are the seven authorized rationale inputs, under /workspace/scratch/55964f568673/f02/. Their hashes remained unchanged between reading and the final pre-write check.

| Rationale document | SHA256 |
| --- | --- |
| SYSTEM_CONTRACT.md | 2f7e84c49029f5527a831c2dd77987d3eb54c1bad249ffa41d76fc2b21eddc17 |
| SOURCE_AND_DATA_CONTRACT.md | f75ba53a8489e579bee585dd48fefc08ba507def21ee1a4a4a3c355400ea083a |
| INTERACTION_STATES.md | 8c254cb43779778e52e25ddcbfed214b2307b657aac2ca80ed8d157a1f36cb21 |
| VERIFICATION.md | a062c9845101fa79ca42e2184cfff729e6c00621bb5fb71834c8a57758051b87 |
| CONTINUITY_AND_GATES.md | 4f1472f10783cdd8696f9c5bed55027b4cd864da08fc6d724a83d80aed657d44 |
| README.md | b7c09d7cf8744760654334bdbe0891a4b187f49bd3caa4288809a05ecaf62343 |
| PAPER_BUILD_PLAN.md | 7e6be991fea4c27357375cf96d5715be856c0f5a85147b1d900b3dde2f29d1c2 |

I read no peer critique, linked capability/Paper ledgers, upstream repository source, or other newly revealed material. Links and source observations inside these documents were considered author-supplied rationale; I did not independently requalify the upstream implementations or their deployment. No browser or renderer was used and no candidate artifact was modified.

## 2. What the rationale changes

The author explicitly describes a partial design/specification candidate, supporting static compositions, and a local interaction specimen. It does not claim a frozen foundation, an installed component package, editable Paper completion, runtime qualification, real save readback, or production release. SYSTEM_CONTRACT sections 1 and 7, README's status, and VERIFICATION's claims boundary are consistent on this point.

That matters for **PRC-007**: the specimen is not required to recreate every Company, Options, Macro, or focused-chart feature internally. Existing owners and source paths may provide the preservation evidence. The unresolved issue is whether later consumption of the shared pattern preserves those capabilities, not whether a fixture contains an entire production application.

The rationale does not excuse the source defects. It explicitly requires the behavior those defects violate:

- Independent availability, coverage, freshness, transport, access, and mutation axes.
- Stable entity/field/observation identity with source namespaces.
- Separate observation, publication, retrieval, session, and instrument attributes.
- Return to the same row when the row remains present.
- Readable narrow layouts rather than scaled desktop geometry.
- English long-form editorial content with bilingual chrome.
- Explicit units for each comparison measure.

The Paper writer and preview constraints explain why certain evidence is absent. They neither demonstrate that the code works nor turn contradictory source logic into a valid shared behavior model.

## 3. Finding-by-finding disposition

| Original finding | Disposition after rationale | Severity / classification |
| --- | --- | --- |
| PRC-001 — Saving changes read-state truth | **UPHELD** | Blocker; original source logic |
| PRC-002 — Evidence is not consistently self-identifying | **UPHELD** | Major; original identity contract violation |
| PRC-003 — Options expiry substitutes for observation time | **UPHELD** | Major; original temporal semantics |
| PRC-004 — Sort breaks return to retained evidence row | **UPHELD** | Major; original return-context logic |
| PRC-005 — HTML mobile chart text scales below readable size | **UPHELD** | Major; source-derived defect, runtime outcome still unverified |
| PRC-006 — Chinese selection mislabels English editorial content | **UPHELD** | Major; original language metadata |
| PRC-007 — Depicted capabilities are not demonstrated | **AMENDED** | Major adoption/integration qualification gap; not a requirement to rebuild all domain features in the fixture |
| PRC-008 — Dividend change loses its explicit unit | **UPHELD** | Minor; original unit omission |
| PRC-009 — Options tape loses task priority | **UPHELD** | Major composition concern; no measured elapsed-time claim |

### PRC-001 — UPHELD

INTERACTION_STATES begins with independent state axes and a combination rule for retained, stale, partial data. SYSTEM_CONTRACT section 5 says a successful fetch need not mean a successful save. SOURCE_AND_DATA_CONTRACT sections 4.3 and 9 prohibit overwriting retained read meaning with mutation status.

The original Save handler's assignment to the same scenario variable still removes read warnings or substitutes loaded fixtures for no-data states. Calling it a local simulation limits the consequences; it does not make that demonstrated behavior conform to the proposed contract. This remains a blocker for adopting the original specimen as the common interaction model.

**Minimum repair evidence:** A frozen source model with independent read/access/write state, plus a bounded trace showing stale and partial data remain visibly qualified through pending and saved states. Show that starting from loading or unsupported cannot reveal observations merely by invoking Save. If only source inspection is available, the code defect may be recorded as source-remediated while runtime verification stays open.

### PRC-002 — UPHELD

SOURCE_AND_DATA_CONTRACT section 4 expressly requires a source-key namespace where keys can collide, stable entity identity, field identity, and evidence precision. SYSTEM_CONTRACT's EvidenceInspector anatomy includes source/entity/field. PAPER_BUILD_PLAN's “Exact row” annotation repeats stable entity/field/observation identity.

The original generic chart keys and generic chart-observation title do not meet those requirements. The explicit illustrative boundary is appropriate and should remain; it is not a reason to omit the fixture's own identity. The Company modal needs to remain intelligible while the surrounding comparison is obscured.

**Minimum repair evidence:** Rendered evidence payloads or source-derived content for the first Macro, Company, and Options chart observations showing distinct consumer/metric/observation identities; a Company row and chart inspector showing the same entity as their origin; and row-to-inspector values/units that match. A generic overview action must be labeled and scoped honestly rather than implying precise field evidence.

### PRC-003 — UPHELD

SOURCE_AND_DATA_CONTRACT section 4.2 distinguishes Options observation window, print range, session date, acquisition, and source clocks. Section 4's Time rule prohibits substitution among clock kinds. This reinforces the original finding.

Contract expiry can remain the aggregation bucket, but it cannot be the only “Observed period” for premium observed in an earlier print window. No production feed is needed to make this distinction correctly in an illustrative fixture.

**Minimum repair evidence:** Both expiry buckets retain their exact amounts and explicitly separate their expiry attribute from the observed trade window/session. The inspector's labels, chart caption, and exact-value table must agree. Real producer/served timing remains a separate D08 integration gate.

### PRC-004 — UPHELD

INTERACTION_STATES' Row evidence contract permits fallback when the row is removed by filtering. It otherwise requires return to the original row and preservation of route/hash/scroll. PAPER_BUILD_PLAN similarly permits fallback “if the row disappeared.”

The rationale's acknowledgement that the original HTML implements only the connected-trigger path confirms the limited implementation; it does not resolve the case where a routine sort detaches a button but preserves its row. Stable logical identity must take precedence over the lifetime of the original DOM node.

**Minimum repair evidence:** Preserve the logical evidence key, resolve the current trigger after rerender, and distinguish retained versus removed rows. A bounded browser trace should open docked evidence, sort while retaining the row, close, and return to the matching trigger and local comparison context. A second trace should remove the row and verify the named fallback/announcement. Source correction alone does not prove scrolling or browser focus behavior.

### PRC-005 — UPHELD

SYSTEM_CONTRACT section 3 specifies readable 11–12px quiet chart metadata. PAPER_BUILD_PLAN item F02-P11 requires a narrow composition that is “not a scaled desktop.” Its width table confirms the same 358px and 288px primary widths used in the first-pass source calculation.

The unavailable browser preview explains the lack of an executed comparison. It does not make the original 740-unit SVG's small labels conform to the mobile sheet. The first pass already classified the pixel estimates as source-derived, not browser measurements; that limitation remains.

**Minimum repair evidence:** Responsive geometry/ticks that preserve actual label size, with source and supplied mobile compositions agreeing. Actual 390px and 320px rendering must show readable dates/scale/gap labels; true 400% zoom from a 1280px starting viewport is a separate required check. An enlarged screenshot or exact-value table alone does not close the chart-legibility question.

### PRC-006 — UPHELD

SOURCE_AND_DATA_CONTRACT section 2.3 makes English long-form content and bilingual chrome an explicit retention requirement. This supports the first pass's refusal to demand an invented Chinese article or translated URL.

The original defect is the inherited language metadata, not the lack of translation. The English article still inherits zh-Hans after Chinese is selected. Retaining English content requires correctly identifying it as English.

**Minimum repair evidence:** The English article has an effective English language attribute in Chinese mode, while intended chrome uses its actual selected language. Show the relevant DOM/source language ownership and preserve canonical/anchor identity. Assistive-technology operation and CJK visual quality remain separate verification tasks.

### PRC-007 — AMENDED IN SCOPE, NOT WITHDRAWN

The original observations remain accurate: the standalone source does not demonstrate deep Company navigation, the complete Options workflow, Macro modules, real access recovery, virtualized inspection, or domain lifecycle behavior. The static sheets cannot themselves establish these paths.

The revealed scope makes a more precise classification possible. SYSTEM_CONTRACT section 1 calls the artifacts contextual component slices. INTERACTION_STATES' applicability table explicitly says the virtualized inspector is not implemented in the specimen. SOURCE_AND_DATA_CONTRACT sections 2, 5, and 8 retain existing domain implementations and defer commissioned integration. CONTINUITY_AND_GATES already carries full capability preservation as F02-G14.

**Amended disposition:** Carry this as a **major consumer-integration and foundation-qualification gap**. Do not require the standalone fixture to rebuild the full product, and do not equate an omitted implementation with removal of a production feature. Existing source owners and bounded real-path evidence may satisfy preservation.

Two limits remain:

1. A painted history, Share, Export, Sign in, or Check access control is not proof of a reachable action.
2. The original Analysis link's NVDA destination is not evidence of an entity-preserving handoff from the EXM fixture.

A draft specimen can remain partial if it says so. A consuming reference cannot be marked capability-preserving solely on this packet. Exact minimum domain evidence is listed in section 5.

### PRC-008 — UPHELD

SOURCE_AND_DATA_CONTRACT section 4's Comparison mapping requires a delta unit, and section 4.1 requires money to retain currency and scale. SYSTEM_CONTRACT's ChangeValue anatomy has the same requirement.

The original static Company sheet supplies “0.00 USD/share,” while the HTML emits “0.00” in a mixed-measure change column. Rationale offers no alternate interpretation that removes the ambiguity.

**Minimum repair evidence:** The HTML comparison and evidence view both explicitly identify the absolute dividend change and its unit. Preserve the distinction from an undefined percent change from a zero baseline. This can be verified from a frozen source/content comparison; it does not require a new backend.

### PRC-009 — UPHELD WITH THE ORIGINAL MEASUREMENT LIMIT

The rationale explains the generic metric/chart/table hierarchy, including its proposed phone order. It also identifies the **twelve-column tape as the Options primary object** and premium-by-expiry as supporting context. It provides no task evidence that placing that support above the tape is preferable for scanning qualifying prints.

The finding remains a composition concern: the supplied layout increases initial vertical travel to the tape and has no compact/tape-first option. It is not a measured claim about elapsed task time, and the differently sized original images should not be treated as a calibrated usability experiment.

**Minimum repair evidence:** A dense Options composition with compact/optional support, or a task-based demonstration of the proposed order, assessed at a matching viewport and known content density. Show where active filters and the first meaningful group of rows fall. A pleasing full-height artboard alone cannot establish that the dense-comparison job was preserved.

## 4. Consequences for the original task matrix

No critical task is upgraded merely because its desired behavior is now written in a contract. The original first-pass matrix remains unchanged in its frozen report.

For later interpretation, the T06/T08/T12 UNKNOWN judgments and the unverified portion of T07 are specifically **integration qualification gaps**, not proof of feature deletion. T01/T07's WORSE assessment concerns visible Options task priority. T03/T04/T05/T10/T11 remain unqualified end to end, with the concrete original source defects described separately.

The rationale preserves the original positives: explicit units and comparators, zero versus unknown, gaps in the illustrative chart, independent trade-side semantics, and candid illustrative/authority labeling. These should survive the repairs.

## 5. Minimum capability-preservation evidence

These are bounded acceptance witnesses for the actual owners. They are not instructions to duplicate the domain engines or to carry out unauthorized writes in this review.

| Owner / task | Exact minimum evidence needed before a capability-preservation claim |
| --- | --- |
| D02/D03 — Macro | A chosen real metric/table/chart mapping naming raw fields, universe/denominator, units, observation/publication/retrieval clocks, missing behavior, and freshness owner; a composed path retaining regime/risk/calendar/linked desks; and affected-scope proof that the US-stock sibling remains intact when the common template changes. The route registry's data-source label alone is insufficient. |
| D07 — Company | One actual supported entity through annual/quarterly statements, all three statement families, earlier-period paging/definitions, and evidence/transcript navigation; raw period/currency/field mappings including a missing field, a reported zero, and a non-comparable earlier definition; a second supported entity switch demonstrating no stale relabeling and correct return/parser context. Existing owner/source receipts may provide the field proof. |
| D08 — Options | A representative print with exact underlying/contract identity and distinct side/exposure meaning; working premium/DTE/moneyness/symbol filtering and existing view tabs; saved-screen, share, and export paths with explicit actual record scope/precision; source/transport/session/coverage states bound to the consumer schema and an actual producer/served receipt. Denied access and entitlement-service unavailability remain distinct. |
| Existing DataInspector owner — virtualized/focused chart | A real existing grid trace preserving canonical row/time keys after sorting, prepending, filtering, and replay; mounted active descendant and row count/index; the existing keyboard/selection map; honest CSV/replay scope and row-limit refusal. A twelve-row ordinary table is not a substitute and a second virtualizer is not required. |
| Public editorial owner | A representative emitted page from the actual chosen builder/template inputs, preserving the authored English body, canonical URL, existing heading slugs, TOC, calendar publication/update dates, related/continuation destinations, and bilingual chrome. Verify effective content language, a calculation/table/source path, and narrow reading order. A different illustrative title/body does not prove the original article migrated intact. |
| Domain verdict/count/lifecycle owners | A retained source-bound example showing the actual domain labels, exhaustive/disjoint count meaning where applicable, and at least one meaningful transition/return condition with its authority intact. Record the actual predecessor and affected scope. Do not replace the domain contract with a generic Accepted chip or a directional color. |
| D23 / current write owner | For later real save integration: actual callback/endpoint ownership, immutable account subject, request/object identity where supported, confirmed failure versus uncertain outcome, deduplication/reconciliation policy, and owner-confirmed readback. Navigation/context/theme actions must remain read-only. Local timer-driven save simulation cannot supply this receipt. |

For access recovery specifically, identify the existing valid sign-in/plan/session return targets or callback slots and show the preserved context. If a supporting fixture does not wire those actions, label that limitation; do not manufacture authentication routes or imply the static action was exercised.

## 6. Gates that rationale does not close

The following are **reported open in the revealed documents, with no new closure evidence supplied to this rationale pass**. I did not requery their live services.

| Gate | Minimum evidence needed | What does not substitute |
| --- | --- | --- |
| P00 Paper writer qualification | Original-owner qualification tied to the actual current server/catalog and admitted carrier, followed by a bounded successful write/readback with exact observed IDs and time. The reported catalog mismatch must be resolved through its owner. | Read serviceability, an approval statement, another carrier, or a static source illustration. |
| Editable Paper composition | Real native editable component/consumer objects and the Read me/adjacent annotations; exact created/changed file/page/node IDs; readback of content/geometry; captures/exports whose hashes bind to the reviewed version. Retained originals remain accounted for. | A construction plan, SVG editability, flat raster screenshots, or invented successor IDs. |
| F01/F02 joint freeze | Versioned shell and system identities covering actual rail/header/local navigation/inspector slots, minimum useful content width, compact/narrow behavior, public/focused-chart boundaries, context/preferences, and overlay/history/return behavior. Bind source and Paper artifacts to the same reviewed set. | Baseline production dimensions or the candidate's own calculated width table. |
| Browser and input qualification | A normally authorized reachable HTTP/HTTPS preview serving the exact frozen candidate; keyboard tab/sort/filter/evidence/return paths; touch access without hover; dock-to-overlay identity/return; scoped table scrolling; actual 400% zoom; meaningful reflow checks at the specified width classes. Record viewport, state, steps, result, and revision. | Direct-drawn narrow frames, syntax checks, source inspection, an unreachable preview, or a policy-blocked URL. |
| Locale and visual accessibility | Real installed-CJK rendering of the Chinese variants with long labels and missing/zero/caveat examples; English-body language metadata in bilingual editorial; light/dark legibility and relevant reduced-motion/forced-color/input checks. | Unrendered Chinese SVG text, token contrast calculations alone, or a tofu image. |
| Source/field/producer qualification | Domain-owned mappings and the bounded receipts/paths in section 5, including current source timing, coverage, citation precision, and access behavior. | Illustrative fixtures, an endpoint name, a consumer schema's existence, or a fresh transport connection. |
| Independent formal review and authority | The required admitted independent reviewer-class receipts for product regression and visual/taste review, bound to the exact final artifact set, with first-pass freeze/rationale sequence and findings dispositions; then the designated authority's actual verdict. | This native advisory report, designer self-certification, a README status, or another domain's historical approval. |

Browser and Paper constraints can justify returning an honest partial candidate. They cannot justify calling those gates complete. They also do not prevent fixing source-visible state, identity, unit, or language defects before further review.

CONTINUITY_AND_GATES preserves Sector and Prophet conditions under their existing owners. Their historical approvals do not approve F02. Those conditions remain scoped to adoption of the affected domain references; this review does not demand unrelated domain reconstruction or silently override any carried condition.

## 7. Ready for frozen delta review

**I am ready for a frozen delta review.** I have not inspected the evolving repair.

The next bounded review input should provide:

1. An immutable replacement artifact directory and manifest with file sizes, individual hashes, artifact-set identity, and committed source identity.
2. A concise mapping from PRC-001 through PRC-009 to changed paths and intended corrections, with the relevant updated source and static images. The repaired set must not silently mix stale sheets with new source.
3. Evidence provenance for any newly supplied browser or Paper captures: actual revision/route, viewport/state, timestamp, and executed steps. If those gates remain open, say so.
4. The original frozen set and both independent report files preserved unchanged.

The delta review can assess source and static repairs without pretending that unavailable runtime/Paper/formal receipts exist. Its result should separately state which original code/design defects are corrected, which behavioral consequences are verified, and which integration or authority gates remain open.

**This rationale pass changes no candidate artifact and grants no approval. The original-set BLOCK remains in force as an advisory judgment until a new frozen set is assessed.**

