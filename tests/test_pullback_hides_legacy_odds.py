"""Hide the forward pullback odds while a measured pullback leads a popup.

US: the dialog swaps its ``.riskdlg-odds`` block for one line. China: the dialog
passes ``hide_odds`` to the shared radar card, which swaps its odds block for the
same line and drops the recovery panel's odds trace, odds turn and odds edge.
The panel's headline and central-bank catalysts stay. Every other caller of the
card omits the flag: Hong Kong, Canada and the US front-page banner are unchanged.
"""
from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from tests.test_cn_pullback_dialog_integration import ROOT
from tests.test_dashboard_template_render import _env as _site_env
from tests.test_macro_risk_dialog import _dlg, _render, _vm
from tests.test_risk_radar_dlg_partial import _RD
from tests.test_risk_radar_pullback_depth_template import native_view

NOTICE_EN = "Forward pullback odds are not shown during a measured pullback."
NOTICE_ZH = "实测回撤期间，不显示回撤前的概率。"
# The measured section's method sentence. It is not the legacy odds block, and
# this lane does not own the fragment that prints it.
METHOD_ZH = "风险水平与现有回撤概率并非对剩余跌幅的预测。"

# Shape of engine/risk_radar_recovery.py's present payload, receding branch. The
# sub-line uses the engine's own odds-turn wording; the salience line stands in
# for the fed_netliq catalyst's measured odds edge.
SUB_EN = "Pullback odds 31% → 24% (peaked 3 days ago)."
SUB_ZH = "回撤概率 31% → 24%（3 日前见顶）。"
EDGE_EN = "buying dips has historically worked ~6pp more often (synthetic)"
EDGE_ZH = "逢低买入成功率约高6个百分点（合成）"
RECOVERY = {
    "present": True, "phase": "receding", "receding": True, "peaking": False,
    "turn_confirmed": False, "turn_confirmed_full": False,
    "headline_en": "Risk receding — pullback odds rolling over",
    "headline_zh": "风险回落 — 回撤概率见顶回落",
    "sub_en": SUB_EN, "sub_zh": SUB_ZH, "caveat_en": "Illustrative context.", "caveat_zh": "仅为示意性背景。",
    "spark_pts": "0,10 5,2 10,6", "spark_w": 10, "spark_h": 12,
    "spark_peak": {"x": 5, "y": 2}, "spark_last": {"x": 10, "y": 6},
    "catalysts": [{
        "key": "fed_netliq", "icon": "$", "region": "US", "fresh": True,
        "label_en": "Fed liquidity expanding", "label_zh": "美联储流动性扩张",
        "detail_en": "Net liquidity rising.", "detail_zh": "净流动性上升。",
        "salience_en": EDGE_EN, "salience_zh": EDGE_ZH,
    }],
}


def _us_dialog(view=None) -> str:
    vm = _vm()
    if view is not None:
        vm["us_pullback_view"] = view
    return _dlg(_render(vm=vm, mode="macro"))


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)


def _country(view=None, mkt="cn", recovery=None) -> str:
    tpl = _env().from_string(
        '{% import "_risk_radar_dlg.html.j2" as rrd %}'
        "{{ rrd.risk_radar_dlg(mkt, rd, none, ctx) }}"
    )
    ctx = {"title_en": "China Risk Radar", "title_zh": "中国风险雷达"}
    if view is not None:
        ctx["pullback_view"] = view
    return tpl.render(mkt=mkt, rd=dict(_RD, recovery=recovery), ctx=ctx)


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


def _outside_measured(html: str) -> tuple[BeautifulSoup, str]:
    soup = BeautifulSoup(html, "html.parser")
    measured = soup.select_one("section.rrp")
    assert measured is not None
    measured.decompose()
    return soup, str(soup)


def test_us_leading_hides_the_legacy_odds_block():
    html = _us_dialog(native_view("us"))
    assert 'class="riskdlg-odds"' not in html
    assert "riskdlg-odds" not in html.replace("riskdlg-odds-k", "")
    assert "Pullback odds" not in html
    # The caption class is the one reused line. It is not the odds block.
    assert html.count('class="riskdlg-odds-k"') == 1
    assert NOTICE_EN in html and NOTICE_ZH in html
    soup = BeautifulSoup(html, "html.parser")
    assert METHOD_ZH in soup.select_one("section.rrp").get_text()
    soup, rest = _outside_measured(html)
    assert "回撤概率" not in rest
    disclosure = soup.select_one("details.riskdlg-legacy-details")
    assert disclosure is not None
    assert NOTICE_EN in disclosure.get_text()
    assert "riskdlg-odds-h" not in str(disclosure)
    assert "riskdlg-odds-rail" not in str(disclosure)


def test_us_not_leading_keeps_the_legacy_odds_block():
    for view in (None, _rejected("us"), _monitoring("us")):
        html = _us_dialog(view)
        assert 'class="riskdlg-odds"' in html
        assert "Pullback odds" in html
        assert "回撤概率 ≥5%" in html
        assert NOTICE_EN not in html
        assert NOTICE_ZH not in html
        assert "riskdlg-odds-h" in html
        assert "riskdlg-odds-rail" in html


