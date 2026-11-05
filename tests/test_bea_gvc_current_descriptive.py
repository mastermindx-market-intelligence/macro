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
          "evidence": {"purchase_access": gmi.RIGHTS_DECISION,
                       "internal_computation": gmi.RIGHTS_DECISION,
                       "redistribution": gmi.RIGHTS_DECISION}}


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
                industry_name="Insurance carriers, except direct life",
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
                quality_flags=["SOURCE_NEGATIVE_REGION_ADJUSTMENT"],
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


def test_rights_are_bound_to_the_exact_bea_decision_and_all_three_uses():
    evidence = dict(RIGHTS["evidence"])
    evidence["redistribution"] = "DEC:UNRELATED-SOURCE-PURPOSE"
    forged = {**RIGHTS, "evidence": evidence}
    assert gmi.current_industry_candidate(
        fake_registry(status=DatasetStatus.PRODUCED, rights=forged),
        industry_code_exact="5241X",
    )["reason"] == "SOURCE_RIGHTS_NOT_GRANTED"

    purchase_denied = {**RIGHTS, "purchase_access": "not_granted"}
    assert gmi.current_industry_candidate(
        fake_registry(status=DatasetStatus.PRODUCED, rights=purchase_denied),
        industry_code_exact="5241X",
    )["reason"] == "SOURCE_RIGHTS_NOT_GRANTED"


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
    rows[0]["quality_flags"] = [
        "WORLD_IMPORT_NONPOSITIVE", "SOURCE_NEGATIVE_REGION_ADJUSTMENT"]
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


def test_annual_quality_and_yoy_are_retrospective_not_historical_pit():
    packet = check()
    first, second = packet["annual_descriptive"][:2]
    assert first["region_rounding_difference_million_USD"] == 0
    assert first["quality"]["negative_region_adjustment_commodities"] == 139
    assert first["quality"]["nonpositive_world_commodities"] == 0
    assert first["quality"]["rounding_residual_commodities"] == 0
    assert first["year_over_year_change_million_USD"] is None
    assert second["year_over_year_change_million_USD"]["world_import_million_USD"] == 0
    assert packet["annual_comparison_basis"] == (
        "RETROSPECTIVE_2026_VINTAGE_NOT_ORIGINAL_HISTORICAL_KNOWLEDGE")

    rows = fake_rows()
    rows[0]["world_import_million_USD"] = 4
    rows[0]["region_rounding_difference_million_USD"] = 1
    rows[0]["quality_flags"] = [
        "SOURCE_NEGATIVE_REGION_ADJUSTMENT", "PUBLISHER_ROUNDING_RESIDUAL"]
    packet = check(rows=rows)
    first, second = packet["annual_descriptive"][:2]
    assert first["region_rounding_difference_million_USD"] == 1
    assert first["quality"]["rounding_residual_commodities"] == 1
    assert second["year_over_year_change_million_USD"]["world_import_million_USD"] == -1
    assert second["year_over_year_change_million_USD"][
        "region_rounding_difference_million_USD"] == -1
    assert packet["historical_pit_eligible"] is False
    assert packet["may_rank"] is False and packet["may_trade"] is False


def test_source_quality_flags_cannot_misrepresent_signs():
    rows = fake_rows()
    rows[0]["quality_flags"] = []
    assert check(rows=rows)["reason"] == "SOURCE_QUALITY_FLAG_DRIFT"
    rows = fake_rows()
    rows[0]["quality_flags"] = ["WORLD_IMPORT_NONPOSITIVE"]
    assert check(rows=rows)["reason"] == "SOURCE_QUALITY_FLAG_DRIFT"


def test_large_source_numbers_refuse_json_precision_loss():
    rows = fake_rows()
    rows[0]["total_use_million_USD"] = 2**53
    assert check(rows=rows)["reason"] == "SOURCE_AMOUNT_EXCEEDS_JSON_SAFE_INTEGER"


def test_annual_sums_and_changes_refuse_json_precision_loss():
    ceiling = gmi.MAX_JSON_SAFE_INTEGER
    rows = fake_rows()
    rows[0]["total_use_million_USD"] = ceiling
    assert check(rows=rows)["reason"] == "ANNUAL_AMOUNT_EXCEEDS_JSON_SAFE_INTEGER"

    rows = fake_rows()
    first_2017 = next(r for r in rows if r["accounting_year"] == 2017)
    first_2017["total_use_million_USD"] = ceiling - 13800
    for row in rows:
        if row["accounting_year"] == 2018:
            row["total_use_million_USD"] = -100
    first_2018 = next(r for r in rows if r["accounting_year"] == 2018)
    first_2018["total_use_million_USD"] = -ceiling + 13800
    assert check(rows=rows)["reason"] == "ANNUAL_CHANGE_EXCEEDS_JSON_SAFE_INTEGER"


