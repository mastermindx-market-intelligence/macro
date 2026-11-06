"""Legacy parquet display gaps preserve dated identity and breadth semantics.

These are synthetic source-contract fixtures written to real parquet files;
the public loader and producer use their normal imports and real renderer.
"""
from __future__ import annotations

import math
import re

import pandas as pd
import pytest

from engine import crypto_universe as U
from scripts import build_crypto as C


def _history(periods=40, *, symbol="ASSET", rank=1, change_30d=10.0):
    dates = pd.date_range("2026-01-01", periods=periods)
    return pd.DataFrame(
        {
            "coin_id": f"{symbol.lower()}-id",
            "source": "fixture-market",
            "symbol": symbol,
            "name": f"Fixture {symbol}",
            "market_cap_rank": rank,
            "current_price": [100.0 + i / 7 for i in range(periods)],
            "change_24h_pct": 2.0,
            "change_7d_pct": 4.0,
            "change_30d_pct": change_30d,
            "market_cap": 1_000_000.0,
            "total_volume": 50_000.0,
        },
        index=dates,
    )


def _write_market(root, frame, name="asset"):
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"market_{name}.parquet"
    frame.to_parquet(path, engine="pyarrow")
    return path


def test_legacy_supplied_slots_reach_the_actual_renderer(tmp_path, monkeypatch):
    frame = _history()
    # An absent source date must not be invented by the display projection.
    frame = frame.drop(frame.index[5])
    dates = frame.index
    frame["current_price"] = frame["current_price"].astype(str)
    for position, value in [(8, "bad"), (9, None), (10, "inf"), (11, "0"), (12, "-1")]:
        frame.iloc[position, frame.columns.get_loc("current_price")] = value
    path = _write_market(tmp_path, frame)
    before = path.read_bytes()

    snapshot = U.load_universe_snapshot(root=tmp_path)
    assert snapshot["excluded"] == []
    row = snapshot["rows"][0]
    assert row["spark_dates"] == [str(day.date()) for day in dates]
    assert [i for i, value in enumerate(row["spark_values"]) if value is None] == [8, 9, 10, 11, 12]
    assert row["history_days"] == 34
    assert row["history_chip"] == "34D"
    assert row["price"] == float(frame.iloc[-1]["current_price"])
    assert (row["state"], row["tone"]) == ("Firm", "bull")
    assert row["as_of"] == str(dates[-1].date())
    assert path.read_bytes() == before

    monkeypatch.setattr(C.store, "read", lambda *_args: pd.DataFrame())
    rendered = C._enrich_universe(snapshot["rows"])[0]
    assert 'data-gap-count="5"' in rendered["spark"]
    path_data = re.search(r'class="ilx-path" d="([^"]+)"', rendered["spark"]).group(1)
    assert path_data.count("M") == 2
    assert "Latest missing" not in rendered["spark"]


def test_ninety_observations_and_breadth_ignore_display_slot_count(tmp_path):
    # Ten eligible assets retain 90 observations despite 93 display slots.
    # One short-history asset has 121 slots but only 29 observations; another
    # has history but no reported return. Neither can enter the denominator.
    dates = _history(121).index
    for i in range(12):
        frame = _history(
            121,
            symbol=f"ASSET{i}",
            rank=i + 1,
            change_30d=10.0 if i < 6 or i == 10 else -10.0,
        )
        if i < 10:
            frame.iloc[[30, 70, 119], frame.columns.get_loc("current_price")] = math.nan
        elif i == 10:
            frame["current_price"] = math.nan
            frame.iloc[0, frame.columns.get_loc("current_price")] = 100.0
            frame.iloc[-28:, frame.columns.get_loc("current_price")] = 101.0
        else:
            frame["change_30d_pct"] = math.nan
        _write_market(tmp_path, frame, f"asset{i}")

    snapshot = U.load_universe_snapshot(root=tmp_path)
    rows = snapshot["rows"]
    assert len(rows) == 12 and snapshot["excluded"] == []
    for row in rows[:10]:
        assert row["spark_dates"] == [str(day.date()) for day in dates[28:]]
        assert len(row["spark_values"]) == 93
        assert sum(value is not None for value in row["spark_values"]) == 90
        assert row["history_days"] == 90 and row["history_chip"] == "90D"
    assert len(rows[10]["spark_values"]) == 121
    assert rows[10]["history_days"] == 29 and rows[10]["history_chip"] == "Building"
    assert rows[11]["change_30d"] is None

    assert U.breadth_read(rows) == {
        "as_of": str(dates[-1].date()),
        "eligible": 10, "required": 10, "excluded": 2,
        "positive": 6, "denominator": 10,
        "basis": "reported_30d_return_positive",
        "available": True, "value": 60, "state": "Broad", "tone": "bull",
    }


