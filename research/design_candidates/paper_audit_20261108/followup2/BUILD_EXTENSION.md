# Builder extensions — News count scope and Sector Dossier opening

This extends [F04 in the ten-file Paper package](https://github.com/mastermindx-market-intelligence/macro/blob/376bc2cee3641eb7f55b113210be916a8a0f85d7/research/design_candidates/paper_audit_20261108/followup/BUILD_PLAN.md). It preserves its 44px coarse-pointer, disclosure, keyboard and explicit-review requirements. The extension is attached to the same existing News Build reference in [Paper](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-3-0): parent 3H7-0, card 414-0, native SVG 417-0.

## Why this boundary needs to be explicit

A source-filtered list may be empty while the activity strip still shows reports. Those facts can both be correct: the activity reading and the visible list have different scopes. The repaired recovery specimen YN-0 makes the aggregate basis explicit with “all 2 sources.” Builders must preserve that distinction through the existing components.

## Existing source and responsibilities

All four implementation files below are byte-identical at the retained Terminal pin d7a83d3348a4fcb762d93221f19c4e94cbe4505e and the refreshed source 8fcce1194c53543361bd21dbb2e69fc6ee556152. Exact blob identities are in SOURCE_COMPARISON.json.

| Owner | Existing responsibility | Boundary to preserve |
| --- | --- | --- |
| [TickerNewsPanel.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/components/news/TickerNewsPanel.tsx) | Gives the ready snapshot's full presented rows to useNewsCatchup; passes snapshot.flow separately to NewsFlowStrip; renders catchup.visible. | Retain existing ticker, readiness, empty-state, coverage and access checks. An old-symbol flow must not appear under a new symbol. |
| [useNewsCatchup.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/components/news/useNewsCatchup.ts) | bySource filters row.source. counts increments once per classified story row. The effective review filter derives visible rows; unreadShown contains only visible New/Updated story IDs. | Do not sum item_count into catch-up chips or broaden source selection to arbitrary publishers inside grouped reports. counts and visible are distinct derivations from bySource. |
| [newsReviewState.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/lib/newsReviewState.ts) | markStoriesReviewed intersects requested IDs with presented rows, saves their [sequence, item_count] revisions and retains the first captured basis. | Advance reviewed-through only when every row in the current presented page is Reviewed. This is not a receipt that all historical feed content was reviewed. |
| [NewsFlowStrip.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/components/news/NewsFlowStrip.tsx) | Uses supplied reports_24h, comparison, history and provenance, with partial coverage taking precedence. | Local source/review filtering does not recompute the supplied flow count, historical comparison or source/clock basis. |

The existing hook also preserves the current user owner and rights context, merges the newest saved owner state before writing, and reads the result back through its current storage mode. Preserve that owner and session fallback. Do not introduce a second review store, request queue, receipt type or filter owner.

## Small presentation extension

At the existing TickerNewsPanel boundary, derive the active source and effective review filter from catchup.source and catchup.filter. When a review-state filter is active, label the report reading “Feed total” / “资讯流总计”. When only the source filter is active, the existing count-basis line may use “all N sources” / “全部 N 个来源”, as in the repaired recovery specimen. Both treatments make the supplied aggregate distinct from the filtered story rows.
Use one fitting scope treatment, not both. Keep the actual publication window, coverage warning and counted-at basis. Do not infer the number of covered sources from visible rows. A source included in the count's coverage may contribute no reports during its window. No new API data or count calculation is needed.

Put the new bilingual chrome in the existing [newsFlowLex.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/lib/newsFlowLex.ts) owner. Preserve publisher-language headlines and the existing report singular/plural keys. The proposed conditional scope label is not implemented by this Paper patch.

## Worked acceptance fixture

This is a synthetic, internally consistent fixture, not a real feed or market claim. Its aggregate is supplied independently; the equality to the three item counts below is not a general algorithm for deriving feed totals.

- One ready, admitted ticker/editorial snapshot; full presented page contains A, B and C.
- Supplied activity: 8 reports in 24h, with its own original comparison, source coverage and counted-at time.
- No previous marks or reviewed-through receipt.

| Story | row.source | Initial sequence | item_count | Initial review state |
| --- | --- | --- | --- | --- |
| A | benzinga | 12 | 3 | New |
| B | benzinga | 11 | 2 | New |
| C | dowjones | 10 | 3 | New |

1. Select Benzinga. A/B are visible; catch-up counts two New story rows. The activity strip still shows eight reports with its explicit feed scope and unchanged source/time/coverage.
2. Activate Mark shown. Only A/B receive their presented revision pairs and first captured evidence bases. C remains unreviewed. The presented-page reviewed-through receipt stays null.
3. Clear the source filter. A/B are Reviewed; C remains New. The aggregate report reading still comes from the supplied flow object.
4. Accept a later correction of A at sequence 13 with the same item_count 3. A is Updated through the existing revision comparison. Its first captured basis remains byte-identical.
5. Repeat the boundary with the effective review-status filter. Hidden or ineligible story IDs are never selected by Mark shown, and completion of a subset never implies completion of the current presented page.
6. Verify account/rights changes and the existing saved/session mode readback. Opening a report, filtering, returning or closing details never calls markStory/markShown.

The inspected [AC-E13-04 test](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/lib/__tests__/newsCatchupPanel.test.tsx) already covers the supplied row.source filter and local summary. Add the combined activity/filter/review case to the existing panel test seam; do not replace that accepted contract. The test was inspected, not rerun here.

## Required consumer proof

Verify the conditional scope wording and unchanged supplied activity through the actual TickerNewsPanel, then verify the real review revision/readback path. Cover source and review filters, grouped stories, hidden rows, a later correction, account/rights changes, missing/partial flow, and a stale-symbol snapshot. Retain the previous F04 keyboard, touch, disclosure, focus, localization and receipt requirements.

Paper proof for this delta is limited to the 360px recovery state, the 612px Build card, exact Text readback and preservation of existing child IDs/JSX. The SVG is a static explanation of existing ownership and the synthetic acceptance fixture; it introduces no interaction or runtime owner.

## F06 extension — a Dossier action must open the inline Dossier

### Source and release status

The relevant native workspace is [templates/si_workspace.js at #10703 head9fc460ff](https://github.com/mastermindx-market-intelligence/macro/blob/9fc460ff36345387c3a2c5435b079852e8488da0/templates/si_workspace.js), blob ac426abc3a8a49a6d1023cc53b8eedb00a23c57a. PR#10703 remains draft/open/unmerged. Its Dossier dependency [#10707](https://github.com/mastermindx-market-intelligence/macro/pull/10707) remains draft/open/unmerged at74930f6931773b23072f91590319dc39fe5a7d07. This describes a proposed R4 action binding against those draft sources. It does not make them a released integration or relax their holds.

The new note is in [Sector Build](https://app.paper.design/file/01M6FAXA774QT1VRDMAG7DFQ2W/p-5-0), parent GYT-0, card HBL-0. The existing G4P/BML acceptance limits, GPL comparison-return proposal and all qualified measurement fixtures remain intact.

### Existing functions have distinct outcomes

| Existing seam | Observed source behavior | Consequence for the R4 action |
| --- | --- | --- |
| SectorCentralOpenCycle(id, trigger) | Captures the current origin/trigger, creates a Cycles entry with cycles:null, activates Cycles, focuses its heading, saves the entry and returns true. | A true return proves accepted navigation, not an open or source-qualified Dossier. |
| refreshDossier() | On a new entry, reads entry.dossier.open into the inline #sc-dossier disclosure. Without an opening state it remains closed. | The intended Dossier opening must be carried through this existing owner; navigation alone is insufficient. |
| syncCycleContext() / dossierAccess() | Retain the actual SectorCyclesApply receipt, identity and verified publication/core evidence. | Keep pending, unavailable and selection outcomes. Do not substitute the previous Energy/default component. |
| refreshDossier() mount checks | Rejoin current entry/href, subject/family and source publication before calling the existing component. | Never bypass these checks with a direct mount or treat a boolean return as the mount receipt. |
| dossierOptions().onOpenCycles | Closes the inline Dossier, saves the entry and focuses sc-cycle-heading. | Use this existing return action. It is distinct from arbitrary disclosure-close gestures. |
| sc-cycle-return | Uses the qualified captured Central origin. | Ordered R4 A/B and full comparison-basis restoration still require the separately specified GPL extension. |

### Implementation boundary

Bind the retained R4 Dossier action to the selected row's admitted native ID and actual invoking control. Extend the existing SectorCentralOpenCycle entry path to carry the inline-Dossier opening intention through its current dossier state and refreshDossier owner. Keep the existing state shape and its validation; do not invent a second route, modal, navigation store or restoration service. Do not infer an identifier from a translated display label.

The component may appear only after the current identity, source publication, applied native selection and matching entry/subject/family checks agree. Preserve the existing pending and unavailable presentations while those conditions are unresolved. A later selection or entry supersedes an earlier loading intention.

### Required consumer proof

Start with ordered A=Energy and B=Technology while the native Cycles view last showed Energy. Activate the Technology Dossier action and retain its actual trigger/context. Prove all of the following:

1. The new native entry requests Technology through its admitted identifier.
2. The Technology Dossier actually opens with the qualified subject, family and publication. Observing SectorCentralOpenCycle()===true does not satisfy this check.
3. Pending, missing, denied or mismatched evidence never paints the Energy/default Dossier as Technology. Existing unavailable and access semantics remain intact.
4. A newer selection during loading makes the earlier opening obsolete.
5. The Dossier-to-Cycles action closes the inline component and focuses sc-cycle-heading through the existing callback.
6. The subsequent Central return uses the existing qualified origin. The ordered pair and full basis are proved only when GPL's native and parent validators, later-intent checks and partial-result handling are implemented and qualified together.

This is an implementation instruction for an unbound design action, not a claim that an implemented R4 action is broken. No native consumer, draft PR, release control or production source was changed by the Paper edit.
