"""Dependency-binding tests for the synthetic Industrials T01 corpus."""

from __future__ import annotations

import pytest

from engine.company_intelligence.financial_dossier import DELIVERY_INPUT_VALIDATOR_VERSION
from tests.industrials_result_cash_helpers import (
    FIXTURE_NAMES,
    case,
    cell,
    comparison,
    publication_harness,
)


REQUIRED_FIXTURES = {
    "service_net_gross",
    "paired_expense_income",
    "cash_quarter_vs_half",
    "segment_recast",
    "same_number_two_headers",
    "preliminary_final",
    "filing_later",
    "both_basis_unknown",
    "source_only",
    "negative_cash",
    "mixed_sector_generation",
    "warm_rights_revoked",
    "logout_late_response",
    "ordinary_refresh_outage",
    "shared_query",
    "shared_owner_bundle",
    "foundation_only_proof",
}


def test_ind_sf07():
    from tests.industrials_result_cash_helpers import case
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs
    result = validate_delivery_inputs(case('source_only'))
    assert result['live_admission'] == 'refused'
    assert result['research_usable'] is True
    assert 'accepted_binding_missing' in result['reasons']


def test_every_required_fixture_is_synthetic() -> None:
    assert REQUIRED_FIXTURES == FIXTURE_NAMES
    for name in sorted(REQUIRED_FIXTURES):
        assert case(name)["synthetic"] is True


def test_cell_requires_decimal_text() -> None:
    assert cell("12.3")["value"] == "12.3"
    with pytest.raises(TypeError):
        cell(12.3)
    with pytest.raises(TypeError):
        cell(True)


def test_comparison_contract_and_purpose_guard() -> None:
    first = cell("1", owner_ref="synthetic:cell:first")
    second = cell("2", owner_ref="synthetic:cell:second")
    receipt = comparison("same_period", [first, second])
    assert receipt["operand_refs"] == ["synthetic:cell:first", "synthetic:cell:second"]
    assert set(receipt["checked"]) == {
        "basis",
        "currency",
        "scale",
        "duration",
        "perimeter",
        "definition",
        "source_mode",
    }
    with pytest.raises(ValueError):
        comparison("unknown_purpose", [first])


def test_foundation_only_proof_negative_state() -> None:
    proof = case("foundation_only_proof")
    assert proof["semiconductor_accepted"] is True
    assert proof["industrials_witnesses"] == []
    assert proof["industrials_accepted"] is False


def test_route_unbound_client_causes_no_read() -> None:
    harness = publication_harness()
    assert harness.read_count == 0
    response = harness.client(entitled=False).get("anything")
    assert response == {"status": "unavailable", "reason": "route_unbound", "status_code": None}
    assert harness.read_count == 0


def test_publish_binds_owner_entry_points(tmp_path) -> None:
    from tests.industrials_result_cash_helpers import publication_harness

    harness = publication_harness()
    before = harness.read_count
    result = harness.publish({}, stage_dir=tmp_path)
    assert result["status"] == "ok"
    assert result["generation_id"].startswith("earnpriv_")
    assert result["pointer"]["generation_id"] == result["generation_id"]
    assert result["read_count"] > before


def test_unknown_delivery_input_key_refused() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    payload = case("source_only")
    payload["unexpected"] = True
    result = validate_delivery_inputs(payload)
    assert DELIVERY_INPUT_VALIDATOR_VERSION == "v1"
    assert result["live_admission"] == "refused"
    assert "unknown_field:unexpected" in result["reasons"]


def test_caller_authored_k1_join_refused() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    payload = case("source_only")
    payload["cross_subject_join"] = {"claimed_binding": "caller-authored"}
    result = validate_delivery_inputs(payload)
    assert result["live_admission"] == "refused"
    assert "unsupported_cross_subject_join" in result["reasons"]


def test_unregistered_realistic_cik_is_not_identity() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    payload = case("source_only")
    payload["identity"] = {"company_id": "synthetic:northgate", "external_ids": {"cik": "00009876541"}}
    result = validate_delivery_inputs(payload)
    assert result["live_admission"] == "refused"
    assert "identity_unresolved" in result["reasons"]


def test_realistic_cik_with_unknown_pair_is_identity_not_registered() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs
    from tests.industrials_result_cash_helpers import issuer_registry

    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000320193"},
    }
    result = validate_delivery_inputs(payload, registry=issuer_registry())
    assert result["live_admission"] == "refused"
    identity = result["bindings"]["identity"]
    assert identity["status"] == "unresolved"
    assert identity["reason"] == "identity_not_registered"


def test_missing_registry_resolves_no_identity() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    result = validate_delivery_inputs(payload)
    assert result["bindings"]["identity"]["status"] == "unresolved"
    assert result["bindings"]["identity"]["reason"] == "identity_not_registered"


def test_owner_ref_with_foreign_namespace_is_refused() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    payload = case("source_only")
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "foreign:thing:registered",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    result = validate_delivery_inputs(payload)
    assert result["live_admission"] == "refused"
    release = result["bindings"]["release_binding"]
    assert release["status"] == "unavailable"
    assert release["reason"] == "owner_namespace_unregistered"


def test_uppercase_digest_is_digest_malformed() -> None:
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    payload = case("source_only")
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "A" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    result = validate_delivery_inputs(payload)
    assert result["live_admission"] == "refused"
    release = result["bindings"]["release_binding"]
    assert release["status"] == "unavailable"
    assert release["reason"] == "digest_malformed"
