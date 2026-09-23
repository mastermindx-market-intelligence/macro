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

STATUS: COMPLETE — packet complete; delivery steps follow

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

## 5. DARK TREATMENT — command center

- **Material:** canvas `--bg #0f1115` holds answer panels `--panel #181b21`; nested evidence uses `--panel2 #1e222a`; hairlines `--line #3a4150` and the micro-edge `--card-shadow` create luminance depth without competing with data. The shared nav remains the only header and consumes its own navigation tokens.
- **Hierarchy:** Action Desk owns the first answer. Its population ladder and rows receive more weight than Radar/Themes; Track Record and Health are support/accountability surfaces. Evidence is calm hairline text, estimates are quiet measurement ink, and actions are the only controls. No neon BUY badge, saturated heatmap wash, blinking state, or chart-background glow is allowed.
- **Emphasis:** selection is a restrained focus/selection ring from `--ink-link`; a critical refusal or availability failure uses a narrow state rail, not a full-row alarm. Featured/new/trigger chips remain secondary to identity and stance. Directional change uses `--ink-up`/`--ink-down` with a sign/arrow/word because hue alone is insufficient under future language conventions.
- **Evidence / estimate / action separation:** evidence sits in `.qual2` and receipt rows on panel surfaces; estimates/uncertainty use `.mtile` plus words and uncertainty state; actions sit in a fixed drawer/list action rail and use `.gbtn`. A price condition is never styled as a filled position or recommendation.
- **State colors:** positive/available/healthy uses `--ink-ok`; adverse/critical uses `--ink-act`; caution/watch/protect uses `--ink-warn`; unknown/not-available/no-read uses `--muted`; research/experimental uses `--ink-info`; navigation/selection uses `--ink-link`; lock-only Prophet violet uses `--mx-tier-accent`/`--ink-tier` and never means data quality. Fill-grade tints stay ≤ the `.mx-stance`/`.mx-callout` formulas.
- **Intentional dark mechanisms:** luminance-step depth, restrained bloom on hover only, and chart ink on transparent instrument surfaces. Critical states may use a small live pulse only when a required source/current availability genuinely changed; every other update is quiet.

## 6. LIGHT TREATMENT — research workspace

- **Material:** cool canvas `--bg #f7f8fa` supports white `--panel` answer surfaces; `--panel2 #eef1f6` and the light `--line` make nested evidence feel like paper layers. Light depth is `--card-shadow`, crisp rules, and whitespace, not a dark glow translation.
- **Hierarchy:** the answer remains first, but the workspace reads as a reading/research desk: stronger typographic grouping, more white space between panels, and quieter saturated fills. The same six destinations, ordering, actions, density meanings, and state words appear; nothing is hidden merely because the theme is light.
- **Emphasis:** hover/selection is a ring and tight shadow, never a bloom; highlight rows use ≤8% tint + 3px rail + deepened ink; gradients become airy tints or disappear. Dark lock ghosting is replaced by the governed light ghost; charts use light grid/series twins and no dark slate.
- **Evidence / estimate / action separation:** evidence tables rely on hairlines and row-hover `--panel2`; estimates use white metric tiles with clear uncertainty labels; actions remain visually separate controls. A colored estimate can never substitute for a readable uncertainty sentence.
- **State colors:** the same semantic families resolve through light tokens and text inks: `--ok/--ink-ok` positive/available; `--act/--ink-act` adverse/critical; `--warn/--ink-warn` caution/watch; `--muted` unknown/unavailable; `--info/--ink-info` research/experimental; `--link/--ink-link` selection/navigation. Light popover/drawer surfaces use `--glass-bg`, `--glass-brd`, `--glass-shadow`, and `--popover-shadow`.
- **Intentional differences:** glow becomes ring+shadow; luminance hierarchy becomes canvas/surface/border/air; hero color fields become structured white cards or quiet tint bands; broad dark shadows become smaller/cooler shadows. Token substitution alone does not qualify; each light panel is judged as a design.

