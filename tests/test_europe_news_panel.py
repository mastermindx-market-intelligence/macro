"""Tests for engine/europe_news_intel.panel() (spec MO-PAID-034 W7-1 F02).

All tests are offline: no network, no real data/ tree. Redirects both this
module's parquet paths and qbus paths to tmp_path."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from pathlib import Path

from engine import europe_news_intel as eni
from engine import qbus
from engine.international_macro_dashboard import build_country_view


def _redirect_data_paths(monkeypatch, tmp_path: Path) -> None:
    """Redirect BOTH this module's and qbus's parquet paths to tmp_path so no
    test ever touches the real repo data/ directory."""
    monkeypatch.setattr(eni, "_events_path", lambda: tmp_path / "europe_events.parquet")
    monkeypatch.setattr(eni, "_coverage_path", lambda: tmp_path / "europe_coverage.parquet")
    monkeypatch.setattr(qbus, "_events_path", lambda: tmp_path / "qbus_items.parquet")


def _accrued_record():
    """One row matching the europe_news_intel.v1 desk schema (event_key absent)."""
    return {
        "event_id": "ev_test_001",
        "item_id": "item-test-001",
        "first_seen_utc": "2026-09-06T12:00:00+00:00",
        "seendate": "2026-09-06T08:00:00+00:00",
        "fetch_clock_utc": "2026-09-06T12:00:00+00:00",
        "asof": "2026-09-06",
        "title": "Commission adopts EU Guidelines on exclusionary abuses",
        "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1769",
        "source": "ec_presscorner",
        "domain": "ec.europa.eu",
        "source_tier": 1,
        "lang": "en",
        "theme": "competition_antitrust",
        "jurisdiction": "EU",
        "coverage_state": "COVERED",
        "timestamp_quality": "PUBLISHER_STATED",
        "body_sha256": "",
        "rights_basis": "CC BY 4.0",
    }


# --------------------------------------------------------------------------- #
# 1. panel is present and callable
# --------------------------------------------------------------------------- #
def test_panel_is_present_and_callable():
    assert hasattr(eni, "panel"), "panel should be added to europe_news_intel"
    assert callable(eni.panel)


# --------------------------------------------------------------------------- #
# 2. panel() returns v1 schema, is_context_only True, correct item fields;
#    importance_raw / event_key absent from items
# --------------------------------------------------------------------------- #
def test_panel_returns_correct_schema_and_fields(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    record = _accrued_record()
    existing = eni.accrue(None, [record])
    existing.to_parquet(eni._events_path(), index=False)

    result = eni.panel()

    assert result is not None
    assert result["schema"] == "europe_news_intel.v1"
    assert result["is_context_only"] is True
    items = result["items"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    assert "title" in item
    assert "url" in item
    assert "source" in item
    assert "seendate" in item
    assert "jurisdiction" in item
    # Forbidden fields
    assert "importance_raw" not in item
    assert "event_key" not in item
    assert "item_id" not in item
    assert "theme" not in item
    # Values present
    assert item["title"] == record["title"]
    assert item["url"] == record["url"]
    assert item["source"] == record["source"]
    assert item["seendate"] == record["seendate"]
    assert item["jurisdiction"] == record["jurisdiction"]


# --------------------------------------------------------------------------- #
# 3. panel() returns None when parquet is missing (never raises)
# --------------------------------------------------------------------------- #
def test_panel_returns_none_when_missing(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    # No accrue — parquet does not exist
    result = eni.panel()
    assert result is None


# --------------------------------------------------------------------------- #
# 4. Template render with synthetic EZ D contains id="europe-news", bilingual
#    labels, fixture title, and no score/rank/signal/confidence/buy/sell
# --------------------------------------------------------------------------- #
def test_template_render_contains_europe_panel_for_ez(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    # Build a proper record that build_country_view can process
    record = _accrued_record()
    existing = eni.accrue(None, [record])
    existing.to_parquet(eni._events_path(), index=False)

    # Build the full view using build_country_view (mirrors test_international_macro_dashboards)
    from engine.international_macro_dashboard import build_country_view

    raw_record = {
        "cc": "EZ",
        "name": "Euro Area",
        "name_zh": "欧元区",
        "flag": "🌐",
        "date": "2026-09-06",
        "quad": "Q2",
        "quad_name": "Reflation",
        "growth_score": 0.4,
        "inflation_score": 0.25,
        "confidence": 0.55,
        "liquidity": "neutral",
        "recession_score": 20.0,
        "recession_band": "low",
        "data_limited": False,
        "macro": {
            "cpi_yoy": 2.1,
            "gdp_yoy": 1.5,
            "unemployment": 5.9,
            "yield_10y": 3.2,
            "policy_rate": 3.5,
            "curve": 0.3,
            "fx": 108.5,
            "fx_strength_3m": -0.8,
            "drawdown": -3.2,
            "realvol": 14.0,
        },
        "macro_asof": {
            "cpi_yoy": "2026-08",
            "gdp": "2026-06",
            "unemployment": "2026-08",
            "yield_10y": "2026-09",
        },
        "equity": {"drawdown_risk": 22.0},
        "risk_radar": {
            "state": "calm",
            "top_score": 55,
            "dominant_label_en": "No dominant scare",
            "dominant_label_zh": "无主导风险",
            "drawdown_prob": {"h21": 0.08, "measure": ">=5% pullback within 21 days"},
            "scares": [],
        },
    }
    history_df = pd.DataFrame({
        "growth_score": [0.4] * 60,
        "inflation_score": [0.25] * 60,
        "recession_score": [20.0] * 60,
        "liquidity": ["neutral"] * 60,
    }, index=pd.bdate_range("2026-07-01", periods=60))

    d_ez = build_country_view(raw_record, history_df, today=date(2026, 9, 6))

    from jinja2 import Environment, FileSystemLoader
    template_path = Path(__file__).parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(template_path), lstrip_blocks=True)
    template = env.get_template("international_macro.html.j2")

    europe_news = eni.panel()
    html = template.render(D=d_ez, RADAR=None, europe_news=europe_news,
                          europe_news_items=europe_news["items"] if europe_news else None)

    assert 'id="europe-news"' in html
    assert 'Europe official press' in html or '欧洲官方新闻' in html
    assert 'l-en' in html
    assert 'l-zh' in html
    assert record["title"] in html
    # Forbidden terms must not appear in the europe-news section
    forbidden = ("score", "rank", "signal", "confidence", "buy", "sell",
                 "importance", "event_key")
    idx = html.index('id="europe-news"')
    panel_end = html.index("</section>", idx)
    panel_html = html[idx:panel_end]
    for term in forbidden:
        assert term not in panel_html, f"{term} should not appear in europe-news section"


# --------------------------------------------------------------------------- #
# 5. Non-EZ D does not contain id="europe-news"
# --------------------------------------------------------------------------- #
def test_template_render_excludes_europe_panel_for_non_ez(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    from engine.international_macro_dashboard import build_country_view

    raw_record = {
        "cc": "JP",
        "name": "Japan",
        "name_zh": "日本",
        "flag": "🇯🇵",
        "date": "2026-09-06",
        "quad": "Q2",
        "quad_name": "Reflation",
        "growth_score": 0.4,
        "inflation_score": 0.25,
        "confidence": 0.55,
        "liquidity": "neutral",
        "recession_score": 20.0,
        "recession_band": "low",
        "data_limited": False,
        "macro": {
            "cpi_yoy": 2.8,
            "gdp_yoy": 1.2,
            "unemployment": 2.5,
            "yield_10y": 0.9,
            "policy_rate": 0.5,
            "curve": 0.2,
            "fx": 147.5,
            "fx_strength_3m": 1.5,
            "drawdown": -4.1,
            "realvol": 12.0,
        },
        "macro_asof": {
            "cpi_yoy": "2026-08",
            "gdp": "2026-06",
            "unemployment": "2026-08",
            "yield_10y": "2026-09",
        },
        "equity": {"drawdown_risk": 18.0},
        "risk_radar": {
            "state": "calm",
            "top_score": 50,
            "dominant_label_en": "No dominant scare",
            "dominant_label_zh": "无主导风险",
            "drawdown_prob": {"h21": 0.05, "measure": ">=5% pullback within 21 days"},
            "scares": [],
        },
    }
    history_df = pd.DataFrame({
        "growth_score": [0.4] * 60,
        "inflation_score": [0.25] * 60,
        "recession_score": [20.0] * 60,
        "liquidity": ["neutral"] * 60,
    }, index=pd.bdate_range("2026-07-01", periods=60))

    d_jp = build_country_view(raw_record, history_df, today=date(2026, 9, 6))

    from jinja2 import Environment, FileSystemLoader
    template_path = Path(__file__).parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(template_path), lstrip_blocks=True)
    template = env.get_template("international_macro.html.j2")

    # Non-EZ: europe_news is None
    html = template.render(D=d_jp, RADAR=None, europe_news=None)

    assert 'id="europe-news"' not in html
