#!/usr/bin/env python3
"""Run the complete local OI reference tests and bounded prohibited mutations.

No network, market inputs, source writes, fitted models or production actions.
Temporary mutant copies are test fixtures, not replacement source workspaces.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def run(folder: Path) -> dict:
    kernel = folder / "oi_identification.py"
    tests = folder / "test_oi_identification.py"
    code = kernel.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("oi_reference_tests", tests)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError(log.getvalue())
    mutations = [
        ("permit_mixed_trade_without_existing_interest", "1 if i0 == 0 and v > 0 else 0", "0", 1),
        ("ignore_nontrading_removals", "d = i1 - i0 + e", "d = i1 - i0", 1),
        ("missing_removals_become_zero", '_count(removals, "removals")', '_count(0 if removals is None else removals, "removals")', 2),
        ("participant_sides_use_matched_volume_denominator", "_fraction(v + d, 2 * v)", "_fraction(v + d, v)", 1),
        ("unknown_removal_interval_becomes_low_point", "candidates = {d_low, d_high, d_low + 1, d_high - 1, -1, 0, 1}", "candidates = {d_low}", 1),
        ("erase_subset_lower_bound", "[max(0, lo + a - v), min(a, hi)]", "[0, min(a, hi)]", 1),
        ("ignore_observed_subset_positions", "mark = int(index in selected)", "mark = 0", 1),
        ("invent_opening_probability", '"opening_probability": None', '"opening_probability": 0.5', 3),
    ]
    killed = []
    for name, before, after, expected_occurrences in mutations:
        if code.count(before) != expected_occurrences:
            raise AssertionError(f"MUTATION_TARGET_DRIFT:{name}")
        mutant = code.replace(before, after)
        ast.parse(mutant)
        with tempfile.TemporaryDirectory(prefix="oi-reference-mutation-") as temp:
            root = Path(temp)
            (root / kernel.name).write_text(mutant, encoding="utf-8")
            shutil.copyfile(tests, root / tests.name)
            probe = subprocess.run([sys.executable, str(root / tests.name)], capture_output=True, text=True, timeout=20)
            if probe.returncode == 0:
                raise AssertionError(f"MUTATION_SURVIVED:{name}")
            if "SyntaxError" in probe.stderr or "ModuleNotFoundError" in probe.stderr:
                raise AssertionError(f"INVALID_MUTATION_KILL:{name}")
            summary = next((line for line in reversed(probe.stderr.splitlines()) if line.startswith("FAILED (")), None)
            if summary is None:
                raise AssertionError(f"MUTATION_RESULT_UNCLASSIFIED:{name}")
            killed.append({"name": name, "killed": True, "test_result": summary})
    # These census sizes are derived from the fully completed loops in the test module.
    exact = sum((initial + volume + 1) * 5 for initial in range(4) for volume in range(11))
    intervals = sum((initial + volume + 1) * sum(5 - low for low in range(4)) for initial in range(3) for volume in range(7))
    ordered = sum((initial + volume + 1) * 3 * 2**volume for initial in range(3) for volume in range(6))
    return {
        "schema": "options.oi.identification.verification.v1",
        "synthetic_only": True,
        "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "exhaustive_geometries": {"exact_count_bounds": exact, "removal_interval_unions": intervals, "fixed_order_subsets": ordered},
        "total_exhaustive_geometries": exact + intervals + ordered,
        "mutation_results": killed,
        "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
        "test_sha256": hashlib.sha256(tests.read_bytes()).hexdigest(),
        "python": sys.version.split()[0],
        "source_certified": False, "predictive_authority": False,
        "verification_kind": "principal deterministic checks; separate Fabric derivation is adjudicated in its own retained receipt",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(Path(__file__).resolve().parent)
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
