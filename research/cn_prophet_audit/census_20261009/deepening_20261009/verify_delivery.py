"""Verify the saved research package without executing any experiment or production code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFIX = "research/cn_prophet_audit/census_20261009/deepening_20261009/"
DISCOVERY = "agentos/discoveries/DSC-CN-PROPHET-CONTRACT-EXPERIMENTS-20261010.md"
ORIGINAL_MANIFEST = "research/cn_prophet_audit/census_20261009/DELIVERY_MANIFEST.json"
ORIGINAL_SHA = "b954977d51173faa801cc5e34180e317dd0390d2194a507d2ac3c7fda3deeb02"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_entry(root: Path, entry: dict) -> None:
    path = root / entry["path"]
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"], f"SHA256 mismatch: {path}"
    if "bytes" in entry:
        assert len(raw) == entry["bytes"], f"Size mismatch: {path}"
    expected_git = entry.get("git_blob", entry.get("git_blob_sha"))
    if expected_git:
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert actual == expected_git, f"Git blob mismatch: {path}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=HERE.parents[3],
                        help="Repository/deliverable root retaining the original relative layout")
    args = parser.parse_args()
    root = args.root.resolve()
    study = root / PREFIX
    manifest = json.loads((study / "FINAL_MANIFEST.json").read_text())
    expected_paths = set()
    for entry in manifest["files"]:
        path = entry["path"]
        assert path.startswith(PREFIX) or path == DISCOVERY, f"Unexpected effect scope: {path}"
        assert path not in expected_paths, f"Duplicate manifest path: {path}"
        expected_paths.add(path)
        verify_entry(root, entry)
    excluded = set(manifest["excluded_from_self_manifest"])
    actual_paths = {
        str(path.relative_to(root)) for path in study.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    actual_paths.add(DISCOVERY)
    assert actual_paths - excluded == expected_paths, {
        "unexpected": sorted(actual_paths - excluded - expected_paths),
        "missing": sorted(expected_paths - actual_paths),
    }
    original = root / ORIGINAL_MANIFEST
    assert digest(original) == ORIGINAL_SHA, "Original first-pass manifest changed"
    original_doc = json.loads(original.read_text())
    for entry in original_doc["files"]:
        verify_entry(root, entry)
    registry = json.loads((study / "ACCEPTANCE_REGISTRY.json").read_text())
    package_payloads = 0
    for package in registry["packages"]:
        path = study / package["path"]
        assert digest(path) == package["sha256"], package["scope"]
        doc = json.loads(path.read_text())
        entries = doc.get("files", doc.get("artifacts"))
        assert entries is not None, package["scope"]
        if isinstance(entries, dict):
            entries = [dict(value, path=key) if isinstance(value, dict)
                       else {"path": key, "sha256": value} for key, value in entries.items()]
        for entry in entries:
            verify_entry(path.parent, entry)
        package_payloads += len(entries)
    print(json.dumps({"status": "PASS", "final_payload_files": len(expected_paths),
                      "final_payload_bytes": sum(x["bytes"] for x in manifest["files"]),
                      "original_files_unchanged": len(original_doc["files"]) + 1,
                      "accepted_package_manifests": len(registry["packages"]),
                      "package_payload_checks_including_repeats": package_payloads,
                      "scope": "File identities only; no experiment, collector, vendor, runtime or deployment execution."}, indent=2))


if __name__ == "__main__":
    main()
