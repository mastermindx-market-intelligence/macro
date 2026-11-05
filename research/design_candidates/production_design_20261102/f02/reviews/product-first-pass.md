# F02 Product Regression Critic — quarantined first pass

**Verdict: BLOCK**

**First-pass freeze time:** 2026-11-03 02:08:11 UTC

**Reviewer role:** Independent native advisory Product Regression Critic. I did not author this candidate. This is an advisory assessment of the supplied reference set, not an admitted Opus RIG receipt, an authority approval, or evidence of production deployment.

## Scope and immutable identity

The reviewed root is /workspace/scratch/55964f568673/f02/.

- Supplied Macro commit: **6ee221069deba909b0f1eceee53869d4f4569ac9**. This commit identity came from the assignment; I did not inspect Git history under the quarantine.
- Artifact-set SHA256 recorded in the supplied manifest: **2823e06343b79f47474657310a9301f22e25b8051e0cd168db60150d6ece97a0**.
- Manifest: reviews/first-pass-artifacts.json; file SHA256 **9cc39370f50e0b0c97614f3742f953d42a1453f89ec1d3f2a132829b489915a5**.
- Task packet: reviews/FIRST_PASS_PACKET.md; file SHA256 **bfcb8bc963903cdbca576a0d0691fd4d4f2887df0e3b1a5820b02163287c3a95**.
- Standalone source: pattern-lab.html; SHA256 **e6466c85a9286f41ee56ded6c2f7a7cf177528ad8dcbda512a7386ea021b7e84**.
- **All 32 manifest members matched their recorded byte lengths and individual SHA256 values.** I visually inspected all 18 supplied raster images, read the complete HTML source, and inspected the text/geometry source of all 13 SVGs. The Chinese-only SVG was assessed as source, not as rendered CJK proof.

The only design inputs read were the packet, its listed artifacts, and the manifest. No author explanations, contracts, READMEs, continuity or verification reports, PR description, or other reviewers' findings were read. I did not execute the HTML, open a browser, run an interaction test, or modify a candidate artifact.

The verdict concerns whether this exact set can serve as a reliable shared interaction and consumer reference. It does **not** assert that omitted production capabilities have been deleted. The packet explicitly describes bounded slices. Their omission creates a preservation evidence gap where indicated below.

## Decision

The visual examples make meaningful progress on units, unknowns, source clocks, and trade-side language. However, the standalone reference has concrete state and identity defects: saving can erase freshness warnings or reveal data from a loading/unsupported scenario without a read transition; chart evidence identifiers collide across consumers; and Options chart evidence labels contract expiry as the observed period.

Those defects concern the core job of knowing what a value is, whether it is usable, and how to return to it. They are sufficient to block adoption of this reference as the shared behavior model. Additional source/static disagreements and unverified integration paths prevent a capability-preservation pass.

### Findings index

| ID | Severity | Evidence class | Main affected tasks |
| --- | --- | --- | --- |
| PRC-001 | blocker | Observable source logic | T04, T10, T12 |
| PRC-002 | major | Observable source/static identity mismatch | T03, T06, T07 |
| PRC-003 | major | Observable source clock semantics | T02, T03, T04, T07 |
| PRC-004 | major | Observable source focus-return logic | T03, T05 |
| PRC-005 | major | Source-derived narrow-layout defect; browser result unverified | T01, T05, T11, T12 |
| PRC-006 | major | Observable document-language metadata defect | T05, T09, T11 |
| PRC-007 | major | Observable specimen omissions plus unverified consumer integration | T06, T07, T08, T10, T12 |
| PRC-008 | minor | Observable unit omission | T02, T06 |
| PRC-009 | major | Visible task-priority regression | T01, T07 |

## Observable defects

### PRC-001 — Saving changes the read-state truth

**Severity: blocker.**

In pattern-lab.html, one variable, cfg.scenario, represents availability, source freshness, coverage, access, and save outcome. The Save handler on line 66 assigns it to pending and then saved. The notice function on line 48 shows the stale/partial/error caveat only while that same variable has the corresponding read-state value. The emptyState function on line 54 similarly controls whether observations exist on screen.

