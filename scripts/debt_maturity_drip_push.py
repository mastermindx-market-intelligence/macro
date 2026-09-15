"""Persist the debt-maturity drip's two output paths back to ``main`` (W8B F09-11).

Context (META-CEO FROZEN SPEC, R1/R2):
  ``.github/workflows/debt-maturity-drip.yml`` already populates the bounded
  per-issuer cache under ``data/debt_maturity/cache/`` and refreshes the
  ``data/edgar/statements.parquet`` PIT-gate snapshot, but the old comment
  block claimed ``daily.yml``'s engine job would carry those writes via a
  broad workspace sweep on the SAME runner. That premise was false:
  ``actions/checkout@v4`` defaults to ``clean: true`` so any subsequent
  checkout on the same registration deletes untracked writes, and the
  ``macstudio`` runner label spans several registrations (each with its
  own ``_work``) so the drip and the engine job rarely share a tree, and
  nothing on the nightly path calls ``collectors.edgar_facts``,
  ``backfill_edgar_flow`` or ``build_debt_maturity`` -- so nothing writes
  the cache from there. This helper is the fix: the drip job is its own
  committer for exactly its two output paths.

R2 (typed artifact, not a forward ledger): both paths are re-derivable
fetch-time caches (per-CIK JSON with ``fetched_at``; parquet with ``as_of``)
with no forward-only accrual semantics, so the nightly-sole-advancer law
does not gate them. The helper commits and pushes ONLY the two paths
below and never touches anything else.

The gate env ``DEBT_MATURITY_DRIP_PUSH`` must equal exactly ``"1"`` for
any work to happen; otherwise the helper exits 0 with a single
``::notice`` line and no commit. That input is the workflow_dispatch
kill switch.

Return codes:
  0  -- success OR a lawful refusal path (gate off, empty diff, ceiling
         exceeded, attempts exhausted on a moving base). All refusal
         paths leave the local index clean and exit 0 so the drip stays
         fail-soft: cache goes stale, never wrong.
  non-zero -- only when the cwd is not a git worktree (infrastructure
              failure: nothing to do, fail loud).

Stdlib only so the helper runs under the drip venv AND under pytest with
no extra install.
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

# The two paths the drip job is allowed to commit. Anything outside this
# tuple must remain unstaged (a modified file under ``engine/`` or
# ``site/`` is NEVER carried by this helper).
ALLOWED_PATHS: tuple[str, ...] = (
    "data/debt_maturity/cache",
    "data/edgar/statements.parquet",
)

# Default payload ceiling in MiB. ``data/edgar/statements.parquet`` is
# currently ~6 MiB and the cache grows at the rate of new tickers; 48 MiB
# is the seat-capped maximum a single drip commit may add before the
# helper refuses outright.
DEFAULT_MAX_MB: int = 48

# Default number of non-fast-forward re-checkout attempts when
# origin/<base> has moved under us between the staging and the push.
# ``data/`` pushes run at ~1/min under [skip ci] so a single-shot
# "refuse when main moved" would never land.
DEFAULT_ATTEMPTS: int = 3

# Identity for the synthetic commit the drip author leaves on main.
# Matches the nightly's identity so a reader grepping the audit trail
# sees one bot across every artifact push.
BOT_NAME: str = "dashboard-bot"
BOT_EMAIL: str = "actions@users.noreply.github.com"

# Subject prefix; the trailing ``[skip ci]`` is mandatory because this
# helper pushes to main and we do NOT want a PR-proof dispatch every
# night for an artifact push.
COMMIT_SUBJECT_PREFIX: str = "debt-maturity-drip: persist cache + statements"


def _run(
    args: list[str],
    *,
    cwd: Path,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Subprocess wrapper that captures stdout/stderr as text.

    ``check=False`` because every command here is a probe; the caller
    inspects ``returncode`` and ``stdout`` to decide what to do.
    """
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
        env=env,
    )


def _emit(kind: str, title: str, message: str) -> None:
    """Print a GitHub workflow command at the START of the line.

    Per ``tests/test_gh_annotation_line_start.py``, GitHub only parses a
    workflow command when ``::`` is the first thing on the line. Logging
    frameworks prefix with ``WARNING `` / ``NOTICE ``, which silently
    drops the annotation; the only safe form is a bare ``print`` with
    ``flush=True`` so a block-buffered CI stdout does not eat it before
    the workflow step concludes.
    """
    print(f"::{kind} title={title}::{message}", flush=True)


