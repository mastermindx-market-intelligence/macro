# sanctions-map — UK press mark legibility (TP-0, F02 O21d R2)

Sixteen-cell Playwright capture of `sanctions_map.html` AFTER PR #8292,
verifying the radius-fixed legend news swatch and the legible UK press
mark across dark/light × EN/ZH × 1440×900 / 390×844.

## Purpose

This evidence dir is the TP-0 receipt for the R2 radius adjudication on
PR #8292. The R1 design check (`scripts/check_design_system.py
--mode enforce-added`) reported exactly 1 blocking item on the R1 diff:
the `.sm-legend .sm-legend-news i { border-radius: 2px; ... }` literal.
That literal was inert at the time R1 wrote its PR (the base `.sm-legend
i` cascade carried `var(--r-ctl,8px)` — the explicit `2px` only won
because specificity was higher, but the underlying design-system token
was still set), but it is a hazard for the next token rename. R2
replaces the literal with `border-radius:0` so the swatch stays a
square outline by design.

The cells here demonstrate that:
1. The fix does not regress the swatch in either theme (the swatch is
   still a dashed outline; the new computed `border-radius` is `0px`).
2. The map still carries `figure.sm-map[data-news-gbr="1"]` when a UK
   row survives the freshness filter, and the GBR path carries the
   `vector-effect: non-scaling-stroke` + dashed stroke + `stroke-width`
   `1.25px` (desktop) / `1.5px` (mobile) per the D6 mobile footprint
   rule.
3. The legend key, the 2-day heading, the ZH note, the seven-row event
   list, and the "no horizontal scroll" invariant hold across all 16 matrix
   points.

## D1 / D4 / D6 / D7 → R1 fix map (F1–F8)

| Fix | What it ships | Cell that proves it |
| --- | --- | --- |
| F1 (D1) — base mark rule with `vector-effect: non-scaling-stroke` and `stroke-dasharray:4 2.5` | `templates/sanctions_map.html.j2:49` | every `map-*` cell |
| F2 (D4) — light theme variant of the mark rule | `templates/sanctions_map.html.j2:51-58` | every `map-light-*.png` cell |
| F3 (D6) — mobile media block that thickens stroke to 1.5px + `stroke-dasharray:13 8` | `templates/sanctions_map.html.j2:109` | every `map-*-mobile.png` cell (`stroke-width == 1.5px`) |
| F4 (D7) — legend news row with EN/ZH copy | `templates/sanctions_map.html.j2:155` | `legend_news_count == 1` in every cell |
| F5 (D7) — 2-day heading "Official press · last 2 days" / "官方新闻 · 近两日" | `templates/sanctions_map.html.j2:181` | `h2_text` contains "last 2 days" (en) / "近两日" (zh) in every cell |
| F6 (D7) — ZH note `<p class="sm-orig l-zh">标题为官方英文原文。</p>` | `templates/sanctions_map.html.j2:184` | `sm_orig_count == 1` and `sm_orig_visible == (locale == "zh")` |
| F7 (D1) — figure-level `data-news-gbr="1"` (template-only mechanism) | `templates/sanctions_map.html.j2:134-142` | `figure_data_news_gbr == "1"` in every cell |
| F8 (R2) — radius literal removed (this PR) | `templates/sanctions_map.html.j2:79` | `legend_news_i_border_radius == "0px"` in every cell |

## Cells

| File | sha256 | w×h | theme | locale | viewport |
| --- | --- | --- | --- | --- | --- |
| `cells/map-dark-en-desktop.png` | `2ae14c2c…` | 1180×696 | dark | en | desktop |
| `cells/news-panel-dark-en-desktop.png` | `47910eb7…` | 1180×382 | dark | en | desktop |
| `cells/map-light-en-desktop.png` | `9737eeee…` | 1180×697 | light | en | desktop |
| `cells/news-panel-light-en-desktop.png` | `188157a4…` | 1180×382 | light | en | desktop |
| `cells/map-dark-zh-desktop.png` | `c045d856…` | 1180×703 | dark | zh | desktop |
| `cells/news-panel-dark-zh-desktop.png` | `dd4c78fc…` | 1180×418 | dark | zh | desktop |
| `cells/map-light-zh-desktop.png` | `d0bee8f7…` | 1180×704 | light | zh | desktop |
| `cells/news-panel-light-zh-desktop.png` | `a306fc08…` | 1180×418 | light | zh | desktop |
| `cells/map-dark-en-mobile.png` | `1053fa1a…` | 350×351 | dark | en | mobile |
| `cells/news-panel-dark-en-mobile.png` | `538c01be…` | 350×671 | dark | en | mobile |
| `cells/map-light-en-mobile.png` | `15590b2f…` | 350×352 | light | en | mobile |
| `cells/news-panel-light-en-mobile.png` | `3229d434…` | 350×671 | light | en | mobile |
| `cells/map-dark-zh-mobile.png` | `07174c8f…` | 350×309 | dark | zh | mobile |
| `cells/news-panel-dark-zh-mobile.png` | `96473f48…` | 350×676 | dark | zh | mobile |
| `cells/map-light-zh-mobile.png` | `cb0d3d37…` | 350×310 | light | zh | mobile |
| `cells/news-panel-light-zh-mobile.png` | `32168951…` | 350×676 | light | zh | mobile |

The full per-cell sha256 (and per-cell DOM metrics) lives in
`manifest.json` under each entry's `sha256` and `dom` keys.

## Per-cell DOM summary (the S4 metrics, recorded for every cell)

Every cell carries the same S4 predicates and is checked fail-closed
(see `_assert_dom_metrics` in `capture.py`):

- `figure.sm-map` carries `data-news-gbr="1"` (the template-only mechanism
  introduced by R1).
- The GBR path `.wm-c[data-iso3="GBR"]` exists; its computed
  `vector-effect` is `non-scaling-stroke`, its `stroke-dasharray` is
  non-`none`, and its `stroke-width` is `1.25px` (desktop) / `1.5px`
  (mobile) per the media query at `templates/sanctions_map.html.j2:109`.
- Exactly one `.sm-legend-news` row exists, and its `i` element's
  computed `border-style` is `dashed` (the swatch remains a dashed
  outline — R2 changes only the radius literal).
- Exactly one `.sm-orig` element exists, and its `offsetParent` is
  non-null iff `locale == "zh"`.
- `section#event-pins h2` contains `last 2 days` (en) / `近两日` (zh).
- `section#event-pins li` count is `7` (the full fixture renders).
- `document.documentElement.scrollWidth <= window.innerWidth` (no
  horizontal scroll at either viewport).
