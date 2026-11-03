# F01 — bounded product amendment after rationale reveal

## Status and preserved first pass

**The first-pass findings and task verdicts remain unchanged. Candidate.3 resolves several requirements in source, while the reviewed native compositions and runtime evidence remain incomplete. The justified remedy refinement is to support sequential modal inspection at 1024px rather than require an undersized dock. Sequential inspection must not be described as demonstrated simultaneous comparison.**

The immutable first pass is `CLOSED_PRODUCT_FIRST_PASS.md`, SHA-256 `a2b2512933686221fdb3b16ac917ab78fabef5312600e379d81eb56a0b2266b8`. Its hash was rechecked before this amendment. The parent reports its publication at Macro `09742de176f553bb30e89a0ade95643d76416c30`, Git blob `cfceb927d16da8c7afe91b1bbc8cb3c549e9fbf0`. This amendment is a separate bounded advisory return. It does not replace that report, confer formal review authority, or establish acceptance, implemented behavior, or test passage.

I read the rationale reveal and the relevant local counterparts of four exact source documents identified there. The counterpart source identity supplied by the reveal is Macro `3ec131bb4b515c5ede76f51e9d8e65f128bc19ae`. I did not read peer reports, browse additional repositories, inspect underlying Terminal code, operate Paper, or execute product behavior. Statements about incumbent source behavior below are attributed to the supplied source contract; they are not a second independent code audit. No new images were inspected in this amendment; native observations remain those from the nineteen images inspected in the frozen first pass.

## Findings that stand, and what source now specifies

| First-pass finding | Amendment disposition | Source-level clarification and remaining closure |
| --- | --- | --- |
| P01 — Company controls, history, transcripts and saved research | **Stands, High. Retention is now explicit in source.** | `PRODUCT_UX_SPEC` §5 requires the Financials subviews, statement type, annual/quarterly history, transcripts, Saved research and Your theses. `ACCEPTANCE_TESTS` CF01–CF03 specifies their paths and return context. C still does not depict these controls. D07 retains composition/parser ownership; the remedy is to expose the existing paths in the measured slot, not invent a new Financials product. |
| P02 — incomplete Options object and export contract | **Stands, High. The schema question is resolved in source only.** | `SOURCE_AND_DATA_CONTRACT` §§3.1–3.2 enumerates the seven categories, fifteen local view/home destinations, guide/Futures access, eleven Tape columns, filter state and separate thirty-column CSV. The CSV exports the entire filtered/sorted collection, beyond the rendered 150-row window. D still omits the complete object and retains its unsupported twelve-field claim. O01–O09 and V01 remain specifications. |
| P03 — ambiguous exact-period evidence selection | **Stands, High. Trigger and replacement requirements are now specific.** | `PRODUCT_UX_SPEC` §6 requires subject-named evidence triggers, one inspector and object replacement. CF04 requires the selected field/period to agree with the displayed value/unit, stable-key focus restoration after rerender, and fallback only on true removal. C still has no depicted FY2024 cell selection or unambiguous period trigger. |
| P04 — comparison obstruction at 1024px | **Observation and unmet comparison outcome stand. Remedy refined below.** | The measured-width rule makes a dock unsuitable at 1024px. A sequential modal is a legitimate responsive mode. It does not establish simultaneous table/evidence comparison or a completed replacement/return flow. The amendment distinguishes these two tasks instead of prescribing a cramped dock. |
| P05 — irreversible-looking compact mode and lost phone local views | **Stands, High. Controls and ownership are now specified.** | `PRODUCT_UX_SPEC` §§2 and 5 defines a separate 44px Compact/Expand control, names, keyboard behavior, focus handling, mounted-instance state scope and phone overflow/More views. N09 covers reversal through width changes. A/H still omit the toggle, and E still lacks the complete local-view treatment. The existing state is not an account preference and should not be advertised as one. |
| P06 — source/event precision | **Stands. Source establishes a stricter limitation.** | The actual Tape contract distinguishes event identity, inferred side and clocks, and supplies no qualified bid/ask/exchange mapping. The first-pass remedy must use real available fields and truthful absence. It must not fill D’s specimen with invented quotes, venue or citations. The new contradiction is detailed below. |
| P07 — incomplete access/data/write outcome evidence | **Stands, High evidence gap.** | The source specifies real-owner inputs, no false write outcome, no automatic replay, and readback/deduplication. B06–B08 give falsifiable cases. It does not supply the missing native state set or demonstrate D23 reconciliation. Retained predecessors remain useful references, not completed new transitions. |
| P08 — layer/focus/phone-target contracts | **Stands, with a more concrete integration dependency.** | `PRODUCT_UX_SPEC` §6 supplies a modal/dock/Brain transition table; §9 specifies the 44px house target and zoom/focus requirements. N10–N11 adds scenarios. The Brain lifecycle binding is explicitly unresolved. Native phone target geometry and actual keyboard/touch behavior remain open. |
| P09 — B loses entries without density gain | **Stands, Medium.** | The reveal acknowledges equal 1168px Macro width and incomplete B utility parity. Source recommends A and treats B as a comparison. Agreement with the finding is not its closure; a repaired B or a demonstrated task advantage would still be required to change the judgment. |
| P10 — unexplained five-of-eleven sector view | **Stands, Medium.** | The reveal confirms that the five-row illustration does not establish full coverage or justify unexplained omissions. D02/D03 own the real content. The correct remedy is an explicitly bounded subset, actual full data when available, and honest coverage—not invented rows or values. |

