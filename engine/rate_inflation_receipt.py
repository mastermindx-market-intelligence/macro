"""Prospective DFII10 five-session point-in-time receipt.

This module is owned by the existing Rates & Inflation / transmission path.  It
creates no store, evaluator, ranking plane, gate or trade authority.  The sole
producer is expected to embed the returned bundle in
``data/transmission/latest.json``; prospective consumers may copy the qualified
measurement into their incumbent append-only evidence row.

Availability law
----------------
``first_known_at`` is the conservative owner capture clock.  It is never inferred
from a FRED observation date.  Exact source retries preserve the earliest owner
capture clock.  A changed source snapshot creates a new receipt.  The bundle keeps
only the current receipt and one prior qualified receipt so a consumer that runs
after the nightly owner can still select the receipt that was actually known at an
intraday decision cut.  There is no historical backfill path.
"""
from __future__ import annotations

import io
import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

DFII10_RECEIPT_SCHEMA = "rates.dfii10_five_session_receipt/v1"
DFII10_BUNDLE_SCHEMA = "rates.dfii10_five_session_bundle/v1"
DFII10_CONTEXT_SCHEMA = "entry_radar.dfii10_context/v1"
DFII10_SERIES_ID = "DFII10"
DFII10_LOOKBACK_SESSIONS = 5
DFII10_CONTEXT_MAX_AGE_SESSIONS = 1
DFII10_CANONICAL_PATH = "data/fred/DFII10.parquet"

MEASUREMENT_ONLY_AUTHORITY: dict[str, bool] = {
    "ranking": False,
    "scoring": False,
    "gating": False,
    "sizing": False,
    "signal_origination": False,
    "position_management": False,
    "trade_execution": False,
}

REVISION_LAW: dict[str, str] = {
    "snapshot_identity": "source_snapshot_hash",
    "exact_retry": (
        "same intrinsic source snapshot preserves the earliest conservative "
        "owner first_known_at"
    ),
    "changed_source": (
        "changed source bytes or bound endpoints emit a new receipt; an already "
        "persisted consumer row is never rewritten"
    ),
    "history": "current plus one prior qualified receipt; no historical backfill",
}


def _utc_timestamp(value: Any) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("timestamp is missing")
    if stamp.tzinfo is None:
        return stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC")


def _utc_iso(value: Any) -> str:
    return _utc_timestamp(value).isoformat().replace("+00:00", "Z")


def _date(value: Any) -> date:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("date is missing")
    return stamp.date()


def _normalise_sessions(completed_sessions: Sequence[Any]) -> list[date]:
    return sorted({_date(value) for value in completed_sessions})


def _source_index_invalid(series: pd.Series | None) -> bool:
    if series is None or len(series) == 0:
        return False
    index = series.index
    return isinstance(index, pd.RangeIndex) or pd.api.types.is_numeric_dtype(index.dtype)


def _normalise_series(series: pd.Series | None) -> dict[date, float]:
    if series is None or len(series) == 0 or _source_index_invalid(series):
        return {}
    numeric = pd.to_numeric(series, errors="coerce").dropna().copy()
    if not numeric.empty:
        numeric = numeric[numeric.map(lambda value: math.isfinite(float(value)))]
    if numeric.empty:
        return {}
    index = pd.to_datetime(numeric.index, errors="coerce", utc=True)
    keep = ~index.isna()
    numeric = numeric.loc[keep]
    index = index[keep].tz_convert(None).normalize()
    numeric.index = index
    numeric = numeric[~numeric.index.duplicated(keep="last")].sort_index()
    return {stamp.date(): float(value) for stamp, value in numeric.items()}


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _has_measurement_only_authority(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and dict(value) == MEASUREMENT_ONLY_AUTHORITY
        and not any(bool(flag) for flag in value.values())
    )


