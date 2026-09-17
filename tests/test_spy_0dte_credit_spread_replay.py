from datetime import datetime, timedelta
from decimal import Decimal
import importlib.util
import sys
from pathlib import Path

PATH = (
    Path(__file__).parents[1]
    / "scripts"
    / "research"
    / "spy_0dte_credit_spread_replay.py"
)
SPEC = importlib.util.spec_from_file_location("spy_0dte_replay", PATH)
REPLAY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPLAY
SPEC.loader.exec_module(REPLAY)


def _quote(timestamp, bid, ask):
    return REPLAY.Quote(
        timestamp,
        Decimal(bid),
        Decimal(ask),
        100,
        100,
        6,
        65,
        50,
        50,
    )


def test_entry_and_exit_use_executable_sides():
    timestamp = datetime(2026, 9, 15, 9, 35)
    short = [_quote(timestamp, ".27", ".28")]
    long = [_quote(timestamp + timedelta(milliseconds=2), ".13", ".14")]

    entry = REPLAY.first_package_quote(
        short,
        long,
        action="entry",
        max_leg_age_seconds=Decimal("1"),
    )
    assert entry.value == Decimal(".13")

    exit_quote = REPLAY.first_package_quote(
        short,
        long,
        action="exit",
        max_leg_age_seconds=Decimal("1"),
    )
    assert exit_quote.value == Decimal(".15")


def test_package_synchrony_fails_closed():
    timestamp = datetime(2026, 9, 15, 9, 35)
    short = [_quote(timestamp, ".27", ".28")]
    long = [_quote(timestamp + timedelta(seconds=2), ".13", ".14")]

    assert (
        REPLAY.first_package_quote(
            short,
            long,
            action="entry",
            max_leg_age_seconds=Decimal("1"),
        )
        is None
    )
    assert REPLAY.first_package_quote(
        short,
        long,
        action="entry",
        max_leg_age_seconds=Decimal("5"),
    ).value == Decimal(".13")


def test_target_and_forensic_pnl_reconciliation():
    timestamp = datetime(2026, 9, 15, 15, 54, 41)
    short = [_quote(timestamp, ".02", ".03")]
    long = [_quote(timestamp, ".01", ".01")]

    target = REPLAY.first_target_debit(
        short,
        long,
        target_debit=Decimal(".02"),
        max_leg_age_seconds=Decimal("1"),
    )
    assert target.value == Decimal(".02")

    net = REPLAY.net_pnl_per_spread(
        Decimal(".13"),
        Decimal(".02"),
        fee_per_contract_side=Decimal(".65"),
    )
    assert net == Decimal("8.40")

    count, residual = REPLAY.infer_spread_count(Decimal("1067.36"), net)
    assert count == 127
    assert residual == Decimal(".56")
    assert (
        REPLAY.structural_max_loss_per_spread(
            Decimal("2"), Decimal(".13")
        )
        == Decimal("187")
    )


def test_payload_identity_and_side_quality():
    contract = REPLAY.Contract(
        "SPY", "2026-09-15", Decimal("755"), "put"
    )
    payload = {
        "response": [
            {
                "contract": {
                    "symbol": "SPY",
                    "expiration": "2026-09-15",
                    "strike": 755.0,
                    "right": "PUT",
                },
                "data": [
                    {
                        "timestamp": "2026-09-15T09:35:00.001",
                        "bid": 0.27,
                        "ask": 0.28,
                        "bid_size": 528,
                        "ask_size": 480,
                        "bid_exchange": 6,
                        "ask_exchange": 65,
                        "bid_condition": 50,
                        "ask_condition": 50,
                    }
                ],
            }
        ]
    }

    rows = REPLAY.qualifying_quotes(payload, contract, needed_side="bid")
    assert len(rows) == 1
    assert rows[0].bid == Decimal(".27")


