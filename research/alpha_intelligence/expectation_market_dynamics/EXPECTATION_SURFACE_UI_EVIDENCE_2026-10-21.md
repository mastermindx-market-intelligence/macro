# Expectation Surface UI — build evidence (BUILD-UI R1, 2026-10-21)

Lane `itp-es-build-ui-20261021-r1` implementing the accepted R1 design of the
Expectation Surface page on PR branch `claude/itp-expectation-surface-2026-10-21`.
Every claim below has an artifact: a command, a test, or a PNG in
`evidence/es_ui_2026-10-21/`.

## Identity

| Item | Value |
|---|---|
| Base (wave-1 PR head, verified by `git merge --ff-only`) | `ff28fc1bb11607ef402ea6dada1dbc94948b31a9` |
| Worktree start HEAD (before ff) | `5c6fdb2ed1f013ffc008fde904e3be72b4524873` |
| origin/main observed at | `80854549f4cda657ad706c0851512fabb5f6a10b` (main has moved past 5c6fdb2e; never merged here) |
| Branch | `lane/itp-es-build-ui-20261021-r1` (local) → pushed to `claude/itp-expectation-surface-2026-10-21` |
| Owned files changed | `templates/expectation_surface.html.j2`, `tests/test_build_expectation_surface.py`, this evidence dir |

## Build timing (real data, exact call)

Call: `from scripts.build_expectation_surface import build; build(write=True)` —
identical to the registration block at `scripts/build_site.py:8415-8416`.

- Elapsed: **4.06 s** (budget < 60 s)
- State: **LIVE**, `reasons: []`
- summary.json: `state: LIVE`; census 687,456 observations / 1,508 securities /
  2 metrics / 4 horizons (`0q +1q 0y +1y`) / 64 sessions / span 2026-08-25 →
  2026-10-21 (8 weeks); identity `COMPLETE_DEGRADED` (1,504 resolved,
  4 unresolved, 1,501 undated aliases); 108 breadth rows (54 compared sessions × 2
  metrics); movers 25/side/metric; exclusions rollover 3,967 / missingness 1,065 /
  zero-prior 2.

## Tests

`python -m pytest tests/test_build_expectation_surface.py -q`

- Baseline (wave-1 head): **18 passed** in 3.14 s.
- Final: **22 passed** in ~4.1 s — the 18 originals plus 4 new UI-contract tests.
  - One original test (`test_template_has_six_ids_in_order_and_four_chips`) had
    two assertions from the wave-1 no-style skeleton contract (`"<style" not in
    src`, `"style=" not in src`) that the ACCEPTED design supersedes by
    construction (§7 mandates a page style block; §6.5/§6.6 mandate
    custom-property style attributes). It now asserts the accepted design's
    equivalents (see DEVIATIONS D1). No test was deleted; none was weakened.

New tests: `test_ui_contract_style_tokens_and_ids` (frozen ids exactly once,
tokens under `body.page-es` only, no color literals outside the style block,
style attributes bind custom properties only),
`test_ui_contract_strings_json_and_language` (`#es-strings` parses, equal EN/ZH
key sets, no 申报, 披露 present), `test_ui_contract_horizon_labels` (G1 map in
radios + string table), `test_ui_offline_page_renders_every_section_and_band`.

## §13 Builder visual-evidence checklist

Served `site/` with `python3 -m http.server 8765 --directory site`; screenshots
via Playwright/Chromium driving the site's own toggles (`window.setTheme`,
`window.setLang` — the theme.js localStorage/attribute mechanism). All shots are
full-page unless noted. Each < 600 KB (four 1440 shots palette-quantized; the
rest native).

### Core matrix (8 required) — all DONE

| Shot | File | Verified |
|---|---|---|
| 1440 dark EN vs board | `es_1440_dark_en.png` (1440×3214) | Done |
| 1440 light EN | `es_1440_light_en.png` | Done |
| 1440 dark ZH (upgrades red) | `es_1440_dark_zh.png` | Done — `.es-bar-up` computes `rgb(224,100,100)` = `#e06464` (red) under `data-lang=zh` |
| 1440 light ZH (light ZH inks) | `es_1440_light_zh.png` | Done |
| 390 dark EN | `es_390_dark_en.png` (390×7110) | Done — no horizontal scroll (`scrollWidth 390`) |
| 390 light EN | `es_390_light_en.png` | Done |
| 390 dark ZH | `es_390_dark_zh.png` | Done |
| 390 light ZH vs board | `es_390_light_zh.png` (390×4968) | Done |

Per-core-shot confirmations (checked programmatically on the live page):
- No container has a one-sided colored edge/stripe: warn/ok/neutral chips carry
  even 1px borders on all four sides (`.es-chip--warn` computed `border-left-width: 1px`
  with the same `--es-warn-line` color as the other three sides).
