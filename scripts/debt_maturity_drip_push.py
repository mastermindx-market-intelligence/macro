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
  by snapshotting THIS RUN's produced files, fetching the remote tip,
  re-checking out onto it, then overlaying those files (never rmtree of
  the cache directory — a foreign file the remote added must survive).
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
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
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


# ---------------------------------------------------------------------------
# Result types — mirror the rejection classes tests/test_push_retry.py
# already uses (GH013, Permission denied, hook rejection → push_error).
# A non-fast-forward is retryable; everything else is a hard refusal.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PushResult:
    """Union type for push outcomes. ``ok`` is retryable-gone-good;
    ``non_fast_forward`` is retryable; ``push_error`` is a hard refusal."""

    kind: str  # "ok" | "non_fast_forward" | "push_error"
    detail: str = ""  # first stderr line for push_error


_OK = PushResult(kind="ok")
_NON_FF = PushResult(kind="non_fast_forward")
_NON_FF_RE = re.compile(
    r"rejected.*non-fast-forward|"
    r"! \[rejected\].*main -> main \(non-fast-forward\)|"
    r"fetch first",
    re.IGNORECASE,
)
_HOOK_RE = re.compile(
    r"hook declined|"
    r"GH006.*hook|"
    r"remote: error.*hook",
    re.IGNORECASE,
)
_AUTH_RE = re.compile(
    r"Permission denied|"
    r"fatal: unable to access|"
    r"authentication failed",
    re.IGNORECASE,
)
_GH013_RE = re.compile(
    r"GH013|"
    r"repository rule violations|"
    r"push declined due to repository rule",
    re.IGNORECASE,
)
_REF_LOCK_RE = re.compile(
    r"cannot lock ref|"
    r"is at .* but expected|"
    r"stale info|"
    r"fetch first",
    re.IGNORECASE,
)


def _classify_push_failure(stderr: str) -> PushResult:
    """Classify a failed push by its error output.

    MAJOR-1: every git outcome is classified. ``non_fast_forward`` and
    ``ref_lock`` (a lost-race, not a conflict) are retryable;
    ``push_error`` (GH013, hook, auth) is a hard refusal — no retry."""
    first_line = stderr.strip().split("\n", 1)[0] if stderr.strip() else ""
    if _NON_FF_RE.search(stderr):
        return PushResult(kind="non_fast_forward")
    if _HOOK_RE.search(stderr) or _AUTH_RE.search(stderr) or _GH013_RE.search(stderr):
        return PushResult(kind="push_error", detail=first_line)
    if _REF_LOCK_RE.search(stderr):
        # A lost-race ref lock is structurally identical to a non-ff:
        # the remote moved while we were preparing. Retry it.
        return PushResult(kind="non_fast_forward")
    return PushResult(kind="push_error", detail=first_line)


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


def _path_is_allowed(path: str) -> bool:
    """True iff ``path`` is inside one of ALLOWED_PATHS (file or prefix)."""
    for allowed in ALLOWED_PATHS:
        if path == allowed or path.startswith(allowed.rstrip("/") + "/"):
            return True
    return False


def _disallowed_commit_paths(cwd: Path) -> list[str] | None:
    """Paths in ``HEAD^..HEAD`` that are outside ALLOWED_PATHS.

    Returns None when ``HEAD^`` is missing (cannot verify). An empty list
    means the persist commit is path-scoped."""
    proc = _run(["git", "diff", "--name-only", "HEAD^..HEAD"], cwd=cwd)
    if proc.returncode != 0:
        return None
    bad: list[str] = []
    for line in proc.stdout.splitlines():
        path = line.strip()
        if path and not _path_is_allowed(path):
            bad.append(path)
    return bad


def _snapshot_run_artifacts(cwd: Path, rel_paths: list[str], dst_root: Path) -> dict[str, str]:
    """Copy only this run's produced files (never a whole directory tree)."""
    mapping: dict[str, str] = {}
    for rel in rel_paths:
        src = cwd / rel
        if not src.is_file():
            continue
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        mapping[rel] = str(dst)
    return mapping


def _overlay_run_artifacts(cwd: Path, mapping: dict[str, str]) -> None:
    """Copy this run's files onto the working tree without wiping siblings.

    A foreign file the remote added (e.g. cache/foreign.json) must survive.
    Never rmtree a destination directory."""
    for rel, abs_src in mapping.items():
        src = Path(abs_src)
        if not src.is_file():
            continue
        dst = cwd / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
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


def _attempt_push(cwd: Path, base: str, remote: str) -> PushResult:
    """Single attempt: ``git push <remote> HEAD:refs/heads/<base>``.
    Classifies the failure (MAJOR-1) so the retry loop can distinguish
    retryable non-fast-forward from a hard push_error. Never a force-push,
    never a history rewrite, never a stash apply."""
    proc = _run(
        ["git", "push", remote, f"HEAD:refs/heads/{base}"],
        cwd=cwd,
        check=False,
    )
    if proc.returncode == 0:
        return _OK
    stderr = (proc.stdout or "") + (proc.stderr or "")
    return _classify_push_failure(stderr)


