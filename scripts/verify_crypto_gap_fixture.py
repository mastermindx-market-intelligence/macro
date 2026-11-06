#!/usr/bin/env python3
"""Browser-check actual crypto producers on explicitly synthetic local inputs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

from playwright.sync_api import sync_playwright


MEASURE = """() => {
  const box = el => { const r = el.getBoundingClientRect();
    return {top:r.top, bottom:r.bottom, width:r.width, height:r.height}; };
  return {
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    fontsReady: document.fonts.status === 'loaded' && document.fonts.check('14px Inter'),
    charts: [...document.querySelectorAll('[data-chart-case] .ilx')].map(el => ({
      case: el.closest('[data-chart-case]').dataset.chartCase,
      role: el.getAttribute('role'), aria: el.getAttribute('aria-label'),
      gapCount: Number(el.dataset.gapCount || 0),
      compact: el.classList.contains('ilx-compact'),
      historical: el.classList.contains('ilx-historical'),
      revealed: el.classList.contains('ilx-in'), box:box(el),
      plot: box(el.querySelector('.ilx-plot') || el.querySelector('svg')),
      note: el.querySelector('.ilx-gap-note') ? box(el.querySelector('.ilx-gap-note')) : null,
      noteText: el.querySelector('.ilx-gap-note')?.innerText || '',
      captions: [...el.querySelectorAll('.ilx-tag, .ilx-d')].map(caption => ({
        classes: caption.className, display: getComputedStyle(caption).display
      })),
      dotX: Number(el.querySelector('.ilx-dot').getAttribute('cx')),
      paths: [...el.querySelectorAll('.ilx-path')].map(p => ({
        runs:(p.getAttribute('d').match(/M/g) || []).length,
        length:p.getTotalLength(), dashOffset:getComputedStyle(p).strokeDashoffset,
        animation:getComputedStyle(p).animationName
      }))
    }))
  };
}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--fixture-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture_bytes = args.fixture_manifest.read_bytes()
    fixture = json.loads(fixture_bytes)
    producer_bytes = (args.fixture_manifest.parent / 'producer-results.json').read_bytes()
    producer_hash = hashlib.sha256(producer_bytes).hexdigest()
    assert producer_hash == fixture['fixture_sha256']['producer-results.json'], 'producer receipt hash mismatch'
    producer_rows = {case['id']: case['row'] for case in json.loads(producer_bytes)}
    expected = {}
    for case in fixture['cases']:
        last_value = next(value for value in reversed(producer_rows[case['id']]['spark_values'])
                          if value is not None)
        # The actual crypto caller supplies value_fmt="{:,.3g}" and no unit.
        spec = {**case, 'last_value_label': format(last_value, ',.3g')}
        expected.update({key: spec for key in case['chart_case_ids']})
    report = {
        'scope': 'Actual crypto producer/component paths on synthetic inputs; no live data or full-route acceptance',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'fixture_manifest_sha256': hashlib.sha256(fixture_bytes).hexdigest(),
        'producer_results_sha256': producer_hash,
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'platform': platform.platform(), 'cells': [], 'failures': [],
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        report['browser'] = {'engine': 'chromium', 'version': browser.version}
        for width in (1440, 390, 320):
            for theme in ('dark', 'light'):
                for locale in ('en', 'zh'):
                    for motion in ('no-preference', 'reduce'):
                        context = browser.new_context(
                            viewport={'width': width, 'height': 900 if width == 1440 else 844},
                            locale='zh-CN' if locale == 'zh' else 'en-US',
                            color_scheme=theme, reduced_motion=motion,
                        )
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('console', lambda e: errors.append(e.text) if e.type == 'error' else None)
                        page.on('response', lambda r: errors.append(f'HTTP {r.status} {r.url}') if r.status >= 400 else None)
                        cell = {'width': width, 'theme': theme, 'locale': locale, 'motion': motion}
                        try:
                            response = page.goto(f'{args.base_url}/{theme}-{locale}.html?natural=1', wait_until='load')
                            assert response and response.ok, 'fixture load failed'
                            assert hashlib.sha256(response.body()).hexdigest() == fixture['page_sha256'][f'{theme}-{locale}.html'], 'served HTML hash mismatch'
                            page.evaluate('document.fonts.ready')
                            initial = page.evaluate(MEASURE)
                            if motion == 'reduce':
                                assert all(p['animation'] == 'none' for c in initial['charts'] for p in c['paths']), 'reduced motion is animated'
                            for figure in page.locator('[data-chart-case] .ilx').all():
                                figure.scroll_into_view_if_needed()
                                page.wait_for_timeout(80)
                            page.wait_for_timeout(1500 if motion == 'no-preference' else 50)
                            observed = page.evaluate(MEASURE)
                            assert not observed['overflow'], 'horizontal overflow'
                            assert observed['fontsReady'], 'fonts did not load'
                            assert {c['case'] for c in observed['charts']} == set(expected), 'unexpected chart cases'
                            for c in observed['charts']:
                                spec = expected[c['case']]
                                assert c['role'] == 'img' and c['aria'], f"missing accessible name: {c['case']}"
                                assert c['revealed'], f"scroll did not reveal: {c['case']}"
                                assert abs(c['box']['width'] - int(c['case'].rsplit('-', 1)[1])) < .1, 'chart width changed'
                                assert c['compact'] and abs(c['box']['height'] - 42) < .1, 'compact 42px figure contract changed'
                                assert len(c['captions']) == 3 and all(caption['display'] == 'none' for caption in c['captions']), 'compact captions are visible or missing'
                                assert f"window {spec['first_date']} to {spec['last_date']}" in c['aria'], 'accessible supplied window lost'
                                assert f"last observed {spec['last_value_label']} on {spec['last_observed_date']}" in c['aria'], 'accessible last value or date lost'
                                assert c['gapCount'] == spec['missing'] and c['historical'] == spec['tail'], 'producer semantics changed'
                                assert sum(p['runs'] for p in c['paths']) == spec['runs'], 'gap connectivity changed'
                                assert all(p['length'] > 0 and abs(float(p['dashOffset'].removesuffix('px'))) < .01 for p in c['paths']), 'hidden or invalid ink'
                                if spec['missing']:
                                    assert c['note'] is not None, 'missing-data status absent'
                                    assert c['note']['top'] >= c['plot']['bottom'] + 3, 'status overlaps ink'
                                    assert c['note']['bottom'] <= c['box']['bottom'] + .1, 'status overflows figure'
                                    assert ('缺失' in c['noteText']) == (locale == 'zh'), 'visible status locale mismatch'
                                else:
                                    assert c['note'] is None and not c['noteText'], 'complete chart has a gap-status row'
                                    assert abs(c['plot']['height'] - 42) < .1, 'complete compact plot lost height'
                                    assert abs(c['plot']['top'] - c['box']['top']) < .1 and abs(c['plot']['bottom'] - c['box']['bottom']) < .1, 'complete plot does not fill its figure'
                                if spec['tail']:
                                    assert c['dotX'] < 560 and spec['last_observed_date'] in c['aria'], 'historical tail drawn current'
                                else:
                                    assert c['dotX'] == 560, 'complete latest observation moved'
                            assert not errors, f'browser errors: {errors}'
                            cell.update(result='pass', observed=observed)
                        except Exception as exc:
                            cell.update(result='fail', error=str(exc), console_errors=errors)
                            report['failures'].append(dict(cell))
                        finally:
                            context.close()
                        report['cells'].append(cell)
        browser.close()
    report['totals'] = {'attempted': len(report['cells']), 'passed': sum(c['result'] == 'pass' for c in report['cells'])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('browser', 'totals', 'failures')}, ensure_ascii=False))
    return bool(report['failures'])


if __name__ == '__main__':
    raise SystemExit(main())
