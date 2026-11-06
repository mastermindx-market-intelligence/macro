"""Validate only this scratch research packet. No fetching, census or source acquisition."""
from pathlib import Path
import hashlib, json, re, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(b):
    return hashlib.sha256(b).hexdigest()
def read(name):
    return json.loads((HERE / name).read_text())
def check(condition, message):
    if not condition:
        raise ValueError(message)

reg = read("PRIMARY_SOURCE_REGISTER.json")
bindings = read("INPUT_BINDINGS.json")
matrix = read("FEASIBILITY_MATRIX.json")
boundary = read("ACQUISITION_BOUNDARY.json")
ids = {s["source_id"] for s in reg["sources"]}
check(len(ids) == len(reg["sources"]) == reg["source_count"] == 35, "source IDs/count mismatch")
for s in reg["sources"]:
    check(s["canonical_url"].startswith("https://"), "noncanonical source URL")
    check(s["raw_response_sha256"] is None and not s["raw_response_bytes_retained"], "raw-response hash misrepresentation")
    excerpt = s["exact_retained_web_excerpt"]
    expected = sha(excerpt.encode("utf-8")) if excerpt is not None else None
    check(s["retained_excerpt_utf8_sha256"] == expected, "excerpt digest mismatch")
    check(not s["security_or_price_dataset_acquired"], "dataset acquisition inconsistent")
    check(not s["customer_entitlement_established"], "entitlement falsely established")
    check(s["public_availability_upper_bound_at_K"] is None, "unsupported public clock")
for r in matrix["rows"]:
    check(set(r["source_ids"]) <= ids, "unknown matrix source")
    check(r["unresolved_population_count"] is None, "invented population count")
    check(not r["exact_D_eligible_frame_proved"] and not r["customer_entitlement_proved"], "unsupported matrix proof")
for inp in bindings["inputs"]:
    actual = sha((ROOT / inp["path"]).read_bytes())
    check(actual == inp["sha256"], "bound input changed: " + inp["path"])
check(boundary["permission_gate"]["unknown_fails_closed"], "rights must fail closed")
check(boundary["status"] == "PROPOSED_OWNER_TASK_ENVELOPE_NOT_AUTHORIZATION_OR_JOB", "boundary grants authority")
for doc in [reg, matrix, boundary]:
    check(doc["D"] == "2026-09-30" and doc["K"] == "2026-10-09T00:00:00Z", "cutoff mismatch")
text = (HERE / "HISTORICAL_FRAME_SOURCING_FEASIBILITY.md").read_text()
check(bindings["inputs"][2]["sha256"] in text, "policy binding absent")
check(not re.search(r"\bturn\d+(?:view|search)\d+\b", text), "chat-native citation in report")
result = {
    "schema": "research.package_validation.v1",
    "result": "PASS",
    "checks": [
        "35 unique canonical source bindings and valid matrix joins",
        "Exact saved excerpt digests verified; raw-response hashes null",
        "Original input SHA-256 bindings verified against readback",
        "D/K equal across packet; unsupported public clocks null",
        "No actual securities/price acquisition, entitlement, frame proof or population counts claimed",
        "Permission unknown fails closed; finite task envelope does not authorize a job",
        "No chat-native citations in standalone report"
    ],
    "limits": "Structural and readback checks do not establish provider capability, license entitlement, historical population completeness, or policy adoption."
}
(HERE / "ARTIFACT_VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))

