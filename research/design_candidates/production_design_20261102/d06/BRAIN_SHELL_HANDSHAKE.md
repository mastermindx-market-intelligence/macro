# D06 — Brain and shell interaction qualification

**Status: source candidate; integration unqualified; RIG draft.** This document supplies D06's source-backed response to F01 candidate.3. It is not bilateral acceptance, a released shell contract, an implementation, a Paper write grant or production proof. Final shell-dependent composition remains held until verified joint F01/F02 v1.

The existing Brain implementation exposes `close`; the Terminal type does not declare it. The material gap is reliable host integration, visible lifecycle acknowledgement and exact focus return. No new API, event name, state store or assistant is introduced here.

## 1. Bound inputs

| Input | Immutable source and meaning |
| --- | --- |
| D06 assignment | [D06 at programme commit `6e1862867193ec6486a22001a0e4fb515da20448`](https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/handoffs/D06-terminal.md): design/research only; focused Terminal and existing owners retained |
| Shared-shell proposal | [F01 product specification §6 at `d6ebeefcba90387b42817f8e87792e630d5862eb`](https://github.com/mastermindx-market-intelligence/macro/blob/d6ebeefcba90387b42817f8e87792e630d5862eb/research/design_candidates/production_design_20261102/f01/PRODUCT_UX_SPEC.md): candidate.3 proposes suspending contextual evidence while Brain is open |
| Joint interface | [F01-F02-SHELL/1.0.0-candidate.3](https://github.com/mastermindx-market-intelligence/macro/blob/d6ebeefcba90387b42817f8e87792e630d5862eb/research/design_candidates/production_design_20261102/f01/JOINT_SHELL_SYSTEM_CONTRACT.md): PARTIAL/RIG draft; no released v1 |
| Terminal source | [Inspected Terminal commit `3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/tree/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9): actual host, chart and selection owners |
| Widget source | [Macro widget at `fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9`](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/mm_brain.js): actual public methods and conditional focus hook |
| Existing D06 requirements | [Product specification at the prior D06 freeze](https://github.com/mastermindx-market-intelligence/macro/blob/217477f80a405af56778563535e5314813897b49/research/design_candidates/production_design_20261102/d06/PRODUCT_UX_SPEC.md) and [interaction states](https://github.com/mastermindx-market-intelligence/macro/blob/217477f80a405af56778563535e5314813897b49/research/design_candidates/production_design_20261102/d06/INTERACTION_STATES.md): chart-first layout, distinct reader/AI selection, one Brain, explicit owner-bound changes |

At the separate source drift check on 3 November 2026, 01:59 America/Chicago, relevant Terminal lifecycle files were unchanged at master `c8a1d0e23255c2d5374258b52197bdf1aed85b27`. Macro `templates/mm_brain.js` and `site/mm_brain.js` were unchanged at main `00438de71e1d67e051d5e2f3938ef49762ecbe97`; both retained blob `e4d7bd63261c4065d720430589377ff0a7f758f8`. These later heads are drift observations, not replacements for the immutable programme inputs.

## 2. What the existing implementation supplies

| Surface | Actual behavior | Limit of the evidence |
| --- | --- | --- |
| Widget public methods | Macro exports `open`, `close`, `toggle`, `explain`, `setPrincipal`, `expand` and `mounted:true`. | The methods exist in inspected source. Their presence does not attest the external asset currently served to beta. |
| Terminal type | `MastermindBrainHost.MMBrain` declares optional `open`, `mounted` and `setPrincipal`. | It omits other implemented methods. Do not describe `close` as invented or already qualified in this type. |
| Terminal entry | Header uses actual `toggle`; navigation/Ask uses `open`. `mm:copilot` and `?ai=1` reuse the existing opener and one 800ms late-script retry. | Invocation and retry are not a visible-open acknowledgement. `openMastermindBrainForSymbol` returning true means it found and invoked `open`, not that rendering/focus completed. |
| Open mechanics | Widget sets panel/scrim open classes, refreshes context, restores existing draft/run and schedules focus after 260ms. Settled focus chooses a visible composer, sign-in action or another visible panel control. | An immediate post-click focus observation can precede the delayed focus transfer. Opening is not a prompt submission. |
| Close mechanics | Widget hides the panel, stops voice, cancels presentation animation and releases its presentation classes. | Closing does **not** cancel an answer or stream. Conversation/request outcome remains with the Brain owner. |
| Existing focus hook | `MM_BRAIN_CFG.onClose()` may restore the invoking object and return `true` to suppress launcher fallback. | It is called only when focus was inside the widget before closing. It is a conditional focus-return hook, not an unconditional close notification. |
| Terminal hook integration | `BrainWidget` does not expose or bind `onClose` in its props/config. | Exact Terminal invoker focus return is not established by the existence of the Macro hook. |
| Installation readiness | The widget exports `mounted:true` and dispatches `mm-brain-ready` after boot. | Neither reports open/closed visibility. No reliable open/close acknowledgement or visibility getter was found in the inspected contract. |
| Escape precedence | Source order is slash palette → context inspector → streaming stop → search close → panel close. | Escape is state-dependent; it must not be advertised as universally closing the panel or cancelling the request. |

Sources: [typed bridge](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/mastermindBrain.ts), [BrainWidget](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/BrainWidget.tsx), [TerminalShell](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/TerminalShell.tsx), [actual widget](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/mm_brain.js).

Terminal loads the external URL `https://www.mastermind-x.com/mm_brain.js`. A Terminal source/build SHA cannot by itself identify that separately served asset. The continuation has not attested its served bytes or release identity. Preserve this boundary when comparing source behavior with live evidence.

## 3. Actual live observation and discrepancy

The approved D06 browser continuation inspected the guest Terminal at 1363×936. These observations establish only the exercised presentation path; no prompt, pin, save or authentication action was performed.

| Exercised path | Observed result | Interpretation |
| --- | --- | --- |
| Open Brain with historical Chart Context selected | Reader showed 2026-10-27; its resized 460px width and scroll position177 remained while Brain overlaid it. | Evidence suspension/width release proposed by F01 is not current observed Terminal behavior. Terminal remains its own focused composition. |
| Settled open | Focus reached the Brain textarea. | Asynchronous entry focus observed on this guest path. No claim about all access classes or sign-in-gate variants. |
| Inspect “What the Brain used” | Disclosure showed Active chart AAPL; no visible selected-bar/timeframe acknowledgement. | Symbol acknowledgement is not exact historical-bar attachment proof. |
| First Escape with context inspector open | Inspector closed; focus stayed on its chip. | Nested dismissal was observed. |
| Second Escape | Brain did not close in the exercised path. | Bounded discrepancy with the inspected nominal Escape chain. Served asset and action path need qualification; no universal failure claim follows from this observation. |
| Visible Close control | Brain disappeared from the accessibility tree; focus became BODY. | Exact invoking Mastermind AI control did not regain focus on this path. |
| Panel accessibility inspection | Main root/panel had no `role`/`aria-modal`; no background `inert` attributes were observed. | Main-modal semantics are unqualified. A scrim and the separate context inspector's dialog markup do not prove full modal behavior. |

The observations are attributed to the [live baseline audit](LIVE_BASELINE_AUDIT.md) and its hashed capture set. They are not runtime tests of the proposed shell arbitration. Do not erase the Escape discrepancy because source appears correct, or claim the source version was served without a release/asset receipt.

## 4. Proposed owner-bound arbitration

D06 recommends retaining F01 candidate.3's aim: one blocking focus owner and sufficient space for the primary analytical object. **The following transitions remain proposed.** They become implementable only through qualified existing Brain/domain interfaces; this document does not name a new event, callback, polling loop or coordinator.

| Starting state and user intent | Required candidate behavior | State and owner boundary |
| --- | --- | --- |
| Shared-shell evidence is visible; user invokes Ask | Suspend evidence presentation, release its dock width or modal focus/scroll ownership, then open the existing Brain through its existing entry path. | Preserve the exact domain entity/field/period and current view in its incumbent in-memory owner. Generic Ask uses ambient context; exact-source Ask requires the domain's already-qualified attachment. |
| Brain is open; user wants evidence or another shell modal | Complete closure through the Brain's own visible control and a qualified owner lifecycle before opening another blocking surface. | Do not unmount the singleton, infer cancellation, inspect private state or use an invented close acknowledgement. Existing public `close` source does not by itself qualify programmatic arbitration. |
| Brain visibly closes after evidence suspension | Restore focus to the connected invoking Ask/source control, or an appropriate logical heading if it no longer exists. Keep the selected evidence reachable through its normal trigger. | No automatic evidence reopening or main-content shrink. Do not steal focus if the user deliberately moved it elsewhere during closure. |
| Evidence is explicitly reopened | Re-measure its applicable placement and restore the same still-valid identity and scroll through the domain owner. | A symbol, field, period, source generation or access change can invalidate prior selection; surface the current truthful state instead of stale attachment. |
| Focused `/terminal` | Keep its existing focused chrome, chart owner and single Brain. Any adoption of evidence suspension is a separately qualified D06/Brain integration change. | F01's 320px shared inspector does not replace the source 360px Terminal reader or its 300–520 clamp. Do not wrap Terminal in the full AppShell or destroy the chart to change presentation. |
| A request or save is pending | Let its existing owner govern continuation, cancellation and confirmed outcome. | Closing an overlay is not a save, rollback or cancellation receipt. |

The existing [Macro ontology host](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/ontology.js) demonstrates the real `onClose` focus seam: checks that the invoking DOM object remains connected, restores focus/scroll and returns whether focus was restored. Reuse the supported seam only after owner qualification. Its domain-specific clearing of selected ontology references must not be copied into Terminal; Terminal retains chart/reader identity according to its own contract.

## 5. Historical selection remains an explicit integration gap

`ChartPanel.inspectVisualTime` updates `visualSelectedTimeRef` and the visual reader; it does not update `TerminalShell.lockedVLine`. AI context revision and chart readout/native-observation binding use the existing locked-bar/replay path. The `ai_context_client.v1` ambient block carries symbol/timeframe/page/panel, not a standalone selected-bar payload. Sources: [ChartPanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/ChartPanel.tsx), [TerminalShell](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/TerminalShell.tsx), [AI context provider](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/aiContext.ts).

Therefore “Ask about this bar” remains a proposed explicit bridge under D14/Terminal ownership. Before dispatch, the UI must acknowledge the exact instrument, interval, selected bar/time basis and still-current generation through the existing readout owner. A changed selection makes the old request context stale; no current quote or alternate bar may silently substitute. This supplements, and does not replace, D06's existing HIST01 requirement.

## 6. Ownership and migration qualification matrix

These are qualification facets, **specified rather than executed**. The live subset above is separately identified. They map to BRAIN01, HIST01, LAY02/LAY06, NAV08 and A11Y01–03 in the 71-case migration ledger; this matrix adds no separate case IDs.

| Qualification case | Existing owner(s) | Required proof / preserved boundary |
| --- | --- | --- |
| Public API and asset identity | D14 / existing Macro Brain widget owner; Terminal integration owner | Bind the actual served widget asset to its supported public methods and hooks. Preserve source-versus-served discrepancies. No claim that readiness equals visibility. |
| Open from evidence; delayed script; rapid close | Brain owner; F01 shell integration; D06 focused integration | One singleton; one intended entry; no late callback steals focus or opens after closure/navigation. Confirm evidence width/focus release only where that policy is adopted. |
| Close by control, toggle and scrim | Brain owner; invoking domain owner | Exact connected invoker or logical fallback; no forced focus theft when focus was elsewhere. Conditional `onClose` is not treated as unconditional notification. |
| Nested Escape and keyboard traversal | Brain owner; F02 accessibility; QA01 | Verify each actual priority state, including source/live second-Escape discrepancy. One blocking focus owner; no hidden focused element or background shortcut activation. |
| Pending stream versus hidden panel | Brain request owner / D14 | Visible close preserves the request as defined by that owner; explicit Stop remains distinct. No source write or cancellation inferred from hiding. |
| Reader resume and resize | D06 / Terminal chart and reader owners | Retain exact bar, active pane, logical range and reader scroll; explicit reopen re-measures current space. No unsolicited dock reopening or duplicate inspector. |
| Historical-bar Ask | D14; Terminal selection/readout owners | Extend HIST01: exact symbol/TF/bar/time basis/generation acknowledgement; reader-local and locked-bar state reconciled explicitly; stale results withheld. |
| Client navigation and owner/auth transition | Existing Brain host; D07 route identity; auth owner | No second script/assistant, dead getter, previous-owner context or private state import. Host callbacks bind/unbind with their existing ownership fences. |
| Focused/native shell variants | D06; F01 integration; native owner | Extend NAV08: ordinary Terminal, `shell=app`, tray/dossier boundaries retain their existing meaning; shared inspector widths never silently replace chart-owned geometry. |
| Responsive and assistive behavior | F01/F02; D06; Brain owner; QA01 | Qualify dock/modal transitions, narrow/zoomed layouts, reduced motion, EN/ZH, virtual keyboard and visible close/focus at actual content widths. Guest desktop evidence alone does not pass these cases. |

## 7. Acceptance and next evidence

The source interface has been inspected and the exercised guest presentation recorded. Cross-layer arbitration, selected-bar attachment, complete modal accessibility and exact close focus return remain unqualified. F01/F02 foundation release and independent design qualification remain separate outstanding gates.

For the design phase, existing owners qualify the supported lifecycle and context boundaries, F01/F02 freeze and qualify the joint foundation, and D06 obtains exact authoring admission before composing and independently reviewing the affected editable references. The migration cases remain specified. Their implementation-level execution belongs to a later separately authorized build; baseline cases that can be exercised now remain separately attributed observations. A source comment, candidate document, advisory consultation or Paper capability receipt cannot satisfy those gates.

No production implementation, Paper mutation, external approval, merge, Ready transition, enqueue, relabel or deployment is claimed or authorized by this document.
