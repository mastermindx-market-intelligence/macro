# D06 published implementation — reader resilience and chart time

**SOURCE_PUBLISHED / LOCALLY_VERIFIED / HOSTED_CI_PENDING / RELEASE_HOLD.** The original publisher is recovered. Both the earlier reader resilience implementation and this chart-time correction are on [Terminal Draft #1270](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1270). Current immutable source: **`0cf50dc0c7db259b284b48632df3f05fcb0fb7b7`**. Overall D06 remains **PARTIAL; RIG draft**. This is the completed bounded implementation continuation, not full programme or production acceptance.

The original [Macro D06 #10655](https://github.com/mastermindx-market-intelligence/macro/pull/10655), owner Astra Pro / ChatGPT4 / `mastermidx4`, source home and operation remain unchanged. The Chairman explicitly authorized implementation before F01 completion. Self-QA proceeds without a blanket extra Web-review ceremony. Binding branch protection, CODEOWNERS, required current-head CI and formal non-author approval where required remain. Ready/un-draft, merge, enqueue, held-PR relabel and deployment remain held.

## 1. Publisher recovery and exact source custody

The original owner had already published the initial implementation at `2d29878cf52b6a8ac950b93ea9a78ec0fae60aff`. D06 recovered that existing branch/PR, verified repository-qualified typed status and compared all 26 published file blobs with its retained original snapshot. They matched. It did not repeat the initial publication or allocate a second carrier.

| Binding | Verified value |
| --- | --- |
| Required five programme inputs | Macro `6e1862867193ec6486a22001a0e4fb515da20448` |
| Current protected Mastermind procedure | `576b59341edc9c871cb9d950833678fcf65078e4`; compatible 1.0.1/bootstrap major 1 |
| Procedure refresh | INDEX unchanged; changed delivery/account instructions read, unchanged required companions verified/reused from valid `910803421beca53ca25145392725ab2d84c7a8e9` |
| Terminal operation | `d06-terminal-reader-resilience-20261103-c4` |
| Same branch | `sol/web-d06-terminal-reader-resilience-20261103-c4` |
| Same managed workspace | `/Volumes/Mastermind/agent-workspaces/terminal/web/d06-terminal-reader-resilience-20261103-c4` |
| Original implementation base | `2ded360882b9c721e690907ff363b553781fb920` |
| Initial published implementation | `2d29878cf52b6a8ac950b93ea9a78ec0fae60aff` |
| Current correction commit | `0cf50dc0c7db259b284b48632df3f05fcb0fb7b7`, parent the initial implementation |
| Typed commit | APPLIED; action `77ebc1d8e8d0c259bdbef7fa0be5a00ead6724ea1c71b84a3e0dcff1880661f2` |
| Typed same-branch push | APPLIED; action `c9e55957c9b1fe14eaf3406be087cd8c2ddbd16d6f9cf554dd87e5d679ce81ea` |
| Publication readback | Local/remote heads match; clean workspace; all 17 changed GitHub file blobs match tested code and captured evidence |

The earlier REFUSED / NOT_APPLIED preflight is historical. Its [original resolution evidence](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1333#issuecomment-6622174610) and actual repository-qualified status explain why the same carrier could proceed. No alternate Terminal Git publisher, new account, branch or PR was used. Macro carries documentation and evidence; executable Terminal source remains in Terminal.

## 2. User-visible correction

The source trace found that numeric type alone was being treated as a UTC declaration. Several existing intraday producers instead encode market-local wall-clock coordinates as display epochs; crypto-shaped coordinates use a different basis. The reader contract has no verified timezone field. Its `basis` describes quote transport, not bar time. The same formatter also dropped seconds from every numeric coordinate.

| Case | Implemented keep/change decision |
| --- | --- |
| Numeric coordinate | Preserve plotted date/clock components and display **Chart time / 图表时间**, with no universal UTC suffix |
| 1s, 5s, 15s, 30s | Retain seconds using the existing `isSecondTf` registry; update the existing prior-range tooltip too |
| Minute/hour and legacy caller | Preserve minute precision |
| Daily business date | Preserve date-only output, without an intraday qualifier or false offset conversion |
| Invalid numeric time | Preserve the formatter's unavailable result and existing localized Not stated reader copy |
| Accessible time description | Link the semantic time element to its visible qualifier; add no unverified UTC/Z machine-readable instant |
| Expanded help | Explain that this view does not specify the timezone and bar time does not establish freshness |
| Historical navigation | Preserve source coordinates and selected-bar identity; new browser evidence checks Previous → Latest and historical calendar withholding |

Changed runtime paths: [VisualIntelligencePanel.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/components/VisualIntelligencePanel.tsx), [visualIntelligence.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/lib/visualIntelligence.ts), [visualIntelligenceCopy.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/lib/visualIntelligenceCopy.ts). The earlier disclosure/scroll/focus hook and 44px CSS remain unchanged. No second conversion, symbol/venue/browser heuristic, data feed, cache, preference store, API field or auth effect is introduced.

The prior implementation still preserves logically open reader disclosures, internal scroll and valid focus across rail/inline/focused-host transitions, resets presentation on identity change or explicit dismissal, and respects the incumbent Close and Candle settings handoffs. Its [historical original record](IMPLEMENTATION_CONTINUATION_20261104.md) retains its exact earlier evidence.

## 3. Verification and evidence

| Check | Actual result and boundary |
| --- | --- |
| Precision regression on unchanged source | 5 failures: four supported second intervals and prior-range tooltip; 11 other new cases already passed |
| Focused unit/DOM | **57 passed**: 16 clock cases, 19 incumbent visual cases, 22 presentation cases |
| Combined browser matrix | **77 passed, 16 intentional viewport skips, 0 failures, 0 flaky**, no retries |
| New versus incumbent execution | 20 new clock executions plus all 57 earlier reader regressions on the updated source |
| Browser start/duration | `2026-11-04T04:50:10.105Z`; 313.732 seconds |
| Static | Scoped ESLint and `tsc --noEmit --incremental false` passed |
| Source/diff | All nine tested source/test hashes unchanged after verification; diff check and scoped diff review passed |
| Visual | All eight new raw EN/ZH PNGs inspected; seconds, qualifier and 320px wrapping readable |
| Cleanup | Test listener on port 3276 ended; test-generated legacy crops restored to their existing HEAD bytes |

The actual routes run locally with deterministic bars. Viewports are 1440×900, 820×1180, 390×844 and the additional 320×844 fine-pointer case. Screenshot dimensions describe captured reader elements, not necessarily the viewport. Desktop images show the viewport-limited scroller; expanded tablet/mobile images expose the full explanation.

[Compact canonical receipt](evidence/chart_time_receipt.json) · [Full Terminal verification](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/docs/pr-crops/d06-chart-time/verification.json) · [Complete browser JSON](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/docs/pr-crops/d06-chart-time/browser-report.json) · [Unit regressions](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/lib/__tests__/chartContextTime.test.ts) · [Browser regressions](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/0cf50dc0c7db259b284b48632df3f05fcb0fb7b7/terminal/e2e/chart-context-time.spec.ts).

| Captures | English | Chinese |
| --- | --- | --- |
| Desktop reader | [EN](evidence/chart_time/chart-time-desktop-en.png) | [ZH](evidence/chart_time/chart-time-desktop-zh.png) |
| Tablet reader | [EN](evidence/chart_time/chart-time-tablet-en.png) | [ZH](evidence/chart_time/chart-time-tablet-zh.png) |
| Mobile reader | [EN](evidence/chart_time/chart-time-mobile-en.png) | [ZH](evidence/chart_time/chart-time-mobile-zh.png) |
| 320px fine pointer | [EN](evidence/chart_time/chart-time-320-en.png) | [ZH](evidence/chart_time/chart-time-320-zh.png) |

The local read-only source/test adviser found no blocking defect. This is optional technical advice, not GitHub approval or a Fabric execution receipt. New coordinate cases preserve supplied regional/DST-shaped components; they do not verify upstream DST conversion, calendars or timezone provenance. New navigation cases do not independently exercise Next/replay; those remain retained behavior with earlier regression coverage. The new narrow geometry check covers rendered collapsed controls, not every expanded target or physical touch.

Hosted CI belongs to the exact new head. The first readback showed queued CodeQL checks, not completion. The incumbent unit workflow recaptures exact-checkout visual evidence before the full suite; D06 did not rewrite the shared historical EVIDENCE.yml. At05:08UTC, CI run41776880568 was queued on the exact new head; CodeQL had two success checks,one neutral check and one queued analysis. These are observed pending states,not a pass or an assumed infrastructure fault. [Exact readback](evidence/chart_time_receipt.json) records run IDs.

## 4. Acceptance, migration and remaining owners

The 75 migration IDs are unchanged. **HIST02** now has partial local-fixture evidence for avoiding a universal UTC claim, preserving seconds and daily dates, and keeping the inspected coordinate. This gives **10 partial cases, 65 specified but unexecuted, zero complete-case passes**. Existing A11Y02 partial coverage gains the visible/associated localized clock qualifier and narrow wrapping; full language/theme/contrast/expanded-target acceptance remains outstanding.

The complete specification still retains all nine route families, 76 existing capability groups (40 RETAIN, 35 IMPROVE, one BLOCKED_DATA), six separately proposed extensions, 99 drawing tools, 29 indicators, five suites/31 modules, 15 research panes, 19 intervals and nine chart types. No route, feature or owner was removed. All 64 earlier beta/Paper/local images remain byte-identical; the eight new captures bring the raw image count to 72.

| Remaining boundary | Owner and next action |
| --- | --- |
| Current-head hosted CI | Observe the existing run on this head; diagnose any concrete failure on this carrier. No duplicate dispatch or idle watcher is claimed |
| Formal approval where binding | Actual eligible non-author under branch/CODEOWNERS policy; self-QA and native advice are not approval |
| Final shell-dependent composition | F01/F02 provide a verified released joint v1; D06 then consumes exact slots/tokens/return semantics with existing owners |
| Paper editable after-design | Establish exact D06/C4 account/app/target admission; preserve live writers and original unresolved operations |
| Timezone/freshness/PIT | Existing producer-to-reader owners supply explicit qualified basis and distinct observation/publication/availability/paint clocks; neutral copy does not certify these |
| Broader Terminal migration | Existing owners retain exact-bar AI handoff, useful-plot budget, shared rail keyboard resize, light/zoom and remaining route/data/performance tests |
| Production acceptance | Explicit release authority, actual deployment identity and served journeys; none is claimed here |

[Current foundation source and D06 boundary response](FOUNDATION_RESPONSE_20261104.md) bind F01dcba5d61/F0279ddabca: candidate.4 remains operative provisionally,candidate.5 is not adopted,and jointv1 is unreleased. The historical D06 source approval is acknowledged at its exact older head; it does not approve the new implementation. [Continuation gates](evidence/continuation_gates.json) retain exact dispositions. Exact Paper references remain [Chart Context](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-W-0), boards `1K9F-0` and `1KNZ-0`; [Intelligence](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-I-1); and the original [Refraction](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-Z-0). Rejected full-pane boards remain excluded. No Paper mutation or after-design approval was invented.

**Bounded implementation result: PROVEN_OUTCOME for source publication and scoped local verification. Broader D06: CHECKPOINTED_CONTINUATION, MISSION_COMPLETE:false.** The exact next action is current-head CI qualification and any necessary same-carrier repair; final composition and release proceed only through their existing gates. No automatic observer, future execution, Ready, merge, enqueue, relabel or deployment is claimed.