These are meaningful specification completions. In particular, the required retained features are no longer merely implicit; exact ownership, state scope, schemas and proposed tests are recorded. They do not change what is visible in C/D/E/H or prove the behaviors described in those files. The report’s UNKNOWN outcomes remain UNKNOWN.

## Refined remedy for 1024px evidence

### The geometry explains a valid constraint

The joint contract §2 gives a 196px expanded navigation rail and 20px gutters at 1024px. The useful content width is:

`1024 − 196 − 20 − 20 = 788px`

A 320px dock plus a 24px gap would leave:

`788 − 320 − 24 = 444px`

That fails the proposed 640px minimum primary width. Even explicit compact navigation would leave only `1024 − 72 − 40 − 320 − 24 = 568px`, so forcing compact mode would neither satisfy the rule nor respect the user’s navigation choice. The source also allows a domain object to require more than 640px; the minimum is not proof that every table is usable exactly at that width.

At 1280px with expanded navigation, the same calculation yields 664px, matching C’s proposed dock layout. This supports a measured-container rule rather than an assumption that every desktop-looking viewport supports a dock. These are checked allocation calculations based on the proposed contract, not measurements of a running implementation.

### Sequential inspection and simultaneous comparison need separate closure

**Sequential inspection at 1024px:** Keep the main object at its useful width while the evidence layer is closed. Open a single modal for an exact row/event. Make the background inert, keep the modal controls reachable, and return to the same valid row, filters, sort and horizontal/vertical scroll after closing. Show a complete inspect → close → select another row → inspect sequence, or an explicit owner-qualified in-modal replacement control. Either approach must preserve exact identity and avoid a nested inspector stack. A proposed replacement rule alone is not a demonstrated flow.

**Simultaneous comparison while reading evidence:** The scrimmed background in D cannot serve as the comparison surface. To satisfy this outcome at 1024px, show a deliberate comparison/reference inside the modal with the relevant exact values and identities, or another domain-qualified comparison presentation that respects the width requirement. Such a presentation has not been supplied. If simultaneous comparison is instead supported only where the primary object and dock fit, state that responsive capability boundary explicitly; do not silently treat the narrower sequential task as passing the same requirement.

Accordingly, P04 should not be read as a claim that a modal at 1024px is intrinsically a regression. Its factual observation stands: the reviewed state prevents usable table/evidence comparison, and no replacement sequence was shown. The appropriate next repair is a coherent sequential modal and separately qualified comparison capability, not a 444px primary table. This amendment does not authorize reducing the original task brief’s comparison outcome.

The agreed source modal is **440px**, while D draws **400px**. Correcting that discrepancy is necessary for source/native consistency; it does not by itself solve comparison or return fidelity. The <=600px full-width treatment likewise needs its own reachable controls and exact-object return evidence. The original F02 handshake file was not opened in this amendment; its concurrence is reported by the supplied joint contract and reveal, and is not claimed as independently revalidated here.

## Additional contradictions and dependencies exposed by the reveal

### A01 — High: D’s side/quote semantics conflict with the declared retained source

`SOURCE_AND_DATA_CONTRACT` §3.2 reports Side values of `~buy`, `~sell`, and `mixed`, with inference explicit. Its inspected consumer supplies no bid, ask or exchange field. D instead depicts “At ask,” a bid/ask pair and a “Time · exchange” label whose value is an ET clock. Time zone is not exchange identity. The illustrative-data label prevents this from becoming a claim of current market data, but does not make those proposed semantics valid mappings to the existing product.

**Closure:** Use the actual inferred-side vocabulary in the retained Tape and its evidence anatomy. Show unsupported quote/venue/source fields as unavailable or omit them with a truthful scope. Preserve the supplied premium without inferring a multiplier from the illustrative price/size. Keep `event.id` as event identity; it is not automatically a vendor/filing citation. O08 is a useful test specification for this correction, still NOT_RUN.

This also refines P06: the remedy is not to demand that an owner invent a filing-like source record for an Options print. It is to expose the available event/feed provenance accurately and identify what is unavailable.

### A02 — Medium: the proposed version and native geometry still disagree

The reveal identifies candidate.3 source against candidate.1 native metadata. I’s candidate.1 label was visible in the first pass; the separate native Readme was not inspected. The joint contract specifies 440px modal evidence while D remains 400px, and its eleven-column requirement still conflicts with D’s twelve-field wording. These mismatches make it possible to review or implement the wrong variant.