def select_dfii10_series(frame: pd.DataFrame) -> tuple[pd.Series, str]:
    """Return the canonical DFII10 value series without guessing among columns."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("DFII10 source must be a DataFrame")
    if frame.shape[1] == 0:
        return pd.Series(index=frame.index, dtype=float, name=DFII10_SERIES_ID), \
            DFII10_SERIES_ID

    preferred = ("DFII10", "us10y_real", "value")
    by_lower = {str(column).lower(): column for column in frame.columns}
    for wanted in preferred:
        column = by_lower.get(wanted.lower())
        if column is not None:
            return frame[column], str(column)

    numeric_columns = [
        column for column in frame.columns
        if pd.api.types.is_numeric_dtype(frame[column])
    ]
    if len(frame.columns) == 1:
        column = frame.columns[0]
        return frame[column], str(column)
    if len(numeric_columns) == 1:
        column = numeric_columns[0]
        return frame[column], str(column)
    raise ValueError(
        "DFII10 source has ambiguous numeric columns; refuse to infer the series"
    )


def _correction_state(
    previous: Mapping[str, Any] | None,
    source_values: Mapping[date, float],
    source_content_sha256: str | None,
) -> dict[str, Any]:
    if not isinstance(previous, Mapping):
        return {
            "state": "NO_PRIOR_RECEIPT",
            "corrected_endpoints": [],
            "uncomparable_endpoints": [],
        }

    changed: list[dict[str, Any]] = []
    uncomparable: list[str] = []
    for key in ("latest", "prior_five_sessions"):
        endpoint = previous.get(key)
        if not isinstance(endpoint, Mapping) or endpoint.get("observation_date") is None:
            continue
        try:
            day = _date(endpoint["observation_date"])
            previous_value = float(endpoint["value_pct"])
        except (KeyError, TypeError, ValueError):
            uncomparable.append(key)
            continue
        if day not in source_values:
            uncomparable.append(key)
            continue
        current_value = float(source_values[day])
        if abs(current_value - previous_value) > 1e-12:
            changed.append({
                "endpoint": key,
                "observation_date": day.isoformat(),
                "previous_value_pct": previous_value,
                "current_value_pct": current_value,
            })

    if changed:
        state = "BOUND_ENDPOINT_CORRECTION_DETECTED"
    elif uncomparable:
        state = "PRIOR_BOUND_ENDPOINT_NOT_COMPARABLE"
    else:
        previous_source = previous.get("source")
        previous_sha = (
            previous_source.get("content_sha256")
            if isinstance(previous_source, Mapping)
            else None
        )
        state = (
            "UNCHANGED_SOURCE_CONTENT"
            if previous_sha == source_content_sha256
            else "SOURCE_CONTENT_CHANGED_NO_BOUND_ENDPOINT_CORRECTION"
        )
    return {
        "state": state,
        "corrected_endpoints": changed,
        "uncomparable_endpoints": uncomparable,
    }


def _snapshot_identity(receipt: Mapping[str, Any]) -> dict[str, Any]:
    source = receipt.get("source")
    return {
        "schema": receipt.get("schema"),
        "series_id": source.get("series_id") if isinstance(source, Mapping) else None,
        "source_path": source.get("path") if isinstance(source, Mapping) else None,
        "source_column": source.get("column") if isinstance(source, Mapping) else None,
        "source_content_sha256": (
            source.get("content_sha256") if isinstance(source, Mapping) else None
        ),
        "eligible_session": receipt.get("eligible_session"),
        "status": receipt.get("status"),
        "missing_state": receipt.get("missing_state"),
        "stale_state": receipt.get("stale_state"),
        "completed_session_lag": receipt.get("completed_session_lag"),
        "latest": receipt.get("latest"),
        "prior_five_sessions": receipt.get("prior_five_sessions"),
        "delta_bp": receipt.get("delta_bp"),
        "bound_session_window": receipt.get("bound_session_window"),
    }


def _source_snapshot_hash(receipt: Mapping[str, Any]) -> str:
    body = json.dumps(
        _snapshot_identity(receipt),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(body).hexdigest()


def _base_receipt(
    *,
    captured_at: Any,
    eligible_session: date | None,
    source_path: str,
    source_column: str | None,
    source_content_sha256: str | None,
    previous_receipt: Mapping[str, Any] | None,
    source_values: Mapping[date, float],
) -> dict[str, Any]:
    captured = _utc_iso(captured_at)
    return {
        "schema": DFII10_RECEIPT_SCHEMA,
        "measurement_only": True,
        "authority": dict(MEASUREMENT_ONLY_AUTHORITY),
        "status": "MISSING",
        "missing_state": "NONE",
        "stale_state": "UNAVAILABLE",
        "completed_session_lag": None,
        "eligible_session": eligible_session.isoformat() if eligible_session else None,
        "source": {
            "series_id": DFII10_SERIES_ID,
            "path": source_path,
            "column": source_column,
            "content_sha256": source_content_sha256,
            "identity_basis": "exact_canonical_parquet_bytes",
        },
        "latest": None,
        "prior_five_sessions": None,
        "delta_bp": None,
        "bound_session_window": [],
        "capture": {
            "captured_at": captured,
            "first_known_at": captured,
            "availability_basis": "conservative_owner_capture",
            "provider_release_time_inferred": False,
        },
        "correction": _correction_state(
            previous_receipt, source_values, source_content_sha256
        ),
        "revision_law": dict(REVISION_LAW),
    }


def _finalise_receipt(
    receipt: dict[str, Any],
    previous_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    receipt["source_snapshot_hash"] = _source_snapshot_hash(receipt)
    if (
        isinstance(previous_receipt, Mapping)
        and previous_receipt.get("source_snapshot_hash")
        == receipt["source_snapshot_hash"]
        and isinstance(previous_receipt.get("capture"), Mapping)
        and previous_receipt["capture"].get("first_known_at")
    ):
        receipt["capture"]["first_known_at"] = str(
            previous_receipt["capture"]["first_known_at"]
        )
    return receipt


def build_missing_dfii10_receipt(
    *,
    captured_at: Any,
    completed_sessions: Sequence[Any],
    missing_state: str,
    source_path: str = DFII10_CANONICAL_PATH,
    source_column: str | None = None,
    source_content_sha256: str | None = None,
    previous_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sessions = _normalise_sessions(completed_sessions)
    receipt = _base_receipt(
        captured_at=captured_at,
        eligible_session=sessions[-1] if sessions else None,
        source_path=source_path,
        source_column=source_column,
        source_content_sha256=source_content_sha256,
        previous_receipt=previous_receipt,
        source_values={},
    )
    receipt["missing_state"] = str(missing_state)
    return _finalise_receipt(receipt, previous_receipt)


def build_dfii10_five_session_receipt(
    series: pd.Series | None,
    *,
    completed_sessions: Sequence[Any],
    captured_at: Any,
    source_content_sha256: str | None,
    source_path: str = DFII10_CANONICAL_PATH,
    source_column: str | None = None,
    previous_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind exact latest and five-completed-session-prior DFII10 endpoints.

    ``completed_sessions`` must come from the canonical NYSE calendar owner.  The
    source is never filled or aligned to a synthetic grid: the fifth prior session
    must have an observation of its own or the receipt is explicitly missing.
    """
    sessions = _normalise_sessions(completed_sessions)
    source_index_invalid = _source_index_invalid(series)
    values = _normalise_series(series)
    eligible = sessions[-1] if sessions else None
    receipt = _base_receipt(
        captured_at=captured_at,
        eligible_session=eligible,
        source_path=source_path,
        source_column=source_column,
        source_content_sha256=source_content_sha256,
        previous_receipt=previous_receipt,
        source_values=values,
    )

    if not sessions:
        receipt["missing_state"] = "COMPLETED_SESSION_CALENDAR_EMPTY"
    elif source_index_invalid:
        receipt["missing_state"] = "SOURCE_INDEX_INVALID"
    elif not values:
        receipt["missing_state"] = "SOURCE_EMPTY"
    elif not _is_sha256(source_content_sha256):
        receipt["missing_state"] = "SOURCE_CONTENT_IDENTITY_MISSING"
    else:
        eligible_days = [day for day in sessions if day <= eligible and day in values]
        if not eligible_days:
            receipt["missing_state"] = "NO_ELIGIBLE_SOURCE_OBSERVATION"
        else:
            latest_day = eligible_days[-1]
            latest_position = sessions.index(latest_day)
            lag = len(sessions) - 1 - latest_position
            receipt["completed_session_lag"] = lag
            receipt["stale_state"] = (
                "CURRENT_AT_CAPTURE" if lag == 0 else "STALE_AT_CAPTURE"
            )
            receipt["latest"] = {
                "observation_date": latest_day.isoformat(),
                "value_pct": values[latest_day],
            }
            if latest_position < DFII10_LOOKBACK_SESSIONS:
                receipt["missing_state"] = "INSUFFICIENT_COMPLETED_SESSION_HISTORY"
            else:
                start = latest_position - DFII10_LOOKBACK_SESSIONS
                prior_day = sessions[start]
                window = sessions[start:latest_position + 1]
                receipt["bound_session_window"] = [day.isoformat() for day in window]
                if prior_day not in values:
                    receipt["missing_state"] = "EXACT_PRIOR_ENDPOINT_MISSING"
                else:
                    receipt["prior_five_sessions"] = {
                        "observation_date": prior_day.isoformat(),
                        "value_pct": values[prior_day],
                    }
                    receipt["delta_bp"] = round(
                        (values[latest_day] - values[prior_day]) * 100.0, 6
                    )
                    receipt["missing_state"] = "NONE"
                    receipt["status"] = "QUALIFIED" if lag == 0 else "STALE"

    return _finalise_receipt(receipt, previous_receipt)


