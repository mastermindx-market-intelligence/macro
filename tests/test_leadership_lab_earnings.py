"""Leadership Lab consumes the existing Earnings dossier; it never recomputes it."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest


def base_view():
    row = {
        "ticker": "AAPL", "legacy_alpha": 2.0, "legacy_rs": 95.0,
        "current_context": {
            "episode": {
                "status": "AVAILABLE",
                "episode_id": "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1",
                "company_id": "ISS:US:320193",
                "security_id": "SEC:US-XNAS-AAPL",
                "identity_epoch": "epoch_0",
                "identity_epoch_state": "provisional",
                "episode_state": "ACTIVE",
                "opened_session": "2026-07-30",
                "opened_at": "2026-07-30T20:33:00Z",
                "last_observed_at": "2026-10-02T20:00:00Z",
                "observation_count": 11,
                "intake_classes": ["technical_emergence"],
            },
            "authority": {"rank": False, "entry": False, "size": False,
                          "execution": False, "trade": False},
        },
    }
    return {
        "schema": "mastermind.leadership_lab.recovery.v1",
        "rows": [deepcopy(row)],
        "shortlist": [deepcopy(row)],
        "current_context": {
            "episode_book": {
                "status": "AVAILABLE",
                "generation_id": "peg:" + "a" * 64,
                "source_validation": {"status": "VALIDATED_CANONICAL_OWNER"},
            },
            "authority": {"rank": False, "entry": False, "size": False,
                          "execution": False, "trade": False},
        },
        "authority": {"prophet_rank": False, "entry": False, "sizing": False,
                      "trade": False, "production_publish": False},
        "forecast_probability": None,
    }


def detail(*, authority=None, episode_id=None, generation_id=None,
           identity_ref=None, opened_at=None, opened_session=None):
    authority = authority or {
        "rank": False, "entry": False, "size": False,
        "execution": False, "trade": False,
    }
    return {
        "schema": "prophet.episode_earnings_detail/v1",
        "episode_ref": {
            "schema": "prophet.candidate_episode/v1",
            "episode_id": episode_id or "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1",
            "generation_id": generation_id or "peg:" + "a" * 64,
            "identity_ref": identity_ref or "ISS:US:320193",
        },
        "source_projection_id": "piv:" + "1" * 64,
        "decision_cut": {
            "opened_at": opened_at or "2026-07-30T20:33:00Z",
            "opened_session": opened_session or "2026-07-30",
            "anchor_time": "2026-07-30T20:00:00Z",
            "known_at": opened_at or "2026-07-30T20:33:00Z",
            "tradable_at": {
                "state": "NOT_ASSERTED", "value": None,
                "basis": "no_us_availability_owner_and_b4_not_built",
            },
        },
        "time_interpretation": "ORIGINAL_SOURCE_VINTAGE_RECONSTRUCTION_NOT_ORIGINAL_RECOMMENDATION",
        "method_scope": "RETROSPECTIVE_FACTUAL_RECONSTRUCTION_NO_AS_RUN_PROMOTION",
        "is_original_as_run_recommendation": False,
        "coverage": {"state": "COVERED", "basis": "qualified_fixture"},
        "headline": "Revenue grew 16.4% against the comparable prior-year quarter",
        "interpretation": "Reported operating evidence; not a consensus beat, forecast or permission to buy.",
        "comparison_state": "COMPARABLE_REPORTED_CHANGE_BOUND",
        "current_observations": [{"private": "must-not-project"}],
        "dossier": {
            "schema": "prophet.earnings_dossier/v1",
            "event_id": "evt_cik0000320193_2026q3_results",
            "issuer_id": "cik:0000320193",
            "decision_at": "2026-07-30T20:33:00Z",
            "reported_changes": [{
                "schema": "prophet.earnings_evidence/v1",
                "kind": "COMPARABLE_REPORTED_CHANGE",
                "metric": "revenue",
                "current_fiscal_period": "2026Q3",
                "prior_fiscal_period": "2025Q3",
                "current_value": 109417,
                "prior_value": 94036,
                "units": "usd_millions",
                "currency": "USD",
                "basis": "gaap",
                "signed_difference": 15381,
                "change_pct": 16.356501765281383,
                "issuer_id": "cik:0000320193",
                "current_event_id": "evt_cik0000320193_2026q3_results",
                "prior_event_id": "evt_cik0000320193_2026q3_results",
                "decision_at": "2026-07-30T20:33:00Z",
                "current_available_at": "2026-07-30T20:30:28Z",
                "prior_available_at": "2026-07-30T20:30:28Z",
                "source_contract_ref": "macro:8069:ref",
                "private_path": "/must/not/leak",
            }],
            "expectation_surprises": [],
            "matched_revisions": [],
            "source_contract_refs": ["macro:8069:ref"],
            "limitations": ["no qualified pre-release expectation surprise"],
            "authority": dict(authority),
        },
        "evidence_brief": {
            "schema": "prophet.earnings_evidence_brief/v1",
            "issuer_id": "cik:0000320193",
            "event_id": "evt_cik0000320193_2026q3_results",
            "decision_at": "2026-07-30T20:33:00Z",
            "summary_state": "FACTS_AVAILABLE",
            "supporting_facts": [{
                "code": "REPORTED_INCREASE",
                "text": "Revenue rose 16.4% against the comparable period.",
                "evidence_ref": "reported_changes[0]",
                "values": {"metric": "revenue", "change_pct": 16.356501765281383,
                           "signed_difference": 15381},
            }],
            "counterevidence": [],
            "context_facts": [],
            "not_established": [
                "QUALIFIED_PRE_RELEASE_EXPECTATION",
                "CURRENT_MARKET_AND_PORTFOLIO_PERMISSION",
            ],
            "next_step": "Review unresolved evidence before treating this research as a trade.",
            "interpretation": "Evidence explanation only; fact count is not conviction.",
            "authority": dict(authority),
        },
        "missing": [
            "QUALIFIED_PRE_RELEASE_EXPECTATION",
            "MATCHED_FORECAST_REVISIONS",
            "CURRENT_ENTRY_AND_MARKET_PERMISSION",
        ],
        "authority": dict(authority),
    }


def attach(view=None, details=None):
    from engine.leadership_lab.earnings import attach_earnings_evidence
    episode_id = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1"
    return attach_earnings_evidence(
        base_view() if view is None else view,
        {episode_id: detail()} if details is None else details,
        subject_bindings_by_episode={episode_id: _owner_subject_binding()},
        issuer_master=_native_issuer_master(),
    )


def test_attaches_whitelisted_fact_evidence_without_changing_rank_or_authority():
    before = base_view()
    result = attach(before)
    assert before == base_view()
    row = result["rows"][0]
    assert row["legacy_alpha"] == 2.0 and row["legacy_rs"] == 95.0
    assert result["authority"] == before["authority"]
    earnings = row["current_context"]["earnings"]
    assert earnings["status"] == "AVAILABLE"
    assert earnings["headline"].startswith("Revenue grew 16.4%")
    assert earnings["comparison_state"] == "COMPARABLE_REPORTED_CHANGE_BOUND"
    assert earnings["forecast_probability"] is None
    assert earnings["catalyst_probability"] is None
    assert earnings["rerating_probability"] is None
    assert all(v is False for v in earnings["authority"].values())


def test_reported_change_projects_only_safe_factual_fields():
    change = attach()["rows"][0]["current_context"]["earnings"]["reported_changes"][0]
    assert change == {
        "metric": "revenue",
        "current_fiscal_period": "2026Q3",
        "prior_fiscal_period": "2025Q3",
        "current_value": 109417.0,
        "prior_value": 94036.0,
        "units": "usd_millions",
        "currency": "USD",
        "basis": "gaap",
        "change_pct": pytest.approx(16.356501765281383),
        "current_available_at": "2026-07-30T20:30:28Z",
        "source_contract_ref": "macro:8069:ref",
    }
    rendered = json.dumps(change)
    assert "private_path" not in rendered


def test_brief_preserves_support_counterevidence_and_not_established_without_vote():
    earnings = attach()["rows"][0]["current_context"]["earnings"]
    assert earnings["brief"]["summary_state"] == "FACTS_AVAILABLE"
    assert earnings["brief"]["supporting_facts"][0]["code"] == "REPORTED_INCREASE"
    assert earnings["brief"]["counterevidence"] == []
    assert "QUALIFIED_PRE_RELEASE_EXPECTATION" in earnings["not_established"]
    assert "CURRENT_MARKET_AND_PORTFOLIO_PERMISSION" in earnings["not_established"]
    assert "score" not in earnings and "confidence" not in earnings


@pytest.mark.parametrize("mutation,reason", [
    ({"schema": "bad"}, "OWNER_SCHEMA_MISMATCH"),
    ({"authority": {"rank": True, "entry": False, "size": False,
                    "execution": False, "trade": False}}, "OWNER_AUTHORITY_DRIFT"),
    ({"is_original_as_run_recommendation": True}, "OWNER_METHOD_SCOPE_DRIFT"),
    ({"method_scope": "PROMOTED"}, "OWNER_METHOD_SCOPE_DRIFT"),
    ({"episode_ref": {"schema": "prophet.candidate_episode/v1",
                      "episode_id": "other", "generation_id": "peg:" + "a" * 64,
                      "identity_ref": "ISS:US:320193"}}, "EPISODE_IDENTITY_MISMATCH"),
    ({"decision_cut": {"opened_at": "2026-07-31T20:33:00Z",
                       "opened_session": "2026-07-30"}}, "EPISODE_CLOCK_MISMATCH"),
])
def test_contract_or_identity_drift_refuses_only_earnings_lane(mutation, reason):
    payload = detail()
    payload.update(mutation)
    result = attach(details={
        "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1": payload})
    row = result["rows"][0]
    assert row["legacy_alpha"] == 2.0
    assert row["current_context"]["earnings"] == {
        "status": "REFUSED", "reason": reason,
    }


def test_missing_earnings_detail_is_unavailable_not_negative():
    result = attach(details={})
    earnings = result["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "UNAVAILABLE", "reason": "NO_EARNINGS_DETAIL"}
    assert result["current_context"]["earnings"]["available_rows"] == 0


def test_detail_for_row_without_native_episode_is_not_joined_by_ticker():
    view = base_view()
    view["rows"][0]["current_context"]["episode"] = {
        "status": "UNAVAILABLE", "reason": "NO_CURRENT_EPISODE"}
    view["shortlist"][0]["current_context"]["episode"] = deepcopy(
        view["rows"][0]["current_context"]["episode"])
    result = attach(view=view)
    earnings = result["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "UNAVAILABLE", "reason": "NO_NATIVE_EPISODE_ID"}


def test_adapter_is_pure_and_contains_no_network_or_source_reader():
    import ast
    from pathlib import Path
    from engine.leadership_lab import earnings as module
    source = Path(module.__file__).read_text()
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "requests" not in imports
    assert "urllib" not in imports
    assert "read_event_source_revisions" not in source
    assert "find_current_event_id_for_company" not in source


@pytest.mark.parametrize('level', ['owner', 'dossier', 'brief'])
def test_authority_requires_literal_false_not_numeric_zero(level):
    payload = detail()
    target = payload if level == 'owner' else payload['dossier'] if level == 'dossier' else payload['evidence_brief']
    target['authority']['rank'] = 0
    result = attach(details={'pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1': payload})
    assert result['rows'][0]['current_context']['earnings']['status'] == 'REFUSED'


def test_reported_fact_after_episode_cut_cannot_be_backdated():
    payload = detail()
    payload['dossier']['reported_changes'][0]['current_available_at'] = '2026-07-31T20:30:28Z'
    result = attach(details={'pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1': payload})
    assert result['rows'][0]['current_context']['earnings']['status'] == 'REFUSED'


def test_earnings_projection_preserves_owner_reference_and_decision_cut():
    payload = detail()
    result = attach(details={'pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1': payload})
    output = result['rows'][0]['current_context']['earnings']
    assert output['source_projection_id'] == payload['source_projection_id']
    assert output['decision_cut'] == payload['decision_cut']
    assert output['source_authentication'] == 'CALLER_SUPPLIED_OWNER_OUTPUT_NOT_INDEPENDENTLY_ATTESTED'


def _owner_subject_binding():
    return {
        "state": "RESOLVED",
        "episode_company_id": "ISS:US:320193",
        "earnings_company_id": "cik:0000320193",
        "owner_subject_id": "evt_cik0000320193_2026q3_results",
    }


def _attach_with_binding(payload):
    from engine.leadership_lab.earnings import attach_earnings_evidence
    episode_id = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1"
    return attach_earnings_evidence(
        base_view(), {episode_id: payload},
        subject_bindings_by_episode={episode_id: _owner_subject_binding()},
        issuer_master=_native_issuer_master(),
    )


def test_nested_dossier_must_match_explicit_owner_subject_binding():
    payload = detail()
    payload["dossier"]["issuer_id"] = "cik:0000789019"
    payload["dossier"]["event_id"] = "evt_cik0000789019_2026q3_results"
    payload["evidence_brief"]["issuer_id"] = "cik:0000789019"
    payload["evidence_brief"]["event_id"] = "evt_cik0000789019_2026q3_results"
    result = _attach_with_binding(payload)
    assert result["rows"][0]["current_context"]["earnings"] == {
        "status": "REFUSED", "reason": "EARNINGS_NATIVE_ISSUER_MISMATCH",
    }


def test_missing_subject_binding_refuses_factual_dossier():
    payload = detail()
    from engine.leadership_lab.earnings import attach_earnings_evidence
    episode_id = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1"
    result = attach_earnings_evidence(
        base_view(), {episode_id: payload}, issuer_master=_native_issuer_master())
    assert result["rows"][0]["current_context"]["earnings"] == {
        "status": "REFUSED", "reason": "EARNINGS_SUBJECT_BINDING_UNAVAILABLE",
    }


@pytest.mark.parametrize("mutation", [
    {"source_projection_id": None},
    {"source_projection_id": "piv:not-a-content-id"},
])
def test_source_projection_reference_is_required_and_typed(mutation):
    payload = detail()
    payload["decision_cut"].update({
        "anchor_time": "2026-07-30T20:00:00Z",
        "known_at": "2026-07-30T20:33:00Z",
        "tradable_at": {
            "state": "NOT_ASSERTED", "value": None,
            "basis": "no_us_availability_owner_and_b4_not_built",
        },
    })
    payload.update(mutation)
    result = _attach_with_binding(payload)
    assert result["rows"][0]["current_context"]["earnings"]["status"] == "REFUSED"


def test_full_decision_cut_must_preserve_owner_max_clock_invariant():
    payload = detail()
    payload["decision_cut"].update({
        "anchor_time": "2099-01-01T00:00:00Z",
        "known_at": "2099-01-01T00:00:00Z",
        "tradable_at": {
            "state": "NOT_ASSERTED", "value": None,
            "basis": "no_us_availability_owner_and_b4_not_built",
        },
    })
    result = _attach_with_binding(payload)
    assert result["rows"][0]["current_context"]["earnings"] == {
        "status": "REFUSED", "reason": "EPISODE_CLOCK_MISMATCH",
    }


def test_every_reported_comparison_availability_clock_must_precede_cut():
    payload = detail()
    payload["decision_cut"].update({
        "anchor_time": "2026-07-30T20:00:00Z",
        "known_at": "2026-07-30T20:33:00Z",
        "tradable_at": {
            "state": "NOT_ASSERTED", "value": None,
            "basis": "no_us_availability_owner_and_b4_not_built",
        },
    })
    payload["dossier"]["reported_changes"][0].update({
        "issuer_id": "cik:0000320193",
        "current_event_id": "evt_cik0000320193_2026q3_results",
        "prior_event_id": "evt_cik0000320193_2026q3_results",
        "decision_at": "2026-07-30T20:33:00Z",
        "prior_available_at": "2026-07-31T00:00:00Z",
    })
    result = _attach_with_binding(payload)
    assert result["rows"][0]["current_context"]["earnings"] == {
        "status": "REFUSED", "reason": "EPISODE_CLOCK_MISMATCH",
    }

# L3A guard: never accept a caller-declared RESOLVED tuple as independent issuer proof.
def _native_issuer_master(*, issuer_state="RESOLVED", security_state=None,
                          cik="0000320193", issuer_id="ISS:US:320193"):
    from lib.dataos.identity import IssuerMaster
    return IssuerMaster.from_records([{
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": issuer_id,
        "issuer_cik": cik,
        "issuer_state": issuer_state,
        "security_state": security_state,
        "listing_key": "US-XNAS-AAPL",
    }])


def _attach_with_native_master(payload, *, issuer_master=None, binding=None):
    from engine.leadership_lab.earnings import attach_earnings_evidence
    episode_id = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1"
    return attach_earnings_evidence(
        base_view(), {episode_id: payload},
        subject_bindings_by_episode={episode_id: binding or _owner_subject_binding()},
        issuer_master=_native_issuer_master() if issuer_master is None else issuer_master,
    )


def test_native_issuer_reader_qualifies_current_subject_without_historical_identity_claim():
    row = _attach_with_native_master(detail())["rows"][0]["current_context"]["earnings"]
    assert row["status"] == "AVAILABLE"
    assert row["issuer_id"] == "cik:0000320193"
    assert row["identity_scope"] == "CURRENT_ISSUER_MASTER_ONLY_NOT_PIT"
    assert row["historical_identity_qualified"] is False
    assert row["authority"]["trade"] is False


def test_caller_declared_resolved_subject_cannot_override_canonical_issuer_cik():
    payload = detail()
    payload["dossier"]["issuer_id"] = "cik:0000000001"
    payload["dossier"]["event_id"] = "evt_cik0000000001_2026q3_results"
    payload["evidence_brief"]["issuer_id"] = payload["dossier"]["issuer_id"]
    payload["evidence_brief"]["event_id"] = payload["dossier"]["event_id"]
    for change in payload["dossier"]["reported_changes"]:
        change["issuer_id"] = payload["dossier"]["issuer_id"]
        change["current_event_id"] = payload["dossier"]["event_id"]
        change["prior_event_id"] = payload["dossier"]["event_id"]
    false_binding = {
        "state": "RESOLVED", "episode_company_id": "ISS:US:320193",
        "earnings_company_id": "cik:0000000001",
        "owner_subject_id": "evt_cik0000000001_2026q3_results",
    }
    earnings = _attach_with_native_master(payload, binding=false_binding)["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "REFUSED", "reason": "EARNINGS_NATIVE_ISSUER_MISMATCH"}


def test_caller_claim_without_native_issuer_reader_must_refuse_even_when_tuple_matches():
    from engine.leadership_lab.earnings import attach_earnings_evidence
    episode_id = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1"
    earnings = attach_earnings_evidence(
        base_view(), {episode_id: detail()},
        subject_bindings_by_episode={episode_id: _owner_subject_binding()},
    )["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "REFUSED", "reason": "EARNINGS_NATIVE_ISSUER_UNAVAILABLE"}


@pytest.mark.parametrize("master", [
    _native_issuer_master(issuer_state="PROVISIONAL"),
    _native_issuer_master(security_state="SUPERSEDED"),
    _native_issuer_master(issuer_id="ISS:US:someone-else"),
])
def test_unresolved_superseded_or_cross_issuer_native_identity_fails_closed(master):
    earnings = _attach_with_native_master(detail(), issuer_master=master)["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "REFUSED", "reason": "EARNINGS_NATIVE_ISSUER_MISMATCH"}


def test_prior_year_event_may_be_distinct_from_current_results_event():
    payload = detail()
    payload["dossier"]["reported_changes"][0]["prior_event_id"] = "evt_cik0000320193_2025q3_results"
    earnings = _attach_with_native_master(payload)["rows"][0]["current_context"]["earnings"]
    assert earnings["status"] == "AVAILABLE"
    assert earnings["reported_changes"][0]["metric"] == "revenue"


def test_unvalidated_b1_episode_cannot_qualify_earnings_even_with_matching_current_cik():
    from engine.leadership_lab.earnings import attach_earnings_evidence
    view = base_view()
    view["current_context"]["episode_book"]["source_validation"] = {"status": "NOT_VALIDATED"}
    episode_id = "pe:SEC:US-XNAS-AAPL:epoch_0:sa:abc:1"
    earnings = attach_earnings_evidence(
        view, {episode_id: detail()},
        subject_bindings_by_episode={episode_id: _owner_subject_binding()},
        issuer_master=_native_issuer_master(),
    )["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "REFUSED", "reason": "EARNINGS_EPISODE_GENERATION_UNVERIFIED"}
