# China Sector Central — wave capture at L6.21

PR #7646, Sector Cycles wave. This pack shows the rendered China Sector Central page at
the branch head in every theme × language × viewport cell. Each cell is captured
three times: at rest, with a handoff name forced to hover, and with a view-rail button
forced to keyboard focus. It supersedes the L6.4 capture (`3fdb12f6`) and the L6.18
capture of this directory, which had no focus cells.

The wave changed the China page in five lanes:

- **L6.5d** (`7df8e95e`). Handoff names drop their fixed direction ink.
- **L6.10** (`54443adb`). The handoff arrow head and its gradient read
  `var(--si-ink-up, var(--up))`, so they follow the locale's up ink.
- **L6.11** (`3fdb12f6`). The What-changed chips wrap inside the phone width, as the
  US chips do.
- **L6.17** (`925921fb`). The What-to-Act-On-Now lane headers lose the 3 px top bar
  that `theme.css` paints through `::before`. The board's include now sets
  `.anv2-lane-hd::before { content: none; }`, so a lane is named by its title and count.
  The Reduce / Avoid subtitle drops its advice clause: "Trend weakening" (趋势转弱).
- **L6.18** (`48182b7f`). The view rail marks the selected view with a quiet fill
  (`color-mix` of the link ink at 11% into the panel), link ink and weight 700. It no
  longer uses a coloured edge: the desktop rail had none, and the 390 px switcher had
  a blue bottom underline (`DESIGN_DOCTRINE.md` §3). `:focus-visible` keeps a full
  2 px outline. `tests/test_china_si_workspace_shell.py::test_rail_selection_has_no_colored_edge`
  guards both layouts.

## Cells

| viewport | lang | theme | forced state | PNG | size |
|---|---|---|---|---|---|
| desktop 1440 | en | dark | — | `8e16dfae4890a1f4.png` | 1440×1407 |
| desktop 1440 | en | dark | rvx_hocol_name_hover | `e0ddb73cdd6ed09f--rvx_hocol_name_hover.png` | 1440×1407 |
| desktop 1440 | en | dark | si_view_btn_focus | `13453171e35b4600--si_view_btn_focus.png` | 1440×1407 |
| desktop 1440 | en | light | — | `9479c5c40db699e1.png` | 1440×1407 |
| desktop 1440 | en | light | rvx_hocol_name_hover | `d9058977455aab13--rvx_hocol_name_hover.png` | 1440×1407 |
| desktop 1440 | en | light | si_view_btn_focus | `d87d7d9ce7ecdfd2--si_view_btn_focus.png` | 1440×1407 |
| desktop 1440 | zh | dark | — | `0a6b51bfabf3b380.png` | 1440×1346 |
| desktop 1440 | zh | dark | rvx_hocol_name_hover | `63036af34422dd43--rvx_hocol_name_hover.png` | 1440×1346 |
| desktop 1440 | zh | dark | si_view_btn_focus | `4d45b332788c1be0--si_view_btn_focus.png` | 1440×1346 |
| desktop 1440 | zh | light | — | `555e4cb6baed9530.png` | 1440×1346 |
| desktop 1440 | zh | light | rvx_hocol_name_hover | `3b1e6d20a65cb3f4--rvx_hocol_name_hover.png` | 1440×1346 |
| desktop 1440 | zh | light | si_view_btn_focus | `5c8f6f3bf6dbc5f9--si_view_btn_focus.png` | 1440×1346 |
| mobile 390 | en | dark | — | `f9d3bf748ba8bae6.png` | 390×3091 |
| mobile 390 | en | dark | rvx_hocol_name_hover | `09c7491eb0b2c206--rvx_hocol_name_hover.png` | 390×3091 |
| mobile 390 | en | dark | si_view_btn_focus | `2ac0d970021ef45f--si_view_btn_focus.png` | 390×3091 |
| mobile 390 | en | light | — | `5e871aa15567a183.png` | 390×3091 |
| mobile 390 | en | light | rvx_hocol_name_hover | `765d816d6da0f12a--rvx_hocol_name_hover.png` | 390×3091 |
| mobile 390 | en | light | si_view_btn_focus | `b7df98e18a284057--si_view_btn_focus.png` | 390×3091 |
| mobile 390 | zh | dark | — | `8cd9b0fe30a8d155.png` | 390×2784 |
| mobile 390 | zh | dark | rvx_hocol_name_hover | `194a6b0911c5dcbd--rvx_hocol_name_hover.png` | 390×2784 |
| mobile 390 | zh | dark | si_view_btn_focus | `0f2d0b70b8f0b390--si_view_btn_focus.png` | 390×2784 |
| mobile 390 | zh | light | — | `98e168865f813d29.png` | 390×2784 |
| mobile 390 | zh | light | rvx_hocol_name_hover | `c3b09be89a800631--rvx_hocol_name_hover.png` | 390×2784 |
| mobile 390 | zh | light | si_view_btn_focus | `f94ef8bf1d96e461--si_view_btn_focus.png` | 390×2784 |

