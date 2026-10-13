"""Fixed-basis crypto rotation: one basis on every row, no unqualified signal."""

from __future__ import annotations

import pytest

from engine.crypto_rotation import coverage, relative_returns

SNAPSHOT = "2026-10-11"
ORIGIN = "2026-09-11"


def _basis(**overrides):
    basis = {
        "origin_date": ORIGIN,
        "horizon_days": 30,
        "quote_currency": "USD",
        "cohort_snapshot_date": SNAPSHOT,
        "weighting": "equal_member",
        "benchmark": "BTC",
    }
    basis.update(overrides)
    return basis


def _row(symbol, return_pct, **extra):
    row = {
        "symbol": symbol,
        "as_of": SNAPSHOT,
        "window_origin": ORIGIN,
        "horizon_days": 30,
        "quote_currency": "USD",
        "weighting": "equal_member",
        "return_kind": "price",
        "instrument_kind": "spot",
        "return_pct": return_pct,
    }
    row.update(extra)
    return row


def test_basis_is_identical_on_every_comparison_row():
    basis = _basis(members=["BTC", "ETH", "SOL", "MISSING"])
    rows = [_row("BTC", 4.0), _row("ETH", 9.0), _row("SOL", None)]
    result = relative_returns(rows, basis=basis)
    echoed = result["basis"]
    assert echoed["origin_date"] == ORIGIN
    assert echoed["horizon_days"] == 30
    assert echoed["quote_currency"] == "USD"
    assert echoed["cohort_snapshot_date"] == SNAPSHOT
    assert echoed["weighting"] == "equal_member"
    assert echoed["benchmark"] == "BTC"
    assert echoed["members"] == ("BTC", "ETH", "SOL", "MISSING")
    assert [row["symbol"] for row in result["comparisons"]] == [
        "BTC", "ETH", "SOL", "MISSING",
    ]
    for row in result["comparisons"]:
        assert row["basis"] is echoed
    eth = result["comparisons"][1]
    assert eth["asset_return_pct"] == 9.0
    assert eth["benchmark_return_pct"] == 4.0
    assert eth["relative_return_pct"] == 5.0
    assert eth["signal"] is True
    btc = result["comparisons"][0]
    assert btc["relative_return_pct"] == 0.0
    assert btc["signal"] is False
    assert result["comparisons"][3]["reason"] == "absent"
    assert result["comparisons"][3]["relative_return_pct"] is None


def test_disqualifiers_produce_no_signal_row():
    rows = [
        _row("BTC", 4.0),
        _row("ETH", -30.0, instrument_kind="depeg"),
        _row("SOL", 15.0, instrument_kind="wrapper"),
        _row("DOGE", 22.0, supply_change=True),
        _row("ADA", 1.0),
    ]
    result = relative_returns(rows, basis=_basis())
    assert {row["symbol"] for row in result["signals"]} == {"ADA"}
    by_symbol = {row["symbol"]: row for row in result["comparisons"]}
    assert by_symbol["ADA"]["relative_return_pct"] == -3.0
    for symbol, reason in (
        ("ETH", "depeg"),
        ("SOL", "wrapper"),
        ("DOGE", "supply_change"),
    ):
        row = by_symbol[symbol]
        assert row["status"] == "withheld"
        assert row["reason"] == reason
        assert row["signal"] is False
        assert row["asset_return_pct"] is None
        assert row["relative_return_pct"] is None
        assert row["basis"] is result["basis"]
    got = coverage(rows, ["BTC", "ETH", "SOL", "DOGE", "ADA"])
    assert got["declared"] == 5
    assert got["available"] == 2
    assert got["missing"] == ["ETH", "SOL", "DOGE"]


