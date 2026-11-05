# China Sector Central — L6.4 wave capture

PR #7646, Sector Cycles wave, lane L6.4. The wave changed
`templates/sector_central_china.html.j2` three times: L6.5d (`7df8e95e`, handoff
names drop their fixed direction ink), L6.10 (`54443adb`, the handoff arrow head and
its gradient read `var(--si-ink-up, var(--up))`, so they follow the locale's up ink)
and L6.11 (`3fdb12f6`, the What-changed chips wrap inside the phone width, as the US
chips do). This pack shows the rendered page in every theme × language × viewport
cell, with a handoff name forced to hover.

## Cells

| viewport | lang | theme | forced state | PNG | size |
|---|---|---|---|---|---|
| desktop 1440 | en | dark | — | `7def084f6678365e.png` | 1440×1407 |
| desktop 1440 | en | dark | rvx_hocol_name_hover | `f44de3505f22d412--rvx_hocol_name_hover.png` | 1440×1407 |
| desktop 1440 | en | light | — | `6319496ab948970c.png` | 1440×1407 |
| desktop 1440 | en | light | rvx_hocol_name_hover | `0052e1588d0b2eaa--rvx_hocol_name_hover.png` | 1440×1407 |
| desktop 1440 | zh | dark | — | `9c48f72588ea5590.png` | 1440×1346 |
| desktop 1440 | zh | dark | rvx_hocol_name_hover | `e22a7f04235cd329--rvx_hocol_name_hover.png` | 1440×1346 |
| desktop 1440 | zh | light | — | `5a1e7dc7a142076f.png` | 1440×1346 |
| desktop 1440 | zh | light | rvx_hocol_name_hover | `aa7a5ef6d271f980--rvx_hocol_name_hover.png` | 1440×1346 |
| mobile 390 | en | dark | — | `bd1629e219a5b761.png` | 390×3094 |
| mobile 390 | en | dark | rvx_hocol_name_hover | `5bacf686fc2dc5af--rvx_hocol_name_hover.png` | 390×3094 |
| mobile 390 | en | light | — | `e028c5382f54c8a1.png` | 390×3094 |
| mobile 390 | en | light | rvx_hocol_name_hover | `b1d88c770120210c--rvx_hocol_name_hover.png` | 390×3094 |
| mobile 390 | zh | dark | — | `a95e87181ddfa927.png` | 390×2787 |
| mobile 390 | zh | dark | rvx_hocol_name_hover | `f74cb2352c5e63d4--rvx_hocol_name_hover.png` | 390×2787 |
| mobile 390 | zh | light | — | `3901659efcf76da9.png` | 390×2787 |
| mobile 390 | zh | light | rvx_hocol_name_hover | `96a7c757028e2a71--rvx_hocol_name_hover.png` | 390×2787 |

## Results

- 16 of 16 cells captured. 0 console errors, 0 failed responses.
- No horizontal overflow at either viewport. At `54443adb` the 390 px page was 499 px
  wide (`horizontal_overflow` true): a What-changed chip held a whole sentence on one
  line. L6.11 lets the chip wrap (`white-space: normal; max-width: 100%`, radius from
  `var(--r-pill, 999px)`); the page is now 390 px wide.
- `elements_wider_than_viewport` is 3 on mobile: the decorative `.rvx-aurora` blobs
  `b.a1`, `b.a2`, `b.a3`, clipped by their container's `overflow-x: hidden`. Not page
  overflow. Desktop: 0.
- Arrow ink, measured on the rendered arrow head: EN `rgb(69, 184, 115)` (green up),
  ZH `rgb(224, 100, 100)` (red up, 红涨绿跌).
- One h1, one h2, two panels, 400 visible words; the as-of stamp is present.
- Forced state: `rvx_hocol_name_hover` on `.rvx-hocol .nm`. The gate asks for hover
  proof because the file's `.nm` class carries a hover rule elsewhere
  (`.scc-desk-tbl .nm a:hover`, line 277). The handoff name has no hover rule of its own and
  keeps `var(--text)` ink, so the forced cell shows no direction or health colour.

## How it was captured

- **Source.** Branch `claude/sic-cycles-wave-20261102` at `3fdb12f6787e1d92fc21c6d256cf645e16287fe9`. The manifest's
  `target.resolved_sha_or_none` is null by design (a live origin does not disclose
  the commit it serves), so this section is the record of what was rendered.
- **Render.** `render_cn.py` (in this directory) renders the HEAD blobs, not the
  working tree. Its report records head `3fdb12f6787e1d92fc21c6d256cf645e16287fe9`, template sha256
  `308c865d775426767f30f380b184a1130806ab239392520c4261bed2971156d6`, generated
  2026-11-05 12:00 UTC, the v2 act-now block present and 16 sectors.
- **Origin.** A scratch render served on `127.0.0.1:8744` by
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
  --registry <scratch>/page_registry.json --base-url http://127.0.0.1:8744 --routes /sector_central_china.html \
  --output-dir mockups/evidence/sector-cycles-wave-china --manifest mockups/evidence/sector-cycles-wave-china/manifest.json --smells mockups/evidence/sector-cycles-wave-china/smells.json \
  --viewports desktop,mobile --locales en,zh --themes light,dark --settle-ms 1500 \
  --as-of 2026-11-05T12:00:00Z \
  --force-state 'rvx_hocol_name_hover:hover(.rvx-hocol .nm)'
```

## Not proven here

- Signed-in tiers (free, essential, pro). The manifest records them as gaps: they
  need an authenticated session and approved fixtures. Every cell is anonymous.
- Page states loading, empty, stale and error. They are not synthesizable against
  static output; the manifest records them as gaps.
- The desk-table name links (`.scc-desk-tbl .nm a:hover`) sit in the map view's
  `#sc-desk-table` disclosure, which ships `hidden`; their hover state was not captured.
- Production. This is a local scratch render. The deployed page and its natural
  nightly update are owed at P22.
