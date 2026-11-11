# Sector Cycles platform page — L6.4 wave capture

PR #7646, Sector Cycles wave, lane L6.4. The wave changed the two page-scoped style
sheets of the US Sector Cycles page: `templates/sector_cycles_platform.css` (L3
`23b5cec0`, the renderer platform: compare, fullscreen and sheet chrome, mobile
breakpoints; L6.5f `3c9b34e5` and L6.5g `81584c5d`, D34: the open mobile sheet
retires the assistant launcher) and `templates/sector_cycles_states.css` (L4
`90fe7973`, typed page states and the SSR as-of line). This pack shows the rendered
page in every theme × language × viewport cell, with the Open Sector Central
action forced to hover and to focus.

## Cells

| viewport | lang | theme | forced state | PNG | size |
|---|---|---|---|---|---|
| desktop 1440 | en | dark | — | `303e21a98c67e2ef.png` | 1440×3290 |
| desktop 1440 | en | dark | cyc_open_central_focus | `8522e4564e7c7a27--cyc_open_central_focus.png` | 1440×3290 |
| desktop 1440 | en | dark | cyc_open_central_hover | `caee2e4a78eba83a--cyc_open_central_hover.png` | 1440×3290 |
| desktop 1440 | en | light | — | `63d3120b1222548d.png` | 1440×3290 |
| desktop 1440 | en | light | cyc_open_central_focus | `b4cb7a6624bd7a01--cyc_open_central_focus.png` | 1440×3290 |
| desktop 1440 | en | light | cyc_open_central_hover | `6301b8393ed0221d--cyc_open_central_hover.png` | 1440×3290 |
| desktop 1440 | zh | dark | — | `68973f552f20df2f.png` | 1440×3477 |
| desktop 1440 | zh | dark | cyc_open_central_focus | `e3e7823ccfd87bd5--cyc_open_central_focus.png` | 1440×3477 |
| desktop 1440 | zh | dark | cyc_open_central_hover | `0ccdf057ac3e22b5--cyc_open_central_hover.png` | 1440×3477 |
| desktop 1440 | zh | light | — | `68771a87530f2911.png` | 1440×3477 |
| desktop 1440 | zh | light | cyc_open_central_focus | `030f74200712270d--cyc_open_central_focus.png` | 1440×3477 |
| desktop 1440 | zh | light | cyc_open_central_hover | `2145138d49c49c9a--cyc_open_central_hover.png` | 1440×3477 |
| mobile 390 | en | dark | — | `04d955ea0eba887f.png` | 390×4682 |
| mobile 390 | en | dark | cyc_open_central_focus | `23f2f26a698f686a--cyc_open_central_focus.png` | 390×4682 |
| mobile 390 | en | dark | cyc_open_central_hover | `c3a9d590385431ba--cyc_open_central_hover.png` | 390×4682 |
| mobile 390 | en | light | — | `784345383a51c3f5.png` | 390×4682 |
| mobile 390 | en | light | cyc_open_central_focus | `62933c93c9388691--cyc_open_central_focus.png` | 390×4682 |
| mobile 390 | en | light | cyc_open_central_hover | `6aef1847e358b11b--cyc_open_central_hover.png` | 390×4682 |
| mobile 390 | zh | dark | — | `6e670360773982be.png` | 390×4552 |
| mobile 390 | zh | dark | cyc_open_central_focus | `afde2dc5ce6ab8d3--cyc_open_central_focus.png` | 390×4552 |
| mobile 390 | zh | dark | cyc_open_central_hover | `d2d7f6204bc8fb5f--cyc_open_central_hover.png` | 390×4552 |
| mobile 390 | zh | light | — | `aad41a1403679bd8.png` | 390×4552 |
| mobile 390 | zh | light | cyc_open_central_focus | `f3f921e2ed3eb8d3--cyc_open_central_focus.png` | 390×4552 |
| mobile 390 | zh | light | cyc_open_central_hover | `f4a57547e4369a34--cyc_open_central_hover.png` | 390×4552 |

## Results