## Results

- **Capture.** 24 of 24 cells captured on the first run, with 0 console errors and 0
  failed responses.
- **Overflow.** Neither viewport overflows horizontally, and the 390 px page is 390 px
  wide. `elements_wider_than_viewport` is 3 on mobile: the decorative
  `.rvx-aurora` blobs `b.a1`, `b.a2` and `b.a3`, clipped by their container's
  `overflow-x: hidden`. That is not page overflow. Desktop reports 0.
- **Structure.** One h1, one h2, two panels and 397 visible words. The as-of stamp is
  present.
- **Rail selection (inspected in the PNGs).** At 1440, the selected "Overview" is a
  filled pill with link ink and no edge (desktop EN light and ZH dark). At 390, the
  selected switcher segment is a filled tile with no underline (mobile EN light and
  ZH dark).
- **Act-now lanes (inspected in the PNGs).** The four lane headers have no top bar.
  The Reduce / Avoid subtitle reads "Trend weakening".
- **Page height.** Unchanged from the L6.18 capture: desktop EN 1407 px and ZH 1346 px,
  mobile EN 3091 px and ZH 2784 px. At L6.18 the mobile pages were 3 px shorter than at
  L6.4 (EN 3094 → 3091 px, ZH 2787 → 2784 px), from the switcher's new padding.
- **Layout shift.** CLS is unchanged from the previous recapture: about 0.68 on
  desktop and 0.27–0.31 on mobile. These are known numbers and are not new to this
  head.
- **Arrow ink.** Measured at L6.4 on the rendered arrow head: EN `rgb(69, 184, 115)`
  (green up) and ZH `rgb(224, 100, 100)` (red up, 红涨绿跌). It was not re-measured
  here, because its rule has not changed since.
- **Forced state.** `rvx_hocol_name_hover` hovers `.rvx-hocol .nm`. The gate asks
  for hover proof because the file's `.nm` class carries a hover rule elsewhere
  (`.scc-desk-tbl .nm a:hover`). The handoff name has no hover rule of its own and keeps
  `var(--text)` ink, so the forced cell shows no direction or health colour.
- **Rail focus (inspected in the PNGs).** `si_view_btn_focus` focuses
  `.si-view-btn[data-view=map]`, the "The Map" button. The gate asks for focus proof
  because the template's `:focus-visible` rule changed at L6.18. At 1440, in EN light
  and EN dark, the focused button carries a complete outline on all four sides, and
  the selected "Overview" keeps its fill. The forced focus does not move the
  selection.
- **Search box.** The 390 px header search box shows a prefilled "600". This is the
  shared shell's search, outside this page's source. It is disclosed on the PR as n1.

## How it was captured

- **Source.** Branch `claude/sic-cycles-wave-20261102`. The render is of
  `48182b7f4559cb9bdeee6118b2ba0f1e691ef435` (L6.18). The cells were captured at
  `07d1962f1e19dd115605612d073419e11c7aa80f` (L6.20). The manifest's
  `target.resolved_sha_or_none` is null by design, because a live origin does not
  disclose the commit it serves. This section is the record of what was rendered.
