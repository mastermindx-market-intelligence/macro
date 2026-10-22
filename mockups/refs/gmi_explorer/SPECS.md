# GMI Explorer — implementation spec

Reference design for the GMI theme-graph surfaces, drawn 2026-10-21/22 by ORCH-DESIGN (Opus 5.5) under the GMI Meta-CEO seat.
**Status: DESIGN REFERENCE ONLY.** Nothing here is shipped. The implementation PR ports the markup below into Jinja
under the existing `_site_nav.html.j2` family and promotes the CSS into governed stylesheets. The design decisions,
critique rounds and data GAPs are in `research/theme_graph/gmi_design_20261021/DESIGN_RECORD.md`.

Every page, PNG and proof line in this folder is regenerated from the committed data fixture by one command (§14).
The HTML specimens and `gmi_explorer.css` are the **implementation source**. The PNGs and the Paper file
"GMI Explorer 2026-10-21" are the **visual reference** for each matrix cell.

---

## 0. Acceptance gates for the implementation PR (not done unless)

1. Every surface renders the specimen class structure at **1440 and 390**, in **dark and light**, in **EN and ZH**.
   The PR body carries per-cell crops that match `png/<page>_<theme>_<lang>_<width>.png`.
2. At 390px, `document.documentElement.scrollWidth == 390` on every page and in both languages (audit command in §14).
3. The S2 index renders **all 371 micro-themes** at 390px. The DOM count of visible `.gmi-irow-name` must be 371
   (the `PROOF` line in §14 checks this).
4. The frozen 68 (Core) and the 303 expansion rows (Extended) are told apart by **mark shape**: hatched versus
   dashed, plus a legend. An Extended row never renders as a hidden zero.
5. Each page has **one h1**. Tier-1 h1 is at most 4 words and the sub-line at most 14 words (budget table in §7).
6. No `title=` attribute carries translated text. Tier-2 tips use `data-tip-en` / `data-tip-zh` and stay at or under 80 words.
7. No stance chip. Never the word "validated". No front-facing falsifier or refutation language. No internal
   state, study or reason-code names on Tier 1, and no vendor names used as taxonomy.
8. Every unset field prints its plain-word unknown from the state matrix (§10). Never print `0`, `—` or blank
   for "not measured".
9. The header is `templates/_site_nav.html.j2` and nothing else. Never add a third header family.
10. `templates/ontology.html.j2` and `templates/ontology.css` are preserved. GMI is a sibling surface, not a redesign of them.

## 1. Files in this folder

| File | Role |
|---|---|
| `build_specimens.py` | Data-driven generator. It asserts 371 / 68 / 303 / 1 PROPOSED_ONLY / 0 admitted, US 1,931 and CN 1,019, emits the six pages and renders the 60 PNGs. sha256 `b8d562c03f89118c4aea11c2f71b632619d6fc15d5c9fc4dc35bd44e1bedbbbb` |
| `gmi_explorer.css` | Reference stylesheet, sections A–N. It extends `templates/theme.css` and declares **no shipped token**. sha256 `21889913bba7bba0228acc3b88c7a4237f506cc9a54c05e06ff1fc43fe72a0a1` |
| `inputs/fixture.json` | Frozen data fixture. Its `provenance` block names the commit and path behind every number (§13) |
| `inputs/nav.html` | Static capture of the `_site_nav` markup, so the specimens wear the real header |
| `s1_issuer.html` | S1 Issuer explainer (Micron Technology) |
| `s2_theme_map.html` | S2 Theme map (census sheet + tree; lenses = coverage, value chain) |
| `s2_index.html` | S2 full index (all 371 micro-themes, grouped by category) |
| `s3_relationships.html` | S3 Relationship explorer |
| `s4_coverage.html` | S4 Coverage & receipts |
| `s5_states.html` | S5 Degraded-state sheet (10 states) |
| `png/` | 60 PNG references (§13) |

## 2. Reference and baseline

- `docs/DESIGN_DOCTRINE.md` wins on any conflict. The doctrine sections applied are §9 density, §12 light,
  §13 zh, §14 accessibility and §15 breakpoints.
- `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` sets the archetype per route (§3).
- `mockups/design_system/specimen.html` holds the canonical components. Section A of `gmi_explorer.css` copies its
  primitives verbatim (specimen lines 20–134) because they are not yet in `theme.css`. That is GAP **G-DS1**:
  the implementation PR promotes them into `theme.css` once, rather than copying them again.
- `templates/theme.css` provides the tokens. The specimens link it live at base commit `9b48e798a3eb` (origin/main at capture).
- `templates/navigation-refresh.css` and the `_site_nav` family provide the header (§0.9).
- Fonts are Inter (EN) and PingFang SC (ZH), through theme.css `--font-ui` / `--font-mono`.

## 3. Archetype per surface

| Surface | Page | Archetype (MPDS V1) | Fold = chrome + answer + ≤2 modules |
|---|---|---|---|
| S1 Issuer explainer | `s1_issuer.html` | **C instrument_analyzer** | head → answer (principal activity + one held theme link) → lineage ladder (micro → sub-theme → theme → category) + fact list (value-chain position, source, as-of, status) |
| S2 Theme map | `s2_theme_map.html` | **B discovery_board** | head → census tally line → census survey sheet (371 cells, lens-switchable) |
| S2 Index | `s2_index.html` | **B discovery_board**, list mode | head → search → 10 collapsible category groups holding all 371 rows |
| S3 Relationships | `s3_relationships.html` | **C instrument_analyzer**, evidence task | head → relationship hero (claim + direction figure, facts grid, filing excerpt one tap below) → magnitude history |
| S4 Coverage & receipts | `s4_coverage.html` | **E intelligence_desk** | head → "0 companies admitted" band with US/CN frozen denominators → disposition ledger |
| S5 Degraded states | `s5_states.html` | states sheet (reference, not a route) | every state card shows what failed, what still works and one action |

S2 uses its own `.gmi-census` and does **not** reuse `.mx-ladder`, which is Prophet-semantic (GAP in DESIGN_RECORD).

## 4. Art direction — two treatments, one information architecture

Dark and light share the information architecture, component semantics, spacing and type scales, state meanings,
actions, data contracts, ordering and density. They differ in **material**. Swapping tokens alone does not
produce the light design. Each mechanism in the table below is written separately per theme in `gmi_explorer.css`.

### DARK TREATMENT — command center

