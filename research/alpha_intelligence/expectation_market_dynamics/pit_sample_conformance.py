"""Research-only conformance harness for institutional PIT expectation samples.

This module implements the deterministic, vendor-neutral *diagnostic* checks
specified by Commission 2.  It is not a source adapter, rights authority,
identity owner, evaluation admission gate, product consumer, or warehouse.

No vendor data is fetched.  A caller supplies an explicit JSON sample.  The
harness preserves unknowns rather than converting missing clocks, rights,
corporate-action lineage, or contributor identity into evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CONTRACT = "commission2.pit_expectation_sample_conformance/v1"
REQUIRED_FIELDS = (
    "observation_id",
    "provider_record_id",
    "provider",
    "issuer_ref",
    "security_ref",
    "provider_company_id",
    "metric_native",
    "metric_canonical",
    "fiscal_period_end",
    "periodicity",
    "fiscal_year",
    "horizon_label_raw",
    "contributor_id",
    "broker_id",
    "analyst_id",
    "value",
    "currency",
    "unit",
    "scale",
    "basis",
    "normalization_class",
    "source_published_at",
    "vendor_received_at",
    "vendor_activated_at",
    "provider_snapshot_at",
    "mastermind_observed_at",
    "known_at",
    "ingested_at",
    "effective_from",
    "effective_to",
    "correction_generation",
    "supersedes_observation_id",
    "withdrawal_state",
    "rights_class",
    "source_receipt",
)
NULLABLE_FIELDS = frozenset(
    {
        "contributor_id",
        "broker_id",
        "analyst_id",
        "value",
        "source_published_at",
        "vendor_received_at",
        "vendor_activated_at",
        "provider_snapshot_at",
        "effective_to",
        "supersedes_observation_id",
    }
)
CLOCK_FIELDS = (
    "source_published_at",
    "vendor_received_at",
    "vendor_activated_at",
    "provider_snapshot_at",
    "mastermind_observed_at",
    "known_at",
    "ingested_at",
    "effective_from",
    "effective_to",
)
IMMUTABLE_GRAIN = (
    "provider",
    "issuer_ref",
    "security_ref",
    "provider_company_id",
    "metric_native",
    "metric_canonical",
    "fiscal_period_end",
    "periodicity",
    "currency",
    "unit",
    "scale",
    "basis",
    "normalization_class",
    "contributor_id",
    "broker_id",
    "analyst_id",
)
WITHDRAWAL_STATES = frozenset({"active", "withdrawn", "deleted", "stale", "unknown"})
MISSING = object()


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    row: int | None
    observation_id: str | None
    detail: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _parse_cutoff(value: str) -> datetime:
    parsed = _parse_time(value)
    if parsed is None:
        raise ValueError("cutoff must be an offset-aware ISO-8601 timestamp")
    return parsed


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _row_id(row: Mapping[str, Any]) -> str | None:
    value = row.get("observation_id")
    return value if _nonempty_string(value) else None


def _finding(
    code: str,
    detail: str,
    *,
    row_index: int | None = None,
    row: Mapping[str, Any] | None = None,
    severity: str = "FAIL",
) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        row=row_index,
        observation_id=_row_id(row or {}),
        detail=detail,
    )


def _validate_shape(rows: Sequence[Mapping[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    seen_ids: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            findings.append(_finding("ROW_NOT_OBJECT", "observation must be a JSON object", row_index=idx))
            continue

        for field in REQUIRED_FIELDS:
            if field not in row:
                findings.append(
                    _finding(
                        "REQUIRED_FIELD_ABSENT",
                        f"required field {field!r} is absent; unknown must be explicit",
                        row_index=idx,
                        row=row,
                    )
                )
                continue
            if row[field] is None and field not in NULLABLE_FIELDS:
                findings.append(
                    _finding(
                        "REQUIRED_FIELD_NULL",
                        f"required field {field!r} may not be null",
                        row_index=idx,
                        row=row,
                    )
                )

        oid = _row_id(row)
        if oid is not None:
            if oid in seen_ids:
                findings.append(
                    _finding(
                        "DUPLICATE_OBSERVATION_ID",
                        f"observation_id {oid!r} is duplicated",
                        row_index=idx,
                        row=row,
                    )
                )
            seen_ids.add(oid)

        for field in (
            "provider_record_id",
            "provider",
            "issuer_ref",
            "security_ref",
            "provider_company_id",
            "metric_native",
            "metric_canonical",
            "fiscal_period_end",
            "periodicity",
            "currency",
            "unit",
            "basis",
            "normalization_class",
            "rights_class",
        ):
            if field in row and row[field] is not None and not _nonempty_string(row[field]):
                findings.append(
                    _finding(
                        "INVALID_STRING_FIELD",
                        f"{field!r} must be a non-empty string when present",
                        row_index=idx,
                        row=row,
                    )
                )

        period_end = row.get("fiscal_period_end")
        if period_end is not None:
            try:
                date.fromisoformat(str(period_end))
            except ValueError:
                findings.append(
                    _finding(
                        "INVALID_FISCAL_PERIOD_END",
                        "fiscal_period_end must be an ISO calendar date",
                        row_index=idx,
                        row=row,
                    )
                )

        fiscal_year = row.get("fiscal_year", MISSING)
        if (
            fiscal_year is not MISSING
            and (
                isinstance(fiscal_year, bool)
                or not isinstance(fiscal_year, int)
                or fiscal_year < 1900
                or fiscal_year > 2200
            )
        ):
            findings.append(
                _finding(
                    "INVALID_FISCAL_YEAR",
                    "fiscal_year must be an integer calendar/fiscal label",
                    row_index=idx,
                    row=row,
                )
            )

        scale = row.get("scale", MISSING)
        if scale is not MISSING:
            valid_scale = (
                _nonempty_string(scale)
                or _finite_number(scale)
            )
            if not valid_scale:
                findings.append(
                    _finding(
                        "INVALID_SCALE",
                        "scale must be a finite number or non-empty provider-native label",
                        row_index=idx,
                        row=row,
                    )
                )

        source_receipt = row.get("source_receipt", MISSING)
        if source_receipt is not MISSING and not (
            _nonempty_string(source_receipt)
            or (isinstance(source_receipt, Mapping) and bool(source_receipt))
        ):
            findings.append(
                _finding(
                    "INVALID_SOURCE_RECEIPT",
                    "source_receipt must be a non-empty opaque reference or object",
                    row_index=idx,
                    row=row,
                )
            )

        generation = row.get("correction_generation", MISSING)
        if (
            generation is not MISSING
            and (
                isinstance(generation, bool)
                or not isinstance(generation, int)
                or generation < 0
            )
        ):
            findings.append(
                _finding(
                    "INVALID_CORRECTION_GENERATION",
                    "correction_generation must be a non-negative integer",
                    row_index=idx,
                    row=row,
                )
            )

        value = row.get("value", MISSING)
        if value is not MISSING and value is not None and not _finite_number(value):
            findings.append(
                _finding(
                    "INVALID_VALUE",
                    "value must be finite numeric or explicit null",
                    row_index=idx,
                    row=row,
                )
            )

        state = row.get("withdrawal_state")
        if state is not None and state not in WITHDRAWAL_STATES:
            findings.append(
                _finding(
                    "INVALID_WITHDRAWAL_STATE",
                    f"withdrawal_state {state!r} is outside the diagnostic vocabulary",
                    row_index=idx,
                    row=row,
                )
            )

        for field in CLOCK_FIELDS:
            if field not in row or row[field] is None:
                continue
            if _parse_time(row[field]) is None:
                findings.append(
                    _finding(
                        "INVALID_CLOCK",
                        f"{field!r} must be offset-aware ISO-8601 or explicit null",
                        row_index=idx,
                        row=row,
                    )
                )

        known = _parse_time(row.get("known_at"))
        observed = _parse_time(row.get("mastermind_observed_at"))
        ingested = _parse_time(row.get("ingested_at"))
        effective = _parse_time(row.get("effective_from"))
        end = _parse_time(row.get("effective_to"))
        if known is not None and ingested is not None and known > ingested:
            findings.append(
                _finding(
                    "KNOWN_AFTER_INGESTED",
                    "known_at may not be later than ingested_at",
                    row_index=idx,
                    row=row,
                )
            )
        if observed is not None and known is not None and observed > known:
            findings.append(
                _finding(
                    "OBSERVED_AFTER_KNOWN",
                    "mastermind_observed_at may not be later than known_at",
                    row_index=idx,
                    row=row,
                )
            )
        if known is not None:
            for field in (
                "source_published_at",
                "vendor_received_at",
                "vendor_activated_at",
                "provider_snapshot_at",
            ):
                other = _parse_time(row.get(field))
                if other is not None and other > known:
                    findings.append(
                        _finding(
                            "SOURCE_CLOCK_AFTER_KNOWN",
                            f"{field} may not be later than known_at",
                            row_index=idx,
                            row=row,
                        )
                    )
        if effective is not None and end is not None and end <= effective:
            findings.append(
                _finding(
                    "INVALID_EFFECTIVE_INTERVAL",
                    "effective_to must be strictly later than effective_from",
                    row_index=idx,
                    row=row,
                )
            )
    return findings


def _validate_corrections(rows: Sequence[Mapping[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    by_id = {_row_id(row): row for row in rows if _row_id(row) is not None}
    children: dict[str, list[str]] = {}
    for row in rows:
        parent_id = row.get("supersedes_observation_id")
        oid = _row_id(row)
        if _nonempty_string(parent_id) and oid is not None:
            children.setdefault(parent_id, []).append(oid)
    for parent_id, child_ids in sorted(children.items()):
        if len(child_ids) > 1:
            parent = by_id.get(parent_id, {})
            findings.append(
                _finding(
                    "SUPERSESSION_FORK",
                    f"one observation is superseded by multiple children: {sorted(child_ids)}",
                    row=parent,
                )
            )

    for idx, row in enumerate(rows):
        parent_id = row.get("supersedes_observation_id")
        generation = row.get("correction_generation")
        if parent_id is None:
            if generation not in (0, None):
                findings.append(
                    _finding(
                        "ORPHAN_CORRECTION_GENERATION",
                        "nonzero correction_generation requires supersedes_observation_id",
                        row_index=idx,
                        row=row,
                    )
                )
            continue
        if not _nonempty_string(parent_id) or parent_id not in by_id:
            findings.append(
                _finding(
                    "SUPERSESSION_TARGET_MISSING",
                    "supersedes_observation_id must bind another observation in the sample",
                    row_index=idx,
                    row=row,
                )
            )
            continue

        if parent_id == _row_id(row):
            findings.append(
                _finding(
                    "SUPERSESSION_CYCLE",
                    "an observation may not supersede itself",
                    row_index=idx,
                    row=row,
                )
            )
            continue

        # Follow the finite in-sample chain to detect longer cycles.
        seen = {_row_id(row)}
        cursor = parent_id
        while _nonempty_string(cursor) and cursor in by_id:
            if cursor in seen:
                findings.append(
                    _finding(
                        "SUPERSESSION_CYCLE",
                        "correction lineage contains a cycle",
                        row_index=idx,
                        row=row,
                    )
                )
                break
            seen.add(cursor)
            cursor = by_id[cursor].get("supersedes_observation_id")

        parent = by_id[parent_id]
        parent_generation = parent.get("correction_generation")
        if not isinstance(generation, int) or not isinstance(parent_generation, int) or generation != parent_generation + 1:
            findings.append(
                _finding(
                    "CORRECTION_GENERATION_GAP",
                    "correction generation must increment exactly by one",
                    row_index=idx,
                    row=row,
                )
            )

        for field in IMMUTABLE_GRAIN:
            if row.get(field) != parent.get(field):
                findings.append(
                    _finding(
                        "CORRECTION_GRAIN_CHANGED",
                        f"correction changed immutable grain field {field!r}",
                        row_index=idx,
                        row=row,
                    )
                )

        child_known = _parse_time(row.get("known_at"))
        parent_known = _parse_time(parent.get("known_at"))
        if child_known is not None and parent_known is not None and child_known <= parent_known:
            findings.append(
                _finding(
                    "CORRECTION_NOT_LATER",
                    "a correction must become known strictly after its predecessor",
                    row_index=idx,
                    row=row,
                )
            )
    return findings


def replay_as_of(rows: Sequence[Mapping[str, Any]], cutoff: datetime) -> list[dict[str, Any]]:
    """Return only rows knowable at *cutoff*, preserving correction history.

    This does not collapse corrections into today's latest value.  It returns the
    latest knowable generation per immutable observation chain at the cutoff.
    """
    visible = [
        dict(row)
        for row in rows
        if (known := _parse_time(row.get("known_at"))) is not None and known <= cutoff
    ]
    by_id = {_row_id(row): row for row in visible if _row_id(row) is not None}
    superseded = {
        row.get("supersedes_observation_id")
        for row in visible
        if _nonempty_string(row.get("supersedes_observation_id"))
        and row.get("supersedes_observation_id") in by_id
    }
    survivors = [row for row in visible if _row_id(row) not in superseded]
    return sorted(
        survivors,
        key=lambda row: (
            str(row.get("provider")),
            str(row.get("security_ref")),
            str(row.get("metric_canonical")),
            str(row.get("fiscal_period_end")),
            str(row.get("contributor_id")),
            str(row.get("observation_id")),
        ),
    )


def classify_transition(previous: Mapping[str, Any], current: Mapping[str, Any]) -> str:
    """Classify a pair without calling fiscal roll or composition change a revision."""
    if any(previous.get(k) != current.get(k) for k in ("provider", "issuer_ref", "security_ref", "metric_canonical")):
        return "INCOMPARABLE"
    if previous.get("fiscal_period_end") != current.get("fiscal_period_end"):
        return "FISCAL_ROLL"
    if any(previous.get(k) != current.get(k) for k in ("basis", "currency", "unit", "scale", "normalization_class")):
        return "BASIS_CHANGE"
    if current.get("withdrawal_state") in {"withdrawn", "deleted", "stale"}:
        return "WITHDRAWAL_OR_STALENESS"
    if previous.get("value") != current.get("value"):
        return "VALUE_REVISION"
    if any(previous.get(k) != current.get(k) for k in ("contributor_id", "broker_id", "analyst_id")):
        return "COMPOSITION_ONLY"
    return "UNCHANGED"


def _invariant_status(
    rows: Sequence[Mapping[str, Any]],
    cutoff: datetime,
    findings: Sequence[Finding],
) -> dict[str, dict[str, Any]]:
    codes = {f.code for f in findings}
    hidden_future = sum(
        1
        for row in rows
        if (known := _parse_time(row.get("known_at"))) is not None and known > cutoff
    )
    explicit_null_clocks = sum(
        1
        for row in rows
        for field in ("source_published_at", "vendor_received_at", "vendor_activated_at", "provider_snapshot_at")
        if field in row and row[field] is None
    )
    rights_classes = sorted({str(row.get("rights_class")) for row in rows if row.get("rights_class") is not None})
    corporate_receipts = 0
    for row in rows:
        receipt = row.get("source_receipt")
        if isinstance(receipt, Mapping) and receipt.get("corporate_action_lineage"):
            corporate_receipts += 1

    return {
        "T1_KNOWLEDGE_CUTOFF": {
            "status": "FAIL"
            if any(_parse_time(row.get("known_at")) is None for row in rows)
            or {"INVALID_CLOCK", "KNOWN_AFTER_INGESTED", "OBSERVED_AFTER_KNOWN", "SOURCE_CLOCK_AFTER_KNOWN"} & codes
            else "PASS",
            "hidden_future_rows": hidden_future,
            "rule": "replay consumes only rows with known_at <= cutoff",
        },
        "T2_NO_RETROACTIVE_CORRECTION": {
            "status": "FAIL"
            if {
                "SUPERSESSION_TARGET_MISSING",
                "CORRECTION_GENERATION_GAP",
                "CORRECTION_GRAIN_CHANGED",
                "CORRECTION_NOT_LATER",
            }
            & codes
            else "PASS",
            "rule": "later correction never rewrites what an earlier replay could see",
        },
        "T3_NO_TIMESTAMP_INVENTION": {
            "status": "PARTIAL",
            "explicit_null_clock_fields": explicit_null_clocks,
            "rule": "unavailable clocks stay explicit null; external source semantics remain owner evidence",
        },
        "T4_FISCAL_IDENTITY": {
            "status": "PASS",
            "rule": "fiscal_period_end is part of immutable comparison identity",
        },
        "T5_COMPOSITION_DECOMPOSITION": {
            "status": "PASS",
            "rule": "contributor-only changes classify separately from value revisions",
        },
        "T6_RIGHTS": {
            "status": "PARTIAL",
            "rights_classes_observed": rights_classes,
            "rule": "row metadata never grants rights; a separate source-rights owner must qualify use",
        },
        "T7_INTRADAY_HONESTY": {
            "status": "UNKNOWN",
            "rule": "timestamp granularity/market availability must come from vendor sample documentation",
        },
        "T8_RECEIPT_SEPARATION": {
            "status": "FAIL"
            if any(field not in row for row in rows for field in CLOCK_FIELDS)
            else "PASS",
            "rule": "source/vendor/provider/Mastermind/known/ingested clocks remain separate fields",
        },
        "T9_CORPORATE_ACTION_LINEAGE": {
            "status": "PASS" if rows and corporate_receipts == len(rows) else "UNKNOWN",
            "rows_with_explicit_lineage": corporate_receipts,
            "rows_total": len(rows),
            "rule": "per-share history requires owner evidence; absence remains unknown",
        },
        "T10_REPRODUCIBILITY": {
            "status": "PASS",
            "rule": "receipt and replay are canonicalized deterministically from explicit input",
        },
    }


def validate_sample(
    rows: Sequence[Mapping[str, Any]],
    *,
    cutoff: datetime,
) -> dict[str, Any]:
    """Validate an explicit sample and return a deterministic diagnostic receipt."""
    shape = _validate_shape(rows)
    correction = _validate_corrections(rows)
    findings = shape + correction
    replay = replay_as_of(rows, cutoff)
    fail_count = sum(f.severity == "FAIL" for f in findings)
    receipt = {
        "schema": CONTRACT,
        "authority": {
            "class": "research_diagnostic_only",
            "canonical_source_owner_changed": False,
            "rights_granted": False,
            "model_use_granted": False,
            "redistribution_granted": False,
            "financial_influence": False,
        },
        "cutoff": cutoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input": {
            "row_count": len(rows),
            "canonical_sha256": _digest(list(rows)),
        },
        "replay": {
            "visible_survivor_count": len(replay),
            "visible_observation_ids": [row.get("observation_id") for row in replay],
            "canonical_sha256": _digest(replay),
        },
        "invariants": _invariant_status(rows, cutoff, findings),
        "findings": [asdict(f) for f in findings],
        "summary": {
            "fail_count": fail_count,
            "finding_count": len(findings),
            "structural_pass": fail_count == 0,
            "rights_ready": False,
            "production_ready": False,
        },
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def _load_rows(path: Path) -> list[Mapping[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("observations"), list):
        rows = payload["observations"]
    else:
        raise ValueError("input must be a JSON list or an object with an observations list")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("every observation must be a JSON object")
    return list(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path, help="explicit local JSON sample; no provider fetch occurs")
    parser.add_argument("--cutoff", required=True, help="offset-aware ISO-8601 replay cutoff")
    parser.add_argument("--output", type=Path, help="optional receipt path")
    args = parser.parse_args(argv)

    rows = _load_rows(args.sample)
    receipt = validate_sample(rows, cutoff=_parse_cutoff(args.cutoff))
    rendered = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if receipt["summary"]["structural_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
