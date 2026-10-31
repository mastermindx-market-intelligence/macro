"""Native next30m-close policy conformance, without market-data or edge claims."""
from __future__ import annotations

import copy

import pytest

from engine.entry_radar.replay import first_green_reversal_descriptor as green
from engine.entry_radar.replay.rs_pullback_launch_data import INPUT_V2_SCHEMA, InputContractError, digest
from tests.test_entry_radar_first_green_variants import minute, set_bar, witness


def market():
    b = witness()
    set_bar(b, 5, open_=103.4, close=104.0, low=103.2, high=104.2)
    return b


def freeze(b=None):
    return green.freeze_first_green_next_close_reference(market() if b is None else b,
                                                         "pivot", buffer_size=.01)


def observe(b, ref, at="2026-10-06T16:30:00Z", state="GREEN30M_CLOSE_CONFIRMED"):
    follow = copy.deepcopy(b)
    follow["candidates"][0]["decision_at"] = at
    r = green.describe_first_green_next_close(follow, "pivot", reference=ref)
    assert r["schema"] == green.NEXT_CLOSE_PROGRESS_SCHEMA
    assert r["definition_id"] == green.NEXT_CLOSE_DEFINITION_ID
    assert r["origin_definition_id"] == green.DEFINITION_ID
    assert r["state"] == state
    assert r["reference_sha256"] == ref["reference_sha256"]
    assert r["native_reference_sha256"] == ref["native_reference"]["reference_sha256"]
    assert r["progress_sha256"] == digest({k: v for k, v in r.items() if k != "progress_sha256"})
    for key in ("source_admitted", "actual_issuance_proven", "detector_registered", "outcomes_computed"):
        assert r[key] is False
    assert r["issued_at"] is None
    assert r["authority"] and all(v is False for v in r["authority"].values())
    return r


def test_wrapper_binds_real_native_reference_and_exact_next_window():
    b = market(); ref = freeze(b)
    native = green.freeze_first_green_reference(b, "pivot", buffer_size=.01,
                                                episode_expires_at="2026-10-06T16:30:00Z")
    assert ref["native_reference"] == native
    assert ref["window_start"] == "2026-10-06T16:00:00Z"
    assert ref["window_end"] == native["expires_at"] == "2026-10-06T16:30:00Z"
    assert ref["reference_sha256"] == digest({k: v for k, v in ref.items() if k != "reference_sha256"})


def test_confirmed_close_is_historical_observation_not_issuance():
    b = market(); r = observe(b, freeze(b))
    assert r["condition_met"] is True and r["window_closed"] is True
    assert r["confirmation"]["bar_end"] == "2026-10-06T16:30:00Z"
    assert r["confirmation"]["known_at"] == "2026-10-06T16:30:00Z"
    assert r["confirmation"]["observed_close"] == 104.0
    assert r["invalidation"] is None


@pytest.mark.parametrize("at", ["2026-10-06T16:00:00Z", "2026-10-06T16:10:00Z", "2026-10-06T16:29:59Z"])
def test_incomplete_window_waits_even_after_native_1m_confirmation(at):
    b = market(); ref = freeze(b)
    r = observe(b, ref, at, "WAITING_CONFIRMATION")
    assert r["confirmation"] is None and r["condition_met"] is None
    assert r["target_bar"] is None and r["window_closed"] is False
    if at == "2026-10-06T16:10:00Z":
        follow = copy.deepcopy(b); follow["candidates"][0]["decision_at"] = at
        native = green.describe_first_green_progress(follow, "pivot", reference=ref["native_reference"])
        assert native["state"] == "GREEN_BREAK_CONFIRMED"


@pytest.mark.parametrize("open_,close,high", [
    (102.9, 103.1, 104.2),  # High touch, not closing above.
    (105., 104., 105.2),   # Above pivot but red.
    (104., 104., 104.2),   # Doji above pivot.
    (102.9, 103.21, 104.2),  # Equality at high+buffer, not strict break.
])
def test_nonqualifying_second_bar_cannot_confirm(open_, close, high):
    b = market(); set_bar(b, 5, open_=open_, close=close, low=min(open_, close)-.1, high=high)
    r = observe(b, freeze(b), state="EXPIRED_NOT_CONFIRMED")
    assert r["condition_met"] is False and r["confirmation"] is None


def test_earlier_1m_break_does_not_replace_failed_30m_close():
    b = market(); minute(b, 179).update(close=103.0, low=102.9)
    r = observe(b, freeze(b), state="EXPIRED_NOT_CONFIRMED")
    assert r["target_bar"]["ohlcv"]["high"] > 103.21


def test_failed_second_bar_cannot_be_rescued_by_third_bar():
    b = market(); set_bar(b, 5, open_=103.0, close=103.1, low=102.9, high=103.2)
    set_bar(b, 6, open_=104., close=110., low=103.5, high=111.)
    r = observe(b, freeze(b), at="2026-10-06T17:00:00Z", state="EXPIRED_NOT_CONFIRMED")
    assert r["target_bar"]["end"] == "2026-10-06T16:30:00Z"


def test_strict_low_breach_precedes_any_confirmation():
    b = market(); minute(b, 150)["low"] = 101.78
    r = observe(b, freeze(b), at="2026-10-06T16:01:00Z", state="INVALIDATED")
    assert r["invalidation"]["bar_end"] == "2026-10-06T16:01:00Z"
    assert r["confirmation"] is None


def test_low_equal_to_invalidation_level_is_not_a_breach():
    b = market(); minute(b, 150)["low"] = 101.79
    observe(b, freeze(b))


def test_later_gap_does_not_erase_witnessed_terminal_invalidation():
    b = market(); minute(b, 150)["low"] = 101.0
    b["minutes"].remove(minute(b, 160))
    r = observe(b, freeze(b), state="INVALIDATED")
    assert r["invalidation"] is not None


