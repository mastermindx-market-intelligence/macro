# F04 extension — feed activity, filtered stories and explicit review

This extends [F04 in the ten-file Paper package](https://github.com/mastermindx-market-intelligence/macro/blob/376bc2cee3641eb7f55b113210be916a8a0f85d7/research/design_candidates/paper_audit_20261108/followup/BUILD_PLAN.md). It preserves its 44px coarse-pointer, disclosure, keyboard and explicit-review requirements. The extension is attached to the same existing News Build reference in [Paper](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-3-0): parent3H7-0, card414-0, native SVG417-0.

## Why this boundary needs to be explicit

A source-filtered list may be empty while the activity strip still shows reports. Those facts can both be correct: the activity reading and the visible list have different scopes. The repaired recovery specimen YN-0 makes the aggregate basis explicit with “all 2 sources.” Builders must preserve that distinction through the existing components.

## Existing source and responsibilities

All four implementation files below are byte-identical at the retained Terminal pin d7a83d3348a4fcb762d93221f19c4e94cbe4505e and the refreshed source8fcce1194c53543361bd21dbb2e69fc6ee556152. Exact blob identities are in SOURCE_COMPARISON.json.

| Owner | Existing responsibility | Boundary to preserve |
| --- | --- | --- |
| [TickerNewsPanel.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/components/news/TickerNewsPanel.tsx) | Gives the ready snapshot's full presented rows to useNewsCatchup; passes snapshot.flow separately to NewsFlowStrip; renders catchup.visible. | Retain existing ticker, readiness, empty-state, coverage and access checks. An old-symbol flow must not appear under a new symbol. |
| [useNewsCatchup.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/components/news/useNewsCatchup.ts) | bySource filters row.source. counts increments once per classified story row. The effective review filter derives visible rows; unreadShown contains only visible New/Updated story IDs. | Do not sum item_count into catch-up chips or broaden source selection to arbitrary publishers inside grouped reports. counts and visible are distinct derivations from bySource. |
| [newsReviewState.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/lib/newsReviewState.ts) | markStoriesReviewed intersects requested IDs with presented rows, saves their [sequence, item_count] revisions and retains the first captured basis. | Advance reviewed-through only when every row in the current presented page is Reviewed. This is not a receipt that all historical feed content was reviewed. |
| [NewsFlowStrip.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/components/news/NewsFlowStrip.tsx) | Uses supplied reports_24h, comparison, history and provenance, with partial coverage taking precedence. | Local source/review filtering does not recompute the supplied flow count, historical comparison or source/clock basis. |

The existing hook also preserves the current user owner and rights context, merges the newest saved owner state before writing, and reads the result back through its current storage mode. Preserve that owner and session fallback. Do not introduce a second review store, request queue, receipt type or filter owner.

## Small presentation extension

At the existing TickerNewsPanel boundary, derive whether a source or effective review filter is active from catchup.source and catchup.filter. When active, make the feed scope clear beside the existing report/window wording. The recovery specimen already has a source-count basis line and uses “all N sources” / “全部 N 个来源”. Other active-filter placements may use the compact “Feed total” / “资讯流总计” label.

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
4. Accept a later correction of A at sequence13 with the same item_count3. A is Updated through the existing revision comparison. Its first captured basis remains byte-identical.
5. Repeat the boundary with the effective review-status filter. Hidden or ineligible story IDs are never selected by Mark shown, and completion of a subset never implies completion of the current presented page.
6. Verify account/rights changes and the existing saved/session mode readback. Opening a report, filtering, returning or closing details never calls markStory/markShown.

The inspected [AC-E13-04 test](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/8fcce1194c53543361bd21dbb2e69fc6ee556152/terminal/lib/__tests__/newsCatchupPanel.test.tsx) already covers the supplied row.source filter and local summary. Add the combined activity/filter/review case to the existing panel test seam; do not replace that accepted contract. The test was inspected, not rerun here.

## Required consumer proof

Verify the conditional scope wording and unchanged supplied activity through the actual TickerNewsPanel, then verify the real review revision/readback path. Cover source and review filters, grouped stories, hidden rows, a later correction, account/rights changes, missing/partial flow, and a stale-symbol snapshot. Retain the previous F04 keyboard, touch, disclosure, focus, localization and receipt requirements.

Paper proof for this delta is limited to the 360px recovery state, the612px Build card, exact Text readback and preservation of existing child IDs/JSX. The SVG is a static explanation of existing ownership and the synthetic acceptance fixture; it introduces no interaction or runtime owner.
