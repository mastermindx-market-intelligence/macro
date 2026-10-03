"""tests/test_sanctions_map_event_pins.py — W7-2 / MO-PAID-008.

Fixture-only public-news layer on sanctions_map.html. UK rows join to the
existing GBR path; EU/EA/EFTA stay a dated list. No second map, no lat/lon,
no overlay of shipping / military / satellite marks.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader

from engine import europe_news_intel, sanctions_map
from engine.i18n import t, td, tr
from engine.sanctions_map import rungs_for

ROOT = Path(__file__).resolve().parent.parent

UK_TITLE = "Bank Rate held at four percent"
EU_TITLE = "Commission publishes a trade notice"

BANNED_IN_PINS = (
    "score",
    "rank",
    "confidence",
    "AIS",
    "satellite",
    "chokepoint",
    "falsifier",
    "percentile",
)

EXCLUSION = "Not on this map: shipping chokepoints, military sites, satellite imagery"


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _sdn_csv(codes: list[str]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    for i, code in enumerate(codes):
        row = [""] * 8
        row[0] = str(i)
        row[3] = code
        w.writerow(row)
    return buf.getvalue()


def _write_ofac(tmp_path: Path) -> tuple[Path, Path, Path]:
    sdn = tmp_path / "sdn.csv"
    sdn.write_text(_sdn_csv(["RUSSIA-EO14024"]), encoding="utf-8")
    meta = tmp_path / "meta.json"
    meta.write_text("{}", encoding="utf-8")
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "programs": [
                    {
                        "code": "RUSSIA-EO14024",
                        "iso3": "RUS",
                        "country_name_en": "Russia",
                        "country_name_zh": "俄罗斯",
                        "name_en": "Russia — EO 14024",
                        "name_zh": "俄罗斯 — 第14024号行政命令",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return sdn, meta, cfg


def _write_events_parquet(path: Path, *, asof_offset_days: int = -1, today: date | None = None) -> None:
    """Write two-event fixture with asof = today + asof_offset_days. Default
    is yesterday, which is the most-recent within the freshness bound (D1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if today is None:
        today = _today_utc()
    asof = (today + timedelta(days=asof_offset_days)).isoformat()
    pd.DataFrame(
        [
            {
                "title": UK_TITLE,
                "url": "https://www.bankofengland.co.uk/news/2026/rate",
                "source": "boe_news",
                "jurisdiction": "UK",
                "asof": asof,
                "seendate": asof,
            },
            {
                "title": EU_TITLE,
                "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
                "source": "ec_presscorner",
                "jurisdiction": "EU",
                "asof": asof,
                "seendate": (today + timedelta(days=asof_offset_days - 1)).isoformat(),
            },
        ]
    ).to_parquet(path, index=False)


def _write_custom_parquet(path: Path, rows: list[dict]) -> None:
    """Write an arbitrary events fixture (parent dir created)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _render(vm, all_iso3=None):
    """Render the template directly. We do NOT post-apply ``_apply_public_news_path_marks``
    because the template now emits the only mechanism (figure data-news-gbr +
    CSS), and the new tests assert D5's invariant that no inline data-news="1"
    appears on a path."""
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.globals.update(tr=tr, td=td, t=t)
    rungs = rungs_for(vm, all_iso3 if all_iso3 is not None else {"RUS", "GBR", "USA"})
    return env.get_template("sanctions_map.html.j2").render(vm=vm, rungs=rungs)


def _pins_section(html: str) -> str:
    m = re.search(r'id="event-pins".*', html, re.S)
    assert m, "id=event-pins missing"
    rest = m.group(0)
    cut = rest.find("</section>")
    return rest if cut < 0 else rest[: cut + len("</section>")]


def test_build_public_news_uk_gbr_eu_none(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)

    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)

    news = vm["public_news"]
    assert isinstance(news, list)
    by_title = {row["title"]: row for row in news}
    assert UK_TITLE in by_title
    assert EU_TITLE in by_title
    uk = by_title[UK_TITLE]
    eu = by_title[EU_TITLE]
    for row in (uk, eu):
        assert set(row) >= {"title", "url", "source", "jurisdiction", "iso3"}
    assert uk["jurisdiction"] == "UK"
    assert uk["iso3"] == "GBR"
    assert uk["url"].startswith("https://")
    assert eu["jurisdiction"] == "EU"
    assert eu["iso3"] is None


def test_rendered_event_pins_uk_title_gbr_path_and_exclusion(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    html = _render(vm)

    assert 'id="event-pins"' in html
    assert UK_TITLE in html
    assert EU_TITLE in html
    assert 'data-iso3="GBR"' in html
    assert 'class="wm-c" data-iso3="GBR"' in html
    assert 'data-news-gbr="1"' in html
    assert 'data-news="1"' not in html
    assert EXCLUSION in html
    # OFAC rungs stay on the existing path; news is a mark, not a rung overwrite.
    assert re.search(r'class="wm-c" data-iso3="GBR"[^>]*data-rung="', html)
    pins = _pins_section(html)
    low = pins.lower()
    for word in BANNED_IN_PINS:
        assert word.lower() not in low, word
    assert "boe_news" not in pins
    assert "ec_presscorner" not in pins
    assert "GBR" not in pins
    assert html.count('class="l-en"') == html.count('class="l-zh"')


def test_missing_europe_parquet_empty_why_ofac_still_paints(tmp_path, monkeypatch):
    missing = tmp_path / "europe_news_vector" / "nope.parquet"
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: missing)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    assert vm["public_news"] == []
    assert vm["coverage"] is not None
    assert any(c["iso3"] == "RUS" for c in vm["countries"])
    html = _render(vm)
    pins = _pins_section(html)
    assert "mx-empty-why" in pins
    assert 'data-iso3="RUS"' in html
    assert EXCLUSION in html
    assert 'id="event-pins"' in html
    assert UK_TITLE not in html


# --------------------------------------------------------------------------- #
# D1 — freshness bound (engine)
# --------------------------------------------------------------------------- #
def test_freshness_ok_when_asof_is_yesterday(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet, asof_offset_days=-1)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    assert vm["public_news_state"] == "ok"
    assert any(row["title"] == UK_TITLE for row in vm["public_news"])


def test_freshness_none_recent_when_asof_is_three_days_old(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet, asof_offset_days=-3)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    assert vm["public_news_state"] == "none_recent"
    assert vm["public_news"] == []
    assert vm["public_news_common"] == {}
    html = _render(vm)
    assert not re.search(r'<figure[^>]*\bdata-news-gbr=', html, re.S)
    pins = _pins_section(html)
    assert "No European official press in the last two days" in pins
    assert "近两日无欧洲官方新闻" in pins
    assert 'class="mx-empty-why sm-null"' in pins


def test_freshness_unavailable_when_store_unreadable(tmp_path, monkeypatch):
    """The today `except` branch lands here — read_events raises → state='unavailable'."""
    def _raise():
        raise RuntimeError("store missing")
    monkeypatch.setattr(europe_news_intel, "read_events", _raise)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    assert vm["public_news_state"] == "unavailable"
    assert vm["public_news"] == []
    html = _render(vm)
    pins = _pins_section(html)
    # Existing unavailable copy, untouched by D2.
    assert "could not read today" in pins
    assert "今日未能读取欧洲官方新闻" in pins


# --------------------------------------------------------------------------- #
# D2 — exact stance strings
# --------------------------------------------------------------------------- #
def test_event_pins_stance_uses_exact_d2_strings(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    html = _render(vm)
    assert (
        "Public official press from Europe. UK items mark the map; EU, "
        "euro-area and EFTA items are listed only."
    ) in html
    assert (
        "欧洲官方公开新闻。英国条目标注于地图；欧盟、欧元区及 EFTA 条目仅列出。"
    ) in html
    # The old overclaim sentence is gone.
    assert "shown on this map" not in html
    assert "显示于本图" not in html


# --------------------------------------------------------------------------- #
# D3 — hoist shared publisher + jurisdiction labels
# --------------------------------------------------------------------------- #
def test_hoist_common_source_when_all_rows_share_publisher(tmp_path, monkeypatch):
    """All-same-source fixture renders `sm-common` once and zero per-row `src` spans."""
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    today = _today_utc()
    asof = today.isoformat()
    _write_custom_parquet(parquet, [
        {
            "title": "Bank Rate held at four percent",
            "url": "https://www.bankofengland.co.uk/news/2026/rate",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": asof,
        },
        {
            "title": "Monetary policy summary — second vote",
            "url": "https://www.bankofengland.co.uk/news/2026/rate2",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": asof,
        },
    ])
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    assert vm["public_news_state"] == "ok"
    assert vm["public_news_common"].get("source") == "Bank of England"
    assert vm["public_news_common"].get("jurisdiction") == "UK"
    html = _render(vm)
    pins = _pins_section(html)
    # sm-common renders exactly once.
    assert pins.count('class="sm-common"') == 1
    # Per-row src spans suppressed because source is hoisted.
    assert pins.count('<span class="src">') == 0
    # Per-row jurisdiction span suppressed because jurisdiction is hoisted.
    assert pins.count("<span>") == 0 or pins.count("<span>United Kingdom</span>") == 0


def test_hoist_common_kept_partial_when_only_source_shared(tmp_path, monkeypatch):
    """Mixed-source fixture renders per-row src spans and no hoisted source."""
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    today = _today_utc()
    asof = today.isoformat()
    _write_custom_parquet(parquet, [
        {
            "title": "Bank Rate held at four percent",
            "url": "https://www.bankofengland.co.uk/news/2026/rate",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": asof,
        },
        {
            "title": EU_TITLE,
            "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
            "source": "ec_presscorner",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
    ])
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    # Sources differ → no shared source; jurisdictions differ → no shared juris.
    assert "source" not in vm["public_news_common"]
    assert "jurisdiction" not in vm["public_news_common"]
    html = _render(vm)
    pins = _pins_section(html)
    # No hoist when values differ.
    assert 'class="sm-common"' not in pins
    # Per-row spans present.
    assert pins.count('<span class="src">') == 2


def test_hoist_common_only_jurisdiction_when_publishers_differ(tmp_path, monkeypatch):
    """Mixed-source / same-jurisdiction fixture hoists only jurisdiction."""
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    today = _today_utc()
    asof = today.isoformat()
    # Two EU rows from different publishers.
    _write_custom_parquet(parquet, [
        {
            "title": "Trade notice one",
            "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_a",
            "source": "ec_presscorner",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
        {
            "title": "Trade notice two",
            "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_b",
            "source": "another_eu",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
    ])
    # Inject the second_eu source with VERIFIED rights so it survives the filter.
    def _sources(cfg=None):
        return [
            {"key": "ec_presscorner", "publisher": "European Commission",
             "rights_state": "VERIFIED_PUBLIC_REUSE"},
            {"key": "another_eu", "publisher": "Eurostat News",
             "rights_state": "VERIFIED_PUBLIC_REUSE"},
        ]
    monkeypatch.setattr(europe_news_intel, "sources", _sources)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    assert vm["public_news_state"] == "ok"
    common = vm["public_news_common"]
    assert common.get("jurisdiction") == "EU"
    assert "source" not in common
    html = _render(vm)
    pins = _pins_section(html)
    assert pins.count('class="sm-common"') == 1
    assert pins.count('<span class="src">') == 2
    # Jurisdiction spans suppressed because juris is hoisted.
    assert pins.count("<span>European Union</span>") == 0


# --------------------------------------------------------------------------- #
# D4 — display-time rights filter
# --------------------------------------------------------------------------- #
def test_rights_filter_drops_unknown_and_unverified_sources(tmp_path, monkeypatch):
    """An unknown source key AND a source with rights_state=UNVERIFIED_EXCLUDED
    are both dropped before the row reaches the template."""
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    today = _today_utc()
    asof = today.isoformat()
    _write_custom_parquet(parquet, [
        {
            "title": UK_TITLE,
            "url": "https://www.bankofengland.co.uk/news/2026/rate",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": asof,
        },
        {
            "title": "Unknown-source EU row",
            "url": "https://example.org/x",
            "source": "unknown_publisher",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
        {
            "title": "Excluded-source EU row",
            "url": "https://example.org/y",
            "source": "excluded_publisher",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
    ])
    def _sources(cfg=None):
        return [
            {"key": "boe_news", "publisher": "Bank of England",
             "rights_state": "VERIFIED_PUBLIC_REUSE"},
            {"key": "excluded_publisher", "publisher": "An Excluded Source",
             "rights_state": "UNVERIFIED_EXCLUDED"},
            # 'unknown_publisher' is intentionally absent.
        ]
    monkeypatch.setattr(europe_news_intel, "sources", _sources)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    titles = [row["title"] for row in vm["public_news"]]
    assert UK_TITLE in titles
    assert "Unknown-source EU row" not in titles
    assert "Excluded-source EU row" not in titles
    # The hoisted source is the only VERIFIED one left.
    assert vm["public_news_common"].get("source") == "Bank of England"
    html = _render(vm)
    pins = _pins_section(html)
    assert "Unknown-source EU row" not in pins
    assert "Excluded-source EU row" not in pins
    assert "unknown_publisher" not in pins
    assert "excluded_publisher" not in pins


# --------------------------------------------------------------------------- #
# D5 — one mechanism for the GBR mark (template)
# --------------------------------------------------------------------------- #
def test_gbr_mark_mechanism_is_data_news_gbr_only(tmp_path, monkeypatch):
    """When only EU rows survive the rights filter, no UK row, the map MUST NOT
    emit data-news-gbr. The data-news="1" path-attribution is gone too."""
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    today = _today_utc()
    asof = today.isoformat()
    _write_custom_parquet(parquet, [
        {
            "title": EU_TITLE,
            "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
            "source": "ec_presscorner",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
    ])
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    html = _render(vm)
    assert not re.search(r'<figure[^>]*\bdata-news-gbr=', html, re.S)
    assert 'data-news="1"' not in html
    # The inline JS that used to mirror the table-row highlight must still be
    # present, but the GBR-marking IIFE is gone.
    assert "sm-tbl" in html


def test_template_no_inline_data_news_one_path_ricker():
    """The figure-level data-news-gbr="1" + CSS is the ONLY mechanism. The
    inline script block that stamped data-news="1" on the path is gone."""
    src = (ROOT / "templates" / "sanctions_map.html.j2").read_text(encoding="utf-8")
    assert "setAttribute('data-news'" not in src
    assert "setAttribute(\"data-news\"" not in src


# --------------------------------------------------------------------------- #
# D6 — mobile footprint
# --------------------------------------------------------------------------- #
def test_mobile_footprint_media_rule_present():
    """The @media (max-width:600px) rule that thickens the stroke in both
    themes is present in the rendered <style>."""
    text = (ROOT / "templates" / "sanctions_map.html.j2").read_text(encoding="utf-8")
    assert "@media (max-width:600px){.sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"],html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]{stroke-width:1.5;stroke-dasharray:13 8}}" in text


# --------------------------------------------------------------------------- #
# Standing invariants — l-en / l-zh balance + BANNED_IN_PINS
# --------------------------------------------------------------------------- #
def test_l_en_l_zh_balance_and_banned_invariants_after_fixes(tmp_path, monkeypatch):
    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet)
    monkeypatch.setattr(europe_news_intel, "_events_path", lambda: parquet)
    sdn, meta, cfg = _write_ofac(tmp_path)
    vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    html = _render(vm)
    pins = _pins_section(html)
    low = pins.lower()
    for word in BANNED_IN_PINS:
        assert word.lower() not in low, word
    assert "boe_news" not in pins
    assert "ec_presscorner" not in pins
    assert "GBR" not in pins
    assert html.count('class="l-en"') == html.count('class="l-zh"')
