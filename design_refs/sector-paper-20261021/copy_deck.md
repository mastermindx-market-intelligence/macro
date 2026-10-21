# Sector Paper completion boards — bilingual copy deck (2026-10-21)

Source deck: `copy_deck.json` (same directory). Contract test:
`tests/test_sector_paper_copy_deck.py`. EN words = whitespace tokens that carry
letters/digits (placeholders like `{n}` count as one word; symbols like → ▾ · do
not). ZH chars = non-whitespace characters, punctuation included. Budgets: h1 ≤ 4
EN words / ≤ 12 ZH chars; subtitle ≤ 14 / ≤ 28; h2 ≤ 7; cta/link ≤ 5 EN words and
verb-first; chip ≤ 3 EN words; exactly one h1 per board.

Cited sources were checked at the pinned commit: a fragment of the EN or ZH string
appears within ±3 lines of the cited line. `NEW` = the string does not exist in the
shipped templates; its ZH needs the native-speaker check at the end of this file.

ZH market-direction convention: 红涨绿跌 is a colour rule owned by CSS/chart
swapping (`templates/chart_i18n.js`), not copy. No string in this deck names a
colour.

## brief — 18 reused / 0 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Sector Intelligence | 板块情报 | 2 | 4 | templates/sector_central.html.j2:1489 |
| `tagline` | subtitle | Sectors, themes and industries, connected. | 串联板块、主题与行业。 | 5 | 11 | templates/sector_central.html.j2:1499 |
| `follow_h2` | h2 | Follow the leadership | 追踪领涨变化 | 3 | 6 | templates/_sector_central_brief.html.j2:8 |
| `next_h2` | h2 | Where to look next | 下一步看哪里 | 4 | 6 | templates/_sector_central_brief.html.j2:46 |
| `handoff_label` | label | Leadership handoff | 领涨交接 | 2 | 4 | templates/_sector_central_brief.html.j2:28 |
| `trailing_label` | label | Trailing leader | 前期领涨 | 2 | 4 | templates/_sector_central_brief.html.j2:31 |
| `current_label` | label | Current strength | 当前强势 | 2 | 4 | templates/_sector_central_brief.html.j2:37 |
| `method_body` | body | Follow leadership, check participation, then assess each stock’s entry. | 先看领涨，再查参与度，最后判断个股入场。 | 9 | 20 | templates/sector_central.html.j2:1529 |
| `distinction_body` | body | Strength tells you where to look. Entry conditions qualify the individual stock. | 强势提示研究方向，入场条件决定个股是否符合要求。 | 12 | 24 | templates/sector_central.html.j2:1546 |
| `leaders_link` | link | Inspect the leaders → | 查看领涨方向 → | 3 | 7 | templates/sector_central.html.j2:1534 |
| `compare_link` | link | Compare groups and windows → | 比较板块与时间区间 → | 4 | 10 | templates/_sector_central_brief.html.j2:24 |
| `find_link` | link | Find the changing leaders → | 寻找领涨变化 → | 4 | 7 | templates/_sector_central_brief.html.j2:49 |
| `participation_link` | link | Check who is participating → | 确认上涨是否扩散 → | 4 | 9 | templates/_sector_central_brief.html.j2:52 |
| `companies_link` | link | Inspect the companies → | 查看成分股 → | 3 | 6 | templates/_sector_central_brief.html.j2:55 |
| `not_measured_chip` | chip | Not measured | 暂无实测 | 2 | 4 | templates/sector_central.html.j2:1543 |
| `asof` | asof | as of | 截至 | 2 | 2 | templates/sector_central.html.j2:1519 |
| `basket_footnote` | footnote | Equal-weight sector basket · not the sector ETF | 等权重板块篮子 · 并非板块ETF | 8 | 15 | templates/_sector_central_brief.html.j2:13 |
| `wait_body` | body | The comparison appears when matching group and benchmark closes are available. | 取得同日期的板块与基准收盘数据后显示对比。 | 11 | 21 | templates/_sector_central_brief.html.j2:15 |

