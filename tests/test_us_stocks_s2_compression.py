"""us_stocks L1 compression + Tier-1 hygiene (S2 frozen spec §0 gates).

Cites research/… no: the frozen spec at
handoffs/.../spec_us_stocks_compression.md §0 / §1–§4.
Rewrites any pre-S2 10-panel pin: the page is header + 7 L1 after the fold
and two demotions. #prophet-live stays hidden and is not an L1 section.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine import i18n
from tests.test_dashboard_template_render import _base_vm, _env
from tests.test_mag7_tape_strip import EVENTS, LATEST, STANDOUTS

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"

L1_IDS = (
    "action-board",
    "us-standouts",
    "dash-tape-band",
    "equity-scoreboard",
    "sectors",
    "dash-mtf-section",
    "holdings",
)


def _stocks(**over) -> str:
    vm = dict(_base_vm())
    vm.update(over)
    return _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


def _hold_row(i: int) -> dict:
    return {
        "fund": f"ARKK", "ticker": f"T{i:02d}", "name": f"Name {i}",
        "sector": "Uranium", "weight_pct": 1.0, "conviction_pp": 0.5,
        "ladder": None, "window": "2026-09-01..2026-09-08",
    }


def _sector_row(**over) -> dict:
    r = {
        "ticker": "XLK", "state": "BUY", "side": "buy",
        "label": "BUY", "label_zh": "买入", "verdict": "BUY",
        "action_txt": "act", "signal_txt": "no fresh cross",
        "conv_dots": "●", "conv_txt": "high", "color": "#00bfff",
        "priority": 1, "tech_str": "✓200d ✓50d", "tech_ok": True,
        "osc_str": "RSI 42 · Stoch 6", "rs_60d": 0.4, "rs_str": "+0.4%",
        "season_str": "-1.1% (50%)", "season_magnitude": "-1.1%",
        "season_tip": "<table></table>",
        "rate_str": "+0.4% vs SPY · 50% up · n=1295",
        "rate_pos": True, "href": "sectors/XLK.html",
        "name": "Information Technology",
        "above200": True, "above50": True, "conviction": 3,
        "two_reads_chip": None,
        "rsi_3d": 42.0, "stoch_3d": 6.0,
        "rate_hit": 50, "rate_n": 1295, "rate_exc": 0.4,
        "flags": {"macd_dn_3d": False, "macd_up_3d": False},
    }
    r.update(over)
    return r


def test_stocks_page_drops_folded_and_demoted_panels():
    """S2 §1.1 / §0.1: #megacap-tape is no longer a top-level panel;
    #accumulation and #theme-tape leave this page."""
    html = _stocks(sector_setups={"sectors": [_sector_row()], "n_buy": 1,
                                 "n_avoid": 0, "n_tactical": 0})
    assert 'class="panel span12" id="megacap-tape"' not in html
    assert 'id="accumulation"' not in html
    assert 'id="theme-tape"' not in html
    for pid in L1_IDS:
        assert f'id="{pid}"' in html, pid
    assert re.search(r'id="prophet-live"[^>]*hidden', html) or 'id="prophet-live" hidden' in html
    assert 'id="stocks-header"' in html


def test_action_board_header_carries_folded_strip_when_mode_stocks():
    """S2 §1.3: mode-gated include after </h2>; strip is a header, not a panel."""
    html = _stocks(latest=LATEST, us_standouts=STANDOUTS)
    ab = html[html.index('id="action-board"'):html.index('id="prophet-live"')]
    assert 'class="acb-tape"' in ab
    assert 'id="megacap-tape"' in ab
    assert 'class="panel span12" id="megacap-tape"' not in html
    assert "Theme heat &amp; reasons → Sector Intelligence" in ab
    assert "主题热度与详情 → 行业情报页" in ab
    assert 'href="sector_central.html#theme-heat-section"' in ab
    assert "Theme reasons → Sector Intelligence" not in ab


def test_mode_gate_does_not_leak_megacap_onto_sector_central_include():
    """S2 §0.4 / §1.3: shared act-now include without mode='stocks' has no tape."""
    env = _env()
    ab = {
        "total": 1, "buy_now": [], "buy_soon": [], "on_the_run": [],
        "take_profits": [], "hold": [], "avoid": [],
    }
    plain = env.get_template("_us_act_now_board.html.j2").render(
        action_board=ab, latest=LATEST, us_standouts=STANDOUTS)
    assert "Mega-cap tape" not in plain
    assert "acb-tape" not in plain
    stocks = env.get_template("_us_act_now_board.html.j2").render(
        action_board=ab, latest=LATEST, us_standouts=STANDOUTS, mode="stocks")
    assert "Mega-cap tape" in stocks
    assert "acb-tape" in stocks


