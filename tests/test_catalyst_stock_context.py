"""Discriminating tests for supplied-cohort arithmetic and owner composition."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.catalyst_intelligence.peer_context import (
    INPUT_SCHEMA, ContextError, build_peer_context, digest,
)
from engine.catalyst_intelligence.assessment import build_stock_assessment

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "research/catalyst_intelligence/stock_context_r1/fixtures"
START = "2026-09-28T13:30:00Z"
END = "2026-09-28T20:00:00Z"
DECISION = "2026-09-28T20:00:08Z"


def peer_inputs():
    members = []
    observations = []
    for sid, cid, ret in (("FOCAL", "ISSUER-F", 12), ("P1", "ISSUER-1", 4),
                          ("P2", "ISSUER-2", 2), ("P3", "ISSUER-3", -3)):
        identity = {"security_id": sid, "company_id": cid, "identity_epoch": "cut-1"}
        members.append({**identity, "known_at": "2026-09-27T00:00:00Z",
                        "effective_from": "2026-09-01T00:00:00Z", "effective_to": None,
                        "source_ref": "fixture:membership:" + sid})
        observations.append({**identity, "start_at": START, "end_at": END,
                             "known_at": DECISION, "start_value": 100, "end_value": 100 + ret,
                             "currency": "USD", "return_basis": "total_return_index_v1",
                             "source_ref": "fixture:price:" + sid})
    return {
        "schema": INPUT_SCHEMA, "decision_at": DECISION,
        "focal": {"security_id": "FOCAL", "company_id": "ISSUER-F", "identity_epoch": "cut-1",
                  "identity_source_ref": "fixture:identity-cut-1"},
        "cohort": {"subtheme_id": "fixture:subtheme-1", "definition_ref": "fixture:definition-1",
                   "membership_ref": "fixture:membership-cut", "formed_at": "2026-09-28T13:00:00Z",
                   "universe_description": "Four invented issuers for research contract testing",
                   "purpose": "supplied_research_cohort", "rights_ref": "fixture:synthetic-no-vendor-data",
                   "members": members},
        "window": {"start_at": START, "end_at": END, "currency": "USD",
                   "return_basis": "total_return_index_v1", "max_age_seconds": 60},
        "observations": observations, "catalysts": [], "catalyst_coverage": [],
    }


def event(sid="FOCAL", cid="ISSUER-F", eid="event-f", comparison="mechanism:fixture-1", **overrides):
    return {"event_owner": "fixture", "event_id": eid, "revision_id": eid + ":r1", "security_id": sid,
            "company_id": cid, "identity_epoch": "cut-1", "event_type": "confirmed_result",
            "comparison_owner": "fixture" if comparison is not None else None,
            "comparison_key": comparison, "source_available_at": "2026-09-28T14:00:00Z",
            "known_at": "2026-09-28T14:01:00Z", "status": "current",
            "source_ref": "fixture:" + eid, **overrides}


def test_focal_does_not_enter_its_peer_comparator():
    inp = peer_inputs()
    first = build_peer_context(inp)
    inp["observations"][0]["end_value"] = 190
    second = build_peer_context(inp)
    assert first["statistics"]["observed_subset_equal_weight_return_pct"] == pytest.approx(1)
    assert second["statistics"]["observed_subset_equal_weight_return_pct"] == pytest.approx(1)
    assert first["statistics"]["focal_minus_observed_peers_pp"] == pytest.approx(11)
    assert second["statistics"]["focal_minus_observed_peers_pp"] == pytest.approx(89)


def test_same_issuer_listing_excluded_and_graph_paths_not_double_counted():
    inp = peer_inputs()
    alt = deepcopy(inp["cohort"]["members"][0]); alt["security_id"] = "FOCAL-ADR"
    inp["cohort"]["members"] += [alt, deepcopy(inp["cohort"]["members"][1])]
    out = build_peer_context(inp)
    assert out["coverage"]["eligible_peer_issuers"] == 3
    assert out["coverage"]["observed_peer_issuers"] == 3
    assert {"security_id": "FOCAL-ADR", "reason": "FOCAL_ISSUER_EXCLUDED"} in out["excluded"]


def test_ambiguous_peer_listings_do_not_get_an_invented_primary_listing():
    inp = peer_inputs()
    alt = deepcopy(inp["cohort"]["members"][1]); alt["security_id"] = "P1-ADR"
    inp["cohort"]["members"].append(alt)
    out = build_peer_context(inp)
    assert out["coverage"] == {"eligible_peer_issuers": 3, "observed_peer_issuers": 2,
                               "fraction": 2 / 3, "ambiguous_peer_issuers": 1}
    assert out["statistics"]["complete_cohort_equal_weight_return_pct"] is None


def test_missing_member_remains_in_eligible_denominator():
    inp = peer_inputs(); inp["observations"].pop()
    out = build_peer_context(inp)
    assert out["state"] == "PARTIAL"
    assert out["coverage"]["fraction"] == 2 / 3
    assert out["statistics"]["observed_subset_equal_weight_return_pct"] == pytest.approx(3)
    assert out["statistics"]["complete_cohort_equal_weight_return_pct"] is None


@pytest.mark.parametrize("field,value,reason", [
    ("known_at", "2026-09-28T20:00:09Z", "PRICE_NOT_KNOWN_AT_DECISION"),
    ("end_at", "2026-09-28T19:59:00Z", "PRICE_WINDOW_MISMATCH"),
    ("start_at", "2026-09-28T13:31:00Z", "PRICE_WINDOW_MISMATCH"),
    ("currency", "EUR", "PRICE_CURRENCY_MISMATCH"),
    ("return_basis", "raw_price", "PRICE_BASIS_MISMATCH"),
    ("identity_epoch", "later-cut", "PRICE_IDENTITY_MISMATCH"),
    ("company_id", "DIFFERENT", "PRICE_IDENTITY_MISMATCH"),
])
def test_bad_peer_observations_reduce_coverage(field, value, reason):
    inp = peer_inputs(); inp["observations"][1][field] = value
    out = build_peer_context(inp)
    assert out["coverage"]["observed_peer_issuers"] == 2
    assert {"security_id": "P1", "reason": reason} in out["excluded"]


def test_stale_endpoints_never_become_zero_returns():
    inp = peer_inputs(); inp["decision_at"] = "2026-09-28T20:02:00Z"
    out = build_peer_context(inp)
    assert out["state"] == "FOCAL_PRICE_UNAVAILABLE"
    assert out["statistics"]["observed_subset_equal_weight_return_pct"] is None


@pytest.mark.parametrize("field,value", [
    ("known_at", "2026-09-28T13:00:01Z"),
    ("effective_from", "2026-09-28T13:00:01Z"),
    ("effective_to", "2026-09-28T13:00:00Z"),
])
def test_membership_is_frozen_before_the_return_window(field, value):
    inp = peer_inputs(); inp["cohort"]["members"][1][field] = value
    out = build_peer_context(inp)
    assert out["coverage"]["eligible_peer_issuers"] == 2
    assert not any(r["security_id"] == "P1" for r in out["observed_peers"])


def test_missing_focal_membership_cannot_claim_subtheme_comparison():
    inp = peer_inputs(); inp["cohort"]["members"].pop(0)
    out = build_peer_context(inp)
    assert out["state"] == "FOCAL_MEMBERSHIP_UNAVAILABLE"
    assert out["statistics"]["focal_minus_observed_peers_pp"] is None


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 0, -1])
def test_bad_prices_refuse(value):
    inp = peer_inputs(); inp["observations"][0]["end_value"] = value
    with pytest.raises(ContextError): build_peer_context(inp)


def test_duplicate_conflicting_identity_refuses():
    inp = peer_inputs()
    row = deepcopy(inp["cohort"]["members"][1]); row["company_id"] = "OTHER"
    inp["cohort"]["members"].append(row)
    with pytest.raises(ContextError, match="conflicting duplicate"): build_peer_context(inp)


def test_common_shock_is_participation_and_never_a_leader():
    inp = peer_inputs()
    for obs in inp["observations"]: obs["end_value"] = 110
    out = build_peer_context(inp)
    assert out["statistics"]["advancing"] == 3
    assert out["statistics"]["focal_minus_observed_peers_pp"] == pytest.approx(0)
    assert not any(out["authority"].values())
    assert out["source_admission_established"] is False
    assert "PARTICIPATION_IS_NOT_CAUSAL_SPILLOVER" in out["interpretation_limits"]


def test_breadth_and_dispersion_preserve_opposite_peer_moves():
    out = build_peer_context(peer_inputs())
    assert out["statistics"]["advancing"] == 2
    assert out["statistics"]["declining"] == 1
    assert out["statistics"]["observed_subset_dispersion_pp"] > 2


def test_shared_comparable_and_other_catalysts_are_distinct():
    inp = peer_inputs()
    inp["catalysts"] = [event(), event("P1", "ISSUER-1"),
                        event("P2", "ISSUER-2", "event-p2"),
                        event("P3", "ISSUER-3", "event-other", "different-mechanism")]
    inp["catalysts"].append(deepcopy(inp["catalysts"][0]))
    peers = build_peer_context(inp)["catalyst_context"]["peers"]
    assert peers[0]["same_underlying_event_ids"] == ["fixture::event-f"]
    assert peers[1]["distinct_comparable_event_ids"] == ["fixture::event-p2"]
    assert peers[2]["other_observed_event_ids"] == ["fixture::event-other"]


def test_no_comparison_key_means_no_inferred_similarity():
    inp = peer_inputs()
    inp["catalysts"] = [event(comparison=None), event("P1", "ISSUER-1", "peer-event", None)]
    row = build_peer_context(inp)["catalyst_context"]["peers"][0]
    assert not row["distinct_comparable_event_ids"]
    assert row["other_observed_event_ids"] == ["fixture::peer-event"]


def test_equal_native_ids_from_different_owners_are_not_equivalent_events():
    inp = peer_inputs()
    inp["catalysts"] = [event(), event("P1", "ISSUER-1", event_owner="different-owner",
                                     comparison_owner="different-owner")]
    row = build_peer_context(inp)["catalyst_context"]["peers"][0]
    assert row["same_underlying_event_ids"] == []
    assert row["distinct_comparable_event_ids"] == []
    assert row["other_observed_event_ids"] == ["different-owner::event-f"]


def test_no_news_coverage_is_not_no_catalyst():
    inp = peer_inputs()
    no_coverage = build_peer_context(inp)["catalyst_context"]["peers"][0]
    assert no_coverage["coverage_state"] == "COVERAGE_UNKNOWN"
    assert not no_coverage["no_event_observed_in_covered_sources"]
    inp["catalyst_coverage"] = [{"security_id": "P1", "company_id": "ISSUER-1",
        "identity_epoch": "cut-1", "covered_from": START, "covered_through": END,
        "known_at": DECISION, "state": "covered", "source_ref": "fixture:covered-source-set"}]
    covered = build_peer_context(inp)["catalyst_context"]["peers"][0]
    assert covered["no_event_observed_in_covered_sources"]


def test_late_corrected_and_withdrawn_revisions_are_not_current_catalysts():
    inp = peer_inputs()
    inp["catalysts"] = [event(status="superseded"),
        event(eid="withdrawn", status="withdrawn"),
        event(eid="late", known_at="2026-09-28T20:00:09Z")]
    ctx = build_peer_context(inp)["catalyst_context"]
    assert ctx["focal_event_ids"] == []
    assert ctx["superseded_revision_count"] == 1
    assert ctx["withdrawn_or_cancelled_count"] == 1
    assert ctx["late_observation_count"] == 1


def test_two_current_revisions_refuse_instead_of_electing_truth():
    inp = peer_inputs(); inp["catalysts"] = [event(), event(revision_id="r2")]
    with pytest.raises(ContextError, match="owner reconciliation"): build_peer_context(inp)


@pytest.mark.parametrize("status", ["current", "withdrawn", "cancelled"])
def test_revision_conflicts_outside_price_window_still_require_owner_reconciliation(status):
    inp = peer_inputs()
    inp["catalysts"] = [event(), event(revision_id="r2", status=status,
        source_available_at="2026-09-28T20:00:01Z", known_at=DECISION)]
    with pytest.raises(ContextError, match="owner reconciliation"): build_peer_context(inp)


def test_covered_withdrawn_history_cannot_become_no_event_observed():
    inp = peer_inputs()
    inp["catalysts"] = [event("P1", "ISSUER-1", "peer-event", status="withdrawn")]
    inp["catalyst_coverage"] = [{"security_id": "P1", "company_id": "ISSUER-1",
        "identity_epoch": "cut-1", "covered_from": START, "covered_through": END,
        "known_at": DECISION, "state": "covered", "source_ref": "fixture:covered"}]
    row = build_peer_context(inp)["catalyst_context"]["peers"][0]
    assert not row["no_event_observed_in_covered_sources"]
    assert row["observed_event_revisions"][0]["status"] == "withdrawn"
    assert row["other_observed_event_ids"] == []


def test_source_mutation_changes_identity_without_mutating_previous_output():
    inp = peer_inputs(); original = deepcopy(inp)
    out = build_peer_context(inp)
    assert inp == original and out == build_peer_context(original)
    inp["observations"][1]["end_value"] = 90
    updated = build_peer_context(inp)
    assert out["context_id"] != updated["context_id"]
    assert out["observed_peers"][0]["return_pct"] == pytest.approx(4)


def test_closed_fields_refuse_a_score_or_admission_flag():
    inp = peer_inputs(); inp["cohort"]["qualified"] = True
    with pytest.raises(ContextError): build_peer_context(inp)
    inp = peer_inputs(); inp["score"] = 99
    with pytest.raises(ContextError): build_peer_context(inp)


def owner_request():
    return json.loads((FIXTURES / "owner_request.json").read_text())


def test_real_owner_code_composition_preserves_b4_and_news_semantics():
    request = owner_request()
    out = build_stock_assessment(request)
    assert out["entry_context"]["owner_projection"] == request["entry"]["payload"]
    assert out["entry_context"]["strategy_scientific_status"] == "CONTROL_ONLY"
    assert out["news_changes"]["state"] == "OWNER_PROJECTION_ATTACHED"
    assert len(out["news_changes"]["views"]) > 0
    assert not any(out["authority"].values())
    assert all(v["value"] is None for v in out["advanced_estimates"].values())


def test_strong_peer_returns_cannot_change_existing_entry_state():
    request = owner_request(); before = build_stock_assessment(request)
    for obs in request["peer_inputs"]["observations"]: obs["end_value"] *= 3
    after = build_stock_assessment(request)
    assert before["entry_context"] == after["entry_context"]


def test_absent_b4_does_not_create_an_entry_signal():
    request = owner_request(); request["entry"] = None
    out = build_stock_assessment(request)
    assert out["entry_context"]["state"] == "OWNER_INPUT_UNAVAILABLE"
    assert out["entry_context"]["owner_projection"] is None


def test_news_changes_require_distinct_historical_owner_snapshot():
    request = owner_request(); request["news"]["prior_owners"] = None
    out = build_stock_assessment(request)
    assert out["news_changes"]["state"] == "OWNER_COMPARISON_CUT_UNAVAILABLE"
    assert out["news_changes"]["views"] == []


def test_news_owner_snapshot_not_known_at_prior_cut_is_unavailable():
    request = owner_request()
    request["news"]["prior_owners"]["known_at"] = request["peer_inputs"]["decision_at"]
    out = build_stock_assessment(request)
    assert out["news_changes"]["state"] == "OWNER_SNAPSHOT_NOT_KNOWN_AT_CUT"


def test_entry_digest_and_cross_facet_identity_are_checked():
    request = owner_request(); request["entry"]["payload"]["entry_open"] = True
    with pytest.raises(ContextError, match="digest"): build_stock_assessment(request)
    request = owner_request(); request["peer_inputs"]["focal"]["identity_epoch"] = "foreign"
    with pytest.raises(ContextError, match="identity"): build_stock_assessment(request)


def test_cli_is_an_actual_replay_consumer():
    request = owner_request()
    result = subprocess.run([sys.executable, "-m", "engine.catalyst_intelligence"], cwd=ROOT,
                            input=json.dumps(request), text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == build_stock_assessment(request)
