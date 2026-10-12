"""Focused ship-loop contracts for canonical semantic evidence consumption."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ship_loop_guard_semantic", ROOT / ".claude" / "hooks" / "ship_loop_guard.py"
)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)

HEAD = "a" * 40
BASE = "b" * 40
MERGE = "c" * 40
WITNESS_TREE = "d" * 40


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def _root_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "kept.txt").write_text("baseline\\n", encoding="utf-8")
    _git(repo, "add", "kept.txt")
    _git(repo, "commit", "-m", "initial")
    return repo


def _linked_root_fixture(tmp_path: Path) -> tuple[Path, Path]:
    primary = _root_fixture(tmp_path)
    worktree = tmp_path / "session-worktree"
    _git(primary, "worktree", "add", "-b", "claude/delivery-root", str(worktree))
    return primary, worktree


def test_delivery_root_rejects_primary_even_on_claude_branch(tmp_path):
    primary = _root_fixture(tmp_path)
    _git(primary, "checkout", "-b", "claude/primary-is-still-shared")

    admitted, reason = GUARD._delivery_root_admission(primary)

    assert admitted is False
    assert "primary/shared checkout" in reason


def test_delivery_root_accepts_linked_claude_worktree(tmp_path):
    _primary, worktree = _linked_root_fixture(tmp_path)
    assert GUARD._delivery_root_admission(worktree) == (True, "")


def test_linked_handoff_seat_is_quarantined_and_stop_does_not_loop(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    worktree = tmp_path / "handoff-seat"
    _git(
        primary,
        "worktree",
        "add",
        "-b",
        "handoff/information-to-price-fable-program-ceo-20261005",
        str(worktree),
    )

    admitted, reason = GUARD._delivery_root_admission(worktree)
    assert admitted is False
    assert "branch handoff/information-to-price-fable-program-ceo-20261005 is not claude/*" in reason

    state_path = tmp_path / "handoff-state.json"
    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "startup"},
    )
    start = json.loads(capsys.readouterr().out.strip())
    context = start["hookSpecificOutput"]["additionalContext"]
    assert "SESSION ROOT QUARANTINE" in context
    assert "MANDATORY SHIP LOOP" in context

    GUARD._stop(
        worktree,
        state_path,
        {
            "hook_event_name": "Stop",
            "last_assistant_message": "SESSION END: DURABLE_EXECUTION_RUNNING",
        },
    )
    assert capsys.readouterr().out.strip() == ""


def test_quarantined_root_denies_bash_before_side_effect(tmp_path, capsys):
    primary = _root_fixture(tmp_path)

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
    _primary, worktree = _linked_root_fixture(tmp_path)

    GUARD._pre_tool_use(
        worktree,
        tmp_path / "state.json",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    assert capsys.readouterr().out.strip() == ""


def test_quarantined_root_lets_enterworktree_repair_itself(tmp_path, capsys):
    primary = _root_fixture(tmp_path)

    # ExitWorktree (keeping the tree) is step 2 of the remedy when the conversation
    # sits in a native .claude/worktrees tree, so it is a repair tool too (2026-10-10).
    for tool in ("EnterWorktree", "ExitWorktree", "Read", "Grep"):
        GUARD._pre_tool_use(
            primary,
            tmp_path / "state.json",
            {"hook_event_name": "PreToolUse", "tool_name": tool},
        )
        assert capsys.readouterr().out.strip() == "", tool

    for tool in ("Bash", "Edit", "Write", "Agent", "mcp__x__y"):
        GUARD._pre_tool_use(
            primary,
            tmp_path / "state.json",
            {"hook_event_name": "PreToolUse", "tool_name": tool},
        )
        out = json.loads(capsys.readouterr().out.strip())
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", tool
        assert "EnterWorktree" in out["hookSpecificOutput"]["permissionDecisionReason"]


# ── the quarantine's own remedy is an in-session act (Chairman 2026-10-10) ──────
#
# DEC:ADMIN-BLOCKERS-ARE-SELF-REMEDIED-NEVER-HANDED-TO-THE-OPERATOR. A Meta-CEO
# seat ended on EXACT_HUMAN_GATE handing the operator the worktree-mint command,
# because the guard denied every execution tool — including the mint its own
# remedy needs — and its text read as "start a fresh session". The guard now
# prints the filled-in remedy and admits exactly that Bash shape.

_REMEDY_REQUEST = json.dumps({"cwd": "/r/primary", "name": "seat", "session_id": "s-1"})

REMEDY_SHAPES = (
    "printf '%s' '" + _REMEDY_REQUEST
    + "' | python3 /Users/x/.local/lib/mastermind/worktree-storage/worktree_storage.py create",
    "printf '%s' '{\"cwd\":\"/r\",\"name\":\"n\"}' | python3 "
    "~/.local/lib/mastermind/worktree-storage/worktree_storage.py "
    "--config /Users/x/.config/mastermind/worktree-storage.json create",
    "python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py check",
    "echo '{\"cwd\":\"/r\",\"name\":\"n\"}' | python3 /repo/.claude/hooks/worktree_create_sparse.py",
    "python \"/Users/x y/.claude/hooks/worktree_create_sparse.py\"",
    "git worktree list --porcelain",
    "git worktree unlock /Volumes/Mastermind/agent-workspaces/claude/abc/seat-abc",
    "git fetch origin",
    "git branch --show-current",
    "git rev-parse --show-toplevel",
    "git status --porcelain",
    "  df -h /Volumes/Mastermind  ",
    "ls -la /Volumes/Mastermind/agent-workspaces/claude",
    "cat ~/.config/mastermind/worktree-storage.json",
    "test -d /Volumes/Mastermind",
    "grep -n root ~/.config/mastermind/worktree-storage.json",
)

NON_REMEDY_SHAPES = (
    "",
    "git worktree list; rm -rf /tmp/x",
    "python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create && git push",
    "printf '%s' '{}' | python3 /x/worktree_storage.py create > /tmp/out",
    "printf '%s' '{}' | python3 /x/worktree_storage.py create | tee /tmp/log",
    "python3 /x/worktree_storage.py create\ngit push origin main",
    "ls $(cat secret)",
    "cat `whoami`",
    "echo \"$HOME\"",
    "git push origin main",
    "git worktree remove /x",
    "git checkout -b claude/x",
    "git commit -m x",
    "python3 other_script.py create",
    "python3 /x/worktree_storage.py",
    "python3 /x/worktree_storage.py delete",
    "rm -rf /Volumes/Mastermind",
    "lsblk",
    "testing",
    "cd /x && ls",
)


@pytest.mark.parametrize("command", REMEDY_SHAPES)
def test_remedy_shaped_bash_is_recognised(command):
    assert GUARD._is_quarantine_remedy_command(command), command


@pytest.mark.parametrize("command", NON_REMEDY_SHAPES)
def test_non_remedy_bash_is_not_recognised(command):
    assert not GUARD._is_quarantine_remedy_command(command), command


def test_quarantined_root_allows_the_remedy_mint_and_denies_other_bash(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    state = tmp_path / "state.json"

    for command in REMEDY_SHAPES:
        GUARD._pre_tool_use(
            primary,
            state,
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": command},
            },
        )
        assert capsys.readouterr().out.strip() == "", command

    for command in NON_REMEDY_SHAPES:
        GUARD._pre_tool_use(
            primary,
            state,
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": command},
            },
        )
        out = json.loads(capsys.readouterr().out.strip())
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", command

    # A Bash call without tool_input (older payloads) is still denied.
    GUARD._pre_tool_use(
        primary, state, {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
    )
    assert json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "permissionDecision"
    ] == "deny"
    # The remedy shape never opens a non-Bash tool.
    GUARD._pre_tool_use(
        primary,
        state,
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"command": REMEDY_SHAPES[0]},
        },
    )
    assert json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "permissionDecision"
    ] == "deny"


def _assert_remedy_text(text: str, root: Path) -> None:
    assert "never hand it to the operator" in text
    assert "never end the session on this blocker" in text
    assert "EnterWorktree" in text
    assert "printf '%s'" in text
    assert str(root) in text
    assert "worktree_storage.py" in text or "worktree_create_sparse.py" in text
    # The printed mint is a shape the guard itself admits while quarantined.
    mint = text.split("with `", 1)[1].split("`", 1)[0]
    assert GUARD._is_quarantine_remedy_command(mint), mint
    assert "fresh worktree-backed Claude session" in text


def test_quarantine_denial_prints_the_filled_in_remedy(tmp_path, capsys):
    primary = _root_fixture(tmp_path)

    GUARD._pre_tool_use(
        primary,
        tmp_path / "state.json",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "session_id": "sess-123",
        },
    )
    reason = json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "permissionDecisionReason"
    ]
    _assert_remedy_text(reason, primary)
    assert "sess-123" in reason
    # Not a native session tree: no ExitWorktree step is demanded.
    assert "ExitWorktree" not in reason


def test_quarantine_context_prints_the_filled_in_remedy(tmp_path, capsys):
    primary = _root_fixture(tmp_path)

    GUARD._session_start(
        primary,
        tmp_path / "state.json",
        {"hook_event_name": "SessionStart", "source": "startup", "session_id": "sess-9"},
    )
    context = json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "SESSION ROOT QUARANTINE" in context
    _assert_remedy_text(context, primary)
    assert "sess-9" in context
    assert "MANDATORY SHIP LOOP" in context


def test_native_session_tree_remedy_adds_the_exitworktree_step(tmp_path, capsys):
    """A conversation in `.claude/worktrees/<name>` must leave that tree first."""
    primary = _root_fixture(tmp_path)
    tree = primary / ".claude" / "worktrees" / "worktree-handoff-seat"
    tree.parent.mkdir(parents=True)
    _git(primary, "worktree", "add", "-b", "handoff/not-admitted", str(tree))
    admitted, _reason = GUARD._delivery_root_admission(tree)
    assert admitted is False

    GUARD._pre_tool_use(
        tree,
        tmp_path / "state.json",
        {"hook_event_name": "PreToolUse", "tool_name": "Write", "session_id": "s"},
    )
    reason = json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "permissionDecisionReason"
    ]
    _assert_remedy_text(reason, tree)
    assert "call ExitWorktree keeping the tree" in reason
    # The suggested name drops the legacy prefix and stays branch-safe.
    assert '"name": "handoff-seat"' in reason


def test_quarantine_suggested_name_is_branch_safe():
    assert GUARD._quarantine_suggested_name(Path("/x/worktree-rs leader(1)")) == "rs-leader-1"
    assert GUARD._quarantine_suggested_name(Path("/x/.hidden")) == "hidden"
    assert GUARD._quarantine_suggested_name(Path("/x/---")) == "seat"
    assert len(GUARD._quarantine_suggested_name(Path("/x/" + "a" * 200))) == 80


def test_quarantine_context_names_the_in_session_repair(tmp_path, capsys):
    primary = _root_fixture(tmp_path)

    GUARD._session_start(
        primary,
        tmp_path / "state.json",
        {"hook_event_name": "SessionStart", "source": "startup"},
    )

    context = json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "SESSION ROOT QUARANTINE" in context
    assert "EnterWorktree" in context


def test_relocated_session_seeds_completion_state_once(tmp_path, capsys):
    _primary, worktree = _linked_root_fixture(tmp_path)
    state_path = tmp_path / "relocated-state.json"
    (worktree / "kept.txt").write_text("dirty before the first effectful call\\n")

    GUARD._pre_tool_use(
        worktree,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    assert capsys.readouterr().out.strip() == ""
    state = GUARD._load(state_path)
    assert state["root"] == str(worktree)
    assert state["start_head"] == _git(worktree, "rev-parse", "HEAD")
    assert state["root_admitted"] is True
    assert state["root_admission_v"] == GUARD._ROOT_ADMISSION_VERSION
    assert state["seeded_by"] == "pre_tool_use_relocation"
    assert "kept.txt" in json.dumps(state["baseline"])

    state["blocker_count"] = 3
    GUARD._save(state_path, state)
    GUARD._pre_tool_use(
        worktree,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "Edit"},
    )
    assert GUARD._load(state_path)["blocker_count"] == 3


def test_quarantined_root_never_seeds_completion_state(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    state_path = tmp_path / "quarantined-state.json"

    GUARD._pre_tool_use(
        primary,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "EnterWorktree"},
    )

    assert capsys.readouterr().out.strip() == ""
    assert GUARD._load(state_path) is None


def _native_session_tree(tmp_path: Path, name: str = "seat") -> tuple[Path, Path]:
    """A tree shaped like Claude Code's native mint: .claude/worktrees/<n> on worktree-<n>."""
    primary = _root_fixture(tmp_path)
    worktree = primary / ".claude" / "worktrees" / name
    _git(primary, "worktree", "add", "-b", f"worktree-{name}", str(worktree))
    return primary, worktree