def _canonical_sessions_for_capture(
    captured_at: Any,
    series: pd.Series | None,
) -> list[date]:
    from lib.nyse_calendar import expected_last_session, sessions_between

    captured = _utc_timestamp(captured_at).to_pydatetime()
    eligible = expected_last_session(captured)
    values = _normalise_series(series)
    start = min(values) if values else eligible - timedelta(days=30)
    return sessions_between(start, eligible)


def capture_dfii10_receipt(
    path: Path,
    *,
    captured_at: Any,
    previous_receipt: Mapping[str, Any] | None = None,
    completed_sessions: Sequence[Any] | None = None,
    source_path: str = DFII10_CANONICAL_PATH,
) -> dict[str, Any]:
    """Read and hash the exact same parquet bytes, then build one owner receipt."""
    path = Path(path)
    if not path.exists():
        sessions = (
            list(completed_sessions)
            if completed_sessions is not None
            else _canonical_sessions_for_capture(captured_at, None)
        )
        return build_missing_dfii10_receipt(
            captured_at=captured_at,
            completed_sessions=sessions,
            missing_state="SOURCE_FILE_MISSING",
            source_path=source_path,
            previous_receipt=previous_receipt,
        )

    try:
        raw = path.read_bytes()
    except OSError:
        sessions = (
            list(completed_sessions)
            if completed_sessions is not None
            else _canonical_sessions_for_capture(captured_at, None)
        )
        return build_missing_dfii10_receipt(
            captured_at=captured_at,
            completed_sessions=sessions,
            missing_state="SOURCE_FILE_UNREADABLE",
            source_path=source_path,
            previous_receipt=previous_receipt,
        )

    content_hash = sha256(raw).hexdigest()
    try:
        frame = pd.read_parquet(io.BytesIO(raw))
        value_series, source_column = select_dfii10_series(frame)
    except Exception:  # source defect is evidence; the owner remains non-fatal
        sessions = (
            list(completed_sessions)
            if completed_sessions is not None
            else _canonical_sessions_for_capture(captured_at, None)
        )
        return build_missing_dfii10_receipt(
            captured_at=captured_at,
            completed_sessions=sessions,
            missing_state="SOURCE_FILE_UNPARSABLE",
            source_path=source_path,
            source_content_sha256=content_hash,
            previous_receipt=previous_receipt,
        )

    sessions = (
        list(completed_sessions)
        if completed_sessions is not None
        else _canonical_sessions_for_capture(captured_at, value_series)
    )
    return build_dfii10_five_session_receipt(
        value_series,
        completed_sessions=sessions,
        captured_at=captured_at,
        source_content_sha256=content_hash,
        source_path=source_path,
        source_column=source_column,
        previous_receipt=previous_receipt,
    )