## 7. DESKTOP 1440 and MOBILE 390 COMPOSITIONS

Desktop width is 1440; mobile width is 390. Every destination uses the one authenticated nav, persistent strategy selector, and shared context strip. Drawer panels are 440px desktop / full-width mobile. Long EN/ZH reasons wrap with a minimum 44px touch target; no ellipsis hides state.

### 7.1 Action Desk — desktop
```
┌──────────────────────── authenticated site nav ────────────────────────┐
├────────────────────────────────────────────────────────────────────────┤
│ MARKET ▾   STRATEGY ▾   Observation …   Quote …   [Research | Promoted] │
│ Group context sentence ………………… limitation ………………… as-of …          │
├───────────────────────────────────────┬────────────────────────────────┤
│ [Population ladder / true empty]      │ EPISODE DRAWER                 │
│ ┌───────────────────────────────────┐ │ Identity + strategy/horizon    │
│ │ ID · strategy · availability      │ │ What changed · leading risk    │
│ │ condition · opposing fact · next  │ │ ENTRY │ RESEARCH │ RECEIPTS    │
│ └───────────────────────────────────┘ │ Fixed WATCH / disabled actions │
│ …≤8 visible rows; See all N           │ Selection and filters persist  │
└───────────────────────────────────────┴────────────────────────────────┘
```

### 7.2 Action Desk — mobile
```
┌──── authenticated nav / search ────┐
│ MARKET ▾  STRATEGY ▾              │
│ Obs … · Quote … · Research/Prom.  │
│ Group sentence + limitation       │
├───────────────────────────────────┤
│ [compact population ladder]       │
│ ┌───────────────────────────────┐ │
│ │ Identity / strategy           │ │
│ │ Availability + key risk       │ │
│ │ Next action · WATCH           │ │
│ └───────────────────────────────┘ │
│ Answer + first 3 rows in a swipe   │
└───────────────────────────────────┘
```
Opening a row covers the list with the drawer. **Back to results** restores the exact filter, scroll position, selected row, and focus.

### 7.3 Early Radar — desktop
```
┌──────────── shared workspace header/context ─────────────┐
├──────────────────────────────────────────────────────────┤
│ [PRODUCER NOMINATION] [TRACKED EPISODE] accounting strip │
├──────────────────────────────────┬───────────────────────┤
│ Radar rows (≤6 glance fields)     │ EPISODE/PRODUCER DRAWER│
│ origin → development → missing    │ First seen · path      │
│ exact monitored condition         │ Group context · source │
└──────────────────────────────────┴───────────────────────┘
```

### 7.4 Early Radar — mobile
```
┌──── nav/header/context ────┐
│ Origin accounting strip     │
│ ┌─────────────────────────┐ │
│ │ Identity / nomination   │ │
│ │ Strategy / availability │ │
│ │ Key missing evidence    │ │
│ │ Next action: watch      │ │
│ └─────────────────────────┘ │
│ Full-width drawer/receipts  │
└─────────────────────────────┘
```

### 7.5 All Candidates — desktop
```
┌──────────── shared workspace header/context ─────────────┐
├──────────────────────────────────────────────────────────┤
│ Search │ strategy │ lifecycle │ source │ status │ watch  │
├───────────────────────────────────┬──────────────────────┤
│ Result rows: identity, lifecycle, │ REASON DRAWER        │
│ availability, research, entry,    │ Exact layer reason   │
│ review outcome; null stays null   │ Episode route        │
│ [Table view] [See all N]          │ Watch readback       │
└───────────────────────────────────┴──────────────────────┘
```

### 7.6 All Candidates — mobile
```
┌──── nav/header/context ────┐
│ Search                     │
│ Filters (sheet)            │
│ ┌─────────────────────────┐ │
│ │ Identity / strategy     │ │
│ │ Availability            │ │
│ │ Key risk / review state │ │
│ │ WATCH or view reason    │ │
│ └─────────────────────────┘ │
│ Reason drawer full width   │
└─────────────────────────────┘
```