def _assert_bash_denied(worktree: Path, state_path: Path, capsys) -> None:
    GUARD._pre_tool_use(
        worktree,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    out = json.loads(capsys.readouterr().out.strip())
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_native_session_tree_is_adopted_at_first_effectful_call(tmp_path, capsys):
    _primary, worktree = _native_session_tree(tmp_path)
    state_path = tmp_path / "native-state.json"

    GUARD._pre_tool_use(
        worktree,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    assert capsys.readouterr().out.strip() == ""
    assert _git(worktree, "branch", "--show-current") == "claude/seat"
    assert GUARD._delivery_root_admission(worktree) == (True, "")
    state = GUARD._load(state_path)
    assert state["root_admitted"] is True
    assert state["seeded_by"] == "pre_tool_use_relocation"


def test_native_session_tree_is_adopted_at_session_start(tmp_path, capsys):
    _primary, worktree = _native_session_tree(tmp_path)
    state_path = tmp_path / "native-start.json"

    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "startup"},
    )

    context = json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
        "additionalContext"
    ]
    assert "SESSION BRANCH ADOPTED" in context
    assert "claude/seat" in context
    assert "SESSION ROOT QUARANTINE" not in context
    assert "MANDATORY SHIP LOOP" in context
    assert _git(worktree, "branch", "--show-current") == "claude/seat"
    assert GUARD._load(state_path)["root_admitted"] is True


