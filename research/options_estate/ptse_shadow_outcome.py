"""Pure matured-outcome projection for PTSE shadow enrollment.

This module never grades prices and never writes the W3/grades stores. It consumes
one validated PTSE shadow enrollment and the incumbent us.prophet_grades/v1 rows.

Missing grades remain PENDING. Matured grades are copied verbatim from the shared
Prophet grader. No p-values, model comparison, pass/fail, promotion, rank, gate,
sizing, execution or trade authority is created here.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from research.options_estate.ptse_shadow_enrollment import (
    validate_shadow_enrollment,
)

SCHEMA = "ptse.shadow_outcome_projection/v1-research"
GRADE_SCHEMA = "us.prophet_grades/v1"
BENCH = "SPY"


class PTSEShadowOutcomeError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PTSEShadowOutcome:
    projection_id: str
    enrollment_id: str
    stamp_date: str
    ticker: str
    board_definition: str
    horizon: int
    status: str
    excess_spy: float | None
    fill_date: str | None
    mark_date: str | None
    graded_asof: str | None
    grade_schema: str | None
    authority: Mapping[str, bool]


AUTHORITY = {
    "research_pass": False,
    "forecast_promotion": False,
    "rank": False,
    "admission": False,
    "entry_gating": False,
    "plan_mutation": False,
    "alert_escalation": False,
    "sizing": False,
    "portfolio": False,
    "execution": False,
    "trade": False,
}


def _fail(code: str) -> None:
    raise PTSEShadowOutcomeError(code)


def _canon(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            dict(value), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise PTSEShadowOutcomeError("OUTCOME_NOT_CANONICAL") from exc


def _finite(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(code)
    number = float(value)
    if not math.isfinite(number):
        _fail(code)
    return number


def _date(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) < 10:
        _fail(code)
    day = value[:10]
    if len(day) != 10 or day[4] != "-" or day[7] != "-":
        _fail(code)
    return day


def _grade_matches(
    row: Mapping[str, Any],
    *,
    stamp_date: str,
    ticker: str,
    board_definition: str,
    horizon: int,
) -> bool:
    return (
        row.get("stamp_date") == stamp_date
        and row.get("ticker") == ticker
        and row.get("board_definition") == board_definition
        and row.get("horizon") == horizon
    )


def project_shadow_outcome(
    *,
    enrollment: Mapping[str, Any],
    grade_rows: Sequence[Mapping[str, Any]],
    horizon: int,
) -> PTSEShadowOutcome:
    """Join one PTSE enrollment to the existing Prophet grader by exact key."""
    try:
        validate_shadow_enrollment(enrollment)
    except Exception as exc:
        raise PTSEShadowOutcomeError("ENROLLMENT_INVALID") from exc

    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        _fail("HORIZON_INVALID")
    if not isinstance(grade_rows, Sequence) or isinstance(grade_rows, (str, bytes)):
        _fail("GRADE_ROWS_INVALID")

    stamp = str(enrollment["stamp_date"])
    ticker = str(enrollment["ticker"])
    definition = str(enrollment["board_definition"])
    matches = [
        row for row in grade_rows
        if isinstance(row, Mapping)
        and _grade_matches(
            row,
            stamp_date=stamp,
            ticker=ticker,
            board_definition=definition,
            horizon=horizon,
        )
    ]
    if len(matches) > 1:
        _fail("GRADE_KEY_AMBIGUOUS")

    if not matches:
        material = {
            "schema": SCHEMA,
            "enrollment_id": enrollment["enrollment_id"],
            "stamp_date": stamp,
            "ticker": ticker,
            "board_definition": definition,
            "horizon": horizon,
            "status": "PENDING",
            "excess_spy": None,
            "fill_date": None,
            "mark_date": None,
            "graded_asof": None,
            "grade_schema": None,
            "authority": dict(AUTHORITY),
        }
    else:
        row = matches[0]
        if row.get("schema") != GRADE_SCHEMA:
            _fail("GRADE_SCHEMA_INVALID")
        if row.get("bench") != BENCH:
            _fail("GRADE_BENCH_INVALID")
        excess = _finite(row.get("excess_spy"), "GRADE_EXCESS_INVALID")
        fill = _date(row.get("fill_date"), "GRADE_FILL_DATE_INVALID")
        mark = _date(row.get("mark_date"), "GRADE_MARK_DATE_INVALID")
        graded = _date(row.get("graded_asof"), "GRADE_ASOF_INVALID")
        if not (stamp < fill <= mark <= graded):
            _fail("GRADE_CLOCK_ORDER_INVALID")
        material = {
            "schema": SCHEMA,
            "enrollment_id": enrollment["enrollment_id"],
            "stamp_date": stamp,
            "ticker": ticker,
            "board_definition": definition,
            "horizon": horizon,
            "status": "MATURED",
            "excess_spy": excess,
            "fill_date": fill,
            "mark_date": mark,
            "graded_asof": graded,
            "grade_schema": GRADE_SCHEMA,
            "authority": dict(AUTHORITY),
        }

    pid = "ptse-outcome:" + hashlib.sha256(_canon(material)).hexdigest()
    return PTSEShadowOutcome(projection_id=pid, **{k:v for k,v in material.items() if k!="schema"})


__all__ = [
    "AUTHORITY",
    "PTSEShadowOutcome",
    "PTSEShadowOutcomeError",
    "project_shadow_outcome",
]