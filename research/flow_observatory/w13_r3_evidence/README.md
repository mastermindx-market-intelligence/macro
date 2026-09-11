# flow_velocity W13 r3 — settled evidence matrix

Provenance: committed head `052a52d400d45b83f0aea89ecfca9438d3372a62`. Porcelain empty at capture.
S1 rig: fixture VM (no live bake), real `body.page-flow-velocity`, Playwright
localStorage seed + setTheme/setLang, `window.__skyDeck = true`, attribute
re-read refuse-on-mismatch, overlay column, SETTLE column.

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
root AND a sampled row. Header-cell contrast recorded. A cell that fails settle
is REFUSED, not captured. Reduced-motion is not the settle mechanism.

## Horizontal page scroll at 390w

- en: client=390 scroll=390 overflow=0 → none
- zh: client=390 scroll=390 overflow=0 → none

## Deleted r2 PNGs (content-addressed reconciliation)

Faded r2 cells captured mid-`fvReveal` (~15% effective contrast) are unjudgeable.
Removed in this evidence commit:

- `research/flow_observatory/w13_r2_evidence/cells/afbdb17924830a44.png`
- `research/flow_observatory/w13_r2_evidence/cells/b1ffddbbbec7f384.png`
- `research/flow_observatory/w13_r2_evidence/cells/board-head-dark-en.png`
- `research/flow_observatory/w13_r2_evidence/cells/board-head-light-en.png`
- `research/flow_observatory/w13_r2_evidence/cells/caption-zh.png`
- `research/flow_observatory/w13_r2_evidence/cells/f1f3e0fb4bc5e47f.png`
- `research/flow_observatory/w13_r2_evidence/cells/fc07d6ca1a2014fe.png`
- `research/flow_observatory/w13_r2_evidence/cells/footer-tip-light-en.png`
- `research/flow_observatory/w13_r2_evidence/manifest.json`
- `research/flow_observatory/w13_r2_evidence/README.md`

## Cells

