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


def _run_hook(name: str, cwd: Path, env_extra: dict | None = None,
              session_id: str | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "MACRO_LOCAL_ROOT"}
    # A host with the SSD storage policy installed delegates every mint to the
    # external volume (2026-10-10); point the hook at a policy that does not exist
    # so these tests exercise the internal mint hermetically on any host.
    env["MASTERMIND_WORKTREE_STORAGE_POLICY"] = str(cwd / "no-such-policy.json")
    env.update(env_extra or {})
    payload: dict = {"name": name, "cwd": str(cwd)}
    if session_id is not None:
        payload["session_id"] = session_id
    return subprocess.run(["python3", str(HOOK_PATH)], input=json.dumps(payload),
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


# ── SSD placement: the hook delegates to the host storage helper (2026-10-10) ──
#
# THE DEFECT THIS PINS: the user-level WorktreeCreate hook DEFERS to any project
# hook, and this project hook planted internally, so a Desktop session launched
# from the macro repo never reached the external SSD the global placement law
# mandates — and a stale host copy of this hook minted ``worktree-<name>`` trees
# the guard quarantined. The fix delegates to the same helper the global hook
# uses whenever the host policy file exists. A helper refusal is FINAL: no
# internal-disk fallback (DEC:ADMIN-BLOCKERS-ARE-SELF-REMEDIED-NEVER-HANDED-TO-THE-OPERATOR).

_FAKE_HELPER_OK = """\
import json, sys
from pathlib import Path
request = json.loads(sys.stdin.read())
Path(__file__).with_name("helper-call.json").write_text(
    json.dumps({"argv": sys.argv[1:], "request": request}), encoding="utf-8")
print("worktree-storage: minting on the external volume", file=sys.stderr)
print("/Volumes/fake/claude/0123456789abcdef/" + request["name"] + "-0123456789abcdef")
"""

_FAKE_HELPER_REFUSE = """\
import sys
print("worktree-storage: REFUSED: external volume /Volumes/Mastermind is not mounted",
      file=sys.stderr)
sys.exit(1)
"""


def _storage_env(tmp_path: Path, helper_source: str | None) -> dict:
    policy = tmp_path / "worktree-storage.json"
    policy.write_text(json.dumps({"root": "/Volumes/fake", "mount": "/Volumes/fake"}),
                      encoding="utf-8")
    helper = tmp_path / "fake_worktree_storage.py"
    if helper_source is not None:
        helper.write_text(helper_source, encoding="utf-8")
    return {"MASTERMIND_WORKTREE_STORAGE_POLICY": str(policy),
            "MASTERMIND_WORKTREE_STORAGE_HELPER": str(helper)}


def test_host_storage_policy_delegates_the_mint_to_the_helper(primary: Path,
                                                              tmp_path: Path) -> None:
    env = _storage_env(tmp_path, _FAKE_HELPER_OK)
    proc = _run_hook("ssd-probe", primary, env, session_id="sess-1")
    assert proc.returncode == 0, proc.stderr
    # stdout is the helper's path and NOTHING else — the harness contract.
    assert proc.stdout.strip() == "/Volumes/fake/claude/0123456789abcdef/ssd-probe-0123456789abcdef"
    assert proc.stdout.strip().count("\n") == 0
    assert "delegating placement to the host storage helper" in proc.stderr
    record = json.loads((tmp_path / "helper-call.json").read_text(encoding="utf-8"))
    assert record["argv"] == ["--config", env["MASTERMIND_WORKTREE_STORAGE_POLICY"], "create"]
    assert record["request"] == {"cwd": str(primary), "name": "ssd-probe",
                                 "session_id": "sess-1"}
    # Nothing was minted internally.
    assert not (primary / ".claude" / "worktrees" / "ssd-probe").exists()
    assert _git(primary, "branch", "--list", "claude/ssd-probe") == ""


def test_helper_refusal_is_final_with_no_internal_fallback(primary: Path,
                                                            tmp_path: Path) -> None:
    env = _storage_env(tmp_path, _FAKE_HELPER_REFUSE)
    proc = _run_hook("ssd-refused", primary, env)
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""
    assert "REFUSED: external volume" in proc.stderr
    assert "no internal-disk fallback" in proc.stderr
    assert not (primary / ".claude" / "worktrees" / "ssd-refused").exists()
    assert _git(primary, "branch", "--list", "claude/ssd-refused") == ""


def test_installed_policy_with_a_missing_helper_refuses(primary: Path,
                                                        tmp_path: Path) -> None:
    env = _storage_env(tmp_path, None)
    proc = _run_hook("ssd-no-helper", primary, env)
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""
    assert "helper" in proc.stderr and "missing" in proc.stderr
    assert not (primary / ".claude" / "worktrees" / "ssd-no-helper").exists()


def test_no_host_policy_means_the_internal_mint(primary: Path, tmp_path: Path) -> None:
    """The env override already points at a nonexistent policy: the mint is local."""
    assert hook.storage_policy_path().name == "worktree-storage.json"
    proc = _run_hook("local-probe", primary)
    assert proc.returncode == 0, proc.stderr
    assert "delegating placement" not in proc.stderr
    assert Path(proc.stdout.strip()) == primary / ".claude" / "worktrees" / "local-probe"
