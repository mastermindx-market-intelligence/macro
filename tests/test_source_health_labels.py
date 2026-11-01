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


def test_unreviewed_provider_id_falls_back_to_generic_and_is_reported():
    assert shl.label_for("acme_tushare_v9") == shl.GENERIC
    assert "acme_tushare_v9" in shl.unknown_ids()


def test_unreviewed_plain_id_is_de_slugged():
    assert shl.label_for("bank_reserve-curve")["en"] == "Bank reserve curve"
    assert "bank_reserve-curve" in shl.unknown_ids()


@pytest.mark.parametrize("raw,want", [
    ("pytrends not installed — Google Trends lane skipped",
     "client library not installed — provider lane skipped"),
    ("HTTP 504 from CNInfo", "HTTP 504 from provider"),
    ("HTTPSConnectionPool(host='api.hkma.gov.hk', port=443)",
     "HTTPSConnectionPool(host=remote, port=443)"),
    ("404 for https://example.org/data/file.csv", "404 for remote file"),
    ("massive_stock_day stale", "US daily prices stale"),
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
    "bonds.html.j2", "canada_stock.html.j2", "intl_stock.html.j2", "stock.html.j2",
])
def test_page_copy_names_no_provider(template):
    src = (ROOT / "templates" / template).read_text(encoding="utf-8")
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    src = re.sub(r"</?polygon\b", "", src)
    assert _PAGE_RE.findall(src) == []
    assert "雅虎" not in src
