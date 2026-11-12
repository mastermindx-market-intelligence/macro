"""Qualify the H3 source contribution in disposable exact-preimage fixtures.

No fetch, install, credential, provider, runtime selection or source-tree mutation.
The native source checkout is read only; all patching and tests use temporary copies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


NATIVE = Path("ops/native_fabric/quota_continuity")
TEST = NATIVE / "tests/test_expiry_account_admission.py"
PREFIX = "ops/native_fabric/quota_continuity/"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def safe_relative(value):
    path = Path(value)
    if not isinstance(value, str) or not value.startswith(PREFIX) or path.is_absolute() or ".." in path.parts:
        raise ValueError("unexpected contribution path")
    return path


def write(root, path, raw):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--contribution", type=Path,
        default=Path(__file__).resolve().parents[1] / "research/h3_expiration_account_admission")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    source = args.native_root.resolve(strict=True)
    contribution = args.contribution.resolve(strict=True)
    raw_manifest = (contribution / "manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest["schema"] != "mastermind.h3_native_contribution.v1":
        raise ValueError("unsupported contribution manifest")
    patch_path = contribution / "native.patch"
    if sha256(patch_path.read_bytes()) != manifest["patch_sha256"]:
        raise ValueError("patch digest changed")
    files = {}
    for record in manifest["inputs"]:
        path = safe_relative(record["path"])
        original = source / path
        if original.resolve(strict=True) != original or not original.is_file():
            raise ValueError("source input is not an ordinary canonical file: " + str(path))
        raw = original.read_bytes()
        if (git_blob(raw) != record["git_blob"] or sha256(raw) != record["sha256"]
                or len(raw) != record["bytes"]):
            raise ValueError("native preimage changed: " + str(path))
        files[path] = raw
    results = []
    with tempfile.TemporaryDirectory(prefix="h3-expiry-proof-") as directory:
        root = Path(directory)
        baseline, composed = root / "baseline", root / "composed"
        for path, raw in files.items():
            write(baseline, path, raw)
            write(composed, path, raw)
        for command in (["git", "apply", "--check", str(patch_path)],
                        ["git", "apply", str(patch_path)]):
            subprocess.run(command, cwd=composed, check=True, capture_output=True)
        for record in manifest["outputs"]:
            path = safe_relative(record["path"])
            raw = (composed / path).read_bytes()
            if sha256(raw) != record["sha256"] or git_blob(raw) != record["git_blob"]:
                raise ValueError("contribution postimage changed: " + str(path))
        write(baseline, TEST, (composed / TEST).read_bytes())
        environment = dict(os.environ)
        environment.pop("H3_NATIVE_SOURCE", None)
        environment.pop("PYTHONPATH", None)
        commands = [
            ("baseline_discriminator", baseline, [sys.executable, str(TEST),
             "ExpiryAdmissionTests.test_actual_claim_chooses_near_and_retains_complete_evidence"]),
            ("composed_regression", composed, [sys.executable, "-m", "unittest", "discover",
             "-s", str(NATIVE / "tests")]),
        ]
        for name, cwd, command in commands:
            result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
                                    text=True, timeout=120)
            output = result.stdout + result.stderr
            match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", output)
            if name == "baseline_discriminator":
                valid = (result.returncode == 1 and match and int(match[1]) == 1
                         and "AssertionError: 'alpha-far' != 'zeta-near'" in output
                         and "FAILED (failures=1)" in output)
            else:
                valid = (result.returncode == 0 and match and int(match[1]) == 91
                         and output.rstrip().endswith("OK"))
            record = {"name": name, "command": command, "exit_code": result.returncode,
                      "tests": int(match[1]) if match else None,
                      "duration_seconds": float(match[2]) if match else None,
                      "expected_result_observed": bool(valid), "output": output}
            results.append(record)
            if not valid:
                raise RuntimeError(name + " failed qualification:\n" + output)
    receipt = {"schema": "mastermind.h3_source_qualification.v1",
        "completed_at": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
        "native_preimage_commit": manifest["native_preimage_commit"],
        "manifest_sha256": sha256(raw_manifest), "patch_sha256": manifest["patch_sha256"],
        "exact_inputs_verified": len(files), "results": results,
        "qualification": "SOURCE_FIXTURE_ONLY", "installed": False, "live_provider_proven": False,
        "external_boundary": "Original native _offline_boundary; no unexpected effect observed"}
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(encoded)
    print(encoded)


if __name__ == "__main__":
    main()
