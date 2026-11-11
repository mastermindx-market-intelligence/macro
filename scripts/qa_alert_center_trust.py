#!/usr/bin/env python3
"""Discriminating browser cases for Alerts; synthetic cases are not live proof."""
from __future__ import annotations
import argparse
from copy import deepcopy
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import hashlib
from pathlib import Path
import re
import sys
import threading
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    assert out != ROOT and out != ROOT / 'site'
    original = json.loads((out / 'factordata/alerts_triage.json').read_text())
    from engine import i18n
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    report = {'kind': 'synthetic_adversarial_browser_cases', 'production_acceptance': False, 'cases': []}
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    def fixture(name, payload, broken=False):
        html = env.get_template('alerts.html.j2').render(**payload)
        if broken:
            html = re.sub(r'(<script id="ac-data"[^>]*>).*?(</script>)', r'\1{"broken":\2', html, flags=re.S)
        (out / (name + '.html')).write_text(html)
        return base + '/' + name + '.html'
    def check(name, fn):
        try:
            fn()
            report['cases'].append({'name': name, 'passed': True})
        except Exception as exc:
            report['cases'].append({'name': name, 'passed': False, 'error': str(exc)[:1000]})
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()
            for verdict in ['no_edge', 'killed', 'underpowered', 'confirmer']:
                def negative(v=verdict):
                    p = deepcopy(original)
                    a = p['explorer']['signals'][0]
                    a['validation'] = {'backtested': True, 'verdict': v, 'hit': 0.0, 'n': 0}
                    page.goto(fixture('trust-' + v, p) + '#id=' + a['alert_id'], wait_until='domcontentloaded')
                    label = page.locator('[data-validation-verdict]')
                    assert label.count() == 1 and label.get_attribute('data-validation-verdict') == v
                    assert label.is_visible() and label.inner_text().strip()
                    assert '0.0%' in page.locator('#ac-detail-body').inner_text()
                check('Validation verdict preserved: ' + verdict, negative)
            for board_day in [None, 'invalid-day', '2999-01-01']:
                def unknown(value=board_day):
                    p = deepcopy(original); p['board_date'] = value
                    page.goto(fixture('trust-day-' + str(value), p), wait_until='domcontentloaded')
                    assert page.locator('#ac-stale').is_visible(), 'Missing/invalid/future snapshot day must not look current'
                    assert page.locator('#ac-stale').inner_text().strip()
                check('Snapshot day visible: ' + str(board_day), unknown)
            def legacy_major():
                page.goto(base + '/alerts.html#view=signals&sev=major', wait_until='domcontentloaded')
                ids = page.locator('#ac-results .acx-row').evaluate_all('(rows)=>rows.map(r=>r.dataset.alertId)')
                by_id = {a['alert_id']: a for a in original['explorer']['signals']}
                assert ids and all(by_id[i]['severity'] == 'major' for i in ids), 'Legacy major must not include critical'
            check('Legacy major filter remains exact', legacy_major)
            def empty_link():
                p = deepcopy(original); a = p['explorer']['signals'][0]; a['link'] = ''
                page.goto(fixture('trust-link', p) + '#id=' + a['alert_id'], wait_until='domcontentloaded')
                links = page.locator('#ac-detail-body a').all_text_contents()
                assert not any('Open original evidence' in s for s in links), 'Empty source link must not resolve to this same page'
            check('Empty source link is not self-evidence', empty_link)
            def failed_payload():
                page.goto(fixture('trust-broken-json', original, broken=True), wait_until='domcontentloaded')
                fallback = page.locator('#ac-fallback')
                assert fallback.count() == 1 and fallback.is_visible(), 'JS failure must retain visible original source links'
                assert fallback.locator('a[href*=".html"]').count() > 0
                assert not page.locator('#ac-filters').is_visible(), 'Do not leave dead interactive controls exposed'
            check('Broken JSON has a useful source fallback', failed_payload)
            def historical_detail():
                p = deepcopy(original); a = p['explorer']['signals'][0]
                event = dict(alert_id=a['alert_id'], source=a['source'], headline='Historical observation',
                             detail='HISTORICAL_DETAIL_NOT_LATEST', detail_zh='历史记录而非最新摘要',
                             board_date='2026-09-02', event_date='2026-09-02', event_ts=None,
                             date_precision='date', recorded_at='2026-09-03T12:00:00Z')
                p['explorer']['history'].insert(0, event)
                url = fixture('trust-history', p) + '#view=history&id=' + a['alert_id'] + '&evt=2026-09-02'
                page.goto(url, wait_until='domcontentloaded')
                selected = page.locator('[data-selected-event]')
                assert 'HISTORICAL_DETAIL_NOT_LATEST' in selected.inner_text()
                assert '2026-09-03T12:00:00Z' in selected.inner_text()
            check('Historical inspector keeps selected event detail and record clock', historical_detail)
            def selected_beyond_page():
                a = original['explorer']['signals'][40]
                page.goto(base + '/alerts.html#view=signals&id=' + a['alert_id'], wait_until='domcontentloaded')
                page.keyboard.press('Escape')
                assert page.locator(':focus').get_attribute('data-alert-id') == a['alert_id']
            check('Deep-linked selection restores a row beyond page one', selected_beyond_page)
            def exact_source_binding():
                manifest = json.loads((out / 'input-manifest.json').read_text())
                required = ['engine/alert_triage.py', 'engine/alert_center_view.py',
                            'engine/alert_time.py', 'scripts/build_site.py',
                            'templates/alerts.html.j2', 'templates/alert_center.css',
                            'templates/alert_center.js', 'templates/theme.css']
                for name in required:
                    assert manifest['candidate_sources'][name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                assert manifest['sources_unchanged_during_build'] is True
                assert manifest['inputs_unchanged_during_build'] is True
                assert manifest['outputs']['alerts.html'] == hashlib.sha256((out / 'alerts.html').read_bytes()).hexdigest()
            check('Real-builder proof binds exact source bytes and output', exact_source_binding)
            def required_shared_assets():
                for name in ['live.js', 'live_config.js', 'nav_market.js']:
                    assert (out / name).is_file(), 'Shared page dependency absent: ' + name
            check('Shared page assets are present in the real-builder preview', required_shared_assets)
            # Exercise the real producer's typed read seam; never edit a live store.
            from datetime import date
            from unittest.mock import patch
            from engine import alert_triage as triage
            board_day = date.fromisoformat(original['board_date'])
            real_reader = triage._jsonl_raw
            def unavailable_bonds(source, *args):
                if source == 'bonds':
                    return triage._read(source, triage.READ_UNAVAILABLE, [], 'synthetic QA outage')
                return real_reader(source, *args)
            with patch.object(triage, '_jsonl_raw', side_effect=unavailable_bonds):
                partial_state = triage.build_triage(today=board_day)
            assert partial_state['coverage']['state'] == 'partial' and partial_state['board_read']['score'] is None
            partial_url = fixture('synthetic-partial', partial_state)
            with patch.object(triage, '_macro_raw', side_effect=lambda *args: triage._read('macro', triage.READ_OK_ZERO, [])), patch.object(triage, '_jsonl_raw', side_effect=lambda source, *args: triage._read(source, triage.READ_OK_ZERO, [])):
                empty_state = triage.build_triage(today=board_day)
            assert empty_state['explorer']['total_signals'] == 0
            empty_url = fixture('synthetic-empty', empty_state)
            report['screenshots'] = []
            scenarios = [('laptop', base + '/alerts.html', 1280, 'real_snapshot'),
                         ('partial', partial_url, 390, 'synthetic_source_outage'),
                         ('empty', empty_url, 390, 'synthetic_empty_window'),
                         ('no-match', base + '/alerts.html#view=signals&s=ZZ_NO_SUCH_OBSERVATION', 1440, 'user_filter'),
                         ('rejected-evidence', base + '/trust-killed.html#id=' + original['explorer']['signals'][0]['alert_id'], 1440, 'synthetic_validation')]
            for name, url, width, origin in scenarios:
                for theme in ['dark', 'light']:
                    context.add_init_script('localStorage.setItem("theme", ' + json.dumps(theme) + ');localStorage.setItem("lang","en");')
                    page.set_viewport_size({'width': width, 'height': 900 if width > 600 else 844})
                    page.goto(url, wait_until='networkidle')
                    page.evaluate('(t)=>window.setTheme ? setTheme(t) : document.documentElement.dataset.theme=t', theme)
                    page.wait_for_timeout(1400)
                    filename = 'supplement-' + name + '-' + theme + '.png'
                    assert page.locator('html').get_attribute('data-theme') == theme
                    assert page.locator('html').get_attribute('data-lang') == 'en'
                    page.screenshot(path=str(out / filename), full_page=False)
                    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                    report['screenshots'].append({'file': filename, 'state_origin': origin, 'width': width,
                                                 'theme': theme, 'locale': 'en', 'horizontal_overflow': overflow})
                    assert not overflow, filename
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    report['test_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['passed'] = bool(report['cases']) and all(c['passed'] for c in report['cases'])
    (out / 'trust-browser-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
