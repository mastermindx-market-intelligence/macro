"""China.html Archetype-D S1 — structure + landing + copy gates.

Frozen spec: spec_china_archetype_d.md. Pins G1 structure, G2 count-truth
labels, G3 banned Tier-1 tokens, G4 Growth-Scare ZH, G5 skeleton, and the
§1.6 demotion landings. Rewrites of older 14-module assertions are justified
by spec §1.2 / §1.3 (the 14→6 L1 map).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "templates" / "china.html.j2").read_text(encoding="utf-8")

_WRAP_START = '  <div class="cnx-wrap">'
_WRAP_END = "  </div>{# /cnx-wrap #}"


def _wrap() -> str:
    start = SRC.index(_WRAP_START)
    end = SRC.index(_WRAP_END) + len(_WRAP_END)
    return SRC[start:end]


def _dialogs() -> str:
    return SRC[SRC.index("<!-- =============== DIALOGS =============== -->") :]


def test_g1_six_l1_sections_in_frozen_order():
    """Spec §1.2 / G1: exactly six first-level sections in frozen order."""
    wrap = _wrap()
    labels = re.findall(
        r'<h2 class="band-label">.*?<span class="l-en">(.*?)</span>',
        wrap,
        flags=re.S,
    )
    assert labels == [
        "What to do",
        "What changed",
        "Why — four drivers",
        "What we're watching",
        "Go deeper",
    ], labels
    assert wrap.count('<header class="mx-vh">') == 1
    assert wrap.count("<section class=") == 5
    # 14-module racks must not remain at L1 (spec §1.2). CSS may still name them.
    assert 'class="cnx-rack2"' not in wrap
    assert 'class="cnx-rack3"' not in wrap
    assert 'class="cnx-hero' not in wrap


def test_g1_demotion_landings_pinned():
    """Spec §1.6: five Go-deeper links, named landings for every demoted module."""
    wrap = _wrap()
    assert 'href="china_policy_watch.html"' in wrap
    assert 'href="flow_velocity.html"' in wrap
    assert 'href="china_intel.html"' in wrap
    assert 'href="alerts.html"' in wrap
    # V2: the 696-story feed lives on china_news.html, not china_policy_watch.
    assert 'href="china_news.html"' in wrap
    assert "Sectors, sentiment &amp; today's full read" in wrap
    assert "板块、情绪与今日完整解读" in wrap
    assert "Full news feed · 24 of 696 kept" in wrap
    assert "完整新闻流 · 已保留 24/696" in wrap
    assert "Policy &amp; credit desk" in wrap
    assert "Alerts &amp; watchlist" in wrap
    assert "cnxOpenDlg('cnx-dlg-playbook')" in wrap
    assert "Regime playbook" in wrap
    assert "周期策略" in wrap


def test_g2_events_slice_label_from_one_source():
    """Spec §2.1 / M2: population is the high-importance subset of event_strip."""
    wrap = _wrap()
    assert "c.importance == 'high'" in wrap
    assert "{% set _ev_shown = _ev_all[:4] %}" in wrap
    assert "{{ _ev_all | length }}" in wrap
    assert "{{ _ev_shown | length }}" in wrap
    assert 'high-impact prints ahead' in wrap
    assert "shown · full calendar →" in wrap
    assert "项已显示 · 完整日历 →" in wrap
    assert "No high-impact prints ahead this session" in wrap
    assert 'class="edot h"' in wrap
    assert "{{ 'h' if c.importance == 'high' else 'm' }}" not in wrap


def test_g2_high_impact_count_is_the_filtered_integer():
    """M2: mixed strip yields the high-importance count, not len(event_strip)."""
    from scripts.capture_china_archetype_d_evidence import fixture_vm, render_macro_block

    vm = fixture_vm()
    vm["event_strip"] = [
        {"name_en": "CPI", "name_zh": "CPI", "date": "09-12", "importance": "high"},
        {"name_en": "Credit", "name_zh": "信贷", "date": "09-15", "importance": "high"},
        {"name_en": "LPR", "name_zh": "LPR", "date": "09-20", "importance": "med"},
        {"name_en": "Briefing", "name_zh": "吹风", "date": "09-22", "importance": "high"},
        {"name_en": "PMI", "name_zh": "PMI", "date": "09-30", "importance": "low"},
    ]
    html = render_macro_block(vm)
    watching = html[html.find("What we're watching"): html.find("Go deeper")]
    assert re.search(
        r'3\s+<span class="l-en">high-impact prints ahead</span>', watching
    ), watching[watching.find("high-impact") - 40: watching.find("high-impact") + 80]
    assert "5 high-impact" not in watching
    assert re.search(
        r'3\s+<span class="l-en">of</span>.*?</span>\s+3\s+<span class="l-en">shown',
        watching,
        flags=re.S,
    ), watching[watching.find("cnx-view-all"): watching.find("cnx-view-all") + 280]


def test_g2_duplicate_45_percent_row_removed():
    """Spec §2.2: keep agreement_pct at the Signals strip; delete the kv twin."""
    dialogs = _dialogs()
    assert "signal_stack.agreement_pct" in dialogs
    assert "t('Signal agreement','信号一致度')" not in dialogs
    assert "(latest.confidence*100)|round|int" not in dialogs


def test_g3_banned_tokens_absent_from_l1_except_tips():
    """Spec §0 G3 / §3: banned tokens only in data-tip-* attribute values."""
    wrap = _wrap()
    banned = [
        "90th percentile",
        "3/3",
        "ONE monetary-conditions vote",
        "~70% hit",
        "Breadth breakdown (all-boats)",
        "Intensity 87/100",
        "×0.78",
    ]
    stripped = re.sub(r'data-tip-(?:en|zh)="[^"]*"', "", wrap)
    for token in banned:
        assert token not in stripped, f"banned token {token!r} at L1 outside a data-tip value"


def test_g3_tier1_what_to_do_copy():
    """Spec §3.1: producer-bound faces keep the round-2 word-budget copy."""
    wrap = _wrap()
    assert "for face in _todo_faces" in wrap
    assert "Everything is falling together" in wrap
    assert "全市场同步下跌" in wrap
    from scripts.capture_china_archetype_d_evidence import render_macro_block

    html = render_macro_block()
    assert "Fear like this has usually been a buying window, not a top" in html
    assert "这种恐慌通常是买入窗口，而不是顶部" in html
    assert "Money is getting tighter at the central bank" in html
    assert "央行层面的货币条件正在收紧" in html
    assert "Borrowed money in A-shares is crowded" in html
    assert "A股杠杆资金拥挤" in html


def test_g4_growth_scare_not_inside_l_zh_in_glance():
    """Spec §4.4 / G4: Growth-Scare never appears inside an l-zh span on L1."""
    wrap = _wrap()
    assert not re.search(r'l-zh[^<]*>[^<]*Growth-Scare', wrap)
    assert '<span class="l-zh">{{ _ms_label_zh }}</span>' in wrap
    assert '<span class="l-en">{{ _ms_label }}</span>' in wrap
    from scripts.capture_china_archetype_d_evidence import render_macro_block

    html = render_macro_block()
    assert re.search(r'<h1 class="mx-vh-word"><span class="l-en">GROWTH SCARE</span>', html)
    assert "<span class=\"l-zh\">增长恐慌</span>" in html
    assert not re.search(r'l-zh[^<]*>[^<]*Growth-Scare', html)


def test_g5_csi_chinext_skeleton_not_bare_dash():
    """Spec §5.1: CSI 300 / ChiNext hydrate from skeleton plates, not em-dashes."""
    wrap = _wrap()
    assert 'data-sym="000300.SS"' in wrap
    assert 'data-sym="399006.SZ"' in wrap
    assert 'mx5-mkt-price nb-px mx-skel' in wrap
    assert 'aria-busy="true"' in wrap
    # The live-only tiles must not bake a lone em-dash into the price slot.
    assert re.search(
        r'data-sym="000300\.SS"[^>]*>\s*—', wrap
    ) is None


def test_g5_single_page_stamp():
    """Spec §5.4: one dtp-asof in the hero; secbar no longer trails a date."""
    wrap = _wrap()
    assert wrap.count('class="dtp-asof tnum"') == 1
    assert "cnx-secbar" in wrap
    # Trailing date span on the secbar is gone.
    assert not re.search(r'cnx-secbar"><b>.*</b><span>\{\{ latest.date \}\}</span>', wrap)


def test_four_driver_headings():
    """Spec §1.5: exactly four driver panels, frozen names."""
    wrap = _wrap()
    assert "Policy &amp; credit" in wrap and "政策与信贷" in wrap
    assert ">Money flows<" in wrap and "资金流向" in wrap
    assert "Market internals" in wrap and "市场内部结构" in wrap
    assert "Property &amp; growth" in wrap and "房地产与增长" in wrap


def test_connect_flows_yi_bn_pair_and_en_names():
    """Spec §4.2 / §4.3: 亿↔bn pair + frozen EN names (no per-holding EN field)."""
    wrap = _wrap()
    assert "cny_yi_pair(I.southbound.net)" in wrap
    assert "Tencent · YOFC · CNOOC" in wrap
    assert "腾讯控股 · 长飞光纤光缆 · 中国海洋石油" in wrap


def test_plain_gross_wired_for_china_dialog():
    """Spec §3.2(d): china dialog uses the multiplier-as-¾ label."""
    dlg = (ROOT / "templates" / "_risk_radar_dlg.html.j2").read_text(encoding="utf-8")
    card = (ROOT / "templates" / "_risk_radar_card.html.j2").read_text(encoding="utf-8")
    assert "plain_gross=(mkt=='cn')" in dlg
    assert "¾ of normal" in card
    assert "约常规四分之三" in card
    assert "_gv.en" in card


def _render_rrx_plain_gross(gross: float) -> str:
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    tmpl = env.get_template("_risk_radar_card.html.j2")
    rd = {
        "state": "elevated", "state_zh": "偏高", "is_loud": False,
        "gross": gross, "dd21": 0.2, "dd_lift": 1.1,
        "label_en": "all-boats", "label_zh": "普跌",
    }
    return tmpl.module.risk_radar_card(rd, [], plain_gross=True)


def test_plain_gross_band_follows_rd_gross_across_two_values():
    """M1: ¾ is the 0.78 snapshot band; 0.50 is not ¾."""
    from engine.china_tier1 import plain_gross_band

    assert plain_gross_band(0.78) == ("¾ of normal", "约常规四分之三")
    assert plain_gross_band(0.50) == ("half of normal", "约常规一半")
    html_hi = _render_rrx_plain_gross(0.78)
    html_lo = _render_rrx_plain_gross(0.50)
    assert "¾ of normal" in html_hi
    assert "约常规四分之三" in html_hi
    assert "¾ of normal" not in html_lo
    assert "half of normal" in html_lo
    assert "约常规一半" in html_lo
    assert "×0.78" in html_hi  # lives in the tip
    assert "×0.50" in html_lo


def _spec_kind_invert(row):
    _store, _name, _col, _en, _zh, kind, _tzh, _decimals, _is_rate, invert = row
    return kind, invert


def test_inverted_tiles_disclose_quote_orientation():
    """Every invert spec row must teach what 'higher' means (B1 structural pin).

    Mirrors tests/test_hk_tier1_shell.py::test_inverted_tiles_disclose_quote_orientation
    against scripts/build_china.MARKET_TILE_SPEC. Guards the spec table itself —
    S1 folded the glance strip into SSE/CSI 300/ChiNext/HSI, so no invert tile
    currently renders at L1.
    """
    from scripts.build_china import CHINA_TILE_COPY, MARKET_TILE_SPEC

    inverted = [row for row in MARKET_TILE_SPEC if _spec_kind_invert(row)[1]]
    assert inverted, "spec must include at least one invert row"
    # Truthy invert (not `is True`) so a 1 would still be pinned.
    assert _spec_kind_invert(("g", "n", "c", "e", "z", "peg", "z2", 4, False, 1))[1]
    assert not _spec_kind_invert(("g", "n", "c", "e", "z", "x", "z2", 0, False, 0))[1]
    assert not _spec_kind_invert(("g", "n", "c", "e", "z", "x", "z2", 0, False, False))[1]
    for row in inverted:
        kind, _invert = _spec_kind_invert(row)
        copy = CHINA_TILE_COPY[kind]
        en, zh = copy["meaning_en"], copy["meaning_zh"]
        assert "higher" in en.lower(), f"{kind} meaning_en must disclose orientation: {en!r}"
        assert "weaker" in en.lower() or "stronger" in en.lower(), (
            f"{kind} meaning_en must name the weaker/stronger reading: {en!r}"
        )
        assert "数值升高" in zh, f"{kind} meaning_zh must disclose orientation: {zh!r}"
    yuan = CHINA_TILE_COPY["USDCNH"]
    assert "higher = a weaker yuan" in yuan["meaning_en"]
    assert "人民币走弱" in yuan["meaning_zh"]
    assert "quoted as yuan per US dollar" in yuan["meaning_en"]
    assert "以美元兑人民币报价" in yuan["meaning_zh"]
    dlg = _dialogs()
    card = dlg[dlg.find("USD/CNH"): dlg.find("10Y CGB")]
    assert "_cnh.meaning_en" in card
    assert "_cnh.meaning_zh" in card
    assert "namespace(tile=none)" in card


def test_l1_index_strip_has_no_inverted_quote_tile():
    """S1 folded market tiles into SSE/CSI 300/ChiNext/HSI — none invert."""
    wrap = _wrap()
    assert wrap.count("mx5-mkt-tile") == 4
    assert 'data-sym="CNH_F"' not in wrap
    assert "Offshore yuan" not in wrap
    assert "USDCNH" not in wrap
    assert "quoted as yuan per US dollar" not in wrap
    assert "以美元兑人民币报价" not in wrap


def test_g8_floor_css_pins():
    """G8: reduced-motion stills the skeleton; chips wrap; focus rings exist."""
    assert "@media (prefers-reduced-motion:reduce)" in SRC
    assert "body.page-china .mx-skel{animation:none;background-image:none}" in SRC
    assert "[data-theme=\"light\"] body.page-china .mx-skel{animation:none;background-image:none}" in SRC
    assert "body.page-china .cnx-chips{display:flex;flex-wrap:wrap" in SRC
    assert "body.page-china .cnx-wrap .depth{display:flex;flex-wrap:wrap" in SRC
    assert "body.page-china .cnx-wrap{overflow-x:clip}" in SRC
    assert "cnx-row .cnx-lens:focus-visible" in SRC
    assert "drivers > .panel:focus-visible" in SRC
    assert 'class="cnx-lens"' in SRC


def test_evidence_crop_hooks_present():
    wrap = _wrap()
    for hook in ("hero", "todo", "changed", "drivers", "watching-deeper"):
        assert f'data-ev="{hook}"' in wrap, hook


def test_fixture_macro_block_renders_six_l1_without_data_dir():
    """Sparse-safe: the evidence fixture renders the wrap with no data/ reads."""
    from scripts.capture_china_archetype_d_evidence import render_macro_block

    html = render_macro_block()
    assert 'class="mx-vh"' in html
    assert "What to do" in html
    assert "What changed" in html
    assert "Why — four drivers" in html
    assert "What we're watching" in html
    assert "Go deeper" in html
    assert "+¥4.6bn" in html
    assert "+¥46亿" in html
    assert "4 " in html and "of</span>" in html
    assert "GROWTH SCARE" in html
    assert "增长恐慌" in html
    assert "CNH_F" not in html
    assert "quoted as yuan per US dollar" not in html
    assert "Neutral — add slowly, don't chase" in html
    assert "中性——慢慢加仓，勿追高" in html
    assert "Regime playbook" in html


def test_hero_word_shares_dial_aria_label_source():
    """B1 contradiction guard: h1 word and dial aria-label both read _ms_label."""
    wrap = _wrap()
    assert 'aria-label="{{ _ms_label }} — {{ _ms_score }}"' in wrap
    assert '<h1 class="mx-vh-word"><span class="l-en">{{ _ms_label }}</span><span class="l-zh">{{ _ms_label_zh }}</span></h1>' in wrap
    assert "GROWTH SCARE</span>" not in wrap


def test_posture_lane_maps_each_producer_state_en_zh():
    """B1: each china_playbook posture → ratified lane words; unknown → cautious."""
    from engine.china_playbook import _POSTURES
    from engine.china_tier1 import CAUTIOUS_LANE, POSTURE_LANE, posture_lane

    expected = {
        "DEFENSIVE": ("Stand aside", "观望"),
        "CAREFUL": ("Watch — don't chase", "观察，勿追高"),
        "NEUTRAL": ("Neutral — add slowly, don't chase", "中性——慢慢加仓，勿追高"),
        "CONSTRUCTIVE": ("Get ready", "做好准备"),
        "AGGRESSIVE": ("Act", "行动"),
    }
    assert list(_POSTURES) == list(expected)
    assert set(POSTURE_LANE) == set(expected)
    for posture, lane in expected.items():
        assert posture_lane(posture) == lane, posture
        assert POSTURE_LANE[posture] == lane
    assert posture_lane("NOT A STATE") == CAUTIOUS_LANE
    assert posture_lane(None) == CAUTIOUS_LANE
    assert posture_lane("BULLISH") == CAUTIOUS_LANE
    assert "Act" not in posture_lane("UNKNOWN")
    assert posture_lane("Watch — don't chase") == CAUTIOUS_LANE


def test_render_each_posture_lane_and_unknown_is_cautious():
    """B1: rendered wrap follows the producer posture; junk never goes bullish."""
    from engine.china_tier1 import POSTURE_LANE, CAUTIOUS_LANE
    from scripts.capture_china_archetype_d_evidence import fixture_vm, render_macro_block

    vm = fixture_vm()
    for posture, (en, zh) in POSTURE_LANE.items():
        vm["pb"] = dict(vm["pb"])
        vm["pb"]["dial"] = dict(vm["pb"]["dial"], posture=posture)
        html = render_macro_block(vm)
        hero = html[html.find('class="mx-vh"'): html.find("What to do")]
        assert en in hero, posture
        assert zh in hero, posture
    vm["pb"]["dial"] = dict(vm["pb"]["dial"], posture="FRESH BUY")
    html = render_macro_block(vm)
    hero = html[html.find('class="mx-vh"'): html.find("What to do")]
    assert CAUTIOUS_LANE[0] in hero
    assert CAUTIOUS_LANE[1] in hero
    assert "FRESH BUY" not in hero
    assert '<span class="l-en">Act</span>' not in hero


def test_missing_playbook_reason_renders_worded_empty_not_frozen_sentence():
    """B1: a missing producer reason is §9.12 worded empty, not the snapshot."""
    from engine.china_tier1 import EMPTY_REASON
    from scripts.capture_china_archetype_d_evidence import fixture_vm, render_macro_block

    vm = fixture_vm()
    vm["pb"] = dict(vm["pb"])
    vm["pb"]["dial"] = dict(vm["pb"]["dial"], reasons=[])
    html = render_macro_block(vm)
    todo = html[html.find("What to do"): html.find("What changed")]
    assert EMPTY_REASON["en"] in todo
    assert EMPTY_REASON["zh"] in todo
    assert todo.count(EMPTY_REASON["en"]) == 3
    assert "Fear like this has usually been a buying window" not in todo


def test_playbook_dialog_has_a_named_opener():
    """M3 / §9.13: cnx-dlg-playbook keeps at least one cnxOpenDlg landing."""
    assert SRC.count("cnxOpenDlg('cnx-dlg-playbook')") >= 1
    assert 'id="cnx-dlg-playbook"' in SRC


def test_post_stack_css_marker_present():
    assert "/* post-stack: consolidate */" in SRC


def test_capture_harness_skips_theme_toggle_flourish():
    """B2: r2 sun/moon disc was skyToggleFx photographed at 150ms; seed bows out."""
    from scripts import capture_china_archetype_d_evidence as cap

    assert "window.__skyDeck = true" in cap._STATE_SEED_SCRIPT
    assert ".sky-fx" in cap._APPLY_STATE_SCRIPT


def test_cnh_dialog_card_renders_orientation_copy():
    """M4: surviving CNH surface carries CHINA_TILE_COPY meaning lines (rendered)."""
    from jinja2 import DictLoader, Environment
    from scripts.build_china import CHINA_TILE_COPY
    from scripts.capture_china_archetype_d_evidence import _extract_macros

    start = SRC.index("{# USD/CNH")
    end = SRC.index("{# 10Y CGB #}")
    env = Environment(
        loader=DictLoader({"s": _extract_macros(SRC) + "\n" + SRC[start:end]}),
        autoescape=False,
    )
    html = env.get_template("s").render(market_tiles=[{
        "tag": "USDCNH 美元离岸",
        "label": "Offshore yuan 离岸人民币",
        "level": "7.123",
        "meaning_en": CHINA_TILE_COPY["USDCNH"]["meaning_en"],
        "meaning_zh": CHINA_TILE_COPY["USDCNH"]["meaning_zh"],
    }])
    assert "quoted as yuan per US dollar — higher = a weaker yuan" in html
    assert "以美元兑人民币报价 — 数值升高 = 人民币走弱" in html
    assert "cnx-orient" in html
    assert "7.123" in html


def test_money_mixed_sentence_renders_mixed_face():
    """B1-a: producer MIXED sentence is not classified as easing."""
    from engine.china_tier1 import reason_faces

    mixed = (
        "i",
        "PBoC monetary conditions mixed (1 easing / 1 tightening / 1 neutral) — no net vote.",
        "央行货币条件分歧 — 无净投票。",
    )
    face = reason_faces([mixed], n=1)[0]
    assert face["sign"] == "ℹ"
    assert "mixed" in face["en"].lower()
    assert "no single vote" in face["en"]
    assert "easier" not in face["en"]
    assert "every part of that read agrees" not in face["en"]
    assert "all point the same way" not in face["tip_en"]
    assert "方向不一" in face["zh"]


def test_money_parsed_count_agreement_contract():
    """B1-b: parsed n/m contract — 1/3, 1/2, 2/3, 3/3, 1/1, no-counts."""
    from engine.china_tier1 import reason_faces

    def face(sign, en, zh="央行货币条件趋宽。"):
        return reason_faces([(sign, en, zh)], n=1)[0]

    # 1/3 plurality, not majority — direction only, no agreement claim.
    f_13 = face(
        "+",
        "PBoC monetary conditions tilting easing (1/3 legs). ONE monetary-conditions vote.",
        "央行货币条件趋宽（1/3项指标同意）— 综合M2/剪刀差/社融的单次货币投票。",
    )
    assert f_13["en"] == "Money is tilting easier at the central bank."
    assert f_13["zh"] == "央行层面的货币条件正在趋宽。"
    assert "most of that read agrees" not in f_13["en"]
    assert "every part of that read agrees" not in f_13["en"]
    assert "多数方向一致" not in f_13["zh"]
    assert "各个部分方向一致" not in f_13["zh"]

    # 1/2 plurality, not majority.
    f_12 = face(
        "-",
        "PBoC monetary conditions tightening (1/2 legs). ONE monetary-conditions vote.",
        "央行货币条件趋紧（1/2项指标同意）— 综合M2/剪刀差/社融的单次货币投票。",
    )
    assert f_12["en"] == "Money is tilting tighter at the central bank."
    assert f_12["zh"] == "央行层面的货币条件正在趋紧。"
    assert "most of that read agrees" not in f_12["en"]
    assert "every part of that read agrees" not in f_12["en"]

    # 2/3 majority.
    f_23 = face(
        "+",
        "PBoC monetary conditions tilting easing (2/3 legs). ONE monetary-conditions vote.",
        "央行货币条件趋宽（2/3项指标同意）— 综合M2/剪刀差/社融的单次货币投票。",
    )
    assert f_23["en"] == (
        "Money is getting easier at the central bank, and most of that read agrees."
    )
    assert "every part of that read agrees" not in f_23["en"]
    assert "多数方向一致" in f_23["zh"]

    # 3/3 unanimity (m>=2).
    f_33 = face(
        "-",
        "PBoC monetary conditions tightening (3/3 legs agree). ONE monetary-conditions vote.",
        "央行货币条件趋紧（3/3项指标同意）— 综合M2/剪刀差/社融的单次货币投票。",
    )
    assert f_33["en"] == (
        "Money is getting tighter at the central bank, and every part of that read agrees."
    )
    assert "most of that read agrees" not in f_33["en"]
    assert "各个部分方向一致" in f_33["zh"]

    # 1/1: n==m but m<2 — no agreement claim.
    f_11 = face(
        "+",
        "PBoC monetary conditions tilting easing (1/1 legs). ONE monetary-conditions vote.",
        "央行货币条件趋宽（1/1项指标同意）— 综合M2/剪刀差/社融的单次货币投票。",
    )
    assert f_11["en"] == "Money is tilting easier at the central bank."
    assert "most of that read agrees" not in f_11["en"]
    assert "every part of that read agrees" not in f_11["en"]

    # Parse-fail / missing counts — direction only.
    f_nc = face(
        "+",
        "PBoC monetary conditions easing. ONE monetary-conditions vote.",
        "央行货币条件趋宽。",
    )
    assert f_nc["en"] == "Money is tilting easier at the central bank."
    assert "most of that read agrees" not in f_nc["en"]
    assert "every part of that read agrees" not in f_nc["en"]


def test_money_tips_parameterized_by_m():
    """MAJOR-2: 1/1 and 2/2 tips name m, never 'Three inputs'."""
    from engine.china_tier1 import reason_faces

    f_11 = reason_faces([
        ("+",
         "PBoC monetary conditions tilting easing (1/1 legs). ONE monetary-conditions vote.",
         "央行货币条件趋宽（1/1项指标同意）。"),
    ], n=1)[0]
    assert "Three inputs" not in f_11["tip_en"]
    assert "三项输入" not in f_11["tip_zh"]
    assert "1 input" in f_11["tip_en"]
    assert "1项输入" in f_11["tip_zh"]
    assert "all point the same way" not in f_11["tip_en"]
    assert "three inputs agree" not in f_11["tip_en"].lower()

    f_22 = reason_faces([
        ("+",
         "PBoC monetary conditions easing (2/2 legs agree). ONE monetary-conditions vote.",
         "央行货币条件趋宽（2/2项指标同意）。"),
    ], n=1)[0]
    assert f_22["en"] == (
        "Money is getting easier at the central bank, and every part of that read agrees."
    )
    assert "Three inputs" not in f_22["tip_en"]
    assert "三项输入" not in f_22["tip_zh"]
    assert "2 inputs" in f_22["tip_en"]
    assert "2项输入" in f_22["tip_zh"]
    assert "all point the same way" in f_22["tip_en"]

    f_mix = reason_faces([
        ("i",
         "PBoC monetary conditions mixed (1 easing / 1 tightening / 0 neutral) — no net vote.",
         "央行货币条件分歧 — 无净投票。"),
    ], n=1)[0]
    assert "Three inputs" not in f_mix["tip_en"]
    assert "2 inputs" in f_mix["tip_en"]
    assert "do not agree" in f_mix["tip_en"]


def test_clamp_does_not_amputate_unless_policy():
    """M-c: overflow sentence falls back to worded-empty, never 'unless policy.'"""
    from engine.china_tier1 import EMPTY_REASON, _clamp_en, reason_faces

    overflow = (
        "Margin leverage is not yet crowded and southbound money has not turned "
        "seller so the downside from here is limited unless policy disappoints "
        "again in the fourth quarter."
    )
    assert _clamp_en(overflow) == ""
    face = reason_faces([("+", overflow, overflow)], n=1)[0]
    assert face["empty"] is True
    assert face["en"] == EMPTY_REASON["en"]
    assert not face["en"].endswith("unless policy.")
    assert "unless policy." not in face["en"]
    # A clause-bounded overflow keeps the leading clause, not a mid-word cut.
    bounded = (
        "Southbound money is still a buyer, and the rest of this sentence is "
        "long enough that the trailing clause must drop rather than be sawn off."
    )
    kept = _clamp_en(bounded)
    assert kept.endswith("buyer.")
    assert "sawn" not in kept


def test_clamp_contrastive_remainder_is_worded_empty():
    """MAJOR-A: dropping a contrastive tail inverts meaning — both lanes empty.

    Every probe states its measured length and must exceed the budget
    (vacuous-at-budget probes are not a test).
    """
    from engine.china_tier1 import (
        EMPTY_REASON,
        _EN_WORD_BUDGET,
        _ZH_CHAR_BUDGET,
        _clamp_en,
        _clamp_zh,
        _en_words,
        _zh_chars,
        reason_faces,
    )

    probe = (
        "The rebound looks broad across every single mainland exchange and every "
        "major sector board today, but it is not at all confirmed by southbound money."
    )
    assert len(_en_words(probe)) == 25
    assert len(_en_words(probe)) > _EN_WORD_BUDGET
    assert _clamp_en(probe) == ""
    zh_probe = (
        "反弹看起来覆盖每一家内地交易所和每一个主要板块，"
        "但并未得到南向资金的任何确认。"
    )
    assert _zh_chars(zh_probe) == 37
    assert _zh_chars(zh_probe) > _ZH_CHAR_BUDGET
    assert _clamp_zh(zh_probe) == ""
    face = reason_faces([("+", probe, zh_probe)], n=1)[0]
    assert face["empty"] is True
    assert face["en"] == EMPTY_REASON["en"]
    assert "rebound looks broad" not in face["en"]
    yet = (
        "Southbound money is buying aggressively and mainland desks are adding "
        "index exposure, yet policy support has not been confirmed by the tape "
        "this session."
    )
    assert len(_en_words(yet)) == 24
    assert len(_en_words(yet)) > _EN_WORD_BUDGET
    assert _clamp_en(yet) == ""

    # Reviewer's six failing ZH remainders (head 33 chars, full 50–51; budget 34).
    zh_head = "南向资金今天在整个内地市场大举买入并且内地交易台在尾盘增加指数敞口，"
    zh_tail = "政策支持得到确认因此需要谨慎对待。"
    assert _zh_chars(zh_head) == 33
    zh_cues = ("除非", "不过", "虽然", "只是", "没有", "无法")
    for cue in zh_cues:
        s = zh_head + cue + zh_tail
        n = _zh_chars(s)
        assert n > _ZH_CHAR_BUDGET, (cue, n)
        assert n in (50, 51), (cue, n)
        assert _clamp_zh(s) == "", (cue, n, _clamp_zh(s))

    # EN twins of those six, each measured over the 22-word budget.
    en_head = (
        "The rebound looks broad across every single mainland exchange and "
        "every major sector board today"
    )
    en_tails = (
        (", unless southbound money has confirmed the move at all today.", 25),
        ("; however southbound money has not confirmed it at all.", 24),
        (", though southbound money has quietly gone the other way today.", 25),
        (", although southbound money has quietly gone the other way today.", 25),
        (", yet southbound money has not confirmed the rebound at all today.", 26),
        (", not confirmed at all by southbound money across the whole complex.", 26),
    )
    for tail, expect in en_tails:
        s = en_head + tail
        n = len(_en_words(s))
        assert n == expect, (tail, n)
        assert n > _EN_WORD_BUDGET, (tail, n)
        assert _clamp_en(s) == "", (tail, n, _clamp_en(s))

    # Connective inside the KEPT portion must not void — normal truncation.
    zh_kept = (
        "南向资金今天在整个内地市场大举买入但并未撤退，"
        "同时成交量明显放大并且各个主要板块都有跟进。"
    )
    assert _zh_chars(zh_kept) == 43
    assert _zh_chars(zh_kept) > _ZH_CHAR_BUDGET
    zh_out = _clamp_zh(zh_kept)
    assert zh_out == "南向资金今天在整个内地市场大举买入但并未撤退。"
    assert "跟进" not in zh_out
    en_kept = (
        "Breadth is broad but thin across every mainland exchange today, "
        "and volume expanded sharply into the closing auction across every "
        "single major sector board today."
    )
    assert len(_en_words(en_kept)) == 25
    assert len(_en_words(en_kept)) > _EN_WORD_BUDGET
    en_out = _clamp_en(en_kept)
    assert en_out.startswith("Breadth is broad but thin")
    assert "volume expanded" not in en_out
    assert en_out != ""


def test_margin_crowded_band_matches_producer_threshold():
    """M-e / MINOR-6: glance copy imports china_playbook.MARGIN_CROWDED_PCTILE."""
    from engine.china_playbook import MARGIN_CROWDED_PCTILE as PLAYBOOK_MARGIN
    from engine.china_tier1 import MARGIN_CROWDED_PCTILE, reason_faces

    assert MARGIN_CROWDED_PCTILE == 85
    assert MARGIN_CROWDED_PCTILE == PLAYBOOK_MARGIN
    src = (ROOT / "engine" / "china_playbook.py").read_text(encoding="utf-8")
    assert "m[\"pctile\"] >= MARGIN_CROWDED_PCTILE" in src
    face = reason_faces([
        ("-", "Margin leverage crowded (90th percentile of float) — late-stage froth, tighten risk.",
         "融资杠杆拥挤（占流通市值 90 分位）— 后期泡沫，收紧风险。"),
    ], n=1)[0]
    assert "top 15%" in face["tip_en"]
    assert "top tenth" not in face["tip_en"]
    assert "最高 15%" in face["tip_zh"]
    assert "最高十分之一" not in face["tip_zh"]


def test_banned_only_reason_is_worded_empty():
    """m-f: a reason that strips to nothing is empty, not a delivered not-arrived lie."""
    from engine.china_tier1 import EMPTY_REASON, reason_faces

    face = reason_faces([("+", "ONE monetary-conditions vote", "ONE monetary-conditions vote")], n=1)[0]
    assert face["empty"] is True
    assert face["en"] == EMPTY_REASON["en"]


def test_zero_high_events_renders_worded_empty():
    """m-g: a day with zero high-importance prints is not a blank clickable strip."""
    from scripts.capture_china_archetype_d_evidence import fixture_vm, render_macro_block

    vm = fixture_vm()
    vm["event_strip"] = [
        {"name_en": "PMI", "name_zh": "PMI", "date": "09-30", "importance": "low"},
    ]
    html = render_macro_block(vm)
    watching = html[html.find("What we're watching"): html.find("Go deeper")]
    assert "No high-impact prints ahead this session" in watching
    assert "本会话暂无高影响数据待发" in watching
    assert "high-impact prints ahead" not in watching.replace("No high-impact prints ahead this session", "")
    assert "cnx-estrip" not in watching


def test_hero_clause_zh_does_not_fall_back_to_english():
    """m-h: missing ZH copy uses the worded-empty clause, never the EN string."""
    from engine.china_tier1 import EMPTY_CLAUSE, hero_clause

    en, zh = hero_clause({}, {"headline_en": "Risk-off tape, policy still easy.", "headline_zh": ""})
    assert en == "Risk-off tape, policy still easy."
    assert zh == EMPTY_CLAUSE[1]
    assert zh != en
    assert "Risk-off" not in zh


def test_hero_clause_reconciles_disagreement():
    """m-j: AGGRESSIVE under a red tape keeps the headline AND names Act."""
    from engine.china_tier1 import hero_clause

    pb = {"dial": {"posture": "AGGRESSIVE"}, "progress": {}, "quad_meaning": {}}
    ms = {
        "color": "red",
        "headline_en": "Breadth is breaking — every boat is sinking.",
        "headline_zh": "广度破裂——所有船都在沉。",
    }
    en, zh = hero_clause(pb, ms)
    assert en.startswith("Breadth is breaking — every boat is sinking.")
    assert "Act" in en
    assert "行动" in zh
    assert "disagree" in en
    assert "广度破裂" in zh
    assert en.index("Breadth is breaking") < en.index("Act")
    assert "tape line" in en
    assert "headline" not in en.lower()
    assert "行情线" in zh
    assert "标题" not in zh


def test_hero_clause_reconcile_requires_headline():
    """MAJOR-4 C2: disagreement without a headline does not dangle 'headline'."""
    from engine.china_tier1 import EMPTY_CLAUSE, _MID_SCARE_CLAUSE, hero_clause

    pb = {
        "dial": {"posture": "AGGRESSIVE"},
        "progress": {"phase": "mid"},
        "quad_meaning": {
            "en": "Growth-scare — both growth and prices falling, fear peaking.",
            "zh": "增长恐慌 — 增长与物价齐跌、恐慌见顶。",
        },
    }
    ms = {"color": "red", "headline_en": "", "headline_zh": ""}
    en, zh = hero_clause(pb, ms)
    assert en == _MID_SCARE_CLAUSE[0]
    assert zh == _MID_SCARE_CLAUSE[1]
    assert "headline" not in en.lower()
    assert "disagree" not in en
    assert "标题" not in zh
    empty_pb = {"dial": {"posture": "AGGRESSIVE"}, "progress": {}, "quad_meaning": {}}
    en2, zh2 = hero_clause(empty_pb, ms)
    assert (en2, zh2) == EMPTY_CLAUSE
    assert "headline" not in en2.lower()
    assert "标题" not in zh2


def test_hero_clause_reconcile_gated_per_lane():
    """MAJOR-B: EN rec only with head_en; ZH rec only with head_zh."""
    from engine.china_tier1 import EMPTY_CLAUSE, hero_clause

    pb = {"dial": {"posture": "AGGRESSIVE"}, "progress": {}, "quad_meaning": {}}
    rec_en = (
        "The tape and the playbook disagree — stance is Act. "
        "Honour both reads; the tape line is context — act on the posture, not the wording."
    )
    rec_zh = "盘面与策略姿态不一致——姿态是行动。两边都要看，行情线是背景——按姿态操作，而非按措辞。"

    # C3: disagree, head_en set, headline_zh "".
    en, zh = hero_clause(pb, {
        "color": "red", "headline_en": "Breadth is breaking.", "headline_zh": "",
    })
    assert en == f"Breadth is breaking. {rec_en}"
    assert zh == EMPTY_CLAUSE[1]
    assert rec_zh not in zh
    assert "标题" not in zh
    assert "行情线" not in zh
    assert "disagree" not in zh

    # Symmetric: head_zh set, head_en "".
    en, zh = hero_clause(pb, {
        "color": "red", "headline_en": "", "headline_zh": "广度破裂。",
    })
    assert en == EMPTY_CLAUSE[0]
    assert rec_en not in en
    assert "headline" not in en.lower()
    assert "disagree" not in en
    assert zh == f"广度破裂。{rec_zh}"
    assert "标题" not in zh

    # Both empty — already the C2 empty-pb path.
    en, zh = hero_clause(pb, {"color": "red", "headline_en": "", "headline_zh": ""})
    assert (en, zh) == EMPTY_CLAUSE
    assert rec_en not in en
    assert rec_zh not in zh


def test_agree_level_rejects_n_gt_m():
    """NIT-D: n>m is majority in the old guardless code; contract says none."""
    from engine.china_tier1 import _agree_level

    assert _agree_level(4, 3) == "none"
    assert _agree_level(5, 2) == "none"
    assert _agree_level(2, 3) == "majority"
    assert _agree_level(3, 3) == "unanimous"
    assert _agree_level(1, 3) == "none"


def test_leg_count_paren_contract_both_lanes():
    """MINOR-C: parenthetical 'agree'/同意 only at majority/unanimity, both lanes."""
    from engine.china_playbook import _dial
    from engine.china_tier1 import _leg_count_paren, _leg_counts

    assert _leg_count_paren(2, 3) == ("(2/3 legs agree)", "（2/3项指标同意）")
    assert _leg_count_paren(3, 3) == ("(3/3 legs agree)", "（3/3项指标同意）")
    assert _leg_count_paren(1, 3) == ("(1 of 3 legs)", "（3项中1项）")
    assert _leg_count_paren(1, 1) == ("(1 of 1 legs)", "（1项中1项）")

    n, m = _leg_counts("tightening (1 of 3 legs).", "央行货币条件趋紧（3项中1项）。")
    assert (n, m) == (1, 3)
    n, m = _leg_counts("tightening (2/3 legs agree).", "央行货币条件趋紧（2/3项指标同意）。")
    assert (n, m) == (2, 3)

    def money_reason(latest, internals):
        reasons = _dial(latest, internals)["reasons"]
        return next(r for r in reasons if "PBoC monetary" in r[1] or "央行货币条件" in r[2])

    # Easing 3/3 unanimous, 2/3 majority, 1/3 plurality.
    r = money_reason(
        {"quad": "Q2", "liquidity_overlay": "expanding"},
        {"credit": {
            "scissors": 3.0, "credit_impulse": 0.5, "credit_impulse_6mo": 0.3,
        }},
    )
    assert r[0] == "+"
    assert "(3/3 legs agree)" in r[1]
    assert "（3/3项指标同意）" in r[2]
    assert "of 3 legs" not in r[1]
    assert "项中" not in r[2]

    r = money_reason(
        {"quad": "Q2", "liquidity_overlay": "expanding"},
        {"credit": {
            "scissors": 3.0, "credit_impulse": 0.1, "credit_impulse_6mo": 0.2,
        }},
    )
    assert "(2/3 legs agree)" in r[1]
    assert "（2/3项指标同意）" in r[2]
    assert "of 3 legs" not in r[1]

    r = money_reason(
        {"quad": "Q2", "liquidity_overlay": "expanding"},
        {"credit": {
            "scissors": 0.0, "credit_impulse": 0.1, "credit_impulse_6mo": 0.2,
        }},
    )
    assert "(1 of 3 legs)" in r[1]
    assert "（3项中1项）" in r[2]
    assert "legs agree" not in r[1]
    assert "项指标同意" not in r[2]

    # Tightening 3/3, 2/3, 1/3.
    r = money_reason(
        {"quad": "Q2", "liquidity_overlay": "contracting"},
        {"credit": {
            "scissors": -3.0, "credit_impulse": -0.5, "credit_impulse_6mo": -0.3,
        }},
    )
    assert r[0] == "-"
    assert "(3/3 legs agree)" in r[1]
    assert "（3/3项指标同意）" in r[2]

    r = money_reason(
        {"quad": "Q2", "liquidity_overlay": "contracting"},
        {"credit": {
            "scissors": -3.0, "credit_impulse": 0.1, "credit_impulse_6mo": 0.2,
        }},
    )
    assert "(2/3 legs agree)" in r[1]
    assert "（2/3项指标同意）" in r[2]

    r = money_reason(
        {"quad": "Q2", "liquidity_overlay": "contracting"},
        {"credit": {
            "scissors": 0.0, "credit_impulse": 0.1, "credit_impulse_6mo": 0.2,
        }},
    )
    assert "(1 of 3 legs)" in r[1]
    assert "（3项中1项）" in r[2]
    assert "legs agree" not in r[1]
    assert "项指标同意" not in r[2]


def test_duplicate_reasons_dedupe():
    """n-l: three identical producer reasons render one row + two empties."""
    from engine.china_tier1 import EMPTY_REASON, reason_faces

    item = ("+", "Southbound buying strong — mainland money leaning risk-on.",
            "南向资金大幅净买入 — 内地资金偏向风险偏好。")
    faces = reason_faces([item, item, item], n=3)
    assert faces[0]["en"] == item[1] or "Southbound" in faces[0]["en"] or faces[0]["empty"] is False
    assert sum(1 for f in faces if not f.get("empty")) == 1
    assert sum(1 for f in faces if f.get("empty")) == 2
    assert faces[1]["en"] == EMPTY_REASON["en"]


def test_dedupe_does_not_promote_fourth_over_distinct_empties():
    """NIT-7: two distinct worded-empty reasons occupy two slots; 4th stays out."""
    from engine.china_tier1 import EMPTY_REASON, reason_faces

    long_a = (
        "The rebound looks broad across every single mainland exchange and every "
        "major sector board today, but it is not at all confirmed by southbound money."
    )
    long_b = (
        "Southbound money is buying aggressively and mainland desks are adding "
        "index exposure, yet policy support has not been confirmed by the tape "
        "this session."
    )
    zh_a = "反弹看起来覆盖每一家内地交易所和每一个主要板块，但并未得到南向资金的任何确认。"
    zh_b = "南向资金在积极买入而且内地席位还在继续加仓指数敞口，然而政策支持尚未被盘面确认。"
    fourth = (
        "+",
        "Southbound buying strong — mainland money leaning risk-on.",
        "南向资金大幅净买入 — 内地资金偏向风险偏好。",
    )
    faces = reason_faces(
        [("+", long_a, zh_a), ("+", long_b, zh_b), fourth, ("-", "other", "其他")],
        n=3,
    )
    assert faces[0]["empty"] is True
    assert faces[1]["empty"] is True
    assert faces[0]["en"] == EMPTY_REASON["en"]
    assert faces[1]["en"] == EMPTY_REASON["en"]
    assert "Southbound buying strong" in faces[2]["en"] or "Southbound" in faces[2]["en"]
    assert "other" not in faces[2]["en"]


def test_explicit_sign_outranks_mixed_regex():
    """MINOR-5: sign '-' beats an unanchored 'mixed' later in the sentence."""
    from engine.china_tier1 import reason_faces

    face = reason_faces([
        ("-",
         "PBoC monetary conditions tightening (2/3 legs agree). mixed signals elsewhere",
         "央行货币条件趋紧（2/3项指标同意）。"),
    ], n=1)[0]
    assert face["sign"] == "−"
    assert "tighter" in face["en"]
    assert "no single vote" not in face["en"]
    assert "mixed — no single vote" not in face["en"]


def test_mobile_dial_clips_overflow():
    """M-d: 390 dial restores overflow:hidden; skyToggleFx is the harness's job."""
    assert "body.page-china .cnx-wrap .dial{margin:4px auto 12px;overflow:hidden;max-width:220px;height:auto;min-height:160px;background:none}" in SRC
    assert "overflow:visible;max-width:220px" not in SRC
    assert "body.page-china .cnx-wrap .dial{text-align:center;height:auto;background:none;border-radius:0}" in SRC


def test_docstring_cites_real_stance_precedent():
    """m-i: Act/Get ready provenance is master_brain / cycles, not a missing hk_tier1."""
    src = (ROOT / "engine" / "china_tier1.py").read_text(encoding="utf-8")
    assert "hk_tier1" not in src
    assert "master_brain" in src
    assert "cycles.py" in src


def test_defect_state_cells_named_in_readme():
    """Evidence gap: README names the defect-state cells including hero-reconcile."""
    from scripts.capture_china_archetype_d_evidence import DEFECT_CELLS

    readme = (ROOT / "mockups" / "evidence" / "china-archetype-d" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "Defect-state cells" in readme
    names = {row[0] for row in DEFECT_CELLS}
    assert names == {
        "mixed-money",
        "majority-money",
        "worded-empty",
        "unknown-posture",
        "hero-reconcile",
    }
    for name in names:
        assert name in readme
    assert "defect-hero-reconcile-dark-en-desktop.png" in readme
    assert "defect-hero-reconcile-light-en-desktop.png" in readme
    assert "defect-hero-reconcile-dark-zh-desktop.png" in readme
    assert "defect-hero-reconcile-light-zh-desktop.png" in readme
