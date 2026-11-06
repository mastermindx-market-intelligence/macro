#!/usr/bin/env python3
"""Read-only verification of the sealed independent acceptance package."""
import hashlib
import json
from pathlib import Path

p = Path(__file__).resolve().parent
m = json.loads((p/"MANIFEST.json").read_bytes())
for row in m["files"]:
    b = (p/row["path"]).read_bytes()
    assert len(b) == row["bytes"], row["path"]
    assert hashlib.sha256(b).hexdigest() == row["sha256"], row["path"]
    assert hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest() == row["git_blob_sha1"], row["path"]
r = json.loads((p/"ACCEPTANCE_RESULTS.json").read_bytes())
assert r["status"] == "ACCEPTED_BOUNDED_RESEARCH_CONTRACT"
assert r["check_count"] == r["passed_n"] == 86 and r["failed_n"] == 0
assert len(r["finding_closure"]) == 15 and all(v == "CLOSED" for v in r["finding_closure"].values())
assert r["review_script_sha256"] == hashlib.sha256((p/"accept_vintage.py").read_bytes()).hexdigest()
for n in ["results.json", "fixtures.json"]:
    assert (p/"producer_replay"/n).read_bytes() == (p/"reviewed_candidate"/n).read_bytes()
print(json.dumps({"status":"verified", "payload_files":len(m["files"]), "payload_bytes":m["total_payload_bytes"],
                  "independent_checks":86, "producer_checks":104, "closed_findings":15,
                  "manifest_sha256":hashlib.sha256((p/"MANIFEST.json").read_bytes()).hexdigest()}))
