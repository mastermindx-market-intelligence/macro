# D06 resumed implementation — reader continuity and compact-chart data clarity

**SOURCE_PUBLISHED / LOCALLY_VERIFIED / CURRENT_HEAD_CI_PENDING / RELEASE_HOLD. Overall D06 remains PARTIAL; RIG draft.** The original [Terminal Draft #1270](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1270) now holds the verified compact-chart source-state/date slice at **974128ee2f9527a9c8a1db2b78ae97fc239a9786**. This is source publication and bounded local proof, not complete D06, final design, merge, deployment or production acceptance.

The Chairman requested resumption after the prior session reached its limit. Recovery retained the same owner, managed workspace, branch, operation and publisher. Earlier reader, chart-time, feedback and language evidence remains bound to its original commits. No replacement source carrier, global lifecycle or control plane was created.

## Published behavior and proof

| Slice | User-visible outcome | Exact source/evidence |
| --- | --- | --- |
| Reader feedback | Keep the activated acknowledgement control mounted, preserve owned/outside focus, announce EN/ZH thanks, accept only the first synchronous choice, and keep the phone focus outline visible | [fed19d1a](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/fed19d1ac3aa8a716f528c8205651ff60b7b413d); [implementation and receipt](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/fed19d1ac3aa8a716f528c8205651ff60b7b413d/terminal/docs/d06-reader-feedback.md) |
| Embed content language | Declare EN or zh-CN on the existing chart and invalid-symbol roots while retaining the saved application/document language | [d73e55b5](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/d73e55b556c532d09ad144e69be0673db31d035c); [implementation and receipt](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/d73e55b556c532d09ad144e69be0673db31d035c/terminal/docs/d06-embed-language.md) |
| Embed daily dates and source states | Distinguish confirmed missing history from unavailable data; show actual latest/hovered daily dates; stop settled skeletons; provide localized status; keep attribution outside the canvas and narrow controls within their strip | [974128ee](https://github.com/mastermindx-market-intelligence/mastermind-terminal/commit/974128ee2f9527a9c8a1db2b78ae97fc239a9786); [implementation](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/974128ee2f9527a9c8a1db2b78ae97fc239a9786/terminal/docs/d06-embed-data.md); [receipt](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/974128ee2f9527a9c8a1db2b78ae97fc239a9786/terminal/docs/pr-crops/d06-embed-data/verification.json) |

The new loader treats only explicit HTTP 404 and a successful empty bars array as absence. Other failed HTTP responses, network/JSON failures, malformed envelopes, no usable rows and duplicate usable dates are unavailable. Canonical calendar validation prevents unsafe date strings from reaching the chart. Existing finite-OHLC filtering, partially usable histories and invalid-volume-to-zero fallback remain explicit; the latter is not evidence of observed zero volume.

Latest daily bar means the last normalized bar date. Crosshair OHLC uses that hovered bar's actual date. Neither claims a live quote, refresh/publication/ingestion time, source freshness, exchange-session completion or producer provenance. The date remains date-only in both tested browser timezones. Hover movement does not change the localized load-status region.

The existing same-origin request/cache/cleanup owner, symbol/range grammar, SMA controls, CTA URL, language preference, native bridge, clean/hdr/fs flags and transparency remain. No API, retry loop, feed, store or shared-shell owner is introduced.

Visual/browser checks also repaired two concrete defects: clean-mode fullscreen activation could scroll the whole 320px root sideways, and render-time reduced-motion detection caused server/client skeleton markup to differ. The existing header group now shrinks into its range strip; the existing CSS media query alone controls animation. The final date and unavailable message use the theme text color, including the light clean variant.

## Actual verification

| Proof | Result and scope |
| --- | --- |
| Earlier reader unit/DOM | 65 passed: eight feedback, 22 presentation, 16 clock and 19 incumbent visual-intelligence |
| Earlier reader combined browser | 46 passed /14 intentional skips, before the final feedback-only scroll-margin refinement |
| Earlier final feedback browser | 12 passed, zero failures/skips/flaky; EN/ZH × Useful/Unclear × three viewports |
| Earlier embed-language browser | 18 passed, with 30 language-state observations; six baseline language failures retained |
| New unchanged-source baseline | Two EN/ZH failures demonstrate HTTP 503 mislabeled as no history |
| New data-helper unit tests | **47 passed, zero failed** |
| First new full browser attempt | 38 passed /one failed; 320px root scrolling and recorded hydration mismatch led to repairs |
| Repaired full browser run | **39 passed**, zero failures/skips/flaky:21 new data/variant executions plus 18 existing language regressions |
| Final color refinement | **Nine overlapping ready/compact executions passed** after the final two text-color changes; includes three light clean unavailable views |
| Contrast |18 computed-color observations, 15 for visible text and three for hidden-header fixtures; minimum 14.053766617886108:1 on tested opaque backgrounds |
| Final static checks | TypeScript passes; four changed helpers/tests have zero lint findings; component retains the same five pre-existing offending-source signatures |
| New visual self-QA |33 success captures retained; 29 inspected, including all final ready/focus/short-mode views and two phone empty samples; three failure captures retained |
| New publication | Typed commit and same-branch push APPLIED; original workspace clean; **57/57 published blobs match** the tested local commit |

The overlapping 39- and 9-case runs are not 48 distinct cases. The full run precedes only the final date/unavailable text-color changes. The final nine cases verify those colors and their affected paths. Request interpretation, data helpers and existing language behavior did not change afterward. Earlier reader/browser counts are historical at their own exact source, not freshly rerun or summed into a new total.

The tests use actual local routes with deterministic fixtures at 1440×900, 820×1180 and 390×844; short frames are 900×300, 390×300 and 320×300. EN uses Pacific/Honolulu and ZH Pacific/Kiritimati. The minimum measured short-frame plot height is 137.859375px. Attribution is outside the canvas and retains a complete keyboard focus outline, with 24px fine-pointer and 44px coarse-pointer minimum height.

No physical-device, actual 400% zoom, screen-reader pronunciation, real native bridge, external transparent-host contrast, live-source or production qualification is inferred. Existing clean-axis palette, other small targets, zoom restrictions, missing-volume semantics and remaining combinations remain separate acceptance work. No lint suppression or replacement preference/lifecycle owner was introduced.

## Acceptance and preserved scope

The 75 migration IDs are unchanged: **12 partial local-fixture cases, 63 specified/unexecuted and zero fully qualified cases**. This slice adds partial EMBED01–02 evidence and extends existing HIST02/A11Y02–04 subsets. The updated [case ledger](evidence/migration_cases.json) preserves every complete-case requirement and prior source reference. EMBED03, DATA01/DATA04, A11Y05 and other broad cases receive no incidental new qualification.

The programme retains all nine route families, 76 existing capability groups (40 RETAIN /35 IMPROVE /one BLOCKED_DATA), six separately proposed extensions, 99 drawing tools, 29 indicators, five suites/31 modules, 15 research panes, 19 intervals and nine chart types. No removal or relocation is introduced. All 72 existing Macro images remain unchanged; new executable proof and captures remain with Terminal.

## Foundation, Paper and custody frontier

Foundation readback at **2026-11-04 07:39:09 UTC** gives F01 **dcba5d618051a1de05dbc5db08254a0fb31dfc15** and F02 **2ea60216320f2294c0f66aa43d6071e6e1d0d587**. The exact F02 [current return](https://github.com/mastermindx-market-intelligence/macro/blob/2ea60216320f2294c0f66aa43d6071e6e1d0d587/research/design_candidates/production_design_20261102/f02/RETURN_F02.md) still records original G15 EFFECT_UNKNOWN and qualified joint v1 gated. Candidate.4 remains provisional; candidate.5/prospective resize behavior is not adopted. Original F01/F02 uncertain effects remain with their original targets and owners.

Protected Mastermind procedure remains pinned to **75a6540519cf519edfef7633e74f57b68aef9329**, compatible with bootstrap major 1. Protected master advanced to 690e5316629815ae3e78f65ebdec2eb87f0cad16 without changing INDEX or required procedure files, so the valid pin was reused. Original programme input remains 6e1862867193ec6486a22001a0e4fb515da20448.

The prior actual read and desktop screenshot of [Chart Context Paper](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-W-0) remain bound to file 01M3NSZGE8JWN2EZCSF0DT05RM, page p-W-0, desktop 1K9F-0, mobile 1KNZ-0 and token hash 55dd37b7. Catalog/schema/write-binding visibility did not establish exact C4 per-seat write acceptance. No Paper prepare/edit/move/comment/canary or after-design approval is claimed. The native consumer STOP AT READ boundary remains; rejected full-pane Refraction remains excluded.

| Continuation field | Binding |
| --- | --- |
| Terminal operation | d06-terminal-reader-resilience-20261103-c4 |
| Branch | sol/web-d06-terminal-reader-resilience-20261103-c4 |
| Managed workspace | /Volumes/Mastermind/agent-workspaces/terminal/web/d06-terminal-reader-resilience-20261103-c4 |
| Published head | 974128ee2f9527a9c8a1db2b78ae97fc239a9786 |
| Macro carrier | Existing Draft #10655 / design/d06-terminal-phase2a-20261103-c4; parent ae52ee1a5118d5d169422bce98ac2f2c88409551 |
| Writer | Chairman-assigned D06 C4/Astra receiver; same workspace and publisher |
| Native advice | Two bounded read-only reasoning returns accepted / STOP; no source writes, formal approval, external messages or ongoing worker |
| Effects | Performed writes/commits/pushes reconciled; no new EFFECT_UNKNOWN |
| DO_NOT_REDO | Accepted reader/clock/feedback/language/data-state proof, prior Paper captures and retained advanced features |
| Watch state | No automatic observer or background execution registered |

## Hosted CI and remaining actions

Earlier chart-time head 0cf50dc0 completed all 17 jobs in [run 41776880568](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/41776880568). Parent d73e55b5 did not complete full qualification: its latest read showed five successful jobs, two cancelled and nine running in run 41788110415. Neither qualifies the current head.

At first publication readback, current-head [CI41793286851](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/41793286851) is pending and PR checks 41793276738 queued. Inspect these exact runs and repair a concrete regression on the original carrier; do not duplicate a run or infer a hosted pass from local results.

Both PRs remain **Draft and unarmed**. Ready/un-draft, enqueue, merge, held relabel and deployment remain held under the existing Sol/Chairman release condition. Binding branch protection, CODEOWNERS, exact-head required CI and actual non-author approvals remain. Optional reasoning and self-QA are not formal approval.

Shared-shell composition requires the actually released joint F01/F02 contract and affected-owner reconciliation. Editable Paper after-designs require exact C4/native-app/target write acceptance through the original admission owner; uncertain original effects must not be replayed. Remaining migration work retains its existing data/host/domain owners, including zoom, exact-bar AI handoff, producer freshness and public-share lifecycle.

**Bounded result: PROVEN_OUTCOME for this published implementation and scoped local verification. Broader D06 remains partial with an exact, durable continuation frontier; MISSION_COMPLETE:false.** Source publication is not user acceptance or a release action.