def test_sector_central_landing_anchors_exist_and_l1_count_unchanged():
    """S2 §1.4: demotions nest; host L1 section ids stay the same five rvx-sec."""
    src = (TPL / "sector_central.html.j2").read_text(encoding="utf-8")
    hosts = (
        'id="actnow-section"',
        'id="si-map"',
        'id="si-movement"',
        'id="internals-section"',
        'id="explore-section"',
    )
    for h in hosts:
        assert src.count(h) == 1, h
    assert 'id="accumulation-section"' in src
    assert 'id="theme-heat-section"' in src
    assert 'id="rotmap-section"' in src
    acc_span = src.index('id="accumulation-section"')
    si = src.index('id="si-movement"')
    si_close = src.index("</section>", si)
    assert si < acc_span < si_close
    th = src.index('id="theme-heat-section"')
    ex = src.index('id="explore-section"')
    ex_close = src.index("</section>", ex)
    assert ex < th < ex_close


def test_holdings_capped_at_eight_with_counted_see_all():
    """S2 §3.1 / §0.2. Label is the unsliced universe, not panel_top_n."""
    rows = [_hold_row(i) for i in range(12)]
    html = _stocks(holdings_changes=rows, holdings_universe_n=24)
    hold = html[html.index('id="holdings"'):]
    hold = hold[:hold.index("</div>", hold.index("<table>"))]
    assert hold.count("<tr>") == 9  # header + 8 data
    assert "See all 24 →" in hold
    assert "查看全部 24 项 →" in hold
    assert "See all 12 →" not in hold
    assert "no signal yet" in hold
    assert "暂无信号" in hold
    assert 'href="sector_central.html#accumulation-section"' in hold
    assert "Accumulation watch → Sector Intelligence" in hold


def test_holdings_drops_count_when_universe_unknown():
    """A wrong count is worse than none — sliced length must not publish as N."""
    html = _stocks(holdings_changes=[_hold_row(i) for i in range(12)])
    hold = html[html.index('id="holdings"'):]
    assert "Full board →" in hold
    assert "See all 12 →" not in hold


def test_holdings_full_board_when_not_capped():
    html = _stocks(holdings_changes=[_hold_row(1)], holdings_universe_n=1)
    hold = html[html.index('id="holdings"'):]
    assert "Full board →" in hold
    assert "完整看板 →" in hold
    assert "See all" not in hold.split('id="holdings"')[1][:2500]


def test_worded_nulls_and_dtp_loading_and_mtf_skeleton():
    """S2 §3.3–§3.5."""
    html = _stocks()
    tape = html[html.index('id="dash-tape-band"'):html.index('id="equity-scoreboard"')]
    assert 'dtp-token loading' in tape
    assert "checking market status" in tape
    assert "正在确认市场状态" in tape
    assert 'id="dtp-token-lbl">—' not in tape
    mtf = html[html.index('id="dash-mtf-body"'):html.index('id="holdings"')]
    assert 'class="mtf-skel"' in mtf
    assert "No stock is showing early bottoming signs tonight." in mtf
    assert 'hidden' in mtf
    assert "Loading turn setup data" not in html
    js = html[html.index("function renderMtfTable"):html.index("function tryRender")]
    assert "L('no signal yet','暂无信号')" in js
    assert "L('—','—')" not in js