- 24 of 24 cells captured. 0 console errors, 0 failed responses.
- No horizontal overflow at either viewport: `scrollWidth` equals the viewport (1440,
  390).
- `elements_wider_than_viewport` is 21 on desktop and 11 on mobile. All of them are
  chart series inside the cycle chart's SVG (`path.mmc-hist`, `g.mmc-series`,
  `g.mmc-allseries`), drawn past the plot edge and clipped by the SVG
  (`overflow: hidden`, 1282 px desktop, 324 px mobile). The counts are identical in
  EN and ZH. They are not page overflow.
- One h1, three h2, 13 panels, 884 visible words; the as-of stamp is present.
- Forced states: `cyc_open_central_hover` and `cyc_open_central_focus` on
  `.cyc-open-central`.

## How it was captured

- **Source.** Branch `claude/sic-cycles-wave-20261102` at `3fdb12f6787e1d92fc21c6d256cf645e16287fe9`. The manifest's
  `target.resolved_sha_or_none` is null by design (a live origin does not disclose
  the commit it serves), so this section is the record of what was rendered.
- **Render.** Rendered at `cf604b9d` into a scratch tree (76 files). `git diff
  cf604b9d 3fdb12f6787e1d92fc21c6d256cf645e16287fe9` touches only `templates/sector_central_china.html.j2` and its test,
  so the render is source-equivalent to HEAD. The served `sector_cycles_platform.css`
  and `sector_cycles_states.css` are byte-identical to the templates at HEAD (sha256
  `a99d22e57e234ce0…` and `3de1b407b48ed76d…`); they ship as separate assets, not
  inlined.
- **Origin.** A scratch render served on `127.0.0.1:8741` by
  `mockups/evidence/sector-cycles-20261105/serve_l6.py`. Lookup order: an
  `X-L6-Variant` header maps to `<out>/_variants/<v>/<path>`; then `<out>/<path>`;
  then the HEAD blob `site/<path>`; then 404. `premiumdata/*` answers 401, the
  anonymous response. Each request is one JSONL log line and nothing else is
  written. This is not production.
- **Tool.** `scripts/capture_page_evidence.py` 1.4.0, module sha256
  `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`, manifest schema
  `mastermind.p0_evidence.v2`. It ran unchanged under a five-line scratch wrapper
  that only sets `BrowserType.launch(executable_path=...)` to the installed
  `chromium_headless_shell-1228` (Chromium 149.0.7827.55, the L6.4 pin). Python
  Playwright 1.62 expects build 1234, which is not installed; no package install
  was made.
- **Registry.** A scratch copy byte-identical to
  `data/product_experience/page_registry.json` at HEAD (sha256 `8d6346856bf24eb4…`),
  passed with `--registry`. The manifest and smell report were written only to this
  directory (`--manifest`, `--smells`, `--output-dir`); the default
  `data/product_experience/` files were not touched.
- **Clock.** `--as-of 2026-11-05T12:00:00Z`, so the manifest's `generated_at` is that
  frozen clock, not the wall time. Settle 1500 ms.

```
python3 <scratch>/cap_wrap.py scripts/capture_page_evidence.py \
  --registry <scratch>/page_registry.json --base-url http://127.0.0.1:8741 --routes /sector_cycles.html \
  --output-dir mockups/evidence/sector-cycles-wave-platform --manifest mockups/evidence/sector-cycles-wave-platform/manifest.json --smells mockups/evidence/sector-cycles-wave-platform/smells.json \
  --viewports desktop,mobile --locales en,zh --themes light,dark --settle-ms 1500 \
  --as-of 2026-11-05T12:00:00Z \
  --force-state 'cyc_open_central_hover:hover(.cyc-open-central)' \
  --force-state 'cyc_open_central_focus:focus(.cyc-open-central)'
```

## Not proven here

- Signed-in tiers (free, essential, pro). The manifest records them as gaps: they
  need an authenticated session and approved fixtures. Every cell is anonymous.
- Page states loading, empty, stale and error. They are not synthesizable against
  static output; the manifest records them as gaps.
- Production. This is a local scratch render. The deployed page and its natural
  nightly update are owed at P22.
