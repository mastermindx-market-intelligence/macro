"""Fragility presentation retains actual owner coverage and year scope."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.intl_risk import vulnerability_table
from scripts.build_intl import _enrich_vulnerability
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=8)
def fragility_owner(state):
    def read(group, name):
        if group != 'imf_weo' or not name.endswith('_USA') or state == 'absent':
            return None
        if state == 'partial' and name.startswith('GGXCNL'):
            return pd.DataFrame({'fiscal_balance_pct_gdp': [0.]}, index=pd.to_datetime(['2022-01-01']))
        if state == 'flagged':
            if name.startswith('GGXWDG'):
                return pd.DataFrame({'gross_debt_pct_gdp': [80.,85.,90.,95.]}, index=pd.date_range('2021-01-01', periods=4, freq='YS'))
            if name.startswith('GGXCNL'):
                return pd.DataFrame({'fiscal_balance_pct_gdp': [-6.]}, index=pd.to_datetime(['2022-01-01']))
            if name.startswith('BCA'):
                return pd.DataFrame({'current_account_pct_gdp': [-4.]}, index=pd.to_datetime(['2023-01-01']))
        return None
    with patch('engine.intl_risk.store.read', side_effect=read):
        return _enrich_vulnerability(vulnerability_table())


def fragility_fixture(state):
    return {'vulnerability': deepcopy(fragility_owner(state))}


def panel(payload):
    soup = BeautifulSoup(render_fixture(risk_desk=payload), 'html.parser')
    return soup.select_one('#intl-structural-fragility').find_parent('div', class_='panel')


@pytest.mark.parametrize('state', ['absent','partial','flagged'])
def test_actual_owner_coverage_never_becomes_clear_or_a_delivery_promise(state):
    payload = fragility_fixture(state); before = deepcopy(payload)
    rows = payload['vulnerability']['countries']
    if state == 'partial':
        assert rows[0]['fiscal_balance'] == 0 and rows[0]['debt_gdp'] is None
        assert rows[0]['fragile'] is False
    if state == 'flagged':
        assert rows[0]['fragile'] is True and len(rows[0]['flags']) == 3
    el = panel(payload); text = el.get_text(' ', strip=True)
    assert 'map is clear' not in text and 'next WEO release' not in text
    assert 'IMF WEO 2025' not in text and '暂无标记' not in text
    if rows:
        assert 'Countries with supplied data: 1' in text and '已提供数据的国家：1' in text
        assert 'Incomplete inputs do not establish an all-clear' in text
        assert ('No supplied country has three or more flags' in text) == (state == 'partial')
    else:
        assert 'Fragility readings unavailable in supplied data' in text and '所提供数据中的脆弱性读数不可用' in text
    assert payload == before


@pytest.mark.parametrize('state,year', [('partial',2022), ('flagged',2024)])
def test_owner_latest_field_year_is_not_an_edition_or_common_observation_clock(state, year):
    payload = fragility_fixture(state)
    assert payload['vulnerability']['as_of_years'] == {'min':year,'max':year}
    text = panel(payload).get_text(' ',strip=True)
    assert f'Latest year within each country: {year}–{year}' in text
    assert 'Underlying values can have different years and include projections' in text
    assert '不是发布日期' in text


@pytest.mark.parametrize('years', [None, {'min':None,'max':None}, {'min':False,'max':2024}, {'min':'<img src=x>','max':2024}])
def test_absent_or_untyped_year_range_remains_unavailable(years):
    payload=fragility_fixture('partial');payload['vulnerability']['as_of_years']=years
    el=panel(payload);text=el.get_text(' ',strip=True)
    assert 'Latest year within each country: Unavailable' in text
    assert not el.select('img[src=x]')
