# flow_velocity W13 r4 — packet-complete settled evidence matrix

Provenance: committed head `97ac2d1b6e5bf2c51b730d6775e29ae56aab3cd1`. Porcelain captured as the git status string.
S1 rig: fixture VM (no live bake), real `body.page-flow-velocity`, Playwright
localStorage seed + setTheme/setLang, `window.__skyDeck = true`, attribute
re-read refuse-on-mismatch, overlay column, SETTLE column, mutations column.
Each cell row carries `capture_sha` equal to this head.

## DARK TREATMENT

Command center. r1/r2 surfaces sit on the existing luminous card — hairline
`--grid`, `--card` fill, `--ink` / `--muted` / `--faint` as instrument captions.
The h1 is ink at 22px/800 (a real title, not the 11px muted eyebrow). The
See-all chip is a flat hairline control. `.fv-caption` and `.empty-why` are
muted captions. The footer is faint on a `--grid` rule; `<b>` is muted.
Monoline icons inherit currentColor (restrained glow lives on the hero card,
not the glyph). STALE chips: desaturated amber ring + dimmed body.
UNAVAILABLE: dashed border. DEGRADED/behind: amber wash + glow.

## LIGHT TREATMENT

Research workspace. Same information architecture, different material.
Paper `--card`, hairline `--line`, SHORT SHADOW instead of glow on the
See-all chip. Caption / empty-why / footer ink is mixed toward `--ink`
because `--muted`/`--faint` wash out on white. The h1 stays 22px ink, no
uppercase tracking. Footer `<b>` is `--ink` (a source label on paper, not a
faint caption). STALE: tinted paper + inset amber rule + deepened ink.
UNAVAILABLE: hatched/dashed hairline — must not read as a dirty smudge.
DEGRADED/behind: amber-tinted paper + inset rule.

## Mechanisms that INTENTIONALLY differ

1. See-all depth — dark = flat hairline chip; light = paper chip + 1px shadow.
2. Caption contrast — dark can use `--muted`/`--faint`; light deepens toward `--ink`.
3. Footer label weight — dark muted, light ink.
4. Degraded chips — dark = glow/desaturate; light = tinted paper + hatch/inset,
   never a token-swap of the glow.
Shared on purpose: spacing, type scale, chip geometry, icon stroke
(currentColor), interaction (checkbox latch, LENS `?`).

## SETTLE gate

`document.fonts.ready`, then `getAnimations({subtree:true})` empty-or-finished
on the content root (force-finish). Effective opacity == 1 on the board/content
root AND a sampled row. Header-cell contrast recorded. Weakest-text contrast in
the clipped region (chip cells include `.s-meta`) is recorded separately.
A cell that fails settle is REFUSED, not captured. Reduced-motion is not the
settle mechanism.

## Mutations (lawful force-finish; disclosed per cell)

Two settle mutations run BEFORE effectiveOpacity() is measured:

1. `.fv-reveal` classList.add(`is-in`) — force-finishes the 0.5s entrance fade
   (the same class the page adds on intersection). Recorded as
   `fv-reveal.is-in force-finish` on every cell.
2. `.lens-pop.open` `style.opacity='1'` and `style.transform='none'` — force-
   finishes the LENS popover entrance. Recorded as
   `lens-pop.open opacity=1 transform=none (opacity gate measured post-force)`
   on every cell that has an open pop at settle time (all σ-tip / footer-tip /
   rank-tip cells). For those cells the opacity gate is measured **post-force**
   (`settle.opacity_gate = post-force-lens-pop`); the host row's opacity is
   still a live ancestor-walk. This is a lawful force-finish, not a fake pass.

## Horizontal page scroll at 390w

- en: client=390 scroll=390 overflow=0 → none
- zh: client=390 scroll=390 overflow=0 → none

## Deleted prior-round evidence (content-addressed reconciliation)

r2 cells captured mid-`fvReveal` (~15% effective contrast) and the r3 42-cell
selection (missing footer/quadrant/middle-band σ) are superseded. Removed in
this evidence commit:

