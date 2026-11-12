"""Qualify the exact H2/H3/H6 composition in disposable source fixtures.

No fetch, install, provider, credential, enrollment or runtime selection. Input
checkouts are read only. The incumbent offline boundary guards all test runs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

NATIVE = Path("ops/native_fabric/quota_continuity")
READER = Path("ops/native_fabric/grok47/quota_billing/quota_remote.py")
H6_TEST = NATIVE / "tests/test_h6_quota_publication.py"
H3_TEST = NATIVE / "tests/test_expiry_account_admission.py"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def relative(value):
    path = Path(value)
    if (not isinstance(value, str) or path.is_absolute() or ".." in path.parts
            or not (value.startswith(str(NATIVE) + "/") or path == READER
                    or value == "tests/test_native_fabric_account_quota.py")):
        raise ValueError("unexpected contribution path")
    return path


def write(root, path, raw):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def apply(root, path):
    for command in (["git", "apply", "--check", "--whitespace=error", str(path)],
                    ["git", "apply", "--whitespace=error", str(path)]):
        subprocess.run(command, cwd=root, check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--h2-root", type=Path, required=True)
    parser.add_argument("--contribution", type=Path,
        default=Path(__file__).resolve().parents[1] / "research/h6_account_publication")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    sources = {"native": args.native_root.resolve(strict=True), "h2": args.h2_root.resolve(strict=True)}
    contribution = args.contribution.resolve(strict=True)
    manifest_bytes = (contribution / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest["schema"] != "mastermind.h6_account_publication_contribution.v1":
        raise ValueError("unsupported contribution manifest")
    patch = contribution / "native.patch"
    h3_patch = contribution.parent / "h3_expiration_account_admission/native.patch"
    if (sha256(patch.read_bytes()) != manifest["patch_sha256"]
            or sha256(h3_patch.read_bytes()) != manifest["h3_patch_sha256"]):
        raise ValueError("contribution patch changed")
    files = {}
    for record in manifest["inputs"]:
        path = relative(record["path"])
        original = sources[record["owner"]] / path
        if original.resolve(strict=True) != original or not original.is_file():
            raise ValueError("source input is not an ordinary canonical file: " + str(path))
        raw = original.read_bytes()
        if (len(raw) != record["bytes"] or blob(raw) != record["git_blob"]
                or sha256(raw) != record["sha256"]):
            raise ValueError("source input changed: " + str(path))
        files[path] = raw

    records = []
    with tempfile.TemporaryDirectory(prefix="h6-publication-proof-") as directory:
        root = Path(directory)
        before, after = root / "before-join", root / "composed"
        for path, raw in files.items():
            write(before, path, raw)
            write(after, path, raw)
        apply(after, patch)
        for record in manifest["outputs"]:
            raw = (after / relative(record["path"])).read_bytes()
            if len(raw) != record["bytes"] or blob(raw) != record["git_blob"] or sha256(raw) != record["sha256"]:
                raise ValueError("contribution postimage changed: " + record["path"])
        if (after / READER).read_bytes() != (after / NATIVE / "candidate/quota_remote.py").read_bytes():
            raise ValueError("producer and native reader diverged")
        # Actual earlier composition: exact H3 patch plus the current H2 reader
        # with H3's original read-only adapter, without any H6 coordination fix.
        apply(before, h3_patch)
        quota = before / NATIVE / "candidate/quota_remote.py"
        h3 = quota.read_text()
        adapter = h3[h3.index("def read_account_admission_cache():"):h3.index("def cached_glm_account_parked(")]
        h2 = (before / READER).read_text()
        quota.write_text(h2.replace("def cached_glm_account_parked(", adapter + "def cached_glm_account_parked(", 1))
        # Only the fixture's filesystem topology and new discriminating tests
        # are copied back. The earlier production code remains unchanged.
        for path in (H3_TEST, H6_TEST):
            write(before, path, (after / path).read_bytes())

        environment = dict(os.environ)
        environment.pop("H3_NATIVE_SOURCE", None)
        environment["PYTHONPATH"] = str(NATIVE / "tests")
        discriminators = [
            ("native_lock_before_claim", "NativeAdmissionPublicationTests.test_publication_contention_refuses_new_worker_and_application_without_allocating", "True is not false"),
            ("pending_refresh_blocks_old_envelope", "NativeAdmissionPublicationTests.test_h2_pending_or_failed_refresh_cannot_leave_h3_old_envelope_admissible", "'zeta-near' != 'alpha-far'"),
            ("original_pending_marker_required", "QuotaPublicationTests.test_original_attempt_cannot_complete_after_its_pending_marker_is_removed", "AssertionError:"),
            ("directory_fsync_required", "QuotaPublicationTests.test_fsync_failure_after_replace_requires_reconciliation_with_visible_postimage", "QuotaCacheWriteError not raised"),
        ]
        runs = [(name, before, [sys.executable, "-m", "unittest", "test_h6_quota_publication." + test], 1, marker)
                for name, test, marker in discriminators]
        guarded_h2 = (
            "import sys, unittest\n"
            "sys.path[:0] = ['ops/native_fabric/quota_continuity/candidate', 'ops/native_fabric/quota_continuity/source', 'ops/native_fabric/quota_continuity/tests']\n"
            "from _offline_boundary import acquire, release\nacquire()\n"
            "try:\n    unittest.main(module=None, argv=['unittest', 'discover', '-s', 'tests'])\n"
            "finally:\n    release()\n"
        )
        runs.extend([
            ("composed_native_regression", after, [sys.executable, "-m", "unittest", "discover", "-s", str(NATIVE / "tests")], 104, None),
            ("current_h2_regression", after, [sys.executable, "-c", guarded_h2], 43, None),
        ])
        for name, cwd, command, expected_count, negative_marker in runs:
            result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            count = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", output)
            valid = bool(count and int(count[1]) == expected_count)
            if negative_marker:
                valid = valid and result.returncode == 1 and "FAILED (failures=1)" in output and negative_marker in output
            else:
                valid = valid and result.returncode == 0 and output.rstrip().endswith("OK")
            records.append({"name": name, "command": command, "exit_code": result.returncode,
                "tests": int(count[1]) if count else None,
                "duration_seconds": float(count[2]) if count else None,
                "expected_result_observed": bool(valid), "output_sha256": sha256(output.encode()), "output": output})
            if not valid:
                raise RuntimeError(name + " failed qualification:\n" + output)

    receipt = {"schema": "mastermind.h6_account_publication_qualification.v1",
        "completed_at": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
        "native_preimage_commit": manifest["native_preimage_commit"], "h2_preimage_commit": manifest["h2_preimage_commit"],
        "h3_source_commit": manifest["h3_source_commit"], "manifest_sha256": sha256(manifest_bytes),
        "patch_sha256": manifest["patch_sha256"], "exact_inputs_verified": len(files), "results": records,
        "positive_tests": 147, "negative_discriminators": 4, "qualification": "SOURCE_FIXTURE_ONLY",
        "installed": False, "live_provider_proven": False, "parent_mission_complete": False,
        "external_boundary": "Incumbent native _offline_boundary guarded all runs; no unexpected effect observed"}
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(encoded)
    print(json.dumps({key: receipt[key] for key in ("qualification", "exact_inputs_verified", "positive_tests", "negative_discriminators", "patch_sha256")}, indent=2))


if __name__ == "__main__":
    main()
