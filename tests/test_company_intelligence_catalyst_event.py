from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from engine.company_intelligence.contracts import ContractError, canonical_json_sha256
from engine.company_intelligence.event_id_adapter import AliasError, canonical_event_id_variant
from engine.company_intelligence.events import (
    SOURCE_EVENT_AUTHORITY,
    canonical_source_event_id,
    project_catalyst_event,
)
from engine.company_intelligence.identity import company_id_for_cik
from engine.biocatalyst.company_event_adapter import project_company_event_input


COMPANY = company_id_for_cik(1365916)
CIK = "0001365916"
CUTOFF = "2026-09-06T12:00:00Z"


def _timing(**overrides):
    value = {
        "state": "consistent",
        "source_class": "issuer_guided",
        "lower_date": "2026-12-01",
        "upper_date": "2026-12-01",
        "precision": "day",
        "source_timezone": None,
        "source_wording": "expects topline data in December 2026",
        "evidence_refs": ["ev_public_1"],
    }
    value.update(overrides)
    return value


def _event(**overrides):
    args = {
        "company_id": COMPANY,
        "issuer_cik": CIK,
        "source_namespace": "issuer_disclosure",
        "native_event_key": "doc_2026_08_18#claim/lucidity_readout_guidance",
        "event_family": "issuer_readout_guidance",
        "revision_ref": "doc_2026_08_18:r1",
        "revision_is_current": True,
        "occurrence": "uncorroborated",
        "timing": _timing(),
        "source_available_at": "2026-08-18T11:30:00-04:00",
        "observed_at": "2026-08-18T15:31:00Z",
        "document_refs": ["doc_2026_08_18:r1"],
        "public_evidence": [],
        "asset_mentions": [],
        "relationship_claims": [],
        "generation_cutoff": CUTOFF,
    }
    args.update(overrides)
    return project_catalyst_event(**args)


def test_source_event_id_is_full_sha256_over_exact_owner_identity() -> None:
    identity = {
        "company_id": COMPANY,
        "source_namespace": "issuer_disclosure",
        "native_event_key": "doc_2026_08_18#claim/lucidity_readout_guidance",
        "event_family": "issuer_readout_guidance",
    }
    expected = "evt_source_" + canonical_json_sha256(identity)
    actual = canonical_source_event_id(**identity)
    assert actual == expected
    assert len(actual) == len("evt_source_") + 64


def test_correction_changes_revision_not_source_event_identity() -> None:
    first = _event()
    corrected = _event(
        revision_ref="doc_2026_09_01:r2",
        timing=_timing(lower_date="2027-01-01", upper_date="2027-03-31", precision="quarter"),
        source_available_at="2026-09-01T08:00:00-04:00",
        observed_at="2026-09-01T12:02:00Z",
    )
    assert corrected["event_id"] == first["event_id"]
    assert corrected["revision_ref"] != first["revision_ref"]
    assert corrected["timing"] != first["timing"]


def test_first_slice_rejects_unknown_namespace_and_unknown_family() -> None:
    with pytest.raises(ContractError, match="source_namespace"):
        canonical_source_event_id(
            COMPANY, "sec_magic", "accession#claim", "issuer_readout_guidance"
        )
    with pytest.raises(ContractError, match="event_family"):
        canonical_source_event_id(
            COMPANY, "issuer_disclosure", "doc#claim", "probable_approval"
        )


def test_future_schedule_is_valid_but_does_not_become_occurrence() -> None:
    event = _event()
    assert event["timing"]["lower_date"] == "2026-12-01"
    assert event["occurrence"] == "uncorroborated"
    assert event["observed_at"] < CUTOFF


def test_civil_date_timing_stays_a_date_and_no_midnight_is_invented() -> None:
    event = _event(timing=_timing(source_timezone=None, precision="day"))
    assert event["timing"]["lower_date"] == "2026-12-01"
    assert event["timing"]["upper_date"] == "2026-12-01"
    assert "T00:00:00" not in event["timing"]["lower_date"]
    assert event["timing"]["source_timezone"] is None


def test_knowledge_after_generation_cutoff_is_refused() -> None:
    with pytest.raises(ContractError, match="cutoff"):
        _event(observed_at="2026-09-06T12:00:01Z")
    with pytest.raises(ContractError, match="cutoff"):
        _event(source_available_at="2026-09-06T12:00:01Z", observed_at="2026-09-06T12:00:02Z")


