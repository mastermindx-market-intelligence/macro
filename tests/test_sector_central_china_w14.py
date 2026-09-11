"""W14 r1 — sector_central_china heal: CSI 300 truth, plain-word chips, Explore demotion, designed states.

Scratch/fixture renders only. Never reads site/. Both lanes asserted via l-en/l-zh dual-emit.
"""
from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, TemplateNotFound

from engine import i18n

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
CYCLES = (ROOT / "engine" / "cycles.py").read_text(encoding="utf-8")
PAGE_SRC = (TPL / "sector_central_china.html.j2").read_text(encoding="utf-8")
ANV2_SRC = (TPL / "_china_act_now_board.html.j2").read_text(encoding="utf-8")

SNIPPET_IMPORTS = (
    '{% import "_prophet_card.html.j2" as pv %}\n'
    '{% import "_decision_card.html.j2" as dc %}\n'
    '{% import "_lens.html.j2" as lens %}\n'
    '{% from "_icons.html.j2" import icon %}\n'
)
T_MACRO = (
    '{%- macro t(en, zh="") -%}'
    '<span class="l-en">{{ en }}</span>'
    '<span class="l-zh">{{ zh if zh else en }}</span>'
    '{%- endmacro -%}\n'
    '{%- macro help(en, zh="") -%}<span></span>{%- endmacro -%}\n'
)

SIBLING_BENCH = (
    ("hk", "Hang Seng", "恒生指数"),
    ("canada", "S&P/TSX", "标普/TSX"),
    ("intl", "Intl ex-US", "国际(除美)"),
    ("factorwatch", "CSI 300", "沪深300"),
)


def _env(extra: dict | None = None) -> Environment:
    env = Environment(
        loader=ChoiceLoader([DictLoader(extra or {}), FileSystemLoader(str(TPL))]),
        autoescape=True,
    )
    env.globals.update(tr=i18n.tr, td=i18n.td)
    return env


def _render_page(**kwargs) -> str:
    env = _env()
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    ctx = {
        "bench_en": "CSI 300",
        "bench_zh": "沪深300",
        "generated_utc": "2026-09-11 00:00 UTC",
        "sleeve_stats": {
            "n_members": 12,
            "sleeve_factor": 0.9,
            "sharpe": 0.57,
            "n_rebalances": 349,
            "excess_per_reb": 0.43,
        },
    }
    ctx.update(kwargs)
    return env.get_template("sector_central_china.html.j2").render(**ctx)


def _blank_row(**kw):
    row = {
        "kind": "SECTOR",
        "id": "X",
        "name": "Foo",
        "name_zh": "福",
        "score": None,
        "reco": None,
        "reco_en": None,
        "reco_zh": None,
        "rel20": None,
        "rel5": None,
        "tag": None,
        "tag_zh": None,
        "urgency": None,
        "reasons": [],
        "phase": None,
        "osc_slope": None,
        "pos": None,
        "rs_63d": None,
        "rs_rank": None,
        "dual_read": False,
        "dual_chip_en": None,
        "dual_chip_zh": None,
        "organ_state": None,
        "organ_chip_en": None,
        "organ_chip_zh": None,
        "href": None,
    }
    row.update(kw)
    return row


def _render_anv2(rows_by_lane: dict) -> str:
    start = ANV2_SRC.index("<!-- ===================== ACT-NOW v2")
    snippet = ANV2_SRC[start:]
    full = SNIPPET_IMPORTS + T_MACRO + snippet
    env = Environment(
        loader=ChoiceLoader([DictLoader({"blk": full}), FileSystemLoader(str(TPL))]),
        autoescape=False,
    )
    env.globals.update(tr=i18n.tr, td=i18n.td)
    lanes = {"buy_now": [], "wait_pullback": [], "bottoming_watch": [], "reduce_avoid": []}
    lanes.update(rows_by_lane)
    return env.get_template("blk").render(
        act_now_v2={"as_of": "2026-09-11", "notes": [], "lanes": lanes},
        mode="stocks",
        lang="en",
        sectors_by_ticker={},
    )


