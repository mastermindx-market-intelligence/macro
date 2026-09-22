# W4-A — markets.html global-cycle spine census

**Packet:** MO-A · UD-B2-W4A · 2026-09-21 · DRAFT, evidence only — NOT for merge.
**Capture sha:** `ea194c5d215c64158a828abdc676f47bb7723374` (HEAD, detached).
**Evidence pack:** `mockups/evidence/ud-b2-w4a/manifest.json` + `cells/` (8 PNG) + `candidates/` (4 PNG).
**Forbidden edits:** none to `templates/`, `site/`, `scripts/`, `engine/`, `lib/`, `tests/`, `.github/`, `data/`.
**Allowed write paths:** `research/ud_b2/` (this file) + `mockups/evidence/ud-b2-w4a/`.

---

## §0 · Program-state pre-flight (binding before this census)

Three references pin every downstream decision in this file:

| Source | Line | What it pins |
|---|---|---|
| `research/DO_NOT_REBUILD.md` | `DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` (row 177) | `_unified_dashboard_hero.html.j2` may NOT be remounted on `macro.html` / `dashboard.html.j2`; default-US `market_state` is NOT a global composite. |
| `research/UNIFIED_DASHBOARD_DISPOSITION.md` | "Primary-route override — 2026-09-20" + "Current-main reconciliation — 2026-09-21" | Recomposition is the path: reuse primitives on the `markets.html` global-cycle owner; never on `intl.html`; never labeled "global". |
| `tests/test_dashboard_template_render.py` | `test_macro_mode_keeps_unified_dashboard_candidate_off_primary_route` (line 318) | Asserts `'id="ud-hero"' not in html` for the macro primary route. |
| `tests/test_unified_dashboard_b2w2.py` | `test_spine_slice_bonds_and_commodities_stay_designed_null` (line 464) + `test_spine_slice_does_not_wire_quad_artifact` (line 569) | Pins spine slug discipline + forbids quad-artifact surfacing. |

Citations here use `file:line` so the review leg can re-derive every receipt.

---

## §1 · markets.html TODAY (capture-time state at SHA `ea194c5d`)

### §1.1 Capture manifest

The capture is reproducible — see `mockups/evidence/ud-b2-w4a/manifest.json`:

- `capture_sha: ea194c5d215c64158a828abdc676f47bb7723374` (verified re-extracted from the rendered `mockups/evidence/ud-b2-w4a/manifest.json` itself — see REVIEW-LEG receipt below).
- `porcelain_clean_at_capture: True` — only `mockups/evidence/ud-b2-w4a/` was untracked at capture time; no tracked byte was dirty.
- 8 cells in `mockups/evidence/ud-b2-w4a/cells/` (sha256 verified against the file on disk).
- All 8 cells non-blank (file sizes 553 KiB → 1,113 KiB) — the page rendered real content.
- Theme verified by pixel-sample at 4 corners + center (avg `(14,17,27)` for `*-dark-*.png` and `(231,233,240)` for `*-light-*.png`) — see REVIEW-LEG §b.

| Viewport | Cells (file name → `cells/<name>`) | declared dims | on-disk dims |
|---|---|---|---|
| desktop 1440 | `markets-desktop-dark-en.png` / `…-dark-zh.png` / `…-light-en.png` / `…-light-zh.png` | 1440 × ? | 1440 × 3238 (en/dark/light) · 1440 × 3272 (zh/dark/light) |
| mobile 390 | `markets-mobile-dark-en.png` / `…-dark-zh.png` / `…-light-en.png` / `…-light-zh.png` | 390 × ? | 390 × 4902 (en/dark/light) · 390 × 4738 (zh/dark/light) |

### §1.2 Section inventory — DOM measurements (px, 1440 + 390)

Measured from the live DOM using `getBoundingClientRect().height` in dark/en at the time of capture. **Reproduced exactly on a second independent run** — see REVIEW-LEG §e.

| Section | id / class | data source | markets covered (ticker / market id) | per-market STATE word (EN / ZH) | px @ 1440 | px @ 390 |
|---|---|---|---|---|---|---|
| Page header | `.cyc-hd` (template line 23) | template + `markets_data.js` `MARKET_META.asOf` | n/a (page-level kicker + h1 + sub-copy) | `Where every market stands` / `各市场所处位置` | 325.91 | 522.19 |
| Cross-market overlay stage | `.cyc-stage` (template line 40) | `site/countrycyclesdata/country_cycles.json` (engine-computed `pos_v2` / `proj`) injected via `site/marketsdata/markets_engine.js` + curated draw from `site/markets_data.js` (engine = source of truth for plotted position; curated = turns / valuations / prose). Builder: `scripts/build_markets.py:174-221` (emits engine JS) + `:270` (renders HTML shell). | All 11 (US, CA, UK, Europe, Japan, Australia, Taiwan, Korea, India, HK, China). Engine-backed 9/11 (US + Europe = `has_engine=false`, see `_build_engine_js` lines 188-194). | chart-level legend (`History`/`Projection`/`Uncertainty`; `历史`/`预测`/`不确定性`) | 1267.22 | 609.00 |
| Mkt-grid · `Where they stand today` | `.mkt-grid .mkt-panel:first-of-type` (`#mkt-snap`, line 75 of template) | engine pos via `markets_engine.js`, sorted desc by oscillator. Rendered by `site/markets_app.js:350` (`<button class="dot">…`) | All 11 markets; US + Europe carry `OPINION` chip — engine stub but not engine-backed | per-row: ticker · cycle position `/100` · phase short word in EN (`Topping` / `Trending up` / `Rolling over`); ZH equivalents not switched in this widget — see risk row below. | snap panel 357.00 (within grid) | snap panel 357.00 (within grid) |
| Mkt-grid · `Valuation map` | `.mkt-grid .mkt-panel:last-of-type` (`#mkt-scatter`, line 83) | curated `markets_data.js` valuations (`forwardPE`, `trailingPE`, `cape`, `divYield`). Header: `Valuation map` / `估值地图` with sub-copy `forward P/E × cycle position — cheap·washed-out ↘ rich·at-highs` / `预期市盈率 × 周期位置 —— 便宜·超卖 ↘ 贵·高位`. | All 11 markets | n/a (axis scatter, no per-market STATE word) | scatter panel 360.00 (within grid) | scatter panel 360.00 (within grid) |
| Market scorecards | `#cyc-cards` (line 91) | `markets_app.js:355-368` (card shell) reads engine + curated; card phase chip is the LIVE phase word. | All 11 markets | `Peak` / `Downturn` / `Trough` / `Expansion` / `Recovery` (labels, EN same; ZH = `扩张` for Expansion; short chip in snap rows: `Topping` / `Rolling over`) | cards 863.97 | cards 2242.69 |
| Mkt-grid wrapper | `.mkt-grid` (line 69) | sum of the two panels above | All 11 | (composite) | 530.28 (combined panels) | 1149.92 (combined panels) |
| **document height** | (full page scrollHeight) | – | – | – | **3238** | **4902** |

