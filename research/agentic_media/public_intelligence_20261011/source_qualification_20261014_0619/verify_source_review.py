"""Verify this bounded source review; no imports of writers or runtime mutation."""
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
phase = root / "research/agentic_media/public_intelligence_20261011/source_qualification_20261014_0619"
base = phase.parent
review = json.loads((phase / "homebuilder_review.json").read_text())
source = review["private_original"]
private = Path(source["path"])
assert hashlib.sha256(private.read_bytes()).hexdigest() == source["sha256"]
assert private.stat().st_size == source["bytes"]
aliases = json.loads((phase / "catalog_alias_review.json").read_text())["groups"]
assert len(aliases) == 3
assert all(r["same_title"] and r["same_institution"] and r["same_catalog_day"] for r in aliases)
assert [r["same_summary_points"] for r in aliases] == [False, True, True]
previous = json.loads((base / "source_qualification_20261014_0531/source_exclusions.json").read_text())
current = json.loads((phase / "source_exclusions.json").read_text())
assert current["preserve_parent_held_refs"] and current["jpm_b50195_remains_hold"]
held = set(json.loads((base / "research_intake_phase/installed_discovery.json").read_text())["held_refs"])
held.update(previous["additional_blocked_refs"])
held.update(current["additional_blocked_refs"])
assert set(aliases[0]["refs"]) <= held
assert review["candidate"] in held
manifest = json.loads((base / "validator_integrity_phase/postlanding/mmx-current-expected-hashes.json").read_text())
assert len(manifest) == 24
assert all(hashlib.sha256((root / rel).read_bytes()).hexdigest() == sha for rel,sha in manifest.items())
assert review["provider_calls"] == review["staging_writes"] == review["producer_writes"] == 0
assert review["publication"] is False and review["cutover"] is False and review["d14_credit"] == "0/10"
print(json.dumps({"result":"PASS", "checks":["retained private source hash and size", "three catalog identity comparisons", "exact-summary equality distinguished from title identity", "cumulative held refs preserve original and alternate Europe Autos identity", "new homebuilder exclusion preserves earlier holds", "all24 reviewed runtime source hashes unchanged", "no generation or publication claimed"], "checks_passed":7, "application_tests_rerun":False, "publication":False},indent=2))
