"""AxisCell v1 — a display-only classification reading.

Readers in later lanes build cells through :func:`available` and
:func:`missing`. This module writes nothing, calls nothing on the network,
and does not resolve rights. ``finviz_themes``, ``ths_concepts`` and
``ltheme:*`` are internal-only and are never subjects.

The forbidden-key walk and the point-in-time check live here, in
:func:`validate_cell`. The JSON Schema does not express them.
"""
from __future__ import annotations

import datetime
import json
import re

from engine.theme_graph.identity import (
    COMPANY_ID_RE,
    NON_BASKET_SUITES,
    basket_node_id,
    etf_node_id,
)

SCHEMA_VERSION = "axis_cell.v1"

AXES = (
    "sic_industry",
    "geography",
    "macro_sensitivity",
    "business_model",
    "lifecycle",
    "value_chain",
)

STATUSES = (
    "available",
    "unknown",
    "unavailable",
    "stale",
    "not_applicable",
    "rights_blocked",
)

REASON_CODES = {
    "available": (),
    "unknown": ("value_missing", "history_not_supported"),
    "unavailable": ("owner_missing", "owner_unavailable", "owner_degraded"),
    "stale": ("owner_stale",),
    "not_applicable": ("not_applicable", "retired_entity", "superseded_entity"),
    "rights_blocked": ("rights_blocked",),
}

LABELS = frozenset({
    "proxy_not_micro_membership",
    "NO_MAPPING",
    "source_local",
    "house_curated",
    "read_time_composition",
})

FORBIDDEN_VALUE_KEY_WORDS = ("weight", "share", "score", "rank", "exposure_pct")

# House theme-subject grammar. Mirrors scripts/check_theme_graph_contracts.py
# THEME_NODE_ID_RE (scripts/ is not importable from engine/).
THEME_SUBJECT_RE = re.compile(r"^theme:[a-z0-9][a-z0-9_]{1,62}$")

_CELL_KEYS = (
    "schema_version",
    "axis",
    "subject_id",
    "status",
    "reason_code",
    "value",
    "unit",
    "observed_at",
    "effective_at",
    "as_of",
    "freshness",
    "quality",
    "labels",
    "source",
    "provenance",
    "rights_context",
)
_CELL_KEY_SET = set(_CELL_KEYS)
_AS_OF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TEMPORAL_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ].*)?$")
_INTERNAL_SUITE_TOKENS = ("finviz_themes", "ths_concepts")
_SOURCE_KEYS = ("owner", "artifact", "field")
_RIGHTS_KEYS = ("license_class", "basis")
_FRESHNESS_KEYS = ("age_days", "max_age_days")