def test_adoption_refuses_a_tree_outside_claude_worktrees(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    worktree = tmp_path / "seat"
    _git(primary, "worktree", "add", "-b", "worktree-seat", str(worktree))

    _assert_bash_denied(worktree, tmp_path / "state.json", capsys)
    assert _git(worktree, "branch", "--show-current") == "worktree-seat"


def test_adoption_refuses_a_branch_that_does_not_match_its_directory(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    worktree = primary / ".claude" / "worktrees" / "seat"
    _git(primary, "worktree", "add", "-b", "worktree-other", str(worktree))
    # A `worktree-seat` that exists but is NOT checked out here: without the
    # current-branch check, `git branch -m worktree-seat claude/seat` would succeed
    # and rename a branch this tree does not own.
    _git(primary, "branch", "worktree-seat")

    _assert_bash_denied(worktree, tmp_path / "state.json", capsys)
    assert _git(worktree, "branch", "--show-current") == "worktree-other"
    assert _git(primary, "for-each-ref", "--format=%(refname)", "refs/heads/claude/") == ""
    assert _git(primary, "rev-parse", "--verify", "refs/heads/worktree-seat")


def test_adoption_refuses_a_branch_with_an_upstream(tmp_path, capsys):
    _primary, worktree = _native_session_tree(tmp_path)
    _git(worktree, "config", "branch.worktree-seat.remote", "origin")
    _git(worktree, "config", "branch.worktree-seat.merge", "refs/heads/worktree-seat")

    _assert_bash_denied(worktree, tmp_path / "state.json", capsys)
    assert _git(worktree, "branch", "--show-current") == "worktree-seat"


def test_adoption_refuses_a_branch_with_a_remote_tracking_copy(tmp_path, capsys):
    _primary, worktree = _native_session_tree(tmp_path)
    _git(worktree, "update-ref", "refs/remotes/origin/worktree-seat", "HEAD")

    _assert_bash_denied(worktree, tmp_path / "state.json", capsys)
    assert _git(worktree, "branch", "--show-current") == "worktree-seat"


def test_adoption_never_clobbers_an_existing_claude_branch(tmp_path, capsys):
    primary, worktree = _native_session_tree(tmp_path)
    _git(primary, "branch", "claude/seat")

    _assert_bash_denied(worktree, tmp_path / "state.json", capsys)
    assert _git(worktree, "branch", "--show-current") == "worktree-seat"
    assert _git(primary, "rev-parse", "--verify", "refs/heads/claude/seat")


def test_adoption_refuses_a_packed_case_variant_of_its_target(tmp_path, capsys):
    primary, worktree = _native_session_tree(tmp_path)
    _git(primary, "branch", "claude/SEAT")
    _git(primary, "pack-refs", "--all")

    _assert_bash_denied(worktree, tmp_path / "state.json", capsys)
    assert _git(worktree, "branch", "--show-current") == "worktree-seat"
    assert (
        _git(primary, "for-each-ref", "--format=%(refname)", "refs/heads/claude/")
        == "refs/heads/claude/SEAT"
    )


def test_a_lost_adoption_race_still_admits_the_tree(monkeypatch, tmp_path, capsys):
    _primary, worktree = _native_session_tree(tmp_path)

    def sibling_hook_won(_root):
        # A concurrent PreToolUse process renamed the branch first; this one's
        # own attempt therefore adopts nothing.
        _git(worktree, "branch", "-m", "worktree-seat", "claude/seat")
        return ""

    monkeypatch.setattr(GUARD, "_adopt_native_session_branch", sibling_hook_won)
    GUARD._pre_tool_use(
        worktree,
        tmp_path / "race.json",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    assert capsys.readouterr().out.strip() == ""
    assert GUARD._load(tmp_path / "race.json")["root_admitted"] is True


def test_adoption_refuses_a_primary_checkout_in_native_shape(tmp_path, capsys):
    primary = tmp_path / ".claude" / "worktrees" / "host"
    primary.mkdir(parents=True)
    _git(primary, "init", "-b", "worktree-host")
    _git(primary, "config", "user.name", "Test")
    _git(primary, "config", "user.email", "test@example.com")
    (primary / "kept.txt").write_text("baseline\n", encoding="utf-8")
    _git(primary, "add", "kept.txt")
    _git(primary, "commit", "-m", "initial")

    _assert_bash_denied(primary, tmp_path / "state.json", capsys)
    assert _git(primary, "branch", "--show-current") == "worktree-host"


def test_root_admitted_in_place_readmits_its_quarantined_record(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    worktree = tmp_path / "handoff-seat"
    _git(primary, "worktree", "add", "-b", "handoff/seat", str(worktree))
    state_path = tmp_path / "in-place.json"

    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "startup"},
    )
    capsys.readouterr()
    born = GUARD._load(state_path)
    assert born["root_admitted"] is False
    assert born["baseline_captured"] is False

    _git(worktree, "branch", "-m", "handoff/seat", "claude/seat")
    (worktree / "kept.txt").write_text("dirty before the first admitted call\n")
    GUARD._pre_tool_use(
        worktree,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )

    assert capsys.readouterr().out.strip() == ""
    state = GUARD._load(state_path)
    assert state["root_admitted"] is True
    assert state["seeded_by"] == "pre_tool_use_admission"
    assert state["baseline_captured"] is True
    assert state["start_head"] == _git(worktree, "rev-parse", "HEAD")
    assert "kept.txt" in json.dumps(state["baseline"])


def test_resume_admitting_a_born_quarantined_root_captures_its_baseline(tmp_path, capsys):
    primary = _root_fixture(tmp_path)
    worktree = tmp_path / "handoff-seat"
    _git(primary, "worktree", "add", "-b", "handoff/seat", str(worktree))
    state_path = tmp_path / "resume.json"

    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "startup"},
    )
    capsys.readouterr()
    _git(worktree, "branch", "-m", "handoff/seat", "claude/seat")
    (worktree / "kept.txt").write_text("dirty before admission\n")
    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "resume"},
    )
    capsys.readouterr()

    state = GUARD._load(state_path)
    assert state["root_admitted"] is True
    assert state["baseline_captured"] is True
    assert "kept.txt" in json.dumps(state["baseline"])


