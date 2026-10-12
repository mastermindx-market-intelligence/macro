"""Owner-to-graph lifecycle regressions. Controlled source fixtures only."""
from __future__ import annotations

import pandas as pd

from engine import basket_membership_pit as pit
from engine.theme_graph import local_sources


def member(day, ticker="300474.SZ", *, removed=None, basket="ths_ai"):
    return dict(snapshot_date=day, suite=pit.SUITE_THS, basket_id=basket,
                ticker=ticker, added=None, removed=removed, name_zh=None,
                members_sha="controlled", source_shape="membership")


def test_explicit_removed_member_agrees_with_owner_without_backdating_open():
    history = pd.DataFrame([
        member("2026-10-01"),
        member("2026-10-03", removed="2026-10-02"),
    ])
    assert not pit._active_at(history.iloc[1], "2026-10-03")
    intervals = local_sources.ths_membership_intervals(history)
    assert len(intervals) == 1
    assert intervals[0].valid_from == "2026-10-01"
    assert intervals[0].valid_to == "2026-10-02"
    assert intervals[0].closed_by == "2026-10-03"


def test_already_removed_at_first_observation_never_mints_live_membership():
    history = pd.DataFrame([member("2026-10-03", removed="2026-10-02")])
    assert not pit._active_at(history.iloc[0], "2026-10-03")
    assert local_sources.ths_membership_intervals(history) == []

import copy
import datetime as dt
import json

import pytest
from lib import config


@pytest.fixture
def owner_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return tmp_path


def document(day, symbols, basket="ths_ai"):
    return {"version": day, "baskets": {basket: {"members": [
        {"ticker": symbol, "added": None, "removed": None} for symbol in symbols]}}}


def receipt(doc, day, basket="ths_ai", state="COMPLETE"):
    generation = pit.collection_generation_sha(doc)
    slots = [m for m in pit._members_from_membership(doc) if m[0] == basket]
    value = dict(schema="basket_membership_collection/v2", suite=pit.SUITE_THS,
                 basket_id=basket, source_ref=f"data/{pit.SUITE_THS}/membership.json",
                 generation_id=generation[:16], generation_sha256=generation,
                 collection_state=state, source_clock_grain="instant",
                 observed_at=day + "T08:00:00Z", known_at=day + "T09:00:00Z",
                 members_sha=pit._sha_of(slots), member_count=len(slots),
                 authority_caps=dict(may_rank=False, may_size=False,
                                     may_gate=False, may_escalate=False))
    value["collection_id"] = pit.collection_id(value)
    return value


def append(owner_root, doc, day, receipts):
    path = owner_root / pit.SUITE_THS / "membership.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return pit.append_snapshot(pit.SUITE_THS, asof=day, lane="asia",
                               collection_receipts=receipts)


def test_complete_empty_is_stored_without_fake_security_and_closes_only_its_basket(owner_root):
    first = document("2026-10-01", ["300474.SZ"])
    assert append(owner_root, first, "2026-10-01", [receipt(first, "2026-10-01")])["written"]
    empty = document("2026-10-03", [])
    assert append(owner_root, empty, "2026-10-03", [receipt(empty, "2026-10-03")])["written"]
    public = pit.read_history(pit.SUITE_THS, strict=True)
    assert len(public) == 1 and set(public["ticker"]) == {"300474.SZ"}
    raw = pit.read_history(pit.SUITE_THS, strict=True, include_collection_records=True)
    assert len(raw) == 3 and len(raw[raw["record_kind"] == "collection.v2"]) == 2
    current = pit.members_asof("ths_ai", "2026-10-03", suite=pit.SUITE_THS)
    assert current["members"] == [] and current["pit"]
    assert pit.members_asof("ths_ai", "2026-10-01", suite=pit.SUITE_THS)["members"] == ["300474.SZ"]
    intervals = local_sources.ths_membership_intervals(raw)
    assert len(intervals) == 1 and intervals[0].valid_to == "2026-10-03"


