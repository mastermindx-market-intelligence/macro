"""Read-only SNI register summary vs Status-column consistency (A01-E1).

Consumes the frozen register and the A01 DRAFT contract as owner-supplied
bytes. Does not re-implement Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. No git subprocess. No network.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "research/single_name_intelligence/protocols/S0_AMENDMENT_A01_DRAFT.md"
JSON_PATH = ROOT / "research/single_name_intelligence/protocols/S0_AMENDMENT_A01_DRAFT.json"
REGISTER_PATH = ROOT / "research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md"

REGISTER_BLOB = "5cea5c88335133e7684200b694f0d170ca4ae5b2"
STATUS_ROW_START = 115
STATUS_ROW_END = 127
ROW_COUNT_LINE = 129
EXPECTED_IDS = [f"P{i:02d}" for i in range(1, 14)]

# Prefix order is matching order: procurement before bridge; DIAGNOSTIC last.
STATUS_PREFIXES = (
    "RETIRED-CONTAMINATED",
    "REGISTERED-GATED",
    "NOT SUPPORTED \u2014 PROCUREMENT-GATED",
    "NOT SUPPORTED \u2014 BRIDGE REQUIRED",
    "DIAGNOSTIC",
)

_WORD_NUM = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
}
_NUM_WORD = {n: w for w, n in _WORD_NUM.items()}

RC02_RETIRE_MSG = (
    "line 129 now agrees with the Status column; retire "
    "test_rc_02_line_129_disagrees_with_status_column and erratum A01-E1 together"
)


def git_blob_sha(data: bytes) -> str:
    """Git blob SHA-1: sha1(b'blob %d\\0' + bytes). Do not shell out."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def pipe_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def classify_status(status: str) -> str:
    for prefix in STATUS_PREFIXES:
        if status.startswith(prefix):
            return prefix
    raise AssertionError(f"unclassified Status cell: {status!r}")


def find_status_table(lines: list[str]) -> tuple[int, int, list[tuple[str, str]]]:
    """Locate the protocol table by its header row, not by a hard-coded line.

    Returns (header_lineno_1based, first_data_lineno_1based, [(pid, status)]).
    """
    header_i = None
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = pipe_cells(line)
        if cells and cells[0] == "id" and cells[-1] == "Status":
            header_i = i
            break
    if header_i is None:
        raise AssertionError("protocol table header (id ... Status) not found")
    sep = lines[header_i + 1]
    sep_cells = pipe_cells(sep)
    assert sep_cells and all(re.fullmatch(r":?-{3,}:?", c) for c in sep_cells), sep
    rows: list[tuple[str, str]] = []
    j = header_i + 2
    while j < len(lines) and lines[j].strip().startswith("|"):
        cells = pipe_cells(lines[j])
        rows.append((cells[0], cells[-1]))
        j += 1
    header_lineno = header_i + 1
    first_data_lineno = header_i + 3
    return header_lineno, first_data_lineno, rows


def derive_counts_and_members(
    rows: list[tuple[str, str]],
) -> tuple[dict[str, int], dict[str, list[str]], dict[str, str]]:
    members: dict[str, list[str]] = {prefix: [] for prefix in STATUS_PREFIXES}
    class_of: dict[str, str] = {}
    for pid, status in rows:
        klass = classify_status(status)
        members[klass].append(pid)
        class_of[pid] = klass
    counts = {klass: len(pids) for klass, pids in members.items()}
    return counts, members, class_of


def _num_token(tok: str) -> int:
    t = tok.lower()
    if t.isdigit():
        return int(t)
    if t not in _WORD_NUM:
        raise AssertionError(f"not a number word: {tok!r}")
    return _WORD_NUM[t]


def parse_stated_counts(line: str) -> dict[str, int]:
    """Parse line-129 (or a rewritten copy) into the five Status-class counts."""
    counts = {prefix: 0 for prefix in STATUS_PREFIXES}
    m = re.search(r"(?i)\b(\w+)\s+carry\s+REGISTERED-GATED\b", line)
    if m:
        counts["REGISTERED-GATED"] = _num_token(m.group(1))
    m = re.search(
        r"(?i)\b(\w+)\s+(?:are|is|carry)\s+RETIRED-CONTAMINATED\b", line
    )
    if m:
        counts["RETIRED-CONTAMINATED"] = _num_token(m.group(1))
    m = re.search(r"(?i)\b(\w+)\s+bridge-required\b", line)
    if m:
        counts["NOT SUPPORTED \u2014 BRIDGE REQUIRED"] = _num_token(m.group(1))
    m = re.search(r"(?i)\b(\w+)\s+procurement-gated\b", line)
    if m:
        counts["NOT SUPPORTED \u2014 PROCUREMENT-GATED"] = _num_token(m.group(1))
    m = re.search(r"(?i)\b(\w+)\s+is\s+DIAGNOSTIC\b", line)
    if m:
        counts["DIAGNOSTIC"] = _num_token(m.group(1))
    return counts


