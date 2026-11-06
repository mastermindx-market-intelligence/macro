"""Tests for research_codegen contracts, output schedule and dormant admission.

The oracle here is fixture logic: expected digests, violation substrings and
dormant flag values are literal constants written into this file, never
computed by calling the production layer against itself.  Nothing in this
file exercises a real codegen candidate, evaluator, transport or ledger.
"""
from __future__ import annotations

import copy

import pytest

from engine.research_codegen import admission, contracts, output_contract

SOURCE = "a" * 64
CONFIG = "b" * 64
PROTOCOL_SHA = "c" * 64
POLICY = "d" * 64
RUNTIME = "e" * 64
EVALUATOR = "f" * 64
ROOT = "01a1333c-a475-7052-95a8-72a88eb8c17b"
CANDIDATE = "rf-codegen-alpha01"
PARENT = "rf-codegen-parent0"
FAMILY = "rf.codegen.sector_entry_v1"
REQUIRED = ["source_runtime_binding", "per_decision_schedule"]

REQUEST_DIGEST = "3e046d2994a343cb7f38c3be17181b5991e249984d5295d2f626bd17f5ebb5d9"
SCHEDULE_DIGEST = "8db5cc47c4f7a7b957110733998e275261d475f41172908a00c323f7366ed6b5"
CANON_FIXTURE_DIGEST = "62b0df540e8c5b6a49b3dee38869a4cd9889105a7a7661b86e039e196f761a89"


def trusted_protocol():
    return {
        "schema": "research_codegen.protocol.v1",
        "protocol_sha256": PROTOCOL_SHA,
        "input_policy_sha256": POLICY,
        "runtime_sha256": RUNTIME,
        "evaluator_sha256": EVALUATOR,
        "trial_family": FAMILY,
        "original_root_id": ROOT,
        "required_evidence": list(REQUIRED),
    }


def valid_manifest(lineage=None):
    if lineage is None:
        lineage = {"original_root_id": ROOT, "parent_candidate_id": None,
                   "refinement_generation": 0}
    return {
        "schema": "research_codegen.manifest.v1",
        "candidate_id": CANDIDATE,
        "source_sha256": SOURCE,
        "config_sha256": CONFIG,
        "protocol_sha256": PROTOCOL_SHA,
        "input_policy_sha256": POLICY,
        "runtime_sha256": RUNTIME,
        "evaluator_sha256": EVALUATOR,
        "trial_family": FAMILY,
        "lineage": lineage,
        "morphology": "research_feature",
        "authority": "display_only",
    }


def trusted_schedule():
    return {
        "schema": "research_codegen.schedule.v1",
        "candidate_id": CANDIDATE,
        "fold_id": "fold-dev-2010-2017",
        "entity_id": "XLK",
        "input_policy_sha256": POLICY,
        "decision_ids": ["decision-2030-03-04", "decision-2030-03-05"],
    }


def valid_output():
    return {
        "schema": "research_codegen.output.v1",
        "candidate_id": CANDIDATE,
        "fold_id": "fold-dev-2010-2017",
        "entity_id": "XLK",
        "input_policy_sha256": POLICY,
        "rows": [
            {"decision_id": "decision-2030-03-04", "status": "available",
             "value": 0.00125, "reason": None},
            {"decision_id": "decision-2030-03-05", "status": "warmup",
             "value": None, "reason": "insufficient trailing sessions"},
        ],
    }


def owner_receipts():
    return {
        "source_runtime_binding": {
            "schema": "research_codegen.owner_reference.v1",
            "evidence_id": "evidence-source-runtime-0001",
            "source_sha256": SOURCE,
            "protocol_sha256": PROTOCOL_SHA,
        },
        "per_decision_schedule": {
            "schema": "research_codegen.owner_reference.v1",
            "evidence_id": "evidence-schedule-binding-0001",
            "source_sha256": SOURCE,
            "protocol_sha256": PROTOCOL_SHA,
        },
    }


def joined(violations):
    return " | ".join(violations)


# ---------------------------------------------------------------- protocol

def test_valid_protocol_and_manifest_accept():
    assert contracts.validate_protocol(trusted_protocol()) == []
    assert contracts.validate_manifest(valid_manifest(),
                                       trusted_protocol=trusted_protocol()) == []


