"""Licensed benchmark closes for the China Risk Radar measured pullback.

Synthetic vendor frames only; no network and no token.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from collectors import china_tushare
from collectors import tushare_index_daily as tid


def _vendor(rows):
    return pd.DataFrame(
        [{"ts_code": "000001.SS", "trade_date": d, "close": c} for d, c in rows])


@pytest.fixture
def store(tmp_path, monkeypatch):
    out = tmp_path / "tushare" / "index_daily.parquet"
    monkeypatch.setattr(tid, "OUT", out)
    monkeypatch.setattr(tid.tc, "enabled", lambda: True)
    return out


def _serve(monkeypatch, frame):
    calls = []

    def query(api_name, fields="", **params):
        calls.append((api_name, fields, params))
        return frame

    monkeypatch.setattr(tid.tc, "query", query)
    return calls


def test_registered_in_the_gated_china_plane():
    assert "tushare_index_daily" in china_tushare._MODULES


def test_gate_closed_reads_nothing(store, monkeypatch):
    monkeypatch.setattr(tid.tc, "enabled", lambda: False)
    calls = _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert calls == [] and not store.exists()


def test_first_fetch_starts_at_the_fixed_anchor_and_writes_iso_sessions(store, monkeypatch):
    calls = _serve(monkeypatch, _vendor([("20261009", 3301.12345), ("20261008", 3290.5)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 2
    api, fields, params = calls[0]
    assert api == "index_daily" and fields == "ts_code,trade_date,close"
    assert params == {"ts_code": "000001.SH", "start_date": "20230101", "end_date": "20261011"}
    held = pd.read_parquet(store)
    assert list(held.columns) == list(tid.COLUMNS)
    assert held["trade_date"].tolist() == ["2026-10-08", "2026-10-09"]
    assert held["close"].tolist() == [3290.5, 3301.1235]
    assert set(held["ticker"]) == {"000001.SS"}


def test_incremental_fetch_overlaps_and_keeps_first_seen(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20260930", 3200.0), ("20261009", 3300.0)]))
    tid.refresh(today=date(2026, 10, 9))
    first = pd.read_parquet(store).set_index("trade_date")["first_seen"].to_dict()
    calls = _serve(monkeypatch, _vendor([("20261009", 3300.0), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert calls[0][2]["start_date"] == "20260909"
    held = pd.read_parquet(store).set_index("trade_date")
    assert held.index.tolist() == ["2026-09-30", "2026-10-09", "2026-10-12"]
    assert held.loc["2026-10-09", "first_seen"] == first["2026-10-09"]


def test_no_new_session_leaves_the_store_untouched(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    tid.refresh(today=date(2026, 10, 9))
    before = store.read_bytes()
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert store.read_bytes() == before


def test_a_disagreeing_vendor_close_keeps_the_last_good_store(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    tid.refresh(today=date(2026, 10, 9))
    before = store.read_bytes()
    _serve(monkeypatch, _vendor([("20261009", 3333.0), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert store.read_bytes() == before


@pytest.mark.parametrize("frame", [
    None,
    pd.DataFrame(columns=["ts_code", "trade_date", "close"]),
    _vendor([("20261009", 0.0)]),
    _vendor([("20261009", float("nan"))]),
    _vendor([("2026-10-09", 3300.0)]),
    _vendor([("20261009", 3300.0), ("20261009", 3301.0)]),
    pd.DataFrame([{"ts_code": "399001.SZ", "trade_date": "20261009", "close": 10000.0}]),
    pd.DataFrame([{"ts_code": "000001.SS", "trade_date": "20261009"}]),
])
def test_inadmissible_responses_write_nothing(store, monkeypatch, frame):
    _serve(monkeypatch, frame)
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert not store.exists()


def test_identical_duplicate_rows_collapse(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20261009", 3300.0), ("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 1
