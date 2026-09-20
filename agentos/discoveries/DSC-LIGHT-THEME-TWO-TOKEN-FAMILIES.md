---
key: LIGHT-THEME-TWO-TOKEN-FAMILIES
claim: "Macro has shared-stylesheet and standalone neutral-token families; a theme.css-only palette edit misses standalone pages unless the existing theme.js compatibility projection is emitted too."
falsifier: "Inspect the generated HTML inventory and standalone templates: this is false if all pages load theme.css or no standalone surface consumes --card/--ink."
so_what: "Author neutral materials only in theme.css, emit the matching theme.js through lib.site_assets, retain light-only --card/--ink aliases, and verify cache-versioned delivery. Never hand-maintain a competing runtime palette or import shared layout CSS into standalone pages."
kind: landmine
verified_at: 2026-09-19
verified_by: "Source census at af92792954e1ad8a4812cf0e73a2dc54dac0672a: 281 top-level HTML pages load theme.js; 201 also load theme.css, 80 do not. Existing lib.site_assets emitter and tests/test_site_assets.py verify the exact CSS projection."
scope: [macro, templates/theme.css, templates/theme.js, lib/site_assets.py]
confidence: verified
---

# Shared neutral materials, two consumers

The old unconditional `html.soft-contrast` runtime palette outcascaded the
stylesheet and changed `--bg` without rebinding standalone `--card`/`--ink`.
That made a nominally soft setting produce darker canvas / white slab contrast
and different heading ink between adjacent pages.

The repair's mission, authority, source pins, exact carrier, acceptance matrix,
current proof and remaining delivery work are recorded in
`research/LIGHT_THEME_COMFORT_REPAIR_2026_09_19.md`. That record explicitly
distinguishes a local repair, browser capture, merge, cache refresh, and live proof.

The raw template JS intentionally carries a safe empty CSS placeholder. Always
emit `site/theme.js` through `lib.site_assets.emit_theme_js`; a raw copy discards
not just this CSS but the existing auth configuration, brain version and Terminal
overlay. This task changes no data, ranking, allocations, routes, or page layouts.


## Compatibility must carry readable ink, not just surfaces
A mixed-version probe reproduced four sub-AA Hold/Avoid chip readings when old
CSS met a new neutral-only projection. The light ink calibrations now travel
inside the same canonical exported block. Keep the full current/legacy ×
EN/ZH × light/dark ink matrix: all 160 native-browser pairs pass after repair,
and corresponding fresh/legacy pairs are paint-equivalent. See
`mixed-version-before.json` and `mixed-version-after.json` under
`mockups/evidence/light-theme-comfort-20260919/`; the browser-free regression is
`test_cached_stylesheet_with_new_material_projection_clears_aa` in
`tests/test_prophet_verb_ink_contrast.py`. This is cache-version compatibility
proof, not evidence that the public CDN has published the candidate.
