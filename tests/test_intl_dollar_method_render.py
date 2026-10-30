"""Presentation must describe the supplied residual model, not infer market causes."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from engine.forex_dollar import smile_decomp
from tests.test_intl_dollar_absence_render import dollar_fixture, dollar_surfaces


@lru_cache(maxsize=3)
def _owner_case(kind):
    # No provider I/O: actual engine on deterministic synthetic input observations.
    rng = np.random.default_rng(19)
    n = 520
    idx = pd.bdate_range('2022-01-03', periods=n)
    changes = rng.normal(0, .025, n)
    returns = .01 * changes + rng.normal(0, .002, n)
    returns[-20:] += {'within': -.0003, 'above': .001, 'below': -.001}[kind]
    series = {
        'dxy': pd.Series(100 * np.exp(np.cumsum(returns)), index=idx),
        'us2y': pd.Series(4 + np.cumsum(changes), index=idx),
        'eur2y': pd.Series(np.full(n, 2.), index=idx),
    }
    with patch('engine.forex_dollar._load_series_for_smile', return_value=series):
        return smile_decomp()


def method_fixture(kind='within'):
    result = deepcopy(_owner_case(kind))
    # Deliberately distinct synthetic clocks, not claims about a live publication.
    result['built'] = '2026-10-12T04:05:06Z'
    return {'smile': result, 'built': '2026-10-14T22:00:00Z'}


@pytest.mark.parametrize('kind,regime,en,zh', [
    ('within', 'rates-driven', 'Within residual band', '残差在区间内'),
    ('above', 'safety-driven', 'Above rate model', '高于利差模型'),
    ('below', 'mixed', 'Below rate model', '低于利差模型'),
])
def test_actual_owner_regimes_are_model_reads_not_causal_verdicts(kind, regime, en, zh):
    payload = method_fixture(kind)
    assert payload['smile']['regime'] == regime
    assert payload['smile']['r2'] < .03  # A category alone does not imply a strong model fit.
    if kind == 'within':
        assert payload['smile']['regime_60d'] == 'mixed'  # No dual-window confirmation.
    if kind == 'above':
        assert payload['smile']['safety_bid_today'] is False  # No five-day confirmation.
    original = deepcopy(payload)
    chip, panel = dollar_surfaces(payload)
    for surface in [chip, panel.select_one('.ird-dollar-card')]:
        text = surface.get_text(' ', strip=True)
        assert en in text and zh in text
        for claim in ['not fear', 'Investors are paying', 'being bought', 'flight to safety',
                      'both rate differences and risk sentiment', '避险资产被买入', '主因']:
            assert claim not in text
    assert 'does not establish the cause' in panel.get_text(' ', strip=True)
    assert payload == original


def test_method_discloses_actual_windows_normalization_and_available_weights():
    _, panel = dollar_surfaces(method_fixture())
    text = panel.get_text(' ', strip=True)
    for expected in ['120-observation', '20-observation', '252-observation',
                     'without subtracting the mean', '60-observation', 'separate',
                     'eur2y', '1.0', 'not causal contributions']:
        assert expected in text
    for rejected in ['DXY vs VIX co-movement', 'Dual-window confirmed', 'Weights used: standard', 'nightly']:
        assert rejected not in text


@pytest.mark.parametrize('built', [None, '', 'omitted', '2026-10-12T04:05:06Z'])
def test_model_build_clock_is_never_an_observation_clock_or_parent_fallback(built):
    payload = method_fixture()
    if built == 'omitted':
        payload['smile'].pop('built')
    else:
        payload['smile']['built'] = built
    _, panel = dollar_surfaces(payload)
    footer = panel.select_one('.ird-asof').get_text(' ', strip=True)
    assert 'Observation date: Unavailable' in footer and '观测日：不可用' in footer
    assert 'Model built:' in footer and '模型生成：' in footer
    assert '2026-10-14' not in footer and 'As of' not in footer and '截至' not in footer
    if built and built != 'omitted':
        assert built in footer
    else:
        assert 'Model built: Unavailable' in footer


def test_clock_and_weights_are_escaped_without_injecting_html():
    payload = method_fixture()
    payload['smile']['built'] = '<b data-clock-injection="1">clock</b>'
    payload['smile']['weights_used'] = {'<b data-weight-injection="1">leg</b>': 1.0}
    _, panel = dollar_surfaces(payload)
    assert not panel.select('[data-clock-injection], [data-weight-injection]')
    assert '<b data-clock-injection="1">clock</b>' in panel.get_text()
    assert '<b data-weight-injection="1">leg</b>' in panel.get_text()


def test_unavailable_tooltip_does_not_promise_a_schedule_or_model_inputs():
    _, panel = dollar_surfaces(dollar_fixture())
    tooltip = panel.select_one('.tip').get_text(' ', strip=True)
    assert 'No supported regime was supplied' in tooltip
    assert 'nightly' not in tooltip and 'risk-off' not in tooltip and '每晚' not in tooltip


def test_displayed_five_day_signal_stays_with_the_separate_two_tier_owner():
    payload = method_fixture('above')
    payload['smile']['safety_bid_today'] = True
    _, panel = dollar_surfaces(payload)
    assert not panel.select('.ird-safety-tag')
    payload['smile']['safety_bid_today'] = False
    payload['two_tier'] = {'safety_bid': True, 'tier2': {'legs': {'safety_bid_flag': {
        'dxy_5d_chg': 1.2, 'dgs2_5d_chg': -4.5}}}}
    _, panel = dollar_surfaces(payload)
    tag = panel.select_one('.ird-safety-tag').get_text(' ', strip=True)
    assert '1.2 pts' in tag and '4.5 bp' in tag
    assert '5-day signal' in panel.get_text()


def five_day_fixture(available=True):
    from engine.contagion import two_tier_read
    idx = pd.bdate_range('2026-09-01', periods=6)
    dxy = pd.DataFrame({'close': [120., 120.2, 120.4, 120.6, 120.8, 121.2]}, index=idx)
    dgs2 = pd.Series([4., 3.99, 3.98, 3.97, 3.96, 3.955], index=idx)
    with patch('engine.contagion._fred_series', side_effect=lambda key: dgs2 if key == 'DGS2' else None), \
         patch('engine.contagion._load_etf_close', return_value=None), \
         patch('engine.contagion.store.read', side_effect=lambda group, key: dxy if (group, key) == ('yahoo', 'DX-Y.NYB') else None):
        owner = two_tier_read(em_stress_state='unknown')
    payload = method_fixture() if available else dollar_fixture()
    payload['two_tier'] = owner
    return payload


@pytest.mark.parametrize('available', [True, False])
def test_five_day_owner_index_change_is_not_a_percent_or_current_date_claim(available):
    payload = five_day_fixture(available)
    leg = payload['two_tier']['tier2']['legs']['safety_bid_flag']
    assert leg['dxy_5d_chg'] == 1.2 and leg['dgs2_5d_chg'] == -4.5
    # 120 -> 121.2 is 1 percent, not 1.2 percent. The field contains index points.
    chip, panel = dollar_surfaces(payload)
    for surface in [chip, panel]:
        tag = surface.select_one('.ird-safety-tag').get_text(' ', strip=True)
        assert '+1.2 pts' in tag and '+1.2点' in tag
        assert '1.2%' not in tag
        assert 'Five-day flag' in tag and 'today' not in tag and '今日' not in tag
        assert '4.5 bp' in tag
