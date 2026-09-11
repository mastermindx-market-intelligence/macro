# sector_central W16 r3 — settled evidence matrix

Provenance: committed head `f0e16b366def6499861cfe15f0521db3c67d543a`. Porcelain empty at capture.
S1 rig: fixture VM (no live bake, no `site/`/`data/` opt-in), real
`body.macro-desk.page-baskets`, Playwright localStorage seed +
`setTheme`/`setLang`, `window.__skyDeck = true`, attribute re-read
refuse-on-mismatch, overlay column, SETTLE column, content-addressed
twins + alias. Crops are viewport-region (canvas-context) captures
with margin — a dark cell must look dark. P3.4 stays deferred
(SEAT RULING 2).

## DARK TREATMENT

Command center. The page canvas is estate `--bg` (luminance depth,
instrument calm). The workspace rail (`.si-side`) sits as a dark
instrument strip; `.si-stage` cards are `--panel` with hairline
`--line`. Action lanes keep their existing luminous cards; the
watch strip is a full-width band under the five, not a sixth badge.
Internals tiles are instrument wells — skeleton bars are a restrained
`--panel2` shimmer freeze-frame, not a glow. LENS `?` tips and
row-pop decision cards are glass over the dark canvas. Monoline
icons inherit currentColor. Mixed/Narrow/Broad take `--warn` /
`--down` / `--up` as instrument colour, not decoration.

## LIGHT TREATMENT

Research workspace. Forced `data-theme="light"` and judged as a
design, not a tint. Canvas is the cool estate light `--bg`; cards
are white material with hairline `--line` and short shadow instead
of glow (page-scoped `#si-confluence` already ships this split;
the overview/board inherit theme.css paper). Internals skeleton
must read as a designed paper hatch — `--panel2` on white, not a
dirty smudge. Empty-why captions deepen toward `--ink` because
`--muted` washes out on paper. LENS and row-pop are white cards
with hairline + shadow. Semantic colour (Narrow/Mixed/Broad) stays
the same tokens, re-inked for paper contrast.

## Mechanisms that INTENTIONALLY differ

1. Material depth — dark = luminance wells / restrained glow; light =
   white paper + 1px shadow / inset hairline.
2. Skeleton — dark freeze-frame of the `--panel2` shimmer; light is a
   paper hatch that must not read as a dirty smudge.
3. Caption contrast — dark can use `--muted`; light deepens toward `--ink`.
4. Confluence view — already ships a distinct light art direction
   (white isles, hairline, no glow).
Shared on purpose: information architecture, six-view rail, bilingual
`.l-en`/`.l-zh`, lane geometry, LENS `?`, row-pop, spacing/type scale.

## SETTLE gate

`document.fonts.ready`, then `getAnimations({subtree:true})`
empty-or-finished on the content root (force-finish). Infinite `.skel`
shimmer is cancelled to a designed freeze-frame. Effective opacity == 1
on the content root AND a sampled row. Unsettled cells are REFUSED.
Reduced-motion is an aid, not the settle mechanism.

## Horizontal page scroll at 390w (every si-view, both languages)

- confluence-en: view=confluence client=390 scroll=390 overflow=0 → none
- confluence-zh: view=confluence client=390 scroll=390 overflow=0 → none
- explore-en: view=explore client=390 scroll=390 overflow=0 → none
- explore-zh: view=explore client=390 scroll=390 overflow=0 → none
- map-en: view=map client=390 scroll=390 overflow=0 → none
- map-zh: view=map client=390 scroll=390 overflow=0 → none
- money-en: view=money client=390 scroll=390 overflow=0 → none
- money-zh: view=money client=390 scroll=390 overflow=0 → none
- moving-en: view=moving client=390 scroll=390 overflow=0 → none
- moving-zh: view=moving client=390 scroll=390 overflow=0 → none
- overview-en: view=overview client=390 scroll=390 overflow=0 → none
- overview-zh: view=overview client=390 scroll=390 overflow=0 → none

## Cells

