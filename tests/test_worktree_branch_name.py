"""Session worktrees are minted on a branch the ship-loop guard admits.

THE DEFECT THIS PINS
--------------------
``.claude/hooks/worktree_create_sparse.py`` minted ``worktree-<name>``, while
``.claude/hooks/ship_loop_guard.py`` admits a delivery root only when it is a
linked worktree on ``claude/*`` (``_delivery_root_admission``) and files
``unsafe_branch`` on Stop otherwise. Every tree the hook planted therefore
started in a state its own guard quarantined (observed 2026-10-09: the operator
had to hand-create a ``claude/*`` branch before any work could ship).

The fix mints ``claude/<name>``. A ``worktree-<name>`` branch that already
exists is still attached exactly as before — branches and worktrees are never
renamed or deleted by the hook.

Hermetic: temp git repos with a local bare origin; no network, no real repo.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "worktree_create_sparse.py"
GUARD_PATH = REPO_ROOT / ".claude" / "hooks" / "ship_loop_guard.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load("_worktree_create_sparse_branch", HOOK_PATH)
guard = _load("_ship_loop_guard_branch", GUARD_PATH)


def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    assert p.returncode == 0, f"git {' '.join(args)} failed: {p.stderr}"
    return p.stdout.strip()


def _run_hook(name: str, cwd: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "MACRO_LOCAL_ROOT"}
    payload = json.dumps({"name": name, "cwd": str(cwd)})
    return subprocess.run(["python3", str(HOOK_PATH)], input=payload,
                          capture_output=True, text=True, env=env)


@pytest.fixture()
def primary(tmp_path: Path) -> Path:
    """A primary checkout whose ``origin`` is a local bare repository."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)],
                   capture_output=True, check=True)
    repo = tmp_path / "primary"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "config").mkdir()
    (repo / "config" / "sparse_worktree.json").write_text(
        json.dumps({"enabled": False, "exclude_dirs": []}), encoding="utf-8")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "init")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")
    return repo


def test_new_mint_is_on_claude_branch(primary: Path) -> None:
    proc = _run_hook("branch-probe", primary)
    assert proc.returncode == 0, proc.stderr
    dest = Path(proc.stdout.strip())
    assert dest == primary / ".claude" / "worktrees" / "branch-probe"
    assert _git(dest, "branch", "--show-current") == "claude/branch-probe"
    assert _git(dest, "rev-parse", "HEAD") == _git(primary, "rev-parse", "origin/main")
    # Nothing is minted in the legacy namespace any more.
    assert _git(primary, "branch", "--list", "worktree-branch-probe") == ""


def test_hook_minted_tree_is_admitted_by_the_ship_loop_guard(primary: Path) -> None:
    """The regression, stated end to end: the guard admits what the hook mints."""
    proc = _run_hook("admission-probe", primary)
    assert proc.returncode == 0, proc.stderr
    dest = Path(proc.stdout.strip())
    assert guard._delivery_root_admission(dest) == (True, "")


def test_existing_legacy_branch_is_still_attached(primary: Path) -> None:
    """A pre-existing ``worktree-<name>`` is attached, never renamed or replaced."""
    (primary / "legacy.txt").write_text("legacy work\n", encoding="utf-8")
    _git(primary, "add", "legacy.txt")
    _git(primary, "commit", "-m", "legacy work")
    _git(primary, "branch", "worktree-legacy-probe")
    legacy_tip = _git(primary, "rev-parse", "worktree-legacy-probe")
    _git(primary, "reset", "--hard", "HEAD~1")

    proc = _run_hook("legacy-probe", primary)
    assert proc.returncode == 0, proc.stderr
    assert "attaching to it" in proc.stderr
    dest = Path(proc.stdout.strip())
    assert _git(dest, "branch", "--show-current") == "worktree-legacy-probe"
    assert _git(dest, "rev-parse", "HEAD") == legacy_tip
    assert (dest / "legacy.txt").read_text(encoding="utf-8") == "legacy work\n"
    # The legacy branch survives untouched and no claude/<name> twin is minted.
    assert _git(primary, "rev-parse", "worktree-legacy-probe") == legacy_tip
    assert _git(primary, "branch", "--list", "claude/legacy-probe") == ""


def test_session_branch_prefers_an_existing_legacy_branch(primary: Path) -> None:
    assert hook.session_branch(primary, "fresh") == "claude/fresh"
    _git(primary, "branch", "worktree-old")
    assert hook.session_branch(primary, "old") == "worktree-old"


def test_name_that_cannot_form_a_branch_fails_cleanly(primary: Path) -> None:
    """``SAFE_NAME`` admits ``x.lock``; git does not — refuse before touching disk."""
    proc = _run_hook("probe.lock", primary)
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""
    assert "does not form a valid branch" in proc.stderr
    assert not (primary / ".claude" / "worktrees" / "probe.lock").exists()
