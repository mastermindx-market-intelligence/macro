"""Preserve first-retained Turn Watch metadata inside the existing engine push.

This is a byte-retention fence, not a clock validator or a separate publisher.
It never changes observation or B1 input bytes. Invalid retained metadata stays
invalid to the reader; a racing producer cannot replace it with another claim.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = "data/us_prophet_rank/episode_inputs/turn_watch/producer_captures"
_PATH = re.compile(re.escape(CAPTURE_ROOT) + r"/[0-9a-f]{64}\.json\Z")


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True).stdout


def _commit(repo: Path, ref: str) -> str:
    return _git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()


def _entries(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    entries = {}
    for entry in _git(repo, "ls-tree", "-r", "-z", commit, "--", CAPTURE_ROOT).split(b"\0"):
        if not entry:
            continue
        meta, path_bytes = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = path_bytes.decode()
        if not _PATH.fullmatch(path) or mode != "100644" or kind != "blob":
            raise ValueError("unexpected producer capture tree entry")
        entries[path] = (mode, oid)
    return entries


def _boundary(repo: Path, onto: str, candidate_ref: str = "HEAD") -> tuple[str, str, dict, dict]:
    target, candidate = _commit(repo, onto), _commit(repo, candidate_ref)
    if _git(repo, "symbolic-ref", "--quiet", "HEAD").decode().strip() != "refs/heads/main":
        raise ValueError("capture retention requires the engine's attached main candidate")
    _git(repo, "merge-base", "--is-ancestor", target, candidate)
    return target, candidate, _entries(repo, target), _entries(repo, candidate)


def check_retained(repo: Path, onto: str = "origin/main", candidate_ref: str = "HEAD") -> dict:
    target, candidate, retained, proposed = _boundary(repo, onto, candidate_ref)
    differing = sorted(path for path, entry in retained.items() if proposed.get(path) != entry)
    if differing:
        raise ValueError(f"candidate changes {len(differing)} retained producer capture(s)")
    return {"state": "PRESERVED", "target": target, "candidate": candidate,
            "retained_count": len(retained)}


def preserve_retained(repo: Path, onto: str = "origin/main") -> dict:
    target, candidate, retained, proposed = _boundary(repo, onto)
    differing = sorted(path for path, entry in retained.items() if proposed.get(path) != entry)
    if not differing:
        return {**check_retained(repo, target), "restored_count": 0}

    # Refuse custody ambiguity before touching either index or receipt worktree.
    # The existing locked commit primitive then enforces this exact allowlist.
    _git(repo, "diff", "--cached", "--quiet")
    if _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all",
            "--ignored=matching", "--", *differing):
        raise ValueError("pending work at a retained producer capture path")
    if _commit(repo, "HEAD") != candidate or _commit(repo, onto) != target:
        raise ValueError("capture retention boundary moved before correction")
    # The incumbent committer acquires Git's real index lock BEFORE replacing
    # exact capture entries in its private index snapshot. Working-file bytes
    # are never overwritten: independent writers do not honor Git's index lock.
    command = ('source "$1"\nshift\n'
               'target="$1"; candidate="$2"; shift 2\n'
               'oip_commit_locked_roots "engine: preserve retained Turn Watch captures" '
               'true --retained-capture-overlay "$target" "$candidate" "$@"')
    subprocess.run(["bash", "-c", command, "turn-watch-capture-retention",
                    str(REPO_ROOT / "scripts/ci/options_signal_nightly.sh"),
                    target, candidate, *differing],
                   cwd=repo, check=True, capture_output=True)
    return {**check_retained(repo, target), "restored_count": len(differing)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preserve", "check"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--onto", default="origin/main")
    parser.add_argument("--candidate", default="HEAD")
    args = parser.parse_args(argv)
    try:
        if args.mode == "preserve":
            if args.candidate != "HEAD":
                raise ValueError("retention correction must use the current HEAD")
            result = preserve_retained(args.repo, args.onto)
        else:
            result = check_retained(args.repo, args.onto, args.candidate)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        # Native errors remain failures; never retry by discarding an index or
        # weakening the existing QLedger/index/ref publication guards.
        detail = (exc.stderr or b"").decode(errors="replace") if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(json.dumps({"state": "WITHHELD", "reason": detail[-1600:] or str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