| id | family | theme | lang | overlay | settle | root opacity | row opacity | header contrast | alias |
|---|---|---|---|---|---|---|---|---|---|
| baseline-dark-en-desktop | baseline | dark | en | clean | settled | 1 | 1 | 16.16 | `baseline-dark-en-desktop.png` |
| baseline-dark-en-mobile | baseline | dark | en | clean | settled | 1 | 1 | 16.16 | `baseline-dark-en-mobile.png` |
| baseline-dark-zh-desktop | baseline | dark | zh | clean | settled | 1 | 1 | 16.16 | `baseline-dark-zh-desktop.png` |
| baseline-dark-zh-mobile | baseline | dark | zh | clean | settled | 1 | 1 | 16.16 | `baseline-dark-zh-mobile.png` |
| baseline-light-en-desktop | baseline | light | en | clean | settled | 1 | 1 | 14.84 | `baseline-light-en-desktop.png` |
| baseline-light-en-mobile | baseline | light | en | clean | settled | 1 | 1 | 14.84 | `baseline-light-en-mobile.png` |
| baseline-light-zh-desktop | baseline | light | zh | clean | settled | 1 | 1 | 14.84 | `baseline-light-zh-desktop.png` |
| baseline-light-zh-mobile | baseline | light | zh | clean | settled | 1 | 1 | 14.84 | `baseline-light-zh-mobile.png` |
| sigma-row-lo-dark-en | sigma-row | dark | en | clean | settled | 1 | 1 | 11.1 | `sigma-row-lo-dark-en.png` |
| sigma-row-hi-dark-en | sigma-row | dark | en | clean | settled | 1 | 1 | 11.1 | `sigma-row-hi-dark-en.png` |
| sigma-row-lo-dark-zh | sigma-row | dark | zh | clean | settled | 1 | 1 | 11.1 | `sigma-row-lo-dark-zh.png` |
| sigma-row-hi-dark-zh | sigma-row | dark | zh | clean | settled | 1 | 1 | 11.1 | `sigma-row-hi-dark-zh.png` |
| sigma-row-lo-light-en | sigma-row | light | en | clean | settled | 1 | 1 | 11.56 | `sigma-row-lo-light-en.png` |
| sigma-row-hi-light-en | sigma-row | light | en | clean | settled | 1 | 1 | 11.56 | `sigma-row-hi-light-en.png` |
| sigma-row-lo-light-zh | sigma-row | light | zh | clean | settled | 1 | 1 | 11.56 | `sigma-row-lo-light-zh.png` |
| sigma-row-hi-light-zh | sigma-row | light | zh | clean | settled | 1 | 1 | 11.56 | `sigma-row-hi-light-zh.png` |
| sigma-chan-lo-dark-en | sigma-chan | dark | en | clean | settled | 1 | 1 | 9.62 | `sigma-chan-lo-dark-en.png` |
| sigma-chan-hi-dark-en | sigma-chan | dark | en | clean | settled | 1 | 1 | 9.62 | `sigma-chan-hi-dark-en.png` |
| sigma-chan-lo-dark-zh | sigma-chan | dark | zh | clean | settled | 1 | 1 | 9.62 | `sigma-chan-lo-dark-zh.png` |
| sigma-chan-hi-dark-zh | sigma-chan | dark | zh | clean | settled | 1 | 1 | 9.62 | `sigma-chan-hi-dark-zh.png` |
| counters-dark-en | counters | dark | en | clean | settled | 1 | 1 | 14.66 | `counters-dark-en.png` |
| counters-dark-zh | counters | dark | zh | clean | settled | 1 | 1 | 14.66 | `counters-dark-zh.png` |
| counters-light-en | counters | light | en | clean | settled | 1 | 1 | 17.73 | `counters-light-en.png` |
| counters-light-zh | counters | light | zh | clean | settled | 1 | 1 | 17.73 | `counters-light-zh.png` |
| rank-firstday-dark-en | rank | dark | en | clean | settled | 1 | 1 | 11.1 | `rank-firstday-dark-en.png` |
| rank-notranked-dark-en | rank | dark | en | clean | settled | 1 | 1 | 5.03 | `rank-notranked-dark-en.png` |
| rank-firstday-dark-zh | rank | dark | zh | clean | settled | 1 | 1 | 11.1 | `rank-firstday-dark-zh.png` |
| rank-notranked-dark-zh | rank | dark | zh | clean | settled | 1 | 1 | 5.03 | `rank-notranked-dark-zh.png` |
| h1-dark-en | h1 | dark | en | clean | settled | 1 | 1 | 16.16 | `h1-dark-en.png` |
| h1-dark-zh | h1 | dark | zh | clean | settled | 1 | 1 | 16.16 | `h1-dark-zh.png` |
| h1-light-en | h1 | light | en | clean | settled | 1 | 1 | 14.84 | `h1-light-en.png` |
| h1-light-zh | h1 | light | zh | clean | settled | 1 | 1 | 14.84 | `h1-light-zh.png` |
| board-cap-dark-en | board | dark | en | clean | settled | 1 | 1 | 5.57 | `board-cap-dark-en.png` |
| board-expanded-dark-en | board | dark | en | clean | settled | 1 | 1 | 5.57 | `board-expanded-dark-en.png` |
| board-cap-light-en | board | light | en | clean | settled | 1 | 1 | 7.03 | `board-cap-light-en.png` |
| board-expanded-light-en | board | light | en | clean | settled | 1 | 1 | 7.03 | `board-expanded-light-en.png` |
| board-sortreset-dark-en | board | dark | en | clean | settled | 1 | 1 | 5.57 | `board-sortreset-dark-en.png` |
| a11y-focus-dark-en | a11y | dark | en | clean | settled | 1 | 1 | 14.66 | `a11y-focus-dark-en.png` |
| degraded-trust-dark-en | degraded | dark | en | clean | settled | 1 | 1 | 14.66 | `degraded-trust-dark-en.png` |
| degraded-insuff-dark-en | degraded | dark | en | clean | settled | 1 | 1 | 11.1 | `degraded-insuff-dark-en.png` |
| degraded-trust-light-en | degraded | light | en | clean | settled | 1 | 1 | 17.73 | `degraded-trust-light-en.png` |
| degraded-insuff-light-en | degraded | light | en | clean | settled | 1 | 1 | 11.56 | `degraded-insuff-light-en.png` |

