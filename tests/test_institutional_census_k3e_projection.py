from __future__ import annotations

import json

from engine.institutional_census.catalog import (
    prepare_catalog_generation,
    publish_catalog_generation,
)
from engine.institutional_census.k3e_projection import project_reported_holding
from engine.institutional_census.storage import publish_raw_evidence
from engine.research_vault.r2_store import LocalStore


FILER_CIK = "0000000001"
ACCESSION = "0000000001-26-000001"
REPORT_PERIOD = "2026-03-31"
CUSIP = "037833100"
PUBLISHED_AT = "2026-05-16T12:00:00Z"
SOURCE_CUTOFF = "2026-05-16T10:00:00Z"
DECISION_CUTOFF = "2026-05-17T00:00:00Z"


def _world(tmp_path, *, quantity="125000", quantity_type="SH", raw_sha_override=None):
    store = LocalStore(tmp_path / "store")
    raw = publish_raw_evidence(
        store,
        accession=ACCESSION,
        filer_cik=FILER_CIK,
        form="13F-HR",
        report_period=REPORT_PERIOD,
        accepted_at="2026-05-15T20:30:00Z",
        retained_at="2026-05-15T20:32:00Z",
        source_url="https://www.sec.gov/Archives/edgar/data/1/000000000126000001/index.json",
        payload=b"owner-verified-a10-fixture",
        producer_version="k3e-a10-fixture/1.0.0",
    )
    filing = {
        "accession": ACCESSION,
        "filer_cik": FILER_CIK,
        "filer_name": "Example Manager",
        "form": "13F-HR",
        "filing_date": "2026-05-15",
        "accepted_at": "2026-05-15T20:30:00Z",
        "report_period": REPORT_PERIOD,
        "report_type": "13F HOLDINGS REPORT",
        "form13f_file_number": "028-00001",
        "is_amendment": False,
        "amendment_number": None,
        "amendment_type": None,
        "amends_accession": None,
        "lineage_state": "original",
        "confidential_omitted": False,
        "table_entry_total": 1,
        "table_value_total_usd": 24500000000,
        "other_manager_count": 0,
        "source_receipt_id": raw.receipt_id,
        "normalization_id": "norm_a10_fixture",
        "raw_sha256": raw_sha_override or raw.raw_object.sha256,
        "first_seen_at": "2026-05-15T20:31:00Z",
        "retained_at": "2026-05-15T20:32:00Z",
        "parser_version": "k3e-a10-fixture/1.0.0",
        "quality_state": "valid",
    }
    holding = {
        "accession": ACCESSION,
        "infotable_sk": 7,
        "name_of_issuer": "APPLE INC",
        "title_of_class": "COM",
        "cusip": CUSIP,
        "figi": "BBG000B9XRY4",
        "value_reported": "24500000",
        "value_unit": "USD_THOUSANDS",
        "value_usd": 24500000000,
        "ssh_prn_amt": quantity,
        "ssh_prn_type": quantity_type,
        "put_call": None,
        "investment_discretion": "SOLE",
        "other_manager": None,
        "voting_authority_sole": 125000,
        "voting_authority_shared": 0,
        "voting_authority_none": 0,
        "row_hash": "b" * 64,
    }
    prepared = prepare_catalog_generation(
        report_period=REPORT_PERIOD,
        source_cutoff_at=SOURCE_CUTOFF,
        published_at=PUBLISHED_AT,
        producer_version="k3e-a10-fixture/1.0.0",
        filings=[filing],
        holdings=[holding],
        manager_relationships=[],
        source_receipt_ids=[raw.receipt_id],
        coverage={"fixture": True, "complete": True},
    )
    generation = publish_catalog_generation(store, prepared)
    return store, generation


def _project(store, **overrides):
    args = dict(
        filer_cik=FILER_CIK,
        report_period=REPORT_PERIOD,
        accession=ACCESSION,
        infotable_sk=7,
        decision_cutoff=DECISION_CUTOFF,
    )
    args.update(overrides)
    return project_reported_holding(store, **args)


