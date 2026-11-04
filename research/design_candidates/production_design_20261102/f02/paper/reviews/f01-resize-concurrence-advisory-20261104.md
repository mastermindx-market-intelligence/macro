# F02 C3 advisory — F01 passive resize proposal

**2026-11-04 · Source-contract advisory only.** This is independent C3 advice to the F02 assignment owner, not owner concurrence, formal RIG, native acceptance, implementation review or permission to release. No Paper or repository source was changed.

## Exact inputs

F01 head: `abfecf1efc452383fe720cb3ea2016ad8d7088e0`. Locally verified Git blobs:

| Input | Blob |
| --- | --- |
| `F01-RESIZE-FOCUS/0.1` proposal | `c5fcb502746843d10ce422ce3c1e35fcc1112a7f` |
| Current joint contract | `653d93bbce70a2515d677ecdb76bb21edfab750c` |
| Interaction conformance | `36271d036bf520e662a2723d976141003ec67dc2` |
| F02 `SYSTEM_CONTRACT.md` | `1310877964805e6e356a6e050472754dae6deb8b` |
| F02 `INTERACTION_STATES.md` | `3d90cbd4e3b95513e54e46c36632b55dbd31192c` |
| F02 `F01_HANDSHAKE_CANDIDATE.md` | `2e8f70171156ba30c6bc5cc6c3f7d56b0be7cdbf` |

## Disposition

**Recommend F02 concur with the two focus-dependent branches as a proposal for a new joint candidate.** No incompatible F02 component role was found. Existing candidate.2 geometry and candidate.4 policy remain operative pending affected-owner responses and explicit version adoption.

| Pretransition ownership | Proposed response | Reason |
| --- | --- | --- |
| Inspector legitimately owns focus | Adapt the single inspector to modal; retain valid identity, disclosure, scroll and logical control | Modal containment and inertness are compatible with retained inspector focus. |
| User deliberately moved focus to the primary task | Suspend evidence presentation, release its width, retain selection/return anchor and expose explicit reopen | Immediately making that task inert cannot preserve its deliberate focus. |

Growth after suspension must not reopen evidence. Explicit reopen revalidates identity, source generation and access before selecting eligible presentation. Modal-to-dock adaptation releases containment/inertness while retaining valid inspector focus. These are proposed behavioral changes, not proof of existing behavior.

## Component constraints and unresolved arbitration

1. Capture legitimate ownership **before** detach, hiding or inertness. BODY afterward is not evidence of intentional departure. Unknown ownership and another modal remain separate cases under the existing owner; do not coerce either into the primary-focus branch.
2. Preserve one inspector/state owner. No overlapping modal/dock, second store, event bus or lifecycle. Owned-focus adaptation retains the logical inspector control; use its named visible, enabled, connected in-inspector fallback if necessary. Returning to the outside trigger during this adaptation would immediately conflict with modal inertness.
3. Suspension leaves no hidden focus, trap, background inertness or residual width reservation. The existing EvidenceTrigger must expose a reachable, context-named reopen action, including EN/ZH and narrow/touch operation. A removed row cannot substitute another row at the same index. Domains must qualify the surviving trigger or equivalent owner-bound recovery.
4. Revalidate exact entity/field/period, access and source generation on reopen and placement change, as candidate.4 already requires. Missing/changed/denied evidence receives the domain's truthful outcome. Selection retention is not authorization to show obsolete or restricted values.
5. Transitions must not cancel requests, confirm saves, reset navigation preference or create reader cursor state. D06's focused reader remains separate. Brain readiness, mounting or method returns are not visibility acknowledgments; conditional `onClose` is not an all-close event, and host success requires actual focus restoration. Old callbacks must not affect a newer surface or route.
6. “Hold ambiguous transition” cannot justify an obscured focused control, second modal or indefinitely ineligible dock. The existing owner must qualify that branch before adoption is represented as complete; concurrence with the two known-focus branches does not close it.

## Separate versioned clarification required

| Existing F02 text | Required clarification in the proposed successor |
| --- | --- |
| `SYSTEM_CONTRACT.md` §6: “Otherwise shared evidence is an overlay”; viewport examples | Geometry determines eligible open presentation. Passive dock loss with deliberate primary focus instead suspends until explicit reopen. Examples do not mandate automatic opening. |
| Component `EvidenceInspector` row: “Close/placement change restores the identity-based trigger”; §6 restoration wording | Separate closure/removal from same-inspector adaptation. Closure conditionally returns outside; owned-focus adaptation retains focus inside the inspector. |
| `INTERACTION_STATES.md`, “Focus, overlays and input details”: “do not silently close” | Explicit, recoverable presentation suspension preserves selection and is distinguishable from discarding evidence. Document the visible recovery and applicable announcement. |
| Handshake, “Responsive mode change” | Add the two branches, suspended-growth behavior and unknown-owner qualification as a proposed successor; preserve historical candidate.4 concurrence. |

## Falsifiers and review boundary

Add facets to existing N07/N10/N11/G07: inside-focus crossings both directions; primary-input focus then shrink; grow/oscillate while suspended; valid/invalidated/denied reopen; removed control/rapid resize/other modal; pending request/save. Reject stolen or detached focus, duplicated layers, lost input/scroll/identity, stale attachment, delayed reopen, preference mutation or false outcome. Include keyboard/assistive-technology, EN/ZH, dark/light, narrow/zoom and actual owner integration. Static screenshots and unit results do not qualify these paths.

Review [5760649569](https://github.com/mastermindx-market-intelligence/macro/pull/10645#pullrequestreview-5760649569) remains bound to review commit `3e334bd3eabf1d6ecc7980845fbd7a813dd023e1` and semantic `8926b16af4e0c3e5310cdb4cf057390ec04d18ff`, blob `1160f14b108bf0948384f59a249320385a1dfb6c`. Root's current comparison establishes only §§2–5 equality; §6 changed. Do not repeat whole-tail equality for `abfecf1`, extend that approval to this proposal/conformance/code, or erase earlier receipts. Obtain scoped affected-owner responses and independent review on immutable successor inputs. Original Paper effects, complete native set, Product/Taste, served Brain/host, consumer, QA01 and formal RIG gates remain unchanged.
