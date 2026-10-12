"""Static regression guard for the shared Meta-CEO Fabric instructions.

This tests a *source contract*, not Codex/Claude installation, provider
admission, worker START, result consumption or production adoption.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
PLAYBOOK = (ROOT / "docs/CODEX_META_CEO_FABRIC.md").read_text(encoding="utf-8")

MARKER = "## Assigned Meta-CEO:"
DOCUMENT = "docs/CODEX_META_CEO_FABRIC.md"


def test_shared_instructions_are_enrolled_in_both_harnesses():
    for name, data in (("AGENTS.md", AGENTS), ("CLAUDE.md", CLAUDE)):
        assert data.count(MARKER) == 1, name
        assert DOCUMENT in data, name
        assert "Codex" in data and "Claude" in data, name
        assert "Fabric" in data, name


def test_role_not_promoted_by_harness_or_model_name():
    assert "Only a current Chairman-assigned principal/Meta-CEO holds this role" in AGENTS
    assert "ordinary workers keep their bounded role" in CLAUDE
    assert "explicitly Chairman-assigned" in PLAYBOOK
    assert "historical chat membership" in PLAYBOOK


def test_installed_adapter_route_is_root_bound_and_preserves_existing_carrier():
    expected = (
        "mastermind-fabric-delegate",
        "fabric_task.py",
        "CODEX_THREAD_ID",
        "VERIFIED_ROOT_ID",
        "--root",
        "--parent",
        "--stdin",
        "RUN_EXISTS",
        "effect uncertainty",
        "same original root",
    )
    for phrase in expected:
        assert phrase in PLAYBOOK, phrase
    assert "rather than" in PLAYBOOK
    assert "new scheduler" in PLAYBOOK


def test_principal_context_and_worker_evidence_are_not_conflated():
    for word in ("STATUS:", "RESULT:", "EVIDENCE:", "GAPS:", "EFFECTS:", "NEXT:"):
        assert word in PLAYBOOK
    assert "does **not** guarantee" in PLAYBOOK
    assert "exit code zero alone is not acceptance" in PLAYBOOK.lower()
    assert "Production adoption proof" in PLAYBOOK
    assert "root-bound accepted leaf count" in PLAYBOOK


def test_no_empty_capacity_spawning_or_automatic_permission_escalation():
    assert "do not start a child just to reach a concurrency count" in PLAYBOOK.lower()
    assert "per-root fair-share" in PLAYBOOK
    assert "workspace custody" in PLAYBOOK
    assert "does not" in PLAYBOOK
    assert "real permission" in PLAYBOOK.lower()
    assert "94" not in PLAYBOOK  # avoid baking a historical utilization number into law
