# site20 S2 tablesort evidence — round 5 (S2-02 keyboard sort + aria-sort, S2-04 filter status + no-results reset)

- **Page:** `/hk.html` (real built page), served by `python3 -m http.server 8942 --bind 127.0.0.1 --directory site`
- **Table:** document table index `2` — the 13-data-row sector table (Sector / 20d RS / State), the table the round-1 census identified as the enhanced, filtered consumer. With the page stylesheet present the table lives inside the `hkx-dlg-sector` modal dialog (`display:none` until opened); every capture/acceptance context opens it via `window.hkxOpenDlg('hkx-dlg-sector')` exactly as the page's own trigger card does, and the crop is raised by scrolling the open dialog (`.hkx-dlg` is its scroll container).
- **r5 re-capture:** working tree of branch claude/ssd-site20-s2-c95f856f22822049 on top of 7bd1198218cb7a0be38e51315b3b6141e26c49f5 with the r5 source changes committed alongside these PNGs (r2b crops were at b92a7943…; all 32 PNGs overwritten by r5)
- **`git rev-parse HEAD:templates/tablesort.js`:** `2a848af0aeeeaf5312ccbd7d88aee4441474dfea` (site copy byte-identical, sha256 `995ddaf84cf481b2fc94a160fc755f9c9c6f3bd1b838dc7872f22c0e5a321b57`; changed by r5)
- **Language/theme method (r5):** theme and language are set BEFORE navigation via `context.addInitScript` (localStorage `theme`/`lang`, `themeAuto` removed), so the page's own <head> boot script applies data-theme/data-lang before tablesort.js initializes — the path a returning zh user takes. No setTheme/setLang after load. Gates per context: data-theme/data-lang equal the requested values and zero `langchange` events reached the page; in the nomatch state the reset label equals `Clear filter` / `清除筛选`, still with zero `langchange` events. r2b and earlier crops set the language AFTER load via `window.setLang()`, which dispatches `langchange` — they could not show a label that was only localized on that event (review finding F1). Gate log: 8 × `gate ok … langchanges=0`, every ZH `reset=清除筛选`.
- **Capture environment (r5):** Linux x86_64 host mastermind-pc (kernel 7.0.0-31-generic), Playwright 1.61.0 / Chromium 149.0.7827.55, system fontconfig default (Noto Sans + Noto Sans CJK), no FONTCONFIG_FILE override, local server python3 -m http.server 8942 --bind 127.0.0.1 --directory site.
- **Page stylesheet present:** `assets/css/7de16248.css` (sparse set widened with `/site/assets/`); same-origin stylesheet/script 4xx = 0 (r2b request gate — recorded per run in the lane log `requests_r2b.txt`)
- **Known limitation — local 404s outside the gate:** the r5 request log (`requests_r5.txt`) records 16 same-origin 404s, all `fetch`es of `/live/quotes.json` and `/live/overlay.json` (2 per context × 8 contexts) — the live-ticker data exists on `origin/main` but sits outside this sparse checkout (`site/live/` absent), so crops render with no live data. No font 404 was recorded this run (font=0). Aborted external hosts: none — no non-127.0.0.1 host was requested.
- **Synthetic tokens:** `ZZTEST13`, `ZZTEST14` — two cloned data rows appended in-page (SYNTHETIC hydration; no real late-row consumer exists on this page) so the `one` state has a deterministic single match; the `one`/`nomatch` queries are `ZZTEST13` / `qqqnomatchqqq`
- **Matrix:** state × theme (`dark|light`) × lang (`en|zh`) × viewport (`1440` = 1440×900, `390` = 390×844) = 32 PNGs named `<state>--<theme>--<lang>--<vw>.png`
- **Crop:** union of the filter bar and the table's header + first 6 visible data rows (hidden filtered rows collapse to zero height), clipped to the viewport width, at most 480 px tall — `page.screenshot({clip})`, never full-page
- **Capture script:** `capture.cjs` (this directory; `node capture.cjs <pagePath> <port> <outDir> [requestsLog]`, non-127.0.0.1 requests aborted; the optional 4th arg appends the same-origin ≥400 + aborted-host request log)

**Synthetic query/hydration on a real built page; local server; not production.**

## r2b contrast gate (measured on the r2b crops; r5 changes no CSS, class or colour)

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
- **`nomatch`** — query `qqqnomatchqqq`: status reads `No matching rows · 0 / 15` (EN) / `无匹配行 · 0 / 15` (ZH) with the `·` U+00B7 separator, and the `Clear filter` / `清除筛选` reset button (`gbtn gbtn-sm gbtn-quiet`, `type="button"`) sits after the count span; no data rows (header remains). In r5 the ZH label is present from page load (no language event).
- **`keyfocus`** — the numeric `20d RS` header focused by keyboard (Tab arms keyboard modality, then focus) and sorted with Enter: `data-dir=desc` shows the ↓ arrow, `aria-sort="descending"` on that cell only, and the browser focus ring on the header cell.

Theme/lang/viewport coverage: every state exists in all 8 theme × lang × viewport combinations listed above.
