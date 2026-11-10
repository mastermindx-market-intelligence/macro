# F01 — Closed visual/taste amendment after rationale disclosure

**Status: bounded advisory second pass, frozen separately.** This amendment preserves the original report and every original finding. It does not provide formal design acceptance, reviewer-class/RIG authority, QA01 qualification, implementation permission, or an executed-behavior result.

## Record preserved

- First-pass report: `CLOSED_TASTE_FIRST_PASS.md`.
- Preserved SHA-256: `e54d3f96a8839c995199dd6fffa41b1a0008e9137c89dd1a8b7507de35448925`.
- First-pass publication supplied by the task: Macro `09742de176f553bb30e89a0ade95643d76416c30`, Git blob `02187204d5ce8f0c55289f94b393966c7d95fbdf`.
- Original closed input: Macro `3ec131bb4b515c5ede76f51e9d8e65f128bc19ae`; manifest SHA-256 `f5092fa6ff999fefb8b00a3ed15d0157756fd5f5fbedeae9fa645e31f113ee1b`.
- Amendment frozen at UTC: 2026-11-03T08:04:39.620683+00:00.

The rationale was read only after the first pass had been frozen and published. The first-pass bytes were checked again before this amendment was written. No peer report was consulted. No new image or changed native composition was supplied or inspected in this pass; native observations below refer to the original nineteen images and nine JSX exports already reviewed.

## Result

**The visual findings remain open. The rationale materially improves their interpretation and the specificity of remedies, especially at 1024px, but does not repair the reviewed compositions.** A remains the preferable desktop foundation. The author's stated choice of A and acknowledgment that B has incomplete utility parity agree with the independent first-pass judgment; that agreement is not additional usability evidence. [RATIONALE_REVEAL §§1–3; PRODUCT_UX_SPEC §2]

The central amendment is to **V04**: sequential modal inspection is a defensible response to the stated 1024px width constraint. I do not recommend forcing a dock into an inadequate content slot or making a genuine modal background interactive. The original observation remains true: D does not demonstrate simultaneous comparison or a replacement sequence while evidence is open. Those operations must be distinguished from sequential inspection and assessed in the mode where they are actually supported. [JOINT_SHELL_SYSTEM_CONTRACT §2; PRODUCT_UX_SPEC §6]

The source also exposes a substantive new mismatch beyond missing columns: D depicts **At ask**, bid/ask quotes, and “Time · exchange,” while the documented Tape consumer supplies inferred `~buy`/`~sell`/`mixed` classification, no qualified bid/ask/exchange fields, and no established multiplier/recomputation contract. Its caution about buyer intent does not fix that schema mismatch. [SOURCE_AND_DATA_CONTRACT §3.2; ACCEPTANCE_TESTS O08]

## 1. Disposition of every first-pass finding

“Specified” below means addressed in a written requirement or source description. It does not mean the pixels, interaction, or retained user outcome have passed review. Original severities and per-task judgments remain part of the unchanged first-pass record; the entries below describe the amendment rather than retroactively rewriting that record.

