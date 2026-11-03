# Evidence — production journey cells (P10–P18 / J13) for sector-intelligence-cycles-20261021

What this directory proves: the coverage cells that proposal.yml `coverage_matrix` marks `PAPER_CAPACITY_LIMITED`
(no Paper board exists for them) are captured on the **rendered production product**, not drawn. Each PNG is a
full-page capture of the production render tree `site/` at **d86344b93a0b** (the #9917 render worktree, data as built:
Sector Intelligence as of 2026-10-19, Sector Cycles as of 2026-10-20), served over plain http on localhost:8931 and
loaded through `evidence_frame.html`, which seeds `localStorage.theme` / `localStorage.lang` before the page's own head
boot reads them (the same keys `templates/theme.js` writes), sizes the iframe to the page's document height, and copies
measurement facts onto the host document. `capture.py` runs two headless-Chrome passes per cell (dump-dom for the
height and the facts, then a screenshot at that height, cropped to the iframe width) and writes `cells.yml`.

- `cells.yml` — one row per cell: route (`src`), viewport/theme/locale, PNG path + sha256 + px, document height,
  `scroll_w` and `horizontal_overflow` (page-level), unclipped overflow candidates, the page's own `data-theme` /
  `data-lang` after boot, the resolved hash, the h1 text, the as-of text read from `#sc-asof` / `#asof` /
  `#si-side-asof`, whether the "different day / incompatible generation" wording appears, and section offsets.