def test_protocol_rejects_unknown_schema_and_shape():
    broken = trusted_protocol()
    broken["schema"] = "research_codegen.protocol.v2"
    assert contracts.validate_protocol(broken) != []
    extra = trusted_protocol()
    extra["thresholds"] = {"alpha": 0.05}
    assert contracts.validate_protocol(extra) != []
    assert contracts.validate_protocol(None) != []
    assert contracts.validate_protocol(["x"]) != []


def test_protocol_rejects_bad_required_evidence():
    empty = trusted_protocol()
    empty["required_evidence"] = []
    assert contracts.validate_protocol(empty) != []
    dup = trusted_protocol()
    dup["required_evidence"] = ["alpha", "alpha"]
    assert joined(contracts.validate_protocol(dup)).find("duplicate") >= 0
    notstr = trusted_protocol()
    notstr["required_evidence"] = ["alpha", 7]
    assert contracts.validate_protocol(notstr) != []


# ---------------------------------------------------------------- manifest

def test_manifest_rejects_extra_forbidden_candidate_fields():
    for smuggled in ("code", "evaluator_module", "actor_ref", "thresholds",
                     "holdout_selector", "baseline_selector", "statistics",
                     "p_value", "accepted", "pass", "authority_granted",
                     "generation_enabled"):
        manifest = valid_manifest()
        manifest[smuggled] = "candidate-controlled"
        assert contracts.validate_manifest(manifest,
                                           trusted_protocol=trusted_protocol()) != [], \
            smuggled


def test_manifest_rejects_wrong_configured_identities():
    for field, bad in (("protocol_sha256", "0" * 64),
                       ("input_policy_sha256", "1" * 64),
                       ("runtime_sha256", "2" * 64),
                       ("evaluator_sha256", "3" * 64),
                       ("trial_family", "rf.other.family_v9")):
        manifest = valid_manifest()
        manifest[field] = bad
        text = joined(contracts.validate_manifest(manifest,
                                                  trusted_protocol=trusted_protocol()))
        assert text.find(field) >= 0, field
    # The source identity is candidate-owned: the protocol does not pin it, so
    # only its format is checked (covered by the bad-hash test above).


def test_manifest_rejects_mismatched_original_root():
    manifest = valid_manifest()
    manifest["lineage"]["original_root_id"] = "other-root-1"
    text = joined(contracts.validate_manifest(manifest,
                                              trusted_protocol=trusted_protocol()))
    assert text.find("original_root_id") >= 0


def test_manifest_rejects_bad_hashes():
    for bad in ("A" * 64, "g" * 64, "a" * 63, "a" * 65, "", None, 5):
        manifest = valid_manifest()
        manifest["config_sha256"] = bad
        assert contracts.validate_manifest(manifest,
                                           trusted_protocol=trusted_protocol()) != [], bad


def test_manifest_rejects_bad_candidate_id_and_morphology():
    for bad in ("candidate-1", "rf-CODEGEN-x", "rf-codegen-", "rf-codegen-../esc",
                None, 7):
        manifest = valid_manifest()
        manifest["candidate_id"] = bad
        assert contracts.validate_manifest(manifest,
                                           trusted_protocol=trusted_protocol()) != [], bad
    for field, bad in (("morphology", "research"), ("authority", "granted")):
        manifest = valid_manifest()
        manifest[field] = bad
        assert contracts.validate_manifest(manifest,
                                           trusted_protocol=trusted_protocol()) != []


def test_manifest_lineage_generations():
    ok1 = {"original_root_id": ROOT, "parent_candidate_id": PARENT,
           "refinement_generation": 1}
    ok2 = {"original_root_id": ROOT, "parent_candidate_id": PARENT,
           "refinement_generation": 2}
    assert contracts.validate_manifest(valid_manifest(ok1),
                                       trusted_protocol=trusted_protocol()) == []
    assert contracts.validate_manifest(valid_manifest(ok2),
                                       trusted_protocol=trusted_protocol()) == []
    orphan = {"original_root_id": ROOT, "parent_candidate_id": None,
              "refinement_generation": 1}
    text = joined(contracts.validate_manifest(valid_manifest(orphan),
                                              trusted_protocol=trusted_protocol()))
    assert text.find("requires parent_candidate_id") >= 0
    reset = {"original_root_id": ROOT, "parent_candidate_id": PARENT,
             "refinement_generation": 0}
    text = joined(contracts.validate_manifest(valid_manifest(reset),
                                              trusted_protocol=trusted_protocol()))
    assert text.find("reset") >= 0
    too_far = {"original_root_id": ROOT, "parent_candidate_id": PARENT,
               "refinement_generation": 3}
    text = joined(contracts.validate_manifest(valid_manifest(too_far),
                                              trusted_protocol=trusted_protocol()))
    assert text.find("outside 0..2") >= 0


