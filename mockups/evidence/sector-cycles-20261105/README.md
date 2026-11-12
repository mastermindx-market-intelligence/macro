# Sector Cycles wave — L6.4 capture (#7646)

Status: **PARTIAL** against lane L6_capture `NOT DONE UNLESS`. The cells, the
manifest and the pinned recipe are complete. Two gaps are named under "What
this pack does not prove". They belong to the lanes that own the renderer and
the ZH copy.

## What the pack is

There are 51 cells, each one PNG and one `*.layout.json` (102 files in `cells/`),
plus 22 `zh_latin/*.txt` scans, one for each ZH cell.

- **28 matrix cells** at the packet viewports 1440×900 and 390×844:
  - v1–v3 × dark/light × EN/ZH × both viewports (24 cells);
  - v4, the China page, ZH only × dark/light × both viewports (4 cells).
- **23 seat delta cells** (`deltas.cjs`). Each one names the closure row it proves:
  - D21 brief tape older than 5 days, and its ≤5-day control (4 cells);
  - D30 unstamped and focused-detail stance faces, plus the international page v5
    (9 cells);
  - D-L3-10 basket chips (4 cells);
  - L4 no-JS for the US and China pages (2 cells);
  - L5 dossier at 375 and the unresolved-member state (4 cells).

| View | URL | Cells |
|---|---|---|
| v1 | `/sector_central.html#cycles` | 12 |
| v2 | `/sector_cycles.html` | 19 |
| v3 | `/sectors/XLK.html#cycle` | 13 |
| v4 | `/sector_cycles_china.html` | 5 |
| v5 (delta only) | `/country_cycles.html` | 2 |

## Archived renderer and recipe scope

The renderer source is preserved byte-for-byte as
[`render_l6.py.txt`](render_l6.py.txt). Its `.txt` suffix identifies it as an
archived record of the capture source at
`b601c02749a34fd83877393d59ee88e6045207cd` (L6.17d).
The archived file has Git blob `f966fdb69d6936bf1896ade36ac5e1be955b4fe6`
and SHA256 `e9d3be1969aa3cc8915168d3b518895a82aa13cff09e713629f278c1659f925b`.

The recipe below belongs to that historical wave checkout. Reproduction requires
its original `render_l6.py`, matching templates and payloads, and
`scripts/build_sector_cycles.py` blob
`60d18b5ee0973713674a055a95fd21573af2639c`, which defines the renderer's
`cycles_page_ctx` dependency. Run the recipe from the original evidence directory
in a separate checkout of that pinned revision.

References below to `render_l6.py`, `HEAD`, `<worktree>`, the render tree and source
currency describe the recorded capture and wave branch. The capture receipts and
their documented gaps keep that historical scope. This archive does not attest a
fresh capture or production acceptance at today's main revision.

## Recipe

```
python3 render_l6.py --out <OUT> --rt <render tree>      # HEAD templates + HEAD payloads -> OUT (outside the worktree)
python3 serve_l6.py <OUT> <worktree> 8741 <log.jsonl>    # 127.0.0.1 static server over OUT
node capture.cjs --selftest                              # pin refusal + cell naming, no browser
node capture.cjs --probe                                 # one cell per view, discovery dump
node capture.cjs --run [regex]                           # matrix + deltas.cjs cells -> cells/, zh_latin/
node capture.cjs --manifest                              # MANIFEST.sha256
```

- `NODE_PATH` holds Playwright 1.61.1 and `L6_SERVE_LOG` names the server log.
- `render_l6.py` writes `fixtures/FIXTURES.json` and the two basket-pulse variant
  fixtures. It labels every cycles entity `FIXTURE`.
- The renderer never writes `site/` or `data/`. It never calls a builder `main()`,
  a store writer, a forward log or a live collector. It fences `config.data_dir`,
  `config.site_dir` and `store._path` onto paths that do not exist.

### Pins

Pins are copied exactly from `scripts/verify_stock_dashboard_mobile_layout.cjs`.

- Chromium 149.0.7827.55 and Playwright 1.61.1 on darwin/arm64.
- The executable is `chrome-headless-shell` with sha256
  `11e393326c7d20a7c56641a7c65def33ea9c280da3b0b74cf8563b07989a0ee3`. The capture
  refuses any other executable, so no system Chrome is used.
- The P0B font pin `/p0b-font-pin/pin.css` is injected first.
- The clock is fixed at 2026-11-05T12:00:00Z.

### Routing

- R2 asset requests are re-routed to the local server. `s3.tradingview.com` is
  stubbed, and every other origin answers 204.
- The server lookup order is:
  1. the `X-L6-Variant` header, which selects `_variants/`;
  2. the render tree;
  3. the HEAD git blob, logged `head-fallback`;
  4. 404.
- `premiumdata/*` answers 401, the anonymous production response, so the capture
  is anonymous.

## Source currency

- Every cell records `head` = `b601c02749a34fd83877393d59ee88e6045207cd` (L6.17d).
- Two source commits sit between that head and the commit that carries this pack.
  Neither changes what these cells render:
  - L6.17e (da07a5e0) changes no template. It only brings `site/sector_cycles.css`
    and `site/sector_cycles.js` back to their template bytes, which are the bytes
    these renders already served from their own copies.
  - L6.18 (48182b7f) changes only the China central page template
    (`sector_central_china.html.j2`) and its shell test. No page in this pack
    includes that template.
  - L6.19 (88870da0) changes only the fund-page dossier. In `sector_cycles_face.js`
    it edits `rsTrail`, which only `sector_dossier.js` calls; the central page calls
    `hazardPass`, `methods`, `prov` and `turnInspector`. The three CSS rules it adds
    to `sector_cycles.css` are scoped to `.scf-rs-key`, `.scf-rs-k` and
    `.scf-rs-sw`, which only `rsTrail` emits. Its other files are
    `sector_dossier.js`, `sector.html.j2` and two tests.

  So the cells still match the source at the branch HEAD.
