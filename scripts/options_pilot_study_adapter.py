#!/usr/bin/env python3
"""Finite study-spec binding and refusal adapter for the options pilot study.

This module is a deliberate boundary, not an inference runner. It performs three
things and nothing else:

* ``inspect`` parses the frozen study specification, binds it to a pinned
  SHA-256 digest and reports the structural facts that the S-stage acceptance
  requires (schema/version, input hashes, the fixed six-pilot OIF mapping, the
  nine unchanged null binding fields, unchanged null split dates, blocked
  empirical status, false authority flags).
* ``synthetic-p3`` hash-validates the supplied synthetic reference, loads it via
  an in-memory ``importlib`` loader only after validation, invokes the reference
  ``run_fixtures()`` and reports the actual synthetic test result with an
  explicit ``synthetic_only`` marker and no empirical acceptance.
* ``empirical`` refuses unconditionally with ``EMPIRICAL_GATES_UNSATISFIED``
  before reading any dataset or fitting anything.

Every input is parsed from bytes. Raw bytes are hashed *before* any JSON
interpretation or Python execution, so a modified, malformed or missing input is
rejected with a structured JSON refusal and a nonzero exit code. ``NaN`` and
``Infinity`` JSON constants and duplicate object keys are refused. No input is
ever fetched automatically and no executable path is loaded without a prior
hash check.

B1-RI is a target-trained summary-information *research* baseline, not the live
incumbent ranker. This adapter never claims rank authority.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
import sys

ADAPTER_SCHEMA = "options.pilot.study.adapter.v1"
EXPECTED_SPEC_SHA256 = "e30796c158da18cffe1b581463ba6820ff33e9acbe8a4248b3fc068e67f70317"
EXPECTED_REFERENCE_SHA256 = "29fc1cc5ff79abc5a7f0377ea1860113adc851f0aad81feb852d27d45a65a11f"
SPEC_SCHEMA_VERSION = "pilot-study-spec.v1"
REFERENCE_SCHEMA_VERSION = "options.p3.positive_offset.reference.v1"

PILOT_IDS = ("P1", "P2", "P3", "P4", "P5", "P6")
PILOT_OIF_MAP = {
    "P1": "OIF01",
    "P2": "OIF04",
    "P3": "OIF19",
    "P4": "OIF22",
    "P5": "OIF13",
    "P6": "OIF35",
}
BINDING_FIELD_NAMES = (
    "principal_adjudication_receipt",
    "incumbent_owners_acceptance_receipts",
    "source_capability_receipt",
    "B0_lineage_manifest",
    "B1_RI_adapter_and_snapshot_receipts",
    "dataset_manifest",
    "split_date_manifest",
    "power_planned_test_lengths",
    "accepted_trial_id",
)
SPLIT_DATE_FIELDS = (
    "training_start",
    "training_fit_cutoff",
    "validation_start",
    "validation_end",
    "test_model_sealed_at",
    "test_start",
    "test_end",
)
EMPIRICAL_GATES = ("G0", "G1", "G2", "G3", "G4", "G5", "G6")

B1_RI_ROLE = "RESEARCH_INFORMATION_ADAPTER_NOT_RANKER"
B1_RI_NOTE = (
    "B1-RI is a target-trained summary-information research baseline evaluated "
    "against each pilot's B0 target model. A result beats this fixed adapter "
    "only; it is not the live incumbent ranker and cannot be substituted for "
    "native-policy outperformance."
)

REFUSAL_EXIT = 2
REQUIRED_SYNTHETIC_CASES = (
    "beta_zero_exactly_recovers_incumbent",
    "negative_feature_keeps_variance_positive",
    "zero_target_valid_affine_boundary",
    "paired_qlike_is_invariant_to_common_variance_units",
    "last_60_eligible_sessions_only",
    "chronology_valid_does_not_attest_capture",
)

FORBIDDEN_NETWORK_MODULES = ("urllib", "socket", "http", "requests", "ftplib", "asyncio")


class Refusal(Exception):
    """A structured, typed refusal that maps to a nonzero process exit."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def emit(payload) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")


def _reject_nonfinite(token: str):
    raise Refusal("NONFINITE_JSON", f"non-finite JSON constant {token!r} is not permitted")


def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise Refusal("DUPLICATE_JSON_KEY", f"duplicate JSON object key {key!r}")
        seen[key] = value
    return seen


