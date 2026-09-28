from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "hk.html.j2"
SOURCE = TEMPLATE.read_text(encoding="utf-8")


def test_hk_hero_uses_native_market_state_without_missing_as_zero():
    assert "_hk_native_score = _hk_ms.get('score')" in SOURCE
    assert "_hk_native_score is not boolean" in SOURCE
    assert "0 <= _hk_native_score <= 100" in SOURCE
    assert "ms.score|default(0)|int" not in SOURCE


def test_hk_factor_breakdown_uses_market_state_tones_and_preserves_threshold_detail():
    assert "c.get('tone') in ('good','warn','bad')" in SOURCE
    assert "data-factor-thresholds" in SOURCE
    assert "_hk_component_shape_valid" in SOURCE
    assert "The checks are still building — flip thresholds will show here once the read is scored." in SOURCE
    assert "Factor data unavailable" in SOURCE


def test_hk_risk_preview_separates_intensity_probability_and_event():
    assert "data-risk-intensity" in SOURCE
    assert "data-risk-probability" in SOURCE
    assert "Intensity is not probability." in SOURCE
    assert "At least a 5% index pullback within 21 trading days." in SOURCE
    assert "_p is number and _p is not boolean and 0 <= _p <= 1" in SOURCE


def test_hk_sentiment_uses_native_fear_euphoria_and_keeps_vhsi_separate():
    assert "latest.get('fear_euphoria')" in SOURCE
    assert 'data-source-field="latest.fear_euphoria.fe_score"' in SOURCE
    assert "Local fear gauge · VHSI" in SOURCE
    assert "range_plain_en" in SOURCE
    assert "_hk_dial = (100 - _hk_pct)" not in SOURCE


def test_hk_sector_detail_preserves_native_relative_strength_dimensions():
    assert 'data-research-table="sectors"' in SOURCE
    for field in ("rank", "mom20", "mom60", "above200"):
        assert f'data-sector-field="{field}"' in SOURCE
    assert "Rank uses 60-day relative strength vs Hang Seng." in SOURCE
    assert 'data-breadth-universe="curated"' in SOURCE
    assert 'data-breadth-universe="main-board"' in SOURCE
    assert "Examples from the stock board, not sector recommendations." in SOURCE


def test_hk_tables_keep_table_semantics_inside_scroll_containers():
    assert not re.search(r"table\.hkx-mt\s*\{[^}]*display\s*:\s*block", SOURCE)
    assert SOURCE.count('<div class="hkx-table-scroll">') == len(re.findall(r'<table\b[^>]*class="hkx-mt"', SOURCE))


def test_hk_mobile_controls_preserve_existing_product_floor():
    assert re.search(r"body\.page-hk \.hkx-hbtn\{[^}]*min-height:40px[^}]*box-sizing:border-box", SOURCE, re.S)
    assert re.search(r"body\.page-hk \.hkx-tkr-btn\{[^}]*min-height:40px[^}]*box-sizing:border-box", SOURCE, re.S)


def test_hk_popup_and_factor_interactions_have_keyboard_focus_treatment():
    assert "body.page-hk .hkx-hbtn:focus-visible" in SOURCE
    assert "body.page-hk .hkx-pop-link:focus-visible" in SOURCE
    assert "body.page-hk .hkx-factor-detail>summary:focus-visible" in SOURCE
