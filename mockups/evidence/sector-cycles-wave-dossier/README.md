# Sector Dossier (fund page) — wave capture at L6.21

PR #7646, Sector Cycles wave. The wave changed the fund dossier template
`templates/sector.html.j2` in four lanes:

- **L5** (`0ead4029`). The native Sector Dossier with its Cycle tab (C17/C21/C22).
- **L6.5q** (`b8ad83cc`). The ZH wording 入场形态 and 基准率, never 配置 or 胜率.
- **L6.17** (`925921fb`). The header names its data date ("Data as of" / 数据截至).
  The verdict box uses an even border, not an edge accent. The Stoch label follows
  its value. A chart that cannot load says so as a typed, neutral notice.
- **L6.19** (`88870da0`). The Cycle tab's RS trail fills the panel width and gains a
  21d / 63d legend (21日 / 63日). The breadth block uses the shared section chrome
  with neutral `.scd-*` rules. The identity header moves above the tablist, so the
  page title stays visible on all seven tabs.

This pack shows the rendered page, `sectors/XLK.html`, on two routes: the default
Overview tab and the Cycle tab (`#cycle`). Each route is captured in every theme ×
language × viewport cell, at rest, with a tab forced to hover and with a tab forced
to keyboard focus. It supersedes the L6.4 capture of this directory (`3fdb12f6`,
24 cells, Overview only).

## Cells

