# D06 Terminal product and UX specification

**Candidate status: draft. Phase 2A source specification; final editable composition held.** This document defines proposed behavior for later reference review and implementation. Existing behavior is identified as observed source, Paper precedent or the separately recorded [live beta baseline](LIVE_BASELINE_AUDIT.md). No requirement below is a claim of implementation, usability measurement or reference approval.

## Product and success

Terminal serves an investor or analyst who needs to answer: **What is this exact instrument doing at this resolution, what does the selected evidence mean, and how do I return to the investigation that brought me here?** The primary object is the chart. Context explains the chart without changing its identity, hiding its tools or implying that current research was known at a historical bar.

The useful first view contains instrument identity, an attributable chart, resolution/session controls and one next step: inspect context. Quote, chart and research clocks remain distinct. A blank chart must explain whether history is loading, absent, unsupported or unavailable. It must not substitute a generic dashboard or silently choose another listing.

Nine canonical route families are in scope; see [route and data contracts](ROUTE_DATA_CONTRACTS.md). Company/Analysis parsing stays with D07; options linkage with D08; AI behavior with D14; Portfolio return with D22; saved objects/alerts with D23; access with D25; public framing with D26. Market Structure, Stage Analysis and S&P Vector are research entry points with their own meaning, not alternate chart engines.

## Complete normal-data journeys

### Research to chart, historical context and return

1. Start on a real Company, Macro, options or Portfolio research object. Carry its exact accepted chart symbol, visible listing context and accepted return href through the existing navigation owner.
2. Open Terminal. Explicit symbol wins over the saved workspace. Preserve the prior workspace instead of persisting the temporary deep-link session over it.
3. Verify displayed instrument, source basis, resolution and session before inspecting a bar. Existing generic incoming timeframe/bar URL support is incomplete; a future exact-bar link must either apply and acknowledge that exact state or explain what was unavailable. It must not report success merely because the URL contains a parameter.
4. Select a rendered bar. Context labels instrument, resolution, selected date/time, time basis, bar quality and whether it is the latest loaded, historical or replay bar. Body return is separate from the header quote's daily return.
5. Open related research or explicitly ask the existing Brain about this bar. The reader's local selection and AI's locked selection are different current state paths; the proposed action must bind the intended selection and invalidate stale results through the existing owner.
6. Close context. Restore a connected, visible, enabled launcher or logical fallback only while focus is still legitimately owned by that close; preserve any deliberate transfer to settings/navigation. Retain active pane, viewport, drawings, indicators and comparisons without an unexpected scroll jump.
7. Return using the captured safe exact href. Restoration of the origin's row, scroll and selection is a separate D07/Macro/D08/D22 handoff, currently unproven. Back/forward and a direct entry with no origin remain meaningful.

Interim behavior: retain symbol-only links and exact safe return href; say “This link opened the instrument. Choose a timeframe to continue” when an incoming exact-state request cannot be honored. Do not label this interim journey as full exact-bar fidelity.

### Professional tools and contextual research

Choose the active pane, use the existing drawing grammar and keyboard shortcuts, change or hide indicators, compare another symbol, save a permitted workspace, and open context or Intelligence. Local overlays must not capture typing intended for an editor, create a second chart engine or reset the view. A docked nonmodal reader retains chart access; a modal sheet traps focus while open. Closing a reader returns to the chart; the proposed broader leave flow asks an explicit save/discard/cancel question. Current verified guards cover script selection and its ID history; full route-exit/unload coverage remains to be tested. No navigation or context selection may write watchlists, drawings, alerts or account preferences accidentally.

All 99 drawing tools, 29 classic indicator IDs, five suites, 19 gated intervals, nine chart types and 15 research panes retain their actual owner and semantics. The [retention ledger](FEATURE_RETENTION.md) and machine-readable registry define coverage. Internal `_lab` remains internal; unsupported intervals remain discoverable with a reason.

### Public share, compact embed and scripts

A public `/x/<slug>` link currently opens a PNG. It is described as a snapshot, with no claimed restorable chart state, expiry date, revocation state or verified source timestamp. A future “Open this chart” action requires approved metadata; generic “Open Terminal” is a separate destination.

