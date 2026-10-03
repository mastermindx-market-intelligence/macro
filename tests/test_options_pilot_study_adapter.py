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
        if "__pycache__" in path.parts:
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
            self.assertFalse(entry["present"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