def parse_json_bytes(raw: bytes, source: str):
    """Parse raw bytes into JSON with duplicate-key and non-finite refusal."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refusal("INVALID_UTF8", f"{source} is not valid UTF-8: {error}") from error
    try:
        return json.loads(
            text,
            parse_constant=_reject_nonfinite,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except Refusal:
        raise
    except json.JSONDecodeError as error:
        raise Refusal("MALFORMED_JSON", f"{source} is not valid JSON: {error}") from error


def read_file(path: str, label: str) -> bytes:
    """Read a file's raw bytes, refusing a missing or unreadable path."""
    if not os.path.isfile(path):
        raise Refusal(f"{label.upper()}_MISSING", f"{label} path does not exist: {path}")
    try:
        with open(path, "rb") as stream:
            return stream.read()
    except OSError as error:
        raise Refusal(f"{label.upper()}_UNREADABLE", f"{label} cannot be read: {error}") from error


def read_pinned_bytes(path: str, label: str, expected_sha256: str):
    """Read bytes and verify the pinned digest before the caller interprets them."""
    raw = read_file(path, label)
    digest = sha256_hex(raw)
    if digest != expected_sha256:
        raise Refusal(
            f"{label.upper()}_HASH_MISMATCH",
            f"{label} sha256 {digest} does not match pinned {expected_sha256}",
        )
    return raw, digest


def _require_mapping(value, code: str, detail: str):
    if not isinstance(value, dict):
        raise Refusal(code, detail)
    return value


def validate_spec_structure(spec) -> None:
    """Refuse any structure drift away from the frozen specification identity."""
    spec = _require_mapping(spec, "SPEC_SCHEMA_UNQUALIFIED", "spec root is not a JSON object")
    if spec.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise Refusal(
            "SPEC_SCHEMA_UNQUALIFIED",
            f"spec schema_version {spec.get('schema_version')!r} != {SPEC_SCHEMA_VERSION!r}",
        )

    pilots = spec.get("pilots")
    if not isinstance(pilots, list) or len(pilots) != len(PILOT_IDS):
        raise Refusal(
            "SPEC_PILOT_MAPPING_MISMATCH",
            "the complete six-pilot family is required and may not shrink",
        )
    observed = {}
    for pilot in pilots:
        if not isinstance(pilot, dict):
            raise Refusal("SPEC_PILOT_MAPPING_MISMATCH", "pilot entry is not an object")
        observed[pilot.get("id")] = pilot.get("feature_id")
    if observed != PILOT_OIF_MAP:
        raise Refusal(
            "SPEC_PILOT_MAPPING_MISMATCH",
            f"pilot feature mapping {observed} != fixed mapping {PILOT_OIF_MAP}",
        )

    binding = spec.get("binding_fields")
    if not isinstance(binding, dict) or tuple(binding.keys()) != BINDING_FIELD_NAMES:
        raise Refusal(
            "SPEC_BINDING_FIELD_DRIFT",
            "binding_fields key set does not match the expected nine fields",
        )
    bound = {name: value for name, value in binding.items() if value is not None}
    if bound:
        raise Refusal(
            "SPEC_BINDING_FIELD_BOUND",
            f"binding fields must remain unbound null; found {sorted(bound)}",
        )

    try:
        split_dates = spec["common"]["splits"]["dates"]
    except (KeyError, TypeError) as error:
        raise Refusal("SPEC_SPLIT_DATE_DRIFT", f"split dates are not addressable: {error}") from error
    if not isinstance(split_dates, dict) or tuple(split_dates.keys()) != SPLIT_DATE_FIELDS:
        raise Refusal(
            "SPEC_SPLIT_DATE_DRIFT",
            "split date key set does not match the expected seven fields",
        )
    changed = {name: value for name, value in split_dates.items() if value is not None}
    if changed:
        raise Refusal(
            "SPEC_SPLIT_DATE_BOUND",
            f"split dates must remain unchanged null; found {sorted(changed)}",
        )


def load_spec(spec_path: str):
    """Hash, parse and structurally validate the frozen specification."""
    raw, digest = read_pinned_bytes(spec_path, "spec", EXPECTED_SPEC_SHA256)
    spec = parse_json_bytes(raw, "spec")
    validate_spec_structure(spec)
    return spec, digest


def build_spec_hash_block(digest: str) -> dict:
    return {
        "sha256": digest,
        "expected_sha256": EXPECTED_SPEC_SHA256,
        "hash_match": digest == EXPECTED_SPEC_SHA256,
    }


def build_reference_hash_block(digest: str) -> dict:
    return {
        "sha256": digest,
        "expected_sha256": EXPECTED_REFERENCE_SHA256,
        "hash_match": digest == EXPECTED_REFERENCE_SHA256,
        "executed": False,
    }


