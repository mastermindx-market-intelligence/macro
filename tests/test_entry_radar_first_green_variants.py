"""Additive native conformance; no market data, new source or efficacy claim."""
from __future__ import annotations

import copy
from datetime import timedelta

import pytest

from engine.entry_radar.replay import first_green_reversal_descriptor as green
from engine.entry_radar.replay.leader_pivot_descriptor import describe_candidate
from engine.entry_radar.replay.rs_pullback_launch_data import INPUT_V2_SCHEMA, InputContractError, digest
from tests.test_entry_radar_rs_pullback_phase1 import candidate, clock, fixture, iso


def set_bar(b, index, open_=103.0, close=102.0, low=None, high=None):
    session = b["candidates"][0]["session"]
    opening = clock(b["calendar"]["sessions"][session]["open"])
    left = opening + timedelta(minutes=index * 30)
    for row in b["minutes"]:
        if row["stream"] == "stock" and left <= clock(row["start"]) < left + timedelta(minutes=30):
            row.update(open=open_, close=close,
                       low=min(open_, close) - .2 if low is None else low,
                       high=max(open_, close) + .2 if high is None else high)


def witness(target=4):
    end = clock("2026-10-06T13:30:00Z") + timedelta(minutes=30 * (target + 1))
    b = fixture([candidate("pivot", iso(end))])
    for index in range(max(0, target - 2), target):
        set_bar(b, index)
    set_bar(b, target, 102.0, 103.0)
    return b


def minute(b, index):
    return next(r for r in b["minutes"] if r["stream"] == "stock"
                and r["revision_id"] == f"synthetic-stock-{index}-v1")


def two(b=None, state="FIRST_GREEN_FORMED"):
    b = witness() if b is None else b
    r = green.describe_first_green_variant(b, "pivot", variant="two_red")
    assert r["schema"] == green.TWO_RED_SCHEMA
    assert r["definition_id"] == green.TWO_RED_DEFINITION_ID
    assert r["variant"] == "two_red" and r["required_red_bars"] == 2
    assert r["state"] == state
    assert r["descriptor_sha256"] == digest({k: v for k, v in r.items() if k != "descriptor_sha256"})
    for key in ("source_admitted", "detector_registered", "outcomes_computed", "actual_issuance_proven"):
        assert r[key] is False
    assert r["issued_at"] is None
    assert r["authority"] and all(v is False for v in r["authority"].values())
    if state != "FIRST_GREEN_FORMED": assert r["pivot"] is None
    return r


@pytest.mark.parametrize("case", ["formed", "red", "doji", "missing", "ineligible", "early", "late"])
def test_one_red_wrapper_is_exact_incumbent_output(case):
    b = witness()
    if case == "red": set_bar(b, 4)
    if case == "doji": set_bar(b, 4, 103.0, 103.0)
    if case == "missing": b["minutes"].remove(minute(b, 90))
    if case == "ineligible": b["contexts"][0]["payload"]["is_leader"] = False
    if case == "early": b = witness(0)
    if case == "late": b["candidates"][0]["decision_at"] = "2026-10-06T16:01:00Z"
    original = green.describe_first_green_candidate(b, "pivot")
    assert green.describe_first_green_variant(b, "pivot") == original
    assert green.describe_first_green_variant(b, "pivot", variant="one_red") == original


def test_two_red_has_distinct_identity_but_same_geometry_when_both_qualify():
    b = witness(); r = two(b)
    one = green.describe_first_green_candidate(b, "pivot")
    assert r["pivot"] == one["pivot"]
    assert r["definition_id"] != one["definition_id"]
    assert r["descriptor_sha256"] != one["descriptor_sha256"]
    assert r["prior_red_sequence"] is True
    assert len(r["reference_bars"]) == 2
    assert r["reference_bars"][0]["end"] == r["reference_bars"][1]["start"]
    assert r["reference_bars"][1] == r["previous_bar"]
    assert r["price_structure_known_at"] == "2026-10-06T16:00:00Z"