The source therefore defines these paths:

| Starting scenario | Authorized local action | Source-defined result |
| --- | --- | --- |
| Stale | Save example view | Stale notice disappears immediately when scenario becomes pending; it stays absent after saved. |
| Partial or refresh error | Save example view | Coverage/error notice disappears even though no source read or coverage change occurred. |
| Loading, empty, or unsupported | Save example view | The Save button is enabled; pending is outside emptyState's cases, so analytical() substitutes the full metrics/chart/table fixture. |

The useful-data timestamps do not change, and the save handler performs no independent source-state reconciliation. A write-state transition has become a read-state transition.

The before-state specimens explicitly retain the dated assessment or available evidence. The production Options image also presents transport, market session, snapshot age, source-response age, and observed cycle separately. The proposed state sheet says these meanings remain independent, but the HTML model does not preserve that independence.

**Required correction:** Keep read availability, freshness, coverage, entitlement/session, and write outcome as independent state. Saving must preserve existing read caveats and must not manufacture a loaded result. Include a combined stale-plus-partial-plus-save-pending example.

**Boundary:** This is a defect in the local simulation's behavior model. I do not claim a real account write, security bypass, or production data exposure occurred.

### PRC-002 — Evidence is not consistently self-identifying

**Severity: major.**

The evidenceContent function on line 59 emits source identity as “f02.fixture.v1 / ” plus the supplied key. The chart keys generated by tableValues on line 50 are only chart-0, chart-1, and so on, regardless of consumer.

Consequently, the same displayed source identity **f02.fixture.v1 / chart-0** can mean:

| Consumer | Displayed observation |
| --- | --- |
| Macro | 2026-10-21: 61.80% |
| Company | FY 2022: USD 12.00 bn |
| Options | Expiry 2026-11-20: USD 2.857 m |

Every one is titled only “Chart observation.” The Company chart inspector does not retain the entity EXM / Example Industries or the metric Revenue. Company row inspectors retain the metric name but also omit that entity. This matters most in the narrow modal, where the comparison behind it is unavailable.

The static 320px Company evidence design expressly includes **EXM · Example Industries**, so the source loses identity that the proposed visual reference itself treats as necessary. The production Company image likewise keeps NVDA and the statement context in view.

The overview source action is also generic: it has no field/metric value or consumer-specific source identity. It cannot substitute for a precise source reference for the headline metric.

**Required correction:** Give evidence a stable consumer/entity/metric/observation identity and render those fields in the inspector. Chart observations must retain the same metric and entity context as their originating chart. A row index within a consumer is insufficient as the sole displayed identity across a shared reference.

**Boundary:** Fixture labeling is candid. This finding does not demand that illustrative data pretend to be a real filing or feed; it demands that the fixture remain internally exact.

### PRC-003 — Options chart evidence substitutes expiry for observation time

**Severity: major.**

The Options rows describe trades observed on 2026-10-30; evidenceContent constructs their period as that date plus the print time in America/New_York. In contrast, the chart branch assigns period from the grouping label, producing **Observed period: Expiry 2026-11-20** or **Expiry 2026-12-18**.

Expiry is the dimension used to aggregate the observed premium, not the time when the premium was observed. The inspector has no separate observed trade window for these aggregate values. The default publication and retrieval clocks remain 2026-10-30, making the mixed meanings particularly apparent.

The Options before-image distinguishes last-session data and source-response timing. The after-sheet also claims that transport and source clocks remain separate. The source then merges an instrument attribute with the observation-period field.

**Required correction:** Preserve the print observation/window date separately from the contract-expiry bucket. Label both explicitly. Aggregate evidence should also name its contributing cohort, rather than using the expiry label as its entire temporal identity.

**Boundary:** This is visible in source construction. No live market clock was queried and no runtime inspector was executed.

### PRC-004 — Sorting a retained row breaks return to its evidence trigger

**Severity: major.**

