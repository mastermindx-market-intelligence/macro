"""Outcome-blind FS-5 admission receipts; no grade, feature, or model access."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd
from lib.flow_score import map_model_bucket
from lib.nyse_calendar import session_n_forward
from lib.flow_score_geometry import BUCKET_HORIZONS, FS5_EVALUATION_SPEC_VERSION

SCHEMA = "flow_signals.fs5_partition/v1"
SPEC_SCHEMA = "flow_signals.fs5_admission_spec/v1"
POPULATIONS = ("train", "calibration_fit", "calibration_eval", "final_oos")
HORIZONS = BUCKET_HORIZONS
CALENDAR = "NYSE-rule-calendar/v1"
STAGE_SCHEMA = "live_flow.event_stage/v1"
ET = ZoneInfo("America/New_York")
SOURCE_FIELDS = (
    "event_id",
    "root",
    "decision_at",
    "available_at",
    "source_stage_observed_at",
    "source_stage_key",
    "source_stage_schema",
    "source_stage_prefix_records",
    "source_stage_prefix_sha256",
)
FORBIDDEN = ("grade", "label", "spy_excess", "return", "target", "outcome")
CENSUS_SCHEMA = "flow_signals.fs5_source_census/v1"
CENSUS_KEYS = (
    "schema",
    "sealed_at",
    "row_count",
    "projection_sha256",
    "anchors",
)
ANCHOR_KEYS = (
    "source_stage_key",
    "source_stage_schema",
    "prefix_records",
    "prefix_sha256",
)
# Amendment §3.3 index roots. Admission and the trainer share this set.
INDEX_ROOTS: frozenset[str] = frozenset(
    {
        "SPX",
        "SPXW",
        "NDX",
        "RUT",
        "VIX",
        "VIXW",
        "OEX",
        "XEO",
        "DJX",
        "MNX",
    }
)


class AdmissionError(ValueError):
    pass


def _text(value: Any) -> str:
    if value is None or not pd.api.types.is_scalar(value) or pd.isna(value):
        return ""
    return value.isoformat() if isinstance(value, pd.Timestamp) else str(value).strip()


def _clock(value: Any, field: str) -> pd.Timestamp:
    try:
        if not isinstance(value, (str, datetime, pd.Timestamp)):
            raise ValueError("clock must be an aware UTC timestamp")
        parsed = pd.Timestamp(value)
        if (
            pd.isna(parsed)
            or parsed.tzinfo is None
            or parsed.utcoffset().total_seconds() != 0
        ):
            raise ValueError("clock must be an aware UTC timestamp")
        return parsed.tz_convert("UTC")
    except (TypeError, ValueError, OverflowError) as exc:
        raise AdmissionError(f"admission_{field}_invalid") from exc


def _digest(value: Mapping[str, Any]) -> str:
    try:
        payload = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise AdmissionError("admission_spec_not_canonical_json") from exc
    return hashlib.sha256(payload.encode()).hexdigest()


def derived_model_bucket(dte_bucket: Any) -> str | None:
    """Return the model bucket implied by ``dte_bucket``.

    This is ``map_model_bucket``. A source-declared ``model_bucket`` is not
    an input to the choice.
    """
    if isinstance(dte_bucket, str):
        text = dte_bucket.strip()
        return map_model_bucket(text) if text else None
    try:
        if dte_bucket is None or pd.isna(dte_bucket):
            return None
    except TypeError:
        return None
    text = str(dte_bucket).strip()
    return map_model_bucket(text) if text else None


def _canonical_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or type(value).__name__ == "bool_":
        raise AdmissionError("admission_source_selection_input_invalid")
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        raise AdmissionError("admission_source_selection_input_invalid")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AdmissionError("admission_source_selection_input_invalid") from exc
    if not math.isfinite(number):
        raise AdmissionError("admission_source_selection_input_invalid")
    if number.is_integer():
        return int(number)
    return number


_OI_PRIORITY = ("prior_oi", "oi", "open_interest")
_ANCHOR_FROM_ROW = (
    ("source_stage_key", "source_stage_key"),
    ("source_stage_schema", "source_stage_schema"),
    ("prefix_records", "source_stage_prefix_records"),
    ("prefix_sha256", "source_stage_prefix_sha256"),
)


def canonical_index_root(value: Any) -> str:
    """Stripped upper root shared by the census projection and the index filter."""
    return _text(value).upper()


def _column_type_token(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series.dtype):
        return "bool"
    if pd.api.types.is_numeric_dtype(series.dtype):
        return "number"
    if pd.api.types.is_string_dtype(series.dtype):
        return "string"
    return "object"


def _value_type_token(value: Any) -> str:
    if isinstance(value, bool) or type(value).__name__ == "bool_":
        return "bool"
    if value is None:
        return "null"
    try:
        if pd.isna(value):
            return "null"
    except TypeError:
        return type(value).__name__
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    return type(value).__name__


def _json_bool(value: Any) -> bool | None:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return bool(value)


def resolve_index_population(
    df: pd.DataFrame,
    index_roots: frozenset[str] | None = None,
) -> dict[str, Any]:
    """One column-priority selection law for projection and the index filter.

    OI priority is the first present column of prior_oi, oi, open_interest.
    A present all-null column is that source; it does not fall back per row.
    """
    if index_roots is None:
        index_roots = INDEX_ROOTS
    if "root" in df.columns:
        roots = df["root"].map(canonical_index_root)
        is_index = roots.isin(index_roots)
    else:
        roots = pd.Series("", index=df.index)
        is_index = pd.Series(False, index=df.index)
    present = [name for name in _OI_PRIORITY if name in df.columns]
    oi_source = present[0] if present else None
    if oi_source is None:
        oi_values = pd.Series(0.0, index=df.index)
    else:
        oi_values = pd.to_numeric(df[oi_source], errors="coerce").fillna(0)
    if "zerodte" in df.columns:
        is_zerodte = df["zerodte"].astype(bool, errors="ignore")
        zerodte_column_type = _column_type_token(df["zerodte"])
        zerodte_present = True
    elif "dte_bucket" in df.columns:
        is_zerodte = df["dte_bucket"] == "0d"
        zerodte_column_type = "absent"
        zerodte_present = False
    else:
        is_zerodte = pd.Series(False, index=df.index)
        zerodte_column_type = "absent"
        zerodte_present = False
    return {
        "root_key": roots,
        "is_index": is_index,
        "oi_source": oi_source,
        "oi_columns_present": present,
        "oi_column_types": {name: _column_type_token(df[name]) for name in present},
        "oi_values": oi_values,
        "oi_readmitted": is_index & (oi_values > 500),
        "zerodte_present": zerodte_present,
        "zerodte_column_type": zerodte_column_type,
        "is_zerodte": is_zerodte,
    }


def _population_masks(
    df: pd.DataFrame,
    bucket: str,
    index_roots: frozenset[str] | None = None,
) -> tuple[dict[str, Any], pd.Series, pd.Series]:
    law = resolve_index_population(df, index_roots)
    is_index = law["is_index"]
    zerodte_index_mask = is_index & law["is_zerodte"]
    if bucket == "0_7":
        excluded = is_index & (~law["oi_readmitted"] | zerodte_index_mask)
    else:
        excluded = is_index & ~law["oi_readmitted"]
    return law, excluded, zerodte_index_mask


def index_population_excluded_mask(
    df: pd.DataFrame,
    bucket: str,
    index_roots: frozenset[str] | None = None,
) -> pd.Series:
    """Row mask for amendment §3.3. Prior OI column order is prior_oi, oi, open_interest."""
    _law, excluded, _zerodte_index_mask = _population_masks(df, bucket, index_roots)
    return excluded


def apply_population_filter(
    df: pd.DataFrame,
    bucket: str,
    index_roots: frozenset[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply amendment §3.3 and return the kept rows plus the incumbent stats."""
    law, excluded, zerodte_index_mask = _population_masks(df, bucket, index_roots)
    is_index = law["is_index"]
    oi_readmitted = law["oi_readmitted"]
    stats = {
        "total_input": int(len(df)),
        "index_excluded_n": int((is_index & ~oi_readmitted).sum()),
        "oi_readmitted_n": int(oi_readmitted.sum()),
        "zerodte_index_excluded_n": int(zerodte_index_mask.sum()),
        "total_output": int((~excluded).sum()),
    }
    return df.loc[~excluded].reset_index(drop=True), stats


