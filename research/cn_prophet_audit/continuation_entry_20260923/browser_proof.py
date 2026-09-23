"""Frozen repository-input component proof; not deployed or investment proof."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from engine.china_act_now import assemble_act_now

OUT = Path(__file__).resolve().parent / 'browser'
OUT.mkdir(exist_ok=True)
def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])
source_commit = 'd34993def9fa00e88c930f39a498b6ecad97455b'
source_path = 'site/chinabasketdata/baskets.json'
raw = git('show', f'{source_commit}:{source_path}')
source_blob = git('rev-parse', f'{source_commit}:{source_path}').decode().strip()
intel = json.loads(raw)['theme_intel']
# Explicit qualification clock for this frozen input, not a current/live read.
clock = datetime.fromisoformat("2026-09-23T05:00:00+00:00")
original = deepcopy(intel)
baseline = types.ModuleType('baseline_china_action_board')
baseline.__file__ = str(ROOT / 'engine/china_act_now.py')
exec(git('show', '2f469476aefd14e6d31c4608d874f0dc20fdb0ad:engine/china_act_now.py'), baseline.__dict__)
before = baseline.assemble_act_now([], intel, [])
after = assemble_act_now([], intel, [], observed_at=clock)
assert original == intel
assert before['lanes'] == after['lanes']
env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
host = BeautifulSoup(git('show', f'{source_commit}:site/china.html'), 'html.parser')
css_paths = [x['href'].split('?')[0] for x in host.select('link[rel=stylesheet]')]
assert all('://' not in x and '..' not in x for x in css_paths)
css = '\n'.join(git('show', f'{source_commit}:site/{x}').decode() for x in css_paths)
body_class = ' '.join(host.body.get('class', []))
js = (ROOT / 'templates/theme.js').read_text()
report = {'proof_kind': 'repository-input component; not production or historical-performance proof',
          'input_commit': source_commit, 'input_blob': source_blob,
          'input_path': source_path, 'input_sha256': hashlib.sha256(raw).hexdigest(),
          'host_css_paths': css_paths, 'host_body_class': body_class,
          'harness_note': 'Uses the recorded host-page CSS bundles and body classes; initial theme.css-only harness was visually invalid and replaced.',
          'input_as_of': intel.get('as_of'), 'observed_at_utc': clock.isoformat(),
          'clock_basis': 'injected qualification clock; not historical availability proof',
          'raw_lanes_unchanged': True, 'input_unchanged': True,
          'baseline_display': {k: [r['id'] for r in v] for k, v in before['display_lanes'].items()},
          'candidate_display': {k: [r['id'] for r in v] for k, v in after['display_lanes'].items()},
          'continuations': [r['id'] for r in after['display_lanes']['buy_now'] if r.get('entry_route') == 'continuation'],
          'captures': [], 'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
              for p in ('engine/china_act_now.py', 'templates/_china_act_now_board.html.j2', 'tests/test_china_act_now.py')}}
(OUT / 'board.json').write_text(json.dumps(after, ensure_ascii=False, indent=2))
# Negative states are controlled perturbations, NOT claims about the real market.
missing = deepcopy(intel)
for td in missing['themes']:
    td['observation']['aggregate_eligible'] = False
conflict = deepcopy(intel)
conflict['act_now']['conflicted'] = deepcopy(conflict['act_now'].get('add_on_pullback') or [])
demotion = deepcopy(intel)
positive = [t for t in demotion['themes'] if t.get('reco') in ('enter', 'accumulate')]
for td, (verb, zh) in zip(positive, [('hold', '持有'), ('trim', '减持'), ('avoid', '回避')]):
    td.update(reco=verb, reco_en=verb.upper(), reco_zh=zh)
cycles = [{'id': 'b-cn_semis', 'kind': 'basket', 'name': 'Semiconductors',
           'phase': 'Trough', 'osc_slope': 1.2, 'pos': 0.3, 'rs_63d': 0.05}]
scenarios = [('current', intel, clock, []), ('missing-members', missing, clock, []),
             ('source-conflict', conflict, clock, []), ('final-demotions', demotion, clock, []),
             ('settling', intel, datetime.fromisoformat('2026-09-22T08:00:00+00:00'), []),
             ('duplicate-evidence', intel, clock, cycles)]
report['negative_state_scope'] = 'Controlled missing-member, conflict, final-demotion, unsettled-clock and duplicate-cycle fixtures derived from the frozen theme input; not production observations. Real sector/cycle input remains unqualified.'

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    try:
        for scenario, source, at, cycle in scenarios:
            view = assemble_act_now([], source, cycle, observed_at=at)
            for theme in ('dark', 'light'):
                for lang in ('en', 'zh'):
                    env.globals.update(t=lambda en, zh, lng=lang: zh if lng == 'zh' else en,
                                       tr=lambda text: text, help=lambda *a, **kw: '')
                    component = env.get_template('_china_act_now_board.html.j2').render(act_now_v2=view)
                    for width in (1440, 390):
                        page = browser.new_page(viewport={'width': width, 'height': 960})
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.route('**/*', lambda route: route.abort())
                        html = (f'<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}">'
                                f'<head><meta charset="utf-8"><style>{css}</style></head><body class="{body_class}">'
                                f'<main>{component}</main><script>{js}</script></body></html>')
                        page.set_content(html, wait_until='domcontentloaded')
                        page.evaluate('(v) => { document.documentElement.dataset.theme=v[0]; document.documentElement.dataset.lang=v[1]; }', [theme,lang])
                        page.locator('#act-now').wait_for(state='visible')
                        result = page.evaluate('''() => ({
                            actualTheme: document.documentElement.dataset.theme,
                            actualLanguage: document.documentElement.dataset.lang,
                            overflow: document.documentElement.scrollWidth > innerWidth,
                            continuationRows: [...document.querySelectorAll('#anv2-buy .anv2-row[data-entry-route="continuation"]')].map(e => e.innerText),
                            buyRows: document.querySelectorAll('#anv2-buy .anv2-row').length,
                            continuationInWait: document.querySelectorAll('#anv2-pull .anv2-row[data-entry-route="continuation"]').length
                        })''')
                        name = f'candidate-{theme}-{lang}-{width}.png' if scenario == 'current' else f'candidate-{scenario}-{theme}-{lang}-{width}.png'
                        page.locator('#act-now').screenshot(path=str(OUT / name))
                        report['captures'].append({'scenario': scenario, 'file': name, 'theme': theme, 'language': lang,
                                                   'width': width, 'page_errors': errors, **result})
                        page.close()
    finally:
        browser.close()
(OUT / 'proof.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('input_commit', 'input_as_of', 'continuations', 'raw_lanes_unchanged')}, indent=2))
print('CAPTURES', len(report['captures']), 'OVERFLOWS', sum(c['overflow'] for c in report['captures']),
      'PAGE_ERRORS', sum(len(c['page_errors']) for c in report['captures']))
