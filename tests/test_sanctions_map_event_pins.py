"""tests/test_sanctions_map_event_pins.py — W7-2 / MO-PAID-008.

Fixture-only public-news layer on sanctions_map.html. UK rows join to the
existing GBR path; EU/EA/EFTA stay a dated list. No second map, no lat/lon,
no overlay of shipping / military / satellite marks.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader

from engine import europe_news_intel, sanctions_map
from engine.i18n import t, td, tr
from engine.sanctions_map import rungs_for
from scripts.build_sanctions_map import _apply_public_news_path_marks

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


def _write_events_parquet(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "title": UK_TITLE,
                "url": "https://www.bankofengland.co.uk/news/2026/rate",
                "source": "boe_news",
                "jurisdiction": "UK",
                "asof": "2026-09-18",
                "seendate": "2026-09-18",
            },
            {
                "title": EU_TITLE,
                "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
                "source": "ec_presscorner",
                "jurisdiction": "EU",
                "asof": "2026-09-18",
                "seendate": "2026-09-17",
            },
        ]
    ).to_parquet(path, index=False)


def _render(vm, all_iso3=None):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.globals.update(tr=tr, td=td, t=t)
    rungs = rungs_for(vm, all_iso3 if all_iso3 is not None else {"RUS", "GBR", "USA"})
    html = env.get_template("sanctions_map.html.j2").render(vm=vm, rungs=rungs)
    return _apply_public_news_path_marks(html, vm)


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
    assert 'data-news="1"' in html
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