| route | viewport | lang | theme | forced state | PNG | size |
|---|---|---|---|---|---|---|
| `/sectors/XLK.html` | desktop 1440 | en | dark | — | `06303cf9bc149690.png` | 1440×1735 |
| `/sectors/XLK.html` | desktop 1440 | en | dark | scd_tab_focus | `a8e7c3ba689d4a19--scd_tab_focus.png` | 1440×1735 |
| `/sectors/XLK.html` | desktop 1440 | en | dark | scd_tab_hover | `5252275ebb942064--scd_tab_hover.png` | 1440×1735 |
| `/sectors/XLK.html` | desktop 1440 | en | light | — | `5aa23f39e2699550.png` | 1440×1735 |
| `/sectors/XLK.html` | desktop 1440 | en | light | scd_tab_focus | `38e46adaa85e9805--scd_tab_focus.png` | 1440×1735 |
| `/sectors/XLK.html` | desktop 1440 | en | light | scd_tab_hover | `dbd5eec292529d9d--scd_tab_hover.png` | 1440×1735 |
| `/sectors/XLK.html` | desktop 1440 | zh | dark | — | `f27a2aceae547631.png` | 1440×1734 |
| `/sectors/XLK.html` | desktop 1440 | zh | dark | scd_tab_focus | `647fd082a33d9723--scd_tab_focus.png` | 1440×1734 |
| `/sectors/XLK.html` | desktop 1440 | zh | dark | scd_tab_hover | `7e068e00808ba655--scd_tab_hover.png` | 1440×1734 |
| `/sectors/XLK.html` | desktop 1440 | zh | light | — | `6f406d9725c59be1.png` | 1440×1734 |
| `/sectors/XLK.html` | desktop 1440 | zh | light | scd_tab_focus | `73f953e59fabcd25--scd_tab_focus.png` | 1440×1734 |
| `/sectors/XLK.html` | desktop 1440 | zh | light | scd_tab_hover | `ae44744d10e6f441--scd_tab_hover.png` | 1440×1734 |
| `/sectors/XLK.html` | mobile 390 | en | dark | — | `4494b8d1c1b8e690.png` | 390×2659 |
| `/sectors/XLK.html` | mobile 390 | en | dark | scd_tab_focus | `08ba9cdba594c8b3--scd_tab_focus.png` | 390×2659 |
| `/sectors/XLK.html` | mobile 390 | en | dark | scd_tab_hover | `7564f20c93362147--scd_tab_hover.png` | 390×2659 |
| `/sectors/XLK.html` | mobile 390 | en | light | — | `6b754ae18759348e.png` | 390×2659 |
| `/sectors/XLK.html` | mobile 390 | en | light | scd_tab_focus | `5bb69b1994c7b57c--scd_tab_focus.png` | 390×2659 |
| `/sectors/XLK.html` | mobile 390 | en | light | scd_tab_hover | `360ff045474c5646--scd_tab_hover.png` | 390×2659 |
| `/sectors/XLK.html` | mobile 390 | zh | dark | — | `a6220d0d6bc52ddb.png` | 390×2543 |
| `/sectors/XLK.html` | mobile 390 | zh | dark | scd_tab_focus | `672846dd988cba13--scd_tab_focus.png` | 390×2543 |
| `/sectors/XLK.html` | mobile 390 | zh | dark | scd_tab_hover | `50e6202c330466f6--scd_tab_hover.png` | 390×2543 |
| `/sectors/XLK.html` | mobile 390 | zh | light | — | `0416f25945721034.png` | 390×2543 |
| `/sectors/XLK.html` | mobile 390 | zh | light | scd_tab_focus | `760d94fa619ed6c7--scd_tab_focus.png` | 390×2543 |
| `/sectors/XLK.html` | mobile 390 | zh | light | scd_tab_hover | `546eee4b425dcd11--scd_tab_hover.png` | 390×2543 |
| `/sectors/XLK.html#cycle` | desktop 1440 | en | dark | — | `da1e0144233c82bf.png` | 1440×1983 |
| `/sectors/XLK.html#cycle` | desktop 1440 | en | dark | scd_tab_focus | `fcc5a276985c5ce5--scd_tab_focus.png` | 1440×1983 |
| `/sectors/XLK.html#cycle` | desktop 1440 | en | dark | scd_tab_hover | `1727fae53070ecb1--scd_tab_hover.png` | 1440×1983 |
| `/sectors/XLK.html#cycle` | desktop 1440 | en | light | — | `ad8ee214a7a8897a.png` | 1440×1983 |
| `/sectors/XLK.html#cycle` | desktop 1440 | en | light | scd_tab_focus | `cbd21c740ce98505--scd_tab_focus.png` | 1440×1983 |
| `/sectors/XLK.html#cycle` | desktop 1440 | en | light | scd_tab_hover | `c13f5c916b6e7c6f--scd_tab_hover.png` | 1440×1983 |
| `/sectors/XLK.html#cycle` | desktop 1440 | zh | dark | — | `d1b7300d7ec84219.png` | 1440×1964 |
| `/sectors/XLK.html#cycle` | desktop 1440 | zh | dark | scd_tab_focus | `5844c5ab5a65324a--scd_tab_focus.png` | 1440×1964 |
| `/sectors/XLK.html#cycle` | desktop 1440 | zh | dark | scd_tab_hover | `a245f5a0186bc15f--scd_tab_hover.png` | 1440×1964 |
| `/sectors/XLK.html#cycle` | desktop 1440 | zh | light | — | `d2f32ea6d32e1eda.png` | 1440×1964 |
| `/sectors/XLK.html#cycle` | desktop 1440 | zh | light | scd_tab_focus | `7f5bace04e309338--scd_tab_focus.png` | 1440×1964 |
| `/sectors/XLK.html#cycle` | desktop 1440 | zh | light | scd_tab_hover | `80c87f286dfb5f71--scd_tab_hover.png` | 1440×1964 |
| `/sectors/XLK.html#cycle` | mobile 390 | en | dark | — | `03795cd439118797.png` | 390×2565 |
| `/sectors/XLK.html#cycle` | mobile 390 | en | dark | scd_tab_focus | `3c584dce9782df2a--scd_tab_focus.png` | 390×2565 |
| `/sectors/XLK.html#cycle` | mobile 390 | en | dark | scd_tab_hover | `979e87bc054f8808--scd_tab_hover.png` | 390×2565 |
| `/sectors/XLK.html#cycle` | mobile 390 | en | light | — | `52d1d2374f3a96c3.png` | 390×2565 |
| `/sectors/XLK.html#cycle` | mobile 390 | en | light | scd_tab_focus | `3331e290be7f1163--scd_tab_focus.png` | 390×2565 |
| `/sectors/XLK.html#cycle` | mobile 390 | en | light | scd_tab_hover | `a2e7e423d068ab0c--scd_tab_hover.png` | 390×2565 |
| `/sectors/XLK.html#cycle` | mobile 390 | zh | dark | — | `d298813578fbb4a1.png` | 390×2343 |
| `/sectors/XLK.html#cycle` | mobile 390 | zh | dark | scd_tab_focus | `d2fe67325daf6295--scd_tab_focus.png` | 390×2343 |
| `/sectors/XLK.html#cycle` | mobile 390 | zh | dark | scd_tab_hover | `ecee02c423c1158d--scd_tab_hover.png` | 390×2343 |
| `/sectors/XLK.html#cycle` | mobile 390 | zh | light | — | `047afc43b955c9bb.png` | 390×2343 |
| `/sectors/XLK.html#cycle` | mobile 390 | zh | light | scd_tab_focus | `bf70f0744bb3d91b--scd_tab_focus.png` | 390×2343 |
| `/sectors/XLK.html#cycle` | mobile 390 | zh | light | scd_tab_hover | `bc801da79ec4d259--scd_tab_hover.png` | 390×2343 |

