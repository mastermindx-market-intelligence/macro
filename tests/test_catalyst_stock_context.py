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


# V2: independent company context and explicit current/history separation.
from engine.catalyst_intelligence import assessment_v2 as A2
from engine.news_impact import thesis as NEWS


def owner_request_v2():
    old = owner_request()
    return {
        "schema": A2.INPUT_SCHEMA,
        "focal": deepcopy(old["peer_inputs"]["focal"]),
        "decision_at": old["peer_inputs"]["decision_at"],
        "peer_inputs": old["peer_inputs"], "entry": old["entry"],
        "news": {"fact_log": old["news"]["fact_log"],
                 "current_owners": old["news"]["current_owners"],
                 "comparison": {"since_at": old["news"]["since_at"],
                                "prior_owners": old["news"]["prior_owners"]}},
    }


def _v2_prior_at(request, at="2026-09-28T14:10:00Z"):
    comp = request["news"]["comparison"]
    comp["since_at"] = at
    cut = comp["prior_owners"]
    cut["as_of"] = cut["known_at"] = at
    cut["payload"]["decision_cut"] = at
    cut["payload_digest"] = digest(cut["payload"])


def test_v2_no_peers_preserves_independent_current_news_and_entry():
    request = owner_request_v2()
    expected = A2.build_stock_assessment_v2(request)
    request["peer_inputs"] = None
    out = A2.build_stock_assessment_v2(request)
    assert out["peer_context"] == {
        "state": "UNAVAILABLE", "reason_code": "PEER_INPUT_NOT_SUPPLIED", "context": None}
    assert out["entry_context"] == expected["entry_context"]
    assert out["news_context"] == expected["news_context"]
    assert not any(out["authority"].values())
    assert not out["source_admission_established"]
    assert all(v["value"] is None for v in out["advanced_estimates"].values())


@pytest.mark.parametrize("defect", ["missing", "late"])
def test_v2_current_news_survives_unavailable_historical_snapshot(defect):
    request = owner_request_v2()
    expected_current = A2.build_stock_assessment_v2(request)["news_context"]["current"]
    if defect == "missing":
        request["news"]["comparison"]["prior_owners"] = None
        reason = "PRIOR_OWNER_INPUT_NOT_SUPPLIED"
    else:
        cut = request["news"]["comparison"]["prior_owners"]
        cut["known_at"] = cut["as_of"].replace("00Z", "00.000001Z")
        reason = "PRIOR_OWNER_NOT_KNOWN_AT_CUT"
    out = A2.build_stock_assessment_v2(request)["news_context"]
    assert out["current"] == expected_current
    assert out["current"]["views"]
    assert out["comparison"]["state"] == "UNAVAILABLE"
    assert out["comparison"]["reason_code"] == reason
    assert out["comparison"]["pairs"] is None
    assert out["comparison"]["prior_views"] is None