def find_row_count_line(lines: list[str]) -> tuple[int, str]:
    for i, line in enumerate(lines):
        if line.startswith("**Row count:**"):
            return i + 1, line
    raise AssertionError("**Row count:** summary line not found")


def _fmt_num(n: int, *, capital: bool = False) -> str:
    w = _NUM_WORD[n]
    return w.capitalize() if capital else w


def rewrite_line_129_to_derived(counts: dict[str, int]) -> str:
    n_reg = counts["REGISTERED-GATED"]
    n_ret = counts["RETIRED-CONTAMINATED"]
    n_br = counts["NOT SUPPORTED \u2014 BRIDGE REQUIRED"]
    n_pr = counts["NOT SUPPORTED \u2014 PROCUREMENT-GATED"]
    n_di = counts["DIAGNOSTIC"]
    return (
        f"**Row count:** 13. {_fmt_num(n_reg, capital=True)} carry REGISTERED-GATED. "
        f"{_fmt_num(n_ret, capital=True)} are RETIRED-CONTAMINATED. "
        f"{_fmt_num(n_br + n_pr, capital=True)} are wholly NOT SUPPORTED: "
        f"{_fmt_num(n_br)} bridge-required and {_fmt_num(n_pr)} procurement-gated. "
        f"{_fmt_num(n_di, capital=True)} is DIAGNOSTIC."
    )


def parse_md_section9_table(
    md_text: str,
) -> tuple[dict[str, int], dict[str, int], dict[str, list[str]]]:
    lines = md_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## 9. Register errata":
            start = i
            break
    if start is None:
        raise AssertionError("## 9. Register errata not found")
    header_i = None
    for i in range(start + 1, len(lines)):
        if not lines[i].strip().startswith("|"):
            continue
        cells = pipe_cells(lines[i])
        if cells[:4] == [
            "class",
            "stated at line 129",
            "derived from the Status column",
            "protocols",
        ]:
            header_i = i
            break
    if header_i is None:
        raise AssertionError("A01-E1 errata table not found under §9")
    stated: dict[str, int] = {}
    derived: dict[str, int] = {}
    members: dict[str, list[str]] = {}
    j = header_i + 2
    while j < len(lines) and lines[j].strip().startswith("|"):
        cells = pipe_cells(lines[j])
        klass, stated_cell, derived_cell, proto_cell = cells[:4]
        stated[klass] = int(stated_cell.split()[0])
        derived[klass] = int(derived_cell.split()[0])
        members[klass] = [p.strip() for p in proto_cell.split(",") if p.strip()]
        j += 1
    return stated, derived, members


def load_erratum() -> dict:
    doc = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    errata = doc["register_errata"]
    assert isinstance(errata, list) and len(errata) == 1
    return errata[0]


def parse_register(text: str) -> tuple[list[str], list[tuple[str, str]], dict, dict, dict, str]:
    lines = text.splitlines()
    header_lineno, first_data_lineno, rows = find_status_table(lines)
    assert first_data_lineno == STATUS_ROW_START, first_data_lineno
    assert first_data_lineno + len(rows) - 1 == STATUS_ROW_END, len(rows)
    assert header_lineno == 113, header_lineno
    counts, members, class_of = derive_counts_and_members(rows)
    rc_lineno, rc_line = find_row_count_line(lines)
    assert rc_lineno == ROW_COUNT_LINE, rc_lineno
    return lines, rows, counts, members, class_of, rc_line


def check_status_column_parsed(rows, class_of) -> None:
    assert len(rows) == 13, len(rows)
    pids = [pid for pid, _ in rows]
    assert pids == EXPECTED_IDS, pids
    assert set(class_of) == set(EXPECTED_IDS)
    for pid, status in rows:
        klass = class_of[pid]
        assert status.startswith(klass)
        # Exactly one class: the first matching prefix, and only that prefix.
        hits = [p for p in STATUS_PREFIXES if status.startswith(p)]
        assert hits == [klass], (pid, hits, klass)


def check_line_129_disagrees(stated_counts: dict, derived_counts: dict) -> None:
    assert stated_counts != derived_counts, RC02_RETIRE_MSG


