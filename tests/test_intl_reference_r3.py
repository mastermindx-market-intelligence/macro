"""Static contract for the international vNext R3 design reference.

The reference is a design artifact, not production. These tests pin the R2
review findings so implementation cannot earn approval by deleting user jobs,
inventing authority, or hiding degraded states.
"""
from __future__ import annotations

import hashlib
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
        assert act in html
    assert 'id="dollar-drivers"' in html
    assert "What's driving the dollar?" in html


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


def test_r3_covers_full_market_and_economy_universes():
    html = _html()
    assert _attr_values(html, "data-turn-market") == {
        "US", "CN", "HK", "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    assert _attr_values(html, "data-economy") == {
        "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    assert _attr_values(html, "data-pressure-market") == {
        "US", "CN", "HK", "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }
    assert _attr_values(html, "data-fragility-country") == {
        "KR", "TW", "JP", "EZ", "GB", "IN", "AU"
    }


def test_r3_restores_horizons_and_change_shape_without_fake_rank_history():
    html = _html()
    assert _attr_values(html, "data-horizon") == {"1m", "3m", "6m", "12m", "ytd"}
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
    assert "rounded components" not in html.lower()
    assert "Australia" in html and 'data-fragility-country="AU"' in html
    assert "a transmission read, not a statement of cause" in html