def _is_git_worktree(cwd: Path) -> bool:
    """Probe the cwd is inside a git worktree.

    Refusal path requires this to return True or the helper exits
    non-zero (infrastructure failure: nothing to do, fail loud). A bare
    gitdir is not a worktree, but the drip always runs from a self-hosted
    runner checkout so this is a guard against a future caller
    misconfiguring ``--repo``.
    """
    result = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return result.returncode == 0 and result.stdout.strip() == "true"


def _ensure_clean_index(cwd: Path) -> None:
    """Drop any partial staging so the helper cannot commit artifacts a
    previous step left behind. The drip step itself only ``tee``s logs
    and runs the bounded universe pass, so this is belt-and-braces --
    but if a future step ever forgets, the helper's contract is "the
    only thing I commit is what I staged via ``ALLOWED_PATHS``", and
    this guarantees that.
    """
    _run(["git", "reset", "-q"], cwd=cwd)


def _stage_allowed(cwd: Path) -> list[str]:
    """Run ``git add -- <path>`` for each ALLOWED_PATH that exists on
    disk. A non-selective staging invocation (one that lists the parent
    directory instead of explicit paths) would silently carry any other
    write under ``data/``; the spec forbids it and ``tests`` will refuse
    the helper if it appears in source.
    """
    staged: list[str] = []
    for rel in ALLOWED_PATHS:
        if not (cwd / rel).exists():
            continue
        _run(["git", "add", "--", rel], cwd=cwd, check=True)
        staged.append(rel)
    return staged


def _staged_diff_is_empty(cwd: Path) -> bool:
    """Return True iff the index matches HEAD (no work to commit).

    ``git diff --cached --quiet`` exits 0 on an empty diff and 1 on any
    staged change, so the helper uses the explicit return code rather
    than parsing stdout.
    """
    return _run(["git", "diff", "--cached", "--quiet"], cwd=cwd).returncode == 0


def _staged_paths(cwd: Path) -> list[str]:
    """Return the list of staged paths as NUL-separated strings.

    NUL-separated so a path containing a newline or a literal ``"`` is
    round-trip-safe; the helper splits on NUL itself rather than asking
    git to do it.
    """
    result = _run(["git", "diff", "--cached", "--name-only", "-z"], cwd=cwd)
    if not result.stdout:
        return []
    return [p for p in result.stdout.split("\x00") if p]


def _staged_blob_size(path: str, cwd: Path) -> int:
    """Size of the staged blob for ``path`` in bytes.

    Uses the colon-prefix form so the size is read off the staged
    object, not the working tree -- a previously committed file that
    was unchanged by this run must not pay the cost, and a fresh cache
    entry that lives only in the working tree must.
    """
    result = _run(["git", "cat-file", "-s", f":{path}"], cwd=cwd)
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def _current_head(cwd: Path) -> str:
    """Resolve the local HEAD sha as a defensive probe."""
    return _run(["git", "rev-parse", "HEAD"], cwd=cwd).stdout.strip()


def _attempt_push(cwd: Path, remote: str, base: str) -> tuple[bool, str]:
    """Single push attempt. Returns ``(ok, message)``.

    ``ok=False`` may mean a non-fast-forward (origin moved), an auth
    failure, or a ruleset rejection (GH013). The caller decides whether
    to retry; this function never raises.
    """
    result = _run(
        ["git", "push", remote, f"HEAD:refs/heads/{base}"],
        cwd=cwd,
    )
    if result.returncode == 0:
        return True, (result.stdout + result.stderr).strip()
    return False, (result.stderr or result.stdout).strip()


def _recheck(cwd: Path, remote: str, base: str, snapshot: Path) -> bool:
    """Non-fast-forward re-checkout cycle when origin/<base> moved.

    Copies the two paths to a temp dir BEFORE the reset (so the new
    tree's working copy is empty for them, and ``git reset --hard``
    FETCH_HEAD does not delete the staged change), then restores them
    from the snapshot, re-stages via ``ALLOWED_PATHS``, and returns
    True iff the index is non-empty AND within the ceiling. The caller
    re-runs the EMPTY/CEILING gate after this returns.

    Per the spec, this NEVER force-pushes, NEVER uses a stash, NEVER
    rewrites history, and NEVER takes one side of a whole file from
    the remote: an artifact push that moves forward by dropping a path
    would silently destroy data.
    """
    try:
        fetch = _run(["git", "fetch", "-q", "--depth", "1", remote, base], cwd=cwd)
        if fetch.returncode != 0:
            return False
        reset = _run(["git", "reset", "-q", "--hard", "FETCH_HEAD"], cwd=cwd)
        if reset.returncode != 0:
            return False
        for rel in ALLOWED_PATHS:
            src = snapshot / rel
            if src.is_file():
                dst = cwd / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            elif src.is_dir():
                dst = cwd / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
        _ensure_clean_index(cwd)
        _stage_allowed(cwd)
    finally:
        shutil.rmtree(snapshot, ignore_errors=True)
    return True


