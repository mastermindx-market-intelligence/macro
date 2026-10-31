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


def _error_signature(error):
    return (
        error.validator, error.message,
        list(error.absolute_path), list(error.absolute_schema_path),
        [_error_signature(child) for child in error.context],
    )


def test_same_value_under_different_property_schemas_keeps_native_errors(payload):
    value = deepcopy(payload)
    # This exact string is valid at the first root property, but invalid at the
    # later nullable-number property. A value-only success cache would hide it.
    value["awards"][0]["values"]["total_obligated"] = value["schema_version"]
    native = list(dossiers._dossier_validator().iter_errors(value))
    actual = list(dossiers._dossier_validation_validator().iter_errors(value))
    assert native
    assert [_error_signature(e) for e in actual] == [_error_signature(e) for e in native]


@pytest.mark.parametrize("invalid", [True, "1"])
def test_repeated_numeric_property_does_not_conflate_types(payload, invalid):
    value = deepcopy(payload)
    value["awards"][0]["values"]["total_obligated"] = 1.0
    value["awards"][1]["values"]["total_obligated"] = invalid
    native = list(dossiers._dossier_validator().iter_errors(value))
    actual = list(dossiers._dossier_validation_validator().iter_errors(value))
    assert native
    assert [_error_signature(e) for e in actual] == [_error_signature(e) for e in native]


@pytest.mark.parametrize("first", ["2026-99-40", "2026-01-02"])
def test_repeated_nested_property_format_errors_are_never_cached(payload, first):
    value = deepcopy(payload)
    value["awards"][0]["dates"]["start_date"] = first
    value["awards"][1]["dates"]["start_date"] = "2026-99-40"
    native = list(dossiers._dossier_validator().iter_errors(value))
    actual = list(dossiers._dossier_validation_validator().iter_errors(value))
    assert ["awards", 1, "dates", "start_date"] in [list(e.absolute_path) for e in native]
    assert [_error_signature(e) for e in actual] == [_error_signature(e) for e in native]


def test_changed_property_ref_sibling_retains_native_fallback(payload, monkeypatch):
    schema = deepcopy(dossiers._dossier_validator().schema)
    schema["properties"]["as_of"] = {
        "$ref": "#/$defs/nullableText", "maxLength": 1,
    }
    native = Draft202012Validator(schema, format_checker=FormatChecker())
    monkeypatch.setattr(dossiers, "_dossier_validator", lambda: native)
    assert dossiers._dossier_validation_validator() is native
    errors = list(native.iter_errors(payload))
    assert any(e.validator == "maxLength" and list(e.absolute_path) == ["as_of"] for e in errors)


def test_repeated_properties_remove_native_descend_and_evolve(payload, monkeypatch):
    value = deepcopy(payload)
    value["actions"] = [deepcopy(value["actions"][0]) for _ in range(64)]
    reference = dossiers._dossier_validation_validator()
    reference_type = type(reference)
    # Keep the already-qualified $ref memo, resolver and every native keyword.
    # Only replace the new properties handler with its former native handler.
    monkeypatch.setitem(reference_type.VALIDATORS, "properties", Draft202012Validator.VALIDATORS["properties"])
    reference = reference_type(reference.schema, format_checker=reference.format_checker)
    candidate = dossiers._dossier_validation_validator()

    def observe(validator):
        counts = {"descend": 0, "evolve": 0}
        cls = type(validator)
        original_descend, original_evolve = cls.descend, cls.evolve

        def descend(self, *args, **kwargs):
            counts["descend"] += 1
            yield from original_descend(self, *args, **kwargs)

        def evolve(self, *args, **kwargs):
            counts["evolve"] += 1
            return original_evolve(self, *args, **kwargs)

        monkeypatch.setattr(cls, "descend", descend)
        monkeypatch.setattr(cls, "evolve", evolve)
        errors = [_error_signature(e) for e in validator.iter_errors(value)]
        return counts, errors

    unchanged, expected = observe(reference)
    corrected, actual = observe(candidate)
    assert expected == actual == []
    assert corrected["descend"] < unchanged["descend"]
    assert corrected["evolve"] < unchanged["evolve"]
    print({"compact_actions": 64, "native_properties": unchanged, "property_memo": corrected})


