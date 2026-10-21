# Sector Cycles workspace — information architecture vs C01–C28 (observed producers only)

Provenance: written on branch `lane/sic-p-cyc-20261021-r1` at commit
`3d8d14acdc8de99fa2c17316aa22de6177364dbc` (packet SIC-P-CYC). Every producer and
render citation below was read in this checkout. The frozen spec sources are
`templates/sector_cycles.html.j2`, `templates/sector_cycles.js` (the shared Cycles
renderer; also embedded by the China hub and the INTL country page — the facts below
are stated for the US standalone page unless a carrier is named),
`templates/sector_cycles.css`, `engine/sector_cycles.py`, `engine/sector_central.py`,
`engine/sector_central_grader.py`, `scripts/build_sector_cycles.py`,
`scripts/fit_cycle_hazard.py`, `engine/hazard_score.py`, and the neighbouring tests.

Artifact keys refer to `site/sectordata/sector_cycles.json` (the full engine payload,
`engine/sector_cycles.py::compute:1302`) and the three split data files the page
actually loads (`scripts/build_sector_cycles.py::main:71` writes
`sector_cycles_data.js` → `window.SECTOR_CYCLES` core at :118,
`sector_cycles_series_data.js` → heavy per-entity arrays at :121,
`sector_cycles_narr_data.js` → `window.SECTOR_NARR` at :124,
`sector_cycles_dna_data.js` → `window.SECTOR_DNA` at :127).