An embed shows the supported daily series in its allotted container and links to Terminal using the existing symbol contract. Unsupported identity, no history and upstream failure must have distinct useful states once the existing data adapter can expose them. No full shell, account data, Brain or Pine runtime belongs in the widget.

A signed-in script author loads their own script, edits and runs a clearly labeled synthetic diagnostic, saves with fresh paid entitlement and an exact update token, then adds the saved script to the chart. Source edits made after the save click remain dirty. Conflicts or missing receipts never become “Saved.” The proposed context-preserving Add journey requires the existing navigation/script owners; current Add only carries the saved script ID.

## Keep and change decisions

| Decision | Requirement and reason |
| --- | --- |
| Keep chart-first hierarchy | Chart owns the largest analytical area. Identity/resolution are adjacent to it. Context is optional and attributable. Do not replace candles, volume, history or tools with a narrative card wall. |
| Keep focused Terminal as a distinct composition | `/terminal` already owns chrome and the Brain singleton. F01 supplies a focused integration contract; do not nest the full AppShell around it. Native `shell=app`, `tray=1`, `dossier=1` remain separate modes. |
| Keep and refine the Chart Context precedent | Reuse desktop `1K9F-0` and mobile `1KNZ-0` hierarchy. Desktop reader docks; narrow/mobile reader uses the chart-owned inline destination. Preserve previous/next bar, close, range/events, chart layers and explanatory disclosure. |
| Keep Intelligence as an explicit expansion | Summary, Oracle, Research and Activity remain distinct. Compact focus is an intentional user action; it does not replace the normal chart-first view. Preserve signal history, filters, source methods and chart return. |
| Change historical handoff precision | Show reader-selected versus AI-locked bar explicitly. A named “Ask about this bar” binds the intended bar; stale symbol/TF/generation responses are withheld. |
| Change clock and unit presentation | Use source-specific stamps and honest units. Correct market-local display-epoch labels; do not append UTC universally. Unknown currency, listing or adjustment remains unknown. |
| Change return fidelity | Preserve existing safe href; add owner-approved origin viewport restoration only when real source state can restore it. No arbitrary `history.back()` replacement. |
| Keep dense tools reachable | Use context-aware overflow on narrow widths, with search/categories and real keyboard equivalents. Demotion is not removal. Mobile timeframe wheel retains all functional intervals. |
| Change misleading failure conflation | Distinguish absence, unsupported coverage, failed refresh, denied access and session expiry. Keep last-good evidence labeled with its age; no empty-zero replacement. |
| Keep public/private capture separate | Public PNG upload and private review capture have different evidence/privacy contracts. No metadata or account state is silently added to public sharing. |
| Keep Refraction at the top edge only | Preserve the restrained original material concept. Full-pane grey-wave variants are rejected history. No animated layer across chart, reader or workspace; reduced motion freezes the edge effect and closing pauses it. |
| Change old decorative treatments | Older gold warning borders and header variants are precedents, not current doctrine. Map warnings to approved neutral containers plus text/icon status. Focus outlines remain valid. |
| Keep Macro analytical depth | Retain every historical range, Stage subview/filter/export/reader and S&P strategy comparison. Correct null/source/model labeling without altering the model or granting new coverage. |

Observed source anchors: [Terminal route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/terminal/page.tsx), [AppShell boundary](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/AppShell.tsx), [TerminalShell](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/TerminalShell.tsx), [ChartPane](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/ChartPane.tsx), [originNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/originNav.ts), [Visual Intelligence](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/VisualIntelligencePanel.tsx).

## Layout contract and available widths

These are **domain requirements pending F01/F02 mapping**, not invented frozen shell dimensions.

Record viewport width and actual document client width separately. Let `A` be the chart region after occupied navigation and content gutters; `I` the effective reader width; `X` the actual price axis, drawing controls and nonoverlapping borders/gaps. Measure `pricePlot = A − I − X` against the actual main price-data canvas. An overlapping splitter hit area is not a second layout gap. Overlay navigation does not consume permanent width but must not obscure required actions. Never infer content width from a viewport or screenshot filename.