class AxisCellError(ValueError):
    """A subject id or an AxisCell failed the v1 contract."""

    def __init__(self, message: str, *, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems: list[str] = [message] if problems is None else list(problems)


def _fail(message: str) -> AxisCellError:
    return AxisCellError(message, problems=[message])


def parse_subject(subject_id: str) -> tuple[str, str]:
    """Return ``(kind, rest)`` for a house subject id.

    ``rest`` is everything after the first colon. ``ltheme:*`` and every
    other prefix raise :class:`AxisCellError`.
    """
    if not isinstance(subject_id, str) or not subject_id:
        raise _fail(f"subject_id must be a non-empty string, got {subject_id!r}")
    if subject_id.startswith("ltheme:"):
        raise _fail("ltheme ids are vendor-local and are never AxisCell subjects")
    if subject_id.startswith("co:"):
        if COMPANY_ID_RE.fullmatch(subject_id):
            return "co", subject_id.split(":", 1)[1]
        raise _fail(f"subject_id {subject_id!r} is not a company id")
    if subject_id.startswith("theme:"):
        if THEME_SUBJECT_RE.fullmatch(subject_id):
            return "theme", subject_id.split(":", 1)[1]
        raise _fail(f"subject_id {subject_id!r} is not a house theme id")
    if subject_id.startswith("basket:"):
        return _parse_basket(subject_id)
    if subject_id.startswith("etf:"):
        return _parse_etf(subject_id)
    raise _fail(f"subject_id {subject_id!r} is not a co, theme, basket, or etf id")


def _parse_basket(subject_id: str) -> tuple[str, str]:
    parts = subject_id.split(":", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise _fail(f"subject_id {subject_id!r} is not a basket id")
    suite, basket_id = parts[1], parts[2]
    if suite in NON_BASKET_SUITES or any(token in suite for token in _INTERNAL_SUITE_TOKENS):
        raise _fail(f"suite {suite!r} is internal-only and cannot be an AxisCell subject")
    try:
        minted = basket_node_id(suite, basket_id)
    except ValueError as exc:
        raise _fail(f"subject_id {subject_id!r} is not a basket id: {exc}") from exc
    if minted != subject_id:
        raise _fail(f"subject_id {subject_id!r} does not round-trip through basket_node_id")
    return "basket", f"{suite}:{basket_id}"


def _parse_etf(subject_id: str) -> tuple[str, str]:
    symbol = subject_id.split(":", 1)[1]
    try:
        minted = etf_node_id(symbol)
    except ValueError as exc:
        raise _fail(f"subject_id {subject_id!r} is not an etf id: {exc}") from exc
    if minted != subject_id:
        raise _fail(f"subject_id {subject_id!r} does not round-trip through etf_node_id")
    return "etf", symbol


def company_parts(subject_id: str) -> tuple[str, str, int | None]:
    """Return ``(market, symbol, epoch_or_None)`` for a ``co:`` subject."""
    kind, rest = parse_subject(subject_id)
    if kind != "co":
        raise _fail(f"subject_id {subject_id!r} is not a company id")
    market, sym_part = rest.split(":", 1)
    if "#" in sym_part:
        symbol, epoch_s = sym_part.rsplit("#", 1)
        return market, symbol, int(epoch_s)
    return market, sym_part, None


def _calendar(text: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _reject_forbidden_keys(value: object, problems: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                lowered = key.lower()
                for word in FORBIDDEN_VALUE_KEY_WORDS:
                    if word in lowered:
                        problems.append(
                            f"value key {key!r} contains forbidden word {word!r}"
                        )
                        break
            _reject_forbidden_keys(child, problems)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_forbidden_keys(child, problems)


def _read_temporal(name: str, value: object, problems: list[str]) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, str):
        match = _TEMPORAL_RE.fullmatch(value)
        if match is not None:
            parsed = _calendar(match.group(1))
            if parsed is not None:
                return parsed
    problems.append(f"{name} must be null or an ISO date/datetime, got {value!r}")
    return None


def _check_freshness(freshness: object, problems: list[str]) -> None:
    if freshness is None:
        return
    if not isinstance(freshness, dict) or set(freshness) != set(_FRESHNESS_KEYS):
        problems.append(
            "freshness must be null or an object with age_days and max_age_days"
        )
        return
    age = freshness["age_days"]
    maximum = freshness["max_age_days"]
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        problems.append("freshness.age_days must be an int >= 0")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        problems.append("freshness.max_age_days must be an int >= 1")


def _check_labels(labels: object, problems: list[str]) -> None:
    if not isinstance(labels, list):
        problems.append(f"labels must be a list, got {type(labels).__name__}")
        return
    for item in labels:
        if not isinstance(item, str) or item not in LABELS:
            problems.append(f"label {item!r} is not allowed")
    try:
        if list(labels) != sorted(labels):
            problems.append("labels must be sorted")
    except TypeError:
        problems.append("labels must be sorted")
    try:
        if len(labels) != len(set(labels)):
            problems.append("labels must be unique")
    except TypeError:
        problems.append("labels must be unique")


def _check_source(source: object, problems: list[str]) -> None:
    if not isinstance(source, dict) or set(source) != set(_SOURCE_KEYS):
        problems.append("source must be an object with owner, artifact, and field")
        return
    owner = source["owner"]
    artifact = source["artifact"]
    field = source["field"]
    if not isinstance(owner, str) or owner == "":
        problems.append("source.owner must be a non-empty string")
    if not isinstance(artifact, str) or artifact == "":
        problems.append("source.artifact must be a non-empty string")
    if field is not None and not isinstance(field, str):
        problems.append("source.field must be a string or null")


def _check_rights(rights: object, problems: list[str]) -> None:
    if rights is None:
        return
    if not isinstance(rights, dict) or set(rights) != set(_RIGHTS_KEYS):
        problems.append(
            "rights_context must be null or an object with license_class and basis"
        )
        return
    license_class = rights["license_class"]
    basis = rights["basis"]
    if not isinstance(license_class, str) or license_class == "":
        problems.append("rights_context.license_class must be a non-empty string")
    if not isinstance(basis, str) or basis == "":
        problems.append("rights_context.basis must be a non-empty string")


def _validate_cell(cell: object) -> list[str]:
    if not isinstance(cell, dict):
        return [f"cell must be a dict, got {type(cell).__name__}"]

    problems: list[str] = []
    missing = [key for key in _CELL_KEYS if key not in cell]
    extra = sorted(str(key) for key in cell if key not in _CELL_KEY_SET)
    if missing:
        problems.append("missing keys: " + ", ".join(missing))
    if extra:
        problems.append("extra keys: " + ", ".join(extra))

    if "schema_version" in cell and cell["schema_version"] != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if "axis" in cell and cell["axis"] not in AXES:
        problems.append(f"axis {cell['axis']!r} is not one of the classification axes")
    if "subject_id" in cell:
        try:
            parse_subject(cell["subject_id"])
        except AxisCellError as exc:
            detail = exc.problems[0] if exc.problems else str(exc)
            problems.append(f"subject_id: {detail}")

    status = cell.get("status", None)
    if "status" in cell and status not in STATUSES:
        problems.append(f"status {status!r} is not one of the classification statuses")
    if "reason_code" in cell and "status" in cell:
        reason = cell["reason_code"]
        if status not in REASON_CODES:
            problems.append(f"reason_code {reason!r} is not allowed for status {status!r}")
        elif status == "available":
            if reason is not None:
                problems.append(
                    f"reason_code {reason!r} is not allowed for status {status!r}"
                )
        elif reason not in REASON_CODES[status]:
            problems.append(f"reason_code {reason!r} is not allowed for status {status!r}")

    if "value" in cell and "status" in cell:
        value = cell["value"]
        if status == "available" and value is None:
            problems.append("value is required when status is 'available'")
        elif status not in ("available", "stale") and value is not None:
            problems.append(f"value must be null when status is {status!r}")
    if "value" in cell:
        _reject_forbidden_keys(cell["value"], problems)
        try:
            json.dumps(cell["value"], allow_nan=False)
        except (TypeError, ValueError) as exc:
            problems.append(f"value is not JSON-serialisable: {exc}")

    if "unit" in cell and not (cell["unit"] is None or isinstance(cell["unit"], str)):
        problems.append("unit must be a string or null")

    as_of_date: datetime.date | None = None
    if "as_of" in cell:
        as_of = cell["as_of"]
        if isinstance(as_of, str) and _AS_OF_RE.fullmatch(as_of):
            as_of_date = _calendar(as_of)
        if as_of_date is None:
            problems.append(f"as_of must be a valid YYYY-MM-DD date, got {as_of!r}")

    observed = None
    if "observed_at" in cell:
        observed = _read_temporal("observed_at", cell["observed_at"], problems)
    effective = None
    if "effective_at" in cell:
        effective = _read_temporal("effective_at", cell["effective_at"], problems)
    if status in ("available", "stale") and as_of_date is not None:
        if observed is not None and observed > as_of_date:
            problems.append(
                f"observed_at {observed.isoformat()} is after as_of {as_of_date.isoformat()}"
            )
        if effective is not None and effective > as_of_date:
            problems.append(
                f"effective_at {effective.isoformat()} is after as_of {as_of_date.isoformat()}"
            )

    if "freshness" in cell:
        _check_freshness(cell["freshness"], problems)
    if "quality" in cell and cell["quality"] != "display_only":
        problems.append("quality must be 'display_only'")
    if "labels" in cell:
        _check_labels(cell["labels"], problems)
    if "source" in cell:
        _check_source(cell["source"], problems)
    if "provenance" in cell:
        provenance = cell["provenance"]
        if (
            not isinstance(provenance, list)
            or any(not isinstance(item, str) or item == "" for item in provenance)
        ):
            problems.append("provenance must be a list of non-empty strings")
    if "rights_context" in cell:
        _check_rights(cell["rights_context"], problems)
    return problems


def validate_cell(cell: object) -> list[str]:
    """Return one problem string per contract violation. Never raises."""
    try:
        return _validate_cell(cell)
    except Exception as exc:  # noqa: BLE001 — the contract is a list, never a raise
        return [f"unexpected validation error: {type(exc).__name__}: {exc}"]


def make_cell(
    *,
    axis: str,
    subject_id: str,
    status: str,
    as_of: str,
    source: dict,
    value: object = None,
    reason_code: str | None = None,
    unit: str | None = None,
    observed_at: str | None = None,
    effective_at: str | None = None,
    freshness: dict | None = None,
    labels: object = (),
    provenance: object = (),
    rights_context: dict | None = None,
) -> dict:
    """Build a cell, normalise labels and provenance, and refuse anything invalid.

    Normalisation is ``labels → sorted(set(labels))`` and
    ``provenance → list(provenance)``. A bad value is not coerced into a
    good one.
    """
    try:
        labels_norm = sorted(set(labels))
    except TypeError as exc:
        raise _fail(f"labels are not a set of sortable values: {exc}") from exc
    try:
        provenance_norm = list(provenance)
    except TypeError as exc:
        raise _fail(f"provenance is not iterable: {exc}") from exc
    cell = {
        "schema_version": SCHEMA_VERSION,
        "axis": axis,
        "subject_id": subject_id,
        "status": status,
        "reason_code": reason_code,
        "value": value,
        "unit": unit,
        "observed_at": observed_at,
        "effective_at": effective_at,
        "as_of": as_of,
        "freshness": freshness,
        "quality": "display_only",
        "labels": labels_norm,
        "source": source,
        "provenance": provenance_norm,
        "rights_context": rights_context,
    }
    problems = validate_cell(cell)
    if problems:
        raise AxisCellError("; ".join(problems), problems=list(problems))
    return cell


def available(
    *,
    axis: str,
    subject_id: str,
    value: object,
    as_of: str,
    source: dict,
    **optional: object,
) -> dict:
    """An ``available`` cell. ``reason_code`` is null and ``value`` is required."""
    return make_cell(
        axis=axis,
        subject_id=subject_id,
        status="available",
        reason_code=None,
        value=value,
        as_of=as_of,
        source=source,
        **optional,
    )


def missing(
    *,
    axis: str,
    subject_id: str,
    status: str,
    reason_code: str,
    as_of: str,
    source: dict,
    **optional: object,
) -> dict:
    """A non-available cell. Refuses ``status='available'``."""
    if status == "available":
        raise _fail("missing() refuses status 'available'")
    return make_cell(
        axis=axis,
        subject_id=subject_id,
        status=status,
        reason_code=reason_code,
        as_of=as_of,
        source=source,
        **optional,
    )


def to_json(cell: dict) -> str:
    """Stable JSON: sorted keys, UTF-8, no NaN, no extra whitespace."""
    return json.dumps(
        cell,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
