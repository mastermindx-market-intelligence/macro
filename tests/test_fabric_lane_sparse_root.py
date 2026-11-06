"""Fabric lane sparse-root admission: opt-in, no incumbent worktree mutation.

Tests use short-lived Git repos under tmp_path only; no live lane is changed.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts import worktree_sparse as ws


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, timeout=20, check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("MASTERMIND_FABRIC_SPARSE_NEW", raising=False)

    repo = home / "project"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "user.email", "fixture@example.test")
    (repo / "config").mkdir()
    (repo / "config" / "sparse_worktree.json").write_text(
        '{"enabled":true,"exclude_dirs":["data","site","mockups","verify_shots"]}\n'
    )
    (repo / "scripts").mkdir()
    (repo / "scripts" / "keep.py").write_text("print(1)\n")
    for name in ("data", "site", "mockups", "verify_shots"):
        (repo / name).mkdir()
        (repo / name / "tracked.txt").write_text(name + "\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "seed")

    lane = home / "lanes" / "wt" / "new-worker"
    lane.parent.mkdir(parents=True)
    _git(repo, "worktree", "add", "--detach", str(lane), "HEAD")
    operator = home / "operator-root"
    _git(repo, "worktree", "add", "--detach", str(operator), "HEAD")
    return repo, lane, operator, home


def test_fabric_lane_default_off_preserves_full(checkouts):
    _, lane, _, _ = checkouts
    assert ws.is_linked_worktree(lane)
    assert not ws.path_under_session_root(lane)
    assert not ws.is_session_worktree(lane)
    assert ws.auto_profile(lane) == 0
    assert (lane / "data" / "tracked.txt").exists()
    result = subprocess.run(["git", "-C", str(lane), "config", "--get", "core.sparseCheckout"],
                            capture_output=True, text=True, timeout=10)
    assert result.stdout.strip() != "true"


def test_qualified_new_fabric_lane_uses_existing_profile(checkouts, monkeypatch):
    _, lane, _, _ = checkouts
    before = _git(lane, "rev-parse", "HEAD")
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.path_under_session_root(lane)
    assert ws.is_session_worktree(lane)
    assert ws.auto_profile(lane) == 0
    assert _git(lane, "config", "--get", "core.sparseCheckout") == "true"
    assert _git(lane, "rev-parse", "HEAD") == before
    assert _git(lane, "status", "--porcelain") == ""
    for name in ("data", "site", "mockups", "verify_shots"):
        assert not (lane / name / "tracked.txt").exists()
    assert (lane / "scripts" / "keep.py").exists()


def test_user_explicit_materialization_survives_auto(checkouts, monkeypatch):
    _, lane, _, _ = checkouts
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.auto_profile(lane) == 0
    _git(lane, "sparse-checkout", "add", "data")
    assert (lane / "data" / "tracked.txt").exists()
    assert ws.auto_profile(lane) == 0
    assert (lane / "data" / "tracked.txt").exists()


def test_opt_in_does_not_touch_operator_checkout(checkouts, monkeypatch):
    _, lane, operator, home = checkouts
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.is_linked_worktree(operator)
    assert not ws.path_under_session_root(operator)
    assert not ws.is_session_worktree(operator)
    assert ws.auto_profile(operator) == 0
    assert (operator / "data" / "tracked.txt").exists()

    nested = home / "lanes" / "wt" / "group" / "child"
    assert not ws.path_under_session_root(nested)


def test_primary_checkout_and_bad_opt_in_not_enrolled(checkouts, monkeypatch):
    _, lane, _, home = checkouts
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "true")
    assert not ws.path_under_session_root(lane)
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")

    primary = home / "lanes" / "wt" / "primary-repository"
    primary.mkdir()
    _git(primary, "init", "-q")
    assert ws.path_under_session_root(primary)
    assert not ws.is_session_worktree(primary)
    assert ws.auto_profile(primary) == 0


def test_new_path_requires_exact_immediate_child(checkouts, monkeypatch):
    _, _, _, home = checkouts
    uncreated = home / "lanes" / "wt" / "future-worker"
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.path_under_session_root(uncreated)
    assert not ws.path_under_session_root(home / "lanes" / "wt")
    assert not ws.path_under_session_root(home / "lanes" / "wt" / "nested" / "future-worker")


def test_original_sparse_minter_avoids_full_checkout_and_rejects_reuse(
    checkouts, monkeypatch,
):
    """The incumbent Git sparse mint—not a new Fabric scheduler—creates a clean lane."""
    repo, _, _, home = checkouts
    destination = home / "lanes" / "wt" / "new-qualified-worker"
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.mint_session_worktree(
        repo, destination, branch="lane/new-qualified-worker",
        base="HEAD", fetch=False, reuse_existing=False, strict=True,
    ) == 0
    original = _git(repo, "rev-parse", "HEAD")
    assert _git(destination, "rev-parse", "HEAD") == original
    assert _git(destination, "branch", "--show-current") == "lane/new-qualified-worker"
    assert _git(destination, "config", "--get", "core.sparseCheckout") == "true"
    assert _git(destination, "status", "--porcelain") == ""
    assert (destination / "scripts" / "keep.py").is_file()
    for name in ("data", "site", "mockups", "verify_shots"):
        assert not (destination / name / "tracked.txt").exists()
    # No unqualified resumption of this same worktree; existing branch is preserved.
    assert ws.mint_session_worktree(
        repo, destination, branch="lane/new-qualified-worker",
        base="HEAD", fetch=False, reuse_existing=False, strict=True,
    ) == 1
    assert _git(destination, "rev-parse", "HEAD") == original
    assert _git(destination, "status", "--porcelain") == ""


def test_original_sparse_minter_refuses_unqualified_fabric_destination(
    checkouts, monkeypatch,
):
    repo, _, _, home = checkouts
    destination = home / "lanes" / "wt" / "unqualified-worker"
    monkeypatch.delenv("MASTERMIND_FABRIC_SPARSE_NEW", raising=False)
    assert ws.mint_session_worktree(
        repo, destination, branch="lane/unqualified-worker",
        base="HEAD", fetch=False, reuse_existing=False, strict=True,
    ) == 1
    assert not destination.exists()
    assert _git(repo, "branch", "--list", "lane/unqualified-worker") == ""

def test_fabric_mint_cli_pinned_commit_and_strict_no_reuse(
    checkouts, monkeypatch,
):
    repo, _, _, home = checkouts
    sha = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(ws, "ROOT", repo)
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.main(["fabric-mint", "lane-alpha", sha]) == 0
    dest = home / "lanes" / "wt" / "lane-alpha"
    assert _git(dest, "rev-parse", "HEAD") == sha
    assert _git(dest, "branch", "--show-current") == "lane/lane-alpha"
    assert _git(dest, "config", "--get", "core.sparseCheckout") == "true"
    assert _git(dest, "status", "--porcelain") == ""
    for name in ("data", "site", "mockups", "verify_shots"):
        assert not (dest / name / "tracked.txt").exists()
    # A repeated command is not a resume or a grant to reset an incumbent.
    assert ws.main(["fabric-mint", "lane-alpha", sha]) == 1
    assert _git(dest, "rev-parse", "HEAD") == sha


def test_fabric_mint_cli_requires_explicit_new_workspace_owner(
    checkouts, monkeypatch,
):
    repo, _, _, home = checkouts
    sha = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(ws, "ROOT", repo)
    monkeypatch.delenv("MASTERMIND_FABRIC_SPARSE_NEW", raising=False)
    assert ws.main(["fabric-mint", "lane-beta", sha]) == 1
    assert not (home / "lanes" / "wt" / "lane-beta").exists()
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    assert ws.main(["fabric-mint", "lane-beta", "0" * 40]) == 1
    assert ws.main(["fabric-mint", "../unsafe", sha]) == 1
    assert ws.main(["fabric-mint", "lane-beta", "not-a-commit"]) == 1
    assert not (home / "lanes" / "wt" / "lane-beta").exists()
    assert _git(repo, "branch", "--list", "lane/lane-beta") == ""

def test_inconsistent_sparse_config_does_not_silently_pass(checkouts, monkeypatch, capsys):
    """A true config bit with no sparse rules is NOT a real sparse checkout."""
    repo, lane, _, home = checkouts
    before = _git(lane, "rev-parse", "HEAD")
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    # Mirrors live Ubuntu1 false-success: setting the config bit without
    # materializing the sparse-checkout pattern file.
    _git(lane, "config", "core.sparseCheckout", "true")
    rules_path = _git(lane, "rev-parse", "--git-path", "info/sparse-checkout")
    assert not Path(rules_path).exists()
    probe = subprocess.run(
        ["git", "-C", str(lane), "sparse-checkout", "list"],
        capture_output=True, text=True, timeout=10,
    )
    assert not probe.stdout.strip()
    assert ws.is_session_worktree(lane)
    assert ws.auto_profile(lane) == 1
    err = capsys.readouterr().err
    assert "inconsistent sparse state" in err
    assert _git(lane, "rev-parse", "HEAD") == before
    assert _git(lane, "status", "--porcelain=v1", "-uall") == ""
    assert (lane / "data" / "tracked.txt").is_file()
    assert (lane / "site" / "tracked.txt").is_file()


def test_true_sparse_rules_preserve_explicit_materialization(checkouts, monkeypatch):
    """A user-requested sparse add data is intentionally NOT reset by auto."""
    _, lane, _, _ = checkouts
    before = _git(lane, "rev-parse", "HEAD")
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    _git(lane, "sparse-checkout", "init", "--cone")
    _git(lane, "sparse-checkout", "set", "scripts")
    _git(lane, "sparse-checkout", "add", "data")
    assert (lane / "data" / "tracked.txt").is_file()
    assert _git(lane, "sparse-checkout", "list")
    assert ws.auto_profile(lane) == 0
    assert (lane / "data" / "tracked.txt").is_file()
    assert not (lane / "site" / "tracked.txt").exists()
    assert _git(lane, "status", "--porcelain=v1", "-uall") == ""
    assert _git(lane, "rev-parse", "HEAD") == before


def test_inconsistent_primary_checkout_is_never_rewritten(checkouts, monkeypatch):
    """An operator's primary checkout remains a protected non-session root."""
    repo, _, _, _ = checkouts
    sha = _git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("MASTERMIND_FABRIC_SPARSE_NEW", "1")
    _git(repo, "config", "core.sparseCheckout", "true")
    assert ws.auto_profile(repo) == 0
    assert _git(repo, "rev-parse", "HEAD") == sha
    assert (repo / "data" / "tracked.txt").exists()
