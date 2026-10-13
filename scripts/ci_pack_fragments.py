#!/usr/bin/env python3
"""Split and join ``.github/ci/legacy-jobs.yml`` at job boundaries.

The manifest stays the only committed source. ``split`` cuts it into ordered
byte slices; ``join`` concatenates those slices. ``join(split(text))`` is the
original text, so a later patch can edit one job's slice and reassemble
without a second copy of the workflow.

A job fragment's owner is the single vertical directory named by its ``paths:``
entries, or ``shared`` when the paths are not confined to one. Suite modules
(``tests/**/test_*.py``) and package ``__init__.py`` markers do not locate a
vertical: every job names its own suite. Preamble and trailer are ``shared``.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml"

PREAMBLE_KEY = "__preamble__"
TRAILER_KEY = "__trailer__"

# Top-level buckets. The vertical is the directory under one of these, not
# the bucket itself. A file that sits directly in a bucket names no vertical.
_GENERIC_ROOTS = frozenset(
    {
        ".claude",
        ".github",
        "admin",
        "agentos",
        "app",
        "browser",
        "calibration",
        "collectors",
        "config",
        "content",
        "contracts",
        "data",
        "docs",
        "engine",
        "finviz_themes",
        "knowledge",
        "lib",
        "ops",
        "orch",
        "plugins",
        "properties",
        "reports",
        "research",
        "scripts",
        "site",
        "templates",
        "tests",
        "tools",
        "ux-evidence",
        "worker",
    }
)

# Exactly two spaces, then a job id, then a colon. Body keys sit at four
# spaces, so this is the job boundary in the real manifest.
_JOB_KEY_RE = re.compile(r"^  ([A-Za-z0-9][A-Za-z0-9_-]*):\s*$")
_PATHS_KEY_RE = re.compile(r"^    paths:\s*$")
_SIBLING_KEY_RE = re.compile(r"^    [A-Za-z0-9_-]+:")
_PATH_ENTRY_RE = re.compile(r"^      - (.*)$")
_SUITE_RE = re.compile(r"^tests/(?:.+/)?test_[^/]+\.py$")


@dataclass(frozen=True)
class Fragment:
    """One ordered slice of a legacy-jobs manifest."""

    key: str
    owner: str
    text: str
    kind: str  # "preamble" | "job" | "trailer"


def _newline_lines(text: str) -> list[str]:
    """Split on ``\\n`` only, keeping each separator, so join is byte-exact.

    ``str.splitlines`` also breaks on ``\\r``, ``\\x0b`` and Unicode separators.
    Those must stay inside the slice that contains them.
    """
    if text == "":
        return []
    parts = text.split("\n")
    if text.endswith("\n"):
        return [part + "\n" for part in parts[:-1]]
    lines = [part + "\n" for part in parts[:-1]]
    lines.append(parts[-1])
    return lines


def _job_keys(lines: list[str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = _JOB_KEY_RE.match(line.rstrip("\r\n"))
        if match:
            found.append((index, match.group(1)))
    return found


def _leading_start(lines: list[str], key_index: int, floor: int) -> int:
    """Include the blank lines and ``  #`` comments that introduce this job.

    Those lines sit between the previous job's body and this job's key. They
    document this job, so they travel with its fragment.
    """
    start = key_index
    cursor = key_index - 1
    while cursor >= floor:
        raw = lines[cursor].rstrip("\r\n")
        if raw.strip() == "" or raw.startswith("  #"):
            start = cursor
            cursor -= 1
            continue
        break
    return start


def _trailer_start(lines: list[str], key_index: int) -> int:
    """First line after the last job's indented body.

    A trailing blank line or a column-0 note is the trailer. Indented body
    lines stay with the job. The real manifest has no trailer bytes.
    """
    cursor = len(lines) - 1
    while cursor > key_index:
        raw = lines[cursor].rstrip("\r\n")
        if raw.startswith("    ") and raw.strip() != "":
            return cursor + 1
        cursor -= 1
    return key_index + 1


def job_paths(job_text: str) -> list[str]:
    """The job's ``paths:`` scalars, in order. Missing ``paths:`` is empty.

    Entries are the plain or quoted scalars the manifest actually writes.
    This does not interpret YAML aliases; the real file has none.
    """
    paths: list[str] = []
    in_paths = False
    for line in job_text.split("\n"):
        if not in_paths:
            if _PATHS_KEY_RE.match(line):
                in_paths = True
            continue
        entry = _PATH_ENTRY_RE.match(line)
        if entry:
            raw = entry.group(1).strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
                raw = raw[1:-1]
            paths.append(raw)
            continue
        if line.strip() == "" or line.startswith("      #") or line.startswith("    #"):
            continue
        if _SIBLING_KEY_RE.match(line):
            in_paths = False
            continue
        in_paths = False
    return paths


def _ignored_for_owner(path: str) -> bool:
    if "*" in path or "?" in path or "[" in path:
        return False
    if path.rsplit("/", 1)[-1] == "__init__.py":
        return True
    return _SUITE_RE.match(path) is not None


def _vertical_token(path: str) -> str | None:
    parts = [part for part in path.split("/") if part and part != "."]
    if not parts:
        return None
    if parts[0] in _GENERIC_ROOTS:
        parts = parts[1:]
    if not parts:
        return None
    token = parts[0]
    if token in {"*", "**"} or any(char in token for char in "*?["):
        return None
    if "." in token:
        return None
    return token


def owner_for_paths(paths: list[str]) -> str:
    """``shared``, unless every locating path names the same vertical directory."""
    tokens: set[str] = set()
    for path in paths:
        if _ignored_for_owner(path):
            continue
        token = _vertical_token(path)
        if token is None:
            return "shared"
        tokens.add(token)
        if len(tokens) > 1:
            return "shared"
    if len(tokens) == 1:
        return next(iter(tokens))
    return "shared"


def split(text: str) -> list[Fragment]:
    """Cut ``text`` into preamble, one fragment per job, and trailer."""
    lines = _newline_lines(text)
    keys = _job_keys(lines)
    if not keys:
        return [
            Fragment(PREAMBLE_KEY, "shared", text, "preamble"),
            Fragment(TRAILER_KEY, "shared", "", "trailer"),
        ]

    starts = []
    floor = 0
    for index, _job_id in keys:
        starts.append(_leading_start(lines, index, floor))
        floor = index + 1
    trailer_at = _trailer_start(lines, keys[-1][0])

    fragments = [
        Fragment(PREAMBLE_KEY, "shared", "".join(lines[: starts[0]]), "preamble")
    ]
    for position, (_index, job_id) in enumerate(keys):
        end = starts[position + 1] if position + 1 < len(keys) else trailer_at
        job_text = "".join(lines[starts[position] : end])
        fragments.append(
            Fragment(
                job_id,
                owner_for_paths(job_paths(job_text)),
                job_text,
                "job",
            )
        )
    fragments.append(
        Fragment(TRAILER_KEY, "shared", "".join(lines[trailer_at:]), "trailer")
    )
    return fragments


def join(fragments: list[Fragment]) -> str:
    """Reassemble slices in the order ``split`` produced."""
    return "".join(fragment.text for fragment in fragments)


def format_report(fragments: list[Fragment]) -> str:
    """``jobs=N fragments=M owners={name: count, ...}`` with owners sorted."""
    counts: dict[str, int] = {}
    jobs = 0
    for fragment in fragments:
        if fragment.kind == "job":
            jobs += 1
        counts[fragment.owner] = counts.get(fragment.owner, 0) + 1
    owners = ", ".join(f"{name}: {counts[name]}" for name in sorted(counts))
    return f"jobs={jobs} fragments={len(fragments)} owners={{{owners}}}"


def _first_difference(left: bytes, right: bytes) -> int:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return index
    return limit


def check_manifest(path: Path = DEFAULT_MANIFEST) -> str:
    """Return the report line, or raise ``ValueError`` when join drifts."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"{path} is not utf-8: {exc}") from exc
    fragments = split(text)
    rejoined = join(fragments).encode("utf-8")
    if rejoined != raw:
        offset = _first_difference(rejoined, raw)
        raise ValueError(
            f"join(split({path})) drifted at byte {offset}: "
            f"{len(rejoined)} bytes vs {len(raw)}"
        )
    return format_report(fragments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 0 iff join(split(manifest)) is byte-identical",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="manifest to check (default: .github/ci/legacy-jobs.yml)",
    )
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("--check is required")
    try:
        print(check_manifest(args.manifest))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
