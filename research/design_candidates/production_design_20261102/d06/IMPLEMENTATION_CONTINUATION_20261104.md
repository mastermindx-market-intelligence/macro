# D06 implementation continuation — reader resilience

**Current outcome: BUILT_AND_LOCALLY_VERIFIED / TERMINAL_PUBLICATION_BLOCKED. Overall D06 remains PARTIAL; RIG draft.**

The Chairman's latest continuation explicitly authorizes implementation before F01 completion. D06 used that authorization to implement the independently owned Chart Context reader repairs identified in the live audit. The complete Phase 2A specification remains in this same [D06 carrier](https://github.com/mastermindx-market-intelligence/macro/pull/10655). This continuation publishes factual research and verification evidence here; it does not turn Macro into an alternative publisher for Terminal code.

The implementation is preserved in its original managed Terminal workspace. The publisher's read-only preflight refused before any effect, so **there is no implementation commit, Terminal PR, hosted CI, formal approval or deployment claim**. The explicit Ready/merge/enqueue/relabel/deploy hold remains. Final shared-shell composition and Paper authoring admission remain separate gates.

## 1. Source, ownership and authorized scope

| Binding | Exact value |
| --- | --- |
| D06 owner | Astra Pro / ChatGPT4 / `mastermidx4`, unchanged |
| Original five programme inputs | Macro `6e1862867193ec6486a22001a0e4fb515da20448` |
| Protected procedure used for this build | Mastermind `910803421beca53ca25145392725ab2d84c7a8e9`, compatible skillpack 1.0.1/bootstrap major 1 |
| Prior durable research freeze | Macro `d7d6b7ddcd950d7e9879bbf58c7e2e481b4708bf` on Draft #10655 |
| Terminal base and unchanged local Git HEAD | `2ded360882b9c721e690907ff363b553781fb920` |
| Managed operation | `d06-terminal-reader-resilience-20261103-c4` |
| Original workspace | `/Volumes/Mastermind/agent-workspaces/terminal/web/d06-terminal-reader-resilience-20261103-c4` |
| Original local branch | `sol/web-d06-terminal-reader-resilience-20261103-c4` |
| Code identity | Five exact source/test file hashes in [implementation_receipt.json](evidence/implementation_receipt.json); no implementation commit exists yet |

The current law was refreshed at one protected SHA. Unchanged required companions were verified against the previously consumed pin; changed delivery/review policy was read. The bootstrap, Paper and Mastermind Craft frontend workflows were applied before source modification. The source instructions and installed Next client-component guide were read.

The writer census found ongoing Chart AI #1048 (including a dirty managed carrier), Intelligence #1252, Options #1248 and startup work #654. D06 acquired one fresh, source-pinned workspace through `mmx-workspace`. It did not edit their ChartPanel, ChartPane, TerminalShell, Intelligence or Options paths, the primary checkout, or a shared return ledger. There was no existing active D06 implementation carrier to duplicate.

The supplied Executive readers returned `backend_unavailable` before sending requests. Fabric admission/START remained unprobed and no authenticated root/parent/grant was obtained. No Fabric modifying request was submitted. The incumbent owner performed the bounded implementation under the documented `NO_ELIGIBLE_PRE_EFFECT_WORKER / LOWER_TOTAL_OVERHEAD` exception. A native reasoning adviser challenged focus and scroll ownership only; this is not an independent approval, routine builder return, or fabricated Fabric START.

## 2. Implemented product behavior

The live audit observed that a historical bar survived a dock/inline move while native disclosures, internal scroll and one focused reader control did not. The new browser regression reproduced the disclosure failure on the unchanged source before the runtime edits.

| User action or state | Implemented behavior |
| --- | --- |
| Move an open reader from the rail to inline and back | Preserve Range & company events, Chart layers and How to read this disclosure state within the same source identity |
| Portal host temporarily becomes null during placement | Preserve logical open intent and presentation memory until its host returns |
| Move between the panel and a bounded focused-mode host | Restore the actual internal scroll offset, clamped to the destination's available range |
| Move to a plain inline page | Leave document scrolling with the page; retain the last internal offset for a later bounded destination |
| Reader control owned focus before its DOM was replaced | Restore the same visible, enabled semantic control only if ownership is still valid, the document is focused, and another control has not taken focus |
| User moves focus or acts outside the reader | Cancel the saved focus claim; an outside click cannot later reacquire that claim merely because activeElement did not change |
| Change symbol, timeframe or replay identity | Reset disclosures and the physical internal reading position; preserve only a still-owned, actually focused connected control without moving focus |
| Explicitly close and reopen the reader | Reopen collapsed at the default position through the incumbent launcher; retain the existing valid selected-bar cursor |
| Activate a summary with mouse, Enter or Space | Apply the disclosure immediately through controlled native details/summary semantics, avoiding a queued-toggle race with portal replacement |
| Use a phone-width fine pointer or a coarse pointer | Apply at least 44×44 pixels to reader buttons and a 44-pixel summary height, including the enable and feedback actions |
| Choose Candle settings | Continue to the existing Mastermind Candles dialog; the reader adds no delayed focus callback that could steal the handoff |

