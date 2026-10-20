"""Missing pressure history is not a measured low-pressure reading."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine import contagion_links as owner
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=2)
def pressure_owner(state):
    def read(group, ticker):
        if state == 'bench_only' and (group, ticker) == owner._BENCH['us']:
            return pd.DataFrame({'close': [100. - i for i in range(25)]},
                                index=pd.bdate_range('2024-01-02', periods=25))
        return None

    with patch('engine.contagion_links.store.read', side_effect=read), \
            patch('engine.contagion_links._read_last_row', return_value=None):
        return owner.compute()


def pressure_fixture(state='bench_only'):
    return deepcopy(pressure_owner(state))


def mixed_pressure_fixture():
    """Actual absent-history artifact plus three explicit schema display controls.

    The controls are synthetic presentation inputs, not computed market findings.
    """
    result = pressure_fixture()
    for market, pct, level in [('jp', 0., 'low'), ('hk', .75, 'moderate'), ('cn', .9, 'high')]:
        result['pressure'][market].update(pct=pct, level=level)
    return result


def panel(payload):
    soup = BeautifulSoup(render_fixture(cgl=payload), 'html.parser')
    return soup.select_one('#intl-trade-supply-links').find_parent('div', class_='panel')


@pytest.mark.parametrize('state', ['absent', 'bench_only'])
def test_actual_owner_without_history_never_becomes_low(state):
    payload = pressure_fixture(state)
    before = deepcopy(payload)
    assert all(row['pct'] is None and row['level'] == 'low' for row in payload['pressure'].values())
    if state == 'bench_only':
        assert payload['pressure']['ca']['raw'] > 0
        assert payload['pressure']['ca']['top_exporters'][0]['market'] == 'us'
    el = panel(payload)
    rows = el.select('.ird-tx-row')
    assert len(rows) == len(payload['pressure']) == 11
    for row in rows:
        chip = row.select_one('.chip')
        assert chip.select_one('.l-en').text == 'Unavailable'
        assert chip.select_one('.l-zh').text == '不可用'
        assert not {'ok', 'warn', 'caut'}.intersection(chip.get('class', []))
        assert not row.select('.ird-tx-bar-wrap')
    assert 'A missing historical comparison is not a low reading.' in el.get_text()
    assert '缺少历史比较不代表压力低。' in el.get_text()
    if state == 'bench_only':
        assert '35%' in el.get_text()  # Supplied US -> Canada weight stays visible.
    assert payload == before


@pytest.mark.parametrize('pct,level,label', [(0., 'low', 'Low'), (.75, 'moderate', 'Building'), (.9, 'high', 'High')])
def test_supplied_zero_and_valid_assessments_remain_distinct(pct, level, label):
    payload = pressure_fixture()
    payload['pressure'] = {'jp': {**payload['pressure']['jp'], 'pct': pct, 'level': level}}
    row = panel(payload).select_one('.ird-tx-row')
    assert row.select_one('.chip .l-en').text == label
    assert row.select_one('.ird-tx-bar')['style'] == f'width:{round(pct * 100)}%'


def test_missing_percentile_field_is_not_assumed_zero():
    payload = pressure_fixture()
    row = payload['pressure']['jp']
    del row['pct']
    payload['pressure'] = {'jp': row}
    el = panel(payload)
    assert 'Unavailable' in el.get_text() and not el.select('.ird-tx-bar')


def test_unknown_level_is_not_recalculated_or_reported_low():
    payload = pressure_fixture()
    payload['pressure'] = {'jp': {**payload['pressure']['jp'], 'pct': .8, 'level': 'unknown'}}
    row = panel(payload).select_one('.ird-tx-row')
    assert row.select_one('.chip .l-en').text == 'Unavailable'
    assert row.select_one('.ird-tx-bar')['style'] == 'width:80%'


def test_unassessed_rows_sort_after_real_zero_without_mutating_owner():
    payload = mixed_pressure_fixture()
    before = deepcopy(payload)
    rows = panel(payload).select('.ird-tx-row')
    names = [r.select_one('span .l-en').text for r in rows]
    assert names[:3] == ['China', 'Hong Kong', 'Japan']
    assert len(rows) == 11
    assert payload == before


@pytest.mark.parametrize('state', ['absent', 'bench_only'])
def test_build_time_and_generic_gaps_do_not_become_current_tape(state):
    payload = pressure_fixture(state)
    if state == 'bench_only':
        assert payload['severity']['us']['as_of'] == '2024-02-05'
    el = panel(payload)
    heading = el.select_one('#intl-trade-supply-links')
    assert heading.select_one('.l-en').text == 'Supplied crash-pressure readings'
    assert heading.select_one('.l-zh').text == '所提供的冲击压力读数'
    footer = el.select_one('.ird-asof').get_text(' ', strip=True)
    assert f'Reported data gaps: {len(payload["gaps"])}' in footer
    assert f'已报告数据缺口：{len(payload["gaps"])}' in footer
    assert 'tonight' not in footer and '今晚' not in footer
    assert 'structural weights only' not in footer
