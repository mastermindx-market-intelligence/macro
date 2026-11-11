from __future__ import annotations

import hashlib
import json
from datetime import date

import pandas as pd
import pytest

from engine.options_tape_archive import (
    SCHEMA,
    TapeArchiveIntegrityError,
    TapeArchiveSchemaError,
    archive_paths,
    archive_trade_nbbo,
    load_trade_nbbo,
)


def _frame(root: str, right: str, *, n: int = 2, extra: str | None = None) -> pd.DataFrame:
    rows = []
    for i in range(n):
        row = {
            "date": pd.Timestamp("2026-07-10"),
            "trade_timestamp": f"2026-07-10T10:00:0{i}.100",
            "quote_timestamp": f"2026-07-10T10:00:0{i}.000",
            "sequence": 100 + i,
            "expiration": "2026-08-21",
            "strike": 100.0 + i,
            "right": right,
            "price": 2.5 + i,
            "size": 10 + i,
            "exchange": "22",
            "bid": 2.4 + i,
            "ask": 2.6 + i,
            "condition": "0",
            "ext_condition1": "255",
            "ext_condition2": "255",
            "ext_condition3": "255",
            "ext_condition4": "255",
            "bid_size": 20 + i,
            "ask_size": 30 + i,
            "root": root,
            "bid_exchange": "11",
            "bid_condition": "0",
            "ask_exchange": "12",
            "ask_condition": "0",
        }
        if extra is not None:
            row["future_vendor_field"] = extra
        rows.append(row)
    return pd.DataFrame(rows)


def test_archive_writes_zstd_parquet_receipt_and_is_idempotent(tmp_path):
    calls = _frame("SPY", "C", extra="future")
    puts = _frame("SPY", "P", extra="future")

    first = archive_trade_nbbo(
        root="SPY",
        trade_date=date(2026, 7, 10),
        calls=calls,
        puts=puts,
        archive_root=tmp_path,
    )
    assert first["archive_status"] == "written"
    assert first["schema"] == SCHEMA
    assert first["rows"] == 4
    assert first["compressed_bytes"] > 0
    assert first["vendor_available_at"] is None

    parquet_path, receipt_path = archive_paths("SPY", "2026-07-10", archive_root=tmp_path)
    assert parquet_path.exists()
    assert receipt_path.exists()

    stored = pd.read_parquet(parquet_path)
    assert len(stored) == 4
    assert set(stored["right"]) == {"C", "P"}
    assert "future_vendor_field" in stored.columns
    assert set(stored["future_vendor_field"]) == {"future"}

    raw = parquet_path.read_bytes()
    receipt = json.loads(receipt_path.read_text())
    assert hashlib.sha256(raw).hexdigest() == receipt["sha256"]
    assert len(raw) == receipt["compressed_bytes"]

    before = raw
    second = archive_trade_nbbo(
        root="SPY",
        trade_date="2026-07-10",
        calls=calls.assign(price=999.0),
        puts=puts.assign(price=999.0),
        archive_root=tmp_path,
    )
    assert second["archive_status"] == "already_present"
    assert parquet_path.read_bytes() == before


def test_archive_fails_closed_on_content_receipt_mismatch(tmp_path):
    calls = _frame("KRE", "C")
    puts = _frame("KRE", "P")
    archive_trade_nbbo(
        root="KRE", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
    )
    parquet_path, _ = archive_paths("KRE", "2026-07-10", archive_root=tmp_path)
    with parquet_path.open("ab") as f:
        f.write(b"tamper")

    with pytest.raises(TapeArchiveIntegrityError, match="size mismatch|sha256 mismatch"):
        archive_trade_nbbo(
            root="KRE", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
        )


def test_archive_fails_closed_on_incomplete_pair(tmp_path):
    calls = _frame("QQQ", "C")
    puts = _frame("QQQ", "P")
    archive_trade_nbbo(
        root="QQQ", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
    )
    _, receipt_path = archive_paths("QQQ", "2026-07-10", archive_root=tmp_path)
    receipt_path.unlink()

    with pytest.raises(TapeArchiveIntegrityError, match="incomplete immutable archive pair"):
        archive_trade_nbbo(
            root="QQQ", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
        )


def test_archive_rejects_source_root_identity_mismatch(tmp_path):
    calls = _frame("SPY", "C")
    puts = _frame("QQQ", "P")
    with pytest.raises(TapeArchiveSchemaError, match="root identity mismatch"):
        archive_trade_nbbo(
            root="SPY", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
        )


def test_archive_preserves_zero_trade_observation(tmp_path):
    empty = _frame("SPY", "C", n=1).iloc[:0].copy()
    receipt = archive_trade_nbbo(
        root="SPY", trade_date="2026-07-11", calls=empty, puts=empty, archive_root=tmp_path
    )
    parquet_path, _ = archive_paths("SPY", "2026-07-11", archive_root=tmp_path)
    assert receipt["rows"] == 0
    assert pd.read_parquet(parquet_path).empty


def test_verified_archive_load_is_replayable(tmp_path):
    calls = _frame("SPY", "C")
    puts = _frame("SPY", "P")
    archive_trade_nbbo(
        root="SPY", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
    )
    loaded = load_trade_nbbo("SPY", "2026-07-10", archive_root=tmp_path)
    assert loaded is not None
    frame, receipt = loaded
    assert len(frame) == 4
    assert receipt["archive_status"] == "replayed"


def test_tape_flow_replays_archive_without_terminal(tmp_path, monkeypatch):
    import collectors.thetadata as td
    import engine.tape_flow as tape_flow
    import scripts.build_tape_flow_daily as mod

    calls = _frame("SPY", "C")
    puts = _frame("SPY", "P")
    archive_trade_nbbo(
        root="SPY", trade_date="2026-07-10", calls=calls, puts=puts, archive_root=tmp_path
    )
    monkeypatch.setenv("THETADATA_TAPE_ARCHIVE", str(tmp_path))
    monkeypatch.setattr(mod, "_TERMINAL_REACHABLE", False)
    monkeypatch.setattr(
        td, "bulk_trade_quote",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("vendor fetch must not run")),
    )
    monkeypatch.setattr(mod, "_get_prior_oi", lambda *a, **k: None)
    monkeypatch.setattr(mod, "_get_greeks_chain", lambda *a, **k: None)
    written = []
    monkeypatch.setattr(mod, "_upsert_daily", lambda root, row: written.append((root, row)))
    monkeypatch.setattr(mod, "_update_raw_manifest", lambda *a, **k: None)
    monkeypatch.setattr(
        tape_flow, "aggregate_day",
        lambda **kw: {
            "root": kw["root"], "date": str(kw["trade_date"]),
            "gross_premium": 1.0, "volume": 4, "trade_count": 4,
        },
    )

    result = mod._process_root_day("SPY", date(2026, 7, 10), "forward")
    assert result["status"] == "ok"
    assert result["raw_archive_status"] == "replayed"
    assert written and written[0][0] == "SPY"
