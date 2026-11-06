# Wave B: news flow on the ticker rail (design and build spec)

Author: ORCH-UP (Opus 5.5 orchestration seat under MI Meta-CEO fd47d431), 2026-10-12, item U6.
Form: scratchpad spec only. No branch, no PR (seat rescope). The seat commissions Wave B from this file after #8902 (n-vel), #8897 (annotations) and #8905 (cluster v2) merge.

Inputs read for this spec:
- PR diffs #8897, #8902, #8905 (saved next to this file as pr8897.diff, pr8902.diff, pr8905.diff).
- macro main: engine/qbus_news_store.py, app/ticker_news.py, engine/leadership_receipt.py.
- terminal master b4095c3debbd (ubuntu3 ~/lanes/wt/mi-g10-t-rail-a11y/terminal): components/news/TickerNewsPanel.tsx and .module.css, app/globals.css, app/settings.css, app/layout.tsx, lib/newsContract.ts, lib/newsValidation.ts, lib/server/tickerNews.ts, components/charts/svgChart.ts, components/fin/CompanyThemeContextCard.tsx, lib/companyThemeExposure.ts, terminal/AGENTS.md.

## What Wave B is

The rail already lists the news for one security. Wave B adds one plain sentence above that list: how many reports this security got in the last 24 hours, and whether that is more than, about the same as, or less than its own typical day. A details button opens the receipt behind the sentence: a 28-day tally, the 7-day count, how many distinct stories the reports group into, which sources were counted, the windows, and the time of the count.

It is a count of coverage. It never says what the coverage means for the price. It never compares one security with another. It never sorts, filters or ranks anything.

User job: is the wire on this name busy right now, and is it many outlets carrying one story or many separate stories? The answer takes under a second to read and implies no direction.

## 0. NOT DONE UNLESS (binding acceptance gates for every lane and every PR)

Each builder commission copies these gates inline. A pointer to this file is context, not enforcement.

- G1 Rights parity. Every flow count includes only items whose source is in the request rights.allowed_sources AND whose news_states.status is active. That is the exact filter the snapshot rows use. A test seeds a restricted source and asserts that the counts and the rows both exclude it. A count that includes content the viewer cannot open is a rights leak, not a rounding difference.
- G2 Commit frozen. def commit in engine/qbus_news_store.py (zero-revision handling and the expected_cursor compare-and-swap) is byte-identical before and after Wave B. All new store code is read-only and runs on the query_only connection. Evidence: a diff showing no hunk inside def commit, plus the existing commit tests passing unchanged.
- G3 Degrade never takes rows down. Any failure in the flow calculation returns HTTP 200 with the rows intact and flow.state set to unavailable. A test forces the calculation to raise.
- G4 Deploy-order independence. Terminal lane B3 merges and runs against an API that sends no flow key: the strip stays hidden and no error appears. API lane B2 serves flow to a terminal that predates B3: the old parser drops the key and no error appears. Each side has a test.
- G5 Provenance complete. Every served count names its source set, window, calculation and as-of time (section 1.3). When state is ok, a test asserts every provenance field is present and non-empty.
- G6 Product law. None of the following, anywhere in Wave B:
  - sentiment, impact scores or confidence
  - ranking or sorting across securities
  - anything that reads as buy or sell
  - color that encodes direction
  - the word validated
  Comparison words compare this security with its own history only. Proof:
  - banned-word tests on the EN and ZH copy (list in 3.5)
  - a route-table test showing no endpoint returns flow for more than one security or accepts a sort parameter
  - a stylesheet test showing NewsFlowStrip.module.css and the .liveDot rule reference none of --up, --down, --buy, --sell or --signal
- G7 Units honest. "reports" means items. "stories" means clusters. No string calls an item a story. The n-vel engine EN label, which says stories while counting items, is renamed in lane B1.
- G8 Glance budget. The strip is at most 9 words in EN and at most 20 characters in ZH (CJK characters plus digits; spaces and separators excluded), in every state, at n = 9999. A lex test enumerates every state.
- G9 Keyboard and screen reader.
  - The details control opens on click, Enter and Space. Hover is never the only way in.
  - Escape closes it and returns focus to the button.
  - Screen readers can reach the strip text.
  - The tally has an aria-label carrying the same numbers.
  - The live dot has a localized accessible name.
- G10 East convention. With html data-updown="east", nothing in the rail changes color meaning. The live dot stays a neutral status token (never --buy), and no flow element changes color. Proof: a screenshot cell plus the token test from G6.
- G11 Evidence matrix complete (section 6).
  - Every live cell is captured, and its crop is posted in the PR body.
  - Light cells are delivered as specimen renders and labelled as specimens.
  - No cell passes on functional success alone; each is judged as a design.
- G12 Fresh happy path. On a fresh terminal load of a seeded security, the strip arrives with the first snapshot response, with no reload and no manual cursor reset. A race you reload around is a bug you own.
- G13 No self-merge. Builder lanes return DRAFT PRs, exact full heads and visual crops to the seat. The seat reviews, wires CI (lanes never edit .github) and merges.

## 1. API contract delta: ticker_news.snapshot.v1 gains a flow key

### 1.1 Where flow appears

- The GET snapshot first page (cursor absent or null) carries a top-level key flow, always present in one of the three states below. The snapshot schema string stays ticker_news.snapshot.v1, because the change is additive.
- Cursor pages do not carry the key. The flow describes the moment the panel opened, not a page.
- The changes endpoint, story detail and SSE never carry flow. The terminal refreshes flow only when it reloads page one: on panel open, on symbol change, and on explicit refresh. There are two reasons:
  - A count that ticks with every SSE event invites people to watch the number move, which is the signal-reading the product law forbids.
  - It would repeat the rights-filtered aggregation on every event.
