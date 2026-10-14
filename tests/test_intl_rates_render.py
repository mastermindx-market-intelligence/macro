"""Supplied rates presentation: missing values never acquire numeric geometry."""
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from engine import intl_inputs
from lib import store
from tests.test_intl_workspace_integration import render_fixture


def rates_render_fixture():
    """Existing rates_desk output shape, synthetic values; no collector/store call."""
    rows = []
    for cc, name, zh, short, y10 in [
        ("JP", "Japan", "日本", None, 2.6),
        ("TW", "Taiwan", "台湾", 0.0, 2.6),
        ("AU", "Australia", "澳大利亚", -0.4, -0.1),
        ("HK", "Hong Kong", "香港", None, None),
    ]:
        curve = y10 - short if y10 is not None and short is not None else None
        rows.append(dict(cc=cc, name=name, name_zh=zh, flag="", region="synthetic",
                         short=short, y10=y10, curve=curve,
                         shape="na" if curve is None else "normal",
                         shape_en="Unavailable" if curve is None else "Normal",
                         shape_zh="不可用" if curve is None else "正常",
                         real_yield=None, carry_vs_us=None, y10_chg3m=None,
                         spark_svg="", y10_asof="synthetic:yield-clock", cpi_asof=None))
    return dict(anchor=dict(y10=4.1, y2=None, curve=None, asof="synthetic:US-clock"),
                rows=rows, liquidity=None, periphery=None)


@pytest.fixture(autouse=True)
def no_data_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("rates presentation must not acquire data")
    monkeypatch.setattr(store, "read", forbidden)
    monkeypatch.setattr(intl_inputs, "_intl_closes", forbidden)


@pytest.mark.parametrize("short,y10,points", [
    (None, 2.6, 0), (0.0, 2.6, 2), (1.2, 2.6, 2), (-0.4, -0.1, 2), (None, None, 0),
])
def test_curve_geometry_requires_both_supplied_endpoints(short, y10, points):
    rates = rates_render_fixture()
    rates["rows"] = [rates["rows"][0]]
    rates["rows"][0].update(short=short, y10=y10)
    original = deepcopy(rates)
    soup = BeautifulSoup(render_fixture(rates=rates), "html.parser")
    panel = soup.select_one('#intl-rates-curves').find_parent('div', class_='panel')
    card = panel.select_one('.rcard')
    assert len(card.select('.curve .d')) == points
    assert len(card.select('.curve .ln')) == int(points > 0)
    if y10 is not None:
        assert f'10y {y10:.1f}' in card.get_text(' ', strip=True)
        if short is None:
            assert '3m unavailable' in card.get_text() and '3月数据不可用' in card.get_text()
        else:
            assert f'3m {short:.1f}' in card.get_text(' ', strip=True)
    else:
        assert 'No keyless yield curve' in card.get_text()
    tool = soup.select_one('[data-im-library-tool="rates_curves_carry"]')
    assert tool.select_one('a[href="#intl-rates-curves"]') is not None
    assert rates == original


@pytest.mark.parametrize("y2,expected", [(None, '— 2y'), (0.0, '0.0% 2y'), (3.85, '3.85% 2y')])
def test_us_anchor_missing_two_year_is_not_printed_as_a_number(y2, expected):
    rates = rates_render_fixture()
    rates['anchor']['y2'] = y2
    soup = BeautifulSoup(render_fixture(rates=rates), 'html.parser')
    header = soup.select_one('#intl-rates-curves').parent.get_text(' ', strip=True)
    assert expected in header and '4.1%' in header
    assert 'None' not in header
