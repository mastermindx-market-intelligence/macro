"""T15-Q1 study scaffold. Pure functions only.

Cohort assignment, account pairing, barrier exclusions, and the primary-cell
paired difference for the frozen question in
CRYPTO_T15_TRANSITION_INCREMENT_PREREG_2026-10-12.md §4.1.
Falsifiers: §4.3 items 1-5. Items 6-7 have no function here: this module
does not promote an alert, a size, an allocation, or a refit.

No read of data/. No network. No template cell is filled. The quoted R9
counts are literals, not a function of the rows passed in.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

R9_MODULE_REL = "research/crypto_science/r9_prebreak_study.py"
R9_IMPORT_NAME = "research.crypto_science.r9_prebreak_study"

# Primary cell from the preregistration §4.1. Other lags, costs, and
# thresholds are refused. Sensitivity rows are not computed.
PRIMARY_LAG_HOURS = 1
PRIMARY_COST_BPS = 10
PRIMARY_THRESHOLD = 0.10

_OK = "ok"
_ACCOUNT_UNAVAILABLE = "account_unavailable"
_UNMATCHED = "unmatched"
_UNAVAILABLE = "unavailable"


class T15ScaffoldError(Exception):
    """A scaffold input broke a frozen rule."""


class CellRefused(T15ScaffoldError):
    """Falsifier 5: lag, cost, or threshold is not the primary cell."""

    def __init__(self, field: str, value: object, expected: object) -> None:
        self.field = field
        self.value = value
        self.expected = expected
        super().__init__(f"{field}={value!r} refused; primary cell requires {expected!r}")


def load_r9_prebreak_study(root: Path | None = None) -> dict[str, str]:
    """Fail closed on the R9 study module.

    Absence is `status=unavailable` and names the missing module. A file that
    happens to be on disk is not imported and is not executed: importing the
    study pulls the R4/R6/R8 stack and `main` reads the data directory.
    The return value is strings only. It is never a metric.
    """
    base = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    path = base / R9_MODULE_REL
    if not path.is_file():
        reason = "module_absent"
        status = _UNAVAILABLE
    else:
        reason = "not_executed"
        status = "present_not_executed"
    return {
        "status": status,
        "module": R9_MODULE_REL,
        "import_name": R9_IMPORT_NAME,
        "reason": reason,
    }


def read_quoted_r9_counts(rows: Sequence[Mapping] | None = None) -> dict[str, tuple[int, int]]:
    """Published R9 match quotations. `rows` is ignored.

    Full-period all-event 20/78, full-period supported 20/37, recent
    all-event 1/15, recent supported 1/5. Preregistration §2. A caller cannot
    overwrite these by passing a recomputed table.
    """
    del rows
    return {
        "full_all_event_recall": (20, 78),
        "full_supported_event_recall": (20, 37),
        "recent_all_event_recall": (1, 15),
        "recent_supported_event_recall": (1, 5),
    }


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise T15ScaffoldError(f"{field} must be a naive datetime")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or value == "":
        raise T15ScaffoldError(f"{field} must be a non-empty string")
    return value


def _refusal(row: Mapping, reason: str) -> dict[str, str]:
    return {
        "row_id": row["row_id"],
        "event_id": row["event_id"],
        "role": row["role"],
        "reason": reason,
    }


def _cohort_row(row: Mapping) -> dict[str, object]:
    return {
        "row_id": row["row_id"],
        "event_id": row["event_id"],
        "role": row["role"],
        "break_issue": row["break_issue"],
        "action_reference": row["action_reference"],
    }


def assign_cohorts(rows: Sequence[Mapping]) -> dict[str, object]:
    """Split detection references from the advance-match set.

    A detection row whose action reference is at or before `break_issue` is
    refused (falsifier 2). No detection `row_id` enters `advance_match`
    (falsifiers 1 and 2). Recall numerators on the result are the quoted R9
    counts, not the size of either cohort.
    """
    normalized: list[dict[str, object]] = []
    for raw in rows:
        role = _text(raw.get("role"), "role")
        normalized.append(
            {
                "row_id": _text(raw.get("row_id"), "row_id"),
                "event_id": _text(raw.get("event_id"), "event_id"),
                "role": role,
                "break_issue": _timestamp(raw.get("break_issue"), "break_issue"),
                "action_reference": _timestamp(raw.get("action_reference"), "action_reference"),
            }
        )
    detection_ids = {row["row_id"] for row in normalized if row["role"] == "detection"}
    detection: list[dict[str, object]] = []
    advance: list[dict[str, object]] = []
    refused: list[dict[str, str]] = []
    for row in normalized:
        action = row["action_reference"]
        break_issue = row["break_issue"]
        if row["role"] == "detection":
            if action <= break_issue:
                refused.append(_refusal(row, "detection_action_at_or_before_break"))
                continue
            detection.append(_cohort_row(row))
            continue
        if row["role"] == "advance":
            if row["row_id"] in detection_ids:
                refused.append(_refusal(row, "detection_row_banned_from_advance_match"))
                continue
            if action >= break_issue:
                refused.append(_refusal(row, "advance_action_at_or_after_break"))
                continue
            advance.append(_cohort_row(row))
            continue
        refused.append(_refusal(row, "unknown_role"))
    det_ids = [row["row_id"] for row in detection]
    adv_ids = [row["row_id"] for row in advance]
    return {
        "detection": detection,
        "advance_match": advance,
        "refused": refused,
        "detection_row_ids_in_advance_match": [row_id for row_id in det_ids if row_id in adv_ids],
        "quoted_r9_counts": read_quoted_r9_counts(),
    }


def _finite_number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        return None
    return value


def pair_accounts(events: Sequence[Mapping]) -> dict[str, object]:
    """Pair detection and advance accounts. Keep the whole catalogue.

    The paired set is the intersection where both statuses are `ok`.
    Every other row stays in `ledger` with `paired_dr` and `paired_du`
    equal to the string `unavailable`. An `account_unavailable` input is
    not written as 0, and an unmatched event is not dropped (falsifier 4).
    """
    ledger: list[dict[str, object]] = []
    paired: list[dict[str, object]] = []
    for event in events:
        event_id = _text(event.get("event_id"), "event_id")
        detection_status = _text(event.get("detection_status"), "detection_status")
        advance_status = _text(event.get("advance_status"), "advance_status")
        both_ok = detection_status == _OK and advance_status == _OK
        record: dict[str, object] = {
            "event_id": event_id,
            "detection_status": detection_status,
            "advance_status": advance_status,
            "in_intersection": False,
            "paired_dr": _UNAVAILABLE,
            "paired_du": _UNAVAILABLE,
        }
        if both_ok:
            detection_dr = _finite_number(event.get("detection_dr"))
            advance_dr = _finite_number(event.get("advance_dr"))
            detection_du = _finite_number(event.get("detection_du"))
            advance_du = _finite_number(event.get("advance_du"))
            if None not in (detection_dr, advance_dr, detection_du, advance_du):
                record["in_intersection"] = True
                record["paired_dr"] = detection_dr - advance_dr
                record["paired_du"] = detection_du - advance_du
                paired.append(
                    {
                        "event_id": event_id,
                        "paired_dr": record["paired_dr"],
                        "paired_du": record["paired_du"],
                    }
                )
        ledger.append(record)
    return {"ledger": ledger, "paired": paired}


def _exclusion(kind: str) -> dict[str, object]:
    return {
        "exclusion": kind,
        "category": kind,
        "y": _UNAVAILABLE,
        "false_window": False,
        "path_return": _UNAVAILABLE,
        "scored": False,
    }


def _price(value: object, field: str) -> float:
    number = _finite_number(value)
    if number is None:
        raise T15ScaffoldError(f"{field} must be a finite number")
    return float(number)


def classify_window(window: Mapping) -> dict[str, object]:
    """Type an ambiguous both-barrier candle or a censored window.

    Ordering matches the frozen single-bar rule: an open through a barrier
    decides before an intrabar both-barrier cross. The both-barrier case
    with an open strictly between the barriers is `ambiguous`. A censored
    or incomplete window is `censored` even when the supplied prices would
    otherwise decide. Neither exclusion is `lower_first`, a false window,
    or a zero return (falsifier 3). This function does not emit a path return.
    """
    if window.get("censored") is True or window.get("complete") is False:
        return _exclusion("censored")
    if window.get("ambiguous") is True:
        return _exclusion("ambiguous")
    open_ = _price(window.get("open"), "open")
    low = _price(window.get("low"), "low")
    high = _price(window.get("high"), "high")
    lower = _price(window.get("lower_barrier"), "lower_barrier")
    upper = _price(window.get("upper_barrier"), "upper_barrier")
    if open_ <= lower:
        category = "lower_first"
    elif open_ >= upper:
        category = "upper_first"
    elif low <= lower and high >= upper:
        return _exclusion("ambiguous")
    elif low <= lower:
        category = "lower_first"
    elif high >= upper:
        category = "upper_first"
    else:
        category = "undecided"
    return {
        "exclusion": None,
        "category": category,
        "y": _UNAVAILABLE,
        "false_window": False,
        "path_return": _UNAVAILABLE,
        "scored": False,
    }


def _require_primary_cell(lag_hours: object, cost_bps: object, threshold: object) -> None:
    if type(lag_hours) is not int or lag_hours != PRIMARY_LAG_HOURS:
        raise CellRefused("lag_hours", lag_hours, PRIMARY_LAG_HOURS)
    if type(cost_bps) is not int or cost_bps != PRIMARY_COST_BPS:
        raise CellRefused("cost_bps", cost_bps, PRIMARY_COST_BPS)
    if type(threshold) is not float or threshold != PRIMARY_THRESHOLD:
        raise CellRefused("threshold", threshold, PRIMARY_THRESHOLD)


def paired_primary_differences(
    rows: Sequence[Mapping],
    *,
    lag_hours: object,
    cost_bps: object,
    threshold: object,
) -> dict[str, object]:
    """Detection minus advance of `dr` and `du` on injected primary-cell rows.

    Lag 1h, cost 10bp, threshold 0.10 only. Any other lag, cost, or threshold
    raises CellRefused before a difference is computed (falsifier 5).
    The §4.4 template cell stays `unfilled`.
    """
    _require_primary_cell(lag_hours, cost_bps, threshold)
    pairs: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        event_id = _text(row.get("event_id"), "event_id")
        detection_status = _text(row.get("detection_status"), "detection_status")
        advance_status = _text(row.get("advance_status"), "advance_status")
        if detection_status != _OK or advance_status != _OK:
            excluded.append({"event_id": event_id, "reason": "not_both_ok"})
            continue
        detection_dr = _finite_number(row.get("detection_dr"))
        advance_dr = _finite_number(row.get("advance_dr"))
        detection_du = _finite_number(row.get("detection_du"))
        advance_du = _finite_number(row.get("advance_du"))
        if None in (detection_dr, advance_dr, detection_du, advance_du):
            excluded.append({"event_id": event_id, "reason": "missing_difference_input"})
            continue
        pairs.append(
            {
                "event_id": event_id,
                "paired_dr": detection_dr - advance_dr,
                "paired_du": detection_du - advance_du,
                "definition": "detection_minus_advance",
            }
        )
    return {
        "cell": "1h_10bp",
        "lag_hours": PRIMARY_LAG_HOURS,
        "cost_bps": PRIMARY_COST_BPS,
        "threshold": PRIMARY_THRESHOLD,
        "pairs": pairs,
        "excluded": excluded,
        "template_cell": "unfilled",
    }
