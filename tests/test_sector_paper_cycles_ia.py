"""Guard tests for design_refs/sector-paper-20261021/cycles_ia.csv (packet SIC-P-CYC).

Parses the Sector Cycles information-architecture CSV written against the C01-C28
capability rows and asserts the contracts the Paper completion boards rely on:
exact header, 28 rows in order, region/tier/status vocabularies, and that every
cited producer (engine/ or scripts/) and renderer (templates/sector_cycles.js)
actually exists in this tree with the named function. Also enforces the lane's
wording fences: the forbidden v-word never appears, and "win rate" only occurs
inside the negated phrase "not a win rate".
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "design_refs" / "sector-paper-20261021" / "cycles_ia.csv"
MD_PATH = ROOT / "design_refs" / "sector-paper-20261021" / "cycles_ia.md"

HEADER = [
    "row_id", "capability", "region", "tier", "producer_file_function",
    "artifact_key", "render_function", "states", "mobile_placement", "a11y",
    "status",
]
REGIONS = {f"R{i}" for i in range(1, 10)}
STATUSES = {"PRODUCED", "PRODUCED_NOT_RENDERED", "NOT YET PRODUCED"}
STATE_WORDS = {
    "fresh", "stale", "incompatible_generation", "partial", "corrected",
    "abstained", "error", "empty", "loading", "offline",
}
MOBILE_RE = re.compile(r"^(inline|full-screen|sheet:[a-z0-9|]+|deferred:[a-z0-9-]+)$")
SKIP_TOKENS = {"NOT RENDERED", "NOT YET PRODUCED"}


def _rows() -> list[list[str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def test_header_exact_and_28_rows_in_order():
    rows = _rows()
    assert rows[0] == HEADER
    body = rows[1:]
    assert len(body) == 28
    assert [r[0] for r in body] == [f"C{i:02d}" for i in range(1, 29)]
    assert all(len(r) == len(HEADER) for r in body)


def test_region_tier_status_states_mobile_vocabularies():
    for r in _rows()[1:]:
        row_id, _cap, region, tier = r[0], r[1], r[2], r[3]
        states, mobile, status = r[7], r[8], r[10]
        assert region in REGIONS, (row_id, region)
        assert tier in {"1", "2", "3"}, (row_id, tier)
        assert status in STATUSES, (row_id, status)
        words = [w for w in states.split(";") if w]
        assert words, (row_id, "empty states cell")
        assert set(words) <= STATE_WORDS, (row_id, states)
        assert MOBILE_RE.match(mobile), (row_id, mobile)


def _check_ref(ref: str, row_id: str, col: str) -> None:
    path_s, _, rest = ref.partition("::")
    name, _, line = rest.partition(":")
    path = ROOT / path_s
    assert path.is_file(), (row_id, col, "missing file", path_s)
    text = path.read_text(encoding="utf-8")
    assert (
        f"def {name}" in text or f"function {name}" in text or f"{name} =" in text
    ), (row_id, col, "function name not found", name, path_s)
    if line:
        assert line.isdigit() and int(line) <= len(text.splitlines()), (
            row_id, col, "line out of range", ref,
        )


def test_cited_producers_and_renderers_exist():
    for r in _rows()[1:]:
        row_id = r[0]
        for col, ref in (("producer", r[4]), ("render", r[6])):
            if ref in SKIP_TOKENS:
                continue
            _check_ref(ref, row_id, col)


def test_forbidden_v_word_absent():
    v_word = "valid" + "ated"  # assembled so this file never writes the literal
    for r in _rows():
        for cell in r:
            assert v_word not in cell.lower(), (r[0], cell)


def test_win_rate_only_negated():
    for r in _rows():
        for cell in r:
            residue = cell.lower().replace("not a win rate", "")
            assert "win rate" not in residue, (r[0], cell)


def test_md_has_region_sections_and_required_sections():
    text = MD_PATH.read_text(encoding="utf-8")
    for i in range(1, 10):
        assert f"## R{i} " in text, f"missing region section R{i}"
    assert "Not yet produced" in text
    assert "Code conditions for states" in text
    assert "NOT IN TREE" in text  # grader value fence
