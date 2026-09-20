# HK sector-ranking route: current-source successor proof

This is **browser fixture proof**, not a canonical production build or a deployment. PR #7163 preserves the accepted P0B receipt and screenshot bytes under `../prophet-p0b-zero-fouc/`. Its `supersessions.json` explicitly binds this HK-only successor; Canada remains on the original receipt.

## Reproduce

From the repository root, with the existing Python/Jinja and Playwright environments:

```sh
python scripts/render_stock_dashboard_fixture.py --market all --out-dir .pytest_cache/hk-successor-rendered --receipt mockups/evidence/prophet-hk-sector-link-20260916/rendered-fixture.json
node scripts/verify_stock_dashboard_mobile_layout.cjs --html .pytest_cache/hk-successor-rendered/hk_stocks.html --site-dir site --fixture-receipt mockups/evidence/prophet-hk-sector-link-20260916/rendered-fixture.json --fixture-assets-dir mockups/evidence/prophet-p0b-zero-fouc/inputs/browser-data --out mockups/evidence/prophet-hk-sector-link-20260916/mobile-layout.json --screenshot-dir mockups/evidence/prophet-hk-sector-link-20260916/screenshots
node scripts/verify_hk_sector_modal.cjs --html .pytest_cache/hk-successor-rendered/hk_stocks.html --fixture-receipt mockups/evidence/prophet-hk-sector-link-20260916/rendered-fixture.json --out mockups/evidence/prophet-hk-sector-link-20260916/sector-modal.json
```

The verifiers accept `--browser /absolute/path/to/chromium` when the installed browser is used. Actual recorded browser: Chromium 153.0.8010.12. All requests are locally fulfilled from the frozen fixture and candidate assets; provider/production sessions are not used. Re-running legitimately changes browser/version/image bytes; review and update only the explicit successor bindings, never the accepted baseline.

## Observed acceptance

The existing full layout/owner verifier passed its seven state cases and expansion, fragment, desktop, and owner-projection matrices. The additional route verifier passed eight modal activations (two controls across EN/ZH and light/dark), six explicit interaction cases covering both controls with pointer/keyboard/touch activation and close-button/Escape/backdrop dismissal, and two JavaScript-disabled same-page fallbacks. It asserts unchanged card-node identity/order, restored page overflow after dismissal, no navigation while enhanced, and zero requests to the missing `sector_ranking.html`. Both modal screenshots were visually inspected.

The exact first-frame/composer Python owners passed **163 tests**. The seven tamper variants reject changed baseline bytes, current-source drift, changed/missing successor receipts, path traversal, Canada supersession, and an unknown schema. The repository’s already-generated `site/` reference guard passed; that committed page is older than the current HK template, so this is explicitly not a fresh canonical-build receipt. A post-merge canonical render and served-page proof remain required.
