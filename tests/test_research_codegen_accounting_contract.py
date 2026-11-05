"""Synthetic accounting-reference evidence only; no canonical records or I/O."""
from copy import deepcopy

import pytest

from engine.research_codegen.accounting_contract import assess_accounting_references


def digest(n):
    return f"{n:064x}"


def variant(n):
    return {"variant_id": f"variant-{n}", "source_sha256": digest(1000 + n),
            "config_sha256": digest(2000 + n), "incumbent_config_hash": f"{3000 + n:016x}"}


def fixtures(width=4, inherited=0, vault=False):
    # Manually specified reference identities. No production hash/ledger function
    # constructs the expected oracle and no storage object is instantiated.
    old = [variant(n) for n in range(inherited)]
    new = [variant(n) for n in range(inherited, width)]
    request = {"window_id": "window-original", "hypothesis_id": "hypothesis-original",
               "request_id": "request-original", "consumption_id": "consume-original",
               "seal_sha256": digest(71), "history_anchor_sha256": digest(72),
               "consumption_record_sha256": digest(73), "minimum_peek_count": 2}
    expected = {"schema": "research_codegen.expected_generation.v1",
                "original_root_id": "original-root", "family": "rf.codegen.sector_entry_v1",
                "protocol_sha256": digest(1), "history_anchor_sha256": digest(2),
                "variants": new, "inherited_variants": old, "trial_ceiling": width,
                "vault_required": vault, "vault_request": request if vault else None}
    trial = {"schema": "research_codegen.trial_readback_reference.v1",
             "original_root_id": "original-root", "family": "rf.codegen.sector_entry_v1",
             "protocol_sha256": digest(1), "history_anchor_sha256": digest(2),
             "snapshot_sha256": digest(3), "snapshot_bytes": 512,
             "writer_receipt_sha256": digest(4), "durable_readback_receipt_sha256": digest(5),
             "history_state": "complete", "load_error": None, "corrupt_lines": 0,
             "recorded_variants": deepcopy(old + new), "declared_floor": width,
             "literal_n": width, "effective_n": width}
    vr = None
    if vault:
        vr = {**deepcopy(request), "schema": "research_codegen.vault_readback_reference.v1",
              "original_root_id": "original-root", "protocol_sha256": digest(1),
              "seals_snapshot_sha256": digest(81), "seals_snapshot_bytes": 128,
              "peek_snapshot_sha256": digest(82), "peek_snapshot_bytes": 1024,
              "writer_receipt_sha256": digest(83), "durable_consumption_receipt_sha256": digest(84),
              "label_mediator_receipt_sha256": digest(85), "history_state": "complete",
              "consumption_state": "recorded", "load_error": None, "corrupt_lines": 0,
              "retired": False, "chain_state": "consistent", "peek_count": 2}
    return expected, trial, vr


def assess(parts):
    expected, trial, vault = parts
    return assess_accounting_references(expected, trial_readback=trial, vault_readback=vault)


def assert_disabled(result):
    for field in ("generation_enabled", "execution_enabled", "evaluation_enabled", "authority_granted"):
        assert result[field] is False
    assert result["owner_origin_and_durability"] == "UNQUALIFIED"
    assert "singleton custody" in result["note"]


def assert_invalid(parts, diagnostic=None):
    result = assess(parts)
    assert result["status"] == "PREREQUISITES_INVALID"
    assert result["violations"]
    if diagnostic:
        assert any(diagnostic in error for error in result["violations"])
    assert_disabled(result)


@pytest.mark.parametrize("vault", [False, True])
def test_complete_references_never_authenticate_or_enable(vault):
    parts = fixtures(width=4, inherited=2, vault=vault)
    before = deepcopy(parts)
    result = assess(parts)
    assert result["status"] == "STRUCTURALLY_COMPLETE_DISABLED"
    assert result["violations"] == []
    assert_disabled(result)
    assert parts == before