def test_manifest_rejects_bool_and_type_masquerades():
    boolgen = {"original_root_id": ROOT, "parent_candidate_id": None,
               "refinement_generation": True}
    text = joined(contracts.validate_manifest(valid_manifest(boolgen),
                                              trusted_protocol=trusted_protocol()))
    assert text.find("exact int") >= 0
    strgen = {"original_root_id": ROOT, "parent_candidate_id": None,
              "refinement_generation": "0"}
    assert contracts.validate_manifest(valid_manifest(strgen),
                                      trusted_protocol=trusted_protocol()) != []
    floatgen = {"original_root_id": ROOT, "parent_candidate_id": None,
                "refinement_generation": 0.0}
    assert contracts.validate_manifest(valid_manifest(floatgen),
                                      trusted_protocol=trusted_protocol()) != []


def test_manifest_rejects_subclass_and_object_injection():
    class FakeDict(dict):
        pass

    class FakeInt(int):
        pass

    assert contracts.validate_manifest(FakeDict(valid_manifest()),
                                       trusted_protocol=trusted_protocol()) != []
    manifest = valid_manifest()
    manifest["config_sha256"] = FakeInt(1)
    assert contracts.validate_manifest(manifest,
                                       trusted_protocol=trusted_protocol()) != []
    manifest = valid_manifest()
    manifest["morphology"] = object()
    assert contracts.validate_manifest(manifest,
                                       trusted_protocol=trusted_protocol()) != []
    assert contracts.validate_manifest(None, trusted_protocol=trusted_protocol()) != []
    assert contracts.validate_manifest((), trusted_protocol=trusted_protocol()) != []


def test_exact_json_refuses_nan_infinity_and_huge_ints():
    assert not contracts.is_exact_json(float("nan"))
    assert not contracts.is_exact_json(float("inf"))
    assert not contracts.is_exact_json(-float("inf"))
    assert not contracts.is_exact_json(2 ** 70)
    assert not contracts.is_exact_json({"value": float("nan")})
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            contracts.canonical_json_sha256(bad)
    with pytest.raises(ValueError):
        contracts.canonical_json_sha256({"deep": [2 ** 70]})
    manifest = valid_manifest()
    manifest["extra_note"] = float("nan")
    assert contracts.validate_manifest(manifest,
                                       trusted_protocol=trusted_protocol()) != []


def test_exact_json_refuses_excessive_depth_and_size():
    deep = current = {}
    for _ in range(contracts.MAX_DEPTH + 4):
        current["child"] = {}
        current = current["child"]
    assert not contracts.is_exact_json(deep)
    assert contracts.validate_manifest(deep,
                                       trusted_protocol=trusted_protocol()) != []
    wide = valid_manifest()
    wide["candidate_id"] = "rf-codegen-" + "a" * 5000
    assert contracts.validate_manifest(wide,
                                       trusted_protocol=trusted_protocol()) != []
    assert not contracts.is_exact_json("x" * (contracts.MAX_STRING_CHARS + 1))
    too_many = {"rows": [{"n": i} for i in range(contracts.MAX_CONTAINER_ITEMS + 1)]}
    assert not contracts.is_exact_json(too_many)


