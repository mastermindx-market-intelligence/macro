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

- Every cell records `head` = `cf604b9d4af34b5746bac572a0fc2d5b7d62a467`.
- Between cf604b9d and the branch HEAD that carries this pack, only two files
  changed: `templates/sector_central_china.html.j2` and
  `tests/test_china_si_workspace_shell.py`. Neither one is rendered by v1–v5, so
  the cells are source-equivalent at that HEAD.
- The China central change has its own pack, `../sector-cycles-wave-china/`,
  rendered at 3fdb12f6.

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

**The data is fixture data, not production.** No P0B receipt was written, and no
live or r2.dev URL was loaded. Production and natural-update proof belong to P22.

## Deviations from the lane packet

- **Extra viewport (DEV-L6-8):** the 375×812 viewport and the 23 delta cells extend the
  28-cell matrix.
- **Render commit (DEV-L6-9):** the cells were rendered at cf604b9d, not at the branch HEAD.
  They are source-equivalent for v1–v5 (see "Source currency").
- **Manifest scope (DEV-L6-10):** the manifest covers `cells/` and `zh_latin/` only.