def test_twenty_generated_variants_cannot_be_replaced_by_one_surviving_result():
    parts = fixtures(width=20)
    parts[1]["recorded_variants"] = [deepcopy(parts[0]["variants"][-1])]
    parts[1]["literal_n"] = 1
    # Even a conservative declared/effective floor20 cannot recover omitted
    # explicit identity evidence; this is not just a count threshold test.
    result = assess(parts)
    assert "trial: full explicit original generation set mismatch" in result["violations"]
    assert "trial: literal count does not match full itemized width" in result["violations"]
    assert_disabled(result)


def test_declared_four_without_itemized_four_refuses():
    parts = fixtures()
    parts[1]["recorded_variants"] = []
    assert_invalid(parts, "full explicit")


def test_same_count_with_swapped_bytes_refuses():
    parts = fixtures()
    parts[1]["recorded_variants"][2]["source_sha256"] = digest(999)
    assert_invalid(parts, "full explicit")


def test_inherited_search_cannot_be_dropped_or_new_family_renamed():
    parts = fixtures(width=20, inherited=19)
    parts[1]["recorded_variants"] = deepcopy(parts[0]["variants"])
    assert_invalid(parts, "full explicit")
    parts = fixtures(width=4, inherited=2)
    parts[1]["family"] = "rf.codegen.fresh_chat"
    assert_invalid(parts, "original generation")


def test_shortened_incumbent_hash_collision_is_not_deduplication():
    parts = fixtures()
    first, second = parts[1]["recorded_variants"][:2]
    second["incumbent_config_hash"] = first["incumbent_config_hash"]
    assert_invalid(parts, "collision")


def test_duplicate_variant_and_duplicate_strong_config_refuse():
    parts = fixtures()
    parts[1]["recorded_variants"][1] = deepcopy(parts[1]["recorded_variants"][0])
    assert_invalid(parts, "duplicate")


@pytest.mark.parametrize("field,value", [
    ("literal_n", True), ("declared_floor", True), ("effective_n", 1),
    ("snapshot_bytes", 0), ("history_state", "partial"),
    ("history_state", "uncertain"), ("load_error", "late fsync failed"),
    ("corrupt_lines", 1), ("corrupt_lines", False),
    ("history_anchor_sha256", digest(999)), ("original_root_id", "replacement-root"),
    ("durable_readback_receipt_sha256", None), ("writer_receipt_sha256", None),
])
def test_trial_reference_failures_refuse(field, value):
    parts = fixtures()
    parts[1][field] = value
    assert_invalid(parts)


@pytest.mark.parametrize("field,value", [
    ("retired", True), ("retired", 0), ("consumption_state", "uncertain"),
    ("consumption_state", "not_recorded"), ("history_state", "truncated"),
    ("chain_state", "broken"), ("history_anchor_sha256", digest(999)),
    ("consumption_record_sha256", digest(999)), ("request_id", "new-free-peek"),
    ("consumption_id", "replacement-attempt"), ("peek_count", 1),
    ("peek_count", True), ("load_error", "partial read"),
    ("corrupt_lines", 1), ("durable_consumption_receipt_sha256", None),
    ("label_mediator_receipt_sha256", None), ("seals_snapshot_bytes", 0),
])
def test_vault_uncertain_retired_or_wrong_original_history_refuses(field, value):
    parts = fixtures(vault=True)
    parts[2][field] = value
    assert_invalid(parts)


def test_chain_consistency_cannot_override_changed_accepted_anchor():
    parts = fixtures(vault=True)
    parts[2]["chain_state"] = "consistent"
    parts[2]["history_anchor_sha256"] = digest(999)
    assert_invalid(parts, "anchor mismatch")


def test_required_vault_reference_cannot_be_omitted():
    expected, trial, _vault = fixtures(vault=True)
    assert_invalid((expected, trial, None), "closed object")


