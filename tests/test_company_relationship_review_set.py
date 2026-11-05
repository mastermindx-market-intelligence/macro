"""Synthetic review journeys; no native admission, source coverage or economic precision proof."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from engine.company_intelligence import relationship_candidates as subject
from engine.earnings_release.receipts import receipt_for_char_span, sha256_text
from lib.dataos.registry import DatasetContract, DatasetStatus, Layer, Registry
from lib.dataos.temporal import TemporalProfile


SOURCE = "Synthetic café.\r\nAurora plans Widget integration into Boreal systems.\r\nEnd."
SPAN = "Aurora plans Widget integration into Boreal systems."


def candidate(candidate_id="candidate-a"):
    start = SOURCE.index(SPAN)
    return {
        "schema": subject.SCHEMA,
        "candidate_id": candidate_id,
        "document": {"document_id": "synthetic-doc", "version": "synthetic-v1",
                     "source_ref": "synthetic-only", "published_date": "2024-02-26"},
        "dataset_id": None, "temporal_row": None,
        "receipt": receipt_for_char_span(source=SOURCE, source_sha256=sha256_text(SOURCE),
                                         char_start=start, char_end=start + len(SPAN)).to_dict(),
        "assertion": {"kind": "product_integration", "subject_label": "Aurora", "object_label": "Boreal",
                      "product_scope": "Widget", "lifecycle": "planned", "magnitude": None},
        "revision": {"supersedes_candidate_id": None, "relation": "original"},
        "identity_annotations": None,
    }


def case(case_id="case-a", value=None, source=SOURCE):
    return {"case_id": case_id, "candidate": candidate() if value is None else value, "source": source}


def review(*cases):
    return {"schema": subject.REVIEW_SET_SCHEMA, "review_set_id": "synthetic-review", "cases": list(cases)}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def assert_authority(result):
    assert result["admission"] == "NOT_ADMITTED"
    assert result["graph1_projection"] is None
    assert result["authority"] == {key: False for key in ("rank", "gate", "size", "trade", "prediction")}
    assert result["content_boundary"]["public_export"] == "NOT_AUTHORIZED"
    assert result["content_boundary"]["public_safe_payload"] == "NOT_CERTIFIED"
    assert result["content_boundary"]["quote_free_payload"] == "NOT_CERTIFIED"


def assert_whole_refusal(result, code):
    assert result["review_status"] == "REFUSED"
    assert result["refusal"] == {"code": code}
    assert result["cases"] == []
    assert result["denominators"] is None
    assert result["processing"]["retained_case_results"] == 0
    assert result["reconciliation"]["candidate_collisions"] == []
    assert result["reconciliation"]["revision_links"] == []
    assert_authority(result)


def write_manifest(tmp_path, cases=None):
    directory = tmp_path.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    entries = []
    for item in cases if cases is not None else [case()]:
        candidate_name = item["case_id"] + ".json"
        source_name = item["case_id"] + ".txt"
        (directory / candidate_name).write_bytes(canonical(item["candidate"]))
        (directory / source_name).write_bytes(item["source"].encode("utf-8"))
        entries.append({"case_id": item["case_id"], "candidate_file": candidate_name, "source_file": source_name})
    value = {"schema": subject.REVIEW_FILES_SCHEMA, "review_set_id": "synthetic-review", "cases": entries}
    manifest = directory / "review.json"
    manifest.write_bytes(canonical(value))
    return manifest, value


def run_in_process(manifest, capsys, *extra):
    exit_code = subject.main(["--review-set", str(manifest), *extra])
    captured = capsys.readouterr()
    assert captured.err == ""
    return exit_code, json.loads(captured.out)


def native_synthetic_registry():
    # In-memory synthetic test contract, never written to the real registry.
    return Registry([DatasetContract(
        dataset_id="synthetic.relationships", layer=Layer.L0_SOURCE, owner="synthetic-only",
        producer="synthetic-only", storage="synthetic-only", format="synthetic-only",
        grain=("candidate_id", "document_id", "document_version"),
        schema={name: {"type": "string"} for name in
                ("candidate_id", "document_id", "document_version", "source_sha256")},
        temporal_profile=TemporalProfile.EVENT, version="synthetic-v1", status=DatasetStatus.PRODUCED,
    )])


def temporal_candidate(candidate_id, published_at):
    value = candidate(candidate_id)
    value["dataset_id"] = "synthetic.relationships"
    value["temporal_row"] = {
        "candidate_id": candidate_id, "document_id": value["document"]["document_id"],
        "document_version": value["document"]["version"], "source_sha256": value["receipt"]["source_sha256"],
        "event_at": published_at, "published_at": published_at, "ingested_at": published_at,
    }
    return value


def test_api_preserves_complete_delegated_results_and_exact_counts(monkeypatch):
    good = case("good")
    changed = case("changed", source=SOURCE + " amended")
    unsupported = case("unsupported")
    unsupported["candidate"]["assertion"]["subject_label"] = "AbsentCompany"
    inputs = review(good, changed, unsupported)
    before = deepcopy(inputs)
    original = subject.inspect_candidate
    calls = []

    def spy(value, **options):
        calls.append((deepcopy(value), options.copy()))
        return original(value, **options)

    monkeypatch.setattr(subject, "inspect_candidate", spy)
    result = subject.inspect_review_set(inputs)
    assert inputs == before
    assert len(calls) == 3
    assert result["review_status"] == "INSPECTED"
    assert result["denominators"] == {
        "requested_cases": 3, "supplied_source_cases": 3, "unique_supplied_source_byte_digests": 2,
        "inspectable_cases": 1, "refused_cases": 2, "unavailable_cases": 0, "not_known_as_of_cases": 0,
    }
    by_id = {item["case_id"]: item for item in inputs["cases"]}
    for row in result["cases"]:
        supplied = by_id[row["case_id"]]
        assert row["inspection"] == original(supplied["candidate"], source=supplied["source"])
        assert_authority(row["inspection"])
    assert result["processing"] == {"requested_cases": 3, "prepared_cases": 3, "processed_cases": 3,
                                    "inspector_calls": 3, "retained_case_results": 3}
    assert_authority(result)


def test_api_binding_is_canonical_payload_not_original_file_bytes():
    item = case()
    result = subject.inspect_review_set(review(item))
    binding = result["cases"][0]["input_bindings"]
    assert binding["candidate"] == {
        "representation": "canonical_api_payload", "raw_file_sha256": None, "raw_file_bytes": None,
        "canonical_payload_sha256": sha256(canonical(item["candidate"])).hexdigest(),
        "canonical_payload_bytes": len(canonical(item["candidate"])),
    }
    assert binding["source"] == {"representation": "api_utf8_bytes", "sha256": sha256(SOURCE.encode()).hexdigest(),
                                  "bytes": len(SOURCE.encode()), "utf8": True}
    identity = {key: value for key, value in result.items() if key not in {"content_sha256", "input_manifest"}}
    assert result["content_sha256"] == sha256(canonical(identity)).hexdigest()
    assert result["input_manifest"] is None
    assert "not_manifest_byte_order_or_native_attestation" in result["content_identity_scope"]


def test_closed_output_fields_do_not_forward_outer_authority_or_paths():
    result = subject.inspect_review_set(review(case()))
    assert set(result) == {
        "schema", "review_set_id", "review_status", "refusal", "admission", "authority", "graph1_projection",
        "content_sha256", "content_identity_scope", "input_manifest", "options", "registry_input", "processing",
        "denominators", "cases", "reconciliation", "content_boundary", "gaps", "limitations",
    }
    assert set(result["cases"][0]) == {"case_id", "status", "input_bindings", "input_refusals", "inspection"}
    assert set(result["reconciliation"]) == {"scope", "resolution", "candidate_collisions",
                                             "repeated_input_references", "revision_links"}
    assert result["registry_input"] == {"supplied": False,
                                         "trust": "caller_supplied_not_authenticated_native_registry_history"}


@pytest.mark.parametrize("value,code", [
    (None, "REVIEW_INPUT_INVALID"),
    ({"schema": subject.REVIEW_SET_SCHEMA, "review_set_id": "empty", "cases": []}, "REVIEW_SET_EMPTY"),
    ({**review(case()), "extra": True}, "REVIEW_INPUT_INVALID"),
    ({**review(case()), "schema": subject.REVIEW_FILES_SCHEMA}, "REVIEW_SCHEMA_UNSUPPORTED"),
    ({**review(case()), "review_set_id": "host/path"}, "REVIEW_ID_INVALID"),
    ({**review(case()), "cases": {}}, "REVIEW_INPUT_INVALID"),
    (review({**case(), "unexpected": "private"}), "REVIEW_INPUT_INVALID"),
    (review(case("with space")), "REVIEW_CASE_ID_INVALID"),
    (review(case("duplicate"), case("duplicate")), "REVIEW_CASE_ID_DUPLICATE"),
])
def test_whole_request_shape_refuses_before_inspection(value, code, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("outer request must refuse before inspection")
    monkeypatch.setattr(subject, "inspect_candidate", forbidden)
    result = subject.inspect_review_set(value)
    assert_whole_refusal(result, code)
    assert result["processing"]["processed_cases"] == 0


def test_exact_64_case_limit_and_empty_are_distinct():
    items = [case(f"case-{index:02d}") for index in range(64)]
    accepted = subject.inspect_review_set(review(*items))
    assert accepted["denominators"]["requested_cases"] == 64
    assert accepted["denominators"]["inspectable_cases"] == 64
    assert_whole_refusal(subject.inspect_review_set(review(*items, case("too-many"))), "REVIEW_CASE_LIMIT")
    assert_whole_refusal(subject.inspect_review_set(review()), "REVIEW_SET_EMPTY")


@pytest.mark.parametrize("where", ["outer", "case"])
def test_oversized_envelope_mapping_refuses_before_materializing_key_set(where, monkeypatch):
    oversized = {f"unwanted-{index}": None for index in range(10000)}
    inputs = oversized if where == "outer" else review(oversized)

    def bounded_set(value=()):
        assert value is not oversized, "oversized mapping was copied into a set"
        return set(value)

    monkeypatch.setattr(subject, "set", bounded_set, raising=False)
    result = subject.inspect_review_set(inputs)
    assert_whole_refusal(result, "REVIEW_INPUT_INVALID")
    assert result["processing"]["inspector_calls"] == 0


def test_outer_schema_does_not_invoke_arbitrary_equality():
    class HostileSchema:
        def __eq__(self, other):
            raise AssertionError("untrusted schema equality was invoked")

    inputs = review(case())
    inputs["schema"] = HostileSchema()
    assert_whole_refusal(subject.inspect_review_set(inputs), "REVIEW_SCHEMA_UNSUPPORTED")


@pytest.mark.parametrize("where", ["outer", "case"])
def test_envelope_nonstring_keys_do_not_invoke_arbitrary_hashing(where):
    class HostileKey:
        armed = False

        def __hash__(self):
            if self.armed:
                raise AssertionError("untrusted key hashing was invoked")
            return 31

    key = HostileKey()
    mapping = {key: None, "one": None, "two": None}
    key.armed = True
    inputs = mapping if where == "outer" else review(mapping)
    assert_whole_refusal(subject.inspect_review_set(inputs), "REVIEW_INPUT_INVALID")


@pytest.mark.parametrize("field,value,code", [
    ("source", None, "SOURCE_INVALID"),
    ("source", "", "SOURCE_LIMIT"),
    ("source", "\ud800", "SOURCE_ENCODING"),
    ("source", "x" * (subject.MAX_SOURCE_BYTES + 1), "SOURCE_LIMIT"),
    ("candidate", {"bad": float("nan")}, "INPUT_INVALID"),
    ("candidate", {"bad": "\ud800"}, "INPUT_ENCODING"),
    ("candidate", {"bad": 2 ** 64}, "INPUT_LIMIT"),
    ("candidate", {"bad": object()}, "INPUT_INVALID"),
])
def test_api_bad_case_remains_visible_with_stable_code(field, value, code):
    item = case()
    item[field] = value
    result = subject.inspect_review_set(review(item))
    assert result["review_status"] == "INSPECTED"
    assert len(result["cases"]) == 1
    assert result["cases"][0]["inspection"]["refusal"]["code"] == code
    assert result["denominators"]["refused_cases"] == 1
    assert result["reconciliation"]["candidate_collisions"] == []


def test_recursive_candidate_is_per_case_bounded_not_traceback():
    value = {}
    value["self"] = value
    result = subject.inspect_review_set(review(case(value=value)))
    assert result["cases"][0]["inspection"]["refusal"] == {"code": "INPUT_LIMIT"}
    assert result["processing"]["inspector_calls"] == 0


def test_shared_large_scalar_stops_encoder_before_consuming_expanded_remainder(monkeypatch):
    # This compact Python object would expand to roughly 256 MiB if fully joined.
    # The sentinel stops an eager implementation before allocating that expansion.
    shared = "x" * 65536
    oversized = [shared] * 4095
    original = json.JSONEncoder.iterencode
    consumed = []

    def checked(self, value, *args, **kwargs):
        iterator = original(self, value, *args, **kwargs)
        if value is oversized:
            for chunk in iterator:
                consumed.append(len(chunk))
                assert len(consumed) <= 8, "serializer consumed the over-budget remainder"
                yield chunk
        else:
            yield from iterator

    monkeypatch.setattr(json.JSONEncoder, "iterencode", checked)
    result = subject.inspect_review_set(review(case(value=oversized)))
    assert result["cases"][0]["inspection"]["refusal"] == {"code": "INPUT_LIMIT"}
    assert 1 < len(consumed) <= 8
    assert sum(consumed) > subject.MAX_CANDIDATE_BYTES
    assert result["cases"][0]["input_bindings"]["candidate"]["canonical_payload_sha256"] is None
    assert result["processing"]["inspector_calls"] == 0


@pytest.mark.parametrize("name,code", [
    ("MAX_REVIEW_CANDIDATE_BYTES", "REVIEW_CANDIDATE_TOTAL_LIMIT"),
    ("MAX_REVIEW_SOURCE_BYTES", "REVIEW_SOURCE_TOTAL_LIMIT"),
])
def test_aggregate_limit_refuses_whole_request_before_semantics(name, code, monkeypatch):
    budget = len(canonical(candidate())) if name == "MAX_REVIEW_CANDIDATE_BYTES" else len(SOURCE.encode())
    monkeypatch.setattr(subject, name, budget)
    result = subject.inspect_review_set(review(case("a"), case("b"), case("c")))
    assert_whole_refusal(result, code)
    assert result["processing"] == {"requested_cases": 3, "prepared_cases": 2, "processed_cases": 0,
                                    "inspector_calls": 0, "retained_case_results": 0}


def test_output_overflow_keeps_processing_truth_and_withholds_all_semantics(monkeypatch):
    monkeypatch.setattr(subject, "MAX_REVIEW_OUTPUT_BYTES", 4096)
    result = subject.inspect_review_set(review(case("a"), case("b")))
    assert_whole_refusal(result, "REVIEW_OUTPUT_LIMIT")
    assert result["processing"] == {"requested_cases": 2, "prepared_cases": 2, "processed_cases": 2,
                                    "inspector_calls": 2, "retained_case_results": 0}
    assert len(canonical(result)) <= 4096
    assert "candidate-a" not in json.dumps(result)


def test_same_candidate_collision_and_explicit_revision_targets_remain_unresolved():
    original = candidate("original")
    conflicting = deepcopy(original)
    conflicting["assertion"]["lifecycle"] = "announced"
    corrected = candidate("correction")
    corrected["revision"] = {"relation": "corrects", "supersedes_candidate_id": "original"}
    orphan = candidate("orphan")
    orphan["revision"] = {"relation": "contradicts", "supersedes_candidate_id": "absent-target"}
    result = subject.inspect_review_set(review(case("original", original), case("conflicting", conflicting),
                                             case("corrected", corrected), case("orphan", orphan)))
    reconciliation = result["reconciliation"]
    assert reconciliation["candidate_collisions"][0]["candidate_id"] == "original"
    assert reconciliation["candidate_collisions"][0]["case_ids"] == ["conflicting", "original"]
    assert len(reconciliation["candidate_collisions"][0]["canonical_payload_sha256s"]) == 2
    links = {item["case_id"]: item for item in reconciliation["revision_links"]}
    assert links["corrected"]["target_status"] == "AMBIGUOUS_TARGET"
    assert links["corrected"]["target_case_ids"] == ["conflicting", "original"]
    assert links["orphan"]["target_status"] == "ABSENT_FROM_INSPECTABLE_SET"
    assert links["orphan"]["target_case_ids"] == []
    assert {item["resolution"] for item in links.values()} == {"UNRESOLVED_NO_AUTOMATIC_SELECTION"}
    assert len(result["cases"]) == 4


def test_repeated_inputs_are_not_independent_support_and_identity_annotations_do_not_merge():
    value = candidate()
    value["identity_annotations"] = {"subject_id": "UNTRUSTED-X", "object_id": "UNTRUSTED-X"}
    result = subject.inspect_review_set(review(case("a", value), case("b", deepcopy(value))))
    repeats = result["reconciliation"]["repeated_input_references"]
    assert len(repeats) == 1
    assert repeats[0]["case_ids"] == ["a", "b"]
    assert repeats[0]["independent_corroboration"] == "NOT_ESTABLISHED"
    assert result["reconciliation"]["candidate_collisions"] == []
    assert "UNTRUSTED-X" not in json.dumps(result["reconciliation"])
    for row in result["cases"]:
        assert row["inspection"]["current_candidate_view"]["canonical_subject_id"] is None
        assert row["inspection"]["current_candidate_view"]["canonical_object_id"] is None


def test_no_wall_clock_or_input_order_truth_selection(monkeypatch):
    value = candidate("linked")
    value["revision"] = {"relation": "corrects", "supersedes_candidate_id": "candidate-a"}
    inputs = review(case("z", value), case("a"))
    with monkeypatch.context() as context:
        def no_clock():
            raise AssertionError("no wall clock belongs in review identity")
        context.setattr(time, "time", no_clock)
        first = subject.inspect_review_set(inputs)
        second = subject.inspect_review_set(review(*reversed(inputs["cases"])))
    assert first == second
    assert [row["case_id"] for row in first["cases"]] == ["a", "z"]
    assert first["reconciliation"]["revision_links"][0]["target_status"] == "PRESENT_UNRESOLVED"


def test_future_and_temporal_refusal_never_contribute_semantic_reconciliation():
    visible = temporal_candidate("visible", "2024-02-26T10:00:00Z")
    future = temporal_candidate("SECRET-FUTURE", "2024-03-01T10:00:00Z")
    future["document"]["document_id"] = "SECRET-DOCUMENT"
    future["temporal_row"]["document_id"] = "SECRET-DOCUMENT"
    future["revision"] = {"relation": "contradicts", "supersedes_candidate_id": "SECRET-TARGET"}
    future["identity_annotations"] = {"subject_id": "SECRET-IDENTITY", "object_id": None}
    refused = temporal_candidate("SECRET-REFUSED", "2024-02-26T10:00:00Z")
    refused["dataset_id"] = "absent-dataset"
    refused["revision"] = {"relation": "corrects", "supersedes_candidate_id": "SECRET-TARGET"}
    result = subject.inspect_review_set(review(case("visible", visible), case("future", future), case("refused", refused)),
                                        as_of="2024-02-27T00:00:00Z", registry=native_synthetic_registry(),
                                        include_support_text=True)
    assert result["denominators"] == {
        "requested_cases": 3, "supplied_source_cases": 3, "unique_supplied_source_byte_digests": 1,
        "inspectable_cases": 1, "refused_cases": 1, "unavailable_cases": 0, "not_known_as_of_cases": 1,
    }
    serialized = json.dumps(result)
    for token in ("SECRET-FUTURE", "SECRET-DOCUMENT", "SECRET-TARGET", "SECRET-IDENTITY", "SECRET-REFUSED"):
        assert token not in serialized
    for row in result["cases"]:
        if row["case_id"] != "visible":
            assert row["inspection"]["current_candidate_view"] is None
            assert row["inspection"]["source_provenance"] is None
            assert row["inspection"]["support"] is None
    assert result["reconciliation"]["revision_links"] == []


def test_visible_reference_to_excluded_candidate_does_not_resolve_target():
    future = temporal_candidate("target", "2024-03-01T10:00:00Z")
    visible = temporal_candidate("visible", "2024-02-26T10:00:00Z")
    visible["revision"] = {"relation": "corrects", "supersedes_candidate_id": "target"}
    result = subject.inspect_review_set(review(case("a", visible), case("b", future)),
                                        as_of="2024-02-27T00:00:00Z", registry=native_synthetic_registry())
    link = result["reconciliation"]["revision_links"][0]
    assert link["target_status"] == "ABSENT_FROM_INSPECTABLE_SET"
    assert link["target_case_ids"] == []


def test_missing_registry_remains_per_case_native_refusal():
    result = subject.inspect_review_set(review(case("a"), case("b")), as_of="2024-02-27T00:00:00Z")
    assert result["denominators"]["refused_cases"] == 2
    assert {row["inspection"]["refusal"]["code"] for row in result["cases"]} == {"AS_OF_REGISTRY_REQUIRED"}
    assert result["reconciliation"]["repeated_input_references"] == []


@pytest.mark.parametrize("cutoff", ["2024-02-27", "2024-02-27T00:00:00", "invalid"])
def test_review_cutoff_is_one_exact_native_instant(cutoff):
    result = subject.inspect_review_set(review(case()), as_of=cutoff)
    assert_whole_refusal(result, "NATIVE_TEMPORAL_REFUSAL")
    assert result["processing"]["inspector_calls"] == 0


def test_support_option_preserves_complete_case_and_rights_caveat():
    item = case()
    default = subject.inspect_review_set(review(item))
    supported = subject.inspect_review_set(review(item), include_support_text=True)
    assert "replayed_value_text" not in default["cases"][0]["inspection"]["support"]
    assert supported["cases"][0]["inspection"] == subject.inspect_candidate(item["candidate"], source=SOURCE,
                                                                             include_support_text=True)
    assert supported["content_sha256"] != default["content_sha256"]
    assert "may_contain_source_text" in supported["content_boundary"]["annotations"]
    assert_authority(supported)
    assert_whole_refusal(subject.inspect_review_set(review(item), include_support_text="yes"), "REVIEW_OPTIONS_INVALID")


def test_cli_mixed_real_file_failures_keep_denominator_and_original_refusals(tmp_path, capsys):
    manifest, value = write_manifest(tmp_path, [case("good"), case("missing"), case("malformed"), case("changed")])
    (manifest.parent / "missing.txt").unlink()
    (manifest.parent / "malformed.json").write_bytes(b'{"bad":')
    (manifest.parent / "changed.txt").write_bytes((SOURCE + " altered").encode())
    exit_code, result = run_in_process(manifest, capsys)
    assert exit_code == 2
    assert result["review_status"] == "INSPECTED"
    assert result["denominators"] == {
        "requested_cases": 4, "supplied_source_cases": 3, "unique_supplied_source_byte_digests": 2,
        "inspectable_cases": 1, "refused_cases": 2, "unavailable_cases": 1, "not_known_as_of_cases": 0,
    }
    by_id = {row["case_id"]: row for row in result["cases"]}
    assert by_id["changed"]["inspection"]["refusal"]["code"] == "SOURCE_REPLAY_FAILED"
    assert by_id["missing"]["inspection"]["refusal"]["code"] == "REVIEW_FILE_UNAVAILABLE"
    assert by_id["malformed"]["inspection"]["refusal"]["code"] == "INPUT_FILE_OR_JSON_INVALID"
    assert by_id["malformed"]["input_bindings"]["candidate"]["canonical_payload_sha256"] is None
    assert result["processing"]["inspector_calls"] == 2
    serialized = json.dumps(result)
    assert str(manifest.parent) not in serialized
    assert "candidate_file" not in serialized and "source_file" not in serialized
    assert result["input_manifest"] == {"raw_file_sha256": sha256(manifest.read_bytes()).hexdigest(),
                                         "raw_file_bytes": manifest.stat().st_size}


@pytest.mark.parametrize("raw,code", [
    (b'{"schema":1,"schema":2}', "JSON_DUPLICATE_KEY"),
    (b'{"value":NaN}', "JSON_CONSTANT_INVALID"),
    (b'{"value":Infinity}', "JSON_CONSTANT_INVALID"),
    (b'\xff', "INPUT_ENCODING"),
    (b'[{', "INPUT_FILE_OR_JSON_INVALID"),
])
def test_cli_manifest_json_failure_is_outer_and_candidate_json_failure_is_per_case(tmp_path, capsys, raw, code):
    manifest, _ = write_manifest(tmp_path)
    original = manifest.read_bytes()
    manifest.write_bytes(raw)
    exit_code, outer = run_in_process(manifest, capsys)
    assert exit_code == 2
    assert_whole_refusal(outer, code)
    manifest.write_bytes(original)
    (manifest.parent / "case-a.json").write_bytes(raw)
    exit_code, inner = run_in_process(manifest, capsys)
    assert exit_code == 2
    assert inner["review_status"] == "INSPECTED"
    assert inner["cases"][0]["inspection"]["refusal"]["code"] == code
    assert inner["cases"][0]["input_bindings"]["candidate"]["raw_file_sha256"] == sha256(raw).hexdigest()


def test_cli_invalid_utf8_source_is_supplied_bytes_without_claiming_utf8(tmp_path, capsys):
    manifest, _ = write_manifest(tmp_path)
    (manifest.parent / "case-a.txt").write_bytes(b'\xff')
    _, result = run_in_process(manifest, capsys)
    row = result["cases"][0]
    assert row["inspection"]["refusal"]["code"] == "SOURCE_ENCODING"
    assert row["input_bindings"]["source"] == {"representation": "original_file_bytes",
                                               "sha256": sha256(b'\xff').hexdigest(), "bytes": 1, "utf8": False}
    assert result["denominators"]["supplied_source_cases"] == 1


def test_cli_different_json_whitespace_has_distinct_raw_identity_and_same_canonical_reference(tmp_path, capsys):
    manifest, _ = write_manifest(tmp_path, [case("a"), case("b")])
    (manifest.parent / "b.json").write_text(json.dumps(candidate(), indent=2), encoding="utf-8")
    code, result = run_in_process(manifest, capsys)
    assert code == 0
    a, b = [row["input_bindings"]["candidate"] for row in result["cases"]]
    assert a["raw_file_sha256"] != b["raw_file_sha256"]
    assert a["canonical_payload_sha256"] == b["canonical_payload_sha256"]
    assert result["reconciliation"]["candidate_collisions"] == []
    assert len(result["reconciliation"]["repeated_input_references"]) == 1


def test_cli_manifest_permutation_preserves_content_identity_and_distinct_raw_manifest(tmp_path, capsys):
    manifest, value = write_manifest(tmp_path, [case("a"), case("b")])
    code, first = run_in_process(manifest, capsys)
    assert code == 0
    value["cases"].reverse()
    manifest.write_text(json.dumps(value, indent=2), encoding="utf-8")
    code, second = run_in_process(manifest, capsys)
    assert code == 0
    assert first["input_manifest"]["raw_file_sha256"] != second["input_manifest"]["raw_file_sha256"]
    assert first["input_manifest"]["raw_file_bytes"] != second["input_manifest"]["raw_file_bytes"]
    assert first["content_sha256"] == second["content_sha256"]
    assert {key: value for key, value in first.items() if key != "input_manifest"} == {
        key: value for key, value in second.items() if key != "input_manifest"}


def test_cli_duplicate_case_ids_refuse_before_opening_case_files(tmp_path, capsys, monkeypatch):
    manifest, value = write_manifest(tmp_path)
    value["cases"].append(deepcopy(value["cases"][0]))
    manifest.write_bytes(canonical(value))
    original = subject._review_regular_bytes
    opened = []

    def read(path, limit):
        opened.append(path)
        assert path == manifest
        return original(path, limit)

    monkeypatch.setattr(subject, "_review_regular_bytes", read)
    code, result = run_in_process(manifest, capsys)
    assert code == 2
    assert_whole_refusal(result, "REVIEW_CASE_ID_DUPLICATE")
    assert opened == [manifest]


def test_cli_registry_loads_once_and_failure_preserves_requested_count(tmp_path, capsys, monkeypatch):
    from lib.dataos import registry as native_registry

    values = [case("a", temporal_candidate("a", "2024-02-26T10:00:00Z")),
              case("b", temporal_candidate("b", "2024-02-26T10:00:00Z"))]
    manifest, _ = write_manifest(tmp_path, values)
    calls = []

    def load(path):
        calls.append(path)
        return native_synthetic_registry()

    monkeypatch.setattr(native_registry, "load_registry", load)
    code, result = run_in_process(manifest, capsys, "--registry", "synthetic-native-registry", "--as-of", "2024-02-27T00:00:00Z")
    assert calls == ["synthetic-native-registry"]
    assert code == 0
    assert result["denominators"]["inspectable_cases"] == 2
    assert {row["inspection"]["temporal"]["as_of"] for row in result["cases"]} == {"2024-02-27T00:00:00+00:00"}
    assert "caller_supplied" in result["registry_input"]["trust"]

    def fail(path):
        raise RuntimeError("sensitive-host-path-must-not-appear")

    monkeypatch.setattr(native_registry, "load_registry", fail)
    code, result = run_in_process(manifest, capsys, "--registry", "unreadable")
    assert code == 2
    assert_whole_refusal(result, "REGISTRY_LOAD_FAILED")
    assert result["processing"]["requested_cases"] == 2
    assert result["processing"]["processed_cases"] == 0
    assert "sensitive-host" not in json.dumps(result)


@pytest.mark.parametrize("kind", ["symlink", "parent_symlink", "fifo", "directory"])
def test_cli_file_descriptor_guards_refuse_nonregular_paths_without_blocking(tmp_path, capsys, kind):
    manifest, value = write_manifest(tmp_path)
    target = manifest.parent / "case-a.txt"
    if kind == "parent_symlink":
        actual = manifest.parent / "actual"
        actual.mkdir()
        target.rename(actual / target.name)
        (manifest.parent / "linked").symlink_to(actual, target_is_directory=True)
        value["cases"][0]["source_file"] = "linked/case-a.txt"
        manifest.write_bytes(canonical(value))
    else:
        target.unlink()
        if kind == "symlink":
            (manifest.parent / "actual.txt").write_text(SOURCE, encoding="utf-8")
            target.symlink_to(manifest.parent / "actual.txt")
        elif kind == "fifo":
            os.mkfifo(target)
        else:
            target.mkdir()
    code, result = run_in_process(manifest, capsys)
    assert code == 2
    assert result["cases"][0]["inspection"]["refusal"]["code"] == "REVIEW_FILE_NOT_REGULAR"
    assert str(target) not in json.dumps(result)


def test_cli_open_race_to_fifo_is_still_nonblocking_descriptor_refusal(tmp_path, capsys, monkeypatch):
    manifest, _ = write_manifest(tmp_path)
    original = subject.os.open
    swapped = False

    def race(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == "case-a.txt" and not swapped:
            swapped = True
            target = manifest.parent / "case-a.txt"
            target.unlink()
            os.mkfifo(target)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(subject.os, "open", race)
    code, result = run_in_process(manifest, capsys)
    assert swapped and code == 2
    assert result["cases"][0]["inspection"]["refusal"]["code"] == "REVIEW_FILE_NOT_REGULAR"


@pytest.mark.parametrize("target,limit", [("review.json", subject.MAX_REVIEW_MANIFEST_BYTES),
                                          ("case-a.json", subject.MAX_CANDIDATE_BYTES),
                                          ("case-a.txt", subject.MAX_SOURCE_BYTES)])
def test_cli_per_file_byte_limits_are_visible_not_silent_truncation(tmp_path, capsys, target, limit):
    manifest, _ = write_manifest(tmp_path)
    (manifest.parent / target).write_bytes(b"x" * (limit + 1))
    code, result = run_in_process(manifest, capsys)
    assert code == 2
    if target == "review.json":
        assert_whole_refusal(result, "INPUT_LIMIT")
    else:
        assert result["review_status"] == "INSPECTED"
        assert result["cases"][0]["inspection"]["refusal"]["code"] == "INPUT_LIMIT"
        assert result["denominators"]["refused_cases"] == 1


def test_cli_aggregate_input_limit_stops_before_later_file_reads(tmp_path, capsys, monkeypatch):
    manifest, _ = write_manifest(tmp_path, [case("a"), case("b"), case("c")])
    monkeypatch.setattr(subject, "MAX_REVIEW_SOURCE_BYTES", len(SOURCE.encode()))
    original = subject._review_regular_bytes
    opened = []

    def read(path, limit):
        opened.append(path.name)
        return original(path, limit)

    monkeypatch.setattr(subject, "_review_regular_bytes", read)
    code, result = run_in_process(manifest, capsys)
    assert code == 2
    assert_whole_refusal(result, "REVIEW_SOURCE_TOTAL_LIMIT")
    assert result["processing"]["requested_cases"] == 3
    assert result["processing"]["prepared_cases"] == 2
    assert "c.json" not in opened and "c.txt" not in opened


def test_actual_second_process_cli_repeatability_and_single_case_compatibility(tmp_path):
    manifest, _ = write_manifest(tmp_path)
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "engine.company_intelligence.relationship_candidates"]
    first = subprocess.run(command + ["--review-set", str(manifest)], cwd=repo, env=env,
                           capture_output=True, text=True, timeout=20)
    second = subprocess.run(command + ["--review-set", str(manifest)], cwd=repo, env=env,
                            capture_output=True, text=True, timeout=20)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    single = subprocess.run(command + ["--candidate", str(manifest.parent / "case-a.json"),
                                       "--source", str(manifest.parent / "case-a.txt")],
                            cwd=repo, env=env, capture_output=True, text=True, timeout=20)
    assert single.returncode == 0 and single.stderr == ""
    assert json.loads(single.stdout) == result["cases"][0]["inspection"]
    changed = subprocess.run(command + ["--candidate", str(manifest.parent / "case-a.json"),
                                        "--source", str(manifest.parent / "case-a.txt"),
                                        "--as-of", "2024-02-27T00:00:00Z"],
                             cwd=repo, env=env, capture_output=True, text=True, timeout=20)
    assert changed.returncode == 2 and changed.stderr == ""
    assert json.loads(changed.stdout)["refusal"]["code"] == "AS_OF_REGISTRY_REQUIRED"


@pytest.mark.parametrize("extra", [["--source", "unused"], ["--candidate", "unused"]])
def test_review_cli_input_modes_are_mutually_exclusive(tmp_path, capsys, extra):
    manifest, _ = write_manifest(tmp_path)
    with pytest.raises(SystemExit) as caught:
        subject.main(["--review-set", str(manifest), *extra])
    assert caught.value.code == 2
    assert capsys.readouterr().out == ""
