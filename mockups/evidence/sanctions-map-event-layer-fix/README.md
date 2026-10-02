# sanctions-map-event-layer-fix — ad-hoc browser capture (F02 / O21 proof, 2026-10-02T19:47:52Z)

This directory is a **capture record**, not a TP-0 evidence receipt.

- `capture.py` materializes the origin/main `site/sanctions_map.html` blob (and the 13 referenced site assets) into a scratch directory and serves them from a fresh `127.0.0.1` socket. **That is the work it does.** Served-copy verification against the production URL is the commissioning seat's responsibility, not the lane's — its observation is recorded verbatim in `SERVED_RECEIPT.json` (and embedded in `manifest.served_receipt`). The tool never fabricates a served timestamp itself.
- The page bytes at fetch time were `page_sha256 = 314a8a00ceba02160414355dc38aab9cbe4c87a1ed9ebbf5dec814489daa5b35`. `source_commit = 891175dd18769e447d91c86147c4db51a7889fad` is the origin/main HEAD at fetch (the parent of the rendered tree). `site_commit = d2c6171bf0b30200fec972d08a1497ec534fd6ab` is the last commit on `main` that wrote `site/sanctions_map.html`; `render_source_commit = e179569208c6` is the source commit of that render. The R1 README incorrectly called d2c6171 the `source_commit`; this R2 distinguishes the three.
- After PR #8281 moved the public-news mark from a post-render path stamp to the template (`figure.sm-map[data-news-gbr]`, `section#event-pins`), and after PR #8284 removed the legacy `data-news=` path stamp (squash `3abe98831ee7`, before this lane ran — the R1 commit message still named "a sibling lane (O21c)" as the retirer; that was already retired), the capture wrote 16 clip cells (`map-*`, `news-panel-*` × dark/light × en/zh × desktop/mobile) plus `manifest.json` and `SERVED_RECEIPT.json`. `manifest.json` is an ad-hoc record of those cells (bbox, data attributes, sha256, observed `public_news_state`).
- Public-news state is classified from the rendered DOM, not from a row count. `state_inferred = ok` iff the `figure.sm-map` carries `data-news-gbr="1"` (the #8281 template-only mechanism; see `templates/sanctions_map.html.j2:134-142`); otherwise the tool reads the `#event-pins .sm-null` empty-state element (template lines 208-214) and maps the "last two days / 近两日" sentence to `none_recent`, the "could not read today's European official press / 今日未能读取欧洲官方新闻" sentence to `unavailable`, anything else to `unknown`. The `<li>` count is kept as the separate `rows` field.

## Per-theme stroke colour (not the same)

The GBR-path stroke colour is **not** identical across the two themes. `--ink-link` is a per-theme `color-mix` over `--link` and `--text` (`templates/theme.css:379`), and the rendered `path.wm-c[data-iso3="GBR"]` reads from it. Measured on this capture:

- dark  ≈ `rgb(122, 167, 224)`
- light ≈ `rgb(41, 90, 234)`

The R1 README claimed "same in both themes"; that was incorrect. The R2 review caught it (D3 minor).

## Fixed page chrome — Ask Mastermind button

The served page ships a floating "Ask Mastermind" button as fixed page chrome (loaded via the cross-origin `mm_brain.js` widget — see `CLAUDE.md` §Neural Web + Mastermind chat). It is part of the page, intentionally not hidden, and **occludes** content in the captured cells:

- desktop maps: roughly the lower-right of the map wrapper (≈ x 1085-1180, y 565-620 inside the captured map clip). Visible in `cells/map-{dark,light}-{en,zh}-desktop.png`.
- mobile panels: the stance line "Public official press from Europe. UK items mark the map; EU, euro-area and EFTA items are listed only." is partially covered; in zh the occluded words are "地图；" (inside "英国条目标注于地图；欧盟、欧元区及 EFTA 条目仅列出。"). Visible in `cells/news-panel-{dark,light}-{en,zh}-mobile.png`.

The R1 README did not disclose this; the R2 review caught it (D5 minor). The capture tool intentionally leaves the chrome visible (it is part of the served page). A future `templates/` lane should consider elevating the FAB or tightening the panel clip — those are product defects and out of scope for this evidence record.

## Notes on `manifest.json`

It is **not** a `mastermind.p0_evidence.v2` manifest (that schema is emitted by `scripts/capture_page_evidence.py` as `pages[].states`), so no `EVIDENCE.yml` points at it — a receipt that did (PR #8278) was rejected by `scripts/check_ui_visual_evidence.py` rule 2 and retired. The TP-0 receipt owning `templates/sanctions_map.html.j2` is `mockups/evidence/sanctions_map/EVIDENCE.yml`; its canonical v2 refresh is a separate lane.

## Files in this directory

- `capture.py` — capture tool
- `manifest.json` — ad-hoc record of the 16 cells + served receipt
- `SERVED_RECEIPT.json` — seat-held production URL observation (embedded verbatim into the manifest)
- `cells/` — 16 PNGs (`map-*`, `news-panel-*`)