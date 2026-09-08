# Neural Web dashboard — visual direction clarification

Date: 2026-09-08
Author: Sol
Status: Design proposal / concept brief. Not an approved final design, implemented UI, production proof, or worker commission.
Continuation: `research/NEURAL_WEB_DASHBOARD_ASSESSMENT_2026-09-08.md`
Existing operation: `committee-neural-web-dashboard-assessment-20260908-sol-001`
Carrier: the existing Macro proposal branch `claude/committee-neural-dashboard-assessment-20260908-sol-a1`. No replacement workstream, runtime job, or source branch is created.

## Chairman's clarification

The current live user message asks for a high-quality mockup, asks whether to make it here or in connected Figma, and asks whether the approved design can be carried through to working code by reusing Committee's neural web. The Chairman explicitly distinguishes the generated reference's advanced/science-fiction atmosphere from the existing graph's cleaner, more modern appearance. He does not say the generated graph is more beautiful.

The four supplied image references show two illustrative science-fiction treatments and two actual Committee graph states (curated and all nodes). Treat these as visual references, not live health or market evidence. Do not use machine-translated or nonsensical labels in the generated references as product vocabulary.

## Proposed direction

Retain the current graph's clean node-link language and make the surrounding workspace more composed, spacious, and useful. Borrow the reference's broad canvas and strong visual hierarchy, not its heavy star field, ubiquitous neon, fictional telemetry, or extreme edge density.

The intended character is a premium analytical workspace with modest luminous depth: graphite/navy surfaces, precise typography, fine separators, stable colored groups, subtle light on selected nodes, generous graph area, and restrained surrounding content. No constant spectacle is required to communicate a sophisticated intelligence system.

Initial concept: one wide desktop overview with the shared Mastermind navigation represented, compact Neural Web title and task views, a large map, narrow intelligence-area selector, one contextual evidence inspector, and a short lower research/context strip. Committee remains a visible first-class task. Use representative static content labeled as a concept rather than presenting fake current financial readings or uptime.

The layout should not repeat the same graph counts in multiple panels. Group colors distinguish subject areas; relationship semantics and market direction stay separate. Do not show agreement as automatically bullish or disagreement as automatically bearish. Do not represent worker activity, research execution, or data freshness without an actual owner-backed source.

## What stays versus what changes

Keep: existing canonical graph/source identities, data loading, node/edge semantics, canvas foundation, zoom/pan/fit/fullscreen concepts, curated/all-nodes capability, Committee evidence, and existing authentication/Brain boundaries.

Change at presentation level: content width and composition; true task views rather than long-scroll-only chapter navigation; label placement and visibility by zoom/selection; visual node hierarchy; edge opacity by relevance; selected-node inspector; graph fit and safe margins; named destinations for the existing deeper content.

The submitted screenshots motivate specific visual acceptance checks: no regime nodes unintentionally cut off at the top in the fitted state; no default-view pile-up of near-equal large nodes; no repeated small-node labels overwhelming all-nodes exploration; no clipping or ellipsis where a selected node's full name is needed. Grouping or label suppression must preserve identity, searchability, and access to every underlying record, not silently discard data.

These refinements require some JavaScript/layout work as well as CSS. They do not, by themselves, justify replacing the graph engine, adding 3D/WebGL, rebuilding the intelligence backend, or creating another data or chat system. Actual reuse boundaries require interaction tests and performance evidence in the source implementation.

## Design-to-code path

An image establishes art direction; it is not an executable component specification. Figma can hold editable layout/components and states when file permissions and tools permit. A browser prototype using the existing renderer is required to judge the real graph: labels, selection, resizing, zoom, dense data, performance, and reduced motion cannot be accepted from a still image.

Preferred order: concept reference, approval of the actual visual direction, editable component/state specification as useful, bounded implementation using the current Committee renderer, adversarial review, then authenticated production verification. Do not equate Figma export with production-ready integration.

No production UI changes or Figma design creation are asserted by this brief. The Figma account connection was confirmed in this session, but file-edit permission was not proven. An inaccessible optional guidance resource is not evidence that all Figma design operations are unavailable. Do not infer an edit denial merely from the returned View seat.

## Both-theme and interaction acceptance

The first concept may be dark desktop only. That is not the full design acceptance set. Before implementation acceptance, specify and inspect dark/light, English/Chinese, desktop/mobile, selected-node and all-nodes states, missing/stale/error states, keyboard/touch access, and the retained Committee journey.

Light direction remains a deliberate research workspace: white panels, cool canvas, dark precise labels, quiet cluster tints, and shadow instead of neon. Shared semantics, ordering, and actions must match dark mode.

End-to-end completion requires an authenticated user to open the real Committee route, explore actual graph evidence, enter the relevant Committee/desk view, and return without losing context. No promise of automatic deployment, uninterrupted unattended execution, or browser access is inferred from the ability to generate a mockup.

## Refreshed source evidence

Protected Mastermind Skillpack INDEX and COLD_START were reloaded at `2bf0266d5476c8e75dae4afa87cca67a8f12a838` (schema mastermind.sol_skillpack.v1, version 1.0.1, bootstrap major 1).

Macro main was read at `19cad7eaa11ffeeb73c081ff3de84696ae2ee4e6`. `templates/committee.html.j2` lines 666–705 were freshly read; the full file blob remains `418c5b2cacb6125e0b325b8ad363aff587948a23`, matching the earlier audit. That excerpt confirms the existing canvas, zoom/fit/all-nodes/fullscreen controls, tooltip, info card, and display/graded legend distinction. It is source evidence, not authenticated production proof.

The existing assessment file was read on the same proposal branch before this additive note. This records the design clarification without changing protected main, merging the proposal, or authorizing a build.

## Exact next step

Show the clean-modern desktop concept to the Chairman. A visual reference needs approval on actual appearance, not merely on the prior written architecture. On approval, turn the chosen look into an interaction/state packet and a first complete overview-to-Committee vertical using the actual renderer. Recheck current source collisions and all applicable execution gates before editing product code.
