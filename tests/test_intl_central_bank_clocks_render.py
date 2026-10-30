"""Independent CB source clocks from actual owner with synthetic source frames."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.cb_desk import snapshot
from tests.test_intl_workspace_integration import render_fixture


class FixedOwnerTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026,10,14,tzinfo=timezone.utc)


def central_bank_clocks_fixture():
    def frame(column, values, dates):
        return pd.DataFrame({column:values},index=pd.to_datetime(dates))
    frames={
        'DFF':frame('fed_funds',[3.5,3.5],['2026-10-12','2026-10-13']),
        'IRSTCI01JPM156N':frame('jp_short',[0.1,0.1],['2026-08-01','2026-09-01']),
        'IR3TIB01GBM156N':frame('gb_short',[4.,4.],['2026-05-01','2026-06-01']),
        'WALCL':frame('assets',[100.,100.],['2026-09-30','2026-10-07']),
        'JPNASSETS':frame('assets',[100.,101.],['2026-08-31','2026-09-30']),
    }
    def read(group, series):
        assert group=='fred'
        return frames.get(series)
    with patch('engine.cb_desk.store.read',read),patch('engine.cb_desk._load_calendar',return_value={}),patch('engine.cb_desk.datetime',FixedOwnerTime):
        return snapshot()


@pytest.mark.parametrize('kind',['dated','missing','omitted','escaped'])
def test_central_bank_clocks_never_borrow_the_latest_roster_date(kind):
    owner=central_bank_clocks_fixture()
    assert [r['id'] for r in owner['cbs']]==['FED','BOJ','BOE']
    assert [r['stale'] for r in owner['cbs']]==[False,False,True]
    if kind=='missing':
        owner['cbs'][1]['asof']=None;owner['cbs'][1]['bs_impulse']['asof']=None
    elif kind=='omitted':
        owner['cbs'][1].pop('asof');owner['cbs'][1]['bs_impulse'].pop('asof')
    elif kind=='escaped':
        owner['cbs'][1]['asof']='<script>alert(1)</script>'
    original=deepcopy(owner)
    soup=BeautifulSoup(render_fixture(risk_desk={'cb_desk':owner}),'html.parser')
    panel=soup.select_one('#intl-central-banks').find_parent('div',class_='panel')
    dates=panel.select('[data-cb-rate-observation]')
    assert len(dates)==3
    assert '2026-10-13' in dates[0].get_text() and 'Daily' in dates[0].get_text()
    assert '2026-06-01' in dates[2].get_text() and 'Monthly' in dates[2].get_text()
    assert 'Stale' in dates[2].get_text() and 'Stale' not in dates[0].get_text()
    assert '2026-10-13' not in dates[1].get_text()
    assert ('Unavailable' if kind in ('missing','omitted') else owner['cbs'][1]['asof']) in dates[1].get_text()
    assert '<span' not in dates[1].get_text() and dates[1].find('script') is None
    balances=panel.select('[data-cb-balance-observation]')
    assert len(balances)==2 and '2026-10-07' in balances[0].get_text()
    assert ('Unavailable' if kind in ('missing','omitted') else '2026-09-30') in balances[1].get_text()
    assert 'Latest rate observation across displayed banks' in panel.get_text()
    assert 'public weekly data' not in str(panel)
    assert owner==original
