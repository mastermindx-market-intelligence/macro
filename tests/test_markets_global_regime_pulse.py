"""Contracts for the compact Global Market Cycles regime pulse.

The pulse is the truthful successor to the misplaced UD-B1 global-looking hero:
it belongs on markets.html, consumes the existing global cycle positions, and
must never relabel the US market_state score as a global composite.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "markets.html.j2"
APP = ROOT / "site" / "markets_app.js"
CSS = ROOT / "site" / "markets.css"
BUILT = ROOT / "site" / "markets.html"


def _function_slice(src: str, name: str) -> str:
    start = src.index(f"function {name}(")
    brace = src.index("{", start)
    depth = 1
    i = brace + 1
    while i < len(src) and depth:
        depth += (src[i] == "{") - (src[i] == "}")
        i += 1
    assert depth == 0, f"unbalanced function {name}"
    return src[start:i]


def test_template_mounts_one_global_regime_pulse():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert src.count('id="global-regime-pulse"') == 1
    assert 'id="global-regime-pulse-label"' in src
    assert 'id="global-regime-pulse-track"' in src
    assert 'id="global-regime-pulse-buckets"' in src


def test_header_is_compact_and_defers_method_detail_below():
    src = TEMPLATE.read_text(encoding="utf-8")
    assert "Eleven national equity markets on one cycle oscillator." in src
    assert "Nine positions are engine-backed" in src
    assert "Observed history (solid), projection (dashed + uncertainty cone)" not in src


def test_global_pulse_uses_cycle_positions_not_us_market_state():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "nowPosOf(c)" in fn
    assert "engPos(c)" in fn
    assert "market_state" not in fn.lower()
    assert "META.regime" not in fn
    assert "regField(" not in fn


def test_global_pulse_reuses_existing_zone_boundaries():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "var highCut = 82;" in fn
    assert "var lowerCut = 42;" in fn
    css = CSS.read_text(encoding="utf-8")
    assert ".grp-track::before { left: 42%; }" in css
    assert ".grp-track::after { left: 82%; }" in css


def test_global_pulse_exposes_mixed_source_provenance():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "engine-backed" in fn
    assert "analyst estimate" in fn
    assert "data-source" in fn


def test_global_pulse_is_interactive_with_existing_focus_path():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "renderGlobalPulse")
    assert "setFocus(" in fn
    assert "data-id" in fn


def test_global_pulse_rerenders_on_boot_and_language_change():
    src = APP.read_text(encoding="utf-8")
    assert _function_slice(src, "boot").count("renderGlobalPulse()") == 1
    assert _function_slice(src, "onLangChange").count("renderGlobalPulse()") == 1


def test_default_panel_no_longer_duplicates_top_level_global_regime():
    src = APP.read_text(encoding="utf-8")
    fn = _function_slice(src, "buildDefaultPanel")
    assert "Global-equity regime" not in fn
    assert "rg-headline" not in fn
    assert "Where the markets stand" in fn


def test_global_pulse_css_has_mobile_reduction_and_no_literal_hex():
    src = CSS.read_text(encoding="utf-8")
    start = src.index("/* ---- global regime pulse")
    end = src.index("/* ---- two-up:", start)
    block = src[start:end]
    assert ".global-regime-pulse" in block
    assert "@media (max-width: 760px)" in block
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", block)


def test_built_markets_page_contains_global_pulse_when_present():
    if not BUILT.exists():
        return
    html = BUILT.read_text(encoding="utf-8")
    assert html.count('id="global-regime-pulse"') == 1


def test_built_markets_page_keeps_asset_stamps_and_defer_contract():
    """The generated page must pass through optimize_assets before commit.

    A raw template render silently drops cache-busting query stamps and the
    defer contract on local scripts, which is a real publication regression.
    """
    if not BUILT.exists():
        return
    html = BUILT.read_text(encoding="utf-8")
    assert re.search(r'href="theme\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'href="navigation-refresh\.css\?v=[0-9a-f]{8}"', html)
    assert re.search(r'src="markets_app\.js\?v=[0-9a-f]{8}" defer', html)
    assert re.search(r'src="theme\.js\?v=[0-9a-f]{8}" defer', html)
