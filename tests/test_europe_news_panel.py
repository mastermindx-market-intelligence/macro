"""Tests for engine/europe_news_intel.panel() (spec MO-PAID-034 W7-1 F02).

All tests are offline: no network, no real data/ tree. Redirects both this
module's and qbus paths to tmp_path via _redirect_data_paths."""
from __future__ import annotations

import inspect
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from engine import europe_news_intel as eni
from engine import qbus
from engine.international_macro_dashboard import REGIONS, ROUTES, build_country_view


_ASOF = date(2026, 9, 19)
_ASOF_TS = pd.Timestamp("2026-09-19T12:00:00+00:00")


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _redirect_data_paths(monkeypatch, tmp_path: Path) -> None:
    """Redirect BOTH this module's and qbus parquet paths to tmp_path so no
    test ever touches the real repo data/ directory.

    Redirects _events_path (used by accrue/ingest) and _events_path_no_mkdir
    (used by read_events/panel) so all code paths respect tmp_path."""
    monkeypatch.setattr(eni, "_events_path", lambda: tmp_path / "europe_events.parquet")
    monkeypatch.setattr(eni, "_events_path_no_mkdir", lambda: tmp_path / "europe_events.parquet")
    monkeypatch.setattr(eni, "_coverage_path", lambda: tmp_path / "europe_coverage.parquet")
    monkeypatch.setattr(qbus, "_events_path", lambda: tmp_path / "qbus_items.parquet")


def _row(**overrides) -> dict:
    ts = overrides.pop("ts", _ASOF_TS)
    iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    rec = {
        "event_id": "ev_test_001",
        "item_id": "item-test-001",
        "first_seen_utc": iso,
        "seendate": iso,
        "fetch_clock_utc": iso,
        "asof": ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10],
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
    rec.update(overrides)
    return rec


def _write_rows(rows: list[dict]) -> None:
    existing = eni.accrue(None, rows)
    existing.to_parquet(eni._events_path(), index=False)


def _macro_record(cc: str) -> dict:
    names = {
        "JP": ("Japan", "日本"),
        "KR": ("South Korea", "韩国"),
        "EZ": ("Euro Area", "欧元区"),
        "GB": ("United Kingdom", "英国"),
        "IN": ("India", "印度"),
    }
    name, name_zh = names[cc]
    return {
        "cc": cc,
        "name": name,
        "name_zh": name_zh,
        "flag": "🌐",
        "date": "2026-09-19",
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


def _history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "growth_score": [0.4] * 60,
            "inflation_score": [0.25] * 60,
            "recession_score": [20.0] * 60,
            "liquidity": ["neutral"] * 60,
        },
        index=pd.bdate_range("2026-07-01", periods=60),
    )


def _render_template(d_view, europe_news):
    from jinja2 import Environment, FileSystemLoader

    template_path = Path(__file__).parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(template_path), lstrip_blocks=True)
    template = env.get_template("international_macro.html.j2")
    items = europe_news["items"] if europe_news else None
    return template.render(
        D=d_view, RADAR=None, europe_news=europe_news, europe_news_items=items
    )


_FIXTURE_PACKET = {
    "schema": "europe_news_intel.v1",
    "is_context_only": True,
    "items": [
        {
            "title": "Commission adopts EU Guidelines on exclusionary abuses",
            "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1769",
            "source": "European Commission",
            "source_zh": "官方来源",
            "seendate": "2026-09-18T10:00:00+00:00",
            "jurisdiction_en": "European Union",
            "jurisdiction_zh": "欧盟",
        }
    ],
}