## Results

- **Capture.** 48 of 48 cells captured, with 0 console errors and 0 failed responses
  on both routes.
- **Overflow.** Neither route overflows horizontally at either viewport, and no
  element is wider than the viewport.
- **Structure.** Overview: one h1, three h2, eight panels and 300 visible words.
  Cycle tab: one h1, one h2, eight h3, three panels and 372 visible words.
- **Data date.** `asof_present` is **true** on both routes. At L6.4 it was false;
  L6.17 added the "Data as of" stamp to the header.
- **Page title on every tab (inspected in the PNGs).** The `#cycle` cells show the
  h1 and the as-of stamp above the tablist.
- **Cycle tab (inspected in the PNGs).** The RS trail spans the panel width with the
  21d / 63d legend under it. The breadth block renders in section chrome with even
  borders and no direction ink.
- **Forced states.** `scd_tab_focus` focuses `#scd-t-overview`, and `scd_tab_hover`
  hovers `#scd-t-cycle`. The template's rules for them are a 2 px `var(--link)`
  outline for `:focus-visible` and `var(--text)` on `var(--panel2)` for hover.
  - In the focus cells, the Overview tab carries a complete outline in light and
    dark.
  - The hover cells force the Cycle tab. On the `#cycle` route that tab is already
    selected, so the hover cell looks the same as the selected state. The hover
    rule is visible only in the Overview-route hover cells.
- **Known minors, disclosed on the PR.**
  - At 390 px the floating action button overlaps the hazard cell.
  - The shared header search shows a prefilled "0".
  - The tab strip is clipped at Companies at 390 px.
  - The `now.above200d` deck-gap chip.

## How it was captured

- **Source.** Branch `claude/sic-cycles-wave-20261102`, capture head
  `07d1962f1e19dd115605612d073419e11c7aa80f` (L6.20). The manifest's
  `target.resolved_sha_or_none` is null by design, because a live origin does not
  disclose the commit it serves. This section is the record of what was rendered.
- **Render.** `templates/sector.html.j2` sha256
  `367049402ac73e528f49fb74a60cae8404db1ab71eb3aacf90beb6aa5638db26`, last changed in
  `88870da0` and identical at the capture head. The scratch fund renderer
  `render_funds.py` rendered `sectors/XLK.html` at 2026-11-06T02:44:08Z, after the
  capture head was committed (02:43:18Z). Its report records:
  - 11 funds (XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY), 0 gaps,
    27 files written;
  - XLK with 20 members, 20 holdings, last ETF close 2026-10-22, the ladder and the
    confluence block present;
  - `XLK.html` sha256
    `fc9b23e2b9e4bb4841ea3f29359d2c6ff4cbfc9e1aa90a313ef5b8c910aa0b01`;
  - nothing written outside the scratch output directory, and no file under the
    worktree's `data/`.
- **Origin.** A scratch render served on `127.0.0.1:8743` by
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
  --registry <scratch>/page_registry.json --base-url http://127.0.0.1:8743 \
  --routes /sectors/XLK.html,/sectors/XLK.html#cycle \
  --output-dir mockups/evidence/sector-cycles-wave-dossier --manifest mockups/evidence/sector-cycles-wave-dossier/manifest.json --smells mockups/evidence/sector-cycles-wave-dossier/smells.json \
  --viewports desktop,mobile --locales en,zh --themes light,dark --settle-ms 1500 \
  --as-of 2026-11-05T12:00:00Z \
  --force-state 'scd_tab_hover:hover(#scd-t-cycle)' \
  --force-state 'scd_tab_focus:focus(#scd-t-overview)'
```

## Not proven here

- **Signed-in tiers** (free, essential, pro). They need an authenticated session and
  approved fixtures, so the manifest records them as gaps. Every cell is anonymous.
- **Page states** loading, empty, stale and error. They cannot be synthesized against
  static output, so the manifest records them as gaps.
- **The other five tabs.** Only Overview and Cycle are captured.
- **Production.** This is a local scratch render. The deployed page and its natural
  nightly update are owed at P22.
