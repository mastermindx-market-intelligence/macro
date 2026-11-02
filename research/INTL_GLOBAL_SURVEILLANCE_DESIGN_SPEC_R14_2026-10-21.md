# International Markets Global Surveillance — Design Spec R14 (frozen for Wave 2 UI)

Status: FROZEN DESIGN SPEC, source-only. Nothing here is built, merged or live.
Date: 2026-10-21. Author: ORCH-D (design orchestrator) under Meta-CEO seat d7c4f490,
programme WS-INTL-GLOBAL-SURVEILLANCE. Masterplan: `research/INTL_GLOBAL_SURVEILLANCE_MASTERPLAN_2026-10-21.md` §13
("Paper design and engineering handoff") and packets IM13–IM18 (masterplan lines 777–808).

Readers: the GLM builders and reviewers for packets IM13–IM18. Read this file, then the PNG
references, before writing any template or CSS. Where this spec and a PNG disagree, **this spec wins**.
Where this spec and `docs/DESIGN_DOCTRINE.md` or `templates/theme.css` disagree, **the doctrine and
the production tokens win**. Treat the gap as a defect in this spec and record it.

## 0. Sources and identities

| Item | Value |
|---|---|
| Paper file | `01M3P1TW5Y3XWQC37ADDS8K5AG` "International Markets · R10 · Current Build" |
| R14 page (target, new) | "Global Surveillance · R14 · Masterpiece" (14 artboards) |
| R13 page (source, untouched) | "Global Surveillance · R13 · Expansion" |
| Paper token hash at freeze | `91ff7025` |
| PNG references | `/private/tmp/claude-501/-Volumes-Mastermind-2-agent-workspaces-claude-14851c4656838a3b-intl-markets-surveillance-masterplan-a50d55-3ceeeb10038460a2/d7c4f490-ba4d-4cb7-a762-aa2a2617f4a7/scratchpad/r14/` (scratchpad, NOT committed; the seat decides whether to copy into `mockups/refs/intl-gs-r14/`) |
| Production token source | `templates/theme.css` (dark root ≈ L77–78 area, light root ≈ L228–229 area; ZH swap rules) |
| Production page | `scripts/build_intl.py` → `templates/intl.html.j2` → `site/intl.html`; workspace shell `templates/intl_workspace/shell.html.j2` |
| Evidence gate | `scripts/check_ui_visual_evidence.py` + `scripts/capture_page_evidence.py` |

The R13 page and every other existing Paper page were left unchanged. The R14 work only adds pages, artboards and tokens.

## 1. Design bar (applies to every board)

### 1.1 Doctrine (verbatim, binding)

> NEVER a colored left edge or accent stripe on any container on any edge; neutral surface
> hierarchy, even borders, typography and labeled semantic ink; featured emphasis = a ring,
> never a filled container; complete focus outlines; meaningful chart series.

Operational consequences:
- Container borders are always even: the same width and the same colour on all four sides.
- No `border-left`, `border-top` or `box-shadow: inset Npx 0` in a semantic colour on any container.
- No pseudo-element bars on any edge.
- A "selected", "featured" or "triggered" container gets a **ring**: `outline` or an even
  `border` of 1.5px in `--info` (featured/triggered) or `--link` (keyboard focus). It never gets a fill or a stripe.
- A semantic colour reaches a container only as a **labelled chip**, an **even dashed outline**
  (qualified, abstain or restricted), or **ink** on a value.
- Chart series colours are allowed only when they encode a named series that the legend or the axis label also names.

### 1.2 The six ordered questions

Every surveillance board answers these questions in this order, and labels each with its number (Q1…Q6):

1. Q1 What changed globally?
2. Q2 Local, FX, common or divergent?
3. Q3 Credit, funding, liquidity?
4. Q4 Transmission into the US?
5. Q5 Eligible US corroboration?
6. Q6 What resolves the thesis? (Confirm / Refute / Expire)

ZH labels as drawn: Q1 全球发生了什么变化？ · Q2 本地、汇率、共同还是背离？ · Q3 信用、融资、流动性？ ·
Q4 如何传导至美国？ · Q5 合格的美国佐证？ · Q6 什么能验证或推翻论点？

### 1.3 Visible honesty (non-negotiable)

Every displayed number carries all five of:
- a **label**;
- a **unit**;
- a **basis**: Local, USD or Hedged;
- the **§5 clock** (masterplan §5 four-clock model) it belongs to: Reference period, Source available, Acquired + qualified, or Published;
- a **tier/rights chip**: Tier 1/2/3, Proxy or Restricted.

Further rules:
- `Qualified` and `Abstain` are first-class states with their own grammar (§7). They are never empty space and never a zero.
- Specimen values carry a visible `Specimen` chip in the page header. They are never shipped to production without the live data path.
- Rule of thumb: if a value cannot carry all five, render the state, not the number.

## 2. Board inventory (R14 page)

Drawn variants are the artboards in Paper. "Specified" variants are not drawn; they follow this spec's matrices (§13). Builders must still produce and capture them (§16).

| # | Board | Paper artboard name(s) | Drawn | PNG reference(s) in `scratchpad/r14/` | Packet |
|---|---|---|---|---|---|
| 1 | Scanner · desktop · dark · EN | R14 · Scanner · Desktop · Dark · EN | yes | `scanner__dark__en__1440.png` (1440×2028) | IM13 |
| 2 | Scanner · desktop · light · EN | R14 · Scanner · Desktop · Light · EN | yes | `scanner__light__en__1440.png` (1440×2028) | IM13 |
| 3 | Scanner · desktop · dark · ZH | R14 · Scanner · Desktop · Dark · ZH | yes | `scanner__dark__zh__1440.png` (1440×2012) | IM13 |
| 4 | Scanner · desktop · light · ZH | R14 · Scanner · Desktop · Light · ZH | yes | `scanner__light__zh__1440.png` (1440×2012) | IM13 |
| 5 | Scanner · mobile · dark · EN | R14 · Scanner · Mobile · Dark · EN | yes | `scanner__dark__en__390.png` (390×3915) | IM13 |
| 6 | Scanner · mobile · light · EN | R14 · Scanner · Mobile · Light · EN | yes | `scanner__light__en__390.png` (390×3915) | IM13 |
| 7 | Scanner · mobile · dark · ZH | R14 · Scanner · Mobile · Dark · ZH | yes | `scanner__dark__zh__390.png` (390×3833) | IM13 |
| 8 | Scanner · mobile · light · ZH | R14 · Scanner · Mobile · Light · ZH | yes | `scanner__light__zh__390.png` (390×3833) | IM13 |
| 9 | Dislocation explorer | R14 · Dislocation explorer · Desktop · Dark · EN | dark EN | `dislocations__dark__en__1440.png` (1440×1871) | IM15 |
| 10 | Transmission workbench | R14 · Transmission workbench · Desktop · Dark · EN | dark EN | `transmission__dark__en__1440.png` (1440×1865) | IM17 |
| 11 | EM market dossier (Brazil) | R14 · EM market dossier · Desktop · Dark · EN | dark EN | `dossier__dark__en__1440.png` (1440×1842) | IM14 + IM16 |
| 12 | Coverage and data states | R14 · Coverage and data states · Desktop · Light · EN | light EN | `coverage__light__en__1440.png` (1440×1754) | IM13 (coverage) + IM16 |
| 13 | **Added §13:** Scenario lab · Event replay · Saved watch | R14 · Scenario lab · Replay · Watch · Dark · EN | dark EN | `scenario-replay-watch__dark__en__1440.png` (1440×2318) | IM18 (+ existing `intl_workspace_scenario.js`) |
| 14 | **Added:** State matrix (specimen, not a page) | R14 · State matrix · Dark/Light · EN/ZH | all 4 theme×locale columns | `state-matrix__all__en-zh__1440.png` (1440×1546) | all packets |

R13 had 12 boards and R14 upgrades all 12 (rows 1–12). Rows 13–14 are additions.

## 3. Typography

### 3.1 Families

| Role | Production token | Paper proxy | Rule |
|---|---|---|---|
| UI text (EN) | `var(--font-ui)` (`-apple-system, BlinkMacSystemFont, Inter, "Segoe UI", Roboto, …`) | Inter | Never hard-code `Inter`; use the token. |
| UI text (ZH) | `var(--font-ui)`, plus scoped `--font-zh` prepended under `html[data-lang="zh"] .intl-gs` (see §5.3) | PingFang SC | ZH copy is real Chinese, never machine placeholder. |
| Numerals | `var(--font-mono)` (`ui-monospace, "SF Mono", …`) with `font-variant-numeric: tabular-nums` | Menlo | Every number, clock, z, σ and % uses the numeral face. |

**Render finding (must be honoured):** Paper's text nodes compute `fontFamily: system-ui, sans-serif`. The visible face in the PNGs is therefore the system face, not Inter. Menlo nodes compute `"Menlo-Bold","Menlo",system-ui`, and Menlo 600 renders as 700. Production must use the tokens above, not the Paper computed values. Weight is specified per role below. Builders must not chase the PNG glyph shapes.

