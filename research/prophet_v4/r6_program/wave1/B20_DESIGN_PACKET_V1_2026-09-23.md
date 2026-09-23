# B20 — Prophet US flagship workspace design packet v1 (D09 input; document only)

**Operation:** `prophet-us-fable-meta-ceo-20260923-001`  
**Status:** DRAFT PACKET — no product code, data owner, score, permission, price, or chart is invented by this document.  
**Scope:** B20 design input for D09 steps 1–2 only.

## 0. Constraints read and binding basis

1. **Content law:** `docs/DESIGN_DOCTRINE.md` — three disclosure tiers and hard word budgets at §1 lines 19–33; stance or it does not ship at §2 lines 38–47; plain words, translated numbers, no raw slugs/internal names at §2 lines 49–74 and 75–80; one as-of and one footnote at §2 lines 82–88; honest nulls and bilingual parity at §2 lines 90–101 and §5 lines 148–162; light is a separate design target at §5 lines 163–180.
2. **System law:** `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` — archetype selection/composition process at §0 lines 21–40; token and density laws at §2 lines 93–104 and §9 lines 348–405; the nine route archetypes at §10 lines 420–490; canonical component inventory and new-component discipline at §11 lines 519–566; the light-mode component contract at §12 lines 587–613; bilingual, accessibility, and responsive law at §13–§15 lines 622–668.
3. **Navigation law:** `templates/_site_nav.html.j2` is the authenticated shell and includes the one shared menu at lines 12–20; contextual links are the only sanctioned page-local addition at lines 21–45. `templates/_navlinks.html.j2` declares itself the single source of truth at lines 1–22 and owns the inventory from line 28. `templates/navigation-refresh.css` owns nav geometry/material at lines 1–20 and 131–170. No third header, local resize, or parallel search is proposed.
4. **Theme law:** `templates/theme.css` root tokens at lines 63–79, light tokens at lines 205–245, text-grade state inks at lines 357–377, and stance semantics at lines 2703–2725. All new presentation derives from `theme.css`; this packet adds no stylesheet or token root.
5. **Executable specimen:** `mockups/design_system/specimen.html` — identity and VerdictHero at lines 187–215; component specimens at lines 348–537; light-only and 390 reductions at lines 658–693; archetype table at lines 704–714. `python3 scripts/worktree_sparse.py add mockups` materialized this file without `data/` or `site/`.
6. **Product plan:** `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/PROPHET_US_MASTER_PLAN_R6.md` — the three user jobs at §2.1 lines 52–60; six destinations and shared context at §14 lines 440–486; dark/light/desktop/mobile/coherent hydration at §15 lines 488–522; WatchStore and disabled action law at §16 lines 524–547.
7. **Incumbent payload semantics:** `templates/_prophet_card.html.j2` lines 575–677; `templates/_prophet_receipts.html.j2` lines 119–233; `templates/_us_board_cards.html.j2` lines 17–38 and 58–308; `templates/_us_prophet_plan_cards.html.j2` lines 1–136; `scripts/build_site.py` refusal generation at lines 4811–4875, stance projection at lines 4979–5039, and plan-book split at lines 5086–5127. Theme-source semantics are visible in `templates/_theme_tape.html.j2` lines 1–65 and 650–704 plus `scripts/build_site.py` lines 6089–6107.
8. **User-action owner:** `templates/watchstore.js` is the cloud seam over the same per-list blob; `templates/watchlist.js` exposes the local store, list scope, provenance generation, and sync events. Prophet only consumes this owner and performs no second save format.

STATUS: IN_PROGRESS

## 1. TASK FLOWS

The following numbered flows are the shared spine of the workspace. “Drawer: closed” means the destination list owns focus; “drawer: open” means the row remains selected and visible while the episode/dossier drawer is anchored beside it on desktop or covers the list on mobile. No flow claims a fill, position, recommendation, or ownership of an unmapped action.