def _selection_inputs(
    record: Mapping[str, Any], *, law: Mapping[str, Any], position: int
) -> dict[str, Any]:
    present = set(record)
    oi_source = law["oi_source"]
    return {
        "dte_bucket": _text(record.get("dte_bucket")),
        "prior_oi": _canonical_number(record.get("prior_oi")) if "prior_oi" in present else None,
        "oi": _canonical_number(record.get("oi")) if "oi" in present else None,
        "open_interest": (
            _canonical_number(record.get("open_interest"))
            if "open_interest" in present
            else None
        ),
        "oi_source": oi_source,
        "oi_columns_present": list(law["oi_columns_present"]),
        "oi_column_types": dict(law["oi_column_types"]),
        "oi_filter_value": (
            _canonical_number(law["oi_values"].iloc[position])
            if oi_source is not None
            else None
        ),
        "zerodte_present": bool(law["zerodte_present"]),
        "zerodte_column_type": law["zerodte_column_type"],
        "zerodte_type": (
            _value_type_token(record.get("zerodte"))
            if law["zerodte_present"]
            else "absent"
        ),
        "zerodte_resolved": _json_bool(law["is_zerodte"].iloc[position]),
    }


def _project_record(
    record: Mapping[str, Any],
    *,
    bucket: str,
    cutoff: pd.Timestamp,
    law: Mapping[str, Any],
    position: int,
) -> dict[str, Any] | None:
    """One closed pre-cutoff row, or None when it is outside this sealed universe.

    Null proof clocks stay null. They are not copied from raw availability or
    from the receipt. Rows observed after the cutoff are later ledger growth.
    Decision, availability, and the actual observed clock are parsed here, and
    only ordered clocks enter the seal.
    """
    decision_text = _text(record.get("decision_at"))
    available_text = _text(record.get("available_at"))
    observed_text = _text(record.get("source_stage_observed_at"))
    if not decision_text or not available_text or not observed_text:
        return None
    observed = _clock(observed_text, "source_stage_observed_at")
    if observed > cutoff:
        return None
    inputs = _selection_inputs(record, law=law, position=position)
    derived = derived_model_bucket(inputs["dte_bucket"])
    if derived != bucket:
        return None
    decision = _clock(decision_text, "decision_at")
    available = _clock(available_text, "available_at")
    event_id = _text(record.get("event_id"))
    if not decision <= available <= observed:
        raise AdmissionError("admission_source_clocks_invalid:" + (event_id or "missing"))
    declared = _text(record.get("model_bucket"))
    if declared and declared != derived:
        raise AdmissionError("admission_source_model_bucket_contradicts:" + event_id)
    if not event_id:
        raise AdmissionError("admission_source_event_id_invalid")
    stage_key = _text(record.get("source_stage_key"))
    stage_schema = _text(record.get("source_stage_schema"))
    if stage_schema != STAGE_SCHEMA or not re.fullmatch(
        r"live_flow/events/\d{4}-\d{2}-\d{2}\.jsonl", stage_key
    ):
        raise AdmissionError("admission_source_stage_identity_invalid")
    prefix_records = _count_text(record.get("source_stage_prefix_records"))
    prefix_hash = _text(record.get("source_stage_prefix_sha256")).lower()
    if not re.fullmatch(r"[a-f0-9]{64}", prefix_hash):
        raise AdmissionError("admission_source_stage_prefix_sha256_invalid")
    projected = {
        "source": _text(record.get("source")),
        "detector_version": _text(record.get("detector_version")),
        "event_id": event_id,
        "root": _text(record.get("root")),
        "model_bucket": derived,
        "decision_at": decision_text,
        "available_at": available_text,
        "source_stage_observed_at": observed_text,
        "source_stage_key": stage_key,
        "source_stage_schema": stage_schema,
        "source_stage_prefix_records": prefix_records,
        "source_stage_prefix_sha256": prefix_hash,
    }
    projected.update(inputs)
    return projected


