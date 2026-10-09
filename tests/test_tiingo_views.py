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