### 3.2 Type scale (production `--fs-*` tokens; all exist in `theme.css`)

| Token | px | Weight | Line-height | Use |
|---|---|---|---|---|
| `--fs-display` | 46 | 700 | 52 | not used on surveillance boards (reserved) |
| `--fs-num-xl` | 38 | 700 numeral | 44 | dossier hero move (`+3.4%`) |
| `--fs-h1` | 28 | 700 | 34 | page H1 |
| `--fs-num-lg` | 22 | 700 numeral | 28 | KPI card value |
| `--fs-h2` | 17 | 600 | 24 | band / panel heading; State-matrix value (17/700 numeral) |
| `--fs-md` | 15 | 400 | 22 | lede |
| `--fs-body` / `--fs-h3` | 14 | 400 / 600 | 20 | table cell text / sub-panel heading |
| `--fs-sm` | 12.5 | 400 | 18 | secondary text, desk read, notes |
| `--fs-label` | 11 | 600–700 | 14 | eyebrow and labels (700, `0.06em`, uppercase EN; ZH no uppercase, `0.02em`) |
| `--fs-micro` | 10 | 600–700 | 12 | chips, table headers (700, `0.06–0.08em`), clocks (numeral 10/400) |

Table header text: 10/700, `0.08em` (scanner) or `0.06em` (other tables), `--muted`. The active sort column is `--text`. In the scanner, `USD %` is the active column.

### 3.3 Spacing rhythm (4/8)

New scoped tokens `--sp-1…--sp-8` = 4 / 8 / 12 / 16 / 20 / 24 / 32 / 44 px, under `.intl-gs` only.

Board usage:
- workspace gap 16;
- band gap 16;
- card gap 8 (question strip) or 12 (KPI row, cards);
- table row 48 (scanner) or 40 (coverage, edge list);
- header row 36 (scanner) or 32 (ranking) or 24 (edge list, coverage);
- panel padding 16/20;
- inspector rail padding 16/20/20 or 20.

### 3.4 Radius

| Token | px | Exists in prod? | Use |
|---|---|---|---|
| `--r-ctl` | 8 | yes | segmented control, selected table row ring, small slots |
| `--r-btn` | 10 | used with fallback `var(--r-btn,10px)` | buttons (h40), question cards |
| `--r-card` | 12 | yes | cards, tables, State-matrix cells |
| `--r-panel` | 14 | **undefined** (intl CSS uses fallback 14px) | panels, bands, inspector rails, State-matrix columns → define scoped `.intl-gs{--r-panel:14px}` |
| `--r-pill` | 999 | used with fallback | chips |

## 4. Colour: production mapping (reuse first)

Paper names its tokens `--mx-dark-*` and `--mx-light-*` because Paper vars do not cascade. Production uses one name per role, and `html[data-theme="light"]` and `html[data-lang="zh"]` re-bind it. **Builders use the production names in the middle column only.** Never write a hex value in a template.

| Role | Production token | Dark hex | Light hex | Light text ink (production) | Note |
|---|---|---|---|---|---|
| page | `--bg` | #0F1115 | #F7F8FA | — | |
| surface 1 | `--panel` | #181B21 | #FFFFFF | — | panels, tables, cards |
| surface 2 | `--panel2` | #1E222A | #EEF1F6 | — | table head, inputs, skeleton, scenario input column |
| primary text | `--text` | #D7DCE3 | #1C2430 | — | |
| secondary text | `--muted` | #8B93A1 | #5D6B7E | — | labels, clocks, stale values |
| hairline | `--line` | #3A4150 | #C9CCD1 | — | even borders, rails, baselines (decorative) |
| positive | `--up` → text `--ink-up` | #45B873 | #1F9A55 (graphic) | #1E6D47 | ZH swaps hue (§6) |
| negative | `--down` → text `--ink-down` | #E06464 | #CF4040 (graphic) | #B23C3D | ZH swaps hue (§6) |
| caution | `--warn` → text `--ink-warn` | #E0A030 | #B9791A (graphic) | #7D5922 | qualified, partial, stale, suspended, spreads |
| good state | `--ok` → text `--ink-ok` | #3DA564 | #2F8A52 (graphic) | **#296B48** | Paper drew #1E6D47; production `--ink-ok` is authoritative (6.01/6.38/5.64 on bg/panel/panel2, PASS) |
| information | `--info` → text `--ink-link` | #5B9BF0 | #285FFF (graphic) | #2758E6 | featured/triggered ring, corrected state |
| link / focus | `--link` → text `--ink-link` | #7AA7E0 | #285FFF | #2758E6 | focus outline, links, Watch stance text |
| provenance | `--prov-ink` | #62A0E8 | #2C62B3 | #2C62B3 | Proxy chip text, lineage links |
| tier | `--ink-tier` | #9B86FF | #5B3FC4 | #5B3FC4 | Tier chip text, Restricted glyph outline |
| tier accent | `--mx-tier-accent` | #7C5CFF | #7C5CFF | — | graphic only; reserved, not used on surveillance boards |
| act | `--act` | #E05555 | #C43D3D | — | **not used** on surveillance boards; dark `--act` on `--panel2` fails text contrast (4.25) |

The light text inks come from production `color-mix(in srgb, var(--X) var(--ink-mix-X), var(--text))`:
- light mixes: up 62%, down 84%, warn 62%, ok 70%, link/info/act 88%;
- dark mixes are 100%, so the dark ink is the base hue;
- light ZH swaps the up/down mixes (up 84%, down 62%).

The values in the table were recomputed from those mixes, and they match the Paper tokens except ink-ok.

## 5. Additive token diff

### 5.1 Paper (done; hash `91ff7025`)

No existing `--mx-*` token was renamed or removed. These tokens were added during R14 and sit after `--mx-light-ink-link` in the Paper token order:
- `--mx-returns-{up,down}-{soft,mid,strong}`;
- `--mx-light-returns-{up,down}-{soft,mid,strong}`;
- `--mx-light-ink-ok`;
- `--font-ui`, `--font-num`, `--font-zh`;
- `--fs-micro … --fs-display` (11);
- `--fw-regular … --fw-extrabold` (5);
- `--bp-mobile/tablet/desktop`;
- `--sp-1 … --sp-8`;
- `--r-ctl/btn/card/panel/pill`.

### 5.2 Production — reuse, do not duplicate

Reuse these unchanged:
- `--bg --panel --panel2 --text --muted --line`;
- `--up --down --warn --ok --info --link` and their `--ink-*`;
- `--prov-ink --ink-tier --mx-tier-accent`;
- `--font-ui --font-mono`, `--fs-*`, `--r-card --r-ctl`, `--card-shadow`.

Do **not** add global `--sp-*`, `--ser-*` or `--returns-*` to `theme.css` in Wave 2.

### 5.3 Production — new tokens, scoped to `.intl-gs` (proposed file `templates/intl_workspace_surveillance.css`)

Scope class: **`.intl-gs`**. Never use `.igs`; it already names a ZH gauge remap scope in production.

```css
.intl-gs{
  --r-panel:14px; --r-btn:10px; --r-pill:999px;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px; --sp-7:32px; --sp-8:44px;
  /* chart series: Local, FX, Common, 4th series */
  --ser-1:#5b9bf0; --ser-2:#d4a017; --ser-3:#0ea5e9; --ser-4:#e08b45;
  /* returns heat — FILL ONLY, never text ink */
  --returns-up-soft:#1a2325; --returns-up-mid:#1d2b29; --returns-up-strong:#213a31;
  --returns-down-soft:#222025; --returns-down-mid:#302429; --returns-down-strong:#402a2f;
}
html[data-theme="light"] .intl-gs{
  --ser-1:#2f63c4; --ser-2:#8f6a04; --ser-3:#0284c7; --ser-4:#b06a25;
  --returns-up-soft:#edf7f1; --returns-up-mid:#dbefe4; --returns-up-strong:#c0e3cf;
  --returns-down-soft:#fbf0f0; --returns-down-mid:#f7e0e0; --returns-down-strong:#f2caca;
}
/* ZH: positive heat follows the red-up convention, exactly like --up/--down */
html[data-lang="zh"] .intl-gs{
  --returns-up-soft:#222025; --returns-up-mid:#302429; --returns-up-strong:#402a2f;
  --returns-down-soft:#1a2325; --returns-down-mid:#1d2b29; --returns-down-strong:#213a31;
}
html[data-theme="light"][data-lang="zh"] .intl-gs{
  --returns-up-soft:#fbf0f0; --returns-up-mid:#f7e0e0; --returns-up-strong:#f2caca;
  --returns-down-soft:#edf7f1; --returns-down-mid:#dbefe4; --returns-down-strong:#c0e3cf;
}
html[data-lang="zh"] .intl-gs{
  --font-zh:"PingFang SC","Hiragino Sans GB","Noto Sans SC","Microsoft YaHei";
  font-family:var(--font-zh),var(--font-ui);
}
```

