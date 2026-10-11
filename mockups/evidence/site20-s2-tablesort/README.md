# site20 S2 tablesort evidence — round 2b (S2-02 keyboard sort + aria-sort, S2-04 filter status + no-results reset)

- **Page:** `/hk.html` (real built page), served by `python3 -m http.server 8942 --bind 127.0.0.1 --directory site`
- **Table:** document table index `2` — the 13-data-row sector table (Sector / 20d RS / State), the table the round-1 census identified as the enhanced, filtered consumer. With the page stylesheet present the table lives inside the `hkx-dlg-sector` modal dialog (`display:none` until opened); every capture/acceptance context opens it via `window.hkxOpenDlg('hkx-dlg-sector')` exactly as the page's own trigger card does, and the crop is raised by scrolling the open dialog (`.hkx-dlg` is its scroll container).
- **r2b re-capture head:** `claude/ssd-site20-s2-c95f856f22822049` @ `b92a79437ff101e40e2213d2678da7d208a0d952` (round-2 crops were taken at `32f8791dacabc01d5cca23a07664176206e87b94` WITHOUT the page stylesheet; the 32 PNGs were overwritten by the r2b run)
- **`git rev-parse HEAD:templates/tablesort.js`:** `982e53e667adc0d93cc7fbe5378076260be41c22` (site copy byte-identical, sha256 `ec92eada6a96db7c5718bf31bf1256a8dec6f2f6b1dead31113d4fa0eba58998`; unchanged by r2b)
- **Page stylesheet present:** `assets/css/7de16248.css` (sparse set widened with `/site/assets/`); same-origin stylesheet/script 4xx = 0 (r2b request gate — recorded per run in the lane log `requests_r2b.txt`)
- **Known limitation — local 404s outside the gate:** `site/fonts/Inter-*.woff2` and `site/live/*.json` (`quotes.json`, `overlay.json`) exist on `origin/main` but sit outside this sparse checkout, so the local server answers 404 for them: crops render with the system fallback font and no live-ticker data. Aborted external hosts: none — no non-127.0.0.1 host was requested.
- **Synthetic tokens:** `ZZTEST13`, `ZZTEST14` — two cloned data rows appended in-page (SYNTHETIC hydration; no real late-row consumer exists on this page) so the `one` state has a deterministic single match; the `one`/`nomatch` queries are `ZZTEST13` / `qqqnomatchqqq`
- **Matrix:** state × theme (`dark|light`) × lang (`en|zh`) × viewport (`1440` = 1440×900, `390` = 390×844) = 32 PNGs named `<state>--<theme>--<lang>--<vw>.png`
- **Crop:** union of the filter bar and the table's header + first 6 visible data rows (hidden filtered rows collapse to zero height), clipped to the viewport width, at most 480 px tall — `page.screenshot({clip})`, never full-page
- **Capture script:** `capture.cjs` (this directory; `node capture.cjs <pagePath> <port> <outDir> [requestsLog]`, non-127.0.0.1 requests aborted; the optional 4th arg appends the same-origin ≥400 + aborted-host request log)

**Synthetic query/hydration on a real built page; local server; not production.**

## r2b contrast gate (complete page, `nomatch` state, dialog open)

Reset button (`gbtn gbtn-sm gbtn-quiet`, unchanged by r2b) and status span, per theme × lang × viewport — bg = most frequent pixel, ink = largest WCAG relative-luminance difference from bg:

```
dark en 1440 reset=10.04 (ink rgb(181, 189, 200) / bg rgb(12, 16, 24)) status=6.15 (ink rgb(139, 147, 161) / bg rgb(12, 16, 24))
dark en 390  reset=10.04 (ink rgb(181, 189, 200) / bg rgb(12, 16, 24)) status=6.12 (ink rgb(139, 147, 161) / bg rgb(12, 17, 24))
dark zh 1440 reset=10.04 (ink rgb(181, 189, 200) / bg rgb(12, 16, 24)) status=6.15 (ink rgb(139, 147, 161) / bg rgb(12, 16, 24))
dark zh 390  reset=10.04 (ink rgb(181, 189, 200) / bg rgb(12, 16, 24)) status=6.12 (ink rgb(139, 147, 161) / bg rgb(12, 17, 24))
light en 1440 reset=8.54 (ink rgb(66, 76, 97) / bg rgb(254, 254, 254)) status=6.97 (ink rgb(76, 90, 108) / bg rgb(254, 254, 254))
light en 390  reset=8.47 (ink rgb(66, 76, 97) / bg rgb(253, 253, 254)) status=6.91 (ink rgb(76, 90, 108) / bg rgb(253, 253, 253))
light zh 1440 reset=8.54 (ink rgb(66, 76, 97) / bg rgb(254, 254, 254)) status=6.97 (ink rgb(76, 90, 108) / bg rgb(254, 254, 254))
light zh 390  reset=8.47 (ink rgb(66, 76, 97) / bg rgb(253, 253, 254)) status=6.91 (ink rgb(76, 90, 108) / bg rgb(253, 253, 253))
```

GATE reset ≥ 4.5 in all 8: **PASS** (min 8.47, light en 390). Status span (record only) also ≥ 4.5 everywhere (min 6.12, dark 390) — no `one`-state re-measure needed, no source change. (The round-2 measurement of reset 1.45:1 / status 2.72:1 was an artifact of the absent page stylesheet: unstyled `<th>`/light body under a dark filter.)

## What to look at, per state

- **`rest`** — the filter bar after load: search input with EN placeholder `Filter…`, empty status span (announced `role="status"`), no reset button; table unsorted (↕ arrows), all 13 rows visible.
- **`one`** — query `ZZTEST13`: status reads `1 / 15`, exactly the single synthetic row visible under the header, no reset button.
- **`nomatch`** — query `qqqnomatchqqq`: status reads `No matching rows · 0 / 15` (EN) / `无匹配行 · 0 / 15` (ZH) with the `·` U+00B7 separator, and the `Clear filter` / `清除筛选` reset button (`gbtn gbtn-sm gbtn-quiet`, `type="button"`) sits after the count span; no data rows (header remains).
- **`keyfocus`** — the numeric `20d RS` header focused by keyboard (Tab arms keyboard modality, then focus) and sorted with Enter: `data-dir=desc` shows the ↓ arrow, `aria-sort="descending"` on that cell only, and the browser focus ring on the header cell.

Theme/lang/viewport coverage: every state exists in all 8 theme × lang × viewport combinations listed above.
