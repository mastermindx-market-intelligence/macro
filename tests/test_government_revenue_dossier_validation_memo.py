"""Strict dossier validation equivalence and per-call memo boundaries."""
from __future__ import annotations

from copy import deepcopy
import math

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from engine.government_revenue import dossiers
from tests.test_government_revenue_dossiers import _write_sources


@pytest.fixture()
def payload(tmp_path):
    _write_sources(tmp_path)
    return dossiers.build_dossier_payload(tmp_path, as_of="2026-06-03")


def native_payload_valid(value):
    """Keep the original schema, format, hash and relational path for comparison."""
    original = dossiers._dossier_validation_validator
    dossiers._dossier_validation_validator = dossiers._dossier_validator
    try:
        return dossiers.is_valid_dossier_payload(value)
    finally:
        dossiers._dossier_validation_validator = original


@pytest.mark.parametrize("mutation", [
    "extra_field", "missing_version", "bad_format", "numeric_string", "bool_number",
    "wrong_hash", "action_award", "award_action", "duplicate_award", "duplicate_action",
    "duplicate_company", "company_award_count", "company_action_count", "company_award",
    "nan", "infinity",
])
def test_schema_hash_and_relational_rejections_match_native(payload, mutation):
    value = deepcopy(payload)
    if mutation == "extra_field":
        value["unexpected"] = True
    elif mutation == "missing_version":
        value.pop("schema_version")
    elif mutation == "bad_format":
        value["awards"][1]["dates"]["start_date"] = "2026-13-40"
    elif mutation == "numeric_string":
        value["awards"][1]["values"]["total_obligated"] = "12"
    elif mutation == "bool_number":
        value["awards"][1]["values"]["total_obligated"] = True
    elif mutation == "wrong_hash":
        value["content_id"] = "grd1-" + "0" * 24
    elif mutation == "action_award":
        value["actions"][0]["award_key"] = "generated:ABSENT"
    elif mutation == "award_action":
        value["awards"][0]["action_keys"].append("action:ABSENT")
    elif mutation == "duplicate_award":
        value["awards"].append(deepcopy(value["awards"][0]))
    elif mutation == "duplicate_action":
        value["actions"].append(deepcopy(value["actions"][0]))
    elif mutation == "duplicate_company":
        value["companies"].append(deepcopy(value["companies"][0]))
    elif mutation == "company_award_count":
        value["companies"][0]["award_count"] = 999
    elif mutation == "company_action_count":
        value["companies"][0]["action_count"] = 999
    elif mutation == "company_award":
        value["companies"][0]["award_keys"].append("generated:ABSENT")
    else:
        value["awards"][0]["values"]["total_obligated"] = (
            math.nan if mutation == "nan" else math.inf
        )
    if mutation != "wrong_hash":
        value["content_id"] = dossiers.dossier_content_id(value)
    assert native_payload_valid(payload)
    assert dossiers.is_valid_dossier_payload(payload)
    assert not native_payload_valid(value)
    assert not dossiers.is_valid_dossier_payload(value)


def test_valid_then_invalid_same_ref_preserves_error_path(payload):
    # Both dates share the same local definition; a successful first occurrence
    # must not hide the later invalid value during this same validator traversal.
    value = deepcopy(payload)
    value["awards"][0]["dates"]["start_date"] = "2026-01-02"
    value["awards"][1]["dates"]["start_date"] = "2026-99-40"
    native = dossiers._dossier_validator()
    optimized = dossiers._dossier_validation_validator()
    expected = [list(e.absolute_path) for e in native.iter_errors(value)]
    actual = [list(e.absolute_path) for e in optimized.iter_errors(value)]
    assert expected == actual
    assert ["awards", 1, "dates", "start_date"] in actual


def test_each_full_call_uses_a_fresh_validator_and_schema(payload, monkeypatch):
    first = dossiers._dossier_validation_validator()
    second = dossiers._dossier_validation_validator()
    assert first is not second
    assert first.schema is not second.schema
    seen = []
    factory = dossiers._dossier_validation_validator

    def track():
        validator = factory()
        seen.append(validator)
        return validator

    monkeypatch.setattr(dossiers, "_dossier_validation_validator", track)
    assert dossiers.is_valid_dossier_payload(payload)
    assert dossiers.is_valid_dossier_payload(payload)
    assert len(seen) == 2
    assert seen[0] is not seen[1]


def test_changed_schema_uses_exact_native_fallback_without_stale_definitions(payload, monkeypatch):
    original = dossiers._dossier_validator()
    before = dossiers._dossier_validation_validator()
    definition = original.schema["$defs"]["ticker"]
    assert before.is_valid(payload)
    schema = deepcopy(original.schema)
    schema["$defs"]["ticker"] = {"const": "CHANGED"}
    native = Draft202012Validator(schema, format_checker=FormatChecker())
    monkeypatch.setattr(dossiers, "_dossier_validator", lambda: native)
    assert dossiers._dossier_validation_validator() is native
    assert not native.is_valid(payload)
    assert original.schema["$defs"]["ticker"] == definition


@pytest.mark.parametrize("keyword", [
    "$id", "$schema", "$dynamicRef", "$recursiveRef", "$anchor", "$dynamicAnchor",
    "unevaluatedProperties", "unevaluatedItems",
])
def test_unsupported_scopes_do_not_enable_root_resolution(keyword):
    schema = {"$defs": {"item": {keyword: False if keyword.startswith("unevaluated") else "urn:test"}}}
    assert not dossiers._dossier_has_closed_refs(schema)


def test_external_reference_is_outside_closed_scope():
    assert not dossiers._dossier_has_closed_refs({"$ref": "https://example.invalid/schema"})


def test_type_distinct_finite_bounded_keys():
    key = dossiers._dossier_ref_memo_key
    ref = "#/$defs/item"
    assert len({key(ref, x) for x in [True, 1, 1.0, "1"]}) == 4
    for value in [math.nan, math.inf, -math.inf, 10**600, "a" * 513,
                  [], {"a": []}, {str(i): i for i in range(13)},
                  {str(i): 10**100 for i in range(12)}]:
        assert key(ref, value) is None
    assert key(ref, {"b": 2, "a": 1}) == key(ref, {"a": 1, "b": 2})
