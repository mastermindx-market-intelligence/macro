"""Read-only decoder for the capital-structure event_versions parquet.

Contract and identity checks for a stored generation live here so the
valuation producer does not reimplement parquet decoding. The compiler
script imports `_load_existing_events` back; this module does not import
the compiler or any collector.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from engine.capital_structure.event_spine import compute_event_id
from engine.capital_structure.spine_paths import event_versions_path

EVENT_COLUMNS = [
    "event_id", "logical_event_id", "accession", "cik", "ticker", "form",
    "filing_date", "accepted_at", "available_at", "classification_state",
    "correction_version", "event_json",
]

_EVENT_CONTRACT_NAME = "capital_structure_event.schema.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _native(value: Any) -> Any:
    """Convert pandas/Arrow nested values to stable Python containers."""
    import pandas as pd

    if isinstance(value, Mapping):
        return {str(key): _native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_native(item) for item in value]
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return _native(value.tolist())
        except Exception:  # noqa: BLE001
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            pass
    return value


def _normalize_cell(value: Any) -> Any:
    native = _native(value)
    return None if native is None else native


def _event_contract() -> dict[str, Any]:
    return json.loads(
        (_repo_root() / "contracts" / _EVENT_CONTRACT_NAME).read_text(encoding="utf-8")
    )


def _contract_errors(record: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in validator.iter_errors(record)
    ]


def _validate_contract(
    record: Mapping[str, Any], schema: Mapping[str, Any], *, label: str
) -> None:
    errors = _contract_errors(record, schema)
    if errors:
        raise ValueError(f"{label} contract violation: {'; '.join(errors[:5])}")


def _validate_event_identity(event: Mapping[str, Any], *, label: str) -> None:
    event_id = str(event.get("event_id") or "")
    expected = compute_event_id(event)
    if event_id != expected:
        raise ValueError(
            f"{label} event_id digest mismatch: {event_id!r} != {expected!r}"
        )


def _validate_event_history(events: Sequence[Mapping[str, Any]]) -> None:
    import pandas as pd

    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        source = event.get("source") or {}
        filing = event.get("filing") or {}
        grouped[(
            str(source.get("source_system") or ""),
            str(filing.get("accession") or source.get("source_id") or ""),
        )].append(event)
    for logical_key, versions in grouped.items():
        by_version: dict[int, Mapping[str, Any]] = {}
        for event in versions:
            number = int((event.get("version") or {}).get("correction_version") or 0)
            if number in by_version:
                raise ValueError(
                    f"logical event {logical_key} has duplicate correction_version {number}"
                )
            by_version[number] = event
        expected = list(range(1, len(by_version) + 1))
        if sorted(by_version) != expected:
            raise ValueError(
                f"logical event {logical_key} has non-contiguous correction history"
            )
        for number in expected:
            event = by_version[number]
            correction_of = (event.get("version") or {}).get("correction_of")
            if number == 1 and correction_of is not None:
                raise ValueError(f"logical event {logical_key} v1 cannot be a correction")
            if number > 1:
                prior_id = str(by_version[number - 1].get("event_id") or "")
                if str(correction_of or "") != prior_id:
                    raise ValueError(
                        f"logical event {logical_key} v{number} must correct {prior_id}"
                    )
                prior_time = pd.Timestamp(
                    (by_version[number - 1].get("point_in_time") or {}).get("available_at")
                )
                current_time = pd.Timestamp(
                    (event.get("point_in_time") or {}).get("available_at")
                )
                if current_time <= prior_time:
                    raise ValueError(
                        f"logical event {logical_key} v{number} must be produced after v{number - 1}"
                    )


def _load_existing_events(
    frame: Any,
    event_schema: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Decode and identity-check rows of event_versions.parquet.

    `frame` is a pandas DataFrame or None. The compiler script imports this
    symbol back so load-time contract checks stay in one place.
    """
    if frame is None:
        return []
    if frame.columns.tolist() != EVENT_COLUMNS:
        raise ValueError(
            "event ledger columns must exactly equal "
            f"{EVENT_COLUMNS}; got {frame.columns.tolist()}"
        )
    if frame.empty:
        return []
    schema = event_schema or _event_contract()
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in frame.iterrows():
        value = row["event_json"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"event ledger row {index} has null/non-string event_json")
        try:
            event = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"event ledger row {index} has malformed event_json"
            ) from exc
        if not isinstance(event, Mapping):
            raise ValueError(f"event ledger row {index} event_json must be an object")
        _validate_contract(event, schema, label=f"event ledger row {index}")
        _validate_event_identity(event, label=f"event ledger row {index}")
        event_id = str(event.get("event_id") or "")
        if event_id in seen:
            raise ValueError(f"event ledger contains duplicate event_id {event_id}")
        seen.add(event_id)
        filing = event.get("filing") or {}
        issuer = event.get("issuer") or {}
        point_in_time = event.get("point_in_time") or {}
        version = event.get("version") or {}
        classification = event.get("classification") or {}
        expected = {
            "event_id": event_id,
            "logical_event_id": f"sec:{filing.get('accession')}",
            "accession": filing.get("accession"),
            "cik": issuer.get("cik"),
            "ticker": issuer.get("ticker"),
            "form": filing.get("form"),
            "filing_date": filing.get("filing_date"),
            "accepted_at": filing.get("accepted_at"),
            "available_at": point_in_time.get("available_at"),
            "classification_state": classification.get("state"),
            "correction_version": int(version.get("correction_version")),
        }
        for column, expected_value in expected.items():
            actual = _normalize_cell(row[column])
            if column == "correction_version" and actual is not None:
                actual = int(actual)
            if actual != expected_value:
                raise ValueError(
                    f"event ledger row {index} denormalized {column} mismatch: "
                    f"{actual!r} != {expected_value!r}"
                )
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        if value != canonical:
            raise ValueError(f"event ledger row {index} event_json is not canonical")
        events.append(dict(event))
    _validate_event_history(events)
    return events


def iter_classified_spine_events(ticker: str) -> list[dict[str, Any]]:
    """Return classified parquet events for ticker from the resolved spine."""
    import pandas as pd

    path = event_versions_path()
    if not path.exists():
        return []
    wanted = ticker.strip().upper()
    frame = pd.read_parquet(path)
    issuer_rows = frame.loc[frame["ticker"].fillna("").str.upper() == wanted]
    classified: list[dict[str, Any]] = []
    for event in _load_existing_events(issuer_rows):
        if (event.get("classification") or {}).get("state") != "classified":
            continue
        classified.append(event)
    return classified


def spine_ticker_row_count(ticker: str) -> int:
    """Count parquet rows for ticker at the resolved spine path (proves a read)."""
    import pandas as pd

    path = event_versions_path()
    if not path.exists():
        return 0
    frame = pd.read_parquet(path)
    wanted = ticker.strip().upper()
    return int((frame["ticker"].fillna("").str.upper() == wanted).sum())


__all__ = [
    "EVENT_COLUMNS",
    "_load_existing_events",
    "event_versions_path",
    "iter_classified_spine_events",
    "spine_ticker_row_count",
]
