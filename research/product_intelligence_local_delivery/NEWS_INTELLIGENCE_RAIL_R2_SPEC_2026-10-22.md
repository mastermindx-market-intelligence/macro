# News Intelligence · Decision Rail · R2 — FROZEN BUILD SPEC (seat fd47d431, 2026-10-22)

Design source: Paper file "News Intelligence · Decision Rail · R2 · 2026-10-21" (artboards A rules,
D1 desktop, D1b ladder, D3 tablet, D5 mobile, S states, Z zh, L light, G guards). Exports and the
rules text live in the seat scratchpad `design_r2/export/`. This file is the only build authority for
Phase 2; the artboards are its illustration. Where the artboard and this file differ, this file wins.

Repository: `mastermindx-market-intelligence/mastermind-terminal`, default branch `master`.
BASE: `187bf9582b3deba2de49b597e29ccce6356333d3` (master 2026-10-21T22:44Z = PR #1105, the
"unavailable feeds retry in place" change). The shipped Retry button (`.retryButton`, `COPY.retry`)
is KEPT. The artboard note "no retry theatre" predates #1105 and is overruled.

All paths below are relative to `terminal/`.

## 0. What R2 changes, in one paragraph

The row's "N reports from K outlets" button becomes an **evidence ladder chip**
`kind › outlets › reports › agreement` that opens an evidence view (clocks, group note, the first two
member reports, "Show n more"). Under the ladder, a **NEXT CHECK** line tells the reader what to do
before relying on the story (four rules, first match wins, never on a 1-report row). The meta row gains
a **topic family** slot derived from the engine's annotation event type. Muted text ink moves from raw
`--muted` to `--flow-muted`. Two ZH copy fixes land (restricted, degraded). Nothing else in the rail
changes: strip, tally, catch-up bar, review tags, Mark reviewed, filters, tabs, states, Retry.

Product law (unchanged, enforced by tests): no sentiment, impact, confidence, rank, score, signal or
call. The ladder counts and compares what the engine grouped; it never says what a story means.

## 1. Contract delta (terminal-only parse; the engine already sends both fields)

`lib/newsTypes.ts` — `TickerNewsStoryRow` gains two optional fields:

```ts
publisher?: string;                              // engine publisher_identity(): a bare domain, e.g. "reuters.com"
annotation?: { event_type: string | null } | null; // engine annotate_row(); null when annotation is not permitted
```

`lib/newsValidation.ts` — `parseStoryRow` reads both; add two parsers next to `parseContentKind`:

- `parsePublisher(value)`: `undefined | null` → `undefined`; non-empty string ≤ 256 → the string
  (lower-cased, trimmed); anything else → `throw new TickerNewsContractError("row_publisher")`.
- `parseAnnotation(value)`: `undefined | null` → `null`; a plain object → `{ event_type }` where
  `event_type` is `null` when the object's `event_type` is `null`/`undefined`, the string when it is a
  non-empty string ≤ 64, else throw `TickerNewsContractError("row_annotation")`; any other value (string,
  number, array) → throw `TickerNewsContractError("row_annotation")`. Every other key of the engine's
  annotation object (figures, evidence, basis, annotator_version, derivation, schema) is ignored.

Members returned by `/api/ticker-news/stories/{id}` go through the same `parseStoryRow`, so they gain the
fields for free. `TickerNewsStory` is unchanged.

## 2. The lexicon module (new, pure): `lib/newsLadderLex.ts`

The file is FROZEN BYTE-FOR-BYTE. Both build lanes copy it from the seat-provided file (sha256 in the
packet) and never edit it. Exports: `NEWS_LADDER_LEX`, `NewsLadderKey`, `newsLadderText`,
`NEWS_TOPIC_FAMILY`, `NewsEventType`, `topicFamily`, `AGREEMENT_GLYPH`, `LadderStep`, `ladderSteps`,
`NextCheckKey`, `nextCheck`. Semantics:

- `ladderSteps(row, lang)` → `[kind, outlets, reports]` for `item_count === 1`, plus `agreement`
  (`text` + `glyph`) for `item_count > 1`. `outlets` uses `k = min(max(source_count,1), item_count)`.
- `nextCheck(row, snapshotState, members)` → `next.differ | next.limited | next.announcement |
  next.catchup | null`. Rules in order: (1) `reporting_state === "reports_differ"`;
  (2) `"comparison_limited"`; (3) `row.content_kind === "press_release"` or any loaded member is a
  press release; (4) snapshot `catching_up | degraded` and row `not_compared` (a missing
  `reporting_state` counts as `not_compared`). `item_count <= 1` → `null` before any rule.