def _snapshot_allowed(cwd: Path) -> Path:
    """Copy the two output paths out of the worktree before a re-checkout.

    The helper needs the bytes to survive a ``git reset --hard
    FETCH_HEAD`` -- FETCH_HEAD is the remote's tip and has no notion
    of the drip's pending writes -- and the cheapest way to keep them
    across that boundary is a temp-dir copy. The helper cleans the
    snapshot on success and on the re-checkout path; on the happy path
    where no re-checkout was needed the snapshot is also torn down.

    ``data/debt_maturity/cache`` is a DIRECTORY tree (one JSON per CIK),
    not a single file, so the snapshot walk has to mirror the whole
    tree -- ``is_file()`` alone would silently copy nothing for that
    path. ``data/edgar/statements.parquet`` is a single file.
    """
    snap = Path(tempfile.mkdtemp(prefix="debt_maturity_drip_push_"))
    for rel in ALLOWED_PATHS:
        src = cwd / rel
        if src.is_file():
            dst = snap / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        elif src.is_dir():
            dst = snap / rel
            # copy the whole tree so per-CIK JSONs survive
            shutil.copytree(src, dst, dirs_exist_ok=True)
    return snap


def _commit(cwd: Path, subject: str) -> str:
    """Make the single allowed commit and return its sha."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = BOT_NAME
    env["GIT_AUTHOR_EMAIL"] = BOT_EMAIL
    env["GIT_COMMITTER_NAME"] = BOT_NAME
    env["GIT_COMMITTER_EMAIL"] = BOT_EMAIL
    result = _run(
        ["git", "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
         "commit", "-q", "-m", subject],
        cwd=cwd,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git commit failed: rc={result.returncode} "
            f"stderr={result.stderr.strip()}"
        )
    return _current_head(cwd)


def main(argv: list[str] | None = None) -> int:
    """The single public entry point.

    Order is fixed by the spec and pinned by the unit tests:
      GATE -> STAGE -> EMPTY -> CEILING -> COMMIT -> PUSH (retry).
    Every refusal path exits 0 (the drip is fail-soft) and emits the
    annotation at the START of the line.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.debt_maturity_drip_push",
        description=(
            "Persist the debt-maturity drip's two output paths back to "
            "the base branch. See module docstring for the W8B F09-11 "
            "context."
        ),
    )
    parser.add_argument(
        "--repo", default=".", help="Path to the git worktree (default: cwd).",
    )
    parser.add_argument(
        "--base", default="main", help="Branch to push to (default: main).",
    )
    parser.add_argument(
        "--remote", default="origin", help="Git remote (default: origin).",
    )
    parser.add_argument(
        "--max-mb", type=int, default=DEFAULT_MAX_MB,
        help=f"Refuse if staged payload exceeds this MiB (default: {DEFAULT_MAX_MB}).",
    )
    parser.add_argument(
        "--attempts", type=int, default=DEFAULT_ATTEMPTS,
        help=f"Rebase-free re-checkout attempts on origin moving "
             f"(default: {DEFAULT_ATTEMPTS}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Walk the gate through EMPTY/CEILING and print what would happen.",
    )
    args = parser.parse_args(argv)
    cwd = Path(args.repo).resolve()

    # GATE -- the kill switch. The drip workflow passes the
    # workflow_dispatch ``push`` input through this env var so an
    # operator can land an empty drip run without a push. Default is
    # ``"1"`` so the schedule path always pushes; the dispatch path can
    # pass ``push=0`` to disable.
    if os.environ.get("DEBT_MATURITY_DRIP_PUSH") != "1":
        _emit(
            "notice", "debt-maturity-drip",
            "push disabled (DEBT_MATURITY_DRIP_PUSH != 1); nothing committed",
        )
        return 0

    if not _is_git_worktree(cwd):
        _emit(
            "error", "debt-maturity-drip",
            f"cwd {cwd} is not a git worktree; refusing to push",
        )
        return 1

    _ensure_clean_index(cwd)
    staged = _stage_allowed(cwd)

    # EMPTY -- nothing on the runner changed. The drip is a no-op when
    # the bounded universe pass refreshed zero tickers, and the helper
    # must NOT mint an empty commit.
    if _staged_diff_is_empty(cwd):
        _emit(
            "notice", "debt-maturity-drip",
            "no changes to persist",
        )
        return 0

    # CEILING -- sum the staged blob sizes and refuse if they exceed
    # ``--max-mb`` MiB. The stage is reset on refusal so the next
    # attempt starts clean.
    total_bytes = sum(_staged_blob_size(p, cwd) for p in _staged_paths(cwd))
    total_mib = total_bytes / (1024 * 1024)
    if total_mib > args.max_mb:
        _run(["git", "reset", "-q"], cwd=cwd)
        _emit(
            "warning", "debt-maturity-drip",
            f"refused: staged payload {total_mib:.1f} MiB exceeds ceiling "
            f"{args.max_mb} MiB; nothing committed",
        )
        return 0

    if args.dry_run:
        _emit(
            "notice", "debt-maturity-drip",
            f"dry-run: would commit {len(staged)} paths "
            f"({total_mib:.1f} MiB) and push to {args.remote}/{args.base}",
        )
        _run(["git", "reset", "-q"], cwd=cwd)
        return 0

    # COMMIT -- a single synthetic commit, author = dashboard-bot (the
    # nightly's identity), subject ends ``[skip ci]`` so the push never
    # fires the merge-gate's PR-proof machinery.
    subject = (
        f"{COMMIT_SUBJECT_PREFIX} "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        f"[skip ci]"
    )
    sha = _commit(cwd, subject)

    # PUSH -- one straight push, then up to ``--attempts``
    # non-fast-forward re-checkout cycles if origin/<base> moved under
    # us. The snapshot of the two paths is taken BEFORE the first push
    # attempt so the re-checkout can restore them after the FETCH_HEAD
    # reset.
    snapshot = _snapshot_allowed(cwd)
    attempts_used = 0
    while True:
        ok, msg = _attempt_push(cwd, args.remote, args.base)
        if ok:
            _emit(
                "notice", "debt-maturity-drip",
                f"pushed {sha} to {args.remote}/{args.base}: "
                f"{len(staged)} files, {total_mib:.1f} MiB",
            )
            shutil.rmtree(snapshot, ignore_errors=True)
            return 0
        if attempts_used >= args.attempts:
            _emit(
                "warning", "debt-maturity-drip",
                f"refused: {args.base} moved under "
                f"{attempts_used + 1} attempts; nothing pushed "
                f"(cache goes stale, not wrong)",
            )
            shutil.rmtree(snapshot, ignore_errors=True)
            return 0
        attempts_used += 1
        if not _recheck(cwd, args.remote, args.base, snapshot):
            _emit(
                "warning", "debt-maturity-drip",
                f"refused: {args.base} moved and re-checkout failed; "
                f"nothing pushed (cache goes stale, not wrong)",
            )
            shutil.rmtree(snapshot, ignore_errors=True)
            return 0
        # After re-checkout, re-gate the index: the reset cleared
        # ALLOWED_PATHS, so re-stage and re-check EMPTY/CEILING.
        if _staged_diff_is_empty(cwd):
            _emit(
                "notice", "debt-maturity-drip",
                "no changes to persist after re-checkout",
            )
            shutil.rmtree(snapshot, ignore_errors=True)
            return 0
        total_bytes = sum(_staged_blob_size(p, cwd) for p in _staged_paths(cwd))
        total_mib = total_bytes / (1024 * 1024)
        if total_mib > args.max_mb:
            _run(["git", "reset", "-q"], cwd=cwd)
            _emit(
                "warning", "debt-maturity-drip",
                f"refused: staged payload {total_mib:.1f} MiB exceeds "
                f"ceiling {args.max_mb} MiB after re-checkout; "
                f"nothing committed",
            )
            shutil.rmtree(snapshot, ignore_errors=True)
            return 0
        sha = _commit(cwd, subject)


if __name__ == "__main__":
    sys.exit(main())