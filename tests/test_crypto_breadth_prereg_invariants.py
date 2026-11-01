"""Invariants for the T14 breadth preregistration.

Pins existing functions only. Cohort as-of signatures named in the prereg
are not implemented in this file.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd

from engine.alt_cycle import breadth_view
from engine.crypto_market_state import build_market_state
from engine.crypto_universe import breadth_read, load_universe_snapshot
from engine.eth_state import build_asset_state
from scripts import build_crypto

ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "research/crypto_science/CRYPTO_T14_BREADTH_INCREMENT_PREREG_2026-10-12.md"
AS_OF = "2026-09-01"


def _breadth_row(as_of: str, change: float, *, symbol: str, history_days: int = 40) -> dict:
    return {
        "symbol": symbol,
        "as_of": as_of,
        "history_days": history_days,
        "change_30d": change,
        "price": 100.0,
        "change_24h": 0.0,
        "state": "Firm",
        "spark_dates": [],
        "spark_values": [],
    }


def _panel(as_of: str = AS_OF) -> list[dict]:
    rows = [
        _breadth_row(as_of, 12.0, symbol="BTC", history_days=5),
    ]
    for i in range(11):
        rows.append(
            _breadth_row(
                as_of,
                3.0 if i % 2 == 0 else -4.0,
                symbol=f"A{i}",
            )
        )
    return rows


def _cut_at(rows: list[dict], as_of: str) -> list[dict]:
    """Rows whose own as_of is on or before the study date."""
    return [row for row in rows if row.get("as_of") and row["as_of"] <= as_of]


def _write_market(root: Path, symbol: str, end: str, *, price: float, change: float, rank: int) -> None:
    dates = pd.date_range(end=end, periods=31, freq="D")
    frame = pd.DataFrame(
        {
            "source": "CoinGecko",
            "coin_id": symbol.lower(),
            "symbol": symbol,
            "name": symbol,
            "market_cap_rank": rank,
            "current_price": price,
            "market_cap": 1_000_000.0,
            "total_volume": 10_000.0,
            "change_24h_pct": change,
            "change_7d_pct": change,
            "change_30d_pct": change,
        },
        index=dates,
    )
    frame.to_parquet(root / f"market_{symbol.lower()}.parquet")


def test_breadth_asof_t_unchanged_when_later_roster_rows_appended():
    base = _panel()
    later = base + [
        _breadth_row("2026-09-20", -8.0, symbol=f"L{i}") for i in range(12)
    ]
    at_t = breadth_read(_cut_at(base, AS_OF))
    at_t_with_later_present = breadth_read(_cut_at(later, AS_OF))
    assert at_t == at_t_with_later_present
    assert at_t["as_of"] == AS_OF
    assert at_t["available"] is True
    # The uncut call follows the newest vintage. It is not the as-of-t measurement.
    uncut = breadth_read(later)
    assert uncut["as_of"] == "2026-09-20"
    assert uncut["value"] != at_t["value"]


def test_breadth_asof_t_unchanged_when_later_prices_appended(monkeypatch):
    short = pd.Series(1.0, index=pd.date_range("2026-07-01", AS_OF, freq="D"))
    long_index = pd.date_range("2026-07-01", "2026-10-01", freq="D")
    long = pd.Series(1.0, index=long_index)
    long.loc[long.index > AS_OF] = 50.0

    monkeypatch.setattr(build_crypto, "_series", lambda *args, **kwargs: short)
    first = build_crypto._enrich_universe(_panel())
    monkeypatch.setattr(build_crypto, "_series", lambda *args, **kwargs: long)
    second = build_crypto._enrich_universe(_panel())

    btc_first = next(row for row in first if row["symbol"] == "BTC")
    btc_second = next(row for row in second if row["symbol"] == "BTC")
    assert btc_first["spark_dates"][-1] == AS_OF
    assert btc_second["spark_dates"][-1] == AS_OF
    assert btc_first["spark_dates"] == btc_second["spark_dates"]
    assert btc_first["spark_values"] == btc_second["spark_values"]
    assert btc_first["history_days"] == btc_second["history_days"]
    assert btc_first["change_30d"] == 12.0
    assert long_index.max().strftime("%Y-%m-%d") > AS_OF
    assert breadth_read(first) == breadth_read(second)


def test_breadth_read_ignores_appended_price_fields():
    rows = [
        _breadth_row(AS_OF, 1.0 if i < 8 else -1.0, symbol=f"P{i}")
        for i in range(12)
    ]
    before = breadth_read(rows)
    decorated = []
    for row in rows:
        copy = dict(row)
        copy["spark_dates"] = ["2026-09-15", "2026-10-01"]
        copy["spark_values"] = [10.0, 999.0]
        copy["future_price"] = 999.0
        decorated.append(copy)
    assert breadth_read(decorated) == before
    assert before["basis"] == "reported_30d_return_positive"


def test_snapshot_latest_row_moves_when_later_rows_appended(tmp_path: Path):
    _write_market(tmp_path, "BTC", AS_OF, price=100.0, change=5.0, rank=1)
    first = load_universe_snapshot(50, root=tmp_path)
    assert first["as_of"] == AS_OF
    assert [row["symbol"] for row in first["rows"]] == ["BTC"]
    assert first["rows"][0]["price"] == 100.0

    _write_market(tmp_path, "BTC", "2026-09-20", price=140.0, change=9.0, rank=1)
    second = load_universe_snapshot(50, root=tmp_path)
    assert second["as_of"] == "2026-09-20"
    assert second["rows"][0]["price"] == 140.0

    _write_market(tmp_path, "BTC", AS_OF, price=100.0, change=5.0, rank=1)
    _write_market(tmp_path, "ETH", "2026-09-20", price=20.0, change=-3.0, rank=2)
    third = load_universe_snapshot(50, root=tmp_path)
    assert third["as_of"] == "2026-09-20"
    assert [row["symbol"] for row in third["rows"]] == ["ETH"]
    assert {item["reason"] for item in third["excluded"]} == {"OLDER_SNAPSHOT"}


def test_existing_outputs_do_not_carry_a_current_roster_label(tmp_path: Path):
    _write_market(tmp_path, "BTC", AS_OF, price=100.0, change=5.0, rank=1)
    _write_market(tmp_path, "ETH", AS_OF, price=20.0, change=-1.0, rank=2)
    snapshot = load_universe_snapshot(50, root=tmp_path)
    reading = breadth_read(snapshot["rows"])
    assert "roster_label" not in snapshot
    assert reading.get("roster_label") is None
    assert snapshot["as_of"] == AS_OF
    assert reading["as_of"] == AS_OF
    assert reading["basis"] == "reported_30d_return_positive"
    # A current-roster claim is the output key. Absence is unlabeled.
    assert reading.get("roster_label") != "current_roster"
    assert snapshot.get("roster_label") != "current_roster"


def test_existing_breadth_entrypoints_take_no_as_of_argument():
    for fn in (breadth_read, breadth_view, build_market_state, build_asset_state):
        assert "as_of" not in inspect.signature(fn).parameters


def test_single_name_relative_state_follows_the_series_end_and_has_no_roster_label():
    index = pd.date_range("2026-01-01", periods=120, freq="D")
    asset = pd.Series(range(100, 220), index=index, dtype=float)
    btc = pd.Series(100.0, index=index)
    early = build_asset_state("ETH", asset, btc, source="coinbase")
    extended = pd.date_range("2026-01-01", periods=160, freq="D")
    asset_later = pd.Series([*range(100, 220), *([50.0] * 40)], index=extended)
    btc_later = pd.Series(100.0, index=extended)
    later = build_asset_state("ETH", asset_later, btc_later, source="coinbase")
    assert early["as_of"] == "2026-04-30"
    assert later["as_of"] == "2026-06-09"
    assert early["relative"]["state"] == "Leading Bitcoin"
    assert later["relative"]["state"] == "Lagging Bitcoin"
    assert "roster_label" not in early
    assert early["display_only"] is True


def test_prereg_pins_question_controls_flow_rule_and_signatures():
    text = PREREG.read_text(encoding="utf-8")
    assert "Does breadth, relative leadership, or a separately qualified capital-source context" in text
    assert "NC-ROTATE" in text and "173" in text
    assert "NC-WEEK" in text and "isocalendar().week" in text
    assert "honestN(h, contrast)" in text
    assert "N_test < 8" in text
    assert "seed `20261012`" in text
    assert "B = 2000" in text
    assert "never an invented flow proxy" in text
    assert "supply_stock_growth" in text
    assert "roster_label` (`point_in_time`)" in text
    assert "roster_label = current_roster" in text
    assert "cohort_breadth_asof" in text
    assert "cohort_leadership_asof" in text
    assert "portfolio allocation authority" in text
    assert "p-value" in text