def test_unavailable_member_lowers_coverage_and_stays_listed():
    cohort = ["BTC", "ETH", "SOL", "XRP"]
    complete = [
        _row("BTC", 5.0),
        _row("ETH", -12.0),
        _row("SOL", 3.0),
        _row("XRP", 1.0),
    ]
    full = coverage(complete, cohort)
    assert full == {
        "declared": 4,
        "available": 4,
        "missing": [],
        "window": {"origin_date": ORIGIN, "cohort_snapshot_date": SNAPSHOT},
    }
    null_return = [_row("BTC", 5.0), _row("ETH", -12.0), _row("SOL", 3.0), _row("XRP", None)]
    lowered = coverage(null_return, cohort)
    assert lowered["declared"] == 4
    assert lowered["available"] == 3
    assert lowered["missing"] == ["XRP"]
    assert lowered["available"] / lowered["declared"] < full["available"] / full["declared"]
    absent = coverage(null_return[:3], cohort)
    assert absent["declared"] == 4
    assert absent["available"] == 3
    assert absent["missing"] == ["XRP"]
    # A negative print is not why ETH remains available.
    assert "ETH" not in lowered["missing"]


def test_share_change_is_not_a_return():
    rows = [
        _row("BTC", 4.0),
        {
            "symbol": "ETH",
            "as_of": SNAPSHOT,
            "window_origin": ORIGIN,
            "horizon_days": 30,
            "quote_currency": "USD",
            "weighting": "equal_member",
            "instrument_kind": "spot",
            "return_kind": "market_cap_share",
            "return_pct": 12.5,
            "market_cap_share_change_pct": 12.5,
        },
    ]
    result = relative_returns(rows, basis=_basis())
    eth = next(row for row in result["comparisons"] if row["symbol"] == "ETH")
    assert eth["asset_return_pct"] is None
    assert eth["relative_return_pct"] is None
    assert eth["market_cap_share_change_pct"] == 12.5
    assert eth["relative_return_pct"] != eth["market_cap_share_change_pct"]
    assert eth["asset_return_pct"] != eth["market_cap_share_change_pct"]
    assert eth["reason"] == "share_change"
    assert eth["status"] == "withheld"
    assert eth["symbol"] not in {row["symbol"] for row in result["signals"]}
    got = coverage(rows, ["BTC", "ETH"])
    assert got["available"] == 1
    assert got["missing"] == ["ETH"]


def test_negative_return_stays_in_the_comparison():
    rows = [_row("BTC", 5.0), _row("ETH", -20.0)]
    result = relative_returns(rows, basis=_basis())
    eth = next(row for row in result["comparisons"] if row["symbol"] == "ETH")
    assert eth["status"] == "available"
    assert eth["asset_return_pct"] == -20.0
    assert eth["relative_return_pct"] == -25.0
    assert eth["signal"] is True
    got = coverage(rows, ["BTC", "ETH"])
    assert got["declared"] == 2
    assert got["available"] == 2
    assert got["missing"] == []


def test_basis_conflicts_raise_rather_than_guess():
    rows = [_row("BTC", 1.0)]
    with pytest.raises(ValueError, match="quote_currency"):
        relative_returns(rows, basis=_basis(quote_currency="EUR"))
    with pytest.raises(ValueError, match="weighting"):
        relative_returns(rows, basis=_basis(weighting="market_cap_share"))
    with pytest.raises(ValueError, match="origin_date"):
        relative_returns(rows, basis=_basis(origin_date="2026-09-10"))
    incomplete = _basis()
    del incomplete["horizon_days"]
    with pytest.raises(ValueError, match="basis missing"):
        relative_returns(rows, basis=incomplete)
    with pytest.raises(ValueError, match="horizon_days"):
        relative_returns(rows, basis=_basis(horizon_days=7))


