"""Hermetic tests for engine.news_impact.thesis (A1 thesis store).

Section 5 worked cases are acceptance fixtures (W3-R1). No network, no data/
or site/ reads, no clock, no RNG except random.Random with a recorded seed
inside the permutation test. tmp_path is unused: the log path is a parameter
and is never opened.
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.news_impact import thesis as T

CIK = "cik:0001045810"
AS_OF_C1 = "2026-09-28T23:59:59Z"
CUT_C1 = "2026-09-28T14:05:00Z"
FACT_AUTH = "fact_a11c0e000000000000000001"
FACT_REUTERS = "fact_a11c0e000000000000000010"
FACT_BBG = "fact_a11c0e000000000000000011"
FACT_CORR = "fact_a11c0e000000000000000004"
FACT_NEMO = "fact_b22d1f000000000000000001"
FACT_DEPLOY = "fact_b22d1f000000000000000002"
FACT_LINK = "fact_b22d1f0000000000000000aa"
FACT_RIVAL = "fact_b22d1f000000000000000003"
CLUSTER_T1 = "ev2_a11c0e0000000001"
CLUSTER_T3 = "ev2_b22d1f0000000002"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
CORR_SHA = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

ABSENCE_CI_T1 = {
    "schema": "field_absence.v1",
    "authority": "context_only",
    "reason": "not_stated",
    "subject": "ci_event_id",
    "detail": "news capital allocation is not in company_event EVENT_TYPES",
    "missing_fields": ["ci_event_id"],
}

PROPHET = {
    "may_rank": False,
    "may_size": False,
    "may_gate": False,
    "prophet_authority": False,
}


def _span(doc: str, hex20: str) -> dict:
    return {"form": "owner_span_ref", "document_id": doc, "span_id": f"span_{hex20}"}


def _key_t1() -> dict:
    return {
        "company_id": CIK,
        "template": "capital_allocation_event.v1",
        "slot": {
            "kind": "t1_authorization_program",
            "action_type": "share_repurchase",
            "horizon_token": "FY2028",
        },
    }


def _key_t3() -> dict:
    return {
        "company_id": CIK,
        "template": "strategic_product_partnership_event.v1",
        "slot": {
            "kind": "t3_object_counterparty",
            "event_kind": "product_release",
            "object_name": "Nemotron 3",
            "counterparty_company_id": None,
        },
    }


def _key_t3_ms(name: str) -> dict:
    return {
        "company_id": CIK,
        "template": "strategic_product_partnership_event.v1",
        "slot": {
            "kind": "milestone_under_proposition",
            "milestone_name": name,
            "object_name": "Nemotron 3",
        },
    }


def case1_log() -> dict:
    return {
        "schema": "fact_log.v1",
        "authority": "context_only",
        "prophet_flags": dict(PROPHET),
        "unsolicited_instruction_detected": False,
        "records": [
            {
                "log_seq": 1,
                "record_kind": "fact_revision",
                "cluster_grain": "fact_revision",
                "fact_id": FACT_AUTH,
                "document_id": "doc_nvda_pr_20260928",
                "observed_at": "2026-09-28T14:05:00Z",
                "source_available_at": "2026-09-28T14:00:00Z",
                "supersedes_fact_id": None,
                "company_id": CIK,
                "cluster_id": CLUSTER_T1,
                "novelty": "new_magnitude_timing_commitment_counterparty",
                "polarity": "supporting",
                "fact_key": _key_t1(),
                "provenance": {
                    "origin_document_id": "doc_nvda_pr_20260928",
                    "origin_claim_id": "claim_nvda_auth_150b",
                    "root_family_id": "root_nvda_auth_20260928",
                    "source_family": "issuer_primary",
                },
                "evidence": _span("doc_nvda_pr_20260928", "aaaaaaaaaaaaaaaaaaaa"),
                "payload_schema": "capital_allocation_event.v1",
                "ci_event_id": dict(ABSENCE_CI_T1),
                "owner_claim_ids": ["claim_nvda_auth_150b"],
                "quantity_fingerprint": {"form": "present", "canonical_sha256": EMPTY_SHA},
                "reports_fact_id": None,
                "linked_fact_ids": [],
                "stated_deadline": "2028-01-30T00:00:00Z",
                "next_expected_observation": {
                    "milestone_name": "executed_repurchase",
                    "window_start": "2026-09-28T14:00:00Z",
                    "window_end": "2028-01-30T00:00:00Z",
                },
                "unsolicited_instruction_detected": False,
            },
            {
                "log_seq": 2,
                "record_kind": "manifestation",
                "cluster_grain": "article_manifestation",
                "fact_id": FACT_REUTERS,
                "document_id": "doc_reuters_nvda_auth_20260928",
                "observed_at": "2026-09-28T14:20:00Z",
                "source_available_at": "2026-09-28T14:18:00Z",
                "supersedes_fact_id": None,
                "company_id": CIK,
                "cluster_id": CLUSTER_T1,
                "novelty": "new_reporting_of_old_fact",
                "polarity": "supporting",
                "fact_key": _key_t1(),
                "provenance": {
                    "origin_document_id": "doc_nvda_pr_20260928",
                    "origin_claim_id": "claim_nvda_auth_150b",
                    "root_family_id": "root_nvda_auth_20260928",
                    "source_family": "wire_reprint",
                },
                "evidence": _span("doc_reuters_nvda_auth_20260928", "bbbbbbbbbbbbbbbbbbbb"),
                "payload_schema": "capital_allocation_event.v1",
                "ci_event_id": dict(ABSENCE_CI_T1),
                "owner_claim_ids": ["claim_nvda_auth_150b"],
                "quantity_fingerprint": {"form": "present", "canonical_sha256": EMPTY_SHA},
                "reports_fact_id": FACT_AUTH,
                "linked_fact_ids": [],
                "unsolicited_instruction_detected": False,
            },
            {
                "log_seq": 3,
                "record_kind": "manifestation",
                "cluster_grain": "article_manifestation",
                "fact_id": FACT_BBG,
                "document_id": "doc_bloomberg_nvda_auth_20260928",
                "observed_at": "2026-09-28T14:25:00Z",
                "source_available_at": "2026-09-28T14:22:00Z",
                "supersedes_fact_id": None,
                "company_id": CIK,
                "cluster_id": CLUSTER_T1,
                "novelty": "new_reporting_of_old_fact",
                "polarity": "supporting",
                "fact_key": _key_t1(),
                "provenance": {
                    "origin_document_id": "doc_nvda_pr_20260928",
                    "origin_claim_id": "claim_nvda_auth_150b",
                    "root_family_id": "root_nvda_auth_20260928",
                    "source_family": "wire_reprint",
                },
                "evidence": _span("doc_bloomberg_nvda_auth_20260928", "cccccccccccccccccccc"),
                "payload_schema": "capital_allocation_event.v1",
                "ci_event_id": dict(ABSENCE_CI_T1),
                "owner_claim_ids": ["claim_nvda_auth_150b"],
                "quantity_fingerprint": {"form": "present", "canonical_sha256": EMPTY_SHA},
                "reports_fact_id": FACT_AUTH,
                "linked_fact_ids": [],
                "unsolicited_instruction_detected": False,
            },
        ],
    }


def case1_owners() -> T.OwnerSnapshot:
    return T.OwnerSnapshot(
        leaf_payloads={
            FACT_AUTH: {
                "incremental": 150_000_000_000,
                "remaining": 235_000_000_000,
                "currency": "USD",
                "commitment_status": "authorized",
                "negated": False,
                "channel_hint": "capital_allocation",
            }
        },
        decision_cut=CUT_C1,
    )


def case3_record() -> dict:
    return {
        "log_seq": 4,
        "record_kind": "fact_revision",
        "cluster_grain": "fact_revision",
        "fact_id": FACT_CORR,
        "document_id": "doc_nvda_8k_corr_20261002",
        "observed_at": "2026-10-02T13:00:00Z",
        "source_available_at": "2026-10-02T12:50:00Z",
        "supersedes_fact_id": FACT_AUTH,
        "company_id": CIK,
        "cluster_id": CLUSTER_T1,
        "novelty": "corrected_fact",
        "polarity": "supporting",
        "fact_key": _key_t1(),
        "provenance": {
            "origin_document_id": "doc_nvda_8k_corr_20261002",
            "origin_claim_id": "claim_nvda_auth_150b_corr",
            "root_family_id": "root_nvda_auth_20260928",
            "source_family": "regulator_filing",
        },
        "evidence": _span("doc_nvda_8k_corr_20261002", "ffffaaaaaaaaaaaaaaaa"),
        "payload_schema": "capital_allocation_event.v1",
        "ci_event_id": dict(ABSENCE_CI_T1),
        "owner_claim_ids": ["claim_nvda_auth_150b_corr"],
        "quantity_fingerprint": {"form": "present", "canonical_sha256": CORR_SHA},
        "reports_fact_id": None,
        "linked_fact_ids": [],
        "stated_deadline": "2028-01-30T00:00:00Z",
        "unsolicited_instruction_detected": False,
    }


def case2_log() -> dict:
    abs_ci = {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": "not_stated",
        "subject": "ci_event_id",
        "detail": "open-model release is not in company_event EVENT_TYPES",
        "missing_fields": ["ci_event_id"],
    }
    abs_deadline = {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": "not_stated",
        "subject": "stated_deadline",
        "detail": "the announcement does not state a commercial deadline",
        "missing_fields": ["stated_deadline"],
    }
    return {
        "schema": "fact_log.v1",
        "authority": "context_only",
        "prophet_flags": dict(PROPHET),
        "unsolicited_instruction_detected": False,
        "records": [
            {
                "log_seq": 1,
                "record_kind": "fact_revision",
                "cluster_grain": "fact_revision",
                "fact_id": FACT_NEMO,
                "document_id": "doc_nvda_nemotron3_20251215",
                "observed_at": "2025-12-15T16:00:00Z",
                "source_available_at": "2025-12-15T15:50:00Z",
                "supersedes_fact_id": None,
                "company_id": CIK,
                "cluster_id": CLUSTER_T3,
                "novelty": "new_magnitude_timing_commitment_counterparty",
                "polarity": "supporting",
                "fact_key": _key_t3(),
                "provenance": {
                    "origin_document_id": "doc_nvda_nemotron3_20251215",
                    "origin_claim_id": "claim_nvda_nemotron3_announce",
                    "root_family_id": "root_nvda_nemotron3",
                    "source_family": "issuer_primary",
                },
                "evidence": _span("doc_nvda_nemotron3_20251215", "dddddddddddddddddddd"),
                "payload_schema": "strategic_product_partnership_event.v1",
                "ci_event_id": abs_ci,
                "owner_claim_ids": ["claim_nvda_nemotron3_announce"],
                "quantity_fingerprint": {"form": "absent"},
                "reports_fact_id": None,
                "linked_fact_ids": [],
                "stated_deadline": abs_deadline,
                "next_expected_observation": {"milestone_name": "artifact_available"},
                "unsolicited_instruction_detected": False,
            },
            {
                "log_seq": 2,
                "record_kind": "fact_revision",
                "cluster_grain": "fact_revision",
                "fact_id": FACT_DEPLOY,
                "document_id": "doc_customer_10k_deploy_20260301",
                "observed_at": "2026-03-01T12:00:00Z",
                "source_available_at": "2026-03-01T11:00:00Z",
                "supersedes_fact_id": None,
                "company_id": CIK,
                "cluster_id": CLUSTER_T3,
                "novelty": "independently_observed_milestone",
                "polarity": "supporting",
                "fact_key": _key_t3_ms("independent_deployment"),
                "provenance": {
                    "origin_document_id": "doc_customer_10k_deploy_20260301",
                    "origin_claim_id": "claim_customer_nemotron_deploy",
                    "root_family_id": "root_customer_deploy_202603",
                    "source_family": "independent_measurement",
                },
                "evidence": _span("doc_customer_10k_deploy_20260301", "eeeeeeeeeeeeeeeeeeee"),
                "payload_schema": "strategic_product_partnership_event.v1",
                "ci_event_id": {
                    "schema": "field_absence.v1",
                    "authority": "context_only",
                    "reason": "not_stated",
                    "subject": "ci_event_id",
                    "detail": "customer mention is not a company_event for this issuer",
                    "missing_fields": ["ci_event_id"],
                },
                "owner_claim_ids": ["claim_customer_nemotron_deploy"],
                "quantity_fingerprint": {"form": "absent"},
                "reports_fact_id": None,
                "linked_fact_ids": [FACT_NEMO],
                "unsolicited_instruction_detected": False,
            },
            {
                "log_seq": 3,
                "record_kind": "thesis_link",
                "cluster_grain": "thesis_link",
                "fact_id": FACT_LINK,
                "document_id": "doc_nvda_nemotron3_20251215",
                "observed_at": "2026-03-01T12:00:01Z",
                "source_available_at": "2026-03-01T11:00:00Z",
                "supersedes_fact_id": None,
                "company_id": CIK,
                "cluster_id": CLUSTER_T3,
                "novelty": "independently_observed_milestone",
                "polarity": "supporting",
                "fact_key": _key_t3(),
                "provenance": {
                    "origin_document_id": "doc_customer_10k_deploy_20260301",
                    "origin_claim_id": "claim_customer_nemotron_deploy",
                    "root_family_id": "root_customer_deploy_202603",
                    "source_family": "independent_measurement",
                },
                "evidence": _span("doc_customer_10k_deploy_20260301", "eeeeeeeeeeeeeeeeeeee"),
                "payload_schema": "strategic_product_partnership_event.v1",
                "ci_event_id": {
                    "schema": "field_absence.v1",
                    "authority": "context_only",
                    "reason": "not_stated",
                    "subject": "ci_event_id",
                    "detail": "thesis link does not mint a company_event",
                    "missing_fields": ["ci_event_id"],
                },
                "owner_claim_ids": [
                    "claim_nvda_nemotron3_announce",
                    "claim_customer_nemotron_deploy",
                ],
                "quantity_fingerprint": {"form": "absent"},
                "reports_fact_id": None,
                "linked_fact_ids": [FACT_NEMO, FACT_DEPLOY],
                "unsolicited_instruction_detected": False,
            },
        ],
    }


def case4_record() -> dict:
    return {
        "log_seq": 4,
        "record_kind": "fact_revision",
        "cluster_grain": "fact_revision",
        "fact_id": FACT_RIVAL,
        "document_id": "doc_rival_deploy_survey_20260615",
        "observed_at": "2026-06-15T09:00:00Z",
        "source_available_at": "2026-06-15T08:30:00Z",
        "supersedes_fact_id": None,
        "company_id": CIK,
        "cluster_id": CLUSTER_T3,
        "novelty": "independently_observed_milestone",
        "polarity": "contrary",
        "fact_key": _key_t3_ms("independent_deployment"),
        "provenance": {
            "origin_document_id": "doc_rival_deploy_survey_20260615",
            "origin_claim_id": "claim_rival_non_nvda_deploy",
            "root_family_id": "root_rival_deploy_202606",
            "source_family": "independent_measurement",
        },
        "evidence": _span("doc_rival_deploy_survey_20260615", "11111111111111111111"),
        "payload_schema": "strategic_product_partnership_event.v1",
        "ci_event_id": {
            "schema": "field_absence.v1",
            "authority": "context_only",
            "reason": "not_stated",
            "subject": "ci_event_id",
            "detail": "survey is not a company_event",
            "missing_fields": ["ci_event_id"],
        },
        "owner_claim_ids": ["claim_rival_non_nvda_deploy"],
        "quantity_fingerprint": {"form": "absent"},
        "reports_fact_id": None,
        "linked_fact_ids": [FACT_NEMO],
        "unsolicited_instruction_detected": False,
    }


def case2_owners() -> T.OwnerSnapshot:
    return T.OwnerSnapshot(
        leaf_payloads={
            FACT_NEMO: {
                "object_name": "Nemotron 3",
                "commitment_status": "announced",
                "negated": False,
                "channel_hint": "strategic_option",
            }
        },
        decision_cut="2025-12-15T16:00:00Z",
    )


def _validate_view(view: dict) -> None:
    schema = T.load_schema("thesis_view.v1.schema.json")
    Draft202012Validator(schema).validate(view)


def _validate_log(log: dict) -> None:
    schema = T.load_schema("fact_log.v1.schema.json")
    Draft202012Validator(schema).validate(log)


# --------------------------------------------------------------------------- section 5 worked cases


def test_case1_nvda_authorization_view() -> None:
    log = case1_log()
    _validate_log(log)
    views = T.F(log, case1_owners(), AS_OF_C1, decision_cut=CUT_C1)
    assert len(views) == 1
    view = views[0]
    _validate_view(view)
    assert view["schema"] == "thesis_view.v1"
    assert view["authority"] == "context_only"
    assert view["prophet_flags"] == PROPHET
    assert view["unsolicited_instruction_detected"] is False
    assert view["company_id"] == CIK
    assert view["original_proposition_fact_id"] == FACT_AUTH
    assert view["decision_cut"] == CUT_C1
    assert view["as_of_utc"] == AS_OF_C1
    assert view["original_proposition"] == {
        "payload_schema": "capital_allocation_event.v1",
        "plain_statement": (
            "Issuer authorized an additional 150 billion dollars of share repurchase, "
            "remaining authorization 235 billion dollars, through fiscal 2028. "
            "Authorization is not execution."
        ),
        "channel_hint": "capital_allocation",
        "commitment_status": "authorized",
        "negated": False,
    }
    assert view["supporting_claim_ids"] == ["claim_nvda_auth_150b", FACT_AUTH]
    assert view["contrary_claim_ids"] == []
    assert view["root_source_families"] == [
        {
            "root_family_id": "root_nvda_auth_20260928",
            "origin_document_id": "doc_nvda_pr_20260928",
            "source_family": "issuer_primary",
            "member_count": 3,
        }
    ]
    assert view["exposure_paths"]["schema"] == "field_absence.v1"
    assert view["exposure_paths"]["subject"] == "exposure_paths"
    assert view["required_assumptions"] == [
        {
            "schema": "field_absence.v1",
            "authority": "context_only",
            "reason": "not_stated",
            "subject": "executed_amount",
            "detail": "authorization packet does not state completed purchases",
            "missing_fields": ["executed_amount"],
        }
    ]
    assert view["current_milestone_evidence"] == [
        {
            "fact_id": FACT_AUTH,
            "milestone_name": "announcement",
            "observed_at": "2026-09-28T14:05:00Z",
            "provenance_group_id": "doc_nvda_pr_20260928",
        }
    ]
    assert view["next_expected_observation"] == {
        "milestone_name": "executed_repurchase",
        "window_start": "2026-09-28T14:00:00Z",
        "window_end": "2028-01-30T00:00:00Z",
    }
    assert view["deadline"] == "2028-01-30T00:00:00Z"
    assert view["weakening_conditions"] == [
        {"code": "missed_stated_deadline", "armed": False, "evidence_fact_ids": []},
        {"code": "expected_observation_absent", "armed": False, "evidence_fact_ids": []},
    ]
    assert view["display"]["what_we_are_watching"] == (
        "actual repurchases and net dilution through the fiscal 2028 window, "
        "not further reprints of the authorization"
    )
    assert view["display"]["windows"] == [
        {
            "label": "stated execution horizon through fiscal 2028",
            "start": "2026-09-28T14:00:00Z",
            "end": "2028-01-30T00:00:00Z",
        }
    ]
    assert view["display"]["plain_status"] == (
        "the source states an authorization. completed purchases are not yet in this "
        "store. operating revenue impact is not established. surprise is unmeasured "
        "without a baseline."
    )
    assert view["live_fact_ids"] == [FACT_AUTH]
    assert view["cluster_ids"] == [CLUSTER_T1]
    assert view["provenance_group_ids"] == ["doc_nvda_pr_20260928"]
    assert view["material_delta_triggers"] == []
    assert view["log_sha256"] == T.canonical_json_sha256(T.parse_fact_log(log))
    assert view["owners_sha256"] == T.canonical_json_sha256(case1_owners().to_dict())
    for key in T.FORBIDDEN_KEYS:
        assert key not in json.dumps(view)


def test_case2_open_model_view() -> None:
    log = case2_log()
    _validate_log(log)
    views = T.F(
        log,
        case2_owners(),
        "2026-03-01T23:59:59Z",
        prior_as_of_utc="2025-12-16T00:00:00Z",
        decision_cut="2025-12-15T16:00:00Z",
    )
    assert len(views) == 1
    view = views[0]
    _validate_view(view)
    assert view["original_proposition_fact_id"] == FACT_NEMO
    assert set(view["live_fact_ids"]) == {FACT_NEMO, FACT_DEPLOY}
    groups = {g["origin_document_id"] for g in view["root_source_families"]}
    assert groups == {"doc_nvda_nemotron3_20251215", "doc_customer_10k_deploy_20260301"}
    assert view["next_expected_observation"]["milestone_name"] == "repeated_active_use"
    names = {m["milestone_name"] for m in view["current_milestone_evidence"]}
    assert "announcement" in names
    assert "independent_deployment" in names
    assert "independently_observed_milestone" in view["material_delta_triggers"]
    assert "new_independent_source" in view["material_delta_triggers"]
    assert "stars" in view["display"]["what_we_are_watching"] or "repeated" in view["display"]["what_we_are_watching"]


def test_case3_correction_supersedes() -> None:
    log = case1_log()
    log = T.append_records(log, [case3_record()])
    _validate_log(log)
    owners = T.OwnerSnapshot(
        leaf_payloads={
            FACT_AUTH: {
                "incremental": 150_000_000_000,
                "remaining": 235_000_000_000,
                "commitment_status": "authorized",
                "channel_hint": "capital_allocation",
                "negated": False,
            },
            FACT_CORR: {
                "incremental": 150_000_000_000,
                "remaining": 210_000_000_000,
                "commitment_status": "authorized",
                "channel_hint": "capital_allocation",
                "negated": False,
            },
        },
        decision_cut=CUT_C1,
    )
    before = T.F(log, owners, "2026-10-01T00:00:00Z", decision_cut=CUT_C1)
    assert before[0]["live_fact_ids"] == [FACT_AUTH]
    after = T.F(
        log,
        owners,
        "2026-10-02T13:00:00Z",
        prior_as_of_utc="2026-10-01T00:00:00Z",
        decision_cut=CUT_C1,
    )
    view = after[0]
    _validate_view(view)
    assert view["original_proposition_fact_id"] == FACT_AUTH
    assert view["live_fact_ids"] == [FACT_CORR]
    assert FACT_AUTH in [r["fact_id"] for r in log["records"]]
    assert "source_correction" in view["material_delta_triggers"]
    assert "changed_numeric_terms" in view["material_delta_triggers"]
    armed = {w["code"]: w["armed"] for w in view["weakening_conditions"]}
    # Legacy scalar-only leaves do not establish compatible quantity terms.
    assert armed.get("source_correction_reduces_magnitude") is False
    assert "source correction" in view["display"]["plain_status"].lower()
    assert "28 September" not in json.dumps(view["display"])
    assert "remaining authorization" not in view["display"]["plain_status"]
    assert "Review the corrected terms" in view["display"]["what_we_are_watching"]


def test_case4_contradiction_absence() -> None:
    log = T.append_records(case2_log(), [case4_record()])
    _validate_log(log)
    views = T.F(
        log,
        case2_owners(),
        "2026-06-15T23:59:59Z",
        prior_as_of_utc="2026-03-02T00:00:00Z",
        decision_cut="2025-12-15T16:00:00Z",
    )
    view = views[0]
    _validate_view(view)
    assert "claim_nvda_nemotron3_announce" in view["supporting_claim_ids"]
    assert "claim_customer_nemotron_deploy" in view["supporting_claim_ids"]
    assert view["contrary_claim_ids"] == ["claim_rival_non_nvda_deploy", FACT_RIVAL]
    assert set(view["material_delta_triggers"]) >= {
        "independently_observed_milestone",
        "new_independent_source",
        "contradiction",
    }
    subjects = {a["subject"] for a in view["required_assumptions"]}
    assert "baseline" in subjects
    assert "does not state which measurement is true" in view["display"]["what_we_are_watching"]


# --------------------------------------------------------------------------- replay / append-only / empty as_of


def test_replay_determinism_and_permuted_input() -> None:
    log = case1_log()
    owners = case1_owners()
    a = T.F(log, owners, AS_OF_C1, decision_cut=CUT_C1)
    b = T.F(log, owners, AS_OF_C1, decision_cut=CUT_C1)
    assert T.canonical_json(list(a)) == T.canonical_json(list(b))
    permuted = copy.deepcopy(log)
    rng = random.Random(0)
    rng.shuffle(permuted["records"])
    c = T.F(permuted, owners, AS_OF_C1, decision_cut=CUT_C1)
    assert T.canonical_json(list(a)) == T.canonical_json(list(c))


def test_append_only_mutation_refused() -> None:
    prior = case1_log()
    cand = copy.deepcopy(prior)
    cand["records"][0]["document_id"] = "doc_mutated"
    with pytest.raises(T.ThesisError) as exc:
        T.check_append_only(prior, cand)
    assert exc.value.code == "APPEND_ONLY_VIOLATION"


def test_append_only_reorder_refused() -> None:
    prior = case1_log()
    cand = copy.deepcopy(prior)
    cand["records"][0], cand["records"][1] = cand["records"][1], cand["records"][0]
    with pytest.raises(T.ThesisError) as exc:
        T.check_append_only(prior, cand)
    assert exc.value.code == "APPEND_ONLY_VIOLATION"


def test_append_only_delete_refused() -> None:
    prior = case1_log()
    cand = copy.deepcopy(prior)
    cand["records"] = cand["records"][:2]
    with pytest.raises(T.ThesisError) as exc:
        T.check_append_only(prior, cand)
    assert exc.value.code == "APPEND_ONLY_VIOLATION"


def test_as_of_earlier_than_every_fact() -> None:
    views = T.F(case1_log(), case1_owners(), "2020-01-01T00:00:00Z", decision_cut="2020-01-01T00:00:00Z")
    assert views == ()
    absence = T.absent_thesis(as_of_utc="2020-01-01T00:00:00Z", company_id=CIK)
    assert absence["schema"] == "field_absence.v1"
    assert absence["reason"] == "not_stated"
    assert absence["subject"] == "thesis_view"
    one = T.project_one(
        case1_log(),
        case1_owners(),
        "2020-01-01T00:00:00Z",
        CIK,
        FACT_AUTH,
        decision_cut="2020-01-01T00:00:00Z",
    )
    assert one["schema"] == "field_absence.v1"


def test_emitted_view_and_log_validate_against_schema() -> None:
    log = T.parse_fact_log(case1_log())
    _validate_log(log)
    views = T.project(log, case1_owners(), AS_OF_C1, decision_cut=CUT_C1)
    for view in views:
        _validate_view(view)
        T.validate_against_schema(view, "thesis_view.v1.schema.json")


def test_jsonl_roundtrip() -> None:
    log = case1_log()
    text = T.serialize_jsonl(log["records"])
    parsed = T.parse_jsonl(text)
    T.validate_log(parsed)
    assert [r["fact_id"] for r in parsed["records"]] == [r["fact_id"] for r in log["records"]]
    whole = T.parse_jsonl(json.dumps(log))
    assert len(whole["records"]) == 3


def test_same_key_non_correction_live_is_latest() -> None:
    log = case1_log()
    extra = copy.deepcopy(log["records"][0])
    extra["log_seq"] = 4
    extra["fact_id"] = "fact_a11c0e00000000000000000a"
    extra["observed_at"] = "2026-09-29T00:00:00Z"
    extra["source_available_at"] = "2026-09-29T00:00:00Z"
    extra["supersedes_fact_id"] = None
    extra["novelty"] = "new_magnitude_timing_commitment_counterparty"
    extra["quantity_fingerprint"] = {"form": "present", "canonical_sha256": CORR_SHA}
    extra["owner_claim_ids"] = ["claim_nvda_auth_new_remaining"]
    extra["document_id"] = "doc_nvda_pr_20260929"
    log2 = T.append_records(log, [extra])
    views = T.F(log2, case1_owners(), "2026-09-29T12:00:00Z", decision_cut=CUT_C1)
    assert views[0]["live_fact_ids"] == ["fact_a11c0e00000000000000000a"]
    assert FACT_AUTH in [r["fact_id"] for r in log2["records"]]


def test_cosmetic_mirror_no_delta() -> None:
    log = case1_log()
    reprint = copy.deepcopy(log["records"][1])
    reprint["log_seq"] = 4
    reprint["fact_id"] = "fact_a11c0e000000000000000012"
    reprint["document_id"] = "doc_wsj_nvda_auth_20260928"
    reprint["observed_at"] = "2026-09-28T15:00:00Z"
    reprint["source_available_at"] = "2026-09-28T14:50:00Z"
    reprint["evidence"] = _span("doc_wsj_nvda_auth_20260928", "dddddddddddddddddddd")
    log2 = T.append_records(log, [reprint])
    v1 = T.F(log, case1_owners(), AS_OF_C1, decision_cut=CUT_C1)[0]
    v2 = T.F(
        log2,
        case1_owners(),
        AS_OF_C1,
        prior_as_of_utc="2026-09-28T14:30:00Z",
        decision_cut=CUT_C1,
    )[0]
    assert v2["material_delta_triggers"] == []
    assert v1["live_fact_ids"] == v2["live_fact_ids"]


def test_pit_correction_replay() -> None:
    log = T.append_records(case1_log(), [case3_record()])
    owners = case1_owners()
    early = T.live_payload(_key_t1(), log, "2026-10-01T00:00:00Z")
    late = T.live_payload(_key_t1(), log, "2026-10-02T13:00:00Z")
    assert early["fact_id"] == FACT_AUTH
    assert late["fact_id"] == FACT_CORR


def test_market_state_change_requires_admitted_owner() -> None:
    log = case1_log()
    owners = case1_owners()
    views = T.F(
        log,
        owners,
        AS_OF_C1,
        prior_as_of_utc="2026-09-27T00:00:00Z",
        prior_owners=owners,
        decision_cut=CUT_C1,
    )
    assert "market_state_change" not in views[0]["material_delta_triggers"]
    with_mkt = T.OwnerSnapshot(
        leaf_payloads=owners.leaf_payloads,
        decision_cut=CUT_C1,
        market_state={"listed": True, "session": "RTH"},
    )
    prior_mkt = T.OwnerSnapshot(
        leaf_payloads=owners.leaf_payloads,
        decision_cut=CUT_C1,
        market_state={"listed": True, "session": "CLOSED"},
    )
    fired = T.F(
        log,
        with_mkt,
        AS_OF_C1,
        prior_as_of_utc="2026-09-27T00:00:00Z",
        prior_owners=prior_mkt,
        decision_cut=CUT_C1,
    )[0]
    assert "market_state_change" in fired["material_delta_triggers"]


def test_fingerprint_numeric_slots_only() -> None:
    payload = {
        "incremental": 150_000_000_000,
        "remaining": 235_000_000_000,
        "blurb": "cosmetic wording does not enter the fingerprint",
    }
    fp = T.quantity_fingerprint(payload, "capital_allocation_event.v1")
    assert fp["form"] == "present"
    expected = T.canonical_json_sha256(
        {"incremental": 150_000_000_000, "remaining": 235_000_000_000}
    )
    assert fp["canonical_sha256"] == expected
    absent = T.quantity_fingerprint({}, "strategic_product_partnership_event.v1")
    assert absent == {"form": "absent"}


def test_assign_polarity_defaults_unclassified() -> None:
    assert T.assign_polarity(False, None) == "unclassified"
    assert T.assign_polarity(True, None) == "contrary"
    assert T.assign_polarity(False, {"form": "owner_span_ref"}) == "contrary"


def test_stripped_fields_at_ingest() -> None:
    raw = case1_log()
    raw["records"][0] = dict(raw["records"][0])
    raw["records"][0]["confidence"] = 0.9
    raw["records"][0]["sentiment"] = "bullish"
    cleaned, stripped = T.strip_forbidden(raw)
    parsed = T.parse_fact_log(raw)
    assert "confidence" not in parsed["records"][0]
    assert "sentiment" not in parsed["records"][0]
    assert "stripped_fields" not in parsed
    assert "confidence" in stripped
    assert "sentiment" in stripped
    assert "confidence" not in cleaned["records"][0]


def test_no_forbidden_key_in_emitted_objects() -> None:
    view = T.F(case1_log(), case1_owners(), AS_OF_C1, decision_cut=CUT_C1)[0]
    blob = T.canonical_json(view)
    for key in T.FORBIDDEN_KEYS:
        assert f'"{key}"' not in blob
    log = T.parse_fact_log(case1_log())
    blob_log = T.canonical_json(log)
    for key in T.FORBIDDEN_KEYS:
        assert f'"{key}"' not in blob_log


def test_dataclasses_to_dict() -> None:
    absence = T.FieldAbsence("x", "y", ("x",)).to_dict()
    assert absence["schema"] == "field_absence.v1"
    fl = T.FactLog(tuple(case1_log()["records"]))
    assert fl.to_dict()["schema"] == "fact_log.v1"
    snap = case1_owners().to_dict()
    assert "leaf_payloads" in snap
    wrapped = T.ThesisView({"schema": "thesis_view.v1"})
    assert wrapped.to_dict()["schema"] == "thesis_view.v1"


# --------------------------------------------------------------------------- CODES: every code asserted exactly


def _one_record_log(**overrides: object) -> dict:
    rec = copy.deepcopy(case1_log()["records"][0])
    rec["log_seq"] = 1
    rec.update(overrides)
    return {
        "schema": "fact_log.v1",
        "authority": "context_only",
        "prophet_flags": dict(PROPHET),
        "unsolicited_instruction_detected": False,
        "records": [rec],
    }


def test_codes_frozenset_contents() -> None:
    assert T.CODES == frozenset(
        {
            "APPEND_ONLY_VIOLATION",
            "LOG_SEQ_INVALID",
            "DUPLICATE_FACT_ID",
            "SUPERSEDES_NOT_FOUND",
            "SUPERSEDES_KEY_MISMATCH",
            "SUPERSEDES_CYCLE",
            "SUPERSEDES_REQUIRED",
            "PIT_CLOCK_VIOLATION",
            "MANIFEST_REPORTS_MISSING",
            "TEXT_SAFE_VIOLATION",
            "SCHEMA_VIOLATION",
            "DECISION_CUT_AFTER_AS_OF",
            "JSONL_PARSE_ERROR",
            "AS_OF_INVALID",
        }
    )


@pytest.mark.parametrize("code", sorted(T.CODES))
def test_every_code_raises_exact_string(code: str) -> None:
    with pytest.raises(T.ThesisError) as exc:
        if code == "APPEND_ONLY_VIOLATION":
            prior = case1_log()
            cand = copy.deepcopy(prior)
            cand["records"] = cand["records"][:1]
            T.check_append_only(prior, cand)
        elif code == "LOG_SEQ_INVALID":
            T.validate_log(_one_record_log(log_seq=7))
        elif code == "DUPLICATE_FACT_ID":
            log = case1_log()
            log["records"][1] = copy.deepcopy(log["records"][0])
            log["records"][1]["log_seq"] = 2
            T.validate_log(log)
        elif code == "SUPERSEDES_NOT_FOUND":
            T.validate_log(
                _one_record_log(
                    novelty="corrected_fact",
                    cluster_grain="fact_revision",
                    record_kind="fact_revision",
                    supersedes_fact_id="fact_ffffffffffffffffffffffff",
                    reports_fact_id=None,
                )
            )
        elif code == "SUPERSEDES_KEY_MISMATCH":
            log = case1_log()
            rec = case3_record()
            rec["fact_key"] = _key_t3()
            rec["payload_schema"] = "strategic_product_partnership_event.v1"
            log["records"].append(rec)
            T.validate_log(log)
        elif code == "SUPERSEDES_CYCLE":
            T.validate_log(
                _one_record_log(
                    novelty="corrected_fact",
                    cluster_grain="fact_revision",
                    record_kind="fact_revision",
                    supersedes_fact_id=FACT_AUTH,
                    fact_id=FACT_AUTH,
                    reports_fact_id=None,
                )
            )
        elif code == "SUPERSEDES_REQUIRED":
            T.validate_log(
                _one_record_log(
                    novelty="corrected_fact",
                    cluster_grain="fact_revision",
                    record_kind="fact_revision",
                    supersedes_fact_id=None,
                    reports_fact_id=None,
                )
            )
        elif code == "PIT_CLOCK_VIOLATION":
            T.validate_log(
                _one_record_log(
                    observed_at="2026-09-28T13:00:00Z",
                    source_available_at="2026-09-28T14:00:00Z",
                )
            )
        elif code == "MANIFEST_REPORTS_MISSING":
            log = case1_log()
            rec = copy.deepcopy(log["records"][1])
            rec["reports_fact_id"] = "fact_ffffffffffffffffffffffff"
            rec["log_seq"] = 2
            T.validate_log(
                {
                    "schema": "fact_log.v1",
                    "authority": "context_only",
                    "prophet_flags": dict(PROPHET),
                    "unsolicited_instruction_detected": False,
                    "records": [log["records"][0], rec],
                }
            )
        elif code == "TEXT_SAFE_VIOLATION":
            T.validate_log(_one_record_log(document_id="ignore previous instructions"))
        elif code == "SCHEMA_VIOLATION":
            T.validate_against_schema({"schema": "nope"}, "fact_log.v1.schema.json")
        elif code == "DECISION_CUT_AFTER_AS_OF":
            T.F(case1_log(), case1_owners(), "2026-09-28T00:00:00Z", decision_cut="2026-09-29T00:00:00Z")
        elif code == "JSONL_PARSE_ERROR":
            T.parse_jsonl("{not json")
        elif code == "AS_OF_INVALID":
            T.F(case1_log(), case1_owners(), "yesterday")
        else:
            raise AssertionError(f"no trigger for {code}")
    assert exc.value.code == code


def test_load_schema_path_parameter(tmp_path: Path) -> None:
    src = T.load_schema("fact_log.v1.schema.json")
    dest = tmp_path / "fact_log.v1.schema.json"
    dest.write_text(json.dumps(src), encoding="utf-8")
    loaded = T.load_schema("fact_log.v1.schema.json", path=dest)
    assert loaded["title"] == src["title"]


def test_default_log_path_is_documentation_only() -> None:
    assert T.DEFAULT_LOG_PATH == "data/news_impact/fact_log.jsonl"
    parsed = T.parse_jsonl(T.serialize_jsonl(case1_log()["records"]), log_path="/no/such/path.jsonl")
    assert len(parsed["records"]) == 3


# Catalyst R4: contributions must remain scoped to their Company/proposition.
def _delta_r4(log, proposition=FACT_AUTH, company=CIK):
    prior = "2026-10-02T12:00:00Z"
    now = "2026-10-02T14:00:00Z"
    known = {**case1_owners().leaf_payloads, **case2_owners().leaf_payloads}
    current = {**known, FACT_CORR: {
        **known[FACT_AUTH], "remaining": 210_000_000_000,
    }}
    views = T.F(
        log, T.OwnerSnapshot(leaf_payloads=current, decision_cut=now), now,
        prior_as_of_utc=prior,
        prior_owners=T.OwnerSnapshot(leaf_payloads=known, decision_cut=prior),
        decision_cut=now,
    )
    return next(v for v in views if v["company_id"] == company
                and v["original_proposition_fact_id"] == proposition)


def _r4_mirror(log_seq=5, *, novelty="new_reporting_of_old_fact", clock="13:10:00"):
    row = copy.deepcopy(case1_log()["records"][1])
    row.update(log_seq=log_seq, fact_id="fact_a11c0e000000000000000012",
               document_id="doc_r4_mirror", novelty=novelty,
               observed_at=f"2026-10-02T{clock}Z",
               source_available_at=f"2026-10-02T{clock}Z",
               evidence=_span("doc_r4_mirror", "dddddddddddddddddddd"))
    return row


@pytest.mark.parametrize("novelty", ["new_reporting_of_old_fact", "commentary"])
@pytest.mark.parametrize("clock", ["12:30:00", "13:10:00"])
def test_material_delta_contributions_survive_known_group_reporting(novelty, clock):
    changed = T.append_records(case1_log(), [case3_record()])
    expected = _delta_r4(changed)["material_delta_triggers"]
    assert {"changed_numeric_terms", "new_independent_source", "source_correction"} <= set(expected)
    combined = T.append_records(changed, [_r4_mirror(novelty=novelty, clock=clock)])
    assert _delta_r4(combined)["material_delta_triggers"] == expected


def _r4_numeric_milestone_log():
    log = case2_log()
    log["records"][1].update(
        observed_at="2026-10-02T13:00:00Z", source_available_at="2026-10-02T12:55:00Z",
        quantity_fingerprint={"form": "present", "canonical_sha256": CORR_SHA},
    )
    log["records"][2].update(
        observed_at="2026-10-02T13:00:01Z", source_available_at="2026-10-02T12:55:00Z",
    )
    T.validate_log(log)
    return log


@pytest.mark.parametrize("other_company", [False, True])
def test_material_delta_numeric_terms_cannot_leak_between_propositions(other_company):
    log = _r4_numeric_milestone_log()
    before = _delta_r4(log, FACT_NEMO)["material_delta_triggers"]
    assert "independently_observed_milestone" in before
    assert "changed_numeric_terms" not in before
    unrelated = copy.deepcopy(case1_log()["records"][0])
    unrelated.update(log_seq=4, observed_at="2026-10-02T13:05:00Z")
    if other_company:
        unrelated["company_id"] = "cik:0000320193"
        unrelated["fact_key"]["company_id"] = unrelated["company_id"]
    combined = T.append_records(log, [unrelated])
    assert _delta_r4(combined, FACT_NEMO)["material_delta_triggers"] == before


@pytest.mark.parametrize("cosmetic", [True, False])
def test_material_delta_milestone_numeric_support_uses_only_eligible_attached_records(cosmetic):
    log = _r4_numeric_milestone_log()
    row = copy.deepcopy(log["records"][0])
    row.update(log_seq=4, fact_id="fact_b22d1f000000000000000009",
               observed_at="2026-10-02T12:30:00Z", source_available_at="2026-10-02T12:25:00Z",
               novelty="new_reporting_of_old_fact" if cosmetic
                       else "new_magnitude_timing_commitment_counterparty",
               quantity_fingerprint={"form": "present", "canonical_sha256": EMPTY_SHA})
    if cosmetic:
        # Owner schema admits cosmetic reporting as a manifestation, never as
        # a fact_revision. Preserve that distinction in this public-path case.
        row.update(record_kind="manifestation", cluster_grain="article_manifestation",
                   reports_fact_id=FACT_NEMO)
    out = _delta_r4(T.append_records(log, [row]), FACT_NEMO)
    assert "independently_observed_milestone" in out["material_delta_triggers"]
    assert ("changed_numeric_terms" in out["material_delta_triggers"]) is (not cosmetic)


def test_material_delta_known_group_reporting_alone_stays_nonmaterial():
    out = _delta_r4(T.append_records(case1_log(), [_r4_mirror(log_seq=4)]))
    assert out["material_delta_triggers"] == []