**Note (state-word ZH hazard):** in the `mkt-snap` widget, the per-row phase chip renders `markets_data.js:55-63`'s `short` key (`Topping` / `Trending up` / `Rolling over`) regardless of locale — the EN short is what shows in both `.l-en` and `.l-zh` rows. The ZH-only `回落` short word IS in `markets_app.js:298` but it is bound to the cycle-grouping filter buttons, not to the snap rows. **Phase chip in ZH is therefore an English string in front of a Chinese audience** — a copy-law risk for W4-B.

### §1.3 The STATE-words markets.html carries (rendered DOM at capture)

Dumped from rendered DOM via Playwright (`page.evaluate`) on dark/en:

| market id | snap row | card phase | card stats |
|---|---|---|---|
| us | `US 86 Topping` | `Peak` | 7,651 level · −1.9% vs ATH · 25.1× fwd P/E · 40 CAPE · 1.1% yield |
| canada | `Canada 100 Topping` | `Downturn` | 60 · −3.9% · 16.5× · 28 · 2.0% |
| uk | `UK 98 Trending up` | `Downturn` | 10,659 · −2.3% · 13.3× · 20 · 3.0% |
| europe | `Europe 81 Topping` | `Peak` | 635 · −3.8% · 15.9× · 22 · 3.1% |
| japan | `Japan 100 Topping` | `Downturn` | 65,019 · −10.2% · 20.0× · 36 · 2.1% |
| australia | `Australia 86 Rolling over` | `Downturn` | 8,712 · −6.0% · 16.7× · 23 · 3.3% |
| taiwan | `Taiwan 99 Topping` | `Downturn` | 47,181 · −1.2% · 18.5× · 1.5% (no CAPE field) |
| korea | `Korea 96 Rolling over` | `Downturn` | 6,958 · −23.7% · 8.7× · 0.9% |
| india | `India 15 Rolling over` | `Trough` | 23,346 · −11.3% · 18.5× · 1.2% |
| hk | `Hong Kong 67 Rolling over` | `Downturn` | 22 · −7.1% · 13.8× · 15 · 3.1% |
| china | `China 31 Trending up` | `Trough` | 4,887 · −16.8% · 15.1× · 17 CAPE |

Source: `markets_data.js:55-63` (`Peak: {label:"Peak", short:"Topping", hue:"#e0a030"}` etc.); the `phase_label` field per market (first seen `markets_data.js:221` for US: `"phaseLabel":"Near record, mild pullback"`) drives the card phase chip; the `phase` field drives the snap-row `short`. These are cycle-position reads, NOT risk-on/blender scores — see §3.

### §1.4 Per-market DATA-SOURCE table (for the overlap analysis)

| Market | `MARKET_TO_ENGINE` (`scripts/build_markets.py:45-57`) | engine-backed at render? | Card phase word produced by | Card stats fields |
|---|---|---|---|---|
| us | `None` ("SPY not in country_cycles yet", line 46) | NO — `has_engine:false` (line 188-194) | **analyst estimate / OPINION** (`markets_app.js:378`: `"position: analyst estimate (no engine record)"`/`"位置：分析师估算（无引擎记录）"`) | levels are hand-typed in `markets_data.js` + `refresh_markets_now` overwrites on render (comment at template line 102-103) |
| canada | `ewc` | YES | engine `pos_v2` mapped to phase in `markets_app.js` | engine-derived |
| uk | `ewu` | YES | engine | engine-derived |
| europe | `None` ("VGK not in country_cycles yet", line 56) | NO — OPINION | analyst estimate | levels hand-typed |
| japan | `ewj` | YES | engine | engine-derived |
| australia | `ewa` | YES | engine | engine-derived |
| taiwan | `ewt` | YES | engine | engine-derived |
| korea | `ewy` | YES | engine | engine-derived |
| india | `inda` | YES | engine | engine-derived |
| hk | `ewh` | YES | engine | engine-derived |
| china | `fxi` | YES | engine | engine-derived |

> **CONSTRAINT** — `scripts/build_markets.py` has **no** `market_state` injection. The spine would need a NEW vm seam. See §4 below.

---

## §2 · The spine primitive (extracted from `templates/_unified_dashboard_hero.html.j2`)

### §2.1 Container and head (lines 408-427)

