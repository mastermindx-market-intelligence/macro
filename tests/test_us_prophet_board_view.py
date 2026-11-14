"""Synthetic, causal checks for the published-board display allowlist."""
from copy import deepcopy
import math
import pytest
from engine.us_prophet_board_view import BoardDetailInvalid, project_board_detail


def board():
    return {"as_of": "2026-11-12", "buy": [{
        "ticker": "TEST", "name": "Synthetic company", "sector": "Industrials",
        "price": 10.123, "signal_asof": "2026-11-11",
        "entry_signal": {"status": "await_confluence", "headline": "Waiting for confirmation",
            "headline_zh": "等待确认", "buy_zone": {"low": 10, "high": 10}, "stop": 10, "chase_above": 12},
        "hold": {"invalidation": 8},
        "signal": {"reason": "Published reason", "above200": False, "weekly_bull": True,
            "provisional": False, "tier_observed_date": "2026-11-12", "tier_observation_provisional": True},
        "lane": "bottoming", "stage": "setting_up",
    }]}


def test_clocks_geometry_and_distinct_provisional_flags_survive_without_inference():
    source = board()
    result = project_board_detail(source, "TEST")
    row = result["row"]
    assert result["as_of"] == "2026-11-12"
    assert row["signal_asof"] == "2026-11-11"
    assert row["price_as_of"] is None
    assert "assessment_asof" not in row and "signal_asof" not in row["entry_signal"]
    assert row["price"] == 10.123
    assert row["entry_signal"]["buy_zone"] == {"low": 10, "high": 10}
    assert row["entry_signal"]["stop"] == 10
    assert row["hold"]["invalidation"] == 8
    assert row["signal"]["provisional"] is False
    assert row["signal"]["tier_observation_provisional"] is True
    assert row["entry_signal"]["status"] == "await_confluence"
    assert source == board()


def test_allowlist_drops_svg_sizing_plan_and_unrelated_source_fields():
    source = board()
    source["buy"][0].update({"spark_svg": "<svg>private</svg>", "size": 500, "plan": {"id": "unrelated"}})
    source["buy"][0]["entry_signal"].update({"spot": 999, "target": 777, "signal_asof": "2020-01-01"})
    row = project_board_detail(source, "TEST")["row"]
    assert set(row) == {"ticker", "name", "sector", "price", "price_as_of", "signal_asof", "entry_signal",
                       "entry_signal_null_reason", "hold", "signal", "lane", "stage"}
    assert set(row["entry_signal"]) == {"status", "headline", "headline_zh", "buy_zone", "stop", "chase_above"}
    assert row["price"] == 10.123


def test_missing_fields_zero_false_and_unknown_owner_vocabulary_are_distinct():
    source = board()
    row = source["buy"][0]
    row.update({"name": None, "hold": None, "price": 0, "signal": None, "stage": "future_stage"})
    row["entry_signal"].update({"status": "future_status", "buy_zone": None, "stop": 0, "chase_above": None})
    result = project_board_detail(source, "TEST")["row"]
    assert result["price"] == 0 and result["entry_signal"]["stop"] == 0
    assert result["signal"]["above200"] is None
    assert result["hold"]["invalidation"] is None
    assert result["entry_signal"]["buy_zone"] is None
    assert result["stage"] == "future_stage" and result["entry_signal"]["status"] == "future_status"


def test_no_main_row_never_reads_watch_leaders_or_candidate_plan_fallbacks():
    source = {"as_of": "2026-11-12", "buy": [], "watch": board()["buy"], "leaders": board()["buy"]}
    assert project_board_detail(source, "TEST") == {"status": "not_on_main_list", "ticker": "TEST", "as_of": "2026-11-12", "row": None}


def test_absent_entry_retains_its_reason_without_fabricating_geometry():
    source = board(); source["buy"][0]["entry_signal"] = None
    source["buy"][0]["entry_signal_null_reason"] = "owner_not_published"
    row = project_board_detail(source, "TEST")["row"]
    assert row["entry_signal"] is None and row["entry_signal_null_reason"] == "owner_not_published"


@pytest.mark.parametrize("source", [None, [], {}, {"as_of": "2026-02-30", "buy": []},
    {"as_of": "2026-11-12"}, {"as_of": "2026-11-12", "buy": None},
    {"as_of": "2026-11-12", "buy": [None]}, {"as_of": "2026-11-12", "buy": [{}]}])
def test_invalid_population_cannot_be_reported_as_absence(source):
    with pytest.raises(BoardDetailInvalid): project_board_detail(source, "TEST")


def test_duplicate_normalized_identity_is_rejected_even_when_another_symbol_is_requested():
    source = board(); duplicate = deepcopy(source["buy"][0]); duplicate["ticker"] = " test "
    source["buy"].append(duplicate)
    with pytest.raises(BoardDetailInvalid): project_board_detail(source, "OTHER")


@pytest.mark.parametrize("field,value", [("price", True), ("price", "10"), ("price", math.inf),
    ("price", math.nan), ("signal_asof", "2026-11-12T01:00:00Z"), ("price_as_of", "2026-11-12T01:00:00"),
    ("price_as_of", "2026-02-30"), ("price_as_of", "2026-11-12T01:00:00+01:99"),
    ("price_as_of", "2026-11-12T01:00:00+00:99"), ("price_as_of", "2026-11-12T24:00:00Z"),
    ("price", 10 ** 400), ("entry_signal", []), ("signal", "bad"), ("name", "x" * 1025)])
def test_malformed_selected_fields_fail_closed(field, value):
    source = board(); source["buy"][0][field] = value
    with pytest.raises(BoardDetailInvalid): project_board_detail(source, "TEST")


@pytest.mark.parametrize("clock", ["2026-11-12", "2026-11-12T14:30:00Z", "2026-11-12T09:30:00-05:00"])
def test_an_explicit_owner_price_clock_is_preserved(clock):
    source = board(); source["buy"][0]["price_as_of"] = clock
    assert project_board_detail(source, "TEST")["row"]["price_as_of"] == clock
