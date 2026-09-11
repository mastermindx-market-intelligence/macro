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


def test_g2_events_slice_label_from_one_source():
    """Spec §2.1: population from event_strip; shown count from the same [:4] loop."""
    wrap = _wrap()
    assert "{% set _ev_all = event_strip or [] %}" in wrap
    assert "{% set _ev_shown = _ev_all[:4] %}" in wrap
    assert "{{ _ev_all | length }}" in wrap
    assert "{{ _ev_shown | length }}" in wrap
    assert 'high-impact prints ahead' in wrap
    assert "shown · full calendar →" in wrap
    assert "项已显示 · 完整日历 →" in wrap


def test_g2_duplicate_45_percent_row_removed():
    """Spec §2.2: keep agreement_pct at the Signals strip; delete the kv twin."""
    dialogs = _dialogs()
    assert "signal_stack.agreement_pct" in dialogs
    assert "t('Signal agreement','信号一致度')" not in dialogs
    assert "(latest.confidence*100)|round|int" not in dialogs


def test_g3_banned_tokens_absent_from_l1_except_tips():
    """Spec §0 G3 / §3: banned tokens only in data-tip-* or dialog bodies."""
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
    for token in banned:
        for m in re.finditer(re.escape(token), wrap):
            # Allow the token only inside a data-tip-* attribute on the same tag.
            left = wrap[max(0, m.start() - 200) : m.start()]
            assert "data-tip-en=" in left or "data-tip-zh=" in left, (
                f"banned token {token!r} at L1 outside a data-tip"
            )


def test_g3_tier1_what_to_do_copy():
    """Spec §3.1: frozen stance rows present byte-for-byte."""
    wrap = _wrap()
    assert "Fear like this has usually been a buying window, not a top" in wrap
    assert "这种恐慌通常是买入窗口，而不是顶部" in wrap
    assert "Money is getting tighter at the central bank" in wrap
    assert "央行层面的货币条件正在收紧" in wrap
    assert "Borrowed money in A-shares is crowded" in wrap
    assert "A股杠杆资金拥挤" in wrap
    assert "Everything is falling together" in wrap
    assert "全市场同步下跌" in wrap


def test_g4_growth_scare_not_inside_l_zh_in_glance():
    """Spec §4.4 / G4: Growth-Scare never appears inside an l-zh span on L1."""
    wrap = _wrap()
    assert not re.search(r'l-zh[^<]*>[^<]*Growth-Scare', wrap)
    assert "<span class=\"l-zh\">增长恐慌</span>" in wrap
    assert "<span class=\"l-en\">GROWTH SCARE</span>" in wrap


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
