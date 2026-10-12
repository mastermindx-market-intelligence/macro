"""Wholly synthetic analyst journeys; no production contract/admission witness."""
from copy import deepcopy
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.company_intelligence.relationship_candidates import SCHEMA, inspect_candidate
from engine.earnings_release.receipts import receipt_for_char_span, sha256_text
from lib.dataos.registry import DatasetContract, DatasetStatus, Layer, Registry
from lib.dataos.temporal import TemporalProfile

# Invented parties/products and UTF-8 prefix; CRLF preservation matters.
SOURCE = (
    "SYNTHETIC — café disclosure.\r\n"
    "<p>Aurora plans to integrate Widget in Boreal systems next year.</p>\r\n"
    "SYNTHETIC end matter."
)
SPAN = "<p>Aurora plans to integrate Widget in Boreal systems next year.</p>"


def make_candidate(source=SOURCE, span=SPAN):
    start = source.index(span)
    receipt = receipt_for_char_span(
        source=source, source_sha256=sha256_text(source),
        char_start=start, char_end=start + len(span),
    ).to_dict()
    return {
        "schema": SCHEMA,
        "candidate_id": "synthetic:relation:1",
        "document": {
            "document_id": "synthetic:issuer:1", "version": "synthetic-v1",
            "source_ref": "synthetic:test-only", "published_date": "2024-02-26",
        },
        "dataset_id": None, "temporal_row": None, "receipt": receipt,
        "assertion": {
            "kind": "product_integration", "subject_label": "Aurora",
            "object_label": "Boreal", "product_scope": "Widget",
            "lifecycle": "planned", "magnitude": None,
        },
        "revision": {"supersedes_candidate_id": None, "relation": "original"},
        "identity_annotations": None,
    }


def inspect(candidate=None, **kwargs):
    return inspect_candidate(candidate if candidate is not None else make_candidate(),
                             source=kwargs.pop("source", SOURCE), **kwargs)


def assert_refused(result, code=None):
    assert result["inspection_status"] == "REFUSED"
    assert result["current_candidate_view"] is None
    assert result["admission"] == "NOT_ADMITTED"
    assert result["graph1_projection"] is None
    assert not any(result["authority"].values())
    assert result["content_boundary"]["machine_replayed_support_text"] == "OMITTED"
    assert result["content_boundary"]["quote_free_payload"] == "NOT_CERTIFIED"
    assert result["content_boundary"]["public_safe_payload"] == "NOT_CERTIFIED"
    assert result["content_boundary"]["public_export"] == "NOT_AUTHORIZED"
    assert set(result["annotation_trust"].values()) == {"caller_supplied_not_authenticated"}
    if code:
        assert result["refusal"]["code"] == code


def synthetic_registry(profile=TemporalProfile.EVENT, status=DatasetStatus.PRODUCED):
    # A explicitly synthetic native contract, never a production admission claim.
    return Registry([DatasetContract(
        dataset_id="synthetic_relationship_rows", layer=Layer.L0_SOURCE,
        owner="synthetic-test", producer="synthetic-test", storage="synthetic",
        format="synthetic", grain=("candidate_id", "document_id", "document_version"),
        schema={k: {"type": "string"} for k in (
            "candidate_id", "document_id", "document_version", "source_sha256",
        )}, temporal_profile=profile, version="synthetic-v1", status=status,
    )])


def with_temporal(candidate=None):
    candidate = deepcopy(candidate or make_candidate())
    candidate["dataset_id"] = "synthetic_relationship_rows"
    candidate["temporal_row"] = {
        "candidate_id": candidate["candidate_id"],
        "document_id": candidate["document"]["document_id"],
        "document_version": candidate["document"]["version"],
        "source_sha256": candidate["receipt"]["source_sha256"],
        "event_at": "2024-02-26T10:00:00Z", "published_at": "2024-02-26T10:00:00Z",
        "ingested_at": "2024-02-26T11:00:00Z",
    }
    return candidate