- `research/flow_observatory/w13_r3_evidence/cells/0562e98c7c3f7375.png`
- `research/flow_observatory/w13_r3_evidence/cells/103517a3e7d17630.png`
- `research/flow_observatory/w13_r3_evidence/cells/118744091d095727.png`
- `research/flow_observatory/w13_r3_evidence/cells/192d22aadaf1f570.png`
- `research/flow_observatory/w13_r3_evidence/cells/1c97cd4f3b0c8f74.png`
- `research/flow_observatory/w13_r3_evidence/cells/1f7ee471c3e212f2.png`
- `research/flow_observatory/w13_r3_evidence/cells/220446f1cab98b55.png`
- `research/flow_observatory/w13_r3_evidence/cells/233ee76504abb8bf.png`
- `research/flow_observatory/w13_r3_evidence/cells/2e2ab9d6c2fa76e4.png`
- `research/flow_observatory/w13_r3_evidence/cells/32883601350f913e.png`
- `research/flow_observatory/w13_r3_evidence/cells/3a0d4ab13cad94e1.png`
- `research/flow_observatory/w13_r3_evidence/cells/3ab97447a6f2bc38.png`
- `research/flow_observatory/w13_r3_evidence/cells/3f3db0814069a2df.png`
- `research/flow_observatory/w13_r3_evidence/cells/4444c6c8ef4c7c1f.png`
- `research/flow_observatory/w13_r3_evidence/cells/44598916edb10807.png`
- `research/flow_observatory/w13_r3_evidence/cells/486889450374a7c6.png`
- `research/flow_observatory/w13_r3_evidence/cells/4d0ca1f8f449565f.png`
- `research/flow_observatory/w13_r3_evidence/cells/5b5d28a5d2a428f5.png`
- `research/flow_observatory/w13_r3_evidence/cells/5e4c2602ffd0f149.png`
- `research/flow_observatory/w13_r3_evidence/cells/610be914e1672cec.png`
- `research/flow_observatory/w13_r3_evidence/cells/7354a3322342e093.png`
- `research/flow_observatory/w13_r3_evidence/cells/79d8520ac145e0eb.png`
- `research/flow_observatory/w13_r3_evidence/cells/8283806829e2fbbd.png`
- `research/flow_observatory/w13_r3_evidence/cells/83b610a6d25a1a94.png`
- `research/flow_observatory/w13_r3_evidence/cells/878bfe32fbebc864.png`
- `research/flow_observatory/w13_r3_evidence/cells/8a83e6246c630cb6.png`
- `research/flow_observatory/w13_r3_evidence/cells/8be572207887f8b4.png`
- `research/flow_observatory/w13_r3_evidence/cells/8ddd44ed76f57dfb.png`
- `research/flow_observatory/w13_r3_evidence/cells/90888c8d44f7b6bb.png`
- `research/flow_observatory/w13_r3_evidence/cells/a11y-focus-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/a180d03b7574024e.png`
- `research/flow_observatory/w13_r3_evidence/cells/ab2293c56e9cfb10.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-dark-en-desktop.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-dark-en-mobile.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-dark-zh-desktop.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-dark-zh-mobile.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-light-en-desktop.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-light-en-mobile.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-light-zh-desktop.png`
- `research/flow_observatory/w13_r3_evidence/cells/baseline-light-zh-mobile.png`
- `research/flow_observatory/w13_r3_evidence/cells/board-cap-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/board-cap-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/board-expanded-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/board-expanded-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/board-sortreset-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/c3f67b74a09eb07f.png`
- `research/flow_observatory/w13_r3_evidence/cells/cf4d31c56d962d61.png`
- `research/flow_observatory/w13_r3_evidence/cells/counters-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/counters-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/counters-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/counters-light-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/d0137b79377d2d16.png`
- `research/flow_observatory/w13_r3_evidence/cells/db24bd08ecabad13.png`
- `research/flow_observatory/w13_r3_evidence/cells/degraded-insuff-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/degraded-insuff-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/degraded-trust-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/degraded-trust-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/df2503ca7868e813.png`
- `research/flow_observatory/w13_r3_evidence/cells/e46b76bce19be2f0.png`
- `research/flow_observatory/w13_r3_evidence/cells/f55d7609b636205d.png`
- `research/flow_observatory/w13_r3_evidence/cells/f5ee0b54eaf5d9cb.png`
- `research/flow_observatory/w13_r3_evidence/cells/f64cef79696c4868.png`
- `research/flow_observatory/w13_r3_evidence/cells/fd9ba82bf9dc94d4.png`
- `research/flow_observatory/w13_r3_evidence/cells/fe0524df507bf9ca.png`
- `research/flow_observatory/w13_r3_evidence/cells/h1-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/h1-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/h1-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/h1-light-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/rank-firstday-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/rank-firstday-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/rank-notranked-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/rank-notranked-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-chan-hi-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-chan-hi-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-chan-lo-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-chan-lo-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-hi-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-hi-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-hi-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-hi-light-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-lo-dark-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-lo-dark-zh.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-lo-light-en.png`
- `research/flow_observatory/w13_r3_evidence/cells/sigma-row-lo-light-zh.png`
- `research/flow_observatory/w13_r3_evidence/manifest.json`
- `research/flow_observatory/w13_r3_evidence/README.md`

