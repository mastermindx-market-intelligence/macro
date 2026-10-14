"""COT real-browser checks using the existing page-evidence owner/schema.

Manual local evidence only. Uses an anonymous temporary Chrome context; never
reads a signed-in profile, changes settings, or runs in the publication pipeline.
"""
from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from lib import config
from scripts import capture_page_evidence as evidence
from scripts.build_cot import build


def main() -> int:
    from playwright.sync_api import sync_playwright

    preview = config.ROOT / ".pytest_cache" / "cot-preview"
    build(site=preview)
    for asset in ("theme.css", "theme.js", "product-nav-icons.css", "navigation-refresh.css", "nav_market.js",
                  "logo_config.js", "stock-logos.js", "live_config.js", "live.js",
                  "account.js", "terminal_overlay.js"):
        source = config.ROOT / "templates" / asset
        if not source.exists():
            source = config.ROOT / "site" / asset
        if source.exists():
            shutil.copy2(source, preview / asset)
    fonts = config.ROOT / "templates" / "fonts"
    if fonts.exists():
        shutil.copytree(fonts, preview / "fonts", dirs_exist_ok=True)
    destination = config.ROOT / "mockups" / "evidence" / "cot-positioning-v1"
    destination.mkdir(parents=True, exist_ok=True)
    server, port = evidence.serve_site_dir(preview)
    origin = f"http://127.0.0.1:{port}"
    manager = sync_playwright().start()
    browser = manager.chromium.launch(channel="chrome", headless=True)
    driver = evidence._PlaywrightDriver(manager, browser, evidence.USER_AGENT,
        dict(evidence.DEFAULT_OBSERVER_CONFIG), 1200)
    try:
        # Behavioral proof uses the real page and actual captured CFTC data.
        context = browser.new_context(viewport={"width":1440,"height":1000})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        response = page.goto(origin + "/cot.html?market=nasdaq", wait_until="networkidle")
        assert response and response.status == 200
        page.wait_for_selector("#cot-chart svg")
        assert page.locator('.cot-table tr[data-market]').count() == 21
        page.locator('#cot-family').select_option('tff')
        assert '73,798' in page.locator('#cot-cohorts').inner_text()
        assert '-19,212' in page.locator('#cot-cohorts').inner_text()
        page.locator('#cot-cohort').select_option('leveraged_funds')
        assert page.locator('#cot-chart path').get_attribute('d')
        page.locator('#cot-search').fill('gold')
        assert page.locator('.cot-table tr[data-market]:visible').count() == 1
        page.locator('[data-select=gold]').click()
        assert 'Gold' in page.locator('#cot-detail-title').inner_text()
        page.locator('#cot-family').select_option('disaggregated')
        assert 'Managed money' in page.locator('#cot-cohorts').inner_text()
        page.locator('#cot-search').fill('no-such-market')
        assert page.locator('#cot-empty').is_visible()
        assert not errors, errors
        context.close()
        payloads = evidence.run_capture(
            rows=evidence.synthesize_rows(['/cot.html'], []), driver=driver,
            base_url=origin, output_dir=destination / 'images', manifest_dir=destination,
            viewports=('desktop','mobile'), locales=('en','zh'), themes=('dark','light'),
            delay_ms=0, timeout_s=25, generated_at=datetime.now(timezone.utc).isoformat(),
            target=evidence.site_dir_target(preview),
            selection={'mode':'explicit_routes','explicit_routes':['/cot.html'],'selected':1},
            force_states=(evidence.ForceState(name='focus_market',kind='focus',value='.cot-market-button',spec='focus_market:focus(.cot-market-button)'),),
        )
        page_bytes = (preview / 'cot.html').read_bytes()
        page_blob = hashlib.sha1(f'blob {len(page_bytes)}\0'.encode() + page_bytes).hexdigest()
        for captured in payloads['manifest']['pages']:
            captured['page_tree_sha'] = page_blob
        (destination / 'manifest.json').write_bytes(evidence.canonical_json_bytes(payloads['manifest']))
        (destination / 'smells.json').write_bytes(evidence.canonical_json_bytes(payloads['smells']))
        (destination / 'behavior.json').write_text(json.dumps({
            'schema':'cot_browser_verification.v1', 'scope':'local_preview_real_cftc_data',
            'source_snapshot':json.loads((preview / 'cotdata' / 'latest.json').read_text())['content_sha256'],
            'checks':['21 markets','Nasdaq TFF reconciliation','cohort chart','gold search','commodity detail','empty filter'],
            'page_errors':errors, 'production_verified':False,
        },indent=2))
        print('COT_BEHAVIOR_PASS',destination)
        print('MANIFEST_SCHEMA',payloads['manifest']['schema'])
    finally:
        driver.close()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