def _render_desk(bench_en: str, bench_zh: str, compact: bool = False) -> str:
    env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=False)
    env.globals["t"] = lambda en, zh="": (
        f'<span class="l-en">{en}</span><span class="l-zh">{zh or en}</span>'
    )
    return env.get_template("_baskets_desk.html.j2").render(
        bench_en=bench_en,
        bench_zh=bench_zh,
        si_hide_actnow_desk=True,
        si_explore_compact=compact,
    )


# ---------------------------------------------------------------------------
# P0 — CSI 300 truth + no silent S&P 500 default
# ---------------------------------------------------------------------------

def test_p0_page_names_csi_300_not_sp500() -> None:
    html = _render_page()
    assert html.count("versus S&P 500") == 0
    assert "5-day return versus CSI 300" in html
    assert "相对" in html and "沪深300" in html


@pytest.mark.parametrize("label,bench_en,bench_zh", SIBLING_BENCH)
def test_p0_sibling_desk_benchmark_unregressed(label, bench_en, bench_zh) -> None:
    html = _render_desk(bench_en, bench_zh)
    plain = html_lib.unescape(html)
    assert f"versus {bench_en}" in plain, f"{label} lost EN bench"
    assert bench_zh in html, f"{label} lost ZH bench"
    assert "versus S&P 500" not in plain or bench_en == "S&P 500"


def test_p0_missing_bench_fails_loudly() -> None:
    env = _env()
    env.globals["t"] = lambda en, zh="": en
    with pytest.raises(TemplateNotFound) as ei:
        env.get_template("_baskets_desk.html.j2").render(si_hide_actnow_desk=True)
    assert "requires bench_en and bench_zh" in str(ei.value)


# ---------------------------------------------------------------------------
# P1a — display twins; routing key untouched
# ---------------------------------------------------------------------------

def test_p1a_watch_display_twins_both_lanes() -> None:
    html = _render_anv2({"bottoming_watch": [_blank_row(tag="WATCH", tag_zh="观察", osc_slope=2.0)]})
    chip = html[html.index("anv2-chip-tag"): html.index("anv2-chip-tag") + 400]
    assert 'class="l-en">Early sign' in chip
    assert 'class="l-zh">初步迹象' in chip
    assert 'class="l-en">WATCH' not in chip


def test_p1a_unconfirmed_display_twins_both_lanes() -> None:
    html = _render_anv2({"reduce_avoid": [_blank_row(
        tag="UNCONFIRMED — HIGH RISK", tag_zh="未确认高风险")]})
    chip = html[html.index("anv2-chip-tag"): html.index("anv2-chip-tag") + 500]
    assert "Not yet confirmed — high risk" in chip
    assert "尚未确认——高风险" in chip
    assert "UNCONFIRMED — HIGH RISK" not in chip


def test_p1a_tag_routing_key_byte_identical_to_cycles() -> None:
    assert '{"tag": "WATCH", "tag_zh": "观察"' in CYCLES
    assert '"tag": "WATCH"' in PAGE_SRC or "row.tag" in ANV2_SRC
    # The producer still reads row.tag — it does not rename the routing key.
    assert "row.tag" in ANV2_SRC
    assert "_tag_label_en" in ANV2_SRC


# ---------------------------------------------------------------------------
# P1b / P1c — slope demoted; EN carried up
# ---------------------------------------------------------------------------

def test_p1b_slope_number_in_tip_not_on_chip() -> None:
    html = _render_anv2({"bottoming_watch": [_blank_row(osc_slope=14.1, rs_63d=-5.2, pos=12)]})
    chip = html[html.index("anv2-chip-turn"): html.index("anv2-chip-turn") + 700]
    assert "turning up" in chip and "转强" in chip
    assert "higher number = sharper turn" in chip
    assert "数字越大转向越明显" in chip
    # number lives in the tip attributes, not as the chip's rest label
    rest = re.sub(r'data-tip-(en|zh)="[^"]*"', "", chip)
    assert "14.1" not in rest
    assert "(14.1)" in chip


def test_p1c_en_carries_popover_words() -> None:
    html = _render_anv2({"bottoming_watch": [_blank_row(osc_slope=1.0, rs_63d=-5.2, pos=12)]})
    assert "63d strength" in html
    assert "63d RS" not in html
    assert 'class="l-en">position' in html
    assert 'class="l-zh">位置' in html
    assert 'class="l-en">pos<' not in html and ">pos <" not in html


