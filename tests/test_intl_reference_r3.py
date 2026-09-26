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
        "US", "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
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


def test_r3_fixed_price_paths_are_semantic_and_visually_separate_from_return_horizons():
    html = _html()
    pulse = re.search(r'<section[^>]+id="global-pulse".*?</section>', html, re.S)
    assert pulse
    block = pulse.group(0)
    path_cards = re.findall(r'<article class="path-card".*?</article>', block, re.S)
    return_cards = re.findall(r'<article class="market-card".*?</article>', block, re.S)
    assert len(path_cards) == 7
    assert len(return_cards) == 7
    expected_directions = {
        "KR": "up", "TW": "up", "JP": "up", "EZ": "up",
        "GB": "up", "IN": "down", "AU": "up",
    }
    for card in path_cards:
        market = re.search(r'data-path-market="([^"]+)"', card)
        assert market
        direction = expected_directions[market.group(1)]
        assert 'data-window-sessions="84"' in card
        assert 'data-horizon-independent="true"' in card
        assert f'data-path-direction="{direction}"' in card
        spark = re.search(r'<div class="sparkline".*?</div>', card, re.S)
        assert spark
        assert "var(--link)" not in spark.group(0)
        assert f"var(--ink-{direction})" in spark.group(0)
    for card in return_cards:
        assert "sparkline" not in card
    visible = html_lib.unescape(block)
    assert "Fixed 84-session price paths" in visible
    assert "Selected return decomposition" in visible
    assert "固定84个交易日价格路径" in visible
    assert "所选收益周期拆分" in visible
    assert 'data-chart-role="fixed-84-session"' in block
    assert 'data-control-scope="return-decomposition-only"' in block
    assert "rotation-spark" not in html
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


def test_r3_initial_locale_synchronizes_selected_horizon_labels_and_controls():
    html = _html()
    assert "const syncInitialControls = () =>" in html
    assert "item.dataset.themeButton === root.dataset.theme" in html
    assert "item.dataset.langButton === root.dataset.lang" in html
    assert "syncInitialControls();" in html
    assert "const initialHorizon = document.querySelector('[data-horizon][aria-pressed=\"true\"]');" in html
    assert "if (initialHorizon) syncHorizonLabels(initialHorizon);" in html


def test_r3_shell_matches_canonical_product_chrome_jobs():
    html = _html()
    assert "MASTERMINDX" in html
    assert 'class="nav-search"' in html
    assert 'aria-label="Search stocks"' in html
    assert "Search any stock" in html
    assert 'class="terminal-link"' in html
    assert 'class="shell-settings"' in html
    assert _attr_values(html, "data-shell-market") == {
        "US", "CN", "HK", "CA", "INTL", "RESEARCH", "OTHER"
    }
    assert 'data-theme-button="dark"' in html
    assert 'data-theme-button="light"' in html
    assert 'data-lang-button="en"' in html
    assert 'data-lang-button="zh"' in html


def test_r3_preserves_the_full_upstream_overview_job():
    html = _html()
    overview = re.search(r'<section[^>]+class="overview".*?</section>', html, re.S)
    assert overview
    block = html_lib.unescape(overview.group(0))
    assert set(re.findall(r'data-overview-market="([^"]+)"', block)) == {
        "US", "HK", "CN", "BONDS", "COMMODITIES"
    }
    assert len(re.findall(r'data-overview-signal="[^"]+"', block)) == 4
    assert len(re.findall(r'data-overview-why="[^"]+"', block)) == 3
    assert len(re.findall(r'data-overview-watch="[^"]+"', block)) == 3
    for route in (
        "macro_context.html", "sector_central.html", "signal_lab.html",
        "macro_signals.html", "news.html", "macro_monetary.html",
    ):
        assert f'href="{route}"' in overview.group(0)
    assert "Five-market readout" in block
    assert "One scale, five markets" not in block
    assert "五市场读数" in block
    assert "同一标尺，五个市场" not in block
    assert "61/100" in block and "US-only" in block


def test_r3_restores_international_risk_desk_synthesis_and_hot_channel():
    html = _html()
    risk = re.search(r'<article[^>]+id="international-risk-desk".*?</article>', html, re.S)
    assert risk
    block = html_lib.unescape(risk.group(0))
    assert set(re.findall(r'data-risk-desk-domain="([^"]+)"', block)) == {
        "EM", "CONTAGION", "USD", "FUNDING"
    }
    assert "1 / 6 active" in block
    assert "no stronger state label is inferred" in block.lower()
    assert "No action needed · EM positions" in block
    assert "1 of 5 US transmission channels are hot" in block
    assert "Dollar moving on rate differences, not fear" in block
    assert "Swap lines ~$0.1bn outstanding" in block
    assert len(re.findall(r'data-transmission-hot="true"', html)) == 1
    assert len(re.findall(r'data-transmission-channel="[^"]+"', html)) == 5