1. **Market/group change → review set** — Destination: **Early Radar**. Select market context and persistent strategy in the shared header, then scan a bounded early field; change a group from the Radar context strip. Drawer: **closed**, except a long group description opens as a popover/LENS, not an episode drawer. Fields: canonical episode identity is `episode_map[p.id].ep` where available (`templates/_us_prophet_plan_cards.html.j2:24–26, 86–99`); watch/intake membership is `book.intake.early_turn_watch` (`templates/_prophet_card.html.j2:139–143`); theme/group membership is `theme_tape.*.members` and `n_members` (`templates/_theme_tape.html.j2:650–704`). Strategy-specific group economics: **UNAVAILABLE_FIELD**.
2. **Security → why now** — Destination: **All Candidates** search → **exact episode drawer**. Search a display name/ticker, open the row, and read “what changed” before any rank. Drawer: **open**. Fields: identity/name/sector/price/spark are the fail-soft candidate join at `cand_map[p.asset]` (`templates/_us_prophet_plan_cards.html.j2:14–21, 101–106, 118`); first-seen/board membership is `n.added_date` (`templates/_us_board_cards.html.j2:274–304`); changed state is `n.adjusted` (`templates/_us_board_cards.html.j2:201–210`); episode/date is `p.id`, `p.plan_asof`, or `p.recorded_at` (`templates/_us_prophet_plan_cards.html.j2:86–99, 122`). Economic event/expectation detail: **UNAVAILABLE_FIELD**.
3. **Research interest → entry permission** — Destination: **Action Desk**, with the drawer's **Entry vs research** layer open. Drawer: **open**. Fields: permission/stance comes from `p.entry_status`, falling back to `p.board_read.fields.status.value` only when available; both absent renders **No read yet**, never guessed Wait (`scripts/build_site.py:4979–5039` and `templates/_us_prophet_plan_cards.html.j2:31–36, 107–113`). Availability and actionability use `entry_signal.status` on candidates (`templates/_us_board_cards.html.j2:89–103`). Entry geometry is `p.entry_zone.low/high`, with “zone sets on confirmation” when absent (`templates/_us_prophet_plan_cards.html.j2:71–80, 119–121`; rendering contract `templates/_prophet_card.html.j2:649–663`). A strategy-specific accepted permission owner: **UNAVAILABLE_FIELD**.
4. **Risks and counterevidence** — Destination: any list; **episode drawer**. Drawer: **open**. Fields: the incumbent caution ledger maps `cand.blowoff.burst_mover`, `cand.alpha_entry == extended`, `cand.ext_z > 2`, `cand.antichase_shadow_blocked`, `cand.earnings_soon.*`, and `cand.in_blackout` to plain risk sentences (`templates/_us_prophet_plan_cards.html.j2:37–60`; sibling contract `templates/_us_board_cards.html.j2:103–107`). Refusal/non-selection reasons come from `refusal_receipts(...).groups[].en/zh/names[].why` (`scripts/build_site.py:4811–4875`; rendering `templates/_prophet_receipts.html.j2:119–159`). Severe-loss/tail estimate: **UNAVAILABLE_FIELD**.
5. **Save/manage to an intended list** — Destination: **drawer action area**; confirmation opens the WatchStore **list-scoped save sheet**. Drawer stays open until owner readback, then focus returns to its Watch button. Fields: list identity and item scope are the existing `WatchStore.lists` / `mdash.wl.<listId>.v1` blob contract (`templates/watchstore.js:182–243`); the consuming seam is `window.WL` / `window.WS` with generation provenance (`templates/watchlist.js:2111–2180`). Episode metadata is not persisted unless WatchStore already owns it; the UI labels that limit in the sheet. **D05 owns any Pass, reason, thesis, or milestone mapping.**
6. **Later inspect the original decision** — Destination: **Track Record → original decision**. The record opens the same episode drawer in historical mode; later corrections remain separate from the then-known snapshot. Drawer: **open**. Fields: current lifecycle is `p.lifecycle_state` (`templates/_us_prophet_plan_cards.html.j2:29–36, 123–126`); lifecycle counts are the published `book.lifecycle_counts`, `lifecycle_live_total`, and `lifecycle_grand_total` (`templates/_prophet_card.html.j2:139–143`; producer `scripts/build_prophet.py:2546–2557`); newer episode is `episode_map[p.id].newer` (`templates/_us_prophet_plan_cards.html.j2:24–26, 86–99`). Frozen original decision/evidence: **UNAVAILABLE_FIELD**.

