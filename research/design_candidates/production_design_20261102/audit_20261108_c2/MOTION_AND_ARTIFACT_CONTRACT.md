# Illustration, motion and answer-artifact contract
Date: 2026-11-08 · Design audit supplement · WS:MARKET-OS
Status: **BUILD CONTRACT CANDIDATE**. Paper storyboards specify behavior; they are not runtime acceptance.

## Exact scope and owners
This supplements the existing MarketOntology Visual Engine reference `01M3P1X4FR6BRTB13KA736Y1HT / p-6-0 / 9T-0`. Preserve the adjacent R12 implementation map `13J-0`, the existing Brain host, gateway, permissions, threads, rendering families and history. Do not add a second renderer, chart planner, research runner or receipt store.
Protected law pin: Mastermind `5c3d3885234358aefb97ecdbc59be0864df14f8b`.
Macro source pin: `338a10852dcefa5d2bd07e5c6be0955c2b1e83fd`.
Current source references:
- [Design System §2.2, §7–8](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md)
- [Illustration contract](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/docs/ILLUSTRATIONS.md)
- [SSR renderer](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/lib/illus.py)
- [Reveal owner](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/illus.js) and [paired CSS](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/illus.css).

## Product intent
The reader should understand the observation before manipulating it. The glance view carries one takeaway, one useful visual, its unit/period and any limitation that changes interpretation. Detailed calculations, clock definitions, receipt IDs, coverage matrices and implementation explanations belong in the evidence layer or this build contract. A source receipt is evidence identity, never an access grant.

### Choose the visual by the question
| Reader question | Existing family / owner | Required meaning | Deliberately excluded |
|---|---|---|---|
| What changed? | Display series through `lib.illus.illus()` | Unit, period, zero/reference where meaningful, null gaps | Candle interaction, decorative fabricated trends |
| How does a change travel? | Existing relationships family / typed artifact proposal on 13J | Named channel, direction, evidence state, selected path | Inferred causal edges based only on correlation |
| What changes the result? | Existing scenario/calculation editor and chart family | Input revision, units, denominator, validated output | Results computed before confirmation; missing treated as zero |
| What supports this claim? | Existing source/value/calculation/absence receipt families | Exact authorized span or value; contradiction retained | A context selection presented as a citation |
| How do I explore price? | Existing Terminal charting stack | Its existing zoom, pan, crosshair, interval behavior | Extending ilx into a second trading chart |

## Storyboard A — reveal and settle
1. Reserve final chart dimensions before rendering. Text, axis meaning where applicable, date and material limitation remain readable.
2. A valid settled artifact enters using the current ilx owner. In-page charts reveal once; scrolling off-screen and back does not replay the animation.
3. The existing renderer keeps disconnected runs disconnected. A missing observation does not interpolate, connect, fill or become zero. Too little history produces the existing honest null state.
4. The end point settles. A static observation never pulses as if live. Loading or stream activity derives from the existing request state, not from a visual timer.
5. If the evidence revision changes or permission is withdrawn during motion, cancel the obsolete visual transition. Resolve the current authorized artifact through the existing owner, then render its final state or explicit unavailability. Animation completion never establishes analysis completion. Preserve focus when the selected mark survives; otherwise restore the section heading.
6. A dialog may replay its chart entrance on a subsequent open under the current `ilxReveal(dialogEl)` behavior. The fallback must not restart a chart already revealing.

### Timing ownership
New UI state transitions use Design System tokens: `--t-fast:.16s`, `--t-med:.2s`, `--t-slow:.55s`, `--ease-std` and `--ease-lift`. Tabs/toggles do not translate. Clickable-card lift remains 1–2px only.
The existing ilx implementation has separate inherited choreography (documented ~950ms ink draw, veil/settle/bar sequence). **This audit does not globally retime it.** Reconcile a future timing migration in the renderer owner and paired templates/site files, with affected consumers; do not override its animation per page.

