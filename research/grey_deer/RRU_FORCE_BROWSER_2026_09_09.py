"""Browser-check the effective permission and earlier-method record, never production."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from RRU_FORCE_APPLICABILITY_TESTS_2026_09_09 import override, sample

OUT = Path(__file__).parent / 'rru_force_browser_20260909_v2'
OUT.mkdir(exist_ok=False)
a.apply_bundle(candidate.bundle)
css = a.committed('templates/theme.css') + '\n' + a.committed('templates/_risk_radar_card.css.j2')
host = a.committed('templates/dashboard.html.j2')
body = re.search(r'(?m)^  body \{[^}]*\}', host)
help_rules = re.findall(r'(?m)^  \.help(?: \.tip)? \{[^}]*\}', host)
assert body and len(help_rules) == 2
css += '\n' + body.group(0) + '\n' + '\n'.join(help_rules)
fixtures = {}
for case in ('complete', 'partial', 'unavailable'):
    sub = a.fixture(a.radar.CN_PROFILE)
    for values in sub.values():
        values.iloc[-1] = .99
    if case == 'partial': next(iter(sub.values())).iloc[-1] = a.np.nan
    if case == 'unavailable':
        for values in sub.values(): values.iloc[-1] = a.np.nan
    out = a.compute(a.radar.CN_PROFILE, sub)
    out.update(can_force=True, forward_log=dict(market='cn', can_force=True, n_graded=200))
    fixtures[case] = override(dict(risk_radar=out))
fixtures['legacy'] = override(dict(risk_radar=sample(False)))
records = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context()
    context.route('**/*', lambda route: route.abort())
    page = context.new_page()
    page.set_default_timeout(10000)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    for width in (1440, 768, 390):
        page.set_viewport_size(dict(width=width, height=900))
        for theme in ('dark', 'light'):
            for lang in ('en', 'zh'):
                for case, rd in fixtures.items():
                    errors.clear()
                    note = 'Synthetic permission fixture — not live market data' if lang == 'en' else '合成权限测试 — 非实时市场数据'
                    html = (f'<!doctype html><html lang="{lang}" data-theme="{theme}" data-lang="{lang}">'
                        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                        f'<style>{css}</style><style>main{{max-width:1000px;margin:24px auto;padding:12px}}'
                        '.fixture-note{color:var(--muted);margin-bottom:12px;font:14px system-ui}'
                        f'</style></head><body><main><p class="fixture-note">{note}</p>{a.render(rd)}</main></body></html>')
                    page.set_content(html, wait_until='domcontentloaded')
                    visible = page.locator('.rrx').inner_text()
                    modern = case != 'legacy'
                    term = 'moving the verdict' if lang == 'en' else '参与定调'
                    expected = 'Earlier construction record' if lang == 'en' else '旧构造往绩'
                    checks = dict(no_false_force=(term not in visible) if modern else (term in visible),
                        record_qualified=(expected in visible) if modern else (expected not in visible),
                        no_overflow=not page.evaluate('document.documentElement.scrollWidth>innerWidth'),
                        no_page_error=not errors,
                        other_language_hidden=not page.locator('.rrx .l-' + ('zh' if lang == 'en' else 'en')).first.is_visible(),
                        help_hidden=not page.locator('.help .tip').first.is_visible(),
                        effective_permission=(rd['can_force'] is (not modern)))
                    if modern:
                        summary = page.locator('.rrx-authority details summary').first
                        summary.focus(); page.keyboard.press('Enter')
                        checks['keyboard_disclosure'] = page.locator('.rrx-authority details').first.evaluate('e=>e.open')
                        checks['expanded_no_overflow'] = not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    shot = OUT / f'{case}-{theme}-{lang}-{width}.png'
                    page.screenshot(path=str(shot), full_page=True)
                    records.append(dict(case=case, theme=theme, lang=lang, width=width, checks=checks,
                        body_background=page.evaluate('getComputedStyle(document.body).backgroundColor'),
                        screenshot=shot.name, sha256=hashlib.sha256(shot.read_bytes()).hexdigest(),
                        html_sha256=hashlib.sha256(html.encode()).hexdigest()))
    context.close(); browser.close()
result = dict(kind='synthetic_browser_fixture_not_production', source_pin=a.PIN, cases=records,
    candidate_source_hashes={p:hashlib.sha256(candidate.edited[p].encode()).hexdigest() for p in candidate.bundle},
    all_checks_pass=all(all(r['checks'].values()) for r in records))
(OUT/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(dict(cases=len(records), all_checks_pass=result['all_checks_pass'], failures=[r for r in records if not all(r['checks'].values())])))
raise SystemExit(0 if result['all_checks_pass'] else 1)
