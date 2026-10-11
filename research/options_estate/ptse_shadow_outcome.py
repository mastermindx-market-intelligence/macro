"""Pure matured-outcome projection for PTSE shadow enrollment.

This module never grades prices and never writes the W3/grades stores. It consumes
one validated PTSE shadow enrollment and the incumbent us.prophet_grades/v1 rows.

Missing grades remain PENDING. Matured grades are copied from the shared Prophet
grader only when the exact grade material is bound to an external owner receipt.
No p-values, model comparison, pass/fail, promotion, rank, gate, sizing, execution
or trade authority is created here.

This outcome is explicitly the incumbent Prophet candidate-return ruler
(excess return versus SPY at the requested shared-grader horizon). It is NOT the
PTSE B0 H5 normalized downside target and is NOT an Options/GEX volatility target.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
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
GRADE_OWNER = "engine.us_prophet_grades"
GRADE_HORIZONS = (10, 21, 42, 63)
OUTCOME_TARGET = "prophet.shared_excess_spy_return/v1"

GRADE_BIND_FIELDS = (
    "schema",
    "stamp_date",
    "ticker",
    "board_definition",
    "horizon",
    "bench",
    "excess_spy",
    "fill_date",
    "mark_date",
    "graded_asof",
)


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
    outcome_target: str
    status: str
    excess_spy: float | None
    fill_date: str | None
    mark_date: str | None
    graded_asof: str | None
    grade_schema: str | None
    grade_row_ref: Mapping[str, str] | None
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
    try:
        number = float(value)
    except (OverflowError, ValueError):
        _fail(code)
    if not math.isfinite(number):
        _fail(code)
    return number


def _date(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) != 10:
        _fail(code)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail(code)
    if parsed.isoformat() != value:
        _fail(code)
    return value


def _ref(value: Mapping[str, Any] | None, code: str) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != {"owner_ref", "artifact_id", "sha256"}
        or not all(isinstance(value.get(k), str) and value.get(k) for k in value)
    ):
        _fail(code)
    digest = value.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        _fail(code)
    return dict(value)


def _grade_artifact_id(
    *,
    stamp_date: str,
    ticker: str,
    board_definition: str,
    horizon: int,
) -> str:
    return f"grade:{stamp_date}:{ticker}:{board_definition}:{horizon}"


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


def _grade_material(row: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical semantic subset used by this projection and its owner receipt."""
    return {field: row.get(field) for field in GRADE_BIND_FIELDS}


def _grade_material_sha256(row: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canon(_grade_material(row))).hexdigest()


def project_shadow_outcome(
    *,
    enrollment: Mapping[str, Any],
    grade_rows: Sequence[Mapping[str, Any]],
    horizon: int,
    grade_row_ref: Mapping[str, Any] | None = None,
) -> PTSEShadowOutcome:
    """Join one PTSE enrollment to the existing Prophet grader by exact key.

    The shared grader remains the sole outcome owner. A matured row is accepted
    only when the caller supplies an immutable owner receipt whose digest binds
    the exact grade fields this projection consumes.
    """
    try:
        validate_shadow_enrollment(enrollment)
    except Exception as exc:
        raise PTSEShadowOutcomeError("ENROLLMENT_INVALID") from exc

    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        _fail("HORIZON_INVALID")
    if horizon not in GRADE_HORIZONS:
        _fail("HORIZON_NOT_ADMITTED")
    if not isinstance(grade_rows, Sequence) or isinstance(grade_rows, (str, bytes, bytearray, memoryview)):
        _fail("GRADE_ROWS_INVALID")

    # A malformed owner collection is not proof that a matching grade has not
    # matured. Validate its keys before projecting absence as PENDING, and do
    # not let Python's equality conflate a float or boolean with an integer
    # registered horizon.
    for row in grade_rows:
        if not isinstance(row, Mapping):
            _fail("GRADE_ROWS_INVALID")
        _date(row.get("stamp_date"), "GRADE_STAMP_INVALID")
        for key in ("ticker", "board_definition"):
            value = row.get(key)
            if (not isinstance(value, str) or not value
                    or any(ord(ch) < 32 or ch.isspace() for ch in value)):
                _fail("GRADE_KEY_INVALID")
        row_horizon = row.get("horizon")
        if type(row_horizon) is not int:
            _fail("GRADE_HORIZON_INVALID")
        if row_horizon not in GRADE_HORIZONS:
            _fail("GRADE_HORIZON_NOT_ADMITTED")

    stamp = str(enrollment["stamp_date"])
    ticker = str(enrollment["ticker"])
    definition = str(enrollment["board_definition"])
    matches = [
        row for row in grade_rows
        if _grade_matches(
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
        if grade_row_ref is not None:
            _fail("GRADE_REF_WITHOUT_ROW")
        material = {
            "schema": SCHEMA,
            "enrollment_id": enrollment["enrollment_id"],
            "stamp_date": stamp,
            "ticker": ticker,
            "board_definition": definition,
            "horizon": horizon,
            "outcome_target": OUTCOME_TARGET,
            "status": "PENDING",
            "excess_spy": None,
            "fill_date": None,
            "mark_date": None,
            "graded_asof": None,
            "grade_schema": None,
            "grade_row_ref": None,
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

        owner_ref = _ref(grade_row_ref, "GRADE_ROW_REF_REQUIRED")
        if owner_ref["owner_ref"] != GRADE_OWNER:
            _fail("GRADE_OWNER_INVALID")
        expected_artifact_id = _grade_artifact_id(
            stamp_date=stamp,
            ticker=ticker,
            board_definition=definition,
            horizon=horizon,
        )
        if owner_ref["artifact_id"] != expected_artifact_id:
            _fail("GRADE_ARTIFACT_ID_MISMATCH")
        if owner_ref["sha256"] != _grade_material_sha256(row):
            _fail("GRADE_ROW_REF_MISMATCH")

        material = {
            "schema": SCHEMA,
            "enrollment_id": enrollment["enrollment_id"],
            "stamp_date": stamp,
            "ticker": ticker,
            "board_definition": definition,
            "horizon": horizon,
            "outcome_target": OUTCOME_TARGET,
            "status": "MATURED",
            "excess_spy": excess,
            "fill_date": fill,
            "mark_date": mark,
            "graded_asof": graded,
            "grade_schema": GRADE_SCHEMA,
            "grade_row_ref": owner_ref,
            "authority": dict(AUTHORITY),
        }

    pid = "ptse-outcome:" + hashlib.sha256(_canon(material)).hexdigest()
    return PTSEShadowOutcome(
        projection_id=pid,
        **{k: v for k, v in material.items() if k != "schema"},
    )


__all__ = [
    "AUTHORITY",
    "BENCH",
    "GRADE_BIND_FIELDS",
    "GRADE_HORIZONS",
    "GRADE_OWNER",
    "GRADE_SCHEMA",
    "OUTCOME_TARGET",
    "PTSEShadowOutcome",
    "PTSEShadowOutcomeError",
    "project_shadow_outcome",
]
