"""Hide the pre-pullback odds block while a measured pullback leads the US popup.

The China card cannot see the dialog's ``_pb_active`` flag: the dialog imports
the card without context and sets the flag inside its own macro. Hong Kong and
Canada dialogs keep the shared odds block.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from tests.test_cn_pullback_dialog_integration import _render as render_country
from tests.test_macro_risk_dialog import _dlg, _render, _vm
from tests.test_risk_radar_pullback_depth_template import native_view

NOTICE_EN = "Pre-pullback odds are not shown while a measured pullback is underway."
NOTICE_ZH = "回撤进行中，不显示回撤前的概率。"
# The measured section's method sentence. It is not the legacy odds block, and
# this lane does not own the fragment that prints it.
METHOD_ZH = "风险水平与现有回撤概率并非对剩余跌幅的预测。"


def _us_dialog(view=None) -> str:
    vm = _vm()
    if view is not None:
        vm["us_pullback_view"] = view
    return _dlg(_render(vm=vm, mode="macro"))


def _monitoring(market: str) -> dict:
    view = native_view(market)
    view["phase"] = "monitoring"
    view["observation"]["phase"] = "monitoring"
    view["observation"]["active"] = False
    return view


def _rejected(market: str) -> dict:
    view = native_view(market)
    view["observation"]["quality"] = "delayed"
    return view


def test_us_leading_hides_the_legacy_odds_block():
    html = _us_dialog(native_view("us"))
    assert 'class="riskdlg-odds"' not in html
    assert "riskdlg-odds" not in html.replace("riskdlg-odds-k", "")
    assert "Pullback odds" not in html
    # The caption class is the one reused line. It is not the odds block.
    assert html.count('class="riskdlg-odds-k"') == 1
    assert NOTICE_EN in html and NOTICE_ZH in html
    soup = BeautifulSoup(html, "html.parser")
    measured = soup.select_one("section.rrp")
    assert measured is not None and METHOD_ZH in measured.get_text()
    measured.decompose()
    rest = str(soup)
    assert "回撤概率" not in rest
    disclosure = soup.select_one("details.riskdlg-legacy-details")
    assert disclosure is not None
    assert NOTICE_EN in disclosure.get_text()
    assert "riskdlg-odds-h" not in str(disclosure)
    assert "riskdlg-odds-rail" not in str(disclosure)


def test_us_not_leading_keeps_the_legacy_odds_block():
    rejected = _rejected("us")
    pre = _monitoring("us")
    for view in (None, rejected, pre):
        html = _us_dialog(view)
        assert 'class="riskdlg-odds"' in html
        assert "Pullback odds" in html
        assert "回撤概率 ≥5%" in html
        assert NOTICE_EN not in html
        assert NOTICE_ZH not in html
        assert "riskdlg-odds-h" in html
        assert "riskdlg-odds-rail" in html


def test_hk_and_ca_dialogs_keep_the_shared_odds_block():
    for market in ("hk", "ca"):
        leading_cn = render_country(native_view("cn"), market)
        plain = render_country(None, market)
        assert leading_cn == plain
        assert 'class="rrx-odds"' in plain
        assert "Pullback odds" in plain
        assert NOTICE_EN not in plain
