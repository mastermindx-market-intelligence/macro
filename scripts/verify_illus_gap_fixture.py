#!/usr/bin/env python3
"""Check the real illustration fixture in isolated Chromium (synthetic data only).

Serve render_illus_gap_fixture.py output on loopback first. This exercises the
unchanged production reveal-on-scroll behavior through ?natural=1; the separate
canonical screenshot capture uses the settled specimen. It does not prove a
live producer, authentication, or any product route outside this fixture.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

from playwright.sync_api import sync_playwright


MEASURE = """() => {
  const box = el => { const r = el.getBoundingClientRect();
    return {top:r.top, bottom:r.bottom, width:r.width, height:r.height}; };
  return {
    viewport: innerWidth,
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    fontsReady: document.fonts.status === 'loaded' && document.fonts.check('14px Inter'),
    charts: [...document.querySelectorAll('.ilx')].map(el => ({
      case: el.closest('[data-case]').dataset.case,
      role: el.getAttribute('role'), aria: el.getAttribute('aria-label'),
      revealed: el.classList.contains('ilx-in'),
      box: box(el),
      plot: el.querySelector('.ilx-plot') ? box(el.querySelector('.ilx-plot')) : null,
      note: el.querySelector('.ilx-gap-note') ? box(el.querySelector('.ilx-gap-note')) : null,
      noteText: el.querySelector('.ilx-gap-note')?.innerText || '',
      tag: el.querySelector('.ilx-tag-historical') ? box(el.querySelector('.ilx-tag-historical')) : null,
      paths: [...el.querySelectorAll('.ilx-path')].map(p => ({
        length:p.getTotalLength(), dashOffset:getComputedStyle(p).strokeDashoffset,
        animation:getComputedStyle(p).animationName
      }))
    }))
  };
}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {
        'scope': 'Synthetic shared illustration component; no live producer or product-route acceptance',
        'generated_at': datetime.now(timezone.utc).isoformat(),
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
                        cell = {'width': width, 'theme': theme, 'locale': locale, 'motion': motion}
                        try:
                            response = page.goto(f'{args.base_url}/{theme}-{locale}.html?natural=1', wait_until='load')
                            assert response and response.ok, 'fixture load failed'
                            page.evaluate('document.fonts.ready')
                            initial = page.evaluate(MEASURE)
                            if motion == 'no-preference':
                                assert not initial['charts'][-1]['revealed'], 'natural mode unexpectedly pre-revealed below-fold chart'
                            else:
                                assert all(p['animation'] == 'none' for c in initial['charts'] for p in c['paths']), 'reduced motion is animated'
                                assert all(float(p['dashOffset'].removesuffix('px')) == 0 for c in initial['charts'] for p in c['paths']), 'reduced-motion ink is hidden'
                            for figure in page.locator('.ilx').all():
                                figure.scroll_into_view_if_needed()
                                page.wait_for_timeout(80)
                            page.wait_for_timeout(1500 if motion == 'no-preference' else 50)
                            observed = page.evaluate(MEASURE)
                            assert not observed['overflow'], 'horizontal overflow'
                            assert observed['fontsReady'], 'fonts did not load'
                            assert len(observed['charts']) == 10, 'unexpected chart count'
                            for c in observed['charts']:
                                assert c['role'] == 'img' and c['aria'], f"missing accessible name: {c['case']}"
                                assert c['revealed'], f"natural scroll did not reveal: {c['case']}"
                                assert c['box']['width'] > 0 and c['box']['height'] > 0, f"empty geometry: {c['case']}"
                                assert all(p['length'] > 0 and abs(float(p['dashOffset'].removesuffix('px'))) < .01 for p in c['paths']), f"hidden or invalid ink: {c['case']}"
                                if c['case'].startswith('compact-'):
                                    assert c['note']['top'] >= c['plot']['bottom'] + 3, f"status overlaps ink: {c['case']}"
                                    assert c['note']['bottom'] <= c['box']['bottom'] + .1, f"status overflows figure: {c['case']}"
                                    assert 'window 2026-10-26 to 2026-11-02' in c['aria'], 'compact accessible window missing'
                                if c['case'] == 'missing-tail':
                                    assert c['tag']['bottom'] + 7 <= c['plot']['top'], 'historical receipt overlaps ink'
                                    assert '2026-10-29' in c['aria'], 'historical date missing'
                                if c['case'] == 'compact-zero-240':
                                    assert 'last observed 0.0 % on 2026-11-02' in c['aria'], 'real zero lost'
                                if c['noteText']:
                                    assert ('缺失' in c['noteText']) == (locale == 'zh'), 'visible status locale mismatch'
                            assert not errors, f'browser errors: {errors}'
                            cell.update({'result': 'pass', 'observed': observed})
                        except Exception as exc:
                            cell.update({'result': 'fail', 'error': str(exc), 'console_errors': errors})
                            report['failures'].append({**cell})
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
