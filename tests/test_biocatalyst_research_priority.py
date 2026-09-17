from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from engine.biocatalyst.research_priority import (
    ResearchPriorityError,
    classify_research_priority,
    interval_overlaps_horizon,
    sort_research_priority_rows,
)

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "research/biocatalyst_decision_intelligence_v3/BIOCATALYST_RP_V1_ACCEPTANCE_CASES_2026-09-06.json").read_text())


def _case_input(case):
    row = deepcopy(FIXTURE["base"])
    row.update(case.get("set", {}))
    return row


def _outcome(row):
    try:
        result = classify_research_priority(
            row,
            evaluation_cutoff=FIXTURE["evaluation_cutoff"],
            anchor_date=FIXTURE["anchor_date"],
        )
    except ResearchPriorityError:
        return "REJECT"
    return result["disposition"] if result["disposition"] != "SELECTED" else result["lane"]


def test_all_normative_lane_cases_execute_against_real_classifier() -> None:
    failures = []
    for case in FIXTURE["lane_cases"]:
        actual = _outcome(_case_input(case))
        if actual != case["expected"]:
            failures.append((case["id"], case["expected"], actual))
    assert failures == []


def test_all_normative_horizon_boundaries_execute() -> None:
    for case in FIXTURE["horizon_cases"]:
        assert interval_overlaps_horizon(
            case["lower"], case["upper"],
            anchor_date=FIXTURE["anchor_date"], days=case["days"],
        ) is case["expected"], case


def test_normative_ordering_and_tie_breaks_execute() -> None:
    by_id = {case["id"]: case for case in FIXTURE["lane_cases"]}
    rows = []
    for case_id in FIXTURE["ordering_cases"][0]["input"]:
        source = _case_input(by_id[case_id])
        classified = classify_research_priority(
            source,
            evaluation_cutoff=FIXTURE["evaluation_cutoff"],
            anchor_date=FIXTURE["anchor_date"],
        )
        rows.append({"id": case_id, **source, "research_priority": classified})
    assert [row["id"] for row in sort_research_priority_rows(rows)] == FIXTURE["ordering_cases"][0]["expected"]

    base = deepcopy(FIXTURE["base"])
    rev_rows = []
    for item in FIXTURE["tie_cases"]["revision_rows"]:
        row = {**base, **item}
        row["research_priority"] = classify_research_priority(row, evaluation_cutoff=FIXTURE["evaluation_cutoff"], anchor_date=FIXTURE["anchor_date"])
        rev_rows.append(row)
    assert [row["id"] for row in sort_research_priority_rows(rev_rows)] == FIXTURE["tie_cases"]["revision_expected"]

    exposure_rows = []
    for item in FIXTURE["tie_cases"]["exposure_rows"]:
        row = {**base, **item}
        row["research_priority"] = classify_research_priority(row, evaluation_cutoff=FIXTURE["evaluation_cutoff"], anchor_date=FIXTURE["anchor_date"])
        exposure_rows.append(row)
    assert [row["id"] for row in sort_research_priority_rows(exposure_rows)] == FIXTURE["tie_cases"]["exposure_expected"]


def test_classifier_reports_all_independent_gaps_in_frozen_order() -> None:
    row = deepcopy(FIXTURE["base"])
    row.update({
        "source_health": "stale",
        "identity_state": "unresolved",
        "timing_state": "conflicted",
        "lower_date": None,
        "upper_date": None,
    })
    result = classify_research_priority(row, evaluation_cutoff=FIXTURE["evaluation_cutoff"], anchor_date=FIXTURE["anchor_date"])
    assert result["lane"] == "RECONCILE"
    assert result["primary_reason"] == "SOURCE_NOT_CURRENT"
    assert result["gap_reasons"] == ["SOURCE_NOT_CURRENT", "IDENTITY_UNRESOLVED", "TIMING_CONFLICT", "TIMING_INCOMPLETE"]


def test_classifier_authority_is_research_only() -> None:
    result = classify_research_priority(deepcopy(FIXTURE["base"]), evaluation_cutoff=FIXTURE["evaluation_cutoff"], anchor_date=FIXTURE["anchor_date"])
    assert result["method_id"] == "biocatalyst.research_triage.v1"
    assert result["authority"] == {
        "classification": "research_priority_only",
        "trade_origination": False,
        "changes_availability": False,
        "position_sizing": False,
        "prophet_admission": False,
    }
