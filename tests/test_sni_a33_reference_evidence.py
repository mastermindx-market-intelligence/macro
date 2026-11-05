"""A33 reference-evidence checker tests (SNI commission 8659).

SNI-local DRAFT tests over the committed Alibaba E1 and Tencent E2
coverage reports. They consume owner-supplied cell values and never mint
issuer or security ids. All six authority flags stay literal False; a
caller that tries to set any of them true is refused (raise). Nothing
here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Fixtures are synthetic. The frozen 2026-08 behavioral pilot never counts
as real current evidence.
"""
from __future__ import annotations

import copy
import json
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPTANCE = REPO / "research" / "single_name_intelligence" / "acceptance"
sys.path.insert(0, str(ACCEPTANCE))

from a33_reference_evidence_check import (  # noqa: E402
    A33_CLASSES,
    AUTHORITY_FLAGS,
    PILOT_PREFIX,
    a33_class_table,
    real_cells,
    real_evidence_present,
    recount_statuses,
    reference_floor,
    refuse_authority_grant,
    structural_errors,
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


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _e1() -> dict:
    return _load(E1_PATH)


def _e2() -> dict:
    return _load(E2_PATH)


def _recompute_counts(metrics: dict) -> dict:
    return recount_statuses(metrics)


def test_a33_01_reports_are_structurally_sound():
    assert structural_errors(_e1()) == []
    assert structural_errors(_e2()) == []


def test_a33_02_real_evidence_present_for_both():
    e1 = _e1()
    e2 = _e2()
    e1_ok, e1_reasons = real_evidence_present(e1, REPO)
    e2_ok, e2_reasons = real_evidence_present(e2, REPO)
    e1_cells = real_cells(e1, REPO)
    e2_cells = real_cells(e2, REPO)
    print(f"Alibaba real_cells={len(e1_cells)}")
    print(f"Tencent real_cells={len(e2_cells)}")
    assert e1_ok is True, e1_reasons
    assert e2_ok is True, e2_reasons
    assert e1_cells
    assert e2_cells
    for key in e1_cells + e2_cells:
        assert not key.startswith(PILOT_PREFIX)


def test_a33_03_alibaba_meets_reference_floor():
    e1 = _e1()
    ok, reasons = reference_floor(e1, REPO)
    assert (ok, reasons) == (True, [])
    rows = a33_class_table(e1, REPO)
    assert [row["class"] for row in rows] == list(A33_CLASSES)
    for row in rows:
        assert row["best_status"] in ("OWNER_NATIVE", "PARTIAL")
        assert row["in_real_cells"] is True


def test_a33_04_tencent_floor_gap_is_exactly_named():
    """Pins the current honest Tencent A33 gap.

    identity_listing is REFUSED (issuer_subject missing in the Data OS
    identity owner) and corporate_actions_adjustment is ABSENT. When the
    Data OS identity owner or the corporate-actions owner closes it, this
    test must be updated together with the A33 matrix row, never loosened
    alone.
    """
    e2 = _e2()
    ok, reasons = reference_floor(e2, REPO)
    assert ok is False
    named: dict[str, str] = {}
    for item in reasons:
        cls, rest = item.split(":", 1)
        status = rest.strip().split()[0]
        named[cls.strip()] = status
    assert named == {
        "identity_listing": "REFUSED",
        "corporate_actions_adjustment": "ABSENT",
    }
    rows = a33_class_table(e2, REPO)
    by_cls = {row["class"]: row for row in rows}
    assert by_cls["identity_listing"]["in_real_cells"] is False
    assert by_cls["corporate_actions_adjustment"]["in_real_cells"] is False
    for cls in A33_CLASSES:
        if cls in named:
            continue
        assert by_cls[cls]["in_real_cells"] is True
        assert by_cls[cls]["best_status"] in ("OWNER_NATIVE", "PARTIAL")


def _all_absence(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    for cell in mutated["metrics"].values():
        cell["status"] = "ABSENT"
        cell["evidence_rows"] = 0
    mutated["counts"] = _recompute_counts(mutated["metrics"])
    return mutated


def _synthetic_owners(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    for cell in mutated["metrics"].values():
        if cell.get("status") in ("OWNER_NATIVE", "PARTIAL"):
            cell["owner"] = ["tests/fixtures/synthetic_issuer.py"]
    return mutated


def _pilot_only(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    for key, cell in mutated["metrics"].items():
        if key.startswith(PILOT_PREFIX):
            continue
        cell["status"] = "ABSENT"
        cell["evidence_rows"] = 0
    mutated["counts"] = _recompute_counts(mutated["metrics"])
    return mutated


def _authority_flipped(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    mutated["authority"]["signal_authority"] = True
    return mutated


def _authority_truthy_not_false(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    mutated["authority"]["rank_authority"] = 0
    return mutated


def _counts_mismatch(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    mutated["counts"]["PARTIAL"] = int(mutated["counts"]["PARTIAL"]) + 1
    return mutated


def _best_status_self_upgrade(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    mutated["a33_required_source_classes"]["identity_listing"][
        "best_status"
    ] = "OWNER_NATIVE"
    return mutated


def _owner_native_cell_forged(report: dict) -> dict:
    mutated = copy.deepcopy(report)
    info = mutated["a33_required_source_classes"]["identity_listing"]
    info["owner_native_cell"] = info["best_cell"]
    return mutated


def _missing_owner_path(report: dict) -> tuple[dict, str]:
    mutated = copy.deepcopy(report)
    cells = real_cells(mutated, REPO)
    target = cells[0]
    mutated["metrics"][target]["owner"] = ["engine/does_not_exist_sni.py"]
    return mutated, target


@pytest.mark.parametrize(
    "mutant",
    [
        "all_absence",
        "synthetic_owners",
        "pilot_only",
        "authority_flipped",
        "authority_truthy_not_false",
        "counts_mismatch",
        "best_status_self_upgrade",
        "owner_native_cell_forged",
        "missing_owner_path",
    ],
)
def test_a33_05_mutants_are_refused(mutant: str):
    e1 = _e1()
    e2 = _e2()
    if mutant == "all_absence":
        mutated = _all_absence(e1)
        assert real_evidence_present(mutated, REPO)[0] is False
        return
    if mutant == "synthetic_owners":
        mutated = _synthetic_owners(e1)
        assert real_evidence_present(mutated, REPO)[0] is False
        return
    if mutant == "pilot_only":
        mutated = _pilot_only(e1)
        cells = real_cells(mutated, REPO)
        assert cells == []
        assert all(
            not key.startswith(PILOT_PREFIX)
            for key in cells
        )
        assert real_evidence_present(mutated, REPO)[0] is False
        return
    if mutant == "authority_flipped":
        mutated = _authority_flipped(e1)
        assert structural_errors(mutated) != []
        with pytest.raises(ValueError):
            refuse_authority_grant(mutated["authority"])
        return
    if mutant == "authority_truthy_not_false":
        mutated = _authority_truthy_not_false(e1)
        assert structural_errors(mutated) != []
        return
    if mutant == "counts_mismatch":
        mutated = _counts_mismatch(e1)
        assert structural_errors(mutated) != []
        return
    if mutant == "best_status_self_upgrade":
        mutated = _best_status_self_upgrade(e2)
        assert structural_errors(mutated) != []
        return
    if mutant == "owner_native_cell_forged":
        mutated = _owner_native_cell_forged(e2)
        assert structural_errors(mutated) != []
        return
    if mutant == "missing_owner_path":
        mutated, target = _missing_owner_path(e1)
        assert target not in real_cells(mutated, REPO)
        return
    raise AssertionError(f"unknown mutant {mutant}")


def test_a33_06_floor_mutant_cannot_pass_by_editing_summary():
    mutated = copy.deepcopy(_e2())
    a33 = mutated["a33_required_source_classes"]
    a33["identity_listing"]["best_status"] = "PARTIAL"
    a33["corporate_actions_adjustment"]["best_status"] = "PARTIAL"
    assert structural_errors(mutated) != []
    ok, _reasons = reference_floor(mutated, REPO)
    assert ok is False


def test_a33_07_checker_is_pure(monkeypatch):
    calls: list[str] = []

    def boom(*_args, **_kwargs):
        calls.append("called")
        raise RuntimeError("subprocess/network forbidden in A33 checker")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(urllib.request, "urlopen", boom)

    e1 = _e1()
    e2 = _e2()

    def _run_all(report: dict) -> tuple:
        return (
            structural_errors(report),
            real_cells(report, REPO),
            real_evidence_present(report, REPO),
            reference_floor(report, REPO),
            a33_class_table(report, REPO),
        )

    first_e1 = _run_all(e1)
    second_e1 = _run_all(e1)
    first_e2 = _run_all(e2)
    second_e2 = _run_all(e2)
    assert calls == []
    assert first_e1 == second_e1
    assert first_e2 == second_e2


def test_a33_authority_record_stays_literal_false():
    for name in AUTHORITY_FLAGS:
        assert _e1()["authority"][name] is False
        assert _e2()["authority"][name] is False
    refuse_authority_grant(_e1()["authority"])
    refuse_authority_grant(_e2()["authority"])
