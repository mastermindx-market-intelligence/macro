"""Leadership Lab peer context reuses Group Flow's leave-issuer-out observation."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest


def view():
    rows = [
        {
            "ticker": "A", "legacy_alpha": 3.0, "legacy_rs": 99.0,
            "current_context": {
                "episode": {"status": "AVAILABLE", "company_id": "ISS:1"},
                "authority": {"rank": False, "entry": False, "size": False,
                              "execution": False, "trade": False},
            },
        },
        {
            "ticker": "B", "legacy_alpha": 2.0, "legacy_rs": 95.0,
            "current_context": {
                "episode": {"status": "AVAILABLE", "company_id": "ISS:2"},
                "authority": {"rank": False, "entry": False, "size": False,
                              "execution": False, "trade": False},
            },
        },
        {
            "ticker": "C", "legacy_alpha": 1.0, "legacy_rs": 90.0,
            "current_context": {
                "episode": {"status": "AVAILABLE", "company_id": "ISS:1"},
                "authority": {"rank": False, "entry": False, "size": False,
                              "execution": False, "trade": False},
            },
        },
        {
            "ticker": "D", "legacy_alpha": None, "legacy_rs": None,
            "current_context": {
                "episode": {"status": "UNAVAILABLE", "reason": "NO_CURRENT_EPISODE"},
                "authority": {"rank": False, "entry": False, "size": False,
                              "execution": False, "trade": False},
            },
        },
    ]
    return {
        "schema": "mastermind.leadership_lab.recovery.v1",
        "rows": deepcopy(rows),
        "shortlist": deepcopy(rows[:3]),
        "groups": [
            {
                "id": "clean", "name": "Clean peers", "category": "Theme",
                "member_count": 3, "observed_count": 3, "coverage": 1.0,
                "members": ["A", "B", "C"],
                "independence_status": "NOT_QUALIFIED",
                "historical_membership_qualified": False,
            },
            {
                "id": "missing", "name": "Missing identity", "category": "Theme",
                "member_count": 4, "observed_count": 3, "coverage": .75,
                "members": ["A", "B", "C", "D"],
                "independence_status": "NOT_QUALIFIED",
                "historical_membership_qualified": False,
            },
        ],
        "authority": {"prophet_rank": False, "entry": False, "sizing": False,
                      "trade": False, "production_publish": False},
        "current_context": {
            "authority": {"rank": False, "entry": False, "size": False,
                          "execution": False, "trade": False},
            "episode_book": {"status": "AVAILABLE", "generation_id": "peg:" + "a" * 64,
                             "source_validation": {"status": "VALIDATED_CANONICAL_OWNER"}},
        },
    }


def attach(payload=None):
    from engine.leadership_lab.peers import attach_independent_peer_context
    return attach_independent_peer_context(view() if payload is None else payload)


def _group(result, ticker, group_id):
    row = next(row for row in result["rows"] if row["ticker"] == ticker)
    return next(group for group in row["current_context"]["peer_groups"]
                if group["group_id"] == group_id)


def test_same_issuer_security_is_excluded_before_peer_comparison():
    result = attach()
    clean = _group(result, "A", "clean")
    alpha = clean["legacy_alpha"]
    assert alpha["independence_status"] == "AVAILABLE"
    assert alpha["peer_denominator"] == 1
    assert alpha["excluded_same_issuer"] == ["A", "C"]
    assert alpha["observed_independent_peers"] == 1
    assert alpha["peer_median"] == 2.0
    assert alpha["focal_value"] == 3.0
    assert alpha["focal_minus_peer_median"] == 1.0


def test_unknown_identity_stays_in_denominator_and_blocks_independence_claim():
    result = attach()
    missing = _group(result, "A", "missing")
    alpha = missing["legacy_alpha"]
    assert alpha["independence_status"] == "UNAVAILABLE"
    assert alpha["peer_denominator"] == 2
    assert alpha["unknown_peer_identity"] == ["D"]
    assert alpha["observed_independent_peers"] == 1
    assert alpha["positive_breadth_lower"] == pytest.approx(.5)
    assert alpha["positive_breadth_upper"] == pytest.approx(1.0)
    assert alpha["focal_minus_peer_median"] is None


def test_rs_peer_context_is_descriptive_and_has_no_rank_score_or_flow_claim():
    result = attach()
    clean = _group(result, "A", "clean")
    rs = clean["legacy_rs"]
    assert rs["peer_median"] == 95.0
    assert rs["focal_minus_peer_median"] == 4.0
    rendered = json.dumps(clean, sort_keys=True).lower()
    for forbidden in ("institutional", "accumulation", '"score"', "buy", "probability"):
        assert forbidden not in rendered


def test_group_membership_is_explicitly_not_historical_pit_proof():
    group = _group(attach(), "A", "clean")
    assert group["membership_basis"] == "RECOVERED_SOURCE_MEMBERSHIP_NOT_PIT_QUALIFIED"
    assert group["historical_membership_qualified"] is False
    assert group["identity_basis"] == "CURRENT_PROPHET_EPISODE_COMPANY_ID_NOT_HISTORICAL"


def test_peer_context_never_reorders_or_changes_legacy_values_or_authority():
    before = view()
    result = attach(before)
    assert before == view()
    assert [row["ticker"] for row in result["rows"]] == ["A", "B", "C", "D"]
    assert [row["ticker"] for row in result["shortlist"]] == ["A", "B", "C"]
    assert [row["legacy_alpha"] for row in result["rows"]] == [3.0, 2.0, 1.0, None]
    assert result["authority"] == before["authority"]
    assert result["current_context"]["peer_context"]["authority"] == {
        "rank": False, "entry": False, "size": False,
        "execution": False, "trade": False,
    }


def test_nonmember_has_empty_peer_groups_not_negative_evidence():
    payload = view()
    payload["groups"] = [payload["groups"][0]]
    row = next(row for row in attach(payload)["rows"] if row["ticker"] == "D")
    assert row["current_context"]["peer_groups"] == []


def test_malformed_group_is_skipped_and_counted_without_breaking_rows():
    payload = view()
    payload["groups"].append({
        "id": "bad", "name": "Bad", "members": ["A", ""],
        "historical_membership_qualified": False,
    })
    result = attach(payload)
    assert result["rows"][0]["legacy_alpha"] == 3.0
    assert result["current_context"]["peer_context"]["skipped_groups"] == 1


def test_peer_context_output_is_strict_json():
    result = attach()
    json.dumps(result, allow_nan=False)


def test_adapter_calls_existing_group_flow_owner_not_private_reimplementation():
    import ast
    from pathlib import Path
    from engine.leadership_lab import peers as module
    source = Path(module.__file__).read_text()
    tree = ast.parse(source)
    names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "engine.group_flow"
        for alias in node.names
    }
    assert names == {"independent_peer_observation"}
    assert "_independent_peer_roster" not in source


def test_unvalidated_episode_projection_cannot_establish_peer_independence():
    payload = view()
    payload['current_context']['episode_book']['source_validation'] = {'status': 'NOT_VALIDATED'}
    result = attach(payload)
    alpha = _group(result, 'A', 'clean')['legacy_alpha']
    assert alpha['independence_status'] == 'UNAVAILABLE'
    assert alpha['observed_independent_peers'] == 0
    assert alpha['peer_median'] is None


def test_positive_rs_percentiles_are_not_positive_return_breadth():
    result = attach()
    rs = _group(result, 'A', 'clean')['legacy_rs']
    assert rs['positive_breadth_lower'] is None
    assert rs['positive_breadth_upper'] is None
    assert rs['breadth_interpretation'] == 'NOT_APPLICABLE_TO_PERCENTILE_LEVELS'


def test_missing_rs_peer_measurement_keeps_alpha_available_and_rs_delta_null():
    payload = view()
    payload["rows"][1]["legacy_rs"] = None
    payload["shortlist"][1]["legacy_rs"] = None
    result = attach(payload)
    group = _group(result, "A", "clean")
    assert group["legacy_alpha"]["independence_status"] == "AVAILABLE"
    assert group["legacy_alpha"]["focal_minus_peer_median"] == pytest.approx(1.0)
    assert group["legacy_rs"]["focal_minus_peer_median"] is None
    assert "B" in group["legacy_rs"]["missing_market_observation"]


def test_committed_peer_evidence_is_explicitly_superseded():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "research/leadership_alpha_rs/evidence/l2_peer_current_read.json"
    payload = json.loads(path.read_text())
    assert isinstance(payload, dict)
    assert payload["status"] == "SUPERSEDED"
    assert payload["do_not_use_for_current_semantics"] is True
    assert "RS_PERCENTILE_SIGN_WAS_NOT_RETURN_BREADTH" in payload["reasons"]
