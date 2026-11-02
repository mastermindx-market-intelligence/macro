# Prophet R7 Wave A2 - watchlist Watchlists-mode visual evidence

This receipt exists because the Portfolio-mode receipt
(`mockups/evidence/prophet-r7-wave-a/watchlist/`) captured every cell on the
page's default Portfolio tab, so it never exercised the Watchlists tab this PR
changes. This directory is the same capture pointed at the Watchlists tab,
re-taken (r3) with a populated anonymous list so the two columns this PR adds
are actually visible. The earlier r2 version of this receipt booted the
anonymous list empty and therefore showed no column headers or rows at all;
those r2 cells were removed when this capture replaced them.

The only difference from the Portfolio-mode receipt is the localStorage
pre-seed script inserted into the scratch copy. The pre-seed reproduces a
returning user's stored tab choice and their earlier-added names, and changes
no page bytes in the repository. The shots show presentation only.

What was rendered: `/watchlist.html` as the render lane would publish it from
this branch. `templates/watchlist.html.j2` was rendered with build_site's
Jinja environment (autoescape, the `min` and `regex_replace` filters, the
`td`/`tr`/`t_pctile`/`zip`/`SITE_BASE`/`CHANNEL_LABEL` globals). The page
context is the JSON already embedded in the tracked `site/watchlist.html`:
`STATE_DISPLAY`, `WL_STARTERS`, `WRI_REGIME`, `WL_SECTOR_ZH`, the public
Supabase config and the generated stamp. The output then went through the same
committed-form sweeps as the render lane: `write_page` (data-base shim +
shared shell), CSS externalization into `assets/css/<sha8>.css`, and the
`?v=` asset stamps (`scripts/optimize_assets.make_optimizer`).

Faithfulness check: the same procedure applied to the merge-base template
(the pre-wave-A template at 194087665d5, the commit whose nightly render wrote
the tracked page) reproduced the tracked `site/watchlist.html` byte for byte,
and its stylesheet matched as well:

    $ cmp /tmp/wlrender-r3/capA/site/watchlist.html site/watchlist.html
    $ echo $?
    0
    $ cmp /tmp/wlrender-r3/capA/site/assets/css/29cecf26.css site/assets/css/29cecf26.css
    $ echo $?
    0

Both `cmp` runs were silent. The rebuilt branch page (with the
`var(--r-card,12px)` fallback this lane adds) was then rendered by the same
procedure into a scratch copy of `site/` — a full copy of the tracked `site/`
with the rebuilt page written over it, so every asset the page requests
(fonts, `account.js`, the nightly payload JSONs) resolves. The scratch copy
lives entirely outside the repository; the tracked `site/watchlist.html` was
never modified. Before the pre-seed was inserted, the rebuilt page differed
from the tracked page only in the wave-A surface this PR already ships (the
two live-region divs, the externalized stylesheet hash `29cecf26` ->
`e8d0f999`, and the `watchlist.js?v=15` -> `?v=16` stamp) — the same three
hunks the r1 packet's NOTES recorded as its reason for not committing the
rebuilt page.

The pre-seed is two localStorage writes in one line, inserted into the scratch
page immediately before the `<script>` tag that loads `watchlist.js`:

    <script>try{localStorage.setItem('mdash.ws.mode.v1','watchlists');localStorage.setItem('mdash.watchlist.v1',JSON.stringify({v:1,updated:'',items:[{t:'AAPL',added:'2026-10-14',note:''},{t:'0700.HK',added:'2026-10-20',note:''}],order:[],settings:{}}))}catch(e){}</script>

The first key restores the tab choice; `watchlist.js` reads it at init
(`templates/watchlist.js` near lines 2362-2364) and `setMode` writes
`html[data-ws-mode]` (near line 777). The second key is the anonymous store
itself (`var KEY = 'mdash.watchlist.v1'`, templates/watchlist.js line 25, read
at init through `migrate()`, which accepts exactly this blob shape). The two
seeded names — AAPL added 2026-10-14, 0700.HK added 2026-10-20 — are fixture
values chosen for the shot: they put two rows on the board so the new columns
render, and nothing else is invented for them (no prices, no stages, no
snapshots; what those cells show comes from the scratch site's own nightly
payload, see below). `capture_page_evidence.py --force-state` can only toggle
`<body>` classes/attributes or hover/focus, so it cannot switch the tab or add
rows; the pre-seed boots the page the way it boots for a visitor who last
chose Watchlists and earlier added these two names.

