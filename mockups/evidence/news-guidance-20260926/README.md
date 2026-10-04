# Ticker News guidance display — synthetic browser evidence

This directory proves a bounded presentation, not production ingestion or release.
The four pages were rendered using the actual candidate ticker template and an explicitly
synthetic Company Intelligence comparison packet. The fixture removes unrelated scripts
and iframes; native disclosure interaction and actual shared CSS remain. No live or premium
source, credential, recommendation, score or model was used.

`manifest.json` was emitted by the unchanged `scripts/capture_page_evidence.py::run_capture`
through its existing injected PageDriver seam. The driver consumed genuine recorded Chrome/
Puppeteer screenshots and observed theme/locale/viewport from `browser-results.json`.
It is not a fake screenshot driver and not a claim that the default Playwright driver ran.
`target` records the driver and source digests and the fixture limitations. Network and broad
page-census metrics were not collected and are not performance claims. The 32 content-addressed
PNG files under `evidence/` are the REST matrix: 4 synthetic states x desktop/mobile x EN/ZH
x dark/light. `interaction-*.png` additionally preserve actual Enter-opened disclosures;
Space closed them in all 32 cases. These are not misfiled as REST cells.

The PNG files contain screenshots only. No font files or browser profile are distributed here.
Fixture HTML uses existing shared `theme.css` and its owned assets; capture scripts are archived
as the exact host-specific observation harness, not installed as a new runner or daemon.
The archived emitter expects the original operation evidence directory described in the PR.
All 32 cases had correct language hiding, no panel overflow, no runtime page error, and
keyboard open/close success. Three representative captures were visually inspected by the
author. This does not satisfy the separate independent review, automatic source pairing,
full live-page behavior, or production acceptance gates.