## 2. INFORMATION ARCHITECTURE

The six destinations are one workspace, not six boards. The shared header persists market, strategy, observation/quote times, and the research-versus-promoted state. The strategy selector changes the economic job and horizon but never silently repairs missing sources or invents a permission. The common context strip is a quiet `.mx-callout`: one measured market/group sentence, one limitation, one `.dtp-asof`; it creates no broad macro score.

### 2.1 Action Desk — `discovery_board`

- **Primary question:** “What deserves consideration now under this strategy?”
- **Glance fields (6):** identity, strategy/horizon, availability/stance, entry-or-risk condition, leading opposing fact, next condition that changes the decision. Priority appears only where its producer field exists and is labelled as readiness, not probability.
- **Layers:** glance row → one-click drawer thesis/change + risk/refusal → entry-versus-research detail, source/observation receipts, and bounded history. Technical values and study details stay in LENS or drawer detail.
- **Empty states:** (1) “Nothing qualifies today. We will look again after the next close.” (2) “This strategy is not supported in the current market environment. You can still research its candidates.” (3) “A required source is unavailable, so we cannot state entry availability. Nothing here is a substitute read.” All are `.mx-empty` + `.mx-empty-why`; only the third uses a warning rail and removes actionable appearance.
- **Degraded/corrected/uncertain/invalidated:** required quote/source failure blocks the entry field but leaves research evidence; optional-source failure names what still works; “Corrected” sits beside the affected fact and links both generations; “No read yet”, “Forecast not calibrated”, and “Quote is stale” remain visible; invalidation changes the row to a non-action state and routes to the original decision.
- **Semantics:** rows come from the incumbent plan/candidate contracts in §1.3–1.4; counts quote the producer and never recount rows.

### 2.2 Early Radar — `discovery_board`

- **Primary question:** “What is emerging before confirmation, and why is it only being watched?”
- **Glance fields (6):** identity, producer nomination or canonical episode, first observation, development since origin, missing evidence, exact confirmation/geometry condition.
- **Layers:** glance → drawer development, group/issuer context, technical event, and monitored condition → source receipts. A four-hour slot appears only if a registered source exists; young history receives a support note, never fabricated long-history indicators.
- **Origin distinction:** canonical rows are DecisionRows with an episode mark; producer-only nominations use a distinct muted provenance mark and the sentence “Producer nomination — not yet a tracked episode.” They never borrow lifecycle/action color. `book.intake.early_turn_watch` and `episode_map[p.id]` remain separate joins.
- **Empty/degraded:** “No new nominations passed source checks.” / “The early source has not published this session.” / “History support is too thin for this name, so it stays in research only.” Unavailable continuation/economic fields say **UNAVAILABLE_FIELD** rather than zero.

### 2.3 All Candidates — `discovery_board`

- **Primary question:** “Where is every supported candidate, including the rows that did not advance?”
- **Glance fields (6):** identity, lifecycle/maturity, source availability, research status, entry status, review outcome. A null rank remains null; off-board and cap-displaced rows remain searchable.
- **Layers:** filter/search → result row → reason drawer → bounded table view/entitled detail. Default filters are strategy, availability, research/entry, lifecycle, and watch context where permitted; sector/group, completeness, and maturity are available but never become a second board.
- **Empty/degraded:** every filtered-out layer names the actual reason. “No rows match these filters.” / “This view is waiting for its required source.” / “The producer did not publish a rank; rank is not inferred.”
- **Corrected/uncertain:** the snapshot identity and correction generation are exposed before search results change; duplicate tails and partial replacements are refused. Protected facts remain absent until entitlement is established.

### 2.4 Themes & Propagation — `intelligence_desk`