# ---------------------------------------------------------------------------
# P1d — every-day plain flow read; σ in receipt tip
# ---------------------------------------------------------------------------

def test_p1d_near_normal_word_and_sigma_in_tip() -> None:
    html = _render_page()
    assert "near normal" in html
    assert "接近常态" in html
    assert "data-tip-rc-en=" in html
    assert "versus its own history" in html
    assert "data-tip-rc-zh=" in html
    assert "相对自身历史" in html
    assert "Southbound flow" in html
    assert "南向资金" in html
    assert "Southbound net z" not in html.replace(
        "// Southbound net z from participation.json (already loaded by build_china for other panels).",
        "",
    )


# ---------------------------------------------------------------------------
# P1f — one-sentence footer; banned constructions gone
# ---------------------------------------------------------------------------

def test_p1f_footer_one_sentence_both_lanes() -> None:
    html = _render_page()
    foot = html[html.index("<footer>"): html.index("</footer>")]
    assert "The conviction read blends credit, volatility and margin conditions with the pattern's conditional odds." in foot
    assert "信念读数由信用、波动率和融资环境，以及走势的条件概率共同决定" in foot
    for banned in (
        "gated-confluence",
        "validated credit/vol/margin",
        "pathway conditional odds",
        "capped context",
        "confluence",
    ):
        assert banned not in foot
    # one EN sentence, one ZH sentence (no stacked period-pairs in either span)
    en = re.search(r'class="l-en">(.*?)</span>', foot, re.S).group(1).strip()
    zh = re.search(r'class="l-zh">(.*?)</span>', foot, re.S).group(1).strip()
    assert en.count(".") == 1
    assert zh.count("。") == 1


# ---------------------------------------------------------------------------
# P2a — Explore demotion landings present
# ---------------------------------------------------------------------------

def test_p2a_named_landings_present() -> None:
    html = _render_page()
    assert 'id="entry-radar-more"' in html
    assert "Entry radar" in html and "入场雷达" in html
    assert 'id="forming-narratives-more"' in html
    assert "Forming narratives" in html and "酝酿中的叙事" in html
    assert 'id="si-theme-desk-more"' in html
    assert 'id="si-concentration-more"' in html
    assert 'id="si-rotation-more"' in html
    assert 'id="si-impulse-more"' in html
    assert 'id="reversal-sleeve-card"' in html
    assert 'href="cn_reversal_sleeve.html"' in html
    assert 'id="entry-radar"' in html
    assert 'id="forming-narratives"' in html
    assert 'id="sleeve-chip"' in html
    assert "hidden" in html[html.index('id="sleeve-chip"'): html.index('id="sleeve-chip"') + 80]


# ---------------------------------------------------------------------------
# P2b / P2c / P2d
# ---------------------------------------------------------------------------

def test_p2b_table_limit_eight_and_counted_see_more() -> None:
    html = _render_page()
    assert "const TABLE_LIMIT = 8;" in html
    assert "See more ${hiddenN}" in html
    assert "查看更多 ${hiddenN} 个" in html
    assert "const TABLE_LIMIT = 12;" not in html


def test_p2c_one_data_stamp_no_built_render_time() -> None:
    html = _render_page()
    assert 'id="sc-asof"' in html
    conf = html[html.find('id="si-confluence"'): html.find("<footer>")]
    assert "2026-09-11 00:00 UTC" not in conf
    assert "生成于" not in conf
    assert re.search(r">\s*Built\s*<", conf) is None


def test_p2d_sigma_mode_named_and_hides_mtd_ytd() -> None:
    html = _render_page()
    assert "How unusual" in html
    assert "反常程度" in html
    assert "btblMode==='sigma' ? TBL_COLS_ALL.filter(c=>/^\\d/.test(c))" in html
    assert "['sigma','σ']" not in html
    assert "月至今" in html and "年至今" in html


# ---------------------------------------------------------------------------
# P3 — designed states
# ---------------------------------------------------------------------------

def test_p3_skeletons_wordless() -> None:
    html = _render_page()
    assert "skel-slot" in html
    assert "Loading…" not in html
    assert "加载中…" not in html


