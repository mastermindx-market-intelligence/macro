# Sector Dossier (fund page) — L6.4 wave capture

PR #7646, Sector Cycles wave, lane L6.4. The wave changed the fund dossier template
`templates/sector.html.j2` twice: L5 (`0ead4029`, the native Sector Dossier with
its Cycle tab, C17/C21/C22) and L6.5q (`b8ad83cc`, the ZH wording 入场形态 and
基准率, never 配置 or 胜率). This pack shows the rendered page, `sectors/XLK.html`,
in every theme × language × viewport cell, with the dossier tabs forced to hover
and to focus.

## Cells

| viewport | lang | theme | forced state | PNG | size |
|---|---|---|---|---|---|
| desktop 1440 | en | dark | — | `69775610905e9513.png` | 1440×1717 |
| desktop 1440 | en | dark | scd_tab_focus | `67ddf920ae3abd8b--scd_tab_focus.png` | 1440×1717 |
| desktop 1440 | en | dark | scd_tab_hover | `b79540943ccd0a43--scd_tab_hover.png` | 1440×1717 |
| desktop 1440 | en | light | — | `ce14dee6de456f4c.png` | 1440×1717 |
| desktop 1440 | en | light | scd_tab_focus | `c4a62e43feedc681--scd_tab_focus.png` | 1440×1717 |
| desktop 1440 | en | light | scd_tab_hover | `965901824a5f4f5e--scd_tab_hover.png` | 1440×1717 |
| desktop 1440 | zh | dark | — | `df0ff50c7b124581.png` | 1440×1716 |
| desktop 1440 | zh | dark | scd_tab_focus | `e5cd73911d90e602--scd_tab_focus.png` | 1440×1716 |
| desktop 1440 | zh | dark | scd_tab_hover | `77e9d9918c28fbda--scd_tab_hover.png` | 1440×1716 |
| desktop 1440 | zh | light | — | `5b9e2ee6f656bb5d.png` | 1440×1716 |
| desktop 1440 | zh | light | scd_tab_focus | `d071ebeaa23dc3c9--scd_tab_focus.png` | 1440×1716 |
| desktop 1440 | zh | light | scd_tab_hover | `17468cf59ad0178b--scd_tab_hover.png` | 1440×1716 |
| mobile 390 | en | dark | — | `c196324f2d5593c5.png` | 390×2671 |
| mobile 390 | en | dark | scd_tab_focus | `f0e09daacbfd54e3--scd_tab_focus.png` | 390×2671 |
| mobile 390 | en | dark | scd_tab_hover | `6002e96fe145ccc4--scd_tab_hover.png` | 390×2671 |
| mobile 390 | en | light | — | `a8d3e864744431e4.png` | 390×2671 |
| mobile 390 | en | light | scd_tab_focus | `7e6507e65bda8e54--scd_tab_focus.png` | 390×2671 |
| mobile 390 | en | light | scd_tab_hover | `0b5f8e0f14ea4d1f--scd_tab_hover.png` | 390×2671 |
| mobile 390 | zh | dark | — | `33c569feac5a2c7a.png` | 390×2554 |
| mobile 390 | zh | dark | scd_tab_focus | `0587525863d7a0e7--scd_tab_focus.png` | 390×2554 |
| mobile 390 | zh | dark | scd_tab_hover | `0a02eda22656d9b3--scd_tab_hover.png` | 390×2554 |
| mobile 390 | zh | light | — | `00a02103b32ee963.png` | 390×2554 |
| mobile 390 | zh | light | scd_tab_focus | `5a9f532ba6013c1a--scd_tab_focus.png` | 390×2554 |
| mobile 390 | zh | light | scd_tab_hover | `590c56bddd94ba36--scd_tab_hover.png` | 390×2554 |

## Results

- 24 of 24 cells captured. 0 console errors, 0 failed responses.
- No horizontal overflow at either viewport; no element wider than the viewport.
- One h1, three h2, seven panels, 306 visible words (EN desktop light).
- Forced states: `scd_tab_hover` and `scd_tab_focus` on `.scd-tabs [role="tab"]`.
  The tool applies each state to the first matching tab (`locator(...).first`): hover
  through a pointer move, focus through `focus()`. The template's rules for them are
  `var(--text)` on `var(--panel2)` for hover and a 2 px `var(--link)` outline for
  `:focus-visible`.
- `asof_present` is **false**: the census found no as-of stamp on this page. This
  pack does not claim that the dossier shows its data date; that check belongs to
  the P22 production journey.

## How it was captured

- **Source.** Branch `claude/sic-cycles-wave-20261102` at `3fdb12f6787e1d92fc21c6d256cf645e16287fe9`. The manifest's
  `target.resolved_sha_or_none` is null by design (a live origin does not disclose
  the commit it serves), so this section is the record of what was rendered.
- **Render.** `templates/sector.html.j2` sha256
  `64714e3f8fbacf3d1f2140d1c633f106dc29d28026f56bc80255f8c3a1c6f74d`, last changed in
  `b8ad83cc` and identical at `3fdb12f6787e1d92fc21c6d256cf645e16287fe9`. `sectors/XLK.html` was rendered at
  2026-11-05T16:09:21Z, after `b8ad83cc` was committed (16:08:47Z). The fund render
  report lists 11 funds, 0 gaps, 27 files written.
- **Origin.** A scratch render served on `127.0.0.1:8743` by
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
  --registry <scratch>/page_registry.json --base-url http://127.0.0.1:8743 --routes /sectors/XLK.html \
  --output-dir mockups/evidence/sector-cycles-wave-dossier --manifest mockups/evidence/sector-cycles-wave-dossier/manifest.json --smells mockups/evidence/sector-cycles-wave-dossier/smells.json \
  --viewports desktop,mobile --locales en,zh --themes light,dark --settle-ms 1500 \
  --as-of 2026-11-05T12:00:00Z \
  --force-state 'scd_tab_hover:hover(.scd-tabs [role="tab"])' \
  --force-state 'scd_tab_focus:focus(.scd-tabs [role="tab"])'
```

## Not proven here

- Signed-in tiers (free, essential, pro). The manifest records them as gaps: they
  need an authenticated session and approved fixtures. Every cell is anonymous.
- Page states loading, empty, stale and error. They are not synthesizable against
  static output; the manifest records them as gaps.
- Production. This is a local scratch render. The deployed page and its natural
  nightly update are owed at P22.
