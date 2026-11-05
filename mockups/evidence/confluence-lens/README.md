# confluence-lens — H3 G4 evidence

Template-only LENS Tier-2 layer + line-590 honesty on
`templates/confluence_screener.html.j2`. Dark and light are two treatments:
dotted-dim rule that brightens (dark) vs solid hairline that washes the
material (light). Token substitution is not the proof.

## How these crops were made

- Render: `scripts.build_confluence_screener.build_context` + `render_html`
  against `origin/main:site/factordata/tech_confluence.json` (read via
  `git show` into `/tmp/tech_confluence.json`; this sparse tree does not
  check out `site/`).
- Serve: temp dir with the rendered HTML + `templates/theme.css` +
  `templates/theme.js`.
- Theme/lang: `window.setTheme` / `window.setLang`, then re-read
  `html[data-theme]` / `html[data-lang]` (see `toggle_receipts.json`).
- Tip open: desktop = `focus()` on rank-01 `.lc-wr-big` (theme.js LENS
  `focusin` → `show()`). Mobile 390 = one in-page bubbling `click`
  (Playwright's composed tap toggled the tip closed; disclosed).
- Repro: `python3 mockups/evidence/confluence-lens/capture_confluence_lens.py`

## Crops (G4)

| File | Theme | Lang | Viewport | Subject |
|---|---|---|---|---|
| `01-dark-en-1440-tip-open.png` | dark | EN | 1440 | Rank-01 card, `.lc-wr-big` tip OPEN |
| `02-dark-zh-1440-tip-open.png` | dark | ZH | 1440 | same |
| `03-dark-en-390-tip-open.png` | dark | EN | 390 | same, LENS bottom sheet (scrim + grab + `lens-lock`) |
| `04-dark-zh-390-tip-open.png` | dark | ZH | 390 | same |
| `05-light-en-1440-tip-open.png` | light | EN | 1440 | same; solid hairline + material wash, no glow |
| `06-light-zh-1440-tip-open.png` | light | ZH | 1440 | same |
| `07-light-en-390-tip-open.png` | light | EN | 390 | light sheet on darkened scrim |
| `08a-dark-en-1440-honesty.png` | dark | EN | 1440 | Healed "How to read this honestly" + edge/consistency chips in frame |
| `08b-dark-en-1440-chips.png` | dark | EN | 1440 | Rank-01 chips ("entering at random", "held up in both eras") |
| `08c-light-en-1440-honesty.png` | light | EN | 1440 | same honesty region |
| `08d-light-en-1440-chips.png` | light | EN | 1440 | same chips |
| `08e-dark-zh-1440-honesty.png` | dark | ZH | 1440 | Honesty bullet 「将鼠标移到任一胜率上…」 in view |
| `08f-dark-zh-1440-chips.png` | dark | ZH | 1440 | Gated chips: 「较随机入场高 N 个百分点」 + 「更早年份未能印证」 |
| `08g-light-zh-1440-honesty.png` | light | ZH | 1440 | same honesty region |
| `08h-light-zh-1440-chips.png` | light | ZH | 1440 | same gated chips |
| `rest-dark-en-1440-numeral.png` | dark | EN | 1440 | At-rest numeral — dim dotted rule |
| `rest-light-en-1440-numeral.png` | light | EN | 1440 | At-rest numeral — solid hairline |

Desktop PNGs are 1440px wide. Mobile PNGs are 390px wide.

## T4 receipt vs artifact

Rank-01 combo `L0120` in `site/factordata/tech_confluence.json`:
`h21.months_test = 62`, `h21.n_test = 318`, `split_date = 2018-01-01`.

T4 `data-tip-rc-en` on the rendered rank-01 card:

`62 months · 318 fires · 2018-01-01 → 2026-09-10 · win = up after 21 trading days`

Matches. Toggle receipts: `toggle_receipts.json`.

## G4 row 8 ZH (r2)

Live top-3 combos are all `consistent=true`, so the healed false-branch
copy would not appear on the artifact page. `08e`–`08h` render
`confluence_screener_row8zh.html`: rank-2 forced `consistent=false` with
positive `edge_test_pp` (「更早年份未能印证」), rank-3 forced
`consistent=false` and `edge_test_pp=-2.4` (「近段未能跑赢随机入场」).
Honesty copy is unchanged. Mutation is recorded in `toggle_receipts.json`
(`row8_zh_mutation` + per-crop `zh_money` in-view flags). Same rig:
`setTheme`/`setLang` then re-read `html[data-theme]`/`html[data-lang]`.
Row-8 ZH captures hide the sitewide `.sky-fx` sun/moon (theme.js flourish
pinned at viewport center) so it cannot occlude the chips.

## Deviation from frozen CSS

`check_design_system.py --mode enforce-added` still blocks the ratified 4px
carriage. Attempted page-scoped
`.cs-tipped{--cs-tip-r:4px; border-radius:var(--cs-tip-r);}`
(`/* post-stack: consolidate to theme.css */`). Checker: `blocking=2` —
`literal-custom-property` on `--cs-tip-r: 4px` and `radius-literal` on
`border-radius: var(--cs-tip-r)` (`RADIUS_TOKEN_RE` only accepts
`var(--r-*)`). Kept `border-radius:var(--r-ctl,8px)`. Mechanism
(dotted-dim vs solid-hairline + wash) is unchanged.
