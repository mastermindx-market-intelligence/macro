"""Regression tests for Claude session-root admission and quarantine."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".claude" / "hooks" / "ship_loop_guard.py"
SPEC = importlib.util.spec_from_file_location("ship_loop_guard_root_admission", HOOK_PATH)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "kept.txt").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", "kept.txt")
    _git(repo, "commit", "-m", "initial")
    return repo


def _commit(repo: Path, rel: str, body: str, message: str) -> str:
    target = repo / rel
    target.write_text(body, encoding="utf-8")
    _git(repo, "add", rel)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _linked_claude_worktree(tmp_path: Path) -> tuple[Path, Path]:
    primary = _repo(tmp_path)
    worktree = tmp_path / "session-worktree"
    _git(primary, "worktree", "add", "-b", "claude/delivery-root", str(worktree))
    return primary, worktree


def test_primary_checkout_is_not_admitted_even_on_claude_branch(tmp_path):
    primary = _repo(tmp_path)
    _git(primary, "checkout", "-b", "claude/primary-is-still-shared")

    admitted, reason = GUARD._delivery_root_admission(primary)

    assert admitted is False
    assert "primary/shared checkout" in reason


def test_linked_claude_worktree_is_admitted(tmp_path):
    _primary, worktree = _linked_claude_worktree(tmp_path)
    assert GUARD._delivery_root_admission(worktree) == (True, "")


def test_quarantined_root_denies_bash_before_side_effect(tmp_path, capsys):
    primary = _repo(tmp_path)

    GUARD._pre_tool_use(
        primary,
        tmp_path / "state.json",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    out = json.loads(capsys.readouterr().out.strip())
    specific = out["hookSpecificOutput"]
    assert specific["permissionDecision"] == "deny"
    assert "SESSION ROOT QUARANTINE" in specific["permissionDecisionReason"]
    assert "fresh worktree-backed Claude session" in specific["permissionDecisionReason"]


def test_admitted_worktree_does_not_intercept_bash(tmp_path, capsys):
    _primary, worktree = _linked_claude_worktree(tmp_path)

    GUARD._pre_tool_use(
        worktree,
        tmp_path / "state.json",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    assert capsys.readouterr().out.strip() == ""


def test_quarantined_session_stops_cleanly_when_shared_main_moves(
    monkeypatch, tmp_path, capsys
):
    primary = _repo(tmp_path)
    state_path = tmp_path / "state.json"

    GUARD._session_start(
        primary,
        state_path,
        {"hook_event_name": "SessionStart", "source": "startup"},
    )
    start = json.loads(capsys.readouterr().out.strip())
    assert "SESSION ROOT QUARANTINE" in start["hookSpecificOutput"]["additionalContext"]
    state = GUARD._load(state_path)
    assert state["root_admission_v"] == GUARD._ROOT_ADMISSION_VERSION
    assert state["root_admitted"] is False

    _commit(primary, "bot.txt", "independent publication\n", "bot: move shared main")
    monkeypatch.setattr(
        GUARD,
        "_github_slug",
        lambda *_a: pytest.fail("a quarantined root reached GitHub"),
    )

    GUARD._stop(
        primary,
        state_path,
        {
            "hook_event_name": "Stop",
            "last_assistant_message": "SESSION END: DURABLE_EXECUTION_RUNNING",
        },
    )

    assert capsys.readouterr().out.strip() == ""


def test_settings_gate_effectful_tools_before_existing_guards():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    admission = [
        group for group in settings["hooks"]["PreToolUse"]
        if "ship_loop_guard.py" in json.dumps(group)
    ]
    assert len(admission) == 1
    matcher = admission[0]["matcher"]
    for required in (
        "Bash",
        "Edit",
        "Write",
        "Agent",
        "Workflow",
        "Skill",
        "EnterWorktree",
        "mcp__.*",
    ):
        assert required in matcher