@pytest.mark.parametrize("state", ["PARTIAL", "FAILED", "MISSING", True, None])
def test_unqualified_empty_collection_preserves_owner_bytes(owner_root, state):
    first = document("2026-10-01", ["300474.SZ"])
    append(owner_root, first, "2026-10-01", [receipt(first, "2026-10-01")])
    path = pit.history_path(pit.SUITE_THS)
    before = path.read_bytes()
    empty = document("2026-10-03", [])
    broken = receipt(empty, "2026-10-03")
    broken["collection_state"] = state
    broken["collection_id"] = pit.collection_id(broken)
    result = append(owner_root, empty, "2026-10-03", [broken])
    assert not result["written"] and result["status"] == "failed"
    assert path.read_bytes() == before


def test_empty_without_receipt_is_not_absence(owner_root):
    first = document("2026-10-01", ["300474.SZ"])
    append(owner_root, first, "2026-10-01", [receipt(first, "2026-10-01")])
    before = pit.history_path(pit.SUITE_THS).read_bytes()
    empty = document("2026-10-03", [])
    assert not append(owner_root, empty, "2026-10-03", None)["written"]
    assert pit.history_path(pit.SUITE_THS).read_bytes() == before


def test_new_unreceipted_subset_does_not_close_missing_member(owner_root):
    first = document("2026-10-01", ["300474.SZ", "600001.SS"])
    append(owner_root, first, "2026-10-01", [receipt(first, "2026-10-01")])
    partial = document("2026-10-03", ["600001.SS"])
    append(owner_root, partial, "2026-10-03", None)
    intervals = local_sources.ths_membership_intervals(
        pit.read_history(pit.SUITE_THS, strict=True, include_collection_records=True))
    assert all(iv.valid_to is None for iv in intervals)

@pytest.mark.parametrize("field,value", [
    ("member_count", True), ("member_count", 0), ("members_sha", "0" * 64),
    ("generation_id", "0" * 16), ("generation_sha256", "0" * 64),
    ("observed_at", "2026-10-03"), ("known_at", None),
    ("observed_at", "2026-10-03T10:00:00Z"),
    ("known_at", "2026-10-02T09:00:00Z"),
    ("source_ref", "data/foreign/membership.json"), ("basket_id", "other"),
])
def test_malformed_or_misbound_collection_refuses_before_write(owner_root, field, value):
    doc = document("2026-10-03", ["300474.SZ"])
    broken = receipt(doc, "2026-10-03")
    broken[field] = value
    broken["collection_id"] = pit.collection_id(broken)
    result = append(owner_root, doc, "2026-10-03", [broken])
    assert result.get("status") == "failed" and not result["written"]
    assert not pit.history_path(pit.SUITE_THS).exists()


def test_numeric_authority_is_not_a_boolean(owner_root):
    doc = document("2026-10-03", [])
    broken = receipt(doc, "2026-10-03")
    broken["authority_caps"]["may_rank"] = 0
    broken["collection_id"] = pit.collection_id(broken)
    assert append(owner_root, doc, "2026-10-03", [broken])["status"] == "failed"


def test_future_collection_and_backdated_stamp_refuse(owner_root):
    doc = document("2099-10-03", [])
    assert append(owner_root, doc, "2099-10-03", [receipt(doc, "2099-10-03")])["status"] == "failed"
    doc = document("2026-10-03", [])
    assert append(owner_root, doc, "2026-10-01", [receipt(doc, "2026-10-03")])["status"] == "failed"


def test_receipted_retirement_and_reappearance_are_two_intervals(owner_root):
    for day, symbols, state in [
            ("2026-10-01", ["300474.SZ"], "COMPLETE"),
            ("2026-10-02", [], "RETIRED"),
            ("2026-10-03", ["300474.SZ"], "COMPLETE")]:
        doc = document(day, symbols)
        assert append(owner_root, doc, day, [receipt(doc, day, state=state)])["written"]
    rows = pit.read_history(pit.SUITE_THS, strict=True, include_collection_records=True)
    intervals = local_sources.ths_membership_intervals(rows)
    assert [(iv.valid_from, iv.valid_to) for iv in intervals] == [
        ("2026-10-01", "2026-10-02"), ("2026-10-03", None)]
    assert pit.members_asof("ths_ai", "2026-10-02", suite=pit.SUITE_THS)["members"] == []
    assert pit.members_asof("ths_ai", "2026-10-03", suite=pit.SUITE_THS)["members"] == ["300474.SZ"]