def test_ref_and_property_successes_share_one_bounded_fresh_lru(payload, monkeypatch):
    import collections

    caches = []
    original = collections.OrderedDict

    class ObservedLRU(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.evictions = 0
            self.namespaces = set()
            caches.append(self)

        def __setitem__(self, key, value):
            self.namespaces.add("property" if key[0] == "property" else "ref")
            return super().__setitem__(key, value)

        def popitem(self, *args, **kwargs):
            self.evictions += 1
            return super().popitem(*args, **kwargs)

    monkeypatch.setattr(collections, "OrderedDict", ObservedLRU)
    validator = dossiers._dossier_validation_validator()
    first = caches[-1]
    value = deepcopy(payload)
    value["actions"] = [deepcopy(value["actions"][0]) for _ in range(4200)]
    for index, row in enumerate(value["actions"]):
        row["action_key"] = f"action:{index}"
        row["description"] = f"distinct memo-eligible reference value {index}"
    assert not list(validator.iter_errors(value))
    assert first.evictions > 0
    assert len(first) == 4096
    assert any(key[0] == "property" for key in first)
    assert first.namespaces == {"ref", "property"}

    def node_ids(node):
        if isinstance(node, dict):
            return {id(node)} | set().union(*(node_ids(item) for item in node.values()))
        if isinstance(node, list):
            return set().union(*(node_ids(item) for item in node))
        return set()

    copied_nodes = node_ids(validator.schema)
    assert all(key[1] in copied_nodes for key in first if key[0] == "property")
    second = dossiers._dossier_validation_validator()
    assert second.schema is not validator.schema
    assert caches[-1] is not first
    assert not caches[-1]


def test_unique_cheap_primitives_keep_native_errors_without_memo_churn(payload, monkeypatch):
    import collections

    caches, primitive_key_calls = [], []
    original_lru = collections.OrderedDict
    original_key = dossiers._dossier_memo_value_key

    class ObservedLRU(original_lru):
        evictions = 0

        def __init__(self):
            super().__init__()
            caches.append(self)

        def popitem(self, *args, **kwargs):
            self.evictions += 1
            return super().popitem(*args, **kwargs)

    def key(value):
        if type(value) is str and value.startswith("unique-primitive:"):
            primitive_key_calls.append(value)
        return original_key(value)

    monkeypatch.setattr(collections, "OrderedDict", ObservedLRU)
    monkeypatch.setattr(dossiers, "_dossier_memo_value_key", key)
    value = deepcopy(payload)
    value["actions"] = [deepcopy(value["actions"][0]) for _ in range(4201)]
    for index, row in enumerate(value["actions"]):
        row["action_key"] = f"unique-primitive:key:{index}"
        row["action_id"] = f"unique-primitive:id:{index}"
        row["obligation"] = index + 0.25
    # Valid singleton values come first. Cheap checks still reject the final
    # length and type errors at their full native paths after all that traffic.
    value["actions"][-1]["action_key"] = "x" * 801
    value["actions"][-1]["action_id"] = True
    native = list(dossiers._dossier_validator().iter_errors(value))
    actual = list(dossiers._dossier_validation_validator().iter_errors(value))
    assert native
    assert [_error_signature(e) for e in actual] == [_error_signature(e) for e in native]
    assert not primitive_key_calls
    assert caches[-1].evictions == 0
    assert len(caches[-1]) < 4096


def test_cheap_text_refs_do_not_displace_reusable_date_memo(monkeypatch):
    import collections

    caches, text_key_calls = [], []
    original_lru = collections.OrderedDict
    original_key = dossiers._dossier_ref_memo_key

    class ObservedLRU(original_lru):
        def __init__(self):
            super().__init__()
            caches.append(self)

    def key(ref, value):
        if ref == "#/$defs/nullableText":
            text_key_calls.append(value)
        return original_key(ref, value)

    monkeypatch.setattr(collections, "OrderedDict", ObservedLRU)
    monkeypatch.setattr(dossiers, "_dossier_ref_memo_key", key)
    validator = dossiers._dossier_validation_validator()
    cls = type(validator)
    original_descend = cls.descend
    date_schema = validator.schema["$defs"]["nullableDate"]
    date_descents = 0

    def descend(self, instance, schema, *args, **kwargs):
        nonlocal date_descents
        if schema is date_schema:
            date_descents += 1
        yield from original_descend(self, instance, schema, *args, **kwargs)

    monkeypatch.setattr(cls, "descend", descend)
    cached = validator.VALIDATORS["$ref"]
    date_ref = "#/$defs/nullableDate"
    text_ref = "#/$defs/nullableText"
    assert not list(cached(validator, date_ref, "2026-01-02", {"$ref": date_ref}))
    # Exercise the actual fixed bound. Cheap successes must not evict the date
    # and force its oneOf/format validation to run a second time.
    for index in range(4096):
        assert not list(cached(validator, text_ref, f"unique text {index}", {"$ref": text_ref}))
    assert not list(cached(validator, date_ref, "2026-01-02", {"$ref": date_ref}))
    assert date_descents == 1, "cheap text admissions displaced the reusable date"
    assert not text_key_calls
    assert all(entry[0] != text_ref for entry in caches[-1])
    assert len(caches[-1]) == 1


@pytest.mark.parametrize("invalid", ["x" * 4001, True, 17, [], {}])
def test_cheap_text_ref_errors_after_success_match_native(payload, invalid):
    value = deepcopy(payload)
    value["awards"][0]["description"] = "preceding valid text"
    value["awards"][1]["description"] = invalid
    expected = list(dossiers._dossier_validator().iter_errors(value))
    actual = list(dossiers._dossier_validation_validator().iter_errors(value))
    assert expected
    assert ["awards", 1, "description"] in [list(e.absolute_path) for e in expected]
    assert [_error_signature(e) for e in actual] == [_error_signature(e) for e in expected]