def test_readmission_after_a_quarantined_compact_keeps_the_sessions_work(tmp_path, capsys):
    """Admitted -> work -> compact while not admissible -> re-admitted -> Stop blocks.

    Re-seeding a fresh record at re-admission would absorb the session's commit
    into start_head and its dirt into the baseline, releasing unshipped work.
    """
    _primary, worktree = _linked_root_fixture(tmp_path)
    state_path = tmp_path / "compact.json"
    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "startup"},
    )
    capsys.readouterr()
    born = GUARD._load(state_path)
    assert born["root_admitted"] is True

    (worktree / "work.txt").write_text("committed by the session\n", encoding="utf-8")
    _git(worktree, "add", "work.txt")
    _git(worktree, "commit", "-m", "session work")
    (worktree / "kept.txt").write_text("edited by the session\n", encoding="utf-8")

    _git(worktree, "checkout", "--detach")
    GUARD._session_start(
        worktree,
        state_path,
        {"hook_event_name": "SessionStart", "source": "compact"},
    )
    capsys.readouterr()
    assert GUARD._load(state_path)["root_admitted"] is False

    _git(worktree, "checkout", "claude/delivery-root")
    GUARD._pre_tool_use(
        worktree,
        state_path,
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    assert capsys.readouterr().out.strip() == ""
    state = GUARD._load(state_path)
    assert state["root_admitted"] is True
    assert state["seeded_by"] == "pre_tool_use_admission"
    assert state["start_head"] == born["start_head"]
    assert state["baseline"] == born["baseline"]

    GUARD._stop(
        worktree,
        state_path,
        {"hook_event_name": "Stop", "last_assistant_message": "SESSION END: PROVEN_OUTCOME"},
    )
    out = json.loads(capsys.readouterr().out.strip())
    assert out["decision"] == "block"
    assert "kept.txt" in out["reason"]


def test_quarantined_session_stops_cleanly_when_shared_main_moves(
    monkeypatch, tmp_path, capsys
):
    primary = _root_fixture(tmp_path)
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

    (primary / "bot.txt").write_text("independent publication\\n", encoding="utf-8")
    _git(primary, "add", "bot.txt")
    _git(primary, "commit", "-m", "bot: move shared main")
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


def _check(name: str, conclusion: str, *, details: bool = False) -> dict:
    return {
        "name": name,
        "status": "completed",
        "conclusion": conclusion,
        "started_at": "2026-08-15T01:00:00Z",
        "details_url": "https://github.com/acme/widgets/actions/runs/77/job/9"
        if details
        else "",
        "pull_requests": [
            {"number": 9, "head": {"sha": HEAD}, "base": {"sha": BASE}}
        ],
    }


def _unit(classification: str = "inherited_base") -> SimpleNamespace:
    return SimpleNamespace(
        logical_job_id="semantic-registry",
        proof_id="registry-contract",
        classification=classification,
        outcome="failed",
        pack_index=7,
        step_spec_sha256="1" * 64,
        job_exec_sha256="2" * 64,
        failure_signature=("failed:tests/test_registry.py::test_contract",),
        detail="base never reached step" if classification == "unknown" else "same failure",
        base_sha=BASE,
        head_sha=HEAD,
    )


def _gate(
    *,
    clear: bool,
    classification: str = "inherited_base",
    infrastructure_blocking: bool = False,
) -> SimpleNamespace:
    unit = _unit(classification)
    return SimpleNamespace(
        clear=clear,
        blocking=() if clear else (unit,),
        inherited=(unit,) if clear else (),
        passed=(),
        infrastructure_blocking=infrastructure_blocking,
    )


def _loaded() -> SimpleNamespace:
    return SimpleNamespace(mode="semantic", evidence={"fixture": "head"})


def _pull() -> dict:
    return {
        "number": 9,
        "head": {"sha": HEAD},
        "base": {"ref": "main", "sha": BASE},
        "labels": [{"name": GUARD.MERGE_ON_GREEN_LABEL}],
    }


def test_unmerged_inherited_red_names_semantic_identity_not_pack(monkeypatch):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "success", details=True),
        _check("fence-pack", "success"),
    ]
    monkeypatch.setattr(GUARD, "_open_pull", lambda *_a: _pull())
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: _loaded())
    monkeypatch.setattr(GUARD, "_semantic_gate", lambda _loaded: _gate(clear=True))
    monkeypatch.setattr(GUARD, "_semantic_authority_touched", lambda *_a: False)

    code, detail = GUARD._armed_pull_status(
        "acme", "widgets", "codex/example", HEAD
    )
    assert code == "unmerged"
    for phrase in (
        "logical job=semantic-registry",
        "proof id=registry-contract",
        "failure signature=",
        "base SHA=",
        "head SHA=",
        "transport pack=7",
        "ProofFreshness",
    ):
        assert phrase in detail
    assert f"base SHA={BASE}" in detail
    assert f"head SHA={HEAD}" in detail
    assert "fix ci-pack-7" not in detail.lower()


def test_main_target_split_ignores_only_inactive_pilot_authority_context() -> None:
    runs = [
        _check("ci-gate", "success"),
        _check("fence-pack", "success"),
        _check("ci-authority/main", "success"),
        _check("ci-authority/codex/merge-queue-pilot", "failure"),
    ]
    assert GUARD._split_head_runs(runs) == (
        [],
        [],
        ["ci-gate", "fence-pack", "ci-authority/main"],
    )

    active_red = [dict(run) for run in runs]
    active_red[2]["conclusion"] = "failure"
    red, pending, passed = GUARD._split_head_runs(active_red)
    assert red == ["ci-authority/main (failure)"]
    assert not pending
    assert passed == ["ci-gate", "fence-pack"]


def test_merged_head_ignores_the_inactive_pilot_context_like_its_siblings(
    monkeypatch,
) -> None:
    """`_check_ci` must agree with `_red_pairs`/`_split_head_runs` on ONE check.

    All three claim to share one definition of "not a red" — `_check_ci`'s own
    comment says so — but only two implemented the inactive-pilot exclusion.
    Measured on #5765's merged head: `_red_pairs` returned [] while `_check_ci`
    called the same head red, blocking a session whose PR had merged fully green.
    The damage is not just a false red: a non-empty `bad` ARMS the semantic
    evidence path, and a merged head cannot bind its proof base (GitHub drops
    `pull_requests` from check-runs once the PR closes), so the session was told
    "advertised semantic evidence is unusable ... does not identify the exact PR
    proof base" — proof plumbing it could not act on, for a check that is by
    design a retarget-invalidation receipt.
    """
    runs = [
        _check("ci-gate", "success"),
        _check("fence-pack", "success"),
        _check("ci-authority/main", "success"),
        _check("ci-authority/codex/merge-queue-pilot", "failure"),
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)

    # The sibling paths already agreed this head is clean.
    assert GUARD._red_pairs(runs) == []
    assert GUARD._split_head_runs(runs)[0] == []

    ok, detail = GUARD._check_ci(
        ROOT, "acme", "widgets", HEAD, MERGE,
        "2026-08-16T03:22:46Z", "claude/example", BASE,
    )
    assert ok, detail
    assert "merge-queue-pilot" not in detail

    # The ACTIVE context stays binding on this path too — the exclusion is one
    # literal, not a widening of the spurious-check allowlist.
    active_red = [dict(run) for run in runs]
    active_red[2]["conclusion"] = "failure"
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: active_red)
    ok_red, detail_red = GUARD._check_ci(
        ROOT, "acme", "widgets", HEAD, MERGE,
        "2026-08-16T03:22:46Z", "claude/example", BASE,
    )
    assert not ok_red
    assert "ci-authority/main" in detail_red


def test_unmerged_unknown_semantic_red_says_exact_refusal(monkeypatch):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]
    monkeypatch.setattr(GUARD, "_open_pull", lambda *_a: _pull())
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: _loaded())
    monkeypatch.setattr(
        GUARD, "_semantic_gate", lambda _loaded: _gate(clear=False, classification="unknown")
    )
    code, detail = GUARD._armed_pull_status(
        "acme", "widgets", "codex/example", HEAD
    )
    assert code == GUARD.CI_FAILED_UNMERGED
    assert "classification=unknown" in detail
    assert "base never reached step" in detail


def test_authority_changing_pr_cannot_use_semantic_self_excuse(monkeypatch):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "success", details=True),
        _check("fence-pack", "success"),
    ]
    monkeypatch.setattr(GUARD, "_open_pull", lambda *_a: _pull())
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: _loaded())
    monkeypatch.setattr(GUARD, "_semantic_gate", lambda _loaded: _gate(clear=True))
    monkeypatch.setattr(GUARD, "_semantic_authority_touched", lambda *_a: True)
    code, detail = GUARD._armed_pull_status(
        "acme", "widgets", "codex/example", HEAD
    )
    assert code == GUARD.CI_FAILED_UNMERGED
    assert "may not use candidate-era" in detail


def test_ship_loop_rename_away_keeps_previous_authority_path(monkeypatch):
    new_path = "docs/moved-merge-controller.py"
    old_path = "scripts/merge_on_green.py"
    monkeypatch.setattr(
        GUARD,
        "_get_json",
        lambda url: [
            {
                "filename": new_path,
                "previous_filename": old_path,
                "status": "renamed",
            }
        ]
        if "/pulls/9/files?" in url
        else pytest.fail(url),
    )
    checked = []

    def is_authority(path):
        checked.append(path)
        return path == old_path

    monkeypatch.setattr(GUARD, "is_ci_authority_path", is_authority)
    assert GUARD._semantic_authority_touched("acme", "widgets", 9) is True
    assert checked == [new_path, old_path]