def test_whole_window_low_protects_delayed_formation():
    b = market(); b["candidates"][0]["decision_at"] = "2026-10-06T16:10:00Z"
    minute(b, 150)["low"] = 101.0
    ref = freeze(b)
    assert ref["native_reference"]["first_minute_start"] == "2026-10-06T16:10:00Z"
    r = observe(b, ref, state="INVALIDATED")
    assert r["invalidation"]["kind"] == "CONFIRMATION_WINDOW_LOW_BREACH"
    assert "bar_end" not in r["invalidation"]  # No invented first-breach minute.
    assert r["invalidation"]["window_end"] == "2026-10-06T16:30:00Z"


def test_window_gap_before_delayed_formation_is_not_ignored():
    b = market(); b["candidates"][0]["decision_at"] = "2026-10-06T16:10:00Z"
    b["minutes"].remove(minute(b, 150))
    r = observe(b, freeze(b), state="UNAVAILABLE")
    assert any(x.startswith("next30m:") for x in r["refusals"])
    assert r["condition_met"] is None


@pytest.mark.parametrize("index", [150, 165, 179])
def test_missing_confirmation_window_minute_is_unavailable(index):
    b = market(); b["minutes"].remove(minute(b, index))
    r = observe(b, freeze(b), state="UNAVAILABLE")
    assert r["condition_met"] is None


def test_delayed_source_knows_close_later_without_backdating():
    b = market(); minute(b, 150)["known_at"] = "2026-10-06T16:31:00Z"
    ref = freeze(b)
    observe(b, ref, state="UNAVAILABLE")
    r = observe(b, ref, at="2026-10-06T16:31:00Z")
    assert r["confirmation"]["bar_end"] == "2026-10-06T16:30:00Z"
    assert r["confirmation"]["known_at"] == r["decision_at"] == "2026-10-06T16:31:00Z"


def test_later_revision_cannot_change_original_query():
    b = market(); ref = freeze(b); original = observe(b, ref)
    revision = copy.deepcopy(minute(b, 179))
    revision.update(known_at="2026-10-06T16:40:00Z", revision_id="later-correction", close=103.0, low=102.9)
    b["minutes"].append(revision)
    assert observe(b, ref) == original
    observe(b, ref, at="2026-10-06T16:45:00Z", state="EXPIRED_NOT_CONFIRMED")
    assert original["condition_met"] is True


def test_post_window_price_is_not_used_to_invent_an_exit():
    b = market(); ref = freeze(b); original = observe(b, ref)
    set_bar(b, 6, 90., 80., low=79., high=91.)
    assert observe(b, ref) == original
    later = observe(b, ref, at="2026-10-06T17:00:00Z")
    assert later["confirmation"] == original["confirmation"]
    assert later["invalidation"] is None


@pytest.mark.parametrize("field,value", [("window_end", "2026-10-06T17:00:00Z"), ("definition_id", "invented"), ("source_admitted", True)])
def test_tampered_outer_reference_rejects_even_with_new_digest(field, value):
    b = market(); ref = freeze(b); ref[field] = value
    ref["reference_sha256"] = digest({k: v for k, v in ref.items() if k != "reference_sha256"})
    with pytest.raises(InputContractError): green.describe_first_green_next_close(b, "pivot", reference=ref)


def test_tampered_native_level_rejects():
    b = market(); ref = freeze(b)
    ref["native_reference"]["confirmation_level"] = "1"
    with pytest.raises(InputContractError): green.describe_first_green_next_close(b, "pivot", reference=ref)


def test_native_v0_reference_is_not_a_policy_wrapper():
    b = market(); ref = freeze(b)
    with pytest.raises(InputContractError): green.describe_first_green_next_close(b, "pivot", reference=ref["native_reference"])


def test_missing_or_non_mapping_reference_rejects():
    for ref in (None, {}, [], {"native_reference": None}):
        with pytest.raises(InputContractError): green.describe_first_green_next_close(market(), "pivot", reference=ref)


def test_nonformed_origin_rejects():
    b = market(); set_bar(b, 4, 103., 102.)
    with pytest.raises(InputContractError): freeze(b)


def test_next_window_must_fit_same_session_and_not_use_stub():
    b = market(); b["calendar"]["sessions"]["2026-10-06"]["close"] = "2026-10-06T16:15:00Z"
    with pytest.raises(InputContractError): freeze(b)


def test_cannot_freeze_origin_after_confirmation_window_ended():
    b = market(); b["schema"] = INPUT_V2_SCHEMA
    b["candidates"][0].update(event_anchor_at="2026-10-06T16:00:00Z", decision_at="2026-10-06T16:30:00Z", max_feature_age_seconds=3600)
    with pytest.raises(InputContractError): freeze(b)


def test_reference_and_input_are_not_mutated():
    b = market(); original = copy.deepcopy(b); ref = freeze(b); original_ref = copy.deepcopy(ref)
    observe(b, ref)
    assert b == original and ref == original_ref


@pytest.mark.parametrize("change", ["basis", "identity", "calendar", "input_kind"])
def test_native_frozen_source_constraints_are_preserved(change):
    b = market(); ref = freeze(b)
    if change == "basis": b["streams"]["stock"]["basis"]["receipt_sha256"] = "c" * 64
    if change == "identity": b["streams"]["stock"]["identity"]["receipt_sha256"] = "c" * 64
    if change == "calendar": b["calendar"]["sessions"]["2026-10-06"]["close"] = "2026-10-06T19:00:00Z"
    if change == "input_kind": b["input_kind"] = "OBSERVED_MARKET"
    r = observe(b, ref, state="UNAVAILABLE")
    assert r["refusals"] and r["confirmation"] is None
