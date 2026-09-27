"""Dependency-binding tests for the synthetic Industrials T01 corpus."""

from __future__ import annotations

import pytest

from engine.company_intelligence.financial_dossier import DELIVERY_INPUT_VALIDATOR_VERSION
from tests.industrials_result_cash_helpers import (
    FIXTURE_NAMES,
    case,
    cell,
    comparison,
    issuer_registry,
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


def _validate(payload, *, registry=None, research_hosts=None):
    """Helper that always passes the test-only research-host policy.

    T05/T06 will replace this with the real host policy supplied by the
    ranking/gating programs.
    """
    from engine.company_intelligence.financial_dossier import validate_delivery_inputs

    if research_hosts is None:
        research_hosts = frozenset({"example.invalid"})
    return validate_delivery_inputs(
        payload,
        registry=registry,
        research_hosts=research_hosts,
    )


def test_ind_sf07():
    from tests.industrials_result_cash_helpers import case
    result = _validate(case('source_only'))
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


def test_run_refresh_binds_acquire_results_filing_with_ordinary_refresh_outage() -> None:
    from tests.industrials_result_cash_helpers import publication_harness

    harness = publication_harness()
    result = harness.run_refresh({}, fail_sources=["ordinary_refresh_outage"])
    assert result["status"] == "unavailable"
    assert result["reason"] == "refresh_source_failed"
    assert result["source"] == "ordinary_refresh_outage"


def test_run_refresh_empty_fail_sources_returns_owner_ok_shape() -> None:
    """N3 (T01 round-5): the seam's own shape, not the seam-unbound refusal.

    With ``fail_sources=()`` the harness must serve the SEC submissions +
    archive + exhibit URLs that ``acquire_results_filing`` reaches for the
    synthetic CIK, and the seam must return every field the owner publishes
    on a real run — ``cik``, ``accession``, ``form``, ``filing_date``,
    ``acceptance_datetime``, ``report_date``, ``exhibit_url``, ``items``.
    """
    harness = publication_harness()
    result = harness.run_refresh({})
    assert result["status"] == "ok"
    for field in (
        "cik",
        "accession",
        "form",
        "filing_date",
        "acceptance_datetime",
        "report_date",
        "exhibit_url",
        "items",
    ):
        assert field in result, (field, sorted(result))
    assert result["cik"] == "0000987654"
    assert result["accession"] == "0000987654-26-000001"
    assert result["form"] == "8-K"
    # The seam constructs the exhibit URL as
    #   f"{archive_base}/{filename}" = https://www.sec.gov/Archives/edgar/data/987654/<acc_nodash>/synthetic-exhibit.htm
    # from the SEC submissions primaryDocument field; the harness serves any
    # URL ending with that filename, so the returned URL is the live archive
    # URL, not a re-derivation of the input document URL.
    assert result["exhibit_url"].endswith("/synthetic-exhibit.htm")


def test_run_refresh_fail_sources_is_causal_not_coincidental() -> None:
    """N3 (T01 round-5): a fail_source name causes the typed refusal; deleting
    the entry flips the result to the owner's ok shape on the very next call.

    The OLD harness returned ``refresh_source_failed`` because the seam's
    archive SGML map was empty — not because the named source failed. This
    test pins the new contract: the same harness instance, same fixtures,
    only the ``fail_sources`` argument changes between the two assertions.
    """
    harness = publication_harness()

    refused = harness.run_refresh({}, fail_sources=["ordinary_refresh_outage"])
    assert refused["status"] == "unavailable"
    assert refused["reason"] == "refresh_source_failed"
    assert refused["source"] == "ordinary_refresh_outage"
    assert "503" in refused["detail"], refused

    ok = harness.run_refresh({}, fail_sources=[])
    assert ok["status"] == "ok", ok
    assert ok["cik"] == "0000987654"
    assert ok["accession"] == "0000987654-26-000001"
    assert ok["exhibit_url"].endswith("/synthetic-exhibit.htm")


def test_top_level_refusal_reasons_are_closed_set_or_unknown_field() -> None:
    from engine.company_intelligence.financial_dossier import (
        DELIVERY_REFUSAL_REASONS,
        validate_delivery_inputs,
    )
    from tests.industrials_result_cash_helpers import issuer_registry

    registry = issuer_registry()
    # Walk every fixture plus a few hand-rolled payloads to exercise every code path.
    fixtures = [
        case(name) for name in sorted(__import__("tests.industrials_result_cash_helpers", fromlist=["FIXTURE_NAMES"]).FIXTURE_NAMES)
    ]
    payloads: list[dict] = list(fixtures)
    # malformed identity (missing fields)
    payloads.append({"synthetic": True, "identity": {}, "release_binding": None, "private_binding": None})
    # identity_not_registered (well-formed but pair not in registry)
    not_registered = case("source_only")
    not_registered["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000320193"},
    }
    payloads.append(not_registered)
    for payload in payloads:
        result = _validate(payload, registry=registry)
        for reason in result["reasons"]:
            assert reason in DELIVERY_REFUSAL_REASONS or reason.startswith("unknown_field:"), (
                f"unrecognized top-level reason: {reason!r}"
            )