def test_p3_errors_are_three_part() -> None:
    html = _render_page()
    assert "mx-error" in html
    assert "China rotation-event data did not load. The rest of this page still works." in html
    assert "中国轮动事件数据未能加载。本页其余部分仍可用。" in html
    assert "Basket data did not load. The rest of this page still works." in html
    assert "篮子数据未能加载。本页其余部分仍可用。" in html
    assert "Retry" in html and "重试" in html


def test_p3_four_dash_sites_use_empty_family() -> None:
    html = _render_page()
    assert "mx-empty-why" in html
    assert "date pending" in html and "日期待加载" in html
    assert "Southbound flow is not in this feed" in html
    assert "南向资金不在本数据源" in html
    assert "Southbound flow: —" not in html
    assert "南向资金：—" not in html
    # hero as-of no longer a permanent em-dash fallback
    assert "asofEl && BASKETS.as_of" in html
    assert "BASKETS.as_of||'—'" not in html


def test_p3e_exactly_one_h1() -> None:
    html = _render_page()
    # CSS comments mention `<h1>`; pin the one real document heading.
    assert html.count('<h1><span class="l-en">China Sector Intelligence') == 1
    assert "Subsector Confluence" in html
    assert re.search(r"<h2[^>]*>.*Subsector Confluence", html, re.S)


def test_p3f_severity_and_ratio_glossed() -> None:
    html = _render_page()
    assert "t('Major','重大')" in html or ">Major<" in html or "'Major','重大'" in html
    assert "10-session ratio change" in html
    assert "10段比值变化" in html
    assert "'/10s'" not in html and '"/10s"' not in html and "+'/10s'" not in html


def test_p3g_row_pop_sub_zh_reuses_visible_dual_emit() -> None:
    html = _render_anv2({"buy_now": [_blank_row(
        kind="THEME", name="Theme", name_zh="主题", score=50,
        reco="accumulate", reco_en="Accumulate", reco_zh="积累",
        rel20=0.042, reasons=["20d +4.2% vs CSI 300"],
    )]})
    block = html[html.index('class="row-pop-sub"'): html.index('class="row-pop-sub"') + 280]
    assert 'class="l-en">20d +4.2% vs CSI 300' in block
    assert 'class="l-zh">20日 +4.2% 相对沪深300' in block


# ---------------------------------------------------------------------------
# DNT — composition identities that must survive
# ---------------------------------------------------------------------------

def test_dnt_validated_edge_chip_kept() -> None:
    html = _render_page()
    assert "VALIDATED EDGE" in html
    assert "已验证优势" in html


def test_dnt_quiet_tape_and_northbound_verbatim() -> None:
    html = _render_page()
    assert "No active China rotation events — quiet state is a valid state." in html
    assert "当前无活跃中国轮动事件——安静状态是有效状态。" in html
    assert "Northbound daily flow is no longer published (since Aug 2024)" in html
    assert "北向每日净买入自2024年8月起已停止披露" in html


def test_dnt8_act_now_four_lanes_survive() -> None:
    src = ANV2_SRC
    for lane_id in ("anv2-buy", "anv2-pull", "anv2-bot", "anv2-red"):
        assert lane_id in src
    assert "{% for row in items %}{{ _anrow(row, lane_key) }}{% endfor %}" in src
    html = _render_page(act_now_v2={
        "as_of": "2026-09-11",
        "notes": [],
        "lanes": {
            "buy_now": [_blank_row(kind="THEME", name="A", name_zh="甲", score=70,
                                   reco="accumulate", reco_en="Accumulate", reco_zh="积累")],
            "wait_pullback": [_blank_row(kind="THEME", name="B", name_zh="乙", score=55,
                                         reco="hold", reco_en="Hold", reco_zh="持有")],
            "bottoming_watch": [_blank_row(name="C", name_zh="丙", osc_slope=1.0)],
            "reduce_avoid": [_blank_row(name="D", name_zh="丁", tag="WATCH", tag_zh="观察")],
        },
    })
    assert html.count('class="anv2-row"') == 4
    assert 'id="anv2-buy"' in html
    assert 'id="anv2-pull"' in html
    assert 'id="anv2-bot"' in html
    assert 'id="anv2-red"' in html