def test_projection_reads_verified_owner_store_and_preserves_delayed_context(tmp_path):
    store, generation = _world(tmp_path)

    out = _project(store)

    assert out["schema"] == "institutional_13f.k3e_reported_holding_context.v1"
    assert out["valid"] is True
    assert out["state"] == "AVAILABLE_UNQUALIFIED"
    assert out["owner"] == "engine.institutional_census"
    assert out["authority"] == "descriptive_context_only"
    assert out["financial_influence"] is False
    assert out["k3e_admissible"] is False

    assert out["generation"]["generation_id"] == generation.generation_id
    assert out["generation"]["report_period"] == REPORT_PERIOD
    assert out["generation"]["source_cutoff_at"] == SOURCE_CUTOFF
    assert out["generation"]["published_at"] == PUBLISHED_AT

    assert out["filing"]["accession"] == ACCESSION
    assert out["filing"]["filer_cik"] == FILER_CIK
    assert out["filing"]["source_receipt_id"].startswith("i13fraw_")
    assert len(out["filing"]["raw_sha256"]) == 64

    assert out["holding"]["infotable_sk"] == 7
    assert out["holding"]["row_hash"] == "b" * 64
    assert out["holding"]["cusip"] == CUSIP
    assert out["holding"]["quantity"] == {"value": "125000", "type": "SH"}
    assert out["interpretation"] == {
        "class": "DELAYED_REPORTED_HOLDING_CONTEXT",
        "is_current_ownership": False,
        "is_flow": False,
        "is_intent": False,
        "is_conviction": False,
    }
    assert set(out["qualification"]["missing"]) == {
        "canonical_security_resolution_receipt",
        "source_use_receipt",
    }


def test_projection_refuses_generation_not_published_by_decision_cutoff(tmp_path):
    store, _ = _world(tmp_path)

    out = _project(store, decision_cutoff="2026-05-16T11:59:59Z")

    assert out["valid"] is False
    assert out["state"] == "UNAVAILABLE"
    assert "GENERATION_NOT_AVAILABLE_AT_CUTOFF" in out["refusals"]
    assert out["holding"] is None


def test_projection_missing_primary_key_is_typed_absence_not_zero(tmp_path):
    store, _ = _world(tmp_path)

    out = _project(store, infotable_sk=999)

    assert out["valid"] is False
    assert out["state"] == "UNAVAILABLE"
    assert "HOLDING_ROW_NOT_FOUND" in out["refusals"]
    assert out["holding"] is None


def test_missing_quantity_type_preserves_raw_absence_without_normalization(tmp_path):
    store, _ = _world(tmp_path, quantity_type=None)

    out = _project(store)

    assert out["valid"] is True
    assert out["holding"]["quantity"] == {"value": "125000", "type": None}
    assert out["holding"]["normalized_quantity"] is None
    assert "QUANTITY_TYPE_UNQUALIFIED" in out["holding"]["limitations"]


def test_constructed_generation_object_cannot_bypass_owner_store_verification(tmp_path):
    _, generation = _world(tmp_path)

    out = _project(generation)

    assert out["valid"] is False
    assert out["state"] == "REFUSED"
    assert out["refusals"] == ["OWNER_STORE_REQUIRED"]


def test_raw_receipt_mismatch_is_owner_refusal_not_projected_context(tmp_path):
    store, _ = _world(tmp_path, raw_sha_override="f" * 64)

    out = _project(store)

    assert out["valid"] is False
    assert out["state"] == "REFUSED"
    assert "SOURCE_RECEIPT_MISMATCH" in out["refusals"]
    assert out["holding"] is None


def test_projection_is_strict_json_and_has_no_positioning_score_or_flow(tmp_path):
    store, _ = _world(tmp_path)
    out = _project(store)

    encoded = json.dumps(out, allow_nan=False, sort_keys=True)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
    assert "positioning_score" not in out
    assert "holding_change" not in out
    assert "flow" not in out


AMEND_ACCESSION = "0000000001-26-000002"