## explore_rotation — 16 reused / 0 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | What is actually changing | 实际在变什么 | 4 | 6 | templates/sector_central.html.j2:2198 |
| `tagline` | subtitle | — measured, not forecast | — 实测，非预测 | 3 | 7 | templates/sector_central.html.j2:2199 |
| `stands_h2` | h2 | Where everything stands | 全景位置 | 3 | 4 | templates/sector_central.html.j2:2155 |
| `quadrant_body` | body | Right = strong vs the S&P. Up = gaining speed this week. Leaders sweep from Leading into Weakening as they tire; laggards turn up through Improving. Hover any dot — click through for members. | 右 = 相对标普强。上 = 本周加速。领涨者会从「领先」滑向「走弱」；落后者经「改善」重新转强。悬停查看，点击进入成分页。 | 32 | 57 | templates/sector_central.html.j2:2167 |
| `measured_body` | body | Measured performance relative to the S&P 500 — a description, not a forecast or an entry call. | 相对标普500的实测表现 — 只是描述，不是预测，也不是入场信号。 | 17 | 31 | templates/sector_central.html.j2:2202 |
| `order_footnote` | footnote | Order = measured 3-month performance, not a recommendation. | 排序 = 实测3个月表现，并非推荐。 | 8 | 16 | templates/sector_central.html.j2:2211 |
| `quad_lead` | label | Leading — strong & rising | 领先 — 强且上行 | 3 | 7 | templates/sector_central.html.j2:2174 |
| `quad_weak` | label | Weakening — strong but fading | 走弱 — 强但转弱 | 4 | 7 | templates/sector_central.html.j2:2175 |
| `quad_improve` | label | Improving — weak but turning up | 改善 — 弱但转强 | 5 | 7 | templates/sector_central.html.j2:2176 |
| `quad_lag` | label | Lagging — weak & falling | 落后 — 弱且下行 | 3 | 7 | templates/sector_central.html.j2:2177 |
| `buyable_chip` | chip | Buyable | 可买 | 1 | 2 | templates/sector_central.html.j2:2184 |
| `changed_label` | label | What changed? | 发生了什么变化？ | 2 | 8 | templates/sector_central.html.j2:1535 |
| `rotation_link` | link | See the rotation map | 查看轮动图 | 4 | 5 | templates/sector_central.html.j2:2437 |
| `select_all_cta` | cta | Select all visible | 全选可见 | 3 | 4 | templates/sector_cycles.js:794 |
| `breadth_label` | label | MARKET BREADTH | 市场广度 | 2 | 4 | templates/sector_central.html.j2:2319 |
| `breadth_body` | body | Breadth tells you whether the rotation is a broad tide or a narrow few. Be selective when it is narrow. | 广度告诉你这是全面上涨还是少数领涨。领涨面窄时应精挑细选。 | 20 | 29 | templates/sector_central.html.j2:2317 |

## explore_lenses — 14 reused / 0 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Explore all | 浏览全部 | 2 | 4 | templates/sector_central.html.j2:2352 |
| `tagline` | subtitle | — every basket, sortable, with a rebased chart | — 全部篮子，可排序，附归一走势图 | 7 | 16 | templates/sector_central.html.j2:2353 |
| `compare_h2` | h2 | Themes & compare | 主题与比较 | 2 | 5 | templates/sector_central.html.j2:1505 |
| `confluence_h2` | h2 | Subsector Confluence | 子行业汇聚 | 2 | 5 | templates/sector_central.html.j2:2418 |
| `table_h2` | h2 | Performance table | 表现一览 | 2 | 4 | templates/sector_central.html.j2:2359 |
| `confluence_body` | body | Every sub-industry as its own basket, scored for entry timing. The read below is answer-first: the rotation backdrop, which groups just turned buyable, which are late or fading, and the stocks firing inside a group with the wind at its back. A timing map — confirm before acting. | 将每个子行业视作独立篮子，按入场时机评分。下方读数以结论优先：轮动情况、哪些子行业刚转为可买、哪些已偏晚或转弱，以及在顺风子行业中触发的个股。择时图——行动前请确认。 | 49 | 83 | templates/sector_central.html.j2:2421 |
| `confluence_footnote` | footnote | Every subsector is an equal-weight basket of its members, scored on a 3-day cadence for entry timing — not a buy list. | 每个子行业为其成分的等权篮子，按 3 日周期为入场时机评分——并非买入清单。层级衡量汇聚交叉的新鲜度（T1 最新）。 | 23 | 55 | templates/sector_central.html.j2:2434 |
| `rebase_footnote` | footnote | Lines are rebased to 0% at the start of the window. Toggle baskets from the legend; “All” covers the available cache history. | 曲线在窗口起点重设为 0%。可在图例中开关篮子；“全部”覆盖可用缓存历史。 | 22 | 36 | templates/sector_central.html.j2:2374 |
| `emerging_label` | label | Emerging | 升温 | 1 | 2 | templates/subsector_rotation.js:313 |
| `fading_label` | label | Fading | 退潮 | 1 | 2 | templates/subsector_rotation.js:314 |
| `versus_body` | body | 1W · 1M = return · trend = heating (+) or cooling (−), the map’s vertical axis | 1周 · 1月 = 涨跌 · 趋势 = 升温(+)/降温(−)，即图中纵轴 | 11 | 29 | templates/subsector_rotation.js:673 |
| `baskets_chip` | chip | Thematic Baskets | 主题篮子 | 2 | 4 | templates/sector_central.html.j2:2428 |
| `nasdaq_chip` | chip | Nasdaq-100 | 纳斯达克100 | 2 | 7 | templates/sector_central.html.j2:2426 |
| `russell_chip` | chip | Russell-2000 | 罗素2000 | 2 | 6 | templates/sector_central.html.j2:2427 |