@pytest.mark.parametrize("malformed_minimum", [True, 1.0])
def test_vault_readback_minimum_must_be_exact_integer_despite_numeric_equality(malformed_minimum):
    parts = fixtures(vault=True)
    parts[0]["vault_request"]["minimum_peek_count"] = 1
    parts[2]["minimum_peek_count"] = malformed_minimum
    # Python equality considers True and1.0 equal to1. Agreement alone must not
    # skip the exact-count qualification of the independent readback.
    assert_invalid(parts, "minimum peek count")


@pytest.mark.parametrize("which", [0, 1, 2])
def test_caller_pass_flags_do_not_supply_authority(which):
    parts = fixtures(vault=True)
    parts[which]["accepted"] = True
    assert_invalid(parts, "closed object")


@pytest.mark.parametrize("field", ["path", "callback", "ledger_object", "labels"])
def test_no_path_callback_ledger_or_labels_slot(field):
    parts = fixtures()
    parts[1][field] = "forbidden-selector"
    assert_invalid(parts, "closed object")


class Dangerous:
    def __str__(self):
        raise AssertionError("must not call custom string conversion")

    def effective_n(self, family):
        raise AssertionError("must not duck-type a ledger")


def test_executable_objects_and_ledger_duck_types_are_never_invoked():
    expected, _trial, _vault = fixtures()
    result = assess_accounting_references(expected, trial_readback=Dangerous())
    assert result["status"] == "PREREQUISITES_INVALID"
    assert_disabled(result)


class DictSubclass(dict):
    def items(self):
        raise AssertionError("must not call subclass hooks")


def test_exact_dict_required_before_hooks():
    expected, trial, vault = fixtures()
    assert_invalid((DictSubclass(expected), trial, vault), "exact JSON")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 2**64])
def test_nonfinite_and_unbounded_numbers_refuse(value):
    parts = fixtures()
    parts[1]["literal_n"] = value
    assert_invalid(parts)


def test_cyclic_or_excessively_deep_reference_refuses_before_encoding():
    expected, trial, vault = fixtures()
    cycle = {}
    cycle["cycle"] = cycle
    assert_invalid((expected, cycle, vault), "exact JSON")
    deep = {}
    cursor = deep
    for _ in range(20):
        cursor["nested"] = {}
        cursor = cursor["nested"]
    assert_invalid((expected, deep, vault), "exact JSON")


def test_container_and_string_budgets_refuse():
    expected, trial, vault = fixtures()
    assert_invalid((expected, {str(n): None for n in range(1025)}, vault), "exact JSON")
    trial["load_error"] = "x" * 4097
    assert_invalid((expected, trial, vault), "exact JSON")


@pytest.mark.parametrize("ceiling", [True, "4", None, 1, 257])
def test_invalid_ceiling_is_safe_failure_not_comparison_exception(ceiling):
    parts = fixtures()
    parts[0]["trial_ceiling"] = ceiling
    assert_invalid(parts)


def test_empty_generation_cannot_become_positive_history():
    parts = fixtures()
    parts[0]["variants"] = []
    assert_invalid(parts, "nonempty distinct")


def test_multibyte_payload_is_bound_by_encoded_bytes():
    expected, trial, vault = fixtures()
    # Each string is individually legal and the container is below its limit,
    # but UTF-8 byte width exceeds the total payload bound.
    large = {str(n): "\U0001f642" * 4000 for n in range(20)}
    assert_invalid((expected, large, vault), "exact JSON")


def test_unsupported_unicode_is_safe_refusal():
    parts = fixtures()
    parts[1]["load_error"] = "\ud800"
    assert_invalid(parts, "exact JSON")


def test_production_imports_have_no_io_or_accounting_core_dependency():
    import ast
    from pathlib import Path
    import engine.research_codegen.accounting_contract as module

    tree = ast.parse(Path(module.__file__).read_text())
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names)
    assert imports == {"__future__", "json", "math", "re"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names.intersection({"open", "exec", "eval", "compile", "__import__",
                                   "TrialLedger", "HoldoutVault"})