The docked inspector stores the original button element as evidenceTrigger. The sort handler on line 66 replaces the comparison region's innerHTML, detaching that button even when its underlying row still exists. closeEvidence on line 60 then checks only whether the old element is connected. If it is not, it focuses the table hint and announces that the original row changed.

A concrete source-defined path is:

1. At a wide layout, open a Macro row's evidence.
2. Sort the comparison by Above 50D while the dock remains open.
3. Close the inspector.

The row's stable data-evidence key is retained by comparison(), but closeEvidence does not use it to find the newly rendered trigger. The user returns to a generic instruction instead of the inspected row. The same issue applies to a retained Options row after filtering or sorting.

The narrow static inspector expressly promises focus return to the source trigger. The source does implement a useful fallback for a truly removed row, but it takes that fallback for a routine rerender too.

**Required correction:** Preserve the evidence key and resolve the current trigger by identity before falling back. Preserve the comparison's applicable scroll context as well; scroll restoration itself remains unverified in this review.

**Boundary:** The detached-node path is observable in the code. Actual keyboard, browser focus, and scroll behavior were not exercised.

### PRC-005 — The HTML does not carry the mobile chart's readable label scale

**Severity: major.**

The supplied 390px static Macro chart uses native-sized 10–11px tick labels and fewer date labels. The HTML chart instead always uses a 740-unit-wide SVG viewBox with all eight Macro date labels. The mobile CSS sets SVG text to 12 units and the chart element to width:100%.

With the source's 16px main padding on each side, a nominal 390px viewport gives a 358px chart width. The SVG's 12-unit text therefore scales to approximately **5.8 CSS pixels**. At 320px, a 288px chart gives approximately **4.7 CSS pixels**. The 190px minimum height creates additional vertical space; it does not enlarge the label scale constrained by the SVG width.

This is materially different from the supplied mobile composition. The exact-value table is a useful alternate path, but it does not make the chart's dates, scale, and missing-session label readable.

**Required correction:** Use responsive chart geometry and an appropriate tick set, preserving an actual readable text size. The source should implement the narrow composition's compression, not simply shrink the desktop SVG.

**Boundary:** These sizes are derived from the supplied CSS and SVG geometry, not measured from a browser screenshot. Narrow rendering and 400% zoom require direct verification after correction.

### PRC-006 — Chinese selection mislabels the retained English article

**Severity: major.**

The article function on line 58 locally defines translation selection to always return English. This preserves the English article, which is consistent with the supplied editorial sheet's stated content boundary. However, sync on line 62 sets the document language to zh-Hans whenever Chinese is selected, and the English article/main content has no lang="en" override.

The result described by the source is a Chinese-language document containing a substantial English article, TOC, headings, and calculation labels that inherit the wrong language metadata. The shared inspector can be Chinese while the underlying article remains English.

**Required correction:** Mark the retained English content explicitly as English and apply the chosen locale to the chrome that is intended to be bilingual. Do not invent an article translation or locale route.

**Boundary:** The metadata defect is observable. Screen-reader pronunciation was not tested.

### PRC-008 — Dividend change loses its explicit unit in the HTML

**Severity: minor.**

The Company static sheets show the Dividend per share change as **0.00 USD/share**. companyRows on line 41 stores its change as only **0.00**, and comparison on line 52 renders that unchanged in a column otherwise mixing percent growth and percentage-point differences.

The row's unit describes the raw per-share amounts. It is not a sufficient substitute for explicitly labeling the change measure when neighboring changes use different units. The inspector repeats the same bare change value.

**Required correction:** Render the absolute dividend change with its unit, and distinguish it from an undefined percentage change from zero. Keep the source and sheets consistent.

### PRC-009 — The Options slice makes scanning the tape materially slower

**Severity: major.**

The production Options image puts workflow navigation, filters, and the tape ahead of a large illustrative summary. Its first data row appears at approximately y=465, with twelve prints visible in the supplied 1043px-high view. In the proposed 1440px static composition, the first row's text is at y=780, after a large page header, three metrics, and the expiry aggregation. The complete twelve-row table extends past y=1120.

