"""Native producer -> GMI current-descriptive reader contract; TEST-ONLY.

Real published collector + its published synthetic fixture helpers drive the real
consumer projection over in-memory candidate bytes. Row native-admission fields
are TEST-LOCAL SIMULATION ONLY, never a Data OS admission/publication/rights
decision; no store write, network, private research view, or JS/browser parity.
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

from collectors import bea_gvc_native as bea
from engine.market_ontology import bea_gvc_current as gmi
from lib.dataos.registry import DatasetContract, DatasetStatus, Layer, Registry
from tests.test_bea_gvc_native import bind, digest, encoded, fixture

INDUSTRY = "5241X"
NATIVE_UTC = "2026-10-17T12:00:00+00:00"  # simulated admission clock; never authority
RIGHTS = dict.fromkeys(RIGHTS_USES := ("purchase_access", "internal_computation",
                                       "redistribution"), "granted")
RIGHTS["evidence"] = {key: gmi.RIGHTS_DECISION for key in RIGHTS_USES}


def registry(status=DatasetStatus.PRODUCED):
    """Exact required in-memory L0/L1 gate fixture; nothing is persisted."""
    kw = dict(owner="macro-dashboard", producer="TEST_ONLY", storage="not_installed",
              format="jsonl", grain=("industry_code_exact",),
              temporal_profile="REVISABLE_RELEASE", version="0.test", status=status,
              rights=RIGHTS, licensing=gmi.RIGHTS_SCOPE)
    return Registry((
        DatasetContract(dataset_id=gmi.L0_ID, layer=Layer.L0_SOURCE, **kw),
        DatasetContract(dataset_id=gmi.L1_ID, layer=Layer.L1_NORMALIZED,
                        inputs=(gmi.L0_ID,), **kw)))


def eight_year_parts():
    """Published synthetic fixtures merged into the 8x9=72-response scope."""
    skeleton, sources, receipts, by_year = None, {}, {}, {}
    for year in bea.YEARS:
        raw_lineage, year_sources, year_receipts = fixture(year=year)
        lineage = json.loads(raw_lineage)
        skeleton = skeleton or lineage
        sources.update(year_sources)
        receipts.update(year_receipts)
        by_year[str(year)] = lineage["sources_by_accounting_year"][str(year)]
    skeleton["sources_by_accounting_year"] = by_year
    skeleton["capture_receipt_sha256"] = {str(i): sha for i, sha in enumerate(receipts)}
    return encoded(skeleton), sources, receipts


def encode_rows(rows):
    return b"".join(json.dumps(row, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False).encode("utf-8")
                    + b"\n" for row in rows)


def simulate_native_admission(view):
    """Explicit test-local in-memory row copies; simulated admission, no authority."""
    rows = []
    for line in view.jsonl_bytes.splitlines():
        row = json.loads(line)
        assert (row["native_ingested_at"], row["native_known_at"],
                row["native_revision_seq"], row["candidate_revision_seq"],
                row["canonical_industry_id"], row["canonical_security_id"]) == (
            None, None, None, 0, None, None)
        assert (row["may_publish"], row["may_rank"], row["may_trade"], row["may_train"],
                row["dataos_native_admitted"], row["historical_pit_eligible"],
                row["named_company_relationship"]) == (False,) * 7
        rows.append({**row, "native_ingested_at": NATIVE_UTC, "native_revision_seq": 0,
                     "dataos_native_admitted": True, "may_publish": True})
    return rows


def mutate(rows, index, **changes):
    out = json.loads(json.dumps(rows))
    out[index].update(changes)
    return out


@pytest.fixture(scope="module")
def harness():
    candidate = bind(eight_year_parts(), years=bea.YEARS)
    view = bea.candidate_industry_jsonl(candidate, INDUSTRY)
    rows = simulate_native_admission(view)

    def read(source=None, *, sha=None, generation=None, native_utc=NATIVE_UTC,
             revision=0, registry_status=DatasetStatus.PRODUCED):
        payload = (view.jsonl_bytes if source == "raw"
                   else encode_rows(rows if source is None else source))
        return gmi.current_industry_candidate(
            registry(registry_status), industry_code_exact=INDUSTRY,
            owner_bound_jsonl=payload,
            owner_expected_sha256=sha or hashlib.sha256(payload).hexdigest(),
            owner_generation_id=generation or candidate.generation_id,
            owner_native_ingested_at=native_utc, owner_native_revision_seq=revision)

    return SimpleNamespace(candidate=candidate, view=view, rows=rows, read=read)


def assert_unavailable(packet, reason):
    assert packet["status"] == "UNAVAILABLE" and packet["reason"] == reason
    assert (packet["rows_examined"], packet["annual_descriptive"],
            packet["source_generation_id"], packet["native_ingested_at"]) == (0, [], None, None)
    assert (packet["may_publish"], packet["may_rank"], packet["may_trade"]) == (False,) * 3
    assert packet["authority_ceiling"] == gmi.AUTHORITY


def test_panel_and_bytes_bind_real_published_producer(harness):
    m, candidate, view = harness.candidate.manifest, harness.candidate, harness.view
    assert m["source_response_count"] == 72
    assert m["complete_2017_2024_panel"] is True and m["candidate_revision_seq"] == 0
    assert m["supersedes_candidate_generation"] is None and m["expected_l1_rows"] == 8 * 138 * 139
    assert m["producer_code_sha256"] == bea._producer_sha256()
    assert (m["dataos_native_admitted"], m["may_publish"], m["may_rank"],
            m["may_train"], m["may_trade"]) == (False,) * 5
    assert view.row_count == 1112 == 8 * gmi.COMMODITIES_PER_YEAR
    assert view.sha256 == digest(view.jsonl_bytes)
    assert view.source_generation_id == candidate.generation_id
    raw = [json.loads(line) for line in view.jsonl_bytes.splitlines()]
    assert len(raw) == 1112
    for row in raw:
        assert row["industry_code_exact"] == INDUSTRY
        assert row["source_generation_id"] == candidate.generation_id
        assert row["source_lineage_sha256"] == m["source_lineage_sha256"]
        assert (set(row["source_response_sha256_by_table"]),
                set(row["capture_receipt_sha256_by_table"])) == (set(bea.TABLES),) * 2


def test_admitted_candidate_reads_as_candidate_not_published(harness):
    p, m = harness.read(), harness.candidate.manifest
    assert p["status"] == "CANDIDATE_NOT_PUBLISHED"
    assert p["reason"] == "OWNER_AUTHENTICATION_AND_RUNTIME_RELEASE_UNPROVEN"
    assert p["authority_ceiling"] == gmi.AUTHORITY
    assert (p["may_publish"], p["may_rank"], p["may_trade"]) == (False,) * 3
    assert p["rows_examined"] == 1112
    assert p["source_generation_id"] == harness.candidate.generation_id
    assert p["source_lineage_sha256"] == m["source_lineage_sha256"]
    assert p["producer_code_sha256"] == bea._producer_sha256()
    assert p["native_ingested_at"] == NATIVE_UTC
    assert p["owner_expected_view_sha256_claim"] == digest(encode_rows(harness.rows))
    assert set(p["industry_names_by_accounting_year"].values()) == {"Industry 0"}
    assert (p["industry_display_name"], p["industry_display_name_state"]) == (
        "Industry 0", "EXACT_SOURCE_LABEL_STABLE")
    assert p["canonical_security_id"] is None
    assert p["legacy_mapping_state"] == "UNRESOLVED_5241X_VS_5241XX"
    # Byte-flow spot proof: engine annuals re-aggregate actual producer JSONL rows;
    # pit/comparison_basis/attribution fields are enforced by candidate_packet_bytes.
    year_rows = [r for r in harness.rows if r["accounting_year"] == 2017]
    first = p["annual_descriptive"][0]
    assert first["year_over_year_change_million_USD"] is None
    assert first["total_use_million_USD"] == sum(r["total_use_million_USD"] for r in year_rows) == 1000
    assert first["world_import_million_USD"] == sum(r["world_import_million_USD"] for r in year_rows) == 3
    assert (first["canada_import_million_USD"], first["china_import_million_USD"], first["europe_import_million_USD"], first["region_rounding_difference_million_USD"]) == (-2, 5, 0, 0)
    assert first["quality"] == {"nonpositive_world_commodities": 138,
                                "negative_region_adjustment_commodities": 1,
                                "rounding_residual_commodities": 0}


def test_packets_serialize_and_fail_closed(harness):
    packet = harness.read()
    assert json.loads(gmi.candidate_packet_bytes(packet)) == packet
    for change in ({"may_publish": True}, {"may_rank": True}, {"hidden_extra_field": True}):
        with pytest.raises(gmi.BEADescriptiveRefused):
            gmi.candidate_packet_bytes({**packet, **change})
    unavailable = harness.read(sha="f" * 64)
    for change in ({"rows_examined": 1}, {"source_generation_id": "a" * 64}):
        with pytest.raises(gmi.BEADescriptiveRefused):
            gmi.candidate_packet_bytes({**unavailable, **change})


CLAIMS = (
    ("unpromoted_raw_candidate", {"source": "raw"}, None, "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"),
    ("proposed_registry", {"registry_status": DatasetStatus.PROPOSED}, None, "SOURCE_NOT_PRODUCED"),
    ("wrong_sha", {"sha": "f" * 64}, None, "SOURCE_VIEW_DIGEST_MISMATCH"),
    ("wrong_generation", {"generation": "e" * 64}, None, "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"),
    ("wrong_native_clock", {"native_utc": "2026-10-16T12:00:00+00:00"}, None, "SOURCE_PROVENANCE_OR_AUTHORITY_INVALID"),
    ("future_native_clock", {"native_utc": "2099-01-01T00:00:00+00:00"}, gmi.BEADescriptiveRefused, None),
)


@pytest.mark.parametrize("name,kwargs,error,reason", CLAIMS)
def test_owner_claims_fail_closed(harness, name, kwargs, error, reason):
    if error is not None:
        with pytest.raises(error):
            harness.read(**kwargs)
    else:
        assert_unavailable(harness.read(**kwargs), reason)


MUTATIONS = (
    ("incomplete_rows", lambda rows: rows[:100] + rows[101:], "INCOMPLETE_COMMODITY_YEARS"),
    ("mixed_industry_row", lambda rows: mutate(rows, 300, industry_code_exact="I001"),
     "SOURCE_GRAIN_OR_IDENTITY_INVALID"),
    ("duplicate_commodity_within_year", lambda rows: mutate(rows, 140, commodity_code_exact="C000"),
     "SOURCE_GRAIN_OR_IDENTITY_INVALID"),
    ("cross_year_commodity_order", lambda rows: mutate(mutate(
        rows, 422, commodity_code_exact="C006"), 423, commodity_code_exact="C005"),
     "COMMODITY_IDENTITY_DRIFT"),
    ("within_year_source_lineage_drift", lambda rows: mutate(rows, 280, source_response_sha256_by_table={
        **rows[280]["source_response_sha256_by_table"], "Use": "a" * 64}),
     "SOURCE_ANNUAL_RESPONSE_DRIFT"),
    ("tampered_amount_breaks_signed_accounting",
     lambda rows: mutate(rows, 1, world_import_million_USD=7),
     "SOURCE_SIGNED_ACCOUNTING_INVALID"),
)


@pytest.mark.parametrize("name,mutated,reason", MUTATIONS)
def test_mutated_payloads_fail_closed(harness, name, mutated, reason):
    assert_unavailable(harness.read(mutated(harness.rows)), reason)