The runtime delta is limited to `terminal/components/VisualIntelligencePanel.tsx`, its CSS module, and the new component-owned `useChartContextPresentation.ts` hook. Two new test files accompany it. There is no new renderer, workspace manager, URL state, preference store, backend, data feed, auth path or general focus service.

## 3. Existing feature and data contracts preserved

| Contract | Preserved owner and practical limit |
| --- | --- |
| Instrument identity | Exact symbol/timeframe/replay props and the existing VisualFrame identity guard; no display-name substitution or inferred listing |
| Historical cursor | Existing `selected`, series index and `onInspectTime`; crosshair and Previous/Next still share one cursor, and Latest clears it. No pin was invented |
| Calendar truth | Existing getFund/visualCalendar source states and historical/replay withholding; no current calendar leaked into selected history |
| Bar facts and overlays | Existing analyzer, RSI, trend, volume, candle colors, optional layers and chart settings callbacks |
| Settings and feedback | Existing preferences and callbacks; no additional persistence or account ownership |
| Close and return | Existing ChartContextDock close contract and TerminalShell launcher/fallback owner; the new hook restores presentation focus synchronously only within its scope |
| Geometry | Existing rail, inline and 40svh focused/native host; no shared rail-width preference or shell slot was replaced |
| Source clocks | Existing labels and formatting remain. The separately specified numeric-time-basis and provenance improvements are not claimed as implemented |

The existing Terminal chart surface is intentionally dark-only: this is explicit in `terminal/app/settings.css` and consistent with its root tokens and layout. Both supported languages were verified. Merely setting a light-theme attribute would not establish a real light-mode journey. Future light composition remains unqualified.

The [76-group retention ledger](FEATURE_RETENTION.md), all nine route families, 99 drawing tools, 29 indicators, five suites/31 modules, 15 research panes, 19 intervals and nine chart types remain in the design package. This slice does not claim that every retained advanced operation was executed.

## 4. Executed verification and evidence

| Check | Actual result |
| --- | --- |
| Pre-change reproduction | The new transition test failed on the disclosure reset at the first dock-to-inline crossing |
| Final focused Vitest suite | **22 passed**, including StrictMode, detached/null hosts, same-host scroller changes, clamping, source reset, outside intent, absent/disabled targets and dismissal |
| Final browser matrix | **57 passed, 12 intentional skips, 0 failed, 0 flaky**, on the real local Terminal route with existing deterministic fixtures |
| Browser suites | `chart-context-resilience.spec.ts`, `chart-context-dock.spec.ts`, `visual-intelligence.spec.ts` |
| Browser viewport projects | 1440×900 desktop, 820×1180 tablet/coarse-pointer emulation, 390×844 phone/coarse-pointer emulation |
| Additional width/input checks | 320×844 with an actual fine-pointer browser context, EN and ZH, reduced motion |
| TypeScript | `npx tsc --noEmit --incremental false`, exit 0 |
| Scoped ESLint | Reader component/helper and the two new test files, exit 0 |
| Whitespace and scope | `git diff --check` passed; generated legacy screenshots restored, leaving only D06-owned source/test/document/proof changes |
| Visual inspection | **12 raw PNGs**, all inspected; copied bytes verified by SHA-256 |

The final browser run started at **2026-11-04T01:07:48.733Z** and took **195.415 seconds**. It contains 14 new reader cases and 43 incumbent executed cases. The 12 skips prevent repeating desktop crossing sequences in each native-viewport project. There were no retries in the final run.

The initial broad run's five failures came from three mistaken automation paths: a nonfocusable chart wrapper, the phone-only floating fullscreen entry at desktop, and the wrong Settings dialog name. They were corrected against actual source and DOM, then passed. Production behavior was not changed to satisfy those incorrect assumptions. The earlier unchanged-source disclosure failure is a separate, genuine regression baseline.

Measured reader widths are 360 pixels in the desktop rail and 820/390 pixels inline. The six locale/viewport records have matching document and scroll widths and the actual dark reader background. Narrow fine-pointer and coarse-pointer cases pass the 44-pixel assertions. These observations are not physical-device, browser-zoom, full contrast or screen-reader proof.