The images have different widths, so this is not a calibrated same-viewport performance measurement. It is nonetheless a clear task-priority change in the proposed layout. The common source confirms the ordering: analytical() always places metrics() and chart() before tableArea(). The density control changes row height; it offers no compact or tape-first arrangement.

An investor whose immediate task is comparing prints has more vertical navigation before reaching the primary object. A reasonable user could prefer the current product for that important task, even though the new table labels and exact contract columns are clearer.

**Required correction:** Provide a dense Options arrangement that keeps the tape and active filters near the top, with compact or optional aggregate context. Retain the useful chart without forcing it to precede every dense comparison.

## Preservation and recovery evidence gap

### PRC-007 — Depicted capabilities are not demonstrated by the supplied source

**Severity: major; this is not a claim of production feature deletion.**

| Area | Concrete before evidence | Proposed evidence and remaining gap |
| --- | --- | --- |
| Company depth | company-before.png shows Income statement / Balance sheet / Cash flow, Annual / Quarterly, transcripts, 17 fiscal years from 2010–2026, and historical paging. | Company sheets depict those statement/period controls and say “17-year history remains reachable.” The HTML has three statement periods, five chart periods, and only Comparison / Chart data tabs. It has no corresponding period/history/transcript path. |
| Options workflow | options-before.png shows workflow/view tabs, presets, premium/DTE/moneyness filters, saved screens, Share Tape view, Export CSV · 2,000, and a 2,000-print count. | Options sheets depict several filters, Share, Export, and Save. The HTML implements only a symbol filter, sorting, twelve fixture rows, and local simulated save. No share/export/saved-screen path or full workflow retention is demonstrated. |
| Macro capabilities | macro-before.png shows regime, mixed/risk assessments, a 61-session path, market instruments, calendar state, and linked working context. | The after is an eight-session breadth slice. Its footer instructs future retention, but it does not demonstrate how these current capabilities remain reachable or compose with the new pattern. |
| Access recovery | The existing pattern specimen includes a View access action. The proposed state matrix depicts Sign in, Check access, and Sign in again. | notice() supplies an action only for refresh error; saveArea() disables saving in guest/denied/expired scenarios. The depicted access-recovery actions have no equivalent action/path in the source. |
| Domain counts/lifecycle and charts | The task manifest requires existing domain-owned meanings, transitions, partitions, and chart/replay capabilities. | Static fixture counts and an Accepted chip do not demonstrate those integration contracts, chart/replay retention, or virtualized-list row identity. |

The shell's current Analysis link is also hard-coded to /analysis?symbol=NVDA while the Company fixture describes EXM. That link is not evidence of an entity-preserving handoff from the proposed Company view.

The packet expressly permits bounded slices, so the right conclusion is **preservation unverified**, not “all these features were removed.” A retention sentence or a painted control cannot establish that a critical user task remains available.

**Required evidence:** Representative consumer integration paths for the retained controls and recovery destinations, with explicit route/entity context and a bounded large-list/virtualization case. If this remains only a visual slice, keep those critical tasks open rather than treating the shared component set as fully qualified.

## Improvements worth retaining

- Compared with paper-metric-before.jpg, which leaves the comparator and delta unit undefined, the after examples explicitly use percentage points, prior-session or fiscal-year comparisons, and meaningful currency units.
- Reported zero is distinct from missing Energy, diluted EPS, and unknown Options moneyness. Missing chart observations break the Macro line rather than being filled in.
- The Options table keeps symbol, full expiry, call/put, strike currency, premium currency, quantity, DTE, moneyness, and flags distinct. Estimated side is explicitly separated from intent and price prediction. Its colors are independent of the direction-convention setting in the source.
- The source provides table captions, numeric alignment, row-specific evidence labels, keyboard-focusable scroll regions, tab roles, an Escape handler, and a native dialog path. These are useful implementation provisions, though they are not completed interaction verification.
- The editorial example retains the calculation, separates arithmetic average, total return, and annualized compound return, and states the no-cash-flow/fee/tax assumptions. It qualifies the sequencing statement rather than suggesting that reordering identical returns alone changes terminal wealth.
- The artifacts repeatedly disclose illustrative data, local save simulation, and static/Paper limitations. I found no basis to treat their “Saved” example as an actual server receipt, or to treat the supplied images as formal browser/Paper/RIG proof.

