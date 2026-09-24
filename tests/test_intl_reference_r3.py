"""Static contract for the international vNext R3 design reference.

The reference is a design artifact, not production. These tests pin the R2
review findings so implementation cannot earn approval by deleting user jobs,
inventing authority, or hiding degraded states.
"""
from __future__ import annotations

import hashlib
import html as html_lib
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "mockups/refs/institutionalize/intl/reference-r2.html"
R3 = ROOT / "mockups/refs/institutionalize/intl/reference-r3.html"
R2_SHA256 = "9fdbe42f1d6b5d55856f0f44029e6a1a8087e7624e5fd20d5c6973a4e7d67918"


def _html() -> str:
    assert R3.exists(), "R3 reference is not built yet"
    return R3.read_text(encoding="utf-8")


def _attr_values(html: str, name: str) -> set[str]:
    return set(re.findall(rf'{re.escape(name)}="([^"]+)"', html))


def test_r2_remains_immutable_and_r3_is_a_new_artifact():
    assert hashlib.sha256(R2.read_bytes()).hexdigest() == R2_SHA256
    html = _html()
    assert "International Markets — vNext reference (R3)" in html
    assert "REFERENCE FIXTURE · NOT LIVE" in html


def test_r3_preserves_shell_overview_and_six_act_flow():
    html = _html()
    visible = html_lib.unescape(html)
    assert 'data-preserve-shell="_site_nav.html.j2"' in html
    assert 'data-preserve-overview="global_regime_html"' in html
    for act in (
        "Global Call",
        "Global Pulse + Material Risk Radar",
        "Rotation & Turns",
        "Transmission & Fragility",
        "Country Inspector",
        "Desk Posture + Deep Desks",
    ):
        assert act in visible
    assert 'id="dollar-drivers"' in html
    assert "What's driving the dollar?" in visible


def test_r3_uses_real_destinations_and_preserves_stocks_mode():
    html = _html()
    assert 'href="intl.html"' not in html
    assert 'data-preserve-route="intl_stocks.html"' in html
    assert 'href="intl_stocks.html"' in html
    for route in ("forex.html", "bonds.html", "sector_central.html"):
        assert f'href="{route}"' in html
    fragment_links = re.findall(r'href="#([^"]+)"', html)
    for fragment in fragment_links:
        assert f'id="{fragment}"' in html, fragment
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith("#"):
            assert f'id="{href[1:]}"' in html, href
            continue
        assert "://" not in href, href
        assert (ROOT / "site" / href).is_file(), href