def build_inspect_report(spec, spec_digest: str, reference_digest) -> dict:
    pilots = []
    for pilot in spec["pilots"]:
        pilots.append(
            {
                "id": pilot["id"],
                "feature_id": pilot["feature_id"],
                "spec_status": pilot.get("status"),
                "empirical_status": "BLOCKED",
                "empirical_receipts": "UNAVAILABLE",
                "b1_ri_role": B1_RI_ROLE,
            }
        )

    declared_inputs = []
    for entry in spec.get("input_manifest", []):
        if isinstance(entry, dict):
            declared_inputs.append(
                {
                    "path": entry.get("path"),
                    "declared_sha256": entry.get("sha256"),
                    "present": False,
                    "fetched": False,
                    "note": "declared only; this adapter never auto-fetches inputs",
                }
            )

    source_hashes = {"spec": build_spec_hash_block(spec_digest), "reference": None}
    if reference_digest is not None:
        source_hashes["reference"] = build_reference_hash_block(reference_digest)

    return {
        "schema": ADAPTER_SCHEMA,
        "status": "PARSED_BOUND",
        "mode": "inspect",
        "spec_schema_version": spec["schema_version"],
        "spec_design_status": spec.get("design_status"),
        "source_hashes": source_hashes,
        "declared_input_manifest": declared_inputs,
        "pilot_oif_map": dict(PILOT_OIF_MAP),
        "pilots_count": len(pilots),
        "pilots": pilots,
        "binding_fields": {name: spec["binding_fields"][name] for name in BINDING_FIELD_NAMES},
        "binding_fields_count": len(BINDING_FIELD_NAMES),
        "binding_fields_all_null": True,
        "split_dates": {name: spec["common"]["splits"]["dates"][name] for name in SPLIT_DATE_FIELDS},
        "split_dates_unchanged": True,
        "empirical_gates": {gate: "HELD" for gate in EMPIRICAL_GATES},
        "empirical_gates_held_count": len(EMPIRICAL_GATES),
        "empirical_status": "BLOCKED_EMPIRICAL_RECEIPTS_UNAVAILABLE",
        "source_certified_accepted": False,
        "rank_authority": False,
        "activation_authority": False,
        "trading_authority": False,
        "mission_complete": False,
        "b1_ri_role": B1_RI_ROLE,
        "b1_ri_note": B1_RI_NOTE,
    }


class _ValidatedSourceLoader(importlib.abc.Loader):
    """Execute already-hash-validated source bytes without touching the path."""

    def __init__(self, source_bytes: bytes, origin: str):
        self._source_bytes = source_bytes
        self._origin = origin

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        try:
            code = compile(self._source_bytes, self._origin, "exec")
        except SyntaxError as error:
            raise Refusal("REFERENCE_COMPILE_ERROR", f"reference did not compile: {error}") from error
        exec(code, module.__dict__)


def load_validated_reference(source_bytes: bytes, origin: str, name: str = "options_p3_reference_validated"):
    """Load a module from hash-validated bytes via an importlib loader."""
    loader = _ValidatedSourceLoader(source_bytes, origin)
    spec = importlib.util.spec_from_loader(name, loader, origin=origin)
    if spec is None:
        raise Refusal("REFERENCE_LOAD_ERROR", "could not build an import spec for the reference")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = origin
    module.__loader__ = loader
    try:
        loader.exec_module(module)
    except Refusal:
        raise
    except Exception as error:  # noqa: BLE001 - any load-time failure is a refusal
        raise Refusal("REFERENCE_LOAD_ERROR", f"reference failed to load: {error}") from error
    return module


def invoke_reference(module) -> dict:
    """Call the reference run_fixtures() and require a complete, clean result."""
    fixtures = getattr(module, "run_fixtures", None)
    if not callable(fixtures):
        raise Refusal("REFERENCE_API_MISSING", "reference does not expose run_fixtures()")
    try:
        result = fixtures()
    except Exception as error:  # noqa: BLE001 - a failing reference is a refusal
        raise Refusal("REFERENCE_FIXTURE_FAILED", f"reference run_fixtures() failed: {error}") from error
    if not isinstance(result, dict):
        raise Refusal("REFERENCE_RESULT_INVALID", "reference run_fixtures() did not return an object")
    if result.get("case_count") != result.get("passed"):
        raise Refusal(
            "REFERENCE_FIXTURE_FAILED",
            f"reference reported {result.get('passed')} passed of {result.get('case_count')}",
        )
    if result.get("source_sha256") != EXPECTED_REFERENCE_SHA256:
        raise Refusal(
            "REFERENCE_SELF_HASH_MISMATCH",
            "reference self-reported source_sha256 does not match the pinned digest",
        )
    return result


