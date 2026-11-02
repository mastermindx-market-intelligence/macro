"""ABX3 reproducible browser checks against the built page and shared renderer.
Run from the owning checkout after scripts.build_aibrief. No model calls.
Synthetic failure inputs below are test fixtures, not market observations.
"""
from __future__ import annotations
import functools
import http.server
import json
from pathlib import Path
import threading
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'site'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'))
    body = env.get_template('_aibrief_body.html.j2').module.aibrief_body
    css = (ROOT / 'templates/theme.css').read_text() + env.get_template('_aibrief_css.j2').render()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for width in (1440, 390):
                    for theme in ('dark', 'light'):
                        for language in ('en', 'zh'):
                            page = browser.new_page(viewport={'width': width, 'height': 900})
                            page.add_init_script(f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(language)});")
                            page.goto(origin + '/aibrief.html', wait_until='domcontentloaded')
                            page.wait_for_function("document.querySelector('[data-aib-freshness]').dataset.state")
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                            assert page.locator('[data-aib-freshness]').first.get_attribute('data-state') == 'old'
                            page.locator('#tab-macro').focus()
                            page.keyboard.press('ArrowRight')
                            assert page.locator('#tab-china').get_attribute('aria-selected') == 'true'
                            assert page.locator('#brief-china').is_visible()
                            assert not page.locator('#brief-macro').is_visible()
                            page.keyboard.press('End')
                            assert page.locator('#tab-btc').get_attribute('aria-selected') == 'true'
                            assert page.evaluate('location.hash') == '#btc'
                            page.keyboard.press('Home')
                            detail = page.locator('#brief-macro .aib2-details').first
                            detail.locator('summary').focus()
                            page.keyboard.press('Enter')
                            assert detail.get_attribute('open') is not None
                            no_rails = page.locator('.aib2-stance,.aib2-card,.aib2-freshness,.aib2-kf').evaluate_all("nodes => nodes.every(n => {const s=getComputedStyle(n); return parseFloat(s.borderLeftWidth)===0 || (s.borderLeftWidth===s.borderRightWidth && s.borderLeftColor===s.borderRightColor);})")
                            assert no_rails
                            results.append({'case': 'page_navigation', 'viewport': width, 'theme': theme, 'language': language, 'pass': True})
                            page.close()
                # Real rendering of malformed/empty/hostile fixture payloads in a browser.
                fixtures = [None, [], 42, {'summary': '<img src=x onerror="window.__abx=1">',
                    'watch_items': ['Credit: verify'], 'confidence': 'unknown', 'key_facts': [None]},
                    {'summary': 'Retained research fixture', 'last_attempt': {'status': 'retained'}}]
                for index, fixture in enumerate(fixtures):
                    page = browser.new_page(viewport={'width': 390, 'height': 844})
                    page.set_content('<html data-theme="light"><head><style>'+css+'</style></head><body>'+str(body(fixture, 'macro', True))+'</body></html>')
                    assert page.locator('img').count() == 0
                    assert page.evaluate('window.__abx === undefined')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    results.append({'case': 'shared_renderer_fixture', 'fixture': index, 'pass': True})
                    page.close()
                # Failed optional review must be explicit, never attributed to rate limiting.
                page = browser.new_page()
                page.route('**/neuralweb/cortex_memo.json', lambda route: route.fulfill(status=503, body='Unavailable'))
                page.goto(origin + '/aibrief.html', wait_until='domcontentloaded')
                page.wait_for_function("document.querySelector('#cortex-body').textContent.includes('could not be loaded')")
                assert 'rate-limit' not in page.locator('#cortex-body').inner_text().lower()
                results.append({'case': 'optional_review_http_error', 'pass': True})
                page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {'scope': 'built local page plus explicitly synthetic failure fixtures; not production acceptance', 'checks': results}
    destination = ROOT / 'mockups/evidence/aibrief-abx3/browser-checks.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'checks': len(results), 'passed': sum(r['pass'] for r in results), 'report': str(destination)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