- **Primary question:** “Is this group really broadening, and which companies does it actually reach?”
- **Glance fields (6):** theme/group, participation count (`on board / members`), persistence, concentration/lead contribution, direct-versus-proxy relation, and selected-company route. No company is reclassified and no second lifecycle is minted.
- **Layers:** glance theme card → member/participation table → dated relationship receipt → GMI/Theme Intelligence detail. Current-only relationships are labelled current research and never presented as a point-in-time history.
- **Empty/degraded:** “No group is turning with enough members to matter.” / “Membership is unavailable, so no member list is shown.” / “These relationships were found recently; we cannot show their history.” A one-stock group says so at glance, not in a footnote.
- **Corrected/uncertain:** membership and relationships carry source/date/coverage; proxy membership cannot appear as direct exposure; missing weights render **UNAVAILABLE_FIELD** rather than equal weights.

### 2.5 Track Record — `instrument_analyzer` (C-signal)

- **Primary question:** “What did this strategy actually do, under which population and ruler?”
- **Glance fields (6):** population/ruler, era/window, coverage, meaningful sample count, unresolved count, and route to original decision. Observational signal quality, rank quality, simulated policy value, managed plans, and user-recorded outcomes are separate tabs and are never pooled into one win rate.
- **Layers:** strategy record header → ruler tabs → original decision drawer → then-known versus later-development comparison → full receipts.
- **Empty/degraded:** “This record has not accrued enough complete outcomes yet.” / “The source era changes here, so older rows are shown separately.” / “Some outcomes remain unresolved and are counted, not dropped.”
- **Corrected/invalidated/uncertain:** the original decision stays immutable; a correction adds a later reading; an invalidated episode shows the binding reason; an unfinished horizon remains unfinished. No example score, return, or win count is invented here.

### 2.6 Health & Receipts — `intelligence_desk`

- **Primary question:** “What can this workspace know right now, and what is it missing?”
- **Glance fields (6):** owed market session, required-source freshness, identity/basis coverage, accepted publication generation, model status, and delivery age. Product correctness and evidence maturity are separate columns.
- **Layers:** impact-first health rows → affected destination/action → source receipts and operational owner route → methodology disclosure.
- **Empty/degraded:** green delivery means “the accepted artifact reached this page,” not “the market session reached you”; an owed-session warning always says that difference. Optional transcript failure removes only its panel; a stale required quote removes actionable appearance.
- **Corrected/uncertain:** same-date corrections compare generation, not date alone; duplicate tails/partial replacements refuse; model status says research, experimental, or unsupported without implying market truth.

## 3. VOCABULARY

| Internal term | EN glance label (≤4 words) | ZH label | Technical detail lives |
|---|---:|---|---|
| `ENTRY_OPEN` | Entry condition open | 入场条件开启 | Drawer entry layer: exact producer status, geometry, clocks, and owner facts |
| unavailable | Not available right now | 暂不可用 | LENS: failed or absent source, affected field, and what still works |
| experimental | Early research method | 实验性研究方法 | Drawer methodology: model version, evidence status, and limits |
| research-only | Research only | 仅供研究 | Drawer: allowed use, missing owner facts, and entry status |
| control | Comparison case | 对照情况 | Study detail: control population, era, endpoint, and receipt |
| displaced-by-cap | Reached the display limit | 达到显示上限 | All Candidates reason drawer: full cap count, exact layer, and search route |
| unscored | No score yet | 尚无评分 | Drawer: which producer did not score and why; null stays null |
| owed session | Market session pending | 市场时段待更新 | Health receipt: expected session, source clock, publication generation |
| stale quote | Quote is stale | 报价已滞后 | Drawer quote receipt: quote time, observation time, and impact on entry |
| uncalibrated forecast | Forecast not calibrated | 预测尚未校准 | Drawer forecast receipt: quantity, model status, and uncertainty limits |
| producer nomination | Producer nomination | 来源提名 | Radar receipt: producer, source time, and why it is not an episode |
| canonical episode | Tracked episode | 已跟踪轮次 | Episode drawer: immutable identity, origin, and later readings |
| research priority | Research priority | 研究优先级 | LENS: producer score meaning and “not entry permission” |
| entry permission | Entry permission | 入场许可 | Drawer entry layer: accepted strategy owner facts and current geometry |
| mandatory source unavailable | Required source missing | 必需数据缺失 | Health and empty-state receipt: source, field, impact, retry/repair owner |
| no read yet | No read yet | 暂无判读 | Drawer: which availability sources were absent; never rendered as Wait |
| corrected | Corrected | 已更正 | Beside the affected fact: previous/current generations and reason |
| invalidated | Condition ended | 条件已结束 | Original decision drawer: binding invalidation and later evidence |
| unresolved outcome | Outcome not final | 结果未定 | Track Record receipt: missing price, horizon, sequence, or source |