Carrier facts that bound this file (do not reinterpret):
- Hazard cells: MODEL/PASS = up/1m, down/1m, down/3m, down/6m; PRIOR (Kaplan–Meier
  family-stratified base rate) = up/3m, up/6m — `engine/hazard_score.py:8-9` ("For
  cells whose gate verdict is PRIOR (up/3m, up/6m)…"), PASS→MODEL at :424-432,
  PRIOR→KM at :434-436; per-cell verdicts written by `scripts/fit_cycle_hazard.py`
  (:589-592 a cell PASSES only if its CI excludes 0 AND survives BH-FDR; :654 prints
  "CELLS PASS: n / 6"); pinned also by `tests/test_hazard_score.py:59,75,125`
  (up/1m MODEL, down/1m MODEL, up/3m+up/6m PRIOR) and the picker comment at
  `templates/sector_cycles.js:1106-1109`. No PRIOR cell is ever upgraded here.
- Grader: the Sector Central grader's hit figure is a **conditional hit rate, not a
  win rate** — value: NOT IN TREE. `engine/sector_central_grader.py:332` computes
  `dir_hit_rate` at runtime from `data/sector_central/calls.parquet` (not in this
  checkout); the ~0.274 figure appears only in
  `research/sector_completion_20261021/README.md:24` and `MASTERPLAN_2026-10-21.md:248`
  (which also records the Neutral-rows-in-denominator caveat to repair).
- Sizing multipliers are inert: `engine/sector_central.py:404` `size_mult = 1.0`, and
  :398-411 document that every cell ships 1.0 (a SIZE lever only; never a size shown
  as output).
- Lead-lag is a recorded STOP, not a pending feature: W5.1 closed with no admitted
  lead-lag relation (`research/sector_completion_20261021/MASTERPLAN_2026-10-21.md:169`,
  `README.md:23`). No Cycles surface shows, implies or sorts by a sector-to-sector
  lead or lag; the inert multiplier and the lead-lag STOP are recorded together on
  the methods row.

ZH labels below are the strings the current template/renderer actually carries
(`L(en, zh)` calls in `templates/sector_cycles.js` and `.l-en/.l-zh` spans in
`templates/sector_cycles.html.j2`). There is no separate i18n dictionary file.

## R1 — header (route title, family selector, as-of + source)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C01 | Eleven SPDR records + identity/group metadata | 板块周期情报 · 每个美股板块所处的位置 (header `templates/sector_cycles.html.j2:37-38`); tab 板块 ETF (:50) | `engine/sector_cycles.py::build_sector:1101` (identity :1119-1123; registry `SECTORS` :45) → `templates/sector_cycles.js::mountChips:783`, counts `wireFamily:773`, cards `mountCards:944` | PRODUCED |
| C02 | Family registry (thematic / Nasdaq / Russell) | 主题篮子 · 纳斯达克100 · 罗素2000 (tabs `templates/sector_cycles.html.j2:51-53`); 主题篮子轮动 (title `sector_cycles.js:736`) | `engine/sector_cycles.py::build_amalgam_family:1241` (+`build_basket:1146`, `_load_baskets:1189`, `_load_amalgams:1230`, families meta :1429) → `switchFamily:747`, `mountBaskets:829` | PRODUCED |

Notes. C01: `meta.n_sectors` (`compute:1427`) is the count of records that actually
built; a sector that fails (`build_sector` returns None when <300 rows,
`engine/sector_cycles.py:1110-1113`) is skipped loudly in the log and the population
shrinks — the "ten measured of eleven expected" journey must read that count against
the `SECTORS` registry (11), not against `n_sectors`. C02: absent Nasdaq/Russell
arrays hide their tabs (`sector_cycles.js:776-779`); a family with no records shows an
unavailable family via that hiding, not an empty successful list. As-of/source strip
itself is C24.

## R2 — chart canvas (rebased price over cycle-position oscillator, scale)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C03 | Rebased real-price series + rebase metadata | 价格 (mode button `templates/sector_cycles.html.j2:62`) | `engine/sector_cycles.py::record_series:605` (points `v/base*100` :701 via `_taper_points:380`; basis key :862; TR/price panel split `compute:1322-1327`) → `seriesFor:357` (price mode), anchor `priceAnchorFactor:311`, extent `priceExtent:317`, tooltip `heroTip:371-383` | PRODUCED |
| C04 | Cycle-position oscillator + legacy phase/position | 周期位置 (`templates/sector_cycles.html.j2:63`); 低 = 超卖 · 高 = 拉伸 (:65); zones 超卖/周期中段/周期晚期/狂热·见顶/复苏 (`sector_cycles.js:390-392`) | `engine/sector_cycles.py::_detrended_osc:146` → `osc` points; `now.pos` :758, `now.phase/phaseLabel` :766 (`_classify_phase:285`) → `seriesFor:357` (default mode; `state` init `sector_cycles.js:73`), `yDomain:332` [0,100], `bands:347`, `zoneWord:390` | PRODUCED |
| C05 | Log/linear scale | 对数 / 线性 (`templates/sector_cycles.html.j2:70-71`) | display transform on the same price field → `yval:298`, `yDomain:332`, `yTicks:338`, toggle `wireControls:532-539`; scale row hidden outside Price mode `syncHeroControls:552-560` | PRODUCED |

Notes. C03 basis (`price` / `tr` / `tr_fallback`, `engine/sector_cycles.py:859-862`)
is stamped per record but **not displayed on the US page** (the only rendered basis
line is the INTL-only "Local basis" fact, `sector_cycles.js:247-249`); the C03
disclosure (price vs TR vs declared fallback) is open Paper work. C04's additive v2
fields (`now.pos_v2` :777, `now.phase_v2` :778, `now.phase_v2_age_bars` :879 —
placeholder 0 at :811-813) are backend-only on this page (no `pos_v2`/`phase_v2`
reference in `sector_cycles.js`); they surface only indirectly through the stamped
stance (C15). Legacy and v2 vocabularies are never mixed in one rendered pair
(coherence fix documented at `engine/sector_cycles.py:791-801`).

## R3 — control rail (zoom/window/re-anchor, phase chips, series picker)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C06 | Zoom presets + window + re-anchor | 全部15年 / 7年 / 3年 / 1年 / 6月 / 首页 ⤢ · 滚动 · 拖拽 (`sector_cycles.js:505-513`) | `meta.xDomain`/`xDomainDefault` (`compute:1392-1400`) → `buildZoom:499` (presets + Home to the 7y default), `mountHero:435` (open on default view), re-anchor `scheduleReanchor:416` | PRODUCED |
| C07 | Phase chips + pinned focus | 所处阶段 (`sector_cycles.js:613`); chips 见顶/上行/回落中/入场良机/筑底中 (:600-604); 全部阶段 (:619) | `now.phase` (`_classify_phase:285`; `PHASES` engine :126-132) → `buildGroups:607`, `syncGroups:634`, `applyVisibility:643` (pinned override `keepShown` :650-651; counts :611) | PRODUCED |
| C08 | Series selection: chips, select-all/clear, search | 全选可见 (`sector_cycles.js:794`/`853`); N 在图中 (:893); picker 选择板块/搜索…/全选/清空/完成 (:1746-1752) | family lists + ranks (`_stamp_rs_ranks:1271`) → `mountChips:783`+`selectAllSectors:812` (sectors), `mountBaskets:829`+`selectAllBaskets:877`+`toggleBasket:904` (basket-like); searchable multi-select overlay `buildSeriesOverlay:1740`, `renderSeriesList:1768`, `filterSeriesList:1803`, `seriesSelectAll:1797`, `openSeriesPicker:1818` | PRODUCED |

Notes. C07's facet never changes the measured cohort — it only hides lines/cards
(`applyVisibility:654-694`); the pinned/selected exception is the focus override
(:650-651) and the filtered count is announced for screen readers (:688-690). The
searchable picker (C08) is mounted only on the China mobile carrier
(`isCnMobile()` gate `mountChips:790,806`); the US page's mobile selection surface is
the chip rail itself plus "Select all visible". A no-results picker search hides rows
(`filterSeriesList:1803-1817`); an over-filtered chart shows the empty-chart hint
(`updateChartHint:707-722`).

## R4 — leadership & turns (21/63 RS, peaks/troughs, leg timeline)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C09 | 21/63d RS + within-family leadership | 领涨 · 对比标普（21日 · 63日） (`sector_cycles.js:1554`; benchLabel 标普 :63) | `engine/sector_cycles.py::_leadership:457` (rs_21d/63d/126d, rs_above_trend, thin_history) + `_stamp_rs_ranks:1271` (rs_rank 63d + rs_21d_rank) → `buildDefaultPanel:1480` leadership rows :1504-1519, focus RS fact `focusHTML:1353-1357`, card RS chip `mountCards:957-958` | PRODUCED |
| C10 | Confirmed peaks/troughs + markers | 波峰 / 波谷 (`sector_cycles.js:593-594`); Now 当前 (:366) | `engine/sector_cycles.py::_detect_swings:160` (+abs variant :214; provisional flag) → markers `seriesFor:362-365` (confirmed only), lastPeak/lastTrough facts `focusHTML:1409-1410`, legend `syncLegend:590-595` | PRODUCED |
| C11 | Leg timeline + dated stories | 周期区段 — 点击查看故事 (`sector_cycles.js:1428`); 上涨/下跌 (:1439) | turns (same producer) joined to narratives by leg start (`legsOf:484-496`) → `legsHTML:1433`, `legBody:1457`, `openLeg:1463` (zooms chart to the leg :1475), chart click `onChartClick:441-453` | PRODUCED |

Notes. C09's reconstructed `rs_history` trail (`_leadership_history_counted:486`,
`_leadership_history:531`; contract stamped at `compute:1405-1426` incl.
`naturally_observed: False`) is **backend-only**: no `rs_history` reference exists in
`sector_cycles.js`. The within-family leader panel ranks by the fast 21d leg when
stamped, with the 63d lens as the muted sub-value (`buildDefaultPanel:1500-1519`);
thin history withholds RS rather than averaging (`_leadership:469-472` → "—"
`focusHTML:1353`). C10 renders only confirmed pivots (provisional filtered at
`seriesFor:362`); confirmation semantics stay engine-side. C11's legs bind to the
exact engine turns; an absent narrative shows the measured leg with
"What drove this move — research pending." (`legBody:1458`).