def test_registered_pair_with_accepted_bindings_is_admissible() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
        "rights_state": "public_primary",
    }
    payload["cross_subject_join"] = None
    result = _validate(payload, registry=issuer_registry())
    assert result["live_admission"] == "admissible"
    assert result["reasons"] == []


def test_wellformed_cik_outside_synthetic_namespace_is_unresolved() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "acme:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    result = _validate(payload, registry=issuer_registry())
    assert "identity_unresolved" in result["reasons"]
    identity = result["bindings"]["identity"]
    assert identity["status"] == "unresolved"
    assert identity["reason"] == "identity_not_registered"


def test_eleven_digit_cik_fails_length_check() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "00009876541"},
    }
    result = _validate(payload, registry=issuer_registry())
    assert "identity_unresolved" in result["reasons"]
    identity = result["bindings"]["identity"]
    assert identity["reason"] == "identity_unresolved"


def test_unknown_delivery_input_key_refused() -> None:
    payload = case("source_only")
    payload["unexpected"] = True
    result = _validate(payload)
    assert DELIVERY_INPUT_VALIDATOR_VERSION == "v1"
    assert result["live_admission"] == "refused"
    assert "unknown_field:unexpected" in result["reasons"]


def test_caller_authored_k1_join_refused() -> None:
    payload = case("source_only")
    payload["cross_subject_join"] = {"claimed_binding": "caller-authored"}
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    assert "unsupported_cross_subject_join" in result["reasons"]


def test_unregistered_realistic_cik_is_not_identity() -> None:
    # Renamed in step 5: this exercises the CIK length boundary (11 digits fail).
    # The dedicated length check lives in test_eleven_digit_cik_fails_length_check.
    payload = case("source_only")
    payload["identity"] = {"company_id": "synthetic:northgate", "external_ids": {"cik": "00009876541"}}
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    assert "identity_unresolved" in result["reasons"]


def test_realistic_cik_with_unknown_pair_is_identity_not_registered() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000320193"},
    }
    result = _validate(payload, registry=issuer_registry())
    assert result["live_admission"] == "refused"
    identity = result["bindings"]["identity"]
    assert identity["status"] == "unresolved"
    assert identity["reason"] == "identity_not_registered"


def test_registry_generator_is_materialized_once_no_contradiction() -> None:
    """N4 (T01 round-5): a generator registry must not contradict itself.

    The OLD harness materialized ``frozenset(registry)`` inside
    ``_check_identity`` — every call after the first exhausted the generator
    and the second ``bindings.identity`` read answered
    ``identity_not_registered`` even though the FIRST identity read had
    answered ``resolved``. Pin the new contract: the registry is materialized
    ONCE at entry, so a generator caller observes the SAME answer in both
    ``live_admission`` and ``bindings.identity``.
    """
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    payload["release_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:release:candidate",
        "revision": "r1",
        "digest": "0" * 64,
    }
    payload["private_binding"] = {
        "status": "accepted",
        "owner_ref": "synthetic:private:candidate",
        "revision": "r1",
        "digest": "0" * 64,
        "rights_state": "public_primary",
    }

    registry = iter(list(issuer_registry()))  # iterator, single-pass
    result = _validate(payload, registry=registry)

    assert result["live_admission"] == "admissible", result
    assert result["bindings"]["identity"]["status"] == "resolved", result["bindings"]
    # No contradiction: identity is resolved AND live_admission is admissible.
    assert "identity_unresolved" not in result["reasons"]


def test_missing_registry_resolves_no_identity() -> None:
    payload = case("source_only")
    payload["identity"] = {
        "company_id": "synthetic:northgate",
        "external_ids": {"cik": "0000987654"},
    }
    result = _validate(payload)
    assert result["bindings"]["identity"]["status"] == "unresolved"
    assert result["bindings"]["identity"]["reason"] == "identity_not_registered"


def test_owner_ref_with_foreign_namespace_is_refused() -> None:
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
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    release = result["bindings"]["release_binding"]
    assert release["status"] == "unavailable"
    assert release["reason"] == "owner_namespace_unregistered"


def test_uppercase_digest_is_digest_malformed() -> None:
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
    result = _validate(payload)
    assert result["live_admission"] == "refused"
    release = result["bindings"]["release_binding"]
    assert release["status"] == "unavailable"
    assert release["reason"] == "digest_malformed"