- No new endpoint. In particular, no list, batch, screener or sort route returns flow across securities.

### 1.2 Shape (schema ticker_news.flow.v1)

    flow = {
      schema:                "ticker_news.flow.v1",
      state:                 "ok" | "thin_history" | "unavailable",
      reason:                null | "no_accessible_sources" | "calculation_failed",
      coverage:              "complete" | "partial",
      as_of:                 ISO-8601 UTC instant (second precision) | null,
      reports_24h:           int >= 0 | null,
      reports_7d:            int >= 0 | null,
      stories_24h:           int >= 0 | null,
      median_daily_28d:      number >= 0 | null,
      daily_counts_28d:      list of exactly 28 ints >= 0, oldest day first | null,
      history_days_observed: int 0..28 | null,
      comparison:            "busier" | "typical" | "quieter" | "insufficient_history" | null,
      provenance:            object (1.3) | null
    }

State semantics:
- ok: history_days_observed >= 20 (the engine _SUFFICIENT_HISTORY_DAYS). All counts are non-null. comparison is busier, typical or quieter, or null when coverage is partial.
- thin_history: fewer than 20 observed days. Counts are non-null and median_daily_28d is null. comparison is insufficient_history, or null when coverage is partial.
- unavailable: reason is non-null. Every count, comparison, as_of and provenance is null.

Invariants: stories_24h <= reports_24h <= reports_7d; daily_counts_28d has exactly 28 entries; history_days_observed <= 28. The terminal parser treats any violation as malformed and maps it to unavailable (section 2.2).

coverage is partial when the snapshot state is catching_up or degraded, and complete otherwise. When coverage is partial, comparison is null whatever the history. An incomplete count would read as quieter for a reason that comes from our feed, not from the market.

### 1.3 Provenance: every count names its source, window, calculation and as-of time

    provenance = {
      velocity_schema:        "qbus.news_velocity.v1",
      sources_counted:        sorted list of source ids = rights.allowed_sources actually applied,
      status_counted:         "active",
      distinct_by:            "source + source_item_id",
      story_grouping:         "news_cluster_members.cluster_id; a report in no cluster is its own story",
      cluster_policy_version: "qbus_news_cluster.v2",
      windows: {
        reports_24h: "rolling, closed at both ends: [as_of - 24h, as_of]",
        reports_7d:  "rolling, closed at both ends: [as_of - 7d, as_of]",
        daily_28d:   { start_date, end_date, unit: "UTC calendar day",
                       excludes: "the current UTC day", order: "oldest first" }
      },
      calculation:            the engine METHOD string verbatim
                              ("distinct stories; withdrawn excluded; UTC calendar days; median of 28 prior days")
                              plus comparison_rule: "flow_compare.v1",
      time_basis_counts_24h:  { published_at: int, received_at: int }
    }

Notes:
- as_of is the calculation instant, meaning the now that the API passes to the engine. It is not the time of the newest report, and the details panel labels it "Counted at".
- Lane B1 asserts the window boundaries exactly as #8902 implements them (closed at both ends). If B1 finds they differ, the provenance text follows the code, never the other way round.
- time_basis_counts_24h answers J3, the open spec question from U2. The n-vel basis_counts are unwindowed. Wave B adds basis_counts_24h over exactly the reports counted in reports_24h, the headline number, and keeps the unwindowed field for existing engine consumers.
- The engine label field ({en, zh}) is NOT served. The terminal lexicon owns all user copy, so there is one copy source.
- cluster_policy_version is the module constant from engine/qbus_news_cluster.py. The #8905 diff shows it is not stored per cluster row, so clusters built before v2 cannot be told apart at read time (section 10).

### 1.4 Comparison rule flow_compare.v1

The engine computes the comparison once and the API serves it. The terminal never recomputes it.

    if coverage == "partial":                               comparison = null
    elif not sufficient_history:                            "insufficient_history"
    elif r24 >= 2 * median and r24 - median >= 3:          "busier"
    elif median >= 2 and r24 <= median / 2:                "quieter"
    else:                                                   "typical"

Why these thresholds:
- A ratio alone would call 1 against 0, or 2 against 1, busier. That is noise on thinly covered names, and the floor of 3 extra reports stops it.
- Quieter needs a typical day of at least 2, because "quieter than a day of zero or one report" says nothing.
- The rule compares a rolling 24 hours with calendar days. Both are 24-hour spans, and the details panel says how they differ.

The thresholds are display copy rules, not a tested finding. They carry no authority: they may not feed ranking, sizing or gating. Any change to them bumps the rule id. The numbers are seat decision D-W2 (section 9).

### 1.5 Rights parity in the engine and store (G1)

- compute_news_velocity gains a REQUIRED keyword-only parameter allowed_sources (Collection[str]). There is no default, so a caller cannot silently count every source. An empty collection gives zero counts, and the API maps empty rights to unavailable / no_accessible_sources before it calls the engine, so the path fails closed at both ends.
- _STORY_SQL changes from "s.status != withdrawn" to "s.status = active AND s.source IN (allowed)". That matches the snapshot filter exactly, so a future status value fails closed.
- New read-only method NewsStore.news_flow(security_id, *, now, rights) -> dict:
  - runs compute_news_velocity on the store query_only connection with allowed_sources = rights.allowed_sources
  - runs one stories_24h query: COUNT DISTINCT over a coalesce of cluster_id and a per-item key, joining news_cluster_members on (source, source_item_id)
  - never calls commit and never opens a writable connection
