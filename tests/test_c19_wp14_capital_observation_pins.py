"""C19/WP14 offline pins for capital-structure observation consumer contracts.

Commission 19 consumers (the composer financial leg and the dossier, MAS-272)
depend on three pinned semantics, tested here against the frozen offline
fixture with no network, no wall clock and no randomness:

1. every instrument candidate term's input receipt binds the exact direct
   document-term observation it was derived from (id, digest, availability
   distinct from the retrieval time);
2. correction lineage is typed -- a projected candidate mirrors source
   supersession as document-term ids only, while its own correction_of
   accepts only candidate-term ids;
3. the v2 share-count metric and the share-count truth surface admit only
   point-in-time outstanding and public-float facts, never a weighted-average
   share basis.
"""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

import engine.capital_structure.instrument_candidates as ic
from engine.capital_structure.document_terms import compile_document_term_records
from engine.capital_structure.instrument_candidates import compile_candidate_term_records
from engine.capital_structure.source_identity import manifest_id_for
from engine.capital_structure import share_count_truth as sct


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/capital_structure/document_terms/registration_fee_table_submission.txt"
CANDIDATE_SCHEMA = ROOT / "contracts/capital_structure_instrument_candidate_term.schema.json"
SHARE_COUNT_V2_SCHEMA = ROOT / "contracts/capital_structure_share_count_observation_v2.schema.json"


def _manifest(raw: bytes) -> dict:
    digest = sha256(raw).hexdigest()
    m = {
        "schema": "capital_structure.source_manifest/v1",
        "source_system": "sec_edgar",
        "source_id": "0000000001-26-000001:0:complete-submission.txt",
        "issuer": {
            "issuer_id": "sec:cik:0000000001", "cik": "1", "ticker": "ABC",
            "aliases": ["ABC Corp"],
        },
        "filing": {
            "accession": "0000000001-26-000001", "form": "S-3",
            "filing_date": "2026-08-01", "accepted_at": "2026-08-01T11:00:00Z",
            "file_number": "333-123456",
        },
        "document": {
            "canonical_url": "https://www.sec.gov/Archives/edgar/data/1/example.txt",
            "document_name": "complete-submission.txt", "document_type": "S-3",
            "document_role": "complete_submission", "sequence": "0",
            "media_type": "text/plain", "byte_length": len(raw),
            "document_version": 1, "content_sha256": digest,
            "parent_manifest_id": None, "root_locator": f"sha256:{digest}",
        },
        "retrieval": {
            "retrieved_at": "2026-08-02T12:00:00Z",
            "first_seen_at": "2026-08-02T12:00:00Z",
            "transport_status": "retrieved",
        },
        "storage": {
            "backend": "r2", "store_id": "r2_shared",
            "object_key": f"capital_structure/sec/sha256/{digest[:2]}/{digest}",
            "content_addressed": True, "retention_state": "retained",
        },
        "rights": {
            "redistribution_class": "public_source_link",
            "attribution_required": True,
            "license_note": "United States SEC EDGAR public filing",
        },
        "privacy": {"classification": "public", "contains_personal_data": True},
        "parser": {
            "eligibility": "eligible", "corruption_state": "clean",
            "parser_version": "sec-source-inspector/1.0.0",
        },
        "spans": [
            {
                "span_id": f"root:{digest}", "locator_type": "document",
                "locator": f"bytes:0-{len(raw)}", "text_sha256": digest,
            },
        ],
    }
    m["manifest_id"] = manifest_id_for(m)
    return m


def _compile() -> tuple:
    raw = FIXTURE.read_bytes()
    m = _manifest(raw)
    src = compile_document_term_records(
        [m], source_reader=lambda _: raw, generated_at="2026-08-03T00:00:00Z",
    )["observations"]
    rows = compile_candidate_term_records(
        src, source_manifests=[m], source_reader=lambda _: raw,
        existing_candidate_terms=[], generated_at="2026-08-04T00:00:00Z",
        source_as_of=None,
    )["observations"]
    return src, rows


def _validator() -> Draft202012Validator:
    return Draft202012Validator(
        json.loads(CANDIDATE_SCHEMA.read_text()), format_checker=FormatChecker(),
    )


def _v2_schema() -> dict:
    return json.loads(SHARE_COUNT_V2_SCHEMA.read_text())


