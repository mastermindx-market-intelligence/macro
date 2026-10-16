"""Each supplied spread observation owns its date; absent clocks stay absent."""
from copy import deepcopy

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.intl_risk import _leg
from tests.test_intl_workspace_integration import render_fixture


def credit_dates_fixture():
    em = _leg(pd.Series([4.25], index=pd.to_datetime(['2026-10-13'])), 252, 'synthetic_credit')
    # Existing regional_oas contract: value, vel_20d_z, asof; no stale flag.
    return {'em_stress': {'legs': {'em_hy_oas': em}}, 'two_tier': {'tier1': {
        'regional_oas': {
            'asia': {'value': 1.75, 'vel_20d_z': None, 'asof': '2026-10-09'},
            'latam': {'value': 0, 'vel_20d_z': 0, 'asof': '2026-09-30'},
            'emea': {'value': 2.5, 'vel_20d_z': None},
        }}}}


def cards(payload):
    return BeautifulSoup(render_fixture(risk_desk=payload), 'html.parser').select('.ird-spread-card')


def test_credit_distinct_dates_are_scoped_to_their_own_card():
    payload = credit_dates_fixture()
    original = deepcopy(payload)
    rendered = cards(payload)
    for card, date in zip(rendered, ['2026-10-13', '2026-10-09', '2026-09-30', None]):
        clock = card.select_one('[data-credit-observation]')
        assert clock is not None
        text = clock.get_text(' ', strip=True)
        assert (date or 'Unavailable') in text
        for foreign in {'2026-10-13', '2026-10-09', '2026-09-30'} - {date}:
            assert foreign not in text
        assert 'Fresh' not in text and 'Stale' not in text
    assert [c.select_one('.sc-val').get_text(strip=True) for c in rendered] == ['4.25%', '1.75%', '0.00%', '2.50%']
    assert payload == original


@pytest.mark.parametrize('missing', ['omitted', None, '', 'absent_leg'])
def test_credit_missing_clock_cannot_borrow_a_neighbours_date(missing):
    payload = credit_dates_fixture()
    legs = [payload['em_stress']['legs'], payload['two_tier']['tier1']['regional_oas']]
    for owner, key in [(legs[0], 'em_hy_oas'), (legs[1], 'asia'), (legs[1], 'latam'), (legs[1], 'emea')]:
        if missing == 'absent_leg':
            owner[key] = None
        elif missing == 'omitted':
            owner[key].pop('asof', None)
        else:
            owner[key]['asof'] = missing
    for card in cards(payload):
        clock = card.select_one('[data-credit-observation]')
        assert clock is not None
        assert 'Unavailable' in clock.get_text(' ', strip=True)
        assert '2026-' not in clock.get_text()


def test_credit_date_strings_are_text_not_markup():
    payload = credit_dates_fixture()
    hostile = '<img src=x onerror=alert(1)> & "clock"'
    payload['em_stress']['legs']['em_hy_oas']['asof'] = hostile
    for leg in payload['two_tier']['tier1']['regional_oas'].values():
        leg['asof'] = hostile
    for card in cards(payload):
        clock = card.select_one('[data-credit-observation]')
        assert clock is not None
        assert clock.find('img') is None
        assert hostile in clock.get_text()