def _patch_builder_io(monkeypatch, tmp_path: Path) -> None:
    from scripts import build_international_macro as builder

    monkeypatch.setattr(
        builder.config,
        "load",
        lambda: {
            "storage": {"site_dir": str(tmp_path), "data_dir": str(tmp_path / "data")}
        },
    )
    monkeypatch.setattr(builder.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(builder, "load_history", lambda _cc: _history())


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
    _write_rows([_row()])

    result = eni.panel(asof=_ASOF)

    assert result is not None
    assert result["schema"] == "europe_news_intel.v1"
    assert result["is_context_only"] is True
    items = result["items"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]

    assert "source" in item
    assert "source_zh" in item
    assert "jurisdiction_en" in item
    assert "jurisdiction_zh" in item
    assert "seendate" in item

    assert "ec_presscorner" not in item["source"]
    assert item["source"] == "European Commission"
    assert item["source_zh"] == "官方来源"
    assert item["jurisdiction_en"] == "European Union"
    assert item["jurisdiction_zh"] == "欧盟"

    assert item["title"] == _row()["title"]
    assert item["url"] == _row()["url"]

    assert "importance_raw" not in item
    assert "event_key" not in item
    assert "item_id" not in item
    assert "theme" not in item


# --------------------------------------------------------------------------- #
# 3. panel() returns None when parquet is missing (never raises)
# --------------------------------------------------------------------------- #
def test_panel_returns_none_when_missing(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    result = eni.panel(asof=_ASOF)
    assert result is None


# --------------------------------------------------------------------------- #
# 4. AMBIGUOUS_JURISDICTION maps to "Europe (unassigned)" / "欧洲（未归属）"
# --------------------------------------------------------------------------- #
def test_ambiguous_jurisdiction_maps_to_plain_labels(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    _write_rows([_row(source="boe_news", jurisdiction="AMBIGUOUS_JURISDICTION",
                      event_id="ev_test_002", item_id="item-test-002")])

    result = eni.panel(asof=_ASOF)
    assert result is not None
    item = result["items"][0]
    assert item["jurisdiction_en"] == "Europe (unassigned)"
    assert item["jurisdiction_zh"] == "欧洲（未归属）"
    assert item["source"] == "Bank of England"
    assert item["source_zh"] == "官方来源"


def test_unknown_jurisdiction_falls_back_to_europe(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    _write_rows([_row(jurisdiction="NARNIA", event_id="ev_unknown_j")])

    result = eni.panel(asof=_ASOF)
    assert result is not None
    item = result["items"][0]
    assert item["jurisdiction_en"] == "Europe"
    assert item["jurisdiction_zh"] == "欧洲"
    assert "NARNIA" not in item["jurisdiction_en"]
    assert "NARNIA" not in item["jurisdiction_zh"]


# --------------------------------------------------------------------------- #
# 5. Recency window + cap: oldest within 14d newest-first, max 12 rows
# --------------------------------------------------------------------------- #
def test_recency_window_newest_first_max12(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)

    records = []
    for i in range(15):
        ts = _ASOF_TS - timedelta(hours=i * 6)
        records.append(_row(
            event_id=f"ev_test_{i:03d}",
            item_id=f"item-test-{i:03d}",
            ts=ts,
            title=f"Headline {i}",
            url=f"https://example.com/{i}",
        ))
    _write_rows(records)

    result = eni.panel(asof=_ASOF)
    assert result is not None
    assert len(result["items"]) == 12
    seendates = [item["seendate"] for item in result["items"]]
    assert seendates == sorted(seendates, reverse=True)


def test_recency_window_excludes_rows_older_than_14_days(monkeypatch, tmp_path):
    """RED-first on the previous head: no fixture older than 14 days existed."""
    _redirect_data_paths(monkeypatch, tmp_path)
    included_ts = _ASOF_TS - timedelta(days=13)
    excluded_ts = _ASOF_TS - timedelta(days=20)
    _write_rows([
        _row(event_id="ev_in", item_id="item-in", ts=included_ts,
             title="Inside the window"),
        _row(event_id="ev_out", item_id="item-out", ts=excluded_ts,
             title="Older than fourteen days"),
    ])

    result = eni.panel(asof=_ASOF)
    assert result is not None
    titles = [item["title"] for item in result["items"]]
    assert "Inside the window" in titles
    assert "Older than fourteen days" not in titles


def test_empty_window_returns_none_not_empty_table(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    stale = _ASOF_TS - timedelta(days=20)
    _write_rows([_row(ts=stale, title="Stale only")])

    result = eni.panel(asof=_ASOF)
    assert result is None


# --------------------------------------------------------------------------- #
# MAJOR 2 — panel() consumes read_events(asof), not a second parquet path
# --------------------------------------------------------------------------- #
def test_panel_consumes_read_events(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    called = {}

    def fake_read_events(asof=None):
        called["asof"] = asof
        rec = _row()
        return pd.DataFrame([rec])

    monkeypatch.setattr(eni, "read_events", fake_read_events)
    result = eni.panel(asof=_ASOF)
    assert called.get("asof") == _ASOF
    assert result is not None
    assert result["items"][0]["title"] == _row()["title"]


# --------------------------------------------------------------------------- #
# MAJOR 3 — no pandas ambient clock in library code (panel must not evade
# tests/test_europe_news_intel.py::test_no_ambient_time_in_library_code)
# --------------------------------------------------------------------------- #
def test_panel_module_has_no_pandas_ambient_clock():
    src = Path(inspect.getfile(eni)).read_text(encoding="utf-8")
    assert "pd.Timestamp.now(" not in src
    assert "Timestamp.utcnow(" not in src


def test_read_events_does_not_mkdir(monkeypatch, tmp_path):
    events_dir = tmp_path / "europe_news_vector"
    monkeypatch.setattr(
        eni, "_events_path", lambda: events_dir / "events.parquet"
    )
    monkeypatch.setattr(
        eni, "_events_path_no_mkdir", lambda: events_dir / "events.parquet"
    )
    assert eni.read_events(asof=_ASOF) is None
    assert eni.panel(asof=_ASOF) is None
    assert not events_dir.exists()


# --------------------------------------------------------------------------- #
# 6. Template render with EZ D contains id="europe-news", bilingual title
#    AND l-en/l-zh INSIDE the panel, fixture title, no forbidden terms
# --------------------------------------------------------------------------- #
def test_template_render_contains_europe_panel_for_ez(monkeypatch, tmp_path):
    _redirect_data_paths(monkeypatch, tmp_path)
    _write_rows([_row()])

    d_ez = build_country_view(_macro_record("EZ"), _history(), today=_ASOF)
    europe_news = eni.panel(asof=_ASOF)
    html = _render_template(d_ez, europe_news)

    assert 'id="europe-news"' in html
    assert "Europe official press" in html
    assert "欧洲官方新闻" in html

    idx = html.index('id="europe-news"')
    panel_end = html.index("</section>", idx)
    panel_html = html[idx:panel_end]
    assert 'class="l-en"' in panel_html
    assert 'class="l-zh"' in panel_html
    assert _row()["title"] in html
    assert "官方来源" in panel_html

    forbidden = ("score", "rank", "signal", "confidence", "buy", "sell",
                 "importance", "event_key", "ec_presscorner", "boe_news")
    for term in forbidden:
        assert term not in panel_html, f"{term!r} should not appear in #europe-news"


# --------------------------------------------------------------------------- #
# MAJOR 1 — real builder render path (not an inlined cc == "EZ" expression)
# --------------------------------------------------------------------------- #
def test_builder_render_path_paints_europe_news_for_ez_only(tmp_path, monkeypatch):
    from scripts import build_international_macro as builder

    _patch_builder_io(monkeypatch, tmp_path)
    monkeypatch.setattr(eni, "panel", lambda asof=None: _FIXTURE_PACKET)

    builder.build_all({"records": [_macro_record(cc) for cc in REGIONS]})

    ez_html = (tmp_path / ROUTES["EZ"]).read_text(encoding="utf-8")
    assert 'id="europe-news"' in ez_html
    assert "Europe official press" in ez_html
    assert "欧洲官方新闻" in ez_html
    assert _FIXTURE_PACKET["items"][0]["title"] in ez_html

    jp_html = (tmp_path / ROUTES["JP"]).read_text(encoding="utf-8")
    assert 'id="europe-news"' not in jp_html


def test_builder_render_path_failsoft_when_panel_raises(tmp_path, monkeypatch):
    from scripts import build_international_macro as builder

    _patch_builder_io(monkeypatch, tmp_path)

    def boom(asof=None):
        raise RuntimeError("panel exploded")

    monkeypatch.setattr(eni, "panel", boom)
    outputs = builder.build_all({"records": [_macro_record(cc) for cc in REGIONS]})
    assert {path.name for path in outputs} == set(ROUTES.values())

    ez_html = (tmp_path / ROUTES["EZ"]).read_text(encoding="utf-8")
    assert 'id="europe-news"' not in ez_html
    assert "International macro command center" in ez_html


def test_builder_render_path_omits_panel_when_none(tmp_path, monkeypatch):
    from scripts import build_international_macro as builder

    _patch_builder_io(monkeypatch, tmp_path)
    monkeypatch.setattr(eni, "panel", lambda asof=None: None)
    builder.build_all({"records": [_macro_record(cc) for cc in REGIONS]})
    ez_html = (tmp_path / ROUTES["EZ"]).read_text(encoding="utf-8")
    assert 'id="europe-news"' not in ez_html
