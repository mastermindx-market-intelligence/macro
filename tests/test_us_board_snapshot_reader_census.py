"""Census fence for the US board snapshots ledger after the rollover to parts.

``data/us_board_ledger/snapshots.jsonl`` is now a frozen base plus
``snapshots_parts/part-NNNNNN.jsonl`` (``engine/us_board_snapshots.py``). A reader
that opens the base alone silently loses every row written after the rollover,
and a writer that appends to the base directly pushes it over GitHub's 100 MiB
limit. This test is the census: every source file that names the base path is
either a reader that goes through ``engine/us_board_snapshots`` or a named
non-reader with the reason recorded here. A new file that names the path fails
until it is added to one list or the other.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("engine", "scripts", "lib", "app", "collectors", "tools", "worker", "admin")
MODULE = "engine/us_board_snapshots.py"

# Readers (and the one writer, grade_us_board) of the base path. Each must read
# through engine/us_board_snapshots and is pinned by a parts-layout test in
# tests/test_us_board_snapshot_readers_build.py or ..._readers_grade.py.
READERS = frozenset({
    "engine/prophet_board_since.py",
    "engine/us_prophet_w3.py",
    "scripts/build_exit_policy_vintage_fixture.py",
    "scripts/build_prophet.py",
    "scripts/build_track_record_page.py",
    "scripts/check_surface_freshness.py",
    "scripts/exit_policy_study.py",
    "scripts/grade_bottom_calls.py",
    "scripts/grade_us_board.py",
    "scripts/prophet_fusion_race.py",
    "scripts/prophet_pit_replay.py",
    "scripts/prophet_postmortem.py",
    "scripts/replay_standout_books.py",
})

# Files that name the path without reading it.
NOT_READERS = {
    "engine/standout_audit.py": "defines _snapshots_path() but never calls it",
    "engine/us_board_rank.py": "docstring only",
    "engine/ledger_clock.py": "docstring only",
    "scripts/prophet_fusion_c2.py": "reads through prophet_fusion_race.load_snapshots",
    "scripts/build_context_candidates.py": "reads retro_grades.parquet; the path is in docstrings",
    "scripts/check_validated_claims.py": "comment only",
    "scripts/build_site.py": "comment only; reads through prophet_board_since",
}

_BASE_NAME = re.compile(r"(?<![\w.])snapshots\.jsonl")
# A direct append to the base, bypassing the parts layout. V2_SNAPSHOTS_JSONL is a
# different, small file and is excluded by the lookbehind.
_DIRECT_APPEND = re.compile(
    r"(?<![A-Za-z0-9_])SNAPSHOTS_JSONL\.open\(|open\(\s*SNAPSHOTS_JSONL\b")


def _sources() -> dict[str, str]:
    out: dict[str, str] = {}
    for top in SOURCE_DIRS:
        base = ROOT / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            out[rel] = path.read_text(encoding="utf-8", errors="replace")
    return out


def _names_us_base(text: str) -> bool:
    return "us_board_ledger" in text and bool(_BASE_NAME.search(text))


def test_every_file_naming_the_us_snapshots_base_is_classified():
    found = {rel for rel, text in _sources().items() if _names_us_base(text)}
    known = set(READERS) | set(NOT_READERS) | {MODULE}
    new = sorted(found - known)
    assert not new, (
        "these files name data/us_board_ledger/snapshots.jsonl but are not in the census. "
        "Rows after the rollover live in snapshots_parts/, so read the ledger through "
        "engine/us_board_snapshots (iter_lines / read_lines / exists) and add the file to "
        f"READERS with a parts-layout test, or to NOT_READERS with the reason: {new}")
    gone = sorted(known - found)
    assert not gone, f"census entries no longer name the path; drop them: {gone}"


def test_every_reader_goes_through_the_parts_module():
    sources = _sources()
    missing = sorted(rel for rel in READERS
                     if not re.search(r"\bus_board_snapshots\b", sources.get(rel, "")))
    assert not missing, f"readers that do not use engine/us_board_snapshots: {missing}"


def test_no_source_appends_to_the_base_directly():
    hits = sorted(rel for rel, text in _sources().items()
                  if rel != MODULE and _DIRECT_APPEND.search(text))
    assert not hits, (
        "append through engine/us_board_snapshots.append_line, which rolls to a new part "
        f"instead of growing the base past the limit: {hits}")


def test_the_grader_appends_through_append_line():
    text = (ROOT / "scripts" / "grade_us_board.py").read_text(encoding="utf-8")
    assert "us_board_snapshots.append_line(" in text


def test_standout_audit_snapshots_path_stays_unused():
    text = (ROOT / "engine" / "standout_audit.py").read_text(encoding="utf-8")
    assert len(re.findall(r"\b_snapshots_path\(", text)) == 1, (
        "engine/standout_audit.py now calls _snapshots_path(); it has become a reader of "
        "the base path, so move it to READERS and read through engine/us_board_snapshots")