def test_r3_fragility_map_restores_anchor_market_and_valued_breaches():
    html = _html()
    fragility = re.search(
        r'(<div class="fragility-row" data-fragility-country="GB".*?)(?=<div class="fragility-row"|</div>\s*<p class="caveat")',
        html,
        re.S,
    )
    united_states = re.search(
        r'(<div class="fragility-row" data-fragility-country="US".*?)(?=<div class="fragility-row"|</div>\s*<p class="caveat")',
        html,
        re.S,
    )
    assert fragility and united_states
    gb = html_lib.unescape(fragility.group(1))
    us = html_lib.unescape(united_states.group(1))
    for block, values in (
        (gb, ("102%", "-3.1%", "-5.4%")),
        (us, ("124%", "-3.6%", "-6.8%")),
    ):
        assert 'data-warning-count="3/4"' in block
        assert all(value in block for value in values)
        assert block.count('data-fragility-breach=') == 3
    assert "8 / 8" in html
    assert "Every declared economy and the US anchor are accounted for" in html


def test_r3_turn_cards_preserve_metrics_risk_driver_and_receipt_depth():
    html = _html()
    cards = re.findall(
        r'(<article class="turn-cell" data-turn-market="([^"]+)".*?</article>)',
        html,
        re.S,
    )
    assert len(cards) == 10
    assert {market for _card, market in cards} == {
        "US", "CN", "HK", "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    for card, market in cards:
        assert 'class="turn-metrics"' in card, market
        assert 'class="turn-risk"' in card, market
        assert 'class="turn-driver"' in card, market
        assert 'class="turn-receipt"' in card, market
        assert 'data-turn-evidence=' in card, market
        assert "20d" in html_lib.unescape(card), market
        assert "Off high" in html_lib.unescape(card), market
    for market in ("US", "CN"):
        card = next(card for card, code in cards if code == market)
        assert 'data-risk-state="unavailable"' in card
        assert "Not published for this market" in html_lib.unescape(card)


def test_r3_restores_rrg_plot_and_reference_depth_views():
    html = _html()
    assert len(re.findall(r'data-rrg-point="(?:GB|TW|EZ|AU|KR|IN|JP)"', html)) == 7
    assert len(re.findall(r'data-regime-point="(?:KR|TW|JP|EZ|GB|IN|AU)"', html)) == 7
    assert len(re.findall(r'data-correlation-cell="[^"]+"', html)) >= 49
    assert len(re.findall(r'data-league-row="(?:KR|TW|JP|EZ|GB|IN|AU)"', html)) == 7
    visible = html_lib.unescape(html)
    assert "Growth × inflation map" in visible
    assert "Pairwise correlation heatmap" in visible
    assert "Comparable league tables" in visible
    assert "Average correlation" in visible


def test_r3_pressure_flow_keeps_source_backed_magnitudes():
    html = _html()
    rows = re.findall(
        r'(<div class="pressure-row" data-pressure-market="([^"]+)".*?)(?=<div class="pressure-row" data-pressure-market=|</div>\s*<p class="caveat")',
        html,
        re.S,
    )
    assert len(rows) == 10
    for row, market in rows:
        assert 'data-pressure-magnitude=' in row, market
        assert row.count('class="pressure-source"') >= 3, market
        assert row.count('data-pressure-share=') >= 3, market
    assert "source-backed pressure magnitude" in html.lower()
    assert 'data-unsourced-magnitude="true"' not in html


def test_r3_macro_table_uses_semantic_state_ink_and_mobile_row_identity():
    html = _html()
    macro = re.search(r'<table class="macro-table".*?</table>', html, re.S)
    assert macro
    block = macro.group(0)
    for state_class in ("state-danger", "state-caution", "state-good", "state-neutral"):
        assert state_class in block
    assert 'class="sticky-market"' in block
    assert ".macro-table .sticky-market" in html
    assert "position:sticky" in html
    assert "left:0" in html.replace(" ", "")


def test_r3_rates_desk_restores_full_comparison_contract():
    html = _html()
    desk = re.search(r'<article[^>]+id="rates-curves".*?</article>', html, re.S)
    assert desk
    block = html_lib.unescape(desk.group(0))
    assert set(re.findall(r'data-rate-market="([^"]+)"', desk.group(0))) == {
        "US", "JP", "KR", "TW", "IN", "AU", "GB", "EZ"
    }
    assert "Long-yield drift" in block
    assert "Carry vs US" in block
    assert 'data-rate-market="TW" data-null-series="true"' in desk.group(0)
    assert "typed null" in block.lower()


def test_r3_removes_redundant_posture_projection_and_compresses_structural_nulls():
    html = _html()
    assert 'id="desk-posture"' not in html
    assert 'class="posture-list"' not in html
    assert html.count("Projection of the accepted stance field only") == 0
    assert html.count("No concurrent structural warning") <= 1


def test_r3_organ_controls_fail_with_the_organ_and_errors_are_distinct():
    html = _html()
    organ = re.search(r'<div class="panel organ" data-organ="global-pulse".*?</div>\s*</section>', html, re.S)
    assert organ
    block = organ.group(0)
    assert 'class="organ-content"' in block
    assert 'class="organ-controls"' in block
    assert block.index('class="organ-controls"') > block.index('class="organ-content"')
    error = re.search(r'data-organ-state="error"[^>]*>(.*?)</div>', block, re.S)
    empty = re.search(r'data-organ-state="empty"[^>]*>(.*?)</div>', block, re.S)
    assert error and empty
    assert "status-danger" in error.group(1)
    assert "Retry data organ" in html_lib.unescape(error.group(1))
    assert "status-danger" not in empty.group(1)


def test_r3_rrg_membership_geometry_matches_declared_engine_quadrants():
    html = _html()
    rows = re.findall(
        r'data-rrg-point="([^"]+)"[^>]+style="--rrg-x:([0-9.]+)%;--rrg-y:([0-9.]+)%"[^>]+title="([^"]+)"[^>]*>.*?<small>.*?<span class="l-en">([^<]+)</span>',
        html,
        re.S,
    )
    assert len(rows) == 7

    def quadrant(x: float, y: float) -> str:
        if x < 50 and y < 50:
            return "Improving"
        if x >= 50 and y < 50:
            return "Leading"
        if x < 50 and y >= 50:
            return "Lagging"
        return "Weakening"

    for market, x, y, title, label in rows:
        assert quadrant(float(x), float(y)) == label, market
        assert label in title
    assert html.count("data-rrg-level=") == 7
    assert html.count("data-rrg-momentum=") == 7


def test_r3_turn_board_survives_performance_organ_failure():
    html = _html()
    organ = re.search(
        r'<div class="panel organ" data-organ="global-pulse".*?</div>\s*</section>',
        html,
        re.S,
    )
    assert organ
    block = organ.group(0)
    assert 'class="turn-grid"' in block
    assert 'data-independent-turn-board="true"' in block
    assert '.organ[data-state="loading"] .organ-content' not in html
    assert '.organ[data-state="empty"] .organ-content' not in html
    assert '.organ[data-state="error"] .organ-content' not in html
    assert '.organ[data-state="loading"] .performance-producer' in html
    assert "turn-state board remains available" in html_lib.unescape(block).lower()


def test_r3_rates_desk_copies_populated_production_fields_instead_of_false_nulls():
    html = _html()
    desk = re.search(r'<article[^>]+id="rates-curves".*?</article>', html, re.S)
    assert desk
    block = html_lib.unescape(desk.group(0))
    expected = {
        "JP": ("1.48", "-2.02", "+0.27"),
        "KR": ("1.32", "-0.67", "+0.10"),
        "IN": ("—", "+1.82", "-0.11"),
        "AU": ("0.50", "+0.05", "+0.18"),
        "GB": ("1.23", "+0.03", "+0.19"),
    }
    for market, (curve, carry, drift) in expected.items():
        row = re.search(rf'<tr[^>]+data-rate-market="{market}".*?</tr>', block, re.S)
        assert row, market
        text = re.sub(r'<[^>]+>', ' ', row.group(0))
        assert curve in text, market
        assert carry in text, market
        assert drift in text, market
    tw = re.search(r'<tr[^>]+data-rate-market="TW"[^>]+data-null-series="true".*?</tr>', block, re.S)
    assert tw
    assert "typed null" in block.lower()


def test_r3_shell_and_mobile_navigation_do_not_fake_canonical_product_chrome():
    html = _html()
    assert 'data-shell-market="OTHER"' in html
    assert 'class="shell-dropdown-caret"' in html
    assert 'data-shell-copilot="true"' in html
    assert 'data-act-jump' in html
    assert 'class="act-jump"' in html
    assert '.nav-search input:focus-visible' in html
    assert 'data-placeholder-en="Search any stock"' in html
    assert 'data-placeholder-zh="搜索任意股票"' in html
    assert 'html[data-lang="zh"] :where(h1,.act h2' in html


def test_r3_pressure_and_overview_visuals_do_not_imply_fake_quantitative_scales():
    html = _html()
    assert 'class="pressure-meter"' not in html
    assert 'class="overview-score"' not in html
    assert "One scale, five markets" not in html
    assert "同一标尺，五个市场" not in html
    assert 'data-pressure-magnitude-unit="two-year-percentile"' in html
    assert "Magnitude percentile" in html
    assert "幅度百分位" in html


def test_r3_heatmap_and_scroll_tables_preserve_readability():
    html = _html()
    assert '.correlation-heat td[data-heat-band="high"]' in html
    assert 'var(--heat-ink-high)' in html
    assert '.rotation-table .sticky-market' in html
    assert '.correlation-heat .sticky-market' in html
    assert '.league-view .sticky-market' in html


def test_r3_turn_metrics_and_hk_risk_match_committed_production_bake():
    html = _html()
    expected = {
        "US": ("20d +0.7%", "Off high −1.2%", 'data-risk-state="unavailable"'),
        "CN": ("20d +0.6%", "Off high −7.2%", 'data-risk-state="unavailable"'),
        "HK": ("20d −3.2%", "Off high −11.2%", 'data-risk-state="elevated"'),
    }
    for market, (mom, off_high, risk_state) in expected.items():
        card = re.search(rf'<article class="turn-cell" data-turn-market="{market}".*?</article>', html, re.S)
        assert card, market
        block = html_lib.unescape(card.group(0))
        assert mom in block, market
        assert off_high in block, market
        assert risk_state in card.group(0), market
    hk = re.search(r'<article class="turn-cell" data-turn-market="HK".*?</article>', html, re.S)
    assert hk
    assert "US rate shock — protect gains" in html_lib.unescape(hk.group(0))


def test_r3_seven_market_return_surface_discloses_its_population_boundary():
    html = html_lib.unescape(_html())
    assert "published seven-market international comparison" in html
    assert "US, China, and Hong Kong remain represented" in html
    assert "十市场拐点状态范围" in html


def test_r3_fixed_paths_are_shape_only_and_grid_aligned():
    html = _html()
    assert 'data-scale-mode="per-market-normalized-shape-only"' in html
    assert "independently normalized to each market’s own range" in html
    assert "never amplitude across markets" in html
    assert ".path-card { display:flex; flex-direction:column; }" in html
    assert ".path-card .path-head { min-height:72px; }" in html
    assert ".path-card .sparkline { margin-top:auto; }" in html


def test_r3_leadership_marker_is_bound_to_declared_share():
    html = _html()
    assert 'data-leadership-ahead="0"' in html
    assert 'data-leadership-total="7"' in html
    assert 'style="--lead-share:0%"' in html
    assert "left:var(--lead-share,0%)" in html


def test_r3_pressure_flow_preserves_export_rule_and_gap_receipt():
    html = html_lib.unescape(_html())
    assert 'data-pressure-export-rule="sigma>=0.5"' in html
    assert 'data-pressure-gap-count="0"' in html
    assert "exporting risk" in html
    assert "none is active in this committed bake" in html
    assert "No structural-only data gaps are present in this bake" in html


def test_r3_shell_locale_syncs_search_and_settings_accessibility_copy():
    html = _html()
    assert "const syncShellLocale = () =>" in html
    assert "node.placeholder = zh ? node.dataset.placeholderZh : node.dataset.placeholderEn" in html
    assert "node.setAttribute('aria-label', zh ? node.dataset.ariaZh : node.dataset.ariaEn)" in html
    assert html.count("syncShellLocale();") >= 2


def test_r3_fragility_unflagged_group_does_not_claim_zero_warnings():
    html = html_lib.unescape(_html())
    assert "Below the 3-of-4 flag threshold" in html
    assert "not zero structural warnings" in html
    assert "BIS credit gap" in html
    assert "Berg & Pattillo (1999)" in html