## R5 — read (epoch narrative + TTL, DNA lazy, bilingual engine read, resolved stance)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C12 | Epoch narratives + TTL + stale quarantine | 分析师注释 (`sector_cycles.js:1339`); 整理于 N 天前 (:1309-1313); 解读 (:1368) | `scripts/_narrative_epoch.py::resolve_narratives:81` (stale_quarantined contract :100) + `scripts/_narrative_ttl.py::enrich_narr_ttl:122`, loaded `scripts/build_sector_cycles.py::_load_narratives:43` (:97-106) → `_buildAnalystNoteHTML:1294` (staleness badge :1305-1314, mechanism-check fail/manual :1317-1329, revision note :1331-1334), chart bands `focusBands:456-480` | PRODUCED |
| C13 | Cycle DNA lazy profile | 周期基因 — 历史为何押韵 (`sector_cycles.js:1258`); 展开更多 ▾ (:1269) | `scripts/build_sector_cycles.py::_load_dna:58` (epoch-aware :62-68) → `dnaHTML:1245`, clamp toggle `_initDnaToggle:1276`, lazy hydration `hydrateExtras:1929` + `_scheduleExtras:1941` | PRODUCED |
| C14 | Bilingual engine read (primary) | 解读 (`sector_cycles.js:1368`); sentence from `now.read_zh` (`engine/sector_cycles.py:110-111`) | `engine/sector_cycles.py::_engine_read:71`, stamped `_set_engine_read:979` (:875/:997-998) → `focusHTML` read block :1363-1376; the hand-authored `NARR[id].now` is demoted to the dated Analyst note (:1361-1366) | PRODUCED |
| C15 | Resolved stance + tone + divergence | 时钟分歧 (`sector_cycles.js:171`); stance chip text from engine `stance_zh`; chip title 综合策略 · 引擎 (:162) | `engine/cycle_ontology.py::resolve_state:884`, stamped `engine/sector_cycles.py:830-854` (:880-887) → `stanceHTML:158` (tone→class `TONE_CLS:153`), `divergenceHTML:166-176`, focus head `focusHTML:1394-1400`, cards `mountCards:962-964` | PRODUCED |

