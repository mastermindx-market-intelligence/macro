# Wave B seat rulings (seat fd47d431, 2026-10-12)

These rulings close section 9 of `WAVE_B_NEWS_FLOW_RAIL_SPEC_2026-10-12.md`. That spec was written by ORCH-UP and is 46,089 bytes. Copy the rulings inline into every Wave B lane commission, next to the section 0 gates.

## D-W1 Theme: ruled specimen only

DARK ships live. LIGHT ships only as the static specimen `terminal/docs/specimens/news-flow.html`. Three conditions apply:

- **The specimen is generated from the live components, never hand-written.** A test server-renders `NewsFlowStrip` and `NewsFlowTally` with the fixture props, using `react-dom/server` `renderToStaticMarkup`. The test fails if the specimen's markup differs from that render, so the specimen cannot drift away from what actually ships.
- **No light styling reaches the running app.** Light CSS lives only in the specimen's own stylesheet, scoped to the specimen. No light rule enters runtime CSS, and `lib/__tests__/tickerNewsRailMount.test.ts:47` stays green.
- **The PR body labels cells L1 to L6 as SPECIMEN.** They are never presented as live evidence.

## D-W2 Comparison thresholds: ruled, `flow_compare.v1` as written

The comparison takes the first matching row:

| Result | Condition |
|---|---|
| null | coverage is partial |
| `insufficient_history` | history is thin |
| `busier` | `r24 >= 2 * median` AND `r24 - median >= 3` |
| `quieter` | `median >= 2` AND `r24 <= median / 2` |
| `typical` | anything else |

Rules for the implementation:

- The thresholds are named module constants.
- The comparison is for display only. It never feeds ranking, sizing or gating.
- Any threshold change bumps the rule id.
- The comparison uses the exact median, never a rounded one.
- Display shows at most one decimal: a median of 2.5 renders as "2.5", never "3". This keeps the copy and the computation from disagreeing.

`test_compare_to_typical_bands` adds these rows. The fractional median is a real case, because a 28-day median is the mean of the 14th and 15th values.

| median | r24 | expected |
|---|---|---|
| 0 | 3 | busier |
| 0 | 2 | typical |
| 2.5 | 6 | busier |
| 2.5 | 5 | typical |
| 2.5 | 1 | quieter |

## D-W3 SSE: ruled, flow stays off SSE

- The terminal never increments or recomputes flow from SSE frames. The engine is the only thing that counts.
- The strip always shows its as-of time (`known_at`), so an aged count is labeled rather than hidden.
- Live ticking is a product-law question and is not part of Wave B.

## Sequencing by file ownership

File ownership was read from GitHub at about 08:2xZ on 2026-10-12.

### Terminal lanes

**B4-terminal** waits for terminal #970, which is open and accepted.
- #970 owns `terminal/components/fin/CompanyThemeContextCard.tsx` and `terminal/lib/__tests__/companyThemeContextCard.test.tsx`.
- B4-terminal branches from fresh master only after #970 merges.
- The commission uses repo-root paths, with the `terminal/` prefix.

**B3** waits for terminal #974 (U5).
- #974 owns `terminal/lib/__tests__/tickerNewsA11y.test.tsx`, and B3 fixes the U5 gaps that this file pins. So B3 branches only after #974 merges.
- B3's live proof needs B2 deployed. So B3 merges only after B2 is live.
- Until then, a response with no `flow` key leaves the strip hidden and the rest of the panel unchanged. G4 and spec section 3.1 govern; the panel is never forced into the unavailable state by a missing flow key (seat ruling on ORCH-WB open item O1, 11:2xZ).

### Macro lanes

**B4-macro** waits for #8967.
- It owns `tests/test_leadership_receipt_edge_matrix.py`, which #8967 creates.
- It branches from fresh main only after #8967 merges, never from #8967's branch.

**B1** starts after macro #8902, #8897 and #8905 merge.

**B2** may build in parallel, against B1's frozen `NewsStore.news_flow` signature and fixtures.
- It merges only after B1 lands.
- No flow count is served before B1's required `allowed_sources` lands (gate G1).

Every macro lane is also gated on heal #8960 and the G10 merges.

## Recorded only

- **Item 12:** `news_changes` is never pruned. This is an ops retention decision and is not part of Wave B.
- **ORCH-UP deviation:** the U4 lane added a per-branch refspec to the git config of the ubuntu0 host repository. The change is reversible. It is recorded here so that a future census can find it.
