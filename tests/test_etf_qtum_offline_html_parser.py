"""QTUM-only offline sponsor-table parser contract.

All source HTML in these fixtures is synthetically generated for unit tests.
No sponsor website, credential, ETF data snapshot, commercial rights grant,
collector constructor, fetch route or filesystem store is involved.
"""
from __future__ import annotations

import ast
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from collectors.etf_holdings import EtfHoldingsAdapter


def _source_html(source_day: str = "10/09/2026") -> str:
    header = "<tr><th>Ticker</th><th>Name</th><th>CUSIP</th><th>ETF Weight</th><th>Shares</th></tr>"
    rows = []
    for i in range(86):
        rows.append(
            f"<tr><td>ZZ{i:03d}</td><td>Synthetic issuer {i:03d}</td>"
            "<td>SYNTHETIC</td><td>1.111%</td><td>1,000</td></tr>"
        )
    for ticker, name in (
        ("FGXXX", "Synthetic money market fund"),
        ("Cash&Other", "Cash & Other"),
        ("TWD", "New Taiwan Dollar balance"),
        ("EUR", "Euro cash balance"),
    ):
        rows.append(
            f"<tr><td>{ticker}</td><td>{name}</td>"
            "<td>SYNTHETIC</td><td>1.111%</td><td>100</td></tr>"
        )
    return (
        f"<html><body><p>Data as of {source_day}</p>"
        '<table id="table-full-holdings">'
        + header + "".join(rows) + "</table></body></html>"
    )


def _parse(html: str | None = None, *, reference_date: date = date(2026, 10, 11)):
    # The parser is an uncalled static helper, not an instantiated collector.
    with (
        patch("socket.create_connection", side_effect=AssertionError("network forbidden")),
        patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")),
    ):
        return EtfHoldingsAdapter._parse_defiance_public_html(
            _source_html() if html is None else html, "QTUM",
            reference_date=reference_date,
        )


def test_synthetic_page_presentation_without_source_fetch():
    raw, asof = _parse()
    assert asof == "2026-10-09"
    assert len(raw) == 90
    assert list(raw) == ["ticker", "name", "source_cusip", "weight", "shares"]
    assert raw["weight"].tolist() == ["1.111%"] * 90
    assert raw["source_cusip"].tolist() == ["SYNTHETIC"] * 90


def test_native_normalizer_keeps_equities_but_not_balance_rows():
    raw, asof = _parse()
    normalized = EtfHoldingsAdapter._normalize(
        raw, "QTUM", asof, wcol="weight", scol="shares", mcol=None,
    )
    assert len(normalized) == 86
    assert normalized["market_value"].isna().all()
    assert normalized["shares"].notna().all()
    assert {"FGXXX", "Cash&Other", "TWD", "EUR"}.isdisjoint(set(normalized["ticker"]))
    assert all(str(x).startswith("ZZ") for x in normalized["ticker"])
    assert "source_cusip" not in normalized.columns


@pytest.mark.parametrize(
    "source_day,reference_day,expected_refusal",
    [
        ("10/09/2026", date(2026, 10, 11), False),
        ("10/11/2026", date(2026, 10, 11), False),
        ("10/04/2026", date(2026, 10, 11), False),
        ("10/03/2026", date(2026, 10, 11), True),
        ("10/12/2026", date(2026, 10, 11), True),
        ("10/13/2026", date(2026, 10, 11), True),
    ],
)
def test_date_window_refuses_any_future_effective_source(source_day, reference_day, expected_refusal):
    if expected_refusal:
        with pytest.raises(ValueError, match="source date outside qualified horizon"):
            _parse(_source_html(source_day), reference_date=reference_day)
    else:
        _, result_day = _parse(_source_html(source_day), reference_date=reference_day)
        month, day, year = source_day.split("/")
        assert result_day == f"{year}-{month}-{day}"


def test_duplicate_date_missing_date_and_wrong_fund_refuse():
    with pytest.raises(ValueError, match="ambiguous"):
        _parse(_source_html() + " Data as of 10/09/2026")
    with pytest.raises(ValueError, match="missing or ambiguous"):
        _parse(_source_html().replace("Data as of 10/09/2026", "Unknown date"))
    with pytest.raises(ValueError):
        EtfHoldingsAdapter._parse_defiance_public_html(
            _source_html(), "BLOK", reference_date=date(2026, 10, 11)
        )
    with pytest.raises(ValueError):
        EtfHoldingsAdapter._parse_defiance_public_html(
            _source_html(), "QTUM", reference_date=None
        )


def test_malformed_symbols_duplicate_tickers_and_invalid_weights_refuse():
    page = _source_html()
    for mutated in (
        page.replace(">ZZ001<", ">ZZ000<", 1),
        page.replace(">ZZ001<", ">ZZ 001<", 1),
        page.replace(">1.111%<", ">NaN%<", 1),
        page.replace(">1.111%<", ">101%<", 1),
        page.replace(">1,000<", ">infinite<", 1),
        page.replace("1.111%", "0.100%"),
    ):
        assert mutated != page
        with pytest.raises(ValueError):
            _parse(mutated)


def test_table_header_or_duplicate_table_refuses():
    page = _source_html()
    for mutated in (
        page.replace("table-full-holdings", "wrong-table", 1),
        page.replace(">ETF Weight<", ">Weight<", 1),
        page.replace("</body>", '<table id="table-full-holdings"></table></body>', 1),
    ):
        with pytest.raises(ValueError):
            _parse(mutated)


def test_static_parser_is_not_wired_into_any_live_fetch_or_save():
    source = Path(__file__).resolve().parents[1] / "collectors" / "etf_holdings.py"
    module = ast.parse(source.read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_parse_defiance_public_html"
    ]
    assert not calls, "parser cannot enter a network or persistence route without owner adoption"
