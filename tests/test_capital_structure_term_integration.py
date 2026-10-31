"""T0 gates: accepted-input candidate integration keeps the pre-instrument boundary closed.

A04 -- re-observation keeps occurrence identity; ids are immutable, clock
independent, never re-minted from a rebuilt ledger and never ``legacy:`` keys.
A08 -- a repeated exhibit in a later filing stays a distinct occurrence; nothing
here joins candidates (that is I0's explicit-evidence job).
A09 -- only the sealed canonical procedure mints; LLM spans/interpretations,
issuer assertions, model prose and bare canonical *claims* are refused.
"""
from __future__ import annotations

import dataclasses
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from engine.capital_structure.document_terms import DOCUMENT_TERM_SCHEMA, compile_document_term_records
from engine.capital_structure.instrument_candidates import (
    INSTRUMENT_CANDIDATE_TERM_SCHEMA,
    candidate_term_id_for,
)
from engine.capital_structure.issuer_state_contracts import (
    CandidateBundle,
    CapitalInputs,
    ContractViolation,
    GenerationBinding,
    sha256_of,
)
from engine.capital_structure.reference_qualification import NON_CANONICAL_FACT_ORIGINS, load_reference_pack
from engine.capital_structure.source_identity import manifest_id_for
from engine.capital_structure.term_integration import (
    CLOSED_CANDIDATE_AUTHORITY,
    TermIntegrationRefusal,
    assert_closed_candidate_term,
    integrate_candidate_terms,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/capital_structure/document_terms/registration_fee_table_submission.txt"
FIRST_ACCESSION = "0000000001-26-000001"
SECOND_ACCESSION = "0000000001-26-000002"


def _manifest(raw: bytes, *, accession: str = FIRST_ACCESSION, filing_date: str = "2026-08-01",
              accepted_at: str = "2026-08-01T11:00:00Z", retrieved_at: str = "2026-08-02T12:00:00Z") -> dict:
    digest = sha256(raw).hexdigest()
    record = {
        "schema": "capital_structure.source_manifest/v1",
        "source_system": "sec_edgar",
        "source_id": f"{accession}:0:complete-submission.txt",
        "issuer": {"issuer_id": "sec:cik:0000000001", "cik": "1", "ticker": "ABC", "aliases": ["ABC Corp"]},
        "filing": {"accession": accession, "form": "S-3", "filing_date": filing_date, "accepted_at": accepted_at, "file_number": "333-123456"},
        "document": {
            "canonical_url": "https://www.sec.gov/Archives/edgar/data/1/example.txt",
            "document_name": "complete-submission.txt", "document_type": "S-3", "document_role": "complete_submission",
            "sequence": "0", "media_type": "text/plain", "byte_length": len(raw), "document_version": 1,
            "content_sha256": digest, "parent_manifest_id": None, "root_locator": f"sha256:{digest}",
        },
        "retrieval": {"retrieved_at": retrieved_at, "first_seen_at": retrieved_at, "transport_status": "retrieved"},
        "storage": {"backend": "r2", "store_id": "r2_shared", "object_key": f"capital_structure/sec/sha256/{digest[:2]}/{digest}",
                    "content_addressed": True, "retention_state": "retained"},
        "rights": {"redistribution_class": "public_source_link", "attribution_required": True,
                   "license_note": "United States SEC EDGAR public filing"},
        "privacy": {"classification": "public", "contains_personal_data": True},
        "parser": {"eligibility": "eligible", "corruption_state": "clean", "parser_version": "sec-source-inspector/1.0.0"},
        "spans": [{"span_id": f"root:{digest}", "locator_type": "document", "locator": f"bytes:0-{len(raw)}", "text_sha256": digest}],
    }
    record["manifest_id"] = manifest_id_for(record)
    return record


def _authority(*, generated_at: str = "2026-08-03T00:00:00Z"):
    raw = FIXTURE.read_bytes()
    manifest = _manifest(raw)
    rows = compile_document_term_records([manifest], source_reader=lambda _: raw, generated_at=generated_at)["observations"]
    return rows, [manifest], (lambda _: raw)


def _second_filing(rows, manifests):
    """The same exhibit re-filed under a later accession -- bytes derived in memory, fixture untouched."""
    first_raw = FIXTURE.read_bytes()
    second_raw = first_raw.replace(FIRST_ACCESSION.encode(), SECOND_ACCESSION.encode())
    assert second_raw != first_raw
    second = _manifest(second_raw, accession=SECOND_ACCESSION, filing_date="2026-08-05",
                       accepted_at="2026-08-05T11:00:00Z", retrieved_at="2026-08-06T12:00:00Z")
    by_id = {manifests[0]["manifest_id"]: first_raw, second["manifest_id"]: second_raw}
    all_manifests = [*manifests, second]
    reader = lambda manifest: by_id[manifest["manifest_id"]]  # noqa: E731
    all_rows = compile_document_term_records(all_manifests, source_reader=reader, existing_observations=rows,
                                             generated_at="2026-08-07T00:00:00Z")["observations"]
    return all_rows, all_manifests, reader


def _inputs(rows, *, support: str = "supported", candidate_terms=()) -> CapitalInputs:
    bindings = [GenerationBinding("document_terms", DOCUMENT_TERM_SCHEMA, support, artifact_sha256=sha256_of(list(rows)))]
    if candidate_terms:
        bindings.append(GenerationBinding("instrument_candidate_terms", INSTRUMENT_CANDIDATE_TERM_SCHEMA, "supported",
                                          artifact_sha256=sha256_of(list(candidate_terms))))
    return CapitalInputs(tuple(bindings), document_terms=tuple(rows), candidate_terms=tuple(candidate_terms))


def _integrate(rows, manifests, reader, *, generated_at="2026-08-04T00:00:00Z", as_of="2026-08-04T00:00:00Z", **kwargs):
    return integrate_candidate_terms(_inputs(rows), source_manifests=manifests, source_reader=reader,
                                     generated_at=generated_at, as_of=as_of, **kwargs)


def _ids(rows, key):
    return sorted(row[key] for row in rows)


# --- closed projection ------------------------------------------------------------------------


def test_accepted_direct_terms_integrate_into_closed_pre_instrument_candidates():
    rows, manifests, reader = _authority()
    result = _integrate(rows, manifests, reader)
    assert result.support == "supported"
    assert result.counts["created"] == len(rows) == len(result.current) == 5
    for row in result.current:
        assert row["authority"] == dict(CLOSED_CANDIDATE_AUTHORITY)
        assert_closed_candidate_term(row)
    assert {origin.fact_origin for origin in result.origins} == {"canonical_extraction"}
    assert all(origin.fact_bearing for origin in result.origins)
    assert result.candidate_binding.schema == INSTRUMENT_CANDIDATE_TERM_SCHEMA
    assert result.candidate_binding.artifact_sha256 == sha256_of(list(result.current))
    assert result.receipt.as_record()["rule_digest"] == result.as_record()["receipt"]["rule_digest"]
    record = result.as_record()
    assert record["candidate_term_ids"] == [row["candidate_term_id"] for row in result.current]
    assert record["refusals"] == []


def test_candidate_bundle_admits_the_compiled_closed_rows():
    rows, manifests, reader = _authority()
    result = _integrate(rows, manifests, reader)
    bundle = result.candidate_bundle()
    assert [row["candidate_term_id"] for row in bundle.candidate_terms] == [row["candidate_term_id"] for row in result.current]
    # The same rows also bind as accepted inputs for the next integration.
    again = integrate_candidate_terms(_inputs(rows, candidate_terms=result.records), source_manifests=manifests,
                                      source_reader=reader, generated_at="2026-08-05T00:00:00Z", as_of="2026-08-05T00:00:00Z")
    assert again.counts["created"] == 0
    flipped = deepcopy(list(result.current))
    flipped[0]["authority"]["prophet_authority"] = True
    with pytest.raises(ContractViolation):
        CandidateBundle(result.candidate_binding, tuple(flipped), result.as_of)


# --- A04: immutable, clock-independent occurrence identity --------------------------------------


def test_a04_rerun_and_reobservation_never_remint_identity():
    rows, manifests, reader = _authority()
    first = _integrate(rows, manifests, reader)
    reobserved = compile_document_term_records(manifests, source_reader=reader, existing_observations=rows,
                                               generated_at="2026-08-05T00:00:00Z")["observations"]
    assert reobserved == rows  # re-observing identical bytes is not new evidence
    second = _integrate(reobserved, manifests, reader, generated_at="2026-08-06T00:00:00Z", as_of="2026-08-06T00:00:00Z",
                        existing_candidate_terms=first.records)
    assert second.counts["created"] == 0 and second.counts["unchanged"] == 5
    assert _ids(second.current, "candidate_term_id") == _ids(first.current, "candidate_term_id")
    assert _ids(second.current, "logical_candidate_term_id") == _ids(first.current, "logical_candidate_term_id")
    assert second.candidate_binding.artifact_sha256 == first.candidate_binding.artifact_sha256


def test_a04_occurrence_identity_is_clock_independent_and_never_legacy():
    rows_a, manifests, reader = _authority(generated_at="2026-08-03T00:00:00Z")
    rows_b, _, _ = _authority(generated_at="2026-08-09T00:00:00Z")
    a = _integrate(rows_a, manifests, reader)
    b = _integrate(rows_b, manifests, reader, generated_at="2026-08-10T00:00:00Z", as_of="2026-08-10T00:00:00Z")
    assert _ids(a.current, "logical_candidate_term_id") == _ids(b.current, "logical_candidate_term_id")
    assert _ids(a.current, "candidate_term_id") != _ids(b.current, "candidate_term_id")  # versions carry system time
    for row in [*a.current, *b.current]:
        for key in ("candidate_term_id", "logical_candidate_term_id"):
            assert not row[key].startswith("legacy:")
            assert row[key].startswith("instrument-candidate-term")


def test_a04_later_interpretation_is_not_retroactive_source_knowledge():
    rows, manifests, reader = _authority()
    before = _integrate(rows, manifests, reader, as_of="2026-08-03T12:00:00Z")
    assert before.current == () and before.counts["created"] == 5
    after = _integrate(rows, manifests, reader, as_of="2026-08-04T00:00:00Z")
    assert len(after.current) == 5


def test_a04_rebuilt_direct_ledger_cannot_remint_existing_candidates():
    rows, manifests, reader = _authority()
    first = _integrate(rows, manifests, reader)
    rebuilt, _, _ = _authority(generated_at="2026-08-05T00:00:00Z")  # fresh ledger, new version ids
    assert _ids(rebuilt, "observation_id") != _ids(rows, "observation_id")
    with pytest.raises(ValueError, match="absent from verified direct ledger"):
        _integrate(rebuilt, manifests, reader, generated_at="2026-08-06T00:00:00Z", as_of="2026-08-06T00:00:00Z",
                   existing_candidate_terms=first.records)


def test_a08_repeated_exhibit_in_a_later_filing_stays_a_distinct_occurrence():
    rows, manifests, reader = _authority()
    first = _integrate(rows, manifests, reader)
    all_rows, all_manifests, all_reader = _second_filing(rows, manifests)
    second = _integrate(all_rows, all_manifests, all_reader, generated_at="2026-08-08T00:00:00Z",
                        as_of="2026-08-08T00:00:00Z", existing_candidate_terms=first.records)
    assert second.counts["created"] == 5 and second.counts["unchanged"] == 5
    assert set(_ids(first.current, "logical_candidate_term_id")) < set(_ids(second.current, "logical_candidate_term_id"))
    amounts = [row for row in second.current if row["term"]["name"] == "amount_to_be_registered"]
    assert len(amounts) == 2
    assert len({row["logical_candidate_term_id"] for row in amounts}) == 2
    assert len({row["filing"]["accession"] for row in amounts}) == 2
    assert amounts[0]["normalized"] == amounts[1]["normalized"]
    for row in amounts:  # identical value, still no join, no identity, no quantity
        assert_closed_candidate_term(row)


# --- A09: only the sealed canonical procedure mints --------------------------------------------


@pytest.mark.parametrize("origin, reason", [
    *[(origin, "fact_origin_not_canonical") for origin in sorted(NON_CANONICAL_FACT_ORIGINS)],
    ("canonical_extraction", "canonical_origin_requires_sealed_procedure"),
    ("adjudicated_gold", "canonical_origin_requires_sealed_procedure"),
    ("vendor_feed", "fact_origin_unknown"),
])
def test_a09_external_nominations_are_refused_and_never_compiled(origin, reason):
    rows, manifests, reader = _authority()
    nomination = {"fact_origin": origin, "term": "amount_to_be_registered", "value": "9,999,999",
                  "instrument_id": "abc-common", "span": "Common stock 9,999,999"}
    clean = _integrate(rows, manifests, reader)
    proposed = _integrate(rows, manifests, reader, nominations=[nomination])
    assert [item.reason for item in proposed.refusals] == [reason]
    assert proposed.refusals[0].nomination_id.startswith("term-nomination")
    assert proposed.records == clean.records
    assert proposed.candidate_binding.artifact_sha256 == clean.candidate_binding.artifact_sha256


def test_a09_reference_pack_is_the_origin_authority():
    pack = load_reference_pack()
    assert {origin for origin, mints in pack.fact_origins.items() if mints} == {"canonical_extraction", "adjudicated_gold"}
    rows, manifests, reader = _authority()
    poisoned = dataclasses.replace(pack, fact_origins={**pack.fact_origins, "llm_interpretation": True})
    with pytest.raises(TermIntegrationRefusal, match="non-canonical origin 'llm_interpretation'"):
        _integrate(rows, manifests, reader, reference_pack=poisoned)
    starved = dataclasses.replace(pack, fact_origins={**pack.fact_origins, "canonical_extraction": False})
    with pytest.raises(TermIntegrationRefusal, match="canonical origin 'canonical_extraction'"):
        _integrate(rows, manifests, reader, reference_pack=starved)


@pytest.mark.parametrize("method", ["llm_interpretation", "llm_proposed_span", "manual", ""])
def test_a09_direct_term_with_non_canonical_extraction_is_refused(method):
    rows, manifests, reader = _authority()
    tampered = deepcopy(rows)
    tampered[0]["extraction"]["method"] = method
    with pytest.raises(TermIntegrationRefusal, match="not an accepted canonical procedure"):
        _integrate(tampered, manifests, reader)


# --- closed-candidate refusal ------------------------------------------------------------------


def test_closed_boundary_refuses_an_existing_candidate_that_claims_instrument_authority():
    rows, manifests, reader = _authority()
    first = _integrate(rows, manifests, reader)
    widened = deepcopy(list(first.records))
    widened[0]["authority"]["instrument_authority"] = True
    widened[0]["candidate_term_id"] = candidate_term_id_for(widened[0])  # self-consistent digest, still refused
    with pytest.raises(TermIntegrationRefusal, match="closed candidate block"):
        _integrate(rows, manifests, reader, generated_at="2026-08-05T00:00:00Z", as_of="2026-08-05T00:00:00Z",
                   existing_candidate_terms=widened)


@pytest.mark.parametrize("key", ["instrument_id", "resolved_instrument_id", "quantity_status", "resolution"])
def test_closed_boundary_refuses_any_nested_instrument_identity_key(key):
    rows, manifests, reader = _authority()
    row = deepcopy(_integrate(rows, manifests, reader).current[0])
    row["candidate"][key] = "abc-common"
    row["candidate_term_id"] = candidate_term_id_for(row)
    with pytest.raises(TermIntegrationRefusal, match="instrument identity keys present"):
        assert_closed_candidate_term(row)


def test_closed_boundary_refuses_a_forged_occurrence_identity():
    rows, manifests, reader = _authority()
    row = deepcopy(_integrate(rows, manifests, reader).current[0])
    row["logical_candidate_term_id"] = "legacy:" + row["filing"]["accession"]
    row["candidate_term_id"] = candidate_term_id_for(row)
    with pytest.raises(TermIntegrationRefusal, match="not derived from its source slot"):
        assert_closed_candidate_term(row)
    tampered = deepcopy(_integrate(rows, manifests, reader).current[0])
    tampered["normalized"]["value"] = "1"
    with pytest.raises(TermIntegrationRefusal, match="not the digest of its record"):
        assert_closed_candidate_term(tampered)


# --- support and binding discipline ------------------------------------------------------------


@pytest.mark.parametrize("support", ["unavailable", "not_built"])
def test_unsupported_direct_generation_yields_no_candidates_and_says_why(support):
    inputs = CapitalInputs((GenerationBinding("document_terms", None, support),))
    result = integrate_candidate_terms(inputs, source_manifests=[], source_reader=lambda _: None,
                                       generated_at="2026-08-04T00:00:00Z", as_of="2026-08-04T00:00:00Z")
    assert result.support == support and result.current == () and result.records == ()
    assert result.candidate_binding.support == support and result.candidate_binding.schema is None
    assert result.candidate_bundle().candidate_terms == ()


def test_missing_direct_binding_is_refused_not_assumed_empty():
    with pytest.raises(TermIntegrationRefusal, match="no document_terms binding"):
        integrate_candidate_terms(CapitalInputs(()), source_manifests=[], source_reader=lambda _: None,
                                  generated_at="2026-08-04T00:00:00Z", as_of="2026-08-04T00:00:00Z")


def test_conflicting_existing_ledgers_are_refused():
    rows, manifests, reader = _authority()
    first = _integrate(rows, manifests, reader)
    other = deepcopy(list(first.records))[:-1]
    with pytest.raises(TermIntegrationRefusal, match="differ from the candidate terms bound"):
        integrate_candidate_terms(_inputs(rows, candidate_terms=first.records), source_manifests=manifests,
                                  source_reader=reader, generated_at="2026-08-05T00:00:00Z",
                                  as_of="2026-08-05T00:00:00Z", existing_candidate_terms=other)


def test_integration_is_deterministic():
    rows, manifests, reader = _authority()
    one = _integrate(rows, manifests, reader).as_record()
    two = _integrate(deepcopy(rows), deepcopy(manifests), reader).as_record()
    assert one == two
