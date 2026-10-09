"""Regression proofs for archive identity and false-PIT admission. Offline only."""
from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

import collectors.tiingo_archive as a
from lib.dataos.tiingo_reader import TiingoViewRefusal, read_research_view
from scripts.tiingo_materialize import materialize_one


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "EXTERNAL_MOUNT", tmp_path)
    return a.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def capture(lake, symbol="AMD", *, params=None, at="2026-10-09T12:00:00Z", source="eod-bars", raw=None):
    raw = raw if raw is not None else b'[{"date":"2020-01-02","close":10,"adjClose":9}]'
    path = a.request_path(source, symbol, params)
    saved = lake.store_response(source, symbol, path, raw, received_at=at)
    rec = next(json.loads(p.read_text()) for p in (lake.root / "receipts").rglob("*.json")
               if json.loads(p.read_text()).get("symbol") == symbol
               and json.loads(p.read_text()).get("request_path") == path)
    return saved, rec


def test_identical_prices_for_different_tickers_never_alias(lake):
    _, one = capture(lake, "AMD")
    _, two = capture(lake, "INTC")
    first = materialize_one(lake.root, one, free_floor=0)
    second = materialize_one(lake.root, two, free_floor=0)
    assert one["raw_sha256"] == two["raw_sha256"]
    assert first["path"] != second["path"]
    assert pq.read_table(lake.root / second["path"]).to_pylist()[0]["ticker_vendor"] == "INTC"


def test_same_statement_bytes_different_query_dimension_never_alias(lake):
    raw = b'[{"date":"2020-02-01","year":2019,"quarter":4,"statementData":{"incomeStatement":[{"dataCode":"netIncome","value":10}]}}]'
    _, one = capture(lake, source="fund-statements", params={"asReported": "true"}, raw=raw)
    _, two = capture(lake, source="fund-statements", params={"asReported": "false"}, raw=raw)
    first = materialize_one(lake.root, one, free_floor=0)
    second = materialize_one(lake.root, two, free_floor=0)
    assert first["path"] != second["path"]
    assert pq.read_table(lake.root / second["path"]).to_pylist()[0]["requested_as_reported"] is False


def test_manifest_checkbox_cannot_authorize_pit(lake):
    saved, rec = capture(lake)
    materialize_one(lake.root, rec, free_floor=0)
    file = next((lake.root / "manifests").rglob("*.json"))
    manifest = json.loads(file.read_text())
    manifest["pit_backtest_eligible"] = True
    file.write_text(json.dumps(manifest))
    with pytest.raises(TiingoViewRefusal):
        read_research_view("eod-bars", "2026-10-09", saved.get("receipt_id", saved["raw_sha256"]),
                           root=lake.root, check_mount=False, purpose="PIT_BACKTEST")


def test_existing_corrupt_output_is_not_reported_as_exists(lake):
    _, rec = capture(lake)
    out = materialize_one(lake.root, rec, free_floor=0)
    (lake.root / out["path"]).write_bytes(b"corrupt parquet")
    with pytest.raises(a.TiingoArchiveError):
        materialize_one(lake.root, rec, free_floor=0)


def test_corrupt_existing_raw_is_not_idempotent_success(lake):
    saved, rec = capture(lake)
    (lake.root / saved["path"]).write_bytes(b"corrupt gzip")
    with pytest.raises(a.TiingoArchiveError):
        capture(lake)


@pytest.mark.parametrize("clock", ["../outside", "2026-10-09", "2026-10-09T12:00:00", "not-a-clock"])
def test_capture_clock_must_be_aware_and_valid(lake, clock):
    with pytest.raises((ValueError, a.TiingoArchiveError)):
        capture(lake, at=clock)


def test_exact_endpoint_not_just_prefix_must_match(lake):
    with pytest.raises((ValueError, a.TiingoArchiveError)):
        lake.store_response("eod-bars", "AMD", "/tiingo/daily/INTC/prices", b"[]")


def test_repeated_raw_uses_original_receipt_observation(lake):
    first, _ = capture(lake)
    second, _ = capture(lake, at="2026-10-09T13:00:00Z")
    assert "receipt_id" in first
    assert first["receipt_id"] == second["receipt_id"]
    assert first["new_raw"] is True and second["new_raw"] is False


def test_receipt_context_must_match_output_rows(lake):
    saved, rec = capture(lake)
    materialize_one(lake.root, rec, free_floor=0)
    file = next((lake.root / "manifests").rglob("*.json"))
    manifest = json.loads(file.read_text())
    manifest["source_receipt_id"] = "0" * 64
    file.write_text(json.dumps(manifest))
    with pytest.raises(TiingoViewRefusal):
        read_research_view("eod-bars", "2026-10-09", saved.get("receipt_id", saved["raw_sha256"]),
                           root=lake.root, check_mount=False)
