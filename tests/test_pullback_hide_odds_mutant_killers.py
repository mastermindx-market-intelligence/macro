"""Kill the mutants the hide-odds suite cannot see.

Three mutants survived tests/test_pullback_hides_legacy_odds.py: swapping the
two arguments of either notice's ``t()`` call (the twin markup keeps every
literal present, so text-presence asserts pass while English readers get the
Chinese sentence), and one added space inside the card's unhidden odds block
(the HK/CA pin compares two live renders, so an identical mutation stays
"equal"). These pins hold the survivors: each language in its own span, and
the exact opening bytes every caller that omits ``hide_odds`` inherits.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from tests.test_pullback_hides_legacy_odds import (
    NOTICE_EN,
    NOTICE_ZH,
    _country,
    _env,
    _us_dialog,
)
from tests.test_risk_radar_dlg_partial import _RD
from tests.test_risk_radar_pullback_depth_template import native_view


def test_cn_notice_puts_each_language_in_its_own_span():
    html = _country(native_view("cn"))
    notice = BeautifulSoup(html, "html.parser").select_one(".rrx-odds-off")
    assert notice is not None
    assert notice.select_one(".l-en").get_text() == NOTICE_EN
    assert notice.select_one(".l-zh").get_text() == NOTICE_ZH


def test_us_notice_puts_each_language_in_its_own_span():
    html = _us_dialog(native_view("us"))
    notice = BeautifulSoup(html, "html.parser").select_one(".riskdlg-odds-k")
    assert notice is not None
    assert notice.select_one(".l-en").get_text() == NOTICE_EN
    assert notice.select_one(".l-zh").get_text() == NOTICE_ZH


def test_unhidden_odds_block_keeps_its_exact_opening_bytes():
    html = _env().from_string(
        '{% import "_risk_radar_card.html.j2" as rrc %}{{ rrc.risk_radar_card(rd, []) }}'
    ).render(rd=dict(_RD))
    opening = html[html.index('<div class="rrx-odds">'):]
    assert opening.startswith('<div class="rrx-odds">\n    <div class="rrx-odds-l">')
