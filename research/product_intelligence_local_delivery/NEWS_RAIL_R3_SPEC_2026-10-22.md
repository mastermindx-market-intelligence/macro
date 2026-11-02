# News rail R3 — frozen spec (Typographic ledger)

Seat fd47d431 · 2026-10-22 · FROZEN. Base: master after terminal #1128 (L3 e2e cells + crops) and
#1129 (L4 ladder-owns-its-line fix + rev4 P1 asserts). Design source: `terminal/docs/design/news-r3/boards/A.html`
on branch `claude/news-r3-design` (PR #1130) — direction A, judged by the seat from the 36 crops.
Direction B is rejected (fixed columns split words at 360 px). Direction C's serif is not adopted;
after review at 360 px no C graft is taken — A's compositions stand as one system.

R3 changes PRESENTATION ONLY. Every string, every `data-*` hook, the lexicon module
(`lib/newsLadderLex.ts`), the ladder step computation, the NEXT CHECK rules, the `aria-*`
contract, the catch-up controls and the restricted/unavailable/degraded states keep their R2
meaning and text. The R2 spec (`NEWS_INTELLIGENCE_RAIL_R2_SPEC.md`) §1, §2, §3 (content and
order), §5 and §6 remain in force; this document replaces §3's visual treatment, §4 and §7.

## 1. Thesis and the five ink roles

The row is a typeset ledger entry: hierarchy is carried by type scale, weight, width and
tabular numerals. There is no box inside the rail: no chip border, no evidence card, no fill
behind NEXT CHECK. Rows are separated by one hairline (`--line-2`). No row hover fill.

| role | token | used for |
|---|---|---|
| ledger-text | `--text` | headline; the `=` agree step |
| ledger-body | `--text-2` | teaser, outlet/report counts, clock values, member titles, NEXT CHECK line |
| ledger-label | `--flow-muted` | meta row, clock labels, static ladder, NEXT CHECK label |
| ledger-accent | `--brand-2` | links, "Show n more", focus ring, New tag |
| ledger-state | `--warn` | the `≠` differ step (glyph + label together), Updated tag |

Separators `›` and `·` stay `--text-dim` and `aria-hidden`. State is never colour-alone.
Light `--warn` must resolve to `#7d5922` where the rail renders on white (the shared-shell
light value fails 3:1); if the shared shell does not already supply it, set it on `.board`
for light only. Doctrine: no accent edge on any container, any side.

## 2. Row anatomy (TickerNewsPanel.tsx; content and order unchanged from R2 §3)

1. **meta** — tag · publisher · topic · time, left to right, `flex-wrap:wrap`, gap 7 px, 9.5 px caps
   `.09em` `--flow-muted`. Time is `white-space:nowrap` and never breaks; the topic may wrap.
   The right-justified time column of board A is DROPPED (collides with ZH topics at tablet).
   Tags: if `.tag` is owned by `TickerNewsPanel.module.css`, restyle to the ledger word form
   (no pill: caps 9.5 px, New `--brand-2`, Updated `--warn`, Reviewed `--flow-muted`); if the
   tag class lives in another module, leave the pill and report it under DEVIATIONS.
2. **headline** — `650 15px/21px var(--font-ui)`, `letter-spacing:-.008em`, `--text`, at ALL
   widths (R2's 13/18 fine-pointer size is retired; the coarse rule becomes the only rule).
3. **teaser** — unchanged: 2-line clamp, 12.5/18.5, `--text-2`, margin-top 6.
4. **review change** — unchanged string, 11/15 `--flow-muted`, margin-top 6.
5. **ladder** — the sentence itself is the control. Button and static variants:
   `display:flex; flex-wrap:wrap; width:fit-content; max-width:100%; gap:0 6px; margin-top:9px;
   padding:0; border:0; background:transparent; min-height:24px; font:600 12px/17px var(--font-ui)`.
   The ladder NEVER clips: steps are `white-space:nowrap` and the sentence wraps at step
   boundaries (board A's `– Not comp…` clip is a defect this spec forbids). Static (1-report)
   rows: `--flow-muted`, no affordance. Button rows: counts `--text-2`, kind `--flow-muted`,
   agreement step `700` in `--text` (`=`), `--warn` (`≠`), `--text-2` (`~`, `–`); a persistent
   underline on the button sentence only (`text-decoration:underline; text-decoration-color:
   var(--line-3); text-underline-offset:3px`) so the control is visible without a box; hover
   switches the underline colour to `--brand-2`; `:focus-visible` is the shipped 2 px `--brand-2`
   outline at offset 3. Coarse pointer / ≤860 px: `min-height:40px`, 13/18.
6. **evidence view** — an open block, `margin-top:11px; padding-top:9px; border-top:1px solid
   var(--line-2)`, no fill, no radius. Inside, in this order (R2 §3.6, now also e2e-pinned):
   - clocks: a two-column grid `grid-template-columns:max-content minmax(0,1fr); column-gap:14px;
     row-gap:4px`; labels 9.5 px caps `.09em` `--flow-muted`; values `500 12px/14px var(--font-num)`
     tabular `--text-2`. A null clock omits its row (unchanged rule).
   - group note: 11/15.5 `--text-2`, margin-top 9.
   - members: grid `grid-template-columns:88px minmax(0,1fr); column-gap:10px; row-gap:7px`;
     publisher 9.5 px caps `--flow-muted`; title 12/16 `--text-2` (link colour `--brand-2` on
     hover only). ZH: publisher column 72px.
   - "Show n more": underlined text in `--brand-2`, 12/17, no box, `min-height:24px` (44 coarse).
7. **NEXT CHECK** — label above line, whitespace only: label `700 9.5px/13px` caps `.12em`
   `--flow-muted`; line `600 12.5px/17px` `--text-2`; margin-top 10. Placement rules unchanged.
8. **Mark reviewed** — always last and always on its own line (the L4 rule: the ladder is
   block-level, so the control never shares the ladder's line). `NewsMarkReviewed` keeps its
   module; if `.markOne` is owned by `NewsCatchup.module.css`, restyle it there to the quiet
   ledger control: `1px solid var(--line)` border, radius 6, padding 0 10px, `min-height:26px`
   (44 coarse), `650 10.5px var(--font-ui)` `--text-2`, margin-top 10, hover border `--line-3`.

States beside the rail (restricted, unavailable + Retry 44 px, degraded note) are unchanged in
text and placement; the degraded note keeps the shipped tinted full-width fill (a fill, not an edge).

## 3. Styles (TickerNewsPanel.module.css) — what the diff may touch

Rewrite only `.meta .source .tag .headline .teaser .ladder .ladderStatic .step .sep .evidence
.clocks .groupNote .sourceLink .moreReports .nextCheck .nextLabel` and the two media blocks.
`.board .bar .heading .title .symbol .liveDot .stateChip .scroll .row .empty .retryButton
.restricted .note .sourceNote .viewControl .coverageNote .editorialTag` are unchanged, except
`.row` loses its hover fill and `.row:focus-within` keeps nothing. Remove the row hover rule.
`fin.css` and `shared-shell.css` are untouched. Motion: none. `prefers-reduced-motion`: nothing to gate.

## 4. Tests (owned)

- `lib/__tests__/tickerNewsPanel.test.tsx` and `tickerNewsA11y.test.tsx`: all existing
  assertions must keep passing unchanged EXCEPT geometry pins that name R2 numbers (24 px chip,
  13/18 headline); update those pins to the R3 numbers in the same commit and list each
  changed assertion by name in the RETURN.
- `e2e/news-flow-responsive.spec.ts` R2 block: the cells stay; their pinned geometry moves to
  R3 (headline 15/21 at all projects; ladder `min-height` 24 fine / ≥40 coarse measured as
  `getBoundingClientRect().height ≥` not `===`); add the sixth fixture `ev2_r3_limited`
  (2 outlets / 2 reports, `reporting_state: "comparison_limited"`, reporting, benzinga.com,
  `event_type: null`) and pin its ladder text (`Reporting › 2 outlets › 2 reports › ~ Comparison
  limited` / ZH mirror); add a `wrap cell`: at mobile the press row's ladder has
  `scrollWidth <= clientWidth` and its bounding box right edge ≤ the panel's right edge − 11.
- Crops: regenerate `docs/pr-crops/news-r2/*.png` from the run (same names) plus
  `R3-<project>-<lang>-limited.png`; README updated.

## 5. Evidence matrix (what the seat judges before merge)

| row | viewport | lang | must show |
|---|---|---|---|
| E1 | 1440 | en | collapsed agree row: headline 15/21, ladder sentence underlined, no chip border, no row hover fill |
| E2 | 1440 | zh | same, ZH strings; meta row wraps the topic, never the time |
| E3 | 1440 | en | expanded differ row: hairline-topped evidence block, clock grid, group note, member grid, "Show 1 more report", NEXT CHECK label/line, Mark reviewed last on its own line |
| E4 | 820 | en | press row: ladder wraps at a step boundary, nothing clipped, `– Not compared` fully visible |
| E5 | 390 | zh | agree row: 15/21 headline, ladder ≥40, Mark reviewed ≥44 and on its own line |
| E6 | 1440 | en | limited row: `~ Comparison limited` in `--text-2`, no NEXT CHECK under live |
| E7 | 1440 | en | restricted / unavailable unchanged |

Receipts: computed contrast of the five ink roles on `--panel` in both themes (≥4.5 body, ≥3
labels); product-law grep on added lines empty; accent-stripe grep empty.

## 6. Ownership

Build lane owns: `components/news/TickerNewsPanel.module.css`, `components/news/TickerNewsPanel.tsx`
(className and structure changes only; no copy, lexicon, state or data changes),
`components/news/NewsCatchup.module.css` (`.markOne` and `.tag` rules only, if owned there),
`lib/__tests__/tickerNewsPanel.test.tsx`, `lib/__tests__/tickerNewsA11y.test.tsx`,
`e2e/news-flow-responsive.spec.ts`, `docs/pr-crops/news-r2/`. Nothing else.

## 7. NOT DONE UNLESS

STEP-0 recorded; §2 items 1–8 implemented with the stated numbers; §3 untouched classes untouched
(`git diff` receipt); §4 tests green (`npx vitest run lib/__tests__/tickerNewsPanel.test.tsx
lib/__tests__/tickerNewsA11y.test.tsx` and the R2 block + wrap cell + limited cell via playwright,
tails pasted); `npx tsc --noEmit -p .` rc=0; crops regenerated and E1–E7 named to files; contrast,
product-law and stripe receipts pasted; one commit on the lane branch, porcelain 0, pushed.
