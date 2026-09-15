"""Commit and push the two debt-maturity-drip output paths to main.

The drip workflow writes data/debt_maturity/cache/** and
data/edgar/statements.parquet on the runner. Neither was previously carried
forward to origin/main, because the nightly engine job lives on a separate
runner registration with its own ``actions/checkout`` (``clean: true`` by
default) that wiped the untracked cache before any commit step could see it.
This helper closes that gap by making the drip job its OWN bounded committer
of those two paths.

Design constraints (R3, packet W8B_F09_11):

* stdlib only — the drip venv installs requirements.txt and pytest, but this
  module must remain runnable in any Python 3.12 environment without a
  third-party import (so it works under both the drip workflow and pytest).
* Exactly two output paths are staged. Never an unfiltered add, never
  a directory-wide add — a third-party write that touched the tree between
  the drip step and this helper MUST remain unstaged and uncommitted.
* A non-fast-forward rejection is normal (origin/main moves every few minutes
  under ``[skip ci]`` data commits); a single-shot "refuse when main moved"
  rule would therefore NEVER land. We retry without rewriting local history
  by snapshotting the two paths into a temp directory, fetching the remote
  tip, resetting hard onto it, then restoring the two paths and re-staging.
* Every refusal path exits 0 — the drip is fail-soft (cache goes stale, not
  wrong). Non-zero returns are reserved for "this is not a git worktree".
* Every GitHub annotation is a bare ``print(... flush=True)`` starting the
  line, so GitHub Actions parses it (CI-guarded by
  tests/test_gh_annotation_line_start.py; logger-based messages like
  ``log.warning("::warning ...")`` are silently dropped).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


# The two paths this helper is permitted to stage and commit. Any other change
# in the working tree MUST remain unstaged and uncommitted — see R3(a)/STAGE.
ALLOWED_PATHS = ("data/debt_maturity/cache", "data/edgar/statements.parquet")

# Bound the staged payload so a runaway writer cannot push hundreds of MB
# (a fetch-time cache under data/debt_maturity/cache/ is ~1-10 KB per ticker).
DEFAULT_MAX_MB = 48

# Origin/main moves every few minutes under [skip ci] data commits, so a
# single-shot push regularly sees a non-fast-forward. Three attempts is enough
# to win the race on a quiet night and stays small enough to fail fast on a
# genuinely busy one.
DEFAULT_ATTEMPTS = 3

# The nightly's bot identity (daily.yml:626-627 — same repo, same workflow
# family). Re-using it keeps the commit graph attributable to one actor.
BOT_NAME = "dashboard-bot"
BOT_EMAIL = "actions@users.noreply.github.com"


def _run(args: list[str], *, cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    """Thin subprocess wrapper. ``check=False`` by default — every failure
    path here is a refused-but-not-fatal exit-0 outcome, so the caller decides
    when to raise. ``stdout``/``stderr`` are captured so an Actions step's
    output stays readable."""
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _notice(title: str, message: str) -> None:
    """Bare ``print`` at line start so GitHub Actions parses the annotation.
    ``flush=True`` is load-bearing (stdout is block-buffered when piped)."""
    print(f"::notice title={title}::{message}", flush=True)


def _warning(title: str, message: str) -> None:
    """Bare ``print`` at line start — the ``::warning`` channel."""
    print(f"::warning title={title}::{message}", flush=True)


def _commit_subject() -> str:
    """``[skip ci]`` keeps the commit out of the merge-gate's path — a fetch
    artifact's rediscovery is not a behavior change worth gating a merge."""
    return f"debt-maturity-drip: persist cache + statements {datetime.now(timezone.utc).isoformat()} [skip ci]"


def _is_git_worktree(cwd: Path) -> bool:
    proc = _run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _existing_allowed_paths(cwd: Path) -> list[str]:
    """Filter ALLOWED_PATHS down to those that exist in the working tree.
    A path that was never written by the drip step has no business being
    staged and committed."""
    return [p for p in ALLOWED_PATHS if (cwd / p).exists()]


def _staged_files(cwd: Path) -> list[str]:
    """Return paths currently staged for commit. ``-z`` keeps filenames with
    spaces / unicode intact; ``--name-only`` is enough — we never read the
    diff body in this helper."""
    proc = _run(["git", "diff", "--cached", "--name-only", "-z"], cwd=cwd)
    if proc.returncode != 0:
        return []
    out = []
    for chunk in proc.stdout.split("\0"):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def _diff_is_empty(cwd: Path) -> bool:
    """``git diff --cached --quiet`` exits 0 when the index matches HEAD."""
    return _run(["git", "diff", "--cached", "--quiet"], cwd=cwd).returncode == 0


