# Paper workflow enhancements — builder and architecture guide

Status: active design work. Calculation-topic and News designs have native Paper proof. International result destinations are the next implementation phase. These are design deliverables; runtime navigation, deployment and production acceptance are not claimed.

## Design authority and separation

Use the human-clarity law in [DESIGN_DOCTRINE](../../docs/DESIGN_DOCTRINE.md) and the existing [portfolio build guide](PORTFOLIO_BUILD_GUIDE.md). Product frames contain the answer, action, necessary qualification and recovery. Requested help explains one question. Formulas, source schemas, architecture, lifecycle behavior and acceptance evidence live in this guide and the preservation registers.

The new News product page owns the Activity and return layout. The older reading-layout proposal is now a Build reference; its publisher-return, missing-story, rights and review conditions remain useful requirements, but its expanded count layout is superseded.

| Surface | Paper file / page | Current design roots |
|---|---|---|
| International calculation topics | 01M3P1TW5Y3XWQC37ADDS8K5AG / p-N-0 | RKV-0; 20 topic frames in INTERNATIONAL_METHOD_BINDINGS.json |
| News Activity and contextual returns | 01M5EXPMQTSBFBAM8KKG83FTZH / p-5-0 | 3HH-0; exact state/control IDs in WORKFLOW_ENHANCEMENT_REGISTER.json |
| Publisher-return conditions, original layout | News / p-3-0, Build | 2RL-0 under 3H0-0; reference, not current product composition |

[International help](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-N-0) · [News product design](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-5-0) · [News Build references](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-3-0).

## 1. Calculation topics

The existing six-topic Methods index had only the return-calculation body rendered. The five additional bodies are Attention ordering, Dates and revisions, Unavailable readings, Scenarios and replay, and Transmission responses. Each now has English/Chinese and light/dark native designs at 390px. The existing return examples and index patterns are retained.

These five topics preserve the R14 method family. They do not redefine R10 analytics, recomputed history or source qualification. Launch a topic only from a context that actually uses that contract.

### Navigation and accessibility

Reuse the incumbent workspace/help owner. Topic → Methods restores focus to the selected index row. Index → Sources and method restores its invoking control. Exiting help restores the originating research screen and valid scroll/reading anchor. Preserve market/issuer, tool/question, period and local-session date, currency/return basis, reference snapshot/vintage, locale, theme, source selection and scroll.

The exact index rows and new destinations are recorded in INTERNATIONAL_METHOD_BINDINGS.json. Native designs are not executable routing proof. Existing index/return designs have a narrower native theme set than the new topic bodies; complete their companion theme states before claiming full journey theme proof.

### Preserved calculation and qualification rules

- Attention uses |standardized USD move| × |standardized divergence| × US-exposure weight; liquidity breaks ties. Divergence-only sorting uses absolute divergence. Label the active ordering. The illustrated score requires 60 aligned sessions; insufficient-history markets remain visible without score/rank.
- Distinguish data period, provider release, collection qualification and snapshot publication. UTC timestamps coexist with local market-session dates. A newer snapshot does not make old source data current.
- Missing, stale, restricted and unscored are distinct. Freshness is source-specific. Missing index close removes move ranking; late FX qualifies USD while local returns can remain. Required unscored Q1–Q3 readings suppress transmission. Qualified/stale/partial inputs cap stance at Watch. Quarterly BIS background is never forward-filled.
- Scenario estimates are conditional. A range crossing zero receives no directional score. R14 replay displays the selected stored snapshot as it was available then; later corrections do not rewrite it. R10 recomputed history may contain revised inputs and must remain separate. Watches recheck snapshots and notify only.
- Market-response channels have their own evidence and US response windows. Missing observations or incomplete windows remain Pending/unavailable. No response requires a completed window and required observations; it does not disprove the channel. Lending exposure is structural and has no same-day response test.

All original method text remains in INTERNATIONAL_METHOD_BINDINGS.json. Shorter help copy does not relax these behavior rules.

## 2. News: one context and one pane owner

The intended flow is Headlines → Activity → Counted sources or How counts work → Activity → Headlines. This is local presentation state inside the existing News component. Do not add a global modal service, independent route registry, count-fetch service or a second feed owner.

The current Terminal implementation has one details-open boolean and a trigger-focused Escape assumption because its original details have no focusable children. The new help actions require an explicit local pane owner and descendant-aware keyboard handling.

### Transition contract

| Action | Result and focus |
|---|---|
| Open Activity | Preserve headline filter, source selection, valid expanded identity and reading anchor; focus the Activity heading/control as appropriate |
| Open Counted sources / How counts work | Keep the same active flow instance; focus the help heading |
| Back or Escape from help | Return one level to Activity; restore the specific invoking help control |
| Escape from Activity | Return to Headlines and focus the Activity opener |
| Explicit Headlines action | Restore the valid story/reading anchor and scroll; use the feed heading if that story no longer exists |
| Open a publisher | Reuse the existing external-link policy; retain the mounted News context |
| Return from the publisher | Revalidate the story, rights and editorial view before restoring a valid anchor |
| Mark reviewed | Perform only the explicit review action; navigation/open/close never marks a story reviewed |

