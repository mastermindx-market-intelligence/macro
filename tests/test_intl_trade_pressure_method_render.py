"""Trade pressure describes its model, not current direction or causal shares."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch

import pandas as pd
import pytest

from engine import contagion_links as owner
from tests.test_intl_trade_pressure_absence_render import panel


@lru_cache(maxsize=2)
def rebound_owner(state='rebound'):
    # US rebounds on the last observation while remaining below its 21-observation high.
    closes = [100.] * 15 + [99., 98., 96., 94., 92., 90., 89., 90., 91., 92.]
    def read(group, ticker):
        if state == 'rebound' and (group, ticker) == owner._BENCH['us']:
            return pd.DataFrame({'close': closes}, index=pd.bdate_range('2024-01-02', periods=25))
        return None
    with patch('engine.contagion_links.store.read', side_effect=read), \
            patch('engine.contagion_links._read_last_row', return_value=None):
        return owner.compute()


def method_fixture(state='rebound'):
    return deepcopy(rebound_owner(state))


def test_rebounding_bench_remains_a_model_pressure_source_not_current_fall():
    p = method_fixture()
    sev = p['severity']['us']
    assert 92 / 91 - 1 > 0
    assert sev['dd21'] == pytest.approx(.08)
    assert sev['ret10'] == pytest.approx(-.08)
    assert sev['sigma'] == 1
    text = panel(p).get_text(' ', strip=True)
    assert 'recent drawdowns and losses' in text
    assert '近期回撤与跌幅' in text
    assert 'actually falling' not in str(panel(p))
    assert '实际下跌方' not in str(panel(p))


def test_source_weight_is_not_its_share_of_inbound_pressure():
    p = method_fixture()
    ca = p['pressure']['ca']
    src = ca['top_exporters'][0]
    assert src['market'] == 'us' and len(ca['top_exporters']) == 1
    assert src['contribution'] == ca['raw']
    assert src['weight'] == pytest.approx(.3469)
    assert src['contribution'] / ca['raw'] == 1
    text = panel(p).get_text(' ', strip=True)
    assert 'Source percentages are linkage weights, not shares of pressure.' in text
    assert '来源百分比是关联权重，并非压力占比。' in text
    assert '35%' in text


@pytest.mark.parametrize('state', ['absent', 'rebound'])
def test_method_explains_fallback_history_and_noncausal_scope_without_changing_payload(state):
    p = method_fixture(state)
    before = deepcopy(p)
    assert all(row is None for row in p['matrix']['dynamic'].values())
    assert p['matrix']['blended'] == p['matrix']['static']
    assert p['params']['pct_window'] == 504
    el = panel(p)
    help_node = el.select_one('#intl-trade-supply-links .help')
    en = help_node.select_one('.tip .l-en').get_text()
    zh = help_node.select_one('.tip .l-zh').get_text()
    for phrase in ['preset linkage weights', 'ETF volatility', 'where available', '21-observation', '10-observation', 'up to 504', 'at least 252', 'not causal', 'not a forecast']:
        assert phrase in en
    for phrase in ['预设关联权重', 'ETF波动率', '21期', '10期', '最多采用504', '至少需要252', '并非因果', '不是预测']:
        assert phrase in zh
    assert 'Levels are historical bands, not a trend.' in el.get_text()
    assert '等级是历史区间，并非趋势。' in el.get_text()
    assert p == before


def test_trade_destination_can_receive_native_keyboard_focus():
    assert panel(method_fixture()).select_one('#intl-trade-supply-links').get('tabindex') == '-1'