## dossier — 24 reused / 0 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Where it stands | 所处位置 | 3 | 4 | templates/sector_cycles.js:1404 |
| `tagline` | subtitle | Tap any card — or its line on the chart — to focus it | 点按任意卡片（或图中其曲线）以聚焦 | 12 | 17 | templates/sector_cycles.html.j2:104 |
| `legs_h2` | h2 | Cycle legs — tap for the story | 周期区段 — 点击查看故事 | 6 | 11 | templates/sector_cycles.js:1428 |
| `record_h2` | h2 | Track record | 跟踪记录 | 2 | 4 | templates/subsector_rotation.js:343 |
| `evidence_date_label` | label | Evidence date | 证据日期 | 2 | 4 | templates/sector_central.html.j2:3711 |
| `measured_order_label` | label | Measured order | 实测排序 | 2 | 4 | templates/sector_central.html.j2:3710 |
| `last_trough_label` | label | Last trough | 上次底部 | 2 | 4 | templates/sector_cycles.js:1409 |
| `last_peak_label` | label | Last peak | 上次顶部 | 2 | 4 | templates/sector_cycles.js:1410 |
| `half_cycle_label` | label | Typical ½-cycle | 典型半周期 | 2 | 5 | templates/sector_cycles.js:1412 |
| `from_central_label` | label | From Sector Central | 来自板块情报 | 3 | 6 | templates/_sector_prophet_context.html.j2:5 |
| `members_label` | label | {n} stocks turning up | {n}只成分股转强 | 4 | 9 | docs/DESIGN_DOCTRINE.md:70 |
| `history_label` | label | History | 历史 | 1 | 2 | templates/sector_central.html.j2:3716 |
| `recon_label` | label | Reconstructed from prices | 按价格重建 | 3 | 5 | templates/sector_central.html.j2:3718 |
| `recorded_label` | label | Recorded at the time | 当时记录 | 4 | 4 | templates/sector_central.html.j2:3720 |
| `recon_body` | body | Reconstructed from prices — calculated later, not what Mastermind showed at the time. | 按价格重建 — 事后计算，并非 Mastermind 当时显示的内容。 | 12 | 31 | templates/sector_central.html.j2:3804 |
| `recorded_body` | body | Recorded by Mastermind at the time — not recalculated later. | 由 Mastermind 当时记录 — 事后未重新计算。 | 9 | 24 | templates/sector_central.html.j2:3850 |
| `context_body` | body | View this sector among the stocks loaded on this page; other filters still apply. Review each stock’s setup and entry conditions, and return to sector evidence for its dated readings. | 在当前已加载的股票中筛选该板块；其他筛选条件仍然适用。请结合各股的形态与入场条件，并返回板块证据查看其日期。 | 30 | 54 | templates/_sector_prophet_context.js.j2:66 |
| `screener_link` | link | View sector in Screener → | 在筛选器中查看该板块 → | 4 | 11 | templates/_sector_prophet_context.html.j2:10 |
| `return_link` | link | Return to sector evidence → | 返回板块证据 → | 4 | 7 | templates/_sector_prophet_context.html.j2:11 |
| `clear_link` | link | Clear context | 清除板块背景 | 2 | 6 | templates/_sector_prophet_context.html.j2:12 |
| `open_central_link` | link | Open in Sector Central | 在板块中枢查看 | 4 | 7 | templates/sector_cycles.js:1236 |
| `prophet_link` | link | Compare in Prophet → | 前往 Prophet 对照 → | 3 | 12 | templates/sector_central.html.j2:3714 |
| `invalid_subject_state` | state_title | Selected sector unavailable | 无法识别所选板块 | 3 | 8 | templates/_sector_prophet_context.js.j2:57 |
| `invalid_subject_body` | state_body | Return to sector evidence to choose a sector. Prophet Stock Signals remains available. | 请返回板块证据，选择一个板块。Prophet 选股仍可查看。 | 13 | 29 | templates/_sector_prophet_context.js.j2:58 |

## research — 3 reused / 8 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Research | 研究 | 1 | 2 | templates/sector_central.html.j2:1497 |
| `tagline` | subtitle | Ask a research question — it comes back with a full write-up… | 提出一个研究问题 — 将返回完整研判… | 12 | 17 | templates/mm_brain.js:3267 |
| `prepare_h2` | h2 | Prepare research question | 准备研究问题 | 3 | 6 | NEW |
| `subject_label` | label | Subject | 研究标的 | 1 | 4 | NEW |
| `question_label` | label | Question | 研究问题 | 1 | 4 | NEW |
| `snapshot_label` | label | Snapshot date | 快照日期 | 2 | 4 | NEW |
| `observation_label` | label | Observation date | 观测日期 | 2 | 4 | NEW |
| `evidence_mode_label` | label | Evidence mode | 证据模式 | 2 | 4 | NEW |
| `origin_label` | label | Origin | 来源 | 1 | 2 | NEW |
| `draft_note` | footnote | A prepared draft is not saved or sent until you choose to. | 草稿不会自动保存或发送，直到你主动操作。 | 12 | 20 | NEW |
| `estimate_body` | body | Research estimate — display only: {p}% over the next {n} sessions. Not a recommendation. | 研究估计 — 仅供展示：未来 {n} 个交易日的概率为 {p}%。不构成建议。 | 13 | 34 | templates/sector_central.html.j2:3891 |

