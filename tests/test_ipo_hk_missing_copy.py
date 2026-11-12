"""Exact native HK calculation and display-function regressions; no market I/O."""
import ast
import copy
import itertools
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from engine import ipo_hk

import pandas as pd
import pytest
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('southbound', 'hibor', 'peg', 'risk')
LABELS = {
    'southbound': ('Southbound flow unavailable', '南向资金流数据缺失'),
    'hibor': ('Subscription-funding cost unavailable', '认购融资成本数据缺失'),
    'peg': ('HKD peg pressure unavailable', '港元联系汇率压力数据缺失'),
    'risk': ('HK risk appetite unavailable', '香港风险偏好数据缺失'),
}


def _view(raw):
    vector = ast.parse((ROOT / 'scripts/build_vector.py').read_text())
    palette = next(n for n in vector.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'C' for t in n.targets))
    ns = {'C': ast.literal_eval(palette.value),
          'ipo_hk': SimpleNamespace(hk_backdrop=lambda: raw)}
    tree = ast.parse((ROOT / 'scripts/build_ipo.py').read_text())
    constants = {'STATE_ZH', 'STATE_COLOR', 'STANCE'}
    chosen = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and (t.id.startswith('HK_') or t.id in constants)
            for t in node.targets):
            chosen.append(node)
        elif isinstance(node, ast.FunctionDef) and (node.name.startswith('_hk_') or node.name == '_window_stance'):
            chosen.append(node)
    exec(compile(ast.Module(body=chosen, type_ignores=[]), 'build_ipo.py', 'exec'), ns)
    return ns['_hk_vm']()


def _raw(present):
    def read(group, name):
        key = 'southbound' if group == 'china_connect' else 'hibor'
        dates = pd.bdate_range('2026-10-15', periods=20)
        column = 'net' if key == 'southbound' else 'hibor_1m'
        return pd.DataFrame({column: [1.0] * 20}, index=dates) if present[KEYS.index(key)] else None
    regime = {'date': '2026-11-11'}
    if present[2]:
        regime['peg_state'] = 'strong'
    if present[3]:
        regime['risk_state'] = 'risk-on'
    with patch.object(ipo_hk.store, 'read', side_effect=read), patch.object(
            ipo_hk, '_hk_regime', return_value=regime):
        return ipo_hk.hk_backdrop()


def _render(view):
    source = (ROOT / 'templates/ipo.html.j2').read_text()
    start = source.index('    <!-- hong kong -->')
    end = source.index('    <!-- methodology', start)
    macro = source[source.index('{% macro t('):]
    macro = macro[:macro.index('{%- endmacro %}') + len('{%- endmacro %}')]
    return Environment(autoescape=True).from_string(macro + source[start:end]).render(
        hk=view, STATEW={})


@pytest.mark.parametrize('present', list(itertools.product([False, True], repeat=4)))
def test_missing_note_names_only_missing_native_legs(present):
    raw = _raw(present)
    original = copy.deepcopy(raw)
    view = _view(raw)
    assert raw == original
    html = _render(view)
    if not any(present):
        assert view == {'available': False}
        assert 'note warn' not in html
        return
    expected = [key for key, exists in zip(KEYS, present) if not exists]
    assert view['missing_legs'] == expected
    assert view['n_legs'] == sum(present)
    assert view['as_of'] == raw['as_of']
    assert view['low_confidence'] == raw['low_confidence']
    for key, labels in LABELS.items():
        for language, label in zip(('en', 'zh'), labels):
            assert (label in view.get('missing_note_' + language, '')) == (key in expected)
            assert (label in html) == (key in expected)
    assert ('note warn' in html) == bool(expected)
    if present[1]:
        assert '1.00%' in html
    if expected == ['hibor']:
        assert view['missing_note_en'] == 'Subscription-funding cost unavailable — this read excludes it.'
        assert view['missing_note_zh'] == '认购融资成本数据缺失 —— 本读数未纳入。'


def test_unknown_future_missing_key_is_generic_not_funding():
    raw = _raw([True] * 4)
    raw['missing_legs'] = ['future_input']
    view = _view(raw)
    assert 'funding' not in view['missing_note_en']
    assert 'future_input' not in view['missing_note_en']
    assert 'A backdrop input is unavailable' in view['missing_note_en']
