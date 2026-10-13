"""Pullback fragment copy and the close-at-peak price gate.

Synthetic observations only. Reuses the fragment render helpers. No forecast
figure is produced or asserted.
"""
import pytest
from bs4 import BeautifulSoup

from tests.test_risk_radar_pullback_depth_template import native_view, render

STAMP = "2026-10-01T09:00:00+00:00"
OLD_CHART_EN = "The chart needs current, usable price evidence."
OLD_CHART_ZH = "图表需要当前且可用的价格数据。"
OLD_UNCOVERED_ZH = "图表不显示：现有收盘历史无法完整支持上述数据。"
NEW_CHART_EN = "A chart appears once current, usable price data is on record."
NEW_CHART_ZH = "待有当前可用的价格数据后再显示图表。"
UNCOVERED_EN = (
    "Chart not shown: the closing history on record does not fully support these figures."
)
NEW_UNCOVERED_ZH = "暂不显示图表：现有收盘历史无法完整支持上述数据。"
OLD_STRINGS = (OLD_CHART_EN, OLD_CHART_ZH, OLD_UNCOVERED_ZH)


def _span(soup, english, chinese):
    node = soup.find("span", class_="l-en", string=english)
    assert node is not None, english
    zh = node.find_next_sibling("span")
    assert zh is not None and "l-zh" in (zh.get("class") or [])
    assert zh.get_text() == chinese


def _phase_view(market, phase, active):
    view = native_view(market)
    view["phase"] = view["observation"]["phase"] = phase
    view["observation"]["active"] = active
    if phase in ("monitoring", "developing"):
        view["observation"]["low_close"] = None
    return view


@pytest.mark.parametrize("market", ["cn", "us"])
def test_e1_current_until_renders_only_on_a_current_view(market):
    """A formattable valid_until stays on the section. The words render only when current."""
    delayed = native_view(market)
    delayed["observation"]["quality"] = "delayed"
    delayed_html = render(delayed, market)
    assert f'data-pb-valid-until="{STAMP}"' in delayed_html
    assert "Current until" not in delayed_html and "有效至" not in delayed_html

    unavailable = native_view(market)
    unavailable["observation"]["available"] = False
    unavailable_html = render(unavailable, market)
    assert f'data-pb-valid-until="{STAMP}"' in unavailable_html
    assert "Current until" not in unavailable_html and "有效至" not in unavailable_html

    soup = BeautifulSoup(render(native_view(market), market), "html.parser")
    stamp = soup.select_one(".rrp-stamp")
    assert "Current until" in stamp.get_text() and "有效至" in stamp.get_text()
    clocks = [node for node in stamp.select("time") if node.get("datetime") == STAMP]
    assert len(clocks) == 1
    assert clocks[0].get_text(strip=True) == "2026-10-01 09:00 UTC+00:00"


@pytest.mark.parametrize("market", ["cn", "us"])
def test_e2_e3_chart_sentences_replace_the_old_copy(market):
    """Unqualified views use the new chart sentence. Uncovered history uses the new Chinese."""
    delayed = native_view(market)
    delayed["observation"]["quality"] = "delayed"
    unavailable = native_view(market)
    unavailable["observation"]["available"] = False
    uncovered = native_view(market)
    uncovered["detail_chart_html"] = ""
    uncovered["detail_withheld"] = "uncovered"
    short = native_view(market)
    short["detail_chart_html"] = ""
    short["detail_withheld"] = "short"
    neutral = native_view(market)
    neutral["detail_chart_html"] = ""
    phases = [
        _phase_view(market, phase, active)
        for phase, active in (
            ("monitoring", False),
            ("developing", False),
            ("underway", True),
            ("stabilizing", True),
            ("recovering", True),
            ("repaired", False),
        )
    ]
    views = (
        delayed,
        unavailable,
        uncovered,
        short,
        neutral,
        native_view(market),
        None,
        {},
        *phases,
    )
    for view in views:
        html = render(view, market)
        for old in OLD_STRINGS:
            assert old not in html, old

    for view in (delayed, unavailable, None, {}):
        soup = BeautifulSoup(render(view, market), "html.parser")
        assert soup.select_one("section.rrp").get("data-pb-phase") == "unavailable"
        _span(soup, NEW_CHART_EN, NEW_CHART_ZH)

    uncovered_html = render(uncovered, market)
    _span(BeautifulSoup(uncovered_html, "html.parser"), UNCOVERED_EN, NEW_UNCOVERED_ZH)
    assert NEW_CHART_EN not in uncovered_html

    current_html = render(native_view(market), market)
    assert NEW_CHART_EN not in current_html and NEW_CHART_ZH not in current_html
    assert NEW_UNCOVERED_ZH not in current_html


@pytest.mark.parametrize("market", ["cn", "us"])
def test_e4_close_equal_to_the_peak_is_unavailable_unless_repairing(market):
    """An underway close on the retained high is contradictory. A repairing close at that high still renders."""
    underway_equal = native_view(market)
    underway_equal["observation"]["close"] = underway_equal["observation"]["peak_close"]
    equal_html = render(underway_equal, market)
    assert 'data-pb-phase="unavailable"' in equal_html
    assert 'class="rrp-metrics"' not in equal_html
    assert 'data-metric="current"' not in equal_html

    recovering = native_view(market)
    recovering["phase"] = recovering["observation"]["phase"] = "recovering"
    recovering["observation"]["active"] = True
    recovering["observation"]["close"] = recovering["observation"]["peak_close"]
    recovering_html = render(recovering, market)
    assert 'data-pb-phase="recovering"' in recovering_html
    assert 'class="rrp-metrics"' in recovering_html
    assert 'data-metric="current"' in recovering_html

    below = native_view(market)
    below["observation"]["peak_close"] = 100.0
    below["observation"]["close"] = 99.9
    below["observation"]["low_close"] = 92.6
    below_html = render(below, market)
    assert 'data-pb-phase="underway"' in below_html
    assert 'class="rrp-metrics"' in below_html
    assert 'data-metric="current"' in below_html
