"""Render actual owner outputs from synthetic frames; never acquire or qualify data."""
from copy import deepcopy
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.cb_desk import snapshot
from tests.test_intl_workspace_integration import render_fixture


def central_bank_fixture(kind='unknown'):
    # One observation has a genuine level but cannot establish either trend or impulse.
    values = {'unknown':[0.0], 'hold':[0.0,0.0], 'hike':[0.0,0.25], 'cut':[0.25,0.0]}[kind]
    dates = pd.date_range('2026-09-01', periods=len(values))
    rate = pd.DataFrame({'fed_funds':values}, index=dates)
    balance = pd.DataFrame({'assets':[100.0] * len(values)}, index=dates)
    def read(group, series):
        assert group == 'fred'
        return {'DFF':rate, 'WALCL':balance}.get(series)
    with patch('engine.cb_desk.store.read', read), patch('engine.cb_desk._load_calendar', return_value={}):
        return snapshot()


@pytest.mark.parametrize('kind,stance', [('unknown','Unavailable'),('hold','Holding'),('hike','Raising'),('cut','Cutting')])
def test_central_bank_unknown_is_not_an_unchanged_assessment(kind, stance):
    owner = central_bank_fixture(kind)
    original = deepcopy(owner)
    assert len(owner['cbs']) == 1
    if kind == 'unknown':
        assert owner['cbs'][0]['trend_3m'] is None
        assert owner['cbs'][0]['bs_impulse']['impulse_13w'] is None
    soup = BeautifulSoup(render_fixture(risk_desk={'cb_desk':owner}), 'html.parser')
    cells = soup.select_one('.ird-cb tbody tr').select('td')
    assert cells[1].select_one('b').get_text(strip=True) == ('0.25%' if kind == 'hike' else '0.00%')
    assert stance in cells[2].get_text()
    assert ('Unavailable' if kind == 'unknown' else 'Flat') in cells[4].get_text()
    if kind == 'unknown':
        assert 'Holding' not in cells[2].get_text() and 'Flat' not in cells[4].get_text()
    assert owner == original


def test_central_bank_absence_does_not_create_a_library_destination():
    html = render_fixture(risk_desk={'cb_desk':{'cbs':[]}})
    soup = BeautifulSoup(html,'html.parser')
    assert soup.select_one('#intl-central-banks') is None


def test_central_bank_missing_impulse_is_not_flat_even_with_known_trend():
    owner = central_bank_fixture('unknown')
    owner['cbs'][0]['trend_3m'] = 'hold'
    soup = BeautifulSoup(render_fixture(risk_desk={'cb_desk':owner}), 'html.parser')
    cell = soup.select_one('.ird-cb tbody tr').select('td')[4]
    assert 'Unavailable' in cell.get_text() and 'Flat' not in cell.get_text()
