"""Issuer-class applicability for statement detectors (FIF E0 / A30)."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from engine.fundamental_forensics import load_registry, run_fixture_slice
from engine.fundamental_forensics.detectors import (
    DETECTOR_APPLICABILITY,
    ISSUER_CLASSES,
    NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,
    NOT_EVALUABLE_REASONS,
    evaluate_detectors,
    issuer_class_for_sic,
)
from engine.fundamental_forensics.models import canonical_json


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "fundamental_forensics"
REGISTRY_PATH = ROOT / "config" / "fundamental_forensics.yml"

INDUSTRIAL_DETECTORS = (
    "margin_compression_despite_revenue_growth",
    "receivables_stretch",
    "inventory_build",
    "capital_intensity_rising",
)
ACCRUALS_DETECTOR = "accruals_trending_up"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _slice(submissions=None):
    return run_fixture_slice(
        _load("companyfacts_versions.json"),
        submissions if submissions is not None else _load("submissions_versions.json"),
        load_registry(REGISTRY_PATH),
        as_of="2025-12-31T23:59:59Z",
        recorded_at="2026-08-01T12:00:00Z",
        computed_at="2026-08-01T12:05:00Z",
        knowledge_clock="source_event",
        vintage_policy="latest_known",
    )


def _selected(result):
    selected_ids = set(result.selected_vintage_ids)
    return tuple(
        item for item in result.statement_vintages if item.vintage_id in selected_ids
    )


def _evaluate(result, issuer_sic=None, *, omit_sic: bool = False):
    kwargs = {
        "computed_at": result.computed_at,
        "entity_cik": result.entity_cik,
    }
    if not omit_sic:
        kwargs["issuer_sic"] = issuer_sic
    return evaluate_detectors(
        result.observations,
        _selected(result),
        load_registry(REGISTRY_PATH),
        **kwargs,
    )


def _finding_bytes(findings) -> str:
    return canonical_json([item.to_dict() for item in findings])


def _by_id(findings):
    return {item.detector_id: item for item in findings}


@pytest.mark.parametrize(
    ("sic", "expected"),
    [
        (None, "unknown"),
        ("", "unknown"),
        ("   ", "unknown"),
        ("abc", "unknown"),
        ("6021.0", "unknown"),
        (True, "unknown"),
        (False, "unknown"),
        (-1, "unknown"),
        ("-6021", "unknown"),
        (6019, "industrial"),
        (6020, "bank"),
        ("6020", "bank"),
        (6021, "bank"),
        ("6021", "bank"),
        (6199, "bank"),
        (6200, "industrial"),
        (6709, "industrial"),
        (6710, "bank"),
        (6719, "bank"),
        (6720, "industrial"),
        (6299, "industrial"),
        (6300, "insurance"),
        ("6300", "insurance"),
        (6411, "insurance"),
        (6412, "industrial"),
        (6797, "industrial"),
        (6798, "reit"),
        ("6798", "reit"),
        (6799, "industrial"),
        (4899, "industrial"),
        (4900, "utility"),
        (4991, "utility"),
        (4992, "industrial"),
        (7369, "industrial"),
        (7370, "software"),
        (7379, "software"),
        ("7372", "software"),
        (7380, "industrial"),
        (3571, "industrial"),
        ("3571", "industrial"),
        (0, "industrial"),
        (9999, "industrial"),
    ],
)
def test_issuer_class_for_sic_boundaries(sic, expected) -> None:
    assert issuer_class_for_sic(sic) == expected


def test_detector_applicability_table() -> None:
    assert ISSUER_CLASSES == frozenset(
        {"industrial", "software", "bank", "insurance", "reit", "utility", "unknown"}
    )
    industrial_or_software = frozenset({"industrial", "software"})
    for detector_id in INDUSTRIAL_DETECTORS:
        assert DETECTOR_APPLICABILITY[detector_id] == industrial_or_software
    assert DETECTOR_APPLICABILITY[ACCRUALS_DETECTOR] == ISSUER_CLASSES - frozenset(
        {"bank", "insurance"}
    )


def test_not_applicable_reason_is_registered() -> None:
    assert (
        NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS
        == "not_applicable_for_issuer_class"
    )
    assert NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS in NOT_EVALUABLE_REASONS


def test_bank_sic_gates_four_industrial_detectors() -> None:
    findings = _evaluate(_slice(), issuer_sic="6021")
    by_id = _by_id(findings)
    for detector_id in INDUSTRIAL_DETECTORS:
        finding = by_id[detector_id]
        assert finding.state.value == "not_evaluable"
        assert finding.missing_inputs == (
            NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,
        )
        assert finding.limitations == ("issuer_class:bank",)
        assert finding.applicability == "insufficient_evidence"


def test_bank_sic_gates_accruals() -> None:
    finding = _by_id(_evaluate(_slice(), issuer_sic=6021))[ACCRUALS_DETECTOR]
    assert finding.state.value == "not_evaluable"
    assert finding.missing_inputs == (
        NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,
    )
    assert finding.limitations == ("issuer_class:bank",)


def test_aapl_sic_3571_findings_match_ungated() -> None:
    result = _slice()
    ungated = _evaluate(result, issuer_sic=None)
    aapl = _evaluate(result, issuer_sic="3571")
    assert _finding_bytes(aapl) == _finding_bytes(ungated)
    assert {item.detector_id: item.state.value for item in aapl} == {
        detector_id: "triggered"
        for detector_id in (*INDUSTRIAL_DETECTORS, ACCRUALS_DETECTOR)
    }


def test_issuer_sic_none_is_byte_identical_to_today() -> None:
    result = _slice()
    today = _evaluate(result, omit_sic=True)
    none_path = _evaluate(result, issuer_sic=None)
    assert _finding_bytes(none_path) == _finding_bytes(today)
    assert {item.state.value for item in none_path} == {"triggered"}
    assert len(none_path) == 5


def test_unknown_sic_follows_none_path() -> None:
    result = _slice()
    none_path = _evaluate(result, issuer_sic=None)
    for unknown in ("", "not-a-sic", "12.5", "zzzz", "6021.0"):
        assert issuer_class_for_sic(unknown) == "unknown"
        assert _finding_bytes(_evaluate(result, issuer_sic=unknown)) == _finding_bytes(
            none_path
        )


def test_insurance_gates_industrial_and_accruals() -> None:
    by_id = _by_id(_evaluate(_slice(), issuer_sic=6300))
    for detector_id in (*INDUSTRIAL_DETECTORS, ACCRUALS_DETECTOR):
        finding = by_id[detector_id]
        assert finding.state.value == "not_evaluable"
        assert (
            NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS
            in finding.missing_inputs
        )
        assert finding.limitations == ("issuer_class:insurance",)


def test_software_sic_does_not_gate_statement_detectors() -> None:
    result = _slice()
    software = _evaluate(result, issuer_sic=7372)
    assert _finding_bytes(software) == _finding_bytes(_evaluate(result, issuer_sic=None))


@pytest.mark.parametrize("sic", [6798, 4900])
def test_reit_and_utility_gate_industrial_keep_accruals(sic) -> None:
    by_id = _by_id(_evaluate(_slice(), issuer_sic=sic))
    issuer_class = issuer_class_for_sic(sic)
    for detector_id in INDUSTRIAL_DETECTORS:
        finding = by_id[detector_id]
        assert finding.state.value == "not_evaluable"
        assert finding.missing_inputs == (
            NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,
        )
        assert finding.limitations == (f"issuer_class:{issuer_class}",)
    assert by_id[ACCRUALS_DETECTOR].state.value == "triggered"


def test_pipeline_threads_submissions_sic_for_bank_class() -> None:
    submissions = deepcopy(_load("submissions_versions.json"))
    submissions["sic"] = "6021"
    by_id = _by_id(_slice(submissions).findings)
    for detector_id in (*INDUSTRIAL_DETECTORS, ACCRUALS_DETECTOR):
        finding = by_id[detector_id]
        assert finding.state.value == "not_evaluable"
        assert (
            NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS
            in finding.missing_inputs
        )
        assert "issuer_class:bank" in finding.limitations