- Snapshot row parity check (B1 does this first): confirm that row source_count and item_count count only members that are active and in allowed_sources.
  - If they do not, fix the snapshot read SQL (read path only, allowed under G2). Otherwise the rail could print "3 reports from 2 outlets" for a story that shows one.
  - Either way, add a pinning test.

## 2. Degrade semantics and parse isolation

### 2.1 API (lane B2)

- Flow is computed after the rows, inside its own try/except Exception.
  - Any exception is logged with logger.exception. This is a FastAPI request path, so it is exempt from the annotation-line rule.
  - The response then serves state unavailable with reason calculation_failed. The rows, next_cursor, has_more, source_health and snapshot state are unchanged, and the status stays HTTP 200.
  - This covers the U2 GAP: _parse_instant raises ValueError on garbage. That is unreachable through the store writers today, but the wrapper must not depend on that.
- Empty rights.allowed_sources gives state unavailable with reason no_accessible_sources, and the engine is not called.
- Snapshot state catching_up or degraded gives coverage partial and comparison null. The counts are still served.
- Cost: B1 measures p95 news_flow latency on a seeded store (28 days, 5,000 items, 3 sources) and records it in the PR body. If p95 exceeds 50 ms, B1 reports it to the seat. Wave B makes no schema or index change on its own.

### 2.2 Terminal (lane B3)

- New parseTickerNewsFlow(value: unknown): TickerNewsFlow | null. It never throws.
  - Key missing: null.
  - Any type error, out-of-range number, unknown enum, wrong schema string or broken invariant (1.2): { state: "unavailable", reason: "malformed", all counts null }.
  - "malformed" is a terminal-only reason and is not part of the API enum.
- parseTickerNewsSnapshot adds flow: when the key is present, parseTickerNewsFlow(obj.flow); otherwise null. Row parsing stays exactly as strict as today, and a malformed flow must never throw the snapshot.
- Load-bearing: lib/server/tickerNews.ts:86 returns Response.json(parse(decoded)), so the proxy re-serializes the PARSED object. Any flow the parser does not carry is silently dropped at the proxy. tickerNewsProxy.test.ts must assert that flow survives the proxy round trip, and that an absent flow stays absent.

## 3. Glance tier, details tier, and all copy (EN and ZH)

### 3.1 Placement

- A one-line strip sits directly under the rail bar (title, symbol, live dot) and above the catching-up chip, outside the scroll area, so it never scrolls away.
- It arrives in the same response as page one, so it causes no layout jump and needs no skeleton.
- It is hidden when:
  - flow is null (old API, or a cursor page)
  - the panel state is restricted or unavailable, because those states already have their own words
  - flow reason is no_accessible_sources
  - the snapshot has zero rows, because the empty state already says it
  - the symbol has just changed and page one for the new symbol has not arrived. It must never show the previous symbol counts, because a stale strip describes the wrong security.

### 3.2 Glance strip copy

The strip is two spans: a count phrase, then a comparison phrase. They are separated by an aria-hidden middle dot plus a visually hidden comma for screen readers.

| key | when | EN | ZH |
|---|---|---|---|
| count.zero | reports_24h = 0 | No reports in 24h | 24小时内暂无报道 |
| count.one | reports_24h = 1 | 1 report in 24h | 24小时内 1 篇报道 |
| count.many | reports_24h > 1 | {n} reports in 24h | 24小时内 {n} 篇报道 |
| cmp.busier | comparison busier | Busier than a typical day | 比平日更密集 |
| cmp.typical | comparison typical | About a typical day | 与平日相当 |
| cmp.quieter | comparison quieter | Quieter than a typical day | 比平日清淡 |
| cmp.insufficient | insufficient_history | Too little history to compare | 历史尚短，暂不比较 |
| cmp.partial | coverage partial | Counts may be incomplete | 计数可能不完整 |
| state.unavailable | state unavailable (calculation_failed or malformed) | Report counts unavailable right now | 报道计数暂不可用 |
| more.label | details button accessible name | How these counts work | 计数说明 |
| live.label | live dot accessible name | Live | 实时 |

Budget check:
- EN worst case is 4 + 5 = 9 words, from count.many with cmp.insufficient. The unavailable state is 5 words, with no comparison and no button.
- ZH worst case at n = 9999 is 5 + 4 + 3 + 8 = 20 characters.
- count.zero never pairs with busier, because the rule makes that impossible.

### 3.3 Details panel copy (technical tier, opened by the button)

| key | EN | ZH |
|---|---|---|
| d.title | Report count, last 28 days | 近28天报道数 |
| d.typical | Typical day: {m} reports (median of the 28 days before today) | 平日水平：{m} 篇（今天之前28天的中位数） |
| d.typical.thin | Typical day: not enough history yet ({d} of 20 days) | 平日水平：历史不足（已有 {d} 天，需 20 天） |
| d.week | Last 7 days: {n} reports | 近7天：{n} 篇报道 |
| d.day | Last 24h: {n} reports in {k} stories | 近24小时：{n} 篇报道，归为 {k} 个新闻事件 |
| d.basis | Placed by published time: {p} · by received time: {r} | 按发布时间计：{p} 篇 · 按接收时间计：{r} 篇 |
| d.sources | Sources counted: {list} | 计入来源：{list} |
| d.asof | Counted at {time} | 统计时间：{time} |
| d.rule | Busier means at least twice a typical day and at least 3 more reports. Quieter means half or less of a typical day of 2 or more. | 更密集：至少为平日的两倍，且多出至少 3 篇。更清淡：不超过平日的一半，且平日至少 2 篇。 |
| d.method | Withdrawn reports are left out. Each report counts once; the same news from two outlets is two reports and one story. 24h is a rolling window; the 28 days are UTC calendar days. | 已撤回的报道不计入。每篇报道只计一次；两家媒体报道同一消息，计为两篇报道、一个新闻事件。24小时为滚动窗口，28天按UTC自然日计。 |
| d.partial | The feed is catching up, so these counts may be low. No comparison is shown until it finishes. | 资讯流正在补齐，计数可能偏低；补齐前不显示比较。 |
| d.disclaimer | Counts describe coverage only. They do not indicate price direction. | 计数仅描述报道量，不代表价格方向。 |
| t.typical | typical | 平日 |
| t.today | 24h | 24小时 |
| t.norecord | no record | 无记录 |
| t.aria | Daily report counts for the 28 days before today, typical day {m}, last 24 hours {n} | 今天之前28天每日报道数，平日 {m} 篇，近24小时 {n} 篇 |

