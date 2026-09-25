"""Stock-specific entry reasons must not become another entry-policy owner."""
from copy import deepcopy
import ast
import itertools
from pathlib import Path

import pytest
from engine import basket_score as bs

ROOT = Path(__file__).resolve().parents[1]


def member(symbol='AMD', score=68, status='buy_now', cycle=False, tier='T1', **extra):
    row = {'symbol': symbol, 'name': symbol,
           'conviction': {'score': score, 'cycle_blocked': cycle,
                          'verdict': 'Constructive', 'entry_pct': .7,
                          'signal': {'tier': tier},
                          'entry': {'status': status, 'headline': 'Buy now',
                                    'headline_zh': '现在买入', 'act_level': 3}}}
    row['conviction'].update(extra)
    return row


def theme(**extra):
    return {'label': 'dominant', 'reco': 'accumulate',
            'textures': {'clean_entry': {'flag': False}, 'bull_age': {'in_bull': True}}, **extra}


def test_theme_texture_is_not_a_second_stock_entry_veto():
    out = bs.act_now_stocks([member()], theme())
    assert out['buys'][0]['symbol'] == 'AMD'
    assert out['entry_checks'][0]['eligible'] is True
    assert out['entry_summary']['qualified'] == 1


@pytest.mark.parametrize('score,status,cycle,code', [
    (None, 'buy_now', False, 'assessment_unavailable'),
    (49, 'buy_now', False, 'conviction_below_threshold'),
    (68, 'buy_now', True, 'cycle_blocked'),
    (68, 'await_confluence', False, 'entry_waiting'),
    (68, 'extended', False, 'entry_waiting'),
    (68, 'unrecognized_future_status', False, 'entry_waiting'),
])
def test_every_rejected_member_exposes_the_deciding_condition(score, status, cycle, code):
    out = bs.act_now_stocks([member(score=score, status=status, cycle=cycle)], theme())
    assert out['buys'] == []
    check = out['entry_checks'][0]
    assert (check['code'], check['eligible']) == (code, False)
    assert check['reason_en'] and check['reason_zh']
    assert 'Buy now' not in check['reason_en']
    assert '现在买入' not in check['reason_zh']


def test_fast_turn_does_not_advertise_buy_as_the_reason_it_is_not_a_buy():
    out = bs.act_now_stocks([member(score=49)], theme())
    assert len(out['early_turn_watch']) == 1
    watch = out['early_turn_watch'][0]
    assert watch['blocker_en'] == out['entry_checks'][0]['reason_en']
    assert 'Buy now' not in watch['blocker_en']


def test_global_theme_block_remains_authoritative():
    out = bs.act_now_stocks([member()], theme(label='fading', reco='trim'))
    assert out['status'] == 'theme_out_of_favour' and out['buys'] == []
    assert out['entry_checks'][0]['code'] == 'theme_blocked'
    assert out['entry_summary']['qualified'] == 0


def test_legacy_admission_is_disclosed_without_duplicate_nonactionable_watch():
    row = member(status=None, verdict='Leader', entry_pct=.7)
    out = bs.act_now_stocks([row], theme())
    assert len(out['buys']) == 1
    assert out['entry_checks'][0]['code'] == 'legacy_qualified'
    assert out['early_turn_watch'] == []


def test_summary_and_complete_diagnostics_do_not_hide_the_thirteenth_member():
    rows = [member(symbol=f'S{i}', tier=None) for i in range(15)]
    out = bs.act_now_stocks(rows, theme())
    assert len(out['buys']) == 12  # original presentation cap is unchanged
    assert len(out['entry_checks']) == 15
    assert out['entry_summary'] == {'members': 15, 'qualified': 15, 'displayed': 12,
                                    'waiting': 0, 'unavailable': 0}


def test_missing_assessments_are_not_described_as_price_extension():
    rows = [member(score=None), member(symbol='ARM', score=None)]
    out = bs.act_now_stocks(rows, theme())
    assert out['entry_summary']['unavailable'] == 2
    assert out['entry_summary']['qualified'] == 0
    assert 'extended' not in out['note_en'].lower()
    assert 'pullback' not in out['note_en'].lower()


def test_diagnostics_do_not_mutate_input_or_manufacture_price_targets():
    rows, th = [member(status='await_confluence'), member(symbol='ARM', cycle=True)], theme()
    before = deepcopy((rows, th))
    out = bs.act_now_stocks(rows, th)
    assert (rows, th) == before
    for check in out['entry_checks']:
        assert 'zone_low' not in check and 'target' not in check
        assert len(check['reason_en'].split()) <= 14