Observed predecessor: Chart Context desktop is 1440×900, with 54px top band, 1080px chart workspace and 360px reader; chart toolbar 46px, footer28px. Current source rail starts at360 and clamps300–520. Current source distinguishes mobile≤860 from phone≤640. These values are **baseline facts**, not F01 v1 geometry.

Proposed domain fit rule for review: preserve at least **640 CSS px of active price-data plot**, excluding its price axis and occupied controls. This is a D06 hypothesis pending owner qualification, distinct from F01's 640px shared primary region and 984px evidence-dock rule. Keep the existing requested rail width (default360, clamp300–520) separate from its temporary effective fit. Cap only the effective width when needed; if even300px cannot fit with the plot minimum, use the existing inline/focused destination. Exactly640 is eligible,639 is not. Automatic adaptation must not overwrite mm.railW or remove a chosen pane. Measure scrollbar occupancy to prevent dock/inline oscillation. Toolbars use named overflow before page-level horizontal scrolling. Keep instrument, interval, context launcher and return/close visible. [Measured responsive evidence and state requirements](RESPONSIVE_AND_STATE_AUDIT.md) supply the actual861/860 boundary and current1024px failure of this proposed fit rule.

| Evaluation width | Required layout and task proof |
| --- | --- |
| 320 / 390 | One chart column; instrument line and quote/source details wrap; 44px house touch targets for search, TF, Draw, context, close, return. Context below chart or in its explicit focus mode. Primary actions visible above the software keyboard when editing. Long Chinese labels may wrap; ticker/exchange remain identifiable. |
| 768 / 860 / 861 | Test both sides of the actual placement boundary and source mobile/phone distinction: no assumption of phone bottom controls. Global navigation uses F01's tablet pattern. Reader uses inline destination if docking would violate chart minimum. Sheets close on leaving phone breakpoint without reopening unexpectedly. |
| 1024 | Test expanded navigation plus inspector as the stress case, then compact rail. Collapse context placement based on available width. Preserve active pane and visible time window through the transition. |
| 1280 / 1440 | Dock reader only with useful chart width. Multi-pane layouts retain toolbar/category reachability. Inspector scrolling stays independent; page does not gain accidental horizontal scroll. |
| 1600 | Add chart/data capacity, not oversized metadata. Preserve readable text widths and restrained space; inspector stays within its source clamp until its owner approves a change. |

Height is also a constraint: chart fills the remaining workspace after actual chrome; drawers and sheets expose a sticky close/action region and a single bounded vertical scroll area. A low-height landscape or zoomed layout must permit reaching all content. No decorative fixed-height clipping. Plot resize uses the existing coalesced ResizeObserver and preserves logical range; no refit/reset on every drag tick.

## Focus, overlays, scrolling and motion

The chart remains mounted through reader and rail toggles. Each destination has one active scroll owner: chart pan/zoom for the plot, independent rail scroll for long research, a bounded modal body for sheets, the existing content document/iframe scroll owner on Macro pages while shared chrome stays fixed. Do not introduce competing outer-page scrolling or duplicate shell chrome. Wheel behavior must not trap a user who is trying to reach the next page section. A visible “Back to chart” action and keyboard path accompany focused research.

Use nonmodal semantics for a docked reader and modal semantics for a blocking sheet. Do not trap focus in the docked reader. On an explicit open, focus its heading/close control. On close, restore a connected, visible, enabled launcher with `preventScroll` or a valid chart fallback only when the closing surface still legitimately owns focus. When a placement change removes the focused reader subtree, transfer to the equivalent visible control or heading/Close fallback; do not steal focus already moved to settings, navigation or another valid target. Escape is owned by the active layer before chart drawing cancel/reset; input, contenteditable and IME composition suppress unrelated global shortcuts. Brain has its own state-dependent chain, including Stop versus Close. Its source/live discrepancy, actual close method and conditional focus hook are bound in [BRAIN_SHELL_HANDSHAKE.md](BRAIN_SHELL_HANDSHAKE.md); do not promise universal panel closure or infer request cancellation from hiding. Resize handles must have keyboard increments and reset controls as alternatives to drag, with focusability, a visible focus state and accurate minimum, maximum and current value. The live 360→460px pointer resize retained reader context/scroll, but the observed separator lacked keyboard/range semantics; that baseline does not pass the keyboard requirement.

