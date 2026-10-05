from __future__ import annotations

import json

from engine.institutional_census.catalog import (
    PublishedCatalogGeneration,
    prepare_catalog_generation,
)
from engine.institutional_census.k3e_projection import project_reported_holding


def _generation(*, quantity="125000", quantity_type="SH", published_at="2026-05-16T12:00:00Z"):
    accession = "0000000001-26-000001"
    prepared = prepare_catalog_generation(
        report_period="2026-03-31",
        source_cutoff_at="2026-05-16T10:00:00Z",
        published_at=published_at,
        producer_version="institutional-census.test",
        filings=[
            {
                "accession": accession,
                "filer_cik": "0000000001",
                "filer_name": "Example Manager",
                "form": "13F-HR",
                "filing_date": "2026-05-15",
                "accepted_at": "2026-05-15T20:30:00Z",
                "report_period": "2026-03-31",
                "report_type": "13F HOLDINGS REPORT",
                "is_amendment": False,
                "lineage_state": "ORIGINAL",
                "confidential_omitted": False,
                "source_receipt_id": "i13fraw_cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "raw_sha256": "a" * 64,
                "first_seen_at": "2026-05-15T20:31:00Z",
                "retained_at": "2026-05-15T20:32:00Z",
                "parser_version": "parser.v1",
                "quality_state": "VERIFIED",
            }
        ],
        holdings=[
            {
                "accession": accession,
                "infotable_sk": 7,
                "name_of_issuer": "APPLE INC",
                "title_of_class": "COM",
                "cusip": "037833100",
                "figi": "BBG000B9XRY4",
                "value_reported": "24500000",
                "value_unit": "USD_THOUSANDS",
                "value_usd": 24500000000,
                "ssh_prn_amt": quantity,
                "ssh_prn_type": quantity_type,
                "put_call": None,
                "investment_discretion": "SOLE",
                "row_hash": "b" * 64,
            }
        ],
        source_receipt_ids=["i13fraw_cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"],
        coverage={"fixture": True},
    )
    return PublishedCatalogGeneration(
        manifest=prepared.manifest,
        payloads=prepared.payloads,
        filings=prepared.filings,
        holdings=prepared.holdings,
        manager_relationships=prepared.manager_relationships,
    )


def test_projection_preserves_as_filed_row_and_owner_generation_without_positioning_claim():
    generation = _generation()
    out = project_reported_holding(
        generation,
        accession="0000000001-26-000001",
        infotable_sk=7,
        decision_cutoff="2026-05-17T00:00:00Z",
    )

    assert out["schema"] == "institutional_13f.k3e_reported_holding_context.v1"
    assert out["valid"] is True
    assert out["state"] == "AVAILABLE_UNQUALIFIED"
    assert out["owner"] == "engine.institutional_census"
    assert out["authority"] == "descriptive_context_only"
    assert out["financial_influence"] is False
    assert out["k3e_admissible"] is False

    assert out["generation"]["generation_id"] == generation.generation_id
    assert out["generation"]["report_period"] == "2026-03-31"
    assert out["generation"]["source_cutoff_at"] == "2026-05-16T10:00:00Z"
    assert out["generation"]["published_at"] == "2026-05-16T12:00:00Z"

    assert out["filing"]["accession"] == "0000000001-26-000001"
    assert out["filing"]["filer_cik"] == "0000000001"
    assert out["filing"]["accepted_at"] == "2026-05-15T20:30:00Z"
    assert out["filing"]["source_receipt_id"] == "i13fraw_cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    assert out["filing"]["raw_sha256"] == "a" * 64

    assert out["holding"]["infotable_sk"] == 7
    assert out["holding"]["row_hash"] == "b" * 64
    assert out["holding"]["cusip"] == "037833100"
    assert out["holding"]["figi"] == "BBG000B9XRY4"
    assert out["holding"]["quantity"] == {"value": "125000", "type": "SH"}
    assert out["holding"]["reported_value"] == {
        "source_value": "24500000",
        "source_unit": "USD_THOUSANDS",
        "normalized_value_usd": 24500000000,
    }

    assert out["interpretation"]["class"] == "DELAYED_REPORTED_HOLDING_CONTEXT"
    assert out["interpretation"]["is_current_ownership"] is False
    assert out["interpretation"]["is_flow"] is False
    assert out["interpretation"]["is_intent"] is False
    assert out["interpretation"]["is_conviction"] is False

    assert set(out["qualification"]["missing"]) == {
        "canonical_security_resolution_receipt",
        "source_use_receipt",
    }


def test_projection_refuses_generation_not_published_by_decision_cutoff():
    out = project_reported_holding(
        _generation(),
        accession="0000000001-26-000001",
        infotable_sk=7,
        decision_cutoff="2026-05-16T11:59:59Z",
    )

    assert out["valid"] is False
    assert out["state"] == "UNAVAILABLE"
    assert "GENERATION_NOT_AVAILABLE_AT_CUTOFF" in out["refusals"]
    assert out["holding"] is None
    assert out["k3e_admissible"] is False


def test_projection_missing_primary_key_is_typed_absence_not_zero():
    out = project_reported_holding(
        _generation(),
        accession="0000000001-26-000001",
        infotable_sk=999,
        decision_cutoff="2026-05-17T00:00:00Z",
    )

    assert out["valid"] is False
    assert out["state"] == "UNAVAILABLE"
    assert "HOLDING_ROW_NOT_FOUND" in out["refusals"]
    assert out["holding"] is None


def test_missing_quantity_type_preserves_raw_absence_without_inventing_normalized_quantity():
    out = project_reported_holding(
        _generation(quantity_type=None),
        accession="0000000001-26-000001",
        infotable_sk=7,
        decision_cutoff="2026-05-17T00:00:00Z",
    )

    assert out["valid"] is True
    assert out["holding"]["quantity"] == {"value": "125000", "type": None}
    assert out["holding"]["normalized_quantity"] is None
    assert "QUANTITY_TYPE_UNQUALIFIED" in out["holding"]["limitations"]
    assert out["k3e_admissible"] is False


def test_non_generation_object_fails_closed():
    out = project_reported_holding(
        {"holdings": []},
        accession="0000000001-26-000001",
        infotable_sk=7,
        decision_cutoff="2026-05-17T00:00:00Z",
    )

    assert out["valid"] is False
    assert out["state"] == "REFUSED"
    assert out["refusals"] == ["OWNER_GENERATION_REQUIRED"]


def test_projection_is_strict_json_and_has_no_change_or_score_field():
    out = project_reported_holding(
        _generation(),
        accession="0000000001-26-000001",
        infotable_sk=7,
        decision_cutoff="2026-05-17T00:00:00Z",
    )

    encoded = json.dumps(out, allow_nan=False, sort_keys=True)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
    assert "positioning_score" not in out
    assert "holding_change" not in out
    assert "flow" not in out