@pytest.mark.parametrize("index", [2, 3])
@pytest.mark.parametrize("open_,close", [(102., 103.), (103., 103.)])
def test_green_or_doji_in_required_suffix_prevents_two_red(index, open_, close):
    b = witness(); set_bar(b, index, open_, close)
    assert two(b, "NO_FIRST_GREEN")["condition_met"] is False
    if index == 2:
        assert green.describe_first_green_candidate(b, "pivot")["state"] == "FIRST_GREEN_FORMED"


@pytest.mark.parametrize("open_,close", [(103., 102.), (103., 103.)])
def test_red_or_doji_current_is_not_first_green(open_, close):
    b = witness(); set_bar(b, 4, open_, close)
    two(b, "NO_FIRST_GREEN")


def test_green_higher_low_need_not_be_undercut_rejection():
    b = witness(); set_bar(b, 3, 101., 100., low=99.)
    assert two(b)["pivot"]["low"] > 99.
    assert describe_candidate(b, "pivot")["state"] == "NO_PIVOT"


def test_red_undercut_rejection_is_not_green():
    b = witness()
    for i in range(4): set_bar(b, i, 101.5, 101., low=100., high=102.)
    set_bar(b, 4, 102., 101.5, low=99., high=102.5)
    assert describe_candidate(b, "pivot")["state"] == "PIVOT_FORMED"
    two(b, "NO_FIRST_GREEN")


def test_earlier_green_does_not_imply_all_day_decline_filter():
    b = witness(); set_bar(b, 1, 100., 105.)
    two(b)
    set_bar(b, 3, 102., 103.)
    two(b, "NO_FIRST_GREEN")


def test_earliest_one_red_and_two_red_windows():
    b = witness(1)
    assert green.describe_first_green_variant(b, "pivot")["state"] == "FIRST_GREEN_FORMED"
    r = two(b, "UNAVAILABLE")
    assert "NO_TWO_PREVIOUS_COMPLETED_SAME_SESSION_30M" in r["refusals"]
    assert r["condition_met"] is None
    assert r["price_structure_known_at"] is None
    assert two(witness(2))["pivot"]["bar_end"] == "2026-10-06T15:00:00Z"
    two(witness(0), "UNAVAILABLE")


@pytest.mark.parametrize("index", [60, 89, 90, 119, 120, 149])
def test_missing_required_minutes_are_unavailable(index):
    b = witness(); b["minutes"].remove(minute(b, index))
    r = two(b, "UNAVAILABLE")
    assert r["condition_met"] is None
    if index < 90:
        assert green.describe_first_green_candidate(b, "pivot")["state"] == "FIRST_GREEN_FORMED"


def test_missing_earlier_bar_not_hidden_by_false_current_pattern():
    b = witness(); set_bar(b, 4); b["minutes"].remove(minute(b, 60))
    two(b, "UNAVAILABLE")


def test_delayed_earlier_receipt_controls_structure_known_at():
    b = witness(); minute(b, 60)["known_at"] = "2026-10-06T16:00:02Z"
    two(b, "UNAVAILABLE")
    b["candidates"][0]["decision_at"] = "2026-10-06T16:00:02Z"
    assert two(b)["price_structure_known_at"] == "2026-10-06T16:00:02Z"


@pytest.mark.parametrize("key,value", [("security_id", "SYNTHETIC:other"), ("basis_id", "other")])
def test_additional_bar_identity_and_basis_refusals_are_native(key, value):
    b = witness(); minute(b, 60)[key] = value
    assert any(x.startswith("earlier:") for x in two(b, "UNAVAILABLE")["refusals"])


def test_unproven_terminal_basis_is_not_relabelled():
    b = witness(); minute(b, 60)["source_ref"] = "terminal-minute-capture:synthetic"
    assert "earlier:TERMINAL_BASIS_UNPROVEN" in two(b, "UNAVAILABLE")["refusals"]


def test_unfinished_current_bar_is_not_selected():
    b = witness(); b["candidates"][0]["decision_at"] = "2026-10-06T15:59:59Z"
    assert two(b, "NO_FIRST_GREEN")["target_bar"]["end"] == "2026-10-06T15:30:00Z"


def test_future_data_and_future_candidate_leave_earlier_output_exact():
    b = witness(); before = two(b)
    for row in b["minutes"]:
        if row["known_at"] > "2026-10-06T16:00:00Z":
            row.update(open=800., high=900., low=700., close=850.)
    b["candidates"].append(candidate("future", "not-an-instant"))
    assert two(b) == before