def test_canonical_json_sha256_known_answer_and_invariance():
    fixture = {"b": 2, "a": [1, 2, {"c": None}], "s": "x\"y\n"}
    assert contracts.canonical_json_sha256(fixture) == CANON_FIXTURE_DIGEST
    reordered = {"s": "x\"y\n", "b": 2, "a": [1, 2, {"c": None}]}
    assert contracts.canonical_json_sha256(reordered) == CANON_FIXTURE_DIGEST
    assert contracts.canonical_json_sha256({"a": True}) \
        != contracts.canonical_json_sha256({"a": 1})
    assert contracts.canonical_json_sha256({"ab": 1}) \
        != contracts.canonical_json_sha256({"a": 1})
    request = {
        "schema": "research_codegen.request.v1",
        "candidate_id": CANDIDATE,
        "fold_id": "fold-dev-2010-2017",
        "entity_id": "XLK",
        "decision_id": "decision-2030-03-04",
        "cutoff": "2030-03-04T14:00:00Z",
        "input_policy_sha256": POLICY,
        "allowed_source_ids": ["yahoo_collectors", "incumbent_store"],
    }
    assert contracts.canonical_json_sha256(request) == REQUEST_DIGEST
    assert contracts.canonical_json_sha256(trusted_schedule()) == SCHEDULE_DIGEST


# ------------------------------------------------------------ output rows

def test_valid_output_envelope_accepts_and_empty_schedule_zero_opportunity():
    assert output_contract.validate_output_envelope(
        valid_output(), trusted_schedule=trusted_schedule()) == []
    empty_schedule = trusted_schedule()
    empty_schedule["decision_ids"] = []
    empty_output = valid_output()
    empty_output["rows"] = []
    assert output_contract.validate_output_envelope(
        empty_output, trusted_schedule=empty_schedule) == []
    text = joined(output_contract.validate_output_envelope(
        valid_output(), trusted_schedule=empty_schedule))
    assert text.find("conserve") >= 0


def test_output_rejects_dropped_duplicate_swapped_shifted_extra_rows():
    base = valid_output()
    dropped = copy.deepcopy(base)
    dropped["rows"] = dropped["rows"][:1]
    assert output_contract.validate_output_envelope(
        dropped, trusted_schedule=trusted_schedule()) != []
    duplicated = copy.deepcopy(base)
    duplicated["rows"] = [duplicated["rows"][0], duplicated["rows"][0]]
    assert output_contract.validate_output_envelope(
        duplicated, trusted_schedule=trusted_schedule()) != []
    swapped = copy.deepcopy(base)
    swapped["rows"].reverse()
    assert output_contract.validate_output_envelope(
        swapped, trusted_schedule=trusted_schedule()) != []
    shifted = copy.deepcopy(base)
    shifted["rows"] = [
        {"decision_id": "decision-shifted-1", "status": "available",
         "value": 1, "reason": None},
        {"decision_id": "decision-2030-03-04", "status": "available",
         "value": 1, "reason": None},
    ]
    assert output_contract.validate_output_envelope(
        shifted, trusted_schedule=trusted_schedule()) != []
    extra = copy.deepcopy(base)
    extra["rows"].append({"decision_id": "decision-2030-03-06",
                          "status": "available", "value": 1, "reason": None})
    assert output_contract.validate_output_envelope(
        extra, trusted_schedule=trusted_schedule()) != []
    schedule3 = trusted_schedule()
    schedule3["decision_ids"] = ["decision-2030-03-04", "decision-2030-03-05",
                                 "decision-2030-03-06"]
    assert output_contract.validate_output_envelope(
        base, trusted_schedule=schedule3) != []


def test_output_status_value_reason_consistency():
    ok_missing = copy.deepcopy(valid_output())
    ok_missing["rows"][0] = {"decision_id": "decision-2030-03-04",
                             "status": "missing", "value": None,
                             "reason": "source unavailable at cutoff"}
    assert output_contract.validate_output_envelope(
        ok_missing, trusted_schedule=trusted_schedule()) == []
    bool_value = copy.deepcopy(valid_output())
    bool_value["rows"][0]["value"] = True
    text = joined(output_contract.validate_output_envelope(
        bool_value, trusted_schedule=trusted_schedule()))
    assert text.find("strict finite") >= 0
    for bad in (float("nan"), float("inf"), -float("inf"), "0.5", None):
        row = copy.deepcopy(valid_output())
        row["rows"][0]["value"] = bad
        assert output_contract.validate_output_envelope(
            row, trusted_schedule=trusted_schedule()) != [], bad
    reason_on_available = copy.deepcopy(valid_output())
    reason_on_available["rows"][0]["reason"] = "why"
    assert output_contract.validate_output_envelope(
        reason_on_available, trusted_schedule=trusted_schedule()) != []
    value_on_missing = copy.deepcopy(valid_output())
    value_on_missing["rows"][1]["value"] = 0.5
    assert output_contract.validate_output_envelope(
        value_on_missing, trusted_schedule=trusted_schedule()) != []
    blank_reason = copy.deepcopy(valid_output())
    blank_reason["rows"][1]["reason"] = ""
    assert output_contract.validate_output_envelope(
        blank_reason, trusted_schedule=trusted_schedule()) != []
    bad_status = copy.deepcopy(valid_output())
    bad_status["rows"][1]["status"] = "passed"
    assert output_contract.validate_output_envelope(
        bad_status, trusted_schedule=trusted_schedule()) != []