def _staged_blob_size_bytes(cwd: Path) -> int:
    """Sum of staged blob sizes via ``git cat-file -s :<path>``. Faster than
    stat'ing the working-tree files because it ignores anything outside the
    index (an off-tree writer cannot inflate the metric)."""
    total = 0
    for path in _staged_files(cwd):
        proc = _run(["git", "cat-file", "-s", f":{path}"], cwd=cwd)
        if proc.returncode == 0:
            try:
                total += int(proc.stdout.strip())
            except ValueError:
                pass
    return total


def _copy_allowed_paths_to(cwd: Path, dst_root: Path) -> dict[str, str]:
    """Snapshot the two allowed paths to a temp dir. Returns a mapping
    ``relative_path -> absolute_under_dst_root`` suitable for restoring after
    a ``git reset --hard`` wiped the working tree. Only copies files that
    actually exist; the caller treats absence as "no change"."""
    mapping: dict[str, str] = {}
    for rel in ALLOWED_PATHS:
        src = cwd / rel
        if not src.exists():
            continue
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        mapping[rel] = str(dst)
    return mapping


def _restore_allowed_paths(cwd: Path, dst_root: Path, mapping: dict[str, str]) -> None:
    """Reverse of ``_copy_allowed_paths_to`` — back into the working tree
    after a reset."""
    for rel, abs_under_dst in mapping.items():
        src = Path(abs_under_dst)
        dst = cwd / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            # Remove the destination first so copytree does not collide on an
            # existing directory that the previous reset left behind.
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def _commit(cwd: Path, subject: str) -> bool:
    proc = _run(
        [
            "git",
            "-c", f"user.name={BOT_NAME}",
            "-c", f"user.email={BOT_EMAIL}",
            "commit", "-q", "-m", subject,
        ],
        cwd=cwd,
        check=False,
    )
    return proc.returncode == 0


def _pushed_sha(cwd: Path, base: str, remote: str) -> str | None:
    """Return the SHA ``origin/<base>`` points at after the push, or None if
    the push did not advance the remote tip."""
    proc = _run(["git", "rev-parse", f"{remote}/{base}"], cwd=cwd)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _attempt_push(cwd: Path, base: str, remote: str) -> bool:
    """Single attempt: ``git push <remote> HEAD:refs/heads/<base>``. Never a
    force-push, never a history rewrite, never a stash apply — the helper
    is a no-history-rewrite re-checkout cycle, never a force-push path."""
    proc = _run(
        ["git", "push", remote, f"HEAD:refs/heads/{base}"],
        cwd=cwd,
        check=False,
    )
    return proc.returncode == 0


def _resync_to_remote(cwd: Path, base: str, remote: str) -> dict[str, str]:
    """Snapshot -> fetch -> reset hard -> restore. Returns the snapshot
    mapping so the caller can restore it after the reset and re-stage."""
    with tempfile.TemporaryDirectory(prefix="dm-drip-") as tmp:
        tmp_root = Path(tmp)
        snapshot = _copy_allowed_paths_to(cwd, tmp_root)
        _run(["git", "fetch", "-q", "--depth", "1", remote, base], cwd=cwd)
        _run(["git", "reset", "-q", "--hard", "FETCH_HEAD"], cwd=cwd)
        _restore_allowed_paths(cwd, tmp_root, snapshot)
        return snapshot


