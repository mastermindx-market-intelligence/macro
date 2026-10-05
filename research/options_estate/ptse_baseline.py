"""PTSE-B0-H5 source-independent benchmark runner.

This module owns no source read, calendar, collector, outcome store, registration
ledger, scheduler, candidate lifecycle, decision policy, or production authority.
It operates only on caller-supplied rows after the existing research owner has
ratified a protocol and the existing source owner has admitted the evidence.

The protocol deliberately has no numerical defaults. Materiality thresholds,
ridge alpha, split boundaries, minimum train support, and evaluation clocks must
arrive explicitly under an immutable owner ratification reference before an
actual protected-outcome caller reads labels.

B0 is a market forecast benchmark only. It never creates Prophet candidate/action
eligibility, entry permission, sizing, portfolio, execution, or trading effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
import re
from typing import Final, Iterable, Literal, Mapping, Sequence

import numpy as np


EXPERIMENT_ID: Final = "PTSE-B0-H5-v1"
TARGET_VERSION: Final = "normalized_h5_closing_path_downside.v1"
FEATURE_NAMES: Final = (
    "log_v20",
    "trend63",
    "momentum5",
    "positive_trend_negative_momentum",
)
SOURCE_GRADES: Final = frozenset(
    {
        "SYNTHETIC",
        "RETROSPECTIVE_PIT_UNPROVEN",
        "PIT_QUALIFIED_REPLAY",
        "PROSPECTIVE_FIRST_SEEN",
    }
)
MODES: Final = frozenset({"SYNTHETIC", "EXPLORATORY", "CONFIRMATORY"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+#=%|~-]{2,255}\Z")


class B0ContractError(ValueError):
    """A closed failure code; no data row contents are echoed."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class B0Protocol:
    experiment_id: str
    target_version: str
    feature_names: tuple[str, ...]
    transform: Literal["TRAIN_ZSCORE"]
    ridge_alpha: float
    min_train_rows: int
    mode: Literal["SYNTHETIC", "EXPLORATORY", "CONFIRMATORY"]
    market: Literal["US"]
    cadence: Literal["DAILY"]
    session_scope: Literal["REGULAR"]
    instrument_id: str
    forecast_horizon_sessions: int
    owner_ratification_ref: str
    source_manifest_sha256: str
    outcome_manifest_sha256: str
    calendar_sha256: str
    feature_version: str
    evaluation_partition_ref: str
    prior_history_exposure_ref: str
    trial_family_ref: str
    embargo_policy_ref: str


@dataclass(frozen=True)
class FoldSpec:
    fold_id: str
    fit_cutoff_session: str
    fit_cutoff_at: str
    embargo_end_session: str
    test_start_session: str
    test_end_session: str
    evaluation_at: str
    cohort_sha256: str
    expected_test_rows: int
    expected_test_origin_ids: tuple[str, ...]


@dataclass(frozen=True)
class B0Row:
    origin_id: str
    market_session: str
    decision_at: str
    source_available_at: str
    label_end_session: str
    label_matured_at: str
    source_grade: str
    source_artifact_sha256: str
    outcome_artifact_sha256: str
    log_v20: float
    trend63: float
    momentum5: float
    positive_trend_negative_momentum: float
    y5: float


@dataclass(frozen=True)
class FoldResult:
    fold_id: str
    fold_spec_digest: str
    cohort_sha256: str
    train_rows: int
    purged_unmatured_or_overlapping_train_rows: int
    expected_test_rows: int
    test_rows: int
    unevaluable_test_rows: int
    source_grades: tuple[str, ...]
    mean_reference_mse: float
    mean_reference_mae: float
    p_vector_mse: float
    p_vector_mae: float
    test_prediction_digest: str


@dataclass(frozen=True)
class B0Result:
    experiment_id: str
    protocol_digest: str
    mode: str
    target_version: str
    feature_names: tuple[str, ...]
    attempted_arms: tuple[str, ...]
    fold_results: tuple[FoldResult, ...]
    evaluable_rows: int
    source_grades: tuple[str, ...]
    authority: Mapping[str, bool]
    result_digest: str


def _fail(code: str) -> None:
    raise B0ContractError(code)


