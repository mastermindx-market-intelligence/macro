"""Additional historical readers preserve vendor units/venues and grant no PIT authority."""
import hashlib
import json

import pytest
import collectors.tiingo_archive as a
from lib.dataos.tiingo_views import research_rows
from lib.dataos.tiingo_reader import read_research_view
from scripts.tiingo_materialize import materialize_one


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def rows(source, symbol, payload, params=None):
    raw = json.dumps(payload).encode()
    receipt = {"source": source, "symbol": symbol, "vendor": "tiingo",
               "raw_sha256": hashlib.sha256(raw).hexdigest(),
               "observed_at_utc": "2026-10-09T12:00:00Z",
               "request_path": a.request_path(source, symbol, params)}
    return research_rows(raw, receipt)


@pytest.mark.parametrize("source,symbol", [("boats-bars", "AMD"), ("iex-bars", "AMD"),
                                            ("forex-bars", "eurusd"), ("equity-intraday-bars", "AMD")])
def test_intraday_retains_source_prices_but_does_not_claim_executable_basis(source, symbol):
    out = rows(source, symbol, [{"date": "2026-10-08T02:00:00.123456789Z",
                                "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1}],
               {"resampleFreq": "1min"})[0]
    assert out["vendor_close"] == 1.1
    assert out["bar_at_vendor"].endswith("123456789Z")
    assert out["canonical_price_basis_admitted"] is False
    assert out["executable_price_proven"] is False
    assert out["pit_backtest_eligible"] is False
    assert out["volume_available"] is False and out["vendor_volume"] is None
    assert "close_raw" not in out


def test_boats_bars_are_venue_overnight_not_nbbo():
    out = rows("boats-bars", "AMD", [{"date": "2026-10-08T02:00:00Z", "close": 2, "volume": 10}])[0]
    assert out["venue"] == "BOATS" and out["session"] == "overnight"
    assert out["is_nbbo"] is False
    assert out["vendor_volume"] == 10 and out["volume_unit_vendor"] == "shares"


def test_crypto_pair_currency_and_nested_volumes_are_retained():
    out = rows("crypto-bars", None, [{"ticker": "btcusd", "baseCurrency": "btc", "quoteCurrency": "usd",
                "priceData": [{"date": "2026-10-08T02:00:00Z", "close": 120000,
                               "volume": 2, "volumeNotional": 240000, "tradesDone": 3}]}],
               {"tickers": "btcusd", "resampleFreq": "1min"})[0]
    assert out["base_currency_vendor"] == "btc" and out["quote_currency_vendor"] == "usd"
    assert out["volume_base_currency"] == 2 and out["volume_quote_currency"] == 240000
    assert out["trades_done_vendor"] == 3
    assert out["venue_scope"] == "vendor_crypto_aggregation"


@pytest.mark.parametrize("payload", [
    [{"ticker": "ethusd", "priceData": []}],
    [{"ticker": "btcusd", "priceData": {} }],
    [{"ticker": "btcusd", "priceData": []}, {"ticker": "btcusd", "priceData": []}],
])
def test_crypto_invalid_or_unrequested_pair_is_not_silently_normalized(payload):
    with pytest.raises(ValueError):
        rows("crypto-bars", None, payload, {"tickers": "btcusd"})


def test_cancelled_split_is_preserved_without_applying_factor():
    out = rows("splits", "AMD", [{"ticker": "AMD", "permaTicker": "123", "exDate": "2020-01-01",
                                  "splitFrom": 1, "splitTo": 10, "splitFactor": 10, "splitStatus": "c"}])[0]
    assert out["split_factor_vendor"] == 10
    assert out["cancellation_reported"] is True
    assert out["eligible_for_factor_construction"] is False
    assert out["permaticker_vendor"] == "123"


def test_dividend_dates_and_zero_are_not_replaced_by_guessed_values():
    out = rows("distributions", "AMD", [{"exDate": "2020-01-01", "distribution": 0,
                                          "declarationDate": "2019-12-15", "paymentDate": None,
                                          "recordDate": "2019-12-31", "distributionFrequency": "c"}])[0]
    assert out["distribution_vendor"] == 0
    assert out["payment_date_vendor"] is None
    assert out["declaration_date_vendor"] == "2019-12-15"
    assert out["cancellation_reported"] is True
    assert out["actual_upstream_available_at_utc"] is None


def test_fund_fee_metrics_keep_prospectus_date_without_percentage_rescaling():
    out = rows("fund-fee-history", "FUND", [{"prospectusDate": "2020-01-01", "netExpense": 0.3,
                                             "feeWaiver": 0, "managementFee": None}])
    values = {x["metric_code"]: x["metric_value_vendor"] for x in out}
    assert values == {"netExpense": 0.3, "feeWaiver": 0.0, "managementFee": None}
    assert all(x["source_date_role"] == "prospectusDate" for x in out)
    assert all(x["pit_backtest_eligible"] is False for x in out)


def test_distribution_yield_metric_not_assumed_to_be_pct_or_return():
    out = rows("distribution-yield", "AMD", [{"date": "2020-01-01", "trailingDiv1Y": "2.5"}])[0]
    assert out["metric_value_vendor"] == 2.5
    assert out["metric_unit_status"] == "VENDOR_UNITS_NOT_REINTERPRETED"


@pytest.mark.parametrize("source", ["boats-bars", "forex-bars", "splits"])
def test_ticker_mismatch_is_rejected(source):
    payload = [{"ticker": "WRONG", "date": "2020-01-01T00:00:00Z", "exDate": "2020-01-01"}]
    with pytest.raises(ValueError):
        rows(source, "AMD", payload)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_boolean_and_nonfinite_numbers_are_not_prices(value):
    with pytest.raises(ValueError):
        rows("boats-bars", "AMD", [{"date": "2020-01-01T00:00:00Z", "close": value}])


def test_intraday_naive_time_is_not_promoted_to_utc():
    with pytest.raises(ValueError):
        rows("forex-bars", "eurusd", [{"date": "2020-01-01T12:00:00", "close": 1.1}])


def test_new_fields_requiring_unreviewed_metric_types_stay_raw_only():
    with pytest.raises(ValueError):
        rows("fund-fee-history", "FUND", [{"prospectusDate": "2020-01-01", "nestedFees": {"fee": 3}}])


def test_existing_news_owner_remains_separate():
    assert rows("news", None, [{"title": "Example"}]) is None


def test_additional_history_runs_through_existing_materializer_and_reader(lake):
    payload = [{"date": "2020-01-01T02:00:00Z", "close": 100, "volume": 12}]
    saved = lake.store_response("boats-bars", "AMD", a.request_path("boats-bars", "AMD"),
                                json.dumps(payload).encode(), received_at="2026-10-09T12:00:00Z")
    rec = json.loads(next((lake.root / "receipts").rglob("*.json")).read_text())
    result = materialize_one(lake.root, rec, free_floor=0)
    assert result["status"] == "WRITTEN"
    view = read_research_view("boats-bars", "2026-10-09", saved["raw_sha256"], root=lake.root, check_mount=False)
    assert view.rows[0]["vendor_close"] == 100
    assert view.pit_backtest_eligible is False


def test_additional_history_registry_is_proposed_with_exact_raw_lineage():
    from lib.dataos.registry import load_registry, DatasetStatus
    registry = load_registry()
    products = ("boats_bars", "iex_bars", "equity_intraday", "forex_bars", "crypto_bars",
                "splits", "distributions", "fund_fee_history", "distribution_yield")
    for suffix in products:
        source_id = "vendor.tiingo.raw." + suffix
        view_id = "vendor.tiingo.research." + suffix
        source, view = registry.get(source_id), registry.get(view_id)
        assert source.status is DatasetStatus.PROPOSED
        assert view.status is DatasetStatus.PROPOSED
        assert view.inputs == (source_id,)
        assert source.vendor == view.vendor == "tiingo"
        assert "scripts/tiingo_corpus_audit.py" in source.code_consumers
        assert "lib/dataos/tiingo_reader.py::read_research_view" in view.code_consumers
        assert source.storage.startswith("/Volumes/Mastermind/market-data/tiingo/raw/")
        assert view.storage.startswith("/Volumes/Mastermind/market-data/tiingo/normalized/")


def test_tiingo_registration_never_marks_fixture_data_as_produced():
    from lib.dataos.registry import load_registry, DatasetStatus, validate_registry
    registry = load_registry()
    ids = [name for name in registry.ids() if name.startswith("vendor.tiingo.")]
    assert len(ids) == 24
    assert all(registry.get(name).status is DatasetStatus.PROPOSED for name in ids)
    assert validate_registry(registry) == []
