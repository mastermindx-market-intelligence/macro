"""Retain the existing native test-renderer outputs; no site build or browser launch."""
from pathlib import Path
import importlib.util
import sys
import json
import hashlib
import subprocess
from bs4 import BeautifulSoup

repo, out = map(Path, sys.argv[1:3])
sys.path.insert(0, str(repo))
out.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('tooltip_contract_tests', repo / 'tests/test_intl_tooltip_locale.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
network_guard = module.no_network.__wrapped__()
next(network_guard)
try:
    disabled_only = len(sys.argv) > 3 and sys.argv[3] == '--disabled-only'
    pages = ({'dislocations-disabled-fixed': module._load('intl_gs_dislocations_fixture').render_page()}
             if disabled_only else module.pages.__wrapped__())
finally:
    try:
        next(network_guard)
    except StopIteration:
        pass
selectors = {
    'scanner': ('scanner-coverage', '.intl-gs__view--scanner [data-abstain][data-tip-en]'),
    'coverage': ('scanner-coverage', '.intl-gs__view--coverage [data-col][data-tip-en]'),
    'dislocations': ('dislocations', '.intl-dislocations__notplotted [data-tip-en], .intl-gs__view--dislocations .intl-gs__num[data-tip-en]'),
    'transmission': ('transmission', '.intl-transmission__mech [data-tip-en]'),
}
if disabled_only:
    selectors = {'dislocations': ('dislocations-disabled-fixed', selectors['dislocations'][1])}
record = {'scope': 'Local existing native fixture template renders only. Synthetic/admitted fixture inputs; no acquisition, economic or historical availability claim; no full build/site emission/browser/publisher.',
          'source_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
          'browser': 'NEW_CHROMIUM_LAUNCH_HELD; no browser execution performed', 'pages': {}, 'views': {}}
for name, html in pages.items():
    (out / (name + '.html')).write_text(html)
    soup = BeautifulSoup(html, 'html.parser')
    bad = [n['title'] for n in soup.select('[title]') if module.CJK.search(n['title'])]
    assert not bad, (name, bad[:2])
    assert soup.select_one('script[src="theme.js"]') is not None
    record['pages'][name] = {'sha256': hashlib.sha256(html.encode()).hexdigest(), 'bytes': len(html.encode()), 'mixed_cjk_native_titles': len(bad), 'canonical_theme_consumer_included': True}
for view, (page, selector) in selectors.items():
    nodes = BeautifulSoup(pages[page], 'html.parser').select(selector)
    assert nodes and all(n.get('tabindex') == '0' and 'title' not in n.attrs and n.get('data-tip-zh') for n in nodes)
    pairs = [(n['data-tip-en'], n['data-tip-zh']) for n in nodes]
    record['views'][view] = {'converted_triggers': len(nodes), 'all_tab_reachable_in_markup': True, 'all_native_titles_removed': True,
                             'exact_locale_pairs_sha256': hashlib.sha256(json.dumps(pairs, ensure_ascii=False).encode()).hexdigest(), 'example': pairs[0]}
if disabled_only:
    soup = BeautifulSoup(pages['dislocations-disabled-fixed'], 'html.parser')
    wrappers = soup.select('.intl-dislocations__btnrow[data-tip-en][tabindex="0"]')
    buttons = soup.select('.intl-dislocations__btnrow button')
    assert wrappers and len(buttons) == 2 * len(wrappers)
    assert all(b.has_attr('disabled') and not b.has_attr('disabledtitle') and not b.has_attr('title') for b in buttons)
    assert all(b['data-tip-en'] == w['data-tip-en'] and b['data-tip-zh'] == w['data-tip-zh'] for w in wrappers for b in w.select('button'))
    record['disabled_actions'] = {'focusable_existing_wrappers': len(wrappers), 'native_disabled_buttons': len(buttons), 'malformed_disabledtitle': 0, 'same_exact_reason_on_wrapper_and_actions': True, 'touch_native_not_claimed': True}
report_name = 'disabled-render-report.json' if disabled_only else 'retained-render-report.json'
(out / report_name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False, indent=2))
