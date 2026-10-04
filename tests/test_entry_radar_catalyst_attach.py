"""Wave 2a attach tests for EDGAR store reader (W2A1+)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from collectors.edgar_earnings_8k import STORE_COLUMNS
from engine.entry_radar.catalyst_adapters import EDGAR_EARNINGS_OWNER
from engine.entry_radar.catalyst_context import (
    CatalystContextError,
    DEFAULT_MAX_SOURCE_STALENESS_SECONDS,
)
from engine.entry_radar.catalyst_edgar_store import (
    DEFAULT_LOOKBACK_DAYS,
    read_edgar_item_202_for_tickers,
)

DECISION = datetime(2026, 10, 2, 13, 4, tzinfo=timezone.utc)
GENERATED = DECISION


def _item202_row(**overrides):
    row = {
        "ticker": "ABC",
        "cik": 1234567,
        "accession": "0001234567-26-000001",
        "form": "8-K",
        "filing_date": "2026-10-02",
        "acceptance_datetime": (DECISION - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report_date": "2026-09-30",
        "items": "2.02,9.01",
    }
    row.update(overrides)
    return row


def _write_store(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows, columns=STORE_COLUMNS).to_parquet(path, index=False)


def _write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest))


def _paths(tmp_path: Path):
    store = tmp_path / "earnings_8k_dates.parquet"
    manifest = tmp_path / "earnings_8k_dates_manifest.json"
    return store, manifest


def test_W2A1_one_ticker_ok_manifest_and_evidence(tmp_path):
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(minutes=10)
    _write_store(store, [_item202_row()])
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    read = got.reads_by_ticker["ABC"]
    assert read.status == "ok"
    assert read.usable_at(DECISION) is True
    assert read.source_asof == ts
    assert read.fresh_until == ts + timedelta(seconds=DEFAULT_MAX_SOURCE_STALENESS_SECONDS)
    assert len(got.evidence_by_ticker["ABC"]) == 1
    ev = got.evidence_by_ticker["ABC"][0]
    assert ev.owner == EDGAR_EARNINGS_OWNER
    assert ev.known_at == ts
    assert got.refusals == {}
    assert got.error is None
    assert got.rows_scanned == 1
    assert got.source_asof == ts


def test_W2A1_stale_manifest_ts_still_emits_evidence(tmp_path):
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(hours=12)
    _write_store(
        store,
        [_item202_row(acceptance_datetime=(DECISION - timedelta(hours=14)).strftime("%Y-%m-%dT%H:%M:%SZ"))],
    )
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    read = got.reads_by_ticker["ABC"]
    assert read.status == "ok"
    assert read.usable_at(DECISION) is False
    assert len(got.evidence_by_ticker["ABC"]) == 1
    assert got.evidence_by_ticker["ABC"][0].known_at == ts


def test_W2A1_refusals_and_manifest_gaps(tmp_path):
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(minutes=10)
    old_accept = (DECISION - timedelta(days=DEFAULT_LOOKBACK_DAYS + 1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    rows = [
        _item202_row(items="9.01"),
        _item202_row(form="10-Q"),
        _item202_row(acceptance_datetime=""),
        _item202_row(acceptance_datetime=old_accept),
    ]
    _write_store(store, rows)
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 4,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
            "ticker:QQQ": {
                "ticker": "QQQ",
                "status": "skipped_no_cik",
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC", "ZZZ", "QQQ"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert sum(got.refusals.values()) == 3
    assert "ABC" not in got.evidence_by_ticker
    assert got.reads_by_ticker["ZZZ"].status == "unavailable"
    assert got.reads_by_ticker["ZZZ"].detail == "manifest entry missing"
    assert got.reads_by_ticker["QQQ"].status == "unavailable"
    assert got.rows_scanned == 4


def test_W2A1_manifest_clock_and_shard_refusals(tmp_path):
    store, manifest = _paths(tmp_path)
    future_ts = (GENERATED + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    _write_store(store, [_item202_row()])
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": future_ts,
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got.reads_by_ticker["ABC"].status == "unavailable"
    assert got.reads_by_ticker["ABC"].detail == "manifest ts after generated_at"

    ts = DECISION - timedelta(minutes=10)
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 2,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got2 = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got2.reads_by_ticker["ABC"].status == "unavailable"
    assert "n_shards_missing=2" in got2.reads_by_ticker["ABC"].detail


def test_W2A1_missing_files_and_bad_clocks(tmp_path):
    store, manifest = _paths(tmp_path)
    got_store = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got_store.error.startswith("store missing")
    assert got_store.reads_by_ticker["ABC"].status == "unavailable"

    _write_store(store, [_item202_row()])
    got_manifest = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got_manifest.error.startswith("manifest missing")
    assert got_manifest.reads_by_ticker["ABC"].status == "unavailable"

    with pytest.raises(CatalystContextError):
        read_edgar_item_202_for_tickers(
            tickers=["ABC"],
            decision_at=datetime(2026, 10, 2, 13, 4),
            generated_at=GENERATED,
            store_path=store,
            manifest_path=manifest,
        )
    with pytest.raises(CatalystContextError):
        read_edgar_item_202_for_tickers(
            tickers=["ABC"],
            decision_at=DECISION,
            generated_at=DECISION - timedelta(seconds=1),
            store_path=store,
            manifest_path=manifest,
        )


def test_W2A1_no_network_with_fetch_monkeypatch(tmp_path, monkeypatch):
    import requests

    def _boom(*_a, **_k):
        raise AssertionError("network")

    monkeypatch.setattr(requests, "get", _boom)
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(minutes=10)
    _write_store(store, [_item202_row()])
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got.reads_by_ticker["ABC"].status == "ok"
    assert len(got.evidence_by_ticker["ABC"]) == 1