Notes. C12: a wrong-epoch narrative set is quarantined at build time
(`stale_quarantined` → the page renders without narratives,
`scripts/build_sector_cycles.py:52-54`), and an expired note carries its dated badge
(red/amber at `sector_cycles.js:1306-1308`) — neither silently attaches to a new
turn. Narrative text never overrides plotted numbers (doctrine comment
`engine/sector_cycles.py:982-983`). C13: DNA absent → the section is simply not
emitted (`dnaHTML:1247` returns "") — an honest unavailable, not an error; its
similarity language is hypothesis-framed by the payload copy. C14: read is a pure
function of computed fields; missing RS is omitted, never averaged
(`_engine_read:86-96`). When `now.read` is still None the panel shows the
"Engine read generating." pending sentence (`sector_cycles.js:1371-1374`). C15: JS
renders stamped fields only — it never recomputes a stance (W3.6 comment
`sector_cycles.js:143-152`); a null stance (resolve failure,
`engine/sector_cycles.py:852-854`) omits the chip (`stanceHTML:159`).

## R6 — timing & projection (ladder, gate, rhythm, hazard)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C16 | Timing ladder + weekly/3-day MACD + DC phase + phase age | NO ZH STRING (not rendered) | `engine/cycles.py::analyze:2558` (ladder + mtf), stamped `engine/sector_cycles.py:867-872` (`timing_state`, `action`, `w_macd_up`, `t3_macd_up`, `dc_phase`) + :878-879 (`phase_v2`, `phase_v2_age_bars` placeholder 0 at :811-813) | PRODUCED_NOT_RENDERED — no timing detail view exists on this page; the ladder state only feeds `resolve_state` internally (`engine/sector_cycles.py:824-833`) |
| C17 | Above-trend + Central 12m gate/conviction | 200日上 / 200日下 (`sector_cycles.js:1393`); gate trace NO ZH STRING | above200d: `engine/sector_cycles.py:761` (rendered in `focusHTML:1393` + engine read) — gate/conviction: `engine/sector_central.py::_trend_gates:527` ({pass, above_200dma, ret_12m, pos_12m}) + `_fuse:337` (conviction block :421; stretched cap :520; `size_mult = 1.0` inert :404) | PRODUCED_NOT_RENDERED for the 12m-gate/conviction trace (Central-artifact fields not consumed by `sector_cycles.js`); the standalone above-trend half is rendered |
| C18 | Next-turn rhythm + interval (+ overdue) | 预计下次顶部/底部约在… (`sector_cycles.js:1135`); 典型半周期 (:1412); 推演下一顶部/底部 (:1142, forecastPoint flag); overdue NO ZH STRING | `engine/cycle_ontology.py::project_next:1149` via `_project_next:343-358` (overdue/overdue_frac additive :353-355) → rhythm card `forecastCardHTML:1131-1148` ("a timing RHYTHM, not a backtested forecast" :1145), projection band `focusBands:465-478`, card next line `mountCards:959`, focus fact `focusHTML:1411` | PRODUCED_NOT_RENDERED for `proj.overdue`/`proj.overdue_frac` — confirmed: the string "overdue" appears nowhere in `templates/sector_cycles.js`; the central date is never walked forward by the renderer |
| C19 | Turn hazard 1/3/6m MODEL vs KM PRIOR + epoch | 转折风险（校准） (`sector_cycles.js:1102`); 通过 / 先验 (:1076-1077); P(转折≤1月)/≤3月/≤6月 (:1091-1093); gate-receipt tooltip NO ZH STRING (EN only :1064-1073) | `engine/sector_cycles.py::_stamp_hazard:1021` → `engine/hazard_score.py::score:351` (epoch :44; PASS→MODEL :424-432; PRIOR→KM :434-436; schema/epoch guard :236-244; monotone-CDF gate `_enforce_hazard_cdf`) → `hazardLineHTML:1080`, badges `_hzBadge:1075`, tooltips `_hzTip:1064`, card chip `hazardCardChip:1117` + `_hzPick:1110` | PRODUCED |