Only the original top-edge Refraction material is eligible. The predecessor specifies a slow16-second drift, no pulse/flash/waveform, and a still panel. Final motion tokens and applicability await F02. Reduced motion stops decorative movement, preserves status and keeps chart/source state changes understandable without animation.

## Accessibility, locale and theme

Target WCAG2.2 AA with an accessible chart-data path: focusable selected-bar summary with OHLC, interval, source basis and time zone; keyboard previous/next sample; text reasons for disabled tools; meaningful series/table summaries. A chart need not announce every crosshair movement. Announce explicit selection, loading outcome and save result with bounded polite live regions. Do not rely on red/green alone for direction, state, gaps or access.

Important mobile controls use the programme's44px house target. WCAG2.2 AA2.5.8 is24×24 CSS px or its spacing/exception rules; these are different requirements. At400% zoom, surrounding text and controls reflow to a320CSS-px equivalent; essential2D chart/table interaction may be contained within its component. Verify text/nontext contrast, visible and unobscured focus, keyboard operation, target spacing and text resize using real rendered colors and measured bounds. Both the live Terminal root and its current root-layout source restrict zoom, as does the earlier Embed source. Resolve `userScalable:false` / `maximumScale:1` with the actual app/widget/native owner. Viewport-width measurements do not constitute pinch-zoom,400%zoom or mobile-device proof.

EN/ZH share semantics and source values. Set the document or relevant content language to match rendered text; the live Chinese embed retained document lang=en, so visual translation alone does not satisfy assistive-language requirements. Translate labels and failure reasons, not canonical symbols/IDs. Preserve Chinese exchange identifiers/leading zeros, CJK wrapping and numeric alignment. Do not infer currency or exchange from language/region. Light and dark must use the released F02 semantic surfaces and chart colors; no local competing token system. Validate dense candlesticks, volume, drawings, selection, disabled items, stale states and focus in both themes.

