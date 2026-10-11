# site20 S2 tablesort evidence — round 2 (S2-02 keyboard sort + aria-sort, S2-04 filter status + no-results reset)

- **Page:** `/hk.html` (real built page), served by `python3 -m http.server 8942 --bind 127.0.0.1 --directory site`
- **Table:** document table index `2` — the 13-data-row sector table (Sector / 20d RS / State), the table the round-1 census identified as the enhanced, filtered consumer
- **Branch/head the bytes came from:** `claude/ssd-site20-s2-c95f856f22822049` @ `32f8791dacabc01d5cca23a07664176206e87b94`
- **`git rev-parse HEAD:templates/tablesort.js`:** `8f878f0a2c4617b6eff9799f5394207d8b3b66e2` (site copy byte-identical, sha256 `d9925360376c9740b02150e729955541baaefce63736eef9c4bc032f9bbf2bad`)
- **Synthetic tokens:** `ZZTEST13`, `ZZTEST14` — two cloned data rows appended in-page (SYNTHETIC hydration; no real late-row consumer exists on this page) so the `one` state has a deterministic single match; the `one`/`nomatch` queries are `ZZTEST13` / `qqqnomatchqqq`
- **Matrix:** state × theme (`dark|light`) × lang (`en|zh`) × viewport (`1440` = 1440×900, `390` = 390×844) = 32 PNGs named `<state>--<theme>--<lang>--<vw>.png`
- **Crop:** union of the filter bar and the table's header + first 6 visible data rows (hidden filtered rows collapse to zero height), clipped to the viewport width, at most 480 px tall — `page.screenshot({clip})`, never full-page
- **Capture script:** `capture.cjs` (this directory; `node capture.cjs <pagePath> <port> <outDir>`, non-127.0.0.1 requests aborted)

**Synthetic query/hydration on a real built page; local server; not production.**

## What to look at, per state

- **`rest`** — the filter bar after load: search input with EN placeholder `Filter…`, empty status span (announced `role="status"`), no reset button; table unsorted (↕ arrows), all 13 rows visible.
- **`one`** — query `ZZTEST13`: status reads `1 / 15`, exactly the single synthetic row visible under the header, no reset button.
- **`nomatch`** — query `qqqnomatchqqq`: status reads `No matching rows · 0 / 15` (EN) / `无匹配行 · 0 / 15` (ZH) with the `·` U+00B7 separator, and the `Clear filter` / `清除筛选` reset button (`gbtn gbtn-sm gbtn-quiet`, `type="button"`) sits after the count span; no data rows (header remains).
- **`keyfocus`** — the numeric `20d RS` header focused by keyboard (Tab arms keyboard modality, then focus) and sorted with Enter: `data-dir=desc` shows the ↓ arrow, `aria-sort="descending"` on that cell only, and the browser focus ring on the header cell.

Theme/lang/viewport coverage: every state exists in all 8 theme × lang × viewport combinations listed above.