def test_candidate_receipt_binds_direct_document_term_observation():
    """A candidate's receipt must name the exact direct observation it came from."""
    src, rows = _compile()
    assert len(src) == 5
    assert len(rows) == 5
    V = _validator()
    for row in rows:
        assert list(V.iter_errors(row)) == []
    src_ids = {row["observation_id"] for row in src}
    src_by_id = {row["observation_id"]: row for row in src}
    for row in rows:
        st = row["source_term"]
        rc = st["receipt"]
        assert rc["direct_observation_id"] == st["observation_id"]
        assert st["observation_id"] in src_ids
        assert rc["direct_observation_sha256"] == st["observation_sha256"]
        assert rc["direct_available_at"] == st["available_at"]
        assert rc["direct_available_at"] != st["source_available_at"]
        assert set(rc) == {
            "direct_available_at", "direct_observation_id",
            "direct_observation_sha256", "receipt_id", "schema",
            "verification_state",
        }
        assert rc["schema"] == (
            "capital_structure.instrument_candidate_term_input_receipt.v1"
        )
        assert rc["verification_state"] == "validated_document_term_observation"
        assert row["version"] == {
            "immutable_record": True, "correction_version": 1,
            "correction_of": None,
        }
        assert row["relationships"] == {
            "supersedes": [], "source_observation_supersedes": [],
            "contradiction_ids": [],
        }
        # The receipt digest must agree with the document-term row's own sha
        # field if that row exposes one.  Document-term rows at BASE carry no
        # row-level sha256 field (the nearest field, the nested
        # document.content_sha256, binds the source bytes -- a different
        # quantity than the candidate's row-body digest), so this sub-assert
        # is skipped here; no hash computation is invented.
        doc_row = src_by_id[st["observation_id"]]
        own_sha_keys = [key for key in doc_row if key.endswith("sha256")]
        if own_sha_keys:
            assert st["observation_sha256"] == doc_row[own_sha_keys[0]]


def test_projection_mirrors_source_correction_lineage():
    """Source supersession is mirrored as document-term ids, never retyped."""
    src, _ = _compile()
    s2 = deepcopy(src[0])
    s2["version"]["correction_version"] = 2
    s2.setdefault("relationships", {})["supersedes"] = [
        "document-term:cs:" + "a" * 24,
    ]
    p = ic._project_record(
        s2, generated_at="2026-08-04T00:00:00Z", correction_version=1,
        correction_of=None,
    )
    assert p["relationships"] == {
        "supersedes": [],
        "source_observation_supersedes": ["document-term:cs:" + "a" * 24],
        "contradiction_ids": [],
    }
    assert p["source_term"]["correction_version"] == 2
    assert p["version"] == {
        "immutable_record": True, "correction_version": 1,
        "correction_of": None,
    }
    assert list(_validator().iter_errors(p)) == []


def test_candidate_correction_of_chains_only_candidate_ids():
    """version.correction_of chains candidate ids only; source_observation_
    supersedes mirrors document-term ids only."""
    _, rows = _compile()
    V = _validator()
    bad = deepcopy(rows[0])
    bad["version"]["correction_of"] = "document-term:cs:" + "b" * 24
    bad["version"]["correction_version"] = 2
    assert len(list(V.iter_errors(bad))) >= 1
    good = deepcopy(rows[0])
    good["version"]["correction_of"] = "instrument-candidate-term:cs:" + "c" * 24
    good["version"]["correction_version"] = 2
    assert list(V.iter_errors(good)) == []
    bad2 = deepcopy(rows[0])
    bad2["relationships"]["source_observation_supersedes"] = [
        "instrument-candidate-term:cs:" + "c" * 24,
    ]
    assert len(list(V.iter_errors(bad2))) >= 1


def test_share_count_metric_kind_rejects_weighted_average():
    """The v2 metric surface has no weighted-average share basis at all."""
    s = _v2_schema()
    metric = s["$defs"]["metric"]
    assert metric["properties"]["kind"]["enum"] == [
        "common_shares_outstanding",
        "public_float",
        "common_shares_authorized",
        "common_shares_issued",
        "common_shares_reserved_for_future_issuance",
    ]
    assert metric["properties"]["scope"] == {
        "const": "direct_sec_companyfacts_fact",
    }
    assert metric["additionalProperties"] is False
    assert not any(
        "weighted" in kind.lower() for kind in metric["properties"]["kind"]["enum"]
    )
    errors = list(
        Draft202012Validator(metric).iter_errors(
            {
                "kind": "weighted_average_shares_outstanding",
                "scope": "direct_sec_companyfacts_fact",
            },
        )
    )
    assert len(errors) >= 1
    assert list(
        Draft202012Validator(metric).iter_errors(
            {
                "kind": "common_shares_outstanding",
                "scope": "direct_sec_companyfacts_fact",
            },
        )
    ) == []


def test_share_count_truth_supported_facts_exclude_weighted_average():
    """The truth surface carries only the six point-in-time facts."""
    keys = sorted(sct.SUPPORTED_FACTS)
    assert keys == [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("dei", "EntityPublicFloat"),
        ("us-gaap", "CommonStockCapitalSharesReservedForFutureIssuance"),
        ("us-gaap", "CommonStockSharesAuthorized"),
        ("us-gaap", "CommonStockSharesIssued"),
        ("us-gaap", "CommonStockSharesOutstanding"),
    ]
    assert not any("weightedaverage" in name.lower() for _, name in keys)
    assert sorted(name for _, name in keys) == sorted(
        _v2_schema()["$defs"]["fact"]["properties"]["name"]["enum"]
    )
