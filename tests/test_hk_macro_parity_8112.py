from pathlib import Path
import re

import pytest
from bs4 import BeautifulSoup

from tests.test_hk_tier1_shell import _make_vm, _render

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
    assert "The checks are still building" not in SOURCE
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


def _render_soup(**overrides):
    return BeautifulSoup(_render(**overrides), "html.parser")


@pytest.mark.parametrize("score, expected", [(0, "0"), (None, "—"), (True, "—"), ("54", "—"), (101, "—")])
def test_native_sentiment_zero_and_invalid_values_render_on_both_surfaces(score, expected):
    latest = dict(_make_vm()["latest"], fear_euphoria={
        "fe_score": score, "band": "Neutral", "band_zh": "中性", "legs": [],
    })
    soup = _render_soup(latest=latest)
    for selector in ("#hkx-sentiment", "#hkx-dlg-sentiment"):
        surface = soup.select_one(selector)
        assert surface is not None
        if expected == "—":
            assert surface.select_one('[data-source-field="latest.fear_euphoria.fe_score"]') is None
            assert "unavailable" in surface.get_text().lower()
            assert "fg-neutral" not in surface.get("class", [])
        else:
            assert surface.select_one('[data-source-field="latest.fear_euphoria.fe_score"]').get_text() == expected


@pytest.mark.parametrize("components", [[], None, "missing", [None], "malformed"])
def test_owner_thresholds_remain_reachable_without_component_readings(components):
    ms = dict(_make_vm()["market_state"], components=components)
    if components == "missing":
        ms.pop("components")
    soup = _render_soup(market_state=ms)
    trigger = soup.select_one('button[aria-controls="hkx-pop-signals"]')
    assert trigger is not None
    assert "0 of 0" not in trigger.get_text()
    assert "now 48/100" in soup.select_one("#hkx-pop-signals").get_text()


@pytest.mark.parametrize("probability, expected", [(0, "0%"), (None, "—"), (False, "—"), (1.2, "—")])
def test_risk_probability_zero_remains_an_estimate_and_unknown_stays_unknown(probability, expected):
    ms = dict(_make_vm()["market_state"])
    radar = {"state": "elevated", "top_score": 88, "dd21": probability}
    soup = _render_soup(market_state=dict(ms, radar=radar))
    assert soup.select_one("[data-risk-probability]").get_text() == expected
    popup = soup.select_one("#hkx-pop-risk").get_text()
    assert "model estimate" in popup
    assert "Intensity is not probability." in popup


@pytest.mark.parametrize("score, valid", [(0, True), (None, False), (True, False), ("37", False), (-1, False)])
def test_market_score_uses_its_own_clock_and_never_falls_back_to_raw(score, valid):
    ms = dict(_make_vm()["market_state"], score=score, raw_score=97, asof="2026-09-24")
    soup = _render_soup(market_state=ms)
    assert "2026-09-24" in soup.select_one("#ms-live-pill").get_text()
    assert "2026-07-10" not in soup.select_one("#ms-live-pill").get_text()
    gauge = soup.select_one(".mx5-gauge-svg")
    assert bool(gauge.select_one("#mx5-gauge-needle")) is valid
    assert "97" not in gauge.get("aria-label", "")


@pytest.mark.parametrize("plain", [True, False])
def test_native_labels_are_text_under_the_production_non_autoescaped_environment(plain):
    attack = '<img src=x onerror="alert(1)">'
    ms = dict(_make_vm()["market_state"], components=[
        {"label_en": attack, "label_zh": attack, "score": 0, "tone": "bad"}],
        flip_en=attack, flip_zh=attack,
        flip_plain_en=attack if plain else None, flip_plain_zh=attack if plain else None)
    latest = dict(_make_vm()["latest"], fear_euphoria={
        "fe_score": 0, "band": "Panic", "band_zh": "恐慌", "legs": [
            {"key": attack, "name_en": attack, "name_zh": attack, "lean": "risk-off", "pct": 0, "value": 0}]})
    soup = _render_soup(market_state=ms, latest=latest)
    for selector in (".hkx-flip", "#hkx-pop-signals", "#hkx-dlg-sentiment", "#hkx-dlg-playbook"):
        surface = soup.select_one(selector)
        assert not surface.select("img[onerror]")
        assert attack in surface.get_text()