def closed_source_projection(
    rows: pd.DataFrame, *, bucket: str, availability_cutoff: str | datetime | pd.Timestamp
) -> list[dict[str, Any]]:
    """Canonical pre-cutoff projection for one model bucket, before the index filter."""
    if "dte_bucket" not in rows.columns:
        raise AdmissionError("admission_source_dte_bucket_missing")
    cutoff = _clock(availability_cutoff, "availability_cutoff")
    law = resolve_index_population(rows)
    projected: list[dict[str, Any]] = []
    for position, record in enumerate(rows.to_dict("records")):
        item = _project_record(
            record, bucket=bucket, cutoff=cutoff, law=law, position=position
        )
        if item is not None:
            projected.append(item)
    if len({item["event_id"] for item in projected}) != len(projected):
        raise AdmissionError("admission_source_duplicate_event_id")
    projected.sort(key=lambda item: item["event_id"])
    return projected


def _anchors_from_projection(projected: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in projected:
        anchor = {
            anchor_key: str(item[row_key]) for anchor_key, row_key in _ANCHOR_FROM_ROW
        }
        ident = tuple(anchor[key] for key in ANCHOR_KEYS)
        if ident in seen:
            continue
        seen.add(ident)
        anchors.append(anchor)
    anchors.sort(key=lambda item: tuple(item[key] for key in ANCHOR_KEYS))
    return anchors


def _census_from_projection(
    projected: list[Mapping[str, Any]], *, sealed_at: str
) -> dict[str, Any]:
    payload = json.dumps(
        projected, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return {
        "schema": CENSUS_SCHEMA,
        "sealed_at": _text(sealed_at),
        "row_count": len(projected),
        "projection_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "anchors": _anchors_from_projection(projected),
    }


def source_census_descriptor(
    rows: pd.DataFrame | list[Mapping[str, Any]],
    *,
    sealed_at: str,
    bucket: str,
    availability_cutoff: str | datetime | pd.Timestamp,
) -> dict[str, Any]:
    """External, source-only census of the original pre-cutoff universe.

    The descriptor binds the row count, the projection digest, and the closed
    stage-prefix anchors. It does not read a receipt and it does not apply the
    index population filter.
    """
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if frame.columns.duplicated().any():
        raise AdmissionError("admission_source_frame_invalid")
    projected = closed_source_projection(
        frame, bucket=bucket, availability_cutoff=availability_cutoff
    )
    return _census_from_projection(projected, sealed_at=sealed_at)


def _canonical_census_document(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(CENSUS_KEYS):
        raise AdmissionError("admission_source_census_missing")
    if value.get("schema") != CENSUS_SCHEMA or not _text(value.get("sealed_at")):
        raise AdmissionError("admission_source_census_missing")
    row_count = value.get("row_count")
    try:
        count = int(row_count)
        if type(row_count) is bool or float(row_count) != count or count < 0:
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise AdmissionError("admission_source_census_missing") from exc
    digest = _text(value.get("projection_sha256")).lower()
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise AdmissionError("admission_source_census_missing")
    raw_anchors = value.get("anchors")
    if not isinstance(raw_anchors, list):
        raise AdmissionError("admission_source_census_missing")
    anchors: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for anchor in raw_anchors:
        if not isinstance(anchor, Mapping) or set(anchor) != set(ANCHOR_KEYS):
            raise AdmissionError("admission_source_census_missing")
        item = {
            "source_stage_key": _text(anchor.get("source_stage_key")),
            "source_stage_schema": _text(anchor.get("source_stage_schema")),
            "prefix_records": _count_text(anchor.get("prefix_records")),
            "prefix_sha256": _text(anchor.get("prefix_sha256")).lower(),
        }
        if item["source_stage_schema"] != STAGE_SCHEMA or not re.fullmatch(
            r"live_flow/events/\d{4}-\d{2}-\d{2}\.jsonl", item["source_stage_key"]
        ):
            raise AdmissionError("admission_source_census_missing")
        if not re.fullmatch(r"[a-f0-9]{64}", item["prefix_sha256"]):
            raise AdmissionError("admission_source_census_missing")
        ident = tuple(item[key] for key in ANCHOR_KEYS)
        if ident in seen:
            raise AdmissionError("admission_source_census_missing")
        seen.add(ident)
        anchors.append(item)
    anchors.sort(key=lambda item: tuple(item[key] for key in ANCHOR_KEYS))
    return {
        "schema": CENSUS_SCHEMA,
        "sealed_at": _text(value.get("sealed_at")),
        "row_count": count,
        "projection_sha256": digest,
        "anchors": anchors,
    }


def _assert_external_census(
    study: Mapping[str, Any],
    expected_study: Mapping[str, Any],
    cutoff: pd.Timestamp,
    admitted_at: pd.Timestamp,
) -> dict[str, Any]:
    """The receipt copy must equal the external seal. Neither side is optional."""
    if "source_census" not in expected_study:
        raise AdmissionError("admission_source_census_missing")
    external = _canonical_census_document(expected_study.get("source_census"))
    if "source_census" not in study:
        raise AdmissionError("admission_source_census_not_external")
    declared = _canonical_census_document(study.get("source_census"))
    if declared != external:
        raise AdmissionError("admission_source_census_not_external")
    sealed = _clock(external["sealed_at"], "source_census_sealed_at")
    if not cutoff < sealed <= admitted_at:
        raise AdmissionError("admission_source_census_clocks_invalid")
    return external


def _count_text(value: Any) -> str:
    try:
        count = int(value)
        if type(value) is bool or float(value) != count or count < 2:
            raise ValueError
        return str(count)
    except (TypeError, ValueError, OverflowError):
        raise AdmissionError("admission_source_stage_prefix_records_invalid")


def _reject_outcomes(receipt: Mapping[str, Any], rows: pd.DataFrame) -> None:
    def walk(v: Any) -> None:
        if isinstance(v, Mapping):
            for k, child in v.items():
                if str(k).lower() != "planned_outcome_end_sessions" and any(
                    x in str(k).lower() for x in FORBIDDEN
                ):
                    raise AdmissionError(f"admission_outcome_dependent_field:{k}")
                walk(child)
        elif isinstance(v, list):
            for child in v:
                walk(child)

    walk(receipt)
    reserved = {"population", "fill_date", "planned_fill_date", "planned_fill_open"}
    bad = [c for c in rows if c in reserved or any(x in c.lower() for x in FORBIDDEN)]
    if bad:
        raise AdmissionError(
            "admission_source_rows_include_outcomes:" + ",".join(sorted(bad))
        )


def _endpoints(decision: pd.Timestamp, bucket: str) -> tuple[str, str, dict[str, str]]:
    if bucket not in HORIZONS:
        raise AdmissionError("admission_bucket_unknown")
    decision_session = decision.to_pydatetime().astimezone(ET).date()
    fill = session_n_forward(decision_session, 1)
    if fill is None:
        raise AdmissionError("admission_next_session_unavailable")
    open_at = (
        datetime.combine(fill, time(9, 30), ET)
        .astimezone(ZoneInfo("UTC"))
        .isoformat()
        .replace("+00:00", "Z")
    )
    ends = {str(h): session_n_forward(fill, h) for h in HORIZONS[bucket]}
    if any(v is None for v in ends.values()):
        raise AdmissionError("admission_horizon_session_unavailable")
    return open_at, fill.isoformat(), {h: v.isoformat() for h, v in ends.items()}


def _member(entry: Mapping[str, Any], bucket: str) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        raise AdmissionError("admission_member_invalid")
    missing = [f for f in SOURCE_FIELDS if not _text(entry.get(f))]
    if missing:
        raise AdmissionError("admission_receipt_field_missing:" + ",".join(missing))
    if _text(entry["source_stage_schema"]) != STAGE_SCHEMA or not re.fullmatch(
        r"live_flow/events/\d{4}-\d{2}-\d{2}\.jsonl", _text(entry["source_stage_key"])
    ):
        raise AdmissionError("admission_source_stage_identity_invalid")
    count = _count_text(entry["source_stage_prefix_records"])
    if not re.fullmatch(
        r"[a-f0-9]{64}", _text(entry["source_stage_prefix_sha256"]).lower()
    ):
        raise AdmissionError("admission_source_stage_prefix_sha256_invalid")
    decision = _clock(entry["decision_at"], "decision_at")
    open_at, fill, ends = _endpoints(decision, bucket)
    if (
        _text(entry.get("planned_fill_open")) != open_at
        or _text(entry.get("planned_fill_date")) != fill
        or entry.get("planned_outcome_end_sessions") != ends
    ):
        raise AdmissionError("admission_planned_calendar_boundary_mismatch")
    values = {f: _text(entry[f]) for f in SOURCE_FIELDS}
    values["source_stage_prefix_records"] = count
    return values | {
        "planned_fill_open": open_at,
        "planned_fill_date": fill,
        "planned_outcome_end_sessions": ends,
    }


def validate_admission_study_identity(
    receipt: Mapping[str, Any],
    *,
    bucket: str,
    validation_at: str | datetime | pd.Timestamp,
    expected_study: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate the external, outcome-blind study binding before source loading.

    The returned identity selects exactly one declared source and detector.  It
    intentionally does not inspect members or any source rows; those checks
    remain in ``validate_admission_receipt`` after the selected immutable
    source universe is loaded.
    """
    if not isinstance(receipt, Mapping):
        raise AdmissionError("admission_document_invalid")
    checked_at = _clock(validation_at, "validation_at")
    if receipt.get("schema") != SCHEMA:
        raise AdmissionError("admission_schema_unknown")
    study, spec, pops = (
        receipt.get("study"),
        receipt.get("study_spec"),
        receipt.get("populations"),
    )
    if (
        not isinstance(study, Mapping)
        or not isinstance(spec, Mapping)
        or spec.get("schema") != SPEC_SCHEMA
    ):
        raise AdmissionError("admission_study_or_spec_missing")
    if _text(study.get("spec_digest")) != _digest(spec):
        raise AdmissionError("admission_spec_digest_mismatch")
    required = (
        "study_ref", "evaluation_spec_version", "source", "detector_version",
        "model_bucket", "calendar", "frozen_at", "admitted_at",
        "availability_cutoff",
    )
    if any(not _text(study.get(f)) for f in required) or not isinstance(
        study.get("horizons"), list
    ):
        raise AdmissionError("admission_study_fields_missing")
    if _text(study["model_bucket"]) != bucket or tuple(study["horizons"]) != HORIZONS.get(bucket):
        raise AdmissionError("admission_bucket_horizon_mismatch")
    if (
        study["calendar"] != CALENDAR
        or study["evaluation_spec_version"] != FS5_EVALUATION_SPEC_VERSION
    ):
        raise AdmissionError("admission_calendar_or_evaluation_spec_unknown")
    if not isinstance(expected_study, Mapping):
        raise AdmissionError("admission_expected_study_missing")
    for field in ("study_ref", "spec_digest", "frozen_at"):
        if _text(expected_study.get(field)) != _text(study.get(field)):
            raise AdmissionError("admission_expected_study_mismatch:" + field)
    for f in (
        "evaluation_spec_version", "source", "detector_version", "model_bucket",
        "calendar", "horizons",
    ):
        if spec.get(f) != study.get(f):
            raise AdmissionError("admission_spec_identity_mismatch:" + f)
    if _text(spec.get("fixed_availability_cutoff")) != _text(
        study.get("availability_cutoff")
    ):
        raise AdmissionError("admission_cutoff_not_bound_to_spec")
    if not isinstance(pops, Mapping) or set(pops) != set(POPULATIONS):
        raise AdmissionError("admission_populations_not_bound")
    frozen_at, admitted_at, cutoff = (
        _clock(study[x], x) for x in ("frozen_at", "admitted_at", "availability_cutoff")
    )
    if not frozen_at < cutoff <= admitted_at <= checked_at:
        raise AdmissionError("admission_study_clocks_invalid")
    # The external seal is required even before any source row is loaded.
    # A receipt that carries its own census is not authority.
    _assert_external_census(study, expected_study, cutoff, admitted_at)
    return dict(study)


def validate_admission_receipt(
    receipt: Mapping[str, Any],
    source_rows: pd.DataFrame,
    *,
    bucket: str,
    validation_at: str | datetime | pd.Timestamp,
    expected_study: Mapping[str, Any] | None = None,
    stage_receipt_resolver: Callable[[str], bytes] | None = None,
) -> pd.DataFrame:
    """Admit a complete cohort against a separately accepted, frozen study.

    ``expected_study`` comes from the owning trainer configuration, never the
    receipt. ``validation_at`` is the caller's actual verification clock. Raw
    R2 reads verify immutable content; they do not replace the collector's
    original first-observation clock. No study binding means no admission.
    """
    if (
        not isinstance(source_rows, pd.DataFrame)
        or source_rows.columns.duplicated().any()
        or any(not isinstance(c, str) for c in source_rows.columns)
    ):
        raise AdmissionError("admission_source_frame_invalid")
    _reject_outcomes(receipt, source_rows)
    study = validate_admission_study_identity(
        receipt,
        bucket=bucket,
        validation_at=validation_at,
        expected_study=expected_study,
    )
    spec, pops = receipt["study_spec"], receipt["populations"]
    plan_pops = spec.get("populations")
    if (
        not isinstance(pops, Mapping)
        or not isinstance(plan_pops, Mapping)
        or set(pops) != set(POPULATIONS)
        or set(plan_pops) != set(POPULATIONS)
    ):
        raise AdmissionError("admission_populations_not_bound")
    frozen_at, admitted_at, cutoff = (
        _clock(study[x], x) for x in ("frozen_at", "admitted_at", "availability_cutoff")
    )
    rows = source_rows.copy()
    missing = [
        f
        for f in (*SOURCE_FIELDS, "source", "detector_version", "dte_bucket")
        if f not in rows
    ]
    if missing:
        raise AdmissionError("admission_source_fields_missing:" + ",".join(missing))
    for f in ("source", "detector_version"):
        if not rows[f].map(_text).eq(_text(study[f])).all():
            raise AdmissionError("admission_source_identity_mismatch:" + f)
    if not rows.event_id.map(
        lambda value: isinstance(value, str) and bool(value) and value == value.strip()
    ).all():
        raise AdmissionError("admission_source_event_id_invalid")
    if rows.event_id.map(_text).duplicated().any():
        raise AdmissionError("admission_source_duplicate_event_id")
    # The sealed universe is the complete pre-cutoff projection for this derived
    # bucket, including rows the index filter will later drop. It is compared
    # before any member is accepted and before grades can be opened.
    external_census = _assert_external_census(study, expected_study, cutoff, admitted_at)
    projected = closed_source_projection(
        rows, bucket=bucket, availability_cutoff=study["availability_cutoff"]
    )
    actual_census = _census_from_projection(
        projected, sealed_at=external_census["sealed_at"]
    )
    if actual_census != external_census:
        raise AdmissionError("admission_source_census_mismatch")
    projected_ids = {item["event_id"] for item in projected}
    excluded_ids = {
        _text(event_id)
        for event_id, excluded in zip(
            rows["event_id"], index_population_excluded_mask(rows, bucket)
        )
        if bool(excluded)
    }
    by_id = {_text(r.event_id): r for r in rows.itertuples(index=False)}
    frozen: list[dict[str, Any]] = []
    roots: set[str] = set()
    prior_end = None
    windows: list[tuple[set[str], pd.Timestamp, pd.Timestamp]] = []
    frozen_ids: set[str] = set()
    for population in POPULATIONS:
        declared, plan_declared = pops[population], plan_pops[population]
        if (
            not isinstance(declared, Mapping)
            or not isinstance(declared.get("window"), Mapping)
            or not isinstance(declared.get("members"), list)
            or not declared["members"]
        ):
            raise AdmissionError("admission_population_missing:" + population)
        if (
            not isinstance(plan_declared, Mapping)
            or not isinstance(plan_declared.get("window"), Mapping)
            or not isinstance(plan_declared.get("roots"), list)
            or not plan_declared["roots"]
        ):
            raise AdmissionError("admission_plan_population_missing:" + population)
        if declared["window"] != plan_declared["window"]:
            raise AdmissionError("admission_window_not_bound_to_spec:" + population)
        start, end = _clock(declared["window"].get("start"), "window_start"), _clock(
            declared["window"].get("end"), "window_end"
        )
        if start > end or (prior_end is not None and start <= prior_end):
            raise AdmissionError("admission_windows_not_ordered")
        if frozen_at >= start or end > cutoff:
            raise AdmissionError("admission_window_outside_frozen_study")
        prior_end = end
        declared_roots = {_text(root).upper() for root in plan_declared["roots"]}
        if "" in declared_roots or roots.intersection(declared_roots):
            raise AdmissionError("admission_roots_not_globally_disjoint")
        roots.update(declared_roots)
        windows.append((declared_roots, start, end))
        for entry in declared["members"]:
            plan = _member(entry, bucket)
            eid = plan["event_id"]
            if eid in frozen_ids:
                raise AdmissionError("admission_member_duplicate")
            if eid not in projected_ids:
                raise AdmissionError("admission_member_outside_source_census:" + eid)
            if eid in excluded_ids:
                raise AdmissionError("admission_population_excluded_member:" + eid)
            row = by_id.get(eid)
            if row is None:
                raise AdmissionError("admission_member_missing_from_source:" + eid)
            actual = {
                f: (
                    _count_text(getattr(row, f))
                    if f == "source_stage_prefix_records"
                    else _text(getattr(row, f))
                )
                for f in SOURCE_FIELDS
            }
            if actual != {f: plan[f] for f in SOURCE_FIELDS}:
                raise AdmissionError("admission_source_receipt_changed:" + eid)
            decision, available, observed = (
                _clock(actual[f], f)
                for f in ("decision_at", "available_at", "source_stage_observed_at")
            )
            if not (
                frozen_at <= decision
                and start <= decision <= end
                and decision <= available <= observed <= cutoff <= admitted_at
            ):
                raise AdmissionError("admission_clocks_or_window_invalid:" + eid)
            if observed > _clock(plan["planned_fill_open"], "planned_fill_open"):
                raise AdmissionError(
                    "admission_observed_after_planned_fill_open:" + eid
                )
            root = plan["root"].upper()
            if root != actual["root"].upper() or root not in declared_roots:
                raise AdmissionError("admission_member_root_outside_plan")
            frozen.append({**plan, "population": population})
            frozen_ids.add(eid)
    if len(roots) < 4:
        raise AdmissionError("admission_insufficient_root_diversity")
    exclusions = receipt.get("exclusions")
    if not isinstance(exclusions, Mapping):
        raise AdmissionError("admission_exclusions_invalid")
    # The ledger grows after the frozen cutoff.  Later rows may never expand
    # the cohort, and need no retrofit into the immutable exclusion receipt.
    for row in rows.itertuples(index=False):
        event_id = row.event_id
        if event_id in frozen_ids:
            if event_id in exclusions:
                raise AdmissionError("admission_member_also_excluded:" + event_id)
            continue
        derived = derived_model_bucket(getattr(row, "dte_bucket", None))
        if derived != bucket or _text(event_id) in excluded_ids:
            # Other DTE buckets, and index rows the shared population law drops,
            # are outside this eligible set. They remain inside the census when
            # they are pre-cutoff rows of this bucket.
            continue
        if not all(_text(getattr(row, field)) for field in SOURCE_FIELDS[2:]):
            reason = "ineligible_legacy"
        else:
            decision, available, observed = (
                _clock(getattr(row, field), field)
                for field in ("decision_at", "available_at", "source_stage_observed_at")
            )
            if not decision <= available <= observed:
                raise AdmissionError("admission_source_clocks_invalid:" + event_id)
            if observed > cutoff:
                continue
            inside = any(
                _text(row.root).upper() in population_roots and start <= decision <= end
                for population_roots, start, end in windows
            )
            if not inside:
                reason = "outside_declared_root_or_window"
            elif observed > _clock(
                _endpoints(decision, bucket)[0], "planned_fill_open"
            ):
                reason = "not_known_before_fill"
            else:
                raise AdmissionError("admission_eligible_member_omitted:" + event_id)
        if exclusions.get(event_id) != reason:
            raise AdmissionError("admission_exclusion_missing_or_wrong:" + event_id)
    admitted = rows.merge(
        pd.DataFrame(frozen), on="event_id", how="inner", suffixes=("", "_receipt")
    )
    if len(admitted) != len(frozen_ids):
        raise AdmissionError("admission_member_join_changed")
    verify_closed_prefix_anchors(external_census["anchors"], stage_receipt_resolver)
    verify_raw_stage_receipts(pd.DataFrame(projected), stage_receipt_resolver)
    # These are source/study identities, established before outcomes are read.
    sessions = admitted["source_stage_key"].str.extract(
        r"/(\d{4}-\d{2}-\d{2})\.jsonl$", expand=False
    )
    if (
        "session_date" in admitted
        and not admitted["session_date"].astype(str).eq(sessions).all()
    ):
        raise AdmissionError("admission_source_session_mismatch")
    if (
        "evaluation_spec_version" in admitted
        and not admitted["evaluation_spec_version"]
        .eq(study["evaluation_spec_version"])
        .all()
    ):
        raise AdmissionError("admission_source_evaluation_spec_mismatch")
    admitted["session_date"] = sessions
    admitted["evaluation_spec_version"] = study["evaluation_spec_version"]
    return admitted


def _exact_prefix(raw: bytes, count: int) -> bytes:
    """Bytes of the first ``count`` records. A later tail is not part of the seal."""
    lines = raw.splitlines(keepends=True)
    if count < 1 or len(lines) < count or not lines[count - 1].endswith(b"\n"):
        raise AdmissionError("admission_raw_stage_prefix_unreadable")
    return b"".join(lines[:count])


def verify_closed_prefix_anchors(
    anchors: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    resolver: Callable[[str], bytes] | None,
) -> None:
    """Hash each externally bound prefix. Do not hash the current file tail."""
    if resolver is None:
        raise AdmissionError("admission_raw_stage_resolver_unavailable")
    from lib.live_flow_event_stage import parse_stage_bytes

    seen: set[tuple[str, str]] = set()
    for anchor in anchors:
        key = _text(anchor.get("source_stage_key"))
        count_text = _count_text(anchor.get("prefix_records"))
        ident = (key, count_text)
        if ident in seen:
            continue
        seen.add(ident)
        match = re.fullmatch(r"live_flow/events/(\d{4}-\d{2}-\d{2})\.jsonl", key)
        if match is None:
            raise AdmissionError("admission_source_stage_identity_invalid")
        count = int(count_text)
        try:
            prefix = _exact_prefix(resolver(key), count)
            parsed = parse_stage_bytes(
                prefix,
                expected_session_date=match.group(1),
                source_stage_key=key,
            )
        except AdmissionError:
            raise
        except Exception as exc:
            raise AdmissionError(
                "admission_raw_stage_unavailable_or_invalid:" + key
            ) from exc
        digest = hashlib.sha256(prefix).hexdigest()
        if digest != _text(anchor.get("prefix_sha256")).lower():
            raise AdmissionError("admission_raw_stage_prefix_mismatch:" + key)
        if not any(
            str(item["source_stage_prefix_records"]) == count_text
            and item["source_stage_prefix_sha256"] == digest
            for item in parsed
        ):
            raise AdmissionError("admission_raw_stage_prefix_mismatch:" + key)


def verify_raw_stage_receipts(
    rows: pd.DataFrame, resolver: Callable[[str], bytes] | None
) -> None:
    """Reparse each row's recorded prefix, not whatever bytes were appended later.

    The resolver is deliberately injected by the owning source client.  A digest
    copied from a mutable ledger is evidence, not independent raw-byte proof.
    ``source_stage_observed_at`` is the collector's first-seen clock. Raw
    availability does not replace it.
    """
    if resolver is None:
        raise AdmissionError("admission_raw_stage_resolver_unavailable")
    if rows.empty:
        return
    from lib.live_flow_event_stage import parse_stage_bytes

    parsed: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in rows.itertuples(index=False):
        key = _text(row.source_stage_key)
        count_text = _count_text(row.source_stage_prefix_records)
        cache_key = (key, count_text)
        if cache_key in parsed:
            continue
        match = re.fullmatch(r"live_flow/events/(\d{4}-\d{2}-\d{2})\.jsonl", key)
        if match is None:
            raise AdmissionError("admission_source_stage_identity_invalid")
        try:
            prefix = _exact_prefix(resolver(key), int(count_text))
            parsed[cache_key] = {
                item["event"]["id"]: item
                for item in parse_stage_bytes(
                    prefix,
                    expected_session_date=match.group(1),
                    source_stage_key=key,
                )
            }
        except AdmissionError:
            raise
        except Exception as exc:
            raise AdmissionError(
                "admission_raw_stage_unavailable_or_invalid:" + key
            ) from exc
    for row in rows.itertuples(index=False):
        cache_key = (
            _text(row.source_stage_key),
            _count_text(row.source_stage_prefix_records),
        )
        raw = parsed[cache_key].get(_text(row.event_id))
        if raw is None:
            raise AdmissionError(
                "admission_raw_stage_event_missing:" + _text(row.event_id)
            )
        if _text(raw["event"].get("root")).upper() != _text(row.root).upper():
            raise AdmissionError(
                "admission_raw_stage_root_mismatch:" + _text(row.event_id)
            )
        expected = {
            "decision_at": raw["decision_at"],
            "available_at": raw["available_at"],
            "source_stage_key": raw["source_stage_key"],
            "source_stage_schema": raw["source_stage_schema"],
            "source_stage_prefix_records": str(raw["source_stage_prefix_records"]),
            "source_stage_prefix_sha256": raw["source_stage_prefix_sha256"],
        }
        actual = {
            key: (
                _count_text(getattr(row, key))
                if key == "source_stage_prefix_records"
                else _text(getattr(row, key))
            )
            for key in expected
        }
        if actual != expected:
            raise AdmissionError(
                "admission_raw_stage_receipt_mismatch:" + _text(row.event_id)
            )


def build_admission_receipt(
    *,
    study: Mapping[str, Any],
    study_spec: Mapping[str, Any],
    populations: Mapping[str, Any],
    exclusions: Mapping[str, str],
) -> dict[str, Any]:
    copied = dict(populations)
    if set(copied) != set(POPULATIONS) or not isinstance(
        study_spec.get("populations"), Mapping
    ):
        raise AdmissionError("admission_populations_missing")
    spec = {**dict(study_spec), "schema": SPEC_SCHEMA}
    return {
        "schema": SCHEMA,
        "study_spec": spec,
        "study": {**dict(study), "spec_digest": _digest(spec)},
        "populations": copied,
        "exclusions": dict(exclusions),
    }


def write_admission_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    """Explicit durable write to the incumbent artifact; no study is authorized here.

    Callers first validate against the complete source-only ledger and external
    study binding. The trainer repeats those checks on every read.
    """
    if path.name != "fs5_partition.json":
        raise AdmissionError("admission_artifact_path_invalid")
    payload = json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n"
    fd, name = tempfile.mkstemp(
        prefix=".fs5_partition-", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