Do not consume Escape during IME composition. Touch and keyboard share the same state owner. The native focus examples illustrate the explicit Headlines action and help return; they do not claim executed browser focus behavior.

### Snapshot, filter and failure behavior

Use the flow from the current accepted snapshot. Security/editorial-view changes invalidate old help and reading identities. All count, history, source and time-basis fields must come from that same flow instance.

- Partial coverage retains available counts and a dashed rolling-24h mark, shows “Counts may be incomplete,” and suppresses the activity comparison. A supplied median may remain as a qualified baseline; it does not prove complete prior coverage.
- A stream interruption retains the last accepted snapshot and actual count time. Show “Updates interrupted.” Do not invent a staleness threshold or call old counts live.
- Upsert/remove/reconnect events can request a new first-page snapshot. Counts change when a qualified replacement snapshot is accepted; SSE does not directly carry the flow aggregate.
- A failed snapshot request, including a failed background request, currently sets the whole panel unavailable and hides rows when not ready. This is different from stream interruption.
- A count-calculation failure inside an otherwise ready news snapshot leaves headlines usable. Null is not zero; omit count metrics, count provenance and count-help actions. If an open count pane loses its valid flow, return safely to the available headline context.
- Rights revocation clears the snapshot and invalidates in-flight work. Manual refresh uses the existing whole-feed refresh/loading behavior; no separate count retry endpoint.
- Headline catch-up/source/review filters do not recompute flow. The count belongs to the accepted security/editorial-view snapshot before client filtering. When a filter could make this ambiguous, show concise scope at the point of interpretation.
- “Counted sources” means permitted feeds included in the count; a feed can contribute zero reports. Do not substitute whichever sources happen to be visible in filtered headlines.

The compact degraded states and partial Activity view are part of the current design. The older QO state matrix remains the detailed edge-case reference; do not create another independent state matrix.

### Shared design fixture and chart repair

The journey preserves the established Paper AAPL fixture: 13 reports in rolling24h, 9 stories, 91 reports in rolling7d, 9 days on record, 13 reports dated by publication time, Benzinga and GlobeNewswire, and the original displayed count time.

The English chart inherited from 35X-0/39J-0 was inconsistent with the seven-day total. Both were repaired, and every new locale uses the coherent existing vector series from 1CX-0:

19 unrecorded slots, then [11, 14, 9, 12, 16, 10, 13, 15, 12].

This is an explicitly preserved Paper design fixture derived from vector geometry, not a recovered production response. Original SVGs and the correction are retained in WORKFLOW_ENHANCEMENT_REGISTER.json. All bars and the outlined13 mark use one linear5px/report scale. The unrecorded run is not drawn as recorded-zero dots. A dashed outline is reserved for incomplete rolling24h counts.

The windows differ: daily bars are 28 UTC dates ending yesterday; reports24h and reports7d are rolling inclusive windows ending at the count time. The final seven daily bins sum87; boundary-day portions can make rolling7d91. Do not force equality between those different windows.

The pinned Terminal source-backed thin fixture is separately 2 reports / 2 stories / 7d3 / history6 with THIN_DAILY in news-flow-responsive.spec.ts. Do not describe the Paper13/91 series as that backend fixture. Real implementation tests must consume explicit timestamped fixtures and the owner payload.

### News source anchors

Terminal pin: cfe14c49f2e0166c0ded5e6f23a274bb663d0fd3.

- [NewsFlowStrip](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/cfe14c49f2e0166c0ded5e6f23a274bb663d0fd3/terminal/components/news/NewsFlowStrip.tsx): incumbent detail owner and Escape assumption.
- [useTickerNewsFeed](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/cfe14c49f2e0166c0ded5e6f23a274bb663d0fd3/terminal/components/news/useTickerNewsFeed.ts): snapshots, refresh, stream interruption, rights and identity.
- [TickerNewsPanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/cfe14c49f2e0166c0ded5e6f23a274bb663d0fd3/terminal/components/news/TickerNewsPanel.tsx): flow before client catch-up filtering.
- [Responsive fixture](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/cfe14c49f2e0166c0ded5e6f23a274bb663d0fd3/terminal/e2e/news-flow-responsive.spec.ts): source-backed FLOW_THIN.
- [Count engine](https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/engine/qbus_news_velocity.py): rolling/calendar windows, observed-history span, median and comparison rules.

## 3. International result destinations — implementation contract

Four reusable destinations cover seven recorded missing result origins plus a newly discovered eighth origin. A methods sheet cannot fulfill a promised result destination. Reuse resolve_intl_tool and the incumbent workspace controller; preserve route_state separately from data_state, verify the actual rendered target, and require matching source_reference.