- **Later source.** Two commits follow the rendered head. L6.19 (`88870da0`) changes
  the fund-page dossier: `sector.html.j2`, `sector_cycles.css`,
  `sector_cycles_face.js` and `sector_dossier.js`. L6.20 (`07d1962f`) changes evidence
  only. The only one of those files this page loads is `sector_cycles.css`, where
  L6.19 adds three rules scoped to `.scf-rs-key`, `.scf-rs-k` and `.scf-rs-sw`. Only
  the fund page's RS trail emits those classes. No builder or template input of this
  page changed, so no cell here would differ at the capture head.
- **Render.** `render_cn.py` (in this directory) renders the HEAD blobs, not the
  working tree. Its report records:
  - head `48182b7f4559cb9bdeee6118b2ba0f1e691ef435`;
  - `sector_central_china.html.j2` sha256
    `c1bd5d9d42ce3afdba42de82e2fc809eeb31f2bdd20d7793abfcd5942d24c97e`;
  - generated 2026-11-05 12:00 UTC;
  - the v2 act-now block present, 16 sectors and no fences;
  - output `sector_central_china.html` at 527594 bytes.

  The included `_china_act_now_board.html.j2` has HEAD sha256
  `9ae924fe7e180fe0cca0cae12fe18ff20bf372e4a25bb062e273b02354fab6c2`.
- **Origin.** A scratch render served on `127.0.0.1:8744` by
  `mockups/evidence/sector-cycles-20261105/serve_l6.py`. Its lookup order:
  1. an `X-L6-Variant` header maps to `<out>/_variants/<v>/<path>`;
  2. `<out>/<path>`;
  3. the HEAD blob `site/<path>`;
  4. 404.

  `premiumdata/*` answers 401, the anonymous response. Each request writes one JSONL
  log line and nothing else. This is not production.
- **Tool.** `scripts/capture_page_evidence.py` 1.4.0, module sha256
  `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`, manifest schema
  `mastermind.p0_evidence.v2`. It ran unchanged under a five-line scratch wrapper,
  which only sets `BrowserType.launch(executable_path=...)` to the installed
  `chromium_headless_shell-1228` (Chromium 149.0.7827.55, the L6.4 pin). Python
  Playwright 1.62 expects build 1234, which is not installed. No package was
  installed.
- **Registry.** A scratch copy byte-identical to
  `data/product_experience/page_registry.json` at HEAD (sha256 `8d6346856bf24eb4…`),
  passed with `--registry`. The manifest and smell report were written only to this
  directory, through `--manifest`, `--smells` and `--output-dir`. The default
  `data/product_experience/` files were not touched.
- **Clock.** `--as-of 2026-11-05T12:00:00Z`, so the manifest's `generated_at` is
  that frozen clock, not the wall time. Settle was 1500 ms.

```
python3 <scratch>/cap_wrap.py scripts/capture_page_evidence.py \
  --registry <scratch>/page_registry.json --base-url http://127.0.0.1:8744 --routes /sector_central_china.html \
  --output-dir mockups/evidence/sector-cycles-wave-china --manifest mockups/evidence/sector-cycles-wave-china/manifest.json --smells mockups/evidence/sector-cycles-wave-china/smells.json \
  --viewports desktop,mobile --locales en,zh --themes light,dark --settle-ms 1500 \
  --as-of 2026-11-05T12:00:00Z \
  --force-state 'rvx_hocol_name_hover:hover(.rvx-hocol .nm)' \
  --force-state 'si_view_btn_focus:focus(.si-view-btn[data-view=map])'
```

## Not proven here

- **Signed-in tiers** (free, essential, pro). They need an authenticated session and
  approved fixtures, so the manifest records them as gaps. Every cell is anonymous.
- **Page states** loading, empty, stale and error. They cannot be synthesized against
  static output, so the manifest records them as gaps.
- **Rail hover.** It was not captured as a forced state. The rail's keyboard focus is
  now captured in pixels (see Results).
- **Desk-table name links** (`.scc-desk-tbl .nm a:hover`). They sit in the map view's
  `#sc-desk-table` disclosure, which ships `hidden`, so their hover state was not
  captured.
- **`/china.html` act-now board.** The board's lane-head override
  (`.anv2-lane-hd::before { content: none; }`) is guarded by source tests only. This
  pack holds no pixel cells of `/china.html`; that page's board is captured at P22.
- **Production.** This is a local scratch render. The deployed page and its natural
  nightly update are owed at P22.