## 4. COMPONENT MAP

| Workspace panel / mechanism | Canonical component + specimen anchor | Notes |
|---|---|---|
| Authenticated shell, search, market menu, theme/language | PageShell/PageHeader — specimen §1 `PageShell / PageHeader` linked-by-reference lines 540–546; source `templates/_site_nav.html.j2`, `templates/_navlinks.html.j2` | No third header or local resizing; only `nav_context_links` may add a back link. |
| Persistent market + strategy context | Section header `.mx-sec` + segmented control `.segbtn` + freshness `.dtp` — specimen “Density/Composition” and “Freshness” anchors around lines 348–390 | Selector writes strategy/market to URL state; observation and quote times remain separate. |
| Workspace context limitation | Callout `.mx-callout` — specimen anchor “Callout + Detail disclosure” lines 492–500 | Quiet tint + rail; one limitation sentence, no macro score. |
| Action Desk headline population | Count ladder `.mx-ladder--board` — specimen “Count ladder” lines 393–405 | Restricted to this lifecycle-derived board; quotes producer counts only. |
| Action Desk row | DecisionRow `.mx-chg-row` — specimen “DecisionRow” lines 369–380 | Six-field glance contract; two-line stack below 640px. |
| Candidate/episode surface | SignalCard `.pvcard` — specimen linked-by-reference lines 540–546 | Reuses incumbent card semantics; no new score or chart. |
| Episode quality / evidence-vs-risk split | Quality block `.qual2` — specimen linked-by-reference lines 540–546 | No fused composite or total score. |
| All Candidates table / Track Record tables / Health table | Table `.mx-tbl` + Tabs `.mx-tabset` — specimen “Table + Tabs” lines 429–447 | Table is Tier 2/3 or behind table view; ≤8 L1 rows and in-container scroll. |
| Radar timeline / lifecycle history | Lifecycle rail `.mx-rail` — specimen “Lifecycle rail” lines 504–512 | Weight, not hue; producer-only rows do not receive a lifecycle dot. |
| Receipts and methodology | Detail disclosure `.mx-disc` + LENS — specimen “LENS receipt” lines 409–427 and disclosure lines 492–500 | Study IDs, generations, model internals, and statistics live here. |
| Empty/loading/error/stale | `.mx-empty` + `.mx-empty-why` — specimen “Empty · Loading · Error · Stale” lines 448–467 | All three Action Desk causes are designed states. |
| Watch/save and disabled actions | Buttons `.gbtn`, including disabled quiet/button-with-reason variants — specimen density/component sections | Only Watch is active; disabled controls keep honest reason text. |
| Theme/member/accounting tables | Table `.mx-tbl` + Card `.panel` — specimen “Surfaces” lines 229–239 and table lines 429–447 | No new heatmap/graph is authorized by this packet. |
| Producer nomination versus tracked episode | **NEW-COMPONENT-NEEDED — `ProvenanceMark`** | A canonical provenance chip does not exist; it must distinguish source nomination from tracked episode without action color. |
| Evidence drawer | **NEW-COMPONENT-NEEDED — `EpisodeDrawer`** | A list-preserving, keyboard-accessible comparison drawer is a workspace primitive, but the specimen has no drawer specimen. |
| Group relationship ledger | **NEW-COMPONENT-NEEDED — `PropagationLedger`** | Direct/proxy/current-only relationships need a row grammar that prevents a graph from implying unmeasured history. |

**NEW count: 3.** Each must land in `theme.css` and the specimen in the implementation PR that first uses it, with dark/light, EN/ZH, desktop 1440, and mobile 390 evidence.