| First-pass finding | Amendment disposition | What the reveal changes, and what remains open |
| --- | --- | --- |
| **V01 — Company depth, S1** | **Stands; source requirement now explicit** | PRODUCT_UX_SPEC §5 and acceptance CF01–CF03 explicitly retain Financials subviews, statement type, available history/transcripts, Saved research, and Your theses under D07. C still does not show those controls. A four-period specimen is now explicitly a window, not an imposed history cap. |
| **V02 — incomplete Options object, S1** | **Stands; source specification substantially clarified** | SOURCE_AND_DATA_CONTRACT §§3.1–3.2 supplies the seven-category/fifteen-destination vocabulary, eleven-column Tape, complete filtered/sorted thirty-column CSV, row-drill behavior, and controls. D's six-data-column specimen and twelve-field claim remain unchanged. The new field-semantic mismatch below strengthens the concern. |
| **V03 — ambiguous Company selection, S1** | **Stands; source replacement/selection requirement explicit** | PRODUCT_UX_SPEC §6 and CF04 now require exact field/period identity, a subject-named trigger, one inspector, stable field-key focus, and preserved history/scroll. C's FY2024 pane, unmarked cell, and darker FY2025 bar remain the observed conflict. |
| **V04 — blocked comparison/replacement, S1** | **Observation stands; remedy refined by mode** | A dock at 1024 would violate the primary-width rule. Sequential modal inspection is the intended narrow mode. The scrim is appropriate for that mode; the missing sequential/replace evidence and unfulfilled simultaneous-comparison claim remain separate issues. See §2. |
| **V05 — B sacrifices utilities without density gain, S2** | **Stands; remedy priority narrowed** | B is explicitly an unselected spatial alternative, not a claimed equivalent. There is no reason to repair every utility merely to archive the comparison; utility parity becomes necessary if B is proposed as a complete replacement. Its equal 1168px width and missing visible utilities remain facts. |
| **V06 — unexplained Macro subset/coverage, S2** | **Stands** | D02/D03 own content; missing values must not be invented. Calling the five-row example illustrative does not explain the subset, denominator, missing session, or source-clock relationship. Remedy is truthful scope/absence and access to qualified content, not fabricated extra rows. |
| **V07 — phone local views, S1** | **Stands as missing native local-navigation evidence; vocabulary remedy refined** | PRODUCT_UX_SPEC §5 now requires actual local views on phone and says the Macro sample tabs illustrate a slot rather than admit routes. Retain the first-pass observation that E drops A's represented local choices, but do not convert the word “Regime” into a newly invented D02 route. Demonstrate parity using D02's real vocabulary. |
| **V08 — compact mode and location cues, S1** | **Stands; source owner/control now specified** | The required control reuses the existing brand-area toggle and mounted-instance state, with separate Compact/Expand labels, 44px anatomy, focus behavior, and no automatic collapse. This is a clearer remedy than inventing a Settings preference. A/H still omit it; the inactive-Today treatment is explicitly required by N12. |
| **V09 — important touch targets, S2 evidence gap** | **Stands; written anatomy requirement explicit** | The joint contract and PRODUCT_UX_SPEC §9 specify the 44px house target and phone rows of at least 48px. Those requirements do not establish the independent activation boxes for E's language/market/evidence controls or F's Clear in the frozen native artifacts. |
| **V10 — directory copy/result return, S2** | **Stands; source owner/retention scope clarified** | Product §4 and source §7 preserve the distinct routes and query/category while the existing directory remains mounted. “Exact routes retained” and “Specialist destination” remain weak investor-facing copy. Do not enlarge the retention promise to reload/account persistence without evidence. |
| **V11 — evidence prose without a real object, S2** | **Stands; completeness remedy refined** | D07/D08 must supply actual source and field semantics. A complete specimen must represent the supported object and honest absence; it must not invent a filing citation, vendor identity, exchange, quote, or multiplier to fill a desired anatomy. See §3. |
| **V12 — return path and layers, S2 evidence gap** | **Stands; some unknowns now have specific source obligations/dependencies** | Product §§6–7 distinguish named-company entry from Open Terminal and supply a transition policy. Native Open chart remains ambiguous. Complete return is expressly unverified; the Brain lifecycle acknowledgment is an identified D06 dependency. Source-only clauses do not close the missing sequences. |
| **V13 — incomplete recovery coverage, S2 evidence gap** | **Stands** | Retained state boards remain references, not newly executed transitions. Source §6 confirms actual owner inputs are needed to distinguish guest, expired, unavailable, and uncertain-write states. The I matrix still does not supply all required user-facing specimens. |

The first-pass **T01–T12** labels remain frozen artifact-only judgments. This pass improves specification coverage for several of those tasks; it supplies no new pixels or completed journeys with which to award visual or behavioral closure.

## 2. Refined remedy for 1024px evidence