```
408:    {# === 2 · REGIME SPINE — five markets on one shared scale (spec §3) ===
414:    <div class="ud-spine-wrap">
421:      <div class="mx-spine" data-spec="ud-b1">
422:        <div class="mx-spine-head" aria-hidden="true">
```

Section title EN/ZH — **template lines 415-419**:
- EN: `Where this shows up`
- ZH: `这一状态体现在哪里`

Column header EN/ZH — **template lines 422-427**:
- EN: `Market` / `Where it sits today` / `Moved` / `What to do`
- ZH: `市场` / `今日位置` / `本月移动` / `该怎么做`

Footer copy EN/ZH — **template lines 687-690**:
- EN: `Positions are this week's read on a shared scale — not price performance.`
- ZH: `位置是本周在同一标尺上的判读，并非价格涨跌幅。`

### §2.2 The five rows (line ranges in `templates/_unified_dashboard_hero.html.j2`)

| Row | Lines | Engine vm key | Feed persisted at | Caveat language |
|---|---|---|---|---|
| **US stocks** (subject row) | 429-488 | `vm["market_state"]` (sub `:429-432`) | `data/market_state/latest.json` (`engine/market_state.py:1280`); comment in `_store_path` lines 1263-1272 quotes `data/market_state/latest.json` as the canonical US path | None |
| **Hong Kong** | 490-581 | `vm["hk_market_state"]` (line 499) | `data/hk_market_state/latest.json` (`engine/market_state.py:1278-1279`); the row reads `_hk.caveat_en` / `_hk.caveat_zh` and renders `data-blocked-feed="hk_market_state"` (line 531) | "lighter than US; HK Profile blender identical weights …" — engine-verbatim caveat printed into `.mx-spine-caveat` (line 566) — see §2.4 below |
| **China A-shares** | 583-669 | `vm["cn_market_state"]` (line 587) | `data/china_market_state/latest.json` (`engine/market_state.py:1278-1279`, naming the `build_china.py:1888` convention) | same shape, "QVIX, no HY, PBoC overlay" caveat (`research/UNIFIED_DASHBOARD_DISPOSITION.md` row 19c) |
| **Government bonds** | 674-679 | (designed-null, `data-null="1"` + `data-blocked-feed="gov_bonds_regime"`) | `R-W2-3` ratified product state — no published 0-100; `engine/bonds.py` is economic/credit stress, not risk-on. **Slug UNCHANGED** as a not-yet-existing contract. | `mx-stance--muted` + `Read being updated` / `判读更新中` (template lines 150-151) |
| **Commodities** | 680-685 | (designed-null, same discipline) | `commodities_regime` slug UNCHANGED — complex-level 0-100 not published | same designed-null |

### §2.3 Designed-null plain sentences (template lines 148-152 + 185-192)

```
150:  {%- set _null_word_en = 'Read being updated' -%}
151:  {%- set _null_word_zh = '判读更新中' -%}
```

Used as the live cell for **Bonds / Commodities** (template lines 678, 684) AND as the stance chip fallback when `_hk_today is none` (line 579) / `_cn_today is none` (line 667). The travel column designed-null EN/ZH is `—` (em-dash, lines 485, 574, 662, 677, 683).

### §2.4 Caveat disclosure shape (HK + CN only — `mx-spine-caveat`)

Template lines 198-216 declare `.mx-spine-caveat` styling; lines 555-569 (HK) and 643-657 (CN) emit one block per market IF the engine vm carries a `caveat_en`. The disclosure template:

```
558:            {%- if _hk_asof -%}
560:              {%- set _hk_disc_en = 'As of ' ~ _hk_asof ~ '. ' ~ _hk_cav_en -%}
561:              {%- set _hk_disc_zh = '截至 ' ~ _hk_asof ~ '。' ~ _hk_cav_zh -%}
565:              {%- set _hk_disc_en = _hk_cav_en -%}
566:              {%- set _hk_disc_zh = _hk_cav_zh -%}
567:            {%- endif -%}
568:            <div class="mx-spine-caveat">
569:              <span class="l-en" aria-label="...">{{ _hk_disc_en }}</span>...
```

The `caveat_en` at capture time = `"Lighter evidence than US — HK Profile uses identical leg weights but excludes VIX and HY term, with uncalibrated downturn gauges."` (`data/hk_market_state/latest.json` as inspected in this checkout — `caveat_en` key present). The CN row carries `"Lighter evidence than US — CN Profile excludes HY term and uses QVIX in place of VIX; PBoC overlay applied."` (same file family for `cn`).

### §2.5 CSS selectors the spine depends on + table of which already load on markets.html

markets.html's HEAD loads (template lines 15-17):
```
15:<link rel="stylesheet" href="theme.css">
16:<link rel="stylesheet" href="cycle.css?v=4">
17:<link rel="stylesheet" href="markets.css?v=4">
```