## Cells

| id | family | theme | lang | overlay | settle | opacity gate | mutations | root opacity | row opacity | header contrast | weakest contrast | alias |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline-dark-en-desktop | baseline | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 4.36 | `baseline-dark-en-desktop.png` |
| baseline-dark-en-mobile | baseline | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 4.36 | `baseline-dark-en-mobile.png` |
| baseline-dark-zh-desktop | baseline | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 4.36 | `baseline-dark-zh-desktop.png` |
| baseline-dark-zh-mobile | baseline | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 4.36 | `baseline-dark-zh-mobile.png` |
| baseline-light-en-desktop | baseline | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 4.59 | `baseline-light-en-desktop.png` |
| baseline-light-en-mobile | baseline | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 4.59 | `baseline-light-en-mobile.png` |
| baseline-light-zh-desktop | baseline | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 4.59 | `baseline-light-zh-desktop.png` |
| baseline-light-zh-mobile | baseline | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 4.59 | `baseline-light-zh-mobile.png` |
| hero-dark-en | hero | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 4.36 | `hero-dark-en.png` |
| hero-dark-zh | hero | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 4.36 | `hero-dark-zh.png` |
| hero-light-en | hero | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 5.07 | `hero-light-en.png` |
| hero-light-zh | hero | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 5.07 | `hero-light-zh.png` |
| h1-dark-en | h1 | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 5.54 | `h1-dark-en.png` |
| h1-dark-zh | h1 | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 5.54 | `h1-dark-zh.png` |
| h1-light-en | h1 | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 5.89 | `h1-light-en.png` |
| h1-light-zh | h1 | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 5.89 | `h1-light-zh.png` |
| degraded-trust-dark-en | degraded | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.66 | 5.03 | `degraded-trust-dark-en.png` |
| degraded-trust-dark-zh | degraded | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.66 | 5.03 | `degraded-trust-dark-zh.png` |
| degraded-trust-light-en | degraded | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 17.73 | 4.59 | `degraded-trust-light-en.png` |
| degraded-trust-light-zh | degraded | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 17.73 | 4.59 | `degraded-trust-light-zh.png` |
| degraded-insuff-dark-en | degraded | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.1 | 4.83 | `degraded-insuff-dark-en.png` |
| degraded-insuff-dark-zh | degraded | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.1 | 4.83 | `degraded-insuff-dark-zh.png` |
| degraded-insuff-light-en | degraded | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.56 | 5.48 | `degraded-insuff-light-en.png` |
| degraded-insuff-light-zh | degraded | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.56 | 5.48 | `degraded-insuff-light-zh.png` |
| quadrant-dark-en | quadrant | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 5.54 | `quadrant-dark-en.png` |
| quadrant-dark-zh | quadrant | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 5.54 | `quadrant-dark-zh.png` |
| quadrant-light-en | quadrant | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 4.59 | `quadrant-light-en.png` |
| quadrant-light-zh | quadrant | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 4.59 | `quadrant-light-zh.png` |
| board-cap-dark-en | board | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 5.57 | 4.83 | `board-cap-dark-en.png` |
| board-cap-dark-zh | board | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 5.57 | 4.83 | `board-cap-dark-zh.png` |
| board-cap-light-en | board | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 7.03 | 5.48 | `board-cap-light-en.png` |
| board-cap-light-zh | board | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 7.03 | 5.48 | `board-cap-light-zh.png` |
| board-expanded-dark-en | board | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 5.57 | 4.83 | `board-expanded-dark-en.png` |
| board-expanded-dark-zh | board | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 5.57 | 4.83 | `board-expanded-dark-zh.png` |
| board-expanded-light-en | board | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 7.03 | 5.48 | `board-expanded-light-en.png` |
| board-expanded-light-zh | board | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 7.03 | 5.48 | `board-expanded-light-zh.png` |
| board-sortreset-dark-en | board | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 5.57 | 4.83 | `board-sortreset-dark-en.png` |
| board-sortreset-dark-zh | board | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 5.57 | 4.83 | `board-sortreset-dark-zh.png` |
| board-sortreset-light-en | board | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 7.03 | 5.48 | `board-sortreset-light-en.png` |
| board-sortreset-light-zh | board | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 7.03 | 5.48 | `board-sortreset-light-zh.png` |
| changed-dark-en | changed | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 6.14 | `changed-dark-en.png` |
| changed-dark-zh | changed | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 16.16 | 6.14 | `changed-dark-zh.png` |
| changed-light-en | changed | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 5.89 | `changed-light-en.png` |
| changed-light-zh | changed | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.84 | 5.89 | `changed-light-zh.png` |
| southbound-dark-en | southbound | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.1 | 4.83 | `southbound-dark-en.png` |
| southbound-dark-zh | southbound | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.1 | 4.83 | `southbound-dark-zh.png` |
| southbound-light-en | southbound | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.56 | 5.48 | `southbound-light-en.png` |
| southbound-light-zh | southbound | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 11.56 | 5.48 | `southbound-light-zh.png` |
| footer-tip-dark-en | footer | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 5.54 | 5.54 | `footer-tip-dark-en.png` |
| footer-tip-dark-zh | footer | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 5.54 | 5.54 | `footer-tip-dark-zh.png` |
| footer-tip-light-en | footer | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | None | 7.03 | `footer-tip-light-en.png` |
| footer-tip-light-zh | footer | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | None | 7.03 | `footer-tip-light-zh.png` |
| sigma-row-lo-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-lo-dark-en.png` |
| sigma-row-lo-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-lo-dark-zh.png` |
| sigma-row-lo-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-lo-light-en.png` |
| sigma-row-lo-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-lo-light-zh.png` |
| sigma-row-hi-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-hi-dark-en.png` |
| sigma-row-hi-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-hi-dark-zh.png` |
| sigma-row-hi-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-hi-light-en.png` |
| sigma-row-hi-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-hi-light-zh.png` |
| sigma-row-b2-pos-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b2-pos-dark-en.png` |
| sigma-row-b2-pos-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b2-pos-dark-zh.png` |
| sigma-row-b2-pos-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b2-pos-light-en.png` |
| sigma-row-b2-pos-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b2-pos-light-zh.png` |
| sigma-row-b2-neg-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b2-neg-dark-en.png` |
| sigma-row-b2-neg-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b2-neg-dark-zh.png` |
| sigma-row-b2-neg-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b2-neg-light-en.png` |
| sigma-row-b2-neg-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b2-neg-light-zh.png` |
| sigma-row-b3-pos-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b3-pos-dark-en.png` |
| sigma-row-b3-pos-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b3-pos-dark-zh.png` |
| sigma-row-b3-pos-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b3-pos-light-en.png` |
| sigma-row-b3-pos-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b3-pos-light-zh.png` |
| sigma-row-b3-neg-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b3-neg-dark-en.png` |
| sigma-row-b3-neg-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-b3-neg-dark-zh.png` |
| sigma-row-b3-neg-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b3-neg-light-en.png` |
| sigma-row-b3-neg-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-b3-neg-light-zh.png` |
| sigma-row-hi-neg-dark-en | sigma-row | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-hi-neg-dark-en.png` |
| sigma-row-hi-neg-dark-zh | sigma-row | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 11.1 | `sigma-row-hi-neg-dark-zh.png` |
| sigma-row-hi-neg-light-en | sigma-row | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-hi-neg-light-en.png` |
| sigma-row-hi-neg-light-zh | sigma-row | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `sigma-row-hi-neg-light-zh.png` |
| sigma-chan-lo-dark-en | sigma-chan | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 9.62 | 9.62 | `sigma-chan-lo-dark-en.png` |
| sigma-chan-lo-dark-zh | sigma-chan | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 9.62 | 9.62 | `sigma-chan-lo-dark-zh.png` |
| sigma-chan-lo-light-en | sigma-chan | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 10.68 | 10.68 | `sigma-chan-lo-light-en.png` |
| sigma-chan-lo-light-zh | sigma-chan | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 10.68 | 10.68 | `sigma-chan-lo-light-zh.png` |
| sigma-chan-hi-dark-en | sigma-chan | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 9.62 | 9.62 | `sigma-chan-hi-dark-en.png` |
| sigma-chan-hi-dark-zh | sigma-chan | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 9.62 | 9.62 | `sigma-chan-hi-dark-zh.png` |
| sigma-chan-hi-light-en | sigma-chan | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 10.68 | 10.68 | `sigma-chan-hi-light-en.png` |
| sigma-chan-hi-light-zh | sigma-chan | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 10.68 | 10.68 | `sigma-chan-hi-light-zh.png` |
| sigma-chan-b2-neg-dark-en | sigma-chan | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 9.62 | 9.62 | `sigma-chan-b2-neg-dark-en.png` |
| sigma-chan-b2-neg-dark-zh | sigma-chan | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 9.62 | 9.62 | `sigma-chan-b2-neg-dark-zh.png` |
| sigma-chan-b2-neg-light-en | sigma-chan | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 10.68 | 10.68 | `sigma-chan-b2-neg-light-en.png` |
| sigma-chan-b2-neg-light-zh | sigma-chan | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 10.68 | 10.68 | `sigma-chan-b2-neg-light-zh.png` |
| counters-dark-en | counters | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.66 | 5.03 | `counters-dark-en.png` |
| counters-dark-zh | counters | dark | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.66 | 5.03 | `counters-dark-zh.png` |
| counters-light-en | counters | light | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 17.73 | 5.48 | `counters-light-en.png` |
| counters-light-zh | counters | light | zh | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 17.73 | 5.48 | `counters-light-zh.png` |
| rank-firstday-dark-en | rank | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 5.03 | `rank-firstday-dark-en.png` |
| rank-firstday-dark-zh | rank | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.1 | 5.03 | `rank-firstday-dark-zh.png` |
| rank-firstday-light-en | rank | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `rank-firstday-light-en.png` |
| rank-firstday-light-zh | rank | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 11.56 | 11.56 | `rank-firstday-light-zh.png` |
| rank-notranked-dark-en | rank | dark | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 5.03 | 5.03 | `rank-notranked-dark-en.png` |
| rank-notranked-dark-zh | rank | dark | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | 5.03 | 5.03 | `rank-notranked-dark-zh.png` |
| rank-notranked-light-en | rank | light | en | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | None | None | `rank-notranked-light-en.png` |
| rank-notranked-light-zh | rank | light | zh | clean | settled | post-force-lens-pop | fv-reveal.is-in force-finish; lens-pop.open opacity=1 transform=none (opacity gate measured post-force) | 1 | 1 | None | None | `rank-notranked-light-zh.png` |
| a11y-focus-dark-en | a11y | dark | en | clean | settled | live | fv-reveal.is-in force-finish | 1 | 1 | 14.66 | 14.66 | `a11y-focus-dark-en.png` |

