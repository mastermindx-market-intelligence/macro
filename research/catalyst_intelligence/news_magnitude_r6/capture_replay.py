"""Recapture the unchanged synthetic R5 requests with the R6 news owner.

Run only from the documented composed research checkout. Writes this research
lane's fixtures; never native data, publisher inputs, or the older R5 captures.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "fixtures"
OLD = ROOT / "research/catalyst_intelligence/company_assessment_v2_r5/fixtures"
EXPECTED = {
    "engine/catalyst_intelligence/assessment_v2.py": "3c321c686f19e1a089c27d163f5280955215793f5fb33fdd4a99a971ef17590b",
    "engine/catalyst_intelligence/__main__.py": "7f878761813b5742a072feb011f66b770a2d9c366bf0d35839ff19dea6749d9f",
    "engine/prophet_entry_availability.py": "a753eb41771bddd8f9832a355c87999485a4042a1dea849ccaca39b35ed97b9f",
    "engine/news_impact/thesis.py": "ae862a16afb7e8cc51debabc3c81615f16218b0f66351264c71d2696e64096bd",
    "engine/news_impact/producer_facts.py": "712796386c750a949ea5e0d1d30ed8e26a27048164a5393b52cb2ed2e6273b17",
}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, obj):
    raw = (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    path.write_bytes(raw)
    return digest(raw)

def main():
    for relative, expected in EXPECTED.items():
        assert digest((ROOT / relative).read_bytes()) == expected, relative
    old_receipt = json.loads((OLD / "capture-receipt.json").read_bytes())
    OUT.mkdir(exist_ok=True)
    cases = {}
    captures = []
    for prior in old_receipt["captures"]:
        name = prior["name"]
        request = (OLD / (name + ".request.json")).read_bytes()
        assert digest(request) == prior["request_sha256"]
        old_result = json.loads((OLD / (name + ".assessment.json")).read_bytes())
        run = subprocess.run(
            [sys.executable, "-m", "engine.catalyst_intelligence"],
            input=request, cwd=ROOT, capture_output=True, check=True,
        )
        result = json.loads(run.stdout)
        assert result["input_digest"] == old_result["input_digest"]
        assert result["entry_context"] == old_result["entry_context"]
        assert result["peer_context"] == old_result["peer_context"]
        assert not any(result["authority"].values())
        views = result["news_context"]["current"]["views"]
        for view in views or []:
            correction = next(w for w in view["weakening_conditions"]
                              if w["code"] == "source_correction_reduces_magnitude")
            assert correction["armed"] is False and correction["evidence_fact_ids"] == []
            assert "28 September" not in json.dumps(view["display"])
            assert "source correction" in view["display"]["plain_status"].lower()
        (OUT / (name + ".request.json")).write_bytes(request)
        assessment_sha = save(OUT / (name + ".assessment.json"), result)
        captures.append({
            "name": name, "request_sha256": digest(request),
            "assessment_sha256": assessment_sha,
            "assessment_id": result["assessment_id"], "cli_exit_code": run.returncode,
            "prior_r5_assessment_id": old_result["assessment_id"],
        })
        cases[name] = result
    base = cases["source_revision"]
    assert cases["peers_missing"]["news_context"] == base["news_context"]
    assert cases["history_missing"]["news_context"]["current"] == base["news_context"]["current"]
    assert cases["history_missing"]["news_context"]["comparison"]["state"] == "UNAVAILABLE"
    assert cases["current_unavailable"]["news_context"]["current"]["views"] is None
    triggers = base["news_context"]["comparison"]["pairs"][0]["material_delta_triggers"]
    assert triggers == ["changed_numeric_terms", "new_independent_source", "source_correction"]
    receipt = {
        "schema": "catalyst.r6_replay_capture.v1",
        "synthetic": True, "native_admission_established": False,
        "scope": "COMPOSED_RESEARCH_CHECKOUT_NOT_PUBLISHED_RUNTIME",
        "consumer_head": "a073abedc58d945b10eb27380d49b879754c5bcc",
        "entry_head": "d4d43810c18f8e48b8cf49fa447392f7901f6b97",
        "news_base_head": "28f35fd86233cae3a42078966538cd8248c3f738",
        "source_sha256": EXPECTED,
        "prior_capture_receipt_sha256": digest((OLD / "capture-receipt.json").read_bytes()),
        "request_bytes_changed": False,
        "adaptations": old_receipt["adaptations"],
        "observed_repair": "Legacy correction remains observed; fingerprint does not establish reduction. Date-specific copy removed.",
        "positive_quantity_path": "Proven separately by producer-adapter and explicit fact-log tests, not these scalar-only legacy examples.",
        "captures": captures, "real_path_assertions": "PASS",
    }
    save(OUT / "capture-receipt.json", receipt)
    save(OUT / "replay_data.json", {"cases": cases, "receipt": receipt})
    print(json.dumps({"result": "APPLIED", "captures": captures, "real_path_assertions": "PASS"}))

if __name__ == "__main__":
    main()
