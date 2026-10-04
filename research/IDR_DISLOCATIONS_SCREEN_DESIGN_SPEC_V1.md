# Dislocations screen — design spec V1 (Terminal `/dislocations`)

Program: Intraday Dislocation + Reclaim (receiver assignment mastermind-terminal#784). Parent spec:
`research/INTRADAY_DISLOCATION_TERMINAL_PRODUCT_SPEC_V1.md` §4.2. Design pinned in the seat's main
loop under `docs/DESIGN_DOCTRINE.md` + the frontend-design skill + Terminal `AGENTS.md`; an external
build lane implements this file verbatim and may not choose palette, type, layout, or copy. Route
contract it consumes: `GET /api/v1/dislocations?view=my|market` (Terminal PR #795, `lib/dislocations/types.ts`).

## §0 Acceptance gates (not done unless)

1. Fresh incognito happy path with zero manual workarounds: signed-in user opens `/dislocations` from
   the top nav, sees the three groups populated from the fixture, toggles My watchlist ↔ Market,
   opens a row's details, follows the chart link, and lands on `/terminal?symbol=<sym>`.
2. Every degraded state in §6 renders its pinned copy and NEVER looks healthy: a stale `ok_empty`
   is a warning, not an empty list; `source_unavailable` says nothing here is live.
3. No glance-tier string contains a state enum, a detector id, a study name, a raw slug, or an
   untranslated statistic. Technicals live only inside the row's details disclosure.
4. Evidence matrix in the PR body: dark × EN/ZH × desktop 1440 / tablet 820 / mobile 390 crops at
   `docs/pr-crops/dislocations/<project>-<scenario>[-zh].png` (scenarios §8). The Terminal is
   dark-only (`<html data-theme="dark">`, no light palette) — recorded as a deviation from the macro
   two-art-direction law, not an omission; a light treatment is out of scope until the Terminal
   grows a light theme.
5. Unit tests (§9) green under `npx vitest run`; the one Playwright spec green on all three projects.
6. Nav, title map and LEX entries wired (§3); `/dislocations` is reachable from the shell without a
   typed URL.

## §1 Thesis and signature

Subject: a trader's dark command center reading today's intraday washouts on delayed 5-minute bars.
The page's single job: *which names washed out, is the turn holding, and how old is what I am
looking at.* Everything the screen says about time is the honest part of the product, so the
signature element is the **knowable-at clock**: each row leads with the ET time its current state
became knowable (bar close plus feed lag), set as the largest numeral on the row, with a live
"n min ago" age beneath it that re-ticks every 30 s. The clock, not the symbol, is what the eye
lands on. One header badge says the feed is delayed; the rows never pretend otherwise.

Everything else is quiet: hairlines, one 2 px semantic rule on the row's left edge, plain-word
stances, no sparkline, no score, no colour on numbers. Nothing here claims edge.

## §2 Information architecture

Three groups in this order, each an `<ol>` under an eyebrow heading with a count:

| Order | Group | Owner states | Why first/last |
|---|---|---|---|
| 1 | Confirmed · 已确认 | CANDIDATE | the only rows that answer "look now" |
| 2 | Forming · 形成中 | PROBING, ARMED, TURNING | watch, don't chase |
| 3 | Ended · 已结束 | INVALIDATED, EXPIRED, RESOLVED | kept for the record |

Rows inside a group are ordered by `knowable_at` descending (newest knowable first). A group with
zero rows renders its heading with "0" and one muted line (§6 copy); groups are never hidden, so the
page shape is stable across refreshes.

## §3 Shell wiring (Terminal repo, `terminal/`)

- `components/AppNav.tsx` `TOP`: insert `{ k: "dislocations", label: "Dislocations", href: "/dislocations" }`
  immediately after the `discover` entry.
- `lib/i18n.tsx` LEX: `dislocations: ["Dislocations", "错位"]`, `pageDislocations: ["Dislocations", "日内错位"]`.
- `components/chrome/AppShell.tsx` `TITLE_MAP`: `["/dislocations", "pageDislocations", "Dislocations"]`.
- `app/(shell)/dislocations/page.tsx`: server component, byte-pattern of `app/(shell)/portfolio/page.tsx`
  — `createClient().auth.getUser()`; the `TERMINAL_E2E_FIXTURE === "1"` branch renders the mount
  without a user; otherwise no user → `<SignupGate surface="dislocations" />`, user → `<DislocationsViewMount />`.
- `components/mounts/DislocationsViewMount.tsx`: same dynamic-import mount pattern as the portfolio
  mount (skeleton = `RouteSkeleton`).
- `components/dislocations/DislocationsView.tsx` + `DislocationsView.module.css`: the screen.
- `lib/dislocations/source.ts` `displayFor`: five-way plain-word stances + watching line (§5).

## §4 Markup (exact; class names are the CSS module's)

```tsx
<section className={s.wrap} aria-labelledby="dislo-title">
  <header className={s.head}>
    <div>
      <h1 id="dislo-title" className={s.title}>{t("pageDislocations", "Dislocations")}</h1>
      <p className={s.sub}>{SUB[lang]}</p>
    </div>
    <div className={s.status} role="status" data-testid="dislo-status">
      <span className={s.badge}>{display.delay_badge}</span>
      <span className={s.dot} aria-hidden="true">·</span>
      <span className={s.asof}>{UPDATED[lang]} {fmtClock(source.asof)}</span>
      {source.pack_fresh === false && <span className={`${s.chip} ${s.chipWarn}`}>{PACK_STALE[lang](source.pack_as_of)}</span>}
    </div>
  </header>

  <WorkspaceTabs ... items={[{k:"my", label: VIEW_MY[lang]}, {k:"market", label: VIEW_MARKET[lang]}]} />

  {/* degraded states (§6) render here INSTEAD of the groups, except `stale`, which renders a warn
      line here AND the groups beneath it */}

  {GROUPS.map(g => (
    <section key={g.key} className={s.group} aria-labelledby={`dislo-${g.key}`}>
      <h2 id={`dislo-${g.key}`} className={s.eyebrow}>
        <span>{g.label[lang]}</span><span className={s.count}>{rows(g).length}</span>
      </h2>
      {rows(g).length === 0
        ? <p className={s.voidLine}>{g.empty[lang]}</p>
        : <ol className={s.list}>
            {rows(g).map(ep => (
              <li key={ep.episode_id} className={s.row} data-ticker={ep.ticker}
                  data-stance={ep.display.stance} data-state={ep.state}>
                <div className={s.rail}>
                  <time className={s.when} dateTime={ep.display.knowable_at}>{fmtClock(ep.display.knowable_at)}</time>
                  <span className={s.age} data-testid="dislo-age">{fmtAge(ep.display.knowable_at, now, lang)}</span>
                </div>
                <a className={s.sym} href={navHref(ep.ticker)}>{ep.ticker}</a>
                <div className={s.body}>
                  <p className={s.sentence}>{lang === "zh" ? ep.display.stance_zh : ep.display.stance_en}</p>
                  {watching(ep) && <p className={s.watching}>{watching(ep)}</p>}
                </div>
                <div className={s.chips}>
                  {catalystChip(ep)}
                  {ep.freshness?.quote_age_s > 1200 && <span className={`${s.chip} ${s.chipWarn}`}>{QUOTE_OLD[lang]}</span>}
                  <details className={s.more}>
                    <summary>{DETAILS[lang]}</summary>
                    <dl className={s.tech}>
                      <dt>state</dt><dd>{ep.state}</dd>
                      <dt>detector</dt><dd>{ep.detector_id}</dd>
                      <dt>price at signal</dt><dd>{fmtPx(ep.price_at_signal)}</dd>
                      <dt>bars</dt><dd>{ep.bar_availability?.grain ?? "—"}</dd>
                      <dt>data quality</dt><dd>{ep.data_quality ?? "—"}</dd>
                      <dt>pack as of</dt><dd>{ep.freshness?.pack_as_of ?? "—"}</dd>
                      <dt>catalyst</dt><dd>{ep.catalyst ? `${ep.catalyst.coverage} · until ${ep.catalyst.relevant_until}` : COVERAGE_UNKNOWN[lang]}</dd>
                      <dt>episode</dt><dd>{ep.episode_id}</dd>
                    </dl>
                  </details>
                </div>
              </li>
            ))}
          </ol>}
    </section>
  ))}

  <p className={s.disclosure}>{FOOT[lang]}</p>
</section>
```

Rules: the chart link is `navHref(ep.ticker)` from `lib/navSymbol.ts` (emits `/terminal?symbol=`);
no `episode` parameter until the T-CHART deep link lands (§4.3 of the parent spec) — a dead
parameter never ships. `fmtClock` = `Intl.DateTimeFormat("en-US", {hour:"2-digit", minute:"2-digit",
hour12:false, timeZone:"America/New_York"})` + " ET" (ZH: " 美东"). `fmtAge` = whole minutes under
60, then `h` + `min`; ZH "{n} 分钟前" / "{h} 小时 {m} 分钟前". `now` is component state advanced
by a 30 s interval while `document.visibilityState === "visible"`. `fmtPx` = `toFixed(2)`.

## §5 Server-built plain words (`lib/dislocations/source.ts`)

`displayFor` keeps `stance`, `knowable_at`, `delay_badge_*`, and replaces the three coarse strings
with a five-way mapping keyed on `state` (ZH parity is a server contract, never a client table):

| state | stance | `stance_en` | `stance_zh` |
|---|---|---|---|
| PROBING, ARMED | forming | `Washout, no turn yet` | `洗盘中，尚未转向` |
| TURNING | forming | `Turn forming, not held` | `转向形成，未站稳` |
| CANDIDATE | confirmed | `Reclaim held` | `收复已站稳` |
| INVALIDATED | ended | `Turn failed` | `转向失败` |
| EXPIRED | ended | `Ran out of session` | `本节已到时` |
| RESOLVED | ended | `Window closed` | `观察期结束` |
| anything else | ended | `Status unavailable` | `状态不可用` |

Add two nullable fields to `EpisodeDisplay`: `watching_en`, `watching_zh`. They are built ONLY when
`risk_geometry` carries BOTH `invalidation_level` (finite number) and `time_budget_until` (ISO
string) — the contract keys the `tactical_dislocation` producer must write (parent spec §3.2;
today's producers write neither, so today the line is absent, never fabricated):

- EN: `Turn fails below {invalidation_level.toFixed(2)} · budget to {HH:MM} ET`
- ZH: `跌破 {level} 即失效 · 预算至 {HH:MM} 美东`

`watching(ep)` on the client is just the language pick. Existing route tests that pin the old
strings are updated to the table above; the `fresh.json` fixture gains one CANDIDATE row carrying
`risk_geometry: {invalidation_level: 182.4, time_budget_until: "<same-day 14:45 ET ISO>"}` so the
line is exercised end to end.

Catalyst chip (`catalystChip`): absent `catalyst` → no chip at glance (details say
`COVERAGE_UNKNOWN`); present and `relevant_until >= knowable_at` → `Catalyst on file` /
`有催化剂记录`; present and older → `Catalyst aged out` / `催化剂已过期`. Never "no catalyst" — absence
is coverage unknown (parent spec §3, catalyst owner).

## §6 States and copy (EN / ZH; ≤ 14 words per line)

| state | where | copy |
|---|---|---|
| header subtitle `SUB` | always | `Intraday washouts and whether the turn is holding, on delayed bars.` / `日内洗盘与转向是否站稳，基于延迟行情。` |
| `UPDATED` | header | `updated` / `更新于` |
| `PACK_STALE(d)` | header chip (warn) | `Nightly pack stale (as of {d})` / `夜间数据包过期（截至 {d}）` |
| `QUOTE_OLD` | row chip (warn), quote age > 20 min | `Quote older than 20 min` / `报价超过 20 分钟` |
| group empty · Confirmed | `voidLine` | `No reclaim has held yet this session.` / `本节尚无站稳的收复。` |
| group empty · Forming | `voidLine` | `No washout under watch right now.` / `当前没有观察中的洗盘。` |
| group empty · Ended | `voidLine` | `Nothing has ended this session.` / `本节尚无已结束的事件。` |
| `ok_empty` (fresh) | in place of groups, `role="status"` | `No dislocations yet this session. The list fills as 5-minute bars close.` / `本节尚无错位。5 分钟 K 线收盘后列表会填充。` |
| `stale` (any count) | warn line above groups + groups render | `Showing the last good read from {asof}. The feed is behind.` / `显示 {asof} 的最后一次有效读取。行情源滞后。` |
| `ok_empty` + `source.delayed && !pack_fresh`, or `stale` with zero rows | in place of groups (warn) | `The feed is behind and nothing is on file. Not a quiet session, an unknown one.` / `行情源滞后且无记录。这不是平静，而是未知。` |
| `source_unavailable` | in place of groups | `The dislocation feed isn't publishing yet. Nothing here is live.` / `错位数据源尚未发布。此处没有实时内容。` |
| `handler_error` / non-JSON | in place of groups | `We couldn't read the feed. Try again in a minute.` / `无法读取数据源。请一分钟后重试。` |
| 429 | in place of groups | `Too many refreshes. Back in {n}s.` / `刷新过于频繁。{n} 秒后恢复。` (n from `Retry-After`, default 30; auto-retry once at n) |
| 403 `paid_tier_required` (Market tab) | in place of groups | paywall card mirroring `components/OptionsPaywall.tsx` structure/CTA; title `Market-wide dislocations are a paid feature.` / `全市场错位为付费功能。`, body `Your watchlist view stays free.` / `自选股视图保持免费。` |
| 401 | never reached (shell gate) | — |
| `DETAILS` | row summary | `details` / `详情` |
| `COVERAGE_UNKNOWN` | details | `coverage unknown — not the same as no catalyst` / `覆盖未知——不等于没有催化剂` |
| `FOOT` | page foot | `Windows, not certainties. Re-read every 5 minutes on delayed bars.` / `是窗口，不是确定性。基于延迟行情每 5 分钟重读。` |
| `VIEW_MY` / `VIEW_MARKET` | tabs | `My watchlist` / `我的自选` · `Market` / `全市场` |

`fetch("/api/v1/dislocations?view=" + view, { cache: "no-store" })`, re-fetched every 60 s while
visible, aborted on unmount; the body's `state` drives the table above; `source.join_degraded`
adds a muted line under the header: `Some watchlist names could not be joined.` / `部分自选股无法关联。`

## §7 CSS (module; tokens only; copy `.title`/`.sub`/`.disclosure` declarations from `EventImpactPanel.module.css`)

```css
.wrap { max-width: 1120px; margin: 0 auto; padding: var(--sp-5) var(--sp-4) var(--sp-8); }
.head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--sp-4); flex-wrap: wrap; }
.status { display: inline-flex; align-items: center; gap: var(--sp-2); color: var(--text-2); font-size: var(--fs-micro); }
.badge { border: 1px solid var(--hairline-strong); border-radius: 999px; padding: 1px var(--sp-2); color: var(--text-2); }
.chip { border-radius: 999px; padding: 1px var(--sp-2); font-size: var(--fs-micro); border: 1px solid var(--hairline); color: var(--text-2); white-space: nowrap; }
.chipWarn { border-color: var(--warn); color: var(--warn); }
.group { margin-top: var(--sp-6); }
.eyebrow { display: flex; align-items: baseline; gap: var(--sp-2); margin: 0 0 var(--sp-2); font-size: var(--fs-micro); letter-spacing: .08em; text-transform: uppercase; color: var(--text-3); border-bottom: 1px solid var(--hairline); padding-bottom: var(--sp-1); }
.count { font-variant-numeric: tabular-nums; color: var(--text-2); }
.list { list-style: none; margin: 0; padding: 0; }
.row { display: grid; grid-template-columns: 4.25rem 5.5rem minmax(0, 1fr) auto; column-gap: var(--sp-3); align-items: start;
       padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-2); border-left: 2px solid var(--hairline-strong); border-bottom: 1px solid var(--hairline); }
.row[data-stance="confirmed"] { border-left-color: var(--up); }
.row[data-stance="forming"]   { border-left-color: var(--brand-2); }
.row[data-state="INVALIDATED"] { border-left-color: var(--down); }
.rail { display: flex; flex-direction: column; }
.when { font-size: var(--fs-num-lg); font-variant-numeric: tabular-nums; line-height: 1; color: var(--text); }
.age  { margin-top: 2px; font-size: var(--fs-micro); color: var(--text-3); font-variant-numeric: tabular-nums; }
.sym  { font-weight: 600; color: var(--text); text-decoration: none; align-self: baseline; }
.sym:focus-visible { outline: 2px solid var(--brand-2); outline-offset: 2px; }
.body { min-width: 0; }
.sentence { margin: 0; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.watching { margin: 2px 0 0; font-size: var(--fs-micro); color: var(--text-3); font-variant-numeric: tabular-nums; }
.chips { display: flex; align-items: center; gap: var(--sp-2); justify-self: end; }
.more summary { cursor: pointer; font-size: var(--fs-micro); color: var(--link); list-style: none; }
.more summary:focus-visible { outline: 2px solid var(--brand-2); outline-offset: 2px; }
.tech { grid-column: 1 / -1; margin: var(--sp-2) 0 0; display: grid; grid-template-columns: max-content 1fr; gap: 2px var(--sp-3); font-size: var(--fs-micro); color: var(--text-3); }
.tech dd { margin: 0; color: var(--text-2); font-variant-numeric: tabular-nums; word-break: break-all; }
.voidLine { margin: 0; padding: var(--sp-3) var(--sp-2); color: var(--text-3); font-size: var(--fs-micro); }
.warnLine { margin: var(--sp-3) 0 0; color: var(--warn); font-size: var(--fs-micro); }
@media (max-width: 820px) {
  .row { grid-template-columns: 3.75rem 4.5rem minmax(0, 1fr); }
  .chips { grid-column: 2 / -1; justify-self: start; margin-top: var(--sp-1); flex-wrap: wrap; }
}
@media (max-width: 480px) {
  .row { grid-template-columns: 3.5rem minmax(0, 1fr); row-gap: 2px; }
  .sym  { grid-column: 2; }
  .body, .chips { grid-column: 2; }
  .sentence { white-space: normal; }
  .when { font-size: var(--fs-num); }
}
@media (prefers-reduced-motion: reduce) { .row, .chip { transition: none; } }
```

The row's `<details>` opens in place; its `.tech` grid spans the row (place the `<details>` so the
`dl` lands in a new grid row: wrap `.chips` + `.more` in the same cell and let `.tech` be
`position: static` — the lane may restructure into `grid-row` spans as long as the visible result
matches the crops' intent: technicals below the row, never beside it).

## §8 Fixtures and e2e

- Route fixtures already exist (`fixtures/dislocations/{fresh,empty,stale_pack,malformed,...}.json`,
  selected by the `mm_e2e_dislo` cookie — the recorded deviation from the parent spec's fixture
  mechanism). `fresh.json` is extended per §5 to cover all seven states at least once (two PROBING
  rows, one TURNING, two CANDIDATE — one with `risk_geometry` keys — one INVALIDATED, one EXPIRED,
  one RESOLVED, one row with `catalyst`, one with `freshness.quote_age_s = 1500`).
- One Playwright spec `e2e/dislocations.spec.ts`, projects desktop 1440×900 / tablet 820×1180 /
  mobile 390×844, scenarios: `populated` (fresh, EN), `populated-zh` (fresh, lang cookie zh),
  `empty` (empty.json), `stale` (stale_pack.json), `unavailable` (no fixture file → route reports
  `source_unavailable`). Crops to `docs/pr-crops/dislocations/<project>-<scenario>.png`. Assertions:
  group order Confirmed → Forming → Ended; first Confirmed row's `.when` reads a HH:MM ET; the
  watching line appears exactly once; the stale scenario shows the warn line; the unavailable
  scenario shows no `<ol>`.

## §9 Unit tests (vitest + jsdom, `components/dislocations/__tests__/DislocationsView.test.tsx`)

1. renders three groups in order with counts from the fixture body; 2. five stances render the §5
strings (EN and ZH via the lang provider); 3. watching line only when both keys present;
4. `ok_empty` with `pack_fresh:false` renders the warn copy, not the quiet copy; 5. `stale` renders
the warn line AND rows; 6. `source_unavailable` / `handler_error` / 429 copy; 7. 403 renders the
paywall card; 8. age text advances under fake timers; 9. chart link href equals `navHref(ticker)`.
`lib/__tests__` for `displayFor`: the seven-row table + the unknown-state fallback + watching
formatting (`182.4 → 182.40`, ET clock).

## §10 Out of scope (later waves)

Alerts on CANDIDATE; the chart deep link with levels (T-CHART, parent §4.3); `view=market`
ranking or filters; any score, rank, or size; a light theme.