- `topicFamily(eventType, lang)` → one of 20 families or `""` for null/unknown.
- Agreement glyphs: `=` no_material_difference, `≠` reports_differ, `~` comparison_limited,
  `–` not_compared. A glyph is never rendered without its label.

## 3. Row anatomy (`components/news/TickerNewsPanel.tsx`), top to bottom

1. **meta** (`.meta`): `NewsReviewTag` · `.source` = `sourceLabel(row.source)` (the outlet, as today,
   without the "· Press release" suffix — kind now lives in the ladder) · `.topic` = `topicFamily(...)`
   rendered ONLY when non-empty (no empty element, no separator) · `<time>` as today.
2. **headline** (`[data-news-headline]`): unchanged markup. Size: `650 13px/18px` fine pointer,
   `15px/20px` at `max-width:860px`.
3. **teaser** (`.teaser`): unchanged, plus a 2-line clamp (`display:-webkit-box; -webkit-line-clamp:2;
   -webkit-box-orient:vertical; overflow:hidden`).
4. **change since review** (`NewsReviewChange`): unchanged.
5. **ladder**:
   - `item_count > 1` → `<button type="button" class="ladder" aria-expanded={open}
     aria-label={newsLadderText(open ? "ladder.close" : "ladder.open", lang)} data-news-ladder>` whose
     visible children are the steps from `ladderSteps`, each `<span class="step" data-step={key}>`,
     separated by `<span class="sep" aria-hidden="true">›</span>`; the agreement step renders
     `<span class="glyph" data-agreement={state} aria-hidden="true">{glyph}</span>` followed by its label
     text. Click toggles the evidence view exactly as `toggleStory(row)` does today (same fetch, same
     `detailTokens`, same busy guard: `disabled` while that story's detail is in flight).
   - `item_count === 1` → `<span class="ladderStatic" data-news-ladder="static">` with the three steps,
     no border, no agreement step, not focusable.
   - The old `.sourcesButton` and its three labels (`copy.reports`, `copy.closeReports`,
     `row.outlets`) are removed from the row (`copy.reports` stays for the evidence view aria-label).
6. **evidence view** (`.evidence`, `role="group"`, `aria-label={copy.reports(detail.item_count)}`),
   rendered only while open, in this order:
   - `.clocks` row: `Published {t}` · `Updated {t}` · `Received {t}` using `newsLadderText("clock.*")`
     and `formatRailTime`; a clock whose timestamp is `null` is omitted; separators are `·`.
   - `.groupNote` = `newsFlowText("row.groupNote", lang)` (unchanged text).
   - members: the first **2** of `detail.members` as today's `.sourceLink` rows (label =
     `reportSourceLabel(member.source, member.content_kind, lang)`; when `member.publisher` is present,
     add it as the link's `title` attribute — nothing else changes).
   - when `detail.members.length > 2`: `<button type="button" class="moreReports">` with
     `newsLadderText("more.reports", lang, { n: members.length - 2 })`; clicking reveals the rest
     (local state, no fetch). Collapsing the ladder resets it.
7. **NEXT CHECK** (`.nextCheck`): when `nextCheck(row, state, detail?.members ?? null)` is non-null:
   `<p class="nextCheck" data-next-check={key}><span class="nextLabel">{newsLadderText("next.label")}</span>
   {newsLadderText(key)}</p>`. Placement: after the ladder when collapsed, after the evidence view when
   expanded; always before Mark reviewed. `state` is the snapshot state passed to the panel today.
8. **Mark reviewed** (`NewsMarkReviewed`): unchanged, always last.

Restricted / unavailable / loading / quiet / degraded / liveInterrupted / curated / filter-empty markup
is unchanged. The restricted state never shows Retry; unavailable keeps Retry (#1105 tests stay green).

## 4. Styles (`components/news/TickerNewsPanel.module.css`)

- Define on the panel root: `--flow-muted: color-mix(in srgb, var(--muted) 75%, var(--text-2)`
  (identical to NewsFlowStrip.module.css so both resolve to the same ink).
- Text ink migration: `.symbol .stateChip .source .empty .note .sourceNote .sourceLink>span:first-child
  .meta` move from `var(--muted)`/`var(--text-dim)` text color to `var(--flow-muted)`. Decorative `›`
  separators (`.sep`) use `var(--text-dim)`. Raw `var(--muted)` no longer colours any text in this file.
- `.ladder`: inline-flex, `height:24px`, `padding:0 8px`, `gap:6px`, `border:1px solid var(--line)`,
  `border-radius:6px`, `background:transparent`, `color:var(--text-2)`, `font:600 10.5px/1 var(--font-ui)`,
  `margin-top:7px`, cursor pointer; hover `background:color-mix(in srgb,var(--brand) 8%,var(--panel-2))`;
  `:focus-visible{outline:2px solid var(--brand-2);outline-offset:2px}`; `[aria-expanded="true"]`
  `border-color:var(--brand-2)`. Agreement colours by `data-agreement`: `no_material_difference`
  `var(--text)`, `reports_differ` `var(--warn)`, `comparison_limited` `var(--text-2)`, `not_compared`
  `var(--flow-muted)` (glyph and label together).
- `.ladderStatic`: same typography, no border/background/padding, `color:var(--flow-muted)`, margin-top 7px.
- `@media (max-width:860px), (pointer:coarse)`: `.ladder{min-height:40px;height:auto;padding:6px 10px;
  flex-wrap:wrap}`; `.headline{font-size:15px;line-height:20px}`; `.moreReports{min-height:44px}`.
- `.evidence`: today's `.sourceList` box (top border `var(--line-2)`, gap 5px, padding-top 6px).
  `.clocks{display:flex;flex-wrap:wrap;gap:6px;color:var(--flow-muted);font:600 10px/1.3 var(--font-ui);
  font-variant-numeric:tabular-nums}`.
- `.nextCheck{margin:6px 0 0;color:var(--text-2);font:500 12px/16px var(--font-ui)}`
  `.nextLabel{display:block;color:var(--flow-muted);font:700 10px/13px var(--font-ui);
  letter-spacing:.08em;text-transform:uppercase}` (ZH: no uppercase effect, same box).
- `.topic{color:var(--text-2);font-weight:600}`.
- `.moreReports`: same visual as today's `.sourcesButton` (brand-2 text, no border), 24px tall on fine pointer.
- Never add a coloured left edge or accent stripe to any container (Chairman rule 2026-10-18).

## 5. Copy fixes in `COPY` (TickerNewsPanel.tsx)

- zh `restricted`: `此账户或新闻源当前不可用。` → `此账户或新闻源暂无新闻访问权限。`
- zh `degraded`: `实时更新降级，显示最近一次已验证读取。` → `实时更新降级，显示最近一次已核实读取。`
- Remove `closeReports` (both langs). Keep every other key, including `retry`.

## 6. Tests (named; vitest, `terminal/`)

Lane L1 (lib):
- `lib/__tests__/newsLadderLex.test.ts` (new):
  1. every `NEWS_LADDER_LEX` and `NEWS_TOPIC_FAMILY` entry is a bilingual tuple of non-empty strings;
  2. `topicFamily` over ALL 23 event classes pins the exact EN and ZH family strings (table), and
     `null`, `undefined`, `""`, `"not_a_class"` → `""`; the distinct EN families number 20;
  3. `ladderSteps`: (n=1,k=1) → 3 steps, no agreement; (n=2,k=1) → "1 outlet"/"2 reports" + agreement;
     (n=5,k=3) → "3 outlets"; (n=3,k=9) clamps to "3 outlets"; (n=2,k=0) → "1 outlet"; glyph/label
     pairs for all four states; `content_kind: "press_release"` → "Company announcement"; ZH mirrors;
  4. `nextCheck` table: n=1 with reports_differ → null; reports_differ → next.differ; comparison_limited
     → next.limited; not_compared + press_release row → next.announcement; not_compared + reporting row +
     press-release member → next.announcement; not_compared + catching_up → next.catchup; not_compared +
     degraded → next.catchup; not_compared + live → null; missing reporting_state behaves as
     not_compared; precedence: reports_differ + press_release → next.differ;
  5. banned vocabulary: the EN (23 terms, word boundary, case-insensitive) and ZH (22 terms, substring)
     lists from `newsFlowLex.test.ts` over every string in both tables, including every filled
     `{n?one|many}` branch.
- `lib/__tests__/newsFlowContract.test.ts` (extend): `parseStoryRow` accepts a row without
  `publisher`/`annotation` (fields `undefined`/`null`), with `publisher: "Reuters.com "` → `"reuters.com"`,
  with `annotation: null`, with `annotation: { event_type: "guidance_cut", figures: {} }` →
  `{ event_type: "guidance_cut" }`, with `annotation: { event_type: null }` → `{ event_type: null }`;
  rejects `publisher: 7` (`row_publisher`), `annotation: "x"` and `annotation: { event_type: 3 }`
  (`row_annotation`).

Lane L2 (UI):
- `lib/__tests__/tickerNewsPanel.test.tsx` (extend, keep every existing case green):
  1. a 3-report row renders `[data-news-ladder]` as a button with `aria-expanded="false"` and the
     steps "Reporting › 3 outlets › 3 reports › Reports agree" (text content, separators included);
  2. a 1-report row renders `[data-news-ladder="static"]`, no button, no `[data-next-check]`;
  3. one case per reporting state asserting `[data-agreement]` and the label text;
  4. NEXT CHECK: reports_differ → `[data-next-check="next.differ"]` with the EN line; comparison_limited;
     press_release row; catching_up snapshot + not_compared; live + not_compared → no `[data-next-check]`;
  5. clicking the ladder fetches the story, sets `aria-expanded="true"`, shows `.clocks` with Published/
     Updated/Received (a null `updated_at` omits Updated), the group note, exactly 2 members and
     "Show 1 more report" for a 3-member detail; clicking it shows the third; the NEXT CHECK line is
     after the evidence view and before Mark reviewed (DOM order);
  6. a row with `annotation.event_type: "guidance_cut"` shows `.topic` "Guidance"; a null event type
     renders no `.topic` element;
  7. ZH: the same 3-report row reads "媒体报道 › 3 家媒体 › 3 条报道 › 报道一致"; restricted shows
     `此账户或新闻源暂无新闻访问权限。` and no Retry; unavailable shows 重试.
- `lib/__tests__/newsFlowSpecimen.test.tsx`: regenerate with `WRITE_SPECIMEN=1` only if the specimen
  content changes; commit the regenerated `docs/specimens/news-flow.html` when it does.
- `npx tsc --noEmit -p .` and `npm run lint` clean; `npm test` fully green.

Lane L3 (e2e, after L1+L2 are on master): extend `e2e/news-flow-responsive.spec.ts` with a ladder
cell per project × lang (collapsed, expanded, NEXT CHECK, static 1-report) captured to the crops dir;
crops committed under `docs/pr-crops/news-r2/`. Specified in its own packet later.

## 7. Evidence matrix (what the seat judges before merge)

| cell | viewport | lang | what must be visible |
|---|---|---|---|
| R1 | 1440 | en | collapsed row: meta with topic, 13/18 headline, ladder chip 24px, NEXT CHECK, Mark reviewed |
| R2 | 1440 | zh | same row in ZH |
| R3 | 1440 | en | expanded: clocks, group note, 2 members, Show n more, NEXT CHECK below, Mark reviewed last |
| R4 | 768 | en | ladder chip ≥40px tall, wraps cleanly |
| R5 | 390 | zh | 15/20 headline, 40px chip, 44px Mark reviewed |
| R6 | 1440 | en | 1-report row: static chain, no NEXT CHECK |
| R7 | 1440 | en | restricted (no Retry) and unavailable (Retry) states |

Unit tests are the gate for L1/L2; the cells are produced by L3 and checked by the seat in the browser.

## 8. Ownership

| lane | owned files (exclusive) |
|---|---|
| L1 | `lib/newsTypes.ts`, `lib/newsValidation.ts`, `lib/__tests__/newsLadderLex.test.ts`, `lib/__tests__/newsFlowContract.test.ts`, plus the verbatim copy of `lib/newsLadderLex.ts` |
| L2 | `components/news/TickerNewsPanel.tsx`, `components/news/TickerNewsPanel.module.css`, `lib/__tests__/tickerNewsPanel.test.tsx`, `docs/specimens/news-flow.html` (regen only), plus the verbatim copy of `lib/newsLadderLex.ts` |
| L3 | `e2e/news-flow-responsive.spec.ts`, `docs/pr-crops/news-r2/**` |

`lib/newsLadderLex.ts` is created identically by L1 and L2 (same bytes → clean merge), and the
two-line `lib/newsTypes.ts` delta (§1) is applied identically by both lanes from the seat-provided
file (same bytes → clean merge). The sha256 of both resulting files is pinned in each packet; a lane
whose copy differs is not done. Nobody edits `.github/**`, `NewsCatchup*`, `NewsFlowStrip*`,
`newsFlowLex.ts`, `newsDisplay.ts`.

## 9. NOT DONE UNLESS (applies to every lane)

- HEAD of the lane tree equals BASE before the first edit; the lane branch has only the lane's commits.
- `npm ci` in `terminal/`, then `npm test` green, `npx tsc --noEmit -p .` clean, `npm run lint` clean,
  with the tails pasted in the return.
- Every named test exists, is listed by name in the return with its pass line, and FAILS when the
  behaviour it pins is reverted (one deliberate revert receipt per lane: L1 reverts rule order in a
  scratch copy and shows the table test red; L2 reverts the static-chain branch and shows test 2 red).
- Commits end with the two trailer lines exactly as the packet states.
- Lanes never push, fetch, merge, rebase, reset, stash or run `gh`. The seat pushes the lane branch
  (`claude/news-r2-<lane>`) and opens the DRAFT PR against `master` itself, from the lane tree, after
  judging the return by artifact.
- The return file exists and ends with the lane's sentinel line.