| Destination | Existing origins | Incumbent capability and gap |
|---|---|---|
| Cross-market correlation | 3OS-0 | Weekly USD calculation and intl-cross-market-correlation mount exist; qualify the rendered instance. Exact pairwise sample counts, endpoints and regime comparison are not in the current payload |
| Recovery evidence | 3KZ-0 | Recovery qualifier exists; no recovery_quality Library mount. Missing external-risk input requires visible qualification |
| Risk track record | P7-0, 2Z2-0, 3OZ-0 | Forward-ledger/scorecard and Japan profile exist; no risk_track_record mount or qualified read-only presentation adapter |
| Economic links | 39H-0, 3EO-0, 3II-0 | Catalogue intent exists; no trade_supply_links mount or verified documented-relationship payload in inspected sources |

Preserve the original seven-count history; 3OZ-0 is an additional discovered risk-card action. Record every action container, text node, selected tool, origin screen, scroll and focus return. Frozen R14 and the newer scanner proposal remain separate work surfaces.

### Correlation

The incumbent correlation_matrix uses weekly Friday-end USD returns. Display available cells, leave missing cells unavailable and show insufficient observations distinctly. Do not show a regime selector, local-currency switch, pairwise count or exact endpoint without a real calculation/adapter contract. A pooled matrix does not establish regime stability, and lower correlation is not a safety conclusion.

### Recovery

Preserve the primary price state. assess_recovery is a qualifier and returns an empty object outside recovery. Its evidence separates price repair, peer breadth and external risk. Current missing-risk input can leave external_hot/external_rising false and still produce recovery_confirmed; the view must not turn absent risk evidence into “Clear.” Qualify the owner assessment or repair that source contract before presenting full confirmation. Distinguish partial evidence, outside-recovery not-applicable and unavailable assessment.

### Risk track record

Use a read-only published projection of the incumbent per-market forward log. Never append logs or invoke nightly governance effects from the UI. n_graded/n_alerts count logged daily observations with overlapping horizons, not independent warning episodes. Grading waits until the longest21-session horizon matures. The adverse outcome is minimum subsequent close versus the warning-date base close; label it “Worst close vs warning date,” not generic peak-to-trough drawdown.

Keep recent_mistakes separate from a full ledger, avoid reconstructing exact false alarms from rounded precision, and preserve logged_at/source provenance. asof alone does not prove user availability at that time. Separate accruing, successfully queried no-warning periods, unavailable/timing-unqualified records and recomputed history. Internal can_force is not a trading recommendation or UI authorization.

### Economic links

Only documented relationship records can establish trade, supply or financing exposure. Modelled pressure, listing country, correlation or an FX hypothesis cannot substitute. A typed record needs relationship type/direction, subject/counterparty identity, geographic/issuer scope, observation period, source record, publication/qualification timing, rights state and correction lineage. Values need units and direct support. No records in a qualified dataset is not “no economic exposure.” Distinguish empty, unavailable, restricted and partial coverage. Draw graph edges only when records support them.

### International source anchors

All inspected at Macro b5674d8ef898e503d6164922654f5ff89be9981c:

- lib/intl_library_view.py and lib/intl_library_mount.py: qualified routes and actual rendered-target admission.
- config/intl_library_catalogue.json: approved tool intent.
- engine/intl_performance.py: correlation payload.
- engine/intl_recovery_quality.py: primary-state/qualifier boundary and missing-risk gap.
- engine/risk_radar_intl_audit.py and engine/risk_radar_intl.py: forward ledger, grading and market profile.
- Existing INTERNATIONAL_METHOD_BINDINGS.json and PORTFOLIO_BUILD_GUIDE.md: preserved original detail and context contract.

## 4. Implementation order and acceptance

1. Bind the help index and bodies through the existing workspace owner; preserve context and implement focus restoration. Complete missing companion theme states.
2. Replace the News detail boolean with local panes, keep one snapshot owner, and bind all values to the same flow. Reuse existing publisher/review behavior.
3. Add qualified International result presentations through the existing resolver and actual rendered regions. Implement missing adapters before advertising routes available.
4. Verify the real consumer path: keyboard/touch/IME; source and review independence; symbol/editorial-view/rights changes; no-record versus zero; partial versus unavailable; snapshot refresh versus stream interruption; same scope/locale/theme on return.
5. Verify source-reference mismatch, absent risk, immature forward outcomes, empty documented relationships and insufficient matched observations. Assert that no fabricated value or method-only destination satisfies a result route.
6. Perform native browser/runtime proof against the exact implementation head. Paper screenshots prove the design composition, not runtime execution.

Native Paper changes, source preservation, visual checks and their limits are recorded in WORKFLOW_ENHANCEMENT_REGISTER.json. Keep implementation/source details here; do not paste this guide into product frames.