## Storyboard B — inspect and return
1. When an admitted typed artifact supports inspection, selecting a mark identifies artifact revision + exact value reference + unit + period. Keyboard and touch reach the same information.
2. Open the existing evidence drawer/sheet; do not start research, change scope, submit the composer or overwrite a saved case.
3. Keep the selected mark visibly distinct using quiet fill plus a labeled focus treatment. Do not add colored container-edge stripes.
4. Show the exact-value/table alternative and authorized receipt; missing or denied support has its own explanation. A chart's decorative illustration layer is hidden from assistive technology when equivalent text already supplies its meaning.
5. Close/Escape returns focus to the invoking control and restores reading position. If that control is gone, use the nearest surviving section heading. Preserve draft, caret, scope and original answer.

Selected-mark follow-up is a **typed-artifact build proposal**, not an existing ilx capability. ilx itself has no hover tooltip, crosshair or zoom. Implement interaction in the existing host artifact family only after owner admission.

## Storyboard C — revise deliberately
| State | What the reader sees | Allowed action / invariant |
|---|---|---|
| Settled revision A | Original result and original evidence clock | Inspect; retain immutable saved revision |
| Inputs edited | Named changed assumptions; prior result labeled previous | Confirm Recalculate or Cancel; no silent request |
| Recalculating | Existing request status; previous result remains identifiable | Existing cancellation semantics; no duplicate job |
| Validated revision B | New values, explanation and table change together | Exact revision binding; comparison may retain A |
| Failed or incomplete | Previous result plus specific failure/unknown state | Retry only the failed operation under existing owner |
| Unknown write result | Pending reconciliation of original request ID | No blind second save/activation |

A result is publishable only when prose, visual, table and receipts agree on revision, unit, denominator and observation period. A newer quote alone never refreshes the assessment. An unverified calculation cannot animate into apparent certainty.

## Responsive and accessibility behavior
- Glance: one reading column; evidence opens temporarily. At 320/390px use the existing sheet pattern, never a permanent second column.
- Use 44px interaction targets, visible keyboard focus, a meaningful accessible name, long EN/ZH labels and 200% text reflow.
- `prefers-reduced-motion: reduce` renders final positions immediately and disables transitions, sweeps and animated pseudo-elements. Information and available actions remain identical.
- Coarse pointers get no breathing CTA or hover dependency. Focus and selected states remain distinct without relying only on color.
- No scroll hijacking, parallax, automatic carousel, auto-advance, or decorative oscillation.

## Build order
1. **Reuse / characterize:** bind the exact consuming route to its existing renderer and receipt owner; keep current behavior tests and record the source head.
2. **Artifact integrity:** add the admitted value/calculation/source/absence references through the existing Brain seam; reject unsupported families and invalid units.
3. **Read-only inspection:** one drawer/sheet, exact table parity and return-state preservation.
4. **Revision handling:** confirm recalculation, swap the validated artifact atomically, keep the old saved revision.
5. **Motion polish:** use existing ilx plus tokenized host transitions; no per-page renderer or observer.
6. **Consumer proof:** real route, real permitted artifact, failure/absence/permission paths, EN/ZH/theme/mobile/reduced motion. Screenshots alone do not close this.

## Acceptance examples
- A series containing [10, 12, null, 11, 14] preserves the absent slot visually and in its table; the line does not bridge it.
- An existing chart that leaves and re-enters the viewport remains settled; a reopened supported dialog follows the current replay rule without double reveal.
- Selecting a supported value and closing the evidence layer restores the invoking focus and unsent draft exactly.
- Editing an assumption does not alter the old saved result. Cancel changes nothing; confirmed recalculation creates a new matched revision.
- With reduced motion enabled, all content is present immediately and no pseudo-element continues sweeping.
- Unauthorized source content is absent from display, copy and export. An old receipt does not bypass permission checks.
- An incomplete or stale source cannot masquerade as zero, a neutral signal, a current assessment or a successful save.

## Audit verification boundary
The design addition and its node readback/screenshot are recorded in AUDIT.md and EFFECTS.json in this directory. No renderer modification, new analytical capability, monitor activation, production deployment or signed-in acceptance is claimed by this contract.
