"""Contract/byte/correction witnesses; all filing and identity inputs are synthetic."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.biocatalyst.company_event_adapter import resolve_current_event_identity
from engine.biocatalyst.what_matters_next import compose_company_event_rows
from engine.company_intelligence.catalyst_evidence import (
    attach_catalyst_public_evidence,
    project_catalyst_public_evidence,
)
from engine.company_intelligence.contracts import ContractError, validate_company_catalyst_event
from engine.company_intelligence.documents import DocumentRevisionChain, FilingKey, SourceDocument, text_span
from engine.company_intelligence.events import project_catalyst_event
from engine.fundamental_forensics.disclosure_diff import normalize_filing
from lib.dataos.identity import IssuerMaster, VendorAliasTable

CIK = "0001234567"
ACCESSION = "0001234567-26-000001"
CUTOFF = "2026-10-19T00:00:00Z"
ROOT = Path(__file__).resolve().parents[1]
BODY = "<html><body><p>Synthetic issuer: expects a study update in Q4. μ</p></body></html>"
LITERAL = "expects a study update in Q4"


def _source(body=BODY, *, accession=ACCESSION, url=None):
    return normalize_filing({
        "entity_cik": CIK, "accession": accession, "form": "8-K",
        "filed_at": "2026-10-18", "report_date": None,
        "source_url": url or (
            "https://www.sec.gov/Archives/edgar/data/1234567/"
            + accession.replace("-", "") + "/synthetic.htm"
        ),
        "content": body, "content_type": "html",
    })


def _event(source, *, anchor=None, revision="revision-1"):
    return project_catalyst_event(
        company_id="cik:" + CIK, issuer_cik=CIK,
        source_namespace="issuer_disclosure",
        native_event_key=(anchor or source.document_id) + "#claim/readout",
        event_family="issuer_readout_guidance", revision_ref=revision,
        revision_is_current=True, occurrence="uncorroborated",
        timing={
            "state": "consistent", "source_class": "issuer_guided",
            "lower_date": "2026-10-01", "upper_date": "2026-12-31",
            "precision": "quarter", "source_timezone": None,
            "source_wording": "Synthetic issuer expects a study update in Q4.",
            "evidence_refs": [],
        },
        source_available_at="2026-10-18T16:00:00Z",
        observed_at="2026-10-18T16:02:00Z",
        document_refs=[source.document_id], public_evidence=[],
        asset_mentions=[], relationship_claims=[], generation_cutoff=CUTOFF,
    )


def _case(body=BODY, *, url=None, source=None, event=None, literal=LITERAL):
    source = source or _source(body, url=url)
    event = event or _event(source)
    document = SourceDocument(
        document_id=source.document_id, event_id=event["event_id"],
        document_kind="release", source_class="issuer_release",
        content_sha256=source.source_sha256, content_bytes=len(source.raw_source.encode("utf-8")),
        filing_key=FilingKey(CIK, source.accession),
        fetched_at=datetime(2026, 10, 18, 16, 1, tzinfo=timezone.utc),
        available_at=datetime(2026, 10, 18, 16, tzinfo=timezone.utc),
        rights_profile="rp_public_primary_v1", rights_state="public_primary",
    )
    raw = source.raw_source.encode("utf-8")
    start = raw.index(literal.encode("utf-8"))
    span = text_span(
        document_id=document.document_id, document_version=document.revision,
        body_sha256=document.content_sha256, segment_index=0,
        segment_text=source.raw_source, start_byte=start,
        end_byte=start + len(literal.encode("utf-8")), text=literal,
        rights_profile=document.rights_profile,
    )
    return event, document, source, span


def _project(case, **overrides):
    event, document, source, span = case
    args = {
        "event": event, "document_chain": DocumentRevisionChain((document,)),
        "source": source, "span": span, "generation_cutoff": CUTOFF,
    }
    args.update(overrides)
    return project_catalyst_public_evidence(**args)


def _rows(event):
    identity = resolve_current_event_identity(
        event, issuer_master=IssuerMaster.from_records([]),
        alias_table=VendorAliasTable.from_records([]),
        identity_cut_date=date(2026, 10, 18),
        identity_observed_at="2026-10-18T17:00:00Z",
        generation_cutoff=CUTOFF,
    )
    return compose_company_event_rows(
        event, identity_projection=identity, source_health="current",
        evaluation_cutoff=CUTOFF, anchor_date="2026-10-19",
    )


def test_existing_owners_replay_source_context_through_real_bio_composer():
    case = _case()
    before = deepcopy(case[0])
    evidence = _project(case)
    enriched = attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff=CUTOFF)
    row = _rows(enriched)[0]
    assert case[0] == before
    assert enriched["schema_version"] == "1.1.0"
    assert row["evidence"] == [evidence]
    assert evidence["event_revision_ref"] == case[0]["revision_ref"]
    assert evidence["document_content_sha256"] == sha256(case[2].raw_source.encode("utf-8")).hexdigest()
    assert evidence["role"] == "source_context" and evidence["excerpt"] is None
    assert row["assets"] == row["relationships"] == []
    assert row["economic_exposure_state"] == "unresolved"
    assert row["revision_summary"]["last_material_revision_known_at"] is None
    assert all(row[name]["state"] == "NOT_ESTIMABLE" for name in (
        "probability", "materiality", "historical_response", "incorporation"
    ))
    assert evidence["authority"]["decision_authority"] is False
    encoded = json.dumps(evidence)
    assert BODY not in encoded and LITERAL not in encoded
    assert not any(key in evidence for key in ("receipt", "locator", "raw_source", "source_locator"))
    row["evidence"][0]["authority"]["allowed_uses"].append("mutated-consumer")
    assert enriched["public_evidence"][0]["authority"]["allowed_uses"] == ["display", "context", "explain"]


def test_v1_0_keeps_empty_evidence_semantics_and_its_frozen_schema():
    case = _case()
    assert _rows(case[0])[0]["evidence"] == []
    payload = deepcopy(case[0])
    payload["public_evidence"] = [_project(case)]
    with pytest.raises(ContractError, match="not admitted in the first producer slice"):
        validate_company_catalyst_event(payload, generation_cutoff=CUTOFF)
    schema = json.loads((ROOT / "contracts/company_intelligence/company_catalyst_event.v1.schema.json").read_text())
    assert schema["properties"]["public_evidence"] == {"const": []}
    assert list(Draft202012Validator(schema).iter_errors(case[0])) == []
    assert list(Draft202012Validator(schema).iter_errors(payload))


def test_new_wire_schemas_validate_actual_owner_output_without_external_refs():
    case = _case()
    evidence = _project(case)
    event = attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff=CUTOFF)
    for path, payload in (
        ("company_catalyst_public_evidence.v1.schema.json", evidence),
        ("company_catalyst_event.v1_1.schema.json", event),
    ):
        schema = json.loads((ROOT / "contracts/company_intelligence" / path).read_text())
        Draft202012Validator.check_schema(schema)
        assert list(Draft202012Validator(schema).iter_errors(payload)) == []
    bad = deepcopy(event)
    bad["public_evidence"][0]["excerpt"] = "unapproved excerpt"
    schema = json.loads((ROOT / "contracts/company_intelligence/company_catalyst_event.v1_1.schema.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(bad))


@pytest.mark.parametrize("field,value", [
    ("rights_state", "unknown"), ("rights_state", "licensed"),
    ("rights_state", "internal_only"), ("rights_profile", "rp_unknown_v1"),
    ("source_class", "third_party"), ("holds_bytes", False),
    ("content_bytes", 1), ("content_sha256", "0" * 64),
    ("superseded_by_document_id", "a-newer-document"),
    ("document_kind", "release_duplicate"), ("available_at", None), ("fetched_at", None),
])
def test_unadmitted_or_unverifiable_document_is_not_a_public_citation(field, value):
    case = _case()
    changed = replace(case[1], **{field: value})
    with pytest.raises(ContractError):
        _project(case, document_chain=DocumentRevisionChain((changed,)))


@pytest.mark.parametrize("field,value", [
    ("document_id", "another-document"),
    ("event_id", "evt_source_" + "0" * 64),
    ("filing_key", FilingKey("0007654321", ACCESSION)),
])
def test_document_association_cannot_be_guessed_from_matching_body(field, value):
    case = _case()
    document = replace(case[1], **{field: value})
    with pytest.raises(ContractError):
        _project(case, document_chain=DocumentRevisionChain((document,)))


def test_url_substitution_with_old_admitted_document_identity_is_rejected():
    case = _case()
    source = replace(case[2], source_url=case[2].source_url.replace("synthetic.htm", "another.htm"))
    with pytest.raises(ContractError, match="disclosure identity"):
        _project(case, source=source)


@pytest.mark.parametrize("url", [
    "https://www.sec.gov/Archives/edgar/data/7654321/000123456726000001/synthetic.htm",
    "https://www.sec.gov/Archives/edgar/data/1234567/000123456726000002/synthetic.htm",
    "https://issuer.example/synthetic.htm",
    "https://localhost/private.htm",
    "https://www.sec.gov/Archives/edgar/data/1234567/000123456726000001/synthetic.htm?secret=1",
    "https://user:secret@www.sec.gov/Archives/edgar/data/1234567/000123456726000001/synthetic.htm",
])
def test_only_bound_public_sec_document_locators_enter_this_slice(url):
    case = _case(url=url)
    with pytest.raises(ContractError, match="SEC locator"):
        _project(case)


def test_exact_source_bytes_cannot_be_replaced_after_receipt():
    case = _case()
    altered = replace(case[2], raw_source=case[2].raw_source.replace("Q4", "Q1"))
    with pytest.raises(ContractError, match="document bytes"):
        _project(case, source=altered)


def test_partial_segment_zero_cannot_masquerade_as_whole_document():
    case = _case()
    span = text_span(
        document_id=case[1].document_id, document_version=1,
        body_sha256=case[1].content_sha256, segment_index=0,
        segment_text=LITERAL, start_byte=0, end_byte=len(LITERAL), text=LITERAL,
        rights_profile="rp_public_primary_v1",
    )
    with pytest.raises(ContractError, match="complete source"):
        _project(case, span=span)


@pytest.mark.parametrize("field,value", [
    ("document_id", "unrelated-document"), ("document_version", 2),
    ("document_version", True), ("span_id", "span_" + "0" * 20),
    ("rights_profile", "rp_unknown_v1"),
])
def test_span_association_identity_and_rights_are_replayed(field, value):
    case = _case()
    span = replace(case[3], **{field: value})
    with pytest.raises(ContractError):
        _project(case, span=span)


def test_future_document_observation_cannot_back_an_earlier_event():
    case = _case()
    future = replace(case[1], fetched_at=datetime(2026, 10, 18, 16, 3, tzinfo=timezone.utc))
    with pytest.raises(ContractError, match="clocks"):
        _project(case, document_chain=DocumentRevisionChain((future,)))


def test_subsecond_source_observation_is_retained_without_rounding_back():
    case = _case()
    precise = replace(case[1], fetched_at=datetime(2026, 10, 18, 16, 1, 0, 987654, tzinfo=timezone.utc))
    evidence = _project(case, document_chain=DocumentRevisionChain((precise,)))
    assert evidence["observed_at"] == "2026-10-18T16:01:00.987654Z"


def test_attachment_cannot_retime_evidence_or_relabel_it_for_another_event_revision():
    case = _case()
    evidence = _project(case)
    with pytest.raises(ContractError, match="same owner projection cut"):
        attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff="2026-10-19T01:00:00Z")
    corrected = deepcopy(case[0])
    corrected["revision_ref"] = "revision-2"
    with pytest.raises(ContractError, match="selected event revision"):
        attach_catalyst_public_evidence(corrected, [evidence], generation_cutoff=CUTOFF)
    with pytest.raises(ContractError, match="generation cutoff"):
        attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff="2026-10-18T23:59:59Z")


@pytest.mark.parametrize("field,value", [
    ("excerpt", "unapproved source text"),
    ("role", "supports_claim"),
    ("scope", "point_in_time_backtest"),
    ("document_ref", "another-document"),
    ("span_end_byte", 99_999_999),
    ("document_revision", True),
])
def test_public_consumer_rejects_promoted_or_unbound_wire_fields(field, value):
    case = _case()
    evidence = _project(case)
    evidence[field] = value
    with pytest.raises(ContractError):
        attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff=CUTOFF)


def test_extra_private_field_and_duplicate_source_spans_fail_closed():
    case = _case()
    evidence = _project(case)
    private = deepcopy(evidence)
    private["private_storage_key"] = "/private/source"
    with pytest.raises(ContractError):
        attach_catalyst_public_evidence(case[0], [private], generation_cutoff=CUTOFF)
    with pytest.raises(ContractError, match="duplicate"):
        attach_catalyst_public_evidence(case[0], [evidence, evidence], generation_cutoff=CUTOFF)


def test_source_correction_preserves_event_identity_and_uses_new_document_span():
    first = _case()
    first_evidence = _project(first)
    new_source = _source(BODY.replace("Q4", "Q1"), accession="0001234567-26-000002")
    new_event = _event(new_source, anchor=first[2].document_id, revision="revision-2")
    second = _case(source=new_source, event=new_event, literal=LITERAL.replace("Q4", "Q1"))
    new_document = replace(
        second[1], revision=2, document_kind="release_amendment",
        supersedes_document_id=first[1].document_id,
    )
    new_span = replace(second[3], document_version=2)
    chain = DocumentRevisionChain((first[1], new_document))
    new_evidence = _project(second, document_chain=chain, span=new_span)
    assert new_event["event_id"] == first[0]["event_id"]
    assert new_evidence["document_content_sha256"] != first_evidence["document_content_sha256"]
    assert new_evidence["document_revision"] == 2
    assert new_evidence["span_ref"] != first_evidence["span_ref"]
    with pytest.raises(ContractError, match="document/span"):
        _project(second, document_chain=chain, span=first[3])
    with pytest.raises(ContractError, match="selected event revision"):
        attach_catalyst_public_evidence(new_event, [first_evidence], generation_cutoff=CUTOFF)
    row = _rows(attach_catalyst_public_evidence(new_event, [new_evidence], generation_cutoff=CUTOFF))[0]
    assert row["event_revision_ref"] == "revision-2"
    assert row["evidence"] == [new_evidence]
    assert row["revision_summary"]["last_material_revision_known_at"] is None


def _api_inputs(event):
    """Existing owner wire, synthetic identity/cut; no admission receipt is claimed."""
    from engine.company_intelligence.contracts import canonical_json_sha256
    from tests.test_biocatalyst_wmn_publication import _wmn_inputs

    master = IssuerMaster.from_records([{
        "security_id": "SEC:US-XNAS-SYNB", "issuer_id": "ISS:US-XNAS-SYNB",
        "issuer_state": "RESOLVED", "issuer_cik": CIK,
        "listing_key": "US-XNAS-SYNB", "security_state": None, "superseded_by": None,
    }])
    aliases = VendorAliasTable.from_records([{
        "vendor": "store", "vendor_symbol": "SYNB", "security_id": "SEC:US-XNAS-SYNB",
        "valid_from": None, "valid_to": None,
    }])
    identity = resolve_current_event_identity(
        event, issuer_master=master, alias_table=aliases,
        identity_cut_date=date(2026, 10, 18), identity_observed_at="2026-10-18T17:00:00Z",
        generation_cutoff=CUTOFF,
    )
    inputs = _wmn_inputs()
    inputs["events"] = [event]
    inputs["identity_projection"] = {event["event_id"]: identity}
    inputs["input_cut"]["cutoff"] = CUTOFF
    inputs["input_cut"]["members"] = [{
        "contract_id": "company_catalyst_event.v1", "ref": event["event_id"],
        "sha256": canonical_json_sha256(event),
        "observed_at": event["observed_at"], "accepted_at": CUTOFF,
        "availability": "available",
    }, {
        "contract_id": "dataos_issuer_master.current",
        "ref": "synthetic-master-cut-2026-10-18", "sha256": "2" * 64,
        "observed_at": "2026-10-18T17:00:00Z", "accepted_at": "2026-10-18T17:00:00Z",
        "availability": "available",
    }]
    inputs["coverage"]["declared_universe_ref"] = "synthetic-company-evidence-contract-case"
    return inputs


def test_real_api_list_and_detail_preserve_the_same_source_context(monkeypatch):
    import app.biocatalyst as api
    from tests.test_biocatalyst_wmn_api import _app, _projection, GENERATION

    case = _case()
    evidence = _project(case)
    event = attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff=CUTOFF)
    inputs = _api_inputs(event)
    monkeypatch.setattr(api, "_wmn_now", lambda: datetime(2026, 10, 19, tzinfo=timezone.utc))
    with _app(lambda: (_projection(inputs), {})) as client:
        listing = client.get("/api/biocatalyst/v1/what-matters-next")
        detail = client.get("/api/biocatalyst/v1/what-matters-next/detail", params={
            "generation_id": GENERATION, "event_fact_ref": event["event_id"],
            "issuer_id": "ISS:US-XNAS-SYNB",
        })
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["rows"][0]["evidence"] == detail.json()["event"]["evidence"] == [evidence]
    for response in (listing, detail):
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization"
        assert BODY not in response.text and "source_locator" not in response.text
    assert detail.json()["event"]["revision_summary"]["last_material_revision_known_at"] is None


def test_api_refuses_evidence_that_does_not_bind_the_input_cut(monkeypatch):
    import app.biocatalyst as api
    from tests.test_biocatalyst_wmn_api import _app, _projection

    case = _case()
    event = attach_catalyst_public_evidence(case[0], [_project(case)], generation_cutoff=CUTOFF)
    inputs = _api_inputs(event)
    inputs["events"][0]["public_evidence"][0]["event_revision_ref"] = "unbound-revision"
    monkeypatch.setattr(api, "_wmn_now", lambda: datetime(2026, 10, 19, tzinfo=timezone.utc))
    with _app(lambda: (_projection(inputs), {})) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next")
    assert response.status_code == 503
    assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}


@pytest.mark.parametrize("field,value", [
    ("observed_at", "2026-10-18T16:01:00.0000001Z"),
    ("projection_cutoff", "2026-10-19T00:00:00+00:00"),
])
def test_wire_does_not_truncate_precision_or_silently_change_clock_encoding(field, value):
    case = _case()
    evidence = _project(case)
    evidence[field] = value
    with pytest.raises(ContractError, match="six fractional digits"):
        attach_catalyst_public_evidence(case[0], [evidence], generation_cutoff=CUTOFF)


@pytest.mark.parametrize("change", [
    {"revision_is_current": False}, {"occurrence": "cancelled"}, {"occurrence": "withdrawn"},
])
def test_fresh_projection_does_not_admit_a_retired_event_revision(change):
    case = _case()
    event = {**case[0], **change}
    with pytest.raises(ContractError, match="current usable event"):
        _project(case, event=event)


@pytest.mark.parametrize("field,value", [
    ("source_available_at", "2026-10-18T16:00:00.0000001Z"),
    ("observed_at", "2026-10-18T16:02:00.0000001Z"),
    ("observed_at", "2026-10-19T00:00:00.0000001Z"),
])
def test_r2_cannot_round_an_unsupported_parent_event_clock_into_the_cut(field, value):
    case = _case()
    event = {**case[0], field: value}
    with pytest.raises(ContractError, match="six fractional digits"):
        _project(case, event=event)


@pytest.mark.parametrize("cutoff", [
    "2026-10-19T00:00:00.0000001Z",
    "2026-10-19T00:00:00+00:00",
])
def test_r2_generation_cut_is_checked_before_precision_or_encoding_is_lost(cutoff):
    with pytest.raises(ContractError, match="six fractional digits"):
        _project(_case(), generation_cutoff=cutoff)


def test_v1_1_preserves_same_second_source_and_event_knowledge_through_real_api(monkeypatch):
    import app.biocatalyst as api
    from tests.test_biocatalyst_wmn_api import _app, _projection

    case = _case()
    event = {**case[0], "observed_at": "2026-10-18T16:01:00.200001Z"}
    document = replace(case[1], fetched_at=datetime(
        2026, 10, 18, 16, 1, 0, 100001, tzinfo=timezone.utc
    ))
    # The old version's behavior remains explicit; R2 uses its new version.
    assert validate_company_catalyst_event(
        event, generation_cutoff=CUTOFF
    )["observed_at"] == "2026-10-18T16:01:00Z"
    evidence = _project(case, event=event, document_chain=DocumentRevisionChain((document,)))
    enriched = attach_catalyst_public_evidence(event, [evidence], generation_cutoff=CUTOFF)
    assert enriched["observed_at"] == event["observed_at"]
    assert evidence["observed_at"] == "2026-10-18T16:01:00.100001Z"
    assert validate_company_catalyst_event(enriched, generation_cutoff=CUTOFF) == enriched
    assert event["schema_version"] == "1.0.0"
    monkeypatch.setattr(api, "_wmn_now", lambda: datetime(2026, 10, 19, tzinfo=timezone.utc))
    with _app(lambda: (_projection(_api_inputs(enriched)), {})) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next")
    assert response.status_code == 200
    assert response.json()["rows"][0]["evidence"] == [evidence]


def test_v1_1_parent_observation_one_microsecond_after_cut_is_refused():
    event = {**_case()[0], "schema_version": "1.1.0",
             "observed_at": "2026-10-19T00:00:00.000001Z"}
    with pytest.raises(ContractError, match="exceeds generation cutoff"):
        validate_company_catalyst_event(event, generation_cutoff=CUTOFF)


def test_internal_upgrade_cannot_smuggle_nonempty_evidence_through_v1_0():
    case = _case()
    evidence = _project(case)
    event = {**case[0], "public_evidence": [evidence]}
    with pytest.raises(ContractError, match="not admitted in the first producer slice"):
        attach_catalyst_public_evidence(event, [evidence], generation_cutoff=CUTOFF)