def test_date_only_or_naive_knowledge_clock_is_refused_not_guessed() -> None:
    with pytest.raises(ContractError, match="explicit timezone"):
        _event(source_available_at="2026-08-18")
    with pytest.raises(ContractError, match="explicit timezone"):
        _event(observed_at="2026-08-18T15:31:00")


def test_port_is_closed_and_source_fact_authority_cannot_be_upgraded() -> None:
    event = _event()
    assert set(event) == {
        "contract_id", "schema_version", "event_id", "company_id", "issuer_cik",
        "event_family", "native_identity", "revision_ref", "revision_is_current",
        "occurrence", "timing", "source_available_at", "observed_at", "document_refs",
        "public_evidence", "asset_mentions", "relationship_claims", "authority",
    }
    assert event["contract_id"] == "company_catalyst_event.v1"
    assert event["schema_version"] == "1.0.0"
    assert event["authority"] == SOURCE_EVENT_AUTHORITY
    assert event["authority"]["decision_authority"] is False
    assert "originate_signal" in event["authority"]["forbidden_uses"]
    assert "size_position" in event["authority"]["forbidden_uses"]

    tampered = deepcopy(event)
    tampered["authority"]["decision_authority"] = True
    from engine.company_intelligence.contracts import validate_company_catalyst_event
    with pytest.raises(ContractError, match="authority"):
        validate_company_catalyst_event(tampered, generation_cutoff=CUTOFF)


def test_timing_object_is_closed_and_reversed_bounds_are_refused() -> None:
    with pytest.raises(ContractError, match="timing"):
        _event(timing={**_timing(), "confidence": 0.8})
    with pytest.raises(ContractError, match="timing"):
        _event(timing=_timing(lower_date="2027-04-01", upper_date="2027-03-31", precision="window"))


def test_company_and_issuer_cik_must_be_the_same_owner_identity() -> None:
    with pytest.raises(ContractError, match="issuer_cik"):
        _event(issuer_cik="0000320193")


def test_event_id_adapter_names_fiscal_and_source_variants_explicitly() -> None:
    assert canonical_event_id_variant("evt_cik0000320193_2026q3_results") == "fiscal"
    assert canonical_event_id_variant(_event()["event_id"]) == "source"
    with pytest.raises(AliasError):
        canonical_event_id_variant("evt_arbitrary_string")


def test_bio_consumer_preserves_owner_identity_and_does_not_reallocate_event() -> None:
    owner = _event()
    consumed = project_company_event_input(owner, generation_cutoff=CUTOFF)
    assert consumed["event_fact_ref"] == owner["event_id"]
    assert consumed["event_family"] == owner["event_family"]
    assert consumed["event_revision_ref"] == owner["revision_ref"]
    assert consumed["revision_is_current"] is True
    assert consumed["occurrence"] == "uncorroborated"
    assert consumed["timing"] == owner["timing"]
    assert consumed["company_id"] == owner["company_id"]
    assert consumed["issuer_cik"] == owner["issuer_cik"]
    assert consumed["authority"] == SOURCE_EVENT_AUTHORITY

from datetime import date
from lib.dataos.identity import IssuerMaster, VendorAliasTable
from engine.biocatalyst.company_event_adapter import resolve_current_event_identity


def _master(rows):
    return IssuerMaster.from_records(rows)


def _security_row(security_id, issuer_id, cik, listing_key, **extra):
    return {
        "security_id": security_id,
        "issuer_id": issuer_id,
        "issuer_state": "RESOLVED",
        "issuer_cik": cik,
        "listing_key": listing_key,
        "security_state": extra.get("security_state"),
        "superseded_by": extra.get("superseded_by"),
    }


def _aliases(rows):
    return VendorAliasTable.from_records(rows)


