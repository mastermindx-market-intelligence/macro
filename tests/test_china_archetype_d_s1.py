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
    assert "3 " in watching and "high-impact prints ahead" in watching
    assert "5 high-impact" not in watching
    assert "3" in watching and "of" in watching


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
    assert "{{ _cnh.meaning_en }}" in card
    assert "{{ _cnh.meaning_zh }}" in card


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
    """M4: surviving CNH surface carries CHINA_TILE_COPY meaning lines."""
    from jinja2 import DictLoader, Environment
    from scripts.build_china import CHINA_TILE_COPY

    snippet = """
    {% set _cnh = cnh %}
    <div class="cnx-ihcard"><div class="t">USD/CNH</div><div class="p">{{ _cnh.level }}</div>
    <span class="cnx-nchip">offshore yuan</span>
    {% if _cnh.meaning_en %}<span class="cnx-orient"><span class="l-en">{{ _cnh.meaning_en }}</span><span class="l-zh">{{ _cnh.meaning_zh }}</span></span>{% endif %}</div>
    """
    env = Environment(loader=DictLoader({"s": snippet}), autoescape=False)
    html = env.get_template("s").render(cnh={
        "level": "7.123",
        "meaning_en": CHINA_TILE_COPY["USDCNH"]["meaning_en"],
        "meaning_zh": CHINA_TILE_COPY["USDCNH"]["meaning_zh"],
    })
    assert "quoted as yuan per US dollar — higher = a weaker yuan" in html
    assert "以美元兑人民币报价 — 数值升高 = 人民币走弱" in html
    assert "cnx-orient" in html
