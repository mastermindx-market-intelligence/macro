"""Presentation of supplied clocks only; no freshness or rights qualification."""
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from tests.test_intl_rates_render import rates_render_fixture, no_data_io
from tests.test_intl_workspace_integration import render_fixture


def rates_dates_fixture():
    rates = rates_render_fixture()
    rates['anchor'].update(y2=3.8, asof='2026-09-29')
    for row, y10_date, cpi_date in zip(rates['rows'],
                                    ['2026-08', None, '2026-07', None],
                                    ['2019-12', '2026-06', None, None]):
        row.update(y10_asof=y10_date, cpi_asof=cpi_date)
    return rates


@pytest.mark.parametrize('mode', ['dated', 'missing', 'omitted', 'escaped'])
def test_rates_date_fields_keep_their_owner_scope_and_absence(mode):
    rates = rates_dates_fixture()
    row = rates['rows'][0]
    if mode == 'missing':
        row.update(y10_asof=None, cpi_asof=None)
        rates['anchor']['asof'] = None
    elif mode == 'omitted':
        row.pop('y10_asof'); row.pop('cpi_asof'); rates['anchor'].pop('asof')
    elif mode == 'escaped':
        row['y10_asof'] = '<script>alert(1)</script>'
    original = deepcopy(rates)
    soup = BeautifulSoup(render_fixture(rates=rates), 'html.parser')
    panel = soup.select_one('#intl-rates-curves').find_parent('div', class_='panel')
    card = panel.select_one('.rcard')
    dates = card.select_one('[data-rates-dates]')
    assert dates is not None
    assert '<span' not in dates.get_text(), 'localized fallback must remain markup, not printed tags'
    assert '10y observation month' in dates.get_text() and 'CPI observation month' in dates.get_text()
    if mode in ('dated', 'escaped'):
        assert row['y10_asof'] in dates.get_text() and '2019-12' in dates.get_text()
    else:
        assert dates.get_text().count('Unavailable') == 2
        assert '2026-08' not in dates.get_text()
    assert dates.find('script') is None
    anchor = panel.select_one('[data-rates-anchor-date]')
    assert anchor is not None and 'US 10y observation date' in anchor.get_text()
    if mode in ('missing', 'omitted'):
        assert 'Unavailable' in anchor.get_text() and '2026-09-29' not in anchor.get_text()
    else:
        assert '2026-09-29' in anchor.get_text()
    assert 'US 2y date unavailable' in anchor.get_text()
    zero_card = panel.select('.rcard')[1]
    assert '3m date unavailable' in zero_card.get_text()
    assert '10y 2.60%' in zero_card.get_text(' ', strip=True)
    assert rates == original