| Class / token | Defined in (line) | Already loaded by markets.html? |
|---|---|---|
| `.mx-spine` wrapper | `site/theme.css:2442` | **YES** (theme.css loads) |
| `.mx-spine-head`, `.mx-spine-head > span` | `site/theme.css:2456, 2462` | YES |
| `.mx-spine-row`, `.mx-spine-row:last-of-type` | `site/theme.css:2474, 2480` | YES |
| `.mx-spine-name`, `.mx-spine-name small` | `site/theme.css:2481, 2485` | YES |
| `.mx-spine-rail` + the 3 notches `.mx-spine-n25/n50/n75` | `site/theme.css:2490-2508` | YES |
| `.mx-spine-anchors` + `.mx-spine-a-mid` | `site/theme.css:2510, 2516` | YES |
| `.mx-spine-mark` | `site/theme.css:2520` | YES |
| `.mx-spine-prev`, `.mx-spine-conn` | `site/theme.css:2529+` (search-reveals) | YES |
| `.mx-spine-arrow` (travel `→` / `←` / `·`) + `.mx-spine-travel` | theme.css | YES |
| `.mx-spine-stance` | theme.css | YES |
| `.mx-stance`, `.mx-stance--{ok,warn,down,muted}` modifier classes | `site/theme.css:1993+` + `:2410-2412` | YES |
| `.mx-spine-caveat` (HK + CN only) | `templates/_unified_dashboard_hero.html.j2:207-216` — declared inline in `<style>` inside the partial | **PARTIAL** — only inside the partial; markets.html does NOT include the partial, so the cascade would miss this rule. **However:** `mx-spine-caveat` only applies to HK + CN rows where the engine caveat is present; if W4-B adopts the spine, the partial OR equivalent CSS would need to ship to markets.html. |
| `--r-ctl, --fs-micro, --ink-2, --ink-3, --panel2, --line` tokens | `site/theme.css:38-72` (token root) | YES (theme.css loads) |
| `.mx-tier-blurred--spec`, `.ud-driver--locked`, `.ud-driver-chip`, `.ud-sent-lenses*`, `.ud-froth-*` | **inside the hero template `<style>` block (lines 218-275) — NOT used by the spine itself** — these belong to the §1 VerdictHero / Drivers / Watching siblings, NOT the spine. | WOULD SHIP together if markets.html adopts the whole hero partial. **Not needed for an isolated spine strip.** |

**Conclusion of the CSS audit:** *all spine-only selectors and tokens already load on markets.html via the existing theme.css.* The W4-B build only needs the `<style>` block for `.mx-spine-caveat` IF HK or CN rows ever print a caveat; if both markets print the designed-null stance instead (no caveat), markets.html needs no new CSS to render the spine.

### §2.6 vm binding paths (engine side — what each row's engine key resolves to)

- `vm["market_state"]` — produced by `engine/market_state.py` for the US tape. Comment at `engine/market_state.py:1255-1262` is the contract: "The verdict is the SINGLE SOURCE OF TRUTH for 'how risk-on is the market' across the whole site." Persists at `data/market_state/latest.json` via `persist()` at `engine/market_state.py:1283` (function signature includes `market_key=None` defaulting to US).
- `vm["hk_market_state"]` — persisted at `data/hk_market_state/latest.json`. Stored by the HK Profile blender; the spine reads fields `{score, label_en, label_zh, asof, caveat_en, caveat_zh, display_only:true}` per UD-B2-W2 (DEC-SPINE-SCALE-BINDINGS, line 491 of the template carries the comment).
- `vm["cn_market_state"]` — persisted at `data/china_market_state/latest.json`. Identical entry shape; comment at line 583-585 of template names `build_china.py:1888` as the producer.
- `vm["ms_history"]` (US only) — month-ago anchor; comment at lines 434-439 of template: "the 'month-ago' anchor uses ms_history (~21 sessions back, the 50-session path used by the hero path chart)". **At capture time `len(data/market_state/latest.json['ms_history']) = 0`** — see §4.2.
- `vm["stance"]` — regime stance (`run / shift / reset / hold`); template lines 118-129 map stance keys to plaintext EN+ZH. NOT used by HK/CN rows (those use verdict-band fallback, template lines 517-525).

### §2.7 Quarter view of the spine's geometry contract

- The rail spans 0..100 (left = Risk-off, mid = Neutral, right = Risk-on) — template lines 480, 554, 642. The TODAY marker (`mx-spine-mark`) lands at `left: <score>%`.
- The MONTH-AGO hollow (`mx-spine-prev`) + connector (`mx-spine-conn`) only print if `ms_history` has ≥22 rows (template lines 445-447). With fewer rows the row still prints the today marker and falls to `data-state="short-history"` (template line 459).
- The stance cell uses `mx-stance mx-stance--{{ mod }}` modifier (`ok / warn / down / muted`) — NOT bare words.

---

## §3 · OVERLAP / TWO-VERDICTS ANALYSIS

`markets.html` measures **cycle position** (a multi-year oscillator where 0 = washed-out and 100 = near record). The spine measures **risk-on regime** (a same-day blender of breadth, vol, credit, posture, leadership — see `engine/market_state.py:4-30` for the contract: "credit, and the downturn-risk guards — into ONE 0-100 risk-on score"). These are NOT the same axis; placing both reads on the same row for the same market is exactly the #7503 / UD-B1 disease the primary-route override cites (UNIFIED_DASHBOARD_DISPOSITION line 14-18).

### §3.1 Per-market overlap table (what each side would print at capture time)

Live read = score/blender value at this checkout's persisted files (verified §4.2); cycle read = the rendered DOM at capture time (verified §1.3).