def _canonical(value: object) -> bytes:
    def normalize(v: object) -> object:
        if v is None or type(v) in (bool, int, str):
            return v
        if type(v) is float:
            if not math.isfinite(v):
                _fail("NONFINITE")
            return int(v) if v.is_integer() else v
        if isinstance(v, tuple):
            return [normalize(x) for x in v]
        if isinstance(v, list):
            return [normalize(x) for x in v]
        if isinstance(v, Mapping):
            if any(not isinstance(k, str) for k in v):
                _fail("NON_STRING_KEY")
            return {k: normalize(v[k]) for k in sorted(v)}
        if hasattr(v, "__dataclass_fields__"):
            return {
                k: normalize(getattr(v, k))
                for k in v.__dataclass_fields__
            }
        _fail("NON_CANONICAL_TYPE")

    return json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _hash(value: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        _fail("DIGEST_REQUIRED")
    return value


def _ref(value: str) -> str:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        _fail("REFERENCE_REQUIRED")
    return value


def _date(value: str) -> date:
    if not isinstance(value, str):
        _fail("DATE_REQUIRED")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("DATE_INVALID")
    if parsed.isoformat() != value:
        _fail("DATE_INVALID")
    return parsed


def _time(value: str) -> datetime:
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        _fail("TIMESTAMP_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("TIMESTAMP_INVALID")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("TIMESTAMP_TIMEZONE_REQUIRED")
    try:
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        _fail("TIMESTAMP_INVALID")


def validate_protocol(protocol: B0Protocol) -> str:
    """Validate the ex-ante packet before any caller opens protected outcomes."""
    if protocol.experiment_id != EXPERIMENT_ID:
        _fail("EXPERIMENT_ID_MISMATCH")
    if protocol.target_version != TARGET_VERSION:
        _fail("TARGET_VERSION_MISMATCH")
    if protocol.feature_names != FEATURE_NAMES:
        _fail("FEATURE_IDENTITY_MISMATCH")
    if protocol.transform != "TRAIN_ZSCORE":
        _fail("TRANSFORM_NOT_REGISTERED")
    if (
        type(protocol.ridge_alpha) not in (int, float)
        or not math.isfinite(float(protocol.ridge_alpha))
        or protocol.ridge_alpha <= 0
    ):
        _fail("RIDGE_ALPHA_REQUIRED")
    if type(protocol.min_train_rows) is not int or protocol.min_train_rows < 1:
        _fail("MIN_TRAIN_ROWS_REQUIRED")
    if protocol.mode not in MODES:
        _fail("MODE_NOT_REGISTERED")
    if (
        protocol.market,
        protocol.cadence,
        protocol.session_scope,
        protocol.forecast_horizon_sessions,
    ) != ("US", "DAILY", "REGULAR", 5):
        _fail("SCOPE_NOT_REGISTERED")
    _ref(protocol.instrument_id)
    _ref(protocol.owner_ratification_ref)
    _hash(protocol.source_manifest_sha256)
    _hash(protocol.outcome_manifest_sha256)
    _hash(protocol.calendar_sha256)
    _ref(protocol.feature_version)
    _ref(protocol.evaluation_partition_ref)
    _ref(protocol.prior_history_exposure_ref)
    _ref(protocol.trial_family_ref)
    _ref(protocol.embargo_policy_ref)
    return sha256(_canonical(protocol)).hexdigest()


def validate_fold(fold: FoldSpec) -> None:
    if not isinstance(fold.fold_id, str) or not fold.fold_id or len(fold.fold_id) > 128:
        _fail("FOLD_ID_REQUIRED")
    cutoff = _date(fold.fit_cutoff_session)
    embargo_end = _date(fold.embargo_end_session)
    start = _date(fold.test_start_session)
    end = _date(fold.test_end_session)
    fit_at = _time(fold.fit_cutoff_at)
    eval_at = _time(fold.evaluation_at)
    if not cutoff <= embargo_end < start <= end:
        _fail("FOLD_ORDER_INVALID")
    if eval_at < fit_at:
        _fail("EVALUATION_BEFORE_FIT")
    _hash(fold.cohort_sha256)
    if type(fold.expected_test_rows) is not int or fold.expected_test_rows < 1:
        _fail("EXPECTED_TEST_ROWS_REQUIRED")
    if (
        not isinstance(fold.expected_test_origin_ids, tuple)
        or len(fold.expected_test_origin_ids) != fold.expected_test_rows
        or not fold.expected_test_origin_ids
    ):
        _fail("COHORT_IDENTITY_REQUIRED")
    for origin_id in fold.expected_test_origin_ids:
        _ref(origin_id)
    if len(set(fold.expected_test_origin_ids)) != len(fold.expected_test_origin_ids):
        _fail("COHORT_IDENTITY_REQUIRED")
    if tuple(sorted(fold.expected_test_origin_ids)) != fold.expected_test_origin_ids:
        _fail("COHORT_IDENTITY_REQUIRED")
    expected_digest = sha256(_canonical(fold.expected_test_origin_ids)).hexdigest()
    if fold.cohort_sha256 != expected_digest:
        _fail("COHORT_DIGEST_MISMATCH")


def _row(row: B0Row, mode: str) -> B0Row:
    _ref(row.origin_id)
    session = _date(row.market_session)
    decision = _time(row.decision_at)
    available = _time(row.source_available_at)
    label_end = _date(row.label_end_session)
    label_matured = _time(row.label_matured_at)
    if available > decision:
        _fail("SOURCE_NOT_AVAILABLE_AT_DECISION")
    if decision.date() != session:
        _fail("DECISION_SESSION_MISMATCH")
    if label_end <= session:
        _fail("LABEL_HORIZON_INVALID")
    if label_matured.date() < label_end:
        _fail("LABEL_MATURITY_INVALID")
    if label_matured <= decision:
        _fail("LABEL_MATURITY_INVALID")
    if row.source_grade not in SOURCE_GRADES:
        _fail("SOURCE_GRADE_INVALID")
    allowed = {
        "SYNTHETIC": {"SYNTHETIC"},
        "EXPLORATORY": {
            "RETROSPECTIVE_PIT_UNPROVEN",
            "PIT_QUALIFIED_REPLAY",
            "PROSPECTIVE_FIRST_SEEN",
        },
        "CONFIRMATORY": {"PIT_QUALIFIED_REPLAY", "PROSPECTIVE_FIRST_SEEN"},
    }[mode]
    if row.source_grade not in allowed:
        _fail("SOURCE_GRADE_NOT_ADMITTED")
    _hash(row.source_artifact_sha256)
    _hash(row.outcome_artifact_sha256)
    for value in (
        row.log_v20,
        row.trend63,
        row.momentum5,
        row.positive_trend_negative_momentum,
        row.y5,
    ):
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            _fail("ROW_NONFINITE")
    if row.positive_trend_negative_momentum not in (0, 1, 0.0, 1.0):
        _fail("INDICATOR_INVALID")
    if row.y5 < 0:
        _fail("TARGET_NEGATIVE")
    return row


def _features(rows: Sequence[B0Row]) -> np.ndarray:
    return np.asarray(
        [
            [
                float(r.log_v20),
                float(r.trend63),
                float(r.momentum5),
                float(r.positive_trend_negative_momentum),
            ]
            for r in rows
        ],
        dtype=float,
    )


def _target(rows: Sequence[B0Row]) -> np.ndarray:
    return np.asarray([float(r.y5) for r in rows], dtype=float)


def _fit_predict_ridge(
    train: Sequence[B0Row],
    test: Sequence[B0Row],
    alpha: float,
) -> np.ndarray:
    x_train = _features(train)
    x_test = _features(test)
    y_train = _target(train)

    means = x_train.mean(axis=0)
    scales = x_train.std(axis=0)
    scales = np.where(scales > 0, scales, 1.0)
    z_train = (x_train - means) / scales
    z_test = (x_test - means) / scales

    design = np.column_stack([np.ones(len(z_train)), z_train])
    design_test = np.column_stack([np.ones(len(z_test)), z_test])
    penalty = np.eye(design.shape[1], dtype=float) * float(alpha)
    penalty[0, 0] = 0.0
    try:
        beta = np.linalg.solve(
            design.T @ design + penalty,
            design.T @ y_train,
        )
    except np.linalg.LinAlgError as exc:
        raise B0ContractError("RIDGE_SOLVE_FAILED") from exc
    return design_test @ beta


def _metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> tuple[float, float]:
    errors = predicted - actual
    return (
        float(np.mean(errors * errors)),
        float(np.mean(np.abs(errors))),
    )


def run_b0(
    protocol: B0Protocol,
    folds: Sequence[FoldSpec],
    rows: Iterable[B0Row],
) -> B0Result:
    """Run only after caller-side source/outcome admission has succeeded.

    This function performs no I/O. validate_protocol is deliberately a separate
    preflight so a real caller can validate owner ratification before reading
    protected label bytes.
    """
    protocol_digest = validate_protocol(protocol)
    if not isinstance(folds, Sequence) or not folds:
        _fail("FOLDS_REQUIRED")
    for fold in folds:
        validate_fold(fold)

    material = [_row(r, protocol.mode) for r in rows]
    material.sort(key=lambda r: (r.market_session, r.origin_id))
    if len({r.origin_id for r in material}) != len(material):
        _fail("DUPLICATE_ORIGIN_ID")
    if len({r.market_session for r in material}) != len(material):
        _fail("DUPLICATE_MARKET_SESSION")

    results: list[FoldResult] = []
    used_origins: set[str] = set()
    used_source_grades: set[str] = set()

    for fold in folds:
        cutoff = _date(fold.fit_cutoff_session)
        test_start = _date(fold.test_start_session)
        test_end = _date(fold.test_end_session)
        fit_at = _time(fold.fit_cutoff_at)
        eval_at = _time(fold.evaluation_at)
        fold_spec_digest = sha256(_canonical(fold)).hexdigest()

        historical_train = [
            r for r in material
            if _date(r.market_session) <= cutoff
        ]
        train = [
            r for r in historical_train
            if (
                _date(r.label_end_session) <= cutoff
                and _time(r.label_matured_at) <= fit_at
            )
        ]
        purged = len(historical_train) - len(train)

        test_window = [
            r for r in material
            if test_start <= _date(r.market_session) <= test_end
        ]
        observed_test_origins = tuple(sorted(r.origin_id for r in test_window))
        if observed_test_origins != fold.expected_test_origin_ids:
            _fail("COHORT_IDENTITY_MISMATCH")
        test = [
            r for r in test_window
            if _time(r.label_matured_at) <= eval_at
        ]
        unevaluable_test_rows = fold.expected_test_rows - len(test)

        if len(train) < protocol.min_train_rows:
            _fail("TRAIN_SUPPORT_INSUFFICIENT")
        if not test:
            _fail("TEST_SUPPORT_INSUFFICIENT")
        if {r.origin_id for r in train} & {r.origin_id for r in test}:
            _fail("TRAIN_TEST_OVERLAP")
        if used_origins & {r.origin_id for r in test}:
            _fail("TEST_FOLD_OVERLAP")
        used_origins |= {r.origin_id for r in test}
        used_source_grades.update(r.source_grade for r in train + test)

        y_train = _target(train)
        y_test = _target(test)
        mean_prediction = np.full(len(test), float(y_train.mean()))
        p_prediction = _fit_predict_ridge(
            train,
            test,
            float(protocol.ridge_alpha),
        )
        mean_mse, mean_mae = _metrics(y_test, mean_prediction)
        p_mse, p_mae = _metrics(y_test, p_prediction)

        prediction_material = [
            {
                "origin_id": row.origin_id,
                "source_artifact_sha256": row.source_artifact_sha256,
                "outcome_artifact_sha256": row.outcome_artifact_sha256,
                "actual_y5": float(row.y5),
                "mean_reference": float(mean_prediction[i]),
                "p_vector_ridge": float(p_prediction[i]),
            }
            for i, row in enumerate(test)
        ]
        prediction_digest = sha256(
            _canonical(prediction_material)
        ).hexdigest()

        results.append(
            FoldResult(
                fold_id=fold.fold_id,
                fold_spec_digest=fold_spec_digest,
                cohort_sha256=fold.cohort_sha256,
                train_rows=len(train),
                purged_unmatured_or_overlapping_train_rows=purged,
                expected_test_rows=fold.expected_test_rows,
                test_rows=len(test),
                unevaluable_test_rows=unevaluable_test_rows,
                source_grades=tuple(
                    sorted({r.source_grade for r in train + test})
                ),
                mean_reference_mse=mean_mse,
                mean_reference_mae=mean_mae,
                p_vector_mse=p_mse,
                p_vector_mae=p_mae,
                test_prediction_digest=prediction_digest,
            )
        )

    authority = {
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

    result_core = {
        "experiment_id": EXPERIMENT_ID,
        "protocol_digest": protocol_digest,
        "mode": protocol.mode,
        "target_version": TARGET_VERSION,
        "feature_names": FEATURE_NAMES,
        "attempted_arms": ("mean_reference", "p_vector_ridge"),
        "fold_results": tuple(results),
        "evaluable_rows": len(used_origins),
        "source_grades": tuple(sorted(used_source_grades)),
        "authority": authority,
    }
    result_digest = sha256(_canonical(result_core)).hexdigest()
    return B0Result(
        **result_core,
        result_digest=result_digest,
    )


__all__ = [
    "EXPERIMENT_ID",
    "TARGET_VERSION",
    "FEATURE_NAMES",
    "B0ContractError",
    "B0Protocol",
    "FoldSpec",
    "B0Row",
    "FoldResult",
    "B0Result",
    "validate_protocol",
    "validate_fold",
    "run_b0",
]