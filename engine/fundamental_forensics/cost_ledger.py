"""Fundamental-forensics cost and operator-burden ledger (V1-b, node V1).

Purpose
-------
Answer the masterplan V1 evidence question — cost per qualified
filing/issuer/query and operator burden — from measured quantities and
declared rates, with no hidden incomplete tiers.

The core honesty rule: a cost that was not measured and has no declared rate
is ``unmeasured``, never ``0``.  A total or per-unit figure assembled from
incomplete components says so, in the same object, every time: the totals
carry ``complete`` plus ``incomplete_components``, the per-unit quotients
carry ``complete`` plus a ``reason``, and ``render_print`` prints the tokens
``UNMEASURED`` / ``INCOMPLETE`` instead of any blank or zero.  A component
kept in ``incomplete_components`` carries a typed ``incomplete_reason`` —
e.g. ``inference_rows_uncosted``, ``usage_lines_undecodable``,
``inference_rows_outside_window_only``, ``storage_lower_bound``,
``burden_ledger_empty`` — and cost-per-query is refused outright when the
queries counting window is absent (``queries_window_absent``).  Windowed
inference cost forms its own ``query_window`` basis group and is never mixed
into the one-time / per-month quotients; the inference read must have used
the same window the queries denominator declares
(``inference_window_mismatch`` — also raised when a measured or estimated
inference quantity carries no window claim of its own against a declared
queries window), and a window whose start does not precede its end is
refused (``window_inverted``).  With no declared queries window an
inference total is a lifetime figure: it is labelled
``undeclared_window``, excluded from the ``query_window`` group (which is
then incomplete, with reason ``queries_window_absent`` on its total), and
the printed per-unit lines carry only the groups in their basis.

Purity
------
Standard library only.  No network, no store, no wall-clock read (``built_at``
is always a caller input), no import from ``scripts/``.  The only filesystem
effects are reading rates / burden / caller-supplied inputs and appending to
the operator-burden ledger; files are opened in modes ``r`` and ``a`` only,
and the burden ledger is never rewritten or truncated.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

RATES_SCHEMA = "fundamental_forensics.cost_rates/v1"
LEDGER_SCHEMA = "fundamental_forensics.cost_ledger/v1"
BURDEN_SCHEMA = "fundamental_forensics.operator_burden/v1"

COMPONENTS = ("source", "licence", "storage", "parse", "inference", "review")
HARD_MAX_INPUT_BYTES = 64 * 1024 * 1024
HARD_MAX_ROWS = 1_000_000
MAX_BURDEN_MINUTES = 1440

# C2 freeze §6.3 (2026-10-17) — deep/core package design assumptions this
# lane must compare its measurements against, never silently substitute.
DEEP_PACKAGE_DESIGN_BYTES_PER_ISSUER = 10_833_964
DEEP_FLEET_DESIGN_BYTES = 2_708_491_000  # 250 deep issuers
CORE_PACKAGE_DESIGN_BYTES_PER_ISSUER = 5_416_982
COMBINED_FLEET_DESIGN_BYTES = 6_771_227_500  # deep ⊂ core, 1,000 issuers
# C2 freeze §6.4 (2026-10-17) — cold-capture GET assumptions.
COLD_DEEP_GETS_PER_ISSUER = 29
COLD_DEEP_GETS_DESIGN_FLEET = 7_250  # 29 GETs × 250 deep issuers
COLD_CORE_GETS_PER_ISSUER = 15
COLD_CORE_GETS_DESIGN_FLEET = 15_000  # 15 GETs × 1,000 core issuers

MEASURED = "measured"
ESTIMATED = "estimated"
UNMEASURED = "unmeasured"

_DENOMINATOR_KEYS = (
    "qualified_filings",
    "qualified_issuers_deep",
    "qualified_issuers_core",
    "queries",
)
_ACTOR_ROLES = ("seat", "operator", "reviewer", "chairman")
_ACT_KINDS = ("review", "repair", "approval", "incident", "manual_run", "credential_step")
_BURDEN_FIELDS = (
    "schema",
    "event_id",
    "recorded_at",
    "actor_role",
    "act_kind",
    "minutes",
    "ref",
    "note",
)
_RECORDED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$")


class CostLedgerError(ValueError):
    """A typed refusal; ``code`` is the machine-readable cause."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Quantity:
    """One measured / estimated / unmeasured input to a component cost."""

    value: float | None
    unit: str
    status: str
    notes: tuple[str, ...] = ()
    counts: dict[str, Any] = field(default_factory=dict)


# ── shared bounded reading ───────────────────────────────────────────────────


def read_text_bounded(path: str | os.PathLike[str]) -> str:
    """Read a whole input file, refusing anything over HARD_MAX_INPUT_BYTES."""
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise CostLedgerError("input_unreadable", f"cannot stat {path}: {exc}")
    if size > HARD_MAX_INPUT_BYTES:
        raise CostLedgerError(
            "input_too_large",
            f"{path} is {size} bytes, over the {HARD_MAX_INPUT_BYTES} byte limit",
        )
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise CostLedgerError("input_unreadable", f"cannot read {path}: {exc}")


# ── rates ────────────────────────────────────────────────────────────────────