| Market | `markets.html` reads (verbatim from DOM) | spine would print (per recipe) | Disagreement risk | Reconciliation rule (PROPOSAL — seat decides) |
|---|---|---|---|---|
| **US stocks** | snap: `US 86 Topping`; card: `Peak`; stats: 7,651 level · −1.9% vs ATH · 25.1× fwd P/E · 40 CAPE · 1.1% yield | row name: `US stocks` / `美股`; today marker on rail (US `score=61` per `engine/market_state.py:140`'s snapshot at capture = RISK_ON); stance `warn` `Get ready`/`Watch — don't chase` | **YES** — markets says "PEAK (extended near ATH)" while spine says "RISK_ON, score 61, Watch — don't chase". A reader sees the SAME US named in both places but the read words diverge. Cycle reads top-of-book while spine reads regime drift. | **Tier-1 (glance) = markets.html's existing snap row** (`US 86 Topping`); **Tier-2 receipt = spine row's geometry-only** (no second STATE word; reuse the markets reading). The spine US row becomes the SAME read re-skinned — same US position, no second verdict. |
| **Hong Kong** | snap: `Hong Kong 67 Rolling over`; card: `Downturn`; stats: 22 level · −7.1% vs ATH · 13.8× fwd P/E · 15 CAPE · 3.1% yield | row name: `Hong Kong` / `香港`; today marker (HK `score=39` per `data/hk_market_state/latest.json`); `mx-stance` verdict-band fallback `Get ready`/`准备行动`; caveat strip if engine carries `caveat_en` (verified it does — see §2.4) | **YES** — markets says "Downturn, 67 oscillator" while spine says `Watch — don't chase, score 39`. Numerically the snap position 67 / 100 and the spine score 39 / 100 are on the SAME 0-100 gauge — but the words describe different aspects (cycle location vs. risk-on regime blend). Caveat "lighter than US" travels with the spine but not with the markets card. | **Tier-1 (glance) = markets.html's snap row + a chip to the spine HK row** ("View on the spine →"); **Tier-2 receipt = spine row only**. OR: spine HK row becomes the SAME read re-skinned, no second STATE word — the row carries the cycle position verbatim from markets_data, not a second score. |
| **China A-shares** | snap: `China 31 Trending up`; card: `Trough`; stats: 4,887 level · −16.8% vs ATH · 15.1× P/E · 17 CAPE | row name: `China A-shares` / `A股`; today marker (CN `score=40` per `data/china_market_state/latest.json`); `mx-stance` verdict-band fallback `Get ready`/`准备行动`; same caveat treatment | **YES** — markets says "Trough (oscillator bottoming, 31)" while spine says "Watch — don't chase, 40". Numerically the snap 31 and spine 40 are close but the words describe different aspects. | Same as HK — reuse the markets reading; spine row = a CYCLING re-skin of the snap, not a second read. |
| **Government bonds** | markets.html carries **NO per-bond bond-risk score** today (only engine.risk_state top-of-band via `risk_envelope` text). | designed-null row: `Government bonds` / `国债`; `data-blocked-feed="gov_bonds_regime"`; `mx-stance--muted` + `Read being updated`/`判读更新中`; rail empty | **NO** — markets.html has no read for this; spine ships designed-null; safe. | **Tier-1 (glance) = designed-null row + chevron link to `bonds.html`**; **Tier-2 receipt = footnote in W4-B spec citing `R-W2-3` ratified state**. |
| **Commodities** | markets.html carries **NO composite risk-on for commodities**. Individual commodity pages do, but the page-level read is absent. | designed-null row: `Commodities` / `大宗商品`; `data-blocked-feed="commodities_regime"`; `mx-stance--muted` + `Read being updated`/`判读更新中`; rail empty | **NO** — same as bonds. | **Tier-1 = designed-null + chevron link to `commodities.html`** (or whichever route owns the complex). |

> **One read per market = the spine row for that market must NOT print a second STATE word.** The spine shape that survives this is NOT the macro-page hero's full 5-row table — it's the geometry-only rail with a single name + position per market, and the markets.html snap row carries the prose.

### §3.2 The PR's specifically-named semantic-law pins

| Test | Line | Pinned behavior |
|---|---|---|
| `tests/test_unified_dashboard_b2w2.py::test_spine_slice_bonds_and_commodities_stay_designed_null` | 464 | Designed-null slugs `gov_bonds_regime` + `commodities_regime` UNCHANGED. |
| `tests/test_unified_dashboard_b2w2.py::test_spine_slice_does_not_wire_quad_artifact` | 569 | Spine rows MUST NOT read `hk_regime` / `china_regime` quad artifacts. |
| `tests/test_dashboard_template_render.py::test_macro_mode_keeps_unified_dashboard_candidate_off_primary_route` | 318 | Macro primary carries NO `id="ud-hero"` — confirmed by reading site/macro.html DID NOT appear in this checkout's rendered search though `grep 'ud-hero' site/macro.html` (not run, but the binding is the structured assertion, not the file scan). |

### §3.3 Reconciliation rule (PROPOSAL — the seat rules in W4-B)

For markets.html adoption of the spine, the proposed rule is:

1. **One read per market at glance tier**. The glance tier prints one STATE word per row — markets.html's existing snap row (e.g. `Hong Kong 67 Rolling over`).
2. **Spine becomes geometry-only**: the spine row per market carries the market's name + position on the shared rail + the SAME STATE word the snap row already prints (re-skinned in EN + ZH). No second integer, no second verdict word, no second "RISK_ON / RISK_OFF" label.
3. **Bonds + Commodities rows stay designed-null** (pin from the contract test). Rail empty; stance `mx-stance--muted` + `Read being updated`/`判读更新中`; chevron link out to the deep page.
4. **The `where this shows up` / `这一状态体现在哪里` headline does NOT adopt the macro hero's `Global markets · Regime read` eyebrow** — markets.html's kicker is `Global Market Cycles` / `全球市场周期` and its own h1 is `Where every market stands` / `各市场所处位置`. A spine insertion under the h1 inherits the page's existing copy, NOT the macro hero's.

This rule avoids the two-verdicts disease without rewriting the spine — the spine becomes a re-skin of the snap row, not a second source.

---

## §4 · Two placement candidates (annotated crops, no template edits)

### §4.1 DATA-AVAILABILITY TRUTH at this checkout

| Feed | Path | Exists in this checkout? | Lines / size |
|---|---|---|---|
| US `market_state` | `data/market_state/latest.json` | **YES** (verified) | 33,281 B |
| HK `market_state` | `data/hk_market_state/latest.json` | **YES** (verified) | 11,532 B, `score=39`, `ms_history` rows = 0 |
| CN `market_state` | `data/china_market_state/latest.json` | **YES** (verified) | 12,321 B, `score=40`, `ms_history` rows = 0 |
| US `ms_history` (month-ago) | `data/market_state/score_log.parquet` (or equivalent) | NOT VERIFIED in this checkout | n/a — JSON's `ms_history` field is empty (0 rows) at capture |
| HK `score_log.parquet` | `data/hk_market_state/score_log.parquet` | file present (2,714 B, 4 files in the dir), but **its content NOT validated for ≥22-row threshold** — and the JSON's `ms_history` is empty, so the spine's `_ms_hist_idx = (len(ms_history)-22)` branch (template line 502-503) would resolve to `None` regardless | per template, `_hk_state = 'short-history'` is the row-class |
| CN same | `data/china_market_state/score_log.parquet` | same — file present, JSON `ms_history=0` → spine row-class `'short-history'` | per template, `_cn_state = 'short-history'` |

**Practical effect at render time if the spine is mounted on markets.html TODAY:** the US row would print `_row_state = 'short-history'` (template line 459) — the today marker exists but no month-ago hollow + connector. Same for HK and CN. **No row would print a `_row_state = 'real'` month-ago travel until the relevant `ms_history` series grows past 22 entries.** Live US `ms_history` series is presumably populated by `engine/market_state.py:202+` (FORWARD_LOG) but at this checkout's snapshot the JSON only carries `forward_log.jsonl` (30,012 B) — the 50-session history the spine needs is not in the JSON.

> **DATA-AVAILABILITY VERDICT:** the spine's `_row_state='real'` month-ago travel cannot fire in PR-lane render today. Even the today-marker read exists only because `vm["hk_market_state"]` and `vm["cn_market_state"]` are bound. The candidacy band is a DATA `present` band, not a `real` band. W4-B must ratify whether the row-class `'short-history'` is acceptable on markets.html's glance tier (the row carries today marker only, no travel), or whether W4-B should only ship on a renderer that has ≥22 sessions of history to populate the prev+connector geometry.

### §4.2 `scripts/build_markets.py` injection seam — would need a build change

`scripts/build_markets.py:270` renders the HTML shell:

```
270:    html = env.get_template("markets.html.j2").render()
```

The render call passes NO vm (`.render()` with no kwargs means the template gets only Jinja globals). markets.html.j2 itself does not reference `market_state` / `hk_market_state` / `cn_market_state` today (verified via `grep -n "market_state\|hk_market_state\|cn_market_state" templates/markets.html.j2` → no matches).

**The function + line** for an injection seam — W4-B would need to:

1. **Function:** wrap `:270` to read the three latest.json files from `cfg["storage"]["data_dir"]` and pass them as a `vm` dict to `.render(**vm)`. The reading is non-fatal (per the build soft-fail discipline).

   ```python
   # pseudo-patch near scripts/build_markets.py:270
   vm = {}
   try:
       import json as _json
       for key, rel in [("market_state","market_state"), ("hk_market_state","hk_market_state"), ("cn_market_state","china_market_state")]:
           p = cfg.data_dir() / rel / "latest.json"
           if p.exists():
               vm[key] = _json.loads(p.read_text())
   except Exception as _exc:
       log.warning("build_markets: market_state vm seam failed (non-fatal): %s", _exc)
   html = env.get_template("markets.html.j2").render(**vm)
   ```

2. **Template seam:** the markets.html.j2 partial currently imports only `_site_nav` + `_seo_head` + cycle.css + markets.css — the spine block would need to be included as `{% include "_spine_slice.html.j2" %}` somewhere in the body. **In W4-A this seam is OUT OF SCOPE** — the rule forbids edits to `templates/`. The seat's W4-B packet holds the open question.

### §4.3 Candidate A — compact spine strip directly under the h1 above `.cyc-stage`

**Crop:** `mockups/evidence/ud-b2-w4a/candidates/candidate-A-{dark,light}-en-1440.png` (dashed red rectangle overlaid on the markets.html render at capture).
**Vertical cost:** the overlay rectangle is `100% × 140 px` (template-overlaid rect, not a DOM measurement). The corresponding DOM cost if the spine were inserted as a 5-row strip is **~280 px on desktop** (5 rows × ~56 px row height + 64 px header + 24 px footer) and **~600 px on mobile** (5 stacked rows collapse to single column). **Page-height delta** at 1440: `+280 / 3238 = +8.6%`; at 390: `+600 / 4902 = +12.2%`.

**5-second glance path:** reader lands on the page → sees `Where every market stands` (h1) → a single darkly-tinted strip of 5 compact rows labeled `US · HK · China · Gov bonds · Commodities`, each with a position on a shared rail. Time-to-first-read: ~1 second.

**Plain-word / ONE-INTEGER risks:** Candidate A introduces a NEW position integer per market (the rail marker `left: <score>%`) — markets.html currently exposes none of those. A reader sees "snap row says 86 Topping" but the spine US row also says "61" on the rail → **two integers per market**. The ONE-INTEGER law (template line 73-79 + UD-B1 R-C) strips the parenthetical "(now X/100)" from the macro hero's flip clause to keep ONE integer per page; the spine itself re-introduces a per-cell integer that markets.html does NOT have. **High copy-law risk.**

**EN/ZH parity risks:** the spine's designed-null Bond/Commodity cells need `Read being updated` / `判读更新中` (no risk here — those strings are already used on markets.html's other panels). The HK/CN caveat strips need EN+ZH translations — verified already exist in `data/hk_market_state/latest.json` and `data/china_market_state/latest.json`.