def test_positive_manual_planned_product_is_deterministic_and_ephemeral():
    candidate = make_candidate()
    before = deepcopy(candidate)
    first = inspect(candidate)
    assert first == inspect(candidate)
    assert candidate == before
    assert first["inspection_status"] == "INSPECTABLE"
    assert first["assertion_basis"] == "manual_review"
    assert first["support"]["status"] == "STRUCTURALLY_REPLAYED"
    assert first["support"]["semantic_adjudication"] == "NOT_PERFORMED"
    assert "replayed_value_text" not in first["support"]
    view = first["current_candidate_view"]
    assert view["assertion"]["lifecycle"] == "planned"
    assert view["scope"] == "product_only" and view["bilateral_candidate"] is True
    for field in ("shipments", "revenue", "economic_weight", "theme_membership"):
        assert view[field] is None
    assert first["source_provenance"]["published_date"] == "2024-02-26"
    assert first["temporal"]["historical_system_replay"] is False
    assert all(first["gaps"][axis] for axis in ("native_adoption", "time", "identity", "rights"))
    assert not any(first["authority"].values())


def test_private_support_opt_in_only_structurally_replays_normalized_text():
    result = inspect(include_support_text=True)
    assert result["support"]["replayed_value_text"] == (
        "Aurora plans to integrate Widget in Boreal systems next year."
    )
    assert result["gaps"]["rights"] and result["admission"] == "NOT_ADMITTED"
    assert result["content_boundary"]["machine_replayed_support_text"] == "INCLUDED"
    assert result["content_boundary"]["public_safe_payload"] == "NOT_CERTIFIED"


def test_fake_sec_metadata_is_echoed_untrusted_despite_body_hash_match():
    candidate = make_candidate()
    candidate["document"].update(
        source_ref="https://www.sec.gov/Archives/edgar/data/0000000000/fabricated.htm",
        published_date="1900-01-01", version="caller-claims-issuer-authentication",
    )
    result = inspect(candidate)
    assert result["inspection_status"] == "INSPECTABLE"
    provenance = result["source_provenance"]
    for key, value in candidate["document"].items():
        assert provenance[key] == value
    assert provenance["metadata_authenticity"] == "caller_supplied_not_authenticated"
    assert provenance["source_hash_status"] == "matched_supplied_bytes"
    assert provenance["source_sha256"] == sha256_text(SOURCE)
    assert provenance["source_credibility"] == "not_verified"
    assert "source_credibility_and_document_metadata_not_authenticated" in result["limitations"]
    assert result["annotation_trust"]["document_annotations"] == "caller_supplied_not_authenticated"


@pytest.mark.parametrize("include_support_text", [False, True])
def test_full_support_sentence_in_scope_is_echoed_with_explicit_content_boundary(include_support_text):
    candidate = make_candidate()
    sentence = candidate["receipt"]["value_text"]
    candidate["assertion"]["product_scope"] = sentence
    candidate["identity_annotations"] = {"subject_id": sentence, "object_id": None}
    result = inspect(candidate, include_support_text=include_support_text)
    assert result["inspection_status"] == "INSPECTABLE"
    view = result["current_candidate_view"]
    assert view["assertion"]["product_scope"] == sentence
    assert view["identity_annotations"]["subject_id"] == sentence
    assert view["canonical_subject_id"] is None
    assert ("replayed_value_text" in result["support"]) is include_support_text
    boundary = result["content_boundary"]
    assert boundary["annotations"] == "echoed_as_supplied_may_contain_source_text"
    assert boundary["machine_replayed_support_text"] == ("INCLUDED" if include_support_text else "OMITTED")
    assert boundary["quote_free_payload"] == boundary["public_safe_payload"] == "NOT_CERTIFIED"
    assert boundary["public_export"] == "NOT_AUTHORIZED"
    assert set(result["annotation_trust"].values()) == {"caller_supplied_not_authenticated"}
    assert result["gaps"]["rights"] and result["admission"] == "NOT_ADMITTED"