### What the width rule establishes

The disclosed rule preserves at least 640px of useful primary content after a 320px dock and 24px gap, with a larger minimum permitted for a domain object. The arithmetic is coherent:

| Composition | Useful width before evidence | Width remaining after 320 + 24 dock | Implication |
| --- | ---: | ---: | --- |
| 1024, expanded 196px navigation, two 20px gutters | 788px | 444px | Dock fails the stated 640px minimum. |
| 1024, explicitly chosen 72px compact navigation, two 20px gutters | 912px | 568px | Compact would still not make the dock eligible. Automatic collapse would also violate the stated mode choice. |
| 1280, expanded 224px navigation, two 24px gutters | 1008px | 664px | Dock is eligible for a domain that can use this remaining width; C demonstrates this allocation. |

These are static calculations from the candidate geometry, not measured browser results. The first-pass preference for keeping C's readable dock remains sound. At 1024, a forced dock would shrink the analytical object below the agreed minimum and would not be a justified remedy for D. [JOINT_SHELL_SYSTEM_CONTRACT §2; SOURCE_AND_DATA_CONTRACT §8; ACCEPTANCE_TESTS G02–G05]

### Sequential inspection and simultaneous comparison are different outcomes

**Sequential inspection** means open one exact record in the modal, read it, close to a stable originating row/control and scroll position, then choose another record. This can preserve analytical work while using the full width for each task in turn. D has not shown that sequence, but the sequence is a legitimate candidate for narrow screens.

**Simultaneous comparison** means the relevant other values and evidence can be read together, and any permitted replacement operation is discoverable while evidence remains open. A dimmed, inert table behind D's modal does not provide that operation. The generic source clause “opening another object replaces the inspector” does not identify the actual control that permits the second choice while the modal owns input. [PRODUCT_UX_SPEC §6]

The refined visual closure for V04 is therefore:

1. Correct D to the contracted **440px** modal anatomy at 1024, with readable content and reachable close/action controls. The current 400px pane is a separate native/source mismatch.
2. Show a selected record before opening, the exact modal object, closure to the same logical row and horizontal position, and opening a second exact record without losing filters/sort. This establishes the proposed sequential design sequence, not runtime restoration.
3. If **replacement while open** is required in this mode, show an owner-qualified record selector or previous/next operation inside the modal. Do not rely on activating the inert table behind it. A selector must preserve real filtered/sorted order and exact event identity; the shell should not invent a new domain traversal model.
4. Demonstrate **simultaneous comparison** at a width where the dock is qualified, or show explicit comparison values inside the modal if that same-width operation is required. Label sequential narrow coverage honestly; do not count it as simultaneous comparison.

This refines the remedy, not the original task into a weaker undisclosed promise. A narrower device can legitimately use a different interaction sequence; its capabilities and limits still need to be visible and tested separately. The original V04 wording already allowed a modal with an equivalent comparison operation. This amendment additionally recognizes a properly demonstrated sequential path without treating the dark modal background itself as a taste defect.

## 3. Source-only resolutions and owner-safe remedies

Several questions raised by the closed packet now have concrete written answers:

- **Company depth and history:** use D07's real parser, subviews, controls, historical windows, and saved-work entry points. Restore these within C's usable width; do not replace them with a generic four-year summary. [PRODUCT_UX_SPEC §5; CF01–CF04]
- **Options completeness:** preserve the actual eleven data columns, current row drill, filters, saved/share state, and existing thirty-column export of all filtered/sorted events. Evidence is an additional separately named action, so it must not swallow the row drill. [SOURCE_AND_DATA_CONTRACT §3.2; O07–O09]
- **Compact choice:** use the existing brand-area toggle, separate from brand navigation, with in-instance state and visible labels in both modes. Do not invent account synchronization, local storage, or an automatic inspector-driven collapse. [PRODUCT_UX_SPEC §2; SOURCE_AND_DATA_CONTRACT §3.3; N09]
- **Exact versus generic chart entry:** a qualified Company action names the symbol; a context without an intended company says Open Terminal; invalid Company identity must not silently fall back to a stale cursor. This clarifies the source intent but leaves A/H/D's visible Open chart text unresolved. [PRODUCT_UX_SPEC §7; N13]
- **Layers:** the candidate suspends evidence while the existing Brain is open and preserves selection for explicit reopen. It avoids two side docks and protects C's 664px primary area. This is a coherent proposed policy; it is not presently demonstrated or integrated merely because a transition table exists. [PRODUCT_UX_SPEC §6; N10–N11]
- **Local views:** use the real domain vocabulary. For E, the first-pass A-to-E discrepancy remains a valid visual stress-test failure, but the repair must not create a new Macro URL or feature from an illustrative tab label. [PRODUCT_UX_SPEC §5]
- **Complete evidence:** “complete” should mean complete supported identity, fields, source/clock semantics, and explicit absence, not a requirement that every imaginable evidence field have a value. A qualified owner example is preferable when available. Where a citation or quote is absent, retain that absence and clearly name the inspector's actual scope. [PRODUCT_UX_SPEC §8; SOURCE_AND_DATA_CONTRACT §§3.2, 9A]

These resolutions help prevent the wrong repairs. They do not change the first-pass observation that the reviewed controls, selection treatments, and complete analytical objects were missing from the native specimens.

## 4. Newly exposed contradictions and limits

### A01 — S1: D's invented quote-level semantics conflict with the documented consumer

**Evidence:** SOURCE_AND_DATA_CONTRACT §3.2 documents inferred `~buy`, `~sell`, and `mixed`; Time ET is a timestamp, not exchange identity. The inspected consumer description supplies no qualified bid, ask, exchange, or multiplier. Original D instead depicts At ask, `$2.40 / $2.45`, and “Time · exchange.” O08 expressly calls for truthful absence and prohibits deriving those fields from inferred side.

**Consequence:** The visual model suggests a more precise observation than the documented object supplies. This is more serious than merely omitting some columns. The statement that an at-ask print does not establish buyer intent is sensible in isolation, but it does not make At ask a supported label for this consumer.

**Falsifiable closure:** Revise the native example against one actual owner-qualified event shape, retaining inferred classification and source premium, with truthful missing-field treatment. Remove quote/exchange/multiplier semantics unless D08 supplies a qualified mapping. Keep the separate evidence action and all retained column/filter behavior.

The first-pass `$2.45 × 1,000 × 100 = $245,000` observation was explicitly conditional arithmetic. The disclosed contract now makes clear that it must **not** be used to infer a multiplier or recompute the premium. Numerical plausibility is not source fidelity.

### A02 — S2: The native set and disclosed source are different candidate states

**Evidence:** Original D.jsx `70JQ-0` is 400px; the joint candidate specifies 440px at 1024. Original I says Candidate 1, while the disclosed product/joint sources are candidate.3. The rationale acknowledges these mismatches and the omitted native controls. I's metadata was actually viewed in the first pass; the separately mentioned native Readme was not read in this amendment.

**Consequence:** A reader could mistakenly treat the original captures as visual proof of candidate.3's geometry, control placement, or interaction completion. Updating a written source or a metadata label alone cannot establish that the native set implements it.

**Falsifiable closure:** After lawful continuation, reconcile the native geometry and missing controls, then bind a new frozen visual export to its exact source candidate and clearly retained predecessor references. Until then, explicitly label the source/native difference. No requirement is waived because an edit is paused.

### A03 — S2 evidence gap: Brain arbitration now has a specific unresolved lifecycle dependency

**Evidence:** Product §6 and source §3.3 record a typed bridge exposing open/mounted/setPrincipal but no qualified close/open-state acknowledgment; D06 must bind the actual lifecycle. Candidate.3's added interaction clauses remain pending F02/D06 review, while the stated earlier concurrence covers unchanged candidate.2 geometry/ownership. This amendment read those documentary sources, not the underlying Terminal bridge code or live script.

