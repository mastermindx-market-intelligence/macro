"""Dollar funding summary must distinguish a missing leg from its threshold result."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.contagion import two_tier_read
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=4)
def _funding_owner(kind):
    idx = pd.bdate_range('2026-09-01', periods=6)
    spreads = {'absent': None, 'short': [.02] * 4, 'triggered': [.02] * 6,
               'not_triggered': [-.01] * 5 + [.02]}[kind]
    def fred(key):
        if spreads is None or key not in ('SOFR', 'IORB'):
            return None
        values = [4. + v for v in spreads] if key == 'SOFR' else [4.] * len(spreads)
        return pd.Series(values, index=idx[:len(spreads)])
    with patch('engine.contagion._fred_series', side_effect=fred), \
         patch('engine.contagion._load_etf_close', return_value=None), \
         patch('engine.contagion.store.read', return_value=None):
        return two_tier_read(em_stress_state='unknown')


def funding_fixture(kind='absent', swap=None):
    return {'two_tier': deepcopy(_funding_owner(kind)), 'swap_lines_bn': swap}


def funding_chip(payload):
    soup = BeautifulSoup(render_fixture(risk_desk=payload), 'html.parser')
    return next(c for c in soup.select('.ird-hchip') if 'Dollar Funding' in c.select_one('.hc-lbl').get_text())


@pytest.mark.parametrize('kind', ['absent', 'short'])
def test_missing_corridor_never_becomes_calm_or_normal(kind):
    payload = funding_fixture(kind)
    assert 'sofr_iorb_corridor' not in payload['two_tier']['tier2']['legs']
    before = deepcopy(payload)
    chip = funding_chip(payload)
    text = chip.get_text(' ', strip=True)
    assert 'Unavailable' in text and '不可用' in text
    assert 'Calm' not in text and 'normal' not in text and 'Ignore' not in text
    assert 'state-unknown' in chip.get('class', [])
    assert payload == before


@pytest.mark.parametrize('kind,hot,en,zh', [('triggered', True, 'Threshold triggered', '阈值已触发'),
                                          ('not_triggered', False, 'Not triggered', '未触发')])
def test_actual_corridor_threshold_is_not_a_general_funding_verdict(kind, hot, en, zh):
    payload = funding_fixture(kind)
    leg = payload['two_tier']['tier2']['legs']['sofr_iorb_corridor']
    assert leg['hot'] is hot and leg['value'] == .02
    before = deepcopy(payload)
    text = funding_chip(payload).get_text(' ', strip=True)
    assert en in text and zh in text
    assert '+2.0 bp' in text  # Owner percentage points -> basis points.
    assert '5 observations' in text and 'quarter-end' in text
    assert 'normal' not in text and 'Calm' not in text and 'no funding stress' not in text
    assert payload == before


@pytest.mark.parametrize('hot', [None, 'false', 0])
def test_unsupported_hot_value_does_not_gain_boolean_authority(hot):
    payload = funding_fixture('not_triggered')
    payload['two_tier']['tier2']['legs']['sofr_iorb_corridor']['hot'] = hot
    assert 'Unavailable' in funding_chip(payload).select_one('.hc-state').get_text()


@pytest.mark.parametrize('swap,en,zh', [(None, 'Fed swap lines: Unavailable', '美联储互换余额：不可用'),
                                      (0., 'Fed swap lines: $0.0bn', '美联储互换余额：0.0亿美元'),
                                      (1.2, 'Fed swap lines: $1.2bn', '美联储互换余额：12.0亿美元')])
def test_swap_availability_and_units_are_independent_of_the_corridor(swap, en, zh):
    payload = funding_fixture('absent', swap)
    text = funding_chip(payload).get_text(' ', strip=True)
    assert en in text and zh in text
    assert 'Unavailable' in funding_chip(payload).select_one('.hc-state').get_text()


@pytest.mark.parametrize('built', [None, '2026-10-14T12:34:56Z'])
def test_shared_desk_build_stamp_is_not_a_common_observation_date(built):
    payload = funding_fixture()
    payload['built'] = built
    soup = BeautifulSoup(render_fixture(risk_desk=payload), 'html.parser')
    footer = soup.select_one('.ird-stage > .ird-asof').get_text(' ', strip=True)
    assert 'Desk built:' in footer and '风险台生成：' in footer
    assert ('Unavailable' if built is None else built) in footer
    assert 'As of' not in footer and '截至' not in footer


def test_corridor_threshold_uses_caution_not_price_direction_semantics():
    chip = funding_chip(funding_fixture('triggered'))
    assert 'state-caut' in chip.get('class', [])
    title_classes = chip.select_one('.hc-state').get('class', [])
    assert 'info' in title_classes and 'red' not in title_classes and 'green' not in title_classes
