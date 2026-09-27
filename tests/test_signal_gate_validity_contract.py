"""The producer contract for next-session confluence receipt validity."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from engine.signal_gate import buy_signal, validity_block
from lib import nyse_calendar
from scripts.check_signal_gate_coherence import _check, main as coherence_main


def _block(as_of: str | None, emitted_at: str) -> dict:
    return validity_block(as_of, emitted_at, "pair-abc")


def _producer_payload(as_of: str, emitted_at: str, pair_id: str) -> dict:
    verdicts = {
        "AAPL": {"eligible": True, "tier_cascade": "T2", "asof": as_of, "weight": 1.0},
        "MSFT": {"eligible": False, "tier_cascade": None, "asof": as_of, "weight": None},
    }
    return {
        "as_of": as_of,
        "verdicts": {
            ticker: {**buy_signal(verdict), "asof": verdict["asof"]}
            for ticker, verdict in verdicts.items()
        },
        "emit": {
            "pair_id": pair_id,
            "at_utc": emitted_at,
            "writer": "build_stock_library",
        },
        "validity": validity_block(as_of, emitted_at, pair_id),
    }


def test_fresh_source_is_valid_for_the_next_session():
    block = _block("2026-09-18", "2026-09-18T22:35:00Z")

    assert block == {
        "schema": "signal_gate.validity/v1",
        "source_session": "2026-09-18",
        "emitted_at": "2026-09-18T22:35:00Z",
        "expected_last_session": "2026-09-18",
        "lag_sessions": 0,
        "settled": True,
        "valid_for_decision_sessions": ["2026-09-21"],
        "expiry_session": "2026-09-21",
        "lineage_token": "pair-abc",
    }


def test_stale_source_is_still_emitted_with_positive_lag():
    # Packet T2 as mandated: emitted intraday on Tuesday 2026-09-22 (16:44Z is before
    # the 20:00Z close), so the last COMPLETED session is Monday 2026-09-21 and a
    # Friday 2026-09-18 source is exactly one session stale. (The packet's own "lag 2"
    # arithmetic counted the still-open Tuesday session; seat ruling 2026-09-23.)
    block = _block("2026-09-18", "2026-09-22T16:44:00Z")

    assert block["source_session"] == "2026-09-18"
    assert block["expected_last_session"] == "2026-09-21"
    assert block["lag_sessions"] == 1
    assert block["settled"] is True


def test_stale_source_after_close_counts_the_completed_session():
    # Same source, emitted after Tuesday's close: Tuesday is now completed, lag 2.
    block = _block("2026-09-18", "2026-09-22T21:00:00Z")

    assert block["source_session"] == "2026-09-18"
    assert block["expected_last_session"] == "2026-09-22"
    assert block["lag_sessions"] == 2
    assert block["settled"] is True


def test_source_ahead_of_settled_calendar_is_unsettled_but_emitted():
    block = _block("2026-09-23", "2026-09-23T15:00:00Z")

    assert block["source_session"] == "2026-09-23"
    assert block["expected_last_session"] == "2026-09-22"
    assert block["lag_sessions"] == -1
    assert block["settled"] is False


@pytest.mark.parametrize(
    ("as_of", "expected_expiry"),
    [("2026-11-25", "2026-11-27"), ("2026-12-24", "2026-12-28"),
     ("2026-12-31", "2027-01-04")],
)
def test_expiry_crosses_holidays_without_raising(as_of, expected_expiry):
    emitted_at = f"{as_of}T22:35:00Z"
    block = _block(as_of, emitted_at)

    assert block["valid_for_decision_sessions"] == [expected_expiry]
    assert block["expiry_session"] == expected_expiry


@pytest.mark.parametrize("as_of", [None, "", "not-a-date", "9999-99-99"])
def test_unusable_source_emits_an_honest_null_block(as_of):
    block = _block(as_of, "2026-09-18T22:35:00Z")

    assert block["schema"] == "signal_gate.validity/v1"
    assert block["source_session"] is None
    assert block["emitted_at"] == "2026-09-18T22:35:00Z"
    assert block["expected_last_session"] is None
    assert block["lag_sessions"] is None
    assert block["settled"] is None
    assert block["valid_for_decision_sessions"] == []
    assert block["expiry_session"] is None
    assert block["lineage_token"] == "pair-abc"


@pytest.mark.parametrize(
    ("as_of", "emitted_at"),
    [
        ("2026-09-17", "2026-09-18T15:40:33Z"),
        ("2026-09-18", "2026-09-19T19:51:14Z"),
        ("2026-09-18", "2026-09-21T14:57:05Z"),
        ("2026-09-18", "2026-09-21T22:12:04Z"),
        ("2026-09-18", "2026-09-21T23:20:32Z"),
    ],
)
def test_source_session_is_never_relabeled_to_emission(as_of, emitted_at):
    block = _producer_payload(as_of, emitted_at, "pair-source")["validity"]

    assert block["source_session"] == as_of
    assert block["source_session"] != datetime.fromisoformat(
        emitted_at.replace("Z", "+00:00")
    ).date().isoformat()


def test_producer_payload_shape_is_json_safe():
    emitted_at = "2026-09-18T22:35:00Z"
    payload = _producer_payload("2026-09-18", emitted_at, "pair-producer")

    assert set(payload) == {"as_of", "verdicts", "emit", "validity"}
    assert payload["as_of"] == "2026-09-18"
    assert payload["emit"]["at_utc"] == emitted_at
    assert payload["emit"]["pair_id"] == "pair-producer"
    assert payload["validity"]["source_session"] == payload["as_of"]
    assert payload["validity"]["expiry_session"] == "2026-09-21"
    assert set(payload["verdicts"]) == {"AAPL", "MSFT"}
    assert all("asof" in verdict for verdict in payload["verdicts"].values())
    json.dumps(payload, separators=(",", ":"), allow_nan=False)


def test_coherence_checker_accepts_validity_and_asof(tmp_path, capsys):
    verdict = {
        "anchor_era": "abs-2026-09-18", "bars_to_cross": 0, "eligible": True,
        "htf_s1": True, "htf_s2": False, "provisional": False,
        "sq_anchor_era": "sq-2026-09-16", "ticks": 1, "tier_cascade": "T2",
        "tier_sub": "confirmed", "young_history": False, "asof": "2026-09-18",
    }
    board = {
        "as_of": "2026-09-18",
        "buy": [{"ticker": "AAPL", "signal": verdict}],
        "watch": [], "leaders": [], "laggards": [],
        "emit": {"pair_id": "pair-coherence", "at_utc": "2026-09-18T22:35:00Z",
                 "writer": "build_stock_library"},
    }
    gate = {
        "as_of": "2026-09-18", "verdicts": {"AAPL": verdict}, **{
            key: board[key] for key in ("emit",)
        },
        "validity": validity_block(
            "2026-09-18", "2026-09-18T22:35:00Z", "pair-coherence"),
    }
    factordata = tmp_path / "factordata"
    factordata.mkdir()
    board_path = factordata / "us_standouts.json"
    gate_path = factordata / "signal_gate.json"
    board_path.write_text(json.dumps(board))
    gate_path.write_text(json.dumps(gate))

    assert _check(str(board_path), str(gate_path)) == []
    assert coherence_main([str(board_path), str(gate_path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_calendar_contract_uses_only_the_owned_calendar_module():
    assert date.fromisoformat("2026-09-18") == nyse_calendar.expected_last_session(
        datetime(2026, 9, 18, 22, 35, tzinfo=timezone.utc)
    )
    assert nyse_calendar.session_n_forward(date(2026, 9, 18), 1) == date(2026, 9, 21)