@pytest.mark.parametrize("changed", [
    SOURCE + " changed unrelated footer",
    SOURCE.replace("café", "cafe"),
    SOURCE.replace("Widget", "Gadget"),
])
def test_full_source_revision_changes_fail(changed):
    assert_refused(inspect(source=changed))


@pytest.mark.parametrize("field,value", [
    ("char_start", True), ("char_end", "123"), ("byte_start", 2.5),
    ("byte_end", -1), ("span_bytes", False), ("source_sha256", 1),
    ("value_text", ["Aurora"]),
])
def test_receipt_prechecks_refuse_native_coercion(field, value):
    candidate = make_candidate()
    candidate["receipt"][field] = value
    assert_refused(inspect(candidate))


@pytest.mark.parametrize("field", ["char_start", "char_end", "byte_start", "byte_end", "span_bytes"])
def test_shifted_utf8_coordinates_fail(field):
    candidate = make_candidate()
    candidate["receipt"][field] += 1
    assert_refused(inspect(candidate))


def test_repeated_span_cannot_borrow_different_character_occurrence():
    source = SOURCE + SPAN
    candidate = make_candidate(source=source)
    start = source.rindex(SPAN)
    candidate["receipt"].update(char_start=start, char_end=start + len(SPAN))
    assert_refused(inspect(candidate, source=source), "RECEIPT_COORDINATES_DISAGREE")


def test_normalized_value_and_value_hash_are_replayed():
    candidate = make_candidate()
    candidate["receipt"]["value_text"] = "fabricated normalized content"
    candidate["receipt"]["value_text_sha256"] = sha256_text("fabricated normalized content")
    assert_refused(inspect(candidate), "SOURCE_REPLAY_FAILED")
    candidate = make_candidate()
    candidate["receipt"]["value_text_sha256"] = "0" * 64
    assert_refused(inspect(candidate), "SOURCE_REPLAY_FAILED")


def test_empty_span_and_empty_visible_support_fail():
    candidate = make_candidate()
    candidate["receipt"]["char_end"] = candidate["receipt"]["char_start"]
    assert_refused(inspect(candidate), "RECEIPT_SPAN_EMPTY_OR_INVALID")
    whitespace = "SYNTHETIC <p> </p> footer"
    candidate = make_candidate(source=whitespace, span="<p> </p>")
    assert_refused(inspect(candidate, source=whitespace), "RECEIPT_SUPPORT_EMPTY")


def test_ambiguous_party_and_missing_source_local_anchor_refuse():
    candidate = make_candidate()
    candidate["assertion"]["object_label"] = "Aurora"
    assert_refused(inspect(candidate), "SUPPORT_AMBIGUOUS")
    candidate = make_candidate()
    candidate["assertion"]["product_scope"] = "all Aurora products"
    assert_refused(inspect(candidate), "SOURCE_LOCAL_LABEL_UNSUPPORTED")


@pytest.mark.parametrize("value", [False, True, 0, 1, "unknown", {}, []])
def test_unknown_magnitude_never_accepts_fabricated_number_or_zero(value):
    candidate = make_candidate()
    candidate["assertion"]["magnitude"] = value
    assert_refused(inspect(candidate), "QUANTITY_MUST_BE_NULL")


@pytest.mark.parametrize("lifecycle", ["realized_shipments", "delivered", "guaranteed_future_revenue"])
def test_product_integration_cannot_claim_deliveries(lifecycle):
    candidate = make_candidate()
    candidate["assertion"]["lifecycle"] = lifecycle
    assert_refused(inspect(candidate), "LIFECYCLE_UNSUPPORTED")