def test_advertised_malformed_v1_is_not_legacy(monkeypatch):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]
    monkeypatch.setattr(GUARD, "_open_pull", lambda *_a: _pull())
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: (_ for _ in ()).throw(
            GUARD.semantic_proof.SemanticProofError("evidence/tree mismatch")
        ),
    )
    code, detail = GUARD._armed_pull_status(
        "acme", "widgets", "codex/example", HEAD
    )
    assert code == GUARD.CI_FAILED_UNMERGED
    assert "may not downgrade" in detail and "tree mismatch" in detail


def test_overall_red_descendant_pass_heals_frozen_unit_monotonically(
    monkeypatch, tmp_path
):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]
    candidates = [
        {"tested_tree_sha": "e" * 40, "overall": "failure", "x": "failed-later"},
        {"tested_tree_sha": WITNESS_TREE, "overall": "failure", "x": "passed"},
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: _loaded())
    monkeypatch.setattr(
        GUARD, "_semantic_gate", lambda _loaded: _gate(clear=False, classification="unknown")
    )
    monkeypatch.setattr(GUARD, "_recent_main_semantic_evidence", lambda *_a: candidates)
    monkeypatch.setattr(GUARD, "_run", lambda *_a, **_k: "")
    monkeypatch.setattr(
        GUARD,
        "_is_ancestor",
        lambda _root, ancestor, descendant: ancestor == MERGE and descendant == WITNESS_TREE,
    )

    def find(job, proof, merge, seen, is_ancestor, **_kwargs):
        assert (job, proof, merge) == (
            "semantic-registry",
            "registry-contract",
            MERGE,
        )
        assert seen == candidates
        assert _kwargs["old_step_spec_sha"] == "1" * 64
        # Newest later-red evidence cannot resurrect the old blocker; search any
        # ancestry-valid PASS, including one in an overall-red run.
        passed = next(item for item in seen if item.get("x") == "passed")
        assert passed["overall"] == "failure"
        assert is_ancestor(merge, passed["tested_tree_sha"])
        return SimpleNamespace(
            workflow_run_id=88,
            tested_tree_sha=passed["tested_tree_sha"],
            old_step_spec_sha="1" * 64,
            witness_step_spec_sha="3" * 64,
            contract_changed=True,
        )

    monkeypatch.setattr(GUARD.semantic_proof, "find_descendant_pass_witness", find)
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is True
    assert "healed by main run 88" in detail
    assert WITNESS_TREE in detail
    assert "1" * 64 in detail
    assert "3" * 64 in detail
    assert "contract_changed=true" in detail


def test_non_descendant_pass_does_not_clear_frozen_red(monkeypatch, tmp_path):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: _loaded())
    monkeypatch.setattr(GUARD, "_semantic_gate", lambda _loaded: _gate(clear=False))
    monkeypatch.setattr(
        GUARD,
        "_recent_main_semantic_evidence",
        lambda *_a: [{"tested_tree_sha": WITNESS_TREE, "x": "passed"}],
    )
    monkeypatch.setattr(GUARD, "_run", lambda *_a, **_k: "")
    monkeypatch.setattr(GUARD, "_is_ancestor", lambda *_a: False)
    monkeypatch.setattr(
        GUARD.semantic_proof,
        "find_descendant_pass_witness",
        lambda *_args, **_kwargs: None,
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "No ancestry-valid descendant PASS" in detail


def test_descendant_unit_pass_cannot_erase_frozen_infrastructure(monkeypatch, tmp_path):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]
    loaded = SimpleNamespace(
        mode="semantic",
        evidence={
            "authority_changed": False,
            "infrastructure": [
                {"outcome": "missing_pack_fragment", "pack_indices": [7]}
            ],
        },
    )
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: loaded)
    monkeypatch.setattr(GUARD, "_semantic_gate", lambda _loaded: _gate(clear=False))
    monkeypatch.setattr(
        GUARD,
        "_recent_main_semantic_evidence",
        lambda *_a: pytest.fail("infrastructure ambiguity attempted unit healing"),
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "missing_pack_fragment" in detail
    assert "cannot erase infrastructure" in detail


def test_descendant_unit_pass_cannot_erase_frozen_job_infrastructure(
    monkeypatch, tmp_path
):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]
    loaded = SimpleNamespace(
        mode="semantic",
        evidence={
            "authority_changed": False,
            "infrastructure": [],
            "jobs": [
                {
                    "logical_job_id": "semantic-registry",
                    "infrastructure": {
                        "outcome": "dependency_failed",
                        "detail": "pip install failed",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: loaded)
    monkeypatch.setattr(
        GUARD,
        "_semantic_gate",
        lambda _loaded: _gate(
            clear=False,
            classification="unknown",
            infrastructure_blocking=True,
        ),
    )
    monkeypatch.setattr(
        GUARD,
        "_recent_main_semantic_evidence",
        lambda *_a: pytest.fail("job infrastructure attempted unit healing"),
    )

    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "dependency_failed" in detail
    assert "cannot erase infrastructure" in detail


def test_green_path_performs_no_semantic_artifact_lookup(monkeypatch, tmp_path):
    monkeypatch.setattr(
        GUARD, "_head_check_runs", lambda *_a: [_check("ci-gate", "success", details=True)]
    )
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: pytest.fail("green path downloaded semantic evidence"),
    )
    assert GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    ) == (True, "")


def test_descendant_search_and_artifact_size_are_bounded():
    assert GUARD.SEMANTIC_RUN_LOOKBACK == 12
    assert GUARD.SEMANTIC_ARTIFACT_MAX_BYTES == 8 * 1024 * 1024


def test_ship_loop_binds_the_exact_ci_gate_base():
    runs = [_check("ci-gate", "failure", details=True)]
    assert GUARD._semantic_pr_base_sha(runs, HEAD, 9) == BASE
    # Absence is left to artifact selection: a genuinely pre-epoch run must keep
    # exact legacy behavior, while any present v1 still refuses without a bound base.
    assert GUARD._semantic_pr_base_sha(runs, HEAD, 10) is None


# --- Authority-only freeze: the ONE bounded clearing path (2026-08-19) -------
#
# An authority-changing PR merged while main was red used to be UNCLEARABLE
# FOREVER: the frozen head's own run is immutable, unit healing is disabled by
# design, and the nonunit refusal returned before E1 was ever consulted. E1 —
# a completed+success ci.yml run on a main DESCENDANT of the merge — executes
# ON the merged authority, so it is proof of main under the new gate, never the
# candidate-era evidence the fence forbids. These tests pin that E1 clears an
# authority-ONLY freeze, that a classified own-regression is never blanketed,
# that infrastructure ambiguity stays outside the path, and that the probe
# fails closed.
#
# The evidence is built by the REAL emitter (`reconcile_evidence`) and judged
# by the REAL gate (`semantic_gate_verdict`), never hand-shaped dicts: the
# emitter records the authority freeze itself as an
# `authority_self_excuse_refused` infrastructure row, so a hand-built
# "authority true, infrastructure empty" fixture is a shape it cannot produce —
# the first draft of these tests pinned exactly that unrealizable shape and
# therefore could not catch the predicate reading the wrong fields (pre-ship
# red team, 2026-08-19).

from tests.test_ci_semantic_proof import (
    _base_replay as _proof_base_replay,
    _fragment as _proof_fragment,
    _plan as _proof_plan,
    _signature as _proof_signature,
)


def _authority_frozen_evidence(*, inherited: bool) -> dict:
    """Real pr_head evidence for an authority-changing head with one red unit.

    ``inherited=True`` is the MOTIVATING case: the base replay failed the same
    way, so the unit classifies `inherited_base`, the emitter appends the
    `authority_self_excuse_refused` infrastructure row, and the gate blocks
    with ZERO blocking units. ``inherited=False`` is the case the clearing
    must refuse: the base replay PASSED the same step, so the unit classifies
    `pr_regression` — the head's own defect.
    """
    plan = _proof_plan(authority=True)
    replay = (
        _proof_base_replay(a_signature=_proof_signature())
        if inherited
        else _proof_base_replay(a_outcome="passed")
    )
    fragment = _proof_fragment(
        a_outcome="failed",
        a_signature=_proof_signature(),
        replay=replay,
        plan=plan,
    )
    return GUARD.semantic_proof.reconcile_evidence(plan, [fragment])


def _authority_frozen_loaded(*, inherited: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        mode="semantic", evidence=_authority_frozen_evidence(inherited=inherited)
    )


def _frozen_head_runs() -> list[dict]:
    return [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
    ]


def test_the_motivating_shape_is_realizable_and_authority_only() -> None:
    """The emitter really produces the shape the clearing is scoped to."""
    evidence = _authority_frozen_evidence(inherited=True)
    assert evidence["authority_changed"] is True
    assert [row["outcome"] for row in evidence["infrastructure"]] == [
        "authority_self_excuse_refused"
    ]
    gate = GUARD.semantic_proof.semantic_gate_verdict(evidence)
    assert gate.clear is False
    assert gate.blocking == ()
    assert GUARD._authority_freeze_is_sole_nonunit_blocker(
        SimpleNamespace(mode="semantic", evidence=evidence), gate
    ) is True


def test_descendant_main_green_clears_an_authority_only_freeze(monkeypatch, tmp_path):
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: _frozen_head_runs())
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: _authority_frozen_loaded(inherited=True),
    )
    monkeypatch.setattr(
        GUARD,
        "_recent_main_semantic_evidence",
        lambda *_a: pytest.fail("an authority freeze attempted semantic unit healing"),
    )
    monkeypatch.setattr(
        GUARD,
        "_merged_content_green",
        lambda _root, _owner, _repo, merge: {"id": 4242, "head_sha": WITNESS_TREE}
        if merge == MERGE
        else pytest.fail(merge),
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is True
    assert "4242" in detail
    assert "under the merged authority" in detail
    assert WITNESS_TREE[:12] in detail
    # The head's own frozen reds are disclosed as base-side, never re-litigated.
    assert "ci-pack-7 (failure)" in detail


def test_authority_freeze_never_blankets_a_classified_own_regression(
    monkeypatch, tmp_path
):
    """A pr_regression under authority_changed is the head's OWN red.

    The severity inversion the red team caught: the head that must stay
    refused is exactly the one whose artifact carries NO self-excuse row and
    no infrastructure — its blocking unit is the disqualifier."""
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: _frozen_head_runs())
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: _authority_frozen_loaded(inherited=False),
    )
    monkeypatch.setattr(
        GUARD,
        "_merged_content_green",
        lambda *_a: pytest.fail("an own-regression head consulted the E1 clearing"),
    )
    monkeypatch.setattr(GUARD, "_run", lambda *_a, **_k: "")
    monkeypatch.setattr(GUARD, "_is_ancestor", lambda *_a: False)
    monkeypatch.setattr(GUARD, "_recent_main_semantic_evidence", lambda *_a: [])
    monkeypatch.setattr(
        GUARD.semantic_proof,
        "find_descendant_pass_witness",
        lambda *_args, **_kwargs: None,
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "candidate-era proof" in detail
    # The refusal must NOT carry the clearing lever: a head with its own
    # classified regression has no descendant-baseline exit.
    assert "gh workflow run ci.yml --ref main" not in detail


def test_authority_only_freeze_names_the_baseline_lever_when_no_descendant_green(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: _frozen_head_runs())
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: _authority_frozen_loaded(inherited=True),
    )
    monkeypatch.setattr(GUARD, "_merged_content_green", lambda *_a: None)
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "authority_changed=true" in detail
    # The block must name its own clearing lever instead of reading as forever.
    assert "gh workflow run ci.yml --ref main" in detail
    assert "main descendant" in detail