## Critical-task judgment matrix

Judgments compare what is actually observable in the supplied before/after evidence. UNKNOWN means the complete task cannot be established from this packet; it does not negate a specific after-source defect listed above.

| Task | Judgment | Evidence and practical implication |
| --- | --- | --- |
| T01 Compare dense numeric rows | **WORSE** | Numeric formatting and units improve, but the Options composition materially postpones access to its primary comparison. Source retains rows in horizontally scrollable tables; full-size/virtualized operation is unverified. PRC-005, PRC-009. |
| T02 Interpret a metric and its change | **BETTER** | The visible percent/pp, fiscal period, currency, zero, and missing distinctions improve on the ambiguous canonical metric. Dividend-change labeling and Options aggregate temporal identity still need correction. PRC-003, PRC-008. |
| T03 Inspect exact evidence and return | **UNKNOWN** | The before images do not establish an executed inspector baseline. The after source has identity collisions and a retained-row focus-return defect; it cannot be considered a passing path. PRC-002–004. |
| T04 Understand stale/partial/connected states | **UNKNOWN** | The copy distinguishes these concepts, but the source erases read warnings on save. Actual prior/after combined-state behavior has not been exercised. PRC-001, PRC-003. |
| T05 Use keyboard/touch/400% zoom | **UNKNOWN** | Several semantic provisions exist. Focus return, mobile chart text, article language, zoom, touch behavior, and large-list semantics prevent a verification claim. PRC-004–006. |
| T06 Preserve Company depth | **UNKNOWN** | Annual/quarterly, earlier periods, definitions/transcripts, and exact entity handoff are not demonstrated by the source. No deletion is inferred. PRC-002, PRC-007, PRC-008. |
| T07 Preserve Options depth and meaning | **WORSE** | The supplied layout is worse for immediate print scanning, while contract/side labels improve. Workflow/filter/saved-screen/share/export retention remains unverified. PRC-003, PRC-007, PRC-009. |
| T08 Preserve Macro capabilities | **UNKNOWN** | The breadth example is useful, but regime/risk/calendar/linked desks and existing domain logic are not integrated in the supplied set. PRC-007. |
| T09 Read and navigate public editorial | **EQUIVALENT** | The displayed core English calculation, body structure, TOC/anchor targets, dates, and continuation hrefs retain the basic reading job. Full article preservation and destination availability are unverified; Chinese-mode language metadata is defective. PRC-006. |
| T10 Handle exceptional read/write/access states | **UNKNOWN** | The state vocabulary improves, but combined states and recovery actions are incomplete in the source. Real write authority/readback and entitlement enforcement are explicitly outside the fixture. PRC-001, PRC-007. |
| T11 Switch theme/locale/density | **UNKNOWN** | Supplied light/dark pairs retain the visible data and semantics. Chinese glyph rendering, long-label behavior, narrow chart labels, English-content language metadata, and actual density usability remain unresolved. PRC-005, PRC-006, PRC-009. |
| T12 Use domain-owned verdict/count/lifecycle and focused charts | **UNKNOWN** | Simple fixture charts/counts do not prove retained domain partitions, lifecycle transitions, replay, or consumer-owned chart logic. Read/write state coupling is a concrete warning against generalizing this source. PRC-001, PRC-005, PRC-007. |

## What this freeze does and does not conclude

This exact set should not be adopted as the common behavior reference until the state, evidence identity/time, return-context, and narrow/language defects are corrected. The useful visual and semantic improvements can be retained in a revised set.

The next review should distinguish corrected artifact behavior from the still-open consumer preservation evidence. Browser/assistive-technology operation, 400% zoom, touch, live source/auth behavior, save authority, and actual destination availability remain unverified here. None was inferred from a static image.

**This first pass is frozen.** Author rationale may be considered in a later, separately identified response; it must not silently replace or amend these observations.