@pytest.mark.parametrize("identity_column", ["source", "coin_id"])
def test_identity_reset_excludes_prior_identity_even_when_it_has_more_history(
    tmp_path, identity_column
):
    frame = _history(110)
    cutoff = 80
    frame.iloc[:cutoff, frame.columns.get_loc(identity_column)] = "previous-identity"
    frame.iloc[cutoff + 10, frame.columns.get_loc("current_price")] = math.nan
    _write_market(tmp_path, frame)

    row = U.load_universe_snapshot(root=tmp_path)["rows"][0]
    assert row["spark_dates"] == [str(day.date()) for day in frame.index[cutoff:]]
    assert len(row["spark_values"]) == 30
    assert row["spark_values"][10] is None
    assert row["history_days"] == 29
    assert row["history_chip"] == "Building"
    assert row["history_reset"] == "SOURCE_IDENTITY_CHANGED"
    assert row["id"] == "asset-id" and row["source"] == "fixture-market"
    assert row["price"] == frame.iloc[-1]["current_price"]
    assert (row["state"], row["tone"]) == ("Firm", "bull")
    assert U.breadth_read([row])["eligible"] == 0


@pytest.mark.parametrize("missing_columns", [("source",), ("coin_id",), ("source", "coin_id")])
def test_unresolved_latest_identity_keeps_empty_history_without_crashing(
    tmp_path, missing_columns
):
    frame = _history()
    for column in missing_columns:
        frame.iloc[-1, frame.columns.get_loc(column)] = None
    _write_market(tmp_path, frame)

    snapshot = U.load_universe_snapshot(root=tmp_path)
    assert snapshot["excluded"] == []
    row = snapshot["rows"][0]
    assert row["spark_dates"] == [] and row["spark_values"] == []
    assert row["history_days"] == 0 and row["history_chip"] == "Building"
    assert row["history_reset"] == "SOURCE_IDENTITY_CHANGED"
    assert row["price"] == frame.iloc[-1]["current_price"]
    assert row["id"] == ("asset" if "coin_id" in missing_columns else "asset-id")
    assert row["source"] == ("Unknown" if "source" in missing_columns else "fixture-market")
    assert (row["state"], row["tone"]) == ("Firm", "bull")


@pytest.mark.parametrize("missing_symbol", [None, math.nan, "", "  "])
def test_missing_latest_symbol_does_not_become_a_nan_or_blank_asset(tmp_path, missing_symbol):
    frame = _history()
    frame.iloc[-1, frame.columns.get_loc("symbol")] = missing_symbol
    _write_market(tmp_path, frame)

    snapshot = U.load_universe_snapshot(root=tmp_path)
    assert snapshot["rows"] == []
    assert [row["reason"] for row in snapshot["excluded"]] == ["MISSING_ASSET_IDENTITY"]


@pytest.mark.parametrize("latest_price", [math.nan, math.inf, 0.0, -1.0])
def test_invalid_latest_price_is_refused_without_backfilling_an_older_quote(
    tmp_path, latest_price
):
    frame = _history()
    frame.iloc[-1, frame.columns.get_loc("current_price")] = latest_price
    _write_market(tmp_path, frame)

    snapshot = U.load_universe_snapshot(root=tmp_path)
    assert snapshot["rows"] == []
    assert snapshot["as_of"] == str(frame.index[-1].date())
    assert snapshot["observed"] == 1
    assert len(snapshot["excluded"]) == 1
    assert snapshot["excluded"][0]["reason"] == "INVALID_LATEST_PRICE"


def test_complete_history_retains_existing_row_projection(tmp_path):
    frame = _history(121)
    _write_market(tmp_path, frame)
    snapshot = U.load_universe_snapshot(root=tmp_path)

    assert snapshot["excluded"] == []
    assert snapshot["rows"] == [{
        "id": "asset-id", "source": "fixture-market",
        "symbol": "ASSET", "name": "Fixture ASSET",
        "rank": 1, "price": float(frame.iloc[-1]["current_price"]),
        "change_24h": 2.0, "change_7d": 4.0, "change_30d": 10.0,
        "market_cap": 1_000_000.0, "volume": 50_000.0,
        "state": "Firm", "tone": "bull",
        "history_days": 90, "history_chip": "90D", "history_reset": None,
        "spark_dates": [str(day.date()) for day in frame.index[-90:]],
        "spark_values": [round(float(value), 8) for value in frame["current_price"].iloc[-90:]],
        "as_of": str(frame.index[-1].date()),
    }]