### 7.7 Themes & Propagation — desktop
```
┌──────────── shared workspace header/context ─────────────┐
├──────────────────────────────────────────────────────────┤
│ Lead theme: participation, persistence, concentration    │
├───────────────────────────────┬──────────────────────────┤
│ Theme brief cards (≤6)         │ PROPAGATION LEDGER       │
│ on-board/member · direct/proxy │ Company rows             │
│ current-only relationship note │ relationship · date      │
│                                │ GMI/Theme receipt route  │
└───────────────────────────────┴──────────────────────────┘
```

### 7.8 Themes & Propagation — mobile
```
┌──── nav/header/context ────┐
│ Lead theme sentence         │
│ ┌─────────────────────────┐ │
│ │ Theme / participation   │ │
│ │ Concentration           │ │
│ │ Relation type           │ │
│ │ Next action: inspect    │ │
│ └─────────────────────────┘ │
│ Ledger cards + receipts     │
└─────────────────────────────┘
```

### 7.9 Track Record — desktop
```
┌──────────── shared workspace header/context ─────────────┐
├──────────────────────────────────────────────────────────┤
│ Strategy record: population + ruler + era + coverage     │
│ [Signals] [Ranking] [Policy] [Plans] [User outcomes]     │
├──────────────────────────────────────┬───────────────────┤
│ Record rows / metrics; separate       │ ORIGINAL DECISION │
│ sample, unresolved, era, convention   │ Then-known drawer │
│                                      │ Later development │
└──────────────────────────────────────┴───────────────────┘
```

