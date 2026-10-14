"""Ticker and as-of strings in the Risk Radar dialogs render escaped.

Both dialogs render under a Jinja environment with autoescape OFF
(scripts/build_site.py; mirrored by tests/test_dashboard_template_render.py
`_env` and by the partial's own contract tests), so a string reaches the HTML
verbatim unless the template escapes it. Tickers and dates arrive from upstream
stores and feeds, not from the template author, so each one carries `|e`:

- the US ``#dlg-risk`` dialog in templates/dashboard.html.j2
- the shared CN/HK/CA dialog in templates/_risk_radar_dlg.html.j2

Each case plants markup in ONE field and asserts it renders as text, so
dropping the filter from any single site fails its own case. `|e` leaves a
string with no ``<>&'"`` byte-identical, and the ordinary-value cases pin the
exact spans an ordinary ticker or ISO date renders.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from tests.test_macro_risk_dialog import _render, _vm

ROOT = Path(__file__).resolve().parent.parent

PLANT = "<img src=x onerror=1>"
ESCAPED = "&lt;img src=x onerror=1&gt;"


# ── US #dlg-risk (templates/dashboard.html.j2) ─────────────────────────────


def _us_vm():
    """The dialog's view model with every ticker / as-of site populated."""
    vm = _vm()
    vm["intl_cascade"] = {
        "n_alert": 1,
        "alerts": [
            {"ticker": "0700.HK", "alert": True, "state": "elevated",
             "score": 71, "asof": "2026-08-27"},
        ],
        "rows": [
            {"ticker": "RY.TO", "alert": False, "state": "calm", "score": 22,
             "asof": "2026-08-28"},
        ],
    }
    vm["vol_weather"] = {"as_of": "2026-08-28"}
    vm["market_state"] = copy.deepcopy(vm["market_state"])
    vm["leadership_crack"] = copy.deepcopy(vm["leadership_crack"])
    vm["leadership_crack"]["worst_members"][1]["ticker"] = "BRK.B"
    vm["sector_heat"] = copy.deepcopy(vm["sector_heat"])
    return vm


def _risk_dlg(html: str) -> str:
    """The #dlg-risk dialog alone — up to the next dialog, whichever it is."""
    start = html.index('id="dlg-risk"')
    nxt = html.find('<div class="mx5-dlg" id="dlg-', start)
    return html[start:] if nxt < 0 else html[start:nxt]


def _set_board_date(vm, value):
    vm["latest"] = dict(vm["latest"], date=value)


def _set_cycle_favor(vm, value):
    vm["market_state"]["radar"]["cycle"]["sector_bias"]["favor"][0]["ticker"] = value


def _set_cycle_avoid(vm, value):
    vm["market_state"]["radar"]["cycle"]["sector_bias"]["avoid"][0]["ticker"] = value


def _set_overseas_ticker(vm, value):
    vm["intl_cascade"]["rows"][0]["ticker"] = value


def _set_overseas_asof_fresh(vm, value):
    vm["intl_cascade"]["rows"][0]["asof"] = value


def _set_overseas_asof_old(vm, value):
    # Sorts before the board date, so the "last graded … before this board"
    # branch renders rather than the plain "Graded …" one.
    vm["intl_cascade"]["alerts"][0]["asof"] = "!" + value


def _set_vol_asof(vm, value):
    vm["vol_weather"]["as_of"] = value


def _set_sector_heat_asof(vm, value):
    vm["sector_heat"]["as_of"] = value


def _set_damage_asof(vm, value):
    vm["leadership_crack"]["asof"] = value


def _set_damage_since(vm, value):
    vm["leadership_crack"]["state_since"] = value


def _set_damage_ticker(vm, value):
    vm["leadership_crack"]["worst_members"][0]["ticker"] = value


US_FIELDS = {
    "header-asof": _set_board_date,
    "cycle-favor-ticker": _set_cycle_favor,
    "cycle-avoid-ticker": _set_cycle_avoid,
    "overseas-ticker": _set_overseas_ticker,
    "overseas-graded-asof": _set_overseas_asof_fresh,
    "overseas-last-graded-asof": _set_overseas_asof_old,
    "vol-asof": _set_vol_asof,
    "sector-heat-asof": _set_sector_heat_asof,
    "damage-asof": _set_damage_asof,
    "damage-state-since": _set_damage_since,
    "damage-ticker": _set_damage_ticker,
}


@pytest.mark.parametrize("setter", US_FIELDS.values(), ids=US_FIELDS.keys())
def test_us_risk_dialog_escapes_planted_markup(setter):
    vm = _us_vm()
    setter(vm, PLANT)
    dlg = _risk_dlg(_render(vm))
    assert PLANT not in dlg
    assert ESCAPED in dlg


def test_us_risk_dialog_renders_ordinary_tickers_and_dates_verbatim():
    dlg = _risk_dlg(_render(_us_vm()))
    for span in (
        '<span class="riskdlg-asof">2026-08-28</span>',
        '<span class="rlx-chip up">XLU</span>',
        '<span class="rlx-chip dn">XLY</span>',
        '<span class="l-en">RY.TO</span>',
        "<span class=\"l-en\">Last graded 2026-08-27, before this board’s date (2026-08-28)",
        '<span class="l-en">Graded 2026-08-28.</span><span class="l-zh">评级日期 2026-08-28。</span>',
        '<div class="rkc-ldr-tkr">NVDA</div>',
        '<div class="rkc-ldr-tkr">BRK.B</div>',
        "<small><span class=\"l-en\">as of</span><span class=\"l-zh\">截至</span> 2026-08-21</small>",
        'data-tip-en="State since 2026-06-26.',
    ):
        assert span in dlg, span


# ── CN / HK / CA shared dialog (templates/_risk_radar_dlg.html.j2) ─────────

_TICKERS = {"cn": "600118.SS", "hk": "0700.HK", "ca": "RY.TO"}


def _country_ctx(mkt, *, ticker=None, asof="2026-08-11", fx_built="2026-08-08"):
    return {
        "asof": asof,
        "leaders": {"rows": [
            {"ticker": ticker or _TICKERS[mkt], "name_en": "Leader", "pct": 40,
             "value": "+4.0%", "tone": "up"},
        ]},
        # A stale currency read older than the board names its own date.
        "fx": {"usd_dir": "weakening", "stale": True, "built_date": fx_built},
    }


def _render_country(mkt, ctx) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    tpl = env.from_string(
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg(mkt, rd, scares, ctx) }}"
    )
    return tpl.render(mkt=mkt, rd=None, scares=None, ctx=ctx)


@pytest.mark.parametrize("mkt", sorted(_TICKERS))
@pytest.mark.parametrize("field", ["ticker", "asof", "fx_built"])
def test_country_dialog_escapes_planted_markup(mkt, field):
    html = _render_country(mkt, _country_ctx(mkt, **{field: PLANT}))
    assert PLANT not in html
    assert ESCAPED in html


@pytest.mark.parametrize("mkt", sorted(_TICKERS))
def test_country_dialog_renders_ordinary_tickers_and_dates_verbatim(mkt):
    html = _render_country(mkt, _country_ctx(mkt))
    assert f'<span class="rrd-ldr-tkr">{_TICKERS[mkt]}</span>' in html
    assert '<span class="l-en">As of 2026-08-11, currency readings from 2026-08-08. </span>' in html
    assert '<span class="l-zh">数据截至 2026-08-11，汇率读数为 2026-08-08。</span>' in html