def test_output_rejects_authority_label_and_stats_smuggling():
    for smuggled, payload in (("label", 1), ("p_value", 0.01),
                              ("eligibility", True), ("cost_bps", 10),
                              ("gate", "open"), ("authority_granted", True),
                              ("statistics", {"t": 2.0}), ("accepted", True),
                              ("signal", 1.0), ("exec_time", "2030-03-04T14:00:00Z")):
        envelope = copy.deepcopy(valid_output())
        envelope["rows"][0][smuggled] = payload
        assert output_contract.validate_output_envelope(
            envelope, trusted_schedule=trusted_schedule()) != [], smuggled


def test_output_rejects_identity_and_schedule_type_mismatch():
    for field, bad in (("candidate_id", PARENT), ("fold_id", "fold-other-1"),
                       ("entity_id", "XLF"), ("input_policy_sha256", "0" * 64)):
        envelope = copy.deepcopy(valid_output())
        envelope[field] = bad
        assert output_contract.validate_output_envelope(
            envelope, trusted_schedule=trusted_schedule()) != [], field
    schedule = trusted_schedule()
    schedule["decision_ids"] = ["decision-2030-03-04", True]
    text = joined(output_contract.validate_output_envelope(
        valid_output(), trusted_schedule=schedule))
    assert text.find("trusted_schedule") >= 0
    schedule = trusted_schedule()
    schedule["decision_ids"] = ["decision-2030-03-04", "decision-2030-03-04"]
    text = joined(output_contract.validate_output_envelope(
        valid_output(), trusted_schedule=schedule))
    assert text.find("duplicate") >= 0
    assert output_contract.validate_output_envelope(
        copy.deepcopy(valid_output()), trusted_schedule=object()) != []
    envelope = copy.deepcopy(valid_output())
    envelope["rows"][0]["decision_id"] = 5
    assert output_contract.validate_output_envelope(
        envelope, trusted_schedule=trusted_schedule()) != []


# --------------------------------------------------------------- admission

def test_complete_receipts_stay_zero_authority_and_dormant():
    result = admission.assess_prerequisites(
        valid_manifest(), trusted_protocol=trusted_protocol(),
        owner_receipts=owner_receipts())
    assert result["status"] == "STRUCTURALLY_COMPLETE_DISABLED"
    assert result["violations"] == []
    assert result["authority_granted"] is False
    assert result["generation_enabled"] is False
    assert result["execution_enabled"] is False
    assert result["evaluation_enabled"] is False
    assert result["trusted_origin_and_effective_boundaries"] == "UNQUALIFIED"
    assert result["note"].find("independently accepted owner integration") >= 0


def test_missing_required_receipt_blocks_despite_pass_claim():
    receipts = owner_receipts()
    del receipts["per_decision_schedule"]
    receipts["opaque_metric"] = {
        "schema": "research_codegen.owner_reference.v1",
        "evidence_id": "evidence-metric-0001",
        "source_sha256": SOURCE,
        "protocol_sha256": PROTOCOL_SHA,
        "accepted": True,
        "pass": True,
    }
    result = admission.assess_prerequisites(
        valid_manifest(), trusted_protocol=trusted_protocol(),
        owner_receipts=receipts)
    assert result["status"] == "PREREQUISITES_INVALID"
    text = joined(result["violations"])
    assert text.find("required receipt missing") >= 0
    assert text.find("unexpected extra receipt") >= 0
    assert result["generation_enabled"] is False
    assert result["authority_granted"] is False