def test_missing_benchmark_does_not_become_zero():
    result = relative_returns([_row("ETH", 8.0)], basis=_basis())
    eth = result["comparisons"][0]
    assert eth["asset_return_pct"] == 8.0
    assert eth["benchmark_return_pct"] is None
    assert eth["relative_return_pct"] is None
    assert eth["status"] == "unavailable"
    assert eth["reason"] == "benchmark_unavailable"
    assert result["signals"] == []
    assert result["benchmark_return_pct"] is None
    withheld_btc = relative_returns(
        [_row("BTC", -40.0, instrument_kind="depeg"), _row("ETH", 8.0)],
        basis=_basis(),
    )
    eth = next(row for row in withheld_btc["comparisons"] if row["symbol"] == "ETH")
    btc = next(row for row in withheld_btc["comparisons"] if row["symbol"] == "BTC")
    assert btc["status"] == "withheld"
    assert btc["relative_return_pct"] is None
    assert eth["benchmark_return_pct"] is None
    assert eth["relative_return_pct"] is None
    assert eth["reason"] == "benchmark_unavailable"
    assert withheld_btc["signals"] == []


def test_wrong_window_outside_cohort_and_unclassified_do_not_signal():
    basis = _basis(members=["BTC", "ETH"])
    unclassified = _row("ETH", 9.0)
    del unclassified["instrument_kind"]
    rows = [
        _row("BTC", 4.0),
        _row("SOL", 9.0, as_of="2026-10-10"),
        _row("DOGE", 100.0),
        unclassified,
    ]
    result = relative_returns(rows, basis=basis)
    assert [row["symbol"] for row in result["comparisons"]] == ["BTC", "ETH"]
    eth = result["comparisons"][1]
    assert eth["reason"] == "unclassified"
    assert eth["relative_return_pct"] is None
    assert eth["signal"] is False
    assert {row["symbol"] for row in result["signals"]} == set()
    mismatched = relative_returns(
        [_row("BTC", 4.0), _row("ETH", 9.0, window_origin="2026-09-10")],
        basis=_basis(),
    )
    eth = next(row for row in mismatched["comparisons"] if row["symbol"] == "ETH")
    assert eth["reason"] == "window_unavailable"
    assert eth["asset_return_pct"] is None
    assert eth["relative_return_pct"] is None


def test_identity_break_and_short_history_lower_coverage():
    rows = [
        _row("BTC", 4.0),
        _row("ETH", 50.0, history_reset="SOURCE_IDENTITY_CHANGED"),
        _row("SOL", 50.0, history_days=10),
    ]
    result = relative_returns(rows, basis=_basis())
    reasons = {row["symbol"]: row["reason"] for row in result["comparisons"]}
    assert reasons["ETH"] == "identity_break"
    assert reasons["SOL"] == "short_history"
    assert result["signals"] == []
    got = coverage(rows, ["BTC", "ETH", "SOL"])
    assert got["declared"] == 3
    assert got["available"] == 1
    assert got["missing"] == ["ETH", "SOL"]


def test_coverage_raises_when_usable_windows_disagree():
    other = _row("ETH", 2.0, as_of="2026-10-10", window_origin="2026-09-10")
    with pytest.raises(ValueError, match="more than one fixed window"):
        coverage([_row("BTC", 1.0), other], ["BTC", "ETH"])


def test_zero_and_bool_returns_are_not_guessed():
    zeros = coverage([_row("BTC", 0.0), _row("ETH", 0.0)], ["BTC", "ETH"])
    assert zeros["available"] == 2
    assert zeros["missing"] == []
    result = relative_returns([_row("BTC", 0.0), _row("ETH", 0.0)], basis=_basis())
    eth = next(row for row in result["comparisons"] if row["symbol"] == "ETH")
    assert eth["asset_return_pct"] == 0.0
    assert eth["relative_return_pct"] == 0.0
    flagged = coverage([_row("BTC", True)], ["BTC"])
    assert flagged["declared"] == 1
    assert flagged["available"] == 0
    assert flagged["missing"] == ["BTC"]
    assert flagged["window"] is None


def test_duplicate_symbol_raises():
    with pytest.raises(ValueError, match="duplicate row"):
        relative_returns([_row("ETH", 1.0), _row("ETH", -5.0)], basis=_basis())
