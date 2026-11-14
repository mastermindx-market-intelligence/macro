# D06 responsive layout and state audit

**Result: measured existing Terminal behavior and a more precise proposed layout contract. Overall design acceptance remains PARTIAL; RIG draft.** This continuation extends the existing D06 source package. It does not implement the recommendations, release F01/F02, or authorize Paper writes.

## Observation scope and source identity

The 3 November 2026 afternoon continuation used the connected Chrome browser and its supported viewport override on [the actual AAPL Terminal](https://beta.mastermind-x.com/terminal?symbol=AAPL). The account UI established a signed-in presentation; entitlement tier and backend authorization were not independently verified. Account identity, watchlist contents and settings screenshots are excluded from this evidence package. Earlier guest observations retain their original scope in [LIVE_BASELINE_AUDIT.md](LIVE_BASELINE_AUDIT.md).

The chart was dark, English, AAPL, 3D, with DPR 1. Pointer and keyboard actions were used. Changing a viewport is not touch-device emulation, browser zoom, screen-reader testing or performance measurement. No AI prompt, save, script execution, public upload, account change or production-code action occurred. A deliberate rail resize was restored to its observed 360 px starting width; the reader was closed and the viewport override reset to 1853×1260. Theme and language preferences were inspected, not changed.

The DOM's Next script URLs carried deployment token **2ded360882b9c721e690907ff363b553781fb920**, equal to the independently read Terminal master SHA. This is stronger source correspondence than the earlier unmatched token, but still not an independent build/bundle attestation. The external Brain asset remained a separately hosted URL without a byte hash. The original assignment and five common inputs stay fixed at **6e1862867193ec6486a22001a0e4fb515da20448**.

The new Terminal head is ten commits ahead of the prior 3cc8da84 source pin. Complete, nontruncated Git tree reads establish that ten core chart/reader/Brain/origin files retain exactly the same blobs. Source changes relevant to D06 are separately qualified in [SOURCE_DELTA_20261103.md](SOURCE_DELTA_20261103.md); the older source contracts are not silently re-pinned.

## Measured responsive behavior

Widths below are CSS pixels from the live DOM. Plot width is the main price-data canvas, excluding its separate price-axis canvas. Reader width is the actual reader section. Values at different viewport heights are not a controlled performance comparison.

| Viewport | Document client width | Price plot width | Reader placement / width | Meaning |
| --- | ---: | ---: | --- | --- |
| 1440×900 | 1440 | 904 | Right rail, 360 | Chart and historical context coexist with substantial plotting space |
| 1024×768 | 1024 | 488 | Right rail, 360 | Existing viewport breakpoint allows a narrow plot while keeping the full rail |
| 861×900 | 861 | 326 | Right rail, 360 | Most severe measured docked case; toolbar overflow/clipping requires attention |
| 860×900 | 851 | 788 | Inline below chart, 851 | One-pixel viewport change crosses the existing 860 px placement breakpoint; document scrollbar consumes 9 px |
| 768×1024 | 759 | 696 | Inline below chart, 759 | Tablet follows the responsive chart pattern, with desktop-style chart toolbar |
| 390×844 | 381 | 318 | Inline below chart, 381 | Phone roller controls replace the broad toolbar |
| 320×844 | 311 | 248 | Inline below chart, 311 | Surrounding context reflows; essential chart detail is dense |
| 320×844, focused | Recorded separately | Not used as a fit verdict | Same reader in a bounded host, client height 337 | Existing 40svh context cap creates an independent scroll area |

No page-level horizontal overflow was observed at the measured normal-layout points: document scroll width equaled document client width. This does not establish that every control was reachable or that local chart/roller overflow was correct. In particular, the 861 px screenshot shows the chart toolbar's right edge constrained by the rail; the 320 px roller intentionally has more controls than its visible horizontal space. Full overflow/keyboard/touch acceptance remains a future gate.

Representative unchanged captures: [1024 px dock](evidence/live/d06-responsive-1024-20261103.jpg), [861 px boundary](evidence/live/d06-responsive-861-20261103.jpg), [768 px inline](evidence/live/d06-responsive-768-20261103.jpg), [390 px inline](evidence/live/d06-responsive-390-20261103.jpg), [320 px scrolled inline](evidence/live/d06-responsive-320-20261103.jpg), [320 px focused](evidence/live/d06-responsive-320-focus-20261103.jpg).

The source agrees with the observed switch: [useMediaQuery](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/lib/useMediaQuery.ts) distinguishes mobile at 860 px from phone at 640 px. [TerminalShell](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/TerminalShell.tsx) places context inline for mobile, focused chart or native-shell mode. [ChartContextPlacement](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/ChartContextPlacement.module.css) bounds focused/native inline content to 40svh and contains overscroll. These are existing behavior, not accepted F01 geometry.

## What survives and what resets

The test selected **2026-10-27** with Previous bar while the latest plotted AAPL 3D date was 2026-10-30. Pointer actions for resizing and navigation stayed outside the price plot.

| Transition | Observed result | Retention decision |
| --- | --- | --- |
| Desktop dock → tablet inline → phone inline | The reader continued to display 2026-10-27 | Retain exact current inspection identity across presentation-only transitions |
| 1024 dock → 768 inline while Previous bar had focus | Focus became BODY; the date remained | Repair focus transfer when the currently focused reader control is removed |
| Phone reader Close | Focus returned to the visible More roller button | Retain this reachable fallback; do not generalize it to every close path |
| More → Analysis hub → Chart context | A real modal hub opened, then reader reopened on 2026-10-27 and focused Close chart context | Preserve this phone route and explicit handoff |
| 320 px focused chart | Reader host height 337, content height 807; scrolling moved host to 420 while document stayed at 0 | Preserve independent focused-reader scrolling |
| Exit focused chart at 320 px | Date stayed 2026-10-27; focus was on the Fullscreen chart control | Retain this observed phone exit path; the earlier guest desktop BODY result remains a separate observation |
| Deliberate rail resize 360→460; widen/narrow through 860 px | On return to 1440, effective reader width was again 460 | Preserve the existing rail preference through automatic placement changes |
| Open How to read this, reader scroll 292; cross dock/inline boundary | Disclosure closed and scroll became 0; date remained 2026-10-27 | Improve disclosure/scroll retention; do not report a lost date |
| Restore initial conditions | Reader width 360, reader closed, viewport 1853×1260, dark/en | Temporary inspection state reconciled |

The phone [Analysis hub capture](evidence/live/d06-phone-analysis-hub-20261103.jpg) shows the retained advanced tools and context entry. Its dialog advertised aria-modal=true. Tool tiles measured 79×84; Close measured 34×34. At 320 px, reader Close measured 32×32, Previous/Next 28×32 and Latest 34×32. These miss the proposed 44 px house target; they are not by themselves proof of a WCAG 2.2 AA target-size failure, whose minimum/spacing exceptions require their own evaluation. No full focus-trap cycle or touch gesture was tested.

## Correct selection semantics before designing around them

**The existing reader does not expose separate committed and transient-hover selections.** [ChartPanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/ChartPanel.tsx) uses inspectVisualTime to write the same visualSelectedTimeRef from crosshair inspection and reader Previous/Next. The [reader](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/components/VisualIntelligencePanel.tsx) has one selected value and resets it when symbol/timeframe/replay changes or a selected bar disappears. Latest explicitly clears that inspection selection.

Consequently, earlier “committed/pinned reader versus hover” wording is corrected by this source qualification. A later valid crosshair event is allowed to update the current reader cursor. This package does not add a pin control, restore an earlier sample after pointer exit, or create another persistent selection store. The testable retention requirement is narrower: a presentation-only transition must retain the current valid inspection cursor until a legitimate owner event changes it.

The AI locked vertical line and Intelligence event location remain separate owners. A future exact-bar Ask must visibly bind and validate the actual instrument, interval, selected time/time basis and data generation through the existing D14/Terminal integration before dispatch. A resize-generated hover cannot be silently treated as explicit acceptance of that attachment. This is proposed handoff behavior, not a currently implemented exact-bar contract.

## Refined proposed layout and state decisions

These are D06 requirements for owner review. They remain conditional on F01/F02 mapping; none releases the shared shell.

1. **Measure useful plot space explicitly.** Define the provisional 640 px minimum as the active price plot's horizontal data area, excluding price axis, occupied drawing controls and actual borders/gaps. Record viewport width, document client width, occupied global navigation/gutters, reader width and measured plot width. A splitter's overlapping pointer hit area is not an additional layout gap. Do not substitute F01's shared 320+24/984 rule for Terminal's measured plot budget.

2. **Separate requested and effective rail width.** Keep the incumbent Terminal rail preference: initial 360, clamp 300–520, currently persisted by mm.railW. When context docking is eligible, cap its effective width to leave the proposed plot minimum. If even 300 px cannot fit, use the existing inline/focused destination. Automatic fit never overwrites the requested width. Restore the requested width when space permits. This requires Terminal/Options rail-owner qualification because the current preference serves more than the reader; D06 introduces no competing width store.

3. **Make the threshold stable.** Exactly 640 px is eligible; 639 is not. Resolve scrollbar occupancy and actual divider/axis width once per layout measurement so moving a reader does not oscillate between modes. Coalesce resizing through the existing owner. Replacing a renderer, resetting its range or changing a user-selected multipane arrangement is not an acceptable way to satisfy the reader rule. In a deliberately dense multipane layout, move context rather than silently remove panes.

4. **Carry open intent through a placement change.** An open reader can move between dock and inline while retaining the same domain context. An explicitly dismissed reader remains closed. Phone-only modal sheets follow their existing breakpoint dismissal rule and do not reopen on returning to phone width. Reader placement and phone-sheet visibility are different states.

5. **Restore focus conditionally.** On a presentation transition, transfer focus only if the removed reader subtree still owns focus; match the corresponding visible control or focus a logical reader heading/Close fallback. On explicit close, restore a connected, visible, enabled invoker with preventScroll or an appropriate visible chart control only while focus still belongs to the closing surface or is otherwise legitimately owned by that close. Preserve focus deliberately moved to another valid target; programmatic removal or navigation is not an unconditional restoration trigger. Settings/navigation transfers and deliberate user focus movement must not be stolen by a delayed restore. Dock/inline readers remain nonmodal; blocking sheets alone trap focus.

6. **Retain valid disclosure and scroll.** Preserve disclosure state and a meaningful scroll anchor/offset across presentation-only changes, clamping only when the content no longer supports the old position. A source/selection change may invalidate content and must be deliberate. Keep this inside the existing reader/placement owner. The observed DOM-native disclosure reset is baseline behavior to improve, not a reason to add a general workspace state store.

7. **Keep clear exits and clocks.** Focused mode retains identity, interval, visible exit, context entry and a bounded reader. Latest plotted bar, selected historical bar and delayed quote are separate clocks. No clock relabeling follows from moving the reader or hiding chrome.

These decisions refine LAY02, LAY06, A11Y01–03 and introduce LAY07. Complete proposed-case executions remain **zero**. [The migration plan](BUILD_AND_TEST_PLAN.md) names the implementation owners and falsifiers.

## Accessibility and proof limits

The live Terminal root, not only Embed, exposed viewport metadata with maximum-scale=1 and user-scalable=no. The [root layout source](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/terminal/app/layout.tsx) contains the same restriction. The responsive-width observations do not establish browser pinch-zoom or 400% behavior. The app/Terminal owner must qualify and resolve this restriction with any native-shell requirements.

Settings showed a signed-in presentation. The appearance preference read Light while the chart DOM and visible chart remained dark; this is recorded only as a reason not to label a screenshot from a preference chip. No setting was changed, no theme-synchronization diagnosis is asserted, and no new light/Chinese Terminal proof is claimed.

Still unproved: real touch/coarse pointer, mobile browser/software keyboard, landscape, 400% zoom, screen-reader behavior, contrast, all overflow controls, full dark/light×EN/ZH matrix, 1280/1600 variants, access enforcement, saved-state races, performance and after-design usability. These are scoped acceptance requirements, not claims that every baseline route failed.

## Paper correspondence and admission

Fresh native Paper reads addressed exact file **01M3NSZGE8JWN2EZCSF0DT05RM** without changing foreground design. The parsed depth-3 summaries for Chart Context **1K9F-0** and Intelligence Summary **19IC-1** matched the two frozen structure exports exactly, including token content hash **55dd37b7**. This establishes correspondence only for those returned summaries, not full-file byte equality or final visual acceptance. The sixteen existing raw Paper screenshots remain unchanged.

The live 0.5.18 catalog reported TOOL_SCOPED_CONTRACT_V1, 16 compatible writes, zero incompatible writes, full-catalog-known=false and snapshot compatibility. Schema readiness does not establish this C4 seat's accepted authoring path. The [10:25 UTC original rollout record](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1011#issuecomment-6601121419) still holds C3/C4 guarded writes behind the original C1 terminal result. The [later P00 record](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1011#issuecomment-6604289465), updated 19:23 UTC, still carries separate original C1 and runtime acceptance gates. No prepare or Paper edit was dispatched.

At final prepublication read, F01 #10645 advanced to2d008bf91ccff696a3490e5d45eb9bc8d721ec9a, narrowing its own native hold to the original uncertain/dependent targets while permitting independent existing-board corrections. Its joint candidate.3 blob remains unchanged and unreleased. F02 #10630 retains its consumed head. This F01 action-scope correction transfers no D06 authoring admission; final shell-dependent composition remains held. The rejected full-pane Refraction variants remain excluded.

## Evidence handling

[evidence/responsive_observations.json](evidence/responsive_observations.json) records measurements, source identities, bounded findings, Paper correspondence and cleanup. [Capture metadata](evidence/live_captures.json) records the seven added payloads.

The Browser tool labeled its image blocks image/png; decoding the actual bytes identified JPEG. Filenames and persisted MIME follow the decoded format, while metadata retains the tool-declared MIME. Returned image dimensions sometimes differ from the requested viewport. D06 preserved the bytes exactly and did not crop, rescale or recolor them. Geometry claims use live DOM measurements, not inferred image pixels. No account-settings or watchlist capture is published.