def run_synthetic_p3(spec_digest: str, reference_path: str) -> dict:
    """Validate the reference digest, then load and run the synthetic fixtures."""
    reference_bytes, reference_digest = read_pinned_bytes(
        reference_path, "reference", EXPECTED_REFERENCE_SHA256
    )
    module = load_validated_reference(reference_bytes, os.path.abspath(reference_path))
    result = invoke_reference(module)

    observed = [case.get("case") for case in result.get("cases", [])]
    missing = [name for name in REQUIRED_SYNTHETIC_CASES if name not in observed]
    if missing:
        raise Refusal(
            "REFERENCE_CASE_MISSING",
            f"expected synthetic positive-branch cases missing: {missing}",
        )

    return {
        "schema": ADAPTER_SCHEMA,
        "status": "SYNTHETIC_REFERENCE_PASSED",
        "mode": "synthetic-p3",
        "synthetic_only": True,
        "empirical_acceptance": False,
        "empirical_status": "BLOCKED_EMPIRICAL_RECEIPTS_UNAVAILABLE",
        "source_hashes": {
            "spec": build_spec_hash_block(spec_digest),
            "reference": {
                "sha256": reference_digest,
                "expected_sha256": EXPECTED_REFERENCE_SHA256,
                "hash_match": reference_digest == EXPECTED_REFERENCE_SHA256,
                "executed": True,
            },
        },
        "reference_schema": result.get("schema"),
        "reference_evidence_class": result.get("evidence_class"),
        "reference_case_count": result.get("case_count"),
        "reference_passed": result.get("passed"),
        "reference_source_sha256": result.get("source_sha256"),
        "reference_result_sha256": sha256_hex(canonical_bytes(result)),
        "reference_solver_policy": result.get("solver_policy"),
        "reference_empirical_fit_performed": result.get("empirical_fit_performed"),
        "reference_availability_attested": result.get("availability_attested"),
        "reference_production_compatible_schema": result.get("production_compatible_schema"),
        "required_synthetic_cases": list(REQUIRED_SYNTHETIC_CASES),
        "reference_cases": result.get("cases", []),
        "source_certified_accepted": False,
        "rank_authority": False,
        "activation_authority": False,
        "trading_authority": False,
        "mission_complete": False,
        "b1_ri_role": B1_RI_ROLE,
        "b1_ri_note": B1_RI_NOTE,
        "note": (
            "Synthetic reference arithmetic only. All empirical gates G0-G6 remain "
            "held; this is not empirical acceptance."
        ),
    }


def run_empirical() -> None:
    """Refuse every empirical request before any dataset read or fitting."""
    raise Refusal(
        "EMPIRICAL_GATES_UNSATISFIED",
        "All empirical gates G0-G6 remain held and empirical receipts are "
        "unavailable. No dataset was read and no fitting was performed. Synthetic "
        "spec metadata cannot authorize a real trial.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="options_pilot_study_adapter.py",
        description=(
            "Finite study-spec binding/refusal adapter. Parses and hash-binds the "
            "frozen spec, runs the hash-pinned synthetic P3 reference, or refuses "
            "empirical requests. Never fetches inputs or loads unvalidated code."
        ),
    )
    parser.add_argument("--spec", metavar="PATH", help="frozen pilot study specification path")
    parser.add_argument(
        "--mode",
        choices=("inspect", "synthetic-p3", "empirical"),
        default="inspect",
        help="adapter operation",
    )
    parser.add_argument(
        "--reference",
        metavar="PATH",
        help="hash-pinned synthetic P3 reference script (required for synthetic-p3)",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = args.mode
    try:
        if not args.spec:
            raise Refusal("MISSING_SPEC_ARGUMENT", "--spec PATH is required")
        spec, spec_digest = load_spec(args.spec)

        if mode == "inspect":
            reference_digest = None
            if args.reference:
                _, reference_digest = read_pinned_bytes(
                    args.reference, "reference", EXPECTED_REFERENCE_SHA256
                )
            emit(build_inspect_report(spec, spec_digest, reference_digest))
            return 0

        if mode == "synthetic-p3":
            if not args.reference:
                raise Refusal(
                    "MISSING_REFERENCE_ARGUMENT", "--reference PATH is required for synthetic-p3"
                )
            emit(run_synthetic_p3(spec_digest, args.reference))
            return 0

        run_empirical()
        return 0
    except Refusal as refusal:
        emit(
            {
                "schema": ADAPTER_SCHEMA,
                "status": "REFUSED",
                "mode": mode,
                "code": refusal.code,
                "detail": refusal.detail,
            }
        )
        return REFUSAL_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