@pytest.mark.parametrize("kind,lifecycle,disposition,bilateral", [
    ("supplier_roster", "listed", "roster_observation_only", False),
    ("framework_agreement", "in_force", "framework_candidate_no_deliveries", True),
    ("administrative_party", "appointed", "administrative_role_only", False),
    ("anonymous_counterparty", "announced", "counterparty_unresolved", False),
    ("thematic_similarity", "observed", "non_relationship_observation", False),
    ("market_correlation", "observed", "non_relationship_observation", False),
])
def test_manual_taxonomy_preserves_disposition_without_role_or_quantity_upgrade(
    kind, lifecycle, disposition, bilateral,
):
    # Each manual category has its own honest synthetic source sentence.
    sentences = {
        "supplier_roster": "Aurora lists Boreal in its Widget supplier roster.",
        "framework_agreement": "Aurora and Boreal signed a Widget framework agreement; no deliveries are stated.",
        "administrative_party": "Aurora appointed Boreal as trustee for Widget notes.",
        "anonymous_counterparty": "Aurora plans Widget for an unnamed customer.",
        "thematic_similarity": "Aurora and Boreal share a Widget theme.",
        "market_correlation": "Aurora and Boreal exhibit Widget market correlation.",
    }
    span = "<p>" + sentences[kind] + "</p>"
    source = "SYNTHETIC category fixture.\\r\\n" + span
    candidate = make_candidate(source=source, span=span)
    candidate["assertion"].update(kind=kind, lifecycle=lifecycle)
    if kind == "anonymous_counterparty":
        candidate["assertion"]["object_label"] = None
    result = inspect(candidate, source=source)
    assert result["inspection_status"] == "INSPECTABLE"
    view = result["current_candidate_view"]
    assert view["disposition"] == disposition
    assert view["bilateral_candidate"] is bilateral
    assert view["assertion"]["product_scope"] == "Widget"
    assert view["shipments"] is None and view["economic_weight"] is None
    assert result["graph1_projection"] is None


def test_anonymous_label_must_be_null_and_no_generic_related_fallback():
    candidate = make_candidate()
    candidate["assertion"]["kind"] = "anonymous_counterparty"
    assert_refused(inspect(candidate), "ANONYMOUS_PARTY_MUST_BE_NULL")
    candidate["assertion"]["kind"] = "RELATED"
    assert_refused(inspect(candidate), "KIND_UNSUPPORTED")


@pytest.mark.parametrize("as_of", ["2024-02-27", "2024-02-27T00:00:00", date(2024, 2, 27), True])
def test_date_and_naive_cutoff_are_not_promoted_to_instants(as_of):
    assert_refused(inspect(as_of=as_of), "NATIVE_TEMPORAL_REFUSAL")


def test_no_native_registry_dataset_or_profile_makes_as_of_unavailable():
    cutoff = "2024-02-27T00:00:00Z"
    assert_refused(inspect(as_of=cutoff), "AS_OF_REGISTRY_REQUIRED")
    assert_refused(inspect(as_of=cutoff, registry=Registry([])), "AS_OF_DATASET_REQUIRED")
    candidate = with_temporal()
    assert_refused(inspect(candidate, as_of=cutoff, registry=Registry([])), "AS_OF_DATASET_UNREGISTERED")
    contract = next(iter(synthetic_registry()))
    bad = Registry([replace(contract, temporal_profile="GUESS")])
    assert_refused(inspect(candidate, as_of=cutoff, registry=bad), "AS_OF_PROFILE_INVALID")


@pytest.mark.parametrize("status", [DatasetStatus.PROPOSED, DatasetStatus.RETIRED])
def test_unproduced_native_contract_never_opens_historical_path(status):
    assert_refused(inspect(with_temporal(), as_of="2024-02-27T00:00:00Z",
                           registry=synthetic_registry(status=status)), "AS_OF_DATASET_NOT_PRODUCED")


def test_unrelated_dataset_profile_cannot_be_borrowed():
    contract = next(iter(synthetic_registry()))
    unrelated = Registry([replace(contract, grain=("symbol", "date"), schema={})])
    assert_refused(inspect(with_temporal(), as_of="2024-02-27T00:00:00Z",
                           registry=unrelated), "AS_OF_DATASET_GRAIN_UNRELATED")


