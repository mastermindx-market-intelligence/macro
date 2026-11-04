# Joint F01/F02 shell-system contract — candidate.5

**Version: F01-F02-SHELL/1.0.0-candidate.5. Status: PROPOSED_NOT_ADOPTED.** This is the complete bounded amendment to candidate.4's shared-evidence presentation rules. Candidate.4 remains the operative provisional specification; it is not a released foundation. F01 is the composing author. F02 has concurred with the two focus-dependent branches **as a proposal**, not with every additional clarification below. No runtime, native, product, independent qualification or release acceptance is asserted.

## 1. Exact source, precedence and ownership

| Input | Immutable identity and meaning |
| --- | --- |
| Programme authority | All five assignment/common/index/shell/checklist documents at Macro `6e1862867193ec6486a22001a0e4fb515da20448` |
| Operative predecessor | [candidate.4 at abfecf1](https://github.com/mastermindx-market-intelligence/macro/blob/abfecf1efc452383fe720cb3ea2016ad8d7088e0/research/design_candidates/production_design_20261102/f01/JOINT_SHELL_SYSTEM_CONTRACT.md), whole-file Git blob `653d93bbce70a2515d677ecdb76bb21edfab750c` |
| Preserved policy | Predecessor §§2–5: 14,315 UTF-8 bytes, SHA-256 `c887ab7c2ab9055410ee57fb5a30763b35f509ce3f3a86b6c7a8c1356c982c6e`, equal to semantic freeze `8926b16af4e0c3e5310cdb4cf057390ec04d18ff`. This amendment changes only the proposed shared-inspector transition interpretation in §4.1; it imports all other geometry, slots, focused-reader, route and return clauses unchanged. |
| Reviewed proposal | [F01-RESIZE-FOCUS/0.1 at abfecf1](https://github.com/mastermindx-market-intelligence/macro/blob/abfecf1efc452383fe720cb3ea2016ad8d7088e0/research/design_candidates/production_design_20261102/f01/RESIZE_FOCUS_DECISION_PROPOSAL.md), blob `c5fcb502746843d10ce422ce3c1e35fcc1112a7f` |
| F02 actual owner response | [F01_RESIZE_FOCUS_RESPONSE.md at 013fdd72](https://github.com/mastermindx-market-intelligence/macro/blob/013fdd72e6a387c6121df84082ce1e6c2201d336/research/design_candidates/production_design_20261102/f02/F01_RESIZE_FOCUS_RESPONSE.md), blob `76ffd9adee60a87d74c2a2a78b72c9fcaf604eff`; [owner comment 6621051326](https://github.com/mastermindx-market-intelligence/macro/pull/10645#issuecomment-6621051326) |
| Historical independent source review | [5760649569](https://github.com/mastermindx-market-intelligence/macro/pull/10645#pullrequestreview-5760649569) is bound to reviewed head `3e334bd3eabf1d6ecc7980845fbd7a813dd023e1`. It does not review or approve candidate.5. |

F01 owns composition, shared-layer policy and the visible shell recovery affordance. F02 owns shared component anatomy, accessibility, density and tokens. Adopting domains own selected-object identity, generation, data/access outcomes and task context. D06 retains its focused Terminal reader; Brain/D14 and its existing host retain visible lifecycle, requests, conditional callbacks and cancellation. No new route registry, event bus, global focus store, modal service, API, persistence key or request owner is proposed.

The source-authoring home remains [F01 Draft #10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645); [F02 Draft #10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630) remains with its existing author. F01 does not edit F02's branch or boards. This amendment does not reopen accepted historical work or clear either author's original uncertain Paper effects.

## 2. Purpose and completion ruler

A dock is nonmodal. A user can return to a primary input while evidence remains open. A passive width change must not turn that voluntary primary task into an inert background or discard the evidence they selected. Conversely, a user actively reading evidence must retain a visible, usable inspector when a dock no longer fits.

The proposed behavior is complete only when the same evidence remains correctly identified, one presentation owns input, the active task retains its meaningful focus and context, recovery is explicit, and pending domain work retains its original identity and outcome. A valid DOM focus reference alone is insufficient: the focused control must be visible inside its scroll viewport.

**DONE_WHEN for adoption:** the exact candidate delta receives the required affected-owner interface responses; actual trigger/fallback/arbitration bindings below are resolved; representative native states and the mapped product cases are qualified against exact implementation source. Source concurrence, implementation, independent qualification and release remain distinct. The current Web review waiver removes optional review ceremony; it does not substitute for another owner's unresolved interface or a binding formal approval/release hold.

## 3. Measurement and focus inputs

### 3.1 Measure the available container before evidence reservation

Use actual CSS pixels after navigation, gutters, safe-area treatment and other reserved local chrome, **before** subtracting evidence width:

`dock eligible = available primary-plus-evidence width >= domain primary minimum + 320 + 24`

The shared primary minimum is 640px; a larger domain-qualified minimum governs. Candidate.2's continuous 600/860/1200 inequalities and candidate.4's calculated 1256px expanded / 1096px compact examples are unchanged. Measure the resulting container, not a device label or a second subtraction from the already narrowed primary pane. A two-pass feedback loop that alternates dock/modal is a failure. Evidence must never silently rewrite the user's explicit compact/expanded preference.

This shared equation does not govern D06's focused reader: its existing 360px initial width, requested 300–520px clamp, `mm.railW` owner and actual price-plot fit remain separate.

### 3.2 Establish ownership before changing presentation

Immediately before hide, detach, reparent, inertness or modal-placement changes, the existing inspector/host captures the applicable logical focus control, selected identity and source generation, disclosure, task return anchor and local scroll. These are transient transition inputs in the incumbent owner, not new persisted state.

| Classification | Required evidence | Invalid shortcut |
| --- | --- | --- |
| Inspector owns focus | A valid control belonging to this presented inspector owns focus under the existing host boundary | Assuming any last remembered control is still the owner |
| Primary task deliberately owns focus | A valid primary-task target was deliberately established after using the inspector | Treating every target outside the inspector as primary intent |
| Another modal owns focus | Existing layer owner establishes its active modal/confirmation | Inferring visibility from mount, readiness, method return or a conditional callback |
| Unknown | Ownership cannot be established, including browser focus loss or removal before the snapshot | Using BODY/HTML, null blur destination or post-detach focus loss as deliberate primary focus |

Portal and embedded-surface ownership must come from the existing host contract. Do not inspect private cross-origin state or invent another focus coordinator. Capture must precede layout mutation; later BODY focus cannot reconstruct user intent.

Recheck ownership and the current presentation intent immediately before applying a deferred transition. An established competing modal or confirmation owns input even when its content is inside the inspector's DOM subtree. If the captured ownership or intent no longer applies, do not commit its focus, inertness or resource changes; use the existing owner's qualified arbitration outcome. A previously captured inspector target does not authorize acting on a later layer.

## 4. Proposed transition contract

| Event and established ownership | Proposed presentation outcome | Preserved context and resource duty |
| --- | --- | --- |
| Open dock loses eligibility; inspector owns focus | Adapt the same inspector to modal | Same valid identity, source generation, disclosure and logical control. If that control disappeared, use the domain's named in-inspector fallback. Establish exactly one trap, background inertness, scroll-lock owner and active Escape owner coherently. |
| Open dock loses eligibility; user deliberately focused the primary task | Suspend inspector **presentation** and release reserved width | Preserve primary focus, input value/selection and task anchor. Retain evidence selection and return anchor. Expose visible explicit Reopen evidence through the existing qualified recovery control. No hidden modal or focused hidden control. |
| Width grows or oscillates while suspended | Remain suspended | Selection is not an automatic-open instruction. No unsolicited reopening, focus transfer or navigation-preference change. |
| User explicitly invokes Reopen evidence | Revalidate exact identity, access and source generation, then choose the currently eligible presentation | Reopen the same valid object or show its existing domain-owned changed/missing/denied state. Never substitute by row position or silently select a different object. |
| Open modal becomes dock eligible and still owns the presentation intent | Adapt the same inspector to nonmodal | Retain logical control, identity, disclosure and usable scroll context. Release only that inspector's modal trap/inertness/scroll lock. Placement change does not restore the outside trigger. |
| Another modal owns focus, or ownership is unknown | Use only an already qualified existing-owner arbitration outcome | This automatic path is **not implementation-qualified** by candidate.5. No second modal, inferred Brain closure, hidden focus, stale callback or queued surprise reopening. See §7 before adoption. |
| User actually dismisses evidence | Apply existing dismissal semantics and conditional return | Restore an identity-based visible trigger/fallback only if the retiring inspector legitimately owns focus. Preserve a deliberate later focus owner. Dismissal does not itself settle a domain request. |

### 4.1 Adaptation is not dismissal

A native dialog `close` operation used to leave modal placement must not execute user-dismissal effects. It must not clear selection, return to an outside trigger, mark a request stopped or retire retained evidence intent. Keep one presented accessible inspector; framework movement/remount must preserve domain state in the existing owner and may not create another request/save lifecycle. No duplicate Escape handlers may act on the same event.

Adaptation must also preserve an active editable session while its logical control remains valid: current text, caret/selection and ongoing composition. A passive resize must not itself commit, cancel, duplicate or discard input. A gesture already owned by composition or the existing control must not become activation or dismissal in the new presentation. Preserving application-state text alone does not establish preservation of an OS composition session. An implementation that cannot preserve the session needs a qualified existing-owner outcome before this automatic path can be adopted; §7's prohibition on an indefinitely invalid-width dock still applies.

Qualification must observe focus and modal resources during the transition, not only after restoration. Whenever input can be delivered, its qualified owner must not leave focus in a hidden/inert control. Adaptation may release only its own trap, inertness and scroll lock, including when another owner becomes active during the transition.

### 4.2 Visible control, logical anchor, then compatible raw scroll

Preserve local scroll where possible. If height shrink, zoom or reflow would hide the retained logical control, make the minimum necessary adjustment in the inspector's own scroll container. Do not reset the primary task to the top. Record logical-anchor preservation and raw offsets separately. Exact raw offset cannot take precedence over visible, reachable focus.

Resolve the retained control by logical identity in the current presentation, including its selected object where applicable. Connectivity alone is insufficient: a node that is hidden, inert, disabled or bound to a different logical control/object is not a valid target. Inspector-owned adaptation uses the named in-inspector fallback when the control is invalid. If responsive reflow invalidates primary-task focus during suspension, its existing task owner must supply a named primary-task fallback; do not move focus into evidence or report BODY as preserved focus. Retain the task's input state through its existing owner. An unbound fallback leaves that transition unqualified under §7.

This precedence is an F01 clarification for candidate.5; the earlier F02 response did not independently qualify it. A primary input's caret/selection remains protected in the deliberate-primary branch. Composition/remount handling requires real input-path proof; synthetic composition flags alone do not qualify OS IME behavior.

### 4.3 Reopen is an explicit, current intent

If identity/access validation is asynchronous, its completion may present evidence only while the same explicit reopen intent, route, owner and retained evidence selection remain current. The binding must distinguish selection replacement from equality of object IDs: after A→B→A, a retired completion for the first A stays retired. The incumbent domain's selection contract determines which changes replace retained evidence; primary focus or an unrelated cursor is not a substitute.

Before applying the result, the existing owner verifies that its source/access validation context remains applicable under domain semantics; otherwise it revalidates or presents the existing changed/stale/denied outcome. This does not prescribe a universal generation-equality rule or a new selection store.

A later evidence dismissal, navigation, replacing selection or competing presentation request accepted by the existing host retires the pending reopen intent. Acceptance of a competing request does not acknowledge visibility or closure; failure of that request does not automatically revive the retired reopen. An unresolved acceptance/arbitration binding remains held under §7. Retiring presentation intent does not itself cancel the underlying request.

Loading, stale, changed, missing, denied and error states retain the incumbent domain's semantics and source clock. The shell must not call stale content fresh, retry a denied action, replace unknown access with a premium/public claim, or invent an API to support the presentation.

### 4.4 Presentation does not settle mutations or historical context

Resize, suspension, modal closure and width recovery do not mean Stop, Saved, rollback, deletion or completion. Existing save/answer/dirty-confirmation owners decide those outcomes. Preserve already-dispatched historical Ask identity; a later selection/resize must not retarget it. Revalidate a prepared attachment through its existing owner when its context changes. Brain Close and Stop remain distinct; its conditional `onClose` is not proof of every close path.

## 5. Reopen anatomy and accessibility binding

Each adopting domain must name the actual persistent recovery affordance, including when the source row is virtualized, filtered out or replaced. The contract requires:

- A visible existing trigger or named persistent fallback, with accessible name identifying evidence and its retained object. It cannot rely on the original row index.
- A 44px house target and visible keyboard focus; EN/ZH names through the existing localization owner. Theme changes retain identity and presentation intent.
- A named, visible in-inspector fallback when the original logical control becomes ineligible under §4.2; return outside the inspector is not the adaptation fallback.
- Where responsive reflow can invalidate primary-task focus, a named fallback in that task through its existing owner. Its absence does not authorize focus transfer into evidence.
- An explicit changed/missing/denied outcome when the object no longer validates, without silently opening a neighboring row.
- Keyboard and touch access once the owning modal permits background interaction. A recovery control behind another active modal is correctly inert and cannot be claimed as currently reachable.

The generic copy candidate is **Reopen evidence / 重新打开证据**. This is proposed anatomy/copy, not a translation release or a new universal button inserted by this document. F02 and adopting domains bind the actual wording and location before implementation.

## 6. Qualification facets in the existing ledger

All facets below are **NOT_RUN**. They refine existing N07/N10/N11/G07, not additional programme IDs or a second test registry. The complete programme remains 86 specifications; narrow directory tests cannot mark these inspector cases passed.

| Existing case | Setup and required observation | Falsifier |
| --- | --- | --- |
| N07 | Deep inspector control focused; cross dock eligibility in both directions, then dismiss deliberately | Adaptation returns outside, loses logical control, duplicates inspector or leaves focused control clipped |
| N07 | Focus primary input with selected text after using dock; shrink | Modal/inertness steals focus, caret/value changes, or absence of DOM containment alone is used to infer intent |
| N07 | Remove, hide, inert, disable or rebind the retained inspector control during transition | Connectivity alone selects an invalid target, BODY chooses the primary branch, or the named inside fallback is not used |
| N07/G07 | Responsive reflow invalidates the focused primary input during suspension | Focus enters evidence, BODY is reported as preserved focus, or the primary-task fallback is unnamed or ineligible |
| N07/N11/G07 | Real IME composition inside the inspector across both dock/modal directions and in the primary input during suspension; include Enter/Escape, held-key repeat and software-keyboard height changes | Resize commits/cancels composition, loses/duplicates text, changes selection without user intent, or transfers a gesture to another layer |
| N11 | Other modal or dirty confirmation active; resize below fit | Two modal owners, invalid-width dock retained indefinitely, wrong Escape owner, unlocked later modal or inferred cancellation/save |
| N11 | Rapid shrink/grow, close/reopen, identity change and delayed callback | An old callback focuses, reveals or releases resources belonging to a later intent |
| N11 | Capture inspector ownership, then admit another modal/confirmation before commit; also overlap competing accepted presentation requests before either is visible | Stale adaptation steals focus or changes a later owner's resources, competing layers both accept input, or a failed later request resurrects a retired reopen |
| N10/N11 | Delay reopen validation across A→B→A and across a relevant source/access context change with unchanged object ID | A retired selection intent becomes current by ID equality, or an obsolete validation verdict is applied without the incumbent domain's validity check or outcome |
| N10 | Pending historical Ask/save during suspension and adaptation | Request identity changes, hidden means Stop/Saved, or Brain close reopens evidence automatically |
| N10 | Explicit reopen after reorder/removal/access/generation change; delay validation then navigate/close | Reopens by index, silently substitutes identity, lies about access/freshness or resurrects a retired intent |
| N10/N11 | Suspend, grow and oscillate with original row absent | Surprise reopening or no named persistent recovery control |
| G07 | Cross fractional nav/gutter and actual domain fit thresholds in both directions | Double subtraction, dock/modal oscillation, primary minimum violation or explicit nav preference change |
| G07 | Shrink height, long ZH labels and zoom with focused control below fold | Exact raw scroll preservation hides focus, document resets to top or retained logical anchor is lost |
| N11/G07 | Browser focus loss, unknown owner, portal/embedded owner and competing-modal branches | Ambiguity silently classified as deliberate primary intent or an unqualified automatic path is shipped |

Each executed facet records exact source/build, before/after presentation, measured width and domain minimum, focus target **before mutation**, during the transition and after completion, evidence identity/generation and selection intent, validation context, relevant request identity, trap/inertness/scroll-lock owner, any fallback chosen, locale/theme/input path and limitations. Required coverage includes 1440×900, 820×1180, 390×844, 320px stress, both threshold directions, keyboard/touch, EN/ZH, light/dark, reduced motion and applicable 400% zoom. Representative cells must be named; a few screenshots do not cover every combination.

## 7. Open interface decisions and adoption gate

**Held means the automatic implementation path lacks qualification. It is not permission to render an invalid-width dock indefinitely.** Before adoption, the actual host must name a concrete safe outcome for unknown ownership and competing modal cases. A floating nonmodal overlay, new inline fourth mode or a timeout-based automatic reopen would be a further design change, not an implied fallback.

| Required response | Existing owner | Concrete answer needed |
| --- | --- | --- |
| Candidate.5 anatomy and resource semantics | F02 | Exact delta concurrence; visible-control/logical-anchor/offset precedence; adaptation distinct from dismissal; actual fallback anatomy; active editing-session preservation and transition focus/resource semantics |
| Shared-layer arbitration | F01 with existing host and Brain/D14 where affected | Outcome for proven other modal, browser focus loss, prior removal and unknown portal ownership; commit-time ownership and competing-request acceptance/supersession/failure behavior; no invalid-width dock, second modal or delayed surprise opening |
| Recovery and retained object | D07/D08 and each adopting domain | Actual persistent trigger, accessible name, eligible in-inspector fallback and primary-task fallback where applicable; retained-evidence selection replacement/repeated-identity semantics, source/access validation compatibility, exact identity/generation and changed/missing/denied behavior |
| Focused-reader boundary | D06 | Confirm any adoption is explicit and does not replace its independent width, price-plot/cursor/Ask requirements |
| Native and product qualification | Existing programme owners | Exact source, represented variants, real input paths and applicable formal QA/RIG disposition; no invented approval |

The existing F02 response satisfies the **proposal-level position on the two focus branches**. It does not satisfy these newly specified bindings, all affected-owner responses or acceptance. Safe independent directory implementation and unchanged candidate.4 consumption may proceed under their own authorization; they need not wait for this amendment.

## 8. Exact change list and F02 source changes on eventual adoption

| Delta from candidate.4 | Provenance / current concurrence |
| --- | --- |
| Pre-mutation ownership classification; inside-focus modal adaptation; deliberate-primary presentation suspension | Directly grounded in F02 response `013fdd72`; proposal-level concurrence |
| Remain suspended on width recovery; explicit identity/access/generation revalidation | Directly grounded in that response; no runtime proof |
| Separate adaptation from dismissal; release only own modal resources | F02 response grounds the distinction; concrete implementation still unqualified |
| Measure before inspector reservation; no oscillating subtraction | Clarifies unchanged geometry; actual measured implementation proof required |
| Visible-control → logical-anchor → compatible raw-offset precedence | Additional F01 clarification; F02/domain response pending |
| Persistent recovery binding and current-intent async validation | Additional F01 precision; actual domain/host binding pending |
| Unknown/other-modal path explicitly unqualified, never an indefinite invalid-width dock | Preserves F02's stated constraint; concrete existing-owner outcome pending |
| Active editable-session preservation and composition/gesture ownership during passive adaptation | Additional F01 clarification; F02/host response and real-input qualification pending |
| Commit-time ownership checks, repeated-identity/validation-context guards and accepted competing-request supersession | Additional F01 clarification; existing host/domain binding and affected-owner response pending |
| Retained-control eligibility, primary-task fallback and observation during transitions | Additional F01 clarification; F02/task-owner binding and qualification pending |

These additional clarifications do not replace the two proposed resize branches or extend the proposal concurrence already received from F02. Their exact affected-owner responses remain pending. Candidate.5 remains PROPOSED_NOT_ADOPTED; candidate.4 remains operative.

On adoption, F02 owns the four successor edits identified in its response: `SYSTEM_CONTRACT.md` §6 overlay rule; EvidenceInspector dismissal/adaptation distinction; `INTERACTION_STATES.md` recoverable presentation suspension; and `F01_HANDSHAKE_CANDIDATE.md` responsive-mode-change row. F01 will record their exact resulting source and owner responses. Until then, their accepted bytes and candidate.4 remain intact. No source comment, rendered board, JSX export, green test or merged unrelated PR releases candidate.5.
