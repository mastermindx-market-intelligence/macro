"""Capture synthetic v2 examples through the actual CLI and pinned owner repairs.

Run only in the documented composed research checkout. No network or native
source stores are read. Files are written only to this research lane's fixtures.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / "research/catalyst_intelligence/company_assessment_v2_r5"
SOURCE_PINS = {
    "engine/catalyst_intelligence/assessment_v2.py":
        "3c321c686f19e1a089c27d163f5280955215793f5fb33fdd4a99a971ef17590b",
    "engine/catalyst_intelligence/__main__.py":
        "7f878761813b5742a072feb011f66b770a2d9c366bf0d35839ff19dea6749d9f",
    "engine/prophet_entry_availability.py":
        "a753eb41771bddd8f9832a355c87999485a4042a1dea849ccaca39b35ed97b9f",
    "engine/news_impact/thesis.py":
        "29e2eb60232e978f2a1a0404d00f495405128de516c53ee5acc1cf5df165a641",
}
BASE_REQUEST_SHA256 = "bd515b37fae9605a85aaaf32328ce080e74494e58c5453364d834768f2ff1865"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return "sha256:" + sha256(canonical(value).encode()).hexdigest()


def revised_request(old):
    request = {
        "schema": "catalyst.stock_research_inputs.v2",
        "focal": deepcopy(old["peer_inputs"]["focal"]),
        "decision_at": old["peer_inputs"]["decision_at"],
        "peer_inputs": deepcopy(old["peer_inputs"]),
        "entry": deepcopy(old["entry"]),
        "news": {"fact_log": deepcopy(old["news"]["fact_log"]),
                 "current_owners": deepcopy(old["news"]["current_owners"]),
                 "comparison": {"since_at": "2026-09-28T14:10:00Z",
                                "prior_owners": deepcopy(old["news"]["prior_owners"])}},
    }
    prior = request["news"]["comparison"]["prior_owners"]
    prior["as_of"] = prior["known_at"] = request["news"]["comparison"]["since_at"]
    prior["payload"]["decision_cut"] = prior["as_of"]
    prior["payload_digest"] = digest(prior["payload"])
    records = request["news"]["fact_log"]["records"]
    correction = deepcopy(records[0])
    correction.update(
        log_seq=max(r["log_seq"] for r in records) + 1,
        fact_id="fact_" + "c" * 24, document_id="doc_synthetic_correction",
        observed_at="2026-09-28T18:00:00Z", source_available_at="2026-09-28T17:59:00Z",
        supersedes_fact_id=records[0]["fact_id"], novelty="corrected_fact",
    )
    correction["quantity_fingerprint"] = {"form": "present", "canonical_sha256": "c" * 64}
    correction["provenance"].update(
        origin_document_id=correction["document_id"], origin_claim_id="claim_synthetic_correction",
        root_family_id="root_synthetic_correction", source_family="regulator_filing",
    )
    correction["evidence"].update(document_id=correction["document_id"], span_id="span_" + "c" * 20)
    correction["owner_claim_ids"] = ["claim_synthetic_correction"]
    mirror = deepcopy(records[1])
    mirror.update(log_seq=correction["log_seq"] + 1, fact_id="fact_" + "e" * 24,
                  document_id="doc_synthetic_late_mirror", observed_at="2026-09-28T19:00:00Z",
                  source_available_at="2026-09-28T18:59:00Z")
    mirror["evidence"].update(document_id=mirror["document_id"], span_id="span_" + "e" * 20)
    records.extend([correction, mirror])
    return request


def main():
    for rel, expected in SOURCE_PINS.items():
        actual = sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"Research replay needs the documented exact source composition: {rel}")
    base_bytes = (ROOT / "research/catalyst_intelligence/stock_context_r1/fixtures/owner_request.json").read_bytes()
    assert sha256(base_bytes).hexdigest() == BASE_REQUEST_SHA256
    base = json.loads(base_bytes)
    complete = revised_request(base)
    requests = {"source_revision": complete}
    requests["peers_missing"] = deepcopy(complete)
    requests["peers_missing"]["peer_inputs"] = None
    requests["history_missing"] = deepcopy(complete)
    requests["history_missing"]["news"]["comparison"]["prior_owners"] = None
    requests["current_unavailable"] = deepcopy(complete)
    requests["current_unavailable"]["news"]["current_owners"] = None
    dest = LANE / "fixtures"
    dest.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "catalyst.v2_replay_capture.v1", "synthetic": True,
        "native_admission_established": False, "source_sha256": SOURCE_PINS,
        "base_request_sha256": BASE_REQUEST_SHA256,
        "owner_prs": {"entry": 9731, "news": 9732},
        "scope": "COMPOSED_RESEARCH_CHECKOUT_NOT_PUBLISHED_RUNTIME",
        "adaptations": [
            "Existing synthetic R1 identity/price/entry fixture retained.",
            "Prior owner snapshot moved to an explicit synthetic 14:10 cutoff.",
            "Invented numeric fingerprint correction at 18:00 and known-source mirror at 19:00.",
            "No economic amount or direction inferred from the fingerprint.",
        ],
        "captures": [],
    }
    outputs = {}
    for name, request in requests.items():
        request_bytes = (canonical(request) + "\n").encode()
        run = subprocess.run([sys.executable, "-m", "engine.catalyst_intelligence"], cwd=ROOT,
                             input=request_bytes, capture_output=True, timeout=30, check=True)
        output = json.loads(run.stdout)
        assert output["source_admission_established"] is False
        assert not any(output["authority"].values())
        outputs[name] = output
        (dest / (name + ".request.json")).write_bytes(request_bytes)
        (dest / (name + ".assessment.json")).write_bytes(run.stdout)
        receipt["captures"].append({
            "name": name, "request_sha256": sha256(request_bytes).hexdigest(),
            "assessment_sha256": sha256(run.stdout).hexdigest(),
            "assessment_id": output["assessment_id"], "cli_exit_code": run.returncode,
        })
    expected = {"changed_numeric_terms", "new_independent_source", "source_correction"}
    pairs = outputs["source_revision"]["news_context"]["comparison"]["pairs"]
    assert any(expected <= set(p["material_delta_triggers"] or []) for p in pairs)
    assert outputs["history_missing"]["news_context"]["current"] == outputs["source_revision"]["news_context"]["current"]
    assert outputs["peers_missing"]["news_context"] == outputs["source_revision"]["news_context"]
    assert outputs["current_unavailable"]["news_context"]["current"]["views"] is None
    receipt["real_path_assertions"] = "PASS"
    (dest / "capture-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