### Actual captures

| Evidence | English | Chinese |
| --- | --- | --- |
| Desktop reader | [1440×900](evidence/implementation/reader-desktop-en.png) | [1440×900](evidence/implementation/reader-desktop-zh.png) |
| Tablet reader | [820×1180](evidence/implementation/reader-tablet-en.png) | [820×1180](evidence/implementation/reader-tablet-zh.png) |
| Phone reader | [390×844](evidence/implementation/reader-mobile-en.png) | [390×844](evidence/implementation/reader-mobile-zh.png) |
| Expanded fine-pointer phone | [320×844](evidence/implementation/phone320-fine-en.png) | [320×844](evidence/implementation/phone320-fine-zh.png) |

The genuine local pre-change baseline is [desktop](evidence/implementation/baseline-desktop.png) and [inline after the failing transition](evidence/implementation/baseline-inline-reset.png). The final candidate's [before](evidence/implementation/desktop-before-transition.png) and [after](evidence/implementation/desktop-after-transition.png) captures accompany the passing roundtrip assertions. The screenshot of the failed inline transition does not itself show the below-fold disclosure; the test assertion supplies that state evidence.

All market values in these 12 new captures come from the existing deterministic local fixture. They are separate from the 36 earlier beta captures and 16 Paper reference captures. None is a deployed after-design or independent taste approval.

### Migration-plan mapping

The new proof covers bounded reader subsets of LAY02, LAY05, LAY06, A11Y01 and A11Y02. The 320-pixel/reduced-motion checks are subsets of A11Y03/04; they do not establish 400% zoom or all Refraction states. Incumbent calendar, layer, replay and settings cases supply related DATA08/HIST03 regression evidence. **No full case in the broader 75-case migration plan is newly marked complete.** LAY07's useful-plot budget, shared rail keyboard resize and final shell composition are not implemented here.

## 5. Exact publication blocker and recovery

The original managed publisher's `studio_git_publish_status` returned:

```text
REFUSED / NOT_APPLIED / TYPED_GIT_PRECHECK_REFUSED
```

No commit or push was attempted afterward. There is no uncertain modifying effect.

One bounded read-only diagnosis established that `mmx-workspace status --operation-id d06-terminal-reader-resilience-20261103-c4 --lane web --repository terminal` resolves the correct preserved dirty workspace, whereas the unqualified lookup returns “workspace is not registered to the source repository.” The inspected publisher implementation calls the unqualified lookup and checks a single configured Mastermind source repository. A repository-binding mismatch is therefore consistent with the evidence. The deployed gateway configuration and its code bytes were not independently attested, so the underlying runtime authorization classification is not invented.

[Terminal's governing source instruction](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2ded360882b9c721e690907ff363b553781fb920/AGENTS.md) requires recovery through the original publisher and applicable typed preflight; it forbids using a replacement branch, account, tool or GitHub direct source writes to evade a refusal. The source remains recoverable in the exact managed workspace above. The review snapshot supplied to the Chairman contains the tested files, raw reports, screenshots and a complete member manifest; it is not an alternative publishing path.

**Executable next action:** the publisher owner qualifies Terminal support for this existing operation and source binding. After material same-carrier repair evidence, D06 rechecks the workspace and recorded hashes, reruns the typed preflight, commits/pushes through that publisher, and opens one Draft Terminal PR linked to #10655. Formal non-author review and hosted CI follow on that actual immutable source. The current explicit release hold remains.

## 6. Remaining acceptance gates

- Final F01/F02 shell composition still needs verified joint v1. The Chairman's build waiver is honored; it is not a released contract receipt.
- D06/C4 Paper write admission remains unestablished. Exact read-only references are [Chart Context](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-W-0), desktop **1K9F-0** and phone **1KNZ-0**; [Intelligence](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-I-1) remains a reference owned by its existing writer. No Paper mutation or after-board approval is claimed.
- The rejected full-pane Refraction treatment remains excluded; the original [top-edge material reference](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-Z-0) is not a composition release.
- The 640-pixel useful-plot budget, rail keyboard resizing, exact-bar AI binding, source-clock changes, root/embed zoom restrictions, light composition and the remaining route/owner tests retain their original ownership and acceptance requirements.
- Independent review, hosted CI and served-after-build proof remain outstanding. Local passing tests are not RIG or production acceptance.

**Finalization of this continuation:** the independent reader build and local proof are complete; Terminal publication and the remaining composition/review/release lanes are blocked by the exact gates above. Source and proof remain with D06's existing owners. No automatic watcher, future execution or background review is claimed.
