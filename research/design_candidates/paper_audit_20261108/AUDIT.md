# Paper audit: clearer journeys and buildable contracts

**Date:** 8 November 2026  
**Operation:** paper-audit-clarity-20261108-c3  
**Scope:** actual Paper edits, source architecture comparison, feature viability, interaction reference, and implementation plans. This package does not deploy product code or accept a production programme.

## What changed

Before this pass, several current experiences mixed repeated introductory copy, ambiguous action labels, historical source descriptions, and feature promises whose implementation boundaries were hard to find. After this pass, five product files contain clearer navigation or actions, and their builder guidance distinguishes implemented source, design intent, and held capabilities.

The inventory covers **35 files and two folders**. Five files received edits: GMI Explorer, Mastermind OS, Mastermind AI, International Markets, and Terminal. The audit examined selected current journeys and builder boards in depth; it did not visually certify every artboard in the workspace. [INVENTORY.md](INVENTORY.md) records the disposition and inspection depth of every file.

### Open the edited Paper surfaces

| Surface | Exact home | Main change |
|---|---|---|
| GMI product | [Current product](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-1-0) | Four mobile theme/language variants reach evidence sooner; twelve navigation targets are 44 px high. |
| GMI interaction and source contract | [Foundations](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-4-0) | S04B explains evidence navigation, motion, exact return, and the actual missing relationship-selection binding. |
| Mastermind OS | [Canonical Atelier](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-D-0) | Today names the Terminal brief and asks the user to review its recipients. |
| Mastermind OS build sequence | [Daily Experience / Builder Notes](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-E-0) | New UX18 board maps existing owners to four journeys and installed-path acceptance. |
| Mastermind AI | [Chat workbench](https://app.paper.design/file/01M3P1QEHS5XXQY85BJT6QR2E1/p-1-0) | “Go deeper…” consistently opens the existing depth/usage confirmation. |
| International Markets | [Start here](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-1-0) | Directory distinguishes R10 core research, frozen R14 Global Surveillance, and reference studies. |
| Terminal | [D08C build contract](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-15-0) | Source/admission panel makes native Plan persistence and release prerequisites explicit. |

## 1. GMI: put the evidence closer to the user's question

### Actual canvas changes

On mobile boards **6DR-0, 6FY-0, 6PA-0 and 6R7-0**, the repeated generic introduction became a compact “GMI Explorer” heading. The topic description is now one direct sentence:

- English: “Memory stacking and advanced chip packaging.”
- Chinese: “高带宽内存堆叠与先进封装。”

The existing claim, source date, limitation, source action, and company → product → platform illustration remain. The customer still sees that the 26 February 2024 source supports a product connection and does not establish present shipments or revenue.

The three navigation items now have **44 px canvas bounds in all four variants**. The twelve exact target measurements are in [NODE_READBACK.json](NODE_READBACK.json). These are design measurements; the eventual DOM must still use appropriate links/buttons, visible focus, and full interactive hit areas.

The measured artboard heights changed from 1396/1411 to 1307/1322 px for the English variants, and from 1276/1291 to 1231/1246 px for the Chinese variants. That is an **89 px reduction in English and 45 px in Chinese**. The difference follows the existing localized line wrapping. This is a layout measurement, not a measured improvement in task completion time.

Dark retains quiet luminance depth and restrained borders. Light retains a cool canvas, white evidence card, hairline structure, and shadow. The improvement preserves those different material treatments instead of applying a single surface effect to both themes.

### Interaction and illustration

The added **S04B section 71U-0** on existing board **6T4-0** contains three editable stages:

1. Capture the current selection before opening evidence.
2. Reveal the ready evidence with a 200 ms opacity transition and at most 8 px movement.
3. Restore the original selection, scroll position, and triggering control on return.

Reduced motion renders the final state immediately. The historical relationship stays settled: no pulsing connection, count-up, or “live” implication. The relationship illustration explains company, named product, and named platform; it is not an estimated transmission model.

The accompanying [evidence-motion-reference.html](evidence-motion-reference.html) is a self-contained interactive design fixture. It demonstrates navigation and recovery without fetching data, saving research, running AI, changing access, or activating a monitor. Its access/error controls are explicitly simulated.

### Current source changes what should be built next

The current product path already exists:

- [scripts/build_gmi_explorer.py](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/scripts/build_gmi_explorer.py) generates the GMI pages and paired assets.
- [scripts/gmi_explorer/model.py](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/scripts/gmi_explorer/model.py) projects incumbent coverage, taxonomy, issuer identity, activity, and relationship artifacts.
- [templates/gmi.js](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/gmi.js) already owns the lens, local search, tree keyboard interaction, and category jumps.
- The shared GMI shell uses the existing site navigation and theme/language owner.

A material selection defect is visible in source. Issuer relationship links in [gmi_issuer.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/gmi_issuer.html.j2) go to bare gmi-relationships.html. The destination in [gmi_relationships.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/gmi_relationships.html.j2) selects model.edges[0]. A user can therefore ask for one issuer's relationship and receive the first package relationship. The rendered species buttons also lack a corresponding selection/filter handler in the inspected GMI script.

**Fix selection identity before adding motion.** Builder section **73G-0** now states the actual owners, defect, required issuer/edge/package binding, missing-selection behavior, and return-state gaps. The implementation must never silently replace a requested relationship with the first available record.

The older reference fixture is also not current product data. The pinned committed GMI map dated 8 November shows one micro-theme with an admitted company and zero held micro-themes; the earlier fixture shows the opposite. The current committed relationship page shows 248 documented relationships in a separately dated, proposed/unreviewed, display-only package. These are committed-source observations, not a new deployment or market-data verification. Keep the Paper Micron story as a dated example and populate current counts from the model. Sources: [current map](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/site/gmi.html), [current relationship page](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/site/gmi-relationships.html), and [older specimen specification](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/mockups/refs/gmi_explorer/SPECS.md).

## 2. Mastermind OS: name the decision and preserve existing execution owners

### Actual canvas changes

On desktop **LNV-0** and mobile **N27-0**, Today now says:

- **Review the Terminal brief**
- **Choose who can see this version.**
- **Review recipients**

The primary action names the decision the user is about to make. “Read brief” remains a separate action. Production must bind the actual artifact title and revision; the illustrative Terminal title is not a publication receipt.

Nine earlier design pages received REF labels, while current canonical pages remain in place. Six hidden mobile groups were named REF ONLY so extraction does not accidentally include old briefing, decision, progress, or source-coverage panels. The hidden node IDs are N4N-0, N4T-0, PNJ-0, N58-0, PM6-0 and N6Z-0. They were preserved, not deleted.

The new **UX18 board XGI-0** gives a compact implementation sequence:

- Create → Open → Start.
- Read → Draft → Send.
- Run → Result → Follow-up.
- Return → Access → Recover.

It specifies exact project identity, native owner reuse, operation reconciliation, current source presence, and the installed proof still owed.

### Architecture finding

The older five-route/read-only source description is not an adequate description of current OS source. At the protected pin, [App.tsx](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/App.tsx), the [OS README](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/README.md), [ProjectWorkspace](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/projects/ProjectWorkspace.tsx), and [compose-mission-host](https://github.com/mastermindx-market-intelligence/Mastermind/blob/5c3d3885234358aefb97ecdbc59be0864df14f8b/app/mastermind_os/src/compose-mission-host.ts) contain materially broader guarded project, execution, result, and native Send paths.

Keep the five primary destinations **Today, Projects, Inbox, Conversations, Knowledge** and the project tabs **Conversation, Overview, Plan, Work, Evidence, Journal, More**. Advanced capabilities belong in contextual disclosure, not another top-level navigation redesign.

The workspace consumes qualified owner slots. It must not become a second reader, sender, persistence layer, or admission system. Add-to-draft does not send. Creating a project does not start work. Opening a result does not accept it. A follow-up is a newly authorized run with its original parent witness, not a replay of an earlier root. The full contracts and proof cases are in [BUILD_PLAN.md](BUILD_PLAN.md).

## 3. Mastermind AI: clarify depth without changing the request boundary

Four visible actions—**5VC-0, 5VF-0, 5VI-0 and 5VL-0**—now read **“Go deeper…”**. The text measures 81 × 20 px inside the existing control. The action still opens the existing **67–68 depth/usage confirmation**. Only **Start research** confirms a request; opening, selecting depth, or cancelling must not spend quota, widen access, or run research.

Sources and Inputs & math remain separate evidence interfaces. “Go deeper” is not a shortcut to the Sources drawer.

The source comparison found a concrete context-receipt gap. [templates/mm_brain.js](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/mm_brain.js) handles context receipts and qualifies them by sent origin, request, and revision. The standalone streaming path in [templates/chat.html](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/templates/chat.html) has no equivalent context_receipt handler in its inspected event dispatcher.

The next build should reuse that contract and bind a receipt to the answer that used it. Selected context is not automatically a citation; an old answer must not rewrite the current context selection. Historical context can only be displayed as available when the actual history reader supplies it.

The existing “Save with monitoring off” hold remains. This audit did not requalify that runtime owner or authorize an active-save-then-archive workaround. Saving, monitor preview, and monitor activation need separate accepted receipts.

## 4. International: preserve two design scopes

The directory and page ordering now make the distinction explicit:

- **R10 core research:** pages 01–04B, with builder contracts on page 80.
- **R14 Global Surveillance:** a frozen design for IM13–IM18, governed by its written specification and amendments.
- **R12 Country Intelligence and R13 earlier expansion:** retained references.

R14 is not an obsolete study. The [R14 freeze decision](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/agentos/decisions/DEC-INTL-GS-R14-DESIGN-FREEZE.md) and [written specification](https://github.com/mastermindx-market-intelligence/macro/blob/338a10852dcefa5d2bd07e5c6be0955c2b1e83fd/research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md) settle that scope. The written contract and production tokens govern where a screenshot differs. This audit changes the directory, not the frozen artwork or its release gates.

China now points to **Intelligence Hub R4**. Returns points to **Terminal / Returns Calendar**. Neither points builders into the oversized monolithic file.

An earlier classification in this audit treated R14 as a generic reference. Final verification detected a concurrent source-map update; the primary freeze decision confirmed its meaning. The directory and R14 page label were corrected before closeout. The effects record retains both operations rather than hiding the correction.

## 5. Terminal: distinguish a usable draft from a qualified saved Plan

A new panel **1Y9G-0** extends the existing **D08C board 1S0R-0**. It identifies current navigation, schema, admission, and persistence boundaries without changing the product screens or their holds.

At the Terminal pin:

- [optionsIa.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/lib/optionsIa.ts) preserves seven categories and existing tab aliases. Plan is not an established workspace route in that map.
- [investigationContracts.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/lib/investigationContracts.ts) accepts manifest v1/v2 and a validated scenario_capture reference in v2. Its closed shape does not accept v3 or option_plan.
- [investigationApiAdmission.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/lib/investigationApiAdmission.ts) requires the exact environment value open. The deployed setting was not probed.

These are schema and admission facts, not fictional feature flags. A valid scenario reference does not prove persistence or entitlements, and must not be used to smuggle an authored Plan into another field.

D08C records shortlist, local draft, editor, and payoff components as reuse candidates. Their current compatibility must be checked before implementation. Native Plan persistence requires the incumbent contract/admission work, applicable #804 holds, and exact owner/record/revision receipt plus readback. Watch activation remains separate.

A second concrete defect concerns replay. [largeTrades/client.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/lib/largeTrades/client.ts) returns typed failures and provenance fields. [IexDepthReplayView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d7a83d3348a4fcb762d93221f19c4e94cbe4505e/terminal/components/futures/IexDepthReplayView.tsx) collapses these to unavailable and drops the artifact/serving metadata. The next UI repair should expose useful state-specific recovery, accurate clocks, safe cursor behavior on artifact refresh, and shared theme roles. No live-feed or interpolated-history claim follows from those changes.

## 6. Consolidation and protection

[INVENTORY.md](INVENTORY.md) distinguishes product homes, source references, QA fixtures, already archived files, an empty cleanup candidate, and an unrelated hospitality project.

No file was deleted or natively archived. The available Paper catalog blocks those operations. Useful consolidation was achieved through directory repair, page ordering, reference labels, and hidden-content labels.

**MASTERMIND PAGES, file 01M2WGNCX9475G79JRKJTCM08P, emitted a file-too-large warning that further changes could cause data loss.** It received no writes. Its copy is not assumed to be a verified replacement. A safe archive/migration path and parity check are separate prerequisites.

## 7. Concurrent editing and attribution

The canvas was shared with at least one independent writer. Observed changes included:

- OS TMP-0 gaining a current owner map in XE7-0 and a combined current/history title.
- AI builder text 1ZE-0 gaining current source guidance.
- GMI status wording becoming “Planned in source” and its Chinese counterpart.
- International's file/Start Here description identifying core plus Global Surveillance.
- Active focus moving to another file between prepare and a guarded action.

These changes were preserved and are not claimed as this session's work. The three native advisers were read-only; the OS adviser explicitly confirmed it did not author XE7-0. Writer identity is otherwise unproven.

Our OS duplicate was repurposed into a complementary build/acceptance board, not a competing current-owner map. An AI edit was abandoned before dispatch when its preimage had changed. Focus mismatches were detected before mutation and reconciled on the original target. Every dispatched edit in [EFFECTS.json](EFFECTS.json) has an observed applied response. No unknown effect remains in this audit's operations.

## 8. Verification and limits

- Actual Paper screenshots were inspected for edited product layouts and builder panels. Ten final captures are committed under [proof/](proof/), with hashes and exact node IDs in [SCREENSHOT_RECEIPTS.json](SCREENSHOT_RECEIPTS.json).
- All twelve GMI navigation targets and all four AI labels were read back by exact node ID.
- Paper page links and builder destinations were read back.
- The interactive reference passed nine source/DOM-harness checks: open identity, Back position/focus, Forward focus, preferences/history, current simulated access denial, reload, direct link, empty query, and failed-read fallback.
- During self-review, the reference's history handling was repaired so an old URL cannot restore earlier simulated access, Forward does not strand the heading below the viewport, and reload can restore a qualified return location.
- A new Terminal panel initially rendered black text because the requested generic color tokens did not exist in that file. Exact JSX and screenshot readback caught it. The owned panel was replaced using the existing Terminal palette and re-inspected.
- Browser-plugin access was unavailable in this session. The HTML reference has **not** received actual browser layout, animation, accessibility-tree, or production integration proof.
- No deployed source, auth policy, API admission flag, monitor, research run, graph admission, trade, or publication was changed.

## Source pins and authority

| Repository | Exact audit pin |
|---|---|
| Mastermind protected master | 5c3d3885234358aefb97ecdbc59be0864df14f8b |
| Macro main | 338a10852dcefa5d2bd07e5c6be0955c2b1e83fd |
| mastermind-terminal protected master | d7a83d3348a4fcb762d93221f19c4e94cbe4505e |

The current Chairman assignment authorized this Paper/source audit. Retrieved records supply evidence, not a new execution commission. Existing runtime, security, source-custody, review, and release holds remain with their canonical owners. This package is an audit and design candidate; merging it does not accept or deploy the future implementations in [BUILD_PLAN.md](BUILD_PLAN.md).

