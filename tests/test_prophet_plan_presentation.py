"""Original model terms cannot become a quote, fill or new entry instruction."""
import copy
import pytest

from engine.prophet_plan_presentation import present_plan_record


def test_original_terms_clocks_and_identity_have_distinct_sources():
    p = {"id": "ABC-BULL-20260801", "asset": "ABC", "entry": 100,
         "invalidation": 90, "targets": [115, 130], "horizon_days": 45,
         "entry_zone": {"low": 97, "high": 100}, "lifecycle_state": "ready",
         "plan_asof": "2026-08-02", "price_basis_date": "2026-08-01",
         "board_read": {"ticker": "ABC", "as_of": "2026-10-14", "fields": {
             "name": {"state": "available", "value": "Original Corp"}}},
         "last_price": 777, "recommended_action": "buy", "entry_date": "2026-08-03",
         "pulse": "published read", "pulse_zh": "已发布读数"}
    identity = {"name": "Different", "sector": "Industrials", "price": 999,
                "entry": 888, "as_of": "2026-10-15"}
    before = copy.deepcopy((p, identity))
    out = present_plan_record(p, identity=identity, episode={"newer": "ABC-BULL-20261001"})
    assert out["entry"] == 100 and out["t1"] == 115 and out["t2"] == 130
    assert (out["created_date"], out["price_basis_date"], out["screen_date"]) == (
        "2026-08-02", "2026-08-01", "2026-10-14")
    assert out["name"] == "Original Corp" and out["sector"] == "Industrials"
    assert out["href"] == "stock.html#ABC"
    assert out["newer_href"] == "#pv-ABC-BULL-20261001"
    assert out["life"] == "ready" and out["horizon_days"] == 45
    assert not ({"quote", "last_price", "action", "recommended_action", "fill", "entry_date",
                 "next_review", "return", "management_date"} & out.keys())
    assert (p, identity) == before


@pytest.mark.parametrize("bad", [None, True, False, 0, -1, float("nan"), float("inf"),
                                  "100", {}, [], 10 ** 1000])
def test_malformed_terms_are_not_formatted_as_prices(bad):
    out = present_plan_record({"entry": bad, "invalidation": bad, "targets": [bad, bad],
                               "entry_zone": {"low": bad, "high": 200}, "horizon_days": bad})
    assert all(out[k] is None for k in ("entry", "invalidation", "t1", "t2", "zone_low",
                                       "zone_high", "horizon_days"))


def test_missing_or_invalid_original_dates_do_not_borrow_the_screen_date():
    out = present_plan_record({"asset": "ABC", "plan_asof": "2026-02-30", "price_basis_date": "2026-13-01",
                               "recorded_at": "2026-01-02", "board_read": {"ticker": "ABC", "as_of": "2026-10-14"}})
    assert out["created_date"] is None and out["price_basis_date"] is None
    assert out["screen_date"] == "2026-10-14"
    assert present_plan_record({"recorded_at": "2026-01-02"})["created_date"] == "2026-01-02"


def test_partial_zone_unknown_state_and_unbound_metadata_remain_unavailable():
    out = present_plan_record({"lifecycle_state": ["ready"], "targets": "12345",
        "entry_zone": {"low": 100, "high": 90}, "horizon_days": 1.5,
        "board_read": {"fields": {"name": {"state": "unavailable", "value": "Do not use"}}}})
    assert out["life"] == "unknown" and out["name"] is None
    assert all(out[k] is None for k in ("zone_low", "zone_high", "t1", "t2", "horizon_days"))
    assert present_plan_record(None)["entry"] is None


@pytest.mark.parametrize("symbol", ["javascript:alert(1)", "ABC/../../x", 'ABC\" onclick=\"x', "ABC DEF"])
def test_invalid_identity_never_creates_a_native_route(symbol):
    out = present_plan_record({"asset": symbol}, episode={"newer": symbol})
    assert out["href"] is None and out["newer_href"] is None


