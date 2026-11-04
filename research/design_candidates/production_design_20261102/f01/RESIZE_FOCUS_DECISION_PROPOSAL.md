# F01 proposal — passive resize and evidence focus

**F01-RESIZE-FOCUS/0.1, 2026-11-04 UTC. Status: F02_PROPOSAL_CONCURRENCE_RECEIVED; NOT_ADOPTED.** F02 answered at [013fdd72](https://github.com/mastermindx-market-intelligence/macro/blob/013fdd72e6a387c6121df84082ce1e6c2201d336/research/design_candidates/production_design_20261102/f02/F01_RESIZE_FOCUS_RESPONSE.md), blob76ffd9adee60a87d74c2a2a78b72c9fcaf604eff. [Joint candidate.5](JOINT_SHELL_SYSTEM_CONTRACT_CANDIDATE5.md) carries the precise successor proposal, extra clarifications and remaining affected-owner decisions. The original decision text below is retained as the reviewed input; candidate.4 remains operative. Neither proposal implements an inspector or blocks the separate directory correction.

## Problem and proposed decision

A dock is nonmodal: a user can deliberately return to the primary page while evidence stays visible. If a passive resize then opens a modal, background inertness can hide that user's new focus or force an unrequested transfer. Preserving outside focus and immediately creating a blocking modal cannot both hold. This edge was previously underspecified.

**Proposed choice: suspend evidence presentation when a passive resize removes dock eligibility and focus has deliberately moved outside it.** Preserve the exact domain selection and return anchor, expose a visible Reopen evidence action through the existing trigger, and leave primary-task focus untouched. The same existing inspector owner decides presentation; no new global store, event bus, lifecycle or second inspector is proposed.

Observe legitimate focus ownership before removing, hiding or applying inertness. BODY after removal does not establish that the user intentionally left. When the inspector still owns focus, its single instance may transition to modal, preserving the valid object, disclosure state, scroll and logical control. Use the existing named in-inspector fallback if the original control is no longer available. Modal containment and background inertness then follow the qualified component contract.

| Trigger and ownership | Proposed result | Preserved context / constraint |
| --- | --- | --- |
| Passive resize removes dock eligibility; inspector owns focus | Convert the single inspector to modal | Same valid identity, disclosure, scroll and logical control; qualified trap/inertness |
| Passive resize removes dock eligibility; user deliberately focused primary page | Suspend evidence presentation; release reserved width | Preserve domain selection/return anchor and valid outside focus; visible explicit reopen; no hidden modal |
| Width grows while suspended | Remain suspended | No surprise reopening or focus transfer; never auto-collapse/expand navigation |
| Explicit Reopen evidence | Revalidate identity, access and source generation, then choose eligible presentation | Existing domain owns stale/missing/denied outcomes; explicit invocation establishes opening intent |
| Open modal becomes dock eligible | Convert the same inspector to nonmodal | Release trap/inertness while retaining valid inspector focus/context |
| Another modal owns focus or ownership cannot be established | Apply existing shared-layer arbitration; hold this ambiguous automatic transition | No second modal and no inference of Brain closure from readiness, mounting or a method return |

Dock geometry remains the candidate.4 measured-width rule:320px evidence plus24px gap, at least640px primary or the domain's larger qualified minimum. Suspension changes presentation only. It does not cancel requests, confirm a save, alter a selected source object or reset an explicit navigation preference.

## Discriminating cases, using the existing acceptance ledger

Add these facets to N07/N10/N11/G07 without marking a complete programme case passed:

1. Focus inside dock; cross eligibility in both directions. Assert one inspector, exact identity, scroll/disclosure retention, legitimate focus and correct trap/inertness.
2. Focus a primary input after using dock; shrink. Assert no blocking modal, no focus theft, preserved input/selection/scroll and reachable reopen.
3. Grow and oscillate around the boundary after suspension. Assert no automatic reopening or preference mutation.
4. Explicitly reopen with valid, invalidated and access-denied evidence. Record exact source generation and the domain-owned outcome separately.
5. Remove the original control, resize rapidly or open another modal. Inspect ownership before transition; reject detached focus, duplicated layers and delayed surprise openings.
6. Keep a pending request/save during presentation changes. Verify the existing owner retains its request identity and outcome semantics.

F01 owns the policy/composition and visible reopen affordance. F02 qualifies component anatomy and modal/nonmodal accessibility. Adopting domains, including D07/D08, qualify identity and retained task context. D06's focused Terminal reader remains a separate exception. Brain/D14 and the existing host retain their lifecycle and request duties.

## Exact decision requested and version treatment

The original F02 question is answered by the exact response above. The successor request is now candidate.5's bounded delta and named trigger/fallback/arbitration decisions, not a duplicate request for candidate.4 or the same two-branch position. Adopting domains must identify their existing selected-object/trigger contract and any inability to preserve/reopen the same evidence.

Keep candidate.4 operative until the affected owners respond. If adopted, publish the changed transition as a new joint candidate with its exact change list and scoped responses. Neither an F01 proposal nor a coordination comment is reciprocal concurrence, independent review, implementation proof or release. The remaining Paper effects and complete-set gates are unchanged.
