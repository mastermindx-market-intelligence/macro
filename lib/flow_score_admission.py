"""Outcome-blind FS-5 admission receipts; no grade, feature, or model access."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd
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
        for f in (*SOURCE_FIELDS, "source", "detector_version", "model_bucket")
        if f not in rows
    ]
    if missing:
        raise AdmissionError("admission_source_fields_missing:" + ",".join(missing))
    for f in ("source", "detector_version", "model_bucket"):
        if not rows[f].map(_text).eq(_text(study[f])).all():
            raise AdmissionError("admission_source_identity_mismatch:" + f)
    if not rows.event_id.map(
        lambda value: isinstance(value, str) and bool(value) and value == value.strip()
    ).all():
        raise AdmissionError("admission_source_event_id_invalid")
    if rows.event_id.map(_text).duplicated().any():
        raise AdmissionError("admission_source_duplicate_event_id")
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
    verify_raw_stage_receipts(admitted, stage_receipt_resolver)
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


def verify_raw_stage_receipts(
    rows: pd.DataFrame, resolver: Callable[[str], bytes] | None
) -> None:
    """Reparse the authoritative raw R2 stage bytes for every frozen receipt.

    The resolver is deliberately injected by the owning source client.  A digest
    copied from a mutable ledger is evidence, not independent raw-byte proof.
    """
    if resolver is None:
        raise AdmissionError("admission_raw_stage_resolver_unavailable")
    from lib.live_flow_event_stage import parse_stage_bytes

    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    for key in rows["source_stage_key"].map(_text).unique():
        match = re.fullmatch(r"live_flow/events/(\d{4}-\d{2}-\d{2})\.jsonl", key)
        if match is None:
            raise AdmissionError("admission_source_stage_identity_invalid")
        try:
            parsed[key] = {
                item["event"]["id"]: item
                for item in parse_stage_bytes(
                    resolver(key),
                    expected_session_date=match.group(1),
                    source_stage_key=key,
                )
            }
        except Exception as exc:
            raise AdmissionError(
                "admission_raw_stage_unavailable_or_invalid:" + key
            ) from exc
    for row in rows.itertuples(index=False):
        raw = parsed[_text(row.source_stage_key)].get(_text(row.event_id))
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