- Hero answer + 4 chips present; one `h1` per page.
- "Sorted by magnitude · descriptive" visible in the movers head.
- Strip: newest column tagged "Latest/最新"; ZH upgrades render red (token flip).
- Tile values are mono; unknown renders "—", never 0 (offline tiles are
  `—` + "Not available while offline").
- No horizontal scroll at 390 (and none at 1440).
- Nav is the shared `_site_nav` family, unchanged (packet law; not restyled).
- ZH shots: `grep 申报` on the built HTML = 0; 披露 present in the identity
  region's accessible name (`data-a-zh="身份披露"`).

### State shots

| Item | File | Result |
|---|---|---|
| OFFLINE full page (observations path → missing fixture file) | `es_1440_dark_en_offline.png` | Done — offline band renders, all six section ids present, tiles "—" |
| STALE hero (rendered_at faked 12 days after latest session) | `es_1440_dark_en_stale_hero.png` | Done — chip reads "Snapshot is 12 days old / 快照已有 12 天" |
| Identity disclosure collapsed at 390 / expanded after tap | `es_390_light_zh_id_collapsed.png`, `es_390_light_zh_id_expanded.png` | Done — collapsed by default at <768, tap flips `aria-expanded` |
| Explorer loading (ticker request held) | `es_1440_dark_en_loading.png` | Done — skeleton + `aria-busy="true"` + "Loading LBRT estimates" |
| Explorer error (ticker request blocked) | `es_1440_dark_en_error.png` | Done — error card + visible Retry |
| No match "MUU" + Enter | (programmatic; see below) | Done — nomatch block shown: "No ticker matches “MUU”. The surface covers 1,508 matched securities; 4 vendor names are not matched yet." |
| Listbox open "M" | (programmatic) | Done — 8 options, note "8 matches. Arrow keys move, Enter opens, Esc closes." |
| Movers empty fixture | `es_1440_dark_en_movers_empty.png` | Done — "No moves between sessions" + switch hint |
| Keyboard focus: mover row ring | `es_1440_dark_en_kbd_focus.png` | Done — `2px solid rgb(122,167,224)` (`--link`), offset 2 |
| Keyboard: chart, ArrowLeft ×2 | `es_1440_dark_en_kbd_chart.png` | Done — selection 2026-10-21 → 2026-10-07, readout + live region updated |
| "All {n} compared sessions" + "Show {n} more" expanded | `es_1440_dark_en_expanded.png` | Done — 54 breadth rows and 25 mover rows visible |
| Method at 390 ("What this is not" open, others closed) | `es_390_light_zh_method.png` | Done — accordion states `[false, false, true]` |

### Interaction proof

- Mover row click opens the row in the explorer (`open(T, {from:'row'})`,
  `history.replaceState('?t=T#es-explorer')`, scroll + focus `#es-card-t`); deep
  link `?t=NKE` renders the NKE card (verified programmatically).
- Quick pick swaps the series (KSS → LBRT → INSW shots/flow verified).
- Metric/horizon radios re-render with **0 fetches** (network listener empty
  across radio changes).
- Language toggle switches every visible string (dual-span `display` flip) and
  the aria-labels (`data-a-en/zh` reapplied on `langchange`) **without a reload**
  (`performance navigation` entry count unchanged).
- Theme toggle recolours the SVG **without a redraw**: `#es-chart-svg` DOM byte
  count and child count identical across `setTheme('dark'→'light')` while the
  average-line stroke changes `rgb(91,155,240)` → `rgb(47,99,196)`.

## §12 Accessibility checklist — all verified

- [x] Exactly one h1; five panels each with an h2 referenced by `aria-labelledby`;
      side titles/method columns h3; explorer ticker is an h3 with `tabindex=-1`.
- [x] Focus: 2px solid `--link`, offset 2, on controls/rows/summary/chart
      (measured on a mover row and the chart under keyboard focus); combobox ring
      on `:focus-within`; radio ring on `+ span`.
- [x] Segmented controls are native radio groups with visually hidden legends
      ("Metric/指标" ×3, "Horizon/期限").
- [x] Combobox WAI-ARIA 1.2: `role=combobox`, `aria-expanded`, `aria-controls`,
      `aria-activedescendant`, `listbox`/`option` + `aria-selected`, polite status.
- [x] Chart: focusable, `aria-labelledby=es-chart-cap`, `aria-describedby=es-kbd-hint`,
      Arrow/Home/End work, polite live summary on keyboard moves (250 ms debounce),
      SVG `aria-hidden`, "Show the numbers" table.