Notes. Hazard cells per record: MODEL/PASS = up/1m, down/1m, down/3m, down/6m;
PRIOR = up/3m, up/6m (provenance block above). Every visible cell carries its
PASS/PRIOR badge (`hazardLineHTML:1087-1088`); PRIOR cells render muted
(`hz-muted`). Display-only framing is explicit ("never a signal",
`sector_cycles.js:1098-1101`). A record whose feature vector fails the scorer's
schema/epoch guard gets no `now.hazard` (stamp is warn-and-skip,
`engine/sector_cycles.py:1093-1098`) and the line is omitted (`hazardLineHTML:1082`)
— that is the current error treatment, not a typed state. C16's
measured phase age is produced by `engine/cycle_phase_age.py` (`forward_log_replay.v2`):
`phase_v2_age {sessions, status, observed_from, history_rows}` with status one of
measured / lower_bound / insufficient_history / source_unavailable / unknown_phase /
not_logged; the shipped read is `lower_bound` (4 sessions, observed from 2026-10-14,
56 history rows) because the forward log began on 2026-10-14. `phase_v2_age_bars`
(0) is the retired placeholder and is never rendered; the UI renders the deck's
`phase_age_*` string for the status, never a bare number. C17's conviction risk
multiplier is inert at 1.0 (`engine/sector_central.py:404`) — record it as inert,
never as a size.

## R7 — events (rotation chips, fragmentation chips, research links)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C20 | Rotation-event chips | 轮动进行中 / 资金流入 (`sector_cycles.js:222-225`); copy from payload `copy_zh` | `engine/rotation_events.py::run_nightly:1991` (+`emit_v2:1627`), written `scripts/build_rotation_events.py:179` → raw fetch `loadRotation:2049-2073`, chip `rotationCardChip:211-226`, mounted `mountCards:972` | PRODUCED |
| C21 | Fragmentation chips | 聚合读数或失真 (`sector_cycles.js:232`); copy from payload `copy_zh` | `engine/sector_fragmentation.py::compute:105`, written `scripts/build_rotation_events.py:136` → same fetch :2053-2055, chip `fragCardChip:227-233` | PRODUCED |
| C22 | Research links + panel transitions | 查看 <名称> 页面 (`sector_cycles.js:1238`) | destinations built by `scripts/build_site.py::main:6093` (us_sector_* themes :1684-1808); route table `US_SECTOR_PAGE` `sector_cycles.js:1203-1215` → `sectorPageHref:1222-1234`, `sectorPageLabel:1235-1240`, open button `focusHTML:1382-1384` | PRODUCED |

