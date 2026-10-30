"""Synthetic identity-boundary tests; no issuer parquet or SEC calls."""
import pytest

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