def test_receipt_truth_flags_are_never_accepted():
    for flag in ("accepted", "pass", "isolation", "admitted", "authority_granted",
                 "generation_enabled", "evaluation_enabled"):
        receipts = owner_receipts()
        receipts["per_decision_schedule"][flag] = True
        result = admission.assess_prerequisites(
            valid_manifest(), trusted_protocol=trusted_protocol(),
            owner_receipts=receipts)
        assert result["status"] == "PREREQUISITES_INVALID", flag
        assert joined(result["violations"]).find("closed object required") >= 0
    complete = admission.assess_prerequisites(
        valid_manifest(), trusted_protocol=trusted_protocol(),
        owner_receipts=owner_receipts())
    assert complete["generation_enabled"] is False


def test_receipt_binding_mismatches_refuse():
    for field, bad in (("source_sha256", "9" * 64),
                       ("protocol_sha256", "8" * 64),
                       ("evidence_id", ""), ("schema", "other.schema.v1")):
        receipts = owner_receipts()
        receipts["source_runtime_binding"][field] = bad
        result = admission.assess_prerequisites(
            valid_manifest(), trusted_protocol=trusted_protocol(),
            owner_receipts=receipts)
        assert result["status"] == "PREREQUISITES_INVALID", field
        assert joined(result["violations"]).find(field) >= 0


def test_assessment_refuses_invalid_manifests_and_receipts():
    result = admission.assess_prerequisites(
        object(), trusted_protocol=trusted_protocol(),
        owner_receipts=owner_receipts())
    assert result["status"] == "PREREQUISITES_INVALID"
    assert result["generation_enabled"] is False
    result = admission.assess_prerequisites(
        valid_manifest(), trusted_protocol=trusted_protocol(),
        owner_receipts=[("source_runtime_binding", "x")])
    assert result["status"] == "PREREQUISITES_INVALID"
    receipts = owner_receipts()
    receipts["per_decision_schedule"]["evidence_id"] = object()
    result = admission.assess_prerequisites(
        valid_manifest(), trusted_protocol=trusted_protocol(),
        owner_receipts=receipts)
    assert result["status"] == "PREREQUISITES_INVALID"


# ------------------------------------------------- package dormancy surface

def test_no_candidate_lifecycle_or_enum_integration():
    import engine.research_codegen as package

    assert package.__all__ == []
    for module in (package, contracts, output_contract, admission):
        for name in ("CandidateState", "CandidateLifecycle", "CodegenCandidate",
                     "admit_candidate", "enable_generation", "run_candidate",
                     "generation_enabled", "QUALIFICATION_ISSUED"):
            assert not hasattr(module, name), name
    # Other CI test modules may have legitimately imported these siblings at
    # collection time. Inspect eager initializer imports in a fresh process.
    import subprocess
    import sys
    from pathlib import Path

    static_probe = """import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import engine.research_codegen as package
assert package.__all__ == []
for sibling in ("accounting_contract", "evaluation", "transport"):
    assert "engine.research_codegen." + sibling not in sys.modules
    assert not hasattr(package, sibling)
"""
    probe = subprocess.run([sys.executable, "-I", "-c", static_probe],
                           cwd=Path(__file__).resolve().parents[1],
                           capture_output=True, text=True, timeout=15)
    assert probe.returncode == 0, probe.stderr


def test_violation_lists_are_plain_deduped_str_lists():
    result = contracts.validate_manifest(valid_manifest(lineage={
        "original_root_id": "", "parent_candidate_id": None,
        "refinement_generation": 9}),
        trusted_protocol=trusted_protocol())
    assert type(result) is list
    assert all(type(item) is str for item in result)
    assert len(result) == len(set(result))
    assert len(result) >= 2  # bad generation and missing parent at once


def test_refinement_cannot_name_itself_as_parent():
    for generation in (1, 2):
        manifest = valid_manifest()
        manifest["lineage"].update(parent_candidate_id=manifest["candidate_id"],
                                   refinement_generation=generation)
        errors = contracts.validate_manifest(manifest, trusted_protocol=trusted_protocol())
        assert errors, "a refinement self-edge cannot be a historical parent"