## watches — 9 reused / 3 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Watches | 观察 | 1 | 2 | templates/sector_central.html.j2:1498 |
| `tagline` | subtitle | Saved investigations — resume one anytime | 已保存的调查 — 随时续看 | 5 | 11 | NEW |
| `accumulation_h2` | h2 | Accumulation watch — sector ETFs | 增持监测 — 板块 ETF | 4 | 10 | templates/_accumulation_watch.html.j2:51 |
| `accumulation_body` | body | Holdings gaining ETF weight faster than price alone explains — a heads-up on quiet accumulation, not a buy list. | 板块 ETF 中权重增长快于价格本身的持仓 — 悄然增持的提示信号，而非买入清单。 | 19 | 37 | templates/_accumulation_watch.html.j2:62 |
| `saved_chip` | chip | Saved | 已保存 | 1 | 3 | templates/watchlist.js:851 |
| `uptodate_chip` | chip | Up to date | 已是最新 | 3 | 4 | templates/watchlist.js:854 |
| `local_label` | label | Local to this browser | 仅存于本浏览器 | 4 | 7 | templates/watchlist.js:860 |
| `nosignal_chip` | chip | no signal yet | 暂无信号 | 3 | 4 | templates/_accumulation_watch.html.j2:81 |
| `top_label` | label | Top 8 · {n} tracked | 前 8 · 共 {n} 项跟踪 | 4 | 10 | templates/_accumulation_watch.html.j2:57 |
| `building_footnote` | footnote | Building — needs at least two daily holdings snapshots per fund (collection began 2026-06-11). Decomposed accumulation signals appear once a second snapshot lands. | 构建中 — 每只基金至少需要两个每日持仓快照（采集自 2026-06-11 开始）。第二个快照落地后将显示拆解后的增持信号。 | 24 | 58 | templates/_accumulation_watch.html.j2:87 |
| `alerts_state` | state_title | Condition alerts are not available | 条件提醒暂不提供 | 5 | 8 | NEW |
| `alerts_body` | state_body | Saving a symbol is not an alert. This page does not monitor conditions or notify. | 保存代码不等于提醒。本页不监测条件，也不发送通知。 | 15 | 25 | NEW |