def test_us_leading_leaves_out_the_risk_workspace():
    # The workspace hero prints the forward odds, so a measured pullback keeps
    # its data and template out. Its script then has nothing to mount.
    html = _us_dialog(native_view("us"))
    assert 'id="risk-radar-workspace-data"' not in html
    assert 'id="risk-radar-workspace-template"' not in html
    assert "rkw-odds" not in html
    assert NOTICE_EN in html


def test_us_not_leading_keeps_the_risk_workspace_unchanged():
    vm = _vm()
    workspace = _site_env().get_template("_risk_radar_workspace.html.j2").render(**vm, mode="macro")
    assert 'id="risk-radar-workspace-data"' in workspace
    for view in (None, _rejected("us"), _monitoring("us")):
        html = _us_dialog(view)
        assert html.count(workspace) == 1
        assert NOTICE_EN not in html


def test_cn_leading_hides_the_card_odds_block():
    html = _country(native_view("cn"))
    assert 'class="rrx-odds"' not in html
    assert "rrx-odds-l" not in html and "rrx-cap-sub" not in html
    assert "1.35×" not in html
    soup, rest = _outside_measured(html)
    assert "Pullback odds" not in rest and "回撤概率" not in rest
    disclosure = soup.select_one("details.riskdlg-legacy-details")
    notice = disclosure.select_one(".rrx-odds-off")
    assert notice is not None
    assert NOTICE_EN in notice.get_text() and NOTICE_ZH in notice.get_text()
    assert len(soup.select(".rrx-odds-off")) == 1


def test_cn_leading_drops_the_recovery_odds_and_keeps_its_catalysts():
    html = _country(native_view("cn"), recovery=RECOVERY)
    soup, rest = _outside_measured(html)
    panel = soup.select_one(".rrx-rec")
    assert panel is not None and panel.find_parent("details", class_="riskdlg-legacy-details")
    assert panel.select_one(".rrx-rec-mid") is None
    assert panel.select_one(".rrx-rec-spark") is None
    assert panel.select_one(".rrx-rec-sal") is None
    for text in (SUB_EN, SUB_ZH, EDGE_EN, EDGE_ZH, "31%"):
        assert text not in rest
    chips = panel.select(".rrx-rec-chip")
    assert len(chips) == 1 and "Fed liquidity expanding" in chips[0].get_text()
    # The engine headline names the odds direction without a figure. It stays.
    assert "Risk receding" in panel.select_one(".rrx-rec-ttl").get_text()


@pytest.mark.parametrize("view", [None, "rejected", "monitoring"])
def test_cn_not_leading_keeps_the_odds_and_the_recovery_odds(view):
    v = {"rejected": _rejected("cn"), "monitoring": _monitoring("cn")}.get(view)
    html = _country(v, recovery=RECOVERY)
    assert "riskdlg-legacy-details" not in html
    assert 'class="rrx-odds"' in html and "Pullback odds" in html
    assert 'class="rrx-rec-mid"' in html and 'class="rrx-rec-sal"' in html
    for text in (SUB_EN, SUB_ZH, EDGE_EN, EDGE_ZH):
        assert text in html
    assert NOTICE_EN not in html and NOTICE_ZH not in html
    assert "rrx-odds-off" not in html


@pytest.mark.parametrize("mkt", ["hk", "ca"])
@pytest.mark.parametrize("recovery", [None, RECOVERY])
def test_hk_and_ca_dialogs_keep_the_shared_odds_block(mkt, recovery):
    leading_cn = _country(native_view("cn"), mkt, recovery)
    plain = _country(None, mkt, recovery)
    assert leading_cn == plain
    assert 'class="rrx-odds"' in plain and "Pullback odds" in plain
    assert NOTICE_EN not in plain and "rrx-odds-off" not in plain
    if recovery:
        assert SUB_EN in plain and EDGE_EN in plain


def test_card_callers_that_omit_the_flag_keep_the_odds():
    tpl = _env().from_string(
        '{% import "_risk_radar_card.html.j2" as rrc %}'
        "{{ rrc.risk_radar_card(rd, []) }}|{{ rrc.risk_radar_card(rd, [], hide_odds=false) }}"
    )
    default, explicit = tpl.render(rd=dict(_RD, recovery=RECOVERY)).split("|", 1)
    assert default == explicit
    assert 'class="rrx-odds"' in default and SUB_EN in default and EDGE_EN in default
    assert NOTICE_EN not in default


def test_card_without_odds_prints_no_notice():
    rd = dict(_RD, dd21=None)
    html = _env().from_string(
        '{% import "_risk_radar_card.html.j2" as rrc %}{{ rrc.risk_radar_card(rd, [], hide_odds=true) }}'
    ).render(rd=rd)
    assert "rrx-odds" not in html and NOTICE_EN not in html
