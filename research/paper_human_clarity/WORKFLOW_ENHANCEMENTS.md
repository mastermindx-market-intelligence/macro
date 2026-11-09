# Paper workflow enhancements — builder and architecture guide

Status: native Paper design work verified through 9 November 2026. News has 20 contextual product states; International has 32 calculation-help states, 36 result/qualification states and 16 tool-method states. A second portfolio pass corrected current Ontology, Prophet, OS and Popup surfaces. The shared law includes current-variant and claim consistency. These are design deliverables; runtime navigation, deployment and production acceptance are not claimed.

## Design authority and separation

Use the human-clarity law in [DESIGN_DOCTRINE](../../docs/DESIGN_DOCTRINE.md) and the existing [portfolio build guide](PORTFOLIO_BUILD_GUIDE.md). Product frames contain the answer, action, necessary qualification and recovery. Requested help explains one question. Formulas, source schemas, architecture, lifecycle behavior and acceptance evidence live in this guide and the preservation registers.

The new News product page p-5 owns the Activity and return layout. The independent full News rail27L remains on product p-2. Earlier compact count views2G9/2JL and count-help studies2NG/2OM are explicitly marked references on p-4, under 3H4/40Y; preserve their other fixtures and edge cases without treating them as another current layout. The older reading-layout proposal is now a Build reference; its publisher-return, missing-story, rights and review conditions remain useful requirements, but its expanded count layout is superseded.

| Surface | Paper file / page | Current design roots |
|---|---|---|
| International calculation help | 01M3P1TW5Y3XWQC37ADDS8K5AG / p-N-0 | RKV-0;32 frames:4 indexes, 20 added-topic bodies, 4 comparison-origin return calculations and 4 index-origin return calculations |
| International Library destinations | International / p-O-0 | RVI-0;36 result, qualification and contextual-return frames |
| International tool methods | International / p-P-0 | S89-0;16 frames across 4 tools, EN/ZH and light/dark |
| News Activity and contextual returns | 01M5EXPMQTSBFBAM8KKG83FTZH / p-5-0 | 3HH-0; exact state/control IDs in WORKFLOW_ENHANCEMENT_REGISTER.json |
| Publisher-return conditions, original layout | News / p-3-0, Build | 2RL-0 under 3H0-0; reference, not current product composition |

