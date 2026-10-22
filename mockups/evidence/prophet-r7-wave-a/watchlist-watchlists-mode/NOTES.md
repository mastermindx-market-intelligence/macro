# Prophet R7 Wave A2 - watchlist Watchlists-mode visual evidence

This receipt exists because the Portfolio-mode receipt
(`mockups/evidence/prophet-r7-wave-a/watchlist/`) captured every cell on the
page's default Portfolio tab, so it never exercised the Watchlists tab this PR
changes. This directory is the same capture pointed at the Watchlists tab.

The only difference from the Portfolio-mode receipt is the localStorage
pre-seed script inserted into the scratch copy. The pre-seed reproduces a
returning user's stored tab choice and changes no page bytes in the
repository. The shots show presentation only.

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

    $ cmp /tmp/wlrender/capA/site/watchlist.html site/watchlist.html
    $ echo $?
    0
    $ cmp /tmp/wlrender/capA/site/assets/css/29cecf26.css site/assets/css/29cecf26.css
    $ echo $?
    0

Both `cmp` runs were silent. The rebuilt branch page (with the
`var(--r-card,12px)` fallback this lane adds) was then rendered by the same
procedure into a scratch copy of `site/` carrying this branch's `watchlist.js`
/ `watchstore.js`, and captured from there. The scratch copy lives entirely
outside the repository; the tracked `site/watchlist.html` was never modified.
Before the pre-seed was inserted, the rebuilt page differed from the tracked
page only in the wave-A surface this PR already ships (the two live-region
divs, the externalized stylesheet hash `29cecf26` -> `e8d0f999`, and the
`watchlist.js?v=15` -> `?v=16` stamp) — the same three hunks the r1 packet's
NOTES recorded as its reason for not committing the rebuilt page.

The pre-seed is one line, inserted into the scratch page immediately before
the `<script>` tag that loads `watchlist.js`:

    <script>try{localStorage.setItem('mdash.ws.mode.v1','watchlists')}catch(e){}</script>

`watchlist.js` restores the tab from that key at init
(`templates/watchlist.js` near lines 2362-2364) and `setMode` writes
`html[data-ws-mode]` (near line 777). `capture_page_evidence.py
--force-state` can only toggle `<body>` classes/attributes or hover/focus, so
it cannot switch the tab; the pre-seed boots the page the way it boots for a
user who last chose Watchlists.

Captured 8 rest cells: desktop 1440 and mobile 390, en and zh, light and dark.
Each rest cell also has a hover cell (`--force-state
"row_hover:hover(#tbl_wl tbody tr)"`, files suffixed `--row_hover`), so the
manifest holds 16 cells. The hover target is the Watchlists tab's own table
(`<table class="hold" id="tbl_wl">`, templates/watchlist.html.j2:1061) — the
Portfolio-mode receipt hovered the same `.hold` table via its class. Settle
time was 1500 ms so the theme toggle animation finishes before each shot.
Manifest-recorded outcome: 16/16 captured, 0 console errors, 0 failed
responses, no horizontal overflow at either width.

Cells opened before committing (desktop EN light rest
`9cfe8f369c3553ae.png`, mobile ZH dark rest `0c7651081ab43c13.png`; sha256
and pixel dimensions verified against the manifest, applied theme/locale read
back from the manifest) and a live DOM probe of the same served payload:

- The Watchlists tab IS active in the Watchlists mode: `html[data-ws-mode]`
  is `watchlists`, the Watchlists button carries `aria-selected="true"` and
  Portfolio `aria-selected="false"`, in both probed viewports/locales/themes.
  This is what the 16 cells show; it is the defect N2 named in the
  Portfolio-mode receipt (every cell there showed the default Portfolio tab).
- The cells show NO `When you saved` / `保存时` or `Tonight` / `今晚` column
  headers, and no ticker rows. The table area shows the anonymous empty-state
  row: "This list is empty. Use the field above to add a name — equity, ETF,
  commodity or crypto." / "这个列表还是空的。用上方的输入框添加名称 ——
  股票、ETF、大宗商品或加密货币。"

Why no headers or rows render, from the shipped code (not a capture defect):
`renderWatchlist()` writes only the empty-state row when the list has no
items — the `WL_HEAD` (which carries the two new column headers) is emitted
only on the has-items branch (templates/watchlist.js near lines 1267-1275).
An anonymous visitor's list boots empty; `WL_STARTERS` (SPY, QQQ, BTC-USD,
GC=F) are quick-add chips for that empty state, not a pre-populated list. The
list the packet calls "the anonymous starter list 'Watchlists 1'" does not
exist anywhere in the repository: `grep -rn "Watchlists 1" templates/
site/watchlist.html site/watchlist.js` returns nothing, and the default list
name is "My watchlist" / "我的自选股" (templates/watchlist.js line 1297).
Per the packet, this is reported as a gap, never substituted or fabricated.

Gaps (recorded, not captured):

- The A2 column headers and a populated row are not visible in any of the 16
  cells, because the anonymous Watchlists list boots empty and the header row
  renders only for a list with items (templates/watchlist.js:1267-1275). An
  honest capture of populated columns needs either a signed-in session or an
  add-interaction drive (type a ticker, click add) that
  `capture_page_evidence.py` cannot perform — both are outside this packet.
- Signed-in access tiers and loading, empty, stale and error states beyond
  the empty-state row shown remain manifest gaps, as in the Portfolio-mode
  receipt.
- The requested visual cross-check of the two opened cells through the
  bounded vision helper was refused by the gate
  (`GLM_VISION_DELEGATION_REFUSED reason=controller_minimax_lease_required`);
  the confirmations above therefore rest on the live DOM probe of the served
  payload plus the manifest's per-cell applied theme/locale, sha256 and
  pixel-dimension records, not on a model's reading of the pixels.
- `asof_present` is `false` in this manifest while the Portfolio-mode
  manifest records `true`; the "Generated … UTC" footer text is present in
  the DOM. The difference follows the tool's page-level check, not a missing
  element.

The Portfolio-mode receipt at `mockups/evidence/prophet-r7-wave-a/watchlist/`
is untouched and remains the honest default-tab receipt.
