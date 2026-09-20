#!/usr/bin/env python3
"""Browser proof for an isolated real-builder Alert Center output."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import unicodedata
from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def plain(text: str) -> str:
    text = str(text or '').strip()
    while text and (unicodedata.category(text[0])[0] in 'PS' or text[0].isspace()):
        text = text[1:]
    return text.strip()


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
            assert page.locator('#ac-results .acx-attention-group').count() >= 2
            assert page.locator('#ac-results').get_by_text('Earlier priority', exact=True).count() == 1
            assert page.locator('#ac-results').get_by_text('Watch next', exact=True).count() == 1
            report['checks'].append('Now separates earlier high-authority events from fresh watch items')
            top_ids = [row['alert_id'] for row in payload['alerts'][:8]]
            top_briefs = [payload['explorer']['briefs'][id_] for id_ in top_ids]
            assert all(brief['status'] == 'supported' for brief in top_briefs)
            expected_actions = [brief['next_action_label'] + ' →' for brief in top_briefs]
            visible_actions = page.locator('#ac-results .acx-row-action').evaluate_all(
                '(rows) => rows.map(row => row.textContent.trim())')
            assert visible_actions == expected_actions
            report['checks'].append('Every first-glance row has a source-bound next action instead of generic evidence copy')
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
            supported_id = next(k for k, v in payload['explorer']['briefs'].items() if v.get('status') == 'supported')
            supported = payload['explorer']['briefs'][supported_id]
            page.goto(url + '#view=explore&id=' + supported_id, wait_until='domcontentloaded')
            assert page.locator('#ac-detail').evaluate('(d) => d.open')
            assert page.locator('#ac-detail').get_by_text('Takeaway', exact=True).count() == 1
            assert page.locator('#ac-detail .acx-next-action').inner_text() == supported['next_action']
            assert 'current source panel' in page.locator('#ac-detail').inner_text().lower()
            report['checks'].append('A real Macro alert renders a source-bound takeaway, limitation, next action and current-panel boundary')
            watch_id = top_ids[3]
            watch_brief = payload['explorer']['briefs'][watch_id]
            page.goto(url + '#view=explore&id=' + watch_id, wait_until='domcontentloaded')
            assert page.locator('#ac-detail').evaluate('(d) => d.open')
            assert page.locator('#ac-detail .acx-next-action').inner_text() == watch_brief['next_action']
            assert watch_brief['limitation'] in page.locator('#ac-detail').inner_text()
            report['checks'].append('A fresh watch-family alert exposes its own implication, limitation and decision-specific follow-up')
            risk_families = {
                'commodity.risk_regime', 'forex.risk_regime', 'macro.gex_flip_cross',
                'macro.hidden_fragility', 'macro.breadth_divergence',
            }
            risk_ids = {
                brief.get('family'): id_ for id_, brief in payload['explorer']['briefs'].items()
                if brief.get('family') in risk_families
            }
            assert set(risk_ids) == risk_families
            for family in sorted(risk_families):
                risk_id = risk_ids[family]
                risk_brief = payload['explorer']['briefs'][risk_id]
                page.goto(url + '#view=explore&id=' + risk_id, wait_until='domcontentloaded')
                assert page.locator('#ac-detail').evaluate('(d) => d.open')
                text = page.locator('#ac-detail').inner_text()
                assert risk_brief['limitation'] in text
                assert page.locator('#ac-detail .acx-next-action').inner_text() == risk_brief['next_action']
                assert risk_brief['evidence_label'] in text
            report['checks'].append('Five next-priority risk families render source-bound limits, actions and evidence destinations')
            liquidity_id = next(id_ for id_, brief in payload['explorer']['briefs'].items()
                                if brief.get('family') == 'macro.net_liquidity_roc_flip')
            liquidity_brief = payload['explorer']['briefs'][liquidity_id]
            page.goto(url + '#view=explore&id=' + liquidity_id, wait_until='domcontentloaded')
            liquidity_text = page.locator('#ac-detail').inner_text()
            assert liquidity_brief['limitation'] in liquidity_text
            assert page.locator('#ac-detail .acx-next-action').inner_text() == liquidity_brief['next_action']
            assert liquidity_brief['evidence_label'] in liquidity_text
            page.screenshot(path=str(out / 'desktop-net-liquidity.png'))
            report['screenshots'].append('desktop-net-liquidity.png')
            report['checks'].append('Net-liquidity flips expose current-state sizing work without becoming timing signals')
            theme_families = {
                'themes.reco_change', 'themes.theme_deteriorating',
                'themes.theme_topping', 'themes.theme_emerging',
                'themes.leadership_rotation',
            }
            theme_ids = {
                brief.get('family'): id_ for id_, brief in payload['explorer']['briefs'].items()
                if brief.get('family') in theme_families
            }
            assert set(theme_ids) == theme_families
            for family in sorted(theme_families):
                theme_id = theme_ids[family]
                theme_brief = payload['explorer']['briefs'][theme_id]
                page.goto(url + '#view=explore&id=' + theme_id, wait_until='domcontentloaded')
                assert page.locator('#ac-detail').evaluate('(d) => d.open')
                text = page.locator('#ac-detail').inner_text()
                assert theme_brief['limitation'] in text
                assert page.locator('#ac-detail .acx-next-action').inner_text() == theme_brief['next_action']
                assert theme_brief['evidence_label'] in text
            report['checks'].append('Five theme-change families render source-bound model limits, reassessment and current-page actions')
            rotation_families = {
                'rotation.rotation_fading', 'rotation.rotation_turn_down',
                'rotation.rotation_turn_up',
            }
            rotation_ids = {
                brief.get('family'): id_ for id_, brief in payload['explorer']['briefs'].items()
                if brief.get('family') in rotation_families
            }
            assert set(rotation_ids) == rotation_families
            for family in sorted(rotation_families):
                rotation_id = rotation_ids[family]
                rotation_brief = payload['explorer']['briefs'][rotation_id]
                page.goto(url + '#view=explore&id=' + rotation_id, wait_until='domcontentloaded')
                assert page.locator('#ac-detail').evaluate('(d) => d.open')
                text = page.locator('#ac-detail').inner_text()
                assert rotation_brief['limitation'] in text
                assert page.locator('#ac-detail .acx-next-action').inner_text() == rotation_brief['next_action']
                assert rotation_brief['evidence_label'] in text
            report['checks'].append('Three rotation rollover families render breadth-aware limits and current-panel reassessment')
            demand_id = next(id_ for id_, brief in payload['explorer']['briefs'].items()
                             if brief.get('family') == 'demand.demand_ahead')
            demand_brief = payload['explorer']['briefs'][demand_id]
            page.goto(url + '#view=explore&id=' + demand_id, wait_until='domcontentloaded')
            demand_text = page.locator('#ac-detail').inner_text()
            assert demand_brief['limitation'] in demand_text
            assert page.locator('#ac-detail .acx-next-action').inner_text() == demand_brief['next_action']
            assert demand_brief['evidence_label'] in demand_text
            page.screenshot(path=str(out / 'desktop-demand-ahead.png'))
            report['screenshots'].append('desktop-demand-ahead.png')
            report['checks'].append('Demand-ahead variants render an expectations-gap workflow without becoming buy signals')
            residual_id = next(id_ for id_, brief in payload['explorer']['briefs'].items()
                               if brief.get('family') == 'forex.residual_shock')
            residual_brief = payload['explorer']['briefs'][residual_id]
            page.goto(url + '#view=explore&id=' + residual_id, wait_until='domcontentloaded')
            residual_text = page.locator('#ac-detail').inner_text()
            assert residual_brief['limitation'] in residual_text
            assert page.locator('#ac-detail .acx-next-action').inner_text() == residual_brief['next_action']
            assert residual_brief['evidence_label'] in residual_text
            page.screenshot(path=str(out / 'desktop-forex-residual.png'))
            report['screenshots'].append('desktop-forex-residual.png')
            report['checks'].append('FX residual shocks expose attribution work without claiming a causal driver')
            situation = next(s for s in payload['explorer']['situations']
                             if len([id_ for id_ in s['member_ids'] if id_ in by_id]) >= 2)
            situation_ids = [id_ for id_ in situation['member_ids'] if id_ in by_id]
            primary_id, related_id = situation_ids[:2]
            page.goto(url + '#view=explore&id=' + primary_id, wait_until='domcontentloaded')
            related_rows = page.locator('#ac-detail .acx-related-observation')
            assert related_rows.count() >= 1
            assert 'not independent confirmation' in page.locator('#ac-detail .acx-related-note').inner_text().lower()
            page.screenshot(path=str(out / 'desktop-related-context.png'))
            report['screenshots'].append('desktop-related-context.png')
            related_row = page.locator(f'[data-related-alert-id="{related_id}"]')
            assert related_row.count() == 1
            related_row.click()
            assert related_id in page.url
            assert plain(by_id[related_id]['headline']) in page.locator('#ac-detail-title').inner_text()
            report['checks'].append('Situation context links related observations without claiming independent confirmation')
            page.click('#ac-close')
            assert not page.locator('#ac-detail').evaluate('(d) => d.open')
            page.click('[data-view="history"]')
            page.go_back(wait_until='domcontentloaded')
            assert page.locator('[data-view="explore"]').get_attribute('aria-current') == 'page'
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