Notes. C20/C21 consume `marketdata/rotation_events.json` and
`marketdata/sector_fragmentation.json` **raw**: `.catch(() => null)` + `r.ok ? json
: null` collapse 404/malformed/offline into chip-absence
(`sector_cycles.js:2051-2053`), with no generation/as-of guard — the incompatible /
stale / failed distinctions exist only in Central's measured adapter
(`engine/leadership_rotation_context.py:1609-1629`,
`status: "incompatible_generation"` at :1626-1629), which this page does not use.
That consumer gap is the packet's U02 repair; this file records it, not fixes it.
C22: Nasdaq/Russell records have no destination (`sectorPageHref` returns null
:1231) so no button renders; the basket route strips the `b-` prefix (:1230); on the
INTL carrier the button is suppressed (:1223).

## R8 — grader & metadata

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C23 | Shared Central grader + prospective cycle log | NO ZH STRING (nothing rendered on this page) | `engine/sector_central_grader.py::grade:220` (+`append_central_log:103`; `dir_hit_rate` :332) and `engine/cycle_forward_log.py::append_forward_log:205` (keep-FIRST :272-274), stamped nightly `scripts/build_sector_cycles.py:89-95` | PRODUCED_NOT_RENDERED — no standalone Cycles outcome-record view exists; the ledger is never read back into a live score (grader docstring :12-16) |
| C24 | Source/basis/history meta + split payloads | 截至 (`templates/sector_cycles.html.j2:45`) | `engine/sector_cycles.py::compute:1302` (`meta.asOf` :1397, benchmark :1404, rebaseDate :1403, xDomain :1399, rs_history meta :1405-1426) → header `#sc-asof` (template :45, filled by inline script :113) and panel caption `buildDefaultPanel:1529` | PRODUCED |

Notes. C23: the grader's hit figure is a conditional hit rate, not a win rate —
value: NOT IN TREE (provenance block above; the ledger `data/sector_central/
calls.parquet` and `data/sector_cycles/forward_log.parquet` live under `data/`, not
in this checkout). C24: the standalone source date starts as an ellipsis — the
template bakes `…` (`templates/sector_cycles.html.j2:45`) and only the trailing
script fills it from `meta.asOf` once JS runs (:113); with JS blocked there is no
baked date (the SSR upgrade the matrix requires). Per-record basis is stamped
(`engine/sector_cycles.py:862,889`) but not displayed (see R2 notes). The four
payload files of different generations are not currently cross-bound by any client
generation check — each script global simply overrides.

## R9 — platform (mobile, keyboard/live region, bilingual/theme, lazy/resilient)

| Row | Element | ZH label | Producer → Render | Status |
|-----|---------|----------|-------------------|--------|
| C25 | Mobile picker + sheet detents + full-screen + touch | 完成 (`sector_cycles.js:1748`); sheet ✕ aria-label "Close" EN only (:1646); fs button aria-label EN only (:1839) | `initSheet:1629` (US peek-expand :1632-1641; China detents `setDetent:1615` hidden→half→full, `detentPx:1627`, 1:1 drag + flick :1656-1687, Esc :1689), picker overlay `buildSeriesOverlay:1740`, full-screen `toggleChartFs:1844`/`mountChartFsBtn:1834`; media queries `templates/sector_cycles.css:424-470`, sheet transforms in `site/cycle.css:326,350-351` | PRODUCED |
| C26 | Keyboard + live region + chart focus | live-region message 已显示 N / M 项 (`sector_cycles.js:690`) | `srStatus:697` (role=status aria-live=polite; node also `templates/sector_cycles.html.j2:86`), `keyActivate:115` (wired on legs :1031 and lead rows :1570), chart role=img (`templates/sector_cycles.html.j2:88`), Esc handlers :1689/:2030-2032, focus-visible outlines `templates/sector_cycles.css:534` | PRODUCED |
| C27 | Bilingual + semantic tone + light/dark | whole-page `l-en`/`l-zh` spans + `L(en, zh)` (`sector_cycles.js:59-60`); tone tokens flip-safe :148-156 | engine-stamped zh fields (`read_zh`, `stance_zh`, `divergence_note_zh`, `name_zh`…) → language flip re-render `rerender:1858` on `langchange` (:2029); theme boot `templates/sector_cycles.html.j2:13`; semantic tone→root tokens `TONE_CLS:153` | PRODUCED |
| C28 | Lazy hydration + resilient core | 引擎解读生成中 (`sector_cycles.js:1374`) | payload split `scripts/build_sector_cycles.py:108-129` (core light / series heavy / narr / dna) → `hydrateSeries:1977` + `_scheduleSeries:2001` (post-first-paint; onerror tolerated :2011), `hydrateExtras:1929` + `_scheduleExtras:1941` (idle-callback), stamped-URL reuse `vUrl:1919`, pre-hydration guards `seriesFor:360-361` / `priceExtent:321` / `sparkSpec:918`, null-safe rotation fetch :2051-2053 | PRODUCED |