- {time} uses the formatter the rail already uses for row times. Wave B adds no second date format.
- {list} gives source display names in sources_counted order, comma-joined (ZH uses the 、 separator).

### 3.4 Row copy changes (existing rail rows)

- When item_count > 1 and source_count > 1, the existing reports button reads "{n} reports from {k} outlets" / "{n} 篇报道，来自 {k} 家媒体".
- When source_count is 1, it keeps the existing "{n} reports".
- The expanded source list gains a one-line note at the top: "Grouped because these reports describe the same event. Reports with different figures, periods or outcomes stay separate." / "这些报道描述同一事件，因此归为一组；数字、期间或结果不同的报道会分开列出。"
- The cluster v2 polarity sets (internally "bullish" and "bearish" rating-target classes, beats against misses, up against down moves) must never surface. The note names only figures, periods and outcomes.

### 3.5 Banned vocabulary (lex test, word-boundary match, every EN and ZH string above)

- EN: unusual, spike, alert, score, signal, validated, rank, ranking, confidence, sentiment, buy, sell, bullish, bearish, positive, negative, beat, miss, upgrade, downgrade, hot, momentum, impact.
- ZH: 异常, 激增, 飙升, 警报, 预警, 评分, 分数, 信号, 验证, 排名, 置信, 情绪, 买, 卖, 利好, 利空, 看涨, 看跌, 超预期, 不及预期, 热度, 影响.

## 4. Art direction: DARK TREATMENT and LIGHT TREATMENT

### 4.0 Theme adjudication (seat decision D-W1)

The terminal is dark-only. Evidence:
- app/settings.css:32: "Terminal is dark-only, so the macro html[data-theme=light] branch is not ported"
- app/globals.css:1283
- app/layout.tsx:54 sets data-theme="dark"
- lib/__tests__/tickerNewsRailMount.test.ts:47 pins that the source does not contain data-theme="light"

On the other side, the TP-0 art-direction law needs both treatments named and evidenced, and terminal/AGENTS.md:43 asks for light, dark and zh screenshots.

Recommended resolution:
- DARK ships live.
- LIGHT is fully specified below and delivered as a static specimen page, terminal docs/specimens/news-flow.html. The specimen shows both treatments side by side from the same markup and is rendered at the section 6 matrix sizes.
- No live light theme ships, and the negative test at tickerNewsRailMount.test.ts:47 stays green.

This keeps the light direction a real design, so a future terminal light theme ports it rather than inventing one, without breaking the pinned dark-only invariant. The alternative is for the seat to waive light for the terminal by ruling, citing settings.css:32. I do not recommend it, because under the law the packet is then PARTIAL.

### 4.1 DARK TREATMENT: command center (ships)

Mechanisms:
- Depth comes from a luminance step (--panel for the strip, --panel-2 for the details panel). There is no drop shadow.
- Exactly one restrained glow: the live dot halo.
- Separators are --line-2 rules.
- Numbers use --font-num tabular figures in --text; words use --text-2.
- No state color anywhere: busier, typical and quieter look identical except for the words.

Pinned markup (components/news/NewsFlowStrip.tsx). Builders implement this; they do not redesign it. The conditional children are written as ternaries here; the builder may use the usual JSX short-circuit form.

    <div className={styles.flow} data-flow-state={flow.state} data-comparison={flow.comparison ?? "none"}>
      <p className={styles.line}>
        <span className={styles.count}>{countText}</span>
        <span className={styles.sep} aria-hidden="true">·</span>
        <span className={styles.srOnly}>, </span>
        <span className={styles.compare}>{compareText}</span>
      </p>
      <button type="button" className={styles.more} aria-expanded={open}
              aria-controls={detailId} aria-label={copy.moreLabel} onClick={toggle}>?</button>
      {open ? (
        <section id={detailId} className={styles.detail} aria-labelledby={headingId}>
          <h3 id={headingId} className={styles.detailTitle}>{copy.detailTitle}</h3>
          <NewsFlowTally flow={flow} copy={copy} />
          <dl className={styles.facts}>
            typical, week, day, basis, sources, asof as dt/dd pairs
            (dd for numbers uses .num; dd for words uses .words)
          </dl>
          {flow.coverage === "partial" ? <p className={styles.partial}>{copy.partial}</p> : null}
          <p className={styles.rule}>{copy.rule}</p>
          <p className={styles.method}>{copy.method}</p>
          <p className={styles.disclaimer}>{copy.disclaimer}</p>
        </section>
      ) : null}
    </div>

- State unavailable renders only <p className={styles.unavailable}> with the unavailable sentence. It has no button and no tally.
- Escape inside the open details closes it and returns focus to the button. A pointerdown outside the strip closes it. Enter and Space open it, because it is a native button.
- No title attributes anywhere: CI law forbids translated text in title=.