### 7.10 Track Record — mobile
```
┌──── nav/header/context ────┐
│ Population / ruler          │
│ [Record tabs → scrolled]    │
│ ┌─────────────────────────┐ │
│ │ Population / era        │ │
│ │ Coverage / unresolved   │ │
│ │ Key limitation          │ │
│ │ Open original decision  │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

### 7.11 Health & Receipts — desktop
```
┌──────────── shared workspace header/context ─────────────┐
├──────────────────────────────────────────────────────────┤
│ Delivery state: owed session → accepted generation → age │
├─────────────────────────────────────┬────────────────────┤
│ Health rows: impact, affected view,  │ RECEIPT DRAWER     │
│ source freshness, coverage, status   │ Source/generation  │
│ Product correctness ≠ evidence       │ Model/method/owner │
└─────────────────────────────────────┴────────────────────┘
```

### 7.12 Health & Receipts — mobile
```
┌──── nav/header/context ────┐
│ Delivery state sentence     │
│ ┌─────────────────────────┐ │
│ │ What is missing         │ │
│ │ What still works        │ │
│ │ Affected action         │ │
│ │ Repair owner / retry    │ │
│ └─────────────────────────┘ │
│ Receipt disclosures        │
└─────────────────────────────┘
```

## 8. INTERACTION

- **Keyboard:** `Tab` reaches nav, strategy selector, destination tabs, filters, rows, drawer, and actions in visual order. `↑/↓` moves list focus without scrolling selection away; `Enter` opens the highlighted drawer; `Escape` closes it and restores row focus; `Shift+?` opens keyboard help. Within the drawer, `↑/↓` move receipt sections, `Enter` activates links, `Escape` returns to the drawer header. Switching lists with `←/→` preserves selection if the identity exists and otherwise focuses the first row with a status message.
- **Focus and updated state:** a critical availability invalidation updates the affected row and announces “Entry availability changed.” A noncritical reorder adds an `Updated` button without stealing focus; activating it applies the order and preserves the selected episode. Every dialog/drawer uses focus trapping and a labelled return target.
- **Coherent hydration:** bind by source generation/correction identity, not date alone. Refuse a mismatched generation, duplicate tail, or partial replacement; keep the prior coherent snapshot, show “This update did not apply. The current view is still complete,” and offer retry. Same-date corrections require refresh when generation differs.
- **Accessibility status:** use `role=status` for load, save/readback, noncritical update, and language/theme change; `role=alert` only for critical availability loss or save failure. Do not announce routine quote ticks. Preserve visible text plus non-color markers for state; tooltips/focus rings meet the system contrast/accessibility floor.

### 8.1 Bilingual plain-language copy contract

ASCII labels are wireframe placeholders, not shipping strings. Production user-facing strings use these paired forms or equally plain task-specific variants. No translated text is placed in `title=`; receipts use LENS `data-tip-en`/`data-tip-zh`.

| Purpose | EN | ZH |
|---|---|---|
| Destination tabs | Action Desk / Early Radar / All Candidates / Themes & Propagation / Track Record / Health & Receipts | 行动台 / 早期雷达 / 全部候选 / 主题与传导 / 战绩记录 / 健康与凭据 |
| Research/promoted | Research view / Promoted view | 研究视图 / 已晋级视图 |
| Action Desk empty: no qualifier | Nothing qualifies today. We will look again after the next close. | 今天没有符合条件的对象。下一收盘后会再看一次。 |
| Action Desk empty: unsupported strategy | This strategy is not supported in the current market environment. You can still research its candidates. | 此策略暂不支持当前市场环境。你仍可研究其候选对象。 |
| Action Desk empty: required source missing | A required source is unavailable, so we cannot state entry availability. Nothing here is a substitute read. | 必需数据源暂不可用，因此无法判断入场可用性。这里没有任何替代判读。 |
| Radar empty | No new nominations passed source checks. | 没有新的提名通过数据源检查。 |
| Themes empty | No group is turning with enough members to matter. | 没有足够多成员转强的主题。 |
| Watch result | Saved to [list]. | 已保存到[list]。 |
| Watch failure | Could not save to that list. Please try again. | 无法保存到该列表。请重试。 |
| Local-only state | Saved on this browser. | 仅保存在此浏览器。 |
| Disabled action reason | Waiting for its owner to be connected. | 等待对应功能接入。 |
| Updated control | Results updated. | 结果已更新。 |
| Hydration failure | This update did not apply. The current view is still complete. | 本次更新未应用。当前视图仍是完整版本。 |
| Critical status | Entry availability changed. | 入场可用性已变化。 |

## 9. USER ACTIONS

- **Watch/Save (enabled):** invokes the existing list-scoped WatchStore only. The save sheet names the exact destination list before commit, waits for the actual owner result, and confirms with “Saved to [list]” or a plain failure. It never equates opening a dossier with saving, saving with a position, or a plan with a fill.
- **Watch readback:** after save, the row button becomes **Saved**, its LENS names the list and update time, and “Manage lists” routes to the incumbent owner surface. A local-only state is labelled “Saved on this browser” and never advertised as cloud thesis persistence.
- **Disabled actions and honest copy:** Pass (“Waiting for its owner to be connected”), Reason/Note (“Notes are local only and are not cloud thesis storage”), Thesis (“Thesis actions arrive after D05 maps their owner”), Milestone (“Milestone tracking arrives after D05 maps its owner”), Review (“Later-review tracking arrives after D05 maps its owner”). Disabled controls remain visible in the action rail with their reason; they never look like loading or entitlement upsells.
- **No ad-hoc store:** Prophet writes only the WatchStore item/list contract and displays WatchStore provenance. Episode context, model status, strategy, or correction generation is not serialized into a Prophet-only note format.
- **Alerts:** only meaningful state changes may link to the protected episode view; transport/preferences/deduplication remain incumbent owners. No notification reveals unlicensed facts, and quote motion alone is not an alert.

## 10. COMPREHENSION ACCEPTANCE (Q24 seed)

1. **Identify strategy and horizon** — From any row/drawer, the participant says the selected strategy and horizon without opening methodology. **Pass:** both are correct and no participant says a four-hour observation is a two-year thesis.
2. **Separate research priority from entry permission** — Given a high-priority row with unavailable entry, the participant declines to call it entry-approved. **Pass:** they point to “Research only”/“Not available right now” and state that no permission exists.
3. **Explain the leading risk** — From the row/drawer, the participant names the most consequential opposing or missing fact and what would change the decision. **Pass:** they cite the displayed fact/condition, not chart decoration or Priority alone.
4. **Save to the intended list** — Starting with at least two lists, the participant saves the exact row to the named list and retrieves it. **Pass:** owner readback is shown and the item appears in the intended list only.
5. **Retrieve the original decision** — After a correction, the participant opens the original decision and distinguishes then-known evidence from later developments. **Pass:** they do not describe the correction as a rewrite of the original snapshot.
6. **Read the record without inferring a trade occurred** — Given a Track Record/episode row with Watch and disabled thesis/plan controls, the participant says no trade, fill, position, or plan is implied. **Pass:** they identify the record as research/decision history and name the separate lifecycle fact if one exists.

Each test uses real source states, difficult unavailable/uncertain cases, EN and ZH, dark and light, desktop 1440, and mobile 390. Numerical pass thresholds belong to the registered usability protocol; task success is not market alpha.

## 11. OPEN TASTE DECISIONS for the Fable Meta-CEO seat

1. **Desk density:** (A) four rich rows with drawer comparison; (B) six compact rows with more drawer work. **Recommend A** — richer rows preserve availability, risk, and next action without hiding the limitation.
2. **Radar provenance split:** (A) one mixed list with two provenance marks; (B) two adjacent lanes. **Recommend A** — comparison is easier and the mark remains accountable if enforced consistently.
3. **Empty Action Desk emphasis:** (A) neutral quiet state; (B) warning-forward state for source failure only. **Recommend B** — “no opportunities” is calm; required-source loss must visibly block permission.
4. **Forecast presentation:** (A) plain sentence plus range in drawer; (B) visual distribution at glance. **Recommend A** — until calibrated, geometry can overstate certainty.
5. **Track Record default:** (A) population/ruler summary first; (B) outcome timeline first. **Recommend A** — comprehension depends on knowing what is measured before seeing outcomes.

## RETURN

STATUS: COMPLETE

RESULT:

- Deliverable: `research/prophet_v4/r6_program/wave1/B20_DESIGN_PACKET_V1_2026-09-23.md`
- Head SHA: recorded in the PR body at creation.
- NEW components: 3 — `ProvenanceMark`, `EpisodeDrawer`, `PropagationLedger`.
- Taste decisions: Desk density: rich rows. Radar: mixed list with provenance. Empty Desk: warning only for required-source failure. Forecast: plain sentence/range. Track Record: population/ruler first.

EVIDENCE:

- Constraints read: §0 records line-level citations for doctrine, design system, nav family, theme tokens, specimen, R6 §14–§16, incumbent Prophet templates/builders, and WatchStore.
- Validation commands and summaries: recorded from the final document checks and delivery commands below.

GAPS:

- The Claude memory index named by workspace law is absent at `~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/memory/MEMORY.md`; no alternative index exists under `~/.claude/projects`. Therefore the three delivery-process memory entries could not be opened. The frozen mission's branch/PR path was followed without merging, polling CI, marking ready, or claiming green checks.
- This is a design document only. The three NEW components and every proposed unavailable owner field require their D09/D05/implementation lanes; no product behavior is claimed shipped.

DEVIATIONS:

- `apply_patch` was not installed as a shell command. The first skeleton attempt failed before creating/committing any file, then the exact skeleton was immediately created with the shell, committed, and pushed as the first successful result. All later commits are new commits; no history rewrite or amend occurred.
- No other departure from the frozen specification.
## 12. CHANGELOG (critique ID → repair)