[International help](https://app.paper.design/file/01M3P1TW5Y3XWQC37ADDS8K5AG/p-N-0) · [News product design](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-5-0) · [News Build references](https://app.paper.design/file/01M5EXPMQTSBFBAM8KKG83FTZH/p-3-0).

## 1. Calculation topics

The six-topic Methods index now has a rendered body for every topic. The five added bodies are Attention ordering, Dates and revisions, Unavailable readings, Scenarios and replay, and Transmission responses. Each has English/Chinese and light/dark native designs at 390px. Existing O17/O23 return-calculation and O1H/O2D index roots moved intact from p-J to p-N; their missing theme counterparts were added. Separate return-calculation examples show both comparison-origin and Methods-index-origin navigation in all four locale/theme combinations. The content and calculation are shared; the back target follows the actual opener.

These five topics preserve the R14 method family. They do not redefine R10 analytics, recomputed history or source qualification. Launch a topic only from a context that actually uses that contract.

### Navigation and accessibility

Reuse the incumbent workspace/help owner. Topic → Methods restores focus to the selected index row. Index → Sources and method restores its invoking control. Exiting help restores the originating research screen and valid scroll/reading anchor. Preserve market/issuer, tool/question, period and local-session date, currency/return basis, reference snapshot/vintage, locale, theme, source selection and scroll.

The exact index rows, body destinations and native theme/context variants are recorded in INTERNATIONAL_METHOD_BINDINGS.json. Native designs are not executable routing proof. The32 calculation-help frames cover the index, six topic bodies and the two return-calculation entry contexts in EN/ZH and light/dark. Do not send an index-launched topic back to a comparison screen. View source dates must use the invoking source/date context, not an unrelated fixed Japan specimen.

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

Preserve the original seven-count history; 3OZ-0 is an additional discovered risk-card action. The following eight observed origins now have native result designs. All inspected origins show Japan/JP research context; none establishes an issuer context. Frozen R14 p-I-0 and another writer’s newer scanner p-L-0 remain separate work surfaces.

| Entry / action container | Origin board / page | Selected tool | Immediate return |
|---|---|---|---|
| P7-0 / P6-0 | L9-0 / p-4-0 | risk_track_record | History & scenarios |
| 2Z2-0 / 2Z1-0 | 2XD-0 / p-4-0 | risk_track_record | History & scenarios |
| 39H-0 / 39G-0 | 38A-0 / p-5-0 | trade_supply_links | Trace the pressure |
| 3EO-0 / 3EN-0 | 3DH-0 / p-5-0 | trade_supply_links | Trace the pressure |
| 3II-0 / 3IH-0 | 3HB-0 / p-5-0 | trade_supply_links | Trace the pressure |
| 3KZ-0 / 3KY-0 | 3JZ-0 / p-5-0 | recovery_quality | Check the recovery |
| 3OS-0 / 3OR-0 | 3NZ-0 / p-5-0 | cross_market_correlation | Challenge the conclusion |
| 3OZ-0 / 3OY-0 | 3NZ-0 / p-5-0 | risk_track_record | Challenge the conclusion |

Result → Method opens only that tool’s explanation. Back/Escape from Method restores the same result state, snapshot and method opener. Result back restores its immediate subgroup or History screen, valid scroll and invoking control. The existing subgroup Back to library control then restores the retained search. Preserve locale/theme, market, tool and source qualifications; do not create a second navigation owner.

RVI-0 contains 16 primary locale/theme examples and 20 focused qualification/return examples, including all four locale/theme History-origin variants. The latter cover insufficient matched history, recovery unavailable/not applicable, accruing/no-warning/pending-warning outcomes, empty/restricted relationships and the distinct History origin. They are illustrative states. The recovery price/breadth-supported plus missing-risk combination is constructed to expose a source-contract gap; it is not a live Japan assessment. No numeric result or provider link was invented. S89-0 contains each tool method in all four EN/ZH and light/dark combinations.

### Correlation

The incumbent correlation_matrix uses weekly Friday-end USD returns. Display available cells, leave missing cells unavailable and show insufficient observations distinctly. Do not show a regime selector, local-currency switch, pairwise count or exact endpoint without a real calculation/adapter contract. A pooled matrix does not establish regime stability, and lower correlation is not a safety conclusion.

### Recovery

Preserve the primary price state. assess_recovery is a qualifier and returns an empty object outside recovery. Its evidence separates price repair, peer breadth and external risk. Current missing-risk input can leave external_hot/external_rising false and still produce recovery_confirmed; the view must not turn absent risk evidence into “Clear.” Qualify the owner assessment or repair that source contract before presenting full confirmation. Distinguish partial evidence, outside-recovery not-applicable and unavailable assessment. An empty assessment object alone cannot establish not-applicable: the current function also returns an empty object for absent or malformed primary state. Not-applicable needs a qualified, recognized primary state outside recovery; missing, invalid or unqualified primary data remains unavailable.

### Risk track record

Use a read-only published projection of the incumbent per-market forward log. Never append logs or invoke nightly governance effects from the UI. n_graded/n_alerts count logged daily observations with overlapping horizons, not independent warning episodes. Grading waits until the longest21-session horizon matures. The adverse outcome is minimum subsequent close versus the warning-date base close; label it “Worst close vs warning date,” not generic peak-to-trough drawdown.

Keep recent_mistakes separate from a full ledger, avoid reconstructing exact false alarms from rounded precision, and preserve logged_at/source provenance. asof alone does not prove user availability at that time. Separate accruing, successfully queried no-warning periods, pending warning outcomes, unavailable/timing-unqualified records and recomputed history. The incumbent reader returns an empty list for an absent ledger, and scorecard fallback can report accruing after read failure or when no rows have matured. That label alone cannot establish a valid collecting state. Accruing requires a successful qualified ledger read with recorded observations and no mature outcomes. No recorded warnings requires successful selected-period coverage qualification and absence of all warning rows, including immature rows; n_alerts counts only graded alerts. A valid empty ledger does not prove the period was monitored. Mature calm rows can coexist with recorded warnings whose21-session windows remain unfinished: use the distinct No warning outcomes yet state. Internal can_force is not a trading recommendation or UI authorization.

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

## 4. Portfolio second pass and preservation

- **Ontology:** AT4 and the selected-oil-evidence section of 44L now show each metric once. Exact17.783% is promoted from the original table; +0.769 remains a raw-unit MA50 change, with strict >25% and >0 thresholds and the both-required condition. Duplicate tables4KR/49W and Required tests cards 4MC/4AJ moved intact to AXF-0 under ASY-0 on p-6. Mechanism/5–60 calendar-day lag, source dates, page-comparison limits and carried-forward-data qualifications remain. Source details use human labels; raw field mappings and the governing Macro 338a1085 observation/MA50 contract remain in AUR-0 and AXF-0. This is a design-contract refinement, not a fresh runtime numeric audit.
- **Prophet:** Y1G-0 now distinguishes pending confirmation, confirmed security membership, refusal and unresolved result without promises of background continuation, once-only writes or durable decision notes. Original copy and removed footers are in1CBX-0 under 15E0-0 on p-E. The governing 13L8/13QZ/13RA/13RE contract supplies no durable operation or Prophet object ID. A membership read does not resolve an outstanding write or authorize retry. Preserve the original account, list, securities, attempt time and the distinction between confirmed readBackAt and membership observedAt. Closing a pane must not be presented as proof that work continues; any persistence/continuation gap remains an implementation requirement of the incumbent owner.
- **OS:** exact architecture note TWB-0 moved from TR7’s readiness detail into ZMN-0 under existing PBR-0 on p-E. The actual operational evidence, permissions and uncertain-effect restrictions remain.
- **Popups:** original 9TH/9ZG forecast studies moved intact from product p-6 to AZR/AZV on Build p-8. Current observed-only US designs are A5I/A7G. Their sample labels remain; construction/release instructions moved into the same Build reference. The proposed2.4–5.6%/9–12% ranges and stress-chart semantics are preserved, not accepted as outputs. Existing rights, validation, original-observer and #8186 hold requirements remain; no hold was cleared.
- **International entry screens:** redundant slogans and the owning-engine footer moved intact into SDT-0 under SDM-0 on Build p-M. Correlation entries now state weekly USD scope; recorded warning outcomes replace unsupported benefit framing. Future currency/window/regime comparisons, sample/false-alarm analysis and adverse-outcome features remain specified in Build. The390px, 320px and 320px/200%-text pressure variants were inspected; no text was shrunk to fit.
- **Mastermind AI:** the bounded second pass inspected context handover, reopened-case and partial-answer states without finding a new confirmed defect. This does not claim a fresh full-file audit.

The current directory remains PORTFOLIO_DISPOSITIONS.md. This phase extends its evidence; it does not create a second lifecycle or design system. Original source wording, exact moves and current node bindings are in WORKFLOW_ENHANCEMENT_REGISTER.json.

## 5. Implementation order and acceptance

1. Bind the completed help index and bodies through the existing workspace owner; preserve the native locale/theme and origin-specific back behavior, and implement focus restoration.
2. Replace the News detail boolean with local panes, keep one snapshot owner, and bind all values to the same flow. Reuse existing publisher/review behavior.
3. Add qualified International result presentations through the existing resolver and actual rendered regions. Implement missing adapters before advertising routes available.
4. Verify the real consumer path: keyboard/touch/IME; source and review independence; symbol/editorial-view/rights changes; no-record versus zero; partial versus unavailable; snapshot refresh versus stream interruption; same scope/locale/theme on return.
5. Verify source-reference mismatch, absent risk, immature forward outcomes, empty documented relationships and insufficient matched observations. Assert that no fabricated value or method-only destination satisfies a result route.
6. Perform native browser/runtime proof against the exact implementation head. Paper screenshots prove the design composition, not runtime execution.

Before accepting a touched family, apply DESIGN_DOCTRINE §8’s current-variant check: identify the current target, reconcile shared fixture values across views, and ensure shorter assurances do not exceed the governing behavior contract. The canonical Paper law remains9X3-0; its content-fit carrier is now ANF-0 and the added acceptance text is AND-0. The installed Paper skill already points builders to the doctrine and separation/preservation workflow; do not duplicate this rule in another control plane.

Native Paper changes, source preservation, visual checks and their limits are recorded in WORKFLOW_ENHANCEMENT_REGISTER.json. All owned edited roots were released after native review. Keep implementation/source details here; do not paste this guide into product frames.
