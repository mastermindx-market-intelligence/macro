"""MUT4E killing tests for A33 checker and acceptance-matrix renderer.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false.
Fixtures are synthetic. Nothing here feeds a ranker, gate, sizer, signal,
escalation, or trade path.

Each test_mut4e_<module>_<function>_<n> docstring names the surviving mutant
from the 2026-10-13 sweep (seed 20261013).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
sys.path.insert(0, str(ACCEPTANCE))

import render_matrix as render_matrix_mod  # noqa: E402
from a33_reference_evidence_check import (  # noqa: E402
    _class_gap_reason,
    a33_class_table,
    owner_path_error,
    real_cells,
    reference_floor,
)
from render_matrix import (  # noqa: E402
    _is_done_evidence_path,
    check_counts,
    check_done_status_law,
    check_gated_status_law,
    check_main_evidence_paths,
    check_non_done_gaps,
)

E1_PATH = (
    REPO
    / "research"
    / "single_name_intelligence"
    / "evidence"
    / "Alibaba"
    / "E1_COVERAGE_REPORT_2026-10-11.json"
)
E2_PATH = (
    REPO
    / "research"
    / "single_name_intelligence"
    / "evidence"
    / "Tencent"
    / "E2_COVERAGE_REPORT_2026-10-11.json"
)
JSON_PATH = ACCEPTANCE / "ACCEPTANCE_EVIDENCE_MATRIX.json"
SYNTHETIC_OWNER = "collectors/equity_earnings.py"


def _e1() -> dict:
    return json.loads(E1_PATH.read_text(encoding="utf-8"))


def _e2() -> dict:
    return json.loads(E2_PATH.read_text(encoding="utf-8"))


def _matrix() -> dict:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def _first_real_key(report: dict) -> str:
    keys = real_cells(report, REPO)
    assert keys, "expected at least one real current evidence cell"
    return keys[0]


def _live_best_cell_not_real(report: dict) -> dict:
    """Keep best_status live but drop that best_cell from real_cells."""
    mutated = copy.deepcopy(report)
    info = mutated["a33_required_source_classes"]["identity_listing"]
    cell_key = info["best_cell"]
    mutated["metrics"][cell_key]["evidence_rows"] = 0
    return mutated


def _done_case_with_evidence(evidence: list[dict]) -> dict:
    doc = copy.deepcopy(_matrix())
    done = next(item for item in doc["cases"] if item["status"] == "DONE")
    done["gated_on"] = None
    done["gap"] = ""
    done["evidence"] = evidence
    return doc


# ---------------------------------------------------------------------------
# a33_reference_evidence_check.py survivors
# ---------------------------------------------------------------------------


def test_mut4e_a33_reference_evidence_check__class_gap_reason_1():
    """a33_reference_evidence_check.py:276, `or` -> `and` (blocking or [])."""
    reason = _class_gap_reason(
        "identity_listing",
        {
            "best_status": "REFUSED",
            "blocking_missing_descriptors": ["issuer_subject"],
        },
    )
    assert reason == "identity_listing: REFUSED (issuer_subject)"


def test_mut4e_a33_reference_evidence_check__class_gap_reason_2():
    """a33_reference_evidence_check.py:283, return f'{cls}: {status}' -> None."""
    reason = _class_gap_reason("financials", {"best_status": "ABSENT"})
    assert reason == "financials: ABSENT"


def test_mut4e_a33_reference_evidence_check_owner_path_error_1():
    """a33_reference_evidence_check.py:222, return prefix-not-allowed -> None."""
    assert owner_path_error("tmp/nope.py", REPO) == (
        "owner prefix not allowed (not guessed): tmp/nope.py"
    )


def test_mut4e_a33_reference_evidence_check_owner_path_error_2():
    """a33_reference_evidence_check.py:210, tests/ check `or` -> `and`."""
    assert owner_path_error("tests/foo.py", REPO) == (
        "owner sits under tests/: tests/foo.py"
    )
    assert owner_path_error("tests", REPO) == "owner sits under tests/: tests"


def test_mut4e_a33_reference_evidence_check_owner_path_error_3():
    """a33_reference_evidence_check.py:205, return non-string error -> None."""
    assert owner_path_error(123, REPO) == "owner path is not a string: 123"


def test_mut4e_a33_reference_evidence_check_real_cells_1():
    """a33_reference_evidence_check.py:246, `or` -> `and` (non-int rows)."""
    report = copy.deepcopy(_e1())
    key = _first_real_key(report)
    report["metrics"][key]["evidence_rows"] = 1.5
    report["metrics"][key]["status"] = "PARTIAL"
    report["metrics"][key]["owner"] = [SYNTHETIC_OWNER]
    assert key not in real_cells(report, REPO)


def test_mut4e_a33_reference_evidence_check_real_cells_2():
    """a33_reference_evidence_check.py:246, `rows <= 0` -> `rows < 0`."""
    report = copy.deepcopy(_e1())
    key = _first_real_key(report)
    report["metrics"][key]["evidence_rows"] = 0
    report["metrics"][key]["status"] = "PARTIAL"
    report["metrics"][key]["owner"] = [SYNTHETIC_OWNER]
    assert key not in real_cells(report, REPO)


def test_mut4e_a33_reference_evidence_check_reference_floor_1():
    """a33_reference_evidence_check.py:311, `live_ok and in_real` -> `or`."""
    report = _live_best_cell_not_real(_e1())
    ok, reasons = reference_floor(report, REPO)
    assert ok is False
    assert any(item.startswith("identity_listing:") for item in reasons)


def test_mut4e_a33_reference_evidence_check_reference_floor_2():
    """a33_reference_evidence_check.py:310, isinstance(str) and in cells -> or."""
    report = _live_best_cell_not_real(_e1())
    ok, reasons = reference_floor(report, REPO)
    assert ok is False
    assert any(item.startswith("identity_listing:") for item in reasons)


def test_mut4e_a33_reference_evidence_check_a33_class_table_1():
    """a33_reference_evidence_check.py:333, blocking or [] -> and."""
    rows = a33_class_table(_e2(), REPO)
    by_cls = {row["class"]: row for row in rows}
    assert by_cls["identity_listing"]["blocking_missing_descriptors"] == [
        "issuer_subject"
    ]


# ---------------------------------------------------------------------------
# render_matrix.py survivors
# ---------------------------------------------------------------------------


def test_mut4e_render_matrix__is_done_evidence_path_1():
    """render_matrix.py:61, return startswith(RUNS_PREFIX) -> None."""
    assert (
        _is_done_evidence_path(
            "research/single_name_intelligence/runs/synthetic.json"
        )
        is True
    )


def test_mut4e_render_matrix__is_done_evidence_path_2():
    """render_matrix.py:60, return True -> False (test_sni path)."""
    assert _is_done_evidence_path("tests/test_sni_foo.py") is True


def test_mut4e_render_matrix__is_done_evidence_path_3():
    """render_matrix.py:60, return True -> None (test_sni path)."""
    assert _is_done_evidence_path("tests/test_sni_foo.py") is True


def test_mut4e_render_matrix_check_counts_1():
    """render_matrix.py:137, delete counts-mismatch raise guard."""
    doc = copy.deepcopy(_matrix())
    doc["counts"] = dict(doc["counts"])
    doc["counts"]["DONE"] = int(doc["counts"]["DONE"]) + 7
    with pytest.raises(AssertionError, match="counts"):
        check_counts(doc)


def test_mut4e_render_matrix_check_gated_status_law_1():
    """render_matrix.py:110, delete 'R1' not in gap raise guard."""
    doc = copy.deepcopy(_matrix())
    gated = next(item for item in doc["cases"] if item["status"] == "GATED")
    gated["gated_on"] = "R1"
    gated["gap"] = "waiting on an unnamed owner release"
    with pytest.raises(AssertionError, match="does not say what R1"):
        check_gated_status_law(doc)


def test_mut4e_render_matrix_check_non_done_gaps_1():
    """render_matrix.py:120, delete gap-must-be-string raise guard."""
    doc = copy.deepcopy(_matrix())
    doc["cases"][0]["gap"] = None
    with pytest.raises(AssertionError, match="gap must be a string"):
        check_non_done_gaps(doc)


def test_mut4e_render_matrix_check_non_done_gaps_2():
    """render_matrix.py:123, delete DONE-gap-must-be-empty raise guard."""
    doc = copy.deepcopy(_matrix())
    done = next(item for item in doc["cases"] if item["status"] == "DONE")
    done["gap"] = "should be empty on DONE"
    with pytest.raises(AssertionError, match="DONE gap must be empty"):
        check_non_done_gaps(doc)


def test_mut4e_render_matrix_check_done_status_law_1():
    """render_matrix.py:87, ok = False -> True."""
    doc = _done_case_with_evidence(
        [
            {
                "ref": "main",
                "path": "research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md",
                "note": "synthetic non-test non-runs path",
            }
        ]
    )
    with pytest.raises(AssertionError, match="DONE without"):
        check_done_status_law(doc, REPO)


def test_mut4e_render_matrix_check_done_status_law_2():
    """render_matrix.py:89, ref==main and done-path -> or."""
    doc = _done_case_with_evidence(
        [
            {
                "ref": "census",
                "path": "research/single_name_intelligence/runs/s2_event_response_v1_1/REPORT.md",
                "note": "synthetic census ref on a runs/ artifact",
            }
        ]
    )
    with pytest.raises(AssertionError, match="DONE without"):
        check_done_status_law(doc, REPO)


def test_mut4e_render_matrix_check_main_evidence_paths_1():
    """render_matrix.py:71, delete missing-file raise guard."""
    doc = copy.deepcopy(_matrix())
    case = doc["cases"][0]
    for item in case["evidence"]:
        if item["ref"] == "main":
            item["path"] = (
                "research/single_name_intelligence/does_not_exist_mut4e.md"
            )
            break
    else:
        raise AssertionError("expected a main evidence path to poison")
    with pytest.raises(AssertionError, match="main evidence missing"):
        check_main_evidence_paths(doc, REPO)


def test_mut4e_render_matrix_main_1(monkeypatch):
    """render_matrix.py:219, Path parent / json name -> *."""
    written: list[str] = []

    def fake_write(self, *args, **kwargs):
        written.append(str(self))
        return None

    monkeypatch.setattr(Path, "write_text", fake_write)
    render_matrix_mod.main()
    assert written, "main must construct the JSON path and write markdown"