def test_complete_empty_initialization_and_repeat_keep_raw_records(owner_root):
    doc = document("2026-10-03", [])
    value = receipt(doc, "2026-10-03")
    assert append(owner_root, doc, "2026-10-03", [value])["written"]
    before = pit.history_path(pit.SUITE_THS).read_bytes()
    assert not append(owner_root, doc, "2026-10-03", [value])["written"]
    assert pit.history_path(pit.SUITE_THS).read_bytes() == before
    assert pit.read_history(pit.SUITE_THS).empty
    raw = pit.read_history(pit.SUITE_THS, include_collection_records=True, strict=True)
    assert len(raw) == 1 and raw.iloc[0]["ticker"] is None


def test_unreadable_prior_still_refuses_collection_append(owner_root):
    path = pit.history_path(pit.SUITE_THS)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"broken prior immutable bytes")
    doc = document("2026-10-03", [])
    assert append(owner_root, doc, "2026-10-03", [receipt(doc, "2026-10-03")])["status"] == "failed"
    assert path.read_bytes() == b"broken prior immutable bytes"


def test_marker_member_digest_corruption_is_not_empty_initialization(owner_root):
    doc = document("2026-10-03", ["300474.SZ"])
    append(owner_root, doc, "2026-10-03", [receipt(doc, "2026-10-03")])
    raw = pit.read_history(pit.SUITE_THS, include_collection_records=True, strict=True)
    raw.loc[raw["record_kind"] == "member.v2", "ticker"] = "600001.SS"
    raw.to_parquet(pit.history_path(pit.SUITE_THS), index=False)
    before = pit.history_path(pit.SUITE_THS).read_bytes()
    with pytest.raises(pit.HistoryIntegrityError):
        pit.read_history(pit.SUITE_THS, include_collection_records=True, strict=True)
    assert pit.read_history(pit.SUITE_THS).empty
    later = document("2026-10-04", [])
    assert append(owner_root, later, "2026-10-04", [receipt(later, "2026-10-04")])["status"] == "failed"
    assert pit.history_path(pit.SUITE_THS).read_bytes() == before


@pytest.mark.parametrize("member", [
    {"ticker": True}, {"ticker": 123}, {"ticker": "A", "removed": False},
    {"ticker": "A", "added": "2026-99-03"}, {"ticker": "A", "removed": []},
])
def test_new_source_strict_member_types_never_stringify_into_security(owner_root, member):
    doc = {"baskets": {"ths_ai": {"members": [member]}}}
    result = append(owner_root, doc, "2026-10-03", None)
    assert result.get("status") == "failed"
    assert not pit.history_path(pit.SUITE_THS).exists()


def test_staggered_complete_empty_cannot_delete_other_basket(owner_root):
    first = document("2026-10-01", ["300474.SZ"])
    first["baskets"]["other"] = {"members": [{"ticker": "600001.SS"}]}
    append(owner_root, first, "2026-10-01",
           [receipt(first, "2026-10-01"), receipt(first, "2026-10-01", basket="other")])
    empty = document("2026-10-03", [])
    append(owner_root, empty, "2026-10-03", [receipt(empty, "2026-10-03")])
    assert pit.members_asof("other", "2026-10-03", suite=pit.SUITE_THS)["members"] == ["600001.SS"]
    intervals = local_sources.ths_membership_intervals(
        pit.read_history(pit.SUITE_THS, include_collection_records=True, strict=True))
    other = next(iv for iv in intervals if iv.basket_id == "other")
    assert other.valid_to is None


def test_duplicate_marker_json_key_refuses_strict_reader(owner_root):
    doc = document("2026-10-03", [])
    append(owner_root, doc, "2026-10-03", [receipt(doc, "2026-10-03")])
    raw = pit.read_history(pit.SUITE_THS, include_collection_records=True, strict=True)
    raw.loc[0, "collection_receipt"] = raw.loc[0, "collection_receipt"].replace(
        '"member_count": 0', '"member_count": 7, "member_count": 0')
    raw.to_parquet(pit.history_path(pit.SUITE_THS), index=False)
    with pytest.raises(pit.HistoryIntegrityError):
        pit.read_history(pit.SUITE_THS, include_collection_records=True, strict=True)