- [x] Breadth: sr sentence per column; counts table has caption + `scope=col/row`.
- [x] Mover rows are `<button>`s; visual cells `aria-hidden`; sr sentence starts
      with the ticker.
- [x] Identity disclosure: button `aria-expanded`/`aria-controls`; region labelled
      "Identity disclosure" / 身份披露.
- [x] No hover-only information (chart pointer selection has click + keys; readout
      always shows values).
- [x] Colour never the only channel (signs + side titles; dash/width/swatch for
      series; text on every state chip).
- [x] No motion except optional smooth scroll under `prefers-reduced-motion`
      (script checks the media query); no animated skeleton.
- [x] `lang`: theme sets `data-lang`; hidden span is `display:none` (theme.css).
- [x] Hit targets: 44px at <768 (buttons/chips/picks/clear/rows/accordions per §7
      media block); ≥28px controls at ≥768.
- [x] Zoom/reflow: no horizontal page scroll at 390 or 1440 (measured
      `scrollWidth == clientWidth`).

## PNG sha256

```
fb3b2244bff372f80c3eb6d586a5b99d548ac2e993f502a33563b308d8767a4d  es_1440_dark_en_error.png
58129517ce377ea8f580b232eed7e2fb519c9528eac5c88e3477450094ad7bcd  es_1440_dark_en_expanded.png
9594006659d490cab0add945aeb63cce96789e582e912f519a539883e616403b  es_1440_dark_en_kbd_chart.png
926072340d11ffc6ccb8c895575afed606e7267093497bc596510294efa59a91  es_1440_dark_en_kbd_focus.png
352da17edc15d7c9b987a14e3b05ad1cd258aa500c2845bf6952a189185f9538  es_1440_dark_en_loading.png
b4e7a8cae65fc7d97e2ee281eb3cee6577b6f9916e98a3260870353c166b5264  es_1440_dark_en_movers_empty.png
6c471efe79ab8896b689cb182c1533d7f518ef2c637942b1598cd4cfc772153c  es_1440_dark_en_offline.png
7aa24bd5683a2c3568a7972972be394e50af9a4a244dfda326a83dd912ebb379  es_1440_dark_en.png
8e393c919fead532ee83fe0a7e91fb421b1e345a64bf7a02787fd7831f458400  es_1440_dark_en_stale_hero.png
ec85714734343fbbf1bef52863d6948b7364eb47a909fd0d509ea14f6e8bb778  es_1440_dark_zh.png
b72fc26eb3d43635d26e8e91f08ec125f67c5fa92f9d3d8c7c1a1fbfa3dc0d80  es_1440_light_en.png
81f4aa6d01eb99ec25073321ee0b0532ffeb77dcfb8cc3c65ccbb650ffcfb869  es_1440_light_zh.png
368c196ebcac1414918256d79885766396d8c59af703685d2b5f3d491e3290aa  es_390_dark_en.png
fc8db9b041bf3b802de6b036b2bcf96dbb90432dea6d606e79f61b7c829eb446  es_390_dark_zh.png
32b10dc506120b31a8d93d8eba3dfec1e2777c9e999aacbfff0ce4029c9bf7ac  es_390_light_en.png
9eec11c1a255a348a0b4614fc12ff6baf448bf5ef78a9c1decf57cd50a3709f5  es_390_light_zh_id_collapsed.png
0d0c31bf431a6d69dc4370591274a9b98d86a9a815e09307f7873fd8980c721b  es_390_light_zh_id_expanded.png
9bcc94a25e2be462c8cfa8ab8be76252aa5b42c89e2ad775c0df65b3a58e737a  es_390_light_zh_method.png
1530877e8a5417f67431f66fc422da6b84cf91851d66844b20ba45681f3784b7  es_390_light_zh.png
```

## Commands run

- `git fetch origin +refs/heads/main:... +refs/heads/claude/itp-expectation-surface-2026-10-21:...`
- `git merge --ff-only origin/claude/itp-expectation-surface-2026-10-21` (to `ff28fc1bb11…`)
- `python3 scripts/worktree_sparse.py add data` (sparse lane; the packet's
  `data/revisions`, `data/reference` are nested paths — the tool materializes
  top-level dirs; 15 files / ~57 MB)
- `python -m pytest tests/test_build_expectation_surface.py -q`
- `python3 -c "from scripts.build_expectation_surface import build; build(write=True)"`
- Fixture builds via the builder's own seams (module constants injected for the
  shot, then restored; honest LIVE build restored last):
  `es.OBSERVATIONS_PATH = ".../expectation_observations_fixture_missing.parquet"`;
  `es._now_iso` faked +12 days; `es._movers` stubbed to empty.
- `python3 -m http.server 8765 --directory site` + Playwright/Chromium.

## GAPS (builder-context gaps derived in-template/in-JS, per packet)

