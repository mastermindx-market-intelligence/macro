"""Retained filing identity and honest same-tenor comparison, without network."""
from pathlib import Path
from decimal import Decimal

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from engine.bond_issue_terms import native_comparison, qualified_issue

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-20T04:00:00Z"


@pytest.fixture(scope="module")
def sources():
    return pd.read_parquet(ROOT / "data/corp_bonds/filing_pricing_sources.parquet").to_dict("records")


def test_native_source_prices_and_identifiers(sources):
    apple, hp = [qualified_issue(row, as_of=NOW) for row in sources]
    assert [r["cusip"] for r in apple] == ["037833EY2", "037833EZ9", "037833FA3", "037833FB1"]
    assert [r["cusip"] for r in hp] == ["40434LAR6", "40434LAS4"]
    assert [float(r["coupon_pct"]) for r in apple] == [4, 4.2, 4.5, 4.75]
    assert [r["spread_bps"] for r in apple] == [25, 30, 40, 50]
    assert [float(r["coupon_pct"]) for r in hp] == [5.4, 6.1]
    assert [r["spread_bps"] for r in hp] == [145, 175]
    expected = [
        ("4.070", "3.820", "99.804", 1500000000, "2028-05-12"),
        ("4.238", "3.938", "99.830", 1000000000, "2030-05-12"),
        ("4.527", "4.127", "99.840", 1000000000, "2032-05-12"),
        ("4.834", "4.334", "99.340", 1000000000, "2035-05-12"),
        ("5.462", "4.012", "99.732", 500000000, "2030-04-25"),
        ("6.130", "4.380", "99.778", 500000000, "2035-04-25"),
    ]
    for row, (issue_yield, treasury_yield, price, principal, maturity) in zip(apple + hp, expected):
        assert Decimal(str(row["yield_pct"])) == Decimal(issue_yield)
        assert Decimal(str(row["benchmark_yield_pct"])) == Decimal(treasury_yield)
        assert Decimal(str(row["price_pct"])) == Decimal(price)
        assert row["principal"] == principal
        assert row["maturity_date"] == maturity
        assert (Decimal(issue_yield) - Decimal(treasury_yield)) * 100 == row["spread_bps"]
    assert apple[0]["filed_date"] == "2025-05-06"
    assert apple[0]["accepted_at"] == "2025-05-06T00:58:13+00:00"
    assert hp[0]["accepted_at"] == "2025-04-14T20:35:15+00:00"
    assert all(r["currency_code"] is None for r in apple + hp)
    assert all("rating" not in r and "ticker" not in r for r in apple + hp)


@pytest.mark.parametrize("field,value", [
    ("cik", "47217"), ("accession", "0001140361-25-013780"),
    ("document", "other.htm"), ("form", "S-3"),
    ("archive_content", b"unknown"), ("index_content", b"unknown"),
    ("archive_receipt", "{}"), ("index_receipt", "{}"),
])
def test_wrong_source_identity_never_renders(sources, field, value):
    assert qualified_issue({**sources[0], field: value}, as_of=NOW) == []


def test_retrieval_clock_cannot_be_backdated(sources):
    assert qualified_issue(sources[0], as_of="2025-05-07T00:00:00Z") == []
    assert qualified_issue(sources[0], as_of="2026-10-20T03:33:39Z") == []


def test_comparison_is_same_tenor_but_different_pricing_dates(monkeypatch):
    import requests
    def no_network(*args, **kwargs):
        raise AssertionError("retained pricing consumer cannot fetch")
    monkeypatch.setattr(requests.Session, "request", no_network)
    result = native_comparison(ROOT, as_of=NOW)
    assert result["status"] == "qualified"
    assert [p["tenor_years"] for p in result["pairs"]] == [5, 10]
    pair = result["pairs"][0]["issues"]
    assert [r["trade_date"] for r in pair] == ["2025-05-05", "2025-04-14"]
    assert [r["maturity_date"] for r in pair] == ["2030-05-12", "2030-04-25"]
    assert "rank" not in result and "recommendation" not in result


def test_absent_or_duplicate_cache_cannot_be_peer_coverage(tmp_path, sources):
    assert native_comparison(tmp_path, as_of=NOW)["status"] == "unavailable"
    p = tmp_path / "data/corp_bonds/filing_pricing_sources.parquet"
    p.parent.mkdir(parents=True)
    pd.DataFrame([sources[0], sources[0]]).to_parquet(p)
    assert native_comparison(tmp_path, as_of=NOW)["status"] == "unavailable"


def test_native_template_exposes_dates_source_and_scope():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True, undefined=StrictUndefined)
    html = env.get_template("capital_structure.html.j2").render(
        active_page="capital_structure", active_section="research",
        bond_comparison=native_comparison(ROOT, as_of=NOW))
    assert 'id="cs-bond-terms"' in html
    assert "Apple Inc." in html and "HP Inc." in html
    assert "+145" in html and "4.200%" in html
    assert "not current quotes" in html and "不是当前报价" in html
    assert "2025-05-05" in html and "2025-04-14" in html
    assert "2026-10-20T03:34" in html
    assert "US40434LAR69" in html
    assert "ny20048442x2_fwp.htm" in html and "ny20045886x5_fwp.htm" in html


def test_unavailable_template_does_not_publish_unqualified_pricing_dates():
    from bs4 import BeautifulSoup
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True, undefined=StrictUndefined)
    html = env.get_template("capital_structure.html.j2").render(
        active_page="capital_structure", active_section="research",
        bond_comparison={"status": "unavailable", "pairs": [], "sources": []})
    section = BeautifulSoup(html, "html.parser").select_one("#cs-bond-terms")
    assert "No comparison is shown" in section.get_text()
    assert "5 May 2025" not in section.get_text()
    assert not section.select(".cs-bond-issuer")