def main(argv: list[str] | None = None) -> int:
    """GATE -> STAGE -> EMPTY -> CEILING -> COMMIT -> PUSH(retry).

    Exit codes: 0 on every success-or-refusal outcome (the drip is fail-soft).
    Non-zero ONLY when the cwd is not a git worktree — that is a hard error
    before any state is touched."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="path to the git worktree (default: cwd)")
    ap.add_argument("--base", default="main", help="base branch to push to (default: main)")
    ap.add_argument("--remote", default="origin", help="remote name (default: origin)")
    ap.add_argument("--max-mb", type=int, default=DEFAULT_MAX_MB,
                    help=f"ceiling on staged payload in MiB (default: {DEFAULT_MAX_MB})")
    ap.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS,
                    help=f"max push attempts before giving up (default: {DEFAULT_ATTEMPTS})")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the gate/stage/empty/ceiling checks but do not commit or push")
    args = ap.parse_args(argv)

    cwd = Path(args.repo).resolve()
    if not _is_git_worktree(cwd):
        print(f"debt_maturity_drip_push: {cwd} is not a git worktree", file=sys.stderr)
        return 2

    # GATE — the kill switch is an env var, not a CLI flag, so a CI operator
    # can disable the push without re-cutting the workflow run.
    if os.environ.get("DEBT_MATURITY_DRIP_PUSH", "0") != "1":
        _notice(
            "debt-maturity-drip",
            "push disabled (DEBT_MATURITY_DRIP_PUSH != 1); nothing committed",
        )
        return 0

    # STAGE — never an unfiltered add, never a directory-wide add. A modify outside
    # ALLOWED_PATHS must remain unstaged.
    existing = _existing_allowed_paths(cwd)
    for rel in existing:
        # ``-- <path>`` is the safe add — it stages that one path even when it
        # is matched by .gitignore rules (the cache dir is intentionally not
        # gitignored; this preserves the option of gitignoring it later).
        _run(["git", "add", "--", rel], cwd=cwd)

    # EMPTY — no-op when the drip step produced no outputs (e.g. every ticker
    # within REFRESH_DAYS so nothing to refresh, or a workflow_dispatch with a
    # zero max_new).
    if _diff_is_empty(cwd):
        _notice("debt-maturity-drip", "no changes to persist")
        return 0

    # CEILING — refuse oversized payloads. A 1.0 MiB file under --max-mb 1
    # must reset the staged diff so the next run starts clean.
    staged_bytes = _staged_blob_size_bytes(cwd)
    staged_mib = staged_bytes / (1024 * 1024)
    if staged_mib > args.max_mb:
        _run(["git", "reset", "-q"], cwd=cwd)
        _warning(
            "debt-maturity-drip",
            f"refused: staged payload {staged_mib:.1f} MiB exceeds ceiling {args.max_mb} MiB; nothing committed",
        )
        return 0

    if args.dry_run:
        _notice(
            "debt-maturity-drip",
            f"dry-run: would commit {len(_staged_files(cwd))} files ({staged_mib:.1f} MiB)",
        )
        return 0

    # COMMIT
    subject = _commit_subject()
    if not _commit(cwd, subject):
        # A commit failing outside the non-fast-forward path is unexpected —
        # the index is dirty AND we cannot commit it. Reset and refuse.
        _run(["git", "reset", "-q"], cwd=cwd)
        _warning("debt-maturity-drip", "commit refused; nothing pushed")
        return 0

    # PUSH — origin/main moves every few minutes under [skip ci] data commits,
    # so a single-shot push regularly sees a non-fast-forward; retry the
    # snapshot-fetch-reset-restore cycle up to --attempts times.
    for attempt in range(1, max(args.attempts, 0) + 1):
        if _attempt_push(cwd, args.base, args.remote):
            sha = _pushed_sha(cwd, args.base, args.remote) or "<unknown>"
            staged = len(_staged_files(cwd))
            _notice(
                "debt-maturity-drip",
                f"pushed {sha} to {args.base}: {staged} files, {staged_mib:.1f} MiB",
            )
            return 0
        if attempt >= max(args.attempts, 0):
            break
        # Re-checkout cycle, then the loop re-runs EMPTY/CEILING/COMMIT/PUSH
        # against the refreshed tree.
        try:
            _resync_to_remote(cwd, args.base, args.remote)
        except Exception as exc:  # pragma: no cover — defensive guard around shutil
            _warning("debt-maturity-drip", f"re-checkout failed: {exc!r}")
            break
        # Re-stage the two allowed paths after the reset restored them.
        existing = _existing_allowed_paths(cwd)
        for rel in existing:
            _run(["git", "add", "--", rel], cwd=cwd)
        if _diff_is_empty(cwd):
            _notice("debt-maturity-drip", "no changes to persist after re-checkout")
            return 0
        staged_bytes = _staged_blob_size_bytes(cwd)
        staged_mib = staged_bytes / (1024 * 1024)
        if staged_mib > args.max_mb:
            _run(["git", "reset", "-q"], cwd=cwd)
            _warning(
                "debt-maturity-drip",
                f"refused on attempt {attempt + 1}: staged payload {staged_mib:.1f} MiB exceeds ceiling {args.max_mb} MiB; nothing committed",
            )
            return 0
        if not _commit(cwd, subject):
            _run(["git", "reset", "-q"], cwd=cwd)
            _warning("debt-maturity-drip", f"commit refused on attempt {attempt + 1}; nothing pushed")
            return 0

    _warning(
        "debt-maturity-drip",
        f"refused: {args.base} moved under {args.attempts} attempts; nothing pushed (cache goes stale, not wrong)",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