1. **`default_ticker_json` not in builder context.** §6.7 wants the default view
   server-rendered from an inlined ticker doc; the builder passes only
   `summary`. Derived: `#es-default-series` inlines `{ticker, horizon,
   securities, unresolved}` and the page script fetches
   `expectation_surface/tickers/<T>.json` through the normal `open()` path on
   boot. Consequence: the explorer's first paint is "—" placeholders until the
   default fetch resolves (fast, local); card pill/counts fill after load. The
   spec's "no loading state on first paint" holds in practice (fetch < 150 ms ⇒
   no skeleton).
2. **Per-ticker `identity_status` not in builder context** (only aggregate
   counts). The card pill is JS-populated from the ticker doc (G6 labels); the
   server-rendered shell leaves it hidden rather than claiming a state.
3. **STALE derivation.** The builder does not compute staleness; the chip is
   server-rendered `hidden` and revealed by the page script when
   `rendered_at − latest_session.at > 9 days` (day-precision is exact via ms
   parsing). Screenshot produced with a faked `rendered_at` (+12 days).
4. **Session cadence + span weeks + hero lead/streak + shares** are computed in
   Jinja from `summary` (builder passes raw counts only).

## DEVIATIONS from the spec (numbered, with reason)

1. **D1 — one original test assertion updated.** The wave-1
   `test_template_has_six_ids_in_order_and_four_chips` asserted `"<style" not in
   src and "style=" not in src` and the wave-1 chip strings. The accepted design
   supersedes both by construction (§7 style block; §6.5/§6.6 custom-property
   style attributes; §8 chip copy). The test now asserts the accepted-design
   equivalents (six ids in order kept; chips per §8; a companion test covers
   tokens-scoping/no-color-literals/custom-prop-only style attrs). Material
   invalidator: the accepted design is a changed contract. Nothing deleted, none
   weakened.
2. **D2 — strip desktop window (12 columns).** §9.1 says "one column per
   compared session" (the board had 9). Real data has **54** compared sessions
   per metric; 54 × the frozen 52px column cannot fit the frozen 676px strip.
   The strip shows the newest 12 at ≥768 (`is-cap` columns hidden; 12 = largest
   count leaving ≥4px between columns at 676px) and the newest 6 at <768 (spec's
   own rule), with the honest "Last {k} of {n} compared sessions" caption shown
   whenever k < n (spec had it <768-only). The counts table keeps all 54 rows
   behind "All {n} compared sessions".
3. **D3 — `[hidden]` guard.** One page-scoped rule
   `.page-es [hidden]{ display:none !important; }` was added: without it the
   author `display:flex` on `.es-breadth-body`/`.es-sides` overrides the UA's
   `[hidden]`, so §10.2's metric toggle would not hide the second body.
4. **D4 — unit strings replaced by the G4 ruling.** §8.6's "USD per share…" unit
   variants are superseded by seat ruling G4 (source `unit` column is NaN on
   every row ⇒ no currency/scale claim anywhere). `#es-unit` and the movers
   footnote carry the G4 note. Revenue magnitudes use the G4 compact forms
   (B/M/k); EPS keeps 2 decimals.
5. **D5 — horizon ZH labels per G1** (seat ruling): 当季/下季/当财年/下财年,
   superseding §8.5's 本季度/下一季度/本财年/下一财年.
6. **D6 — wave-1 anchor ids `#es-search` / `#es-ticker-panel` kept.** The packet
   freezes them; the accepted design's explorer ids differ. `#es-search` sits on
   the combobox container, `#es-ticker-panel` on a plain wrapper around
   `#es-view` (no visual effect). The six spec-frozen section ids are untouched.
7. **D7 — offline `es-empty` reason codes.** §6.8 shows a literal
   `observations_parquet_missing`; the page renders the build's actual
   `s.reasons` codes instead (honest, machine-checkable).
8. **D8 — `#es-stale` text node** carries a span (`#es-stale-text`) instead of
   the board's en/zh span pair idiom — setT fills it with a two-span pair.
9. **D9 — visual review via DOM/computed-style probes, not a second model.** The
   guarded vision helper returned a typed refusal
   (`GLM_VISION_DELEGATION_REFUSED: controller_minimax_lease_required`), so the
   §13 confirmations were verified programmatically (computed styles, geometry,
   token values) rather than by visual judgment.

## Not done here (for the seat)

- `RESEARCH_PROGRAM_URL` renders `research/index.html` per ruling G3 (the file
  is not materialized in this sparse evidence build; the href is the contract).
- The site chrome (`site/theme.css`, `site/theme.js`, fonts) was copied from
  `templates/` **locally only** for the evidence screenshots; nothing under
  `site/` is staged.
