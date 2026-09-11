#!/usr/bin/env python3
"""Browser proof for an isolated real-builder Alert Center output."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    assert (out / 'alerts.html').is_file(), 'Run prove_alert_center_v2.py first'
    payload = json.loads((out / 'factordata/alerts_triage.json').read_text())
    by_id = {a['alert_id']: a for a in payload['explorer']['signals']}
    report = {'checks': [], 'screenshots': [], 'page_errors': [], 'production_acceptance': False}
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(out)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/alerts.html'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900}, locale='en-US')
            page = context.new_page()
            page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
            page.goto(url, wait_until='domcontentloaded')
            page.locator('#ac-results .acx-row').first.wait_for()
            assert page.locator('#ac-results .acx-row').count() == 8
            report['checks'].append('Now initially shows eight canonical ranked observations')
            page.select_option('#ac-source', 'bonds')
            ids = page.locator('#ac-results .acx-row').evaluate_all('(rows) => rows.map(r => r.dataset.alertId)')
            assert ids and all(by_id[id_]['source'] == 'bonds' for id_ in ids)
            report['checks'].append('Full-source Bonds evidence is reachable beyond the capped queue')
            page.fill('#ac-search', 'NO_MATCH_EXPECTED_4729')
            page.locator('#ac-noresults').wait_for(state='visible')
            assert page.locator('#ac-results .acx-row').count() == 0
            page.click('#ac-reset-empty')
            assert page.locator('#ac-results .acx-row').count() == 25
            report['checks'].append('Search AND source filtering, genuine no-results, and reset')
            selected = page.locator('#ac-results .acx-row').first.get_attribute('data-alert-id')
            page.locator('#ac-results .acx-row').first.click()
            assert page.locator('#ac-detail').evaluate('(d) => d.open')
            assert selected in page.url
            assert page.locator('#ac-share').get_attribute('href') == page.url
            page.reload(wait_until='domcontentloaded')
            assert page.locator('#ac-detail').evaluate('(d) => d.open')
            assert page.locator('#ac-detail-title').inner_text()
            report['checks'].append('Evidence selection has a reloadable canonical-ID permalink')
            page.keyboard.press('Escape')
            assert not page.locator('#ac-detail').evaluate('(d) => d.open')
            assert page.locator(':focus').get_attribute('data-alert-id') == selected
            report['checks'].append('Native Escape closes evidence and restores the selected row')
            page.click('[data-view="history"]')
            page.go_back(wait_until='domcontentloaded')
            assert page.locator('[data-view="signals"]').get_attribute('aria-current') == 'page'
            page.goto(url + '#sev=major&cl=all&q=recurring&s=%E0%A4%A', wait_until='domcontentloaded')
            assert page.locator('#ac-noresults').is_visible()
            report['checks'].append('Browser back and malformed legacy hash values do not crash')
            page.goto(url, wait_until='domcontentloaded')
            for width, height, size in [(1440, 900, 'desktop'), (390, 844, 'mobile')]:
                page.set_viewport_size({'width': width, 'height': height})
                for theme in ('dark', 'light'):
                    for lang in ('en', 'zh'):
                        page.evaluate('([theme,lang]) => {document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;}', [theme, lang])
                        page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Horizontal overflow: {size}/{theme}/{lang}'
                        first_row = page.locator('#ac-results .acx-row').first.bounding_box()
                        name = f'{size}-{theme}-{lang}.png'
                        page.screenshot(path=str(out / name))
                        report['screenshots'].append(name)
                        report.setdefault('viewport_metrics', []).append({'name':name, 'first_row':first_row})
                        assert first_row and first_row['y'] + first_row['height'] <= height, f'No first-glance signal: {size}/{theme}/{lang}'
            report['checks'].append('Dark/light × EN/ZH × desktop/mobile: no overflow and first signal in first viewport')
            page.set_viewport_size({'width':1440, 'height':900})
            page.evaluate("document.documentElement.dataset.theme='dark';document.documentElement.dataset.lang='en'")
            page.click('[data-view="history"]')
            page.locator('#ac-results .acx-row').first.click()
            assert 'evt=' in page.url, 'Historical selection must identify its actual event date, not silently open only the latest signal'
            report['checks'].append('History selection retains the actual firing clock in its permalink')
            page.screenshot(path=str(out / 'desktop-evidence-history.png'))
            report['screenshots'].append('desktop-evidence-history.png')
            assert not report['page_errors'], report['page_errors']
            report['passed'] = True
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        report.setdefault('passed', False)
        (out / 'browser-proof.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
