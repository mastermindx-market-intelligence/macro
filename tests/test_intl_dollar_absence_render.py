"""Unavailable owner regimes must not become an affirmative mixed-dollar read."""
from copy import deepcopy
from unittest.mock import patch

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.forex_dollar import smile_decomp
from tests.test_intl_workspace_integration import render_fixture


def missing_dollar_owner(kind):
    s = pd.Series([100 + i for i in range(10)], index=pd.bdate_range('2026-09-01', periods=10))
    series = {'dxy': s, 'us2y': s / 20, 'eur2y': s / 30}
    if kind == 'missing_dxy': series['dxy'] = None
    elif kind == 'missing_us2y': series['us2y'] = None
    elif kind == 'missing_foreign': series['eur2y'] = None
    with patch('engine.forex_dollar._load_series_for_smile', return_value=series):
        result = smile_decomp()
    assert result['regime'] is None and result['gaps']
    return result


def dollar_fixture(kind='missing_dxy'):
    smile = (None if kind == 'absent' else {} if kind == 'empty' else
             {'regime': 'unknown', 'display_only': True} if kind == 'unknown' else missing_dollar_owner(kind))
    return {'smile': smile, 'built': '2026-10-14T00:00:00Z'}


def dollar_surfaces(payload):
    soup = BeautifulSoup(render_fixture(risk_desk=payload), 'html.parser')
    chip = next(c for c in soup.select('.ird-hchip') if 'Dollar' in c.select_one('.hc-lbl').get_text())
    panel = soup.select_one('#intl-dollar-conditions').find_parent('div', class_='panel')
    return chip, panel


@pytest.mark.parametrize('kind', ['absent', 'empty', 'missing_dxy', 'missing_us2y', 'missing_foreign', 'short_history', 'unknown'])
def test_unavailable_dollar_owner_is_never_a_mixed_read(kind):
    payload = dollar_fixture(kind)
    original = deepcopy(payload)
    chip, panel = dollar_surfaces(payload)
    for element in [chip, panel.select_one('.ird-dollar-card')]:
        text = element.get_text(' ', strip=True)
        assert 'Unavailable' in text
        assert 'Mixed picture' not in text and 'both in play' not in text
        assert 'tonight' not in text.lower()
    assert 'state-ok' not in chip.get('class', [])
    assert payload == original


@pytest.mark.parametrize('regime,word', [('rates-driven', 'Within residual band'), ('safety-driven', 'Above rate model'), ('mixed', 'Below rate model')])
def test_known_dollar_regime_remains_available(regime, word):
    _, panel = dollar_surfaces({'smile': {'regime': regime, 'display_only': True}})
    assert word in panel.select_one('.regime-word').get_text()


def test_independent_safety_bid_is_not_lost_when_regime_unavailable():
    payload = dollar_fixture()
    payload['two_tier'] = {'safety_bid': True}
    chip, panel = dollar_surfaces(payload)
    assert 'Unavailable' in chip.get_text()
    assert 'Five-day flag' in panel.get_text()