Series colours (`--ser-*`) do **not** swap in ZH. They encode decomposition components, not direction.

### 5.3 amendment A1 (2026-10-22) — pure theme derivations, no literals

Status: seat ruling A1 (2026-10-22). This amendment supersedes the §5.3 token block above for every consumer of `templates/intl_workspace_surveillance.css`. The block above stays as the R14 historical record.

Why: the pack-3 design-governance forward-only ratchet (`scripts/check_design_system.py --mode enforce-added`, rules 4 and 1) refuses token values minted in a template. `templates/theme.css` is the sole token root and stays unchanged, so every A1 token is a derivation of an existing theme token.

The surveillance stylesheet carries exactly this block, START marker included, before `/* === END INTL-GS §5.3 TOKENS === */`:

```css
/* === INTL-GS §5.3 TOKENS — amendment A1 (2026-10-22): pure theme derivations, no literals === */
.intl-gs{
  --r-panel:var(--r-card); --r-btn:var(--r-ctl);
  --r-pill:calc(var(--r-card) * 100);   /* pill = any radius ≥ half-height; theme has no pill token */
  --ser-1:var(--info); --ser-2:var(--q2); --ser-3:var(--ok); --ser-4:var(--orange);
  --ink-tier:var(--ink-link);           /* tier_preview.css's own default outside the prophet gate */
}
/* returns heat — FILL ONLY, never text ink; follows --up/--down so light theme and ZH red-up
   hold BY CONSTRUCTION (theme.css L277 swaps --up/--down under html[data-lang="zh"]) */
.intl-gs__heat--up-soft{fill:var(--up);fill-opacity:.14;}
.intl-gs__heat--up-mid{fill:var(--up);fill-opacity:.26;}
.intl-gs__heat--up-strong{fill:var(--up);fill-opacity:.42;}
.intl-gs__heat--down-soft{fill:var(--down);fill-opacity:.14;}
.intl-gs__heat--down-mid{fill:var(--down);fill-opacity:.26;}
.intl-gs__heat--down-strong{fill:var(--down);fill-opacity:.42;}
.intl-gs__heatbg{position:relative;isolation:isolate;}
.intl-gs__heatbg::before{content:"";position:absolute;inset:0;background:var(--heat-ink);opacity:var(--heat-a);z-index:-1;pointer-events:none;}
.intl-gs__heatbg--up-strong{--heat-ink:var(--up);--heat-a:.42;}
.intl-gs__heatbg--down-strong{--heat-ink:var(--down);--heat-a:.42;}
```

Deleted (not moved):
- the `--sp-1…8` spacing scale;
- every `--returns-*` property;
- the light-theme `.intl-gs` override block;
- all four ZH and light+ZH override blocks;
- the `--font-zh` block;
- the T2 `--ink-tier` hex pair.

Literal `var()` fallbacks, such as `var(--r-btn,10px)` and its siblings, are dropped.

A1.1: --r-card/--r-ctl are not yet at :root (DS-PR-0 pending); radius declarations carry the estate fallback pairs 12px/8px/999px; the derivations become live automatically when DS-PR-0 lands.

Accepted visual deltas:
- panel radius 14px → 12px (`--r-card`);
- button radius 10px → 8px (`--r-ctl`);
- series 3 → `--ok`;
- tier ink → link ink (`--ink-link`, the `templates/tier_preview.css` default outside the prophet gate);
- returns heat → opacity steps (.14 / .26 / .42) over `--up` / `--down`. The light theme and the ZH red-up convention therefore hold by construction, because theme.css swaps `--up`/`--down` under `html[data-lang="zh"]`.