## cycles — 34 reused / 5 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Sector Cycle Intelligence | 板块周期情报 | 3 | 6 | templates/sector_cycles.html.j2:38 |
| `tagline` | subtitle | Where every US sector stands | 每个美股板块所处的位置 | 5 | 11 | templates/sector_cycles.html.j2:40 |
| `intro_body` | body | The 11 GICS sector ETFs on one cycle clock — real price (rebased & log, so every line shares an axis) with a one-tap cycle-position view. Peaks & troughs are auto-detected from the tape, each sector is graded by where it sits in its cycle, and clicking a leg tells you what drove the move. Projections here are windows, not certainties — re-drawn nightly as new data lands. | 11 个 GICS 板块 ETF 同处一张周期时钟——真实价格（再基准化并取对数，使每条线共用同一坐标轴），并可一键切换为周期位置视图。波峰与波谷由价格走势自动识别，每个板块按其周期所处阶段评级，点击任一区段即可了解推动该走势的原因。这里的预测是时间窗口，而非确定性结论——每晚随新数据重新计算。 | 68 | 143 | templates/sector_cycles.html.j2:40 |
| `r1_header` | h2 | Header | 页头 | 1 | 2 | NEW |
| `r2_chart` | h2 | Chart | 图表 | 1 | 2 | NEW |
| `r3_controls` | h2 | Chart options | 图表选项 | 2 | 4 | templates/sector_cycles.html.j2:67 |
| `r4_leadership` | h2 | Leadership & turns | 领涨与拐点 | 2 | 5 | NEW |
| `r5_read` | h2 | The read | 解读 | 2 | 2 | templates/sector_cycles.js:1368 |
| `r6_timing` | h2 | Timing & projection | 时机与推演 | 2 | 5 | NEW |
| `r7_events` | h2 | Events | 事件 | 1 | 2 | NEW |
| `r8_grader` | h2 | Self-grader — measured accuracy | 自评分器 — 已衡量准确度 | 4 | 11 | templates/sector_central.html.j2:3334 |
| `r9_metadata` | h2 | Built | 生成于 | 1 | 3 | templates/sector_central.html.j2:2439 |
| `mode_price_chip` | chip | Price | 价格 | 1 | 2 | templates/sector_cycles.html.j2:62 |
| `mode_osc_chip` | chip | Cycle position | 周期位置 | 2 | 4 | templates/sector_cycles.html.j2:63 |
| `scale_log_chip` | chip | Log | 对数 | 1 | 2 | templates/sector_cycles.html.j2:70 |
| `scale_linear_chip` | chip | Linear | 线性 | 1 | 2 | templates/sector_cycles.html.j2:71 |
| `zoom_hint_aria` | aria | scroll · drag | 滚动 · 拖拽 | 2 | 5 | templates/sector_cycles.js:511 |
| `zoom_home_chip` | chip | Home ⤢ | 首页 ⤢ | 1 | 3 | templates/sector_cycles.js:513 |
| `range_7y_chip` | chip | 7y | 7年 | 1 | 2 | templates/sector_cycles.js:506 |
| `all_chip` | chip | All | 全选 | 1 | 2 | templates/sector_cycles.js:1751 |
| `clear_chip` | chip | Clear | 清空 | 1 | 2 | templates/sector_cycles.js:1752 |
| `compare_chip` | chip | Compare | 对比 | 1 | 2 | templates/subsector_rotation.js:848 |
| `reanchor_chip` | chip | Re-anchor | 再基准化 | 2 | 4 | templates/sector_central.html.j2:2222 |
| `phase_topping_chip` | chip | Topping · late | 见顶 · 晚期 | 2 | 5 | templates/sector_cycles.js:1542 |
| `phase_trending_chip` | chip | Trending | 上行中 | 1 | 3 | templates/sector_cycles.js:1543 |
| `phase_rolling_chip` | chip | Rolling over | 回落中 | 2 | 3 | templates/sector_cycles.js:1544 |
| `phase_prime_chip` | chip | Prime entry | 入场良机 | 2 | 4 | templates/sector_cycles.js:1545 |
| `phase_bottoming_chip` | chip | Bottoming | 筑底中 | 1 | 3 | templates/sector_cycles.js:1548 |
| `all_phases_chip` | chip | All phases | 全部阶段 | 2 | 4 | templates/sector_cycles.js:619 |
| `hz_1m_chip` | chip | P(turn ≤ 1m) | P(转折≤1月) | 3 | 8 | templates/sector_cycles.js:1091 |
| `hz_3m_chip` | chip | ≤3m | ≤3月 | 1 | 3 | templates/sector_cycles.js:1092 |
| `hz_6m_chip` | chip | ≤6m | ≤6月 | 1 | 3 | templates/sector_cycles.js:1093 |
| `clocks_chip` | chip | Clocks disagree | 时钟分歧 | 2 | 4 | templates/sector_cycles.js:171 |
| `overdue_chip` | chip | Overdue | 已逾期 | 1 | 3 | templates/country_cycles.html.j2:122 |
| `short_history_chip` | chip | Short history | 价格历史不足 | 2 | 6 | templates/sector_central.html.j2:3507 |
| `dna_h2` | h2 | Cycle DNA — why it rhymes | 周期基因 — 历史为何押韵 | 5 | 11 | templates/sector_cycles.js:1258 |
| `hazard_label` | label | Turn hazard (calibrated) | 转折风险（校准） | 3 | 8 | templates/sector_cycles.js:1102 |
| `hazard_footnote` | footnote | P(next confirmed turn within horizon) for the open {direction}-leg. PASS cells: isotonic-calibrated hazard model (calibration-gated vs KM, W4.2 gate). PRIOR cells: KM base rate, shown muted. Display-only context — never a signal. | 开放周期段在各时间窗内出现下一个已确认拐点的概率。PASS=经W4.2门槛校准的模型输出；PRIOR=KM基准率（弱化显示）。仅供展示，绝非信号。 | 37 | 73 | templates/sector_cycles.js:1101 |
| `forecast_footnote` | footnote | Projected next {turn} ≈ {month} ({low}–{high}), from this {unit}’s own median half-cycle. A timing estimate, not a guarantee. | 预计下次{turn}约在 {month}（{low}–{high}），基于该{unit}自身的中位半周期。仅为时间估计。 | 20 | 59 | templates/sector_cycles.js:1134 |

## components — 14 reused / 10 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Shared components | 共享组件 | 2 | 4 | NEW |
| `tagline` | subtitle | Patterns every board shares | 各看板共用的模式 | 4 | 8 | NEW |
| `stance_act` | chip | Act | 行动 | 1 | 2 | NEW |
| `stance_get_ready` | chip | Get ready | 做好准备 | 2 | 4 | templates/china_altdata.html.j2:227 |
| `stance_watch` | chip | Watch — don’t chase | 观察 —— 别追 | 3 | 6 | templates/stage_analysis.html.j2:1497 |
| `stance_protect` | chip | Protect gains | 保护利润 | 2 | 4 | templates/stage_analysis.html.j2:1499 |
| `stance_aside` | chip | Stand aside | 暂时观望 | 2 | 4 | templates/stage_analysis.html.j2:1500 |
| `stance_ignore` | chip | Ignore | 忽略 | 1 | 2 | templates/options.html.j2:3630 |
| `asof_label` | asof | As of | 截至 | 2 | 2 | templates/sector_cycles.html.j2:45 |
| `asof_pattern` | asof | As of {date} · {source} | 截至 {date} · {source} | 4 | 17 | templates/sector_central.html.j2:3865 |
| `footnote_pattern` | footnote | Display-only context — never a signal. | 仅供展示，绝非信号。 | 6 | 10 | templates/sector_cycles.js:1101 |
| `badge_model` | chip | MODEL | 模型 | 1 | 2 | NEW |
| `badge_prior` | chip | PRIOR | 先验 | 1 | 2 | templates/sector_cycles.js:1077 |
| `prior_gloss` | footnote | PRIOR — historical base rate, not a model | 先验 — 历史基准率，并非模型 | 7 | 13 | NEW |
| `grader_caption` | footnote | Conditional hit rate, not a win rate | 条件命中率，并非胜率 | 7 | 10 | NEW |
| `lock_chip` | chip | Locked | 已锁定 | 1 | 3 | NEW |
| `see_all_link` | link | See all {n} ▾ | 展开全部 {n} ▾ | 3 | 8 | templates/sector_cycles.js:1551 |
| `see_less_link` | link | See less ▴ | 收起 ▴ | 2 | 3 | templates/sector_cycles.js:1578 |
| `alt_table_label` | label | Performance table | 表现一览 | 2 | 4 | templates/sector_central.html.j2:2359 |
| `alt_map_link` | link | See the rotation map | 查看轮动图 | 4 | 5 | templates/sector_central.html.j2:2437 |
| `alt_toggle_aria` | aria | Switch between chart and table | 在图表与表格之间切换 | 5 | 10 | NEW |
| `rel_not_supplied` | state_title | Sector relationship not supplied | 未提供板块间关系 | 4 | 8 | NEW |
| `no_evidence_attached` | state_title | No Sector evidence attached | 未附带板块证据 | 4 | 7 | NEW |
| `search_aria` | aria | Search sectors | 搜索板块 | 2 | 4 | templates/sector_cycles.js:1750 |