- 31 coverage cells (`kind: coverage`): Explore·Rotation 6 (`#map`), Explore·Lenses 8 (`#moving`), Dossier 6
  (`sectors/XLK.html`, the production Dossier home per baseline.yml:101), Research 6 (`#tm-mount`, the explore view's
  research target), Watches 5 (`#accumulation-section`, the moving view's watches target). Routes come from the
  production hash router (`si_workspace.js` VIEWS + LEGACY_ANCHORS) and the workflow switcher
  (`templates/sector_central.html.j2:1494-1499`).
- 15 compositions (`kind: composition`): the other three Explore lenses (`#money`, `#explore`, `#confluence`) at two
  corner cells each, and the J13 widths 320 / 430 / 768 for Brief (`#overview`), Rotation (`#map`) and the standalone
  Cycles page, dark/EN.

Facts worth reading before the PNGs (all from `cells.yml`):

- Theme and locale took effect on every cell: `data_theme == theme` and `data_lang == lang` for all 46 rows.
- No horizontal overflow at 1440 or 390 on any cell. Three J13-width compositions overflow and are recorded as
  production facts, not repaired here: `w320-rotation-dark-en` (the rotation map card `.rvx-map-card` reaches 384 px
  at 320), `w320-cycles-dark-en` and `w430-cycles-dark-en` (the Cycles tab row `#sc-tabs` is 464 px wide; the baseline
  already records the standalone Cycles page's 390 overflow as a baseline smell, baseline.yml:84).
- As-of: Sector Intelligence cells read `2026-10-19`; Cycles cells read `2026-10-20`; the Dossier page exposes no as-of
  id (its signal note dates the trigger ≈ 2026-10-19) and is recorded with an empty `asof`. The two dates differ by
  design (the Brief specimen is as of 2026-10-19, the chart capture 2026-10-20, as board 40 states).
- The "different day / incompatible generation" wording appears on no captured cell (the fixture for it is board 31).

Not proven here (recorded, not claimed): keyboard and touch paths, 200% zoom and reduced motion (J13 interaction
items — exercised separately in the browser pane and reported in the continuation handoff, not as PNGs); J11 watch
saves and account isolation (the static render tree has no watch-owner API; the save journey needs the account-owned
watch endpoint); signed-in states (the render tree serves the anonymous gated preview); J15 release / natural update
(P19–P20, pending by design until the reference is accepted). The composite desk (boards 40/41) is a review instrument,
not a shipped surface, and has no cell here.

Regenerate: start the `sic-render` launch config (serves the render tree's `site/` on :8931), copy
`evidence_frame.html` to `<render tree>/site/__sic_evidence_frame.html` (untracked), then
`RT=<render tree> python3 capture.py <out_dir>` and copy the PNGs + `cells.yml` here.

## Interaction journeys exercised in the browser pane (production render tree d86344b93a0b, localhost:8931)

Facts read from the live DOM through the pane's script tool (not from screenshots); one 0.4×-scale pane screenshot is
kept under `journeys/`. Everything below is the production candidate as built, not the RIG specimen.

- **J02 routes / Back / Forward** — `#map`, `#money`, `#confluence` mount their `.si-view` and switch the title
  (Market map / Breadth & money / Entry evidence); the legacy aliases `#rotmap-section` → map and `#si-money` → money
  keep the alias in the URL; `#tm-mount` → explore (Research switcher current), `#accumulation-section` → moving
  (Watches switcher current). `history.back()` ×2 and `forward()` replayed the view **and** the scroll position
  (y 1687 for `#money`, 415 for `#si-money`). An unknown hash (`#bogus-route`) shows Brief and leaves the hash as typed.
  The selected sector rides in the query: `?g=XLE#map` reloads with the Energy row `aria-pressed` and its detail open.
- **J03 select on the rotation map** — clicking the measured-list row selects it (`aria-pressed=true`, URL gains `?g=XLE`,
  detail shows 1m/3m vs S&P 500, measured order 1 of 11, evidence date 2026-10-20, a "Compare in Prophet →" link);
  pointer events on a map dot raise the `#rvx-rtip` tooltip (hovered dot `us_sector_health`: strength 75, 20d relative
  +5.8%, week speed +3, "领先 → 持有/加仓" in ZH). Screenshot: `journeys/j03-map-select-zh-light-0.4x.jpg` (ZH/light).
- **J04 Cycles select** — clicking a card (`article.cyc-card#xli`) lights it, sets `#xli` and swaps the default panel for the
  focus panel ("← All sectors", "Open Industrials page ↗"). The production card still reads the legacy clock
  ("Bottoming / AVOID / cycle position 0/100"; ZH 筑底 / 回避 / 周期位置 0/100) — the named mandatory gap the RIG replaces.
- **J06 dossier → member → return** — `sectors/XLE.html` (h1 "Energy (XLE)", 35 member links `../stock.html#<T>`, body
  as-of 2026-10-19, no as-of id) → `stock.html#APA` loads "APA Corporation (APA)" → Back returns to the dossier →
  its "Subsector Confluence" link returns to `sector_central.html#confluence` with the confluence view mounted.
- **J10 Research (Time Machine)** — the `#tm-mount` shell is a collapsed `<details>`; opening it loads
  `oracledata/tm_manifest.json` and renders the episode buttons (2021 Growth Top … 2025–26 Semis → Healthcare), the
  universe buttons (Sectors 1998→, Subsectors 2021→, Themes 2021→, Factors 2013→) and the year row. There is no text
  editor on this surface. **Gap:** the measured-list "Compare in Prophet →" link targets
  `us_stocks.html?si_sector=XLE&si_asof=…#sector-prophet-context`; at d86344b93a0b `us_stocks.html` and its scripts
  contain neither that id nor a `si_sector` consumer (the page loads at the top, no XLE context). The emitter (SIC-I06R,
  sector_central.html `sectorProphetHref`) exists; the consumer does not, so the edit → save → return leg of J10 is
  not provable on this tree.
- **J13 theme / locale switch** — writing `localStorage.theme=light`, `lang=zh` and reloading flips the Cycles page to
  `data-theme=light` (body rgb(232,235,241)) and `data-lang=zh` (cards in ZH). The keys are per origin, so the switch
  applied to every tab.
- **J14 Record / Methods** — the production pages carry no Record or Methods control (grep of sector_central.html,
  sector_cycles.html, sectors/XLE.html and a DOM text scan for method/record/方法/记录 find only the nav's
  "Strategy Track Record" item). Replay countercases and the scientific disposition are specimen-only until the
  reference lands.
- **Network / console** — the only failing request on sector_central is `/api/billing/offers/founding_pro` (404 on the
  static tree, swallowed by account.js); every data fetch returned 200.
- **Not exercised:** keyboard and touch paths, zoom, reduced motion, J11 watch saves and account isolation, signed-in
  states, J15 natural update (see the first section).