def test_bio_current_identity_keeps_all_active_share_classes_without_preference() -> None:
    owner = _event()
    master = _master([
        _security_row("SEC:US-XNAS-ABCA", "ISS:US-XNAS-ABCA", CIK, "US-XNAS-ABCA"),
        _security_row("SEC:US-XNAS-ABCB", "ISS:US-XNAS-ABCA", CIK, "US-XNAS-ABCB"),
    ])
    aliases = _aliases([
        {"vendor": "store", "vendor_symbol": "ABCA", "security_id": "SEC:US-XNAS-ABCA", "valid_from": None, "valid_to": None},
        {"vendor": "store", "vendor_symbol": "ABCB", "security_id": "SEC:US-XNAS-ABCB", "valid_from": None, "valid_to": None},
    ])
    identity = resolve_current_event_identity(
        owner,
        issuer_master=master,
        alias_table=aliases,
        identity_cut_date=date(2026, 9, 6),
        identity_observed_at="2026-09-06T10:00:00Z",
        generation_cutoff=CUTOFF,
    )
    assert identity["state"] == "resolved"
    assert identity["identity_scope"] == "current_only"
    assert len(identity["issuers"]) == 1
    assert [row["security_id"] for row in identity["issuers"][0]["securities"]] == [
        "SEC:US-XNAS-ABCA", "SEC:US-XNAS-ABCB"
    ]
    assert [row["display_symbol"] for row in identity["issuers"][0]["securities"]] == ["ABCA", "ABCB"]
    assert "preferred_security_id" not in identity
    assert "preferred" not in identity["issuers"][0]


def test_bio_current_identity_keeps_security_when_display_symbol_is_missing() -> None:
    owner = _event()
    master = _master([
        _security_row("SEC:US-XNYS-ABC", "ISS:US-XNYS-ABC", CIK, "US-XNYS-ABC"),
    ])
    identity = resolve_current_event_identity(
        owner,
        issuer_master=master,
        alias_table=_aliases([]),
        identity_cut_date=date(2026, 9, 6),
        identity_observed_at="2026-09-06T10:00:00Z",
        generation_cutoff=CUTOFF,
    )
    security = identity["issuers"][0]["securities"][0]
    assert security["security_id"] == "SEC:US-XNYS-ABC"
    assert security["display_symbol"] is None
    assert security["state"] == "active"


def test_bio_current_identity_distinguishes_unresolved_and_ambiguous_cik() -> None:
    owner = _event()
    unresolved = resolve_current_event_identity(
        owner,
        issuer_master=_master([]),
        alias_table=_aliases([]),
        identity_cut_date=date(2026, 9, 6),
        identity_observed_at="2026-09-06T10:00:00Z",
        generation_cutoff=CUTOFF,
    )
    assert unresolved["state"] == "unresolved"
    assert unresolved["issuers"] == []

    master = _master([
        _security_row("SEC:US-XNAS-A", "ISS:US-XNAS-A", CIK, "US-XNAS-A"),
        _security_row("SEC:US-XNYS-B", "ISS:US-XNYS-B", CIK, "US-XNYS-B"),
    ])
    ambiguous = resolve_current_event_identity(
        owner,
        issuer_master=master,
        alias_table=_aliases([]),
        identity_cut_date=date(2026, 9, 6),
        identity_observed_at="2026-09-06T10:00:00Z",
        generation_cutoff=CUTOFF,
    )
    assert ambiguous["state"] == "ambiguous"
    assert [row["issuer_id"] for row in ambiguous["issuers"]] == ["ISS:US-XNAS-A", "ISS:US-XNYS-B"]


def test_bio_current_identity_refuses_future_identity_observation() -> None:
    with pytest.raises(ContractError, match="identity_observed_at"):
        resolve_current_event_identity(
            _event(),
            issuer_master=_master([]),
            alias_table=_aliases([]),
            identity_cut_date=date(2026, 9, 6),
            identity_observed_at="2026-09-06T12:00:01Z",
            generation_cutoff=CUTOFF,
        )


def test_company_catalyst_event_schema_mirrors_runtime_contract() -> None:
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator

    path = Path(__file__).resolve().parents[1] / "contracts/company_intelligence/company_catalyst_event.v1.schema.json"
    schema = json.loads(path.read_text())
    validator = Draft202012Validator(schema)
    event = _event()
    validator.validate(event)

    bad = deepcopy(event)
    bad["native_identity"]["source_namespace"] = "unapproved_source"
    errors = list(validator.iter_errors(bad))
    assert errors

    bad = deepcopy(event)
    bad["authority"]["decision_authority"] = True
    errors = list(validator.iter_errors(bad))
    assert errors
