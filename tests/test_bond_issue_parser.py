"""Adversarial retained-table cases; no model output or network fixtures."""
from pathlib import Path

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.bond_issue_parser import parse_issue_terms

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def apple():
    return pd.read_parquet(ROOT / "data/corp_bonds/filing_pricing_sources.parquet").iloc[0].archive_content


def alter_field(content, label, *, value=None, remove=False, duplicate=False, hidden=False):
    soup = BeautifulSoup(content, "html.parser")
    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        nonempty = [cell for cell in cells if cell.get_text(strip=True)]
        if len(nonempty) == 2 and " ".join(nonempty[0].get_text(" ", strip=True).split()).rstrip(":") == label:
            if remove:
                row.decompose()
            elif duplicate:
                row.insert_after(BeautifulSoup(str(row), "html.parser"))
            elif hidden:
                row["style"] = "display: none"
            else:
                nonempty[1].clear()
                nonempty[1].append(value)
            return str(soup).encode()
    raise AssertionError("native field not found: " + label)


def test_native_coupon_is_not_yield_and_makewhole_is_not_issue_spread(apple):
    rows = parse_issue_terms(apple)
    assert len(rows) == 4
    assert rows[0]["coupon_pct"] == "4.000"
    assert rows[0]["yield_pct"] == "4.070"
    assert rows[0]["spread_bps"] == 25
    assert rows[-1]["spread_bps"] == 50


@pytest.mark.parametrize("label,value", [
    ("Coupon", "4.070%"),  # valid coupon remains distinct from the yield
    ("Benchmark Treasury Yield", "3.820%"),
])
def test_explicit_independent_field_values_are_preserved(apple, label, value):
    rows = parse_issue_terms(alter_field(apple, label, value=value))
    assert len(rows) == 4
    if label == "Coupon":
        assert rows[0]["coupon_pct"] == "4.070"


@pytest.mark.parametrize("label,value", [
    ("Yield", "4.750%"),
    ("Spread to Benchmark Treasury", "+250 Basis Points"),
    ("CUSIP/ISIN", "037833EY3 / US037833EY27"),
    ("CUSIP/ISIN", "037833EY2 / US037833EY28"),
    ("CUSIP/ISIN", "037833EZ9 / US037833EZ91"),  # duplicate tranche
    ("Maturity", "May 13, 2028"),
    ("Trade Date", "May 13, 2025"),
    ("Principal Amount", "$1,500 million"),
    ("Coupon", "NaN%"),
    ("Coupon", "-4.0%"),
    ("Issuer", "A different issuer"),
])
def test_ambiguous_or_inconsistent_native_terms_refuse_whole_filing(apple, label, value):
    assert parse_issue_terms(alter_field(apple, label, value=value)) == []


@pytest.mark.parametrize("operation", ["remove", "duplicate", "hidden"])
def test_incomplete_or_duplicate_table_field_is_not_filled_from_prose(apple, operation):
    changed = alter_field(apple, "Coupon", **{operation: True})
    changed += b"<p>Coupon: 4.000%</p>"
    assert parse_issue_terms(changed) == []


@pytest.mark.parametrize("wrapper", [
    '<div hidden>{}</div>', '<div aria-hidden="true">{}</div>',
    '<div style="display: none">{}</div>', '<template>{}</template>',
])
def test_hidden_false_table_cannot_replace_visible_native_values(apple, wrapper):
    fake = '<table><tr><td>Issuer:</td><td>False issuer</td></tr></table>'
    assert parse_issue_terms(apple + wrapper.format(fake).encode()) == parse_issue_terms(apple)


@pytest.mark.parametrize("content", [None, "html", b"", b"\xff", b"x" * (1024 * 1024 + 1), b"<p>Apple Inc. Coupon 4.000%</p>"])
def test_wrong_type_size_encoding_or_prose_refused(content):
    assert parse_issue_terms(content) == []
