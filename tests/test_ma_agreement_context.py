"""Dated filing facts must not turn into funded cash or an automatic break fee."""
import html
from pathlib import Path

import pandas as pd
import pytest
from bs4 import BeautifulSoup

from engine.ma_agreement_context import featured_agreement, parse_agreement, qualified_agreement

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-10-20T05:00:00Z"


@pytest.fixture(scope="module")
def source():
    return pd.read_parquet(ROOT / "data/special_situations/agreement_sources.parquet").to_dict("records")[0]


@pytest.fixture(scope="module")
def premium():
    # The nightly featured deal may rotate. Qualify this retained filing against
    # its explicit consumer join, without pinning future nightly selection.
    return {"status": "computed", "issuer_key": "cik:1847590",
            "offer_accession": "0001140361-26-038492",
            "offer_form_type": "DEFM14A", "offer_filing_date": "2026-10-05"}


@pytest.fixture(scope="module")
def visible(source):
    soup = BeautifulSoup(source["archive_content"], "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def test_native_proxy_financing_and_directional_fees(source, premium):
    result = qualified_agreement(source, premium, as_of=NOW)
    assert result["status"] == "qualified"
    assert result["buyer"] == "Prive Parent, Inc."
    assert result["agreement_date"] == "2026-08-10"
    assert result["currency"] == "USD"  # Annex explicitly defines Dollars.
    assert result["equity_commitment"] == 605210000
    assert result["term_loan_commitment"] == 420000000
    assert result["revolver_commitment"] == 65000000
    assert result["delayed_draw_commitment"] == 65000000
    assert result["company_to_parent_fee"] == 26861672
    assert result["parent_to_company_fee"] == 46048580
    assert result["reduced_company_fee"] == 13430836
    assert result["reduced_fee_deadline"] == "2026-09-28"
    assert result["funded_amount"] is None
    assert result["fee_payable_now"] is None
    assert result["closing_probability"] is None
    assert result["financing_is_closing_condition"] is False
    assert result["other_closing_conditions_apply"] is True
    assert result["accepted_at"] == "2026-10-05T10:02:34+00:00"
    assert result["retrieved_at"] == "2026-10-20T04:23:16.977566+00:00"


@pytest.mark.parametrize("field,value", [
    ("issuer_key", "cik:320193"), ("status", "refused"),
    ("offer_accession", "0001140361-26-000001"), ("offer_form_type", "8-K"),
    ("offer_filing_date", "2026-10-04"),
])
def test_ticker_or_company_name_cannot_join_another_deal(source, premium, field, value):
    assert qualified_agreement(source, {**premium, field: value}, as_of=NOW) == {}


@pytest.mark.parametrize("field,value", [
    ("cik", "320193"), ("accession", "0001140361-26-000001"),
    ("document", "other.htm"), ("form", "8-K"),
    ("archive_content", b"unretained"), ("index_content", b"unretained"),
    ("archive_receipt", "{}"), ("index_receipt", "{}"),
])
def test_source_and_index_custody_are_both_required(source, premium, field, value):
    assert qualified_agreement({**source, field: value}, premium, as_of=NOW) == {}


@pytest.mark.parametrize("removed", [
    "not subject to any financing condition",
    "subject to the satisfaction or waiver of the conditions to the Closing",
    "subject to the satisfaction of certain customary conditions to funding",
    "on or prior to September 28, 2026",
    "Superior Proposal received from an Excluded Party",
    "prior to such termination an Acquisition Proposal",
    "publicly announced or publicly disclosed and not publicly withdrawn",
    "within 12 months following such termination",
    "Subject to certain limitations and cure provisions",
    "ready, willing and able",
    "references to “ $ ” or “ Dollars ” are references to U.S. dollars.",
])
def test_amounts_without_their_conditions_are_unavailable(visible, removed):
    assert removed in visible
    assert parse_agreement(html.escape(visible.replace(removed, "[missing]")).encode()) == {}


def test_duplicate_financing_is_ambiguous_not_first_match(visible):
    assert parse_agreement(html.escape(visible + " " + visible).encode()) == {}


def test_hidden_document_is_not_visible_evidence(source):
    assert parse_agreement(b'<div hidden>' + source["archive_content"] + b'</div>') == {}


def test_boundaries_and_retrieval_clock(source, premium):
    assert parse_agreement(b"x" * (4 * 1024 * 1024 + 1)) == {}
    assert parse_agreement(b"\xff") == {}
    assert qualified_agreement(source, premium, as_of="2026-10-20T04:23:16Z") == {}
    assert qualified_agreement(source, premium, as_of="2026-10-20T05:00:00") == {}


def test_native_consumer_cannot_fetch_or_invent_missing_cache(monkeypatch, premium, tmp_path):
    import requests
    def no_network(*args, **kwargs):
        raise AssertionError("retained agreement consumer cannot fetch")
    monkeypatch.setattr(requests.Session, "request", no_network)
    assert featured_agreement(ROOT, premium, as_of=NOW)["status"] == "qualified"
    assert featured_agreement(tmp_path, premium, as_of=NOW) == {}


def test_template_retains_conditions_dates_and_unavailable_state(premium):
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True, undefined=StrictUndefined)
    env.globals["t"] = lambda en, zh: en + " / " + zh
    template = env.get_template("_ma_agreement_context.html.j2")
    rendered = template.render(agreement=featured_agreement(ROOT, premium, as_of=NOW))
    assert "605,210,000" in rendered and "26,861,672" in rendered and "46,048,580" in rendered
    assert "not cash already funded" in rendered and "not a finding" in rendered
    assert "2026-09-28" in rendered and "not a current reduced-fee option" in rendered
    assert "12 months" in rendered and "cure provisions" in rendered
    assert "2026-10-05" in rendered and "2026-10-20T04:23" in rendered
    assert "不是当前仍可选择" in rendered and "并非已到账现金" in rendered
    missing = template.render(agreement={})
    assert "No agreement terms are qualified" in missing and "605,210,000" not in missing
