"""The one-close age line, from the owner through the US popup and the China dialog.

Synthetic closes only. ``lib.pullback_observation.observe`` admits
``observed_closes_since_onset == 1``. The smallest series is 62 flat 100.0
closes plus one close at 95.0 (63 sessions, the shock rule on the first bar
the reference window can judge). One fewer close is not enough history. A
single close at 95.1 does not confirm. Two closes at 98.0 also admit count 1,
and that series is one session longer. The product path is the same reader
shape as ``_feed`` in tests/test_pullback_episode_fuzz.py: a synthetic
``LicensedCloses`` into ``snapshot(..., observer=observe)`` and ``present``.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup

from lib import cn_calendar, nyse_calendar
from lib.pullback_depth import LicensedCloses
from lib.pullback_observation import RULES, observe
from lib.cn_pullback_observation import present as present_cn
from lib.cn_pullback_observation import snapshot as snapshot_cn
from lib.us_pullback_observation import present as present_us
from lib.us_pullback_observation import snapshot as snapshot_us

ROOT = Path(__file__).resolve().parents[1]
_END = date(2026, 6, 12)
_US_NOW = datetime.combine(_END, time(18, 0), tzinfo=nyse_calendar.ET)
_CN_NOW = datetime.combine(_END, time(18, 0), tzinfo=cn_calendar.CST)

_SINGULAR_EN = "1 observed close since the pullback was confirmed"
_SINGULAR_ZH = "1 个已观测收盘（自回撤确认起）"
_PLURAL_EN = "2 observed closes since the pullback was confirmed"


def _weekday(day: date) -> bool:
    return day.weekday() < 5


def _rows(n_flat: int, tail: list[float], is_session, end: date) -> list[tuple[str, float]]:
    needed = n_flat + len(tail)
    found: list[date] = []
    cursor = end
    while len(found) < needed:
        if is_session(cursor):
            found.append(cursor)
        cursor -= timedelta(days=1)
        if (end - cursor).days > needed * 4 + 40:
            raise RuntimeError(f"no {needed} sessions on or before {end}")
    found.reverse()
    values = [100.0] * n_flat + [float(price) for price in tail]
    return [(day.isoformat(), price) for day, price in zip(found, values)]


def _owner(n_flat: int, tail: list[float]) -> dict:
    rows = _rows(n_flat, tail, _weekday, _END)
    return observe(
        rows,
        expected_session=date.fromisoformat(rows[-1][0]),
        is_session=_weekday,
    )


def _product(market: str, tail: list[float]) -> tuple[dict, dict]:
    """snapshot + present, with the synthetic series standing in for the reader."""
    if market == "us":
        now, is_session = _US_NOW, nyse_calendar.is_session
        expected = nyse_calendar.expected_last_session(now)
        snap, present = snapshot_us, present_us
    else:
        now, is_session = _CN_NOW, cn_calendar.is_session
        expected = cn_calendar.expected_last_session(now)
        snap, present = snapshot_cn, present_cn
    rows = _rows(RULES.reference_closes - 1, tail, is_session, expected)

    def read(_expected, rows=rows):
        return LicensedCloses(rows=list(rows))

    observation = snap(now=now, read=read, observer=observe)
    return observation, present(observation)


@lru_cache(maxsize=1)
def _dashboard():
    import jinja2
    from engine import i18n

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.filters["min"] = lambda seq: min(seq)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    return env


def _us_popup_age(view: dict):
    from tests.test_macro_risk_dialog import _vm

    vm = _vm()
    vm["us_pullback_view"] = view
    html = _dashboard().get_template("dashboard.html.j2").render(**vm, mode="macro")
    dialog = BeautifulSoup(html, "html.parser").select_one("#dlg-risk")
    assert dialog is not None
    age = dialog.select_one('[data-metric="age"]')
    assert age is not None
    return age


def _cn_dialog_age(view: dict):
    import jinja2
    from tests.test_risk_radar_dlg_partial import _RD

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")), autoescape=False,
    )
    tpl = env.from_string(
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg(mkt, rd, none, ctx) }}"
    )
    html = tpl.render(
        mkt="cn", rd=_RD,
        ctx={"title_en": "China Risk Radar", "title_zh": "中国风险雷达",
             "pullback_view": view},
    )
    dialog = BeautifulSoup(html, "html.parser").select_one("#cnx-dlg-risk")
    assert dialog is not None
    age = dialog.select_one('[data-metric="age"]')
    assert age is not None
    return age


def _lines(age) -> tuple[str, str]:
    """Number plus the template's following space, then each language span."""
    prefix = str(age.contents[0])
    return (
        prefix + age.select_one(".l-en").get_text(),
        prefix + age.select_one(".l-zh").get_text(),
    )


def test_owner_admits_one_observed_close_on_the_smallest_series():
    """62 flat 100.0 closes and one 95.0 close is the shortest count of 1."""
    flat = RULES.reference_closes - 1
    shock = _owner(flat, [95.0])
    assert shock["observed_closes_since_onset"] == 1
    assert shock["phase"] == "underway" and shock["active"] is True
    assert len(_rows(flat, [95.0], _weekday, _END)) == RULES.reference_closes

    shorter = _owner(flat - 1, [95.0])
    assert shorter.get("observed_closes_since_onset") is None
    assert shorter["quality"] == "insufficient_history"

    mild = _owner(flat, [95.1])
    assert mild["observed_closes_since_onset"] is None
    assert mild["phase"] == "developing"

    single_onset = _owner(flat, [98.0])
    assert single_onset["observed_closes_since_onset"] is None
    assert single_onset["phase"] == "developing"

    two = _owner(flat, [98.0, 98.0])
    assert two["observed_closes_since_onset"] == 1
    assert len(_rows(flat, [98.0, 98.0], _weekday, _END)) == RULES.reference_closes + 1


def test_us_popup_prints_one_observed_close():
    """The US dlg-risk popup prints the singular English line and the Chinese line."""
    obs, view = _product("us", [95.0])
    assert obs["observed_closes_since_onset"] == 1
    en, zh = _lines(_us_popup_age(view))
    assert en == _SINGULAR_EN
    assert zh == _SINGULAR_ZH


def test_cn_dialog_prints_one_observed_close():
    """The China shared dialog prints the same singular lines."""
    obs, view = _product("cn", [95.0])
    assert obs["observed_closes_since_onset"] == 1
    en, zh = _lines(_cn_dialog_age(view))
    assert en == _SINGULAR_EN
    assert zh == _SINGULAR_ZH


def test_two_observed_closes_print_closes():
    """One more close after the shock prints the plural in both shells."""
    for market, render in (("us", _us_popup_age), ("cn", _cn_dialog_age)):
        obs, view = _product(market, [95.0, 94.0])
        assert obs["observed_closes_since_onset"] == 2
        en, zh = _lines(render(view))
        assert en == _PLURAL_EN
        assert zh == "2 个已观测收盘（自回撤确认起）"