def _midnight_receipt(doc, day, basket="ths_ai", state="COMPLETE"):
    value = receipt(doc, day, basket=basket, state=state)
    value["observed_at"] = value["known_at"] = day + "T00:00:00Z"
    value["collection_id"] = pit.collection_id(value)
    return value


def test_qualified_positive_after_known_future_removal_reappears_without_gap_cancellation(owner_root):
    first = document("2026-10-01", ["300474.SZ"])
    first["baskets"]["ths_ai"]["members"][0]["removed"] = "2026-10-03"
    assert append(owner_root, first, "2026-10-01", [_midnight_receipt(first, "2026-10-01")])["written"]
    second = document("2026-10-02", ["300474.SZ"])
    assert append(owner_root, second, "2026-10-02", [_midnight_receipt(second, "2026-10-02")])["written"]
    assert pit.members_asof("ths_ai", "2026-10-03")["members"] == []
    prior = pit.read_history(pit.SUITE_THS, strict=True, include_collection_records=True)
    fourth = document("2026-10-04", ["300474.SZ"])
    assert append(owner_root, fourth, "2026-10-04", [_midnight_receipt(fourth, "2026-10-04")])["written"]
    assert pit.members_asof("ths_ai", "2026-10-04")["members"] == ["300474.SZ"]
    assert pit.members_asof("ths_ai", "2026-10-03")["members"] == []
    actual = pit.read_history(pit.SUITE_THS, strict=True, include_collection_records=True)
    intervals = local_sources.ths_membership_intervals(actual)
    assert [(v.valid_from, v.valid_to, v.closed_by) for v in intervals] == [
        ("2026-10-01", "2026-10-03", "2026-10-01"), ("2026-10-04", None, None)]
    retained = actual[actual["snapshot_date"].lt("2026-10-04")]
    assert retained.to_json(orient="records") == prior.to_json(orient="records")


def test_latest_unreceipted_generation_never_inherits_old_completeness(owner_root):
    first = document("2026-10-01", ["300474.SZ", "300475.SZ"])
    original_receipt = _midnight_receipt(first, "2026-10-01")
    assert append(owner_root, first, "2026-10-01", [original_receipt])["written"]
    partial = document("2026-10-02", ["300474.SZ"])
    assert append(owner_root, partial, "2026-10-02", [])["written"]
    actual = pit.members_asof("ths_ai", "2026-10-02")
    assert actual["members"] == ["300474.SZ", "300475.SZ"]
    assert actual["snapshot_date"] == "2026-10-02"
    assert actual["collection_state"] == "UNAVAILABLE"
    assert actual["collection_receipt"] is None
    assert actual["last_qualified_collection"] == original_receipt


@pytest.mark.parametrize("state", ["COMPLETE", "RETIRED"])
def test_latest_empty_collection_retains_exact_state_receipt_and_scope(owner_root, state):
    first = document("2026-10-01", ["300474.SZ"])
    assert append(owner_root, first, "2026-10-01", [_midnight_receipt(first, "2026-10-01")])["written"]
    empty = document("2026-10-02", [])
    qualified = _midnight_receipt(empty, "2026-10-02", state=state)
    assert append(owner_root, empty, "2026-10-02", [qualified])["written"]
    actual = pit.members_asof("ths_ai", "2026-10-02")
    assert actual["members"] == []
    assert actual["collection_state"] == state
    assert actual["collection_receipt"] == qualified
    assert actual["last_qualified_collection"] == qualified


def test_other_basket_collection_does_not_refresh_this_baskets_complete_receipt(owner_root):
    first = document("2026-10-01", ["300474.SZ"], basket="A")
    qualified = _midnight_receipt(first, "2026-10-01", basket="A")
    assert append(owner_root, first, "2026-10-01", [qualified])["written"]
    other = document("2026-10-02", ["300475.SZ"], basket="B")
    assert append(owner_root, other, "2026-10-02",
                  [_midnight_receipt(other, "2026-10-02", basket="B")])["written"]
    actual = pit.members_asof("A", "2026-10-02")
    assert actual["members"] == ["300474.SZ"]
    assert actual["snapshot_date"] == "2026-10-01"
    assert actual["collection_receipt"] == qualified
    assert actual["collection_observation_scope"] == "PRIOR_BASKET_OBSERVATION"
    assert actual["last_qualified_collection"] == qualified