def test_v2_unrequested_comparison_does_not_replay_current_owners_as_prior(monkeypatch):
    request = owner_request_v2()
    request["news"]["comparison"] = None
    real = A2.project_news_theses
    calls = []
    def observe(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    monkeypatch.setattr(A2, "project_news_theses", observe)
    out = A2.build_stock_assessment_v2(request)["news_context"]
    assert out["current"]["state"] == "PROJECTED"
    assert out["comparison"]["state"] == "NOT_REQUESTED"
    assert len(calls) == 1
    assert "prior_owners" not in calls[0] and "prior_as_of_utc" not in calls[0]


@pytest.mark.parametrize("defect", ["missing", "late"])
def test_v2_missing_current_does_not_display_prior_as_current(defect):
    request = owner_request_v2()
    if defect == "missing":
        request["news"]["current_owners"] = None
        reason = "CURRENT_OWNER_INPUT_NOT_SUPPLIED"
    else:
        request["news"]["current_owners"]["known_at"] = DECISION.replace("08Z", "08.000001Z")
        reason = "CURRENT_OWNER_NOT_KNOWN_AT_CUT"
    out = A2.build_stock_assessment_v2(request)
    assert out["news_context"]["current"]["views"] is None
    assert out["news_context"]["comparison"]["pairs"] is None
    assert out["news_context"]["current"]["reason_code"] == reason
    assert out["entry_context"]["state"] == "OWNER_PROJECTION_ATTACHED"


def test_v2_empty_projected_news_is_distinct_from_missing_news():
    request = owner_request_v2()
    request["peer_inputs"] = request["entry"] = None
    request["focal"]["company_id"] = "cik:0000000001"
    empty = A2.build_stock_assessment_v2(request)["news_context"]
    assert empty["current"]["state"] == "PROJECTED"
    assert empty["current"]["views"] == []
    assert empty["comparison"]["state"] == "PROJECTED"
    assert empty["comparison"]["pairs"] == []
    request["news"] = None
    missing = A2.build_stock_assessment_v2(request)["news_context"]
    assert missing["current"]["state"] == "UNAVAILABLE"
    assert missing["current"]["views"] is None


def test_v2_supplied_peer_owner_context_is_preserved():
    request = owner_request_v2()
    out = A2.build_stock_assessment_v2(request)
    assert out["peer_context"]["context"] == build_peer_context(request["peer_inputs"])


@pytest.mark.parametrize("field", ["security_id", "company_id", "identity_epoch", "identity_source_ref"])
def test_v2_peer_identity_mismatch_refuses_instead_of_becoming_missing(field):
    request = owner_request_v2()
    request["peer_inputs"]["focal"][field] = "different"
    with pytest.raises(ContextError, match="peer focal"):
        A2.build_stock_assessment_v2(request)


@pytest.mark.parametrize("field", ["security_id", "company_id", "identity_epoch", "identity_source_ref"])
def test_v2_explicit_identity_is_validated_without_peers(field):
    request = owner_request_v2()
    request["peer_inputs"] = None
    request["focal"][field] = " "
    with pytest.raises(ContextError):
        A2.build_stock_assessment_v2(request)


@pytest.mark.parametrize("value", [{}, [], False, 0])
def test_v2_malformed_optional_peers_are_not_absence(value):
    request = owner_request_v2()
    request["peer_inputs"] = value
    with pytest.raises(ContextError):
        A2.build_stock_assessment_v2(request)


@pytest.mark.parametrize("at", [
    "2026-09-28T20:00Z", "2026-09-28T20:00:08.0000001Z",
    "20260928T20:00:08Z", "2026-09-28 20:00:08Z",
    "2026-09-28T20:00:08+00:00", "2026-09-28T20:00:08,1Z",
])
def test_v2_unsupported_composition_clock_is_refused(at):
    request = owner_request_v2()
    request["decision_at"] = at
    with pytest.raises(ContextError, match="complete UTC clock"):
        A2.build_stock_assessment_v2(request)


def test_v2_equivalent_clock_spelling_preserves_all_owner_evidence():
    request = owner_request_v2()
    original = deepcopy(request)
    before = A2.build_stock_assessment_v2(request)
    request["decision_at"] = DECISION.replace("08Z", "08.000000Z")
    after = A2.build_stock_assessment_v2(request)
    assert after["entry_context"] == before["entry_context"]
    assert after["news_context"] == before["news_context"]
    assert after["peer_context"] == before["peer_context"]
    assert after["input_digest"] != before["input_digest"]
    assert request["news"] == original["news"] and request["entry"] == original["entry"]


def test_v2_one_microsecond_peer_cut_mismatch_refuses():
    request = owner_request_v2()
    request["peer_inputs"]["decision_at"] = DECISION.replace("08Z", "08.000001Z")
    with pytest.raises(ContextError, match="peer decision"):
        A2.build_stock_assessment_v2(request)


@pytest.mark.parametrize("which", ["current", "prior"])
def test_v2_owner_evidence_timestamp_spelling_is_not_rewritten(which):
    request = owner_request_v2()
    cut = (request["news"]["current_owners"] if which == "current"
           else request["news"]["comparison"]["prior_owners"])
    cut["as_of"] = cut["as_of"][:-1] + ".000Z"
    with pytest.raises(ContextError, match="explicit decision_cut"):
        A2.build_stock_assessment_v2(request)


@pytest.mark.parametrize("which", ["current", "prior", "entry"])
def test_v2_overprecision_source_cut_is_refused(which):
    request = owner_request_v2()
    cut = (request["entry"] if which == "entry" else request["news"]["current_owners"]
           if which == "current" else request["news"]["comparison"]["prior_owners"])
    cut["known_at"] = cut["known_at"][:-1] + ".0000001Z"
    with pytest.raises(ContextError, match="complete UTC clock"):
        A2.build_stock_assessment_v2(request)


def test_v2_bad_prior_digest_is_refused_even_when_current_is_absent():
    request = owner_request_v2()
    request["news"]["current_owners"] = None
    request["news"]["comparison"]["prior_owners"]["payload"]["decision_cut"] = DECISION
    with pytest.raises(ContextError, match="digest"):
        A2.build_stock_assessment_v2(request)


def test_v2_nonpreceding_comparison_is_refused():
    request = owner_request_v2()
    request["news"]["comparison"]["since_at"] = DECISION
    with pytest.raises(ContextError, match="must precede"):
        A2.build_stock_assessment_v2(request)


def test_v2_malformed_fact_log_is_not_hidden_by_missing_owner_input():
    request = owner_request_v2()
    request["news"]["current_owners"] = None
    request["news"]["fact_log"] = {"schema": "invalid"}
    with pytest.raises(ContextError, match="fact log"):
        A2.build_stock_assessment_v2(request)


def test_v2_multiple_propositions_pair_by_company_and_original_fact():
    request = owner_request_v2()
    _v2_prior_at(request)
    log = request["news"]["fact_log"]
    new = deepcopy(log["records"][0])
    new.update(log_seq=max(r["log_seq"] for r in log["records"]) + 1,
               fact_id="fact_" + "d" * 24, cluster_id="ev2_" + "d" * 16,
               document_id="doc_synthetic_second_proposition",
               observed_at="2026-09-28T19:00:00Z", source_available_at="2026-09-28T18:59:00Z")
    new["fact_key"]["slot"]["horizon_token"] = "FY2030"
    new["provenance"].update(origin_document_id=new["document_id"],
                            origin_claim_id="claim_synthetic_second",
                            root_family_id="root_synthetic_second")
    new["evidence"].update(document_id=new["document_id"], span_id="span_" + "d" * 20)
    new["owner_claim_ids"] = ["claim_synthetic_second"]
    log["records"].append(new)  # The public projector validates this synthetic log.
    out = A2.build_stock_assessment_v2(request)["news_context"]
    pairs = out["comparison"]["pairs"]
    assert len(pairs) == 2
    indexed = {p["view_key"]["original_proposition_fact_id"]: p for p in pairs}
    assert indexed[log["records"][0]["fact_id"]]["presence"] == "BOTH_CUTS"
    assert indexed[new["fact_id"]]["presence"] == "CURRENT_ONLY"
    assert all(p["view_key"]["company_id"] == request["focal"]["company_id"] for p in pairs)
    owner = NEWS.project(log, request["news"]["current_owners"]["payload"], DECISION,
                         prior_as_of_utc=request["news"]["comparison"]["since_at"],
                         prior_owners=request["news"]["comparison"]["prior_owners"]["payload"],
                         decision_cut=DECISION)
    expected = {v["original_proposition_fact_id"]: v["material_delta_triggers"] for v in owner}
    assert {k: p["material_delta_triggers"] for k, p in indexed.items()} == expected


@pytest.mark.parametrize("stage", ["current", "prior", "compared"])
def test_v2_duplicate_owner_keys_refuse(stage, monkeypatch):
    request = owner_request_v2()
    _v2_prior_at(request)
    real = A2.project_news_theses
    def duplicate(*args, **kwargs):
        views = real(*args, **kwargs)
        actual = ("compared" if "prior_owners" in kwargs else
                  "current" if args[2] == DECISION else "prior")
        return views + (deepcopy(views[0]),) if stage == actual and views else views
    monkeypatch.setattr(A2, "project_news_theses", duplicate)
    with pytest.raises(ContextError, match="duplicate proposition"):
        A2.build_stock_assessment_v2(request)


@pytest.mark.parametrize("defect", ["keys", "payload", "triggers"])
def test_v2_disagreeing_owner_comparison_is_refused(defect, monkeypatch):
    request = owner_request_v2()
    real = A2.project_news_theses
    def corrupt(*args, **kwargs):
        views = real(*args, **kwargs)
        if "prior_owners" in kwargs:
            if defect == "keys":
                return ()
            views = tuple(deepcopy(v) for v in views)
            if defect == "payload":
                views[0]["as_of_utc"] = "2026-09-28T20:00:08.000001Z"
            else:
                views[0]["material_delta_triggers"] = None
        return views
    monkeypatch.setattr(A2, "project_news_theses", corrupt)
    with pytest.raises(ContextError, match="NewsImpact"):
        A2.build_stock_assessment_v2(request)


def test_v2_prior_only_is_not_invented_as_withdrawal_or_empty_current_change(monkeypatch):
    request = owner_request_v2()
    _v2_prior_at(request)
    real = A2.project_news_theses
    def historical_only(*args, **kwargs):
        views = real(*args, **kwargs)
        return () if args[2] == DECISION else views
    monkeypatch.setattr(A2, "project_news_theses", historical_only)
    out = A2.build_stock_assessment_v2(request)["news_context"]
    assert out["current"]["views"] == []
    assert len(out["comparison"]["prior_views"]) == 1
    assert out["comparison"]["pairs"][0]["presence"] == "PRIOR_ONLY"
    assert out["comparison"]["pairs"][0]["material_delta_triggers"] is None


def test_v2_immutable_replay_and_cli_preserve_v1_frozen_output():
    request = owner_request_v2()
    original = deepcopy(request)
    packet = A2.build_stock_assessment_v2(request)
    assert request == original
    assert packet == A2.build_stock_assessment_v2(original)
    for req, expected in [
        (request, packet),
        (owner_request(), json.loads((FIXTURES / "owner_assessment.json").read_text())),
    ]:
        result = subprocess.run([sys.executable, "-m", "engine.catalyst_intelligence"], cwd=ROOT,
                                input=json.dumps(req), text=True, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == expected
