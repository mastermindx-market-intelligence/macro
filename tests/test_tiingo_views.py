"""Data OS L1 Tiingo research adapters: hermetic PIT/price/receipts tests."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

import collectors.tiingo_archive as a
from lib.dataos.tiingo_views import (
    equity_eod, fundamentals_statements, fundamentals_daily, boats_messages,
    research_rows,
)
from scripts.tiingo_materialize import (
    verified_raw, materialize_one, materialize_many,
)


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "tiingo", check_mount=False, free_floor=0)


def _receipt(lake, name, sym, data, path=None):
    path = path or a.request_path(name, sym)
    saved = lake.store_response(name, sym, path,
                                json.dumps(data).encode("utf-8"),
                                received_at="2026-10-09T06:00:00+00:00")
    files = list((lake.root / "receipts").rglob("*.json"))
    rec = next(json.loads(f.read_text()) for f in files if f.stem.startswith(
        Path(saved["path"]).name.split("-")[0]))
    return rec


def test_equity_eod_raw_and_tradj_are_not_merged(lake):
    rec = _receipt(lake, "eod-bars", "NVDA", [{
        "date": "2024-06-03T00:00:00.000Z", "open": 1147, "high": 1154,
        "low": 1129, "close": 1150, "adjClose": 115,
        "adjOpen": 114.7, "volume": 20, "adjVolume": 200,
        "divCash": 0, "splitFactor": 1,
    }])
    rows = equity_eod([{
        "date": "2024-06-03", "close": 1150, "adjClose": 115,
        "volume": 20, "adjVolume": 200
    }], rec)
    assert rows[0]["close_raw"] == 1150
    assert rows[0]["close_tradj"] == 115
    assert rows[0]["volume_raw"] == 20
    assert rows[0]["volume_vendor_adjusted"] == 200
    assert rows[0]["adjustment_asof_utc"] == "2026-10-09T06:00:00+00:00"
    assert rows[0]["pit_backtest_eligible"] is False
    assert rows[0]["dataos_identity_admitted"] is False


def test_statements_fiscal_release_metric_and_requested_as_reported(lake):
    path = a.request_path("fund-statements", "MSFT", {"asReported": "true"})
    rec = _receipt(lake, "fund-statements", "MSFT", [], path=path)
    rows = fundamentals_statements([{
        "date": "2022-10-27T20:00:00Z", "year": 2022, "quarter": 3,
        "statementData": {
            "incomeStatement": [{"dataCode": "netIncome", "value": 42}],
            "cashFlow": [{"dataCode": "cashflow", "value": 18}],
        }
    }], rec)
    assert len(rows) == 2
    assert rows[0]["requested_as_reported"] is True
    assert rows[0]["statement_public_release_date_vendor"] == "2022-10-27T20:00:00Z"
    assert rows[0]["actual_upstream_available_at_utc"] is None
    assert rows[1]["metric_code"] == "cashflow"


def test_statement_bad_release_structure_raises(lake):
    rec = _receipt(lake, "fund-statements", "MSFT", [])
    with pytest.raises(ValueError, match="statementData"):
        fundamentals_statements([{"statementData": []}], rec)


def test_daily_fund_dynamic_metrics_preserved(lake):
    rec = _receipt(lake, "fund-daily", "MSFT", [])
    rows = fundamentals_daily([{"date": "2025-10-04", "marketCap": 100,
                                "nextNewMetric": 3.2}], rec)
    assert {row["metric_code"] for row in rows} == {"marketCap", "nextNewMetric"}
    assert all(row["pit_backtest_eligible"] is False for row in rows)


def test_boats_mixed_trade_quote_fields_all_represented(lake):
    msg = [
        {"service": "boats", "data": ["Q", "2026-10-09T01:00Z", 17,
                                      "AAPL", 500, 220.1, 220.15, 220.2, 600]},
        {"service": "boats", "data": ["T", "2026-10-09T01:01Z", 18,
                                      "AAPL", 220.18, 300, "@", "F", "", "X"]},
    ]
    receipt = lake.store_boats_batch([
        ("2026-10-09T01:00:00Z", json.dumps(msg[0])),
        ("2026-10-09T01:01:00Z", json.dumps(msg[1])),
    ])
    recfile = next((lake.root / "receipts" / "boats-firehose").rglob("*.json"))
    rec = json.loads(recfile.read_text())
    rows = research_rows(
        gzip.decompress((lake.root / receipt["path"]).read_bytes()), rec)
    assert len(rows) == 2
    assert rows[0]["bid_raw"] == 220.1
    assert rows[1]["sale_conditions"][1] == "F"
    assert rows[1]["is_break"] is False
    assert all(r["is_nbbo"] is False for r in rows)


def test_raw_only_is_explicit_not_normalized(lake):
    rec = _receipt(lake, "news", None, [{"title": "test"}])
    assert research_rows(b'[{"title":"test"}]', rec) is None
    assert materialize_one(lake.root, rec, free_floor=0)["status"] == "RAW_ONLY"


def test_materialize_eod_writes_immutable_parquet(lake):
    rec = _receipt(lake, "eod-bars", "AMD", [{
        "date": "2026-10-08", "open": 222, "high": 225, "low": 221,
        "close": 223, "adjClose": 223, "volume": 10, "adjVolume": 10,
    }])
    before = materialize_one(lake.root, rec, free_floor=0, dry_run=True)
    assert before["status"] == "WOULD_WRITE"
    out = materialize_one(lake.root, rec, free_floor=0)
    assert out["status"] == "WRITTEN"
    same = materialize_one(lake.root, rec, free_floor=0)
    assert same["status"] == "EXISTS"
    table = pq.read_table(lake.root / out["path"]).to_pylist()
    assert table[0]["close_raw"] == 223
    assert table[0]["pit_backtest_eligible"] is False
    assert table[0]["adjustment_asof_utc"] == "2026-10-09T06:00:00+00:00"
    assert len(list((lake.root / "manifests").rglob("*.json"))) == 1


def test_materialize_mixed_boats_parquet_union_not_loses_trade(lake):
    lake.store_boats_batch([
        ("2026-10-09T01:00Z", json.dumps({"service": "boats", "data": [
            "Q", "2026-10-09T01:00Z", 10, "AMD", 2, 1, 1.1, 1.2, 4
        ]})),
        ("2026-10-09T01:01Z", json.dumps({"service": "boats", "data": [
            "B", "2026-10-09T01:01Z", 11, "AMD", 1.1, 12, "@", "F", "", "X"
        ]})),
    ])
    rec = json.loads(next((lake.root / "receipts").rglob("*.json")).read_text())
    out = materialize_one(lake.root, rec, free_floor=0)
    vals = pq.read_table(lake.root / out["path"]).to_pylist()
    assert vals[0]["bid_raw"] == 1
    assert vals[1]["bid_raw"] is None
    assert vals[1]["sale_conditions"] == ["@", "F", "", "X"]
    assert vals[1]["is_break"] is True
    assert vals[1]["transport_continuity"] == "NOT_PROVEN"


def test_source_digest_mismatch_quarantined(lake):
    rec = _receipt(lake, "eod-bars", "AAPL", [{"date": "2026-10-08", "close": 5}])
    rec["raw_sha256"] = "0" * 64
    with pytest.raises(a.TiingoArchiveError, match="digest"):
        verified_raw(lake.root, rec)


def test_external_path_escape_quarantined(lake):
    rec = _receipt(lake, "eod-bars", "AAPL", [{"date": "2026-10-08", "close": 5}])
    rec["raw_path"] = "../../../tmp/leak"
    with pytest.raises(a.TiingoArchiveError, match="escaped"):
        verified_raw(lake.root, rec)


def test_materialize_many_offline_reread(lake):
    _receipt(lake, "eod-bars", "AMD", [{"date": "2026-10-08", "close": 5}])
    _receipt(lake, "news", None, [{"title": "test"}])
    dry = materialize_many(lake.root, check_mount=False, free_floor=0,
                           dry_run=True, max_receipts=50)
    assert dry["would_write"] == 1 and dry["raw_only"] == 1
    live = materialize_many(lake.root, check_mount=False, free_floor=0,
                            dry_run=False, max_receipts=50)
    assert live["written"] == 1 and live["raw_only"] == 1
    repeat = materialize_many(lake.root, check_mount=False, free_floor=0,
                              dry_run=False, max_receipts=50)
    assert repeat["existing"] == 1 and repeat["raw_only"] == 1


def test_missing_output_manifest_is_verified_and_repaired(lake):
    rec = _receipt(lake, "eod-bars", "AMD", [
        {"date": "2026-10-08", "close": 25, "adjClose": 25}])
    saved = materialize_one(lake.root, rec, free_floor=0)
    assert saved["status"] == "WRITTEN"
    manifest = next((lake.root / "manifests").rglob("*.json"))
    manifest.unlink()
    dry = materialize_one(lake.root, rec, free_floor=0, dry_run=True)
    assert dry["status"] == "WOULD_REPAIR"
    repaired = materialize_one(lake.root, rec, free_floor=0)
    assert repaired["status"] == "REPAIRED_MANIFEST"
    assert manifest.is_file()


def test_orphaned_output_with_incorrect_prices_is_not_repaired(lake):
    import pyarrow as pa
    import pyarrow.parquet as pq

    rec = _receipt(lake, "eod-bars", "AMD", [
        {"date": "2026-10-08", "close": 25}])
    saved = materialize_one(lake.root, rec, free_floor=0)
    manifest = next((lake.root / "manifests").rglob("*.json"))
    manifest.unlink()
    parquet_path = lake.root / saved["path"]
    vals = pq.read_table(parquet_path).to_pylist()
    vals[0]["close_raw"] = 999999
    pq.write_table(pa.Table.from_pylist(vals), parquet_path, compression="zstd")
    with pytest.raises(a.TiingoArchiveError, match="disagrees"):
        materialize_one(lake.root, rec, free_floor=0)
    assert not manifest.exists()


# Pure read-side quality guards; no provider request or source-writer repair.
def _quality_receipt(source="eod-bars"):
    return {"source": source, "vendor": "tiingo", "symbol": "AMD",
            "raw_sha256": "a" * 64, "observed_at_utc": "2026-10-09T12:00:00Z",
            "request_path": "/tiingo/fundamentals/AMD/statements?asReported=true"}


def _quality_statement(**changes):
    row = {"date": "2020-02-01", "year": 2019, "quarter": 4,
           "statementData": {"incomeStatement": [{"dataCode": "netIncome", "value": 12}]}}
    row.update(changes)
    return row


@pytest.mark.parametrize("source", ["eod-bars", "fund-statements", "fund-daily"])
@pytest.mark.parametrize("bad", [True, False, float("nan"), float("inf"), "garbage", "1e-9999", [], {}])
def test_strict_numeric_view_rejects_malformed_vendor_value(source, bad):
    receipt = _quality_receipt(source)
    if source == "eod-bars":
        call = lambda: equity_eod([{"date": "2020-01-02", "close": bad}], receipt)
    elif source == "fund-daily":
        call = lambda: fundamentals_daily([{"date": "2020-01-02", "peRatio": bad}], receipt)
    else:
        report = _quality_statement(statementData={"incomeStatement": [{"dataCode": "netIncome", "value": bad}]})
        call = lambda: fundamentals_statements([report], receipt)
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("field,bad", [("year", True), ("year", "2019"), ("year", None),
    ("quarter", -1), ("quarter", 5), ("quarter", 2.5), ("quarter", True)])
def test_statement_fiscal_period_has_real_typed_bounds(field, bad):
    with pytest.raises(ValueError):
        fundamentals_statements([_quality_statement(**{field: bad})], _quality_receipt("fund-statements"))


@pytest.mark.parametrize("bad", [None, "bad-date", "2020-02-30", "2020-02-01trailing"])
def test_statement_release_date_is_valid_not_silent_text(bad):
    with pytest.raises(ValueError):
        fundamentals_statements([_quality_statement(date=bad)], _quality_receipt("fund-statements"))


def test_annual_zero_and_loss_zero_null_survive_without_pit_promotion():
    report = _quality_statement(quarter=0, statementData={"incomeStatement": [
        {"dataCode": "loss", "value": -25}, {"dataCode": "zero", "value": 0},
        {"dataCode": "absent", "value": None}, {"dataCode": "futureMetric", "value": "1.25"}]})
    result = fundamentals_statements([report], _quality_receipt("fund-statements"))
    assert [r["metric_value"] for r in result] == [-25, 0, None, 1.25]
    assert all(r["fiscal_quarter"] == 0 and not r["pit_backtest_eligible"] for r in result)


def test_duplicate_metric_key_is_not_two_independent_facts():
    report = _quality_statement(statementData={"incomeStatement": [
        {"dataCode": "netIncome", "value": 12}, {"dataCode": "netIncome", "value": 13}]})
    with pytest.raises(ValueError):
        fundamentals_statements([report], _quality_receipt("fund-statements"))


@pytest.mark.parametrize("code", [True, 15, "", " ", []])
def test_metric_code_is_nonempty_string(code):
    report = _quality_statement(statementData={"incomeStatement": [{"dataCode": code, "value": 12}]})
    with pytest.raises(ValueError):
        fundamentals_statements([report], _quality_receipt("fund-statements"))


def test_statement_metric_value_key_cannot_be_missing():
    report = _quality_statement(statementData={"incomeStatement": [{"dataCode": "netIncome"}]})
    with pytest.raises(ValueError):
        fundamentals_statements([report], _quality_receipt("fund-statements"))


@pytest.mark.parametrize("query", ["asReported=oops", "asReported=", "asReported=true&asReported=false"])
def test_as_reported_dimension_is_never_guessed(query):
    receipt = _quality_receipt("fund-statements")
    receipt["request_path"] = "/tiingo/fundamentals/AMD/statements?" + query
    with pytest.raises(ValueError):
        fundamentals_statements([_quality_statement()], receipt)


def test_nonempty_malformed_statement_is_not_an_empty_success():
    for section in (None, {}, {"incomeStatement": []}):
        with pytest.raises(ValueError):
            fundamentals_statements([_quality_statement(statementData=section)], _quality_receipt("fund-statements"))


def test_eod_duplicate_market_date_is_not_silently_double_counted():
    with pytest.raises(ValueError):
        equity_eod([{"date": "2020-01-02", "close": 10},
                    {"date": "2020-01-02", "close": 11}], _quality_receipt())


def test_eod_integer_volume_not_rounded_by_float_conversion():
    value = 2**53 + 1
    row = equity_eod([{"date": "2020-01-02", "close": 10, "volume": value}], _quality_receipt())[0]
    assert type(row["volume_raw"]) is int and row["volume_raw"] == value


@pytest.mark.parametrize("bad", [-1, 1.5, True])
def test_eod_raw_volume_must_be_nonnegative_integer(bad):
    with pytest.raises(ValueError):
        equity_eod([{"date": "2020-01-02", "close": 10, "volume": bad}], _quality_receipt())


def test_daily_fundamental_identity_fields_are_not_numeric_metrics():
    row = {"date": "2020-01-02", "ticker": "AMD", "peRatio": -2, "permaTicker": "123"}
    projected = fundamentals_daily([row], _quality_receipt("fund-daily"))
    assert [r["metric_code"] for r in projected] == ["peRatio"]
    assert projected[0]["permaticker_vendor"] == "123"


@pytest.mark.parametrize("source", ["eod-bars", "fund-daily"])
def test_unrequested_response_ticker_is_refused_in_pure_view(source):
    row = {"date": "2020-01-02", "ticker": "OTHER", "close": 10, "peRatio": 2}
    call = equity_eod if source == "eod-bars" else fundamentals_daily
    with pytest.raises(ValueError):
        call([row], _quality_receipt(source))



def test_json_duplicate_metric_keys_are_not_last_value_wins():
    raw = b'[{"date":"2020-01-02","close":10,"close":99}]'
    with pytest.raises(ValueError):
        research_rows(raw, _quality_receipt())


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e9999"])
def test_nonstandard_json_numbers_are_refused_not_missing(token):
    raw = ('[{"date":"2020-01-02","close":' + token + '}]').encode()
    with pytest.raises(ValueError):
        research_rows(raw, _quality_receipt())


@pytest.mark.parametrize("clock", ["2020-01-02T12:00:00+00:60", "2020-01-02T12:00:60Z", "2020-01-02T24:00:00Z"])
def test_source_time_components_may_not_be_normalized_into_another_time(clock):
    with pytest.raises(ValueError):
        equity_eod([{"date": clock, "close": 10}], _quality_receipt())


def test_valid_aware_source_date_keeps_the_original_date_and_text():
    value = "2020-01-02T23:45:12.123456789-05:00"
    row = equity_eod([{"date": value, "close": 10}], _quality_receipt())[0]
    assert row["market_date"] == "2020-01-02" and row["source_date_vendor"] == value


def test_distinct_report_release_vintages_are_kept_not_deduplicated():
    reports = [_quality_statement(date="2020-02-01"), _quality_statement(date="2020-03-01")]
    rows = fundamentals_statements(reports, _quality_receipt("fund-statements"))
    assert len(rows) == 2 and rows[0]["statement_public_release_date_vendor"] != rows[1]["statement_public_release_date_vendor"]


def test_stable_vendor_id_query_does_not_require_current_ticker_as_identity():
    receipt = _quality_receipt("fund-daily")
    receipt["symbol"] = "123"
    projected = fundamentals_daily([{"date": "2020-01-02", "ticker": "OLD", "permaTicker": "123", "peRatio": 2}], receipt)
    assert projected[0]["ticker_or_permaticker_vendor"] == "123"


def test_empty_response_is_distinct_from_empty_report_or_empty_daily_row():
    assert fundamentals_statements([], _quality_receipt("fund-statements")) == []
    assert fundamentals_daily([], _quality_receipt("fund-daily")) == []
    with pytest.raises(ValueError):
        fundamentals_daily([{"date": "2020-01-02"}], _quality_receipt("fund-daily"))



def test_integer_volume_lexeme_not_rounded_from_json_decimal():
    raw = b'[{"date":"2020-01-02","close":10,"volume":9007199254740993.0}]'
    assert research_rows(raw, _quality_receipt())[0]["volume_raw"] == 9007199254740993