Primary standards: [W3C target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [W3C reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html). No conformance measurement is claimed.

## Paper composition plan and acceptance

Reuse the exact inspected references:

- [Chart Context](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-W-0): `1K9F-0`, `1KNZ-0`.
- [Intelligence](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-I-1): desktop Summary`19IC-1`, Oracle`19WI-1`, Research`19PG-1`, Activity`1A3O-1`; compact focus`1AAY-1`; mobile Summary`1AEB-1` and existing detail variants.
- [Refraction](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-Z-0): original material`1M58-0`; original desktop/mobile`1M4U-0`/`1M53-0`. Preserve rejected R2`1MFJ-0`/`1ML8-0`/`1MNZ-0` as history, never successors.
- [Source-only page](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-G-0): historical evidence only; group`YYM-0` returned an unusable1px screenshot and is not presented as a visual proof.

After joint F01/F02 v1 is actually verified, the same D06 owner must re-read target nodes and writers, qualify the authoring carrier, and create editable compositions for desktop docked/context, focused return, phone/tablet, public snapshot, embed, scripts and the three Macro route archetypes. Required state specimens are linked in [interaction states](INTERACTION_STATES.md). [Prepared Paper annotations](PAPER_BUILD_ANNOTATIONS.md) contain the Read me and adjacent-control copy; they have **not** been placed on the canvas.

Acceptance needs an immutable after-artifact set plus independent product-regression and visual/taste review under actual RIG admission. The first pass gets only job, production-before, proposed-after and capability/task manifest; rationale follows frozen findings. Current RIG remains **draft**. No baseline capture or advisory source consultation is an approval receipt.

## Measurement plan

Later implementation should measure successful exact-instrument entry, exact requested state acknowledgement, wrong-context suppression, return restoration, tool reachability and time to first useful chart. Report by device/locale/access class and include failures. Avoid recording private drawing text, portfolios, script source or full watchlists in analytics. Performance budgets are LCP≤2.5s, INP≤200ms and CLS≤0.1 atp75, separately for mobile and desktop; none was measured here. [Web Vitals](https://web.dev/articles/vitals) supplies the metric definitions.


## Additional predecessor findings

The older Intelligence reference 19BB-1 includes an illustrative “Suggested size 50%”; current R3 specimens instead show sizing unavailable. Keep the unavailable state until the existing sizing owner supplies an approved producer and access/decision contract. The mobile Activity predecessor omits a visible Re-entries filter, so the final composition must provide a reachable equivalent without losing that supported capability. Live desktop Entries exposes RE-ENTRY records, proving their current reachability. Exact parity with the predecessor’s dedicated Re-entries filtering, including isolation, counts, scope and narrow/touch access, remains to be qualified. Retain that filtering obligation until the existing owner resolves it. The older Refraction settings grid omits 12h; source registry parity, not screenshot copying, governs the full 19-interval chooser.

## Live-informed refinements for the existing owners

These are candidate requirements grounded in the [baseline audit](LIVE_BASELINE_AUDIT.md), not changes applied to the product.

| Journey | Required refinement | Existing owner |
| --- | --- | --- |
| Generic versus company entry | Generic Open Terminal uses its qualified workspace/default path; named Open [symbol] chart uses an explicitly qualified current identity. A valid Analysis URL identity wins over stale shared cursor; an explicitly invalid identity never silently opens the previous company. | F01/D07/Terminal; NAV10 |
| Evidence and Brain | Retain one Brain and existing selection/request owners. Qualify real close/visibility/focus before adopting candidate.3 evidence suspension; do not automatically reopen the reader after Brain closes. Terminal width remains independently owned. | D14/F01/F02/Terminal; BRAIN01 |
| Focus and historical context | Preserve the current valid inspection cursor and logical range across presentation-only transitions until a legitimate crosshair, step, Latest or other owner event changes it. Retain valid disclosure/scroll and distinguish the separate AI lock; exact-bar Ask needs explicit validated binding. Test settled layout with the pointer outside the plot. | Chart/reader/D14; LAY06 |
| Event location | A located historical event can pan the chart without selecting the same reader bar. Keep Latest truthful until an explicit selection bridge is supported; retain Intelligence's observed launcher focus return. | Intelligence/ChartPanel; HIST01/LAY06 |
| Comparison | Expose primary/overlay identity, actual common anchor, adjustment basis and unequal coverage dates. Readouts must identify their interval or absence; no fabricated zero returns. Qualify the observed anchor/readout discrepancy with its producer owner. | Comparison/data; COMP01 |
| Shared current navigation | Mark only the actual matching destination current; zero current destinations is valid for an unmapped utility route. The live Scripts Today marker does not satisfy this requirement. | F01 navigation |
| Partial publication | Each Stage slice reports its own observed load state. Do not promise a sibling works when its state is unknown or failed; preserve valid overview/siblings and targeted retry. | Stage publication; STAGE04 |

The source Read me content is independently useful before final composition. Its actual Paper placement requires current D06/C4 account/app/target admission; final shell-dependent composition additionally requires verified joint F01/F02 v1. Neither supported v20 edit schemas nor another account's accepted write supplies that grant.

## Later source-qualified retention refinements

The [current source delta](SOURCE_DELTA_20261103.md) at2ded360882b9c721e690907ff363b553781fb920 qualifies Company search preview/query/listing context, optional cache acquisition cutoffs, the missing public-data fallback and Pine's opt-in reference receipt. They attach to existing owners and capability groups; they create no new route, selection store, data proxy, customer export button or model-validation claim.

The reader currently has **one inspection cursor** shared by crosshair and Previous/Next, not separate committed and hover pins. Preserve the valid cursor across presentation changes until a legitimate owner event replaces/clears it; Latest clears it. Preserve valid disclosure/scroll within the existing reader owner. AI locked selection and Intelligence event location remain separate. A future exact-bar Ask needs an explicit, visible, generation-validated handoff. These semantics refine the normal journey above without adding a hidden persistent state path.
