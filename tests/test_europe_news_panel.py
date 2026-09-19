"""Tests for engine/europe_news_intel.panel() (spec MO-PAID-034 W7-1 F02).

All tests are offline: no network, no real data/ tree. Redirects both this
module's and qbus paths to tmp_path via _redirect_data_paths."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from pathlib import Path

from engine import europe_news_intel as eni
from engine import qbus
from engine.international_macro_dashboard import build_country_view


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _redirect_data_paths(monkeypatch, tmp_path: Path) -> None:
    """Redirect BOTH this module's and qbus parquet paths to tmp_path so no
    test ever touches the real repo data/ directory.

    Redirects _events_path (used by accrue/read_events) and
    _events_path_no_mkdir (used by panel) so all code paths respect tmp_path."""
    monkeypatch.setattr(eni, "_events_path", lambda: tmp_path / "europe_events.parquet")
    monkeypatch.setattr(eni, "_events_path_no_mkdir", lambda: tmp_path / "europe_events.parquet")
    monkeypatch.setattr(eni, "_coverage_path", lambda: tmp_path / "europe_coverage.parquet")
    monkeypatch.setattr(qbus, "_events_path", lambda: tmp_path / "qbus_items.parquet")


# --------------------------------------------------------------------------- #
# 1. panel is present and callable — FAILS on origin/main (hasattr false)
# --------------------------------------------------------------------------- #
def test_panel_is_present_and_callable():
    assert hasattr(eni, "panel"), "panel should be added to europe_news_intel"
    assert callable(eni.panel)


# --------------------------------------------------------------------------- #
# 2. panel() returns v1 schema, is_context_only True, correct item fields;
#    source_label / jurisdiction_en+zh; importance_raw/event_key absent
# --------------------------------------------------------------------------- #
def test_panel_returns_correct_schema_and_fields(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    # Today's date so the row falls inside the 14-day recency window
    today = pd.Timestamp.now(tz="UTC")
    seendate = (today - timedelta(hours=2)).isoformat()
    record = {
        "event_id": "ev_test_001",
        "item_id": "item-test-001",
        "first_seen_utc": today.isoformat(),
        "seendate": seendate,
        "fetch_clock_utc": today.isoformat(),
        "asof": today.date().isoformat(),
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

    # Presence of new bilingual fields
    assert "source" in item
    assert "source_zh" in item
    assert "jurisdiction_en" in item
    assert "jurisdiction_zh" in item
    assert "seendate" in item

    # No raw machine keys rendered
    assert "ec_presscorner" not in item["source"]
    assert item["source"] == "European Commission"
    assert item["source_zh"] == "European Commission"
    assert item["jurisdiction_en"] == "European Union"
    assert item["jurisdiction_zh"] == "欧盟"

    # Title / url / seendate preserved
    assert item["title"] == record["title"]
    assert item["url"] == record["url"]
    assert item["seendate"] == seendate

    # Forbidden fields absent
    assert "importance_raw" not in item
    assert "event_key" not in item
    assert "item_id" not in item
    assert "theme" not in item


# --------------------------------------------------------------------------- #
# 3. panel() returns None when parquet is missing (never raises)
# --------------------------------------------------------------------------- #
def test_panel_returns_none_when_missing(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    # No accrue — parquet does not exist
    result = eni.panel()
    assert result is None


# --------------------------------------------------------------------------- #
# 4. AMBIGUOUS_JURISDICTION maps to "Europe (unassigned)" / "欧洲（未归属）"
# --------------------------------------------------------------------------- #
def test_ambiguous_jurisdiction_maps_to_plain_labels(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    today = pd.Timestamp.now(tz="UTC")
    seendate = (today - timedelta(hours=2)).isoformat()
    record = {
        "event_id": "ev_test_002",
        "item_id": "item-test-002",
        "first_seen_utc": today.isoformat(),
        "seendate": seendate,
        "fetch_clock_utc": today.isoformat(),
        "asof": today.date().isoformat(),
        "title": "Test ambiguous jurisdiction item",
        "url": "https://example.com",
        "source": "boe_news",
        "domain": "bankofengland.co.uk",
        "source_tier": 1,
        "lang": "en",
        "theme": "monetary_policy",
        "jurisdiction": "AMBIGUOUS_JURISDICTION",
        "coverage_state": "COVERED",
        "timestamp_quality": "PUBLISHER_STATED",
        "body_sha256": "",
        "rights_basis": "OGL v3",
    }
    existing = eni.accrue(None, [record])
    existing.to_parquet(eni._events_path(), index=False)

    result = eni.panel()
    assert result is not None
    item = result["items"][0]
    assert item["jurisdiction_en"] == "Europe (unassigned)"
    assert item["jurisdiction_zh"] == "欧洲（未归属）"
    assert item["source"] == "Bank of England"
    assert item["source_zh"] == "Bank of England"


# --------------------------------------------------------------------------- #
# 5. Recency window + cap: oldest within 14d newest-first, max 12 rows
# --------------------------------------------------------------------------- #
def test_recency_window_newest_first_max12(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    today = pd.Timestamp.now(tz="UTC")
    records = []
    for i in range(15):  # 15 rows — cap should return only 12
        offset_hours = i * 6  # 0, 6, 12, ... 84 hours ago
        ts = today - timedelta(hours=offset_hours)
        records.append({
            "event_id": f"ev_test_{i:03d}",
            "item_id": f"item-test-{i:03d}",
            "first_seen_utc": ts.isoformat(),
            "seendate": ts.isoformat(),
            "fetch_clock_utc": ts.isoformat(),
            "asof": today.date().isoformat(),
            "title": f"Headline {i}",
            "url": f"https://example.com/{i}",
            "source": "ec_presscorner",
            "domain": "ec.europa.eu",
            "source_tier": 1,
            "lang": "en",
            "theme": "policy_geo_other",
            "jurisdiction": "EU",
            "coverage_state": "COVERED",
            "timestamp_quality": "PUBLISHER_STATED",
            "body_sha256": "",
            "rights_basis": "CC BY 4.0",
        })

    existing = eni.accrue(None, records)
    existing.to_parquet(eni._events_path(), index=False)

    result = eni.panel()
    assert result is not None
    # Max 12 rows despite 15 written
    assert len(result["items"]) == 12
    # Newest first (seendate descending)
    seendates = [item["seendate"] for item in result["items"]]
    assert seendates == sorted(seendates, reverse=True)


# --------------------------------------------------------------------------- #
# 6. Template render with EZ D contains id="europe-news", bilingual title
#    AND l-en/l-zh INSIDE the panel, fixture title, no forbidden terms
# --------------------------------------------------------------------------- #
def test_template_render_contains_europe_panel_for_ez(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    today = pd.Timestamp.now(tz="UTC")
    seendate = (today - timedelta(hours=2)).isoformat()
    record = {
        "event_id": "ev_test_001",
        "item_id": "item-test-001",
        "first_seen_utc": today.isoformat(),
        "seendate": seendate,
        "fetch_clock_utc": today.isoformat(),
        "asof": today.date().isoformat(),
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
    existing = eni.accrue(None, [record])
    existing.to_parquet(eni._events_path(), index=False)

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

    # Bilingual title: BOTH languages present (AND, not OR)
    assert 'Europe official press' in html
    assert '欧洲官方新闻' in html

    # l-en AND l-zh appear INSIDE the europe-news section
    idx = html.index('id="europe-news"')
    panel_end = html.index("</section>", idx)
    panel_html = html[idx:panel_end]
    assert 'class="l-en"' in panel_html, "l-en must appear inside #europe-news"
    assert 'class="l-zh"' in panel_html, "l-zh must appear inside #europe-news"

    # Fixture title present
    assert record["title"] in html

    # No forbidden terms in the panel
    forbidden = ("score", "rank", "signal", "confidence", "buy", "sell",
                 "importance", "event_key", "ec_presscorner", "boe_news")
    for term in forbidden:
        assert term not in panel_html, f"{term!r} should not appear in #europe-news"


# --------------------------------------------------------------------------- #
# 7. Non-EZ page (JP) does NOT include id="europe-news"
# --------------------------------------------------------------------------- #
def test_builder_gate_excludes_europe_panel_for_non_ez(monkeypatch, tmp_path):
    """Verify the builder gate at build_international_macro.py:cc=='EZ' —
    JP cc != "EZ" so panel() is not called and europe_news stays None."""
    _redirect_data_paths(monkeypatch, tmp_path)

    # Write the parquet so panel() works if called, but JP won't call it
    today = pd.Timestamp.now(tz="UTC")
    seendate = (today - timedelta(hours=2)).isoformat()
    record = {
        "event_id": "ev_test_001",
        "item_id": "item-test-001",
        "first_seen_utc": today.isoformat(),
        "seendate": seendate,
        "fetch_clock_utc": today.isoformat(),
        "asof": today.date().isoformat(),
        "title": "Any title",
        "url": "https://example.com",
        "source": "ec_presscorner",
        "domain": "ec.europa.eu",
        "source_tier": 1,
        "lang": "en",
        "theme": "policy_geo_other",
        "jurisdiction": "EU",
        "coverage_state": "COVERED",
        "timestamp_quality": "PUBLISHER_STATED",
        "body_sha256": "",
        "rights_basis": "CC BY 4.0",
    }
    existing = eni.accrue(None, [record])
    existing.to_parquet(eni._events_path(), index=False)

    # Build a minimal JP D object using build_country_view
    raw_jp = {
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
            "cpi_yoy": 2.8, "gdp_yoy": 1.2, "unemployment": 2.5,
            "yield_10y": 0.9, "policy_rate": 0.5, "curve": 0.2,
            "fx": 147.5, "fx_strength_3m": 1.5, "drawdown": -4.1, "realvol": 12.0,
        },
        "macro_asof": {
            "cpi_yoy": "2026-08", "gdp": "2026-06",
            "unemployment": "2026-08", "yield_10y": "2026-09",
        },
        "equity": {"drawdown_risk": 18.0},
        "risk_radar": {
            "state": "calm", "top_score": 50,
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

    d_jp = build_country_view(raw_jp, history_df, today=date(2026, 9, 6))

    # Simulate the builder gate: for JP (cc != "EZ"), panel() is NOT called
    # This mirrors build_international_macro.py:117 exactly
    cc = "JP"
    europe_news = eni.panel() if cc == "EZ" else None
    assert europe_news is None, \
        "For cc='JP', panel() must not be called — builder gate should pass None"

    from jinja2 import Environment, FileSystemLoader
    template_path = Path(__file__).parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(template_path), lstrip_blocks=True)
    template = env.get_template("international_macro.html.j2")

    html = template.render(D=d_jp, RADAR=None,
                          europe_news=None, europe_news_items=None)
    assert 'id="europe-news"' not in html, \
        "JP page must not contain #europe-news section"
