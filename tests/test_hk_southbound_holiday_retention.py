"""Independent southbound holdings writes must retain real provider observation dates."""
from datetime import date

import pandas as pd
import pytest

from engine import hk_southbound_stocks as sb
from lib import config, market_session


def row(day="2026-09-30", shares=100.0, code="00700.HK"):
    return {"HOLD_DATE": day, "SECUCODE": code, "SECURITY_NAME": "Synthetic",
            "HOLD_SHARES": shares, "HOLD_MARKET_CAP": 1000.0, "CLOSE_PRICE": 10.0}


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    initial = pd.DataFrame({"hold_shares": [100.0], "hold_mktcap": [1000.0],
                            "close": [10.0], "date": [pd.Timestamp("2026-09-30")]},
                           index=pd.Index(["0700.HK"], name="ticker"))
    sb._persist(initial)
    path = sb._store_path()
    return path, path.read_bytes()


@pytest.mark.parametrize("data", [
    [], [row("2026-10-07")], [row("2026-10-09")],
    [row("bad-date")], [row(shares="unavailable")],
])
def test_unusable_provider_snapshot_keeps_last_good_holdings(snapshot, monkeypatch, data):
    path, before = snapshot
    monkeypatch.setattr(sb, "_fetch_page", lambda *args: data)
    result = sb.fetch_snapshot(max_pages=1)
    assert path.read_bytes() == before
    assert result is not None
    assert result["date"].max() == pd.Timestamp("2026-09-30")
    assert result.loc["0700.HK", "hold_shares"] == 100.0


def test_holiday_retrieval_preserves_actual_hold_date_and_valid_correction(snapshot, monkeypatch):
    path, _before = snapshot
    monkeypatch.setattr(sb, "_fetch_page", lambda *args: [row(shares=110.0)])
    result = sb.fetch_snapshot(max_pages=1)
    assert result["date"].max() == pd.Timestamp("2026-09-30")
    history = pd.read_parquet(path)
    assert history.index.get_level_values("date").unique().tolist() == [pd.Timestamp("2026-09-30")]
    assert history.loc[(pd.Timestamp("2026-09-30"), "0700.HK"), "hold_shares"] == 110.0


def test_valid_historical_snapshot_can_accrue_without_regressing_latest(snapshot, monkeypatch):
    path, _before = snapshot
    monkeypatch.setattr(sb, "_fetch_page", lambda *args: [row("2026-09-29")])
    result = sb.fetch_snapshot(max_pages=1)
    assert result["date"].max() == pd.Timestamp("2026-09-30")
    assert set(pd.read_parquet(path).index.get_level_values("date")) == {
        pd.Timestamp("2026-09-29"), pd.Timestamp("2026-09-30")}


def test_cold_start_bad_snapshot_creates_no_holdings_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    monkeypatch.setattr(sb, "_fetch_page", lambda *args: [row("2026-10-07")])
    assert sb.fetch_snapshot(max_pages=1) is None
    assert not sb._store_path().exists()