§15 re-run: `--ink-tier` (= `--ink-link`) text on `--panel`, measured in Chromium on the W2F fixture site (independent review r7, WCAG 2.x relative luminance; chip ink rgb(122,167,224) dark, rgb(41,90,234) light), gives dark 7.12:1 on the states panel (#151820) and 7.20:1 on the coverage panel (#14171e), and light 5.61:1 on #ffffff (the AA body-text threshold is 4.5:1). The 6.92 / 5.79 figures in the §15 table below are the Paper-token values, not the rendered theme.

## 6. Direction-ink rule (incl. ZH)

1. `--up`/`--down` ink is used **only** for a standalone, return-like, signed value: a % move, a residual z, or a divergence. It is also used for the signed divergence bar fill.
2. A mixed comparison uses neutral `--text`: two signed values side by side whose relation is the point, or "expected vs observed".
3. Spreads, CDS, yields and funding basis use `--text`. A widening beyond the market's own threshold uses `--ink-warn` plus the label "wider" or "tighter". They never use up/down: a wider spread is not "down".
4. A stale or out-of-window value is `--muted` with no direction ink, plus the `Stale · Nd` chip.
5. Decomposition colours:
   - Local = `--ser-1`;
   - FX = `--ser-2`;
   - Common = `--ser-3`;
   - Residual/idiosyncratic = `--info` 1px **outline** segment (no fill).
   - Totals are printed in `--text` and must sum to the shown total.
6. Stance:
   - Get ready = warn chip;
   - Watch = info chip (ring `--info`, text `--link`/`--ink-link`);
   - Stand aside = muted chip.
   - Stance never uses up/down ink.
7. **ZH flip.** Under `html[data-lang="zh"]`, positive is red and negative is green. Production already swaps `--up`/`--down` (dark `#e06464`/`#45b873`, light `#cf4040`/`#1f9a55`) and the light ink mixes. Components must therefore bind **semantic** tokens (`--up`/`--ink-up` for positive, `--down`/`--ink-down` for negative) and never hard-code a hue. `--warn`, `--ok`, `--info`, `--link` and `--ser-*` **never** flip. Expected ZH light ink: positive #B23C3D, negative #1E6D47 (verified in the drawn ZH boards).
8. A sign is always typed: `+3.4%`, `−1.2σ` (U+2212 minus). Colour is never the only carrier of direction. The divergence bar also carries its side of zero and the printed signed value.

## 7. State grammar (State-matrix board is the canonical specimen)

Each state has a chip label, a value treatment and a clock treatment. The cell anatomy is shown in the State matrix:
- cell: h92, padding 10/12, radius `--r-card`, `--panel` bg, even 1px `--line` border;
- top row: market 11/600 `--muted` + chip;
- value: numeral 17/700 + basis 11 `--muted`;
- clock: numeral 10 `--muted`.

| State | Chip (h20, pad 0 7, `--r-pill`, 10/600) | Container | Value | Clock |
|---|---|---|---|---|
| Complete | `Complete` · 1px `--ok` border, `--ink-ok` text | even 1px `--line` | signed ink per §6 | §5 clock, `--muted` |
| Loading | `Loading` · `--muted` border/text | even 1px `--line`; two `--panel2` skeleton bars (h10/h8, radius 4) | **no number**, no "0" | "Acquiring…" `--muted` |
| Qualified | `Qualified` · 1px **dashed** `--warn`, `--ink-warn` text | **even 1px dashed `--warn`** outline | value kept, ink per §6 | reason line (e.g. "proxy basis", "thin session") |
| Abstain | `Abstain` · dashed `--muted` | even 1px dashed `--muted` | "—" in `--muted` | reason, e.g. "Unscored · insufficient history" / "band spans zero" |
| Empty | `No data` · `--muted` | even 1px `--line` | "—" | reason (e.g. "Not published by source") |
| Partial | `Partial · 3 of 5` · `--warn` | even 1px `--line` | value from available legs | list of missing legs |
| Stale | `Stale · 2d` · `--warn` | even 1px `--line` | **`--muted`, no direction ink** | "Last good 19 Oct 21:00 UTC" |
| Closed | `Closed` · `--muted` | even 1px `--line` | last close, `--muted` | reopen clock ("Opens 00:00 UTC") |
| Suspended | `Suspended` · `--warn` | even 1px `--line` | last print, `--muted` | halt clock |
| Rights-restricted | `Restricted` · dashed `--warn` | even 1px `--line` | **empty dashed slot 72×22, radius 6, 1px dashed `--line`**; never a blurred or obscured number | entitlement note ("Licensed feed · not redistributable") |
| Corrected | `Corrected` · `--info` border, `--ink-link` text | **1px `--info` ring** | old value numeral 12.5 `--muted` line-through, new value numeral 17/700 | correction clock |
| Recovered | `Recovered` · `--ok` | even 1px `--line` | value with ink | the gap stays marked on the series |

Coverage glyphs (12×12, inline before a clock):

| Glyph | State |
|---|---|
| filled `--ok` dot + clock | Complete |
| dashed `--warn` square | Qualified |
| `--warn` ring | Partial |
| filled `--warn` square + "Stale · Nd" | Stale |
| `--muted` dash | Abstain |
| `--muted` ring | Closed |
| `--ink-tier` outline square | Restricted |
| `--info` ring | Corrected |

Precedence when several states apply:
1. Restricted
2. Loading
3. Abstain
4. Stale
5. Suspended / Closed
6. Corrected
7. Qualified
8. Partial
9. Complete

The chip shows the highest state, and the inspector lists all of them.

## 8. Component inventory

All sizes are in px. "D / L" means dark hex / light hex. Text colours in light mode use the `--ink-*` value from §4. Every interactive element gets the focus outline `outline:2px solid var(--link); outline-offset:3px`. This matches the existing `.intl-workspace … :focus-visible` rule in `templates/intl_workspace.css`. Paper drew offset 2, and the existing production 3 wins.

| Component | Geometry | Tokens (D / L) | Notes |
|---|---|---|---|
| Chip | h20, pad 0 7, `--r-pill`, 10/600, gap 4 | border 1px semantic (§7); text `--ink-*`; bg transparent | never filled; dashed = qualified/abstain/restricted |
| Tier chip | as chip | border `--line` (#3A4150 / #C9CCD1); text `--ink-tier` (#9B86FF / #5B3FC4) | labels `T1` `T2` `T3`; `Proxy` uses `--prov-ink` (#62A0E8 / #2C62B3) text; `Restricted` = dashed `--warn` |
| Stance chip | as chip | Get ready: `--warn` (#E0A030 / border #B9791A, text #7D5922) · Watch: border `--info` (#5B9BF0 / #285FFF), text `--link`/`--ink-link` (#7AA7E0 / #2758E6) · Stand aside: `--muted` (#8B93A1 / #5D6B7E) | never up/down |
| Specimen chip | as chip, page header | dashed `--warn`, text `--ink-warn` | label "Specimen values · not live"; `white-space:nowrap` |
| Section label / eyebrow | 11/700, `0.06em`, uppercase (EN) | `--muted` | ZH: no uppercase, `0.02em` |
| Question card (strip of 6) | pad 10/12, `--r-btn` (10), gap 8; number circle 22×22, 1px `--line`, numeral 11/700 centred | bg `--panel` (#181B21 / #FFFFFF); title 12.5/600 `--text`; one-line answer 11 `--muted` | desktop 6 equal columns, gap 8; mobile 2×3 grid, gap 8; answered question = number circle ring `--info` 1.5 |
| Panel / band | pad 16/20, `--r-panel` (14), gap 12–16, even 1px `--line` | bg `--panel` | band head = Q-number label + H2 17/600 + subtitle 12.5 `--muted` + right-aligned clock |
| Inspector rail | width 400, pad 16/20/20 (dislocation) or 20 (edge), `--r-panel`, gap 14–16 | bg `--panel`, 1px `--line` | sticky `top: 80px` at ≥1100; stacks below the main column under 1100 |
| Featured container | as panel | **ring**: `outline:1.5px solid var(--info)` (#5B9BF0 / #285FFF), no fill | desk stance card, Q6 thesis card, selected peer card, triggered watch row |
| Button (primary / secondary) | h40, pad 0 16, `--r-btn`, 12.5/600 (`--fs-sm`) | primary: 1px `--link` border, `--link` text; secondary: 1px `--line`, `--text` | no filled primary; disabled = `--muted` text + dashed `--line` |
| Segmented control | h32 desktop / h40 mobile, `--r-ctl`, 1px `--line`, segment pad 0 10 | active segment: bg `--panel2` + `--text` 600; inactive `--muted` | Mode / Basis / Horizon in the snapshot bar |
| Snapshot bar | pad 14/16, `--r-panel`, gap 12, bg `--panel`, 1px `--line` | four §5 clocks: label 10/700 `--muted` + numeral 12.5 `--text` | chips "Since last visit · 6 changes", "Coverage 31/34 · 3 partial"; note line 12.5 `--muted` |
| KPI card | pad 14/16, `--r-card`, gap 6, bg `--panel`, 1px `--line` | label 11/700 `--muted`; value numeral 22/700 with ink per §6; basis + clock 10 `--muted`; tier chip top-right | 4 per row, gap 12 |
| Session hand-off strip | h56, 3 segments with `→` separators, 1px `--line` | segment: session name 12.5/600 + state chip + clock | Asia close → Europe open → US pre-market |
| Table (generic) | `--r-card`, overflow clip, 1px `--line`; head bg `--panel2`; rows separated by 1px `--line` bottom | head 10/700 `--muted`, active sort column `--text` | fixed-width slots with `flex-shrink:0` and a single flex column; numbers right-aligned |
| Selected table row | h48, pad-inline 14, `--r-ctl` | selected: 1.5px `--info` ring; focused: 2px `--link` outline; hover: neutral `--panel2` surface | the drawn BR row is the composite selected + focused + hover; never a stripe |
| Mini stacked bar (Local / FX) | slot 120 (pad-left 16); bar 88×8, radius 2, centred zero tick 1px `--muted` h12 | Local `--ser-1`, FX `--ser-2` | diverging around zero, scale ±5% = ±44px; tooltip/aria gives both legs + total |
| Signed divergence bar | slot 120 (pad-left 16); half-width 40 each side of 1px `--muted` zero tick (h14); bar h8 radius 2; ±2σ dashed `--line` ticks | fill `--up` / `--down` (graphic) | length = min(\|z\|,3)/3 × 40; printed z numeral 12.5/700 with direction ink after the bar |
| Sparkline (USD 20D) | slot 96; svg 88×24 | stroke 1.5 `--ser-1`; baseline 1px dashed `--line` at the window start value; end dot r2 `--ser-1` | no fill, no smoothing; a gap breaks the line; a stale tail is dashed `--muted` |
| Typed-edge glyph | 28×10 inline svg | flow `--ser-1` solid 2.5 · lending `--ser-2` dash 6 4 · credit `--ser-3` dash 2 3 · commodity `--ser-4` dash 10 4 | always paired with the type word; the legend repeats it |
| Graph node | pad 8/12, `--r-btn`, 1px `--line`, bg `--panel` | label 12.5/600 `--text`, sub 10 `--muted` | the source node is featured (1.5px `--info` ring) |
| Coverage glyph | 12×12 | per §7 table | precedes every clock in the coverage matrix |
| Rights slot | 72×22, radius 6, 1px dashed `--line` | empty | replaces a restricted value; never blur |
| Skeleton bar | h10 / h8, radius 4 | `--panel2` (#1E222A / #EEF1F6) | Loading only; no shimmer animation under `prefers-reduced-motion` |
| Range slider (scenario) | track h4 radius 2 `--line`; thumb 20×20 circle 1px `--link` on `--panel`; hit area 40×40 | value numeral 12.5 `--text`, unit 10 `--muted` | keyboard: arrows ±0.1, PgUp/PgDn ±1; `aria-valuetext` carries the unit |
| Estimate band (scenario) | svg 150×16, zero tick x=125, 25px per 1% | band rect 1px: Clears bar solid `--ok`; Qualified dashed `--warn`; Abstain `--muted` + "—"; Restricted dashed `--warn` + rights slot; point 2px `--text` tick | 80% interval stated in the column header |
| Replay rail | dots 10px on rail; past rail 2px `--link`, future rail 1px `--line` | past dot filled `--muted`; selected 1.5px `--info` ring + 2px `--link` focus; future dot hollow 1px `--muted` | step label numeral 10 `--muted`; selected label `--text` |
| Clock card (replay) | pad 12/14, `--r-card`, 1px `--line` | §5 clock label 10/700 `--muted`, numeral 14 `--text` | three cards + the lag card "Source → board lag 1m 58s" |
| Watch row | h56, columns ID 40 · Condition flex · Scope·basis 200 · Last check 170 · State 230 · Action 130 | 1px `--line` bottom; triggered row = 1.5px `--info` ring, no fill | chips: Triggered solid `--warn`; Armed `--info`/`--link`; Qualified dashed `--warn`; Expired `--muted`; action buttons h40 |
| Correction note | inline, 12.5 | `Corrected` chip + old value `--muted` line-through + new value `--text` + clock | e.g. "Corrected 21 Oct 08:00 UTC · USD/BRL close 5.712 → 5.698" |
| Footnote | 11, `--muted`, max-width 960 | — | sources, rights, specimen statement |

## 9. Chart craft rules

1. Every chart carries a title, unit, basis, §5 as-of clock and a source/tier line. Axis labels are numeral 10 `--muted`. Gridlines are 1px dashed `--line` (2 4).
2. **Series are meaningful.**
   - `--ser-1` Local, `--ser-2` FX, `--ser-3` Common, `--ser-4` the 4th series (commodity channel), each named in a legend.
   - Never use series colours decoratively.
   - All four pass ≥3:1 against bg/panel/panel2 in both themes (§15).
   - Typed edges add a dash pattern so that colour is never the only cue.
3. No smoothing or interpolation across missing data. A gap breaks the line, and the break is labelled when it exceeds one session.
4. A zero or baseline is always drawn: 1px `--muted` zero ticks on signed bars, and a 1px dashed `--line` baseline on sparklines.
5. Signed bars diverge from a centred zero, and the printed value is always adjacent.
6. Expected-vs-observed charts use neutral ink:
   - expected = dashed `--muted` 1.5, with the 80% band as a `--panel2` area;
   - observed = `--text` 2.
7. Dislocation scatter:
   - x = fragility 0–100, y = residual σ;
   - the fragility threshold is a dashed `--warn` line at 60, labelled;
   - points are 8px circles with a `--panel2` fill and a 1.5px stroke `--up`/`--down` by residual sign;
   - the selected point has a 1.5px `--info` ring;
   - markets that cannot be plotted appear as "Not plotted" chips (reason in the tooltip) under the plot, never silently dropped.
8. The rank strip (US exposure by channel) uses h8 bars in the channel's typed-edge series colour, with labels left and value right.
9. Every SVG chart has `role="img"` plus an `aria-label` that states the reading in words. A visually hidden data table follows the chart.
10. Motion: none needed. Any transition must be ≤150ms and disabled under `prefers-reduced-motion: reduce`.

## 10. Per-board layout grids

### 10.0 Shared desktop shell (all 1440 boards except the State matrix)

```
board 1440, bg --bg
├─ site-nav (existing product family, §12)          h64, pad-inline 32, gap 10, --panel, 1px --line bottom
└─ workspace  .intl-gs                               column, pad 20/32/48, gap 16, content width 1376
   ├─ toolbar        breadcrumb · sub-tab view-nav (§12) · [Saved investigations] [Watch conditions] (h40)
   ├─ page-header    eyebrow · H1 28/700 · lede 15 --muted (max 760) · Specimen chip │ right: Desk stance card (featured ring, 320)
   ├─ six-question strip   6 × flex 1, gap 8
   ├─ snapshot-bar   §5 clocks ×4 · chips · Mode | Basis | Horizon · alignment note
   ├─ board body     (per board below)
   └─ footnote
```

### 10.1 Scanner (boards 1–4, 1440; packet IM13)

```
Q1 band  (band-head + kpi-row 4 × flex 1, gap 12 + session hand-off strip)
Q2 band  scanner-row gap 16:  scanner-table 1040  |  attention-rail 320 (--r-card)
Q3–Q6    row "Q3 Q4": 2 × flex 1, gap 16, --r-card   (Q3 credit/funding series table | Q4 channel table with typed-edge glyphs)
         row "Q5 Q6": 2 × flex 1, gap 16            (Q5 US instruments table | Q6 Confirm / Refute / Expire + [Arm watch])
footnote
```

The scanner table is a 1040 panel, `--r-card`, clipped. Head: h36, pad-inline 16, `--panel2`, 10/700 `0.08em`. Rows are h48 with the same pad-inline.

| Column | Width | Align | Content |
|---|---|---|---|
| MARKET | 152 | left | flag-free name 14/600 + code 10 `--muted` |
| LOCAL % | 72 | right | numeral 14 (`--fs-body`) signed ink |
| FX % | 72 | right | numeral 14 (`--fs-body`) signed ink |
| USD % (active sort, header `--text`) | 72 | right | numeral 14/700 signed ink |
| Local · FX mini bar | 120 (pad-left 16) | — | §8 mini stacked bar |
| COMMON | 64 | right | numeral 14 `--text` (share of move, %) |
| DIVERGENCE z | 120 (pad-left 16) | — | §8 signed divergence bar + z |
| USD 20D | 96 | — | §8 sparkline |
| TIER | 104 | left | tier chip (+ state chip if not Complete) |
| STANCE | flex (min 112) | left | stance chip |

Specimen rows, in order:
1. BR (selected + focus composite)
2. TW (Proxy)
3. KR
4. MX
5. JP
6. AU
7. IN (Qualified, dashed warn)
8. ZA (Stale · 2d, muted values)
9. PL (Abstain, "Unscored · insufficient history", "—")

The footer row (`tfoot`) holds the row count and coverage. The attention rail (320) holds a ranked list of 5 attention items. Each item has a Q-number, a one-line reason, a chip and a clock.

### 10.2 Scanner mobile (boards 5–8, 390; IM13)

```
status bar (device chrome — not built)
site-nav mobile ≤900   brand · [Terminal 40] · [EN|中文 40] · [≡ 40] / row 2: search h44   pad 4/16/12, gap 8
workspace  pad 16/16/40, gap 16
├─ toolbar · mobile      breadcrumb + horizontally scrolling sub-tab view-nav (scroll-snap, 40 targets)
├─ page-header · mobile  eyebrow · H1 22/700 · lede 14 · Specimen chip · Desk stance card full width
├─ six-questions 2×3     gap 8
├─ snapshot-card         pad 14, --r-card, gap 12 (clocks as 2×2 grid; controls as full-width segmented, h40)
└─ Q1 … Q6 bands stacked; the scanner table becomes market cards (§11.1)
```

### 10.3 Dislocation explorer (board 9, IM15)

```
explorer-row gap 16
├─ left column flex, gap 16
│  ├─ Q2 dislocation map (scatter §9.7, h≈420) + "Not plotted" chips
│  └─ LatAm peers compare (5 compact peer cards)
└─ inspector rail 400  pad 16/20/20, --r-panel, gap 16   (selected market: decomposition, fragility drivers, Q3–Q6 summary, buttons)
divergence ranking panel  pad 16/20/12, --r-panel
```

Ranking head: h32, pad-inline 12, gap 12, 11/700 `0.06em`.

| Column | Width | Align |
|---|---|---|
| # | 28 | left |
| MARKET | 200 | left |
| DOWN ◀ RESIDUAL ▶ UP | 320 | centre (wide divergence bar, half-width 140) |
| Z | 72 | right |
| USD | 80 | right |
| LOCAL | 72 | right |
| FX | 72 | right |
| FRAGILITY | 80 | right (0–100, `--text`; ≥60 `--ink-warn` + "above threshold") |
| DATA STATE | 180 | left (state chip + clock) |
| STANCE | flex | left |

There are seven specimen rows. Brazil is the selected row (ring). Chile is Qualified: its bar is drawn with a dashed `--warn` outline and no fill.

### 10.4 Transmission workbench (board 10, IM17)

```
transmission-row gap 16
├─ left column flex, gap 16
│  ├─ Q4 transmission graph: source picker (segmented) · typed-edge legend · graph (Brazil → EWZ / CBOT soy / EMB / US banks) · desk read 12.5
│  └─ Q4 US exposure by channel (rank strip §9.8)
└─ inspector rail · edge 400  pad 20, gap 14: expected vs observed (§9.6) · cumulative chart · edge evidence · Q5 corroboration · buttons
edge list panel  pad 16/20, --r-panel, gap 10
```

Edge-list head: h24, pad-inline 8, gap 12, 10/700 `0.06em`. Rows are h40.

| Column | Width |
|---|---|
| # | 28 |
| EDGE | 220 |
| TYPE | 116 (glyph + word) |
| MECHANISM | flex |
| EVIDENCE | 140 |
| US WINDOW | 150 (numeral clock range) |
| US RESPONSE | 200 (expected vs observed, neutral ink) |
| TIER | 90 |

### 10.5 EM market dossier — Brazil (board 11, IM14 + IM16)

```
dossier-row gap 16
├─ left column flex (min-width 0), gap 16
│  ├─ Q1 what moved: hero numeral 38/700 (+3.4%, ink per §6) · basis/clock · decomposition bar (Local/FX/Common/Residual, totals sum) · 60-session path chart
│  ├─ Q2·Q3 why: σ decomposition bars + credit/funding table (spreads in --text / --ink-warn, never up/down)
│  └─ Q4·Q5 typed edges table
└─ right rail 400, gap 16: Q6 thesis (featured ring) · Clocks and rights · Corrections · Sources and lineage
LatAm peers row: 5 cards × flex 1, pad 16/20, --r-panel, gap 12 (Chile Qualified dashed warn, Peru Abstain dashed muted)
```

The IM16 EM credit and external-dollar fields depend on the market-by-capability acceptance matrix (§17, gap G4).

### 10.6 Coverage and data states (board 12, light; IM13 coverage + IM16)

```
coverage matrix panel  pad 16/20, --r-panel
├─ head (title, totals "204 cells", legend link)
├─ column header  h24, 10/700 0.06em
└─ region groups Asia / EMEA / Americas, rows h40, each group collapses to "+N more" (button h40)
lower row gap 16:  State legend 420 | Question impact flex | Recovery log 420   (each pad 16/20, --r-panel, gap 10)
```

| Column | Width |
|---|---|
| MARKET | 150 |
| SESSION | 150 |
| INDEX CLOSE | 132 |
| FX FIX | 132 |
| 10Y YIELD | 132 |
| CDS 5Y | 132 |
| USD FUNDING | 132 |
| US PROXY | 132 |
| WHAT THE ANSWER CAN USE | flex (≈244 at 1440) |

Each data cell is a glyph (§7) plus a numeral 10 (`--fs-micro`) clock. The State-legend counts must sum to the matrix total (specimen 204). Question impact maps the missing cells to the affected Q1–Q6, for example "Q3 qualified for 3 markets (CDS licensed)".

### 10.7 Scenario lab · Event replay · Saved watch (board 13, IM18)

```
Scenario lab panel  pad 16/20, --r-panel, gap 16
├─ head: Q-labels, title, "Model estimate · not a forecast" chip, clock
└─ body gap 20
   ├─ Shock inputs 380: --panel2, pad 14/16, --r-card, gap 12 — 3 sliders (§8) · [Run scenario] [Reset] [Save as watch] · path decomposition
   └─ Propagated impact flex: typed-edge graph + target table (Target | Channel | Estimate (80% band §8) | State)
Event replay panel  pad 16/20, --r-panel, gap 16
├─ replay rail (§8) with step clocks
├─ three §5 clock cards + lag card
├─ At-step vs Now table across Q1–Q6 (neutral ink for the comparison; signed ink only in each standalone cell)
└─ correction note
Saved watch panel  pad 16/20, --r-panel, gap 12 — watch table (§8 Watch row)
footnote
```

Estimate states:
- "Clears bar · z 2.4" = solid `--ok`;
- Qualified = dashed `--warn`;
- "Abstain · band spans zero" = `--muted` "—";
- Restricted = dashed `--warn` plus a rights slot.

### 10.8 State matrix (board 14; specimen, not a page — no nav)

1440 wide, pad 32, gap 20. The title row is followed by 4 columns (Dark·EN, Light·EN, Dark·ZH, Light·ZH). Each column has pad 12, gap 8, `--r-panel`, the theme `--bg` and 1px `--line`. Each column stacks the 12 state cells of §7. The ZH columns use ZH chip labels:

| EN | ZH |
|---|---|
| Complete | 完整 |
| Loading | 加载中 |
| Qualified | 有条件 |
| Abstain | 弃权 |
| No data | 无数据 |
| Partial | 部分 |
| Stale | 过期 |
| Closed | 休市 |
| Suspended | 停牌 |
| Restricted | 受限 |
| Corrected | 已更正 |
| Recovered | 已恢复 |

The ZH columns also flip the direction ink. Builders render this as a test fixture page (`site/` is not required) so that every state can be captured in 8 cells.

## 11. Responsive rules

| Breakpoint | Rule |
|---|---|
| ≥1440 | Grids as in §10; content width 1376; workspace pad-inline 32 |
| 1100–1439 | Content fluid; fixed table slots kept; the flex column absorbs the shrink; inspector rails stay 400 → 360 at <1280 |
| 901–1099 | Rails (attention 320, inspector 400, right rail 400) **stack below** the main column, full width; Q3–Q6 pairs become single column; KPI row 2×2 |
| ≤900 | Mobile nav family (§12); workspace pad 16/16/40; six questions 2×3; snapshot bar becomes a card |
| 390 (reference) | Tables become cards (§11.1); all hit targets ≥40×40; search h44; sub-tabs scroll horizontally with `scroll-snap-type:x mandatory`; no horizontal page scroll |

### 11.1 Table → card transformation (≤900)

| Table | Card treatment |
|---|---|
| Scanner | Each row becomes a market card: pad 12/14, `--r-card`, 1px `--line`, gap 8. Card content: name + tier/state chips · USD % numeral 17/700 · Local / FX / Common inline row · divergence bar full width · sparkline full width · stance chip. A selected card gets the ring, and the first 5 cards are shown. "Show all 34" is a 40px button. |
| Ranking, edge list, coverage | Same pattern: label/value pairs in a 2-column grid. The state glyph precedes the clock. |
| Watch | One card per condition. The action button is full width, h40. |

### 11.2 Long text

ZH copy is 10–25% shorter in width, and EN is the binding width case. Text is never truncated in a value. Labels may clamp to 2 lines with the full text in `title` and `aria-label`.

## 12. Nav family statement

- **No new header.** R14 boards clone the existing authenticated/product header `templates/_site_nav.html.j2`:
  - inventory: `templates/_navlinks.html.j2`;
  - behaviour and appearance: `templates/navigation-refresh.css`, `templates/nav_market.js`, `templates/theme.js`;
  - the Paper boards use the "site-nav · single" clone.
- Desktop ≥901: links | search | Terminal, theme switch, EN|中文.
- ≤900: brand + Terminal (40) + EN|中文 (40) + hamburger (40), then a 44px search row. The theme switch lives in the menu.
- The R14 sub-tab bar (Scanner · Dislocations · Transmission · Dossiers · Scenario lab · Replay · Coverage) is **not a header**. It extends the existing workspace view loop `nav.intl-workspace__view-nav` in `templates/intl_workspace/shell.html.j2` (line ~15–16), which today holds overview/compare/macro/risk/history/library. New views are appended to that loop with the same markup, the same `aria-current` treatment and the same focus rule.
- `nav_prefix` may vary by directory depth only. Typography, geometry, menu contents, search, breakpoints and motion may change only in the shared family source, never locally.
- The State matrix is a specimen and carries no nav.

## 13. Theme × locale matrices

### 13.1 What was drawn vs. specified (8 cells = desktop/mobile × EN/ZH × dark/light)

| Board | D·EN·dark | D·EN·light | D·ZH·dark | D·ZH·light | M·EN·dark | M·EN·light | M·ZH·dark | M·ZH·light |
|---|---|---|---|---|---|---|---|---|
| Scanner | drawn | drawn | drawn | drawn | drawn | drawn | drawn | drawn |
| Dislocation explorer | drawn | spec | spec | spec | spec | spec | spec | spec |
| Transmission workbench | drawn | spec | spec | spec | spec | spec | spec | spec |
| EM dossier | drawn | spec | spec | spec | spec | spec | spec | spec |
| Coverage | spec | drawn | spec | spec | spec | spec | spec | spec |
| Scenario · Replay · Watch | drawn | spec | spec | spec | spec | spec | spec | spec |
| State matrix | drawn (all 4 theme×locale columns in one board) | | | | n/a (specimen) | | | |

How to read "spec":
- the builder derives the cell from the drawn cell using §13.2 and §13.3;
- the mobile layout follows §10.2 and §11;
- all 8 cells are still captured as evidence (§16).

### 13.2 Theme swap (dark → light)

| Role | Dark | Light |
|---|---|---|
| surfaces / borders / SVG strokes | `--bg --panel --panel2 --line` dark | the same names re-bound by `html[data-theme="light"]` |
| primary / secondary text | `--text` / `--muted` | `--text` / `--muted` (light values) |
| positive / negative / caution / good **text** | `--up --down --warn --ok` (100% hue) | `--ink-up --ink-down --ink-warn --ink-ok` (mixed inks, §4) |
| positive / negative / caution / good **graphics** | base hue | base light hue (`--up` #1F9A55 etc.); never used as small text |
| info / link text | `--link` #7AA7E0 | `--ink-link` #2758E6 |
| tier text | `--ink-tier` #9B86FF | `--ink-tier` #5B3FC4 |
| focus | 2px `--link` #7AA7E0 | 2px `--link` #285FFF |
| series | `--ser-1…4` dark | `--ser-1…4` light (§5.3) |
| returns heat | dark heat | light heat (§5.3) |

Rule for builders: use `--ink-*` for every coloured **text**, in both themes, because in dark the ink equals the hue. Then the theme swap needs no component code.

### 13.3 Locale swap (EN → ZH)

| Aspect | EN | ZH |
|---|---|---|
| Font | `--font-ui` | `--font-zh` prepended (§5.3) |
| Direction ink | positive green, negative red | **positive red, negative green** (automatic via `--up`/`--down` swap; §6.7) |
| Returns heat | up = green heat | up = red heat (§5.3 ZH block) |
| Series, warn, ok, info, tier | unchanged | unchanged |
| Labels | uppercase 11/700 `0.06em` | no uppercase, `0.02em`, same size/weight |
| Dates | `21 Oct 08:00 UTC` | `10月21日 08:00 UTC` |
| Numbers | `+3.4%`, `−1.2σ`, `5.698` | identical numerals and signs (no 万/亿 rescaling in surveillance tables) |
| Copy | EN masterplan vocabulary | real ZH copy (§1.2 questions; §10.8 state labels); every string goes through `t('EN','中文')` like the existing shell |
| Market names | `Brazil` | `巴西` (+ code `BR` unchanged) |

## 14. Component → template / CSS / JS homes

Class roots:
- shared primitives: `.intl-gs__*` (scope `.intl-gs` on the workspace body);
- per-view classes: `.intl-scanner__*`, `.intl-dislocations__*`, `.intl-transmission__*`, `.intl-dossier__*`, `.intl-coverage__*`, `.intl-scenario__*`, `.intl-replay__*`, `.intl-watch__*`.

None of these exist in production today (grep-verified 2026-10-21). Never use `.igs`.

| Component / view | Home (existing or **proposed new**) | Packet |
|---|---|---|
| Scoped tokens §5.3 + shared primitives (chip, tier/stance/specimen chip, question strip, snapshot bar, panel/band head, featured ring, table, selected row, mini bar, divergence bar, sparkline, typed-edge glyph, coverage glyph, rights slot, skeleton, state cell, buttons, segmented control, footnote) | **`templates/intl_workspace_surveillance.css`** (new) + **`templates/intl_workspace/_gs_macros.html.j2`** (new Jinja macros) | IM13 (first consumer; all others reuse) |
| View registration (sub-tabs) | `templates/intl_workspace/shell.html.j2`: extend **both** view loops (the `nav.intl-workspace__view-nav` button loop and the `.intl-workspace__view-select` `<select>` loop) with `scanner`, `dislocations`, `transmission`, `dossier`, `scenario`, `replay`, `coverage` + ZH labels 扫描 · 背离 · 传导 · 档案 · 情景 · 回放 · 覆盖 | IM13 |
| Snapshot bar, Mode/Basis/Horizon, since-last-visit | `shell.html.j2` (snapshot host) + `templates/intl_workspace_state.js` (existing state store; no new store) | IM13 |
| Scanner view | **`templates/intl_workspace/scanner.html.j2`** | IM13 |
| Dislocation explorer | **`templates/intl_workspace/dislocations.html.j2`** | IM15 |
| Transmission workbench | **`templates/intl_workspace/transmission.html.j2`** | IM17 |
| EM dossier | **`templates/intl_workspace/dossier.html.j2`**, reusing rail patterns from existing `inspector.html.j2` (do not fork the inspector) | IM14 (+ IM16 fields) |
| Coverage and data states | **`templates/intl_workspace/coverage.html.j2`** | IM13 / IM16 |
| Scenario lab | **`templates/intl_workspace/scenario.html.j2`**; behaviour extends existing `templates/intl_workspace_scenario.js` | IM18 |
| Event replay | **`templates/intl_workspace/replay.html.j2`** (relates to existing `history.html.j2`; do not duplicate its history model) | IM18 |
| Saved watch | **`templates/intl_workspace/watch.html.j2`**; persistence through `intl_workspace_state.js` / the IM06/IM08/IM09 contracts | IM18 |
| Scenario / replay / watch styles | **`templates/intl_workspace_scenario.css`** (new) | IM18 |
| State matrix fixture | **`templates/intl_workspace/_gs_state_fixture.html.j2`** — test/evidence fixture only, not linked from nav | all |
| Stylesheet links | `templates/intl.html.j2` after line 30: `<link rel="stylesheet" href="intl_workspace_surveillance.css">` (+ `_scenario.css` in IM18) | IM13 / IM18 |
| Asset emission | `scripts/build_intl.py` lines 42–43 asset tuple: append `"intl_workspace_surveillance.css"` (IM13) and `"intl_workspace_scenario.css"` (IM18) | IM13 / IM18 |
| Header | **unchanged** `_site_nav.html.j2` family (§12) | — |

## 15. Contrast table (WCAG 2.x relative luminance; computed from the Paper token hex values, `get_tokens` hash `91ff7025`)

Bars:
- 4.5:1 for text;
- 3.0:1 for graphics/non-text;
- hairline `--line` is decorative and exempt.

The "on returns-strong" column is a text colour on the same-sign strong heat fill. A row's **Min/Pass** is its worst cell. Dark `down` and light `ink-down` fail **only** in the on-fill column (they pass on bg/panel/panel2). Dark `act` fails **only** on panel2. All three are handled by the prohibitions below the table.

| Role | Token | Hex | bg | panel | panel2 | on returns-strong (own sign) | Use | Bar | Min | Pass |
|---|---|---|---|---|---|---|---|---|---|---|
| text | --mx-dark-text | #D7DCE3 | 13.71 | 12.51 | 11.56 | 8.89/9.58 | text | 4.5 | 8.89 | PASS |
| muted | --mx-dark-muted | #8B93A1 | 6.11 | 5.57 | 5.15 | — | text | 4.5 | 5.15 | PASS |
| up | --mx-dark-up | #45B873 | 7.52 | 6.86 | 6.34 | 4.87 | text | 4.5 | 4.87 | PASS |
| down | --mx-dark-down | #E06464 | 5.56 | 5.07 | 4.69 | 3.88 | text | 4.5 | 3.88 | FAIL |
| warn | --mx-dark-warn | #E0A030 | 8.31 | 7.59 | 7.01 | — | text | 4.5 | 7.01 | PASS |
| ok | --mx-dark-ok | #3DA564 | 6.09 | 5.56 | 5.13 | — | text | 4.5 | 5.13 | PASS |
| link | --mx-dark-link | #7AA7E0 | 7.59 | 6.92 | 6.40 | — | text | 4.5 | 6.40 | PASS |
| info | --mx-dark-info | #5B9BF0 | 6.65 | 6.07 | 5.61 | — | text | 4.5 | 5.61 | PASS |
| tier-ink | --mx-dark-tier-ink | #9B86FF | 6.52 | 5.95 | 5.50 | — | text | 4.5 | 5.50 | PASS |
| prov-ink | --mx-dark-prov-ink | #62A0E8 | 6.94 | 6.33 | 5.85 | — | text | 4.5 | 5.85 | PASS |
| act | --mx-dark-act | #E05555 | 5.04 | 4.60 | 4.25 | — | text | 4.5 | 4.25 | FAIL |
| ser-1 | --mx-dark-ser-1 | #5B9BF0 | 6.65 | 6.07 | 5.61 | — | graphic/non-text | 3.0 | 5.61 | PASS |
| ser-2 | --mx-dark-ser-2 | #D4A017 | 7.95 | 7.26 | 6.71 | — | graphic/non-text | 3.0 | 6.71 | PASS |
| ser-3 | --mx-dark-ser-3 | #0EA5E9 | 6.82 | 6.22 | 5.75 | — | graphic/non-text | 3.0 | 5.75 | PASS |
| ser-4 | --mx-dark-ser-4 | #E08B45 | 7.15 | 6.53 | 6.03 | — | graphic/non-text | 3.0 | 6.03 | PASS |
| line | --mx-dark-line | #3A4150 | 1.85 | 1.69 | 1.56 | — | decorative hairline (exempt) | — | 1.56 | n/a |
| text | --mx-light-text | #1C2430 | 14.70 | 15.62 | 13.80 | 11.25/10.47 | text | 4.5 | 10.47 | PASS |
| muted | --mx-light-muted | #5D6B7E | 5.11 | 5.43 | 4.79 | — | text | 4.5 | 4.79 | PASS |
| ink-up | --mx-light-ink-up | #1E6D47 | 5.93 | 6.30 | 5.56 | 4.54 | text | 4.5 | 4.54 | PASS |
| ink-down | --mx-light-ink-down | #B23C3D | 5.48 | 5.82 | 5.14 | 3.90 | text | 4.5 | 3.90 | FAIL |
| ink-warn | --mx-light-ink-warn | #7D5922 | 5.95 | 6.32 | 5.58 | — | text | 4.5 | 5.58 | PASS |
| ink-ok | --mx-light-ink-ok | #1E6D47 | 5.93 | 6.30 | 5.56 | — | text | 4.5 | 5.56 | PASS |
| ink-link | --mx-light-ink-link | #2758E6 | 5.45 | 5.79 | 5.12 | — | text | 4.5 | 5.12 | PASS |
| tier-ink | --mx-light-tier-ink | #5B3FC4 | 6.69 | 7.11 | 6.28 | — | text | 4.5 | 6.28 | PASS |
| prov-ink | --mx-light-prov-ink | #2C62B3 | 5.64 | 5.99 | 5.29 | — | text | 4.5 | 5.29 | PASS |
| up (graphic only) | --mx-light-up | #1F9A55 | 3.40 | 3.61 | 3.19 | — | graphic/non-text | 3.0 | 3.19 | PASS |
| down (graphic only) | --mx-light-down | #CF4040 | 4.43 | 4.71 | 4.16 | — | graphic/non-text | 3.0 | 4.16 | PASS |
| warn (border only) | --mx-light-warn | #B9791A | 3.40 | 3.61 | 3.19 | — | graphic/non-text | 3.0 | 3.19 | PASS |
| ok (border only) | --mx-light-ok | #2F8A52 | 4.05 | 4.30 | 3.80 | — | graphic/non-text | 3.0 | 3.80 | PASS |
| info/link (ring/focus) | --mx-light-info | #285FFF | 4.74 | 5.03 | 4.45 | — | graphic/non-text | 3.0 | 4.45 | PASS |
| ser-1 | --mx-light-ser-1 | #2F63C4 | 5.34 | 5.67 | 5.01 | — | graphic/non-text | 3.0 | 5.01 | PASS |
| ser-2 | --mx-light-ser-2 | #8F6A04 | 4.67 | 4.96 | 4.38 | — | graphic/non-text | 3.0 | 4.38 | PASS |
| ser-3 | --mx-light-ser-3 | #0284C7 | 3.85 | 4.10 | 3.62 | — | graphic/non-text | 3.0 | 3.62 | PASS |
| ser-4 | --mx-light-ser-4 | #B06A25 | 4.01 | 4.26 | 3.76 | — | graphic/non-text | 3.0 | 3.76 | PASS |
| line | --mx-light-line | #C9CCD1 | 1.52 | 1.61 | 1.42 | — | decorative hairline (exempt) | — | 1.42 | n/a |
| ink-ok (production) | `--ink-ok` light | #296B48 | 6.01 | 6.38 | 5.64 | — | text | 4.5 | 5.64 | PASS |

**Prohibitions that follow from the FAIL rows.** No drawn board uses these combinations; a transcript census found 0 hits.

1. Do **not** put signed `--down`/`--ink-down` text on a `--returns-down-strong` fill: dark 3.88, light 3.90. Text on any returns heat fill is `--text` (8.89–11.25, PASS). If a signed ink on a fill is ever required, use the on-fill inks #F08A8A (dark, 5.48) or #9E3132 (light, 4.79). They are not tokens in Wave 2; adding them needs a spec amendment.
2. Do **not** use dark `--act` as text on `--panel2` (4.25). `--act` is unused on surveillance boards. Elsewhere it is restricted to `--bg`/`--panel` or graphics.
3. Light `--up/--down/--warn/--ok/--info` base hues are **graphic-only** (3.19–4.71). Light text always uses the `--ink-*` value.
4. ZH light positive text (#B23C3D) and negative text (#1E6D47) are the same inks as EN light down and up, so ZH passes with the same figures.

## 16. Acceptance — per-board checklist on the 8 evidence crops

### 16.1 Evidence mechanics (`scripts/check_ui_visual_evidence.py`; it checks evidence integrity, not taste)

The gate checks only that the evidence is real and complete:
- a committed **`EVIDENCE.yml`** receipt under `mockups/refs/` or `mockups/evidence/`, with exactly the keys `schema: mastermind.page_evidence_receipt.v1`, `changed_paths`, `manifest`;
- the manifest is a `mastermind.p0_evidence.v2` capture from `scripts/capture_page_evidence.py`. The relevant flags are `--site-dir` or `--base-url`, `--routes`, `--viewports desktop,mobile`, `--locales en,zh`, `--themes dark,light`, `--as-of`, and `--settle-ms ≥1200`, because `theme.js` runs a ~1100ms toggle flourish;
- every page in the manifest carries all **8 rest cells** (desktop/mobile × en/zh × dark/light), and each cell's PNG is present with a matching sha256 and byte length.

Interaction cells: a diff that adds `:hover` or `:focus*` selectors needs, in one owning manifest, a declared `axes.force_states` entry of that kind (for example `focus(.intl-gs__row)`, `hover(.intl-gs__row)`). It must be captured on desktop/en in **both** dark and light. Every Wave 2 view adds a focus rule, so every packet owes a focus force-state.

The **taste judgment** is the reviewer's, using the checklist below on those 8 crops. A green gate is not acceptance.

### 16.2 Checks common to every board (all 8 cells)

| ID | Check |
|---|---|
| C1 | Zero accent stripes. No container has a coloured edge on any side. Featured, selected and triggered containers use a ring. |
| C2 | The six questions appear in order and are labelled Q1–Q6, with ZH labels in ZH cells. |
| C3 | Every visible number has a label, unit, basis, §5 clock and tier/rights chip. Specimen values show the Specimen chip. |
| C4 | Direction ink follows §6. In ZH cells positive is red and negative is green. Spreads, CDS and yields are never up/down. Stale values are muted. |
| C5 | Qualified and abstain are drawn per §7. There are no blank cells and no zeros standing in for missing values. Restricted values use the empty dashed slot. |
| C6 | Typography uses tokens only. Numerals are tabular in the mono face. No clipping, truncated values or overflow at 390. |
| C7 | The header is the existing `_site_nav` family (desktop ≥901 or mobile ≤900 pattern). The sub-tabs are the workspace view-nav, not a second header. |
| C8 | Contrast: no FAIL combination from §15 is present. Light coloured text uses `--ink-*`. |
| C9 | Mobile: tables become cards, all targets are ≥40px, search is 44px, and there is no horizontal page scroll. |
| C10 | A focus force-state crop (desktop/en, dark + light) shows a complete 2px `--link` outline with offset 3. |
| C11 | Chart series are named in a legend or axis. Typed edges carry both colour and dash. Every signed bar has a zero tick. |

### 16.3 Board-specific checks

| Board | Additional checks on its 8 crops |
|---|---|
| Scanner (IM13) | (S1) Column slots match §10.1 exactly; numbers are right-aligned in fixed slots across all rows. (S2) Rows include Selected (ring), Proxy, Qualified, Stale and Abstain specimens. (S3) USD % is the active sort column. (S4) KPI row has 4 cards with tier chips. (S5) Session hand-off strip is present. (S6) Mobile market cards per §11.1. |
| Dislocation explorer (IM15) | (D1) Scatter with the labelled fragility threshold 60, axis units and "Not plotted" chips. (D2) The ranking's DOWN◀RESIDUAL▶UP bar is centred, and the Qualified bar is a dashed outline. (D3) Inspector rail is 400 at ≥1100 and stacks below at <1100. (D4) The fragility ≥60 value carries the "above threshold" label, not colour alone. |
| Transmission workbench (IM17) | (T1) The four typed edges carry colour + dash, the legend matches, and the TYPE column spells the word. (T2) Expected vs observed uses neutral ink. (T3) The US window is a numeral clock range. (T4) The edge list columns match §10.4. |
| EM dossier (IM14/16) | (E1) Hero move with basis and clock; decomposition totals sum. (E2) The credit/funding table uses `--text`/`--ink-warn`, never up/down. (E3) Q6 thesis card is featured (ring). (E4) The Corrections block uses the corrected grammar. (E5) Peer cards: Qualified dashed warn, Abstain dashed muted. |
| Coverage (IM13/16) | (V1) The glyph grammar of §7 is used in every data cell. (V2) Legend counts sum to the matrix total. (V3) Question impact names the affected Q-numbers. (V4) Region groups collapse to "+N more" (40px). |
| Scenario · Replay · Watch (IM18) | (R1) Sliders have a visible value, unit and 40px hit area. (R2) The estimate band shows all four states (clears / qualified / abstain / restricted). (R3) "Model estimate · not a forecast" chip. (R4) Replay rail: past/selected/future grammar; three §5 clock cards + lag card. (R5) At-step vs Now table in neutral comparison ink. (R6) The triggered watch row has a ring and no fill; chip set per §8. |
| State matrix (fixture) | (M1) All 12 states in all four theme×locale columns, with ZH labels per §10.8. (M2) Loading shows no number. (M3) Stale shows no direction ink. (M4) Restricted shows an empty slot, never a blurred value. (M5) The ZH columns flip the direction ink. |

## 17. Gaps and open decisions (seat to freeze before IM13–IM18)

| ID | Gap | Owner / action |
|---|---|---|
| G1 | Only the scanner is drawn in all 8 cells. The other 6 boards are drawn once; their remaining cells are specified, not drawn. | Accept spec-derived cells for Wave 2, or commission one more Paper pass for the light/ZH/mobile variants of the dislocation, transmission and dossier boards. |
| G2 | Paper renders UI text in the system face (`system-ui`), not Inter. The PNG glyph shapes are therefore approximate. | None. Production uses `--font-ui`/`--font-mono` (§3.1). |
| G3 | Paper light `--mx-light-ink-ok` (#1E6D47) differs from production `--ink-ok` (#296B48). | Production wins. Optionally align the Paper token in a later design pass. No production change. |
| G4 | IM16 (EM credit / external-dollar) needs the **market-by-capability acceptance matrix** adopted by the programme owner before freeze (masterplan IM16). The dossier Q3 and coverage CDS/USD-funding columns depend on it. | Seat: adopt the matrix, then mark which coverage cells are Restricted vs Qualified by design. |
| G5 | All specimen values are fabricated for layout only and are marked as specimens. No board may ship them. | Builders bind every value to the IM06/IM08/IM09 contracts or render the state. |
| G6 | The on-fill signed inks (#F08A8A / #9E3132) are not tokens. | Add them only by spec amendment, if a heat cell ever needs signed text. |
| G7 | The PNG references live in the session scratchpad and are not committed. | Seat decides whether to copy them into `mockups/refs/intl-gs-r14/` with a receipt. Scratchpad files do not survive host cleanup. |

