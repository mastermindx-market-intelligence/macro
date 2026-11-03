#!/usr/bin/env python3
"""Bounded pytest garbage reclamation for the existing Ubuntu storage sentinel.

No Git worktree, regular pytest-N generation, cold storage, or session scratch
is in this deletion scope. Default is read-only; callers explicitly arm a
single foreground sweep only under the incumbent disk-pressure guard.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import time
import uuid

NAME = re.compile(r"garbage-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\Z")
USER = re.compile(r"[a-z_][a-z0-9_-]{0,30}\Z")
SCHEMA = "mastermind.ubuntu_pytest_garbage_reclaim.v1"
DEFAULT_RECEIPT = "/var/lib/mastermind-storage-guard/pytest-garbage-ledger.jsonl"


class Refusal(RuntimeError):
    """Uncertain ownership or safety evidence: no deletion is permitted."""


def _path_in(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _base(username: str, tmp_root: str = "/tmp") -> tuple[Path, int, int]:
    if USER.fullmatch(username) is None:
        raise Refusal("invalid_username")
    root = Path(tmp_root)
    parent = root.lstat()
    if not stat.S_ISDIR(parent.st_mode) or root.is_symlink():
        raise Refusal("tmp_root_not_real_directory")
    base = root / ("pytest-of-" + username)
    try:
        owner = pwd.getpwnam(username).pw_uid
        s = base.lstat()
    except (KeyError, OSError) as exc:
        raise Refusal("pytest_base_unavailable") from exc
    if (
        not stat.S_ISDIR(s.st_mode)
        or stat.S_ISLNK(s.st_mode)
        or s.st_uid != owner
        or s.st_dev != parent.st_dev
        or s.st_mode & 0o077
    ):
        raise Refusal("pytest_base_untrusted")
    return base, owner, s.st_dev


def _candidates(base: Path, owner: int, device: int, age_hours: int) -> list[Path]:
    now = time.time()
    current = base / "pytest-current"
    protected = os.path.realpath(current) if current.is_symlink() else None
    out = []
    for e in os.scandir(base):
        if NAME.fullmatch(e.name) is None:
            continue
        s = e.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(s.st_mode)
            or s.st_uid != owner
            or s.st_dev != device
            or s.st_mode & 0o077
            or now - s.st_mtime < age_hours * 3600
            or e.path == protected
        ):
            continue
        out.append(Path(e.path))
    return sorted(out)


def _check_mounts(paths: list[Path], mountinfo: str = "/proc/self/mountinfo") -> None:
    with open(mountinfo, encoding="utf-8", errors="replace") as stream:
        for line in stream:
            words = line.split()
            if len(words) < 5:
                raise Refusal("mountinfo_unreadable")
            mount = words[4].replace(r"\040", " ").replace(r"\011", "\t")
            if any(_path_in(mount, str(p)) for p in paths):
                raise Refusal("mounted_subtree_present")


def _check_procs(paths: list[Path], proc_root: str = "/proc") -> None:
    roots = tuple(str(p) for p in paths)
    if not roots:
        return
    for ent in list(os.scandir(proc_root)):
        if not ent.name.isdigit():
            continue
        proc = ent.path
        try:
            links = ("cwd", "root", "exe")
            for kind in links:
                try:
                    value = os.readlink(os.path.join(proc, kind)).removesuffix(" (deleted)")
                except FileNotFoundError:
                    continue
                except PermissionError as exc:
                    raise Refusal("process_link_unreadable") from exc
                if any(_path_in(value, p) for p in roots):
                    raise Refusal("live_process_reference")
            try:
                with os.scandir(os.path.join(proc, "fd")) as fds:
                    for fd in fds:
                        try:
                            value = os.readlink(fd.path).removesuffix(" (deleted)")
                        except FileNotFoundError:
                            continue
                        except PermissionError as exc:
                            raise Refusal("process_fd_unreadable") from exc
                        if any(_path_in(value, p) for p in roots):
                            raise Refusal("live_open_file")
            except FileNotFoundError:
                continue
            except PermissionError as exc:
                raise Refusal("process_fd_inventory_unreadable") from exc
        except FileNotFoundError:
            continue


def _check_registrations(paths: list[Path], username: str) -> None:
    """Consult existing donor registries; unknown donor inventory fails closed."""
    home = Path(pwd.getpwnam(username).pw_dir)
    parents = [home / "lanes" / "repos", home / "Documents" / "GitHub"]
    donor_roots = []
    for parent in parents:
        if not parent.exists():
            continue
        if parent.is_symlink() or not parent.is_dir():
            raise Refusal("donor_parent_untrusted")
        for candidate in parent.iterdir():
            if candidate.is_symlink():
                continue
            if candidate.is_dir() and (candidate / ".git").exists():
                donor_roots.append(candidate)
    if not donor_roots or len(donor_roots) > 40:
        raise Refusal("donor_inventory_unqualified")
    for root in donor_roots:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "worktree", "list", "--porcelain"],
                capture_output=True, text=True, timeout=12, check=False,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal("donor_registry_unavailable") from exc
        if result.returncode != 0:
            raise Refusal("donor_registry_unreadable")
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                worktree = line[len("worktree "):]
                if any(_path_in(worktree, str(p)) for p in paths):
                    raise Refusal("registered_worktree_in_candidate")


def _hold_unreconciled(base: Path, receipt: Path) -> None:
    """Never silently start another sweep after a crashed or partial deletion."""
    with os.scandir(base) as entries:
        if any(e.name.startswith(".reclaim-") for e in entries):
            raise Refusal("quarantined_previous_effect_requires_reconciliation")
    try:
        with open(receipt, "rb") as stream:
            stream.seek(0, os.SEEK_END)
            total = stream.tell()
            stream.seek(max(0, total - 32768))
            lines = stream.read().splitlines()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise Refusal("ledger_read_unavailable") from exc
    if not lines:
        raise Refusal("ledger_empty_untrusted")
    try:
        last = json.loads(lines[-1])
    except (ValueError, TypeError) as exc:
        raise Refusal("ledger_unreadable") from exc
    if last.get("schema") != SCHEMA or last.get("event") != "complete":
        raise Refusal("previous_reclaim_not_terminal")


def _receipt(path: Path, event: dict) -> None:
    parent = path.parent
    s = parent.lstat()
    if not stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode) or s.st_uid != 0 or s.st_mode & 0o077:
        raise Refusal("ledger_directory_untrusted")
    flags = os.O_APPEND | os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise Refusal("ledger_file_untrusted")
        payload = (json.dumps({"schema": SCHEMA, "epoch": time.time(), **event}, sort_keys=True) + "\n").encode()
        if os.write(fd, payload) != len(payload):
            raise Refusal("ledger_short_write")
        os.fsync(fd)
    finally:
        os.close(fd)


def reclaim(
    username: str,
    *,
    apply: bool = False,
    min_age_hours: int = 24,
    max_dirs: int = 6,
    tmp_root: str = "/tmp",
    receipt: str = DEFAULT_RECEIPT,
) -> dict:
    if min_age_hours < 24 or not 1 <= max_dirs <= 12:
        raise Refusal("invalid_reclamation_bounds")
    base, owner, device = _base(username, tmp_root)
    selected = _candidates(base, owner, device, min_age_hours)[:max_dirs]
    result = {"candidate_count": len(selected), "deleted": 0,
              "scope": "pytest-generated-garbage-only", "applied": False,
              "source_delete_enabled": False}
    if not selected or not apply:
        return result
    if os.geteuid() != 0 or tmp_root != "/tmp":
        raise Refusal("requires_root_and_canonical_tmp")
    ledger = Path(receipt)
    _hold_unreconciled(base, ledger)
    _check_mounts(selected)
    _check_procs(selected)
    _check_registrations(selected, username)
    root = base.lstat()
    if root.st_uid != owner or root.st_dev != device:
        raise Refusal("base_changed")
    operation = uuid.uuid4().hex
    _receipt(ledger, {"event": "begin", "operation": operation,
                      "username": username, "candidates": len(selected)})
    for original in selected:
        # Recheck the exact source leaf before an atomic same-filesystem move.
        st = original.lstat()
        if (
            not stat.S_ISDIR(st.st_mode) or st.st_uid != owner or
            st.st_dev != device or st.st_mode & 0o077 or
            time.time() - st.st_mtime < min_age_hours * 3600
        ):
            raise Refusal("candidate_changed")
        _check_procs([original])
        quarantine = base / (".reclaim-" + operation + "-" + original.name)
        if quarantine.exists() or quarantine.is_symlink():
            raise Refusal("quarantine_collision")
        os.rename(original, quarantine)
        if quarantine.lstat().st_ino != st.st_ino:
            raise Refusal("rename_inode_mismatch_held")
        _receipt(ledger, {"event": "moved", "operation": operation,
                          "name": original.name})
        try:
            call = subprocess.run(["/usr/bin/rm", "-rf", "--one-file-system",
                                   "--", str(quarantine)],
                                  capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal("delete_effect_unknown_held") from exc
        if call.returncode != 0 or quarantine.exists():
            raise Refusal("delete_partial_held")
        result["deleted"] += 1
        _receipt(ledger, {"event": "deleted", "operation": operation,
                          "name": original.name})
    result["applied"] = True
    _receipt(ledger, {"event": "complete", "operation": operation,
                      "deleted": result["deleted"]})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--min-age-hours", type=int, default=24)
    parser.add_argument("--max-dirs", type=int, default=6)
    args = parser.parse_args(argv)
    try:
        answer = reclaim(args.username, apply=args.apply,
                         min_age_hours=args.min_age_hours, max_dirs=args.max_dirs)
        print(json.dumps(answer, sort_keys=True))
        return 0
    except (Refusal, OSError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