- The page sits on `--bg` (#0f1115). Panels step up in luminance (`--panel` #181b21 → `--panel2` #1e222a), not in lines.
- Hero bands carry the page's only atmosphere: a 9% radial `--info` wash from the top-left corner (`--gmi-hero-wash`).
- Elevation is a 1px inset top highlight plus a 1px drop (`--gmi-elev`). There are no large shadows.
- Census bands separate by alternating luminance (`--gmi-step`, text at 2.5%), like an instrument panel's banding.
- Glow is rationed to two states: **held** (`--gmi-glow-held`: a 3px info ring at 16% plus a 14px bloom) and
  **selected** (`--gmi-select`: a 1px link ring plus a 22px soft glow). Nothing else glows.
- Degraded content dims under a veil (`opacity:.45; filter:saturate(.4)`), so the page reads as "powered down" rather than broken.
- Calm: no animated glow, no gradient text, no colored container edges. Status is labeled ink (doctrine §9).

### LIGHT TREATMENT — research workspace

- A cool canvas `--bg` (#f7f8fa) under white `--panel` material, with `--line` hairlines.
- Elevation is a two-layer soft shadow: `0 1px 2px rgba(20,30,50,.06), 0 8px 24px -16px rgba(20,32,64,.22)`.
  Shadow replaces glow everywhere.
- There is no hero wash. The hero is a white card with a hairline and a shadow.
- Census bands are a **ruled survey sheet**: hairline separators at radius 0 instead of luminance bands.
- Held is a 3px `--ink-info` ring at 14% with no bloom. Selected is a 2px `--link` ring.
- Mark ink is denser (`--gmi-mark` 86% vs 78% in dark; hatch 30% vs 40%), because a white sheet reads lighter.
- The histogram's "now" column is a solid text-colour bar instead of a glow.
- Degraded content prints in muted ink under a 6px hatched top band. This is a print idiom and survives grayscale.
- Chips, buttons, search, ladder rungs and path nodes become white objects (panel + line + small shadow).

### Mechanisms that intentionally differ

| Mechanism | Dark | Light | Where |
|---|---|---|---|
| Atmosphere | `--gmi-hero-wash` radial info 9% | none | `.gmi-band`, S1/S3 hero |
| Elevation | inset highlight + 1px drop | two-layer soft shadow | `--gmi-elev` |
| Band separation | luminance step (`--gmi-step`) | hairline rules, radius 0 | `.gmi-census` bands |
| Held emphasis | ring + bloom | ring only | `--gmi-glow-held` on `.gmi-sm--held` |
| Selection | 1px ring + glow | 2px ring | `--gmi-select` |
| "Now" column | glow | solid text-colour bar | `.gmi-hist-col--now` |
| Degraded | veil (opacity .45, saturate .4) | muted ink + 6px hatched band | `.gmi-degraded` |
| Controls | panel2 fill | white + line + shadow | chips, `.gmi-btn`, search, rungs, path nodes |
| Mark density | mark 78%, hatch 40% | mark 86%, hatch 30% | `--gmi-mark`, `--gmi-hatch` |

### Theme-specific degraded states

The `stale` state and the `source_paused` fallback both use `.gmi-degraded`. In dark, the last good read is
shown dimmed under the veil. In light, it is shown in muted ink under the hatched band. Either way, the data stays
legible and the state title says which read is showing. `loading` uses the specimen `.skel` shimmer in both
themes (luminance in dark, panel2 grey in light). Every other state is a card whose elevation follows its theme.

## 5. Tokens — an extension of `templates/theme.css` only

**Shipped tokens consumed** (all present in `templates/theme.css` at `9b48e798a3eb`, checked by grep):
`--bg --panel --panel2 --text --muted --line --link --info --ink-info --ink-ok --ink-warn --ink-act --font-ui --font-mono --fs-display --fs-h1 --fs-h2 --fs-md --fs-body --fs-sm --fs-label --fs-micro --fs-num-lg --fs-num-xl`.

**New `--gmi-*` tokens.** Each one is a `color-mix()` or composition of a shipped token. There is no new hue.
This is section B of `gmi_explorer.css`, verbatim:

```css
/* ---------- B. GMI extension tokens (derived only) ------------------------------ */
:root{
  --gmi-mark:       color-mix(in srgb, var(--text) 78%, transparent);  /* admitted: solid ink   */
  --gmi-mark-faint: color-mix(in srgb, var(--text) 44%, transparent);  /* outlines              */
  --gmi-hatch:      color-mix(in srgb, var(--text) 40%, transparent);  /* acceptance-set hatch  */
  --gmi-held:       var(--info);                                       /* held ring (redundant to shape) */
  --gmi-hair:       color-mix(in srgb, var(--text) 9%, transparent);   /* dark hairline         */
  --gmi-step:       color-mix(in srgb, var(--text) 2.5%, transparent); /* dark luminance step   */
  --gmi-elev:       inset 0 1px 0 rgba(255,255,255,.035), 0 1px 0 rgba(0,0,0,.35);
  --gmi-select:     0 0 0 1px var(--link), 0 0 22px -8px color-mix(in srgb, var(--link) 70%, transparent);
  --gmi-hero-wash:  radial-gradient(120% 160% at 0% 0%, color-mix(in srgb, var(--info) 9%, transparent), transparent 62%);
  --gmi-glow-held:  0 0 0 3px color-mix(in srgb, var(--info) 16%, transparent), 0 0 14px 0 color-mix(in srgb, var(--info) 55%, transparent);
  --gmi-cell:14px; --gmi-cell-gap:5px;
}
html[data-theme="light"]{
  --gmi-mark:       color-mix(in srgb, var(--text) 86%, transparent);
  --gmi-mark-faint: color-mix(in srgb, var(--text) 40%, transparent);
  --gmi-hatch:      color-mix(in srgb, var(--text) 30%, transparent);
  --gmi-held:       var(--ink-info);
  --gmi-hair:       var(--line);
  --gmi-step:       transparent;
  --gmi-elev:       0 1px 2px rgba(20,30,50,.06), 0 8px 24px -16px rgba(20,32,64,.22);
  --gmi-select:     0 0 0 2px var(--link);
  --gmi-hero-wash:  none;
  --gmi-glow-held:  0 0 0 3px color-mix(in srgb, var(--ink-info) 14%, transparent);
}
@media (max-width:640px){ :root{ --gmi-cell:10px; --gmi-cell-gap:3px; } }
```

**Specimen primitives (G-DS1).** Section A copies `--sp-1…8` (4/8/12/16/20/24/32/44),
`--r-ctl 8 / --r-btn 10 / --r-card 12 / --r-panel 14 / --r-pill 999`, `--t-fast/med/slow` and `--ease-std/lift`,
plus `.mx-sec`, `.mx-tabset`, `.mx-empty`, `.skel` and `.mx-disc`, verbatim from `mockups/design_system/specimen.html`.
`--r-ctl` and `--r-card` appear in theme.css only inside a comment and as `var()` fallbacks, so section A re-declares
nothing that is shipped. Promote section A into theme.css once. Do not copy it into a page stylesheet.

## 6. Survey marks — shape carries meaning, hue only reinforces

| Mark | Class | Meaning (EN / ZH) | Drawing |
|---|---|---|---|
| ■ | `.gmi-sm--adm` | Admitted / 已纳入 | solid `--gmi-mark` |
| ◉ | `.gmi-sm--held` | Held for review / 待审核 | 2px info ring + centre dot + `--gmi-glow-held` |
| ▨ | `.gmi-sm--acc` | Core (frozen 68) / 核心 | 135° hatch inside a faint 1px border |
| ⬚ | `.gmi-sm--disp` | Extended (303, display tier) / 扩展 | 1px dashed faint border |
| □ | `.gmi-sm--none` | not mapped | 1px hairline |

Section D of `gmi_explorer.css`, verbatim:

```css
/* ---------- D. survey marks: shape carries meaning, hue only reinforces --------- */
.gmi-sm{ display:inline-block; flex:none; width:var(--gmi-cell); height:var(--gmi-cell);
  border-radius:2px; position:relative; vertical-align:-2px; }
.gmi-sm--adm { background:var(--gmi-mark); }
.gmi-sm--held{ border:2px solid var(--gmi-held);
  background:radial-gradient(circle, var(--gmi-held) 0 22%, transparent 27%); box-shadow:var(--gmi-glow-held); }
.gmi-sm--acc { border:1px solid var(--gmi-mark-faint);
  background:repeating-linear-gradient(135deg, var(--gmi-hatch) 0 1.4px, transparent 1.4px 3.6px); }
.gmi-sm--disp{ border:1px dashed var(--gmi-mark-faint); }
.gmi-sm--none{ border:1px solid var(--gmi-hair); }
.gmi-key .gmi-sm, .gmi-tally .gmi-sm, .gmi-inline .gmi-sm{ --gmi-cell:12px; }
.gmi-sm--xl{ --gmi-cell:20px; border-radius:3px; }
.gmi-key{ display:flex; flex-wrap:wrap; gap:var(--sp-2) var(--sp-5); font-size:var(--fs-sm); color:var(--muted); }
.gmi-key span{ display:inline-flex; align-items:center; gap:7px; }
```

Today's real distribution is 0 admitted, 1 held (Micron's proposed `theme:hbm_packaging` link), 68 Core (67 EMPTY
plus 1 PROPOSED_ONLY) and 303 Extended. The S2 census sheet therefore shows **one** held mark among 371 cells. That is
the honest picture and the design's bold move: a surveyed ground with one flag on it, not a heat map.

## 7. Tier-1 budgets (doctrine: h1 ≤ 4 words, sub-line ≤ 14 words)

| Page | h1 EN / ZH | Sub-line EN | Words |
|---|---|---|---|
| s1_issuer | Micron Technology / 美光科技 | One proposed theme link, not yet a member. | 8 |
| s2_theme_map | Theme map / 主题地图 | 371 micro-themes mapped. None has an admitted company yet. | 9 |
| s2_index | All micro-themes / 全部细分主题 | Every one of the 371, grouped by category. | 8 |
| s3_relationships | Documented relationships / 已记录的关系 | Links a company names in its own filings. One documented so far. | 12 |
| s4_coverage | Coverage & receipts / 覆盖率与凭证 | No company is admitted to a theme yet. Here is why. | 11 |
| s5_states | Data states / 数据状态 | How each surface reads when data is late, missing or held. | 11 |

Each page has exactly one `<h1>`. The ZH h1 strings are in the copy deck (§12).

## 8. Density budgets

- **Fold:** chrome + answer + at most 2 modules (table in §3). Detail sits below the fold or one tap away (Tier-2 tip, details row).
- **One integer per population, one as-of per panel.** S4 prints a single `0` for admitted companies. Each panel
  carries one as-of line. Duplicate dates are not printed per row.
- **Tables and lists:** at most 8 rows, then **"See all N"**. The S2 tree is an accordion: 10 category rows, one
  category open to its themes, and one theme open to its sub-themes and micro-themes. Empty sub-themes collapse into
  one summary row that names them. The tree ends with "See all 371 in the index" / "在索引中查看全部 371 个".
- **371 leaves on a phone:** the census sheet draws all 371 cells at `--gmi-cell` 14px with a 5px gap (1440), and
  10px with a 3px gap at ≤ 640px, where each category band stacks its label above its cells. The **index** is the
  complete list: 10 `<details>` groups and 371 rows. Names wrap and never truncate, and the hash `#open=all` opens every group.
  Proof: `png/s2_index_all371_*_390.png`, four cells.
- **Tree rows** truncate to one line at 1440 and clamp to two lines at ≤ 640px. **Index names** wrap, so a name is
  always readable in full somewhere.
- **Tips:** at most 80 words, `data-tip-en` / `data-tip-zh` on `.lens-q.gmi-tip` buttons. The button's visible
  label is `?` and its accessible name ("More detail" / "更多说明") is in a `.gmi-vh` span.
- **Targets:** at least 40px for every interactive control (doctrine §14).

## 9. Breakpoints (doctrine §15: 900 / 760 / 640, 390 floor, no horizontal scroll)

| Width | Change |
|---|---|
| ≤ 900 | `.gmi-cols` / `.gmi-row` stack into one column; `.gmi-relgrid` becomes a single column; the tally line wraps |
| ≤ 760 | `.gmi-head` stacks (title over side meta); the S1 lineage ladder and S3 paths stack vertically |
| ≤ 640 | `--gmi-cell` 10px / gap 3px; wrap padding 16px; h1 24px; panels padded `--sp-4`; tree names clamp to 2 lines; the index jump-nav hides; magnitude numbers drop one size |
| 390 | floor: every page has scrollWidth 390 in EN and ZH (§14 audit) |

Section M of `gmi_explorer.css`, verbatim:

```css
/* ---------- M. responsive floor ------------------------------------------------ */
@media (max-width:760px){
  .gmi-head{ flex-direction:column; align-items:flex-start; gap:var(--sp-3); }
  .gmi-head-side{ align-items:flex-start; flex-direction:row; flex-wrap:wrap; }
}
@media (max-width:640px){
  .gmi-wrap{ padding:0 16px 48px; gap:var(--sp-5); }
  .gmi-head{ padding:var(--sp-5) 0 var(--sp-4); }
  .gmi-h1{ font-size:24px; }
  .gmi-band, .gmi-panel, .gmi-state{ padding:var(--sp-4); }
  .gmi-dl dt{ flex-basis:104px; }
  .gmi-mag-num{ font-size:var(--fs-num-lg); }
  .gmi-big0 .gmi-mag-num{ font-size:var(--fs-num-xl); }
  .gmi-relgrid .gmi-mag-num{ font-size:var(--fs-num-xl); } .gmi-relgrid .gmi-mag-cap{ max-width:none; }
}
/* reference-only: specimen shows the nav without its dropdown menus */
.gmi-page .nav-dd-menu{ display:none !important; }
```

**Lens state.** `html[data-gmi-lens]` is read from the URL hash `#theme=&lang=&lens=` (`coverage` | `chain`), and
`.gmi-census--coverage` / `.gmi-census--chain` toggle on it. The lens buttons use `aria-selected`. The jump-nav
`#id` links in the index would clobber this hash state. That is a GAP: the implementation should use
`scrollIntoView` and keep the hash.

**ZH typography (doctrine §13).** ZH has no uppercase and no tracking on crumbs, tally caps, index titles, rung
levels or facet headers (`html[data-lang="zh"] … { letter-spacing:0; text-transform:none }`). ZH steps up to
`--fs-sm` where EN uses `--fs-label` caps.

## 10. State matrix (S5)

Every degraded state says **what failed + what still works + one action**. The dark and light treatments are the
ones in §4. Specimen keys (`gmi-state-k`) are reference-only: no contract emits them yet (GAP).

| Key | EN title | ZH title | Action | Dark | Light |
|---|---|---|---|---|---|
| `fetch_failed` | Couldn’t load the theme map | 主题地图加载失败 | Retry · Open index | card on panel, inset elev | white card, soft shadow |
| `stale` | Showing the 19 Oct read | 显示10月19日的读取结果 | — (the read stays usable) | last read under a veil (`.gmi-degraded`) | muted ink + hatched 6px band |
| `rights_withheld` | Size withheld | 规模暂不显示 | Open the filing | card | card |
| `purpose_denied` | Limited to research use | 仅限研究用途 | Open the theme map | card | card |
| `source_paused` | Paused: source check failed | 已暂停：来源校验未通过 | Show last verified read · 21 Oct 2026 | veil fallback | hatched fallback |
| `unknown` | Not disclosed · Not set yet | 未披露 · 尚未设定 | — | ink only | ink only |
| `loading` | Loading | 加载中 | — | `.skel` luminance shimmer | `.skel` panel2 grey |
| `empty` | No documented relationships yet | 尚无已记录的关系 | Open the company | `.mx-empty` | `.mx-empty` |
| `read_updated` | Read updated | 读取已更新 | See what changed | chip, link ring | chip, white + line |
| `path_template` | Conditioned path · layout only | 附条件路径 · 仅版式 | — | dashed path nodes | white path nodes + hairline |

`read_updated` is the front-facing form of correction lineage. A correction never shows as "refuted" or
"falsified". The chip opens the corrections log on S4. `unknown` prints "Not disclosed" for a magnitude that is
null at the source and "Not set yet" for a field the contract does not carry yet. Neither is ever printed as zero.

## 11. Exact markup

The full markup is in the six specimen pages, one per surface; the implementation ports their class structure
verbatim. Below are the canonical blocks, extracted by `outer-HTML-by-class` from the specimens and trimmed only where marked.


##### Tier-1 head (all pages) — `s1_issuer.html`, first `.gmi-head`

```html
<header class="gmi-head">
  <div class="gmi-head-main">
    <nav class="gmi-crumb" aria-label="Breadcrumb"><span class="l-en">Research</span><span class="l-zh">研究</span><i aria-hidden="true">›</i><span class="l-en">Companies</span><span class="l-zh">公司</span></nav>
    <div class="gmi-ident" style="margin-bottom:6px"><span class="gmi-ticker">MU · Nasdaq</span></div><h1 class="gmi-h1"><span class="l-en">Micron Technology</span><span class="l-zh">美光科技</span></h1>
    <p class="gmi-sub"><span class="l-en">One proposed theme link, not yet a member.</span><span class="l-zh">一个拟议主题关联，尚未成为成员。</span></p>
  </div>
  <div class="gmi-head-side"><span class="gmi-asof"><span class="l-en">Read as of 21 Oct 2026</span><span class="l-zh">数据截至2026年10月21日</span></span><span class="gmi-chip gmi-chip--ghost"><span class="l-en">Update history not tracked yet</span><span class="l-zh">尚未跟踪更新记录</span></span></div>
</header>
```

##### S1 principal-activity answer — `s1_issuer.html`, first `.gmi-answer`

```html
<p class="gmi-answer"><span class="l-en">Proposed, not a member. Not used on the map or in any count until a curator reviews it.</span><span class="l-zh">拟议关联，尚非成员。审核员审核前，不会用于主题地图或任何统计。</span></p>
```

##### S1 facet (labelled fact; unset = ink) — `s1_issuer.html`, first `.gmi-facet`

```html
<div class="gmi-facet"><div class="gmi-facet-h"><span class="l-en">Principal activity</span><span class="l-zh">主营业务</span></div>
<div class="gmi-facet-v gmi-facet-v--unset"><span class="l-en">Not set yet</span><span class="l-zh">尚未设定</span></div>
<p class="gmi-note"><span class="l-en">No reviewed description of Micron’s main business is on file. It will appear here, with its source, once reviewed.</span><span class="l-zh">目前没有经审核的美光科技主营业务描述。审核后将连同来源显示于此。</span></p></div>
```

##### S1 lineage ladder (micro → sub-theme → theme → category) — `s1_issuer.html`, first `.gmi-lineage`

```html
<div class="gmi-lineage"><div class="gmi-rung gmi-rung--held"><span class="gmi-rung-lvl"><span class="l-en">Micro-theme</span><span class="l-zh">细分主题</span></span><span class="gmi-rung-name"><span class="l-en">HBM &amp; advanced packaging</span><span class="l-zh">HBM 与先进封装</span></span><span class="gmi-rung-note"><span class="l-en">Proposed link · held</span><span class="l-zh">拟议关联 · 待审核</span></span></div><div class="gmi-link"><svg …icon…/></div><div class="gmi-rung gmi-rung--void"><span class="gmi-rung-lvl"><span class="l-en">Sub-theme</span><span class="l-zh">子主题</span></span><span class="gmi-rung-name"><span class="l-en">None — sits directly under its theme</span><span class="l-zh">无 —— 直接隶属于主题</span></span></div><div class="gmi-link"><svg …icon…/></div><div class="gmi-rung"><span class="gmi-rung-lvl"><span class="l-en">Theme</span><span class="l-zh">主题</span></span><span class="gmi-rung-name"><span class="l-en">AI Semiconductors</span><span class="l-zh">AI半导体</span></span><span class="gmi-rung-note"><span class="l-en">Also listed under Memory, HBM &amp; Storage</span><span class="l-zh">亦列于：存储与HBM</span></span></div><div class="gmi-link"><svg …icon…/></div><div class="gmi-rung"><span class="gmi-rung-lvl"><span class="l-en">Category</span><span class="l-zh">类别</span></span><span class="gmi-rung-name"><span class="l-en">Semiconductors & hardware</span><span class="l-zh">半导体与硬件</span></span><span class="gmi-rung-note"><span class="l-en">Its theme also sits in Technology &amp; software</span><span class="l-zh">所属主题亦归入：科技与软件</span></span></div></div>
```

##### S2 census band (one category) — `s2_theme_map.html`, first `.gmi-cband`

```html
<div class="gmi-cband"><div class="gmi-cband-label"><span class="gmi-cband-name"><span class="l-en">Technology &amp; software</span><span class="l-zh">科技与软件</span></span><span class="gmi-cband-meta"><span class="l-en">61 · 4 core</span><span class="l-zh">61 · 核心 4</span></span></div><div class="gmi-cells"><span class="gmi-vh"><span class="l-en">61 micro-themes: 4 core, 57 extended, 0 held, 0 admitted</span><span class="l-zh">61个细分主题：核心4个，扩展57个，待审核0个，已纳入0个</span></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><i class="gmi-cells-sep" aria-hidden="true"></i><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidd
<!-- … truncated; full markup in s2_theme_map.html -->
```

##### S2 tree row — `s2_theme_map.html`, first `.gmi-trow`

```html
<div class="gmi-trow" role="treeitem" aria-level="1" aria-expanded="false" tabindex="0"><svg …icon…/><span class="gmi-trow-name"><span class="l-en">Technology &amp; software</span><span class="l-zh">科技与软件</span></span><span class="gmi-trow-strip" aria-hidden="true"><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--acc" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></spa
<!-- … truncated; full markup in s2_theme_map.html -->
```

##### S2 index row — `s2_index.html`, first `.gmi-irow`

```html
<div class="gmi-irow"><span class="gmi-sm gmi-sm--disp" aria-hidden="true"></span><span class="gmi-irow-name"><span class="l-en">2.5D/3D advanced packaging (AI logic)</span><span class="l-zh">2.5D/3D先进封装制造</span></span><span class="gmi-vh"><span class="l-en">Extended</span><span class="l-zh">扩展</span></span></div>
```

##### S3 relationship head — `s3_relationships.html`, first `.gmi-rel-head`

```html
<div class="gmi-rel-head" id="rel-h"><span class="gmi-party"><span class="l-en">Skyworks</span><span class="l-zh">思佳讯</span></span>
<span class="gmi-arrow"><svg …icon…/><span class="l-en">supplies</span><span class="l-zh">供货</span></span><span class="gmi-party"><span class="l-en">Apple</span><span class="l-zh">苹果</span></span>
<span class="gmi-kind">· <span class="l-en">Supplier → customer</span><span class="l-zh">供应商 → 客户</span></span></div>
```

##### S3 magnitude (unknown when null) — `s3_relationships.html`, first `.gmi-mag`

```html
<div class="gmi-mag"><div><div class="gmi-mag-num">67<small>%</small></div>
<div class="gmi-mag-cap"><span class="l-en">of Skyworks’ revenue came from Apple in FY2025</span><span class="l-zh">思佳讯2025财年营收来自苹果的占比</span></div></div>
<div class="gmi-hist" aria-hidden="true"><div class="gmi-hist-col"><span class="gmi-hist-v">58%</span><span class="gmi-hist-bar" style="height:52px"></span><span class="gmi-hist-p"><span class="l-en">FY22</span><span class="l-zh">2022财年</span></span></div><div class="gmi-hist-col"><span class="gmi-hist-v">66%</span><span class="gmi-hist-bar" style="height:59px"></span><span class="gmi-hist-p"><span class="l-en">FY23</span><span class="l-zh">2023财年</span></span></div><div class="gmi-hist-col"><span class="gmi-hist-v">69%</span><span class="gmi-hist-bar" style="height:62px"></span><span class="gmi-hist-p"><span class="l-en">FY24</span><span class="l-zh">2024财年</span></span></div><div class="gmi-hist-col gmi-hist-col--now"><span class="gmi-hist-v">67%</span><span class="gmi-hist-bar" style="height:60px"></span><span class="gmi-hist-p"><span class="l-en">FY25</span><span class="l-zh">2025财年</span></span></div></div></div>
```

##### S3 conditional path (layout only) — `s3_relationships.html`, first `.gmi-path`

```html
<div class="gmi-path"><div class="gmi-pnode"><b><span class="l-en">Skyworks</span><span class="l-zh">思佳讯</span></b><small><span class="l-en">Supplier</span><span class="l-zh">供应商</span></small></div>
<div class="gmi-pedge"><span class="gmi-pedge-line"></span><span class="gmi-pedge-lab"><span class="l-en">supplies · no condition stated</span><span class="l-zh">供货 · 未列明条件</span></span></div>
<div class="gmi-pnode"><b><span class="l-en">Apple</span><span class="l-zh">苹果</span></b><small><span class="l-en">Customer</span><span class="l-zh">客户</span></small></div>
<div class="gmi-pedge gmi-pedge--void"><span class="gmi-pedge-line"></span><span class="gmi-pedge-lab"><span class="l-en">next step</span><span class="l-zh">下一步</span></span></div>
<div class="gmi-pnode gmi-pnode--void"><b><span class="l-en">No documented links from Apple yet</span><span class="l-zh">尚无苹果的已记录关联</span></b></div></div>
```

##### S4 coverage row (numerator / frozen denominator) — `s4_coverage.html`, first `.gmi-cov-row`

```html
<div class="gmi-cov-row"><div class="gmi-cov-top"><span class="gmi-cov-mkt"><span class="l-en">US</span><span class="l-zh">美国</span></span>
<span class="gmi-cov-num">0</span><span class="gmi-cov-den"><span class="l-en">of 1,926–1,931 companies</span><span class="l-zh">/ 共 1,926–1,931 家公司</span></span><button class="lens-q gmi-tip" type="button" data-tip-en="The count is a range because 6 listed securities are not yet matched to a company." data-tip-zh="该数字为区间，因为有6只上市证券尚未匹配到对应公司。"><span aria-hidden="true">?</span><span class="gmi-vh"><span class="l-en">More detail</span><span class="l-zh">更多说明</span></span></button></div>
<div class="gmi-track"><span class="gmi-track-zero"></span></div>
<p class="gmi-note" style="margin-top:4px"><span class="l-en">Why none is admitted yet</span><span class="l-zh">尚无公司纳入的原因</span></p><div class="gmi-stack" aria-hidden="true"><i class="s1" style="flex:726 1 0"></i><i class="s2" style="flex:1201 1 0"></i><i class="s3" style="flex:4 1 0"></i></div><div class="gmi-legend"><span><i class="s1" style="display:inline-block"></i><b>726</b><span class="l-en">company identity not confirmed</span><span class="l-zh">公司身份尚未确认</span></span><span><i class="s2" style="display:inline-block"></i><b>1,201</b><span class="l-en">only on a third-party list</span><span class="l-zh">仅见于第三方名单</span></span><span><i class="s3" style="display:inline-block"></i><b>4</b><span class="l-en">no activity evidence</span><span class="l-zh">无业务活动证据</span></span></div></div>
```

##### S5 state card — `s5_states.html`, first `.gmi-state`

```html
<article class="gmi-state"><div class="gmi-state-h"><span class="gmi-ink-warn" style="display:flex"><svg …icon…/></span><span class="gmi-state-t"><span class="l-en">Couldn’t load the theme map</span><span class="l-zh">主题地图加载失败</span></span><span class="gmi-state-k">fetch_failed</span></div><p><span class="l-en">The latest read did not arrive.</span><span class="l-zh">最新一次读取未能送达。</span></p><p class="gmi-state-ok"><span class="l-en">Search and the full index still work from the last read (22 Oct 2026).</span><span class="l-zh">搜索与完整索引仍可使用上次读取结果（2026年10月22日）。</span></p><div class="gmi-state-a"><button class="gmi-btn" type="button"><svg …icon…/><span class="l-en">Retry</span><span class="l-zh">重试</span></button><a class="gmi-btn gmi-btn--quiet" href="s2_index.html"><span class="l-en">Open index</span><span class="l-zh">打开索引</span></a></div></article>
```

## 12. EN / ZH copy deck

This is every user-visible string per page, extracted from the specimens. `copy` is on-page text. `tip` is the
Tier-2 `data-tip-en` / `data-tip-zh` body. ZH is written natively; it is not a word-for-word translation. Scope
strings that name a contract stay in English (GAP). The relationship sentence on S3 comes from the frozen premise
deck `describe_premises_v1.json` and is used verbatim.

#### s1_issuer

| kind | EN | ZH |
|---|---|---|
| copy | Research | 研究 |
| copy | Companies | 公司 |
| copy | Micron Technology | 美光科技 |
| copy | One proposed theme link, not yet a member. | 一个拟议主题关联，尚未成为成员。 |
| copy | Read as of 21 Oct 2026 | 数据截至2026年10月21日 |
| copy | Update history not tracked yet | 尚未跟踪更新记录 |
| copy | Held for review | 待审核 |
| copy | More detail | 更多说明 |
| copy | Proposed, not a member. Not used on the map or in any count until a curator reviews it. | 拟议关联，尚非成员。审核员审核前，不会用于主题地图或任何统计。 |
| copy | Where it would sit | 拟归属位置 |
| copy | Micro-theme | 细分主题 |
| copy | Proposed link · held | 拟议关联 · 待审核 |
| copy | Sub-theme | 子主题 |
| copy | None — sits directly under its theme | 无 —— 直接隶属于主题 |
| copy | Theme | 主题 |
| copy | Also listed under Memory, HBM & Storage | 亦列于：存储与HBM |
| copy | Category | 类别 |
| copy | Its theme also sits in Technology & software | 所属主题亦归入：科技与软件 |
| copy | What Micron does | 美光科技的业务 |
| copy | Principal activity | 主营业务 |
| copy | Not set yet | 尚未设定 |
| copy | No reviewed description of Micron’s main business is on file. It will appear here, with its source, once reviewed. | 目前没有经审核的美光科技主营业务描述。审核后将连同来源显示于此。 |
| copy | Value-chain position | 价值链位置 |
| copy | Upstream | 上游 |
| copy | Midstream | 中游 |
| copy | Downstream | 下游 |
| copy | Enabler | 赋能 |
| copy | Not recorded for HBM & advanced packaging yet. | HBM与先进封装的价值链位置尚未记录。 |
| copy | Why it was proposed | 提议依据 |
| copy | Source | 来源 |
| copy | Micron press release | 美光科技新闻稿 |
| copy | 26 Feb 2024 | 2024年2月26日 |
| copy | Product | 产品 |
| copy | Platform | 平台 |
| copy | Customer named | 所提及客户 |
| copy | NVIDIA | 英伟达 |
| copy | Stage | 阶段 |
| copy | Planned | 计划中 |
| copy | On file since | 收录日期 |
| copy | 11 Oct 2026 | 2026年10月11日 |
| copy | Receipt | 凭证 |
| copy | proposal record, dates, permissions | 提议记录、日期、权限 |
| copy | Nothing here is inferred beyond the cited text. | 以上内容均来自引文，未作推断。 |
| copy | What we don’t know yet | 尚不清楚的信息 |
| copy | Whether Micron belongs here | 美光科技是否属于该主题 |
| copy | Awaiting review | 待审核 |
| copy | Deal size | 规模 |
| copy | Not in the source | 来源未披露 |
| copy | Start date | 开始日期 |
| copy | Business segment | 业务分部 |
| copy | Documented relationships | 已记录的关系 |
| copy | None documented for Micron yet. | 美光科技暂无已记录的关系。 |
| copy | See documented relationships | 查看已记录的关系 |
| tip | A proposed link waiting for a curator. Held links are not members and are left out of every count. | 等待审核员处理的拟议关联。待审核关联不是成员，不计入任何统计。 |

#### s2_theme_map

| kind | EN | ZH |
|---|---|---|
| copy | Research | 研究 |
| copy | Theme map | 主题地图 |
| copy | 371 micro-themes mapped. None has an admitted company yet. | 已绘制 371 个细分主题，尚无公司获准纳入。 |
| copy | Read as of 22 Oct 2026 | 数据截至2026年10月22日 |
| copy | micro-themes mapped | 个细分主题已绘制 |
| copy | Made up of | 构成 |
| copy | Core set | 核心集 |
| copy | More detail | 更多说明 |
| copy | Extended · not counted | 扩展 · 不计入 |
| copy | Core set so far | 核心集进展 |
| copy | Admitted | 已纳入 |
| copy | Held for review | 待审核 |
| copy | Every micro-theme, by category | 按类别列出全部细分主题 |
| copy | Every micro-theme, by value-chain position | 按价值链位置列出全部细分主题 |
| copy | Review status | 审核状态 |
| copy | Value chain | 价值链 |
| copy | 61 · 4 core | 61 · 核心 4 |
| copy | 61 micro-themes: 4 core, 57 extended, 0 held, 0 admitted | 61个细分主题：核心4个，扩展57个，待审核0个，已纳入0个 |
| copy | 43 · 10 core | 43 · 核心 10 |
| copy | 43 micro-themes: 9 core, 33 extended, 1 held, 0 admitted | 43个细分主题：核心9个，扩展33个，待审核1个，已纳入0个 |
| copy | 64 · 12 core | 64 · 核心 12 |
| copy | 64 micro-themes: 12 core, 52 extended, 0 held, 0 admitted | 64个细分主题：核心12个，扩展52个，待审核0个，已纳入0个 |
| copy | 50 · 7 core | 50 · 核心 7 |
| copy | 50 micro-themes: 7 core, 43 extended, 0 held, 0 admitted | 50个细分主题：核心7个，扩展43个，待审核0个，已纳入0个 |
| copy | 78 · 21 core | 78 · 核心 21 |
| copy | 78 micro-themes: 21 core, 57 extended, 0 held, 0 admitted | 78个细分主题：核心21个，扩展57个，待审核0个，已纳入0个 |
| copy | 56 · 14 core | 56 · 核心 14 |
| copy | 56 micro-themes: 14 core, 42 extended, 0 held, 0 admitted | 56个细分主题：核心14个，扩展42个，待审核0个，已纳入0个 |
| copy | 19 · 0 core | 19 · 核心 0 |
| copy | 19 micro-themes: 0 core, 19 extended, 0 held, 0 admitted | 19个细分主题：核心0个，扩展19个，待审核0个，已纳入0个 |
| copy | No micro-themes mapped yet | 尚未绘制细分主题 |
| copy | Upstream | 上游 |
| copy | 55 | 55 |
| copy | 55 micro-themes: 0 core, 55 extended, 0 held, 0 admitted | 55个细分主题：核心0个，扩展55个，待审核0个，已纳入0个 |
| copy | Midstream | 中游 |
| copy | 127 | 127 |
| copy | 127 micro-themes: 0 core, 127 extended, 0 held, 0 admitted | 127个细分主题：核心0个，扩展127个，待审核0个，已纳入0个 |
| copy | Downstream | 下游 |
| copy | 78 | 78 |
| copy | 78 micro-themes: 0 core, 78 extended, 0 held, 0 admitted | 78个细分主题：核心0个，扩展78个，待审核0个，已纳入0个 |
| copy | Enabler | 赋能 |
| copy | 43 | 43 |
| copy | 43 micro-themes: 0 core, 43 extended, 0 held, 0 admitted | 43个细分主题：核心0个，扩展43个，待审核0个，已纳入0个 |
| copy | Not set yet | 尚未设定 |
| copy | 68 | 68 |
| copy | 68 micro-themes: 67 core, 0 extended, 1 held, 0 admitted | 68个细分主题：核心67个，扩展0个，待审核1个，已纳入0个 |
| copy | Value-chain position is recorded for the extended set only. The core set’s positions are not recorded yet. | 仅扩展集记录了价值链位置；核心集的位置尚未记录。 |
| copy | Each square is one micro-theme. Shape carries meaning; colour only repeats it. | 每个方块代表一个细分主题。含义由形状表达，颜色仅作重复提示。 |
| copy | Browse the tree | 浏览主题树 |
| copy | Search 371 micro-themes | 搜索 371 个细分主题 |
| copy | Held | 待审核 |
| copy | Core | 核心 |
| copy | 4 sub-themes have no micro-themes yet | 4个子主题尚无细分主题 |
| copy | None yet | 暂无 |
| copy | See all 371 in the index | 在索引中查看全部 371 个 |
| copy | Micron → HBM & advanced packaging | 美光科技 → HBM 与先进封装 |
| copy | Proposed, not a member. Not counted until reviewed. | 拟议关联，尚非成员。审核前不计入统计。 |
| copy | Open Micron | 查看美光科技 |
| copy | Two kinds of micro-theme | 两类细分主题 |
| copy | Core set — the original set. Coverage is measured here. | 核心集 —— 最初的集合，覆盖率在此衡量。 |
| copy | Extended — added 21 Oct 2026 for orientation. Not counted in coverage. | 扩展 —— 2026年10月21日新增，用于浏览，不计入覆盖率。 |
| copy | How coverage is measured | 覆盖率如何衡量 |
| tip | The original 68 micro-themes. Coverage and accuracy are measured on this set only. | 最初的68个细分主题。覆盖率与准确性仅在此集合上衡量。 |
| tip | 303 micro-themes added on 21 Oct 2026 to help you find your way around. They are shown but not counted in coverage. | 2026年10月21日新增的303个细分主题，用于帮助浏览。予以显示，但不计入覆盖率。 |
| tip | A company joins a micro-theme only after a curator admits it from its own filings. None has been admitted yet. | 公司须经审核员依据其自身申报文件批准后才纳入细分主题。目前尚无公司获准纳入。 |
| tip | A proposed link waiting for a curator. Held links are not members and are left out of every count. | 等待审核员处理的拟议关联。待审核关联不是成员，不计入任何统计。 |
| tip | Not mapped yet: AI Semiconductor Design Chain, Advanced Packaging & Integration, Semiconductor Process Materials, AI Network Fabric. | 尚未绘制：AI芯片设计链、先进封装与集成、半导体工艺材料、AI 网络互连。 |

#### s2_index

| kind | EN | ZH |
|---|---|---|
| copy | Research | 研究 |
| copy | Theme map | 主题地图 |
| copy | Index | 索引 |
| copy | All micro-themes | 全部细分主题 |
| copy | Every one of the 371, grouped by category. | 全部 371 个，按类别分组。 |
| copy | Read as of 22 Oct 2026 | 数据截至2026年10月22日 |
| copy | Search 371 micro-themes | 搜索 371 个细分主题 |
| copy | Core set | 核心集 |
| copy | Extended · not counted | 扩展 · 不计入 |
| copy | Admitted | 已纳入 |
| copy | Held for review | 待审核 |
| copy | 4 core · 57 extended | 核心 4 · 扩展 57 |
| copy | Extended | 扩展 |
| copy | Core | 核心 |
| copy | 10 core · 33 extended | 核心 10 · 扩展 33 |
| copy | Held | 待审核 |
| copy | 12 core · 52 extended | 核心 12 · 扩展 52 |
| copy | 7 core · 43 extended | 核心 7 · 扩展 43 |
| copy | 21 core · 57 extended | 核心 21 · 扩展 57 |
| copy | 14 core · 42 extended | 核心 14 · 扩展 42 |
| copy | 0 core · 19 extended | 核心 0 · 扩展 19 |
| copy | none yet | 暂无 |
| copy | No micro-themes mapped yet | 尚未绘制细分主题 |
| copy | 371 rows: 68 core, 303 extended. Held and admitted links are marked on their row. | 共 371 行：核心 68 个，扩展 303 个。待审核与已纳入的关联在所在行标注。 |

#### s3_relationships

| kind | EN | ZH |
|---|---|---|
| copy | Research | 研究 |
| copy | Relationships | 关系 |
| copy | Documented relationships | 已记录的关系 |
| copy | Links a company names in its own filings. One documented so far. | 公司在自身申报文件中写明的关联。目前已记录一条。 |
| copy | Read as of 21 Oct 2026 | 数据截至2026年10月21日 |
| copy | Supplier → customer | 供应商 → 客户 |
| copy | Contract manufacturing (foundry, CDMO) | 代工制造（晶圆代工、CDMO） |
| copy | Licensing | 授权许可 |
| copy | Distribution | 分销 |
| copy | Component dependency | 零部件依赖 |
| copy | Zero means none documented yet, not none exist. | 为零表示尚未记录，而非不存在。 |
| copy | Skyworks | 思佳讯 |
| copy | supplies | 供货 |
| copy | Apple | 苹果 |
| copy | Proposed · not reviewed yet | 拟议 · 尚未审核 |
| copy | Read updated · 30 Jan 2026 | 读取已更新 · 2026年1月30日 |
| copy | of Skyworks’ revenue came from Apple in FY2025 | 思佳讯2025财年营收来自苹果的占比 |
| copy | FY22 | 2022财年 |
| copy | FY23 | 2023财年 |
| copy | FY24 | 2024财年 |
| copy | FY25 | 2025财年 |
| copy | Skyworks disclosed that net revenue from Apple in aggregate, through distributors, contract manufacturers and direct sales was 67% of Skyworks consolidated net revenue for FY2025. | 思佳讯披露，2025财年期间net revenue from Apple in aggregate, through distributors, contract manufacturers and direct sales占Skyworks consolidated net revenue的67%。 |
| copy | Direction | 方向 |
| copy | Skyworks supplies Apple | 思佳讯向苹果供货 |
| copy | Period covered | 覆盖期间 |
| copy | Oct 2021 – Oct 2025 | 2021年10月 – 2025年10月 |
| copy | Conditions | 条件 |
| copy | None stated in the filing | 申报文件未列明条件 |
| copy | First known | 首次获知 |
| copy | 15 Nov 2024 | 2024年11月15日 |
| copy | Last stated | 最近一次陈述 |
| copy | 7 Nov 2025 | 2025年11月7日 |
| copy | Last checked | 最近核对 |
| copy | 30 Jan 2026 | 2026年1月30日 |
| copy | Source | 来源 |
| copy | The filing’s words | 申报文件原文 |
| copy | How this figure was read over time | 该数值的历次读取 |
| copy | As known at 30 Jan 2026: | 截至2026年1月30日已知： |
| copy | Skyworks first published 69% for FY2024 in 10-K 0000004127-24-000131 (known 15 Nov 2024). | 思佳讯在10-K 0000004127-24-000131 |
| copy | The next publication, 10-K 0000004127-25-000085 (known 7 Nov 2025), repeated the same value 69%. | 下一份申报文件10-K 0000004127-25-000085 |
| copy | Skyworks first published 67% for FY2025 in 10-K 0000004127-25-000085 (known 7 Nov 2025). | 思佳讯在10-K 0000004127-25-000085 |
| copy | 0000004127-26-000003 amends 0000004127-25-000085; it does not restate this figure (Part III only amendment). | 0000004127-26-000003 |
| copy | Where this link leads | 关联路径 |
| copy | Supplier | 供应商 |
| copy | supplies · no condition stated | 供货 · 未列明条件 |
| copy | Customer | 客户 |
| copy | next step | 下一步 |
| copy | No documented links from Apple yet | 尚无苹果的已记录关联 |
| copy | Paths list documented links only. They do not estimate how far an effect spreads. | 路径仅列出已记录的关联，不估算影响的传导范围。 |
| copy | Held for review | 待审核 |
| copy | More detail | 更多说明 |
| copy | Micron → HBM & advanced packaging | 美光科技 → HBM 与先进封装 |
| copy | A proposed theme link, not a member. Not shown on the map. | 拟议主题关联，尚非成员，不在主题地图上显示。 |
| copy | Named customer | 所提及客户 |
| copy | NVIDIA · H200 platform | 英伟达 · H200 平台 |
| copy | Stage | 阶段 |
| copy | Planned | 计划中 |
| copy | Size | 规模 |
| copy | Not disclosed | 未披露 |
| copy | Use on the map | 用于主题地图 |
| copy | Not permitted yet | 暂不允许 |
| copy | Open Micron | 查看美光科技 |
| copy | How complete is this? | 覆盖程度 |
| copy | Not measured yet | 尚未衡量 |
| copy | Filings from one company have been read so far. Zero elsewhere means none documented yet, not none exist. | 目前仅读取了一家公司的申报文件。其他处为零，表示尚未记录，而非不存在。 |
| tip | A proposed link waiting for a curator. Held links are not members and are left out of every count. | 等待审核员处理的拟议关联。待审核关联不是成员，不计入任何统计。 |

#### s4_coverage

| kind | EN | ZH |
|---|---|---|
| copy | Research | 研究 |
| copy | Coverage | 覆盖率 |
| copy | Coverage & receipts | 覆盖率与凭证 |
| copy | No company is admitted to a theme yet. Here is why. | 尚无公司获准纳入任何主题。原因如下。 |
| copy | Read as of 22 Oct 2026 | 数据截至2026年10月22日 |
| copy | companies admitted to any theme | 家公司获准纳入任何主题 |
| copy | More detail | 更多说明 |
| copy | US | 美国 |
| copy | of 1,926–1,931 companies | / 共 1,926–1,931 家公司 |
| copy | Why none is admitted yet | 尚无公司纳入的原因 |
| copy | company identity not confirmed | 公司身份尚未确认 |
| copy | only on a third-party list | 仅见于第三方名单 |
| copy | no activity evidence | 无业务活动证据 |
| copy | China | 中国 |
| copy | of 1–1,019 companies | / 共 1–1,019 家公司 |
| copy | What is measured | 衡量范围 |
| copy | core micro-themes | 个核心细分主题 |
| copy | 67 have no admitted company. 1 has a link held for review. | 67个尚无获准纳入的公司；1个有待审核的关联。 |
| copy | extended micro-themes are shown on the map but not counted. | 个扩展细分主题在地图上显示，但不计入。 |
| copy | Corrections log | 更正记录 |
| copy | 30 Jan 2026 | 2026年1月30日 |
| copy | Skyworks 10-K/A amends its 10-K. The Apple revenue share is unchanged. | 思佳讯10-K/A修订其10-K，来自苹果的营收占比未变。 |
| copy | Theme links | 主题关联 |
| copy | Changes are not tracked yet. | 变更尚未跟踪。 |
| copy | Accuracy check | 准确性抽查 |
| copy | Not measured yet | 尚未衡量 |
| copy | Needs 200 admitted links (100 US, 100 China) before a sample is drawn. Now 0. | 需要200条获准纳入的关联（美国100条、中国100条）后才会抽样。目前为0。 |
| copy | Sources: company filings; exchange symbol directory, 21 Oct 2026; review ledger, 22 Oct 2026. | 来源：公司申报文件；交易所证券代码目录（2026年10月21日）；审核记录（2026年10月22日）。 |
| tip | A company joins a micro-theme only after a curator admits it from its own filings. None has been admitted yet. | 公司须经审核员依据其自身申报文件批准后才纳入细分主题。目前尚无公司获准纳入。 |
| tip | The count is a range because 6 listed securities are not yet matched to a company. | 该数字为区间，因为有6只上市证券尚未匹配到对应公司。 |
| tip | The range is wide because none of the 1,019 listed securities is matched to a company yet. | 区间较宽，因为1,019只上市证券均尚未匹配到对应公司。 |
| tip | The original 68 micro-themes. Coverage and accuracy are measured on this set only. | 最初的68个细分主题。覆盖率与准确性仅在此集合上衡量。 |
| tip | 303 micro-themes added on 21 Oct 2026 to help you find your way around. They are shown but not counted in coverage. | 2026年10月21日新增的303个细分主题，用于帮助浏览。予以显示，但不计入覆盖率。 |

#### s5_states

| kind | EN | ZH |
|---|---|---|
| copy | Research | 研究 |
| copy | Theme map | 主题地图 |
| copy | Data states | 数据状态 |
| copy | How each surface reads when data is late, missing or held. | 数据延迟、缺失或暂缓时，各页面如何呈现。 |
| copy | Read as of 22 Oct 2026 | 数据截至2026年10月22日 |
| copy | Every state says what failed, what still works, and one next step. Keys in the corner are for builders and are not shown in the product. | 每种状态都说明：哪里失败、哪些仍可用、下一步做什么。右上角的键名供开发参考，不在产品中显示。 |
| copy | Couldn’t load the theme map | 主题地图加载失败 |
| copy | The latest read did not arrive. | 最新一次读取未能送达。 |
| copy | Search and the full index still work from the last read (22 Oct 2026). | 搜索与完整索引仍可使用上次读取结果（2026年10月22日）。 |
| copy | Retry | 重试 |
| copy | Open index | 打开索引 |
| copy | Showing the 19 Oct read | 显示10月19日的读取结果 |
| copy | Read being updated | 读取结果更新中 |
| copy | Counts and links are as of 19 Oct 2026 until the new read lands. | 新读取结果送达前，计数与关联以2026年10月19日为准。 |
| copy | Size withheld | 规模暂不显示 |
| copy | Skyworks | 思佳讯 |
| copy | Apple | 苹果 |
| copy | Display rights for this figure are still being confirmed. The source filing is linked. | 该数值的展示权限仍在确认中。已附来源申报文件链接。 |
| copy | The relationship, its dates and the source stay visible. | 关系本身、日期与来源仍然可见。 |
| copy | Open the filing | 打开申报文件 |
| copy | Limited to research use | 仅限研究用途 |
| copy | This detail is limited to research use. | 此详情仅限研究用途。 |
| copy | The theme map and coverage still work. | 主题地图与覆盖率仍可使用。 |
| copy | Open the theme map | 打开主题地图 |
| copy | Paused: source check failed | 已暂停：来源校验未通过 |
| copy | A source file did not match its record, so this view is paused rather than shown wrong. | 某来源文件与其记录不一致，因此暂停显示，而不是显示错误内容。 |
| copy | Everything else on the page still works. | 页面其余部分仍可正常使用。 |
| copy | Show last verified read · 21 Oct 2026 | 显示上次核实的读取结果 · 2026年10月21日 |
| copy | Not disclosed · Not set yet | 未披露 · 尚未设定 |
| copy | Deal size | 规模 |
| copy | Not disclosed | 未披露 |
| copy | Value-chain position | 价值链位置 |
| copy | Not set yet | 尚未设定 |
| copy | “Not disclosed” means the company did not publish it. “Not set yet” means we have not recorded it. | “未披露”表示公司未公布；“尚未设定”表示我们尚未记录。 |
| copy | Loading | 加载中 |
| copy | The page frame and navigation are usable while rows load. | 行数据加载期间，页面框架与导航可正常使用。 |
| copy | No documented relationships yet | 尚无已记录的关系 |
| copy | Zero means none documented yet, not none exist. | 为零表示尚未记录，而非不存在。 |
| copy | The company’s themes and filings still show. | 该公司的主题与申报文件仍可查看。 |
| copy | Open the company | 打开公司页 |
| copy | Read updated | 读取已更新 |
| copy | Read updated · 30 Jan 2026 | 读取已更新 · 2026年1月30日 |
| copy | A later filing touched this figure. Open it to see what changed and what did not. | 后续申报文件涉及该数值。打开即可查看变更与未变更之处。 |
| copy | See what changed | 查看变更 |
| copy | Conditioned path · layout only | 附条件路径 · 仅版式 |
| copy | No documented conditioned path exists yet. This shows where a stated condition would sit. | 目前尚无已记录的附条件路径。此处仅示意所述条件的位置。 |
| copy | If Apple reduces or stops its purchases | 如果苹果减少或停止采购 |
| copy | Effect stated in the filing | 申报文件所述影响 |
| copy | quoted text appears here | 此处显示引文 |

## 13. Evidence matrix

**60 PNG references** in `png/`. Each is a full-page capture at device-pixel ratio 1, taken from the specimen at
`#theme=<t>&lang=<l>` and rendered against `templates/theme.css` at `9b48e798a3eb`.

| Surface | 1440 | 390 |
|---|---|---|
| S1 Issuer | `s1_issuer_dark_en_1440.png`<br>`s1_issuer_dark_zh_1440.png`<br>`s1_issuer_light_en_1440.png`<br>`s1_issuer_light_zh_1440.png` | `s1_issuer_dark_en_390.png`<br>`s1_issuer_dark_zh_390.png`<br>`s1_issuer_light_en_390.png`<br>`s1_issuer_light_zh_390.png` |
| S2 Theme map · coverage lens | `s2_theme_map_dark_en_1440.png`<br>`s2_theme_map_dark_zh_1440.png`<br>`s2_theme_map_light_en_1440.png`<br>`s2_theme_map_light_zh_1440.png` | `s2_theme_map_dark_en_390.png`<br>`s2_theme_map_dark_zh_390.png`<br>`s2_theme_map_light_en_390.png`<br>`s2_theme_map_light_zh_390.png` |
| S2 Theme map · value-chain lens | `s2_theme_map_chain_dark_en_1440.png`<br>`s2_theme_map_chain_dark_zh_1440.png`<br>`s2_theme_map_chain_light_en_1440.png`<br>`s2_theme_map_chain_light_zh_1440.png` | `s2_theme_map_chain_dark_en_390.png`<br>`s2_theme_map_chain_dark_zh_390.png`<br>`s2_theme_map_chain_light_en_390.png`<br>`s2_theme_map_chain_light_zh_390.png` |
| S2 Index | `s2_index_dark_en_1440.png`<br>`s2_index_dark_zh_1440.png`<br>`s2_index_light_en_1440.png`<br>`s2_index_light_zh_1440.png` | `s2_index_dark_en_390.png`<br>`s2_index_dark_zh_390.png`<br>`s2_index_light_en_390.png`<br>`s2_index_light_zh_390.png` |
| S3 Relationships | `s3_relationships_dark_en_1440.png`<br>`s3_relationships_dark_zh_1440.png`<br>`s3_relationships_light_en_1440.png`<br>`s3_relationships_light_zh_1440.png` | `s3_relationships_dark_en_390.png`<br>`s3_relationships_dark_zh_390.png`<br>`s3_relationships_light_en_390.png`<br>`s3_relationships_light_zh_390.png` |
| S4 Coverage & receipts | `s4_coverage_dark_en_1440.png`<br>`s4_coverage_dark_zh_1440.png`<br>`s4_coverage_light_en_1440.png`<br>`s4_coverage_light_zh_1440.png` | `s4_coverage_dark_en_390.png`<br>`s4_coverage_dark_zh_390.png`<br>`s4_coverage_light_en_390.png`<br>`s4_coverage_light_zh_390.png` |
| S5 States | `s5_states_dark_en_1440.png`<br>`s5_states_dark_zh_1440.png`<br>`s5_states_light_en_1440.png`<br>`s5_states_light_zh_1440.png` | `s5_states_dark_en_390.png`<br>`s5_states_dark_zh_390.png`<br>`s5_states_light_en_390.png`<br>`s5_states_light_zh_390.png` |
| S2 371-leaf proof | — | `s2_index_all371_dark_en_390.png`<br>`s2_index_all371_dark_zh_390.png`<br>`s2_index_all371_light_en_390.png`<br>`s2_index_all371_light_zh_390.png` |

The S2 value-chain lens cells are `s2_theme_map_chain_*`. The 371 proof cells are `s2_index_all371_{dark,light}_{en,zh}_390.png`:
the index with every group open, captured only after a DOM assertion that 371 `.gmi-irow-name` elements are visible inside the 390px viewport width.

**Paper file "GMI Explorer 2026-10-21"** has 16 boards on page 1, each reviewed by screenshot:

- a cover / brief
- S1 at 1440 and 390
- S2 coverage lens at 1440 and 390
- S2 value-chain lens at 1440 and 390
- S2 index at 1440 and 390
- S2 371-proof at 390
- S3 at 1440 and 390
- S4 at 1440 and 390
- S5 at 1440 and 390

Each S-board places four cells side by side: DARK·EN, DARK·ZH, LIGHT·EN and LIGHT·ZH. The boards hold the rendered
captures. The HTML specimens remain the exact implementation source (see DEVIATIONS in DESIGN_RECORD).

**Data provenance** (`inputs/fixture.json` → `provenance`):

| Input | Source |
|---|---|
| Theme hierarchy, 371 micros, Core/Extended tiers | crosswalk on main (merged #10017), generator `hier.json` |
| Activity proposal (Micron → `theme:hbm_packaging`, PROPOSED) | `data/theme_graph/probation/activity_proposals.jsonl` @ `64ef5131` |
| Coverage, US [1926, 1931] / CN [1, 1019], numerators 0 | `research/theme_graph/coverage_20261019/coverage_report.json` @ `64ef5131` |
| Disposition 68 = 67 EMPTY + 1 PROPOSED_ONLY | `scripts/gmi_coverage_proof.py` (record M3_MICRO_DISPOSITION_2026-10-22) |
| Precision sample EMPTY_POPULATION | record M3_PRECISION_SAMPLE (0 admitted; the floor is 200) |
| Relationship edge SWKS → AAPL + excerpt | `research/theme_graph/gmi_relationships_20261021/sources/0000004127-25-000085.json` @ `f955f52f` (#10005, read-only; not on main) |
| Relationship sentence / condition labels | `describe_premises_v1.json` (seat prereg, verbatim) |

## 14. Regenerate and verify

```bash
# from any cwd outside the repo (user site has playwright + PIL); -P keeps the cwd off sys.path
cd /tmp && python3 -P <repo>/mockups/refs/gmi_explorer/build_specimens.py
#  -> rewrites the six s*.html pages and png/ (60 files); prints 4 PROOF lines:
#     "PROOF s2_index_all371_<theme>_<lang>_390.png: 371 index rows rendered and visible at 390px"
#  -> asserts 371 micros / 68 Core / 303 Extended / 1 PROPOSED_ONLY / 0 admitted / US 1931 / CN 1019

# 390 overflow audit (each page × lang must print 390)
#   for each page: document.documentElement.scrollWidth at viewport 390×844, #theme=dark&lang={en,zh}
#   (clipped .gmi-vh screen-reader labels extend past 390 by design and do not scroll)

git diff --stat origin/main -- templates/   # must be empty: this folder edits no shipped template
```

## 15. Contract bindings and GAPs

Every field drawn without a published data contract is listed as a GAP in
`research/theme_graph/gmi_design_20261021/DESIGN_RECORD.md` §6. The implementation must bind each one to a real
contract or keep its plain-word unknown (§10). Three of them change the layout if they land:

- `value_chain_position` is absent on the frozen 68, so the value-chain lens draws every cell as "Not set yet".
- `principal_business_activity` has no rows, so S1's answer prints "Not set yet" under the principal-activity facet.
- There is no correction-lineage field. The `read_updated` chip and the S4 corrections log are drawn from the
  disposition record's history and need a contract before shipping.
