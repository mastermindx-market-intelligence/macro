"""Fixture tests for the T15 transition-increment scaffold.

One test per mission item (a)-(f). Each assertion is also run against a
deliberately wrong toy so a zero-fill, a dropped row, a detection row in
the advance-match set, a non-primary cell, or a recomputed R9 count fails.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "research" / "crypto_science" / "t15_transition_increment.py"
)
_SPEC = importlib.util.spec_from_file_location("t15_transition_increment_scaffold", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
t15 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(t15)

_T0 = datetime(2026, 1, 1, 0, 0, 0)
_HOUR = timedelta(hours=1)

_QUOTED = {
    "full_all_event_recall": (20, 78),
    "full_supported_event_recall": (20, 37),
    "recent_all_event_recall": (1, 15),
    "recent_supported_event_recall": (1, 5),
}


def _no_numbers(payload: object) -> None:
    if isinstance(payload, str):
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert isinstance(key, str)
            _no_numbers(value)
        return
    raise AssertionError(f"loader payload contains a non-string: {payload!r}")


def test_a_absent_r9_module_is_unavailable_and_not_a_number(tmp_path: Path) -> None:
    def _assert_absent(payload: dict) -> None:
        assert payload["status"] == "unavailable"
        assert payload["module"] == "research/crypto_science/r9_prebreak_study.py"
        assert payload["import_name"] == "research.crypto_science.r9_prebreak_study"
        assert payload["reason"] == "module_absent"
        _no_numbers(payload)

    absent = t15.load_r9_prebreak_study(tmp_path)
    _assert_absent(absent)
    _assert_absent(t15.load_r9_prebreak_study())

    present = tmp_path / "research" / "crypto_science"
    present.mkdir(parents=True)
    # Executing this file would abort the test. The loader must not import it.
    (present / "r9_prebreak_study.py").write_text("raise SystemExit('r9 must not be executed')\n")
    held = t15.load_r9_prebreak_study(tmp_path)
    assert held["status"] == "present_not_executed"
    assert held["module"] == "research/crypto_science/r9_prebreak_study.py"
    assert held["reason"] == "not_executed"
    _no_numbers(held)

    def _wrong_loader(_root=None):
        return {
            "status": "unavailable",
            "module": "research/crypto_science/r9_prebreak_study.py",
            "import_name": "research.crypto_science.r9_prebreak_study",
            "reason": "module_absent",
            "lift": 0,
        }

    with pytest.raises(AssertionError):
        _assert_absent(_wrong_loader())


def test_b_detection_at_or_before_break_is_refused_and_cannot_match() -> None:
    rows = [
        {
            "row_id": "det-after",
            "event_id": "e-after",
            "role": "detection",
            "break_issue": _T0,
            "action_reference": _T0 + _HOUR,
        },
        {
            "row_id": "det-at",
            "event_id": "e-at",
            "role": "detection",
            "break_issue": _T0,
            "action_reference": _T0,
        },
        {
            "row_id": "det-before",
            "event_id": "e-before",
            "role": "detection",
            "break_issue": _T0,
            "action_reference": _T0 - _HOUR,
        },
        {
            "row_id": "det-after",
            "event_id": "e-after",
            "role": "advance",
            "break_issue": _T0,
            "action_reference": _T0 - _HOUR,
        },
        {
            "row_id": "adv-before",
            "event_id": "e-adv",
            "role": "advance",
            "break_issue": _T0,
            "action_reference": _T0 - _HOUR,
        },
        {
            "row_id": "adv-after",
            "event_id": "e-late",
            "role": "advance",
            "break_issue": _T0,
            "action_reference": _T0 + _HOUR,
        },
    ]

    def _assert_cohorts(result: dict) -> None:
        detection_ids = {row["row_id"] for row in result["detection"]}
        advance_ids = {row["row_id"] for row in result["advance_match"]}
        refused = {(row["row_id"], row["reason"]) for row in result["refused"]}
        assert detection_ids.isdisjoint(advance_ids)
        assert result["detection_row_ids_in_advance_match"] == []
        assert detection_ids == {"det-after"}
        assert advance_ids == {"adv-before"}
        assert ("det-at", "detection_action_at_or_before_break") in refused
        assert ("det-before", "detection_action_at_or_before_break") in refused
        assert ("det-after", "detection_row_banned_from_advance_match") in refused
        assert ("adv-after", "advance_action_at_or_after_break") in refused
        assert "det-at" not in detection_ids
        assert "det-before" not in detection_ids
        assert "adv-after" not in advance_ids
        assert result["quoted_r9_counts"] == _QUOTED

    _assert_cohorts(t15.assign_cohorts(rows))

    def _wrong_leak(source):
        return {
            "detection": list(source),
            "advance_match": list(source),
            "refused": [],
            "detection_row_ids_in_advance_match": [],
            "quoted_r9_counts": dict(_QUOTED),
        }

    with pytest.raises(AssertionError):
        _assert_cohorts(_wrong_leak(rows))


def test_c_ledger_keeps_unavailable_and_unmatched_without_zero_fill() -> None:
    events = [
        {
            "event_id": "both-ok",
            "detection_status": "ok",
            "advance_status": "ok",
            "detection_dr": 2,
            "advance_dr": 2,
            "detection_du": 5,
            "advance_du": 1,
        },
        {
            "event_id": "det-missing",
            "detection_status": "account_unavailable",
            "advance_status": "ok",
            "detection_dr": 0,
            "detection_du": 0,
            "advance_dr": 4,
            "advance_du": 4,
        },
        {
            "event_id": "unmatched",
            "detection_status": "ok",
            "advance_status": "unmatched",
            "detection_dr": 7,
            "detection_du": 7,
            "advance_dr": 0,
            "advance_du": 0,
        },
        {
            "event_id": "neighbor-ok",
            "detection_status": "ok",
            "advance_status": "ok",
            "detection_dr": 9,
            "advance_dr": 1,
            "detection_du": 8,
            "advance_du": 3,
        },
    ]

    def _assert_ledger(source, result: dict) -> None:
        ledger = result["ledger"]
        assert [row["event_id"] for row in ledger] == [event["event_id"] for event in source]
        paired_ids = {row["event_id"] for row in result["paired"]}
        by_id = {row["event_id"]: row for row in ledger}
        assert set(by_id) == {event["event_id"] for event in source}
        for event in source:
            row = by_id[event["event_id"]]
            assert row["detection_status"] == event["detection_status"]
            assert row["advance_status"] == event["advance_status"]
            both_ok = event["detection_status"] == "ok" and event["advance_status"] == "ok"
            if both_ok:
                assert event["event_id"] in paired_ids
                assert row["paired_dr"] == event["detection_dr"] - event["advance_dr"]
                assert row["paired_du"] == event["detection_du"] - event["advance_du"]
            else:
                assert event["event_id"] not in paired_ids
                assert row["paired_dr"] == "unavailable"
                assert row["paired_du"] == "unavailable"
        assert by_id["det-missing"]["paired_dr"] != by_id["neighbor-ok"]["paired_dr"]
        assert by_id["unmatched"]["paired_dr"] != 0
        assert by_id["both-ok"]["paired_dr"] == 0
        assert by_id["both-ok"]["paired_du"] == 4

    _assert_ledger(events, t15.pair_accounts(events))

    def _wrong_zero_fill_and_drop(source):
        ledger = []
        paired = []
        for event in source:
            if event["advance_status"] == "unmatched":
                continue
            both_ok = event["detection_status"] == "ok" and event["advance_status"] == "ok"
            if both_ok:
                row = {
                    "event_id": event["event_id"],
                    "detection_status": event["detection_status"],
                    "advance_status": event["advance_status"],
                    "paired_dr": event["detection_dr"] - event["advance_dr"],
                    "paired_du": event["detection_du"] - event["advance_du"],
                }
            else:
                row = {
                    "event_id": event["event_id"],
                    "detection_status": event["detection_status"],
                    "advance_status": event["advance_status"],
                    "paired_dr": 0,
                    "paired_du": 0,
                }
            ledger.append(row)
            paired.append(row)
        return {"ledger": ledger, "paired": paired}

    with pytest.raises(AssertionError):
        _assert_ledger(events, _wrong_zero_fill_and_drop(events))


def test_d_ambiguous_and_censored_windows_are_typed_exclusions() -> None:
    ambiguous = {
        "open": 100.0,
        "high": 104.0,
        "low": 94.0,
        "lower_barrier": 95.0,
        "upper_barrier": 103.0,
        "category": "lower_first",
        "path_return": 0,
    }
    censored = {
        "censored": True,
        "complete": False,
        "open": 100.0,
        "high": 100.0,
        "low": 90.0,
        "lower_barrier": 95.0,
        "upper_barrier": 103.0,
        "path_return": 0,
    }

    def _assert_exclusion(result: dict, kind: str) -> None:
        assert result["exclusion"] == kind
        assert result["category"] == kind
        assert result["category"] != "lower_first"
        assert result["false_window"] is False
        assert result["path_return"] == "unavailable"
        assert result["path_return"] != 0
        assert result["y"] == "unavailable"
        assert result["y"] != 0
        assert result["scored"] is False

    _assert_exclusion(t15.classify_window(ambiguous), "ambiguous")
    _assert_exclusion(t15.classify_window(censored), "censored")
    flagged = dict(ambiguous)
    flagged["ambiguous"] = True
    _assert_exclusion(t15.classify_window(flagged), "ambiguous")

    def _wrong_score(_window):
        return {
            "exclusion": None,
            "category": "lower_first",
            "y": 0,
            "false_window": True,
            "path_return": 0,
            "scored": True,
        }

    with pytest.raises(AssertionError):
        _assert_exclusion(_wrong_score(ambiguous), "ambiguous")


def test_e_paired_difference_is_primary_cell_only() -> None:
    rows = [
        {
            "event_id": "p1",
            "detection_status": "ok",
            "advance_status": "ok",
            "detection_dr": 5,
            "advance_dr": 2,
            "detection_du": 1,
            "advance_du": 4,
        },
        {
            "event_id": "p2",
            "detection_status": "ok",
            "advance_status": "ok",
            "detection_dr": 0,
            "advance_dr": 4,
            "detection_du": 2,
            "advance_du": 2,
        },
    ]
    result = t15.paired_primary_differences(rows, lag_hours=1, cost_bps=10, threshold=0.10)
    assert result["cell"] == "1h_10bp"
    assert result["template_cell"] == "unfilled"
    assert "mean_paired_dr" not in result
    assert "mean_paired_du" not in result
    by_id = {row["event_id"]: row for row in result["pairs"]}
    assert by_id["p1"]["paired_dr"] == 3
    assert by_id["p1"]["paired_du"] == -3
    assert by_id["p2"]["paired_dr"] == -4
    assert by_id["p2"]["paired_du"] == 0
    assert by_id["p1"]["definition"] == "detection_minus_advance"

    refused = (
        {"lag_hours": 6, "cost_bps": 10, "threshold": 0.10},
        {"lag_hours": 1, "cost_bps": 0, "threshold": 0.10},
        {"lag_hours": 1, "cost_bps": 25, "threshold": 0.10},
        {"lag_hours": 1, "cost_bps": 10, "threshold": 0.20},
    )

    def _assert_refuses(fn) -> None:
        for kwargs in refused:
            try:
                produced = fn(rows, **kwargs)
            except t15.CellRefused:
                continue
            raise AssertionError(f"non-primary cell accepted: {kwargs} -> {produced!r}")

    _assert_refuses(t15.paired_primary_differences)
    with pytest.raises(t15.CellRefused) as caught:
        t15.paired_primary_differences(rows, lag_hours=6, cost_bps=10, threshold=0.10)
    assert caught.value.field == "lag_hours"

    def _wrong_accepts_any_cell(source, **_kwargs):
        return {
            "cell": "other",
            "template_cell": "filled",
            "pairs": [
                {
                    "event_id": row["event_id"],
                    "paired_dr": row["detection_dr"] - row["advance_dr"],
                    "paired_du": row["detection_du"] - row["advance_du"],
                }
                for row in source
            ],
        }

    with pytest.raises(AssertionError):
        _assert_refuses(_wrong_accepts_any_cell)


def test_f_quoted_r9_counts_ignore_recomputed_rows() -> None:
    rows = [
        {"matched": True, "supported": True, "recent": False},
        {"matched": True, "supported": False, "recent": False},
        {"matched": False, "supported": True, "recent": True},
        {"matched": False, "supported": False, "recent": True},
    ]

    def _assert_frozen(counts: dict) -> None:
        assert counts == _QUOTED
        assert counts["full_all_event_recall"] == (20, 78)
        assert counts["full_supported_event_recall"] == (20, 37)
        assert counts["recent_all_event_recall"] == (1, 15)
        assert counts["recent_supported_event_recall"] == (1, 5)

    _assert_frozen(t15.read_quoted_r9_counts(rows))
    overwritten = t15.read_quoted_r9_counts(rows)
    overwritten["full_all_event_recall"] = (3, 4)
    _assert_frozen(t15.read_quoted_r9_counts(rows))

    def _wrong_recompute(source):
        matched = sum(1 for row in source if row["matched"])
        total = len(source)
        ratio = (matched, total)
        return {
            "full_all_event_recall": ratio,
            "full_supported_event_recall": ratio,
            "recent_all_event_recall": ratio,
            "recent_supported_event_recall": ratio,
        }

    with pytest.raises(AssertionError):
        _assert_frozen(_wrong_recompute(rows))