def build_dfii10_receipt_bundle(
    current: Mapping[str, Any],
    previous_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Keep current plus one prior decision-eligible qualified receipt.

    Multiple changed source captures can occur after an intraday decision but
    before the reconciler runs.  A naive "previous current" slot would let the
    second same-night capture evict the prior-night receipt that was actually
    known at the decision.  Candidates are therefore restricted to receipts
    whose latest observation predates the current eligible session; among those
    we keep the newest observation and then the latest correction known before
    the next session.
    """
    current_dict = dict(current)
    current_hash = current_dict.get("source_snapshot_hash")
    try:
        current_eligible = _date(current_dict.get("eligible_session"))
    except (TypeError, ValueError):
        current_eligible = None
    current_latest = current_dict.get("latest")
    try:
        current_latest_day = (
            _date(current_latest.get("observation_date"))
            if isinstance(current_latest, Mapping)
            else None
        )
    except (TypeError, ValueError):
        current_latest_day = None
    current_binds_eligible_session = (
        current_dict.get("status") == "QUALIFIED"
        and current_eligible is not None
        and current_latest_day == current_eligible
    )

    history_candidates: list[tuple[date, pd.Timestamp, dict[str, Any]]] = []
    seen_hashes: set[str] = set()
    if isinstance(previous_bundle, Mapping):
        for slot in ("current", "previous_qualified"):
            candidate = previous_bundle.get(slot)
            if not isinstance(candidate, Mapping):
                continue
            candidate_dict = dict(candidate)
            candidate_hash = str(candidate_dict.get("source_snapshot_hash") or "")
            if (
                candidate_dict.get("status") != "QUALIFIED"
                or not candidate_hash
                or candidate_hash == current_hash
                or candidate_hash in seen_hashes
            ):
                continue
            latest = candidate_dict.get("latest")
            capture = candidate_dict.get("capture")
            if not isinstance(latest, Mapping) or not isinstance(capture, Mapping):
                continue
            try:
                latest_day = _date(latest.get("observation_date"))
                first_known = _utc_timestamp(capture.get("first_known_at"))
            except (TypeError, ValueError):
                continue
            if current_eligible is not None and latest_day > current_eligible:
                continue
            if current_binds_eligible_session and latest_day == current_eligible:
                continue
            seen_hashes.add(candidate_hash)
            history_candidates.append((latest_day, first_known, candidate_dict))

    previous_qualified = (
        max(history_candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]
        if history_candidates
        else None
    )
    return {
        "schema": DFII10_BUNDLE_SCHEMA,
        "series_id": DFII10_SERIES_ID,
        "measurement_only": True,
        "authority": dict(MEASUREMENT_ONLY_AUTHORITY),
        "current": current_dict,
        "previous_qualified": previous_qualified,
        "history_policy": "current_plus_one_prior_qualified_no_backfill",
        "history_selection": (
            "latest qualified observation strictly before current eligible session; "
            "latest first-known correction wins within that observation date"
        ),
        "revision_law": dict(REVISION_LAW),
    }


def build_dfii10_owner_bundle(
    data_dir: Path,
    *,
    captured_at: Any,
    previous_bundle: Mapping[str, Any] | None = None,
    completed_sessions: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build the bundle embedded in the incumbent transmission contract.

    This helper writes nothing.  ``scripts.build_transmission`` remains the sole
    writer of ``data/transmission/latest.json``.
    """
    previous_receipt = (
        previous_bundle.get("current")
        if isinstance(previous_bundle, Mapping)
        and isinstance(previous_bundle.get("current"), Mapping)
        else None
    )
    try:
        current = capture_dfii10_receipt(
            Path(data_dir) / "fred" / "DFII10.parquet",
            captured_at=captured_at,
            previous_receipt=previous_receipt,
            completed_sessions=completed_sessions,
        )
    except Exception:
        # A calendar/import/programming failure is still explicit measurement
        # absence.  It never becomes a zero, regime label, rank or gate.
        current = build_missing_dfii10_receipt(
            captured_at=captured_at,
            completed_sessions=list(completed_sessions or ()),
            missing_state="OWNER_CAPTURE_ERROR",
            previous_receipt=previous_receipt,
        )
    return build_dfii10_receipt_bundle(current, previous_bundle)


def load_dfii10_bundle(root: Path) -> tuple[dict[str, Any] | None, str]:
    path = Path(root) / "data" / "transmission" / "latest.json"
    if not path.exists():
        return None, "TRANSMISSION_CONTRACT_MISSING"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "TRANSMISSION_CONTRACT_UNREADABLE"
    bundle = payload.get("real_yield_5session") if isinstance(payload, Mapping) else None
    if not isinstance(bundle, Mapping):
        return None, "DFII10_BUNDLE_MISSING"
    if bundle.get("schema") != DFII10_BUNDLE_SCHEMA:
        return None, "DFII10_BUNDLE_SCHEMA_MISMATCH"
    return dict(bundle), "LOADED"


def _unavailable(
    reason: str,
    *,
    decision_known_at: str | None,
    decision_session: str | None,
    load_state: str | None = None,
) -> dict[str, Any]:
    context = {
        "schema": DFII10_CONTEXT_SCHEMA,
        "status": "UNAVAILABLE",
        "reason": reason,
        "decision_known_at": decision_known_at,
        "decision_session": decision_session,
        "authority": dict(MEASUREMENT_ONLY_AUTHORITY),
    }
    if load_state:
        context["load_state"] = load_state
    return context


def _candidate_calendar(
    prior_day: date,
    decision_day: date,
    completed_sessions: Sequence[Any] | None,
) -> list[date]:
    if completed_sessions is not None:
        return _normalise_sessions(completed_sessions)
    from lib.nyse_calendar import sessions_between

    return sessions_between(prior_day, decision_day)


def bind_dfii10_context(
    bundle: Mapping[str, Any] | None,
    *,
    decision_known_at: Any,
    decision_session: Any,
    completed_sessions: Sequence[Any] | None = None,
    load_state: str | None = None,
) -> dict[str, Any]:
    """Select the newest qualified owner receipt actually known at a decision cut."""
    decision_iso = str(decision_known_at) if decision_known_at else None
    decision_session_iso = str(decision_session) if decision_session else None
    if not isinstance(bundle, Mapping):
        return _unavailable(
            load_state or "DFII10_BUNDLE_UNAVAILABLE",
            decision_known_at=decision_iso,
            decision_session=decision_session_iso,
            load_state=load_state,
        )
    if bundle.get("schema") != DFII10_BUNDLE_SCHEMA:
        return _unavailable(
            "DFII10_BUNDLE_SCHEMA_MISMATCH",
            decision_known_at=decision_iso,
            decision_session=decision_session_iso,
        )
    if (
        bundle.get("series_id") != DFII10_SERIES_ID
        or bundle.get("measurement_only") is not True
        or not _has_measurement_only_authority(bundle.get("authority"))
    ):
        return _unavailable(
            "DFII10_BUNDLE_AUTHORITY_INVALID",
            decision_known_at=decision_iso,
            decision_session=decision_session_iso,
        )

    try:
        decision_ts = _utc_timestamp(decision_known_at)
        decision_day = _date(decision_session)
    except (TypeError, ValueError):
        return _unavailable(
            "DECISION_CLOCK_INVALID",
            decision_known_at=decision_iso,
            decision_session=decision_session_iso,
        )

    candidates: list[tuple[pd.Timestamp, date, str, Mapping[str, Any], int]] = []
    rejected: list[str] = []
    for slot in ("current", "previous_qualified"):
        receipt = bundle.get(slot)
        if not isinstance(receipt, Mapping):
            continue
        if receipt.get("schema") != DFII10_RECEIPT_SCHEMA:
            rejected.append(f"{slot}:SCHEMA_MISMATCH")
            continue
        if receipt.get("status") != "QUALIFIED":
            rejected.append(f"{slot}:STATUS_{receipt.get('status')}")
            continue
        source = receipt.get("source")
        capture = receipt.get("capture")
        latest = receipt.get("latest")
        prior = receipt.get("prior_five_sessions")
        if (
            not isinstance(source, Mapping)
            or source.get("series_id") != DFII10_SERIES_ID
            or source.get("path") != DFII10_CANONICAL_PATH
            or not isinstance(source.get("column"), str)
            or not source.get("column")
            or source.get("identity_basis") != "exact_canonical_parquet_bytes"
            or not _is_sha256(source.get("content_sha256"))
        ):
            rejected.append(f"{slot}:SOURCE_IDENTITY_INVALID")
            continue
        if (
            receipt.get("measurement_only") is not True
            or not _has_measurement_only_authority(receipt.get("authority"))
        ):
            rejected.append(f"{slot}:AUTHORITY_INVALID")
            continue
        if not isinstance(capture, Mapping) or not all(
            isinstance(endpoint, Mapping) for endpoint in (latest, prior)
        ):
            rejected.append(f"{slot}:ENDPOINTS_MISSING")
            continue
        try:
            first_known = _utc_timestamp(capture["first_known_at"])
            captured = _utc_timestamp(capture["captured_at"])
            latest_day = _date(latest["observation_date"])
            prior_day = _date(prior["observation_date"])
            latest_value = float(latest["value_pct"])
            prior_value = float(prior["value_pct"])
            delta_bp = float(receipt["delta_bp"])
            window = [_date(value) for value in receipt["bound_session_window"]]
            snapshot_hash = str(receipt["source_snapshot_hash"])
        except (KeyError, TypeError, ValueError):
            rejected.append(f"{slot}:RECEIPT_FIELDS_INVALID")
            continue
        if not _is_sha256(snapshot_hash):
            rejected.append(f"{slot}:HASH_IDENTITY_INVALID")
            continue
        if not all(math.isfinite(value) for value in (latest_value, prior_value, delta_bp)):
            rejected.append(f"{slot}:RECEIPT_NUMERIC_INVALID")
            continue
        if (
            capture.get("availability_basis") != "conservative_owner_capture"
            or capture.get("provider_release_time_inferred") is not False
        ):
            rejected.append(f"{slot}:CAPTURE_BASIS_INVALID")
            continue
        try:
            expected_snapshot_hash = _source_snapshot_hash(receipt)
        except (TypeError, ValueError):
            rejected.append(f"{slot}:SOURCE_SNAPSHOT_HASH_INVALID")
            continue
        if expected_snapshot_hash != snapshot_hash:
            rejected.append(f"{slot}:SOURCE_SNAPSHOT_HASH_MISMATCH")
            continue
        if first_known > captured:
            rejected.append(f"{slot}:FIRST_KNOWN_AFTER_CAPTURE")
            continue
        if (
            len(window) != DFII10_LOOKBACK_SESSIONS + 1
            or window[0] != prior_day
            or window[-1] != latest_day
            or len(set(window)) != len(window)
        ):
            rejected.append(f"{slot}:SESSION_WINDOW_INVALID")
            continue
        calendar = _candidate_calendar(
            prior_day, decision_day, completed_sessions
        )
        canonical_window = [day for day in calendar if prior_day <= day <= latest_day]
        if canonical_window != window:
            rejected.append(f"{slot}:SESSION_WINDOW_NOT_CANONICAL")
            continue
        if abs(delta_bp - ((latest_value - prior_value) * 100.0)) > 1e-6:
            rejected.append(f"{slot}:DELTA_MISMATCH")
            continue
        if (
            receipt.get("eligible_session") != latest_day.isoformat()
            or receipt.get("stale_state") != "CURRENT_AT_CAPTURE"
            or receipt.get("completed_session_lag") != 0
            or receipt.get("missing_state") != "NONE"
        ):
            rejected.append(f"{slot}:PRODUCER_QUALITY_INVALID")
            continue
        if first_known > decision_ts:
            rejected.append(f"{slot}:NOT_KNOWN_AT_DECISION")
            continue
        if latest_day > decision_day:
            rejected.append(f"{slot}:OBSERVATION_AFTER_DECISION")
            continue
        age = sum(latest_day < day <= decision_day for day in calendar)
        if age > DFII10_CONTEXT_MAX_AGE_SESSIONS:
            rejected.append(f"{slot}:STALE_AT_DECISION_{age}")
            continue
        candidates.append((first_known, latest_day, slot, receipt, age))

    if not candidates:
        return _unavailable(
            "NO_QUALIFIED_RECEIPT_AT_DECISION",
            decision_known_at=decision_iso,
            decision_session=decision_session_iso,
            load_state=";".join(rejected) or load_state,
        )

    first_known, _, slot, receipt, age = max(
        candidates, key=lambda candidate: (candidate[1], candidate[0])
    )
    source = receipt["source"]
    latest = receipt["latest"]
    prior = receipt["prior_five_sessions"]
    correction = receipt.get("correction") or {}
    return {
        "schema": DFII10_CONTEXT_SCHEMA,
        "status": "QUALIFIED",
        "reason": "OWNER_RECEIPT_KNOWN_AT_DECISION",
        "decision_known_at": decision_iso,
        "decision_session": decision_session_iso,
        "receipt_source_slot": slot,
        "source_series_id": DFII10_SERIES_ID,
        "source_snapshot_hash": receipt.get("source_snapshot_hash"),
        "source_content_sha256": source.get("content_sha256"),
        "receipt_first_known_at": first_known.isoformat().replace("+00:00", "Z"),
        "receipt_captured_at": str(receipt["capture"]["captured_at"]),
        "latest_observation_date": str(latest["observation_date"]),
        "latest_value_pct": float(latest["value_pct"]),
        "prior_observation_date": str(prior["observation_date"]),
        "prior_value_pct": float(prior["value_pct"]),
        "delta_bp": float(receipt["delta_bp"]),
        "receipt_age_completed_sessions": age,
        "correction_state": correction.get("state"),
        "authority": dict(MEASUREMENT_ONLY_AUTHORITY),
    }


def flatten_dfii10_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Stable columns copied into the incumbent prospective evidence row."""
    return {
        "dfii10_context_status": context.get("status"),
        "dfii10_context_reason": context.get("reason"),
        "dfii10_context_load_state": context.get("load_state"),
        "dfii10_source_snapshot_hash": context.get("source_snapshot_hash"),
        "dfii10_source_content_sha256": context.get("source_content_sha256"),
        "dfii10_receipt_first_known_at": context.get("receipt_first_known_at"),
        "dfii10_receipt_captured_at": context.get("receipt_captured_at"),
        "dfii10_latest_observation_date": context.get("latest_observation_date"),
        "dfii10_latest_value_pct": context.get("latest_value_pct"),
        "dfii10_prior_observation_date": context.get("prior_observation_date"),
        "dfii10_prior_value_pct": context.get("prior_value_pct"),
        "dfii10_delta_bp": context.get("delta_bp"),
        "dfii10_receipt_age_sessions": context.get("receipt_age_completed_sessions"),
        "dfii10_correction_state": context.get("correction_state"),
        "dfii10_context_json": json.dumps(
            dict(context), sort_keys=True, separators=(",", ":"), allow_nan=False
        ),
    }


__all__ = [
    "DFII10_BUNDLE_SCHEMA",
    "DFII10_CANONICAL_PATH",
    "DFII10_CONTEXT_MAX_AGE_SESSIONS",
    "DFII10_CONTEXT_SCHEMA",
    "DFII10_LOOKBACK_SESSIONS",
    "DFII10_RECEIPT_SCHEMA",
    "DFII10_SERIES_ID",
    "MEASUREMENT_ONLY_AUTHORITY",
    "REVISION_LAW",
    "bind_dfii10_context",
    "build_dfii10_five_session_receipt",
    "build_dfii10_owner_bundle",
    "build_dfii10_receipt_bundle",
    "build_missing_dfii10_receipt",
    "capture_dfii10_receipt",
    "flatten_dfii10_context",
    "load_dfii10_bundle",
    "select_dfii10_series",
]