def test_sectors_receipt_sweep_and_band_boundaries():
    """S2 §2 frozen presentation bands at the cutoffs, plus banned vocab gone."""
    rows = [
        _sector_row(ticker="A", stoch_3d=20, rsi_3d=42, rate_hit=54, rate_n=100,
                    rate_exc=0.1, flags={"macd_dn_3d": True, "macd_up_3d": False}),
        _sector_row(ticker="B", stoch_3d=21, rsi_3d=50, rate_hit=55, rate_n=200,
                    rate_exc=0.2, flags={"macd_dn_3d": False, "macd_up_3d": True}),
        _sector_row(ticker="C", stoch_3d=79, rsi_3d=60, rate_hit=64, rate_n=1295,
                    rate_exc=0.4, season_str="-1.1% (50%)", season_magnitude="-1.1%"),
        _sector_row(ticker="D", stoch_3d=80, rsi_3d=70, rate_hit=65, rate_n=300,
                    rate_exc=1.0),
    ]
    html = _stocks(sector_setups={"sectors": rows, "n_buy": 4, "n_avoid": 0, "n_tactical": 0})
    sec = html[html.index('id="sectors"'):html.index('id="dash-mtf-section"')]
    assert "washed out" in sec and "超卖" in sec
    assert "mid-range" in sec and "中位" in sec
    assert "stretched" in sec and "拉伸" in sec
    assert "even odds" in sec and "胜率接近五五" in sec
    assert "more often up" in sec and "多数时候上涨" in sec
    assert "usually up" not in sec and "通常上涨" not in sec
    assert "rolling over" in sec and "正在回落" in sec
    assert "turning up" in sec and "正在转强" in sec
    assert "MACD ↓" not in sec
    assert "MACD ↑" not in sec
    assert "RSI 42 · Stoch 6" not in sec
    assert "-1.1% (50%)" not in sec
    assert ">-1.1%<" in sec or ">-1.1%" in sec
    assert "1,295" in sec
    assert "Windows overlap — this ranks the state, it is not an independent sample." in sec
    assert "multi-timeframe momentum" not in sec
    assert "the confluence signal" not in sec
    assert "whether the daily, 3-day and weekly charts agree" in sec
    assert "日线／3 日线／周线是否一致" in sec


def test_lex_holds_theme_keys_and_neocloud_gpu_rental_ruling():
    """S2 §4 + seat ruling: combined Neocloud / AI Data Center key ships the
    GPU-rental ZH; the overbroad 新一代云服务商 candidate is rejected."""
    for en, zh in (
        ("Uranium", "铀矿"),
        ("Junior Gold Miners", "小型黄金矿商"),
        ("Meme / Retail", "迷因股／散户"),
        ("AI & Big Data", "人工智能与大数据"),
        ("AI Data Center", "人工智能数据中心"),
        ("Neocloud / AI Data Center", "新型 GPU 云服务商 / AI 数据中心"),
    ):
        assert i18n.LEX[en] == zh
    assert "Neocloud" not in i18n.LEX
    assert "新一代云服务商" not in i18n.LEX.values()
    html = i18n.td("Neocloud / AI Data Center")
    assert "新型 GPU 云服务商 / AI 数据中心" in str(html)
    page = _stocks(holdings_changes=[{**_hold_row(1), "sector": "Neocloud / AI Data Center"}])
    hold = page[page.index('id="holdings"'):]
    assert "新型 GPU 云服务商 / AI 数据中心" in hold
    assert "新一代云服务商" not in hold


def _acc_row(i: int) -> dict:
    return {
        "fund": "XLK", "sector": "Information Technology",
        "ticker": f"A{i:02d}", "name": f"Name {i}",
        "raw_change": 0.10, "active_change": 0.20, "active_pct": 0.01,
        "flow_str": "$1M", "flow_mn": 1.0,
        "direction": "up", "confirmed": False,
        "ladder": None, "window": "2026-09-01..2026-09-08", "vol": None,
    }


def test_accumulation_cap_label_present_when_n_gt_8():
    """Label is the unsliced universe, not the sliced panel length."""
    html = _env().get_template("_accumulation_watch.html.j2").render(
        accumulation=[_acc_row(i) for i in range(12)],
        accumulation_universe_n=110)
    assert "Top 8 · 110 tracked" in html
    assert "前 8 · 共 110 项跟踪" in html
    assert "Top 8 · 12 tracked" not in html
    assert html.count("<tr>") == 9  # header + 8 data
    h2 = html[html.index("<h2>"):html.index("</h2>")]
    assert "<a " not in h2
    assert "See all" not in html
    assert "查看全部" not in html
    assert 'class="tbl-scroll"' in html
    assert "#accumulation .help" in html
    assert "#accumulation .tbl-scroll" in html


def test_accumulation_drops_count_when_universe_unknown():
    html = _env().get_template("_accumulation_watch.html.j2").render(
        accumulation=[_acc_row(i) for i in range(12)])
    assert "Top 8" in html
    assert "Top 8 · 12 tracked" not in html
    assert "共 12 项跟踪" not in html


def test_accumulation_cap_label_absent_when_n_le_8():
    html = _env().get_template("_accumulation_watch.html.j2").render(
        accumulation=[_acc_row(i) for i in range(5)])
    assert "Top 8" not in html
    assert "前 8" not in html
    assert html.count("<tr>") == 6  # header + 5