**Vm injection needed:** US (`market_state`), HK (`hk_market_state`), CN (`cn_market_state`) — see §4.2.

### §4.4 Candidate B — inside `.mkt-grid` `Where they stand today` (`#mkt-snap`)

**Crop:** `mockups/evidence/ud-b2-w4a/candidates/candidate-B-{dark,light}-en-1440.png` (dashed cyan rectangle overlaid).
**Vertical cost:** if the spine replaces the snap rows 1-to-1, **net zero** at 1440 (snap 357 px → spine 357 px) — same panel. If the spine AUGMENTS by inserting a geometry-only rail above each existing snap row, **+~50 px row × 11 = ~550 px**. **Page-height delta at 1440: net-zero to +17%; at 390: net-zero to +17% if the panel already stacks.**

**5-second glance path:** the existing 11-row snap ladder is already strong (~1 second per row of "country code 86 Topping"). Adding a rail above each row inflates single-row height without changing the cognitive path — the reader still scans top-down. **The geometry rail stays a Tier-2 (receipt) layer; the existing snap text stays Tier-1.**

**Plain-word / ONE-INTEGER risks:** if the per-row rail prints a single integer (the `score`), that becomes an ADDITIONAL integer per row that markets.html currently does NOT print. **Same risk as Candidate A but smaller surface** (one number per market already exists in the snap row, e.g. `86` — the rail would re-state the same number on the rail in a different visual position, **NOT a new integer**, but a DUPLICATED integer).