def test_authority_freeze_probe_failure_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: _frozen_head_runs())
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: _authority_frozen_loaded(inherited=True),
    )

    def boom(*_a):
        raise RuntimeError("api down")

    monkeypatch.setattr(GUARD, "_merged_content_green", boom)
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "could not be probed" in detail
    assert "api down" in detail


def test_pending_checks_outrank_the_authority_freeze_clearing(monkeypatch, tmp_path):
    runs = _frozen_head_runs() + [
        {
            "name": "fence-pack",
            "status": "in_progress",
            "conclusion": None,
            "started_at": "2026-08-15T01:10:00Z",
            "details_url": "",
            "pull_requests": [],
        }
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: _authority_frozen_loaded(inherited=True),
    )
    monkeypatch.setattr(
        GUARD,
        "_merged_content_green",
        lambda *_a: {"id": 4242, "head_sha": WITNESS_TREE},
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert detail.startswith("CI still running")
    assert "fence-pack" in detail


def test_authority_freeze_with_infrastructure_never_consults_the_clearing(
    monkeypatch, tmp_path
):
    """A foreign infrastructure row alongside the freeze keeps the refusal."""
    evidence = _authority_frozen_evidence(inherited=True)
    evidence["infrastructure"].append(
        {"outcome": "missing_pack_fragment", "detail": "pack 5 emitted no fragment"}
    )
    loaded = SimpleNamespace(mode="semantic", evidence=evidence)
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: _frozen_head_runs())
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: loaded)
    monkeypatch.setattr(GUARD, "_semantic_gate", lambda _loaded: _gate(clear=False))
    monkeypatch.setattr(
        GUARD,
        "_merged_content_green",
        lambda *_a: pytest.fail("infrastructure ambiguity consulted the E1 clearing"),
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "cannot erase infrastructure" in detail


def test_authority_freeze_predicate_fails_closed_on_unreadable_evidence():
    frozen_gate = SimpleNamespace(
        clear=False, blocking=(), inherited=(_unit(),), passed=(),
        infrastructure_blocking=True,
    )
    unreadable = SimpleNamespace(mode="semantic", evidence=None)
    assert (
        GUARD._authority_freeze_is_sole_nonunit_blocker(unreadable, frozen_gate)
        is False
    )
    benign = SimpleNamespace(mode="semantic", evidence={"authority_changed": False})
    assert (
        GUARD._authority_freeze_is_sole_nonunit_blocker(benign, frozen_gate) is False
    )
    frozen = _authority_frozen_loaded(inherited=True)
    # A classified blocking unit disqualifies even a perfect freeze artifact.
    blocking_gate = _gate(clear=False)
    assert (
        GUARD._authority_freeze_is_sole_nonunit_blocker(frozen, blocking_gate)
        is False
    )
    # A gate missing the attribute entirely fails closed.
    bare_gate = SimpleNamespace(clear=False)
    assert GUARD._authority_freeze_is_sole_nonunit_blocker(frozen, bare_gate) is False
    # A foreign infrastructure row disqualifies.
    foreign = SimpleNamespace(mode="semantic", evidence=dict(frozen.evidence))
    foreign.evidence["infrastructure"] = list(foreign.evidence["infrastructure"]) + [
        {"outcome": "planner_configuration_failure", "detail": "boom"}
    ]
    assert (
        GUARD._authority_freeze_is_sole_nonunit_blocker(foreign, frozen_gate) is False
    )
    # A failed job-level infrastructure outcome disqualifies.
    job_infra = SimpleNamespace(mode="semantic", evidence=dict(frozen.evidence))
    job_infra.evidence["jobs"] = [
        {
            "logical_job_id": "job-a",
            "infrastructure": {"outcome": "dependency_failed"},
        }
    ]
    assert (
        GUARD._authority_freeze_is_sole_nonunit_blocker(job_infra, frozen_gate)
        is False
    )
    # The realizable freeze-only shape is the ONE admitted shape.
    assert (
        GUARD._authority_freeze_is_sole_nonunit_blocker(frozen, frozen_gate) is True
    )


def test_ship_loop_uses_strict_shared_artifact_parser():
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            GUARD.SEMANTIC_ARTIFACT_FILE,
            '{"workflow":"ci","workflow":"forged"}',
        )
    with pytest.raises(
        GUARD.semantic_proof.SemanticProofError,
        match="duplicate JSON key 'workflow'",
    ):
        GUARD._semantic_json_from_archive(archive.getvalue())