| id | family | theme | lang | fixture | overlay | settle | root opacity | row opacity | header contrast | alias |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline-dark-en-desktop | baseline | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `baseline-dark-en-desktop.png` |
| baseline-dark-en-mobile | baseline | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `baseline-dark-en-mobile.png` |
| baseline-dark-zh-desktop | baseline | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `baseline-dark-zh-desktop.png` |
| baseline-dark-zh-mobile | baseline | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `baseline-dark-zh-mobile.png` |
| baseline-light-en-desktop | baseline | light | en | populated | clean | settled | 1 | 1 | 7.03 | `baseline-light-en-desktop.png` |
| baseline-light-en-mobile | baseline | light | en | populated | clean | settled | 1 | 1 | 7.03 | `baseline-light-en-mobile.png` |
| baseline-light-zh-desktop | baseline | light | zh | populated | clean | settled | 1 | 1 | 7.03 | `baseline-light-zh-desktop.png` |
| baseline-light-zh-mobile | baseline | light | zh | populated | clean | settled | 1 | 1 | 7.03 | `baseline-light-zh-mobile.png` |
| tab-overview-dark-en-desktop | tabs | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `tab-overview-dark-en-desktop.png` |
| tab-map-dark-en-desktop | tabs | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `tab-map-dark-en-desktop.png` |
| tab-moving-dark-en-desktop | tabs | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `tab-moving-dark-en-desktop.png` |
| tab-money-dark-en-desktop | tabs | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `tab-money-dark-en-desktop.png` |
| tab-explore-dark-en-desktop | tabs | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `tab-explore-dark-en-desktop.png` |
| tab-confluence-dark-en-desktop | tabs | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `tab-confluence-dark-en-desktop.png` |
| hscroll-map-dark-en-mobile | hscroll | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-map-dark-en-mobile.png` |
| hscroll-map-dark-zh-mobile | hscroll | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-map-dark-zh-mobile.png` |
| hscroll-moving-dark-en-mobile | hscroll | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-moving-dark-en-mobile.png` |
| hscroll-moving-dark-zh-mobile | hscroll | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-moving-dark-zh-mobile.png` |
| hscroll-money-dark-en-mobile | hscroll | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-money-dark-en-mobile.png` |
| hscroll-money-dark-zh-mobile | hscroll | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-money-dark-zh-mobile.png` |
| hscroll-explore-dark-en-mobile | hscroll | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-explore-dark-en-mobile.png` |
| hscroll-explore-dark-zh-mobile | hscroll | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-explore-dark-zh-mobile.png` |
| hscroll-confluence-dark-en-mobile | hscroll | dark | en | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-confluence-dark-en-mobile.png` |
| hscroll-confluence-dark-zh-mobile | hscroll | dark | zh | populated | clean | settled | 1 | 1 | 5.73 | `hscroll-confluence-dark-zh-mobile.png` |
| b1-narrow-dark-en | b1 | dark | en | populated | clean | settled | 1 | 1 | 12.23 | `b1-narrow-dark-en.png` |
| b1-narrow-light-en | b1 | light | en | populated | clean | settled | 1 | 1 | 9.68 | `b1-narrow-light-en.png` |
| b1-mixed-dark-en | b1 | dark | en | populated | clean | settled | 1 | 1 | 12.23 | `b1-mixed-dark-en.png` |
| b1-mixed-dark-zh | b1 | dark | zh | populated | clean | settled | 1 | 1 | 12.23 | `b1-mixed-dark-zh.png` |
| b1-empty-dark-en | b1 | dark | en | populated | clean | settled | 1 | 1 | 12.23 | `b1-empty-dark-en.png` |
| b1-empty-dark-zh | b1 | dark | zh | populated | clean | settled | 1 | 1 | 12.23 | `b1-empty-dark-zh.png` |
| b1-empty-light-en | b1 | light | en | populated | clean | settled | 1 | 1 | 9.68 | `b1-empty-light-en.png` |
| b1-empty-light-zh | b1 | light | zh | populated | clean | settled | 1 | 1 | 9.68 | `b1-empty-light-zh.png` |
| tri-baked-dark-en | tri-state | dark | en | populated | clean | settled | 1 | 1 | 6.14 | `tri-baked-dark-en.png` |
| tri-baked-dark-zh | tri-state | dark | zh | populated | clean | settled | 1 | 1 | 6.14 | `tri-baked-dark-zh.png` |
| tri-baked-light-en | tri-state | light | en | populated | clean | settled | 1 | 1 | 5.89 | `tri-baked-light-en.png` |
| tri-baked-light-zh | tri-state | light | zh | populated | clean | settled | 1 | 1 | 5.89 | `tri-baked-light-zh.png` |
| tri-skel-dark-en | tri-state | dark | en | no_payload | clean | settled | 1 | 1 | 6.14 | `tri-skel-dark-en.png` |
| tri-skel-light-en | tri-state | light | en | no_payload | clean | settled | 1 | 1 | 5.89 | `tri-skel-light-en.png` |
| tri-jsempty-dark-en | tri-state | dark | en | no_payload | clean | settled | 1 | 1 | 6.14 | `tri-jsempty-dark-en.png` |
| tri-jsreject-dark-en | tri-state | dark | en | no_payload | clean | settled | 1 | 1 | 6.14 | `tri-jsreject-dark-en.png` |
| tri-jsempty-dark-zh | tri-state | dark | zh | no_payload | clean | settled | 1 | 1 | 6.14 | `tri-jsempty-dark-zh.png` |
| tri-jsreject-dark-zh | tri-state | dark | zh | no_payload | clean | settled | 1 | 1 | 6.14 | `tri-jsreject-dark-zh.png` |
| grader-tip-dark-en | tips | dark | en | populated | clean | settled | 1 | 1 | 10.61 | `grader-tip-dark-en.png` |
| lead-tip-dark-en | tips | dark | en | populated | clean | settled | 1 | 1 | 11.42 | `lead-tip-dark-en.png` |
| grader-tip-dark-zh | tips | dark | zh | populated | clean | settled | 1 | 1 | 10.61 | `grader-tip-dark-zh.png` |
| lead-tip-dark-zh | tips | dark | zh | populated | clean | settled | 1 | 1 | 11.42 | `lead-tip-dark-zh.png` |
| grader-tip-light-en | tips | light | en | populated | clean | settled | 1 | 1 | 10.21 | `grader-tip-light-en.png` |
| lead-tip-light-en | tips | light | en | populated | clean | settled | 1 | 1 | 11.56 | `lead-tip-light-en.png` |
| grader-tip-light-zh | tips | light | zh | populated | clean | settled | 1 | 1 | 10.21 | `grader-tip-light-zh.png` |
| lead-tip-light-zh | tips | light | zh | populated | clean | settled | 1 | 1 | 11.56 | `lead-tip-light-zh.png` |
| m3-wait-dark-en | m3 | dark | en | populated | clean | settled | 1 | 1 | 11.42 | `m3-wait-dark-en.png` |
| m3-wait-dark-zh | m3 | dark | zh | populated | clean | settled | 1 | 1 | 11.42 | `m3-wait-dark-zh.png` |
| m3-wait-light-en | m3 | light | en | populated | clean | settled | 1 | 1 | 11.56 | `m3-wait-light-en.png` |
| m3-wait-light-zh | m3 | light | zh | populated | clean | settled | 1 | 1 | 11.56 | `m3-wait-light-zh.png` |
| sibling-usstocks-dark-en | sibling | dark | en | us_stocks_host | clean | settled | 1 | 1 | 12.23 | `sibling-usstocks-dark-en.png` |
| sibling-si-dark-en | sibling | dark | en | populated | clean | settled | 1 | 1 | 11.42 | `sibling-si-dark-en.png` |
| m6-watch-dark-en | m6 | dark | en | populated | clean | settled | 1 | 1 | None | `m6-watch-dark-en.png` |
| m6-watch-light-en | m6 | light | en | populated | clean | settled | 1 | 1 | None | `m6-watch-light-en.png` |
| m6-absent-dark-en | m6 | dark | en | empty_board | clean | settled | 1 | 1 | 11.42 | `m6-absent-dark-en.png` |
| confluence-sp500-dark-en | confluence | dark | en | populated | clean | settled | 1 | 1 | 12.23 | `confluence-sp500-dark-en.png` |
| grader-atrest-dark-en | grader-rest | dark | en | populated | clean | settled | 1 | 1 | 10.61 | `grader-atrest-dark-en.png` |
| confluence-sp500-dark-zh | confluence | dark | zh | populated | clean | settled | 1 | 1 | 12.23 | `confluence-sp500-dark-zh.png` |
| grader-atrest-dark-zh | grader-rest | dark | zh | populated | clean | settled | 1 | 1 | 10.61 | `grader-atrest-dark-zh.png` |
| flow-table-dark-zh | flows | dark | zh | populated | clean | settled | 1 | 1 | 12.23 | `flow-table-dark-zh.png` |
| board-header-dark-en | board-header | dark | en | populated | clean | settled | 1 | 1 | 11.42 | `board-header-dark-en.png` |