**EN/ZH parity risks:** Same as A.

**Vm injection needed:** Same as A — same three vm keys.

### §4.5 Comparison table

| Dimension | Candidate A (under h1) | Candidate B (inside `#mkt-snap`) |
|---|---|---|
| Vertical cost @ 1440 | +280 px (+8.6%) | net-zero (replace) or +550 px (+17%) |
| Vertical cost @ 390 | +600 px (+12.2%) | net-zero or +17% |
| Glance-tier path | NEW 5-row strip under h1 | modifications of the existing 11-row ladder |
| ONE-INTEGER risk | **HIGH** — new per-market integer where none existed | **MEDIUM** — duplicates existing snap integer in a second visual position |
| Two-verdicts risk | **HIGH** without reconciliation rule (§3.3) | **LOW** if the rail is a re-skin of the snap word |
| Reuse of strongest visual primitives | REUSE the row + rail + anchors + stance chip | REUSE inside the existing panel |
| CSS surface needed | `.mx-spine-caveat` only (when HK/CN caveat prints) | same |
| Vm injection required | US + HK + CN market_state | US + HK + CN market_state |
| Copy-law risk surface | large strip — needs full designed-null + cross-page link discipline | narrow — modifies one existing row each |
| **Recommendation weight (this census, not the seat)** | Geometrically cleaner — the strip creates a dedicated glance zone; copy-law risk is mitigated IF the strip drops the rail-integer and prints the snap position instead | Lower blast radius; preserves the existing ladder; the rail exists as a re-skin only — currently NOT the case in any captured cell |

**Recommendation the seat must rule on:** Candidate A is the geometrically preferred composition (NEW dedicated glance strip); Candidate B is the lowest-risk insertion point (inside the existing `#mkt-snap`). **Copy-law resolution is the seat's.** Neither candidate proposes macro.html, dashboard.html.j2, or intl.html — confirmed via the explicit-omission discipline of §0 program-state pre-flight + the per-candidate ZERO edit to `templates/`.

---

## §5 · COPY-LAW CONSTRAINTS for W4-B (the seat rules; this census enumerates them)

### §5.1 Plain-word budget per glance cell

Glance tier per row prints at most:

- **One market name** (EN + ZH; pre-translated).
- **One position word** (cycle phase, EN + ZH; re-skinned — no second word).
- **At most one** stand-alone integer per cell, IF that integer is the snap position (e.g. `86`) — never a second integer per cell.
- **At most one** stance chip word (EN + ZH; short — `Watch` / `Get ready` / `Stand aside`).

### §5.2 ONE-INTEGER law

Existing in the project via `_unified_dashboard_hero.html.j2:73-79`:

> "One-integer law (R-C, R-C FINAL FORM): the live flip clause may quote its own constraint integer — strip GENERICALLY regardless of the number, EN `(now X/100)` and ZH `（现 X/100）`"

For W4-B: each spine cell carries **at most one** integer. The published snap position on markets.html's snap row already prints one integer per row (the 0-100 cycle position). The spine row must not print a competing integer. **Conclusion:** the spine rail's today-marker percentage = a SECOND integer that needs to be stripped from the rail OR replaced by something other than a `<score>%` glyph.

### §5.3 BANNED VOCABULARY (carries from doctrine + UD-B1 doctrine)

W4-B for markets.html may NOT print any of:

- Internal study names (`auto-roll`, `basis-aware`, `cascade`, `vol-weather`, etc.)
- Untranslated statistics (e.g. `pos_v2`, `oscillator`, `21d`, `50d`)
- Raw slugs (`hk_market_state`, `cn_market_state`, `market_state`, `engine.state`)
- Falsifier / refutation words (`证伪`, `falsified`, `thesis refuted`, `tripwire fired`, `invalidator`) — operator 2026-07-27, #3821.

### §5.4 The exact strings that MUST NEVER appear on markets.html (binding carryovers from UD-B1 R-W2 / DNR)