def test_late_revision_only_changes_later_decision():
    b = witness(); original = two(b)
    revised = copy.deepcopy(minute(b, 89))
    revised.update(known_at="2026-10-06T16:01:00Z", revision_id="late-correction", close=104., high=104.2)
    b["minutes"].append(revised)
    assert two(b) == original
    b["candidates"][0]["decision_at"] = "2026-10-06T16:02:00Z"
    two(b, "NO_FIRST_GREEN")


def test_input_immutable_and_return_not_shared():
    b = witness(); before = copy.deepcopy(b)
    r = two(b); r["reference_bars"][0]["ohlcv"]["close"] = 0
    assert b == before
    assert two(b)["reference_bars"][0]["ohlcv"]["close"] == 102.


@pytest.mark.parametrize("key", ["is_leader", "controlled_pullback"])
def test_daily_eligibility_not_loosened(key):
    b = witness(); b["contexts"][0]["payload"][key] = False
    two(b, "NOT_ELIGIBLE")


def test_stale_daily_context_remains_unavailable():
    b = witness(); b["contexts"][0]["asof_session"] = "2026-10-02"
    two(b, "UNAVAILABLE")


def test_market_label_does_not_self_admit():
    b = witness(); b.update(input_kind="OBSERVED_MARKET", source_admitted=True)
    assert two(b)["evidence_status"] == "DESCRIPTOR_BUILT_NOT_ADMITTED"


def test_v2_anchor_is_not_shifted_to_late_decision_bar():
    b = witness(); b["schema"] = INPUT_V2_SCHEMA
    b["candidates"][0].update(event_anchor_at="2026-10-06T16:00:00Z",
        decision_at="2026-10-06T16:45:00Z", max_feature_age_seconds=3600)
    minute(b, 60)["known_at"] = "2026-10-06T16:10:00Z"
    r = two(b)
    assert r["pivot"]["bar_end"] == "2026-10-06T16:00:00Z"
    assert r["decision_at"] == "2026-10-06T16:45:00Z"
    assert r["price_structure_known_at"] == "2026-10-06T16:10:00Z"


def test_v2_future_anchor_refuses():
    b = witness(); b["schema"] = INPUT_V2_SCHEMA
    b["candidates"][0].update(event_anchor_at="2026-10-06T16:30:00Z", max_feature_age_seconds=3600)
    assert "EVENT_ANCHOR_AFTER_DECISION" in two(b, "UNAVAILABLE")["refusals"]


def test_two_red_cannot_impersonate_incumbent_frozen_reference():
    with pytest.raises(InputContractError):
        green._reference_value(two(), .01, "2026-10-06T17:00:00Z",
                               "2026-10-06T13:30:00Z", "2026-10-06T20:00:00Z")


@pytest.mark.parametrize("variant", ["", "three_red", None, True, [], {}])
def test_bad_variant_rejects(variant):
    with pytest.raises(InputContractError): green.describe_first_green_variant(witness(), "pivot", variant=variant)


def test_candidate_identity_and_duplicate_refuse():
    b = witness()
    with pytest.raises(InputContractError): green.describe_first_green_variant(b, "missing")
    b["candidates"].append(copy.deepcopy(b["candidates"][0]))
    with pytest.raises(InputContractError): green.describe_first_green_variant(b, "pivot", variant="two_red")


def test_nonfinite_earlier_price_rejects():
    b = witness(); minute(b, 60)["close"] = float("nan")
    with pytest.raises((InputContractError, ValueError)): green.describe_first_green_variant(b, "pivot", variant="two_red")


def test_early_close_and_stub_respect_native_window():
    b = witness(6); b["calendar"]["sessions"]["2026-10-06"]["close"] = "2026-10-06T17:15:00Z"
    b["candidates"][0]["decision_at"] = "2026-10-06T17:15:00Z"
    assert two(b)["target_bar"]["end"] == "2026-10-06T17:00:00Z"
    b["candidates"][0]["decision_at"] = "2026-10-06T17:15:01Z"
    two(b, "UNAVAILABLE")