def _resync_to_remote(
    cwd: Path,
    base: str,
    remote: str,
    artifacts: list[str] | None = None,
) -> dict[str, str]:
    """Fetch the remote tip, re-checkout onto it, overlay this run's artifacts.

    Overlay, never wipe: a foreign file the remote added must survive.
    MAJOR-1: a failed ``git fetch --depth 1`` ABORTS the resync — we never
    ``git reset --hard FETCH_HEAD`` onto a stale tip."""
    print("::notice title=debt-maturity-drip::resync_to_remote", flush=True)
    rels = list(artifacts or ())
    with tempfile.TemporaryDirectory(prefix="dm-drip-") as tmp:
        tmp_root = Path(tmp)
        snapshot = _snapshot_run_artifacts(cwd, rels, tmp_root)
        fetch_proc = _run(
            ["git", "fetch", "-q", "--depth", "1", remote, base],
            cwd=cwd,
            check=False,
        )
        if fetch_proc.returncode != 0:
            # A fetch failure means we cannot establish a clean remote tip.
            # Abort rather than reset onto a stale local ref.
            raise RuntimeError(
                f"git fetch failed (exit {fetch_proc.returncode}); "
                "aborting resync rather than resetting to stale FETCH_HEAD"
            )
        _run(["git", "reset", "-q", "--hard", "FETCH_HEAD"], cwd=cwd)
        _overlay_run_artifacts(cwd, snapshot)
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

    # ANCESTOR — refuse unless HEAD is already on origin/<base>'s history.
    # A workflow_dispatch from a PR branch must never fast-forward main to
    # a feature tip. Fetch first so the check is against a fresh tip.
    fetch_base = _run(["git", "fetch", "-q", args.remote, args.base], cwd=cwd)
    if fetch_base.returncode != 0:
        _warning(
            "debt-maturity-drip",
            f"git fetch {args.remote} {args.base} failed; refusing to push "
            "(cache goes stale, not wrong)",
        )
        return 0
    ancestor = _run(
        ["git", "merge-base", "--is-ancestor", "HEAD", f"{args.remote}/{args.base}"],
        cwd=cwd,
    )
    if ancestor.returncode != 0:
        _warning(
            "debt-maturity-drip",
            f"HEAD is not an ancestor of {args.remote}/{args.base}; refusing to push "
            "(cache goes stale, not wrong)",
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

    # Capture the staged list BEFORE committing — after commit the index is
    # empty and a post-commit ``_staged_files`` count would report 0.
    artifacts = _staged_files(cwd)
    staged = len(artifacts)

    if args.dry_run:
        _notice(
            "debt-maturity-drip",
            f"dry-run: would commit {staged} files ({staged_mib:.1f} MiB)",
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

    # PATH-SCOPE — the persist commit's tree-vs-parent must be ⊆ ALLOWED_PATHS
    # (computed here, not only in the workflow YAML) before any push.
    bad = _disallowed_commit_paths(cwd)
    if bad is None:
        _warning(
            "debt-maturity-drip",
            "cannot compute persist commit path-scope (HEAD^ missing); refusing to push "
            "(cache goes stale, not wrong)",
        )
        return 0
    if bad:
        _warning(
            "debt-maturity-drip",
            f"blocked path in persist commit: {bad[0]}; refusing to push "
            "(cache goes stale, not wrong)",
        )
        return 0

    # PUSH — origin/main moves every few minutes under [skip ci] data commits,
    # so a single-shot push regularly sees a non-fast-forward; retry the
    # fetch → re-checkout → overlay cycle up to --attempts times.
    #
    # MAJOR-1: classify every outcome.  push_error (auth / hook / GH013) is a
    # hard refusal — exit immediately without retry.  non_fast_forward and
    # ref_lock (a lost race, not a conflict) are retryable up to --attempts.
    last_result: PushResult | None = None
    for attempt in range(1, max(args.attempts, 0) + 1):
        result = _attempt_push(cwd, args.base, args.remote)
        last_result = result
        if result.kind == "ok":
            sha = _pushed_sha(cwd, args.base, args.remote) or "<unknown>"
            _notice(
                "debt-maturity-drip",
                f"pushed {sha} to {args.base}: {staged} files, {staged_mib:.1f} MiB",
            )
            return 0
        if result.kind == "push_error":
            # Hard refusal — no retry.  Name the class in the terminal warning.
            _warning(
                "debt-maturity-drip",
                f"push_error: {result.detail}; {args.base} refused (cache goes stale, not wrong)",
            )
            return 0
        # non_fast_forward or ref_lock — retryable.
        if attempt >= max(args.attempts, 0):
            break
        # Re-checkout onto the remote tip, overlay THIS RUN's artifacts only.
        try:
            _resync_to_remote(cwd, args.base, args.remote, artifacts)
        except Exception as exc:
            _warning("debt-maturity-drip", f"re-checkout failed: {exc!r}")
            return 0
        # Re-stage the two allowed paths after the overlay.
        existing = _existing_allowed_paths(cwd)
        for rel in existing:
            _run(["git", "add", "--", rel], cwd=cwd)
        if _diff_is_empty(cwd):
            _notice("debt-maturity-drip", "no changes to persist after re-checkout")
            return 0
        artifacts = _staged_files(cwd)
        staged = len(artifacts)
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
        bad = _disallowed_commit_paths(cwd)
        if bad is None or bad:
            detail = "HEAD^ missing" if bad is None else bad[0]
            _warning(
                "debt-maturity-drip",
                f"blocked path in persist commit: {detail}; refusing to push "
                "(cache goes stale, not wrong)",
            )
            return 0

    # MAJOR-1: terminal warning names the class instead of always saying "moved under N attempts".
    final_kind = last_result.kind if last_result else "unknown"
    _warning(
        "debt-maturity-drip",
        f"{final_kind}: {args.base} refused after {args.attempts} attempts (cache goes stale, not wrong)",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