def test_sector_values_keep_native_order_zero_missing_and_relative_trend():
    sectors = [
        dict(name="Energy", rank=2, mom20=0, mom60=None, above200=True, dir=None),
        dict(name="Materials", ticker="materials", rank=1, mom20=-1.2, mom60=3.4, above200=False, dir=None),
        dict(name="Financials & Banks", ticker="banks", rank=None, mom20=None, mom60=0, above200=None, dir=None),
    ]
    soup = _render_soup(sectors=sectors, breadth={"pct_above_50": 55},
                        full_breadth=dict(adv=123, dec=456, n_members=789, asof="2026-09-24"))
    rows = soup.select('[data-research-table="sectors"] tbody tr')
    assert [r.select_one('[data-sector-field="rank"]').get_text() for r in rows] == ["2", "1", "—"]
    assert rows[0]["data-sector-key"] == ""
    values = [[r.select_one(f'[data-sector-field="{field}"]') for field in ("mom20", "mom60")] for r in rows]
    assert [[v.get_text() for v in row] for row in values] == [["+0.0%", "—"], ["-1.2%", "+3.4%"], ["—", "+0.0%"]]
    for cell in (values[0][0], values[0][1], values[2][0], values[2][1]):
        assert not {"hkx-up", "hkx-dn"}.intersection(cell.get("class", []))
    assert "hkx-dn" in values[1][0]["class"] and "hkx-up" in values[1][1]["class"]
    assert "Ratio above 200d" in rows[0].get_text()
    assert "Ratio below 200d" in rows[1].get_text()
    assert rows[2].select_one('[data-sector-field="above200"]').get_text() == "—"
    main_board = soup.select_one('[data-breadth-universe="main-board"]').get_text()
    assert "123 / 456" in main_board and "789" in main_board and "2026-09-24" in main_board
    assert "55%" not in main_board
    assert "55%" in soup.select_one('[data-breadth-universe="curated"]').get_text()
    absent = _render_soup(full_breadth=None).select_one('[data-breadth-universe="main-board"]').get_text()
    assert "Main-board breadth unavailable" in absent


def test_native_confirmation_coverage_and_short_history_are_preserved():
    fe = {"fe_score": 54, "band": "Neutral", "band_zh": "中性", "warming_up": True,
          "legs": [dict(key="copper", name_en="Copper", name_zh="铜", lean="risk-on", pct=50, value=0.1)],
          "confirmation": {"verdict_en": "divergent (no consensus)", "verdict_zh": "背离（无共识）",
                           "dissent": [{"en": "A < B", "zh": "甲 < 乙"}]}}
    soup = _render_soup(latest=dict(_make_vm()["latest"], fear_euphoria=fe))
    for selector in ("#hkx-sentiment", "#hkx-dlg-sentiment"):
        surface = soup.select_one(selector)
        assert "1 gauges with readings" in surface.get_text()
        assert "Shorter history" in surface.get_text()
    detail = soup.select_one("#hkx-dlg-sentiment")
    assert "divergent (no consensus)" in detail.select_one("[data-native-confirmation]").get_text()
    assert "A < B" in detail.get_text()


def test_degraded_factor_is_disclosed_in_popup_and_unknown_risk_has_no_calm_driver():
    ms = dict(_make_vm()["market_state"], degraded_components=["funding"], components=[
        dict(key="funding", label_en="Funding", label_zh="资金", score=60, tone="good", degraded=True)],
        radar=dict(state=None, label_en="calm", label_zh="平静", top_score=None, dd21=None))
    soup = _render_soup(market_state=ms)
    assert "Some inputs unavailable" in soup.select_one("#hkx-pop-signals").get_text()
    risk = soup.select_one("#hkx-pop-risk")
    assert risk.select_one(".hkx-risk-driver") is None
    assert "Unavailable" in risk.get_text()