def test_derived_native_profile_refuses_pit_before_relation_view():
    candidate = with_temporal()
    candidate["temporal_row"].update(
        computed_at="2024-02-26T12:00:00Z", code_version="synthetic-v1", input_cutoffs={},
    )
    assert_refused(inspect(candidate, as_of="2024-02-27T00:00:00Z",
                           registry=synthetic_registry(TemporalProfile.DERIVED)),
                   "NATIVE_TEMPORAL_REFUSAL")


def synthetic_profile_candidate(profile):
    """Explicitly synthetic native rows for the bounded probe's accepted shapes."""
    candidate = with_temporal()
    row = candidate["temporal_row"]
    if profile is TemporalProfile.BARS:
        row.update(period_start="2024-02-01", period_end="2024-02-26")
    elif profile is TemporalProfile.REVISABLE_RELEASE:
        row.update(period_end="2024-02-26", revision_seq=0)
    elif profile is TemporalProfile.INTELLIGENCE:
        row.update(
            computed_at="2024-02-26T12:00:00Z", served_at="2024-02-26T12:01:00Z",
            code_version="synthetic-v1",
            input_cutoffs={"synthetic_input": "2024-02-26T11:00:00Z"},
            data_cutoff_at="2024-02-26T11:00:00Z", expires_at="2024-02-28T12:00:00Z",
        )
    return candidate


@pytest.mark.parametrize("profile,changes", [
    (TemporalProfile.BARS, {"period_start": []}),
    (TemporalProfile.BARS, {"period_end": False}),
    (TemporalProfile.BARS, {"period_start": "2024-02-30"}),
    (TemporalProfile.BARS, {"period_end": "2024-02-26T10:00:00"}),
    (TemporalProfile.REVISABLE_RELEASE, {"period_end": {}}),
    (TemporalProfile.REVISABLE_RELEASE, {"revision_seq": False}),
    (TemporalProfile.REVISABLE_RELEASE, {"revision_seq": -1}),
    (TemporalProfile.REVISABLE_RELEASE, {"revision_seq": "0"}),
    (TemporalProfile.INTELLIGENCE, {"code_version": False}),
    (TemporalProfile.INTELLIGENCE, {"code_version": " "}),
    (TemporalProfile.INTELLIGENCE, {"input_cutoffs": False}),
    (TemporalProfile.INTELLIGENCE, {"input_cutoffs": {}}),
    (TemporalProfile.INTELLIGENCE, {"input_cutoffs": {"": "2024-02-26T11:00:00Z"}}),
    (TemporalProfile.INTELLIGENCE, {"input_cutoffs": {"synthetic_input": False}}),
    (TemporalProfile.INTELLIGENCE, {"input_cutoffs": {"synthetic_input": "2024-02-26"}}),
    (TemporalProfile.INTELLIGENCE, {"data_cutoff_at": False}),
    (TemporalProfile.INTELLIGENCE, {"expires_at": False}),
    (TemporalProfile.INTELLIGENCE, {"expires_at": "2024-02-28T12:00:00"}),
])
def test_supplied_profile_row_shape_cannot_be_satisfied_by_presence_alone(profile, changes):
    candidate = synthetic_profile_candidate(profile)
    candidate["temporal_row"].update(changes)
    assert_refused(inspect(candidate, as_of="2024-02-27T00:00:00Z",
                           registry=synthetic_registry(profile)))


