"""Prevent obsolete startup ceremony from contradicting current workspace custody.

These are instruction-source checks, not proof of native installation, hook trust,
or autonomous continuation. Runtime/release protections retain their own tests.
"""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]


def normalized(path: str) -> str:
    return " ".join(re.sub(r"[*`#>]", "", (ROOT / path).read_text()).split()).lower()


@pytest.mark.parametrize("path", ["AGENTS.md", "CLAUDE.md"])
def test_task_start_does_not_merge_the_shared_primary_checkout(path):
    text = normalized(path)
    assert "at session start: git fetch origin && git merge --ff-only origin/main" not in text
    assert "never merge, pull, reset, rebase or stash the shared primary checkout" in text


@pytest.mark.parametrize("path", ["AGENTS.md", "CLAUDE.md"])
def test_workspace_recovery_does_not_escalate_a_failed_fast_forward_by_itself(path):
    text = normalized(path)
    assert "if the fast-forward fails, stop and tell the operator" not in text
    assert "fast-forward fails, stop and tell the operator" not in text
    assert "an administrative fast-forward failure is not a mission-wide stop" in text
    assert "preserve its changes and acquire or recover the task's isolated workspace" in text


@pytest.mark.parametrize("path", ["AGENTS.md", "CLAUDE.md"])
def test_accepted_workspace_path_and_branch_are_not_renamed_to_fit_an_old_default(path):
    text = normalized(path)
    assert "reuse the exact workspace and branch assigned by the accepted harness or workspace owner" in text
    assert "mmx-workspace acquire" in text
    assert "--repository macro" in text
    assert "do not rename an existing accepted branch to satisfy a different client's convention" in text


def test_checkpoint_first_recovery_does_not_require_all_account_local_memory():
    text = normalized("AGENTS.md")
    assert "read claude.md in full" not in text
    assert "for delivery work, always include" not in text
    assert "recover the current cumulative checkpoint before following historical handoffs" in text
    assert "account-local memory is optional advisory context" in text


@pytest.mark.parametrize("path", ["AGENTS.md", "CLAUDE.md"])
def test_recovery_shortcut_does_not_waive_real_custody_or_permission_gates(path):
    text = normalized(path)
    assert "live writer, permission denial and unresolved effect remain real action-scoped gates" in text
    assert "a new workspace does not transfer a started operation" in text