def test_ship_loop_linked_red_call_delta_is_three_json_plus_one_archive(monkeypatch):
    api_calls = []
    archive_calls = []
    loader_kwargs = {}
    loaded = SimpleNamespace(
        mode="semantic", evidence={"fixture": True, "tested_tree_sha": MERGE}
    )
    artifact = {
        "name": "ci-semantic-evidence-77",
        "archive_download_url": "https://api.github.com/artifact.zip",
        "expired": False,
    }

    def get(url):
        api_calls.append(url)
        if url.endswith("/actions/runs/77"):
            return {
                "id": 77,
                "name": "ci",
                "path": ".github/workflows/ci.yml",
                "event": "pull_request",
                "head_sha": HEAD,
                "pull_requests": _check("ci-gate", "failure")["pull_requests"],
            }
        if url.endswith("/actions/runs/77/artifacts?per_page=100"):
            return {"total_count": 1, "artifacts": [artifact]}
        if url.endswith(f"/git/commits/{MERGE}"):
            return {
                "sha": MERGE,
                "parents": [{"sha": BASE}, {"sha": HEAD}],
            }
        raise AssertionError(url)

    monkeypatch.setattr(GUARD, "_get_json", get)
    monkeypatch.setattr(
        GUARD,
        "_get_artifact_bytes",
        lambda url: archive_calls.append(url) or b"archive",
    )
    monkeypatch.setattr(
        GUARD, "_semantic_json_from_archive", lambda _raw: {"fixture": True}
    )
    def load(*_args, **kwargs):
        loader_kwargs.update(kwargs)
        return loaded

    monkeypatch.setattr(GUARD.semantic_proof, "load_semantic_evidence", load)
    result = GUARD._semantic_evidence_for_head(
        "acme",
        "widgets",
        HEAD,
        check_runs=[_check("ci-gate", "failure", details=True)],
        expected_base_sha=BASE,
    )
    assert result is loaded
    assert len(api_calls) == 3
    assert not any("/workflows/ci.yml/runs" in url for url in api_calls)
    assert api_calls[-1].endswith(f"/git/commits/{MERGE}")
    assert archive_calls == ["https://api.github.com/artifact.zip"]
    assert loader_kwargs["expected_event"] == "pull_request"
    assert loader_kwargs["expected_tested_tree_sha"] is None


@pytest.mark.parametrize(
    ("commit", "message"),
    [
        (
            {"sha": "e" * 40, "parents": [{"sha": BASE}, {"sha": HEAD}]},
            "returned a different commit",
        ),
        (
            {
                "sha": MERGE,
                "parents": [{"sha": BASE}, {"sha": HEAD}, {"sha": "e" * 40}],
            },
            "not the exact two-parent PR merge",
        ),
    ],
)
def test_ship_loop_artifact_cannot_self_claim_tested_merge_tree(
    monkeypatch, commit, message
):
    artifact = {
        "name": "ci-semantic-evidence-77",
        "archive_download_url": "https://api.github.com/artifact.zip",
        "expired": False,
    }

    def get(url):
        if url.endswith("/actions/runs/77/artifacts?per_page=100"):
            return {"total_count": 1, "artifacts": [artifact]}
        if url.endswith(f"/git/commits/{MERGE}"):
            return commit
        raise AssertionError(url)

    monkeypatch.setattr(GUARD, "_get_json", get)
    monkeypatch.setattr(GUARD, "_get_artifact_bytes", lambda _url: b"archive")
    monkeypatch.setattr(GUARD, "_semantic_json_from_archive", lambda _raw: {"v": 1})
    monkeypatch.setattr(
        GUARD.semantic_proof,
        "load_semantic_evidence",
        lambda *_a, **_k: SimpleNamespace(
            mode="semantic", evidence={"tested_tree_sha": MERGE}
        ),
    )

    with pytest.raises(GUARD.semantic_proof.SemanticProofError, match=message):
        GUARD._semantic_evidence_for_run(
            "acme",
            "widgets",
            {
                "id": 77,
                "name": "ci",
                "path": ".github/workflows/ci.yml",
                "event": "pull_request",
                "head_sha": HEAD,
                "pull_requests": _check("ci-gate", "failure")["pull_requests"],
            },
            role="pr_head",
            expected_base_sha=BASE,
        )


def test_malformed_later_main_artifact_cannot_resurrect_older_valid_pass(monkeypatch):
    runs = [
        {"id": 99, "conclusion": "failure"},
        {"id": 88, "conclusion": "failure"},
    ]
    older = {"schema": "validated-older-pass"}
    monkeypatch.setattr(
        GUARD,
        "_get_json",
        lambda url: {"workflow_runs": runs}
        if "/workflows/ci.yml/runs" in url
        else pytest.fail(url),
    )

    def load(_owner, _repo, run, *, role):
        assert role == "main"
        if run["id"] == 99:
            raise GUARD.semantic_proof.SemanticProofError("malformed later artifact")
        return SimpleNamespace(mode="semantic", evidence=older)

    monkeypatch.setattr(GUARD, "_semantic_evidence_for_run", load)
    assert GUARD._recent_main_semantic_evidence("acme", "widgets") == [older]


# ---------------------------------------------------------------------------
# The other edge of the inactive-context exclusion (#5773/#5776 -> this).
#
# Excluding a check from the reds must not promote the head to PROVEN. The
# inactive context is red on every pull request in this repository, so its
# standing failure was accidentally the only thing keeping a head that proved
# NOTHING out of `_check_ci`'s cheap green return — `NON_RED_CONCLUSIONS` holds
# `skipped` and `neutral`. Measured on 65f9669f: all three shapes below returned
# `(True, "")`, releasing a session on a head with no CI verdict at all.
# ---------------------------------------------------------------------------

#: Spelled out rather than read off the guard: this suite must be able to fail
#: against a build that dropped the exclusion, and a test that reads its
#: subject's own constant cannot do that.
INACTIVE_CONTEXT = "ci-authority/codex/merge-queue-pilot"