@pytest.mark.parametrize("profile", [TemporalProfile.BARS, TemporalProfile.REVISABLE_RELEASE])
@pytest.mark.parametrize("interval_label", ["2024-02-26", "2024-02-26T10:00:00+05:00"])
def test_interval_date_and_aware_labels_remain_original_labels(profile, interval_label):
    candidate = synthetic_profile_candidate(profile)
    candidate["temporal_row"]["period_end"] = interval_label
    if profile is TemporalProfile.BARS:
        candidate["temporal_row"]["period_start"] = interval_label
    original = deepcopy(candidate)
    result = inspect(candidate, as_of="2024-02-27T00:00:00Z", registry=synthetic_registry(profile))
    assert result["inspection_status"] == "INSPECTABLE"
    assert candidate == original
    assert candidate["temporal_row"]["period_end"] == interval_label
    assert result["temporal"]["known_at"] == "2024-02-26T10:00:00+00:00"
    assert result["temporal"]["row_validation"] == "bounded_candidate_probe_not_universal_native_schema"
    assert result["temporal"]["historical_system_replay"] is False


def test_valid_synthetic_intelligence_cutoff_map_still_has_native_history_gaps():
    candidate = synthetic_profile_candidate(TemporalProfile.INTELLIGENCE)
    candidate["temporal_row"]["input_cutoffs"] = {
        "synthetic_one": "2024-02-26T11:00:00Z",
        "synthetic_two": "2024-02-26T13:00:00+02:00",
    }
    result = inspect(candidate, as_of="2024-02-27T00:00:00Z",
                     registry=synthetic_registry(TemporalProfile.INTELLIGENCE))
    assert result["inspection_status"] == "INSPECTABLE"
    assert result["temporal"]["known_at"] == "2024-02-26T12:01:00+00:00"
    assert "supplied_row_not_authenticated_native_history" in result["gaps"]["time"]
    assert result["admission"] == "NOT_ADMITTED"


@pytest.mark.parametrize("cutoffs", [False, [], {}])
def test_derived_native_refusal_precedes_narrower_probe_shape_validation(cutoffs):
    candidate = with_temporal()
    candidate["temporal_row"].update(
        computed_at="2024-02-26T12:00:00Z", code_version=False, input_cutoffs=cutoffs,
    )
    assert_refused(inspect(candidate, as_of="2024-02-27T00:00:00Z",
                           registry=synthetic_registry(TemporalProfile.DERIVED)),
                   "NATIVE_TEMPORAL_REFUSAL")


def test_future_known_is_excluded_before_receipt_interpretation(monkeypatch):
    def forbidden_replay(*args, **kwargs):
        pytest.fail("native replay must not run for an excluded as-of row")
    monkeypatch.setattr("engine.company_intelligence.relationship_candidates.replay_receipt",
                        forbidden_replay)
    result = inspect(with_temporal(), as_of="2024-02-26T09:59:59Z", registry=synthetic_registry())
    assert result["inspection_status"] == "NOT_KNOWN_AS_OF"
    assert result["current_candidate_view"] is None and result["support"] is None
    assert result["source_provenance"] is None and result["refusal"] is None
    assert result["content_boundary"]["quote_free_payload"] == "NOT_CERTIFIED"
    assert result["content_boundary"]["public_safe_payload"] == "NOT_CERTIFIED"
    assert result["annotation_trust"]["document_annotations"] == "caller_supplied_not_authenticated"


def test_synthetic_native_visible_row_is_still_candidate_only_not_authenticated_replay():
    result = inspect(with_temporal(), as_of="2024-02-26T10:00:00Z", registry=synthetic_registry())
    assert result["inspection_status"] == "INSPECTABLE"
    assert result["temporal"]["known_at"] == "2024-02-26T10:00:00+00:00"
    assert result["temporal"]["historical_system_replay"] is False
    assert "supplied_row_not_authenticated_native_history" in result["gaps"]["time"]
    assert result["admission"] == "NOT_ADMITTED"


@pytest.mark.parametrize("change,code", [
    ({"published_at": "2024-02-26"}, "NATIVE_TEMPORAL_REFUSAL"),
    ({"event_at": "2024-02-26T10:00:00"}, "NATIVE_TEMPORAL_REFUSAL"),
    ({"published_at": None}, "AS_OF_PROFILE_CLOCK_MISSING"),
    ({"document_version": "borrowed-other-version"}, "AS_OF_ROW_SOURCE_UNBOUND"),
    ({"source_sha256": "0" * 64}, "AS_OF_ROW_SOURCE_UNBOUND"),
])
def test_native_row_clock_and_source_binding_are_required(change, code):
    candidate = with_temporal()
    candidate["temporal_row"].update(change)
    assert_refused(inspect(candidate, as_of="2024-02-27T00:00:00Z",
                           registry=synthetic_registry()), code)