def check_erratum_matches_derived(
    erratum: dict,
    derived_counts: dict[str, int],
    derived_members: dict[str, list[str]],
    stated_counts: dict[str, int],
    md_text: str,
) -> None:
    assert erratum["derived_counts"] == derived_counts
    assert erratum["derived_members"] == derived_members
    assert erratum["stated_counts"] == stated_counts
    md_stated, md_derived, md_members = parse_md_section9_table(md_text)
    assert md_stated == erratum["stated_counts"]
    assert md_derived == erratum["derived_counts"]
    assert md_members == erratum["derived_members"]


def test_rc_01_status_column_parsed():
    text = REGISTER_PATH.read_text(encoding="utf-8")
    _lines, rows, counts, members, class_of, _rc = parse_register(text)
    check_status_column_parsed(rows, class_of)
    assert sum(counts.values()) == 13
    for pid, _status in rows:
        klass = class_of[pid]
        assert pid in members[klass]


def test_rc_02_line_129_disagrees_with_status_column():
    text = REGISTER_PATH.read_text(encoding="utf-8")
    _lines, rows, derived_counts, _members, _class_of, rc_line = parse_register(text)
    stated_counts = parse_stated_counts(rc_line)
    check_line_129_disagrees(stated_counts, derived_counts)


def test_rc_03_erratum_matches_derived():
    text = REGISTER_PATH.read_text(encoding="utf-8")
    _lines, rows, derived_counts, derived_members, _class_of, rc_line = parse_register(
        text
    )
    stated_counts = parse_stated_counts(rc_line)
    erratum = load_erratum()
    md_text = MD_PATH.read_text(encoding="utf-8")
    check_erratum_matches_derived(
        erratum, derived_counts, derived_members, stated_counts, md_text
    )


def test_rc_04_erratum_pins_register_bytes():
    erratum = load_erratum()
    data = REGISTER_PATH.read_bytes()
    blob = git_blob_sha(data)
    assert erratum["register_blob"] == blob
    doc = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert erratum["register_blob"] == doc["amends_blob"]
    assert blob == doc["amends_blob"]


def test_rc_05_register_untouched():
    data = REGISTER_PATH.read_bytes()
    assert git_blob_sha(data) == REGISTER_BLOB


def test_rc_06_positive_controls():
    text = REGISTER_PATH.read_text(encoding="utf-8")
    lines, rows, derived_counts, derived_members, class_of, rc_line = parse_register(
        text
    )
    stated_counts = parse_stated_counts(rc_line)
    erratum = load_erratum()
    md_text = MD_PATH.read_text(encoding="utf-8")
    check_status_column_parsed(rows, class_of)
    check_line_129_disagrees(stated_counts, derived_counts)
    check_erratum_matches_derived(
        erratum, derived_counts, derived_members, stated_counts, md_text
    )

    # 1. Move one RETIRED-CONTAMINATED cell back to REGISTERED-GATED.
    mut_lines = list(lines)
    flipped = False
    for i, line in enumerate(mut_lines):
        if not line.strip().startswith("|"):
            continue
        cells = pipe_cells(line)
        if cells and cells[0] == "P01" and cells[-1].startswith("RETIRED-CONTAMINATED"):
            mut_lines[i] = line.replace("RETIRED-CONTAMINATED", "REGISTERED-GATED", 1)
            flipped = True
            break
    assert flipped, "P01 RETIRED-CONTAMINATED row not found for mutation"
    mut_text = "\n".join(mut_lines) + "\n"
    _h, _f, mut_rows = find_status_table(mut_text.splitlines())
    mut_counts, mut_members, mut_class = derive_counts_and_members(mut_rows)
    assert mut_counts != derived_counts
    assert mut_class["P01"] == "REGISTERED-GATED"
    with pytest.raises(AssertionError):
        check_erratum_matches_derived(
            erratum, mut_counts, mut_members, stated_counts, md_text
        )

    # 2. Edit the erratum's derived count for one class.
    tainted = copy.deepcopy(erratum)
    tainted["derived_counts"] = dict(tainted["derived_counts"])
    tainted["derived_counts"]["RETIRED-CONTAMINATED"] = (
        tainted["derived_counts"]["RETIRED-CONTAMINATED"] + 1
    )
    with pytest.raises(AssertionError):
        check_erratum_matches_derived(
            tainted, derived_counts, derived_members, stated_counts, md_text
        )

    # 3. Rewrite line 129 to the derived counts so the disagreement disappears.
    rewritten = rewrite_line_129_to_derived(derived_counts)
    stated_fixed = parse_stated_counts(rewritten)
    assert stated_fixed == derived_counts
    with pytest.raises(AssertionError, match="retire"):
        check_line_129_disagrees(stated_fixed, derived_counts)