def _publish_amendment_generation(store, *, filing_orig, holding_orig, raw_orig):
    raw_amend = publish_raw_evidence(
        store,
        accession=AMEND_ACCESSION,
        filer_cik=FILER_CIK,
        form="13F-HR/A",
        report_period=REPORT_PERIOD,
        accepted_at="2026-05-20T12:00:00Z",
        retained_at="2026-05-20T12:05:00Z",
        source_url="https://www.sec.gov/Archives/edgar/data/1/000000000126000002/index.json",
        payload=b"owner-verified-a10-amend-fixture",
        producer_version="k3e-a10-fixture/1.0.0",
    )
    filing_amend = {
        **filing_orig,
        "accession": AMEND_ACCESSION,
        "form": "13F-HR/A",
        "accepted_at": "2026-05-20T12:00:00Z",
        "is_amendment": True,
        "amendment_number": 1,
        "amendment_type": "RESTATEMENT",
        "amends_accession": ACCESSION,
        "lineage_state": "amendment_restatement",
        "source_receipt_id": raw_amend.receipt_id,
        "raw_sha256": raw_amend.raw_object.sha256,
        "retained_at": "2026-05-20T12:05:00Z",
    }
    holding_amend = {
        **holding_orig,
        "accession": AMEND_ACCESSION,
        "ssh_prn_amt": "999999",
        "row_hash": "c" * 64,
    }
    prepared = prepare_catalog_generation(
        report_period=REPORT_PERIOD,
        source_cutoff_at="2026-05-21T00:00:00Z",
        published_at="2026-05-21T12:00:00Z",
        producer_version="k3e-a10-fixture/1.0.0",
        filings=[filing_orig, filing_amend],
        holdings=[holding_orig, holding_amend],
        manager_relationships=[],
        source_receipt_ids=[raw_orig.receipt_id, raw_amend.receipt_id],
        coverage={"fixture": True, "complete": True},
    )
    return publish_catalog_generation(store, prepared)


def test_later_generation_amendment_does_not_change_pinned_earlier_snapshot(tmp_path):
    store, generation_a = _world(tmp_path)
    filing_orig = dict(generation_a.filings[0])
    holding_orig = dict(generation_a.holdings[0])

    class _RawRef:
        def __init__(self, receipt_id: str, sha256: str) -> None:
            self.receipt_id = receipt_id
            self.raw_object = type("RawObj", (), {"sha256": sha256})()

    raw_ref = _RawRef(
        str(filing_orig["source_receipt_id"]),
        str(filing_orig["raw_sha256"]),
    )
    _publish_amendment_generation(
        store, filing_orig=filing_orig, holding_orig=holding_orig, raw_orig=raw_ref
    )

    out = _project(store, generation_id=generation_a.generation_id)

    assert out["valid"] is True
    assert out["holding"]["quantity"]["value"] == "125000"


def test_non_effective_accession_is_refused_not_partial(tmp_path):
    store, _ = _world(tmp_path)

    out = _project(store, accession=AMEND_ACCESSION)

    assert out["valid"] is False
    assert out["state"] == "UNAVAILABLE"
    assert "FILING_ACCESSION_NOT_EFFECTIVE_AT_CUTOFF" in out["refusals"]
    assert out["holding"] is None


def test_invalid_identity_keys_are_refused_without_projection(tmp_path):
    store, _ = _world(tmp_path)

    assert _project(store, filer_cik="")["refusals"] == ["INVALID_FILER_KEY"]
    assert _project(store, decision_cutoff="not-a-clock")["refusals"] == [
        "INVALID_DECISION_CUTOFF"
    ]
    assert _project(store, infotable_sk=-1)["refusals"] == ["INVALID_HOLDING_KEY"]


def test_unknown_generation_id_pins_fail_closed_without_holding(tmp_path):
    store, _ = _world(tmp_path)
    missing_id = "i13fgen_" + "0" * 64

    out = _project(store, generation_id=missing_id)

    assert out["valid"] is False
    assert out["state"] == "REFUSED"
    assert out["holding"] is None
    assert "GENERATION_LOAD_REFUSED" in out["refusals"]


def test_malformed_generation_id_pin_is_refused_without_holding(tmp_path):
    store, _ = _world(tmp_path)

    out = _project(store, generation_id="not-a-generation-id")

    assert out["valid"] is False
    assert out["state"] == "REFUSED"
    assert out["holding"] is None
    assert out["refusals"] == ["INVALID_GENERATION_ID"]
