"""The pullback chart's accessible name follows the visible language.

The shared renderer emits one English aria-label. On an underway view the
fragment wraps that figure in role=img. The name is one clipped span that
holds .l-en and .l-zh. The page hides the other language with display:none.
Chromium keeps a display:none node in the name when aria-labelledby points
at that node, and drops it when the node is only a child of the labelledby
target, so the target is the parent. The figure stays inside
.rrp-chart[aria-hidden=true]: its own English label is not a second name.
The Chinese text is the presenter's aria_zh for this same observation.
No forecast is produced.

Synthetic observations only, the ones the dialog suites already build.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from lib.pullback_depth import chart_accessible_names
from tests.test_pullback_depth_a11y import EVIDENCE, RAW_PATH, _observation
from tests.test_risk_radar_pullback_depth_template import native_view, render

# Words the no-forecast invariant already forbids in rendered pullback copy.
_FORBIDDEN = (
    "probability", "probable", "odds", "forecast", "quantile",
    "概率", "可能性", "预计", "预期", "预测", "目标价", "见底", "抄底",
)


def _underway(market):
    view = _observation(market, "underway", path=RAW_PATH, **EVIDENCE)
    return view, BeautifulSoup(render(view, market), "html.parser")


def _name_root(soup):
    return soup.select_one('[role="img"][aria-labelledby]')


def test_chart_accessible_names_passes_the_pair_through_and_refuses_a_blank():
    assert chart_accessible_names("Observed drawdown", "已观测回撤") == (
        "Observed drawdown", "已观测回撤")
    assert chart_accessible_names("", "已观测回撤") is None
    assert chart_accessible_names("Observed drawdown", "") is None
    assert chart_accessible_names(None, "已观测回撤") is None
    assert chart_accessible_names("Observed drawdown", None) is None


def test_underway_chart_is_named_in_both_languages_for_each_market():
    """US and CN dialogs both render this fragment. Each market gets its own ids."""
    seen = {}
    for market in ("us", "cn"):
        view, soup = _underway(market)
        root = _name_root(soup)
        assert root is not None, market
        name_id = root.get("aria-labelledby")
        assert name_id == f"{market}-rrp-chart-name"
        name = soup.find(id=name_id)
        assert name is not None and name.parent is root
        # The labelledby target is clipped, not display:none. The language
        # spans are its children, so the hidden language is not a direct target.
        style = name.get("style") or ""
        assert "display" not in style
        assert "clip:rect(0,0,0,0)" in style
        en, zh = name.select_one(".l-en"), name.select_one(".l-zh")
        assert en is not None and zh is not None
        assert en.get("style") is None and zh.get("style") is None
        en_text, zh_text = en.get_text(), zh.get_text()
        assert en_text == view["chart_label_en"]
        assert zh_text == view["chart_label_zh"]
        assert en_text != zh_text
        # Same numbers as the English label: the Chinese line adds none.
        en_figures = [ch for ch in en_text if ch.isdigit() or ch == "%"]
        zh_figures = [ch for ch in zh_text if ch.isdigit() or ch == "%"]
        assert zh_figures == en_figures
        blob = f"{en_text}\n{zh_text}".lower()
        for word in _FORBIDDEN:
            assert word not in blob
        seen[market] = (name_id, en_text, zh_text)
    assert seen["us"][0] != seen["cn"][0]
    assert seen["us"][1] != seen["cn"][1]
    assert "SPY" in seen["us"][1] and "Shanghai Composite" in seen["cn"][1]
    assert "参考高点" in seen["us"][2] and "参考高点" in seen["cn"][2]


def test_english_figure_label_is_hidden_so_it_is_not_read_twice():
    for market in ("us", "cn"):
        view, soup = _underway(market)
        root = _name_root(soup)
        holder = root.select_one(".rrp-chart")
        assert holder is not None
        assert holder.get("aria-hidden") == "true"
        figure = holder.find("figure")
        assert figure is not None
        assert "img" in (figure.get("role") or "").split()
        # The figure keeps the renderer's English name; the wrapper does not use it.
        assert figure.get("aria-label") == view["chart_label_en"]
        assert figure.get("aria-label") not in (root.get("aria-label") or "")
        svg = figure.find("svg")
        assert svg is not None and svg.get("aria-hidden") == "true"
        # The visible caption stays outside the hidden chart.
        caption = soup.select_one(".rrp-chart-caption")
        assert caption is not None and caption.find_parent(attrs={"aria-hidden": "true"}) is None


def test_a_chart_without_presenter_labels_does_not_invent_a_chinese_name():
    soup = BeautifulSoup(render(native_view("us"), "us"), "html.parser")
    assert _name_root(soup) is None
    assert soup.select_one('.rrp-chart[aria-hidden="true"]') is not None
