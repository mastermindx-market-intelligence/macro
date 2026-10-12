#!/usr/bin/env python3
"""Tests for the finite options pilot study binding/refusal adapter.

Covers the S-stage acceptance: parse, bind, synthetic reference, refuse, report.
The tests never invoke the empirical path as anything other than an unconditional
refusal and never mutate the supplied reference files.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ADAPTER = ROOT / "scripts" / "options_pilot_study_adapter.py"
RESEARCH = ROOT / "research" / "options_intelligence" / "2026-10-03"
SPEC = RESEARCH / "pilot-study-spec.v1.json"
REFERENCE = RESEARCH / "pilot-p3-reference.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("options_pilot_study_adapter", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()

REQUIRED_CASES = (
    "beta_zero_exactly_recovers_incumbent",
    "negative_feature_keeps_variance_positive",
    "zero_target_valid_affine_boundary",
    "paired_qlike_is_invariant_to_common_variance_units",
    "last_60_eligible_sessions_only",
    "chronology_valid_does_not_attest_capture",
)


def run_cli(*args):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(ADAPTER), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
    )


def parse_stdout(completed):
    return json.loads(completed.stdout)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_tree():
    entries = []
    for path in sorted(ROOT.rglob("*")):
        if "__pycache__" in path.relative_to(ROOT).parts:
            continue
        entries.append((str(path.relative_to(ROOT)), path.is_dir()))
    return entries


class InspectTests(unittest.TestCase):
    def test_original_inspect_keeps_spec_bytes_immutable(self):
        before = sha256_file(SPEC)
        self.assertEqual(before, adapter.EXPECTED_SPEC_SHA256)
        first = run_cli("--spec", str(SPEC), "--mode", "inspect")
        second = run_cli("--spec", str(SPEC), "--mode", "inspect")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(sha256_file(SPEC), before)

    def test_inspect_reports_required_facts(self):
        report = parse_stdout(run_cli("--spec", str(SPEC), "--mode", "inspect"))
        self.assertEqual(report["schema"], adapter.ADAPTER_SCHEMA)
        self.assertEqual(report["status"], "PARSED_BOUND")
        self.assertEqual(report["spec_schema_version"], "pilot-study-spec.v1")
        self.assertEqual(
            report["source_hashes"]["spec"]["sha256"], adapter.EXPECTED_SPEC_SHA256
        )
        self.assertTrue(report["source_hashes"]["spec"]["hash_match"])
        self.assertEqual(report["pilot_oif_map"], adapter.PILOT_OIF_MAP)
        self.assertEqual(report["pilots_count"], 6)
        self.assertEqual(
            report["binding_fields_count"], 9
        )
        self.assertTrue(report["binding_fields_all_null"])
        self.assertTrue(all(v is None for v in report["binding_fields"].values()))
        self.assertEqual(set(report["binding_fields"]), set(adapter.BINDING_FIELD_NAMES))
        self.assertTrue(report["split_dates_unchanged"])
        self.assertEqual(set(report["split_dates"]), set(adapter.SPLIT_DATE_FIELDS))
        self.assertTrue(all(v is None for v in report["split_dates"].values()))
        self.assertEqual(set(report["empirical_gates"]), set(adapter.EMPIRICAL_GATES))
        self.assertTrue(all(v == "HELD" for v in report["empirical_gates"].values()))
        self.assertEqual(report["empirical_gates_held_count"], 7)
        for pilot in report["pilots"]:
            self.assertEqual(pilot["empirical_status"], "BLOCKED")
            self.assertEqual(pilot["empirical_receipts"], "UNAVAILABLE")
        self.assertFalse(report["source_certified_accepted"])
        self.assertFalse(report["rank_authority"])
        self.assertFalse(report["activation_authority"])
        self.assertFalse(report["trading_authority"])
        self.assertFalse(report["mission_complete"])

    def test_inspect_does_not_fetch_declared_inputs(self):
        report = parse_stdout(run_cli("--spec", str(SPEC), "--mode", "inspect"))
        for entry in report["declared_input_manifest"]:
            self.assertFalse(entry["fetched"])
            self.assertIsNone(entry["present"])

    def test_no_boolean_claimed_as_observation(self):
        report = parse_stdout(run_cli("--spec", str(SPEC), "--mode", "inspect"))
        for key, value in report.items():
            if isinstance(value, bool):
                self.assertNotIn("observ", key.lower())
                self.assertNotIn("empiric", key.lower())


class RefusalTests(unittest.TestCase):
    def test_missing_spec_argument(self):
        completed = run_cli("--mode", "inspect")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(parse_stdout(completed)["code"], "MISSING_SPEC_ARGUMENT")

    def test_missing_spec_file(self):
        completed = run_cli("--spec", str(ROOT / "does-not-exist.json"), "--mode", "inspect")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(parse_stdout(completed)["code"], "SPEC_MISSING")

    def test_missing_reference_argument(self):
        completed = run_cli("--spec", str(SPEC), "--mode", "synthetic-p3")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(parse_stdout(completed)["code"], "MISSING_REFERENCE_ARGUMENT")

    def test_empirical_refuses_with_valid_spec(self):
        completed = run_cli("--spec", str(SPEC), "--mode", "empirical")
        self.assertNotEqual(completed.returncode, 0)
        report = parse_stdout(completed)
        self.assertEqual(report["status"], "REFUSED")
        self.assertEqual(report["code"], "EMPIRICAL_GATES_UNSATISFIED")

    def test_empirical_refusal_survives_synthetic_authorization_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            forged = json.loads(SPEC.read_bytes())
            forged["authorize_empirical"] = True
            forged["binding_fields"] = {k: "receipt" for k in adapter.BINDING_FIELD_NAMES}
            path = Path(tmp) / "forged.json"
            path.write_bytes(json.dumps(forged).encode("utf-8"))
            completed = run_cli("--spec", str(path), "--mode", "empirical")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(parse_stdout(completed)["code"], "SPEC_HASH_MISMATCH")

    def test_tampered_spec_rejected_by_hash_before_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "spec.json"
            raw = bytearray(SPEC.read_bytes())
            raw[10] = raw[10] ^ 0x01
            tampered.write_bytes(bytes(raw))
            completed = run_cli("--spec", str(tampered), "--mode", "inspect")
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(parse_stdout(completed)["code"], "SPEC_HASH_MISMATCH")

    def test_duplicate_key_spec_hash_precedes_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            duplicate = Path(tmp) / "duplicate.json"
            duplicate.write_bytes(b'{"schema_version": "pilot-study-spec.v1", "schema_version": "x"}')
            completed = run_cli("--spec", str(duplicate), "--mode", "inspect")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(parse_stdout(completed)["code"], "SPEC_HASH_MISMATCH")

    def test_tampered_reference_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "reference.py"
            tampered.write_bytes(
                REFERENCE.read_bytes() + b'\nprint("EXECUTED_TAMPERED_REFERENCE")\n'
            )
            completed = run_cli(
                "--spec", str(SPEC), "--mode", "synthetic-p3", "--reference", str(tampered)
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("EXECUTED_TAMPERED_REFERENCE", completed.stdout)
        report = parse_stdout(completed)
        self.assertEqual(report["code"], "REFERENCE_HASH_MISMATCH")
        self.assertNotIn("reference_cases", report)

    def test_inspect_also_rejects_tampered_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "reference.py"
            tampered.write_bytes(REFERENCE.read_bytes() + b"\n")
            completed = run_cli("--spec", str(SPEC), "--mode", "inspect", "--reference", str(tampered))
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(parse_stdout(completed)["code"], "REFERENCE_HASH_MISMATCH")


class ParseTests(unittest.TestCase):
    def test_duplicate_json_key_typed(self):
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.parse_json_bytes(b'{"a": 1, "a": 2}', "test")
        self.assertEqual(ctx.exception.code, "DUPLICATE_JSON_KEY")

    def test_nonfinite_json_typed(self):
        for payload in (b'{"a": NaN}', b'{"a": Infinity}', b'{"a": -Infinity}'):
            with self.assertRaises(adapter.Refusal) as ctx:
                adapter.parse_json_bytes(payload, "test")
            self.assertEqual(ctx.exception.code, "NONFINITE_JSON")

    def test_malformed_and_invalid_utf8_typed(self):
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.parse_json_bytes(b"{not json", "test")
        self.assertEqual(ctx.exception.code, "MALFORMED_JSON")
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.parse_json_bytes(b"\xff\xfe", "test")
        self.assertEqual(ctx.exception.code, "INVALID_UTF8")

    def test_valid_spec_still_parses_strictly(self):
        parsed = adapter.parse_json_bytes(SPEC.read_bytes(), "spec")
        self.assertEqual(parsed["schema_version"], "pilot-study-spec.v1")


class StructureDriftTests(unittest.TestCase):
    def setUp(self):
        self.spec = adapter.parse_json_bytes(SPEC.read_bytes(), "spec")

    def test_complete_six_pilot_family_never_shrinks(self):
        shrunk = copy.deepcopy(self.spec)
        shrunk["pilots"] = shrunk["pilots"][:5]
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.validate_spec_structure(shrunk)
        self.assertEqual(ctx.exception.code, "SPEC_PILOT_MAPPING_MISMATCH")

    def test_pilot_feature_mapping_is_fixed(self):
        drifted = copy.deepcopy(self.spec)
        drifted["pilots"][0]["feature_id"] = "OIF99"
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.validate_spec_structure(drifted)
        self.assertEqual(ctx.exception.code, "SPEC_PILOT_MAPPING_MISMATCH")

    def test_binding_field_cannot_be_bound(self):
        drifted = copy.deepcopy(self.spec)
        drifted["binding_fields"]["dataset_manifest"] = {"sha256": "x"}
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.validate_spec_structure(drifted)
        self.assertEqual(ctx.exception.code, "SPEC_BINDING_FIELD_BOUND")

    def test_split_date_cannot_change(self):
        drifted = copy.deepcopy(self.spec)
        drifted["common"]["splits"]["dates"]["training_start"] = "2017-01-01"
        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.validate_spec_structure(drifted)
        self.assertEqual(ctx.exception.code, "SPEC_SPLIT_DATE_BOUND")


class SyntheticP3Tests(unittest.TestCase):
    def test_synthetic_positive_branch_runs_actual_reference(self):
        completed = run_cli(
            "--spec", str(SPEC), "--mode", "synthetic-p3", "--reference", str(REFERENCE)
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = parse_stdout(completed)
        self.assertEqual(report["status"], "SYNTHETIC_REFERENCE_PASSED")
        self.assertTrue(report["synthetic_only"])
        self.assertFalse(report["empirical_acceptance"])
        self.assertFalse(report["mission_complete"])
        self.assertFalse(report["source_certified_accepted"])
        self.assertFalse(report["rank_authority"])
        self.assertFalse(report["activation_authority"])
        self.assertFalse(report["trading_authority"])
        self.assertEqual(report["reference_source_sha256"], adapter.EXPECTED_REFERENCE_SHA256)
        self.assertTrue(report["source_hashes"]["reference"]["hash_match"])
        self.assertTrue(report["source_hashes"]["reference"]["executed"])
        self.assertEqual(report["reference_case_count"], report["reference_passed"])
        self.assertFalse(report["reference_empirical_fit_performed"])
        self.assertFalse(report["reference_availability_attested"])
        self.assertFalse(report["reference_production_compatible_schema"])
        by_name = {case["case"]: case for case in report["reference_cases"]}
        for name in REQUIRED_CASES:
            self.assertIn(name, by_name, f"missing reference case {name}")
            self.assertEqual(by_name[name]["result"], "PASS")

    def test_failing_reference_is_refusal(self):
        class Broken:
            @staticmethod
            def run_fixtures():
                raise AssertionError("boom")

        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.invoke_reference(Broken)
        self.assertEqual(ctx.exception.code, "REFERENCE_FIXTURE_FAILED")

    def test_incomplete_reference_result_is_refusal(self):
        class Incomplete:
            @staticmethod
            def run_fixtures():
                return {"case_count": 3, "passed": 2, "source_sha256": adapter.EXPECTED_REFERENCE_SHA256}

        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.invoke_reference(Incomplete)
        self.assertEqual(ctx.exception.code, "REFERENCE_FIXTURE_FAILED")

    def test_reference_api_missing_is_refusal(self):
        class Empty:
            pass

        with self.assertRaises(adapter.Refusal) as ctx:
            adapter.invoke_reference(Empty)
        self.assertEqual(ctx.exception.code, "REFERENCE_API_MISSING")

    def test_validated_loader_executes_only_validated_bytes(self):
        module = adapter.load_validated_reference(
            b"VALUE = 41 + 1\n", str(ROOT / "virtual_reference.py")
        )
        self.assertEqual(module.VALUE, 42)


class SideEffectTests(unittest.TestCase):
    def test_no_filesystem_or_network_effects(self):
        before = snapshot_tree()
        run_cli("--spec", str(SPEC), "--mode", "inspect")
        run_cli("--spec", str(SPEC), "--mode", "synthetic-p3", "--reference", str(REFERENCE))
        run_cli("--spec", str(SPEC), "--mode", "empirical")
        after = snapshot_tree()
        self.assertEqual(before, after)

    def test_adapter_has_no_network_imports(self):
        source = ADAPTER.read_text(encoding="utf-8")
        for name in adapter.FORBIDDEN_NETWORK_MODULES:
            self.assertIsNone(
                re.search(rf"^\s*(import|from)\s+{name}\b", source, re.MULTILINE),
                f"adapter must not import {name}",
            )


# ── Q02-U1: as-of receipt, scaler causality, no-rescue and label refusals ──

def _reference_module():
    raw, _ = adapter.read_pinned_bytes(str(REFERENCE), "reference", adapter.EXPECTED_REFERENCE_SHA256)
    return adapter.load_validated_reference(raw, str(REFERENCE))


def _mutant_reference(testcase, old: bytes, new: bytes):
    raw, _ = adapter.read_pinned_bytes(str(REFERENCE), "reference", adapter.EXPECTED_REFERENCE_SHA256)
    testcase.assertEqual(raw.count(old), 1)
    return adapter.load_validated_reference(
        raw.replace(old, new), str(REFERENCE), name="options_p3_reference_mutant"
    )


# Inline copy of the reference chronology row (pilot-p3-reference.py:404-410).
_BASE_RECORD = {
    "id": "historical-a",
    "source_revision_id": "synthetic-source-a",
    "feature_revision_id": "synthetic-feature-a",
    "baseline_revision_id": "synthetic-baseline-a",
    "label_revision_id": "synthetic-label-a",
    "formation_at_ns": 1000,
    "label_mature_at_ns": 2000,
    "label_revision_available_at_ns": 2000,
    "feature_input_available_at_ns": 900,
    "feature_published_at_ns": 950,
    "feature_received_at_ns": 980,
    "nuisance_fit_at_ns": 800,
    "nuisance_latest_training_label_mature_at_ns": 790,
    "baseline_input_available_at_ns": 900,
    "baseline_fit_at_ns": 850,
    "baseline_latest_training_label_mature_at_ns": 840,
    "baseline_published_at_ns": 960,
    "baseline_received_at_ns": 990,
}


def _scaler_history():
    # Inline copy of the reference scaler census (pilot-p3-reference.py:426-427).
    return [
        {
            "root": "SYNTHETIC",
            "clock_bin": "09:35",
            "session": f"session-{i:03d}",
            "formation_at_ns": 100 + i,
            "available_at_ns": 101 + i,
            "eligible": True,
            "value": float(i),
        }
        for i in range(65)
    ]


def _no_rescue_violations(report) -> list[str]:
    violations = []
    expected_policy = {
        "beta_domain": [-1, 1],
        "bracket_tolerance": 1e-10,
        "max_iterations": 100,
        "intercept": False,
        "epsilon_floor": False,
        "failed_row_fallback": False,
    }
    if report.get("reference_solver_policy") != expected_policy:
        violations.append("reference_solver_policy")
    expected_codes = {
        "negative_target_is_not_dropped": "INVALID_DOMAIN",
        "zero_baseline_is_not_floored": "INVALID_DOMAIN",
        "nonfinite_feature_is_not_clipped": "NONFINITE_INPUT",
        "positive_variance_underflow_is_not_zero": "POSITIVE_UNDERFLOW",
        "zero_weight_does_not_drop_failed_row": "INVALID_DOMAIN",
        "empty_fit_does_not_fallback": "NO_TRAINING_ROWS",
        "scaler_zero_MAD_refuses": "ZERO_MAD",
        "invalid_scale_cannot_epsilon_rescue": "INVALID_SCALE",
    }
    cases = {}
    for case in report.get("reference_cases") or []:
        if isinstance(case, dict):
            cases[case.get("case")] = case
    for name, code in expected_codes.items():
        case = cases.get(name)
        if case is None:
            violations.append(f"missing:{name}")
            continue
        if case.get("result") != "PASS":
            violations.append(f"result:{name}")
        if case.get("refusal") != code:
            violations.append(f"refusal:{name}")
    clipped = cases.get("RZ_is_unclipped")
    if clipped is None:
        violations.append("missing:RZ_is_unclipped")
    else:
        if clipped.get("result") != "PASS":
            violations.append("result:RZ_is_unclipped")
        if "refusal" in clipped:
            violations.append("refusal:RZ_is_unclipped")
        observed = clipped.get("observed")
        z_value = observed.get("z") if isinstance(observed, dict) else None
        if isinstance(z_value, bool) or not isinstance(z_value, (int, float)) or not z_value > 1000:
            violations.append("observed.z:RZ_is_unclipped")
    return violations


def _increment_claims(obj, path="$") -> list[str]:
    """Path of every dict key or string containing 'increment', case-insensitive."""
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{path}.{key}"
            if isinstance(key, str) and "increment" in key.lower():
                found.append(child)
            found.extend(_increment_claims(value, child))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found.extend(_increment_claims(value, f"{path}[{index}]"))
    elif isinstance(obj, str) and "increment" in obj.lower():
        found.append(path)
    return found


class Q02U1CausalityAndNoRescueTests(unittest.TestCase):
    def test_reference_refuses_late_baseline_board_receipt(self):
        ref = _reference_module()
        self.assertEqual(
            ref.validate_training_chronology([_BASE_RECORD], 3000, 4000)["status"],
            "ORDERING_VALID",
        )
        expected_detail = "baseline:historical-a"
        overrides = (
            {"baseline_received_at_ns": 1001},
            {"baseline_published_at_ns": 1001, "baseline_received_at_ns": 1001},
            {"baseline_input_available_at_ns": 961},
            {"baseline_input_available_at_ns": 1001},
        )
        for override in overrides:
            row = {**_BASE_RECORD, **override}
            with self.assertRaises(ref.Refusal) as ctx:
                ref.validate_training_chronology([row], 3000, 4000)
            self.assertEqual(ctx.exception.code, "PREDICTION_NOT_ASOF")
            self.assertEqual(ctx.exception.detail, expected_detail)

        mutant = _mutant_reference(
            self,
            b'for prefix in ("feature", "baseline"):',
            b'for prefix in ("feature",):',
        )
        for override in overrides:
            row = {**_BASE_RECORD, **override}
            result = mutant.validate_training_chronology([row], 3000, 4000)
            self.assertEqual(result["status"], "ORDERING_VALID")

    def test_reference_refuses_feature_input_after_publication_or_formation(self):
        ref = _reference_module()
        expected_detail = "feature:historical-a"
        overrides = (
            {"feature_input_available_at_ns": 951},
            {"feature_input_available_at_ns": 1001},
        )
        for override in overrides:
            row = {**_BASE_RECORD, **override}
            with self.assertRaises(ref.Refusal) as ctx:
                ref.validate_training_chronology([row], 3000, 4000)
            self.assertEqual(ctx.exception.code, "PREDICTION_NOT_ASOF")
            self.assertEqual(ctx.exception.detail, expected_detail)

        mutant = _mutant_reference(
            self,
            b'clocks[f"{prefix}_input_available_at_ns"] <= ',
            b"",
        )
        for override in overrides:
            row = {**_BASE_RECORD, **override}
            result = mutant.validate_training_chronology([row], 3000, 4000)
            self.assertEqual(result["status"], "ORDERING_VALID")

    def test_scaler_refuses_observation_at_fit_and_inverted_availability(self):
        ref = _reference_module()
        history = _scaler_history()
        self.assertEqual(
            ref.robust_scaler(history, 1000, "SYNTHETIC", "09:35")["status"],
            "SCALER_FIT",
        )
        expected_code = "SCALER_FUTURE_INFORMATION"
        variant_at_fit = history[:-1] + [
            {**history[-1], "formation_at_ns": 1000, "available_at_ns": 1000}
        ]
        variant_inverted = history[:-1] + [{**history[-1], "available_at_ns": 163}]
        for variant in (variant_at_fit, variant_inverted):
            with self.assertRaises(ref.Refusal) as ctx:
                ref.robust_scaler(variant, 1000, "SYNTHETIC", "09:35")
            self.assertEqual(ctx.exception.code, expected_code)
            self.assertEqual(ctx.exception.detail, "session-064")

        drop_observed_bound = _mutant_reference(self, b"observed >= cutoff or ", b"")
        self.assertEqual(
            drop_observed_bound.robust_scaler(variant_at_fit, 1000, "SYNTHETIC", "09:35")["status"],
            "SCALER_FIT",
        )
        drop_inverted_bound = _mutant_reference(self, b" or available < observed", b"")
        self.assertEqual(
            drop_inverted_bound.robust_scaler(variant_inverted, 1000, "SYNTHETIC", "09:35")["status"],
            "SCALER_FIT",
        )

    def test_reference_solver_policy_and_nine_no_rescue_cases_pinned(self):
        completed = run_cli(
            "--spec", str(SPEC), "--mode", "synthetic-p3", "--reference", str(REFERENCE)
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = parse_stdout(completed)
        self.assertEqual(_no_rescue_violations(report), [])

        missing_case = copy.deepcopy(report)
        missing_case["reference_cases"] = [
            case for case in missing_case["reference_cases"]
            if case.get("case") != "empty_fit_does_not_fallback"
        ]
        self.assertNotEqual(_no_rescue_violations(missing_case), [])

        floored = copy.deepcopy(report)
        floored["reference_solver_policy"] = {
            **floored["reference_solver_policy"],
            "epsilon_floor": True,
        }
        self.assertNotEqual(_no_rescue_violations(floored), [])

        failed_row = copy.deepcopy(report)
        for case in failed_row["reference_cases"]:
            if case.get("case") == "zero_baseline_is_not_floored":
                case["result"] = "FAIL"
        self.assertNotEqual(_no_rescue_violations(failed_row), [])

        rescued = copy.deepcopy(report)
        for case in rescued["reference_cases"]:
            if case.get("case") == "scaler_zero_MAD_refuses":
                case["refusal"] = "SCALER_FIT"
        self.assertNotEqual(_no_rescue_violations(rescued), [])

        clipped = copy.deepcopy(report)
        for case in clipped["reference_cases"]:
            if case.get("case") == "RZ_is_unclipped":
                case["observed"]["z"] = 1000
        self.assertNotEqual(_no_rescue_violations(clipped), [])

    def test_reports_never_claim_incumbent_information_incrementality(self):
        expected_role = "RESEARCH_INFORMATION_ADAPTER_NOT_RANKER"
        inspect_run = run_cli("--spec", str(SPEC), "--mode", "inspect")
        synthetic_run = run_cli(
            "--spec", str(SPEC), "--mode", "synthetic-p3", "--reference", str(REFERENCE)
        )
        empirical_run = run_cli("--spec", str(SPEC), "--mode", "empirical")
        self.assertEqual(inspect_run.returncode, 0, inspect_run.stdout + inspect_run.stderr)
        self.assertEqual(synthetic_run.returncode, 0, synthetic_run.stdout + synthetic_run.stderr)
        inspect_report = parse_stdout(inspect_run)
        synthetic_report = parse_stdout(synthetic_run)
        empirical_report = parse_stdout(empirical_run)
        for report in (inspect_report, synthetic_report, empirical_report):
            self.assertEqual(_increment_claims(report), [])
        self.assertEqual(inspect_report["b1_ri_role"], expected_role)
        self.assertEqual(synthetic_report["b1_ri_role"], expected_role)
        for pilot in inspect_report["pilots"]:
            self.assertEqual(pilot["b1_ri_role"], expected_role)
        self.assertEqual(empirical_report["status"], "REFUSED")

        spec, digest = adapter.load_spec(str(SPEC))
        patched_note = adapter.B1_RI_NOTE + " Demonstrates incumbent-information incrementality."
        with mock.patch.object(adapter, "B1_RI_NOTE", patched_note):
            forged = adapter.build_inspect_report(spec, digest, None)
        self.assertEqual(_increment_claims(forged), ["$.b1_ri_note"])
        self.assertNotEqual(_increment_claims({"incrementality_label": "x"}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