## states — 25 reused / 15 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | States | 状态 | 1 | 2 | NEW |
| `tagline` | subtitle | What happened, and what still works | 发生了什么，以及哪些仍可用 | 6 | 13 | NEW |
| `fresh_title` | state_title | Up to date | 已是最新 | 3 | 4 | templates/watchlist.js:854 |
| `fresh_body` | state_body | The latest completed session is in; each panel stamps its own evidence date. | 最新完成的交易日已纳入；每个面板均标注证据日期。 | 13 | 24 | NEW |
| `stale_title` | state_title | Older evidence shown | 显示较早证据 | 3 | 6 | NEW |
| `stale_body` | state_body | Observation is no longer current. | 观测已过期。 | 5 | 6 | templates/sector_central.html.j2:1968 |
| `stale_action` | state_action | Check the evidence date | 请核对证据日期 | 4 | 7 | NEW |
| `incompatible_generation_title` | state_title | History is from a different day | 历史来自不同日期 | 6 | 8 | templates/sector_central.html.j2:3537 |
| `incompatible_generation_body` | state_body | History {x}, current read {y}. Not drawn, so the two are never mixed. | 历史 {x}，当前读数 {y}。不绘制，避免混用。 | 13 | 23 | templates/sector_central.html.j2:3539 |
| `partial_title` | state_title | Partial coverage | 覆盖不完整 | 2 | 5 | templates/sector_central.html.j2:3877 |
| `partial_body` | state_body | Based on {x} of {y} checks | 基于 {y} 项检查中的 {x} 项 | 6 | 14 | templates/sector_central.html.j2:3875 |
| `corrected_title` | state_title | Record corrected | 记录已修正 | 2 | 5 | NEW |
| `corrected_body` | state_body | Comparison reset after a source change. | 数据变更后，正在重新建立比较。 | 6 | 15 | templates/sector_central.html.j2:1973 |
| `abstained_title` | state_title | No call made | 未下判断 | 3 | 4 | NEW |
| `abstained_body` | state_body | Forecast: none — no forecasting model has been approved for this read. | 预测：无 — 此项尚无获批的预测模型。 | 11 | 17 | templates/sector_central.html.j2:3895 |
| `error_title` | state_title | History unavailable right now | 历史暂不可用 | 4 | 6 | templates/sector_central.html.j2:3746 |
| `error_body` | state_body | The current read above is unaffected. | 上方的当前读数不受影响。 | 6 | 12 | templates/sector_central.html.j2:3747 |
| `empty_title` | state_title | No recorded events are open. | 目前没有已记录事件。 | 5 | 10 | templates/sector_central.html.j2:3820 |
| `empty_body` | state_body | Events appear here once Mastermind records one. | Mastermind 记录后将自动出现。 | 7 | 19 | templates/sector_central.html.j2:3821 |
| `no_access_title` | state_title | Sign in to view | 登录后可查看 | 4 | 6 | NEW |
| `no_access_body` | state_body | Sign in with access to view these observations. | 请使用有权限的账户登录查看。 | 8 | 14 | templates/sector_central.html.j2:1990 |
| `no_access_action` | state_action | Sign in | 登录 | 2 | 2 | templates/theme.js:2001 |
| `loading_title` | state_title | Loading… | 加载中… | 1 | 4 | templates/sector_central.html.j2:2431 |
| `loading_body` | state_body | Loading history… | 历史加载中… | 2 | 6 | templates/sector_central.html.j2:3743 |
| `offline_title` | state_title | Offline — changes kept locally | 离线 · 更改已存在本地 | 4 | 10 | templates/watchlist.js:863 |
| `offline_body` | state_body | We cannot reach the network right now. Your changes are kept on this device and written through when it comes back. | 当前无法连接网络。更改会先保存在本机，恢复后自动写入。 | 21 | 27 | templates/watchlist.js:864 |
| `unauthorized_title` | state_title | Not in your plan | 当前方案未包含 | 4 | 7 | NEW |
| `unauthorized_body` | state_body | You are signed in; this part needs a different plan. | 你已登录；此部分需要其他方案。 | 10 | 15 | NEW |
| `unauthorized_action` | state_action | See plans | 查看方案 | 2 | 4 | NEW |
| `locked_title` | state_title | Locked | 已锁定 | 1 | 3 | NEW |
| `locked_body` | state_body | This section is withheld by its owner. The rest of the page stays available. | 此部分由其所有者保留。页面其余内容仍可查看。 | 14 | 22 | NEW |
| `invalid_payload_title` | state_title | Source could not be checked | 无法核验来源 | 5 | 6 | templates/_sector_central_coverage.js.j2:67 |
| `invalid_payload_body` | state_body | The source coverage could not be checked. Open the full evidence for details. | 无法核验来源覆盖情况。请打开完整证据查看详情。 | 13 | 23 | templates/_sector_central_coverage.js.j2:67 |
| `zero_title` | state_title | No names clear both gates today. | 今日无名单同时通过双门槛。 | 6 | 13 | templates/us_stocks_v2.html.j2:212 |
| `zero_body` | state_body | Zero fill pressure: however many qualify (an empty lane is honest). | 零填充压力：合格多少就显示多少（空榜也是诚实的）。 | 11 | 25 | templates/us_stocks_v2.html.j2:205 |
| `empty_search_title` | state_title | No items match this phase | 该阶段暂无条目 | 5 | 7 | templates/sector_cycles.js:717 |
| `empty_search_body` | state_body | Nothing on the clock — tap an item or hit Select all visible to chart them. | 图中暂无条目——点击任一条目或点全选可见即可绘制。 | 15 | 25 | templates/sector_cycles.js:719 |
| `empty_search_action` | state_action | All phases | 全部阶段 | 2 | 4 | templates/sector_cycles.js:619 |
| `uncertain_command_title` | state_title | Command outcome uncertain | 指令结果未确认 | 3 | 7 | NEW |
| `uncertain_command_body` | state_body | It was sent, but the result is not confirmed. Nothing retries automatically — check the record before repeating it. | 操作已发出，但结果未确认。不会自动重试——重复前请先核对记录。 | 18 | 31 | NEW |

