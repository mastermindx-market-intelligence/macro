#!/usr/bin/env python3
"""Read-only verification of this review and its sealed input packages."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEALED = {
    "matched_controls/MANIFEST.json": "3d1330cdaf37342e7a185997640e97526c8decdb24c53d3f9650d450250725d5",
    "reviews/intelligence_contract_review/MANIFEST.json": "0105976d7a771f47cb824e311a2f9dc221ca14f9c0725cac4bc322ec35832939",
    "reviews/intelligence_contract_review/acceptance_83944fe1/MANIFEST.json": "5099588bb3a866eb2a311e9d34f29d1c459fb08df6d6d8578680998606c8bc51",
    "reviews/intelligence_contract_review/acceptance_f2f5aeeb/MANIFEST.json": "922d370c6dfa6fc98b79bfdca11c55f72dc7da90c47c570aab66631b5a346a36",
    "tradability_lab/MANIFEST.json": "2cb1b5f7cfae2332ada90e1ea1abe1c05c3f055853b751002b3ac7ddaa70dff5",
    "reviews/vintage_repair_acceptance/MANIFEST.json": "8fa6b5fdcc7cea12842d8513e07c05088df15f0f0c2c0b1bf014e98e9381256e",
    "intelligence_lab/MARGIN_HORIZON_MANIFEST.json": "d21ce925119d58094c3248a399374ddd43a4292332588eb92e06046ccb7e8ada",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(path, expected=None):
    raw = path.read_bytes()
    if expected is not None:
        assert digest(raw) == expected, str(path)
    manifest = json.loads(raw)
    entries = manifest["files"]
    if isinstance(entries, dict):
        entries = [{"path": key, **value} for key, value in entries.items()]
    total = 0
    for entry in entries:
        payload = (path.parent / entry["path"]).read_bytes()
        assert len(payload) == entry["bytes"], entry["path"]
        assert digest(payload) == entry["sha256"], entry["path"]
        blob = entry.get("git_blob_sha1", entry.get("git_blob"))
        if blob is not None:
            assert hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest() == blob, entry["path"]
        total += len(payload)
    return {"manifest": str(path.relative_to(ROOT)), "manifest_sha256": digest(raw), "payload_files": len(entries), "payload_bytes": total}


def main():
    prior = [verify(ROOT / rel, expected) for rel, expected in SEALED.items()]
    if "--prior-only" in sys.argv:
        print(json.dumps({"status": "SEALED_INPUTS_UNCHANGED", "packages": prior, "payload_files": sum(x["payload_files"] for x in prior)}, sort_keys=True))
        return
    own = verify(HERE / "MANIFEST.json")
    manifest = json.loads((HERE / "MANIFEST.json").read_bytes())
    paths = {x["path"] for x in manifest["files"]}
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob("*") if p.is_file() and p != HERE / "MANIFEST.json"}
    assert paths == actual, {"unexpected": sorted(actual - paths), "missing": sorted(paths - actual)}
    result = json.loads((HERE / "REVIEW_RESULTS.json").read_bytes())
    assert result["status"] == "ACCEPTED_BOUNDED_ADDENDUM"
    assert result["check_count"] == result["passed_n"] == 39 and result["failed_n"] == 0
    assert all(x["passed"] for x in result["checks"])
    assert result["review_script_sha256"] == digest((HERE / "review_margin_horizon.py").read_bytes())
    assert result["manifest_sha256"] == SEALED["intelligence_lab/MARGIN_HORIZON_MANIFEST.json"]
    assert result["original_scenarios_reproduced"] == 8
    print(json.dumps({"status": "VERIFIED", "review": own, "checks": 39, "passed": 39, "sealed_input_packages": len(prior), "sealed_input_payload_files": sum(x["payload_files"] for x in prior)}, sort_keys=True))


if __name__ == "__main__":
    main()