def test_entry_admission_matches_the_frozen_native_function():
    fixture = ROOT / 'tests/fixtures/theme_recommendation_reasons/legacy_act_now_stocks.py'
    namespace = {}
    exec(compile(fixture.read_text(), str(fixture), 'exec'), namespace)
    old = namespace['act_now_stocks']
    for score, status, cycle, verdict, ep, label, reco in itertools.product(
        [None, 0, 49, 50, 80], ['buy_now', 'partial', 'await_confluence', None],
        [False, True], ['Leader', 'Neutral'], [None, .44, .45],
        ['dominant', 'neutral', 'fading'], ['accumulate', 'hold', 'avoid']):
        rows = [member(score=score, status=status, cycle=cycle, verdict=verdict, entry_pct=ep)]
        th = theme(label=label, reco=reco)
        before, after = old(rows, th), bs.act_now_stocks(rows, th)
        for key in ['status', 'buys', 'uncovered']:
            assert after[key] == before[key], (score, status, cycle, verdict, ep, label, reco, key)


def test_actual_detail_consumer_discloses_stock_specific_checks():
    src = (ROOT / 'templates/basket_detail.html.j2').read_text()
    assert 'function stockEntryChecksHtml(' in src
    assert 'stockEntryChecksHtml(an, stk)' in src
    assert 'Review stock entries' in src
    assert '查看个股入场条件' in src
    assert 'most are extended or mid-trend' not in src


def render_checks(payload):
    import json
    import shutil
    import subprocess
    node = shutil.which('node')
    assert node, 'The repository JavaScript consumer checks require Node.'
    src = (ROOT / 'templates/basket_detail.html.j2').read_text()
    function = src[src.index('function stockEntryChecksHtml('):src.index('// Native details is the state owner.')]
    prelude = "const L=(en,zh)=>`<span class=\"l-en\">${en}</span><span class=\"l-zh\">${zh}</span>`; const esc=s=>String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));\n"
    call = '\nconsole.log(stockEntryChecksHtml(' + json.dumps(payload) + ',s=>`<a href="../stock.html#${encodeURIComponent(s)}">${esc(s)}</a>`));'
    return subprocess.check_output([node, '-e', prelude + function + call], text=True)


def test_javascript_consumer_uses_native_reasons_and_stock_links():
    payload = bs.act_now_stocks([member(status='await_confluence')], theme())
    html = render_checks(payload)
    assert 'Waiting for signal confirmation.' in html
    assert '../stock.html#AMD' in html
    assert '1 waiting' in html
    assert '0 qualified' in html


@pytest.mark.parametrize('mutation', ['count', 'qualified', 'waiting', 'unavailable', 'translation'])
def test_consumer_rejects_inconsistent_diagnostic_payload(mutation):
    payload = bs.act_now_stocks([member()], theme())
    if mutation == 'count':
        payload['entry_summary']['members'] = 99
    elif mutation == 'translation':
        payload['entry_checks'][0]['reason_zh'] = None
    else:
        payload['entry_summary'][mutation] = 99
    html = render_checks(payload)
    assert 'Stock entry reasons are unavailable.' in html
    assert '<table' not in html


def test_consumer_escapes_reason_and_symbol_markup():
    payload = bs.act_now_stocks([member(symbol='<unsafe>')], theme())
    payload['entry_checks'][0]['reason_en'] = '<script>alert(1)</script>'
    html = render_checks(payload)
    assert '<script>' not in html and '<unsafe>' not in html
    assert '&lt;script&gt;' in html
    assert '%3Cunsafe%3E' in html


def test_old_payload_does_not_invent_a_complete_stock_evaluation():
    assert render_checks({'status': 'no_clean_entries', 'buys': []}).strip() == ''


def test_existing_theme_entry_and_risk_texture_functions_are_unchanged():
    import hashlib
    import json
    fixture = ROOT / 'tests/fixtures/theme_recommendation_reasons/legacy_basket_function_hashes.json'
    old = json.loads(fixture.read_text())['functions']
    current = (ROOT / 'engine/basket_score.py').read_text()
    new = {n.name: hashlib.sha256(ast.get_source_segment(current, n).encode()).hexdigest()
           for n in ast.parse(current).body if isinstance(n, ast.FunctionDef)}
    for name, digest in old.items():
        assert new[name] == digest, name


def test_missing_stock_assessment_is_disclosed_even_when_theme_is_blocked():
    out = bs.act_now_stocks([member(score=None), member(symbol='ARM')],
                            theme(label='fading', reco='trim'))
    assert out['status'] == 'theme_out_of_favour' and out['buys'] == []
    assert out['entry_summary']['unavailable'] == 1
    assert out['entry_checks'][0]['code'] == 'assessment_unavailable'
    assert out['entry_checks'][1]['code'] == 'theme_blocked'


@pytest.mark.parametrize('damage', ['missing_summary', 'bad_count', 'bad_reason'])
def test_rejected_stock_detail_has_a_focusable_real_anchor(damage):
    out = bs.act_now_stocks([member(status='await_confluence')], theme())
    if damage == 'missing_summary':
        out.pop('entry_summary')
    elif damage == 'bad_count':
        out['entry_summary']['qualified'] = 9
    else:
        out['entry_checks'][0]['reason_en'] = None
    html = render_checks(out)
    assert 'Stock entry reasons are unavailable.' in html
    assert html.count('id="stock-entry-checks"') == 1
    assert 'tabindex="-1"' in html
    assert 'role="status"' in html
    assert '<table' not in html
