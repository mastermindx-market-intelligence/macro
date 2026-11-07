"""Group-level descriptive Leadership Lab projection; no new score or forecast."""
from __future__ import annotations

from copy import deepcopy
import json


def view():
    rows = [
        {"ticker": "A", "legacy_alpha": 3.0, "legacy_rs": 99.0,
         "current_context": {"peer_groups": [{"group_id": "g1", "legacy_alpha": {
             "independence_status": "AVAILABLE"}}]}},
        {"ticker": "B", "legacy_alpha": 2.0, "legacy_rs": 95.0,
         "current_context": {"peer_groups": [{"group_id": "g1", "legacy_alpha": {
             "independence_status": "AVAILABLE"}}]}},
        {"ticker": "C", "legacy_alpha": 2.0, "legacy_rs": 90.0,
         "current_context": {"peer_groups": [{"group_id": "g1", "legacy_alpha": {
             "independence_status": "UNAVAILABLE"}}]}},
        {"ticker": "D", "legacy_alpha": None, "legacy_rs": None,
         "current_context": {"peer_groups": []}},
    ]
    return {
        "schema": "mastermind.leadership_lab.recovery.v1",
        "rows": deepcopy(rows),
        "shortlist": deepcopy(rows[:3]),
        "groups": [{
            "id": "g1", "name": "Memory, HBM & Storage", "category": "AI",
            "member_count": 4, "observed_count": 3, "coverage": .75,
            "members": ["A", "B", "C", "D"],
            "historical_membership_qualified": False,
        }],
        "authority": {"prophet_rank": False, "entry": False, "sizing": False,
                      "trade": False, "production_publish": False},
        "current_context": {
            "peer_context": {
                "mode": "EXISTING_GROUP_FLOW_OBSERVATION_ONLY",
                "authority": {"rank": False, "entry": False, "size": False,
                              "execution": False, "trade": False},
            },
            "authority": {"rank": False, "entry": False, "size": False,
                          "execution": False, "trade": False},
        },
    }


def attach(payload=None):
    from engine.leadership_lab.groups import attach_group_leadership
    return attach_group_leadership(view() if payload is None else payload)


def test_group_projection_orders_existing_alpha_and_rs_without_new_score():
    result = attach()
    group = result["current_context"]["group_leadership"][0]
    assert group["group_id"] == "g1"
    assert group["top_legacy_alpha"] == [
        {"ticker": "A", "value": 3.0},
        {"ticker": "B", "value": 2.0},
        {"ticker": "C", "value": 2.0},
    ]
    assert group["top_legacy_rs"] == [
        {"ticker": "A", "value": 99.0},
        {"ticker": "B", "value": 95.0},
        {"ticker": "C", "value": 90.0},
    ]
    assert "score" not in json.dumps(group).lower()
    assert "probability" not in json.dumps(group).lower()


def test_ties_are_deterministic_and_missing_values_never_become_zero():
    payload = view()
    payload["rows"][1]["legacy_alpha"] = 2.0
    payload["rows"][2]["legacy_alpha"] = 2.0
    group = attach(payload)["current_context"]["group_leadership"][0]
    assert [x["ticker"] for x in group["top_legacy_alpha"]] == ["A", "B", "C"]
    assert all(x["ticker"] != "D" for x in group["top_legacy_alpha"])


def test_group_coverage_and_membership_caveat_are_preserved():
    group = attach()["current_context"]["group_leadership"][0]
    assert group["member_count"] == 4
    assert group["observed_alpha_count"] == 3
    assert group["observed_rs_count"] == 3
    assert group["coverage"] == .75
    assert group["membership_basis"] == "RECOVERED_SOURCE_MEMBERSHIP_NOT_PIT_QUALIFIED"
    assert group["historical_membership_qualified"] is False


def test_independent_peer_ready_count_is_a_coverage_count_not_a_vote():
    group = attach()["current_context"]["group_leadership"][0]
    assert group["independent_peer_ready_count"] == 2
    assert group["independent_peer_total_recovered_members"] == 4
    assert group["independent_confirmation_count"] is None


def test_projection_preserves_rows_shortlist_and_authority():
    before = view()
    result = attach(before)
    assert before == view()
    assert result["rows"] == before["rows"]
    assert result["shortlist"] == before["shortlist"]
    assert result["authority"] == before["authority"]
    assert all(v is False for v in result["current_context"]["group_leadership_authority"].values())


def test_invalid_group_is_omitted_not_normalized_into_a_fake_group():
    payload = view()
    payload["groups"].append({"id": "", "name": "Broken", "members": []})
    result = attach(payload)
    assert len(result["current_context"]["group_leadership"]) == 1
    assert result["current_context"]["group_leadership_skipped"] == 1


def test_output_is_strict_json():
    json.dumps(attach(), allow_nan=False)
