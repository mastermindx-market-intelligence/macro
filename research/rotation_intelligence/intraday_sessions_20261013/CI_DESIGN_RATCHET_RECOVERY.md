# Exact-head hosted CI design-governance recovery

The 2026-10-15 hosted CI run 38685780949 concluded red in ci-pack-4. Its semantic failure was two new literal radii in `templates/sector_central.html.j2`, lines 452 and 456; the other 11 packs passed. The design-system checker identified `radius-literal` twice. The prior local contract check did not cover the independent design-governance gate.

Remedy: `.si-intra` uses the incumbent `var(--r-card,12px)` and its refresh button uses `var(--r-ctl,8px)`, matching the nearby Sector Central token idiom. No producer, access, scoring, retrieval, event or alert logic changed. The PR was disarmed before source changes and will only re-arm after exact-head checks.

Proof: the original pre-image ratchet reproducibly reports two failures; candidate with substituted token values reports zero. Updated actual-Jinja-page captures: four Chromium and four WebKit cases, no page-script errors and no overflowing panel, with current source SHA256 bound in both `ui_proof/browser_report.json` files. Focused UI+producer integration suites: 80 passed. Browser fixtures use synthetic replay, not signed-in production.

Do not merge or claim release on this note: rerun exact commit guards and hosted CI, preserve existing guarded merge ownership. Once merged, verify actual render and installed consumer separately.
