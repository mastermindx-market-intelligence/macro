"""Contract tests for lib/source_health_labels.py and provider-free page copy.

Product rule: product surfaces never name a data provider. The data-health panel
renders reviewed labels for collector ids (which stay unchanged in data and
logs), and page copy describes the data instead of naming where it came from.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib import source_health_labels as shl

ROOT = Path(__file__).resolve().parent.parent

# The served-page check. The `(` lookahead spares function names in inline JS.
_PAGE_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:yfinance|yahoo|tushare|polygon|massive)(?![A-Za-z0-9(])"
)


def test_every_label_is_bilingual_and_provider_free():
    for sid, pair in shl.LABELS.items():
        for lang in ("en", "zh"):
            text = pair[lang]
            assert text.strip(), (sid, lang)
            assert not shl.PROVIDER_RE.search(text), (sid, lang, text)
            assert not _PAGE_RE.search(text), (sid, lang, text)


@pytest.mark.parametrize("sid,en", [
    ("china_tushare", "China market data"),
    ("massive_stock_day", "US daily prices"),
    ("polygon_gex_accrual", "Options exposure accrual"),
    ("polygon_news", "News feed"),
    ("yahoo", "US quotes"),
])
def test_provider_named_ids_get_neutral_labels(sid, en):
    assert shl.label_for(sid)["en"] == en


# Fail closed: an unreviewed id may be named after a provider the token list
# does not know, so it never contributes its own words to the page.
@pytest.mark.parametrize("sid", ["acme_tushare_v9", "acme_stock_day", "bank_reserve-curve"])
def test_unreviewed_id_renders_generic_label(sid):
    assert shl.label_for(sid) == shl.GENERIC


def test_unreviewed_ids_lists_only_ids_without_a_label():
    assert shl.unreviewed_ids(["yahoo", "acme_stock_day", "breadth", "a_new_feed"]) == [
        "a_new_feed", "acme_stock_day",
    ]


def test_health_rows_warns_about_unreviewed_ids(monkeypatch, caplog):
    from scripts import build_site

    monkeypatch.setattr(build_site.store, "read_status", lambda: {"sources": {
        "acme_stock_day": {"status": "ok", "rows": 3},
        "breadth": {"status": "ok", "rows": 5},
    }})
    with caplog.at_level("WARNING"):
        rows = build_site.health_rows()
    assert [(r["name"], r["label"]) for r in rows] == [
        ("acme_stock_day", shl.GENERIC["en"]), ("breadth", "US market breadth"),
    ]
    assert "no reviewed label for acme_stock_day" in caplog.text


@pytest.mark.parametrize("raw,want", [
    ("pytrends not installed — Google Trends lane skipped",
     "client library not installed — provider lane skipped"),
    ("HTTP 504 from CNInfo", "HTTP 504 from provider"),
    ("HTTPSConnectionPool(host='api.hkma.gov.hk', port=443)",
     "HTTPSConnectionPool(host=remote, port=443)"),
    ("404 for https://example.org/data/file.csv", "404 for remote file"),
    ("massive_stock_day stale", "US daily prices stale"),
    ("yfinance: https://query1.finance.yahoo.com/v8/chart 429",
     "client library: remote file 429"),
    ("timeout from www.hkex.com.hk", "timeout from remote host"),
    ("api.polygon.io timed out", "remote host timed out"),
    # Tickers, attribute paths and module paths are not hosts.
    ("no data for 0700.HK", "no data for 0700.HK"),
    ("AttributeError: Ticker.info", "AttributeError: Ticker.info"),
    ("pandas.io parser error", "pandas.io parser error"),
    ("", ""),
])
def test_neutral_note_scrubs_providers_urls_and_hosts(raw, want):
    assert shl.neutral_note(raw) == want


def test_committed_status_ids_render_provider_free():
    status = ROOT / "data" / "run_status.json"
    if not status.is_file():
        pytest.skip("data/run_status.json is not in this checkout")
    sources = json.loads(status.read_text(encoding="utf-8")).get("sources", {})
    for sid, entry in sources.items():
        pair = shl.label_for(sid)
        assert not _PAGE_RE.search(pair["en"] + pair["zh"]), sid
        assert not _PAGE_RE.search(shl.neutral_note(entry.get("error") or "")), sid


# Pages whose copy used to credit a provider by name. `<polygon` SVG tags are
# markup, not copy, and Jinja comments never reach the page.
@pytest.mark.parametrize("template", [
    "canada_stock.html.j2", "intl_stock.html.j2", "stock.html.j2",
])
def test_page_copy_names_no_provider(template):
    src = (ROOT / "templates" / template).read_text(encoding="utf-8")
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    src = re.sub(r"</?polygon\b", "", src)
    assert _PAGE_RE.findall(src) == []
    assert "雅虎" not in src
