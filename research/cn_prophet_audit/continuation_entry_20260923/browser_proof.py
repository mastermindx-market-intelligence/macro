"""Frozen repository-input component proof; not deployed or investment proof."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json
import subprocess
import sys
import types
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from engine.china_act_now import assemble_act_now, load_member_names, load_cycle_rows
from engine.i18n import tr as source_tr

MIXED = '--mixed' in sys.argv
OUT = Path(__file__).resolve().parent / ('mixed-browser' if MIXED else 'browser')
OUT.mkdir(exist_ok=True)
def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])
source_commit = ('88a3f1cfd18f391d2802e9086dc00f6fe5545607' if MIXED else
                 'd34993def9fa00e88c930f39a498b6ecad97455b')
source_path = 'site/chinabasketdata/baskets.json'
raw = git('show', f'{source_commit}:{source_path}')
source_blob = git('rev-parse', f'{source_commit}:{source_path}').decode().strip()
intel = json.loads(raw)['theme_intel']
sectors, snapshot_cycles, extra_inputs = [], [], {}
if MIXED:
    sectors_path = 'site/chinabasketdata/act_now_cn.json'
    sectors_raw = git('show', f'{source_commit}:{sectors_path}')
    sectors = list(json.loads(sectors_raw)['sectors_by_ticker'].values())
    cycle_path = 'data/china_sector_cycles/forward_log.parquet'
    cycle_raw = git('show', f'{source_commit}:{cycle_path}')
    with tempfile.TemporaryDirectory(prefix='cn-action-proof-cycles-') as temp_dir:
        cycle_file = Path(temp_dir) / 'forward_log.parquet'
        cycle_file.write_bytes(cycle_raw)
        snapshot_cycles = load_cycle_rows(str(cycle_file))
    assert sectors and snapshot_cycles
    extra_inputs = {path: hashlib.sha256(data).hexdigest() for path, data in
                    ((sectors_path, sectors_raw), (cycle_path, cycle_raw))}

# Use the real member-name loader on the SAME already-loaded frozen basket bytes.
# This is temporary proof input, never a write to a product artifact.
with tempfile.TemporaryDirectory(prefix='cn-action-proof-names-') as temp_dir:
    name_source = Path(temp_dir) / 'baskets.json'
    name_source.write_bytes(raw)
    member_names = load_member_names(str(name_source))
assert member_names, 'frozen basket member names must be present'
# Explicit qualification clock for this frozen input, not a current/live read.
clock = datetime.fromisoformat("2026-09-23T05:00:00+00:00")
original = deepcopy(intel)
baseline = types.ModuleType('baseline_china_action_board')
baseline.__file__ = str(ROOT / 'engine/china_act_now.py')
exec(git('show', '2f469476aefd14e6d31c4608d874f0dc20fdb0ad:engine/china_act_now.py'), baseline.__dict__)
before = baseline.assemble_act_now(sectors, intel, snapshot_cycles, member_names=member_names)
after = assemble_act_now(sectors, intel, snapshot_cycles, observed_at=clock, member_names=member_names)
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
          'mixed_input': MIXED, 'sector_count': len(sectors), 'cycle_count': len(snapshot_cycles),
          'extra_input_sha256': extra_inputs,
          'input_path': source_path, 'input_sha256': hashlib.sha256(raw).hexdigest(),
          'host_css_paths': css_paths, 'host_body_class': body_class,
          'harness_note': 'Uses the recorded host-page CSS bundles and body classes; initial theme.css-only harness was visually invalid and replaced.',
          'input_as_of': intel.get('as_of'), 'observed_at_utc': clock.isoformat(),
          'clock_basis': 'injected qualification clock; not historical availability proof',
          'translation': 'real engine.i18n.tr; existing untranslated-source fallbacks remain visible',
          'member_names': {'loader': 'engine.china_act_now.load_member_names', 'count': len(member_names), 'source': source_path},
          'raw_lanes_unchanged': True, 'input_unchanged': True,
          'baseline_display': {k: [r['id'] for r in v] for k, v in before['display_lanes'].items()},
          'candidate_display': {k: [r['id'] for r in v] for k, v in after['display_lanes'].items()},
          'continuations': [r['id'] for r in after['display_lanes']['buy_now'] if r.get('entry_route') == 'continuation'],
          'captures': [], 'hover_captures': [], 'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
              for p in ('engine/china_act_now.py', 'templates/_china_act_now_board.html.j2', 'tests/test_china_act_now.py')}}
(OUT / 'board.json').write_text(json.dumps(after, ensure_ascii=False, indent=2))
# Negative states are controlled perturbations, NOT claims about the real market.
missing = deepcopy(intel)
for td in missing['themes']:
    td['observation']['aggregate_eligible'] = False
partial = deepcopy(intel)
partial_tid = next(row['id'] for row in after['display_lanes']['buy_now'] if row.get('kind') == 'THEME')
for td in partial['themes']:
    if td['id'] == partial_tid:
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
             ('partial-members', partial, clock, []),
             ('source-conflict', conflict, clock, []), ('final-demotions', demotion, clock, []),
             ('settling', intel, datetime.fromisoformat('2026-09-22T08:00:00+00:00'), []),
             ('duplicate-evidence', intel, clock, cycles)]
scenarios = [(name, source, at, snapshot_cycles + cycle) for name, source, at, cycle in scenarios]
report['negative_state_scope'] = ('Controlled negative theme states on immutable repository inputs, not live observations. '
    + ('The actual sector and latest cycle rows are included unchanged; their freshness policy is not modified.' if MIXED
       else 'Sector and native-cycle inputs are omitted in this mode.'))

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    try:
        for scenario, source, at, cycle in scenarios:
            view = assemble_act_now(sectors, source, cycle, observed_at=at, member_names=member_names)
            for rows in view["display_lanes"].values():
                for row in rows:
                    if row.get("theme_decision", {}).get("status") == "UNAVAILABLE":
                        assert not row.get("dual_read") and not row.get("action_disagreement")
            for theme in ('dark', 'light'):
                for lang in ('en', 'zh'):
                    env.globals.update(t=lambda en, zh, lng=lang: zh if lng == 'zh' else en,
                                       tr=source_tr, help=lambda *a, **kw: '')
                    component = env.get_template('_china_act_now_board.html.j2').render(act_now_v2=view, sectors_by_ticker={r['ticker']: r for r in sectors})
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
                        note = view.get('theme_data_note')
                        note_el = page.locator('[data-theme-data-status]')
                        assert note_el.count() == (1 if note else 0)
                        note_text = note_el.inner_text() if note else None
                        assert note_text == (note['zh' if lang == 'zh' else 'en'] if note else None)
                        result['themeDataNote'] = note_text
                        name = f'candidate-{theme}-{lang}-{width}.png' if scenario == 'current' else f'candidate-{scenario}-{theme}-{lang}-{width}.png'
                        page.locator('#act-now').screenshot(path=str(OUT / name))
                        report['captures'].append({'scenario': scenario, 'file': name, 'theme': theme, 'language': lang,
                                                   'width': width, 'page_errors': errors, **result})
                        if scenario in ('current', 'missing-members', 'partial-members', 'settling'):
                            lane = '#anv2-buy' if scenario == 'current' else '#anv2-pull'
                            selector = (lane + f' .anv2-row a[href="basket_china/{partial_tid}.html"]'
                                        if scenario == 'partial-members' else lane + ' .anv2-row a')
                            page.locator(selector).first.focus()
                            pop = page.locator('.row-pop[role=tooltip]')
                            pop.wait_for(state='visible')
                            text = pop.inner_text()
                            expected = ('领先趋势延续' if lang == 'zh' else 'Leadership continuing') if scenario == 'current' else (
                                ('交易日数据尚待确认' if lang == 'zh' else 'Session not yet settled') if scenario == 'settling' else
                                ('当前输入暂缺' if lang == 'zh' else 'Current inputs unavailable'))
                            assert expected in text, (scenario, lang, text)
                            if scenario != 'current':
                                assert ('数据状态' if lang == 'zh' else 'Data status').casefold() in text.casefold(), (scenario, lang, text)
                                assert pop.locator('.row-pop-score').count() == 0
                            box = pop.bounding_box()
                            assert box and box['x'] >= 0 and box['x'] + box['width'] <= width
                            popfile = f'hover-{scenario}-{theme}-{lang}-{width}.png'
                            pop.screenshot(path=str(OUT / popfile))
                            report['hover_captures'].append({'scenario': scenario, 'theme': theme,
                                'language': lang, 'width': width, 'file': popfile,
                                'interaction': 'native keyboard-focus handler at responsive viewport',
                                'visible_text': text, 'bounds': box, 'page_errors': list(errors)})
                        page.close()
    finally:
        browser.close()
(OUT / 'proof.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('input_commit', 'input_as_of', 'continuations', 'raw_lanes_unchanged')}, indent=2))
print('CAPTURES', len(report['captures']), 'OVERFLOWS', sum(c['overflow'] for c in report['captures']),
      'PAGE_ERRORS', sum(len(c['page_errors']) for c in report['captures']))