def test_surviving_l1_panels_are_not_display_none():
    """S2 §1.2: the frozen 7 stay in flow; leftover research boards stay hidden."""
    html = _stocks()
    hide_start = html.index("body.page-stocks #sector-heat")
    hide_end = html.index("{display:none!important}", hide_start)
    hide = html[hide_start:hide_end]
    for pid in ("dash-tape-band", "equity-scoreboard", "sectors",
                "dash-mtf-section", "holdings"):
        assert pid not in hide, pid
    assert "sector-heat" in hide
    assert "sentiment-regime" in hide
    assert "cross-asset-macro" in hide


def test_holdings_table_scrolls_in_container():
    html = _stocks(holdings_changes=[_hold_row(i) for i in range(12)])
    hold = html[html.index('id="holdings"'):]
    hold = hold[:hold.index('id="health"')] if 'id="health"' in hold else hold
    assert 'class="tbl-scroll"' in hold


def test_evidence_fixture_render_carries_subjects_and_control_has_no_tape():
    """Round-2 capture VM: four G-gate subjects present; control has no tape."""
    from scripts.capture_us_stocks_compression_evidence import (
        render_sector_central_control, render_stocks_page,
    )
    html = render_stocks_page()
    for pid in L1_IDS:
        assert f'id="{pid}"' in html, pid
    assert 'class="acb-tape"' in html
    assert "Theme heat &amp; reasons → Sector Intelligence" in html
    assert "See all 24 →" in html
    assert "See all 12 →" not in html
    assert "新型 GPU 云服务商 / AI 数据中心" in html
    assert "no signal yet" in html
    assert 'class="mtf-skel"' in html
    assert "body.page-stocks #holdings{display:none!important}" not in html
    assert "body.page-stocks .mx5-aurora{display:none}" in html
    assert 'class="page-stocks"' in html
    ctrl = render_sector_central_control()
    assert 'id="action-board"' in ctrl
    assert "acb-tape" not in ctrl
    assert "Mega-cap tape" not in ctrl
    assert "macro-desk page-baskets" in ctrl
    assert 'id="accumulation"' in ctrl
    assert 'id="theme-tape"' in ctrl


def test_macro_mode_untouched_by_demotion():
    """S2 §1.4c BMV: macro.html did not render #accumulation; still doesn't."""
    html = _env().get_template("dashboard.html.j2").render(**_base_vm(), mode="macro")
    assert 'id="accumulation"' not in html
    assert 'id="theme-tape"' not in html
    assert "acb-tape" not in html


def _theme_tape_fixture() -> dict:
    from tests.test_theme_tape import _build
    return _build()


def _sc_builder_ctx(**over) -> dict:
    """scripts/build_sector_central.py:524-531 context shape (no `mode`)."""
    ctx = dict(
        flows_html="",
        pgate=None,
        bottoming=None,
        theme_context=None,
        factor_season=None,
        flow=None,
        basket_member_syms=[],
        action_board=None,
        accumulation=[_acc_row(i) for i in range(12)],
        accumulation_universe_n=24,
        theme_tape=_theme_tape_fixture(),
        generated_utc="2026-09-10",
    )
    ctx.update(over)
    return ctx


def test_sector_central_real_path_renders_landings_and_does_not_leak_tape():
    """M3: render sector_central.html.j2 via the builder context, not a
    standalone partial. Board-less else branch + both landing includes."""
    html = _env().get_template("sector_central.html.j2").render(**_sc_builder_ctx())
    assert 'id="accumulation-section"' in html
    assert 'id="theme-heat-section"' in html
    assert 'id="accumulation"' in html
    assert 'id="theme-tape"' in html
    assert "#accumulation .help" in html
    assert "#accumulation .tbl-scroll" in html
    assert "#theme-tape .help" in html
    assert "Refreshing the action board" in html or "正在刷新操作板" in html
    assert "acb-tape" not in html
    assert "Mega-cap tape" not in html
    assert 'class="panel span12" id="megacap-tape"' not in html
    assert "Top 8 · 24 tracked" in html
    assert "Top 8 · 12 tracked" not in html

    ab = {
        "total": 1, "buy_now": [], "buy_soon": [], "on_the_run": [],
        "take_profits": [], "hold": [], "avoid": [],
    }
    with_board = _env().get_template("sector_central.html.j2").render(
        **_sc_builder_ctx(action_board=ab))
    assert 'id="action-board"' in with_board
    assert "acb-tape" not in with_board
    assert "Mega-cap tape" not in with_board
    assert 'id="accumulation"' in with_board
    assert 'id="theme-tape"' in with_board