- The pack was first captured at cf604b9d (L6.4). It was recaptured whole after
  the visual-review repairs L6.16–L6.17d. No cell from the earlier capture remains.
- The China central change has its own pack, `../sector-cycles-wave-china/`. The
  China central page loads `sector_cycles.css` and `sector_cycles.js`, and L6.18
  changes its view rail, so that pack was recaptured at 48182b7f (L6.18).

## Repairs this recapture carries

- **L6.16:** the face position chip and the inspector date localise. The kv rows
  re-scope by language.
- **L6.17:** clock labels, the resting sheet, the chip rail, the phase-map cut, the
  China order and the fund dossier.
- **L6.17b (M4):** the China rank check in the evidence render now allows ties from
  rounding. When two baskets round to the same `rs_21d` value, the order is a tie.
  The render keeps HEAD's order for those two (`cn_rs_rank_rounded_tie_swaps_kept_head`:
  baskets 2). It never re-sorts them by unrounded values the page cannot show.
- **L6.17c (M1/M1b):** at 390px the resting sheet is `visibility: hidden`. Its active
  panel inherits that state instead of re-asserting `visible`. At rest the sheet has
  0 focusable controls, the half detent has 17, and a close returns to 0.
- **L6.17d:** at 390px the full-screen button moves to the y-axis gutter, the
  first-hint pill clears the top label, and the hero card flattens into the stage
  (the chart widens from 286px to 324px). The button, hint and chart labels were
  measured pairwise disjoint in ZH 7y, EN 7y, 1y, full-screen enter and exit, and the
  Themes basket family.

## Manifest scope

`MANIFEST.sha256` has 124 lines: the 102 `cells/*` files and the 22 `zh_latin/*.txt`
files. `shasum -a 256 -c MANIFEST.sha256` reports 0 failures, and each layout JSON's
`png.sha256` matches its manifest line. The manifest does not cover the scripts,
`fixtures/` or this README.

## Assertions across all 51 cells

| Assertion | Result |
|---|---|
| scrollWidth ≤ viewport | 51/51 (no horizontal page scroll) |
| `size_mult` visible | 0/51 |
| page errors | 0 |
| edge-stripe audit flagged | 0 |
| theme and lang applied | 49/51 (the 2 no-JS cells carry no runtime theme or lang, by design) |
| served misses | 0 (525 requests answered by `head-fallback`) |
| console errors | v1 has 1 per cell (the anonymous `premiumdata` 401, expected); v2–v5 have 0 |

Per view:

| View | Element `[data-fixture="true"]` | zh_latin (ZH cells) |
|---|---|---|
| v1 | absent | 217 (document scope) |
| v2 | absent | 6; 24 on d30-detail |
| v3 | present and visible on 13/13 | 3 |
| v4 | absent | 14; 11 on l4-nojs |
| v5 | absent | EN only |

## What this pack does not prove

**GAP-L6-FIX-1: the fixture label is missing on 38 cells.** The spec requires
every cell to visibly carry `components.fixture_chip`. Only the dossier (v3)
renders one.

- On v1, v2, v4 and v5 there is no `[data-fixture="true"]` element anywhere in the
  page: it is absent, not off-screen.
- `render_l6.py` labels every cycles entity `FIXTURE`. But the fixture chip is
  face-only (`SC_FACE.card`), and the grid and inspector rows carry no chip.
- Owning lanes:
  - the L3 renderer, for the grid and inspector rows;
  - the shell of each page, for a page-level label.
- Until a fix lands, these cells are fixture captures that are not labelled on the
  page. Treat each one as fixture data, never as a production reading.

**zh_latin is above 0 on all 22 ZH cells.** The scan runs at document scope (skipping
`details`, `nav`, `script`, `style`, `svg`, `title`, `head`, `[hidden]` and `.l-en`),
so it also counts tickers, company names and data-source acronyms. The counts come
from:

- the allow-list `^(XL[A-Z]|FIX|SPY|MODEL|PRIOR)$`, which does not cover these
  tokens (GAP-ZHGREP-1);
- engine-generated English ladder copy (GAP-ZH-ENG-1):
  - `engine/cycles.py:1125-1130`;
  - `engine/ticker_alerts.py:76-78` and `:218`;
  - `templates/sector.html.j2:482` and `:508`.

The full token lists are in `zh_latin/`. A human native-ZH review is still owed.

**The China order is re-stamped in the fixture (GAP-B M4).** The China fixture
carried `rs_21d_rank` values from before the L6.5o stamper. `render_l6.py` now
re-stamps the China sectors and baskets with `engine.sector_cycles._stamp_rs_ranks`
and refuses if the result differs from the engine at HEAD. The count is in
`CHECKS["cn_rs_21d_rank_restamped"]`, and each re-stamped entity carries a
provenance note. This proves the order the current engine produces, not the
production order: that arrives with the next natural nightly (GAP-D33-1).

**The data is fixture data, not production.** No P0B receipt was written, and no
live or r2.dev URL was loaded. Production and natural-update proof belong to P22.

## Deviations from the lane packet

- **Extra viewport (DEV-L6-8):** the 375×812 viewport and the 23 delta cells extend the
  28-cell matrix.
- **Render commit (DEV-L6-9):** the first capture was rendered at cf604b9d, not at the
  branch HEAD. It is superseded: the recapture is rendered at b601c027, the source HEAD
  under the evidence commit (see "Source currency").
- **Manifest scope (DEV-L6-10):** the manifest covers `cells/` and `zh_latin/` only.
