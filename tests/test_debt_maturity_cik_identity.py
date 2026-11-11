"""Synthetic identity-boundary tests; no issuer parquet or SEC calls."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from engine.cash_runway import extract_cash_runway
from engine.debt_maturity import BUCKETS, extract_maturity_ladder

from scripts import build_debt_maturity as producer


@pytest.fixture
def issuer_lookup(tmp_path, monkeypatch):
    ledger = tmp_path / "absent-ledger.json"
    issuer = tmp_path / "issuer.parquet"
    issuer.touch()
    monkeypatch.setattr(producer, "_cik_ledger_path", lambda: ledger)
    monkeypatch.setattr(producer, "_issuer_master_path", lambda: issuer)

    def lookup(raw_cik):
        monkeypatch.setattr(
            producer, "_load_issuer_master_ticker_cik_map_cached",
            lambda path: {"SYNTHETIC": raw_cik},
        )
        return producer.resolve_cik("synthetic")

    return lookup


@pytest.mark.parametrize("raw", [
    123456.75, "123456.75", float("inf"), float("-inf"), float("nan"),
    True, False, None, "", "NA", -123456, 0, "10000000000",
])
def test_invalid_issuer_cik_never_selects_a_different_identity(issuer_lookup, raw):
    assert issuer_lookup(raw) is None


@pytest.mark.parametrize("raw", [123456, 123456.0, "123456", "123456.0", "0000123456"])
def test_exact_integer_identity_remains_supported(issuer_lookup, raw):
    assert issuer_lookup(raw) == "0000123456"

# Source-document identity is stricter than issuer-parquet lookup normalization.


_CIK = "0000099999"
_AS_OF = date(2025, 6, 1)
_INVALID_SOURCE_CIKS = [
    None, "", "not-a-cik", 0, -1, True, False, 99999.5, 99999.0,
    float("nan"), float("inf"), float("-inf"), "10000000000", "0000320193",
]
_MATCHING_SOURCE_CIKS = [99999, "99999", "0000099999", " 99999 "]


def _source_facts():
    path = Path(__file__).parent / "fixtures" / "cash_runway" / "synthetic_burn.json"
    facts = json.loads(path.read_text())
    annual = deepcopy(facts["facts"]["us-gaap"]["CashAndCashEquivalentsAtCarryingValue"]
                      ["units"]["USD"][0])
    annual["val"] = 10_000_000
    facts["facts"]["us-gaap"][BUCKETS[0][1]] = {"units": {"USD": [annual]}}
    return facts


@pytest.fixture
def cache_receiver(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    ledger = tmp_path / "cik-ledger.json"
    ledger.write_text(json.dumps({"tickers": {"SYNTHETIC": _CIK}}))
    monkeypatch.setattr(producer, "_cache_dir", lambda: cache)
    monkeypatch.setattr(producer, "_cik_ledger_path", lambda: ledger)
    monkeypatch.setattr(producer, "_issuer_master_path", lambda: tmp_path / "absent.parquet")
    monkeypatch.setattr(producer, "_utc_now_iso", lambda: "2025-06-01T00:00:00Z")
    return cache


@pytest.mark.parametrize("extractor", [extract_cash_runway, extract_maturity_ladder])
@pytest.mark.parametrize("raw", _INVALID_SOURCE_CIKS)
def test_present_invalid_or_foreign_source_identity_is_not_missing(extractor, raw):
    facts = _source_facts()
    facts["cik"] = raw
    result = extractor(facts, cik=_CIK, as_of=_AS_OF)
    assert result["status"] == "identity_mismatch"


@pytest.mark.parametrize("raw", _INVALID_SOURCE_CIKS)
@pytest.mark.parametrize("existing_cache", [False, True])
def test_wired_identity_refusal_precedes_all_cache_effects(cache_receiver, raw, existing_cache):
    cache = cache_receiver
    target = cache / f"CIK{_CIK}.json"
    if existing_cache:
        assert producer.refresh_cache_for_cik(_CIK, full_companyfacts=_source_facts())
    before = target.read_bytes() if existing_cache else None
    rejected = _source_facts()
    rejected["cik"] = raw

    assert producer.refresh_cache_for_cik(_CIK, full_companyfacts=rejected) is False
    if existing_cache:
        assert target.read_bytes() == before
        assert sorted(p.name for p in cache.iterdir()) == [target.name]
        cik, retained, state = producer.load_debt_maturity_facts("synthetic")
        assert (cik, state) == (_CIK, "loaded")
        assert extract_cash_runway(retained, cik=cik, as_of=_AS_OF)["cash_usd"] == 50_000_000
    else:
        assert not cache.exists()


@pytest.mark.parametrize("raw", _MATCHING_SOURCE_CIKS + ["absent"])
def test_wired_matching_or_absent_identity_reaches_native_consumers(cache_receiver, raw):
    facts = _source_facts()
    if raw == "absent":
        facts.pop("cik")
    else:
        facts["cik"] = raw
    for extractor in (extract_cash_runway, extract_maturity_ladder):
        assert extractor(facts, cik=_CIK, as_of=_AS_OF)["status"] == "reported"

    assert producer.refresh_cache_for_cik(_CIK, full_companyfacts=facts)
    cik, cached, state = producer.load_debt_maturity_facts("synthetic")
    assert (cik, state) == (_CIK, "loaded")
    cash = extract_cash_runway(cached, cik=cik, as_of=_AS_OF)
    debt = extract_maturity_ladder(cached, cik=cik, as_of=_AS_OF)
    assert cash["status"] == debt["status"] == "reported"
    assert (cash["cash_usd"], cash["runway_months"]) == (50_000_000, 20.0)
    assert debt["total_reported_usd"] == 10_000_000
    assert set(cached["facts"]["us-gaap"]) <= set(producer._ALL_TAGS)


def test_explicit_confirmed_absence_retains_no_filings_semantics(cache_receiver):
    assert producer.refresh_cache_for_cik(_CIK, full_companyfacts=None)
    cik, facts, state = producer.load_debt_maturity_facts("synthetic")
    assert (cik, facts, state) == (_CIK, None, "confirmed_no_filings")
    for extractor in (extract_cash_runway, extract_maturity_ladder):
        assert extractor(facts, cik=cik, as_of=_AS_OF)["status"] == "no_filings"