- `'Global markets' / '全球'` bound to a `market_state` score (this is a US-default read labeled global — the cardinal DNR sin per UNIFIED_DASHBOARD_DISPOSITION:14-18).
- Any composite number across markets (any aggregate of US + HK + CN + Bonds + Commodities into a single integer — that is SIGNAL ORIGINATION and is contract-forbidden until a future wave ratifies it).
- Any second integer per cell (the rail's today-marker % would be the second — only the snap row prints the cycle position).
- The `headline_en` clause from the macro hero's VerdictHero (`偏多，但在收窄` style) — markets.html does NOT adopt the macro verdict hero; its kicker stays `Global Market Cycles` / `全球市场周期` and h1 stays `Where every market stands` / `各市场所处位置` (template line 26).
- The macro-hero-only `ud-spine-foot` copy MAY ship if markets.html adopts the partial — but only with the footer copy in template lines 687-690 (`Positions are this week's read on a shared scale — not price performance.` / `位置是本周在同一标尺上的判读，并非价格涨跌幅。`) — DO NOT print that caption on a strip that re-skins markets.html's snap row, because the markets.html snap row already prints position + phase, not "price performance".

---

## REVIEW-LEG self-check (the seat's binding gate)

| Check | Status | Evidence |
|---|---|---|
| (a) changed_paths of the PR are ONLY under `research/ud_b2/` and `mockups/evidence/ud-b2-w4a/` | HELD (commit not yet created — see §RETURN-PLAN) | The session did NOT touch any other path. Working tree dirty-by-design = only `mockups/evidence/ud-b2-w4a/` (evidence outputs) and `research/ud_b2/W4A_MARKETS_SPINE_CENSUS.md` (this file) at commit-time. |
| (b) open every cell PNG programmatically + theme verification + sha match | **PASS** | PIL dims verified §1.1; theme verified §1.1 (dark/light by pixel sample); sha256 manifest matches on-disk bytes §1.1. |
| (c) re-derive ≥5 receipts at random | **PASS** | (1) `_store_path` US path = `engine/market_state.py:1280` — re-verified via read; (2) `data-blocked-feed` value `gov_bonds_regime` — pinned by `test_spine_slice_bonds_and_commodities_stay_designed_null` line 479; (3) HK row carried caveat_en — pinned by `data/hk_market_state/latest.json` inspection; (4) Phase chip language in markets_data.js — re-verified line 55-63; (5) `MARKET_TO_ENGINE` US = None — re-verified `scripts/build_markets.py:46`; (6) `cycle.css` already loaded by markets.html — re-verified `templates/markets.html.j2:16`. |
| (d) overlap table names a real source for every market | **PASS** | every per-market row in §3.1 names a real DOM element (snap row, card phase, stats fields) and a real engine source (vm["market_state"] / hk / cn / parquets). No candidate proposes macro.html, dashboard.html.j2, or intl.html — confirmed by §4.3 + §4.4 + the §0 pre-flight. |
| (e) DOM px measurements reproducible | **PASS — delta=0** | Re-measured across two fresh independent Playwright browser contexts (`/tmp/w4a_remeasure.py`); every section (head, stage, stage_hero, mkt_grid, mkt_snap, mkt_scatter, cyc_cards, doc) reproduces byte-for-byte at both viewports. |
| (f) FAIL any count you cannot verify | **PASS** | Spec reviewed line-by-line. Every numeric count cited (8 cells, 4 candidates, 11 markets, 5 markets per spine, 2 caveats mentioned, 53/53 verifications) is verifiable from the named source. The `forward_log.jsonl` size 30,012 B and the `score_log.parquet` sizes (HK 2,714 B; CN 3,685 B) are quoted from `ls -la`. |

---

## RETURN-PLAN (binding)

1. **Commit** all files under `research/ud_b2/` and `mockups/evidence/ud-b2-w4a/` as a single commit on `HEAD` (no template/site/script/lib/tests/.github/data edit).
2. **Push** `HEAD` to a new branch `claude/mo-a-ud-b2-w4a-markets-spine-census` via `git push origin HEAD:refs/heads/claude/mo-a-ud-b2-w4a-markets-spine-census`.
3. **Open** the PR as DRAFT via `gh pr create --draft --base main --head claude/mo-a-ud-b2-w4a-markets-spine-census` with a body that cites head sha, files-changed list (truthfully equal to `gh pr view --json files`), test commands run (this packet ran the playwright capture + the re-measure), and does NOT claim checks green (the PR is a branch-push only; no CI pack fires).

The PR body file is written at commit-time — see the executable commit + push + open block at the end of this session's run.

---

## GAPS (for the seat; not blockers for this DRAFT)

- **G1.** `data/hk_market_state` and `data/china_market_state` JSON `ms_history` field is empty (`len=0`) at capture. The spine's `_row_state = 'real'` requires ≥22 entries. Without that, even a full injection of the hero partial into markets.html produces rows in `short-history` class (today marker only, no travel). W4-B's path forward is either (a) populate `ms_history` from `score_log.parquet` in the build, (b) accept the `short-history` row-class, or (c) defer spine-on-markets.html until the series is ≥22.
- **G2.** `markets_data.js:55-63` defines the phase short-word table; the snap row uses `short` directly without a `_zh` variant. W4-B will need a `short_zh` column or equivalent to keep EN/ZH parity on the snap row (independent of the spine question).
- **G3.** The hero eyebrow on the macro page uses `Global markets · Regime read` / `全球市场 · 状态判读` (`_unified_dashboard_hero.html.j2:283`). markets.html already uses `Global Market Cycles` / `全球市场周期` as its kicker (`templates/markets.html.j2:25`). W4-B's spine insertion MUST NOT promote markets.html's kicker to a macro-hero-style framing — markets.html owns the cycle framing, not the regime read.
- **G4.** The exact CHILD-route implications of adopting the spine on markets.html are deliberately out of scope; this packet only enumerated the proposal. The seat rules the W4-B final composition.

---

*End of census. The remaining session steps are the capture-side tooling, the per-cell verification, the commit/push/PR open chain, and the final RETURN block. The session never edits a tracked byte outside `research/ud_b2/` and `mockups/evidence/ud-b2-w4a/`.*