Notes. C25 carrier split: the multi-detent sheet, the searchable Series picker and
the full-screen chart are gated to the China mobile carrier (`isCnMobile()`,
`sector_cycles.js:94-95` gate at :806/:1695/:1835; detent CSS scoped `.sc-china`,
`site/cycle.css:350-351`); the US standalone page's ≤880px journey has the
peek-expand underbar only (`setFocus:1014-1017` → `expandSheet:1603`,
`.cyc-detail.expanded` `site/cycle.css:326`). So the C25 acceptance journey (390px:
picker → half/full detail → leg → close → full-screen → return) is not deployable on
the US page today — that is the matrix's "complete actual deployed mobile journey
remains unproved", recorded as-is. C26 keeps outlines (`:focus-visible` rule
`sector_cycles.css:534`); hover-only chart content has keyboard equivalents via
focusable legs/cards/chips. C27 residual EN-only strings: the hazard gate-receipt
tooltips (:1064-1073), the two mobile aria-labels (:1646, :1839) — ZH parity gaps to
carry into the Paper design. C28: pre-hydration views draw guarded empties (never
throw); the current catch-to-null behavior on optional payloads is the quiet-failure
pattern the matrix's U-row wants upgraded to typed states.

## Not yet produced

No C01–C28 row is wholly `NOT YET PRODUCED` — every capability has at least an
observed producer. The honestly-missing pieces, all narrower than a full row:

1. **Measured phase age: the UI home** (C16 acceptance): the producer exists
   (`engine/cycle_phase_age.py`, `phase_v2_age` with a typed status; shipped read
   `lower_bound`, 4 sessions from 2026-10-14). What is missing is the Cycles home
   that renders `phase_age_measured` / `phase_age_lower_bound` /
   `phase_age_unknown` by status, and the nightly accrual that turns the lower
   bound into a measurement; the placeholder `phase_v2_age_bars` is retired.
2. **Typed optional-payload states** (C20/C21/C28): the renderer collapses
   404/malformed/network/absent into quiet chip-absence
   (`templates/sector_cycles.js:2051-2053`); no 401/403/incompatible-generation
   state is produced anywhere on this page's own fetch path.
3. **SSR source date** (C24): the page bakes an ellipsis
   (`templates/sector_cycles.html.j2:45`) — no server-side date producer reaches the
   shell.
4. **Standalone views that have no artifact of their own**: the Timing detail view
   (C16) and the Cycles outcome-record/grader presentation (C23) — their underlying
   data is produced; the views themselves do not exist in any file.
5. **rs_history renderer** (C09): the reconstructed trail is produced and
   contract-stamped (`engine/sector_cycles.py:1405-1426`) but no renderer consumes
   it (`sector_cycles.js` has no `rs_history` reference).
6. **Coherent v2 presentation** (C04): `pos_v2`/`phase_v2` are stamped but unrendered
   (see R2 notes); the labelled methodology comparison is unbuilt.

Rows whose status column records a produced-but-unrendered capability:
**C16, C17, C18 (overdue flag), C23** — all `PRODUCED_NOT_RENDERED`.

