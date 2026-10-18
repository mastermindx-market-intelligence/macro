"""Offline browser acceptance for the actual CDI include, not a deployment claim.

Run: python -m scripts.verify_credit_dislocation_ui --output-dir .cdi-proof/browser
Requires an already installed Playwright browser. Downloads no browser or data.
Synthetic inputs come from the independently tested compiler fixture. Optional
--snapshot exercises an existing local artifact without mutating its source.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import runpy

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from engine.credit_dislocation import compile_snapshot
from engine.credit_dislocation_view import build_view

ROOT = Path(__file__).resolve().parents[1]


def document(view: dict, *, lang: str, theme: str) -> str:
    font400 = (ROOT / 'templates/fonts/Inter-400.woff2').as_uri()
    font600 = (ROOT / 'templates/fonts/Inter-600.woff2').as_uri()
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    body = env.from_string('{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}{% include "_credit_dislocation.html.j2" %}').render(cdi=view)
    style = f'''@font-face{{font-family:Inter;src:url('{font400}') format('woff2');font-weight:400}}
@font-face{{font-family:Inter;src:url('{font600}') format('woff2');font-weight:600}}'''
    style += '''
:root{--bg:#f7f8fa;--card:#fff;--text:#1c2430;--ink:#1c2430;--muted:#5d6b7e;--blue:#285fff;--red:#b23c3d;--amber:#b9791a;--info:#285fff;--ink-down:#b23c3d;--ink-warn:#7d5922}
html[data-theme="dark"]{--bg:#0f1115;--card:#181b21;--text:#d7dce3;--ink:#d7dce3;--muted:#8b93a1;--blue:#5b9bf0;--red:#e06464;--amber:#e0a030;--info:#5b9bf0;--ink-down:#e06464;--ink-warn:#e0b96b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"PingFang SC",sans-serif}.wrap{max-width:1200px;margin:auto;padding:20px 20px 50px}.fixture{font-size:11px;color:var(--muted);border-bottom:1px solid color-mix(in srgb,var(--muted) 30%,var(--card));padding-bottom:10px}
html:not([data-lang="zh"]) .l-zh{display:none}html[data-lang="zh"] .l-en{display:none}
'''
    return f'<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CDI component acceptance fixture</title><style>{style}</style></head><body><main class="wrap"><p class="fixture">UI acceptance fixture — not market quotes or a deployed product</p>{body}</main></body></html>'


def run(output: Path, snapshot: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    fixture_module = runpy.run_path(str(ROOT / 'tests/test_credit_dislocation.py'))
    payload = compile_snapshot(*fixture_module['fixture'](), as_of=date(2026, 10, 16))
    view = build_view(payload, as_of=date(2026, 10, 16))
    assert view['paired_count'] == 6
    receipts = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for width, height, lang, theme in [
                (1440, 1100, 'en', 'light'), (1440, 1100, 'en', 'dark'),
                (768, 1050, 'zh', 'light'), (390, 1000, 'zh', 'dark')]:
                filename = f'cdi-{width}-{lang}-{theme}'
                path = output / f'{filename}.html'
                path.write_text(document(view, lang=lang, theme=theme))
                page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='reduce')
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(path.resolve().as_uri(), wait_until='load')
                page.locator('[data-cdi-search]').wait_for()
                assert page.locator('[data-cdi-issuer]').count() == 6
                expected_option = 'All cohorts' if lang == 'en' else '\u5168\u90e8\u7ec4\u522b'
                assert page.locator('[data-cdi-grade] option:checked').inner_text() == expected_option
                assert page.locator('.cdi-bond-target table').count() == 0
                overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
                assert not overflow, f'page overflow at {width}'
                search = page.locator('[data-cdi-search]')
                search.fill('TEST0')
                assert page.locator('[data-cdi-count]').inner_text() == '1'
                assert page.locator('[data-cdi-issuer]:visible').count() == 1
                search.focus()
                page.keyboard.press('Tab')
                assert page.locator('[data-cdi-grade]').evaluate('(e)=>e===document.activeElement')
                summary = page.locator('[data-cdi-issuer]:visible > summary').first
                summary.focus()
                page.keyboard.press('Enter')
                page.locator('[data-cdi-issuer]:visible[open]').wait_for()
                inspector = page.locator('[data-cdi-issuer]:visible [data-cdi-bond-inspector]')
                inspector.locator('summary').click()
                inspector.locator('table').wait_for(state='visible')
                assert inspector.locator('tbody tr').count() == 1
                inspector.locator('summary').click()
                inspector.locator('summary').click()
                assert inspector.locator('table').count() == 1, 'lazy hydration duplicated a table'
                assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
                shot = output / f'{filename}.png'
                page.screenshot(path=str(shot), full_page=True)
                search.fill('does-not-exist')
                assert page.locator('[data-cdi-no-results]').is_visible()
                assert page.locator('[data-cdi-count]').inner_text() == '0'
                search.fill('')
                page.locator('[data-cdi-grade]').select_option('HY')
                assert page.locator('[data-cdi-count]').inner_text() == '0'
                page.locator('[data-cdi-grade]').select_option('all')
                page.locator('[data-cdi-coverage]').select_option('paired')
                assert page.locator('[data-cdi-count]').inner_text() == '6'
                if lang == 'zh':
                    assert page.locator('#cdi-title .l-zh').is_visible()
                    assert not page.locator('#cdi-title .l-en').is_visible()
                receipts.append({'viewport': [width, height], 'lang': lang, 'theme': theme,
                                 'search': True, 'filters': True, 'keyboard': True,
                                 'lazy_bonds_once': True, 'no_page_overflow': True,
                                 'screenshot': shot.name, 'screenshot_sha256': hashlib.sha256(shot.read_bytes()).hexdigest()})
                page.close()
            if snapshot:
                current = json.loads(snapshot.read_text())
                native_view = build_view(current, as_of=date.fromisoformat(current['as_of']))
                path = output / 'native-binding.html'
                path.write_text(document(native_view, lang='en', theme='light'))
                page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                page.goto(path.resolve().as_uri(), wait_until='load')
                assert page.locator('[data-cdi-issuer]').count() == len(native_view['issuers'])
                if native_view['status'] == 'stale':
                    assert 'Historical' in page.locator('#cdi-title').inner_text()
                    assert 'Historical only' in page.locator('.cdi-status').inner_text()
                receipts.append({'native_source_as_of': native_view['source_as_of'],
                                 'native_status': native_view['status'], 'native_issuer_count': len(native_view['issuers']),
                                 'scope': 'local source binding, not current market or deployment proof'})
                page.close()
        finally:
            browser.close()
    assert not errors, errors
    result = {'scope': 'actual CDI template/component acceptance', 'deployed': False,
              'browser': 'installed Playwright Chromium', 'console_errors': errors, 'cases': receipts}
    (output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('.cdi-proof/browser'))
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    result = run(args.output_dir, args.snapshot)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
