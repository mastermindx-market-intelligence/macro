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


_DETERIORATION = "Deterioration: no repair evidence yet"
_EARLY = "Pullback still active: early repair signs are not confirmed"
_LABEL_EN = "Portion of the high-to-low drop regained"
_LABEL_ZH = "高点到低点的跌幅中已收回的比例"
_SUB_EN = (
    "A rebound alone does not confirm recovery; that takes closes back at or "
    "above the reference high."
)
_SUB_ZH = "仅有价格回升不足以确认修复；需收盘价重回参考高点或以上。"


def _verdict_en(view, market):
    soup = BeautifulSoup(render(view, market), "html.parser")
    node = soup.select_one('[data-signal="verdict"] .l-en')
    assert node is not None
    return node.get_text(), soup


@pytest.mark.parametrize("market", ["cn", "us"])
def test_f1_verdict_follows_the_printed_recovered_share(market):
    """0.3 prints 0% and is not early repair. 0.6 prints 1% and is.

    Both rows have no closes holding the low, so only the printed share decides.
    """
    zero = native_view(market)
    zero["observation"]["no_new_low_closes"] = 0
    zero["observation"]["loss_recovered_pct"] = 0.3
    verdict, soup = _verdict_en(zero, market)
    printed = soup.select_one('[data-signal="recovered"]').find_next_sibling("dd")
    assert printed.get_text(strip=True) == "0%"
    assert verdict == _DETERIORATION

    one = native_view(market)
    one["observation"]["no_new_low_closes"] = 0
    one["observation"]["loss_recovered_pct"] = 0.6
    verdict, soup = _verdict_en(one, market)
    printed = soup.select_one('[data-signal="recovered"]').find_next_sibling("dd")
    assert printed.get_text(strip=True) == "1%"
    assert verdict == _EARLY


@pytest.mark.parametrize("market", ["cn", "us"])
def test_f2_recovered_row_names_the_high_to_low_drop(market):
    """The recovered row keeps its signal and uses the high-to-low wording."""
    soup = BeautifulSoup(render(native_view(market), market), "html.parser")
    label = soup.select_one('[data-signal="recovered"]')
    assert label.select_one(".l-en").get_text() == _LABEL_EN
    assert label.select_one(".l-zh").get_text() == _LABEL_ZH
    assert "Share of the loss retraced" not in soup.get_text()
    assert "已收复跌幅比例" not in soup.get_text()


@pytest.mark.parametrize("market", ["cn", "us"])
def test_f3_current_subline_requires_closes_at_the_reference_high(market):
    """Only a current view uses the rebound sentence, and that sentence has no cutoff."""
    soup = BeautifulSoup(render(native_view(market), market), "html.parser")
    _span(soup, _SUB_EN, _SUB_ZH)
    sub = soup.select_one(".rrp-sub").get_text()
    assert not any(ch.isdigit() for ch in sub)
    assert "Watch the retest of the low" not in soup.get_text()
    assert "观察低点回踩" not in soup.get_text()

    delayed = native_view(market)
    delayed["observation"]["quality"] = "delayed"
    delayed_soup = BeautifulSoup(render(delayed, market), "html.parser")
    _span(
        delayed_soup,
        "A current closing-price assessment is not available.",
        "当前收盘价评估暂不可用。",
    )
    assert _SUB_EN not in delayed_soup.get_text()
    assert _SUB_ZH not in delayed_soup.get_text()


@pytest.mark.parametrize("market", ["cn", "us"])
def test_f5_monitoring_close_at_the_peak_still_renders_metrics(market):
    """A monitoring close on the retained high is a new high and stays current.

    An underway close on that high is contradictory. test_e4_close_equal_to_the_peak_is_unavailable_unless_repairing
    already pins that half.
    """
    view = _phase_view(market, "monitoring", False)
    view["observation"]["close"] = view["observation"]["peak_close"]
    html = render(view, market)
    assert 'data-pb-phase="monitoring"' in html
    assert 'class="rrp-metrics"' in html
    assert 'data-metric="current"' in html