**Consequence:** The proposed one-modal/one-Brain policy cannot be counted as operationally feasible or already coordinated from the available bridge description. Assuming that “hide” means “closed,” inventing a close event, or mounting another host would defeat the retained-owner constraint.

**Falsifiable closure:** Bind the real D06 lifecycle signals and F02-reviewed interaction clauses, then show the intended evidence → Brain → close → explicit evidence-reopen sequence with stable focus and identity. Preserve the distinction between a source agreement, a visual sequence, and an executed integration result.

### Effect hold and acceptance specifications

The disclosed unresolved Paper operation and DOCUMENT_CHANGED response explain why pixel repairs have not been completed. I did not inspect their dispatch/effect receipts, retry them, rekey them, or treat them as no-effect proof. They do not reduce the visual closure criteria. [RATIONALE_REVEAL §6]

The acceptance document contains **79 distinct case IDs**, counted during this pass, and expressly marks the work **NOT_RUN**. Counting cases was document inspection, not running tests. The additional source clauses and case coverage are useful planning artifacts; they do not close the original visual findings, prove complete Terminal return, or qualify recovery/write outcomes. [ACCEPTANCE_TESTS status, §§8–10]

## 5. Actual files read and boundaries

The following local counterparts were the new content inputs to this bounded pass. Their declared published source is candidate.3 at Macro `3ec131bb4b515c5ede76f51e9d8e65f128bc19ae`; the review records the actual local byte hashes below. I did not independently fetch the remote commit blobs, the linked F02 handshake, or underlying Terminal producer files. Statements about those sources are attributed to the documents actually read.

| File relative to `/workspace/scratch/43a778472c23/` | Actual review scope | SHA-256 |
| --- | --- | --- |
| `f01-drafts/evidence/blind/RATIONALE_REVEAL.md` | Read in full. | `590be01ad7fe281ad6929e2e34036a0a3a728348d9921a345f9766653d9f6645` |
| `f01-drafts/PRODUCT_UX_SPEC.md` | Read in full, focusing on direction, local depth, width/mode rules, layer transitions, exact chart entry, and retained scope. | `91837f76c9d987e096125402d5fa60513fa9c4e488309aebad1f0772bef2c4f9` |
| `f01-drafts/JOINT_SHELL_SYSTEM_CONTRACT.md` | Read in full; geometry and candidate.2 versus candidate.3 concurrence scope are central to this amendment. | `7530c394cb76fdae555c172e8eeefcaa3039ade3d8a5b18d25d568af1555fb0f` |
| `f01-drafts/SOURCE_AND_DATA_CONTRACT.md` | Read relevant sections and indexed headings: ownership, global/local state, Options hierarchy/Tape, compact/Brain, return, source inputs, recovery, directory, geometry, composition boundaries, dependencies, and open obligations. The company-search transport subsection was not separately reviewed in full. | `b3bfc2d65ba490a6942424ae89a193916023fed41c899efe61b2b1b1665e0484` |
| `f01-drafts/ACCEPTANCE_TESTS.md` | Read relevant rules and cases through search/excerpts, especially sections 5–9; counted all case IDs. This was a specification read, not test execution. | `786e1ddb0744440f3e2cbe4eca48b614fc89c36258d4191408011e5e31624e8d` |

The original `f01-review-output/CLOSED_TASTE_FIRST_PASS.md` was read only to verify its unchanged SHA-256. No peer report was opened. No new images were claimed as viewed, and no browser, Paper, account, GitHub, source, or external mutation was performed. Only `f01-review-output/CLOSED_TASTE_AMENDMENT.md` was written.

**Stop condition:** This is the one commissioned bounded second-pass return. The original report remains unchanged; no formal acceptance or behavioral pass is inferred from author agreement, source concurrence, unavailable runtime evidence, or the effect hold.