Pinned CSS (components/news/NewsFlowStrip.module.css), dark tokens only:

    .flow{position:relative;display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;padding:6px 12px;border-bottom:1px solid var(--line-2);background:var(--panel);font:12px/16px var(--font-ui);color:var(--text-2)}
    .line{margin:0;flex:1 1 auto;min-width:0;display:flex;flex-wrap:wrap;gap:0 6px}
    .count{font-family:var(--font-num);font-variant-numeric:tabular-nums;color:var(--text)}
    .sep{color:var(--text-dim)}
    .srOnly{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
    .compare{color:var(--text-2)}
    .unavailable{margin:0;color:var(--muted)}
    .more{flex:0 0 auto;width:20px;height:20px;padding:0;border-radius:50%;border:1px solid var(--line-3);background:transparent;color:var(--text-2);font:600 11px/1 var(--font-ui);cursor:pointer}
    .more:hover{color:var(--text);border-color:var(--text-dim)}
    .more[aria-expanded=true]{color:var(--text);border-color:var(--text-2)}
    .more:focus-visible{outline:2px solid var(--brand-2);outline-offset:2px}
    .detail{position:absolute;top:calc(100% + 4px);right:8px;z-index:5;width:min(320px,calc(100% - 16px));padding:12px;border:1px solid var(--line-3);border-radius:6px;background:var(--panel-2);color:var(--text-2)}
    .detailTitle{margin:0 0 8px;font:600 12px/16px var(--font-ui);color:var(--text)}
    .facts{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0}
    .facts dt{color:var(--muted)}
    .facts dd{margin:0}
    .num{font-family:var(--font-num);font-variant-numeric:tabular-nums;color:var(--text)}
    .words{font-family:var(--font-ui);color:var(--text-2)}
    .partial{margin:6px 0 0;color:var(--text-2)}
    .rule,.method{margin:6px 0 0;font-size:11px;line-height:15px;color:var(--muted)}
    .disclaimer{margin:8px 0 0;padding-top:8px;border-top:1px solid var(--line-2);font-size:11px;line-height:15px;color:var(--text-2)}
    @media (max-width:860px){.flow{padding:6px 10px}.detail{position:static;flex-basis:100%;width:auto}}
    @media (prefers-reduced-motion:no-preference){.detail{animation:flowIn 120ms ease-out}}
    @keyframes flowIn{from{opacity:0;transform:translateY(-2px)}to{opacity:1;transform:none}}

Live dot fix (components/news/TickerNewsPanel.module.css .liveDot, plus the TickerNewsPanel.tsx markup):
- The dot uses var(--buy) today, and html[data-updown="east"] swaps that token to red (globals.css:124-132). A live indicator that turns red reads as an error.
- New rule: .liveDot{background:var(--brand-2);box-shadow:0 0 0 3px color-mix(in srgb,var(--brand-2) 18%,transparent)}. The precedent is globals.css:1569: status never uses --buy, --sell or --up, because they swap under east.
- New markup: <span className={styles.liveDot} role="img" aria-label={copy.live} />. It replaces the EN-only aria-label="live" on a role-less span (U5 GAP, TickerNewsPanel.tsx:160).

### 4.2 LIGHT TREATMENT: research workspace (specimen only, see 4.0)

Light keeps everything structural from dark: the markup, states, word budget, ordering, the outlined-today device and the zero versus no-record distinction. Only the material differs.

Surfaces:
- The canvas is #f3f5f8, a cool grey rather than cream.
- The strip surface is #ffffff with a 1px #e2e6ec bottom hairline. There is no luminance step.
- The details panel is #ffffff with a 1px #dde2e9 border and the shadow 0 8px 24px rgba(15,23,42,.10), 0 1px 2px rgba(15,23,42,.06). Shadow replaces the dark panel-2 step.

Text colors:

| Role | Color |
|---|---|
| Count | #161a22 |
| Words | #4a5361 |
| Muted | #6b7482 |
| Dim | #9aa2ae |

Marks and controls:
- The live dot is solid #2f5ce6 with NO halo. Glow is a dark-only mechanism.
- Tally bars are #5f6877 at full opacity. Dark lifts the bars by lightness; light darkens them for contrast on white.
- The median hairline is #9aa2ae, the today outline is #161a22, and gridlines are #edf0f4.
- The focus ring is #2f5ce6, 2px wide, offset 2px.

These mechanisms intentionally differ from dark:
- Depth: a luminance step in dark, a shadow in light.
- Live-dot glow: a halo in dark, none in light.
- Separators: a panel rule in dark, a hairline on white in light.
- Bar contrast runs in opposite directions.
- Gridline weight.

These must not differ: markup, copy, word budget, state set, ordering, and the absence of any direction color.

Contrast: every text pair is at least 4.5:1 in both treatments. B3 records the measured ratios for count, words and muted on their surfaces in the PR body.

### 4.3 Signature element: the wire tally (components/news/NewsFlowTally.tsx, details panel only)

The tally is the wire desk tally sheet, one mark per day of copy. It carries in pure geometry the one distinction the whole feature depends on: a rolling 24 hours is not a calendar day.

Chart law (terminal/AGENTS.md:31): the tally is built on components/charts/svgChart.ts.
- Width comes from useChartWidth(ref, 296). Height is MIN_CHART_H.spark (120).
- The y domain is padDomain(0, max(maxDaily, reports_24h, median)).
- niceTicks(lo, hi, 3) gives 2 to 3 faint gridlines in var(--line-2), labelled with fmtTick in 10px --font-num --text-dim.
- x labels use thinLabels over the day ticks with minGapPx 36, and show the day of month for the first, middle and last prior day.
- The viewBox is a 1:1 pixel box (viewBox 0 0 w h, matching width and height attributes). Never use preserveAspectRatio none.

MIN_CHART_H.spark = 120 is also why the tally is not in the glance strip: a 120px chart cannot sit in a one-line strip, and the doctrine puts technicals behind the details control anyway.

Marks:
- The 28 prior days get one bar each, oldest on the left, with 2px gaps. The fill is var(--text-2) at opacity .72.
- A zero-count day is a 2px baseline dot in var(--line-3), so zero reads as zero.
- Days before history began (index < 28 - history_days_observed) get no bar. They get a dotted baseline run instead (stroke var(--line-3), dasharray 1 3), with one t.norecord label under the run when it is at least 36px wide. Unrecorded is not zero.
- The median is a 1px hairline across the 28 bars in var(--text-dim), with a t.typical label at the right end in 10px var(--muted). It is absent in thin_history.
- Today comes after a 10px gap: one bar for the rolling last 24 hours, drawn OUTLINED (fill none, stroke var(--text), 1.25px) and labelled t.today below.
  - When reports_24h is 0, it is a 2px outlined stub.
  - When coverage is partial, the stroke uses dasharray 3 2, meaning incomplete, again without color.
- No color encodes busier or quieter.
- The svg has role img and aria-label t.aria, with the numbers filled in.

## 5. Degraded and empty states (complete list; every row is a test case in B3)

| case | trigger | strip | details | tally |
|---|---|---|---|---|
| ok busier, typical or quieter | state ok, coverage complete | count + comparison | full | full |
| ok, zero today | reports_24h 0, median < 2 | No reports in 24h · About a typical day | full | today = outlined 2px stub |
| ok, zero today, normally covered | reports_24h 0, median >= 2 | No reports in 24h · Quieter than a typical day | full | today = outlined stub |
| thin_history | fewer than 20 observed days | count · Too little history to compare | d.typical.thin shown; rule line still shown | observed-day bars, dotted no-record run, no median |
| partial | snapshot catching_up or degraded | count · Counts may be incomplete | d.partial note above the rule | today bar dashed |
| unavailable, calculation_failed | API caught an exception | Report counts unavailable right now (no button) | none | none |
| unavailable, malformed | terminal parser rejected flow | same as calculation_failed | none | none |
| unavailable, no_accessible_sources | empty rights | hidden; the panel restricted note speaks | none | none |
| flow null | old API, or cursor page | hidden | none | none |
| zero rows | snapshot rows empty | hidden; the panel empty state speaks | none | none |
| panel restricted or unavailable | existing panel states | hidden | none | none |
| symbol change in flight | new symbol, page one pending | hidden; never the previous symbol counts | none | none |

The strip never uses a shimmer or skeleton. It appears with page one or not at all.

## 6. Evidence matrix (G11)

### 6.1 Live cells (DARK, Playwright e2e/news-flow-responsive.spec.ts)

The fixture is seeded through route interception of /api/news/{symbol}. That route is the terminal proxy, so the fixture also exercises the parser.

| cell | theme | lang | viewport |
|---|---|---|---|
| D1 | dark | EN | 1440x900 |
| D2 | dark | ZH | 1440x900 |
| D3 | dark | EN | 820x1180 |
| D4 | dark | ZH | 820x1180 |
| D5 | dark | EN | 390x844 |
| D6 | dark | ZH | 390x844 |
| E1 | dark, html data-updown="east" | EN | 1440x900 |

States captured per cell: busier, typical, quieter, thin_history, partial, unavailable, and details open (busier fixture). That is 7 states across 6 cells, 42 crops, plus E1 (strip and live dot).

The PR body carries at least two things per language:
- the details-open crop for every cell
- one strip-state contact sheet

Assertions per cell:
- no horizontal scroll (document scrollWidth <= clientWidth)
- in EN, the strip stays on one line at 1440 and 820, and takes at most two lines at 390
- the details panel stays fully inside the viewport
- the focus ring is visible on the details button after Tab
- the live dot computed background equals the --brand-2 value in every cell, including E1

### 6.2 Light cells (SPECIMEN)

- L1 to L6 cover the same theme-language-viewport grid, rendered from docs/specimens/news-flow.html with the light material (a Playwright screenshot of the static file).
- The PR body labels them SPECIMEN. They are never presented as live evidence.
- Negative proof: lib/__tests__/tickerNewsRailMount.test.ts:47 stays green, meaning no live light theme shipped.

### 6.3 Review rule

A cell passes only when a reviewer judges it as a design. The criteria are:
- hierarchy
- material
- semantic neutrality: no direction color, and the words carry the comparison
- responsive composition
- EN and ZH parity

Rendering without error is necessary and never sufficient. The review route for B3 is an Opus reviewer (MODE: READ_ONLY) given the crops.

## 7. Build lanes, owned files, named tests

Order:
- B1, B3 and B4 start together once #8902, #8897 and #8905 are merged.
- B2 starts from fresh main after B1 merges. Stacking B2 on an unmerged B1 under squash merges is not worth the risk.
- B3 merges independently because of G4.

Lane rules:
- One owner per file. Lanes never edit .github; each lane names the CI job its new tests belong to, and the seat wires them. The existing macro job for this area is ticker-news-qbus.
- Each commission copies section 0 inline, together with the lane owned files and tests below.
- Each lane returns a DRAFT PR with its exact full head.

### B1: engine flow (macro)

Owned files:
- engine/qbus_news_velocity.py
- engine/qbus_news_store.py: the new read method news_flow; and, only if the 1.5 parity check fails, the snapshot read SQL for source_count and item_count. Never def commit.
- tests/test_qbus_news_velocity.py
- tests/test_qbus_news_flow_store.py (new)

Work:
- Required keyword allowed_sources, and status = active (1.5).
- stories_24h and basis_counts_24h.
- compare_to_typical(r24, median, sufficient, coverage) implementing flow_compare.v1.
- Rename the EN label unit from stories to reports. It is kept for engine consumers; ZH already says 篇报道 or will after the rename.
- Assert that daily_counts_28d runs oldest first.
- Record the window boundaries.
- Measure p95 (2.1).

Named tests:
- test_flow_counts_only_allowed_sources
- test_flow_counts_only_active_status
- test_flow_empty_allowed_sources_counts_zero
- test_allowed_sources_is_required_keyword
- test_stories_24h_counts_distinct_clusters
- test_unclustered_report_is_its_own_story
- test_basis_counts_24h_windowed
- test_compare_to_typical_bands, a table of (r24, median) to comparison:

| r24 | median | expected |
|---|---|---|
| 0 | 0 | typical |
| 2 | 0 | typical |
| 3 | 0 | busier |
| 2 | 1 | typical |
| 5 | 3 | typical |
| 6 | 3 | busier |
| 1 | 2 | quieter |
| 0 | 2 | quieter |
| 2 | 3 | typical |
| 1 | 3 | quieter |
| 0 | 1.5 | typical |

  Also: partial gives None, and insufficient history gives insufficient_history.
- test_window_boundaries_closed_both_ends
- test_daily_counts_oldest_first
- test_label_unit_is_reports_en_zh
- test_banned_words_en_zh (extends the existing BANNED_WORDS test with the 3.5 lists)
- test_news_flow_runs_on_query_only_connection (a write attempt raises)
- test_snapshot_source_count_respects_rights (a pin, whether or not a fix was needed)

Evidence in the PR body:
- the diff of engine/qbus_news_store.py showing no hunk inside def commit (G2)
- the existing commit tests unchanged and passing
- red-before-fix for the rights test on the #8902 engine

### B2: API flow key (macro)

Owned files:
- app/ticker_news.py
- tests/test_ticker_news_flow_api.py (new)

Work: build the flow key per section 1 and degrade per 2.1. Do not serve the engine label.

Named tests:
- test_first_page_carries_flow
- test_cursor_page_omits_flow
- test_changes_story_and_sse_never_carry_flow
- test_flow_failure_degrades_rows_still_200
- test_flow_parse_instant_garbage_degrades (the U2 GAP, carried)
- test_flow_no_accessible_sources
- test_flow_partial_when_catching_up_or_degraded
- test_flow_provenance_complete_when_ok
- test_flow_has_no_engine_label_and_no_banned_words
- test_no_multi_security_or_sorted_flow_route
- test_flow_counts_match_visible_rows_under_rights (end to end, with a restricted source seeded)
- test_old_terminal_parser_shape_unaffected (G4, API side): the rows payload is byte-identical with and without flow

### B3: terminal strip (terminal repo, new branch from fresh master)

Owned files:
- lib/newsTypes.ts
- lib/newsValidation.ts (parseTickerNewsFlow)
- lib/newsContract.ts (carries flow)
- lib/newsFlowLex.ts (new; all section 3 copy)
- components/news/NewsFlowStrip.tsx and NewsFlowStrip.module.css (new; pinned in 4.1)
- components/news/NewsFlowTally.tsx (new; 4.3)
- components/news/TickerNewsPanel.tsx: mount the strip, live-dot markup, reports-from-outlets copy, grouping note, and the U5 a11y gaps below
- components/news/TickerNewsPanel.module.css (.liveDot)
- docs/specimens/news-flow.html (new; both treatments)
- the tests below
- e2e/news-flow-responsive.spec.ts (new)

U5 a11y gaps folded in. They are in the same file, which keeps one owner:
- TickerNewsPanel.tsx:201: the CJK title= in ZH. Remove the title attribute and give the reason as visible text or through aria-describedby.
- :160: the live aria-label is EN-only. Use role img with a localized label (4.1).
- :218: aria-label sits on a generic div. Give it role group with the label, or drop the label.
- Duplicate "Mark reviewed" accessible names. Include the headline in each accessible name: EN "Mark reviewed: {title}"; ZH uses the existing mark-reviewed copy followed by the title.
- Flip the it.fails case in lib/__tests__/tickerNewsA11y.test.tsx to a passing it.

Named tests (vitest via npm run test, plus npm run test:e2e:responsive):
- lib/__tests__/newsFlowContract.test.ts:
  - parses ok, thin_history and unavailable; a missing key gives null
  - malformed variants give unavailable/malformed and never throw: stories > reports, 27 daily entries, a negative count, an unknown state, a wrong schema string, reports_24h > reports_7d
  - rows still parse when flow is malformed
- lib/__tests__/tickerNewsProxy.test.ts (extended): flow survives proxy re-serialization; an absent flow stays absent
- lib/__tests__/newsFlowLex.test.ts:
  - every state is at most 9 EN words and at most 20 ZH characters at n = 9999
  - no 3.5 banned term appears in any string
  - every key has both EN and ZH
- lib/__tests__/newsFlowStrip.test.tsx:
  - renders each section 5 row
  - the strip is hidden for null flow, restricted, zero rows and symbol change
  - details opens on click, Enter and Space; Escape closes it and focus returns to the button
  - no title attributes
  - the tally aria-label carries the numbers
- lib/__tests__/newsFlowTokens.test.ts: NewsFlowStrip.module.css and the .liveDot rule contain none of --up, --down, --buy, --sell or --signal
- lib/__tests__/tickerNewsRailMount.test.ts:47 stays green, so no live light theme ships
- e2e/news-flow-responsive.spec.ts: the whole 6.1 matrix, plus specimen captures for 6.2

### B4: carried candidates (two small PRs)

B4-macro owned files:
- engine/leadership_receipt.py
- tests/test_leadership_receipt_edge_matrix.py: flip the two strict xfails that #8967 pinned into ordinary passing tests

B4-macro work:
- :43 _parse_date returns None for a datetime OBJECT. Accept it so that _parse_date(dt) == _parse_date(dt.isoformat()) for aware and naive datetimes alike. The str path stays the reference behavior.
  - Test test_datetime_object_as_of_parses.
  - Python datetime is a subclass of date, so check the isinstance order explicitly.
- :150 a future-dated theme_state as_of currently reads fresh. When ts_as_of > ti_as_of by at least one calendar day, status becomes "invalid".
  - I map it to the existing "invalid" status rather than adding a new "future" status. A "future" status would widen the terminal union at lib/companyThemeExposure.ts:42-43, which the terminal parses strictly, and buys no visible difference: both mean "do not trust this date".
  - Tests test_future_dated_theme_state_is_invalid and test_same_day_theme_state_is_fresh.
- :539 breadth has no _zh string. Add one. Test test_breadth_has_zh.
- :208-209 hardcode "5 days". Derive the text from _THEME_STATE_MAX_AGE_DAYS. Test test_stale_copy_follows_max_age_constant.
- The two U4 GAPs above are fixed in the same file, which keeps one owner.

B4-terminal owned files:
- components/fin/CompanyThemeContextCard.tsx
- its existing test file. If none exists, lib/__tests__/companyThemeContextCard.test.tsx (new).

B4-terminal work:
- :205 not_found currently returns null, which hides the card. Render a compact empty state that reuses the existing shell:

      <section className="ci-theme-card ci-theme-empty">
        <span className="ci-theme-kicker">{pick(zh, "CURRENT THEME CONTEXT", "当前主题背景")}</span>
        <p>{pick(zh, "No theme context for this company yet. It appears here once the company is mapped to a tracked theme.", "该公司暂无主题背景；纳入跟踪主题后会显示在这里。")}</p>
      </section>

  - There is no retry button, because the state is not retryable.
  - There is no role status, because an empty state is not a live update.
  - The .ci-theme-empty modifier goes in the stylesheet that already owns .ci-theme-card. It is a single compact line in --muted with no new token.
- Tests:
  - not_found renders the empty state in EN and ZH
  - status invalid, as produced by a future-dated as_of, renders the existing invalid treatment, and the union is unchanged

B4-terminal does not depend on B4-macro, because the invalid status already exists.

## 8. Carried candidates index (traceability)

| # | origin | item | lands in |
|---|---|---|---|
| 1 | seat / U4 | engine/leadership_receipt.py:150: a future as_of reads fresh | B4-macro, mapped to invalid |
| 2 | seat / U4 | engine/leadership_receipt.py:43: a datetime object is not parsed | B4-macro |
| 3 | seat / E | CompanyThemeContextCard.tsx:205: not_found hides the card | B4-terminal |
| 4 | seat / E | lib/companyThemeExposure.ts:42-43: the union has no "future" status | resolved by mapping #1 to invalid; union unchanged; pinned by a B4-terminal test |
| 5 | U2 J3 | _parse_instant raises ValueError on garbage | B2 degrade test |
| 6 | U2 J3 | basis_counts is unwindowed | B1 basis_counts_24h |
| 7 | U2 J3 | cross-source items are counted per item | units law G7 |
| 8 | U6 review of #8902 | _STORY_SQL has no rights filter | B1, G1 |
| 9 | U5 GAPs | TickerNewsPanel.tsx :160, :201, :218, duplicate names | B3 |
| 10 | U4 GAPs | leadership_receipt.py :539 (no _zh), :208-209 (hardcoded 5 days) | B4-macro |
| 11 | U6 | the live dot uses --buy, which flips red under east | B3, G10 |
| 12 | U1 GAP | news_changes is never pruned | NOT Wave B. Flow reads news_items, news_states and news_cluster_members, never news_changes, so it adds no cost there. Retention is a separate ops decision; recorded only. |

## 9. Seat decisions needed (consequential; not mine to take)

- D-W1 Theme: light delivered as a specimen only (recommended, 4.0), or a waiver by ruling.
- D-W2 Comparison thresholds for flow_compare.v1: busier at 2x and +3; quieter at half or less, with a typical day of at least 2.
  - These are display rules only.
  - The seat may change the numbers before B1 starts. A change after ship bumps the rule id.
- D-W3 Flow on SSE is excluded by design (1.1). If live ticking is wanted, it is a product-law question first, not a build change.

## 10. Known limits (stated, not hidden)

- Clusters built before v2 cannot be told apart at read time. CLUSTER_POLICY_VERSION is a module constant, not a stored column (#8905 diff), so provenance reports the constant. A stored column is out of Wave B scope.
- A rolling 24 hours compared with a calendar-day median is an approximation. The details panel says so.
- Daily buckets are UTC days. A US-hours security has its US evening split across two UTC days. Provenance states this, and Wave B does not localize it.
- The 28-day median is per security and per rights set. Two viewers with different rights can see different counts for the same security. This is correct by G1, and it is why no flow number may be cached across users.