def _merged_check(name: str, conclusion: str, *, details: bool = False) -> dict:
    """A check run on a MERGED head: `_check` minus the associations GitHub drops."""
    run = _check(name, conclusion, details=details)
    run["pull_requests"] = []
    return run


def test_the_inactive_context_literal_is_the_one_the_guard_excludes() -> None:
    assert GUARD.CI_AUTHORITY_INACTIVE_CONTEXT == INACTIVE_CONTEXT
    assert GUARD._is_non_binding_check(INACTIVE_CONTEXT)
    assert not GUARD._is_non_binding_check("ci-authority/main")


def test_vercel_build_rate_limit_status_is_non_binding_in_ship_gate() -> None:
    assert GUARD.VERCEL_STATUS_CONTEXT == "Vercel"
    assert GUARD._is_non_binding_check("Vercel")


@pytest.mark.parametrize(
    "runs",
    [
        pytest.param(
            [
                _merged_check("ci-plan", "skipped"),
                _merged_check("ci-gate", "skipped"),
                _merged_check(INACTIVE_CONTEXT, "failure"),
            ],
            id="every binding check skipped",
        ),
        pytest.param(
            [
                _merged_check("some-app", "neutral"),
                _merged_check(INACTIVE_CONTEXT, "failure"),
            ],
            id="neutral only",
        ),
        pytest.param(
            [
                _merged_check(INACTIVE_CONTEXT, "failure"),
                _merged_check("Workers Builds: macro", "failure"),
            ],
            id="nothing binding at all",
        ),
    ],
)
def test_check_ci_refuses_a_merged_head_with_no_affirmative_pass(
    monkeypatch, tmp_path, runs
):
    """An unproven head must not read as green just because nothing is red."""
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(
        GUARD,
        "_semantic_evidence_for_head",
        lambda *_a, **_k: pytest.fail("an unproven head must not buy evidence"),
    )
    ok, reason = GUARD._check_ci(
        tmp_path, "acme", "widgets", HEAD, MERGE, "2026-08-16T01:32:13Z", "claude/x", BASE
    )
    assert ok is False
    assert "no affirmative passing check" in reason
    # `_stop` files anything starting with "Failing" as the INTERNAL `ci_failed`
    # ladder (10 consecutive / 15 total). A merged head with no CI verdict must
    # not be the cheap external 2/3 exit, which any other wording would make it.
    assert reason.startswith("Failing")


def test_check_ci_still_greens_a_normally_merged_head(monkeypatch, tmp_path):
    """Bound on the rule above: one real success is all it asks for.

    The sweeper refuses to merge a head with no `success` at all, so every head
    reaching `_check_ci` merged has one — measured 10 of 17 on the records-only
    PR #5772. `skipped` siblings and the inactive context do not change that.
    """
    runs = [
        _merged_check("ci-gate", "success"),
        _merged_check("ci-plan", "skipped"),
        _merged_check(INACTIVE_CONTEXT, "failure"),
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    assert GUARD._check_ci(
        tmp_path, "acme", "widgets", HEAD, MERGE, "2026-08-16T01:32:13Z", "claude/x", BASE
    ) == (True, "")


def test_a_pending_head_is_still_reported_as_running_not_unproven(
    monkeypatch, tmp_path
):
    """Pending outranks the new rule: a head still working is not a head that failed."""
    runs = [
        _merged_check("ci-gate", "skipped"),
        dict(_merged_check("ci-pack-3", "success"), status="in_progress", conclusion=None),
        _merged_check(INACTIVE_CONTEXT, "failure"),
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    ok, reason = GUARD._check_ci(
        tmp_path, "acme", "widgets", HEAD, MERGE, "2026-08-16T01:32:13Z", "claude/x", BASE
    )
    assert ok is False
    assert reason.startswith("CI still running")


# ---------------------------------------------------------------------------
# The permanent-trap fence: a unit main is not eligible to report on can never
# be cleared by a descendant PASS, so it must never pin a session (PR #5936,
# 2026-08-19). Semantic eligibility is role-dependent — ci.yml plans the merge
# gate `--gate code` while `gate: data` jobs run on data-health.yml, which
# emits no main-role evidence at all — so a head planned before that split
# froze blocking units no main run will ever name again.
# ---------------------------------------------------------------------------


def _inventory(job_ids, *, artifacts=5, descendant=4):
    return GUARD.semantic_proof.MainRoleInventory(
        frozenset(job_ids), artifacts, descendant
    )


def _frozen_red_head(monkeypatch, inventory):
    runs = [
        _check("ci-pack-7", "failure"),
        _check("ci-gate", "failure", details=True),
        _check("some-other-check", "success"),
    ]
    monkeypatch.setattr(GUARD, "_head_check_runs", lambda *_a: runs)
    monkeypatch.setattr(GUARD, "_semantic_evidence_for_head", lambda *_a, **_k: _loaded())
    monkeypatch.setattr(GUARD, "_semantic_gate", lambda _loaded: _gate(clear=False))
    monkeypatch.setattr(
        GUARD, "_recent_main_semantic_evidence", lambda *_a: [{"fixture": "main"}]
    )
    monkeypatch.setattr(GUARD, "_run", lambda *_a, **_k: "")
    monkeypatch.setattr(GUARD, "_is_ancestor", lambda *_a: True)
    monkeypatch.setattr(
        GUARD.semantic_proof,
        "find_descendant_pass_witness",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        GUARD.semantic_proof,
        "main_role_job_inventory",
        lambda *_args, **_kwargs: inventory,
    )


def test_unit_main_never_plans_is_retired_not_waited_on(monkeypatch, tmp_path):
    """The measured trap: block forever on a job no main run can ever emit.

    #5936 merged clean and its Stop gate then demanded a descendant PASS for
    `house-law-registry`/`signal-contract` across seven post-merge main runs
    that structurally could not carry them.
    """
    _frozen_red_head(monkeypatch, _inventory({"some-code-job", "another-code-job"}))
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is True
    # Retirement is loud: the unit stays in the record by name.
    assert "semantic-registry/registry-contract" in detail
    assert "structurally unclearable" in detail
    assert "main-eligible=no" in detail


def test_main_eligible_unit_still_blocks_and_says_waiting_can_help(
    monkeypatch, tmp_path
):
    _frozen_red_head(monkeypatch, _inventory({"semantic-registry", "some-code-job"}))
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "main-eligible=yes" in detail
    assert "structurally unclearable" not in detail


def test_thin_main_inventory_never_retires_a_unit(monkeypatch, tmp_path):
    """Fail-closed: too few readable main artifacts answers `unknown`, not `no`."""
    _frozen_red_head(
        monkeypatch, _inventory({"some-code-job"}, artifacts=1, descendant=1)
    )
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "main-eligible=unknown" in detail
    assert "structurally unclearable" not in detail


def test_unreadable_inventory_leaves_the_old_refusal_intact(monkeypatch, tmp_path):
    """A raising inventory probe must not crash the gate or release the head."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("artifact window unreadable")

    _frozen_red_head(monkeypatch, _inventory({"some-code-job"}))
    monkeypatch.setattr(GUARD.semantic_proof, "main_role_job_inventory", boom)
    ok, detail = GUARD._check_ci(
        tmp_path,
        "acme",
        "widgets",
        HEAD,
        MERGE,
        "2026-08-15T01:30:00Z",
        "codex/example",
    )
    assert ok is False
    assert "No ancestry-valid descendant PASS" in detail
