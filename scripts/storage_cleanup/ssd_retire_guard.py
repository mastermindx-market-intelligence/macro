"""Safety-only adapter for Mastermind's existing SSD worktree reaper.

Does not own a new lifecycle. Git is the worktree registry; Executive/Fabric owns
session liveness; GitHub is the publication proof. Fail closed on uncertainty.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

PINNED_COMMIT = "6b154e09357300964c0720448cee9654bf2585d0"
GC_RELEASE = Path.home() / ".local/lib/mastermind/storage-cleanup/gc-releases" / PINNED_COMMIT
REQUIRED_HUMAN_ROOTS = frozenset({
    "/Volumes/Mastermind/worktrees",
    "/Volumes/Mastermind/agent-workspaces/sol",
    "/Volumes/Mastermind/agent-workspaces/review",
})
HELPER_LOCK = "mastermind-external-storage: removable volume protection"
AUDIT = Path.home() / ".local/state/mastermind/storage-cleanup/ssd-reaper-ledger.jsonl"


def _inside(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([str(path), str(root)]) == str(root)
    except ValueError:
        return False


def load_pinned_gc():
    """Verify canonical GitHub blob hashes and source pin before importing code."""
    m = json.loads((GC_RELEASE / "manifest.json").read_text())
    if m.get("source_commit") != PINNED_COMMIT or m.get("source_repo") != "mastermindx-market-intelligence/macro":
        raise RuntimeError("GC pin identity changed")
    for name in ("worktree_gc.py", "worktree_gc.json"):
        p = GC_RELEASE / name
        expected = m["files"][name]["sha256"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise RuntimeError("GC source integrity mismatch: " + name)
    cfg = json.loads((GC_RELEASE / "worktree_gc.json").read_text())
    if not REQUIRED_HUMAN_ROOTS.issubset(set(cfg.get("human_driven_roots") or ())):
        raise RuntimeError("GC lacks required human-driven protections")
    if cfg.get("include_open_pr") or cfg.get("include_orphans"):
        raise RuntimeError("GC unexpectedly permits unresolved/open source retirement")
    if cfg.get("min_age_days", 0) < 3:
        raise RuntimeError("GC retention below ratified 3-day floor")
    spec = importlib.util.spec_from_file_location("macro_pinned_worktree_gc", GC_RELEASE / "worktree_gc.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("GC release cannot be imported")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "human_driven_protection") or not hasattr(mod, "classify"):
        raise RuntimeError("GC protection interface absent")
    return mod, cfg


def journal(phase: str, path: Path, detail: str = "") -> None:
    """Reuse the existing SSD reaper audit ledger, including an effect fence."""
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"phase": phase, "path": str(path),
                                 "detail": detail, "pin": PINNED_COMMIT}) + "\n")
        output.flush()
        os.fsync(output.fileno())


def unresolved_effects() -> list[str]:
    if not AUDIT.exists():
        return []
    pending: set[str] = set()
    for line in AUDIT.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            raise RuntimeError("audit journal unreadable; retirement suspended")
        phase, path = item.get("phase"), item.get("path")
        if phase == "BEGIN_REMOVE":
            pending.add(path)
        elif phase in ("VERIFIED_REMOVED", "VERIFIED_RELOCKED", "EFFECT_NONE"):
            pending.discard(path)
        elif phase == "EFFECT_UNKNOWN":
            pending.add(path)
    return sorted(pending)


def _cmd(*args: str, timeout: int = 40):
    return subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)


def _must(code, detail):
    if not code:
        raise ValueError(detail)


def remove_candidate(*, gc, primary: Path, w, cfg: dict, procs, pr_states,
                     fetch_ok: bool, protected, check_volume, member) -> dict:
    """One non-force Git retirement. Any uncertain Git mutation freezes replay.

    No branch deletion. No ignored artifact deletion. Nonzero return is refusal.
    """
    path = Path(w.path)
    act = {"path": str(path), "branch": w.branch, "head": w.head,
           "verdict": w.verdict, "proof": w.proof}
    mutated = False
    def skip(reason: str):
        act["skipped"] = reason
        return act
    if unresolved_effects():
        return skip("earlier effect unresolved")
    if w.verdict not in gc.SAFE_VERDICTS or not w.proof or not w.head or not w.branch:
        return skip("no exact positive completion or remote preservation proof")
    if not fetch_ok or pr_states is None or procs is None:
        return skip("remote publication or process evidence unavailable")
    if (pr_states.get(w.branch) or {}).get("state") == "OPEN":
        return skip("open PR")
    if any(_inside(path, Path(r)) for r in protected):
        return skip("human-driven root")
    root = Path(member["root"])
    if not _inside(path, root / "claude") and not _inside(path, root / "codex") and not _inside(path, root / "manual"):
        return skip("outside managed client roots")
    if os.path.islink(path) or not path.is_dir():
        return skip("path absent or symlink")
    try:
        check_volume(member, path, check_space=False)
    except Exception as exc:
        return skip("SSD identity not verified: " + type(exc).__name__)
    marker = path / ".git"
    if not marker.is_file() or marker.is_symlink():
        return skip("not an ordinary linked Git worktree")
    try:
        pointer = marker.read_text().strip()
        _must(pointer.startswith("gitdir: "), "invalid Git pointer")
        gitdir = Path(pointer[8:])
        if not gitdir.is_absolute():
            gitdir = (path / gitdir).resolve()
        common_result = _cmd("git", "-C", str(primary), "rev-parse", "--path-format=absolute",
                             "--git-common-dir", timeout=25)
        _must(common_result.returncode == 0, "Git common-dir unavailable")
        common = Path(common_result.stdout.strip())
        _must(_inside(gitdir, common / "worktrees"), "Git pointer outside original common-dir")
        lock_path = gitdir / "locked"
        _must(not (gitdir / "index.lock").exists(), "Git index locked")
        _must(not lock_path.exists() or lock_path.read_text().strip() == HELPER_LOCK,
              "operator lock held")
        head = _cmd("git", "-C", str(path), "rev-parse", "HEAD", timeout=35)
        branch = _cmd("git", "-C", str(path), "symbolic-ref", "--short", "HEAD", timeout=25)
        _must(head.returncode == 0 and head.stdout.strip() == w.head, "HEAD changed")
        _must(branch.returncode == 0 and branch.stdout.strip() == w.branch, "branch changed")
        local = _cmd("git", "--git-dir=" + str(common), "rev-parse",
                     "--verify", "refs/heads/" + w.branch, timeout=25)
        _must(local.returncode == 0 and local.stdout.strip() == w.head, "branch ref changed")
        registered = _cmd("git", "-C", str(primary), "worktree", "list", "--porcelain", timeout=50)
        registered_paths = [line[9:] for line in registered.stdout.splitlines()
                            if line.startswith("worktree ")]
        _must(registered.returncode == 0 and any(Path(p).resolve() == path.resolve()
              for p in registered_paths), "Git registration missing or moved")
        latest_processes = gc.proc_cwd_map([path])
        _must(latest_processes is not None, "process scan unavailable")
        exact = str(path.resolve())
        _must(not any(_inside(Path(cwd).resolve(), Path(exact))
                      for cwd in latest_processes), "process using worktree")
        ps = _cmd("ps", "-axo", "command", timeout=12)
        _must(ps.returncode == 0 and str(path) not in ps.stdout,
              "process command may reference worktree")
        status = _cmd("git", "--no-optional-locks", "-C", str(path),
                      "status", "--porcelain=v1", "--untracked-files=all", timeout=60)
        _must(status.returncode == 0 and not status.stdout.strip(), "dirty/untracked files")
        ignored = _cmd("git", "--no-optional-locks", "-C", str(path), "status",
                       "--porcelain=v1", "--ignored=matching", "--untracked-files=normal", timeout=60)
        _must(ignored.returncode == 0 and not ignored.stdout.strip(),
              "ignored files preserved (no forced deletion)")
        refreshed = gc.Worktree(path=path, branch=w.branch, head=w.head)
        gc.classify(refreshed, primary, cfg, latest_processes, pr_states,
                    fetch_ok, Path.cwd(), __import__("time").time(), protected=protected)
        _must(refreshed.verdict in gc.SAFE_VERDICTS and refreshed.proof,
              "positive proof no longer holds")
        # Receipt + lock handling are a single operation. No second carrier or blind retry.
        journal("BEGIN_REMOVE", path, w.head)
        if lock_path.exists():
            unlock = _cmd("git", "-C", str(primary), "worktree", "unlock", str(path), timeout=45)
            if unlock.returncode != 0:
                journal("EFFECT_UNKNOWN", path, "unlock refused or ambiguous")
                return skip("Git unlock unresolved")
            mutated = True
        remove = _cmd("git", "-C", str(primary), "worktree", "remove", str(path), timeout=160)
        if remove.returncode != 0:
            if mutated:
                restore = _cmd("git", "-C", str(primary), "worktree", "lock", "--reason",
                               HELPER_LOCK, str(path), timeout=50)
                if restore.returncode != 0 or not lock_path.exists():
                    journal("EFFECT_UNKNOWN", path, "could not restore helper lock")
                    return skip("Git removal and relock unresolved")
            journal("VERIFIED_RELOCKED" if mutated else "EFFECT_NONE", path,
                    "non-force Git removal refused: " + remove.stderr[:180])
            return skip("Git non-force removal refused")
        if path.exists():
            journal("EFFECT_UNKNOWN", path, "Git returned success but path remains")
            return skip("Git removal effect unknown")
        branch_after = _cmd("git", "--git-dir=" + str(common), "rev-parse",
                            "--verify", "refs/heads/" + w.branch, timeout=25)
        if branch_after.returncode != 0 or branch_after.stdout.strip() != w.head:
            journal("EFFECT_UNKNOWN", path, "branch ref not preserved")
            return skip("branch preservation unknown")
        journal("VERIFIED_REMOVED", path, w.head)
        act["remove_rc"] = 0
        act["branch_preserved"] = True
        return act
    except subprocess.TimeoutExpired as exc:
        if mutated:
            journal("EFFECT_UNKNOWN", path, "timeout after Git metadata change: " + str(exc)[:180])
        return skip("timeout; effect must be reconciled" if mutated else "preflight timeout")
    except (OSError, ValueError, RuntimeError) as exc:
        if mutated:
            journal("EFFECT_UNKNOWN", path, "exception after Git metadata change: " + str(exc)[:180])
        return skip("preflight refused: " + str(exc)[:180])
