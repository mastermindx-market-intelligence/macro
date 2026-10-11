#!/usr/bin/env python3
"""Read-only custody check for the bounded handoff review; no suite execution."""
from pathlib import Path
from hashlib import sha256
import argparse
import json

HERE = Path(__file__).resolve().parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-sha", required=True)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[5],
                        help="Delivered tree root containing research/ and agentos/.")
    args = parser.parse_args()
    manifest = HERE / "MANIFEST.json"
    assert digest(manifest) == args.manifest_sha, "Review manifest identity changed"
    data = json.loads(manifest.read_text())
    for entry in data["files"]:
        path = HERE / entry["path"]
        assert path.stat().st_size == entry["bytes"], entry["path"]
        assert digest(path) == entry["sha256"], entry["path"]
    checked = 0
    for name in ("FINAL_DOCUMENT_INPUTS.json", "ACCEPTED_EVIDENCE_INPUTS.json"):
        inputs = json.loads((HERE / name).read_text())
        for entry in inputs["files"]:
            assert digest(HERE / entry["snapshot_path"]) == entry["sha256"], entry["snapshot_path"]
            original = args.source_root / entry["source_path"]
            assert original.stat().st_size == entry["bytes"], entry["source_path"]
            assert digest(original) == entry["sha256"], entry["source_path"]
            checked += 1
    print(json.dumps({"status": "PASS", "scope": "Read-only file custody; no experiments rerun",
                      "review_manifest_sha256": digest(manifest),
                      "review_payload_files": len(data["files"]),
                      "external_document_and_evidence_files": checked}))


if __name__ == "__main__":
    main()
