# F02 Product Regression Critic — Candidate 2 repair pass

**Advisory verdict for adoption: BLOCK.**

**Repair disposition:** Eight original source/static defects are resolved in the supplied evidence. PRC-007 remains an open major consumer-integration qualification gap. One additional minor source defect is recorded as PRC-010.

**Review freeze time:** 2026-11-03 02:46:30 UTC

**Role and authority:** Independent native advisory Product Regression Critic. I did not author Candidate 2. This report is not an admitted Opus RIG receipt, designated design-authority approval, browser qualification, or production acceptance. The original first-pass and rationale-pass reports remain unchanged.

The adoption block does **not** mean the original state/identity blocker remains in the repaired source. Those repairs are substantive. The current set is a useful partial source/static proposal, but it does not yet establish the critical consumer-preservation and interaction paths required by the unchanged task manifest. The new density issue is minor and is not the principal reason for this verdict.

## 1. Exact reviewed identity

All paths in this report are relative to **/workspace/scratch/55964f568673/f02/** unless an absolute path is given.

| Identity | Value |
| --- | --- |
| Candidate | F02-SYSTEM/1.0.0-candidate.2 |
| Supplied Macro commit | `1253a647d193e1eacd1eb6f523a7a031529d2150` |
| Supplied branch / review context | `design/f02-system-v1-20261102-c2`; Draft PR 10630 |
| Artifact manifest | `reviews/repair-artifacts.json` |
| Manifest freeze | `2026-11-03T02:33:00.270945+00:00` |
| Artifact-set SHA256 | `6c1f8ba6937c620a306644764d69d7adef5672d27f6c512a080dcb35063f9ca3` |
| Manifest file SHA256 | `638215e4a9f8cb7cc8f8bd58dc6c59d866a7ece046b4252b5ba283bab15352ea` |
| HTML SHA256 | `126fd3bce0677f73ca0f422c762f0ce47bc239d61f04d959688c1a93d2555360` |
| Unchanged task packet SHA256 | `bfcb8bc963903cdbca576a0d0691fd4d4f2887df0e3b1a5820b02163287c3a95` |
| Original artifact commit | `6ee221069deba909b0f1eceee53869d4f4569ac9` |
| Original artifact-set SHA256 | `2823e06343b79f47474657310a9301f22e25b8051e0cd168db60150d6ece97a0` |

**All 53 manifest members matched their recorded byte lengths and individual SHA256 values, including the final pre-write recheck.** I also independently reproduced the aggregate digest by sorting relative paths lexically and hashing the UTF-8 concatenation of each `path + U+0000 + lowercase SHA256 + U+000A`. The manifest itself is excluded from its member list. The supplied repository commit was recorded as assignment provenance; I did not independently inspect Git history.

The two historical reports were rehashed immediately before this report was written:

| Preserved report | SHA256 |
| --- | --- |
| `reviews/product-first-pass.md` | `dc49d84c50d250a0616079372d5e3f5508edc66acc9c634f1a5b53a8ed62051b` |
| `reviews/product-rationale-pass.md` | `0599244070916d53ce282551141d2e55c407e12e942da96ef2aaadb6cc41dbfe` |

The original exact artifact copy remains at **/workspace/scratch/55964f568673/f02-review-freeze-1/**. This report does not revise either earlier judgment about that earlier set.

## 2. What was actually inspected

I read the complete repaired `pattern-lab.html`, the typed Company fixture, the repair packet, the unchanged T01–T12 job manifest, the relevant updated contract/state/verification sections, and the explicitly authorized architect consultation and author dispositions. I read the source-model checker and its supplied report as source evidence; I did **not** execute the checker, candidate JavaScript, or HTML.

I visually inspected the six revised Macro/Company/Options light/dark desktop PNGs, `mobile-comparison.png`, `macro-dark-390.png`, and `states-and-semantics.png`. I inspected the Chinese mobile SVG and 320px Company evidence SVG as text/geometry source. The seven before-images and the two editorial desktop PNGs are byte-identical to those examined in the first pass; their earlier visual observations carry forward. I additionally reopened the unchanged Options before-image for the task-priority comparison.

A read-only JSON comparison established that the embedded Company fixture and `fixtures/company-history.json` decode to the same object. The five series each contain 17 values, and each series' latest five values agree with its corresponding FY 2022–2026 statement row. This is data/source consistency, not a plotted-pixel or real-filing test.

No browser, alternate renderer, DOM, input automation, service, account, or Paper operation was used. No peer critic report was read. I wrote only this new review report.

### Evidence provenance matters

The supplied `repair-model-verification.json` reports 480 source-state combinations, 3,360 read-invariance transitions, 59 evidence records, four overview entry points and 96 observation-admission cases at the current HTML digest. The checker extracts pure functions and markup generators. It does not run `render`, native dialog behavior, event dispatch, focus, scrolling, browser layout, fonts, or service callbacks. These counts are **author-supplied model-check results**, not browser executions or independent path receipts.

The architect consultation's own final HTML digest is `254be643794b4dff7d517c72ebeeda8b6a40cd93bde85aa4cae982b30e165c1b`, which predates the current `126fd3…` source. `ARCHITECT_DISPOSITIONS.md` identifies the later focus-visibility change. I inspected that change in the current source; I do not silently extend the architect's older exact-source check to a new revision or treat it as independent approval.

The supplied PNG/SVG plates are directly drawn compositions. Their compact arrangements are visual design evidence. They are not screenshots of the HTML, native editable Paper exports, actual 400% zoom results, or proof that depicted controls work.

## 3. Original findings: exact dispositions

“Resolved in supplied source/static evidence” means the concrete original defect is corrected at this artifact boundary. It does not close the separately listed runtime or integration qualification.

| Finding | Original severity | Candidate 2 disposition | Concrete basis and remaining boundary |
| --- | --- | --- | --- |
| PRC-001 — Saving changes read-state truth | Blocker | **RESOLVED IN SOURCE/STATIC EVIDENCE** | Separate availability/freshness/coverage/access/write fields; write transitions preserve read fields; save-only rendering retains the read DOM; combined stale/partial/pending and expired/uncertain examples are explicit. Runtime and real reconciliation remain unverified. |
| PRC-002 — Evidence is not self-identifying | Major | **RESOLVED IN SOURCE/STATIC EVIDENCE** | Consumer/entity/metric/period namespaces, explicit EXM identity, exact cohort/contract context, and explicit overview mappings replace the collisions and generic evidence. Actual consumer-to-inspector integration remains unverified. |
| PRC-003 — Expiry substitutes for observation time | Major | **RESOLVED IN SOURCE/STATIC EVIDENCE** | Options aggregate evidence records the print window separately from contract expiry and contributor identities; tables and chart copy agree. Actual producer clocks/coverage remain open. |
| PRC-004 — Sort loses the retained evidence trigger | Major | **RESOLVED IN SOURCE** | Current triggers are resolved by the stable evidence key after rerender, with stored local scroll, deliberate visibility request, and a distinct removed-row fallback. Actual focus/scroll behavior remains unverified. |
| PRC-005 — Narrow chart labels shrink | Major | **RESOLVED IN SOURCE/STATIC EVIDENCE** | Macro/Options use measured-width SVG geometry; Company retains minimum 840px geometry in a named local scroll region. Actual pixels, zoom and font behavior remain unverified. |
| PRC-006 — Chinese selection mislabels the English article | Major | **RESOLVED IN SOURCE** | English article main, harness and skip link have explicit language metadata; translated component specimens have their own selected language. Effective AT/CJK behavior remains unverified. |
| PRC-007 — Consumer preservation is unproved | Major integration gap | **STILL OPEN** | Company specimen breadth improves, and the misleading NVDA shell link is removed. Full domain workflows, source mappings, recovery, lifecycle and existing virtualized/chart paths remain unproved. |
| PRC-008 — Dividend delta omits its unit | Minor | **RESOLVED IN SOURCE/STATIC EVIDENCE** | Comparison and evidence use `0.00 USD/share`; the note explicitly distinguishes undefined percentage growth from a zero base. |
| PRC-009 — Options tape loses task priority | Major | **RESOLVED IN SOURCE/STATIC EVIDENCE** | The revised plates put filters and all twelve prints before the expiry chart; HTML ordering puts the comparison before the chart and reduces summary spacing. Same-viewport browser density and full workflow integration remain unverified. |

### PRC-001 — Read truth survives local write transitions

The relevant source is `transition`, `readSnapshot`, `notice`, `emptyState`, `renderSaveOnly`, and the save/access event handlers. `SAVE_START`, `SAVE_RESULT`, and `SAVE_CHECK` alter the write axis without changing availability, freshness or coverage. An access loss while pending changes the outcome to uncertain. The generation guard prevents a superseded local timer from reporting a later success for a different consumer or access generation.

The ordinary save path updates only the save area. It no longer substitutes the loaded analytical body merely because a write becomes pending or saved. A no-observation state also routes its source action to coverage context, and `openEvidence` independently rejects inadmissible observation requests.

The state plate explicitly shows “older source / partial 7 of 8” alongside pending save and alongside post-dispatch session expiry with unknown outcome. These are concrete corrections to the original model and drawing. The supplied pure-model result is consistent with the inspected source.

The local “saved” and “check save status” transitions remain simulations, disclosed by the persistent harness. They do not establish a request identity, server commit, authenticated account, or reconciled readback. Real access recovery remains PRC-007.

### PRC-002 — Evidence now retains its own meaning

`evidenceRecord` and `evidenceContent` now construct and display consumer, entity/cohort, metric, observation period/window, source identity, publication/retrieval or article-update context, units, and explicit dimensions.

For example, the first chart observations now have distinct source identities derived from their actual meaning:

| Source path | Identity construction in the current source |
| --- | --- |
| Macro universe history | `f02.fixture.v2/macro/example_universe/share_above_50d/2026-10-21` |
| Company first fiscal year | `f02.fixture.v2/company/EXM/income_statement_five_series/FY2010` |
| Options November expiry group | `f02.fixture.v2/options/cohort_12/observed_premium/2026-10-30/expiry_2026-11-20` |

Company row and chart records retain **EXM · Example Industries**. The chart record for a fiscal year contains all five series for that year. An Options row retains symbol, expiry, call/put, strike currency, print identity and observation time. Overview actions have an explicit consumer mapping; editorial resolves to its own calculation, while the Options overview uses total cohort premium rather than silently relabeling one expiry bucket.

The 320px Company plate retains entity, metric, five fiscal periods, change measure and separate source clocks while the originating table is out of view. This addresses the original isolation problem. Production field/citation precision is still a consumer-owned acceptance case.

### PRC-003 — Options time and aggregation are separate

The current aggregate record's observation window is **2026-10-30, 15:47:31–15:58:42 America/New_York**. Contract expiry is a separately labeled bucket, and contributor print IDs are recorded separately. The two source-derived bucket sums remain USD 2.857m and USD 1.687m, with five and seven contributing prints; together they are the twelve-print USD 4.544m fixture cohort.

The exact-value caption and revised plates describe observed premium grouped by expiry. They explicitly avoid claiming a market/session total. This resolves the substitution of expiry for observed time. The common fixture window is not proof of continuous feed coverage or the actual market-wide population.

### PRC-004 — Return logic now uses logical identity

`closeEvidence` searches current `[data-evidence]` elements for the captured key when the original button has been detached. The source restores the stored table-region offsets, focuses the current matching trigger with `preventScroll`, and then requests nearest visibility using `scrollIntoView`. Scroll padding reserves space for a sticky header. A genuinely absent row takes the named comparison/main fallback and announces that the source row is no longer in the view.

This fixes the original source branch that treated every rerender as row removal. It also addresses the architect's later observation that merely focusing a retained row after restoring an old offset could leave the target offscreen.

A layout box is not proof of visibility, and the visibility request is not proof that the relevant browser will expose the right button without losing useful scroll context. Retained-row, removed-row, horizontal-scroll, dock/overlay and actual zoom traces remain required. I observed no browser result for those paths.

### PRC-005 — Responsive geometry replaces whole-chart shrinkage

For Macro and Options, `chartSvg` derives its viewBox and explicit CSS width from the measured host width; the labels remain 12px in the source geometry. Narrow Macro plots use fewer date ticks with edge-aware alignment. The line still breaks at the missing session.

Company deliberately keeps 17 fiscal groups and five series within a minimum 840px plot inside a named, focusable horizontal scroll region. This is a reasonable two-dimensional-data boundary: it retains the plotted observations instead of squeezing 85 bars and their labels into a phone width. The exact-value table remains available.

The new 390px Macro drawing uses native-sized labels and retains the gap. The original 740-unit chart scaled into 358px/288px is no longer the source model. Actual 390px/320px layout, 400% zoom, plot overflow, CJK glyphs and forced-color readability still need the permitted preview.

### PRC-006 and PRC-008 — Language and unit corrections are explicit

The retained English article uses `lang="en"` on its main content. The English-only specimen harness and skip link also have explicit English metadata; the component specimens carry the selected locale. The root language can therefore change without mislabeling the entire English article. No translated article or new locale route is claimed.

The Company fixture now stores `0.00 USD/share` as the dividend-change measure. Both the table and inspector use it, and the note states that percentage growth from a zero base is undefined. The desktop and narrow Company evidence compositions retain the relevant units and fiscal-period distinctions.

### PRC-009 — Dense comparison priority is restored

The revised 1440px Options drawings place the first print's text at approximately y=390 and the twelfth at approximately y=808; the prior 1440px proposed drawing postponed the first row to approximately y=780. The revised aggregate chart follows the twelve-print comparison. This is a visible improvement between the drawn proposals, not a task-time measurement against production.

The current HTML's `analytical` composition similarly places Macro/Options `tableArea()` before `chart()`, with reduced summary and heading spacing. Company retains its long multi-series history ahead of its statement table, reflecting that exemplar's different task.

The source still includes a specimen harness, metrics and reference controls that are not identical to the compact Options drawing. I do not claim the HTML reaches the same y coordinate or displays the same row count in a real viewport. The original forced chart-before-tape policy is nevertheless removed. Full Options views, filters and actions remain PRC-007.

## 4. Additional concrete finding

### PRC-010 — Options body rows bypass the density setting

**Severity: minor.**  
**Evidence class:** Observable CSS/state wiring; no measured browser claim.  
**Affected task:** T11.

`pattern-lab.html` defines Comfortable by changing `--row` to 52px, and the general table-cell rule uses `height:var(--row)`. Candidate 2 then applies the more specific rule:

```css
.table-options td,
.table-options tbody th { height:40px }
```

Its narrow override fixes the same cells at 52px. The selected density is written to the root's `data-density`; there is no corresponding density-aware Options-body override.

Consequently, the Options body's declared spacing policy is the same in Dense and Comfortable modes at a given width. Other table cells, including its header, can follow the density token while the body bypasses it. Intrinsic content can make a row taller than its declared height; this finding does **not** assert that actual rendered rows measure 40px. It identifies the source-level reason the advertised preference cannot change these body cells' row-height policy.

SYSTEM_CONTRACT section 4.1 says density changes row spacing and that Comfortable increases breathing room. This hard-coded override contradicts that behavior for the Options comparison.

**Minimum correction:** Make the Options body rule respond to the selected row-density policy while retaining the appropriate narrow touch minimum. Preserve the dense tape-first layout. Bind the changed source to a new artifact identity; check the actual density effect in the already-required browser qualification, rather than claiming it from this CSS review.

I found no additional major or blocker defect within the bounded source/static repair scope inspected here. That statement is not a completeness claim for the unexecuted application.

## 5. PRC-007 remains an adoption/integration gap

The Company fixture is materially richer: 17 fiscal years × five series, five recent statement periods, a missing EPS field and a reported zero dividend. The shell no longer contains the mismatched `/analysis?symbol=NVDA` link; it clearly presents noninteractive context governed by F01. These are meaningful specimen repairs.

They do not establish annual/quarterly switching, all statement families, earlier definitions, transcript destinations, real entity switching, Options saved screens/share/export, Macro linked desks or the existing chart/DataInspector engine. Those functions are not required to be rebuilt inside the fixture. They require source-bound preservation receipts and exercised paths from the existing owners.

The following are finite minimum witnesses for closing the gap. Each applicable row needs both the relevant source/data mapping and an exercised path at the candidate implementation revision; a nonapplicable case needs an explicit owner disposition.

| Owner / area | Minimum evidence still required |
| --- | --- |
| D02/D03 Macro | One real metric/table/chart mapping naming raw fields, universe/denominator, units, observation/publication/retrieval clocks, missing behavior and freshness owner; a composed regime/risk/calendar/linked-desk path; affected-scope proof for the sibling US-stock region of the shared template. |
| D07 Company | One supported entity through annual/quarterly, all three statement families, earlier-period/definition and evidence/transcript paths; missing/zero/non-comparable/currency mappings; a second entity switch showing correct route/parser/return context and no stale relabeling. |
| D08 Options | Exact print and contract identity; side/exposure/expiry/observation distinctions; existing workflow/view tabs and premium/DTE/moneyness/symbol filters; saved-screen/share/export paths with actual scope and precision; producer/served coverage and stale receipts; distinct denied and entitlement-service-unavailable outcomes. |
| Existing chart/DataInspector owner | Canonical row/time identity through sort, prepend, filter and replay; mounted active descendant, row count/index and real keyboard/selection behavior; honest CSV/replay scope and row-limit refusal. Reuse the existing engine; the twelve-row fixture does not qualify virtualization. |
| Public editorial owner | An actual emitted page from the selected builder/template preserving English body, canonical URL, original heading slugs/TOC, dates, calculation, assumptions and continuation destinations; effective content/chrome language and a narrow reading/table/source path. The illustrative article is not a full content-migration receipt. |
| Domain verdict/count/lifecycle owners | Actual labels and partition meaning, a meaningful transition/return condition, and retained source/authority provenance. A generic accepted chip or fixture count cannot establish these meanings. |
| D23/current mutation and access owners | Actual callback/endpoint, authorized subject, immutable request/object identity where supported, confirmed failure versus uncertainty, reconciliation/deduplication policy and owner readback; valid sign-in/plan/session return paths retaining the current context. The local timer and simulated check-status button supply none of those receipts. |

This gap remains **major and open**, without implying that production features have been deleted. The author contracts correctly keep it open; that candor does not itself satisfy the capability requirement.

## 6. Critical-task judgments

These judgments compare the supplied before-state evidence with the repaired candidate at the scope actually observable. UNKNOWN means the complete critical task cannot be established. It is not a synonym for a newly observed defect, and a source repair does not automatically turn an entire task into a pass.

| Task | First-pass judgment | Candidate 2 judgment | Evidence and remaining limitation |
| --- | --- | --- | --- |
| T01 Compare dense numeric rows | WORSE | **EQUIVALENT** | The visible tape-priority regression is removed; dense rows, exact columns, source actions and zero/unknown distinctions remain. Company offers five raw periods. This restores the comparison task in the bounded drawings/source; real large-list behavior and density switching are not established. |
| T02 Interpret a metric and its change | BETTER | **BETTER** | Explicit percent/pp/currency, comparator periods, missing versus zero, corrected dividend units and separate Options observation/expiry semantics improve the supplied ambiguous canonical metric. Real producer mapping is still required. |
| T03 Inspect exact evidence and return | UNKNOWN | **UNKNOWN** | Identity and return-target source defects are repaired. Exact source/static records improve, but actual focus, visibility, scroll and consumer citation paths have not been exercised. |
| T04 Understand stale/partial/connected states | UNKNOWN | **UNKNOWN** | Independent read/write axes and combined warning examples correct the original model. Actual transport/session/coverage/freshness ownership and served behavior remain unproved. |
| T05 Use keyboard/touch/400% zoom | UNKNOWN | **UNKNOWN** | Responsive geometry, local scroll regions, stable-key return and language metadata improve the source. Real input, focus visibility, modal behavior, zoom and virtualized semantics remain open. |
| T06 Preserve Company depth | UNKNOWN | **UNKNOWN** | The fixture now has 17 years, five series and five recent raw periods with entity/units intact. Annual/quarterly, all statement families, definitions, transcripts and true route/entity handoff remain PRC-007. |
| T07 Preserve Options depth and meaning | WORSE | **UNKNOWN** | The immediate tape-scanning defect is corrected, and contract/cohort/time/side meaning is clearer. The complete task still requires existing workflow/filter/saved/share/export and coverage/access integration. |
| T08 Preserve Macro capabilities | UNKNOWN | **UNKNOWN** | Comparison-first breadth and gap-preserving history are useful. Regime/risk/calendar/linked desks and existing domain logic have no new exercised integration proof. |
| T09 Read and navigate public editorial | EQUIVALENT | **EQUIVALENT** | The bounded English reading/calculation/TOC/date/continuation structure remains, with corrected language metadata and explicit formula. Actual builder output, full original content and destinations remain unqualified. |
| T10 Handle exceptional read/write/access states | UNKNOWN | **UNKNOWN** | Source state separation and pending-to-uncertain behavior are corrected. Authentication/recovery destinations, actual failure semantics, authority and reconciled save readback remain open. |
| T11 Switch theme/locale/density | UNKNOWN | **UNKNOWN** | Light/dark plates retain visible meaning and English metadata is corrected. PRC-010 exposes an Options density-policy defect; real Chinese glyphs, long labels and preference/input behavior remain unverified. |
| T12 Use domain verdict/count/lifecycle and focused charts | UNKNOWN | **UNKNOWN** | Company history and source state semantics improve, but domain partitions/transitions, canonical time keys, replay and existing chart-engine behavior still require owner receipts. |

T01 and T07 no longer inherit the old WORSE judgment merely because the first candidate failed. Their current judgments follow the corrected evidence and the distinct remaining limits.

## 7. Conditions required before adoption

### Source correction

Resolve PRC-010 in a newly frozen affected-source set. Do not amend this report to make the present bytes appear corrected. The first-pass and rationale reports likewise remain historical evidence.

### Browser, input and rendered consistency

Use a normally authorized reachable HTTP/HTTPS preview serving the exact implementation revision. The minimum targeted cases are:

1. Open evidence, sort or filter while retaining the identity, close, and verify the exact current trigger is both focused and visibly reachable. Include a moved row, existing horizontal/vertical local scroll and dock-to-overlay transition.
2. Remove the inspected row, close, and verify the deliberate named fallback, announcement and visible return context. Exercise close-button and Escape paths.
3. Show stale plus partial data through pending and saved states; show loading/unsupported cannot expose observation values through save or source-detail actions; show pending access loss becomes uncertain. Distinguish fixture transitions from the later real owner/readback path.
4. Exercise manual tab activation, source actions and local table/chart scrolling by keyboard and touch without a hover-only essential path. Include the existing virtualized inspector's separate owner cases.
5. Verify narrow 390px and 320px rendering and actual 400% zoom from a 1280px starting viewport. Check readable chart dates/scale/gap labels, scoped two-dimensional overflow, sticky-column evidence access, overlay reachability and absence of unintended global overflow.
6. Verify light/dark and real installed-CJK variants with long labels, missing/zero/caveat cases, effective English-body language, selected/focused distinction, relevant forced colors/reduced motion, and an actual Options Dense/Comfortable change after PRC-010 is corrected.

Each trace must identify revision/route, viewport or zoom, starting state, actions, expected result and observed result. A drawn narrow plate, JavaScript syntax result, model-state count or token-contrast calculation is not that receipt. The current inability to supply such evidence explains a partial return; it does not make those tests pass.

### Consumer integration

Supply the owner-bound witnesses in section 5. There is no requirement to invent new authentication routes, rebuild the chart engine, duplicate complete domain workspaces inside the specimen, or perform real writes during this review. The actual implementation owners must prove the existing paths remain usable.

### Paper, shared shell and authority gates

The current authorized documents still report these gates open, and this review supplies no new closure evidence:

| Gate | Minimum evidence needed |
| --- | --- |
| P00 writer qualification | Original-owner resolution tied to the actual current server/catalog and admitted carrier, with a bounded supported write/readback and exact observed IDs/time. A read-only service or alternative carrier does not close the reported mismatch. |
| Editable Paper reference | Native editable component and consumer objects, Read me and adjacent annotations, exact file/page/node IDs, content/geometry readback, and captures/exports bound to the reviewed set. Direct-drawn SVG/PNG plates and a construction plan are insufficient. |
| F01/F02 joint freeze | Versioned shell and system identities for actual rail/header/local-nav/inspector slots, useful content widths, narrow/focused/public boundaries, preference/context ownership and return/history behavior; source and Paper references bound to that same set. |
| Independent formal review and authority | Required admitted independent reviewer-class receipts for the exact final artifact set, with first-pass/rationale chronology and finding dispositions, followed by the designated authority's actual verdict. This advisory report does not substitute. |
| Served implementation qualification | Applicable source/producer/access/interaction receipts and the actual served revision. No deployment or production-conformance claim follows from this design review. |

Historical Sector/Prophet conditions remain with their existing owners and scope. Their prior dispositions do not confer F02 approval. No constraint described above excuses a real source defect, and no source repair fabricates the missing qualification.

## 8. Frozen conclusion

Candidate 2 corrects the eight original source/static defects, including the original blocker. The revised comparison priority, exact evidence identity, separate clock meanings, independent state axes, English-content metadata and explicit dividend units should be retained.

**Adoption remains blocked by the open critical consumer-preservation and interaction qualification; PRC-007 remains major and open. PRC-010 is a new minor source correction.** The proposed set can continue through bounded repair and qualification as a partial candidate. It cannot yet be represented as a frozen common behavior implementation, fully preserved consumer system, editable Paper completion or approved RIG reference.

This report is frozen at the UTC time above. Any later correction or new evidence requires a separately identified delta assessment.

