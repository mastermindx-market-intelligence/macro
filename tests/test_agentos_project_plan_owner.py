"""The actual Agent OS DEC validator and stdout-only author preserve plan facts."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def owner():
    spec = importlib.util.spec_from_file_location("plan_owner_test", ROOT / "scripts/agentos.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adoption():
    return {
        "schema": "agentos.project_plan_adoption.v1", "work_ref": "WS:PLAN-TEST",
        "adopted_source": {
            "repository": "mastermindx-market-intelligence/macro",
            "path": "agentos/workstreams/WS-PLAN-TEST.md",
            "commit": "a" * 40, "content_sha256": hashlib.sha256(b"actual bytes\n").hexdigest(),
        },
        "predecessor": None, "proposal_source": None, "display_revision": None,
    }


def decision():
    return {
        "key": "PLAN-DECISION", "question": "Which exact content is the baseline?",
        "answer": "The referenced bytes, after an actual present decision.",
        "rationale": "An authored current record is distinct from an accepted baseline.",
        "alternatives": [{"option": "Infer adoption", "why_not": "No owner decision."}],
        "evidence": ["Source-only fixture"], "affects": ["WS:PLAN-TEST"],
        "confidence": "high", "reversibility": "easy", "decided_by": "fixture-seat",
        "decided_at": "2026-11-04", "project_plan_adoption": adoption(),
    }


def test_actual_drafter_preserves_closed_metadata_and_round_trips(tmp_path):
    module = owner()
    payload = decision()
    before = deepcopy(payload)
    text = module.draft_decision(payload)
    output = tmp_path / "DEC-PLAN-DECISION.md"
    output.write_text(text, encoding="utf-8")
    parsed, _ = module.parse_record(output)
    assert parsed["project_plan_adoption"] == payload["project_plan_adoption"]
    assert parsed["project_plan_adoption"]["display_revision"] is None
    assert not [p for p in module.check_decision(parsed, output) if p.hard]
    assert payload == before
    assert "stdout only" in text


@pytest.mark.parametrize("mutate", [
    lambda rec: rec["project_plan_adoption"].update({"granted": True}),
    lambda rec: rec["project_plan_adoption"].update({"work_ref": "WS:FOREIGN"}),
    lambda rec: rec["project_plan_adoption"]["adopted_source"].update({"path": "../private.md"}),
    lambda rec: rec["project_plan_adoption"].update({"display_revision": "SECRET\nvalue"}),
    lambda rec: rec.update({"project_plan_adoption": None}),
    lambda rec: rec["project_plan_adoption"].update({"predecessor": "DEC:PRIOR-DECISION"}),
    lambda rec: rec["project_plan_adoption"].update({"predecessor": "DEC:PLAN-DECISION"}),
])
def test_validator_and_drafter_refuse_invalid_declarations_without_echo(mutate, capsys):
    module = owner()
    rec = decision()
    mutate(rec)
    findings = module.check_decision(rec, Path("DEC-PLAN-DECISION.md"))
    errors = [p for p in findings if p.hard and p.rule == "bad-project-plan-adoption"]
    assert len(errors) == 1
    with pytest.raises(SystemExit):
        module.draft_decision(rec)
    output = capsys.readouterr()
    assert "SECRET" not in str(errors) + output.out + output.err
    assert "private.md" not in str(errors) + output.out + output.err


def test_legacy_decisions_do_not_load_optional_helper(monkeypatch):
    module = owner()
    rec = decision()
    del rec["project_plan_adoption"]
    def forbidden():
        raise AssertionError("optional helper was loaded for legacy source")
    monkeypatch.setattr(module, "_project_plan_contract", forbidden)
    assert not [p for p in module.check_decision(rec, Path("DEC-PLAN-DECISION.md")) if p.hard]
    assert "project_plan_adoption" not in module.draft_decision(rec)


def test_declared_extension_without_captured_helper_fails_closed(monkeypatch, capsys):
    module = owner()
    def missing():
        raise FileNotFoundError("sensitive source path must not leak")
    monkeypatch.setattr(module, "_project_plan_contract", missing)
    findings = module.check_decision(decision(), Path("DEC-PLAN-DECISION.md"))
    assert any(p.hard and p.message == "PLAN_CONTRACT_UNAVAILABLE" for p in findings)
    with pytest.raises(SystemExit):
        module.draft_decision(decision())
    output = capsys.readouterr()
    assert "sensitive source" not in output.out + output.err + str(findings)


def test_existing_cli_emits_metadata_but_does_not_write_record(tmp_path):
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(decision()), encoding="utf-8")
    canonical = ROOT / "agentos/decisions/DEC-PLAN-DECISION.md"
    assert not canonical.exists()
    result = subprocess.run([sys.executable, str(ROOT / "scripts/agentos.py"),
                             "draft-decision", "--from", str(source)],
                            text=True, capture_output=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    output = tmp_path / "DEC-PLAN-DECISION.md"
    output.write_text(result.stdout, encoding="utf-8")
    parsed, _ = owner().parse_record(output)
    assert parsed["project_plan_adoption"] == adoption()
    assert not canonical.exists()


def test_loader_uses_exact_sibling_not_ambient_scripts(tmp_path, monkeypatch):
    decoy = tmp_path / "scripts"
    decoy.mkdir()
    (decoy / "__init__.py").write_text("")
    (decoy / "agentos_project_plan_contract.py").write_text("raise AssertionError('ambient import')")
    monkeypatch.syspath_prepend(str(tmp_path))
    module = owner()
    assert module._validated_project_plan_adoption(decision()) == adoption()


@pytest.mark.parametrize("candidate", [
    b"\n  # Leading whitespace\n", b"# LF\n", b"# CRLF\r\n",
    "\ufeff# Exact Unicode 内容\n".encode("utf-8"),
])
@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_proposal_owner_preserves_every_candidate_byte(candidate, ending):
    module = owner()
    header = {"schema": "agentos.project_plan_proposal.v1", "proposal_id": "PLAN-PROPOSAL",
              "work_ref": "WS:PLAN-TEST", "base_adoption": None,
              "base_source": adoption()["adopted_source"],
              "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
              "rationale": "A bounded candidate, not an adoption.", "evidence": []}
    # Actual YAML owner serializer, then exact framing; no candidate reserialization.
    yaml_header = module.yaml.safe_dump(header, sort_keys=False).replace("\n", ending)
    raw = ("---" + ending + yaml_header + "---" + ending).encode("utf-8") + candidate
    parsed, returned = module.parse_project_plan_proposal(raw, work_ref="WS:PLAN-TEST")
    assert parsed == header
    assert returned == candidate


@pytest.mark.parametrize("raw", [b"not YAML", b"---\nsecret: [broken\n---\nbody",
                                  b"---\n{}\n--- trailing\nbody", b"---\n{}\n---"])
def test_invalid_proposal_artifact_has_closed_value_free_error(raw):
    module = owner()
    with pytest.raises(ValueError, match="^INVALID_PROPOSAL$"):
        module.parse_project_plan_proposal(raw, work_ref="WS:PLAN-TEST")


def test_adoption_read_join_requires_real_decision_not_only_metadata():
    module = owner()
    rec = decision()
    current = module.select_project_plan_adoption([rec], work_ref="WS:PLAN-TEST")
    assert current == {"decision_ref": "DEC:PLAN-DECISION", "adoption": adoption()}
    # The pure metadata graph cannot manufacture the surrounding owner decision.
    del rec["question"]
    with pytest.raises(ValueError, match="^INVALID_ADOPTION$"):
        module.select_project_plan_adoption([rec], work_ref="WS:PLAN-TEST")


def test_legacy_only_adoption_join_is_absent_not_inferred():
    module = owner()
    rec = decision()
    del rec["project_plan_adoption"]
    rec["answer"] = "Plan v18 accepted and current"  # prose is not a typed receipt
    assert module.select_project_plan_adoption([rec], work_ref="WS:PLAN-TEST") is None


def test_real_git_proposal_binds_enclosing_artifact_and_candidate_separately(tmp_path):
    module = owner()
    candidate = "\n  # Proposed 内容\r\n".encode("utf-8")
    header = {"schema": "agentos.project_plan_proposal.v1", "proposal_id": "PLAN-PROPOSAL",
              "work_ref": "WS:PLAN-TEST", "base_adoption": None,
              "base_source": adoption()["adopted_source"],
              "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
              "rationale": "Real Git bytes in a local fixture, not a product decision.",
              "evidence": []}
    raw = module._yaml_frontmatter(header).encode("utf-8") + candidate
    repository = tmp_path / "captured-macro"
    repository.mkdir()
    def git(*args):
        result = subprocess.run(["git", "-C", str(repository), *args],
                                capture_output=True, check=True)
        return result.stdout
    git("init", "--quiet")
    artifact = repository / "proposal.md"
    artifact.write_bytes(raw)
    git("add", "proposal.md")
    git("-c", "user.name=Plan fixture", "-c", "user.email=fixture@invalid.example",
        "commit", "--quiet", "-m", "Fixture only")
    commit = git("rev-parse", "HEAD").decode("ascii").strip()
    captured = git("show", commit + ":proposal.md")
    source_ref = {"repository": "mastermindx-market-intelligence/macro",
                  "path": "proposal.md", "commit": commit,
                  "content_sha256": hashlib.sha256(captured).hexdigest()}
    assert module._project_plan_contract().bind_source_ref(source_ref, captured) == source_ref
    parsed, returned = module.parse_project_plan_proposal(captured, work_ref="WS:PLAN-TEST")
    assert returned == candidate and parsed == header
    assert source_ref["content_sha256"] != parsed["candidate_sha256"]
    with pytest.raises(ValueError, match="^SOURCE_BYTES_MISMATCH$"):
        module._project_plan_contract().bind_source_ref(source_ref, candidate)


def test_actual_owner_round_trips_reciprocal_three_decision_lineage(tmp_path):
    module = owner()
    records = []
    keys = ["PLAN-FIRST", "PLAN-SECOND", "PLAN-THIRD"]
    for index, key in enumerate(keys):
        rec = decision()
        rec["key"] = key
        if index:
            predecessor = "DEC:" + keys[index - 1]
            rec["project_plan_adoption"]["predecessor"] = predecessor
            rec["supersedes"] = [predecessor]
        if index < 2:
            rec["superseded_by"] = "DEC:" + keys[index + 1]
        rec["project_plan_adoption"]["display_revision"] = "Explicit fixture " + str(index)
        path = tmp_path / ("DEC-" + key + ".md")
        path.write_text(module.draft_decision(rec), encoding="utf-8")
        parsed, _ = module.parse_record(path)
        assert not [problem for problem in module.check_decision(parsed, path) if problem.hard]
        records.append(parsed)
    current = module.select_project_plan_adoption(records, work_ref="WS:PLAN-TEST")
    assert current["decision_ref"] == "DEC:PLAN-THIRD"
    assert current["adoption"]["display_revision"] == "Explicit fixture 2"
    # A stale decision on an older baseline is rejected by the actual pure writer
    # precondition. This still does not turn a stdout draft into a CAS transaction.
    stale = adoption()
    stale["predecessor"] = "DEC:PLAN-FIRST"
    with pytest.raises(ValueError, match="^STALE_PREDECESSOR$"):
        module._project_plan_contract().require_expected_predecessor(stale, current)
    # An intact-looking current row cannot conceal a missing superseded record.
    with pytest.raises(ValueError):
        module.select_project_plan_adoption(records[1:], work_ref="WS:PLAN-TEST")


def test_actual_record_key_is_required_no_invented_id_alias():
    module = owner()
    rec = decision()
    rec["id"] = "DEC:" + rec.pop("key")
    with pytest.raises(ValueError, match="^INVALID_ADOPTION$"):
        module._project_plan_contract().select_current_adoption([rec], work_ref="WS:PLAN-TEST")


def test_stale_base_checks_validate_current_shape_and_same_workstream():
    module = owner()
    contract = module._project_plan_contract()
    foreign = adoption()
    foreign["work_ref"] = "WS:FOREIGN"
    foreign["adopted_source"]["path"] = "planning/foreign.md"
    current = {"decision_ref": "DEC:FOREIGN-DECISION", "adoption": foreign}
    candidate = adoption()
    candidate["predecessor"] = current["decision_ref"]
    with pytest.raises(ValueError, match="^WORK_REF_MISMATCH$"):
        contract.require_expected_predecessor(candidate, current)
    proposal = {"schema": "agentos.project_plan_proposal.v1", "proposal_id": "PLAN-PROPOSAL",
                "work_ref": "WS:PLAN-TEST", "base_adoption": current["decision_ref"],
                "base_source": deepcopy(foreign["adopted_source"]),
                "candidate_sha256": hashlib.sha256(b"Candidate\n").hexdigest(),
                "rationale": "A proposal", "evidence": []}
    with pytest.raises(ValueError, match="^WORK_REF_MISMATCH$"):
        contract.require_proposal_base(proposal, current)
    malformed_current = {"decision_ref": "DEC:PLAN-DECISION", "adoption": adoption()}
    malformed_current["adoption"]["schema"] = "agentos.execution_plan.v1"
    candidate["predecessor"] = malformed_current["decision_ref"]
    with pytest.raises(ValueError, match="^INVALID_ADOPTION$"):
        contract.require_expected_predecessor(candidate, malformed_current)