def test_two_records_on_one_security_keep_separate_episodes_and_terms():
    a, b = [present_plan_record(p) for p in [
        {"id": "BRK.B-BULL-20260801", "asset": "BRK.B", "entry": 100},
        {"id": "BRK.B-BULL-20260901", "asset": "BRK.B", "entry": 150}]]
    assert a["href"] == b["href"] == "stock.html#BRK.B"
    assert a["plan_id"] != b["plan_id"] and (a["entry"], b["entry"]) == (100, 150)


def test_foreign_screen_does_not_supply_this_plan_identity_or_clock():
    out = present_plan_record({"asset": "ABC", "entry": 100,
        "board_read": {"ticker": "XYZ", "as_of": "2026-10-14", "fields": {
            "name": {"state": "available", "value": "Foreign Company"}}}},
        identity={"name": "Bound ABC identity"})
    assert out["name"] == "Bound ABC identity" and out["screen_date"] is None
    assert out["entry"] == 100


def _observed_plan(**changes):
    row = {"id": "ABC-BULL-20260801", "asset": "ABC", "entry": 100,
           "plan_asof": "2026-08-01", "price_basis_date": "2026-07-31",
           "management_status": "available", "management_asof": "2026-10-14",
           "last_price": 123.45, "last_price_asof": "2026-10-13",
           "recommended_action": "enter", "management_confidence": 91,
           "board_read": {"ticker": "ABC", "as_of": "2026-10-15"}}
    row.update(changes)
    return row


def test_dated_management_close_is_separate_from_original_terms_and_screen():
    row = _observed_plan()
    before = copy.deepcopy(row)
    out = present_plan_record(row)
    observation = out["observation"]
    assert observation == {"close": 123.45, "close_date": "2026-10-13",
                           "management_date": "2026-10-14", "price_frame_state": "unknown"}
    assert out["entry"] == 100
    assert (out["created_date"], out["price_basis_date"], out["screen_date"]) == (
        "2026-08-01", "2026-07-31", "2026-10-15")
    assert not {"action", "quote", "return", "fill", "confidence"} & observation.keys()
    assert row == before


@pytest.mark.parametrize("changes", [
    {"last_price_asof": None}, {"last_price_asof": "2026-02-30"},
    {"management_asof": None}, {"management_asof": "2026-13-01"},
    {"last_price_asof": "2026-10-15"},
    {"management_status": "unavailable"}, {"management_error": "failed"},
    {"last_price": float("nan")}, {"last_price": True}, {"last_price": 0},
    {"price_frame": "stale"},
    {"price_frame": {"state": "stale", "last_close_date": "2026-09-01"}},
])
def test_unqualified_close_stays_missing_instead_of_borrowing_another_clock(changes):
    out = present_plan_record(_observed_plan(**changes))["observation"]
    assert out["close"] is None and out["close_date"] is None


def test_stale_close_keeps_its_own_date_and_native_freshness_disclosure():
    observation = present_plan_record(_observed_plan(last_price_asof="2026-09-01",
        price_frame={"state": "stale", "last_close_date": "2026-09-01"}))["observation"]
    assert observation == {"close": 123.45, "close_date": "2026-09-01",
                           "management_date": "2026-10-14", "price_frame_state": "stale"}
    # Removing an optional freshness stamp never mints a current/live assertion.
    assert present_plan_record(_observed_plan())["observation"]["price_frame_state"] == "unknown"


def test_each_original_plan_keeps_its_own_observation_even_for_the_same_security():
    first = _observed_plan()
    second = _observed_plan(id="ABC-BULL-20260901", last_price=110,
                            management_asof="2026-10-10", last_price_asof="2026-10-09")
    assert [present_plan_record(p)["observation"]["close"] for p in (first, second)] == [123.45, 110]
    assert [present_plan_record(p)["observation"]["close_date"] for p in (first, second)] == [
        "2026-10-13", "2026-10-09"]