## Code conditions for states

State words used in `cycles_ia.csv`, each with the code condition that actually
produces it (file:line as read in this checkout):

- **fresh** — the ordinary path: engine record built and stamped nightly
  (`engine/sector_cycles.py::compute:1302`; `meta.asOf` :1397), page rebuilt by
  `scripts/build_sector_cycles.py::main:71` (:81-95, :118-146).
- **loading** — heavy series not yet hydrated → guarded empty line/spark
  (`templates/sector_cycles.js:360-361`, `:321`, `:918`); lazy narr/DNA pending
  (`_scheduleExtras:1941-1965`); engine read pending sentence (`:1371-1374`);
  header date pending until JS (`templates/sector_cycles.html.j2:45` + `:113`).
- **partial** — sector too thin → record skipped, population shrinks
  (`engine/sector_cycles.py:1110-1113`); thin RS history → RS withheld ("—" at
  `sector_cycles.js:1353-1357`; flagged `engine/sector_cycles.py:469-472`);
  price-basis gap → `basis: "tr_fallback"`, labeled but not displayed
  (`engine/sector_cycles.py:667-674`, `:859-862`); DNA/record subsets absent →
  section/chip omitted (`dnaHTML:1247`, `hazardLineHTML:1082`); hazard stamp failure
  → warn + no stamp (`engine/sector_cycles.py:1093-1098`); pos_v2 unavailable →
  falls back, v2 fields absent (`engine/sector_cycles.py:785-786`).
- **empty** — no chart items match the phase facet / nothing selected
  (`sector_cycles.js:711-721`); no legs in window (`:1435`); default-panel bucket
  empty row ("No … at prime entry right now", `:1492-1493`, `:1545-1547`); no
  rotation/fragmentation rows → no chips (`:2056-2059`).
- **stale** — narrative TTL badge: `staleness_days` with amber/red classes from
  `_ttl.stale_amber/stale_red` (`sector_cycles.js:1305-1314`; produced by
  `scripts/_narrative_ttl.py::enrich_narr_ttl:122`); baked page date ages until the
  next nightly rebuild (no client staleness clock on this page).
- **incompatible_generation** — narrative/DNA epoch mismatch → quarantined at build,
  page renders without them (`scripts/_narrative_epoch.py:81-116`, consumed
  `scripts/build_sector_cycles.py:52-54`, `:62-68`). The equivalent guard for the
  rotation/fragmentation fetch does not exist on this page (it exists only in
  Central's adapter, `engine/leadership_rotation_context.py:1609-1629`) — which is
  why C20/C21 do not claim this state.
- **corrected** — narrative revision provenance note rendered verbatim from
  `_ttl.revision_note` (`sector_cycles.js:1331-1334`); no engine-side restatement
  contract exists (do not invent one).
- **abstained** — hazard PRIOR cells (KM base rate, muted, PRIOR-badged:
  `engine/hazard_score.py:434-436`, `sector_cycles.js:1071-1073`); hazard unavailable
  block when the mixed MODEL/PRIOR set breaks monotonicity
  (`engine/hazard_score.py` `_unavailable_hazard`, "unavailable_reason:
  non_monotone_cdf"); stance withheld on resolve failure (`engine/sector_cycles.py:852-854`
  → chip absent `sector_cycles.js:159`); divergence withheld when clocks agree
  (`sector_cycles.js:167`); Central conviction capped/de-rated (stretched cap
  `engine/sector_central.py:520`, gate fail path :398-411).
- **error** — scorer schema/epoch guard returns None → no hazard line
  (`engine/hazard_score.py:236-244` + `engine/sector_cycles.py:1093-1098` →
  `sector_cycles.js:1082`); optional-payload fetch failure currently collapses to
  quiet absence rather than a typed error (`sector_cycles.js:2051-2053`).
- **offline** — same collapse: `fetch` rejected or `!r.ok` → null → chips absent
  (`sector_cycles.js:2051-2053`); lazy script `onerror` tolerated so the core keeps
  working (`:1956`, `:2011`). No distinct offline presentation exists today.