def test_machine_packet_serializer_rejects_authority_and_status_forgery():
    valid = check()
    assert gmi.candidate_packet_bytes(valid)
    for change in (
        {"status": "DESCRIPTIVE"},
        {"reason": "NATIVE_SOURCE_PRODUCED"},
        {"authority_ceiling": "published_current_source"},
        {"may_rank": True},
        {"may_trade": True},
        {"historical_pit_eligible": True},
        {"owner_digest_is_not_authenticated_here": False},
        {"annual_comparison_basis": "AS_KNOWN_AT_YEAR_END"},
        {"named_company_relationship": True},
        {"canonical_security_id": "SEC:US-MU"},
        {"unknown_secret": "accidentally-forwarded"},
    ):
        with pytest.raises(gmi.BEADescriptiveRefused):
            gmi.candidate_packet_bytes({**valid, **change})


def test_machine_packet_serializer_revalidates_annual_math_and_labels():
    from copy import deepcopy
    source = check()
    bad = deepcopy(source)
    bad["annual_descriptive"][1]["year_over_year_change_million_USD"][
        "world_import_million_USD"] = 9
    with pytest.raises(gmi.BEADescriptiveRefused):
        gmi.candidate_packet_bytes(bad)
    bad = deepcopy(source)
    bad["annual_descriptive"][0]["canada_import_million_USD"] = 3
    with pytest.raises(gmi.BEADescriptiveRefused):
        gmi.candidate_packet_bytes(bad)
    bad = deepcopy(source)
    bad["annual_descriptive"][0]["quality"]["rounding_residual_commodities"] = 140
    with pytest.raises(gmi.BEADescriptiveRefused):
        gmi.candidate_packet_bytes(bad)
    bad = deepcopy(source)
    bad["industry_display_name_state"] = "SOURCE_LABELS_VARY_ACROSS_YEARS"
    with pytest.raises(gmi.BEADescriptiveRefused):
        gmi.candidate_packet_bytes(bad)


def test_machine_packet_serializer_never_exposes_unavailable_data():
    unavailable = gmi.current_industry_candidate(
        fake_registry(), industry_code_exact="5241X")
    assert json.loads(gmi.candidate_packet_bytes(unavailable)) == unavailable
    for change in (
        {"status": "CANDIDATE_NOT_PUBLISHED"},
        {"reason": "DATA_NOW_READY_TO_SERVE"},
        {"source_generation_id": GEN},
        {"rows_examined": 1},
        {"annual_descriptive": [{"accounting_year": 2017, "trade": True}]},
        {"native_ingested_at": NATIVE_UTC},
        {"private_path": "/retained/originals.json"},
    ):
        with pytest.raises(gmi.BEADescriptiveRefused):
            gmi.candidate_packet_bytes({**unavailable, **change})


def test_source_industry_names_are_preserved_without_silent_aliases():
    packet = check()
    label = "Insurance carriers, except direct life"
    assert packet["industry_display_name"] == label
    assert packet["industry_display_name_state"] == "EXACT_SOURCE_LABEL_STABLE"
    assert packet["industry_names_by_accounting_year"] == {
        str(year): label for year in gmi.YEARS}

    rows = fake_rows()
    for row in rows:
        if row["accounting_year"] == 2018:
            row["industry_name"] = "Different published 2018 name"
    packet = check(rows=rows)
    assert packet["status"] == "CANDIDATE_NOT_PUBLISHED"
    assert packet["industry_display_name"] is None
    assert packet["industry_display_name_state"] == "SOURCE_LABELS_VARY_ACROSS_YEARS"
    assert packet["industry_names_by_accounting_year"]["2018"] == (
        "Different published 2018 name")

    rows = fake_rows()
    rows[1]["industry_name"] = "Different within one year"
    assert check(rows=rows)["reason"] == "SOURCE_INDUSTRY_NAME_DRIFT_WITHIN_YEAR"

    rows = fake_rows()
    rows[0]["industry_name"] = ""
    assert check(rows=rows)["reason"] == "SOURCE_INDUSTRY_NAME_INVALID"


def test_source_name_rejects_surrogate_bidi_and_zero_width_spoofing():
    for invalid_name in ("Invalid" + chr(0xD800) + "name",
                         "Insurance" + chr(0x202E) + "Carriers",
                         "Insurance" + chr(0x200B) + "Carriers",
                         "Insurance" + chr(0x2066) + "Carriers"):
        rows = fake_rows()
        rows[0]["industry_name"] = invalid_name
        assert check(rows=rows)["reason"] == "SOURCE_INDUSTRY_NAME_INVALID"


def test_machine_packet_rejects_synthetic_aggregate_residual_overflow():
    from copy import deepcopy
    source = check()
    forgery = deepcopy(source)
    first = forgery["annual_descriptive"][0]
    first["world_import_million_USD"] += 1000000
    first["region_rounding_difference_million_USD"] += 1000000
    second = forgery["annual_descriptive"][1]
    second["year_over_year_change_million_USD"]["world_import_million_USD"] -= 1000000
    second["year_over_year_change_million_USD"][
        "region_rounding_difference_million_USD"] -= 1000000
    with pytest.raises(gmi.BEADescriptiveRefused, match="RESIDUAL"):
        gmi.candidate_packet_bytes(forgery)


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