## authority — 10 reused / 5 NEW

| key | role | EN | ZH | EN words | ZH chars | source |
|---|---|---|---|---:|---:|---|
| `title` | h1 | Authority & record | 权威与记录 | 2 | 5 | NEW |
| `tagline` | subtitle | What is current, candidate, and archived | 何为现行、候选、归档 | 6 | 10 | NEW |
| `current_label` | label | Current | 现行 | 1 | 2 | NEW |
| `candidate_label` | label | Candidate | 候选 | 1 | 2 | NEW |
| `archive_label` | label | Archive | 归档 | 1 | 2 | templates/committee.html.j2:1702 |
| `toc_label` | label | Table of contents | 目录 | 3 | 2 | NEW |
| `built_asof` | asof | Built {timestamp} | 生成于 {timestamp} | 2 | 14 | templates/sector_central.html.j2:2439 |
| `generated_asof` | asof | Generated {timestamp} | 生成于 {timestamp} | 2 | 14 | templates/sector_central.html.j2:2447 |
| `grader_h2` | h2 | Self-grader — measured accuracy | 自评分器 — 已衡量准确度 | 4 | 11 | templates/sector_central.html.j2:3334 |
| `grader_body` | body | Realized directional hit-rate, cross-sectional rank-IC and excess-vs-SPY of the conviction calls, by horizon. Sparse until it accrues; never fed back into the live score. | 按时间跨度衡量信念判断的已实现方向命中率、横截面秩相关与超越SPY的超额收益。数据累积前较稀疏；绝不回灌入实时评分。 | 29 | 58 | templates/sector_central.html.j2:3336 |
| `accruing_body` | body | Accruing — dated calls are logged and will be graded against realized forward returns as time passes ({n} calls logged). | 累积中 — 带日期的判断已记录，将随时间推移对照已实现的前瞻收益进行评分（已记录 {n} 个判断）。 | 19 | 46 | templates/sector_central.html.j2:3323 |
| `lanes_footnote` | footnote | Lanes are the only gated, graded calls on this page — everything below is context, measured nightly. | 操作清单是本页唯一的门控与自评分判断 — 下方内容均为背景信息，每晚计算。 | 16 | 35 | templates/sector_central.html.j2:2093 |
| `basis_total_return` | label | total return | 含股息总回报 | 2 | 6 | templates/_sector_central_coverage.js.j2:81 |
| `basis_price_only` | label | price only | 仅价格 | 2 | 3 | templates/_sector_central_coverage.js.j2:81 |
| `clock_mismatch_body` | state_body | The measurement date is later than its source page. Review the source dates. | 实测日期晚于来源页面日期。请核对来源日期。 | 13 | 21 | templates/_sector_central_coverage.js.j2:71 |