Captured 8 rest cells: desktop 1440 and mobile 390, en and zh, light and dark.
Each rest cell also has a hover cell (`--force-state
"row_hover:hover(#tbl_wl tbody tr)"`, files suffixed `--row_hover`), so the
manifest holds 16 cells. The hover target is the Watchlists tab's own table
(`<table class="hold" id="tbl_wl">`, templates/watchlist.html.j2:1061) — the
Portfolio-mode receipt hovered the same `.hold` table via its class. Settle
time was 1500 ms so the theme toggle animation finishes before each shot.
Manifest-recorded outcome: 16/16 captured, 0 console errors, 0 failed
responses, no horizontal overflow at either width.

Cells opened before committing (desktop EN light rest `8fedb2fa4d8e5ced.png`,
mobile ZH dark rest `5a7d07451a527d74.png`; sha256 and pixel dimensions
verified against the manifest, applied theme/locale read back from the
manifest), plus a live DOM probe of the same served payload the cells were
shot from (`/tmp/wlrender-r3/capB/site`, per-span computed-display and text
reads) and a direct reading of the two PNGs:

- The Watchlists tab IS active in both opened cells: `html[data-ws-mode]` is
  `watchlists`, the Watchlists button carries `aria-selected="true"` and the
  count "1", Portfolio `aria-selected="false"`. The list dropdown reads
  "My watchlist" — the default anonymous list name (templates/watchlist.js
  line 1297) — with "2 names" / "Showing all 2".
- Desktop EN light rest `8fedb2fa4d8e5ced.png`: the full 10-column head is
  visible, including the two columns this PR adds — "WHEN YOU SAVED" and
  "TONIGHT" — and the two fixture rows render: AAPL (Apple Inc) and 0700.HK
  (Tencent). AAPL's row: Signal "Early sign", Risk flags "Near its high",
  Sector "Information Technology", When you saved "Not supplied", Tonight
  "Early sign". 0700.HK's row: Signal "Broke down", Sector "Internet & Tech",
  When you saved "Not supplied", Tonight "Broke down". The table footnote and
  the "2 rows" scope line render below the rows.
- Mobile ZH dark rest `5a7d07451a527d74.png`: the Watchlists tab (自选股) is
  active and both rows render as the mobile card layout — AAPL / Apple Inc
  with 初现 (Early sign) and the 接近高点 (Near its high) flag, 0700.HK /
  Tencent with 已破位 (Broke down). The 保存时 / 今晚 column headers are NOT
  visible in this cell, on purpose: the shipped ≤720px reduction clips the
  whole `.hold thead` and hides `.hold .c-wsv, .hold .c-ton`
  (templates/watchlist.html.j2:476-482) — the same demotion that routed this
  PR's change to hover evidence in the Portfolio-mode receipt. The desktop
  cells carry the two-column proof; no mobile cell can show the headers by
  design.

What the two new columns show, and why:

- "When you saved" shows "Not supplied" / "未提供" in every seeded row. That
  is by design, not a defect: `saveSnapOf()` returns `null` when no list id is
  bound, and the anonymous store has no list id
  (`if (!listId) return null;` — templates/watchlist.js near line 1103), so an
  anonymous visitor never has a saved-decision snapshot. A populated saved
  column needs a signed-in session, which this receipt cannot synthesize.
- "Tonight" shows real stage labels, not "Unavailable": AAPL "Early sign" /
  初现 (`stg s-early`), 0700.HK "Broke down" / 已破位 (`stg s-invalid`).
  `tonightCell()` renders the row's existing state label when the row has one
  and falls back to "Unavailable" / "暂不可用" only when `r.st` is empty
  (templates/watchlist.js near lines 1127-1131). The nightly payload
  resolves from the scratch site (the full tracked `site/` copy carries the
  payload JSONs the page fetches), so both rows have a current stage. Those
  stages are the payload's own values for these tickers on the captured
  build — they are not fixture data and nothing was invented for them.

Gaps (recorded, not captured):

- The saved-decision half of the pair stays "Not supplied" in every cell:
  snapshots exist only for a signed-in list, which cannot be produced from
  static output. The two-column history law is therefore proven here with a
  real Tonight column beside the designed anonymous absence in When-you-saved.
- Signed-in access tiers and loading, empty, stale and error states remain
  manifest gaps, as in the Portfolio-mode receipt.
- Confirmation basis: the packet for this capture names the live DOM probe
  plus the manifest's per-cell records as the accepted confirmation and
  directs that no vision delegation be run; none was (the r2 capture's
  request to the bounded vision helper had been refused by the gate). The two
  cells were opened directly in this session and read as described above,
  alongside the DOM probe and the manifest's per-cell applied theme/locale,
  sha256 and pixel-dimension records.
- `asof_present` is `false` in this manifest while the Portfolio-mode
  manifest records `true`; the "Generated … UTC" footer text is present in
  the DOM (both opened cells show it). The difference follows the tool's
  page-level check, not a missing element.

The Portfolio-mode receipt at `mockups/evidence/prophet-r7-wave-a/watchlist/`
is untouched and remains the honest default-tab receipt.