def test_duplicate_registry_contract_and_missing_row_refuse():
    candidate = with_temporal()
    contract = next(iter(synthetic_registry()))
    assert_refused(inspect(candidate, as_of="2024-02-27T00:00:00Z",
                           registry=Registry([contract, contract])), "AS_OF_DATASET_AMBIGUOUS")
    candidate["temporal_row"] = None
    assert_refused(inspect(candidate, as_of="2024-02-27T00:00:00Z",
                           registry=synthetic_registry()), "AS_OF_ROW_REQUIRED")


def test_correction_preserves_revision_and_does_not_erase_or_choose_latest():
    original = make_candidate()
    snapshot = deepcopy(original)
    corrected_source = SOURCE.replace("next year", "after review")
    correction = make_candidate(source=corrected_source,
                                span=SPAN.replace("next year", "after review"))
    correction["candidate_id"] = "synthetic:relation:2"
    correction["document"]["version"] = "synthetic-v2"
    correction["revision"] = {"supersedes_candidate_id": original["candidate_id"],
                              "relation": "corrects"}
    corrected = inspect(correction, source=corrected_source)
    old = inspect(original)
    assert original == snapshot
    assert old["inspection_status"] == corrected["inspection_status"] == "INSPECTABLE"
    view = corrected["current_candidate_view"]
    assert view["revision"] == correction["revision"]
    assert view["revision_resolution"] == "NO_AUTOMATIC_SELECTION_OR_ORIGINAL_ERASURE"
    assert old["source_provenance"]["source_sha256"] != corrected["source_provenance"]["source_sha256"]
    correction["revision"]["relation"] = "contradicts"
    assert inspect(correction, source=corrected_source)["current_candidate_view"]["revision"]["relation"] == "contradicts"


def test_annotations_never_resolve_identity_or_rights():
    candidate = make_candidate()
    candidate["identity_annotations"] = {"subject_id": "cik:0000000001", "object_id": "ISS:fake"}
    result = inspect(candidate)
    view = result["current_candidate_view"]
    assert view["canonical_subject_id"] is None and view["canonical_object_id"] is None
    assert view["identity_annotation_status"] == "UNTRUSTED_NOT_RESOLVED"
    assert result["gaps"]["identity"] and result["gaps"]["rights"]
    assert result["admission"] == "NOT_ADMITTED"


@pytest.mark.parametrize("key,value", [
    ("authority", {"trade": True}), ("admission", "ADMITTED"),
    ("rights_profile", "rp_public_primary_v1"), ("temporal_profile", "EVENT"),
    ("confidence", 1), ("graph1_projection", {"weight": 0}),
])
def test_caller_cannot_flip_authority_or_invent_rights(key, value):
    candidate = make_candidate()
    candidate[key] = value
    assert_refused(inspect(candidate))


@pytest.mark.parametrize("candidate", [None, [], "hostile", {"schema": SCHEMA}, {"schema": []}])
def test_hostile_payload_is_bounded_typed_refusal(candidate):
    assert_refused(inspect_candidate(candidate, source=SOURCE))


def test_hostile_nesting_and_bad_encoding_are_bounded():
    candidate = make_candidate()
    nested = {}
    for _ in range(20):
        nested = {"x": nested}
    candidate["temporal_row"] = nested
    assert_refused(inspect(candidate), "INPUT_LIMIT")
    assert_refused(inspect(source="\ud800"), "SOURCE_ENCODING")


