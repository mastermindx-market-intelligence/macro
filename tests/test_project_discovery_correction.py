"""Actual canonical correction compiler/parser; synthetic records, no publication."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agentos
import project_knowledge_recipes as recipes

WORK = "WS:ALPHA"
OLD = "DSC:ORIGINAL-FINDING"
COMMIT = "b" * 40
ACTOR = "workspace:" + "a" * 64
STAMP = "d" * 64


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record(data, body="\nOriginal note. 中文 stays literal.\n"):
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True) + "---\n" + body


def workstream(key="ALPHA", discoveries=None):
    return record({"schema": "agentos.workstream.v1", "key": key, "title": "Correct a finding",
        "objective": "Preserve evidence while learning", "status": "active", "program": "mmos-core",
        "repos": ["macro"], "owner": "chairman", "class": "build", "blast_radius": "reversible",
        "ambiguity": "specified", "waves": [{"id": "wave-1", "title": "Evidence", "status": "in_progress"}],
        "next_action": "Read the evidence", "discoveries": discoveries or [], "decisions": [], "artifacts": []})


def discovery(key="ORIGINAL-FINDING"):
    return record({"schema": "agentos.discovery.v1", "key": key, "claim": "The old measured claim.",
        "falsifier": "pytest tests/check_finding.py changes the measured result", "so_what": "Choose the measured path.",
        "kind": "runtime", "verified_at": "2026-10-01", "verified_by": "pytest tests/check_finding.py",
        "scope": [WORK], "confidence": "probable"})


def request(ws, old, *, old_ref=OLD, request_stamp="1"):
    return {"schema": recipes.SCHEMA_DISCOVERY_CORRECT_REQUEST,
        "request_id": "mmos-project-discovery-correct-" + request_stamp * 40,
        "work_ref": WORK, "source_commit": COMMIT, "base_revision": sha(ws),
        "discovery_ref": old_ref, "expected_discovery_revision": sha(old),
        "correction_reason": "A new recorded observation contradicts the previous result.",
        "replacement": {"claim": "The newer measured claim.", "falsifier": "pytest tests/new_finding.py disproves it",
            "so_what": "Use the corrected measured path.", "kind": "runtime", "confidence": "probable",
            "verified_at": "2026-11-05", "verified_by": "pytest tests/new_finding.py",
            "expires": None, "body_utf8": "\nCorrection evidence and limitations. 中文\n",
            "evidence": ["tests/new_finding.py:12"]}}


def new_ref(req):
    identity = {"principal_scope": ACTOR[len("workspace:"):], "request_id": req["request_id"], "work_ref": WORK}
    return "DSC:PROJECT-CORRECTION-" + sha(recipes.canonical(identity))[:40].upper()


def records_for(ws, old):
    rec = agentos.parse_project_discovery_reference_text(old)
    return {"WS/ALPHA": agentos.parse_project_discovery_reference_text(ws), "DSC/" + rec["key"]: rec}


def closure(req, records):
    lineage = agentos.qualify_project_discovery_correction(records, work_ref=WORK,
        discovery_ref=req["discovery_ref"], replacement_ref=new_ref(req))
    return {"schema": "agentos.project_discovery_reference_closure.v1", "source_commit": COMMIT,
        "parser_content_sha256": sha((ROOT / "scripts/agentos.py").read_text()),
        "work_ref": WORK, "discovery_ref": req["discovery_ref"], "replacement_ref": new_ref(req),
        "coverage": "COMPLETE", "member_counts": {prefix: sum(key.startswith(prefix + "/") for key in records)
            for prefix in ("WS", "DEC", "DSC", "HND")},
        "record_manifest_sha256": "c" * 64, "lineage": lineage, "referring_work_refs": [WORK],
        "replacement_absent": True}


def build(req, ws, old, records=None, captured=None):
    return recipes.build_project_discovery_correct(req, actor_ref=ACTOR,
        permission_binding_digest=STAMP, captured_commit=COMMIT, workstream_text=ws,
        discovery_text=old, decision_date="2026-11-07",
        reference_closure=captured or closure(req, records or records_for(ws, old)))


def apply(images, records):
    result = copy.deepcopy(records)
    for image in images:
        rec = agentos.parse_project_discovery_reference_text(image["content_utf8"])
        result[("WS/" if image["path"].startswith("agentos/workstreams/") else "DSC/") + rec["key"]] = rec
    return result


def test_actual_three_images_preserve_original_bytes_evidence_dates_and_workstream_body():
    ws, old = workstream(), discovery()
    req = request(ws, old); result = build(req, ws, old)
    assert result["state"] == "DRAFT_ONLY" and result["action"] == "project_discovery_correct"
    assert len(result["postimages"]) == 3
    old_post, new_post, ws_post = result["postimages"]
    assert old_post["content_utf8"].replace("\nsuperseded_by: " + new_ref(req), "", 1) == old
    assert old_post["expected_preimage_sha256"] == sha(old)
    assert new_post["expected_preimage_sha256"] is None
    for image in result["postimages"]:
        assert image["content_sha256"] == sha(image["content_utf8"])
    new = agentos.parse_project_discovery_reference_text(new_post["content_utf8"])
    assert new["verified_at"] == "2026-11-05" and new["confidence"] == "probable"
    assert new["project_correction"]["corrected_on"] == "2026-11-07"
    assert new["project_correction"]["request_sha256"] == sha(recipes.canonical(req))
    assert new["project_correction"]["evidence"] == req["replacement"]["evidence"]
    for image in (old_post, new_post):
        parsed = agentos.parse_project_discovery_reference_text(image["content_utf8"])
        assert not [p for p in agentos.check_discovery(parsed, Path(image["path"])) if p.hard]
    assert recipes._load_record(ws_post["content_utf8"], "INVALID_WORKSTREAM_RECORD")[1] == recipes._load_record(ws, "INVALID_WORKSTREAM_RECORD")[1]
    current = apply(result["postimages"], records_for(ws, old))
    assert current["WS/ALPHA"]["discoveries"] == [OLD, new_ref(req)]
    assert agentos.qualify_project_discovery_correction(current, work_ref=WORK,
        discovery_ref=new_ref(req), replacement_ref=None) == [OLD, new_ref(req)]


def test_a_corrected_finding_can_be_corrected_again_without_deleting_its_history():
    ws, old = workstream(), discovery(); first_req = request(ws, old)
    first = build(first_req, ws, old); current = apply(first["postimages"], records_for(ws, old))
    ws2, old2 = first["postimages"][2]["content_utf8"], first["postimages"][1]["content_utf8"]
    second_req = request(ws2, old2, old_ref=new_ref(first_req), request_stamp="2")
    second = build(second_req, ws2, old2, current)
    current = apply(second["postimages"], current)
    assert agentos.qualify_project_discovery_correction(current, work_ref=WORK,
        discovery_ref=new_ref(second_req), replacement_ref=None) == [OLD, new_ref(first_req), new_ref(second_req)]
    assert set(current["WS/ALPHA"]["discoveries"]) == {OLD, new_ref(first_req), new_ref(second_req)}


@pytest.mark.parametrize("kind", ["ws", "program", "artifact", "artifact_dot", "artifact_space", "artifact_prefix_space", "artifact_absolute", "artifact_root_escape", "artifact_other_repo_escape", "handoff", "decision", "decision_reader", "new_reference", "dangling_lineage", "fan_in", "wide_scope"])
def test_complete_reference_qualification_refuses_foreign_or_ambiguous_effects(kind):
    ws, old = workstream(), discovery(); req = request(ws, old); records = records_for(ws, old)
    other = agentos.parse_project_discovery_reference_text(workstream("OTHER"))
    records["WS/OTHER"] = other
    if kind == "ws": other["discoveries"] = [OLD]
    elif kind == "program": other["program"] = WORK
    elif kind.startswith("artifact"):
        other["artifacts"] = [("./" if kind == "artifact_dot" else "") + "agentos/discoveries/DSC-ORIGINAL-FINDING.md"]
        if kind.endswith("space"):
            other["artifacts"] = ["  " + ("macro:" if kind == "artifact_prefix_space" else "") + other["artifacts"][0] + "  "]
        if kind == "artifact_absolute": other["artifacts"] = ["/workspace/macro/" + other["artifacts"][0]]
        if kind == "artifact_root_escape": other["artifacts"] = ["../macro/" + other["artifacts"][0]]
        if kind == "artifact_other_repo_escape": other["artifacts"] = ["mastermind:../macro/" + other["artifacts"][0]]
    elif kind == "handoff": records["HND/foreign"] = {"workstream": "WS:OTHER", "discoveries": [OLD]}
    elif kind.startswith("decision"):
        records["DEC/CITING"] = {"affects": [WORK] if kind == "decision_reader" else ["WS:OTHER"], "discoveries": [OLD]}
        if kind == "decision_reader": other["decisions"] = ["DEC:CITING"]
    elif kind == "new_reference": other["discoveries"] = [new_ref(req)]
    elif kind == "dangling_lineage": records["DSC/UNRELATED"] = {"superseded_by": new_ref(req), "scope": [WORK]}
    elif kind == "fan_in": records["DSC/UNRELATED"] = {"superseded_by": OLD, "scope": [WORK]}
    else: records["DSC/ORIGINAL-FINDING"]["scope"].append("WS:OTHER")
    with pytest.raises(agentos.ProjectDiscoveryCorrectionScopeError): closure(req, records)


@pytest.mark.parametrize("where", ["old", "new"])
def test_concurrent_foreign_reference_is_rejected_in_candidate_merged_tree(where):
    ws, old = workstream(), discovery(); req = request(ws, old); result = build(req, ws, old)
    current = apply(result["postimages"], records_for(ws, old))
    current["WS/OTHER"] = agentos.parse_project_discovery_reference_text(workstream("OTHER", [OLD if where == "old" else new_ref(req)]))
    paths = {key: Path("agentos/" + ("workstreams/WS-" if key.startswith("WS/") else "discoveries/DSC-") + key.split("/", 1)[1] + ".md") for key in current}
    problems = agentos.check_references(current, paths)
    assert any(problem.hard and problem.rule == "project-correction-scope" and problem.path == paths["WS/OTHER"] for problem in problems)


@pytest.mark.parametrize("mutation", ["ws_cas", "old_cas", "extra", "aggregate", "confidence", "confidence_type", "kind_type", "date", "closure"])
def test_closed_request_cas_bounds_and_retained_closure(mutation):
    ws, old = workstream(), discovery(); req = request(ws, old); captured = closure(req, records_for(ws, old))
    if mutation == "ws_cas": req["base_revision"] = "f" * 64
    elif mutation == "old_cas": req["expected_discovery_revision"] = "f" * 64
    elif mutation == "extra": req["actor_ref"] = ACTOR
    elif mutation == "aggregate": req["replacement"]["body_utf8"] = "x" * 8193
    elif mutation == "confidence": req["replacement"]["confidence"] = "automatically_verified"
    elif mutation == "confidence_type": req["replacement"]["confidence"] = []
    elif mutation == "kind_type": req["replacement"]["kind"] = []
    elif mutation == "date": req["replacement"]["verified_at"] = "2026-02-30"
    else: captured["coverage"] = "PARTIAL"
    with pytest.raises(recipes.KnowledgeRecipeError): build(req, ws, old, captured=captured)


def test_reference_parser_rejects_duplicate_keys_and_alias_cycles():
    for text in ("---\nkey: A\nkey: B\n---\n", "---\nkey: A\nrefs: &x [*x]\n---\n"):
        with pytest.raises((ValueError, yaml.YAMLError)):
            agentos.parse_project_discovery_reference_text(text)


def test_full_validator_and_actual_current_context_preserve_and_follow_correction(tmp_path):
    ws, old = workstream(), discovery(); req = request(ws, old)
    result = build(req, ws, old); root = tmp_path / "agentos"
    for image in result["postimages"]:
        target = tmp_path / image["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(image["content_utf8"], encoding="utf-8")
    def run(*args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/agentos.py"), *args,
            "--root", str(root)], text=True, capture_output=True, cwd=tmp_path, timeout=20)
    valid = run("validate")
    assert valid.returncode == 0, valid.stdout + valid.stderr
    current = run("compile-context", "--workstream", "ALPHA", "--now", "2026-11-07T12:00:00Z")
    assert current.returncode == 0, current.stdout + current.stderr
    bundle = json.loads(current.stdout)
    keys = {item["key"] for section in bundle["sections"] for item in section["items"]}
    assert new_ref(req) in keys and OLD not in keys
    assert any(row.get("key") == OLD and "superseded_by" in row.get("reason", "") for row in bundle["excluded"])
    assert (root / "discoveries/DSC-ORIGINAL-FINDING.md").read_text().replace("\nsuperseded_by: " + new_ref(req), "", 1) == old

    # A later merge can introduce a foreign citation. The same unscoped
    # canonical validator rejects it and current context cannot emit the
    # corrected claim as an eligible discovery.
    (root / "workstreams/WS-OTHER.md").write_text(workstream("OTHER", [new_ref(req)]))
    invalid = run("validate")
    assert invalid.returncode == 1 and "project-correction-scope" in invalid.stdout
    current = run("compile-context", "--workstream", "ALPHA", "--now", "2026-11-07T12:00:00Z")
    assert current.returncode == 0, current.stdout + current.stderr
    bundle = json.loads(current.stdout)
    assert new_ref(req) not in {item["key"] for section in bundle["sections"] for item in section["items"]}
    assert any(row.get("key") == new_ref(req) and "malformed" in row.get("reason", "") for row in bundle["excluded"])