**Closure:** After lawful effect reconciliation, publish repaired native artifacts and matching version/schema/geometry metadata in one exact evidence set. Rehash the repaired artifacts. Do not revise the frozen first-pass evidence or use a source-only version increment as proof of a native update.

### A03 — High source-level dependency: exact return promises exceed the documented existing paths

The source contract §3.1 reports that Options local tab changes use `URLSearchParams.set` and `replaceState(null)`, so ordinary query bytes can be reserialized, duplicate tab values collapse, and other history metadata is not established as preserved. §4 reports different company-context behavior across toolbar, mobile and directory entry, and distinguishes hard named return from bounded legacy restoration. These disclosures reinforce T06/T11 UNKNOWN. They prevent a byte-preserving shell transport from being used as blanket proof for local native actions.

**Closure:** Use O03/O09 and H01–H07 to establish the intended per-action query/hash/history contract and actual return outcome. Keep the change with the existing Options/navigation owner. Separately verify current URL-selected company versus stale active cursor across every entry. A/H/D’s generic “Open chart” must be repaired to the source’s defined “Open Terminal” meaning when no exact company is intended. Native selection/scroll/focus restoration remains separate from returning to the right URL.

### A04 — High integration dependency: the Brain arbitration policy lacks a qualified lifecycle signal

`PRODUCT_UX_SPEC` §6 and the source contract §3.3 say the inspected typed bridge exposes open/mounted/setPrincipal, without a qualified close/open-state acknowledgement. The proposed policy suspends evidence, preserves its identity, and relies on the existing Brain closing through its own owner before another surface opens. This is a useful design policy, but the acknowledgement it requires is not established by the reviewed source material.

**Closure:** D06 must supply the actual lifecycle binding and F02 must review the added interaction clauses. Then demonstrate N10/N11 without a second assistant, hidden focused layer, duplicate source attachment, discarded request or false cancellation. No guessed event, private-state polling or extra host should be introduced merely to satisfy the diagrammed transition.

One further action distinction is now explicit: company search’s **Show all markets** invokes an existing persisted visibility preference, not merely a transient search filter (`SOURCE_AND_DATA_CONTRACT` §5.1). Preserve that intentional action and its owner-confirmed delivery semantics. Ordinary query entry or market navigation must not invoke it implicitly. This is a source-specified constraint for T02/T07/T11, not a newly observed write defect.

## Evidence status and bounded recommendation

All 79 uniquely identified acceptance cases are explicitly **NOT_RUN**. I counted the case rows; I did not execute them. The reported Company Financials return-target observation establishes neither a completed Terminal round trip nor selection/scroll/focus restoration. No access/save recovery is newly demonstrated.

The unresolved Paper effect and later non-retryable metadata result explain why native corrections remain undone. This amendment did not inspect dispatch/effect receipts, reconcile an operation, or attempt a write. A missing terminal receipt is not evidence that an operation had no effect, and the hold does not reduce any product closure requirement.

The bounded direction remains **A**, with complete domain-owned local controls, the C dock where measured width permits it, a qualified sequential modal at narrow widths, exact F route identity, and explicit state/recovery ownership. Retain P01–P10 and the first-pass task verdicts. Use the source completions to make the next native and behavioral evidence precise; do not describe them as finished product work.

## Actual files read and hashes

The following new input files were read in this amendment. Paths are relative to `/workspace/scratch/43a778472c23/f01-drafts/`.

| File | Actual inspection scope | SHA-256 |
| --- | --- | --- |
| `evidence/blind/RATIONALE_REVEAL.md` | Complete | `590be01ad7fe281ad6929e2e34036a0a3a728348d9921a345f9766653d9f6645` |
| `PRODUCT_UX_SPEC.md` | Complete | `91837f76c9d987e096125402d5fa60513fa9c4e488309aebad1f0772bef2c4f9` |
| `JOINT_SHELL_SYSTEM_CONTRACT.md` | Complete | `7530c394cb76fdae555c172e8eeefcaa3039ade3d8a5b18d25d568af1555fb0f` |
| `SOURCE_AND_DATA_CONTRACT.md` | Sections 1–4, 5.1, 6–9 and 10; headings and targeted keyword matches elsewhere. Section 3.2’s previously truncated portion was separately reread. | `b3bfc2d65ba490a6942424ae89a193916023fed41c899efe61b2b1b1665e0484` |
| `ACCEPTANCE_TESTS.md` | Complete; case IDs counted only | `786e1ddb0744440f3e2cbe4eca48b614fc89c36258d4191408011e5e31624e8d` |

The first-pass file was read only for its SHA-256 recheck during this amendment; its known content and image observations were retained from the prior task. No peer report, source-receipt JSON, underlying Terminal implementation, original F02 handshake, execution-hold receipt, or additional native artifact was read. This separate amendment is frozen on delivery; its SHA-256 is reported outside the file.