def run_cli(tmp_path, candidate=None, source=SOURCE, raw_json=None, extra=()):
    candidate_path = tmp_path / "synthetic-candidate.json"
    source_path = tmp_path / "synthetic-disclosure.txt"
    candidate_path.write_text(raw_json if raw_json is not None else json.dumps(candidate or make_candidate()),
                              encoding="utf-8")
    source_path.write_bytes(source.encode("utf-8"))
    process = subprocess.run(
        [sys.executable, "-m", "engine.company_intelligence.relationship_candidates",
         "--candidate", str(candidate_path), "--source", str(source_path), *extra],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False,
    )
    assert "Traceback" not in process.stderr
    assert process.stderr == ""
    return process.returncode, json.loads(process.stdout)


def test_cli_positive_actual_files_preserve_crlf_and_default_omit_support(tmp_path):
    code, result = run_cli(tmp_path)
    assert code == 0 and result["inspection_status"] == "INSPECTABLE"
    assert "replayed_value_text" not in result["support"]
    assert "next year" not in json.dumps(result)
    code, explicit = run_cli(tmp_path, extra=("--include-support-text",))
    assert code == 0 and "next year" in explicit["support"]["replayed_value_text"]


def test_cli_default_echoes_sentence_annotation_without_claiming_quote_free_output(tmp_path):
    candidate = make_candidate()
    sentence = candidate["receipt"]["value_text"]
    candidate["assertion"]["product_scope"] = sentence
    code, result = run_cli(tmp_path, candidate=candidate)
    assert code == 0 and result["inspection_status"] == "INSPECTABLE"
    assert result["current_candidate_view"]["assertion"]["product_scope"] == sentence
    assert "replayed_value_text" not in result["support"]
    assert result["content_boundary"]["quote_free_payload"] == "NOT_CERTIFIED"
    assert result["content_boundary"]["public_safe_payload"] == "NOT_CERTIFIED"
    assert result["annotation_trust"]["manual_assertions"] == "caller_supplied_not_authenticated"


def test_cli_refuses_changed_source_and_historic_date(tmp_path):
    code, result = run_cli(tmp_path, source=SOURCE + "changed footer")
    assert code == 2
    assert_refused(result, "SOURCE_REPLAY_FAILED")
    code, result = run_cli(tmp_path, extra=("--as-of", "2024-02-26"))
    assert code == 2
    assert_refused(result, "NATIVE_TEMPORAL_REFUSAL")


@pytest.mark.parametrize("raw_json", ['{"schema":', '{"schema":1,"schema":2}', '{"x":NaN}', '[' * 1200])
def test_cli_malformed_json_is_refusal_without_traceback(tmp_path, raw_json):
    code, result = run_cli(tmp_path, raw_json=raw_json)
    assert code == 2
    assert_refused(result)


def test_cli_malformed_optional_registry_is_bounded(tmp_path):
    registry = tmp_path / "synthetic-malformed-registry.yml"
    registry.write_text("datasets: [invalid", encoding="utf-8")
    code, result = run_cli(tmp_path, extra=("--registry", str(registry)))
    assert code == 2
    assert_refused(result, "REGISTRY_LOAD_FAILED")


def test_research_witness_refuses_changed_capture_from_foreign_directory(tmp_path):
    # This is an invented body, not a redistribution of the original source.
    source = tmp_path / "changed-capture.html"
    source.write_text("SYNTHETIC changed capture", encoding="utf-8")
    witness = (Path(__file__).resolve().parents[1]
               / "research/theme_graph/economic_network_execution_20261009/replay_micron_witness.py")
    run = subprocess.run([sys.executable, str(witness), "--source", str(source)],
                         cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert run.returncode == 2
    assert run.stderr == ""
    result = json.loads(run.stdout)
    assert result["status"] == "REFUSED"
    assert result["reason"] == "exact_held_source_capture_or_span_unavailable"
    assert result["admission"] == "NOT_ADMITTED"
    assert result["historical_system_replay"] is False
    assert "outcomes" not in result  # No CLI semantic view is derived from replacement bytes.