def test_r3_covers_full_market_and_economy_universes():
    html = _html()
    assert _attr_values(html, "data-turn-market") == {
        "US", "CN", "HK", "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    assert _attr_values(html, "data-economy") == {
        "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    assert _attr_values(html, "data-pressure-market") == {
        "US", "CN", "HK", "CA", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    assert _attr_values(html, "data-fragility-country") == {
        "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }


def test_r3_restores_horizons_and_change_shape_without_fake_rank_history():
    html = _html()
    assert _attr_values(html, "data-horizon") == {"1m", "3m", "6m", "12m", "ytd"}
    assert _attr_values(html, "data-label-en") == {"1M", "3M", "6M", "12M", "YTD"}
    assert _attr_values(html, "data-label-zh") == {"1月", "3月", "6月", "12月", "年初至今"}
    assert "button.textContent.trim()" not in html
    assert "button.dataset.labelZh" in html and "button.dataset.labelEn" in html
    assert 'data-rotation-source="engine-result"' in html
    assert "20D ago" not in html
    assert "historical rank" not in html.lower()
    assert "sparkline" in html.lower()


def test_r3_removes_tautological_odds_and_unsourced_quantitative_bars():
    html = _html()
    assert "radar-odds" not in html
    assert "dip odds" not in html.lower()
    assert "vs base" not in html.lower()
    assert "sender-bar" not in html
    assert "press-bar" not in html
    assert 'data-unsourced-magnitude="true"' not in html


def test_r3_market_decomposition_is_arithmetically_reconcilable():
    html = _html()
    cards = re.findall(
        r'<[^>]+data-performance-market="([^"]+)"[^>]*'
        r'data-usd="([+-]?[0-9.]+)"[^>]*'
        r'data-local="([+-]?[0-9.]+)"[^>]*'
        r'data-fx-contribution="([+-]?[0-9.]+)"',
        html,
    )
    assert len(cards) == 7
    for market, usd, local, fx in cards:
        assert math.isclose(float(usd), float(local) + float(fx), abs_tol=0.05), market
    assert "FX contribution to USD return" in html
    assert "Currency move" in html


def test_r3_does_not_expose_misleading_partial_rotation_derivation():
    html = _html()
    rotation = re.search(r'<section[^>]+id="rotation-turns".*?</section>', html, re.S)
    assert rotation
    block = rotation.group(0)
    assert "Engine rotation rank" in block
    assert "rs20" not in block.lower()
    assert "rs5" not in block.lower()
    assert "held back" not in block.lower()
    assert "formula inputs" not in block.lower()


def test_r3_degraded_states_are_organ_local_and_fail_open():
    html = _html()
    assert 'data-demo-organ="global-pulse"' in html
    assert _attr_values(html, "data-organ-state") >= {"loading", "empty", "stale", "error"}
    assert "body.is-error .real-content" not in html
    assert "body.is-empty .real-content" not in html
    assert "body.is-loading .real-content" not in html
    assert "body.is-stale .real-content" not in html
    assert 'data-organ="global-pulse"' in html
    assert 'data-organ="dollar-drivers"' in html


def test_r3_separates_direction_ink_from_status_semantics():
    html = _html()
    for token in ("--ink-up", "--ink-down", "--ink-warn", "--status-danger", "--status-good"):
        assert token in html
    status_rules = "\n".join(re.findall(r'\.(?:status|state)-[^\{]+\{[^}]+\}', html))
    assert "--status-danger" in status_rules
    assert "--status-good" in status_rules
    assert "var(--up)" not in status_rules
    assert "var(--down)" not in status_rules
    zh_block = re.search(r'html\[data-lang="zh"\]\s*\{([^}]+)\}', html)
    assert zh_block
    assert "--status-danger" not in zh_block.group(1)
    assert "--status-good" not in zh_block.group(1)


def test_r3_light_and_cjk_text_use_the_canonical_readability_floor():
    html = _html()
    assert 'html[data-theme="light"]' in html
    assert 'html[data-lang="zh"] :where(' in html
    assert "letter-spacing:0" in html.replace(" ", "")
    sizes = [float(v) for v in re.findall(r'font-size\s*:\s*([0-9.]+)px', html)]
    assert sizes and min(sizes) >= 10.0
    rrg_rule = re.search(r'\.rrg-pill\s*\{([^}]+)\}', html)
    assert rrg_rule
    assert "#fff" not in rrg_rule.group(1).lower()
    assert "var(--ink-" in rrg_rule.group(1)


def test_r3_removes_ambiguous_or_duplicate_receipts():
    html = _html()
    assert not re.search(r'\(h\s+[0-9.]+\)', html)
    assert html.count("Dragged by") == 1
    assert "Net is recomputed from the displayed rounded components" in html
    assert "Australia" in html and 'data-fragility-country="AU"' in html
    assert "a transmission read, not a statement of cause" in html


def test_r3_fixed_price_paths_are_neutral_and_separate_from_return_horizons():
    html = _html()
    pulse = re.search(r'<section[^>]+id="global-pulse".*?</section>', html, re.S)
    assert pulse
    block = pulse.group(0)
    cards = re.findall(r'<article class="market-card".*?</article>', block, re.S)
    assert len(cards) == 7
    for card in cards:
        assert 'data-window-sessions="84"' in card
        assert 'data-horizon-independent="true"' in card
        spark = re.search(r'<div class="sparkline".*?</div>', card, re.S)
        assert spark
        assert "var(--up)" not in spark.group(0)
        assert "var(--down)" not in spark.group(0)
        assert "var(--link)" in spark.group(0)
    visible = html_lib.unescape(block)
    assert "Selected return window" in visible
    assert "84-session price path · fixed" in visible
    assert "所选收益周期" in visible
    assert "84个交易日价格路径 · 固定" in visible
    whole_visible = html_lib.unescape(html)
    assert 'data-leadership-horizon="3m"' in html
    assert "3M relative leadership" in whole_visible
    assert "3个月相对领先" in whole_visible


def test_r3_turn_board_repeats_exact_accepted_state_and_stance_vocabulary():
    html = _html()
    us = re.search(r'<article class="turn-cell" data-turn-market="US".*?</article>', html, re.S)
    cn = re.search(r'<article class="turn-cell" data-turn-market="CN".*?</article>', html, re.S)
    assert us and cn
    assert us.group(0).count("Healthy trend") == 2
    assert us.group(0).count("趋势健康") == 2
    assert "Hold positions" not in us.group(0)
    assert "持有仓位" not in us.group(0)
    assert "Repair attempt" in cn.group(0)
    assert "修复尝试" in cn.group(0)
    assert "Unconfirmed — wait for breadth and external pressure to improve" in cn.group(0)
    assert "尚未确认——等待市场宽度与外部压力改善" in cn.group(0)
    assert "Watch the repair" not in cn.group(0)
    assert "观察修复" not in cn.group(0)


def test_r3_discloses_short_rate_and_partial_recession_methodology():
    html = _html()
    inspector = re.search(r'<section[^>]+id="country-inspector".*?</section>', html, re.S)
    assert inspector
    block = inspector.group(0)
    visible = html_lib.unescape(block)
    assert "Short / policy rate" in visible
    assert "短端／政策利率" in visible
    assert "three-month market-rate proxy" in visible
    assert "3个月市场利率代理" in visible
    assert "separate from the realized central-bank policy-rate table in Act 6" in visible
    assert "与第6部分的已实现央行政策利率表分开" in visible
    assert "Policy rate" not in visible
    tw_row = re.search(r'<tr[^>]+data-economy="TW".*?</tr>', block, re.S)
    tw_panel = re.search(r'<article[^>]+id="country-TW".*?</article>', block, re.S)
    assert tw_row and tw_panel
    assert 'data-recession-legs="1/3"' in tw_row.group(0)
    assert "0 · 1/3 legs" in html_lib.unescape(tw_row.group(0))
    assert "0/100 from the equity-drawdown leg only" in html_lib.unescape(tw_panel.group(0))
    assert "仅来自股市回撤一项" in html_lib.unescape(tw_panel.group(0))
    assert "not a probability" in html_lib.unescape(tw_panel.group(0))
    assert "不是概率" in html_lib.unescape(tw_panel.group(0))
    assert "0.98%" in html


def test_r3_preserves_populated_regional_sector_rotation_without_duplication():
    html = _html()
    sector = re.search(r'<article[^>]+id="sector-intelligence".*?</article>', html, re.S)
    assert sector
    block = html_lib.unescape(sector.group(0))
    assert "zero qualifying" not in block.lower()
    assert "No qualifying regional sector rows" not in block
    assert "3-month relative-strength board" in block
    assert "3个月相对强弱看板" in block
    assert 'href="intl_stocks.html"' in sector.group(0)
    assert "separately preserved International Stock Dashboard" in block


def test_r3_true_locale_copy_covers_challenged_labels_and_fixture_controls():
    html = _html()
    visible = html_lib.unescape(html)
    for en, zh in (
        ("Dragged by", "拖累来源"),
        ("United States", "美国"),
        ("World", "全球"),
        ("Jul 2023", "2023年7月"),
        ("Reference state", "参考状态"),
        ("Default", "默认"),
        ("Loading", "加载中"),
        ("Empty", "空状态"),
        ("Stale", "已陈旧"),
        ("Error", "错误"),
        ("Dark", "深色"),
        ("Light", "浅色"),
    ):
        pair = f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'
        assert pair in html, pair
    assert "US-only regime" in visible
    assert "仅美国周期" in visible
    assert "separate from the global 66/100 verdict" in visible
    assert "与第1部分的全球66/100总判断分开" in visible


def test_r3_deep_link_labels_describe_their_actual_fragments():
    html = _html()
    for misleading in ("Open regime map", "Open ranked reference views", "Open full comparison"):
        assert misleading not in html
    for label, fragment in (
        ("Open cross-country comparison", "macro-comparison"),
        ("Open current rotation and ranks", "rotation-turns"),
        ("Open performance comparison", "global-pulse"),
    ):
        assert re.search(rf'href="#{fragment}"[^>]*>.*?{re.escape(label)}', html, re.S)
    assert "Eurozone fragmentation" in html
    assert "欧元区分化" in html


def test_r3_initial_locale_synchronizes_selected_horizon_labels():
    html = _html()
    assert "const initialHorizon = document.querySelector('[data-horizon][aria-pressed=\"true\"]');" in html
    assert "if (initialHorizon) syncHorizonLabels(initialHorizon);" in html
