# sanctions-map-event-mark — ad-hoc browser capture (MO-PAID-008 proof, 2026-10-02)

This directory is a **capture record**, not a TP-0 evidence receipt.

- `capture.py` drove a real browser against the served `sanctions_map.html` and wrote
  16 clip cells (`map-*` and `news-panel-*` × dark/light × en/zh × desktop/mobile) plus
  `manifest.json`, an ad-hoc record of those cells (bbox, data attributes, sha256).
- `manifest.json` is **not** a `mastermind.p0_evidence.v2` manifest (that schema is
  emitted by `scripts/capture_page_evidence.py` as `pages[].states`), so no
  `EVIDENCE.yml` may point at it. The receipt that shipped here with PR #8278 did, and
  `scripts/check_ui_visual_evidence.py` rule 2 rightly rejected it; it was retired by
  the main-red heal that added this file.
- The TP-0 receipt owning `templates/sanctions_map.html.j2` is
  `mockups/evidence/sanctions_map/EVIDENCE.yml`.
- Acceptance of the MO-PAID-008 proof (CEO A ruling D26) rested on the seat viewing
  these cells, and stands. A canonical v2 re-capture of the post-#8281 page is the
  follow-up proof lane, not this directory.