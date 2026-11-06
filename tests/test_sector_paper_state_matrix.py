"""Guard the Sector Paper board x state matrix (design_refs/sector-paper-20261021).

Checks the frozen contract from packet sic-p-states-20261021-r1: exact header,
102 rows covering 6 boards x 17 states, yes/no applicability, real file:line
triggers, capability ids that exist in the completion capability matrix, no
forbidden v-word, and tier1_render within 20 words.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "design_refs" / "sector-paper-20261021" / "state_matrix.csv"
CAPABILITY = (
    ROOT / "research" / "sector_completion_20261021" / "CAPABILITY_MATRIX_2026-10-21.csv"
)

BOARDS = ["brief", "explore", "dossier", "research", "watches", "cycles"]
STATES = [
    "fresh",
    "stale",
    "incompatible_generation",
    "partial",
    "corrected",
    "abstained",
    "error",
    "empty",
    "no_access",
    "loading",
    "offline",
    "unauthorized",
    "locked",
    "invalid_payload",
    "zero",
    "empty_search",
    "uncertain_command",
]
HEADER = [
    "board",
    "state",
    "applies",
    "trigger_code",
    "tier1_render",
    "still_works",
    "user_action",
    "live_region",
    "matrix_rows",
    "status",
]
# The common-rules v-word, assembled so this file never writes it literally.
FORBIDDEN = "valid" + "ated"
TRIGGER_RE = re.compile(r"^(.+):(\d+)$")


def _rows():
    with MATRIX.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _capability_ids():
    with CAPABILITY.open(encoding="utf-8-sig", newline="") as fh:
        return {r["row_id"] for r in csv.DictReader(fh) if r.get("row_id")}


def _file_lines(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)


def test_header_exact():
    with MATRIX.open(encoding="utf-8", newline="") as fh:
        assert next(csv.reader(fh)) == HEADER


def test_exactly_102_rows_covering_6_boards_x_17_states():
    rows = _rows()
    assert len(rows) == 102
    seen = {(r["board"], r["state"]) for r in rows}
    assert seen == {(b, s) for b in BOARDS for s in STATES}


def test_applies_is_yes_or_no():
    assert all(r["applies"] in ("yes", "no") for r in _rows())


def test_trigger_codes_name_existing_file_and_line_in_range():
    for r in _rows():
        trig = r["trigger_code"].strip()
        if trig == "NOT YET PRODUCED":
            continue
        if not trig and r["applies"] == "no":
            continue
        m = TRIGGER_RE.match(trig)
        assert m, f"malformed trigger {trig!r} on {r['board']}/{r['state']}"
        rel, line = m.group(1), int(m.group(2))
        path = ROOT / rel
        assert path.is_file(), f"trigger names missing file {rel}"
        n = _file_lines(path)
        assert 1 <= line <= n, f"{rel}:{line} outside file length 1..{n}"


def test_matrix_rows_ids_exist_in_capability_matrix():
    ids = _capability_ids()
    assert ids, "capability matrix read produced no row ids"
    for r in _rows():
        cells = r["matrix_rows"].strip()
        if cells == "none":
            continue
        for cid in cells.split(";"):
            assert cid.strip() in ids, f"unknown capability id {cid!r}"


def test_no_cell_contains_forbidden_v_word():
    for r in _rows():
        for cell in r.values():
            assert FORBIDDEN not in cell.lower(), (r["board"], r["state"])


def test_tier1_render_at_most_20_words():
    for r in _rows():
        assert len(r["tier1_render"].split()) <= 20, (r["board"], r["state"])


def test_status_vocabulary_matches_trigger_presence():
    for r in _rows():
        assert r["status"] in ("PRODUCED", "NOT YET PRODUCED")
        has_trigger = TRIGGER_RE.match(r["trigger_code"].strip()) is not None
        assert (r["status"] == "PRODUCED") == has_trigger, (r["board"], r["state"])