_RATE_FIELDS = (
    "rate_id",
    "component",
    "unit",
    "usd_per_unit",
    "status",
    "verified",
    "basis_period",
    "source",
    "as_of",
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_rate_entry(entry: Any) -> None:
    if not isinstance(entry, dict):
        raise CostLedgerError("rates_shape", "each rate must be a JSON object")
    for key in _RATE_FIELDS:
        if key not in entry:
            raise CostLedgerError("rates_shape", f"rate is missing '{key}'")
    if entry["component"] not in COMPONENTS:
        raise CostLedgerError(
            "rates_shape", f"unknown rate component '{entry['component']}'"
        )
    for key in ("rate_id", "unit", "source", "as_of"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise CostLedgerError("rates_shape", f"rate '{key}' must be a non-empty string")
    if entry["status"] not in ("declared_rate", "unmeasured"):
        raise CostLedgerError(
            "rates_shape", f"rate status must be declared_rate or unmeasured, got {entry['status']!r}"
        )
    if not isinstance(entry["verified"], bool):
        raise CostLedgerError("rates_shape", "rate 'verified' must be a boolean")
    if entry["basis_period"] not in ("one_time", "per_month"):
        raise CostLedgerError(
            "rates_shape", "rate 'basis_period' must be one_time or per_month"
        )
    usd = entry["usd_per_unit"]
    if entry["status"] == "declared_rate":
        if not _is_number(usd) or not math.isfinite(usd) or usd < 0:
            raise CostLedgerError(
                "rates_shape",
                f"declared_rate '{entry['rate_id']}' needs a finite usd_per_unit >= 0",
            )
    elif usd is not None:
        raise CostLedgerError(
            "rates_shape", f"unmeasured rate '{entry['rate_id']}' must carry usd_per_unit null"
        )


def load_rates(path: str | os.PathLike[str]) -> dict:
    """Load and check a rates config; every component needs exactly one rate.

    Returns a normalized structure with ``rates_id``, ``content_sha256``,
    ``inference_row_filter`` and a ``components`` mapping used by
    ``build_cost_ledger``.
    """
    text = read_text_bounded(path)
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CostLedgerError("rates_shape", f"rates config is not JSON: {exc}")
    if not isinstance(doc, dict) or doc.get("schema") != RATES_SCHEMA:
        raise CostLedgerError("rates_shape", f"rates config schema must be {RATES_SCHEMA}")
    rates_id = doc.get("rates_id")
    if not isinstance(rates_id, str) or not rates_id.strip():
        raise CostLedgerError("rates_shape", "rates_id must be a non-empty string")
    entries = doc.get("rates")
    if not isinstance(entries, list):
        raise CostLedgerError("rates_shape", "'rates' must be a list")
    seen: dict[str, dict] = {}
    for entry in entries:
        _check_rate_entry(entry)
        component = entry["component"]
        if component in seen:
            raise CostLedgerError(
                "rates_duplicate_component", f"component '{component}' has more than one rate"
            )
        seen[component] = dict(entry)
    missing = [component for component in COMPONENTS if component not in seen]
    if missing:
        raise CostLedgerError(
            "rates_missing_component", f"no rate declared for: {', '.join(missing)}"
        )
    row_filter = doc.get("inference_row_filter") or {}
    if not isinstance(row_filter, dict):
        raise CostLedgerError("rates_shape", "inference_row_filter must be an object")
    normalized_filter: dict[str, list[str]] = {}
    for key in ("stage_prefixes", "lane_prefixes"):
        prefixes = row_filter.get(key) or []
        if not isinstance(prefixes, list) or any(
            not isinstance(prefix, str) for prefix in prefixes
        ):
            raise CostLedgerError(
                "rates_shape", f"inference_row_filter '{key}' must be a list of strings"
            )
        normalized_filter[key] = [prefix for prefix in prefixes if prefix]
    return {
        "rates_id": rates_id,
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "inference_row_filter": normalized_filter,
        "components": seen,
    }


# ── quantity readers ─────────────────────────────────────────────────────────


def _numeric_sum(mapping: Any) -> int | None:
    if not isinstance(mapping, dict):
        return None
    numbers = [value for value in mapping.values() if _is_number(value)]
    return int(sum(numbers)) if numbers else None


def _cold_deep_gets_per_issuer(sub: Any) -> int | None:
    """1 submissions GET plus one index GET per deep slot, per the receipt."""
    if not isinstance(sub, dict):
        return None
    if all(key in sub for key in ("submissions_per_issuer", "index_per_slot", "deep_slots")):
        return int(sub["submissions_per_issuer"]) + int(sub["index_per_slot"]) * int(
            sub["deep_slots"]
        )
    return _numeric_sum(sub)


def source_quantity_from_receipt(receipt: Mapping[str, Any]) -> Quantity:
    """GET count from an economics receipt; a warm-cache run says so."""
    if not isinstance(receipt, dict):
        raise CostLedgerError("receipt_shape", "economics receipt must be a JSON object")
    if "get_count_total" not in receipt:
        return Quantity(
            None, "get", UNMEASURED, notes=("get_count_total_missing",), counts={}
        )
    raw = receipt["get_count_total"]
    if not _is_number(raw) or not math.isfinite(raw):
        return Quantity(
            None, "get", UNMEASURED, notes=("get_count_total_unreadable",), counts={}
        )
    value = float(raw)
    counts: dict[str, Any] = {}
    notes: list[str] = []
    transfer = receipt.get("transfer_bytes_total")
    counts["transfer_bytes_total"] = transfer if _is_number(transfer) else None
    cold = receipt.get("measured_implied_cold_gets")
    if isinstance(cold, dict):
        if value == 0.0:
            notes.append("warm_cache_run")
        counts["cold_deep_gets_per_issuer"] = _cold_deep_gets_per_issuer(
            cold.get("deep_per_issuer")
        )
        counts["cold_core_gets_per_issuer"] = _numeric_sum(cold.get("core_per_issuer"))
        fleet = cold.get("deep_cold_fleet_total_estimate_at_measured")
        if _is_number(fleet):
            counts["cold_deep_gets_fleet_estimate"] = fleet
    return Quantity(value, "get", MEASURED, notes=tuple(notes), counts=counts)


_DEEP_PACKAGE_COLUMNS = (
    "cik",
    "slot_id",
    "accession",
    "member_count",
    "primary_present",
    "primary_bytes",
    "schema_present",
    "schema_bytes",
    "presentation_present",
    "presentation_bytes",
    "calculation_present",
    "calculation_bytes",
    "definition_present",
    "definition_bytes",
    "label_present",
    "label_bytes",
    "summed_declared_bytes",
    "notes",
)
_PACKAGE_ROLES = ("primary", "schema", "presentation", "calculation", "definition", "label")
_ROLE_PRESENT_COLUMN = {
    role: _DEEP_PACKAGE_COLUMNS.index(f"{role}_present") for role in _PACKAGE_ROLES
}
_ROLE_BYTES_COLUMN = {
    role: _DEEP_PACKAGE_COLUMNS.index(f"{role}_bytes") for role in _PACKAGE_ROLES
}
_SUMMED_COLUMN = _DEEP_PACKAGE_COLUMNS.index("summed_declared_bytes")
_NOTES_COLUMN = _DEEP_PACKAGE_COLUMNS.index("notes")


def _parse_nonnegative_int(cell: str) -> int | None:
    try:
        parsed = int(cell)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def storage_quantity_from_deep_packages(csv_text: str) -> Quantity:
    """Six-role byte total (decimal GB) from a deep-packages census CSV.

    Cells that do not parse as non-negative integers — the census emitted the
    text ``False`` for some role-byte cells — are excluded from the sum and
    counted per role, which makes the quantity a lower bound (``estimated``).
    """
    reader = csv.reader(io.StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        raise CostLedgerError("packages_shape", "deep packages CSV has no header row")
    if tuple(cell.strip() for cell in header) != _DEEP_PACKAGE_COLUMNS:
        raise CostLedgerError(
            "packages_shape", "deep packages CSV header does not match the census layout"
        )
    rows = 0
    six_role_bytes = 0
    all_member_bytes = 0
    suspects = 0
    unparseable = {role: 0 for role in _PACKAGE_ROLES}
    missing_role = {role: 0 for role in _PACKAGE_ROLES}
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        rows += 1
        if rows > HARD_MAX_ROWS:
            raise CostLedgerError(
                "too_many_rows", f"deep packages CSV exceeds {HARD_MAX_ROWS} rows"
            )
        if len(row) != len(_DEEP_PACKAGE_COLUMNS):
            raise CostLedgerError(
                "packages_shape", f"row {rows} has {len(row)} cells, expected {len(_DEEP_PACKAGE_COLUMNS)}"
            )
        if "exhibit" in row[_NOTES_COLUMN].lower():
            suspects += 1
        for role in _PACKAGE_ROLES:
            if row[_ROLE_PRESENT_COLUMN[role]].strip() != "True":
                missing_role[role] += 1
            parsed = _parse_nonnegative_int(row[_ROLE_BYTES_COLUMN[role]])
            if parsed is None:
                unparseable[role] += 1
            else:
                six_role_bytes += parsed
        summed = _parse_nonnegative_int(row[_SUMMED_COLUMN])
        if summed is not None:
            all_member_bytes += summed
    notes: list[str] = []
    if any(unparseable.values()):
        status = ESTIMATED
        notes.append("unparseable_cells_excluded")
    else:
        status = MEASURED
    if suspects:
        notes.append("primary_bytes_understated")
    counts = {
        "rows": rows,
        "six_role_bytes": six_role_bytes,
        "all_member_bytes": all_member_bytes,
        "unparseable_cells": unparseable,
        "missing_role_cells": missing_role,
        "primary_misidentified_suspect": suspects,
    }
    return Quantity(six_role_bytes / 1e9, "gb", status, tuple(notes), counts)


def _parse_instant(text: Any) -> datetime | None:
    """Parse a strict ISO instant; anything else (naive, malformed) is None."""
    if not isinstance(text, str) or not text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None or moment.utcoffset() is None:
        return None
    return moment


def _window_bounds(window: Any) -> tuple[datetime, datetime] | None:
    """Half-open ``[start, end)`` bounds of a queries counting window.

    A window that is absent, not an object, missing a bound, or carrying an
    unparseable bound is not a declared window (``None``): rows are then not
    filtered and cost-per-query is refused with ``queries_window_absent``.
    A window whose start does not strictly precede its end is a typed
    refusal (``window_inverted``) — it declares no interval at all.
    """
    if not isinstance(window, dict):
        return None
    start = _parse_instant(window.get("start"))
    end = _parse_instant(window.get("end"))
    if start is None or end is None:
        return None
    if start >= end:
        raise CostLedgerError(
            "window_inverted", "window start must strictly precede its end"
        )
    return start, end


def _utc_text(moment: datetime) -> str:
    """ISO-8601 UTC text with a trailing ``Z``."""
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalized_window(window: Any) -> dict | None:
    """A declared window as UTC ``Z`` text, or ``None`` when not declared."""
    bounds = _window_bounds(window)
    if bounds is None:
        return None
    return {"start": _utc_text(bounds[0]), "end": _utc_text(bounds[1])}


def inference_quantity_from_usage(
    lines: Iterable[str],
    row_filter: Mapping[str, Any],
    window: Mapping[str, Any] | None = None,
) -> Quantity:
    """Sum est_cost_usd over ai_costs.usage.v1 rows this lane caused.

    When a queries counting window is declared the matched rows are tied to
    the same half-open ``[start, end)`` interval: rows outside it — including
    matched rows whose ``ts`` cannot be placed — are excluded from the sum and
    counted as ``inference_rows_outside_window`` (untimed rows also in
    ``inference_rows_untimed``), never silently included.  The window the
    reader applied is recorded, normalised to UTC, as ``declared_window`` so
    the ledger build can prove it equals the queries counting window.

    The honesty rule: an empty or absent filter, an undecodable usage line
    (it could have been a matching row), zero matching rows, matched rows
    that all fall outside the window, or in-window rows whose cost is missing
    all make the quantity ``unmeasured`` with a typed reason — the value is
    ``None``, never a measured or estimated zero.  Only a set in which every
    matched row sits in the window and decodes with a cost is ``measured``.
    """
    if row_filter is None:
        row_filter = {}
    if not isinstance(row_filter, dict):
        raise CostLedgerError("row_filter_shape", "inference row filter must be an object")
    stage_prefixes = [
        prefix.lower() for prefix in (row_filter.get("stage_prefixes") or []) if prefix
    ]
    lane_prefixes = [
        prefix.lower() for prefix in (row_filter.get("lane_prefixes") or []) if prefix
    ]
    bounds = _window_bounds(window)
    declared_window = _normalized_window(window)
    rows_read = 0
    rows_matched = 0
    rows_in_window = 0
    rows_undecodable = 0
    rows_uncosted = 0
    rows_outside_window = 0
    rows_untimed = 0
    total = 0.0
    stamps: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        rows_read += 1
        if rows_read > HARD_MAX_ROWS:
            raise CostLedgerError("too_many_rows", f"usage ledger exceeds {HARD_MAX_ROWS} rows")
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            rows_undecodable += 1
            continue
        if not isinstance(row, dict):
            rows_undecodable += 1
            continue
        stage = row.get("stage")
        lane = row.get("lane")
        stage = stage if isinstance(stage, str) else ""
        lane = lane if isinstance(lane, str) else ""
        stage_hit = any(stage.lower().startswith(prefix) for prefix in stage_prefixes)
        lane_hit = any(lane.lower().startswith(prefix) for prefix in lane_prefixes)
        if not (stage_hit or lane_hit):
            continue
        rows_matched += 1
        raw_ts = row.get("ts")
        moment = _parse_instant(raw_ts)
        if bounds is not None:
            if moment is None:
                # A matched row that cannot be placed in time is never
                # included: it is outside the window and untimed.
                rows_outside_window += 1
                rows_untimed += 1
                continue
            if not bounds[0] <= moment < bounds[1]:
                rows_outside_window += 1
                continue
        rows_in_window += 1
        if isinstance(raw_ts, str) and raw_ts:
            stamps.append(raw_ts)
        cost = row.get("est_cost_usd")
        if not _is_number(cost) or not math.isfinite(cost):
            rows_uncosted += 1
        else:
            total += float(cost)
    window_summary = {"min": min(stamps), "max": max(stamps)} if stamps else None
    # Reason precedence, first match wins: filter, undecodable lines, absent
    # rows, outside-window-only rows, uncosted in-window rows, else measured.
    if not stage_prefixes and not lane_prefixes:
        status, value, notes = UNMEASURED, None, ("inference_filter_empty",)
    elif rows_undecodable:
        status, value, notes = UNMEASURED, None, ("usage_lines_undecodable",)
    elif rows_matched == 0:
        status, value, notes = UNMEASURED, None, ("inference_rows_absent",)
    elif rows_in_window == 0:
        status, value, notes = UNMEASURED, None, ("inference_rows_outside_window_only",)
    elif rows_uncosted:
        status, value, notes = UNMEASURED, None, ("inference_rows_uncosted",)
    else:
        status, value, notes = MEASURED, total, ()
    counts = {
        "rows_read": rows_read,
        "rows_matched": rows_matched,
        "rows_in_window": rows_in_window,
        "rows_undecodable": rows_undecodable,
        "rows_uncosted": rows_uncosted,
        "inference_rows_outside_window": rows_outside_window,
        "inference_rows_untimed": rows_untimed,
        "declared_window": declared_window,
        "window": window_summary,
    }
    return Quantity(value, "usd", status, notes, counts)


def parse_quantity(parse_cpu_seconds: float | None = None) -> Quantity:
    """Parse cost quantity; absent input stays unmeasured, never zero."""
    if parse_cpu_seconds is None:
        return Quantity(
            None, "cpu_second", UNMEASURED, notes=("parse_cpu_seconds_not_provided",), counts={}
        )
    if not _is_number(parse_cpu_seconds) or not math.isfinite(parse_cpu_seconds) or parse_cpu_seconds < 0:
        raise CostLedgerError(
            "quantity_shape", "parse_cpu_seconds must be a finite number >= 0"
        )
    return Quantity(float(parse_cpu_seconds), "cpu_second", MEASURED)


def licence_quantity(issuers: int | None = None) -> Quantity:
    """Licence cost quantity (issuers covered); absent input stays unmeasured."""
    if issuers is None:
        return Quantity(
            None, "issuer", UNMEASURED, notes=("licence_issuers_not_provided",), counts={}
        )
    if not _is_number(issuers) or issuers < 0:
        raise CostLedgerError("quantity_shape", "licence issuers must be a number >= 0")
    return Quantity(float(issuers), "issuer", MEASURED)


def review_quantity_from_burden_rows(burden_rows: list[dict] | None) -> Quantity:
    """Review-minutes quantity from the burden ledger state.

    An empty or absent ledger is ``unmeasured`` with the typed reason
    ``burden_ledger_empty`` — a null value, never a measured zero.  A ledger
    with entries is ``measured`` even when the minutes sum to 0: emptiness
    demotes, a zero sum does not.
    """
    if burden_rows is None:
        return Quantity(
            None,
            "minute",
            UNMEASURED,
            notes=("no_burden_file", "burden_ledger_empty"),
            counts={},
        )
    if not burden_rows:
        return Quantity(
            None, "minute", UNMEASURED, notes=("burden_ledger_empty",), counts={"events": 0}
        )
    minutes = float(sum(row["minutes"] for row in burden_rows))
    return Quantity(minutes, "minute", MEASURED, counts={"events": len(burden_rows)})


# ── operator-burden ledger (append-only JSONL) ───────────────────────────────


def _parse_recorded_at(text: Any) -> datetime:
    if not isinstance(text, str) or not _RECORDED_AT_PATTERN.match(text):
        raise CostLedgerError(
            "burden_shape", "recorded_at must be strict UTC text like 2026-10-19T00:00:00Z"
        )
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CostLedgerError("burden_shape", f"recorded_at is not a real instant: {exc}")


def _check_burden_row(row: Any) -> None:
    if not isinstance(row, dict):
        raise CostLedgerError("burden_shape", "burden row must be a JSON object")
    if set(row) != set(_BURDEN_FIELDS):
        raise CostLedgerError(
            "burden_shape", f"burden row keys must be exactly {sorted(_BURDEN_FIELDS)}"
        )
    if row["schema"] != BURDEN_SCHEMA:
        raise CostLedgerError("burden_shape", f"burden row schema must be {BURDEN_SCHEMA}")
    for key in ("event_id", "ref"):
        if not isinstance(row[key], str) or not row[key].strip():
            raise CostLedgerError("burden_shape", f"burden row '{key}' must be a non-empty string")
    if not isinstance(row["note"], str):
        raise CostLedgerError("burden_shape", "burden row 'note' must be a string")
    if row["actor_role"] not in _ACTOR_ROLES:
        raise CostLedgerError(
            "burden_shape", f"actor_role must be one of {_ACTOR_ROLES}, got {row['actor_role']!r}"
        )
    if row["act_kind"] not in _ACT_KINDS:
        raise CostLedgerError(
            "burden_shape", f"act_kind must be one of {_ACT_KINDS}, got {row['act_kind']!r}"
        )
    minutes = row["minutes"]
    if (
        not _is_number(minutes)
        or not math.isfinite(minutes)
        or not 0 < minutes <= MAX_BURDEN_MINUTES
    ):
        raise CostLedgerError(
            "burden_shape",
            f"minutes must be finite and in (0, {MAX_BURDEN_MINUTES}], got {minutes!r}",
        )
    _parse_recorded_at(row["recorded_at"])


def read_burden(path: str | os.PathLike[str]) -> list[dict]:
    """Read every burden row, checking shape, uniqueness and clock order."""
    text = read_text_bounded(path)
    rows: list[dict] = []
    seen_ids: set[str] = set()
    previous: datetime | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if len(rows) >= HARD_MAX_ROWS:
            raise CostLedgerError("too_many_rows", f"burden ledger exceeds {HARD_MAX_ROWS} rows")
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise CostLedgerError("burden_shape", f"burden line {line_number} is not JSON: {exc}")
        _check_burden_row(row)
        if row["event_id"] in seen_ids:
            raise CostLedgerError(
                "burden_duplicate", f"event_id '{row['event_id']}' appears twice"
            )
        seen_ids.add(row["event_id"])
        moment = _parse_recorded_at(row["recorded_at"])
        if previous is not None and moment < previous:
            raise CostLedgerError(
                "burden_clock_regression",
                f"line {line_number} recorded_at {row['recorded_at']} precedes the prior row",
            )
        previous = moment
        rows.append(row)
    return rows


def append_burden(path: str | os.PathLike[str], row: Mapping[str, Any]) -> dict:
    """Append exactly one burden row; the file is never rewritten or truncated."""
    _check_burden_row(row)
    existing = read_burden(path) if os.path.exists(path) else []
    if any(prior["event_id"] == row["event_id"] for prior in existing):
        raise CostLedgerError(
            "burden_duplicate", f"event_id '{row['event_id']}' already exists in {path}"
        )
    if existing:
        last = _parse_recorded_at(existing[-1]["recorded_at"])
        if _parse_recorded_at(row["recorded_at"]) < last:
            raise CostLedgerError(
                "burden_clock_regression",
                f"recorded_at {row['recorded_at']} precedes the last row's {existing[-1]['recorded_at']}",
            )
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    return dict(row)


# ── ledger build ─────────────────────────────────────────────────────────────


def _check_denominators(denominators: Any) -> dict:
    if not isinstance(denominators, dict):
        raise CostLedgerError("denominators_shape", "denominators must be an object")
    if set(denominators) != set(_DENOMINATOR_KEYS):
        raise CostLedgerError(
            "denominators_shape", f"denominators keys must be exactly {list(_DENOMINATOR_KEYS)}"
        )
    checked: dict[str, dict] = {}
    for key in _DENOMINATOR_KEYS:
        entry = denominators[key]
        if not isinstance(entry, dict):
            raise CostLedgerError("denominators_shape", f"denominator '{key}' must be an object")
        if set(entry) - {"value", "source", "window"}:
            raise CostLedgerError(
                "denominators_shape", f"denominator '{key}' has unknown keys"
            )
        for required in ("value", "source"):
            if required not in entry:
                raise CostLedgerError(
                    "denominators_shape", f"denominator '{key}' is missing '{required}'"
                )
        value = entry["value"]
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise CostLedgerError(
                "denominators_shape", f"denominator '{key}' value must be an integer or null"
            )
        if not isinstance(entry["source"], str):
            raise CostLedgerError(
                "denominators_shape", f"denominator '{key}' source must be a string"
            )
        checked[key] = {
            "value": value,
            "source": entry["source"],
        }
        if key == "queries":
            # An inverted queries counting window is refused here as well as
            # in the usage reader: both surfaces must reject it.
            _window_bounds(entry.get("window"))
            checked[key]["window"] = entry.get("window")
    return checked


def _burden_summary(burden_rows: list[dict] | None) -> dict:
    if burden_rows is None:
        return {
            "status": UNMEASURED,
            "minutes_total": None,
            "events": 0,
            "by_act_kind": {},
            "by_actor_role": {},
            "window": None,
            "notes": ["no_burden_file", "burden_ledger_empty"],
        }
    if not burden_rows:
        return {
            "status": UNMEASURED,
            "minutes_total": None,
            "events": 0,
            "by_act_kind": {},
            "by_actor_role": {},
            "window": None,
            "notes": ["burden_ledger_empty"],
        }
    by_act_kind: dict[str, float] = {}
    by_actor_role: dict[str, float] = {}
    for row in burden_rows:
        by_act_kind[row["act_kind"]] = by_act_kind.get(row["act_kind"], 0.0) + float(row["minutes"])
        by_actor_role[row["actor_role"]] = by_actor_role.get(row["actor_role"], 0.0) + float(
            row["minutes"]
        )
    return {
        "status": MEASURED,
        "minutes_total": float(sum(row["minutes"] for row in burden_rows)),
        "events": len(burden_rows),
        "by_act_kind": by_act_kind,
        "by_actor_role": by_actor_role,
        "window": {
            "first": burden_rows[0]["recorded_at"],
            "last": burden_rows[-1]["recorded_at"],
        },
        "notes": [],
    }


def _design_comparison(quantities: Mapping[str, Quantity]) -> dict | None:
    storage_counts = quantities["storage"].counts
    source_counts = quantities["source"].counts
    if "six_role_bytes" not in storage_counts or not source_counts:
        return None
    six_role = storage_counts.get("six_role_bytes")
    all_member = storage_counts.get("all_member_bytes")
    fleet_estimate = source_counts.get("cold_deep_gets_fleet_estimate")
    six_ratio = six_role / DEEP_FLEET_DESIGN_BYTES if _is_number(six_role) else None
    fleet_ratio = (
        fleet_estimate / COLD_DEEP_GETS_DESIGN_FLEET if _is_number(fleet_estimate) else None
    )
    return {
        "deep_fleet_design_bytes": DEEP_FLEET_DESIGN_BYTES,
        "deep_six_role_bytes_measured": six_role,
        "deep_six_role_ratio_to_design": six_ratio,
        "deep_all_member_bytes_measured": all_member,
        "cold_deep_gets_design": COLD_DEEP_GETS_DESIGN_FLEET,
        "cold_deep_gets_receipt_estimate": fleet_estimate,
        "cold_deep_gets_ratio_receipt_to_design": fleet_ratio,
    }


# Typed reasons a component stays in incomplete_components even when its
# cost_status alone would not say so (F1/F3/F4 r2 rulings, 2026-10-19; R1/R3
# r3 rulings the same day).
_COMPONENT_REASON_NOTES = {
    "inference": frozenset(
        {
            "inference_rows_uncosted",
            "inference_rows_absent",
            "inference_filter_empty",
            "usage_lines_undecodable",
            "inference_rows_outside_window_only",
        }
    ),
    "review": frozenset({"burden_ledger_empty"}),
}


def _incomplete_reason(component: str, quantity: Quantity) -> str | None:
    """The typed reason a component belongs in incomplete_components."""
    if component == "storage":
        # A lower bound: unparseable cells were excluded, or primary bytes
        # are known understated — the sum is reported but never complete.
        if quantity.status == ESTIMATED or "primary_bytes_understated" in quantity.notes:
            return "storage_lower_bound"
        return None
    allowed = _COMPONENT_REASON_NOTES.get(component, frozenset())
    for note in quantity.notes:
        if note in allowed:
            return note
    return None


def build_cost_ledger(
    *,
    rates: Mapping[str, Any],
    quantities: Mapping[str, Quantity],
    denominators: Mapping[str, Any],
    burden_rows: list[dict] | None,
    built_at: datetime,
) -> dict:
    """Assemble the cost ledger; incomplete tiers are named, never zero-filled."""
    if not isinstance(built_at, datetime) or built_at.tzinfo is None or built_at.utcoffset() is None:
        raise CostLedgerError("naive_clock", "built_at must be a timezone-aware datetime")
    if not isinstance(quantities, dict) or set(quantities) != set(COMPONENTS):
        raise CostLedgerError(
            "ledger_shape", f"quantities must carry exactly {list(COMPONENTS)}"
        )
    components_by_rate = rates.get("components")
    if not isinstance(components_by_rate, dict) or set(components_by_rate) != set(COMPONENTS):
        raise CostLedgerError("ledger_shape", "rates must be a load_rates() result")
    for component in COMPONENTS:
        if not isinstance(quantities[component], Quantity):
            raise CostLedgerError(
                "ledger_shape", f"quantities['{component}'] must be a Quantity"
            )
    checked_denominators = _check_denominators(denominators)

    # The inference rows must have been read against the same window the
    # queries denominator declares: a windowed cost divided by a differently
    # windowed count is not a quotient.  One side declared and the other not
    # is the same refusal — and a measured or estimated quantity that carries
    # no ``declared_window`` claim at all (not produced by the usage reader)
    # is refused against a declared queries window too: it cannot prove its
    # rows sit inside that window.
    inference_counts = quantities["inference"].counts
    queries_window = _normalized_window(
        checked_denominators["queries"].get("window")
    )
    queries_window_declared = queries_window is not None
    carries_window_claim = (
        isinstance(inference_counts, dict) and "declared_window" in inference_counts
    )
    if carries_window_claim:
        inference_window = _normalized_window(inference_counts.get("declared_window"))
        if inference_window != queries_window:
            raise CostLedgerError(
                "inference_window_mismatch",
                f"inference rows were read with window {inference_window} "
                f"but the queries denominator declares {queries_window}",
            )
    elif queries_window_declared and quantities["inference"].status in (
        MEASURED,
        ESTIMATED,
    ):
        raise CostLedgerError(
            "inference_window_mismatch",
            "a measured or estimated inference quantity used against a "
            "declared queries window must carry counts.declared_window",
        )

    components_out: dict[str, dict] = {}
    for component in COMPONENTS:
        quantity = quantities[component]
        rate = components_by_rate[component]
        cost_usd: float | None = None
        if quantity.value is not None and rate["status"] == "declared_rate":
            cost_usd = quantity.value * float(rate["usd_per_unit"])
        if quantity.status == UNMEASURED or rate["status"] == "unmeasured":
            # An unmeasured component is never promoted to measured or
            # declared, whatever its rate says.
            cost_status = "incomplete"
        elif rate["verified"] is False:
            cost_status = "declared_unverified"
        elif quantity.status == MEASURED:
            cost_status = "measured"
        else:
            cost_status = "declared"
        rate_basis = rate["basis_period"]
        # Windowed inference is never mixed into the one-time / per-month
        # quotients: it forms its own basis group — ``query_window`` when a
        # queries window was declared, else ``undeclared_window``, because
        # the figure is then a lifetime total — while
        # ``rate_basis_period`` still echoes the rate's own declared basis.
        if component == "inference":
            basis_period = "query_window" if queries_window_declared else "undeclared_window"
        else:
            basis_period = rate_basis
        components_out[component] = {
            "quantity_value": quantity.value,
            "quantity_unit": quantity.unit,
            "quantity_status": quantity.status,
            "usd_per_unit": rate["usd_per_unit"],
            "rate_status": rate["status"],
            "rate_verified": rate["verified"],
            "basis_period": basis_period,
            "rate_basis_period": rate_basis,
            "cost_usd": cost_usd,
            "cost_status": cost_status,
            "incomplete_reason": _incomplete_reason(component, quantity),
            "notes": list(quantity.notes),
            "counts": quantity.counts,
        }

    periods: dict[str, list[tuple[str, dict]]] = {
        "one_time": [],
        "per_month": [],
        "query_window": [],
        "undeclared_window": [],
    }
    for component in COMPONENTS:
        periods[components_out[component]["basis_period"]].append(
            (component, components_out[component])
        )
    # r5 (2026-10-19): the incomplete query-window total names why — a
    # measured or estimated inference quantity was moved to
    # undeclared_window because no queries window was declared.  An
    # unmeasured inference carries no reason: its incompleteness is the
    # ordinary unmeasured-component fact, not a windowing one.
    query_window_reason = (
        "queries_window_absent"
        if not queries_window_declared
        and quantities["inference"].status in (MEASURED, ESTIMATED)
        else None
    )
    totals: dict[str, dict] = {}
    for period in ("one_time", "per_month", "query_window"):
        members = periods[period]
        if period == "query_window" and not queries_window_declared:
            # With no declared queries window an inference total is a
            # lifetime figure, never a window total: the undeclared members
            # stay in the group's accounting — named in
            # incomplete_components, forcing complete=False — but their
            # costs never enter known_usd.  The per-query quotient is
            # separately refused (queries_window_absent).
            members = members + periods["undeclared_window"]
            members_with_cost: list[tuple[str, dict]] = []
            incomplete = sorted(component for component, _ in members)
        else:
            members_with_cost = members
            incomplete = sorted(
                component
                for component, entry in members
                if entry["cost_status"] == "incomplete"
                or entry["incomplete_reason"] is not None
            )
        known = [
            entry["cost_usd"]
            for _, entry in members_with_cost
            if entry["cost_usd"] is not None
        ]
        totals[period] = {
            "known_usd": sum(known) if known else None,
            "complete": not incomplete,
            "incomplete_components": incomplete,
            "reason": query_window_reason if period == "query_window" else None,
        }
    complete = all(
        totals[period]["complete"] for period in ("one_time", "per_month", "query_window")
    )

    per_unit: dict[str, dict] = {}
    for key in _DENOMINATOR_KEYS:
        denominator = checked_denominators[key]["value"]
        if key == "queries":
            # Cost-per-query divides only the windowed inference total; the
            # one-time and per-month costs are never per-query.
            basis_groups = ("query_window",)
        else:
            # Per-filing and per-issuer quotients divide the one-time and
            # per-month totals only; inference is never in their numerator.
            basis_groups = ("one_time", "per_month")
        numerator_components = sorted(
            component for period in basis_groups for component, _ in periods[period]
        )
        groups_complete = all(totals[period]["complete"] for period in basis_groups)
        entry = {
            "one_time_usd": None,
            "per_month_usd": None,
            "query_window_usd": None,
            "components": numerator_components,
            "basis": list(basis_groups),
            "complete": False,
            "reason": None,
        }
        if key == "queries" and not queries_window_declared:
            # Cost-per-query is refused outright when the queries counting
            # window is absent: the inference rows cannot be tied to the
            # counted queries, so no quotient is honest.
            entry["reason"] = "queries_window_absent"
        elif denominator is None:
            entry["reason"] = "denominator_unmeasured"
        elif denominator == 0:
            entry["reason"] = "denominator_zero"
        else:
            for period in basis_groups:
                known = totals[period]["known_usd"]
                if known is not None:
                    entry[f"{period}_usd"] = known / denominator
            if not groups_complete:
                entry["reason"] = "components_incomplete"
        # A refused quotient is never complete, whatever its numerator.
        entry["complete"] = groups_complete and entry["reason"] is None
        per_unit[key] = entry

    ledger = {
        "schema": LEDGER_SCHEMA,
        "built_at": built_at.isoformat(),
        "complete": complete,
        "rates": {
            "rates_id": rates["rates_id"],
            "content_sha256": rates["content_sha256"],
        },
        "components": components_out,
        "totals": totals,
        "denominators": checked_denominators,
        "per_unit": per_unit,
        "operator_burden": _burden_summary(burden_rows),
    }
    design = _design_comparison(quantities)
    if design is not None:
        ledger["design_comparison"] = design
    return ledger


# ── printing ─────────────────────────────────────────────────────────────────


def _fmt(value: float | None) -> str:
    return "UNMEASURED" if value is None else f"{value:.6f}"


def _fmt_quotient(value: float | None, period_complete: bool) -> str:
    if value is None:
        return "UNMEASURED"
    text = f"{value:.6f}"
    return text if period_complete else text + "/INCOMPLETE"


def render_print(ledger: Mapping[str, Any]) -> str:
    """One line per component and per denominator, plus burden and comparison."""
    lines: list[str] = []
    lines.append(f"fif cost ledger schema={ledger['schema']}")
    lines.append(f"built_at={ledger['built_at']}")
    lines.append(
        f"rates={ledger['rates']['rates_id']} sha256={ledger['rates']['content_sha256']}"
    )
    lines.append(f"complete={ledger['complete']}")
    for component in COMPONENTS:
        entry = ledger["components"][component]
        notes = ",".join(entry["notes"])
        reason = entry.get("incomplete_reason") or "none"
        lines.append(
            f"component {component}: cost_usd={_fmt(entry['cost_usd'])}"
            f" status={entry['cost_status']}"
            f" qty={_fmt(entry['quantity_value'])} {entry['quantity_unit']}"
            f" notes=[{notes}] reason={reason}"
        )
    for period in ("one_time", "per_month", "query_window"):
        period_totals = ledger["totals"][period]
        known = _fmt_quotient(period_totals["known_usd"], period_totals["complete"])
        incomplete = ",".join(period_totals["incomplete_components"])
        line = (
            f"total {period}: known_usd={known}"
            f" complete={period_totals['complete']} incomplete_components=[{incomplete}]"
        )
        if period == "query_window":
            # r5: only this total can carry a typed reason (the queries
            # window being absent) and the line ends with it; the other
            # totals' lines are unchanged.
            reason = (
                period_totals["reason"]
                if period_totals["reason"] is not None
                else "none"
            )
            line = f"{line} reason={reason}"
        lines.append(line)
    for key in _DENOMINATOR_KEYS:
        entry = ledger["per_unit"][key]
        denominator = ledger["denominators"][key]["value"]
        denominator_text = "UNMEASURED" if denominator is None else str(denominator)
        reason = entry["reason"] if entry["reason"] is not None else "none"
        # Only the groups in the entry's basis print: a group the quotient
        # never divides is not an UNMEASURED measurement, and printing it
        # as one would read as a missing measurement.  (The JSON output is
        # unchanged — a non-applicable group stays null there.)
        quotient_tokens = []
        for period in entry["basis"]:
            value = entry[f"{period}_usd"]
            period_complete = ledger["totals"][period]["complete"]
            quotient_tokens.append(
                f"{period}_usd={_fmt_quotient(value, period_complete)}"
            )
        lines.append(
            f"per_unit {key}: denominator={denominator_text}"
            f" {' '.join(quotient_tokens)}"
            f" complete={entry['complete']} reason={reason}"
        )
    burden = ledger["operator_burden"]
    window = burden["window"]
    window_text = "none" if window is None else f"{window['first']}..{window['last']}"
    lines.append(
        f"operator_burden: status={burden['status']}"
        f" minutes_total={_fmt(burden['minutes_total'])}"
        f" events={burden['events']} window={window_text}"
    )
    lines.append(
        f"operator_burden by_act_kind={burden['by_act_kind']}"
        f" by_actor_role={burden['by_actor_role']}"
    )
    design = ledger.get("design_comparison")
    if design:
        six_ratio = _fmt(design["deep_six_role_ratio_to_design"])
        fleet_ratio = _fmt(design["cold_deep_gets_ratio_receipt_to_design"])
        lines.append(
            "design_comparison:"
            f" deep_fleet_design_bytes={design['deep_fleet_design_bytes']}"
            f" deep_six_role_bytes_measured={design['deep_six_role_bytes_measured']}"
            f" six_role_ratio_to_design={six_ratio}"
            f" deep_all_member_bytes_measured={design['deep_all_member_bytes_measured']}"
            f" cold_deep_gets_design={design['cold_deep_gets_design']}"
            f" cold_deep_gets_receipt_estimate={design['cold_deep_gets_receipt_estimate']}"
            f" cold_deep_gets_ratio_receipt_to_design={fleet_ratio}"
        )
    return "\n".join(lines)
