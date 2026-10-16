"""Hermetic GMI BEA descriptive consumer, denied until actual native source admission.

All positive fixtures are synthetic. A supplied proof digest is not a signed owner
receipt, and this module never creates an API route or grants publication.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from lib.dataos.registry import DatasetContract, DatasetStatus, Layer, Registry
from engine.market_ontology import bea_gvc_current as gmi


NATIVE_UTC = "2026-10-10T13:47:00+00:00"
GEN = "a" * 64
RIGHTS = {"purchase_access": "granted", "internal_computation": "granted",
          "redistribution": "granted",
          "evidence": {"purchase_access": "DEC:TEST",
                       "internal_computation": "DEC:TEST",
                       "redistribution": "DEC:TEST"}}


def fake_registry(*, status=DatasetStatus.PROPOSED, rights=None, l1_inputs=(gmi.L0_ID,)):
    kw = dict(owner="macro-dashboard", producer="TEST_ONLY", storage="not_installed",
              format="jsonl", grain=("industry_code_exact",), temporal_profile="REVISABLE_RELEASE",
              version="0.test", status=status,
              rights=RIGHTS if rights is None else rights, licensing=gmi.RIGHTS_SCOPE)
    l0 = DatasetContract(dataset_id=gmi.L0_ID, layer=Layer.L0_SOURCE, **kw)
    l1 = DatasetContract(dataset_id=gmi.L1_ID, layer=Layer.L1_NORMALIZED,
                         inputs=l1_inputs, **kw)
    return Registry((l0, l1))


def fake_rows(*, industry="5241X"):
    result = []
    for year in gmi.YEARS:
        for i in range(139):
            result.append(dict(
                dataset_id=gmi.L1_ID,
                publisher_edition_date=gmi.EDITION_DATE,
                publication_precision="DAY",
                published_at=None,
                original_historical_available_at=None,
                source_generation_id=GEN,
                native_ingested_at=NATIVE_UTC,
                native_revision_seq=0,
                dataos_native_admitted=True, may_publish=True,
                may_rank=False, may_trade=False, named_company_relationship=False,
                canonical_security_id=None,
                industry_code_exact=industry,
                commodity_code_exact=f"C{i:03d}",
                accounting_year=year,
                total_use_million_USD=100,
                world_import_million_USD=3,
                canada_import_million_USD=-2,
                china_import_million_USD=5,
                europe_import_million_USD=0,
                japan_import_million_USD=0,
                mexico_import_million_USD=0,
                rest_of_asia_and_pacific_import_million_USD=0,
                rest_of_world_import_million_USD=0,
                region_rounding_difference_million_USD=0,
                source_kind="imputed_industry_commodity_accounting",
                source_units="million USD",
                code_namespace=gmi.SOURCE_NAMESPACE,
                source_lineage_sha256="3" * 64,
                producer_code_sha256="4" * 64,
                source_response_sha256_by_table={
                    key: hashlib.sha256(f"{year}:source:{key}".encode()).hexdigest()
                    for key in gmi.SOURCE_TABLES},
                capture_receipt_sha256_by_table={
                    key: hashlib.sha256(f"{year}:receipt:{key}".encode()).hexdigest()
                    for key in gmi.SOURCE_TABLES},
            ))
    return result


def encoded(rows):
    return b"".join(json.dumps(row, sort_keys=True,
                               separators=(",", ":")).encode() + b"\n" for row in rows)


def check(*, rows=None, registry=None, **kwargs):
    body = encoded(fake_rows()) if rows is None else encoded(rows)
    return gmi.current_industry_candidate(
        fake_registry(status=DatasetStatus.PRODUCED) if registry is None else registry,
        industry_code_exact="5241X",
        owner_bound_jsonl=body,
        owner_expected_sha256=hashlib.sha256(body).hexdigest(),
        owner_generation_id=GEN,
        owner_native_ingested_at=NATIVE_UTC,
        owner_native_revision_seq=0,
        **kwargs,
    )


def test_proposed_and_unregistered_source_never_touch_bytes():
    class Bomb:
        def __len__(self):
            raise AssertionError("unproduced source must not even read bytes")
    for reg, reason in (
        (fake_registry(), "SOURCE_NOT_PRODUCED"),
        (Registry(()), "SOURCE_UNREGISTERED"),
        (Registry((fake_registry().get(gmi.L0_ID),)), "SOURCE_UNREGISTERED"),
    ):
        result = gmi.current_industry_candidate(
            reg, industry_code_exact="5241X", owner_bound_jsonl=Bomb())
        assert result["status"] == "UNAVAILABLE"
        assert result["reason"] == reason
        assert result["annual_descriptive"] == []
        assert result["may_publish"] is False


def test_existing_registry_contract_and_rights_are_required():
    r = fake_registry(status=DatasetStatus.PRODUCED)
    assert check(registry=r)["status"] == "CANDIDATE_NOT_PUBLISHED"
    no_redistribution = {
        **RIGHTS, "redistribution": "not_granted",
    }
    assert gmi.current_industry_candidate(
        fake_registry(status=DatasetStatus.PRODUCED, rights=no_redistribution),
        industry_code_exact="5241X",
    )["reason"] == "SOURCE_RIGHTS_NOT_GRANTED"
    assert gmi.current_industry_candidate(
        fake_registry(status=DatasetStatus.PRODUCED, l1_inputs=()),
        industry_code_exact="5241X",
    )["reason"] == "SOURCE_CONTRACT_NOT_BOUND"
    l0, l1 = tuple(r)
    altered = replace(l1, licensing="UNKNOWN")
    assert gmi.current_industry_candidate(
        Registry((l0, altered)), industry_code_exact="5241X",
    )["reason"] == "SOURCE_SCOPE_UNQUALIFIED"
    assert gmi.current_industry_candidate(
        Registry((l0, l1, l1)), industry_code_exact="5241X",
    )["reason"] == "DUPLICATE_SOURCE_REGISTRY_ID"


def test_signed_current_descriptive_packet_and_same_machine_bytes():
    packet = check()
    assert packet["status"] == "CANDIDATE_NOT_PUBLISHED"
    assert packet["reason"] == "OWNER_AUTHENTICATION_AND_RUNTIME_RELEASE_UNPROVEN"
    assert packet["authority_ceiling"] == "internal_descriptive_candidate_only"
    assert packet["rows_examined"] == 1112
    assert packet["source_generation_id"] == GEN
    assert packet["native_ingested_at"] == NATIVE_UTC
    assert [y["accounting_year"] for y in packet["annual_descriptive"]] == list(gmi.YEARS)
    for year in packet["annual_descriptive"]:
        assert year["total_use_million_USD"] == 13900
        assert year["world_import_million_USD"] == 417
        assert year["canada_import_million_USD"] == -278
        assert year["china_import_million_USD"] == 695
    assert packet["legacy_mapping_state"] == "UNRESOLVED_5241X_VS_5241XX"
    assert packet["canonical_security_id"] is None
    assert packet["historical_pit_eligible"] is False
    assert packet["owner_digest_is_not_authenticated_here"] is True
    assert packet["may_publish"] is False
    assert gmi.candidate_packet_bytes(packet) == gmi.candidate_packet_bytes(check())
    assert json.loads(gmi.candidate_packet_bytes(packet)) == packet
    same_instant = fake_rows()
    same_instant[0]["native_ingested_at"] = "2026-10-10T13:47:00Z"
    assert check(rows=same_instant)["status"] == "CANDIDATE_NOT_PUBLISHED"
    with pytest.raises(gmi.BEADescriptiveRefused, match="PUBLICATION"):
        gmi.candidate_packet_bytes({**packet, "may_publish": True})


def test_candidate_flags_or_mixed_generation_cannot_be_launched():
    rows = fake_rows()
    rows[0]["dataos_native_admitted"] = False
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"
    rows = fake_rows()
    rows[0]["may_publish"] = False
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"
    rows = fake_rows()
    rows[0]["source_generation_id"] = "b" * 64
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"
    rows = fake_rows()
    rows[0]["canonical_security_id"] = "SEC:US-MU"
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"


def test_malformed_edition_and_retrospective_pit_do_not_pass():
    rows = fake_rows()
    rows[0]["publisher_edition_date"] = "2017-01-01"
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"
    rows = fake_rows()
    rows[0]["original_historical_available_at"] = "2017-12-31T00:00:00Z"
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"
    rows = fake_rows()
    rows[0]["native_ingested_at"] = "2017-12-31T00:00:00Z"
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"
    rows = fake_rows()
    rows[0]["may_rank"] = True
    assert check(rows=rows)["reason"] == "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"


def test_incomplete_duplicate_or_drifting_commodity_fails_closed():
    rows = fake_rows()[:-1]
    assert check(rows=rows)["reason"] == "INCOMPLETE_COMMODITY_YEARS"
    rows = fake_rows()
    rows[1]["commodity_code_exact"] = "C000"
    assert check(rows=rows)["reason"] == "SOURCE_GRAIN_OR_IDENTITY_INVALID"
    rows = fake_rows()
    a = next(row for row in rows if row["accounting_year"] == 2018)
    a["commodity_code_exact"] = "SHIFT"
    assert check(rows=rows)["reason"] == "COMMODITY_IDENTITY_DRIFT"


def test_signed_amounts_zeros_negative_regions_and_rounding():
    rows = fake_rows()
    rows[0]["world_import_million_USD"] = -1
    rows[0]["canada_import_million_USD"] = -6
    assert check(rows=rows)["status"] == "CANDIDATE_NOT_PUBLISHED"
    rows = fake_rows()
    rows[0]["world_import_million_USD"] = 5
    assert check(rows=rows)["reason"] == "SOURCE_SIGNED_ACCOUNTING_INVALID"
    rows = fake_rows()
    rows[0]["world_import_million_USD"] = True
    assert check(rows=rows)["reason"] == "SOURCE_AMOUNTS_INVALID"
    rows = fake_rows()
    rows[0]["region_rounding_difference_million_USD"] = 0.0
    assert check(rows=rows)["reason"] == "SOURCE_SIGNED_ACCOUNTING_INVALID"


def test_original_nine_table_source_and_capture_lineage_guards():
    rows = fake_rows()
    rows[0]["source_response_sha256_by_table"]["Use"] = "BAD"
    assert check(rows=rows)["reason"] == "ORIGINAL_RESPONSE_LINEAGE_UNBOUND"
    rows = fake_rows()
    rows[0]["capture_receipt_sha256_by_table"].pop("ImMatCan")
    assert check(rows=rows)["reason"] == "ORIGINAL_RESPONSE_LINEAGE_UNBOUND"
    rows = fake_rows()
    rows[1]["source_response_sha256_by_table"]["Use"] = "5" * 64
    assert check(rows=rows)["reason"] == "SOURCE_ANNUAL_RESPONSE_DRIFT"
    rows = fake_rows()
    rows[139]["source_lineage_sha256"] = "6" * 64
    assert check(rows=rows)["reason"] == "SOURCE_PRODUCER_OR_LINEAGE_DRIFT"
    rows = fake_rows()
    rows[0]["source_kind"] = "observed_named_company_supplier_edge"
    assert check(rows=rows)["reason"] == "ORIGINAL_RESPONSE_LINEAGE_UNBOUND"


def test_invalid_source_digest_and_source_framing_refuse():
    body = encoded(fake_rows())
    actual = hashlib.sha256(body).hexdigest()
    result = gmi.current_industry_candidate(
        fake_registry(status=DatasetStatus.PRODUCED),
        industry_code_exact="5241X", owner_bound_jsonl=body + b" ",
        owner_expected_sha256=actual, owner_generation_id=GEN,
        owner_native_ingested_at=NATIVE_UTC, owner_native_revision_seq=0)
    assert result["reason"] == "SOURCE_VIEW_DIGEST_MISMATCH"
    with pytest.raises(gmi.BEADescriptiveRefused, match="UNSAFE"):
        gmi.current_industry_candidate(fake_registry(), industry_code_exact="../escape")
    with pytest.raises(gmi.BEADescriptiveRefused, match="OWNER_GENERATION"):
        gmi.current_industry_candidate(
            fake_registry(status=DatasetStatus.PRODUCED),
            industry_code_exact="5241X", owner_bound_jsonl=body,
            owner_expected_sha256=actual,
            owner_generation_id="wrong",
            owner_native_ingested_at=NATIVE_UTC, owner_native_revision_seq=0)
    with pytest.raises(gmi.BEADescriptiveRefused, match="NAIVE_NATIVE_CLOCK"):
        gmi.current_industry_candidate(
            fake_registry(status=DatasetStatus.PRODUCED),
            industry_code_exact="5241X", owner_bound_jsonl=body,
            owner_expected_sha256=actual, owner_generation_id=GEN,
            owner_native_ingested_at="2026-10-10T01:00:00",
            owner_native_revision_seq=0)