def test_exit_long_zero_bid_is_source_present_conservative_carry_only():
    contract = REPLAY.Contract("SPY", "2023-01-03", Decimal("391"), "call")
    payload = {
        "response": [{
            "contract": {
                "symbol": "SPY", "expiration": "2023-01-03",
                "strike": 391.0, "right": "call",
            },
            "data": [{
                "timestamp": "2023-01-03T11:12:00.000",
                "bid": 0.0, "ask": 0.01,
                "bid_size": 0, "ask_size": 12,
                "bid_exchange": 0, "ask_exchange": 6,
                "bid_condition": 0, "ask_condition": 50,
            }],
        }]
    }
    assert REPLAY.qualifying_quotes(payload, contract, needed_side="bid") == []
    long_exit = REPLAY.qualifying_exit_quotes(payload, contract, role="long")
    assert len(long_exit) == 1 and long_exit[0].bid == Decimal("0")

    timestamp = datetime(2023, 1, 3, 11, 12)
    short = [_quote(timestamp, ".04", ".05")]
    package = REPLAY.first_package_quote(
        short, long_exit, action="exit", max_leg_age_seconds=Decimal("1")
    )
    assert package.value == Decimal(".05")
    assert package.long_liquidation_zero is True


def test_exit_zero_bid_requires_source_present_firm_long_ask():
    contract = REPLAY.Contract("SPY", "2023-01-03", Decimal("391"), "call")
    payload = {
        "response": [{
            "contract": {
                "symbol": "SPY", "expiration": "2023-01-03",
                "strike": 391.0, "right": "call",
            },
            "data": [{
                "timestamp": "2023-01-03T11:12:00.000",
                "bid": 0.0, "ask": 0.01,
                "bid_size": 0, "ask_size": 0,
                "bid_exchange": 0, "ask_exchange": 6,
                "bid_condition": 0, "ask_condition": 50,
            }],
        }]
    }
    assert REPLAY.qualifying_exit_quotes(payload, contract, role="long") == []


def test_new_invalidating_quote_clears_previously_firm_entry_side():
    t = datetime(2026, 9, 15, 9, 35)
    short = [
        _quote(t, ".20", ".21"),
        REPLAY.Quote(t + timedelta(milliseconds=500), Decimal("0"), Decimal(".21"), 0, 100, 0, 65, 0, 50),
    ]
    long = [_quote(t + timedelta(milliseconds=600), ".09", ".10")]
    assert REPLAY.first_package_quote(
        short, long, action="entry", max_leg_age_seconds=Decimal("1")
    ) is None


def test_new_invalidating_quote_clears_previously_firm_exit_side():
    t = datetime(2026, 9, 15, 15, 0)
    short = [
        _quote(t, ".01", ".02"),
        REPLAY.Quote(t + timedelta(milliseconds=500), Decimal(".01"), Decimal("0"), 100, 0, 6, 0, 50, 0),
    ]
    long = [_quote(t + timedelta(milliseconds=600), ".01", ".02")]
    assert REPLAY.first_package_quote(
        short, long, action="exit", max_leg_age_seconds=Decimal("1")
    ) is None


def test_zero_debit_exit_is_executable_not_dropped():
    t = datetime(2026, 9, 15, 15, 0)
    short = [_quote(t, ".00", ".01")]
    long = [_quote(t, ".01", ".02")]
    package = REPLAY.first_package_quote(
        short, long, action="exit", max_leg_age_seconds=Decimal("1")
    )
    assert package is not None and package.value == Decimal("0")


def test_start_at_seeds_predecision_state_without_using_future_rows():
    t = datetime(2026, 9, 15, 9, 35)
    short = [_quote(t - timedelta(milliseconds=200), ".20", ".21")]
    long = [_quote(t - timedelta(milliseconds=100), ".09", ".10")]
    packages = REPLAY.package_quotes(
        short, long, action="entry", max_leg_age_seconds=Decimal("1"),
        start_at=t, end_at=t + timedelta(seconds=1),
    )
    assert len(packages) == 1
    assert packages[0].timestamp == t
    assert packages[0].value == Decimal(".10")


def test_equal_timestamp_leg_updates_are_applied_before_evaluation():
    t = datetime(2026, 9, 15, 9, 35)
    short = [_quote(t, ".20", ".21")]
    long = [_quote(t, ".09", ".10")]
    packages = REPLAY.package_quotes(
        short, long, action="entry", max_leg_age_seconds=Decimal("1")
    )
    assert len(packages) == 1 and packages[0].value == Decimal(".10")