## Reused vs NEW — totals

| board | reused | NEW | total |
|---|---:|---:|---:|
| brief | 18 | 0 | 18 |
| explore_rotation | 16 | 0 | 16 |
| explore_lenses | 14 | 0 | 14 |
| dossier | 24 | 0 | 24 |
| research | 3 | 8 | 11 |
| watches | 9 | 3 | 12 |
| cycles | 34 | 5 | 39 |
| components | 14 | 10 | 24 |
| states | 25 | 15 | 40 |
| authority | 10 | 5 | 15 |
| **total** | **167** | **46** | **213** |

## NEW ZH strings — native-speaker check required

None of these exists in the shipped templates. EN is fixed by the packet or
composed from shipped EN fragments; the ZH is new prose and must be checked by a
native speaker before the boards are labelled final. Vocabulary notes follow the
list.

1. `research.prepare_h2` — 准备研究问题
2. `research.subject_label` — 研究标的
3. `research.question_label` — 研究问题
4. `research.snapshot_label` — 快照日期
5. `research.observation_label` — 观测日期
6. `research.evidence_mode_label` — 证据模式
7. `research.origin_label` — 来源
8. `research.draft_note` — 草稿不会自动保存或发送，直到你主动操作。
9. `watches.tagline` — 已保存的调查 — 随时续看
10. `watches.alerts_state` — 条件提醒暂不提供
11. `watches.alerts_body` — 保存代码不等于提醒。本页不监测条件，也不发送通知。
12. `cycles.r1_header` — 页头
13. `cycles.r2_chart` — 图表
14. `cycles.r4_leadership` — 领涨与拐点
15. `cycles.r6_timing` — 时机与推演
16. `cycles.r7_events` — 事件
17. `components.title` — 共享组件
18. `components.tagline` — 各看板共用的模式
19. `components.stance_act` — 行动
20. `components.badge_model` — 模型
21. `components.prior_gloss` — 先验 — 历史基准率，并非模型
22. `components.grader_caption` — 条件命中率，并非胜率
23. `components.lock_chip` — 已锁定
24. `components.alt_toggle_aria` — 在图表与表格之间切换
25. `components.rel_not_supplied` — 未提供板块间关系
26. `components.no_evidence_attached` — 未附带板块证据
27. `states.title` — 状态
28. `states.tagline` — 发生了什么，以及哪些仍可用
29. `states.fresh_body` — 最新完成的交易日已纳入；每个面板均标注证据日期。
30. `states.stale_title` — 显示较早证据
31. `states.stale_action` — 请核对证据日期
32. `states.corrected_title` — 记录已修正
33. `states.abstained_title` — 未下判断
34. `states.no_access_title` — 登录后可查看
35. `states.unauthorized_title` — 当前方案未包含
36. `states.unauthorized_body` — 你已登录；此部分需要其他方案。
37. `states.unauthorized_action` — 查看方案
38. `states.locked_body` — 此部分由其所有者保留。页面其余内容仍可查看。
39. `states.uncertain_command_title` — 指令结果未确认
40. `states.uncertain_command_body` — 操作已发出，但结果未确认。不会自动重试——重复前请先核对记录。
41. `authority.title` — 权威与记录
42. `authority.tagline` — 何为现行、候选、归档
43. `authority.current_label` — 现行
44. `authority.candidate_label` — 候选
45. `authority.toc_label` — 目录

Vocabulary notes on the NEW ZH:
- Cycles region names (页头, 图表, 领涨与拐点, 时机与推演, 事件) are region labels only;
  图表 continues the shipped 图表选项 (`templates/sector_cycles.html.j2:67`).
- Control names Compare/对比 and Re-anchor/再基准化: the deck cites shipped ZH terms
  (`templates/subsector_rotation.js:848`, `templates/sector_central.html.j2:2222`);
  only the EN control label is composed.
- Overdue/已逾期 reuses the shipped overdue vocabulary of
  `templates/country_cycles.html.j2:122` (已过期窗口，按逾期程度排列).
- 状态 titles borrow the product's plain-state register (已是最新, 离线, 已保存):
  no apology wording, unknown is never described as zero, empty states say why.
- 未附带板块证据 follows the shipped 附带证据 of `templates/news.html.j2:924`.

## Budget-driven adjustments from shipped strings

- `cycles.title`: the shipped h1 「Where every US sector stands / 每个美股板块所处
  的位置」 is 5 EN words, over the h1 budget of 4. The shipped kicker 「Sector Cycle
  Intelligence / 板块周期情报」 (`templates/sector_cycles.html.j2:38`) is the h1, and
  the shipped h1 became the subtitle (`cycles.tagline`) unchanged. No string was
  rewritten.
- Quadrant legend labels (「Weakening — strong but fading / 走弱 — 强但转弱」 etc.) are
  4 EN words as chips, over the ≤3 chip budget; they stay verbatim under the `label`
  role (legend labels have no word budget). No string was shortened.

