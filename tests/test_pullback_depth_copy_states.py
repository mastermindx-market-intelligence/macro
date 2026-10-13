"""Copy rules for the measured pullback section.

Observations are built with lib.pullback_observation.observe() on synthetic
weekday closes, then rendered through the US and CN adapters' present().
Nothing here is a market print or a downside estimate.
"""
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from lib import cn_pullback_observation as cn_adapter
from lib import us_pullback_observation as us_adapter
from lib.pullback_observation import observe

ROOT = Path(__file__).resolve().parents[1]
_DETAIL = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    autoescape=False,
).from_string(
    '{% import "_risk_radar_pullback_depth.html.j2" as p %}'
    "{{ p.detail(market, v) }}"
)

EARLY_EN = "Pullback still active: early repair signs are not confirmed"
EARLY_ZH = "回撤仍在进行：初步修复迹象尚未确认"
DETERIORATION_EN = "Deterioration: no repair evidence yet"
DETERIORATION_ZH = "恶化：尚无修复证据"
REPAIR_EN = "Repair evidence building; not a confirmed recovery"
REPAIR_ZH = "修复证据增加中，尚未确认修复"
ABOVE_EN = "Above the reference high"
ABOVE_ZH = "高于参考高点"
FROM_EN = "From the reference high"
FROM_ZH = "距参考高点"


def session(day):
    return day.weekday() < 5


def weekday_closes(values, start=date(2025, 1, 2)):
    """Map a price list onto weekdays, as test_pullback_scenario_replay does."""
    day = start
    rows = []
    for value in values:
        while not session(day):
            day += timedelta(days=1)
        rows.append((day.isoformat(), float(value)))
        day += timedelta(days=1)
    return rows


def observe_series(values):
    rows = weekday_closes(values)
    read = observe(
        rows,
        expected_session=date.fromisoformat(rows[-1][0]),
        is_session=session,
    )
    assert read["available"] is True and read["quality"] == "current", read.get("quality")
    return read


def render_read(read, market):
    stamped = dict(
        read,
        market=market,
        clock="settled_close",
        valid_until="2026-12-31T21:00:00+00:00",
    )
    adapter = us_adapter if market == "us" else cn_adapter
    view = adapter.present(stamped)
    return _DETAIL.render(market=market, v=view)


def soup_of(read, market):
    return BeautifulSoup(render_read(read, market), "html.parser")


def verdict_pair(soup):
    node = soup.select_one('[data-signal="verdict"]')
    assert node is not None
    return node.select_one(".l-en").get_text(), node.select_one(".l-zh").get_text()


def test_b1_underway_with_repair_evidence_does_not_claim_no_repair():
    read = observe_series([100] * 70 + [90, 94, 96])
    assert read["phase"] == "underway" and read["active"] is True
    assert read["loss_recovered_pct"] == 60.0
    assert read["no_new_low_closes"] == 2
    for market in ("us", "cn"):
        en, zh = verdict_pair(soup_of(read, market))
        assert en == EARLY_EN
        assert zh == EARLY_ZH
        assert DETERIORATION_EN not in soup_of(read, market).get_text()
        assert DETERIORATION_ZH not in soup_of(read, market).get_text()


def test_b1_underway_without_repair_evidence_keeps_the_deterioration_verdict():
    read = observe_series([100] * 70 + [90])
    assert read["phase"] == "underway" and read["active"] is True
    assert read["no_new_low_closes"] == 0
    assert read["loss_recovered_pct"] == 0.0
    for market in ("us", "cn"):
        en, zh = verdict_pair(soup_of(read, market))
        assert en == DETERIORATION_EN
        assert zh == DETERIORATION_ZH
        assert EARLY_EN not in soup_of(read, market).get_text()


def test_b2_close_above_the_reference_high_reads_as_above():
    read = observe_series([100] * 70 + [90, 101])
    assert read["phase"] == "recovering" and read["active"] is True
    assert read["close"] == 101.0 and read["peak_close"] == 100.0
    for market in ("us", "cn"):
        soup = soup_of(read, market)
        label = soup.select_one(".rrp-metrics .rrp-label")
        assert label.select_one(".l-en").get_text() == ABOVE_EN
        assert label.select_one(".l-zh").get_text() == ABOVE_ZH
        value = soup.select_one('[data-metric="current"]')
        assert value is not None
        assert value.get_text(strip=True) == "+1.0%"
        assert "−" not in value.get_text()
        en, zh = verdict_pair(soup)
        assert en == REPAIR_EN and zh == REPAIR_ZH


def _after_settled_close(soup):
    """The node or text that follows the settled-close label."""
    label = None
    for node in soup.select(".rrp-stamp .l-zh"):
        if node.get_text() == "收盘价":
            label = node
            break
    assert label is not None
    sibling = label.next_sibling
    while isinstance(sibling, str) and not sibling.strip():
        sibling = sibling.next_sibling
    return sibling


def test_c1_settled_close_is_a_time_only_when_asof_is_present():
    read = observe_series([100] * 70 + [90, 94, 96])
    assert read["asof"]
    for market in ("us", "cn"):
        held = _after_settled_close(soup_of(read, market))
        assert getattr(held, "name", None) == "time"
        assert held.get("datetime") == read["asof"]
        assert held.get_text(strip=True) == read["asof"]
        for blank in (None, ""):
            cleared = dict(read, asof=blank)
            soup = soup_of(cleared, market)
            held = _after_settled_close(soup)
            text = held.strip() if isinstance(held, str) else held.get_text(strip=True)
            assert text == "—"
            assert getattr(held, "name", None) != "time"
            assert soup.select("time[datetime='']") == []


def test_b2_close_equal_to_the_reference_high_stays_zero_under_the_old_label():
    read = observe_series([100] * 70 + [90, 100])
    assert read["phase"] == "recovering" and read["close"] == read["peak_close"]
    for market in ("us", "cn"):
        soup = soup_of(read, market)
        label = soup.select_one(".rrp-metrics .rrp-label")
        assert label.select_one(".l-en").get_text() == FROM_EN
        assert label.select_one(".l-zh").get_text() == FROM_ZH
        assert soup.select_one('[data-metric="current"]').get_text(strip=True) == "0.0%"
