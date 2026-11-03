# Native clone and theme adaptation

**Assessment:** all four authored dark/light pairs are structurally identical. Step keys, parent references, element/tag order, dimensions, spacing, typography, borders’ widths/styles and all other non-color styles match. Data is unchanged. The source packet is SHA256 `163c42de68b7e5f630ef5e4f36b16cec639cb969096cc8e4ac29f351de4c7d92`.

This establishes that cloning can be exact **if the actual Paper clone tree can be mapped reliably**. It does not assume that the importer’s native node tree is identical to the HTML DOM. No native IDs or Paper effects are asserted here.

## Minimal strategy

1. Complete and visually check a dark reference. Clone that actual artboard through the qualified `duplicate_nodes` tool. Preserve the observed clone response and inspect the resulting clone’s native structure/IDs and canvas placement.
2. Map the 16 exact color roles below only within the new clone. Batched `update_styles` may group actual nodes sharing an identical required style change. Preserve border width/style and recolor the existing edge; do not add borders. Do not modify design tokens globally.
3. Replace only the observed clone roots for Macro `history-chart`, Company `history-chart`, and Options `expiry-summary` using the corresponding **light** input groups. This conservative choice avoids assuming how native SVG fill/stroke descendants are represented. It also recolors the explanatory text inside those three groups without altering data or geometry.
4. Patch the six text exceptions below and their corresponding layer names. Rename each artboard to its light name. Preserve all other text and geometry.
5. Read back native text/styles, capture the finished light artboard, and compare with the dark construction and light input. Check every semantic role, neutral selected fill, controls/edges, SVG legends, chart values and Chinese glyphs. Keep `height: fit-content` and preserve the native final geometry unless a real defect requires a separately recorded correction.

If the clone response/read APIs cannot establish a complete native target map, use the existing incremental light input. A guessed ID, blanket background override or color change to shared tokens is not equivalent.

## Exact color map

| Role | Authored dark value | Resolved dark | Light |
| --- | --- | --- | --- |
| Canvas / reversed glyph | `var(--noir-canvas)` | `#080808` | `#f6f6f3` |
| Rail | `var(--noir-sidebar)` | `#0c0c0c` | `#efefec` |
| Panel | `var(--noir-panel)` | `#121212` | `#ffffff` |
| Raised | `var(--noir-raised)` | `#191919` | `#f0f0ed` |
| Selected | `var(--noir-selected)` | `#292929` | `#e2e2dc` |
| Primary text / brand fill | `var(--noir-text-primary)` | `#f3f3f3` | `#1a1c20` |
| Secondary text | `var(--noir-text-secondary)` | `#b8b8b8` | `#51555b` |
| Quiet text | `var(--noir-text-tertiary)` | `#949494` | `#5f6368` |
| Accent / series 1 | `var(--noir-champagne)` | `#c9b99b` | `#66543b` |
| Neutral line | `#343434` | `#343434` | `#cbccc7` |
| Control edge | `#6f6f6f` | `#6f6f6f` | `#85877f` |
| Positive / series 3 | `#b0d4b9` | `#b0d4b9` | `#256341` |
| Link / series 2 | `#a7c9f1` | `#a7c9f1` | `#235b8e` |
| Negative / series 5 | `#efa6ad` | `#efa6ad` | `#a62d43` |
| Estimated sell / series 4 | `#d9a6ef` | `#d9a6ef` | `#7c3d9b` |
| Estimated buy | `#70cbdc` | `#70cbdc` | `#18687c` |

The mapping is unambiguous both as authored variables and after resolving the known dark tokens. `transparent` stays transparent. `#fff` in the JSON equals `#ffffff`; normalize native hex/rgb representations before matching. Color roles are shared visual roles, not a claim that Options side and Company series have the same domain meaning.

## Text and vector exceptions

| Consumer | Text changes | Group replacement |
| --- | --- | --- |
| Macro | `F02 / MACRO / DARK` → `F02 / MACRO / LIGHT` | `history-chart` |
| Company | `F02 / COMPANY / DARK` → `F02 / COMPANY / LIGHT` | `history-chart` |
| Options | `F02 / OPTIONS / DARK` → `F02 / OPTIONS / LIGHT` | `expiry-summary` |
| Editorial | Artifact label DARK → LIGHT; `Research · Tools · Learn` → `研究 · 工具 · 学习`; `Home / Blog / Compound Growth for Traders` → `首页 / 研究札记 / Compound Growth for Traders` | None |

These six changed text nodes also change their authored `layer-name`. The rest of the article, all numbers, dates, periods, units and source annotations are identical.

## Files and call reduction

`clone-theme-plan.json` is the compact plan. `clone-theme-assessment.json` contains every differing property with its input step and DOM path. `assess_clone_theme.py` regenerates the comparison and fails on any structural or non-color style difference.

The full construction has 292 HTML insertion steps. Constructing four dark boards requires 146 of those; cloning and a verified theme patch avoids rebuilding the other 146. The additional calls depend on the actual native clone mapping and safe batching, so no fixed native-call count is asserted.

I retained the existing Macro decomposition. Its longer 49-step sequence includes a real docked evidence receipt with separate fields and rows. Combining it into a single card would conflict with the one-visual-group construction guidance. Cloning offers the larger reduction without changing the verified information hierarchy.
