#!/usr/bin/env python3
"""Read-only package identity and research-result verification."""
import hashlib
import json
from pathlib import Path

p = Path(__file__).resolve().parent
m = json.loads((p / "MANIFEST.json").read_bytes())
for row in m["files"]:
    b = (p / row["path"]).read_bytes()
    assert len(b) == row["bytes"], row["path"]
    assert hashlib.sha256(b).hexdigest() == row["sha256"], row["path"]
    assert hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest() == row["git_blob_sha1"], row["path"]
r = json.loads((p / "results.json").read_bytes())
assert r["all_passed"] and r["check_count"] == 77
assert all(x["passed"] for x in r["checks"])
assert r["input_sha256"] == hashlib.sha256((p / "TRADABILITY_INPUT.json").read_bytes()).hexdigest()
assert r["script_sha256"] == hashlib.sha256((p / "run_tradability_lab.py").read_bytes()).hexdigest()
assert (p / "weight_replay/weight_results.json").read_bytes() == (p / "weight_reviewed_source/weight_results.json").read_bytes()
print(json.dumps({"status": "verified", "payload_files": len(m["files"]), "payload_bytes": m["total_payload_bytes"],
                  "checks": r["check_count"], "all_passed": True,
                  "manifest_sha256": hashlib.sha256((p / "MANIFEST.json").read_bytes()).hexdigest()}))
