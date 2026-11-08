# China Explore: layout and keyboard evidence

The 24 PNGs in `manifest.json` show the anonymous **candidate**, not a signed-in production deployment. They were captured from the `/sector_central_china.html#explore` route rendered with the pinned template, scripts, styles and committed 2026-11-02 China data from `4cd6d08918e9fed5b847c526ec090121ead3884b`. The rendering used the checked-in Jinja template and data in an isolated site directory, not a new market-data build. The manifest records the actual capture-tool hash. The earlier desktop and phone WebPs are overview previews, not the interaction evidence.

For each of desktop (1440×900) and phone (390×844), English and Chinese, and light and dark, the manifest includes three states: at rest, focus on the first theme name, and pointer hover over a category card. All 24 assets were checked against their SHA-256, byte length and PNG dimensions. The desktop and touch-width hover pictures demonstrate the pointer styling; they do not assert that tapping a phone is hover. The capture reported no failed asset requests or console errors.

```sh
python3 scripts/capture_page_evidence.py --site-dir site \
  --routes '/sector_central_china.html#explore' --viewports desktop,mobile \
  --locales en,zh --themes light,dark --max-pages 1 --settle-ms 450 --timeout-s 12 --delay-ms 0 \
  --force-state 'theme-focus:focus(#theme-desk .tcard:first-child .nm)' \
  --force-state 'category-hover:hover(#cards .card:first-of-type)' \
  --output-dir mockups/evidence/china-explore-20261102/screenshots \
  --manifest mockups/evidence/china-explore-20261102/manifest.json \
  --smells mockups/evidence/china-explore-20261102/smells.json
```

`journey.json` separately records the real Chromium interactions at 320, 390 and 1440 pixels in all four locale/theme combinations. In each, Show all revealed 22 cards; the full text of every name cleared the score; all 22 SVG previews fit within their own card; the populated narrative cards fit their grid. Keyboard navigation opened Details and the Baijiu holdings list with all seven rows visible and focus on the member disclosure. The 320px regression previously produced a 370px-wide document from a fixed 340px narrative track. The fix is scoped to China Explore. The anonymous, locally served captures prove neither hosted CI, independent review nor production release.