- Every `.sm-events li > span` sits on a single client rect (the
  `white-space:nowrap` rule at line 81 holds, including for the ≥90-char
  titles at 390 wide).

## Honest limits

- **Fixture render, not served route.** The R2 radius patch is on this
  branch but unmerged; the served route cannot show it yet. The capture
  tool renders `templates/sanctions_map.html.j2` directly with a fixture
  news parquet (4 UK + 3 EU, hard-coded `asof=2026-10-02`, with
  `seendate` spanning 2026-10-01 and 2026-10-02 so the rows
  demonstrably span two dates), so the cells reflect what the page
  *will* render once #8292 lands.
- **DSF 1.** The diff between R1 and the `frozen` mark rules is
  display-only; the radius literal correction does not change user-visible
  behavior at the served site (the literal was inert), so the cells
  look the same as the R1 evidence dir's `news-panel-*` cells for the
  news-panel region. The cells here exist to receive the bytes-after-fix
  proof and to keep the matrix closed across all 16 points.
- **`none_recent` / `unavailable` states are NOT captured.** The fresh
  D2 stance strings (`No European official press in the last two days
  · 近两日无欧洲官方新闻` / `We could not read today's European official
  press · 今日未能读取欧洲官方新闻`) live in
  `tests/test_sanctions_map_event_pins.py` and were the R1 fix; a
  state-less cell render would require dropping the parquet to old or
  raising `read_events`, which is a separate evidence story.
- **Synthetic titles.** The fixture titles are illustrative — they
  reflect the publishers' actual pattern (BoE rate decisions, EC
  trade notices, ECB statements) but are not a verbatim reproduction
  of any real-world press release. The capture is a visual proof of
  the legibility fixes, not a snapshot of the desk's accrual.

## Re-run

```sh
# from the repo root
python3 mockups/evidence/sanctions-map-news-mark-legibility/capture.py
```

The tool is self-contained: no credentials, no network beyond the
bundled static fixtures served from a local `python http.server` on
127.0.0.1. Re-runs produce byte-identical PNGs (the events parquet is
hard-coded to 2026-10-02 / 2026-10-01; only the `generated_at` ISO
timestamp and `capture_tool_module_sha256` move between runs).