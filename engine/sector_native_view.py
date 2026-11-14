"""Pure Sector core/history/Brief/action-board projection for a selected runtime generation.

The caller supplies one verified, coherent input set and performs authorization.
This module never loads data, reads configuration, takes the current time, grades
calls, or changes a publication pointer. It does not infer freshness from a poll.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
import re
from typing import Any, Literal
from urllib.parse import urlsplit

from lib.sector_action_preview import _ACTNOW_LANES, partition_actnow
from lib.sector_history_contract import (
    RS_HISTORY_HORIZONS, RS_HISTORY_MAX_POINTS, RS_HISTORY_MODE, RS_HISTORY_SCHEMA,
)

MAX_VIEW_BYTES = 4 * 1024 * 1024
# These are explicit bounds of the native representation, not a new source cohort.
MAX_CORE_SECTORS = 100
MAX_HISTORY_TURNS = 256
_SECTOR_ID = re.compile(r"[a-z][a-z0-9_-]{0,79}\Z")
_SECTOR_TICKER = re.compile(r"[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)?\Z")
_MEASURED_READ_SCHEMA = "leadership_rotation_context.measured_group_read/v1"
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_GROUP_FIELDS = (
    "id", "name", "name_zh", "category", "health", "desk_score", "breadth",
    "r10", "alloc_rank", "val_state", "label", "reco",
)
_ROW_FIELDS = (
    "kind", "ticker", "slug", "name", "name_zh", "reco", "label", "label_zh",
    "score", "alloc_rank", "above_trend", "eligible", "durability", "book_wt",
    "validated", "signal_grade", "clean_entry", "clean_quality", "perf_20d_rel",
    "breadth_pct50", "top_members", "rollover_band", "rollover_band_zh",
    "reco_why_en", "reco_why_zh", "rs_pctile", "flip_distance",
)
_FACTOR_FIELDS = ("chip_en", "chip_zh", "tip_en", "tip_zh", "tone")
# The optional dated sector dossier is display-only evidence over the frozen
# eleven-identity native cohort. Its owner is the leadership rotation producer;
# this module only projects an accepted packet and never composes one.
_DOSSIER_SCHEMA = "leadership_rotation_context.sector_dossiers/v1"
_DOSSIER_COHORT_ID = "us_sectors_11"
_DOSSIER_POPULATION = "eleven_sector_etf_proxies"
# The closed v1 owner attributes exactly one source family for this dossier.
_DOSSIER_SOURCE_ROOT = "engine.sector_cycles"
_DOSSIER_UNITS = "pct"
_DOSSIER_WINDOWS = (21, 63)
_DOSSIER_UNAVAILABLE_WINDOWS = (5, 20)
# The native cohort identities in the owner's native order. This is a frozen
# contract of eleven sector ETF proxies, not a new cohort and not a data load.
_DOSSIER_GROUP_IDS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE",
                      "XLU", "XLV", "XLY")
_DOSSIER_AUTHORITY_FLAGS = ("may_rank", "may_gate", "may_size", "may_trade",
                            "may_escalate")
_MAX_DOSSIER_GROUPS = 11
_MAX_DOSSIER_LIST = 64
_MAX_DOSSIER_TEXT = 160
# The owner's dossier producer bounds its own input at 128 rows. The malformed
# counts it publishes are over THAT bound, not over the eleven-identity output
# cohort, so a genuine packet may carry more malformed rows than the cohort
# has members.
_MAX_DOSSIER_INPUT_ROWS = 128
# The owner publishes at most eleven outside-cohort identities.
_MAX_DOSSIER_OUTSIDE = 11
# The owner's own bounded identity form, used for a cohort member and for an
# outsider alike. It is the owner's shape, not a new registry.
_DOSSIER_IDENTITY = re.compile(r"[A-Z][A-Z0-9]{0,7}\Z")
# The one qualification string this projection recognises by name: the owner
# marks a row whose identity appeared more than once in its own input.
_DOSSIER_DUPLICATE_REASON = "duplicate_group_identity"


class SectorViewUnavailable(ValueError):
    """A safe, closed reason code; never attach input or private manifest data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SectorViewReceipt:
    """Already-qualified public identity, supplied by the publication adapter."""

    generation_id: str
    source_session: str
    published_at: str
    qualification: Literal["accepted", "stale", "degraded"]
    input_version: str
    # Explicit migration baseline, never inferred from an older secondary file.
    baseline_session: str | None = None


@dataclass(frozen=True)
class SectorViewInputs:
    central: dict[str, Any]
    cycles: dict[str, Any]
    baskets: dict[str, Any]
    handoff: dict[str, Any]
    action_board: dict[str, Any]


def _session(value: Any) -> str:
    if not isinstance(value, str):
        raise SectorViewUnavailable("invalid_source_session")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        raise SectorViewUnavailable("invalid_source_session") from None
    return value


def _pick(doc: dict, keys: tuple[str, ...]) -> dict:
    result = {}
    for key in keys:
        if key not in doc:
            continue
        value = doc[key]
        # Native fields are scalar, except the existing top-members string list.
        # An unexpected nested object must not smuggle source/private metadata.
        if key == "top_members":
            if value is not None and (not isinstance(value, list)
                                      or any(not isinstance(v, str) for v in value)):
                raise SectorViewUnavailable("invalid_projection_value")
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise SectorViewUnavailable("invalid_projection_value")
        result[key] = deepcopy(value)
    return result


def _receipt(receipt: SectorViewReceipt) -> tuple[dict, str]:
    if not isinstance(receipt, SectorViewReceipt):
        raise SectorViewUnavailable("invalid_receipt")
    for token in (receipt.generation_id, receipt.input_version):
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise SectorViewUnavailable("invalid_receipt")
    source = _session(receipt.source_session)
    baseline = _session(receipt.baseline_session) if receipt.baseline_session else source
    if baseline > source:
        raise SectorViewUnavailable("future_baseline")
    if receipt.qualification not in ("accepted", "stale", "degraded"):
        raise SectorViewUnavailable("invalid_qualification")
    try:
        published = datetime.fromisoformat(receipt.published_at.replace("Z", "+00:00"))
        if published.tzinfo is None or published.utcoffset() is None:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise SectorViewUnavailable("invalid_publication_clock") from None
    return {
        "schema": "sector_native_view.receipt.v1",
        "source": "macro.sector",
        "generation_id": receipt.generation_id,
        "source_session": source,
        "published_at": receipt.published_at,
        "qualification": receipt.qualification,
        "input_version": receipt.input_version,
        "baseline_session": baseline if baseline != source else None,
    }, baseline


def build_brief_series(subject_id: str | None, chart: Any) -> dict | None:
    """The existing Brief's 21 matched observations / 20-session relative wealth.

    Equivalent to templates/_sector_central_brief.js.j2::buildSectorBriefSeries;
    this is a presentation projection of accepted levels, not a new signal.
    """
    if not isinstance(subject_id, str) or not subject_id or not isinstance(chart, dict):
        return None
    dates, benchmark = chart.get("dates"), chart.get("bench")
    baskets = chart.get("baskets")
    values = baskets.get(subject_id) if isinstance(baskets, dict) else None
    if not all(isinstance(v, list) for v in (dates, benchmark, values)):
        return None
    if len(dates) < 21 or len(values) != len(dates) or len(benchmark) != len(dates):
        return None
    dates, values, benchmark = dates[-21:], values[-21:], benchmark[-21:]
    previous = None
    for observed, value, bench in zip(dates, values, benchmark):
        try:
            _session(observed)
        except SectorViewUnavailable:
            return None
        if previous is not None and observed <= previous:
            return None
        previous = observed
        for number in (value, bench):
            if (isinstance(number, bool) or not isinstance(number, (int, float))
                    or not math.isfinite(number) or number <= 0):
                return None
    points = [
        {"date": observed, "value": ((value / values[0]) / (bench / benchmark[0]) - 1) * 100}
        for observed, value, bench in zip(dates, values, benchmark)
    ]
    if any(not math.isfinite(point["value"]) for point in points):
        return None
    return {
        "points": points, "start": dates[0], "end": dates[-1],
        "sessions": 20, "value": points[-1]["value"],
    }


def _safe_href(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 1024:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (parsed.scheme or parsed.netloc or value.startswith("//")
            or "\\" in value or any(part in (".", "..") for part in parsed.path.split("/"))
            or not parsed.path.endswith(".html")):
        return None
    return value


def _board(board: Any, *, audience: str, preview_rows: int) -> dict:
    if not isinstance(board, dict):
        raise SectorViewUnavailable("invalid_action_board")
    for lane, _, _ in _ACTNOW_LANES:
        rows = board.get(lane, [])
        if (not isinstance(rows, list) or len(rows) > 10000
                or any(not isinstance(row, dict) for row in rows)):
            raise SectorViewUnavailable("invalid_action_board")
    lanes, total, withheld_total = {}, 0, 0
    # All slicing comes from the builder's canonical partition, including the
    # shared hold/avoid budget. Unknown top-level fields never bypass the split.
    for key, _, _, preview, withheld in partition_actnow(board, preview_rows):
        total += len(preview) + len(withheld)
        rows = preview + withheld if audience == "entitled" else preview
        visible = []
        for row in rows:
            item = _pick(row, _ROW_FIELDS)
            href = _safe_href(row.get("href"))
            if href is not None:
                item["href"] = href
            visible.append(item)
        hidden = 0 if audience == "entitled" else len(withheld)
        withheld_total += hidden
        lanes[key] = {"rows": visible, "total": len(preview) + len(withheld), "locked": hidden}
    return {"lanes": lanes, "total": total, "locked": withheld_total}


def _typed_fields(doc: Any, *, strings=(), numbers=(), booleans=(), code: str) -> dict:
    """Copy only the declared nullable fields; no coercion or zero substitution."""
    if not isinstance(doc, dict):
        raise SectorViewUnavailable(code)
    out = {}
    for keys, expected in ((strings, str), (numbers, (int, float)), (booleans, bool)):
        for key in keys:
            if key not in doc:
                continue
            value = doc[key]
            if value is not None:
                if not isinstance(value, expected):
                    raise SectorViewUnavailable(code)
                if expected == (int, float) and (isinstance(value, bool) or not math.isfinite(value)):
                    raise SectorViewUnavailable(code)
            out[key] = value
    return out


def _sector_identity(row: Any, code: str) -> tuple[str, str]:
    if (not isinstance(row, dict) or row.get("kind") != "sector"
            or not isinstance(row.get("id"), str) or not _SECTOR_ID.fullmatch(row["id"])
            or not isinstance(row.get("ticker"), str)
            or not _SECTOR_TICKER.fullmatch(row["ticker"])):
        raise SectorViewUnavailable(code)
    return row["id"], row["ticker"]


def _bounded_records(value: Any, limit: int, code: str) -> list:
    if (not isinstance(value, list) or len(value) > limit
            or any(not isinstance(row, dict) for row in value)):
        raise SectorViewUnavailable(code)
    return value


def _dossier_text(value: Any, code: str) -> str:
    """A bounded, printable owner string; never echoes the input back."""
    if (not isinstance(value, str) or not value or len(value) > _MAX_DOSSIER_TEXT
            or any(ord(char) < 32 for char in value)):
        raise SectorViewUnavailable(code)
    return value


def _dossier_optional_text(value: Any, code: str) -> str | None:
    return None if value is None else _dossier_text(value, code)


def _dossier_number(value: Any, code: str) -> int | float:
    """A finite, non-boolean relative-wealth percentage inside its domain."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SectorViewUnavailable(code)
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise SectorViewUnavailable(code) from None
    # Nonnegative group wealth over positive benchmark wealth cannot produce a
    # relative-wealth percentage below -100.
    if not math.isfinite(number) or number < -100.0:
        raise SectorViewUnavailable(code)
    return value


def _dossier_unavailable_block(doc: Any, code: str) -> dict:
    """A stated limitation: unavailable status plus its bounded reason."""
    if not isinstance(doc, dict) or doc.get("status") != "unavailable":
        raise SectorViewUnavailable(code)
    return {"status": "unavailable", "reason": _dossier_text(doc.get("reason"), code)}


def _sector_dossiers(value: Any, parent: dict, source: str,
                     parent_ids: set[str]) -> dict:
    """Project the optional dated dossier carried inside a measured read.

    The dossier is display-only evidence over the frozen eleven-identity sector
    cohort. It never ranks, gates, sizes or trades, and it never completes a
    missing measurement: unavailable rows keep their own null reasons instead of
    being filled from the outer receipt or from another generation. A present but
    malformed packet fails closed; an absent packet stays absent.
    """
    code = "invalid_sector_dossiers"
    binding = "mixed_sector_dossier_binding"
    identity = "invalid_sector_dossier_identity"
    if not isinstance(value, dict) or value.get("schema") != _DOSSIER_SCHEMA:
        raise SectorViewUnavailable(code)
    generation = parent.get("generation")
    cohort = parent.get("cohort")
    if not isinstance(generation, dict) or not isinstance(cohort, dict):
        raise SectorViewUnavailable(code)
    # Fixed contract claims: the cohort, its population, the units and the
    # existing 21/63 session windows. The 5/20 windows stay explicitly absent.
    if (value.get("cohort_id") != _DOSSIER_COHORT_ID
            or value.get("population") != _DOSSIER_POPULATION
            or value.get("units") != _DOSSIER_UNITS
            or value.get("windows_sessions") != list(_DOSSIER_WINDOWS)):
        raise SectorViewUnavailable(code)
    unavailable_windows = value.get("unavailable_windows")
    if (not isinstance(unavailable_windows, dict)
            or unavailable_windows.get("sessions") != list(_DOSSIER_UNAVAILABLE_WINDOWS)
            or unavailable_windows.get("reason") != "not_supplied_by_owner"):
        raise SectorViewUnavailable(code)

    # --- parent bindings -------------------------------------------------------
    # The dossier is a child of this measured read, so it must agree with the
    # bindings the parent actually makes available.
    parent_cohort_id = generation.get("cohort_id")
    if isinstance(parent_cohort_id, str) and parent_cohort_id != value["cohort_id"]:
        raise SectorViewUnavailable(binding)
    if value.get("benchmark") != generation.get("benchmark"):
        raise SectorViewUnavailable(binding)
    # The compatibility key is a compatibility key, not an immutable generation
    # identity: it is checked against the parent here and never promoted below.
    if value.get("compatibility_key") != generation.get("id"):
        raise SectorViewUnavailable(binding)
    price_basis = value.get("price_basis")
    if price_basis is not None:
        if price_basis != "total_return":
            raise SectorViewUnavailable(code)
        parent_basis = generation.get("price_basis")
        if isinstance(parent_basis, str) and parent_basis != price_basis:
            raise SectorViewUnavailable(binding)
    as_of = value.get("as_of")
    if as_of is not None:
        if not isinstance(as_of, str):
            raise SectorViewUnavailable(code)
        # An unavailable clock stays unavailable; it is never filled from the
        # outer receipt or promoted to this generation.
        if as_of != source:
            raise SectorViewUnavailable(binding)

    # --- groups ----------------------------------------------------------------
    rows = _bounded_records(value.get("groups"), _MAX_DOSSIER_LIST, code)
    if len(rows) != _MAX_DOSSIER_GROUPS:
        raise SectorViewUnavailable(identity)
    projected, identities = [], []
    for row, expected_id in zip(rows, _DOSSIER_GROUP_IDS):
        group_id = row.get("group_id")
        if not isinstance(group_id, str) or not _SECTOR_TICKER.fullmatch(group_id):
            raise SectorViewUnavailable(identity)
        # Every native identity is present exactly once, in the native order.
        if group_id != expected_id:
            raise SectorViewUnavailable(identity)
        identities.append(group_id)
        relative = row.get("relative_wealth_pct")
        null_reasons = row.get("null_reasons")
        if not isinstance(relative, dict) or not isinstance(null_reasons, dict):
            raise SectorViewUnavailable(code)
        values, reasons = {}, {}
        for sessions in _DOSSIER_WINDOWS:
            field = f"rs_{sessions}d"
            if field not in relative or field not in null_reasons:
                raise SectorViewUnavailable(code)
            number, reason = relative[field], null_reasons[field]
            if number is None:
                if not isinstance(reason, str) or not reason or len(reason) > _MAX_DOSSIER_TEXT:
                    raise SectorViewUnavailable(code)
                values[field], reasons[field] = None, reason
            else:
                if reason is not None:
                    raise SectorViewUnavailable(code)
                values[field] = _dossier_number(number, code)
                reasons[field] = None
        present = sum(1 for number in values.values() if number is not None)
        status = ("available" if present == len(_DOSSIER_WINDOWS)
                  else "partial" if present else "unavailable")
        if row.get("status") != status:
            raise SectorViewUnavailable(code)
        qualification = row.get("qualification_reasons")
        if (not isinstance(qualification, list) or len(qualification) > _MAX_DOSSIER_LIST
                or any(not isinstance(item, str) or not item
                       or len(item) > _MAX_DOSSIER_TEXT for item in qualification)):
            raise SectorViewUnavailable(code)
        projected.append({
            "group_id": group_id,
            "name_en": _dossier_optional_text(row.get("name_en"), code),
            "name_zh": _dossier_optional_text(row.get("name_zh"), code),
            "status": status,
            "relative_wealth_pct": values,
            "null_reasons": reasons,
            "qualification_reasons": list(qualification),
        })
    # Every dossier row must have an available parent binding.
    if set(identities) != parent_ids:
        raise SectorViewUnavailable(binding)

    # --- measured value binding to the same parent group ------------------------
    # The owner emits a non-null child measurement only when it equals the
    # measured read of the SAME parent group in the SAME window. A child that
    # detaches from its own group, or that publishes a value where that group
    # has none, is refused. A withheld child null stays null: the owner can
    # qualify more strictly than the parent, and the projector never completes
    # a missing measurement.
    parent_current = {}
    for row in parent.get("groups") or ():
        if isinstance(row, dict) and isinstance(row.get("group_id"), str):
            parent_current[row["group_id"]] = row.get("current")
    for group in projected:
        current = parent_current.get(group["group_id"])
        current = current if isinstance(current, dict) else {}
        for sessions in _DOSSIER_WINDOWS:
            field = f"rs_{sessions}d"
            child = group["relative_wealth_pct"][field]
            if child is None:
                # A withheld child value is never completed from the parent.
                continue
            owner = current.get(field)
            if (isinstance(owner, bool) or not isinstance(owner, (int, float))
                    or owner != child):
                raise SectorViewUnavailable(binding)

    # --- counts, status and value consistency ----------------------------------
    counts = value.get("cross_sector_breadth_counts")
    if not isinstance(counts, dict) or set(counts) != {str(s) for s in _DOSSIER_WINDOWS}:
        raise SectorViewUnavailable(code)
    projected_counts = {}
    for sessions in _DOSSIER_WINDOWS:
        block = counts[str(sessions)]
        if not isinstance(block, dict):
            raise SectorViewUnavailable(code)
        field = f"rs_{sessions}d"
        valid = [group["relative_wealth_pct"][field] for group in projected
                 if group["relative_wealth_pct"][field] is not None]
        expected_n, measured_n = block.get("expected_n"), block.get("measured_n")
        positive_n = block.get("positive_n")
        if (type(expected_n) is not int or type(measured_n) is not int
                or not 0 <= measured_n <= expected_n <= _MAX_DOSSIER_GROUPS
                or expected_n != _MAX_DOSSIER_GROUPS or measured_n != len(valid)):
            raise SectorViewUnavailable(code)
        positive = sum(1 for number in valid if number > 0) if valid else None
        if positive is None:
            if positive_n is not None:
                raise SectorViewUnavailable(code)
        elif type(positive_n) is not int or positive_n != positive:
            raise SectorViewUnavailable(code)
        projected_counts[str(sessions)] = {
            "expected_n": expected_n, "measured_n": measured_n, "positive_n": positive_n,
        }
    any_values = any(group["relative_wealth_pct"][f"rs_{sessions}d"] is not None
                     for group in projected for sessions in _DOSSIER_WINDOWS)
    if value.get("status") != ("partial" if any_values else "unavailable"):
        raise SectorViewUnavailable(code)
    all_available = all(group["status"] == "available" for group in projected)
    measurement_status = ("available" if all_available
                          else "partial" if any_values else "unavailable")
    if value.get("measurement_status") != measurement_status:
        raise SectorViewUnavailable(code)

    # --- authority, forecasts and stated limitations ---------------------------
    authority = value.get("authority")
    if (not isinstance(authority, dict)
            or set(authority) != set(_DOSSIER_AUTHORITY_FLAGS)):
        raise SectorViewUnavailable(code)
    if any(authority[flag] is not False for flag in _DOSSIER_AUTHORITY_FLAGS):
        raise SectorViewUnavailable(code)
    forecasts = value.get("forecasts")
    if (not isinstance(forecasts, dict)
            or set(forecasts) != {"status", "expected_return", "persistence_estimate",
                                  "allocation_weight"}
            or forecasts.get("status") != "not_qualified"):
        raise SectorViewUnavailable(code)
    if any(forecasts[key] is not None for key in
           ("expected_return", "persistence_estimate", "allocation_weight")):
        raise SectorViewUnavailable(code)
    history = value.get("history")
    if (not isinstance(history, dict) or history.get("mode") != "reconstructed_price_history"
            or history.get("naturally_observed") is not False):
        raise SectorViewUnavailable(code)
    freshness = value.get("freshness")
    if not isinstance(freshness, dict) or freshness.get("status") != "unverified":
        raise SectorViewUnavailable(code)
    corrections = value.get("corrections")
    if not isinstance(corrections, dict) or corrections.get("status") != "unavailable":
        raise SectorViewUnavailable(code)
    source_generation = value.get("source_generation")
    if (not isinstance(source_generation, dict)
            or source_generation.get("status") != "unavailable"
            or source_generation.get("id") is not None):
        raise SectorViewUnavailable(code)
    availability = value.get("availability")
    if not isinstance(availability, dict):
        raise SectorViewUnavailable(code)
    mode = availability.get("mode")
    if mode not in ("as_known", "dated_snapshot"):
        raise SectorViewUnavailable(code)
    cutoff = availability.get("decision_cutoff")
    if cutoff is not None:
        cutoff = _dossier_text(cutoff, code)
        try:
            parsed = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        except ValueError:
            raise SectorViewUnavailable(code) from None
        if parsed.tzinfo is None:
            raise SectorViewUnavailable(code)
    # The original availability clock is never filled from the outer receipt and
    # a dated snapshot is never promoted to historical admissibility.
    if (availability.get("original_available_at") is not None
            or availability.get("historically_admissible") is not False):
        raise SectorViewUnavailable(code)
    # --- owner qualification invariants ----------------------------------------
    # The owner withholds EVERY measurement whenever its own qualification
    # reasons are non-empty. A dated snapshot carries no decision cutoff, and
    # an as-known request always withholds because the original availability
    # clock is not supplied. A packet that contradicts its own stated
    # availability cannot keep a superficially valid status.
    if mode == "as_known":
        if any_values:
            raise SectorViewUnavailable(code)
    elif cutoff is not None:
        raise SectorViewUnavailable(code)
    if any_values:
        # A measured packet is a qualified one: the owner withholds every
        # value unless the return basis and the dated clock are supplied.
        if price_basis != "total_return":
            raise SectorViewUnavailable(code)
        if as_of is None:
            raise SectorViewUnavailable(code)
        if generation.get("price_basis") != "total_return":
            raise SectorViewUnavailable(binding)
    audit = value.get("dependency_audit")
    if not isinstance(audit, dict):
        raise SectorViewUnavailable(code)
    roots = audit.get("source_roots")
    if (not isinstance(roots, list) or len(roots) > _MAX_DOSSIER_LIST
            or any(not isinstance(root, str) or not root
                   or len(root) > _MAX_DOSSIER_TEXT for root in roots)):
        raise SectorViewUnavailable(code)
    family_count = audit.get("source_family_count")
    if type(family_count) is not int or not 0 <= family_count <= _MAX_DOSSIER_LIST:
        raise SectorViewUnavailable(code)
    # The closed v1 owner attributes exactly one source family, or none. It
    # never names a second lineage owner and never counts the same one twice.
    if list(roots) == [_DOSSIER_SOURCE_ROOT]:
        expected_families = 1
    elif not roots:
        expected_families = 0
    else:
        raise SectorViewUnavailable(code)
    if family_count != expected_families:
        raise SectorViewUnavailable(code)
    if (audit.get("independence") != "not_established"
            or audit.get("shared_rolling_windows") is not True):
        raise SectorViewUnavailable(code)
    if not roots and any_values:
        # Without an attributed source root the owner withholds every
        # measurement, so a measured packet cannot claim an unattributed one.
        raise SectorViewUnavailable(code)
    diagnostics = value.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise SectorViewUnavailable(code)
    listed = {}
    for key in ("qualification_reasons", "duplicate_groups", "outside_cohort"):
        items = diagnostics.get(key)
        if (not isinstance(items, list) or len(items) > _MAX_DOSSIER_LIST
                or any(not isinstance(item, str) or not item
                       or len(item) > _MAX_DOSSIER_TEXT for item in items)):
            raise SectorViewUnavailable(code)
        listed[key] = list(items)
    malformed = {}
    for key in ("malformed_source_rows", "malformed_measured_rows"):
        count = diagnostics.get(key)
        # The owner counts malformed rows over ITS OWN input bound of 128, not
        # over the eleven-identity output cohort. The count is a plain integer
        # in 0..128 (a boolean is not an integer here). A positive count does
        # not withhold the valid native measurements by itself.
        if type(count) is not int or not 0 <= count <= _MAX_DOSSIER_INPUT_ROWS:
            raise SectorViewUnavailable(code)
        malformed[key] = count

    # --- owner qualification and diagnostic relationships -----------------------
    # The owner withholds every measurement of a row whenever that row carries
    # a qualification reason, and it withholds every row whenever the packet
    # carries a global qualification reason. A global reason also occurs in
    # EVERY row's own qualification list.
    global_reasons = listed["qualification_reasons"]
    if len(set(global_reasons)) != len(global_reasons):
        raise SectorViewUnavailable(code)
    global_set = set(global_reasons)
    if global_set:
        # A global qualification withholds EVERY child measurement.
        if any(group["relative_wealth_pct"][f"rs_{sessions}d"] is not None
               for group in projected for sessions in _DOSSIER_WINDOWS):
            raise SectorViewUnavailable(code)
    for group in projected:
        qualification = group["qualification_reasons"]
        # The owner publishes each ROW's own qualification list sorted and
        # unique. The GLOBAL list is published in the owner's construction
        # order and is not sorted, so only its uniqueness is required here.
        if (len(set(qualification)) != len(qualification)
                or qualification != sorted(qualification)):
            raise SectorViewUnavailable(code)
        if not global_set.issubset(qualification):
            raise SectorViewUnavailable(code)
        if not qualification:
            # An unqualified row may still miss one window on its own. The
            # projector never completes it from the parent and never requires
            # its two window reasons to agree.
            continue
        values = [group["relative_wealth_pct"][f"rs_{sessions}d"]
                  for sessions in _DOSSIER_WINDOWS]
        if any(value is not None for value in values):
            raise SectorViewUnavailable(code)
        reasons = [group["null_reasons"][f"rs_{sessions}d"]
                   for sessions in _DOSSIER_WINDOWS]
        # One reason for both windows, and it belongs to this row's own list.
        # The owner chose that reason in construction order and published the
        # list sorted, so the first published reason is not necessarily the
        # one the owner withheld with.
        if (reasons[0] != reasons[1] or reasons[0] not in qualification
                or (global_reasons and reasons[0] != global_reasons[0])):
            raise SectorViewUnavailable(code)

    # --- duplicate identity relationship ----------------------------------------
    # The owner publishes the identities it read more than once and withholds
    # each of them with its duplicate reason. A listed identity and a row that
    # carries that reason are the same fact, in both directions.
    duplicate_groups = listed["duplicate_groups"]
    if (len(set(duplicate_groups)) != len(duplicate_groups)
            or duplicate_groups != sorted(duplicate_groups)
            or any(ident not in _DOSSIER_GROUP_IDS for ident in duplicate_groups)):
        raise SectorViewUnavailable(code)
    duplicate_set = set(duplicate_groups)
    for group in projected:
        qualified = _DOSSIER_DUPLICATE_REASON in group["qualification_reasons"]
        if group["group_id"] in duplicate_set:
            # A listed identity is fully withheld and carries the owner's
            # duplicate reason. Its null reason need not be that reason: an
            # earlier global reason can be the common cause.
            if not qualified:
                raise SectorViewUnavailable(code)
            if any(group["relative_wealth_pct"][f"rs_{sessions}d"] is not None
                   for sessions in _DOSSIER_WINDOWS):
                raise SectorViewUnavailable(code)
        elif qualified:
            raise SectorViewUnavailable(code)

    # --- outside cohort relationship --------------------------------------------
    # The owner publishes the identities it read outside the native cohort.
    outside_cohort = listed["outside_cohort"]
    if (len(set(outside_cohort)) != len(outside_cohort)
            or outside_cohort != sorted(outside_cohort)
            or len(outside_cohort) > _MAX_DOSSIER_OUTSIDE):
        raise SectorViewUnavailable(code)
    for ident in outside_cohort:
        # An outside identity is never a native cohort identity and carries the
        # owner's own bounded identity form. A contradictory identity is
        # refused: it is never normalised and never promoted into the cohort.
        if ident in _DOSSIER_GROUP_IDS or not _DOSSIER_IDENTITY.fullmatch(ident):
            raise SectorViewUnavailable(code)

    mechanism = value.get("mechanism")
    if not isinstance(mechanism, dict) or mechanism.get("status") != "unavailable":
        raise SectorViewUnavailable(code)
    risk = value.get("risk")
    if (not isinstance(risk, dict) or risk.get("status") != "unavailable"
            or risk.get("scope") is not None):
        raise SectorViewUnavailable(code)

    return {
        "schema": _DOSSIER_SCHEMA,
        "status": "partial" if any_values else "unavailable",
        "measurement_status": measurement_status,
        "cohort_id": _DOSSIER_COHORT_ID,
        "population": _DOSSIER_POPULATION,
        "as_of": as_of,
        "benchmark": value.get("benchmark"),
        "price_basis": price_basis,
        "units": _DOSSIER_UNITS,
        "windows_sessions": list(_DOSSIER_WINDOWS),
        "unavailable_windows": {
            "sessions": list(_DOSSIER_UNAVAILABLE_WINDOWS),
            "reason": "not_supplied_by_owner",
        },
        "absolute_returns": _dossier_unavailable_block(value.get("absolute_returns"), code),
        "compatibility_key": _dossier_optional_text(value.get("compatibility_key"), code),
        "source_generation": {
            "status": "unavailable",
            "reason": _dossier_text(source_generation.get("reason"), code),
            "id": None,
        },
        "availability": {
            "mode": mode,
            "decision_cutoff": cutoff,
            "original_available_at": None,
            "historically_admissible": False,
            "reason": _dossier_text(availability.get("reason"), code),
        },
        "history": {"mode": "reconstructed_price_history", "naturally_observed": False},
        "freshness": {
            "status": "unverified",
            "reason": _dossier_text(freshness.get("reason"), code),
        },
        "corrections": {
            "status": "unavailable",
            "reason": _dossier_text(corrections.get("reason"), code),
        },
        "authority": {flag: False for flag in _DOSSIER_AUTHORITY_FLAGS},
        "forecasts": {
            "status": "not_qualified", "expected_return": None,
            "persistence_estimate": None, "allocation_weight": None,
        },
        "mechanism": {
            "status": "unavailable",
            "reason": _dossier_text(mechanism.get("reason"), code),
            "owner": _dossier_optional_text(mechanism.get("owner"), code),
        },
        "risk": {
            "status": "unavailable",
            "reason": _dossier_text(risk.get("reason"), code),
            "owner": _dossier_optional_text(risk.get("owner"), code),
            "scope": None,
        },
        "constituent_breadth": _dossier_unavailable_block(
            value.get("constituent_breadth"), code),
        "constituent_concentration": _dossier_unavailable_block(
            value.get("constituent_concentration"), code),
        "cross_sector_breadth_counts": projected_counts,
        "dependency_audit": {
            "source_roots": list(roots),
            "source_family_count": family_count,
            "independence": "not_established",
            "shared_rolling_windows": True,
            "constituent_overlap": _dossier_text(audit.get("constituent_overlap"), code),
        },
        "diagnostics": {
            "qualification_reasons": listed["qualification_reasons"],
            "duplicate_groups": listed["duplicate_groups"],
            "outside_cohort": listed["outside_cohort"],
            "malformed_source_rows": malformed["malformed_source_rows"],
            "malformed_measured_rows": malformed["malformed_measured_rows"],
        },
        "groups": projected,
    }



# Exact-session companion: a bounded native projection of already measured
# values. This owner never imports or calls the measurement producer.
_WINDOW_SCHEMA = "leadership_rotation_context.sector_window_measurements/v1"
_WINDOW_SESSIONS = (5, 20, 63)
_WINDOW_FIELDS = ("absolute_return_pct", "relative_wealth_pct")
_WINDOW_REASONS = frozenset((
    "missing_input", "non_finite_input", "invalid_price", "benchmark_missing",
    "benchmark_invalid", "insufficient_reference_history", "empty_panel",
    "future_tail", "source_session_mismatch", "ambiguous_duplicate_price_index",
    "ambiguous_duplicate_column", "cohort_identity_mismatch",
    "benchmark_identity_mismatch", "return_basis_not_qualified"))
_WINDOW_BLOCKS = _WINDOW_REASONS - {
    "missing_input", "non_finite_input", "invalid_price", "benchmark_missing",
    "benchmark_invalid", "insufficient_reference_history"}
_WINDOW_ENDPOINT = (
    "Endpoint return: P(T)/P(S_N) - 1, where T is the explicit end session and "
    "S_N is the canonical US session exactly N positions before T, so a "
    "5-session return spans 6 session endpoints. Relative wealth is "
    "(1+R_group)/(1+R_benchmark) - 1 -- a wealth ratio, never a return difference. "
    "Interior gaps never move an endpoint; they are disclosed as observed "
    "coverage. Prices are strictly positive, finite, total-return adjusted "
    "closes read at the two endpoints only.")
_WINDOW_COVERAGE_NOTE = (
    "observed_n counts usable observations inside the window; an interior gap "
    "never moves an endpoint")


def _window_json_preflight(value: Any, code: str, *, byte_limit: int,
                           depth_limit: int, node_limit: int) -> None:
    """Bound ordinary JSON before copying or serializing any containing object.

    Count the producer's default ensure_ascii=True encoding, including comma
    and colon spaces. The 256 bound applies to each container's length, not the
    number of containers. Exact builtin types exclude custom conversion/copy
    hooks. Keys contribute bytes; the owner's node budget counts values.
    """
    nodes, encoded = 0, 0
    active: set[int] = set()

    def add(n):
        nonlocal encoded
        encoded += n
        if encoded > byte_limit:
            raise SectorViewUnavailable(code)

    def string_size(text):
        if type(text) is not str or len(text) > byte_limit:
            raise SectorViewUnavailable(code)
        add(2)
        for char in text:
            point = ord(char)
            add(2 if char in '"\\\b\f\n\r\t' else
                6 if point < 32 or 127 <= point <= 65535 else
                12 if point > 65535 else 1)

    def walk(node, depth):
        nonlocal nodes
        nodes += 1
        if nodes > node_limit or depth > depth_limit:
            raise SectorViewUnavailable(code)
        kind = type(node)
        if node is None:
            add(4)
        elif kind is bool:
            add(4 if node else 5)
        elif kind is str:
            string_size(node)
        elif kind in (int, float):
            if kind is int and node.bit_length() > byte_limit * 4:
                raise SectorViewUnavailable(code)
            if kind is float and not math.isfinite(node):
                raise SectorViewUnavailable(code)
            try:
                # Only a bounded primitive, never an unvisited object.
                add(len(json.dumps(node, allow_nan=False)))
            except (ValueError, OverflowError):
                raise SectorViewUnavailable(code) from None
        elif kind in (dict, list):
            if len(node) > 256 or id(node) in active:
                raise SectorViewUnavailable(code)
            active.add(id(node))
            add(2 + max(0, len(node) - 1) * 2)
            try:
                if kind is dict:
                    for key, child in node.items():
                        string_size(key)
                        add(2)
                        walk(child, depth + 1)
                else:
                    for child in node:
                        walk(child, depth + 1)
            finally:
                active.remove(id(node))
        else:
            raise SectorViewUnavailable(code)

    walk(value, 0)


def _window_object(value: Any, keys, code: str) -> dict:
    keys = frozenset(keys.split() if isinstance(keys, str) else keys)
    if type(value) is not dict or len(value) != len(keys) or set(value) != keys:
        raise SectorViewUnavailable(code)
    return value


def _window_text(value: Any, code: str, limit: int = 64) -> str:
    if (type(value) is not str or not value or len(value) > limit
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SectorViewUnavailable(code)
    return value


def _window_date(value: Any, code: str) -> str:
    if type(value) is not str or len(value) != 10:
        raise SectorViewUnavailable(code)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        raise SectorViewUnavailable(code) from None
    return value


def _window_count(value: Any, maximum: int, code: str) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise SectorViewUnavailable(code)
    return value


def _window_coverage(value: Any, expected: int, code: str) -> int:
    _window_object(value, "observed_n expected_n ratio", code)
    observed = _window_count(value["observed_n"], expected, code)
    if type(value["expected_n"]) is not int or value["expected_n"] != expected:
        raise SectorViewUnavailable(code)
    ratio = value["ratio"]
    if (type(ratio) not in (int, float) or not 0 <= ratio <= 1 or not math.isfinite(ratio)
            or abs(ratio - round(observed / expected, 6)) > 1e-9):
        raise SectorViewUnavailable(code)
    return observed


def _window_value_reason(value: Any, reason: Any, code: str) -> bool:
    if value is None:
        if type(reason) is not str or reason not in _WINDOW_REASONS:
            raise SectorViewUnavailable(code)
        return False
    _dossier_number(value, code)
    if reason is not None:
        raise SectorViewUnavailable(code)
    return True


def _sector_window_measurements(value: Any, parent: dict, source: str,
                                parent_ids: set[str]) -> dict:
    code = "invalid_sector_window_measurements"
    # Fixed native payloads fit comfortably within this containing-document
    # budget. Receipt has its stricter independent owner budget below.
    _window_json_preflight(value, code, byte_limit=131072,
                           depth_limit=16, node_limit=8192)
    _window_object(value, (
        "schema status reason units price_basis benchmark cohort_id population "
        "source_session end_session windows_sessions endpoint_definition clocks "
        "source_roots receipt limitations windows groups diagnostics authority"), code)
    if (value["schema"] != _WINDOW_SCHEMA or value["units"] != "pct"
            or value["price_basis"] != "total_return"
            or value["cohort_id"] != _DOSSIER_COHORT_ID
            or value["population"] != _DOSSIER_POPULATION
            or value["windows_sessions"] != list(_WINDOW_SESSIONS)
            or any(type(n) is not int for n in value["windows_sessions"])
            or value["endpoint_definition"] != _WINDOW_ENDPOINT):
        raise SectorViewUnavailable(code)
    end = _window_date(value["end_session"], code)
    if _window_date(value["source_session"], code) != end or end != source:
        raise SectorViewUnavailable(code)
    generation = parent["generation"]
    benchmark = _window_text(value["benchmark"], code)
    if (generation.get("session_end") != end
            or generation.get("cohort_id") != value["cohort_id"]
            or generation.get("price_basis") != value["price_basis"]
            or _window_text(generation.get("benchmark"), code).strip().upper()
            != benchmark.strip().upper()
            or not benchmark.strip()
            or parent_ids != set(_DOSSIER_GROUP_IDS)):
        raise SectorViewUnavailable(code)

    clocks = _window_object(value["clocks"],
        "publication availability correction history", code)
    for clock in clocks.values():
        if clock is None:
            continue
        _window_text(clock, code)
        try:
            parsed = datetime.fromisoformat(clock)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError
        except ValueError:
            raise SectorViewUnavailable(code) from None
    roots = value["source_roots"]
    if type(roots) is not list or len(roots) > 32:
        raise SectorViewUnavailable(code)
    for root in roots:
        _window_text(root, code, 256)
    receipt = value["receipt"]
    if receipt is not None:
        if type(receipt) is not dict or len(receipt) > 32:
            raise SectorViewUnavailable(code)
        _window_json_preflight(receipt, code, byte_limit=16384,
                               depth_limit=8, node_limit=2048)
    limitations = _window_object(value["limitations"],
        "availability publication history corrections freshness point_in_time", code)
    for key in ("availability", "publication", "history"):
        expected = ({"status": "unknown", "reason": f"owner_{key}_clock_not_supplied"}
                    if clocks[key] is None else {"status": "supplied", "clock": clocks[key]})
        if limitations[key] != expected:
            raise SectorViewUnavailable(code)
    for key, status, reason in (
        ("corrections", "unavailable", "native_revision_selection_not_supplied"),
        ("freshness", "unverified", "owner_freshness_receipt_not_supplied"),
        ("point_in_time", "not_qualified", "point_in_time_admission_not_supplied")):
        if limitations[key] != {"status": status, "reason": reason}:
            raise SectorViewUnavailable(code)
    authority = _window_object(value["authority"], _DOSSIER_AUTHORITY_FLAGS, code)
    if any(flag is not False for flag in authority.values()):
        raise SectorViewUnavailable(code)

    diagnostics = _window_object(value["diagnostics"], (
        "panel_rows malformed_rows duplicate_sessions ambiguous_columns columns "
        "binding_keys receipt_withheld future_tail_sessions expected_columns "
        "qualification_reasons measured_cells complete_cells total_cells coverage_note"), code)
    _window_count(diagnostics["panel_rows"], 20000, code)
    _window_count(diagnostics["malformed_rows"], 2**53 - 1, code)
    if (type(diagnostics["receipt_withheld"]) is not bool
            or (diagnostics["receipt_withheld"] and receipt is not None)
            or type(diagnostics["expected_columns"]) is not int
            or diagnostics["expected_columns"] != 12
            or type(diagnostics["total_cells"]) is not int
            or diagnostics["total_cells"] != 33
            or diagnostics["coverage_note"] != _WINDOW_COVERAGE_NOTE):
        raise SectorViewUnavailable(code)
    for key, maximum in (("duplicate_sessions", 16), ("ambiguous_columns", 16),
                         ("columns", 64), ("future_tail_sessions", 16),
                         ("binding_keys", 7), ("qualification_reasons", 8)):
        items = diagnostics[key]
        if type(items) is not list or len(items) > maximum:
            raise SectorViewUnavailable(code)
        for item in items:
            _window_text(item, code)
            if key in ("duplicate_sessions", "future_tail_sessions"):
                _window_date(item, code)
            if key == "future_tail_sessions" and item <= end:
                raise SectorViewUnavailable(code)
        if items != sorted(set(items)):
            raise SectorViewUnavailable(code)
    if not set(diagnostics["binding_keys"]) <= {
            "source_roots", "clocks", "receipt", "cohort_id", "benchmark",
            "source_session", "price_basis"}:
        raise SectorViewUnavailable(code)
    reasons = diagnostics["qualification_reasons"]
    if not set(reasons) <= _WINDOW_BLOCKS:
        raise SectorViewUnavailable(code)
    primary = reasons[0] if reasons else None
    if value["reason"] != primary:
        raise SectorViewUnavailable(code)
    declared_measured = _window_count(diagnostics["measured_cells"], 33, code)
    declared_complete = _window_count(diagnostics["complete_cells"], 33, code)
    windows = _window_object(value["windows"], ("5", "20", "63"), code)
    groups = value["groups"]
    if type(groups) is not list or len(groups) != 11:
        raise SectorViewUnavailable(code)
    for ident, group in zip(_DOSSIER_GROUP_IDS, groups):
        _window_object(group, "group_id name_en name_zh windows", code)
        if group["group_id"] != ident:
            raise SectorViewUnavailable(code)
        for name in ("name_en", "name_zh"):
            if group[name] is not None:
                _window_text(group[name], code, 160)
        _window_object(group["windows"], ("5", "20", "63"), code)

    measured, complete = 0, 0
    for n in _WINDOW_SESSIONS:
        key, expected = str(n), n + 1
        window = _window_object(windows[key], (
            "window_sessions status start_session end_session benchmark_return_pct "
            "benchmark_null_reason benchmark_coverage null_reason"), code)
        if (type(window["window_sessions"]) is not int
                or window["window_sessions"] != n or window["end_session"] != end):
            raise SectorViewUnavailable(code)
        insufficient = window["start_session"] is None
        if not insufficient and _window_date(window["start_session"], code) >= end:
            raise SectorViewUnavailable(code)
        cause = "insufficient_reference_history" if insufficient else primary
        if window["null_reason"] != cause:
            raise SectorViewUnavailable(code)
        benchmark_present = _window_value_reason(window["benchmark_return_pct"],
            window["benchmark_null_reason"], code)
        benchmark_observed = _window_coverage(window["benchmark_coverage"], expected, code)
        if ((benchmark_present and benchmark_observed < 2)
                or (cause is None and window["benchmark_null_reason"] in
                    (_WINDOW_BLOCKS | {"insufficient_reference_history"}))
                or (cause and (benchmark_present or window["benchmark_null_reason"] != cause))
                or (insufficient and benchmark_observed != 0)):
            raise SectorViewUnavailable(code)
        window_measured, window_complete = 0, 0
        for group in groups:
            cell = _window_object(group["windows"][key],
                "status absolute_return_pct relative_wealth_pct null_reasons coverage", code)
            nulls = _window_object(cell["null_reasons"], _WINDOW_FIELDS, code)
            present = [_window_value_reason(cell[field], nulls[field], code)
                       for field in _WINDOW_FIELDS]
            observed = _window_coverage(cell["coverage"], expected, code)
            status = "available" if all(present) else "partial" if any(present) else "unavailable"
            if (cell["status"] != status or (present[1] and not benchmark_present)
                    or (present[1] and not present[0]
                        and nulls["absolute_return_pct"] != "non_finite_input")
                    or (cause is None and any(nulls[f] in
                        (_WINDOW_BLOCKS | {"insufficient_reference_history"}) for f in _WINDOW_FIELDS))
                    or (any(present) and observed < 2)
                    or (cause and (any(present) or any(nulls[f] != cause for f in _WINDOW_FIELDS)))
                    or (insufficient and observed != 0)):
                raise SectorViewUnavailable(code)
            window_measured += int(any(present))
            window_complete += int(all(present))
        status = ("available" if window_complete == 11 else
                  "partial" if window_measured else "unavailable")
        if window["status"] != status:
            raise SectorViewUnavailable(code)
        measured += window_measured
        complete += window_complete
    status = ("unavailable" if primary else "available" if complete == 33 else
              "partial" if measured else "unavailable")
    if (value["status"] != status or declared_measured != measured
            or declared_complete != complete or (primary and measured)):
        raise SectorViewUnavailable(code)
    # These nested windows retain counts from one panel with one end session.
    for short, long, extra in (("5", "20", 15), ("20", "63", 43)):
        if windows[short]["start_session"] is None or windows[long]["start_session"] is None:
            continue
        pairs = [(windows[short]["benchmark_coverage"]["observed_n"],
                  windows[long]["benchmark_coverage"]["observed_n"])]
        pairs.extend((row["windows"][short]["coverage"]["observed_n"],
                      row["windows"][long]["coverage"]["observed_n"]) for row in groups)
        if any(b < a or b - a > extra for a, b in pairs):
            raise SectorViewUnavailable(code)
    # The whole fixed document and opaque receipt have now passed bounded
    # primitive and semantic checks. Preserve owner bytes/values, never repair.
    return deepcopy(value)


def _measured_read(value: Any, source: str) -> dict:
    code = "invalid_measured_read"
    if (not isinstance(value, dict) or value.get("schema") != _MEASURED_READ_SCHEMA
            or value.get("status") not in ("available", "partial", "unavailable")):
        raise SectorViewUnavailable(code)
    out = _typed_fields(value, strings=("schema", "status", "reason"), code=code)
    containers = ("generation", "cohort", "groups")
    if not any(key in value for key in containers):
        # This exact outage stub is emitted by the canonical central adapter.
        if value["status"] != "unavailable" or value.get("reason") != "projection_error":
            raise SectorViewUnavailable(code)
        if "sector_dossiers" in value:
            # A dossier cannot bind to a stub that carries no generation or cohort.
            raise SectorViewUnavailable("invalid_sector_dossiers")
        if "sector_window_measurements" in value:
            raise SectorViewUnavailable("invalid_sector_window_measurements")
        return out
    if not all(key in value for key in containers):
        raise SectorViewUnavailable(code)
    out["generation"] = _typed_fields(value["generation"], strings=("session_end", "benchmark"), code=code)
    out["cohort"] = _typed_fields(value["cohort"], numbers=("expected_n", "measured_n"), code=code)
    if _session(out["generation"].get("session_end")) != source:
        raise SectorViewUnavailable("mixed_measured_session")
    if out["generation"].get("benchmark") != "SPY":
        raise SectorViewUnavailable(code)
    expected, measured = out["cohort"].get("expected_n"), out["cohort"].get("measured_n")
    horizon = value["cohort"].get("horizon")
    if (type(expected) is not int or type(measured) is not int
            or not 0 <= measured <= expected <= MAX_CORE_SECTORS or expected == 0
            or horizon not in ("rs_21d", "rs_63d")):
        raise SectorViewUnavailable(code)
    status = "available" if measured == expected else "partial" if measured else "unavailable"
    if value["status"] != status:
        raise SectorViewUnavailable(code)
    out["groups"], seen, ranks = [], set(), []
    for row in _bounded_records(value["groups"], MAX_CORE_SECTORS, code):
        ident = row.get("group_id")
        if not isinstance(ident, str) or not _SECTOR_TICKER.fullmatch(ident) or ident in seen:
            raise SectorViewUnavailable(code)
        seen.add(ident)
        group = _typed_fields(row, strings=("group_id", "name_en", "name_zh"), code=code)
        current = _typed_fields(row.get("current"), strings=("status", "reason"),
                                numbers=("rank", "rs_21d", "rs_63d"), code=code)
        if current.get("status") == "measured":
            if (type(current.get("rank")) is not int or current["rank"] < 1
                    or current.get(horizon) is None or current.get("reason") is not None):
                raise SectorViewUnavailable(code)
            ranks.append(current["rank"])
        elif current.get("status") == "unmeasured":
            if (current.get("rank") is not None or not current.get("reason")
                    or current.get(horizon) is not None):
                raise SectorViewUnavailable(code)
        else:
            raise SectorViewUnavailable(code)
        group["current"] = current
        out["groups"].append(group)
    if len(seen) != expected or sorted(ranks) != list(range(1, measured + 1)):
        raise SectorViewUnavailable(code)
    if "sector_dossiers" in value:
        # The optional dated dossier is a child of this measured read, so it is
        # checked against the parent that carries it. When it is absent the
        # projected representation stays exactly as it was before.
        out["sector_dossiers"] = _sector_dossiers(
            value["sector_dossiers"], value, source, seen)
    if "sector_window_measurements" in value:
        out["sector_window_measurements"] = _sector_window_measurements(
            value["sector_window_measurements"], value, source, seen)
    if "sector_dossiers" in value or "sector_window_measurements" in value:
        # Keep the already-qualified containing identity for downstream readers.
        # Both optional evidence children bind to this parent. Dropping the
        # metadata for a dossier-only generation makes the browser reject the
        # same packet the native owner accepted. No children preserves old bytes.
        child_code = ("invalid_sector_window_measurements" if "sector_window_measurements" in value
                      else "invalid_sector_dossiers")
        generation = value["generation"]
        for field in ("cohort_id", "price_basis"):
            out["generation"][field] = generation[field]
        if "id" in generation:
            out["generation"]["id"] = (None if generation["id"] is None else
                _window_text(generation["id"], child_code, 160))
        for original, projected in zip(value["groups"], out["groups"]):
            for field, expected in (("group_kind", "sector"),):
                if field in original:
                    if type(original[field]) is not str or original[field] != expected:
                        raise SectorViewUnavailable(child_code)
                    projected[field] = original[field]
            for field, expected in (("metric", "relative_wealth_pct"), ("units", "pct")):
                if field in original["current"]:
                    if (type(original["current"][field]) is not str
                            or original["current"][field] != expected):
                        raise SectorViewUnavailable(child_code)
                    projected["current"][field] = original["current"][field]
    return out


def _dated_context(document: Any) -> dict:
    """Admit the bounded owner addendum without converting it to sector evidence.

    This is transport qualification, not a second explanation engine. The owner
    retains its statements, independent clocks and optional qualified subsections.
    Clock values and the coherence contradiction list are documented opaque JSON;
    their parent shapes are closed and their bytes share the same output budget.
    """
    code = "invalid_sector_dated_context"
    try:
        from engine.sector_dated_context import (
            SCHEMA, SCOPE, STATUSES, SECTION_STATUSES, COMPARISON_IDS, AUTHORITY_FLAGS,
            ATTRIBUTION_KEYS, REASONS, HISTORICAL_REASON,
        )
    except ImportError:
        # The dated owner is a separately integrated dependency. A selected
        # member containing it cannot be admitted without its real contract.
        raise SectorViewUnavailable(code) from None

    def refuse():
        raise SectorViewUnavailable(code)

    # Bound before serialization/deepcopy, including hostile in-process values.
    # Use the owner's actual compact UTF-8 encoding, not ASCII-escaped size.
    stack, active, nodes, size = [(document, 0, False)], set(), 0, 0
    while stack:
        value, depth, exiting = stack.pop()
        if exiting:
            active.remove(id(value))
            continue
        nodes += 1
        if nodes > 16384 or depth > 16:
            refuse()
        if type(value) in (dict, list):
            if id(value) in active or len(value) > 16384 - nodes:
                refuse()
            size += 2 + max(0, len(value) - 1) + (len(value) if type(value) is dict else 0)
            active.add(id(value))
            stack.append((value, depth, True))
            if type(value) is dict:
                if any(type(key) is not str for key in value):
                    refuse()
                children = [part for pair in value.items() for part in pair]
            else:
                children = value
            if len(children) > 16384 - nodes:
                refuse()
            stack.extend((child, depth + 1, False) for child in children)
        elif value is not None and type(value) not in (str, bool, int, float):
            refuse()
        elif type(value) is float and not math.isfinite(value):
            refuse()
        else:
            if type(value) is str and len(value) > 16384:
                refuse()
            try:
                size += len(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                       separators=(",", ":")).encode("utf-8"))
            except (ValueError, TypeError, UnicodeError, OverflowError):
                refuse()
        if size > 16384:
            refuse()
    try:
        encoded = json.dumps(document, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        refuse()
    if len(encoded) > 16384:
        refuse()

    def shape(value, fields, required=()):
        if (type(value) is not dict or set(value) - set(fields)
                or not set(required) <= set(value)):
            refuse()
        for key, item in value.items():
            spec = fields[key]
            if callable(spec):
                spec(item)
            elif spec == "json":
                pass  # Already bounded ordinary finite JSON above.
            elif spec == "texts":
                if type(item) is not list or any(type(v) is not str for v in item):
                    refuse()
            elif spec == "reasons":
                if type(item) is not list or any(type(v) is not str or v not in REASONS for v in item):
                    refuse()
            elif spec == "text":
                if item is not None and type(item) is not str:
                    refuse()
            elif spec == "bool":
                if type(item) is not bool:
                    refuse()
            elif spec in ("number", "count"):
                if item is not None and (type(item) not in (int, float)
                        or spec == "count" and (item < 0 or item % 1 != 0)):
                    refuse()
            else:
                refuse()

    def fields(*, texts="", numbers="", counts="", booleans="", opaque="", **nested):
        out = dict(nested)
        for keys, kind in ((texts, "text"), (numbers, "number"), (counts, "count"),
                           (booleans, "bool"), (opaque, "json")):
            out.update({key: kind for key in keys.split()})
        return out

    def obj(spec, required=(), nonnullable=False, nullable=()):
        def check(value):
            shape(value, spec, required)
            if nonnullable and any(item is None and key not in nullable for key, item in value.items()):
                refuse()
        return check

    def each(spec, mapping=False, nonnullable=False):
        def check(value):
            if type(value) is not (dict if mapping else list):
                refuse()
            for item in (value.values() if mapping else value):
                shape(item, spec)
                if nonnullable and any(field is None for field in item.values()):
                    refuse()
        return check

    def section(value, spec, required=()):
        shape(value, {"status": "text", "reasons": "reasons", **spec},
              ("status", "reasons", *required))
        if value["status"] not in SECTION_STATUSES:
            refuse()

    top = ("schema", "status", "scope", "theme", "observations", "comparison",
           "market_risk", "provenance", "limitations", "authority")
    if type(document) is not dict or set(document) != set(top):
        refuse()
    if (document["schema"] != SCHEMA or document["scope"] != SCOPE
            or document["status"] not in STATUSES):
        refuse()
    authority = document["authority"]
    if (type(authority) is not dict or set(authority) != set(AUTHORITY_FLAGS)
            or any(value is not False for value in authority.values())):
        refuse()
    expected_limits = {
        "current_sector_usable": False, "historically_admissible": False,
        "sector_mapping": {"status": "unavailable", "reason": "native_sector_mapping_not_supplied"},
        "original_available_at": None,
        "availability_reason": "native_availability_and_revision_selection_not_supplied",
        "attribution_verification": "not_established_by_projection",
    }
    limits = document["limitations"]
    if (type(limits) is not dict or limits != expected_limits
            or limits["current_sector_usable"] is not False
            or limits["historically_admissible"] is not False):
        refuse()
    theme = document["theme"]
    section(theme, fields(texts="theme_key name membership_basis", counts="roster_size", roster="texts"),
            ("theme_key", "name", "membership_basis", "roster", "roster_size"))
    if (theme["membership_basis"] != "configured_theme_roster"
            or type(theme["roster_size"]) is not int
            or theme["roster_size"] != len(theme["roster"]) or len(theme["roster"]) > 64
            or len(set(theme["roster"])) != len(theme["roster"])
            or any(not value or len(value) > 16 for value in theme["roster"])
            or theme["theme_key"] is not None and (not theme["theme_key"] or len(theme["theme_key"]) > 64)
            or theme["name"] is not None and (not theme["name"] or len(theme["name"]) > 120)):
        refuse()

    component = fields(texts="description", numbers="value",
                       counts="n_reporting latest_fy min_required", booleans="met_gate weight_provisional")
    fingerprint = fields(texts="theme basis", numbers="fingerprint_tightness leg7_member_inventory leg8_member_backlog",
        counts="n_legs_live", booleans="provisional", components=each(component, mapping=True))
    bottleneck = fields(texts="asof name naics band numeric_band",
        numbers="tightness numeric_composite cap_u_latest ppi_yoy_latest language_accel",
        counts="n_legs language_hits language_n_filers", booleans="regime text_only",
        leg6_detail=obj(fields(numbers="value accel", counts="hits n_filers", booleans="provisional")),
        fingerprint=obj(fingerprint))
    revision = fields(texts="asof level_state broadening_state",
        numbers="breadth est_drift_90d breadth_accel breadth_cov coverage",
        counts="net_up_total n_covered n_members breadth_accel_basis_days")
    contributor = fields(texts="ticker", numbers="breadth est_chg_90d breadth_cov",
                         counts="n_analysts n_covering")
    clocks = fields(opaque="regime_asof regime_built_at theme_revisions_asof bottleneck_asof",
        regime_freshness=obj(fields(opaque="asof built_at age_days age_sessions max_age_sessions stale")))
    units = fields(texts="breadth est_drift_90d breadth_accel breadth_cov est_chg_90d net_up_total coverage n_covered n_members n_analysts n_covering breadth_accel_basis_days")
    observations = document["observations"]
    section(observations, {"clocks": obj(clocks), "units": obj(units),
        "revision_state": obj(revision, nonnullable=True),
        "contributors": each(contributor, nonnullable=True), "bottleneck": obj(bottleneck)})
    if observations["status"] in ("withheld", "unavailable") and set(observations) - {"status", "reasons", "clocks"}:
        refuse()
    contributors = observations.get("contributors", [])
    if len(contributors) > 64:
        refuse()
    identities = [row.get("ticker") for row in contributors]
    if (any(type(ticker) is not str or ticker not in theme["roster"] for ticker in identities)
            or len(set(identities)) != len(identities)):
        refuse()
    revision_values = observations.get("revision_state", {})
    members, covered = revision_values.get("n_members"), revision_values.get("n_covered")
    coverage = revision_values.get("coverage")
    if ((members is not None and members != len(theme["roster"]))
            or (covered is not None and covered != len(contributors))
            or (members is not None and covered is not None and
                (covered > members or members == 0 and coverage is not None
                 or members > 0 and coverage is not None and abs(coverage - covered / members) > 1e-9))):
        refuse()

    risk = document["market_risk"]
    section(risk, fields(texts="scope definition_id market bundle_id source_session as_of observed_at produced_at revision data_state stale_after",
        measured_state=obj(fields(texts="verdict as_of role source_artifact", numbers="score", booleans="usable"),
                           ("verdict", "usable"), nonnullable=True),
        hazard_summary=obj(fields(texts="stage stage_reason stage_since stage_since_basis primary_episode_id",
            counts="active_episode_count", booleans="display_only", contributing_sources="texts",
            unreadable_sources="texts", capped_sources="texts", unmapped_required_sources="texts"),
            nonnullable=True, nullable=("stage", "primary_episode_id")),
        freshness=obj(fields(texts="source_session", booleans="all_on_session", off_session_sources="texts",
            per_source=each(fields(texts="as_of state", booleans="matches_session"), mapping=True, nonnullable=True)),
            ("all_on_session", "per_source"), nonnullable=True),
        coherence=obj(fields(texts="state scope", counts="contradiction_count", booleans="display_only",
            opaque="contradictions", compares="texts", excludes="texts"), ("state",), nonnullable=True),
        policy_summary=obj(fields(texts="posture basis", counts="policy_count", booleans="display_only", active_policy_ids="texts"),
                           ("posture", "basis", "active_policy_ids"), nonnullable=True),
        source_authority=obj(fields(booleans="envelope_may_execute envelope_may_gate envelope_may_rank envelope_may_size policy_actions_require_individual_authority"),
            ("envelope_may_execute", "envelope_may_gate", "envelope_may_rank", "envelope_may_size", "policy_actions_require_individual_authority"))), ("scope",))
    if (risk["scope"] != "market_global" or risk["status"] in ("withheld", "unavailable")
            and set(risk) != {"status", "reasons", "scope"}):
        refuse()
    if "contradictions" in risk.get("coherence", {}) and type(risk["coherence"]["contradictions"]) is not list:
        refuse()

    comparison = document["comparison"]
    section(comparison, {"evaluation": "text", "entries": "json"}, ("evaluation", "entries"))
    entries = comparison["entries"]
    if comparison["evaluation"] != "prospective_unevaluated" or type(entries) is not list:
        refuse()
    if not entries:
        if comparison["status"] != "unavailable":
            refuse()
    elif [entry.get("id") if type(entry) is dict else None for entry in entries] != list(COMPARISON_IDS):
        refuse()
    for entry in entries:
        shape(entry, {"id": "text", "evaluation": "text", "status": "text", "statement": "text",
            "evidence_refs": "texts", "falsifier": obj({"check": "text", "met": "bool"}, ("check", "met")),
            "reasons": "reasons"}, ("id", "evaluation", "status", "statement", "evidence_refs", "falsifier", "reasons"))
        if (entry["evaluation"] != "prospective_unevaluated" or entry["status"] not in ("supported", "unresolved")
                or type(entry["statement"]) is not str or len(entry["statement"]) > 320
                or type(entry["falsifier"]["check"]) is not str or len(entry["falsifier"]["check"]) > 320
                or entry["falsifier"]["met"] is not False
                or entry["status"] == "supported" and not entry["evidence_refs"]):
            refuse()
        for reference in entry["evidence_refs"]:
            parts = reference.split(".")
            value = document
            if parts[0] not in ("observations", "market_risk"):
                refuse()
            for part in parts:
                if type(value) is not dict or part not in value:
                    refuse()
                value = value[part]

    provenance = document["provenance"]
    section(provenance, {"source_attribution": "json", "attribution_verification": "text", "projection": "json"})
    if "source_attribution" in provenance:
        attribution = provenance["source_attribution"]
        if type(attribution) is not dict or set(attribution) not in (set(), set(ATTRIBUTION_KEYS)):
            refuse()
        for value in attribution.values():
            shape(value, {"source_ref": "text", "raw_sha256": "text"}, ("source_ref", "raw_sha256"))
            if (value["source_ref"] is not None and (not value["source_ref"] or len(value["source_ref"]) > 512)
                    or value["raw_sha256"] is not None and re.fullmatch(r"[0-9a-f]{64}", value["raw_sha256"]) is None):
                refuse()
        if (provenance.get("attribution_verification") != "not_established_by_projection"
                or provenance.get("projection") != {"schema": SCHEMA, "deterministic": True,
                    "reads": list(ATTRIBUTION_KEYS) + ["source_attribution"], "writes": []}
                or provenance["projection"]["deterministic"] is not True):
            refuse()
    elif set(provenance) != {"status", "reasons"}:
        refuse()
    # These are the owner's withholding/presence invariants, not a second
    # explanation calculation. Independent partial sections remain admissible.
    if theme["status"] not in ("available", "unavailable"):
        refuse()
    if theme["status"] == "unavailable" and theme["roster"]:
        refuse()
    if theme["status"] == "available" and (theme["name"] is None or theme["reasons"]):
        refuse()
    has_revision, has_bottleneck = "revision_state" in observations, "bottleneck" in observations
    if has_revision != ("units" in observations) or has_revision != ("contributors" in observations):
        refuse()
    historical = observations["status"] == "withheld"
    if historical:
        if (observations["reasons"] != [HISTORICAL_REASON]
                or comparison["status"] != "withheld"
                or comparison["reasons"] != [HISTORICAL_REASON]
                or risk["status"] not in ("withheld", "unavailable")
                or any(entry["status"] != "unresolved" or entry["evidence_refs"] for entry in entries)):
            refuse()
    else:
        expected_observations = ("available" if has_revision and has_bottleneck
                                 else "partial" if has_revision or has_bottleneck else "unavailable")
        if observations["status"] != expected_observations or comparison["status"] == "withheld" or risk["status"] == "withheld":
            refuse()
    if theme["status"] != "available" and (has_revision or has_bottleneck
            or any(entry["status"] != "unresolved" or entry["evidence_refs"] for entry in entries[:3])):
        refuse()
    if entries and entries[3]["status"] != "unresolved":
        refuse()
    expected_status = ("unavailable" if theme["status"] != "available" else
                       "dated_context" if all(section["status"] == "available" for section in
                                              (observations, comparison, risk)) else "partial")
    if document["status"] != expected_status:
        refuse()
    if "source_attribution" not in provenance and (
            any(document[name]["status"] != "unavailable" for name in
                ("theme", "observations", "comparison", "market_risk", "provenance"))
            or entries or set(observations) != {"status", "reasons"}
            or set(risk) != {"status", "reasons", "scope"}):
        refuse()
    return deepcopy(document)


def _classification_context(document: Any) -> dict:
    try:
        return _checked_classification_context(document)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise SectorViewUnavailable("invalid_sector_classification_context") from None


def _checked_classification_context(document: Any) -> dict:
    """Qualify the bounded descriptive capture, without admitting sector use.

    Identity resolution remains with the native identity/association owners.
    This transport only accepts the capture adapter's explicit LEGACY shape,
    exact configured subset, source seals, separate clocks and false authority.
    """
    from engine.entry_radar.replay.identity_observation_snapshot import REFERENCE_ARTIFACTS
    from engine.neuralweb.sector_map import GICS_TO_ETF
    from lib.dataos.identity import IdentityError, parse_id, parse_listing_key
    code = "invalid_sector_classification_context"

    def require(condition):
        if not condition:
            raise SectorViewUnavailable(code)

    # Bound hostile in-process containers before serialization or copying.
    pending, seen, nodes = [(document, 0)], set(), 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        require(nodes <= 2048 and depth <= 9)
        if type(value) in (dict, list):
            require(id(value) not in seen and len(value) <= 64)
            seen.add(id(value))
            if type(value) is dict:
                require(all(type(k) is str and len(k) <= 64 for k in value))
            pending.extend((v, depth + 1) for v in
                           (value.values() if type(value) is dict else value))
        else:
            require(value is None or type(value) in (str, int, bool))
            if type(value) is str:
                require(len(value) <= 512)
                try:
                    value.encode("utf-8")
                except UnicodeError:
                    require(False)

    def keys(value, fields):
        require(type(value) is dict and set(value) == set(fields.split()))

    def text(value, limit=128):
        require(type(value) is str and 0 < len(value) <= limit
                and value == value.strip() and not any(ord(c) < 32 for c in value))
        return value

    def clock(value):
        text(value, 64)
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            require(stamp.tzinfo is not None and stamp.utcoffset() is not None)
            return stamp
        except ValueError:
            raise SectorViewUnavailable(code) from None

    def count(value, maximum):
        require(type(value) is int and 0 <= value <= maximum)

    def digest(value):
        require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)

    def roster(value):
        require(type(value) is list and len(value) <= 5)
        for symbol in value:
            text(symbol, 16)
        require(len(set(value)) == len(value))

    keys(document, "schema status theme_key configured_roster membership_roster missing_roster unclassified_rows_n capture association")
    require(document["schema"] == "sector_classification_context/v1"
            and document["theme_key"] == "memory_storage")
    configured, membership, missing = (document[n] for n in
        ("configured_roster", "membership_roster", "missing_roster"))
    for values in (configured, membership, missing):
        roster(values)
    require(membership == [s for s in configured if s not in missing]
            and missing == [s for s in configured if s not in membership])
    count(document["unclassified_rows_n"], 15)
    capture = document["capture"]
    keys(capture, "mode status reason captured_at producer_receipt_sha256 artifact_sha256")
    require(capture["mode"] == "LEGACY")
    observed = clock(capture["captured_at"])
    if capture["status"] != "captured":
        reasons = ({"configured_roster_unavailable", "no_captured_membership_label",
                    "captured_classification_rows_incomplete"}
                   if capture["status"] == "not_attempted" else {
                       "native_reference_requires_native_reader", "reference_resource_bound",
                       "reference_writer_busy", "reference_capture_unavailable"})
        require(capture["status"] in {"not_attempted", "unavailable"}
                and capture["reason"] in reasons
                and capture["producer_receipt_sha256"] is None
                and capture["artifact_sha256"] is None
                and document["association"] is None and document["status"] == "unavailable")
        if capture["status"] == "not_attempted":
            if capture["reason"] == "captured_classification_rows_incomplete":
                require(bool(membership) and document["unclassified_rows_n"] > 0)
            else:
                require(not membership and document["unclassified_rows_n"] == 0)
                require((capture["reason"] == "configured_roster_unavailable") == (not configured))
        else:
            require(bool(membership) and document["unclassified_rows_n"] == 0)
        return deepcopy(document)

    require(bool(membership) and capture["reason"] is None and document["unclassified_rows_n"] == 0)
    digest(capture["producer_receipt_sha256"])
    hashes = capture["artifact_sha256"]
    require(type(hashes) is dict and set(hashes) == set(REFERENCE_ARTIFACTS))
    for value in hashes.values():
        digest(value)
    association = document["association"]
    keys(association, "schema status identity_mode lookup_on observed_at coverage associations source_attribution limitations authority")
    require(association["schema"] == "sector_map.captured_associations/v1"
            and association["identity_mode"] == "current"
            and association["observed_at"] == capture["captured_at"])
    require(date.fromisoformat(_session(association["lookup_on"])) <= observed.date())
    limits = association["limitations"]
    keys(limits, "current_sector_usable historically_admissible sector_membership_established sector_representativeness_established causal_claim")
    require(all(v is False for v in limits.values()))
    authority = association["authority"]
    keys(authority, "may_rank may_gate may_size may_trade may_escalate may_publish")
    require(all(v is False for v in authority.values()))
    attrs = association["source_attribution"]
    require(type(attrs) is list and len(attrs) == 5)
    expected = {"vendor_aliases": "vendor_aliases.parquet", "issuer_master": "security_master.parquet"}
    populations = {"breadth", "midcap_breadth", "smallcap_breadth"}
    by_ref, seen_kind, seen_pop = {}, set(), set()
    for attr in attrs:
        fields = "kind source_ref raw_sha256 read_receipt_sha256 source_version generation_id captured_at source_effective_on source_available_at"
        keys(attr, fields + (" population" if attr.get("kind") == "constituents" else ""))
        require(attr["source_ref"] not in by_ref and attr["read_receipt_sha256"] is None
                and attr["source_version"] is None and attr["source_effective_on"] is None
                and attr["source_available_at"] is None and clock(attr["captured_at"]) <= observed)
        digest(attr["raw_sha256"])
        if attr["kind"] == "constituents":
            pop = attr["population"]
            require(pop in populations and pop not in seen_pop)
            seen_pop.add(pop)
            require(attr["source_ref"] == "breadth_member_generation/groups/" + pop + "/constituents.json")
            require(_TOKEN.fullmatch(text(attr["generation_id"])) is not None)
        else:
            kind = attr["kind"]
            require(kind in expected and kind not in seen_kind)
            seen_kind.add(kind)
            name = expected[kind]
            require(attr["source_ref"] == "R/data/reference/" + name
                    and attr["raw_sha256"] == hashes[name] and attr["generation_id"] is None
                    and attr["captured_at"] == capture["captured_at"])
        by_ref[attr["source_ref"]] = attr
    require(seen_kind == set(expected) and seen_pop == populations
            and len({a["generation_id"] for a in attrs if a["kind"] == "constituents"}) == 1)
    rows = association["associations"]
    require(type(rows) is list and len(rows) == len(membership))
    counts = {"available": 0, "unavailable": 0, "conflict": 0}
    reasons_allowed = {"ALIAS_UNAVAILABLE", "NONCANONICAL_SECURITY", "ALIAS_NOT_RECIPROCAL",
        "MASTER_SECURITY_ABSENT", "SECURITY_NOT_ACTIVE", "ISSUER_NOT_RESOLVED", "IDENTITY_INCOMPLETE",
        "IDENTITY_INCONSISTENT", "NATIVE_IDENTITY_REFUSED", "CLASSIFICATION_EFFECTIVE_AFTER_OBSERVATION",
        "CLASSIFICATION_CONFLICT", "UNSUPPORTED_SECTOR", "NO_CAPTURED_CLASSIFICATION"}
    for symbol, row in zip(membership, rows):
        keys(row, "subject status security_id issuer_id listing_key sector sector_etf_proxy etf_security_id etf_identity_status source_observations duplicate_observations_n reason_codes")
        keys(row["subject"], "vendor vendor_symbol")
        require(row["subject"] == {"vendor": "membership", "vendor_symbol": symbol}
                and row["status"] in counts and row["etf_security_id"] is None
                and row["etf_identity_status"] == "not_supplied")
        counts[row["status"]] += 1
        sid, issuer, listing = (row[n] for n in ("security_id", "issuer_id", "listing_key"))
        if sid is None:
            require(issuer is None and listing is None)
        else:
            try:
                kind, identity = parse_id(text(sid))
                issuer_kind, issuer_key = parse_id(text(issuer))
                require(kind == "security" and sid == "SEC:" + identity.render()
                        and issuer_kind == "issuer" and issuer == "ISS:" + issuer_key.render()
                        and parse_listing_key(text(listing)) == identity and listing == identity.render())
            except IdentityError:
                raise SectorViewUnavailable(code) from None
        reasons = row["reason_codes"]
        require(type(reasons) is list and len(reasons) <= len(reasons_allowed))
        require(all(type(r) is str and r in reasons_allowed for r in reasons)
                and reasons == sorted(set(reasons)))
        # These verified populations contain each label once; this adapter does
        # not accept an independently aggregated or padded population here.
        require(type(row["duplicate_observations_n"]) is int and row["duplicate_observations_n"] == 0)
        observations = row["source_observations"]
        require(type(observations) is list and len(observations) <= 3)
        row_refs, sectors = set(), set()
        for item in observations:
            keys(item, "source_ref population native_symbol native_name native_sector source_effective_on source_available_at captured_at binding_status")
            ref = item["source_ref"]
            require(ref in by_ref and ref not in row_refs)
            row_refs.add(ref)
            attr = by_ref[ref]
            require(attr["kind"] == "constituents" and item["population"] == attr["population"]
                    and item["native_symbol"] == symbol and item["source_effective_on"] is None
                    and item["source_available_at"] is None and item["captured_at"] == attr["captured_at"]
                    and item["binding_status"] == ("bound" if sid is not None else "unbound"))
            text(item["native_name"], 512)
            text(item["native_sector"])
            if sid is not None:
                sectors.add(item["native_sector"])
        if row["status"] == "available":
            require(sid is not None and not reasons and len(sectors) == 1
                    and row["sector"] in GICS_TO_ETF and sectors == {row["sector"]}
                    and row["sector_etf_proxy"] == GICS_TO_ETF[row["sector"]])
        else:
            require(row["sector"] is None and row["sector_etf_proxy"] is None and bool(reasons))
            require((row["status"] == "conflict") == (len(sectors) > 1))
            if row["status"] == "conflict":
                require("CLASSIFICATION_CONFLICT" in reasons)
    coverage = association["coverage"]
    keys(coverage, "requested_n associated_n unavailable_n conflict_n duplicate_requests_n")
    for value in coverage.values():
        count(value, 5)
    require(coverage == {"requested_n": len(rows), "associated_n": counts["available"],
        "unavailable_n": counts["unavailable"], "conflict_n": counts["conflict"], "duplicate_requests_n": 0})
    status = ("conflict" if counts["conflict"] else "available" if counts["available"] == len(rows)
              else "partial" if counts["available"] else "unavailable")
    require(association["status"] == status)
    expected_status = "partial" if status == "available" and (missing or document["unclassified_rows_n"]) else status
    require(document["status"] == expected_status)
    require(len(json.dumps(document, ensure_ascii=False, allow_nan=False,
                           separators=(",", ":")).encode("utf-8")) <= 32768)
    return deepcopy(document)


def _core(central: dict, source: str) -> tuple[dict, dict[str, str]]:
    code = "invalid_sector_core"
    rows, identities, tickers = [], {}, set()
    source_rows = _bounded_records(central.get("sectors"), MAX_CORE_SECTORS, code)
    if not source_rows:
        raise SectorViewUnavailable(code)
    for row in source_rows:
        ident, ticker = _sector_identity(row, code)
        if ident in identities or ticker in tickers or not isinstance(row.get("name"), str) or not row["name"]:
            raise SectorViewUnavailable(code)
        identities[ident] = ticker
        tickers.add(ticker)
        item = _typed_fields(row, strings=("id", "ticker", "kind", "name", "name_zh", "accent"), code=code)
        for block, strings, numbers, booleans in (
            ("momentum", ("lead",), ("rs_21d", "rs_63d", "rs_21d_rank", "rs_rank"), ("above_200d",)),
            ("heat", (), ("heat_1M", "breadth_pct", "adv", "dec"), ()),
            ("rotation", ("state", "state_plain_en", "state_plain_zh"), (), ()),
            ("conviction", ("label_en",), (), ()),
            ("cycle", ("phaseLabel",), (), ()),
        ):
            if block in row:
                item[block] = None if row[block] is None else _typed_fields(
                    row[block], strings=strings, numbers=numbers, booleans=booleans, code=code)
        for block, fields, minimum in (("momentum", ("rs_21d_rank", "rs_rank"), 1),
                                        ("heat", ("adv", "dec"), 0)):
            for key in fields:
                value = (item.get(block) or {}).get(key)
                if value is not None and (value < minimum or value % 1 != 0):
                    raise SectorViewUnavailable(code)
        rows.append(item)
    out = {"as_of": source, "sectors": rows}
    if "measured_read" in central:
        out["measured_read"] = _measured_read(central["measured_read"], source)
    if "dated_context" in central:
        out["dated_context"] = _dated_context(central["dated_context"])
    if "captured_classification" in central:
        out["captured_classification"] = _classification_context(central["captured_classification"])
    return out, identities


def _history(cycles: dict, source: str, core_ids: dict[str, str]) -> dict:
    code = "invalid_sector_history"
    meta = cycles.get("meta")
    contract = meta.get("rs_history") if isinstance(meta, dict) else None
    expected = {
        "schema": RS_HISTORY_SCHEMA, "mode": RS_HISTORY_MODE,
        "naturally_observed": False, "basis": "tr", "benchmark": "SPY",
        "horizons_sessions": list(RS_HISTORY_HORIZONS),
        "max_points_per_sector": RS_HISTORY_MAX_POINTS,
    }
    if (not isinstance(contract, dict)
            or any(contract.get(key) != value for key, value in expected.items())
            or contract.get("naturally_observed") is not False
            or type(contract.get("max_points_per_sector")) is not int
            or type(contract.get("horizons_sessions")) is not list
            or any(type(v) is not int for v in contract["horizons_sessions"])
            or ("as_of" in contract and contract["as_of"] != source)
            or meta.get("benchmark", "SPY") != "SPY"):
        raise SectorViewUnavailable(code)
    rows, identities, tickers = [], set(), set()
    core_by_ticker = {ticker: ident for ident, ticker in core_ids.items()}
    source_rows = _bounded_records(cycles.get("sectors"), MAX_CORE_SECTORS, code)
    if not source_rows:
        raise SectorViewUnavailable(code)
    for row in source_rows:
        ident, ticker = _sector_identity(row, code)
        if ident in identities or ticker in tickers:
            raise SectorViewUnavailable(code)
        identities.add(ident)
        tickers.add(ticker)
        if ((ident in core_ids and core_ids[ident] != ticker)
                or (ticker in core_by_ticker and core_by_ticker[ticker] != ident)):
            raise SectorViewUnavailable("mixed_sector_identity")
        points, prior = [], ""
        for point in _bounded_records(row.get("rs_history"), RS_HISTORY_MAX_POINTS, code):
            day = _session(point.get("date"))
            if day > source or day <= prior:
                raise SectorViewUnavailable(code)
            prior = day
            projected = _typed_fields(point, strings=("date",), numbers=("rs_21d", "rs_63d"), code=code)
            if any(projected.get(key) is None for key in ("rs_21d", "rs_63d")):
                raise SectorViewUnavailable(code)
            points.append(projected)
        turns, prior = [], ""
        for turn in _bounded_records(row.get("turns"), MAX_HISTORY_TURNS, code):
            day = _session(turn.get("date"))
            if (day > source or day <= prior or turn.get("k") not in ("peak", "trough")
                    or type(turn.get("major")) is not bool or type(turn.get("provisional")) is not bool):
                raise SectorViewUnavailable(code)
            prior = day
            projected = _typed_fields(turn, strings=("date", "k"), numbers=("mag_pct",),
                                      booleans=("major", "provisional"), code=code)
            if projected.get("mag_pct") is not None and projected["mag_pct"] < 0:
                raise SectorViewUnavailable(code)
            turns.append(projected)
        rows.append({"id": ident, "ticker": ticker, "kind": "sector", "rs_history": points, "turns": turns})
    if identities != set(core_ids):
        raise SectorViewUnavailable("mixed_sector_identity")
    # Missing observations stay explicitly empty. Never complete them from
    # another generation, infer observations, or export raw price/cycle internals.
    return {"meta": {"asOf": source, "rs_history": deepcopy(expected)}, "sectors": rows}


_TYPED_BLOCK_MAX_BYTES = 64 * 1024
#: The five lane-1 v1.1 row blocks (wire §1) carry full group rows and members, so
#: they are measured against their own cap, above the 60 KiB carry / 64 KiB serve
#: caps of the seven incumbent blocks.
_TYPED_ROW_BLOCK_MAX_BYTES = 516 * 1024
_CONFLUENCE_UNIVERSES = 4
#: name -> (owning document, closed key). Lane 7 blocks are entitled-only depth.
#: ``carried`` is ``sector_central.json["carried"]``, written by the central builder
#: (lib.sector_central_carry) from existing producer artifacts. ``hazard_qualification``
#: has no producer on this base (``hazard_score.qualify_current_model`` is not here).
#: The last five (wire v1.1 §1) are the confluence-universe row blocks and the theme
#: row array: carried key equal to the block name, entitled-only.
_TYPED_BLOCK_SOURCES = (
    ("r1_rising_priced_share", "carried", "sector_central_r1", False),
    ("r2_display_order", "carried", "display_order", False),
    ("r2_hazard_qualification", "central", "hazard_qualification", False),
    ("etf_flows", "carried", "etf_flows", True),
    ("confluence", "carried", "confluence", True),
    ("bottoming_watch", "carried", "bottoming_watch", True),
    ("theme_table", "carried", "theme_table", True),
    ("confluence_universe_sp500", "carried", "confluence_universe_sp500", True),
    ("confluence_universe_nasdaq", "carried", "confluence_universe_nasdaq", True),
    ("confluence_universe_russell", "carried", "confluence_universe_russell", True),
    ("confluence_universe_baskets", "carried", "confluence_universe_baskets", True),
    ("theme_rows", "carried", "theme_rows", True),
)
#: Serving rules of the universe row blocks (wire v1.1 §1/§4): the required owner
#: word and the exact ``group_arrays`` list of section 1.
_TYPED_ROW_BLOCK_UNIVERSES = {
    "confluence_universe_sp500": ("sp500_subsectors", ("subsectors", "sectors")),
    "confluence_universe_nasdaq": ("nasdaq_subsectors", ("subsectors", "sectors")),
    "confluence_universe_russell": ("russell_subsectors", ("subsectors", "sectors")),
    "confluence_universe_baskets": ("curated_baskets", ("baskets",)),
}
_TYPED_ROW_BLOCK_NAMES = frozenset(_TYPED_ROW_BLOCK_UNIVERSES) | {"theme_rows"}


def _typed_block(value: Any, *, name: str) -> dict:
    """One optional typed block: ``available`` only if strictly well formed.

    A malformed block reads ``invalid_shape`` - it is never repaired, never
    raises and never changes any other part of the projection.
    """
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
        ok = isinstance(value, dict) and len(encoded) <= _TYPED_BLOCK_MAX_BYTES
        if ok and name == "confluence":
            ok = len(value) == _CONFLUENCE_UNIVERSES
    except (TypeError, ValueError, OverflowError, RecursionError):
        ok = False
    if not ok:
        return {"status": "unavailable", "reason": "invalid_shape", "value": None}
    return {"status": "available", "reason": None, "value": json.loads(encoded)}


def _typed_row_block(value: Any, *, name: str) -> dict:
    """One lane-1 v1.1 row block (wire §4), in this order:

    1. a carried mapping with ``status`` ``unavailable`` and reason
       ``block_too_large`` reads ``unavailable / block_too_large`` with a null
       value; any other reason reads ``unavailable / invalid_shape``;
    2. otherwise ``available`` only when the value is a mapping, finite JSON, at
       most ``_TYPED_ROW_BLOCK_MAX_BYTES`` encoded, dated (a non-empty string
       ``as_of``), and for a universe block ``data`` is a mapping whose
       ``universe`` is the required owner word with exactly the section-1
       ``group_arrays`` list, every named array a list; for ``theme_rows``
       ``rows`` is a list.

    Never repaired, never raised, never changes another part of the projection.
    The closed reason set for these five is ``audience_not_entitled``,
    ``not_produced``, ``invalid_shape``, ``block_too_large``.
    """
    if isinstance(value, dict) and value.get("status") == "unavailable":
        if value.get("reason") == "block_too_large":
            return {"status": "unavailable", "reason": "block_too_large", "value": None}
        return {"status": "unavailable", "reason": "invalid_shape", "value": None}
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
        as_of = value.get("as_of") if isinstance(value, dict) else None
        ok = (isinstance(value, dict) and len(encoded) <= _TYPED_ROW_BLOCK_MAX_BYTES
              and isinstance(as_of, str) and bool(as_of))
        if ok and name in _TYPED_ROW_BLOCK_UNIVERSES:
            owner_word, group_arrays = _TYPED_ROW_BLOCK_UNIVERSES[name]
            data = value.get("data")
            ok = (isinstance(data, dict) and data.get("universe") == owner_word
                  and value.get("group_arrays") == list(group_arrays)
                  and all(isinstance(data.get(array), list) for array in group_arrays))
        elif ok:  # theme_rows
            ok = isinstance(value.get("rows"), list)
    except (TypeError, ValueError, OverflowError, RecursionError):
        ok = False
    if not ok:
        return {"status": "unavailable", "reason": "invalid_shape", "value": None}
    return {"status": "available", "reason": None, "value": json.loads(encoded)}


def _typed_blocks(inputs: SectorViewInputs, audience: str) -> dict:
    """Optional lane 7/8 blocks, carried so downstream lanes get a stable shape.

    Closed source locations only (``central.carried.*`` and
    ``central.hazard_qualification``); nothing is read from disk and no value is
    derived. On producers that do not emit a block it reads
    ``unavailable/not_produced``.
    """
    carried = inputs.central.get("carried")
    documents = {"central": inputs.central,
                 "carried": carried if isinstance(carried, dict) else {}}
    blocks = {}
    for name, owner, key, entitled_only in _TYPED_BLOCK_SOURCES:
        if entitled_only and audience != "entitled":
            blocks[name] = {"status": "unavailable", "reason": "audience_not_entitled",
                            "value": None}
        elif key not in documents[owner]:
            blocks[name] = {"status": "unavailable", "reason": "not_produced", "value": None}
        else:
            reader = _typed_row_block if name in _TYPED_ROW_BLOCK_NAMES else _typed_block
            blocks[name] = reader(documents[owner][key], name=name)
    return blocks


def typed_blocks_of(data: dict) -> dict:
    """The twelve blocks of a projected ``data`` object, absent key included.

    An absent ``typed_blocks`` means no producer emitted any block: every block
    reads ``unavailable/not_produced`` (the entitled-only nine read
    ``audience_not_entitled`` for a preview projection). Nothing is invented.
    """
    present = data.get("typed_blocks")
    if isinstance(present, dict):
        return present
    preview = data.get("audience") == "preview"
    return {name: {"status": "unavailable",
                   "reason": "audience_not_entitled" if preview and entitled_only
                   else "not_produced", "value": None}
            for name, _owner, _key, entitled_only in _TYPED_BLOCK_SOURCES}


def project_sector_view(
    inputs: SectorViewInputs,
    receipt: SectorViewReceipt,
    *,
    audience: Literal["preview", "entitled"],
    preview_rows: int = 3,
) -> dict[str, Any]:
    """Project accepted owner outputs without creating intelligence or authority.

    Audience is a trusted caller decision, not authorization. The API must enforce
    the existing canonical-resource policies even for a preview representation.
    Older basket/Brief inputs require an explicit common baseline in the receipt;
    a mixed or future session is never silently promoted to the current source.
    """
    public_receipt, baseline = _receipt(receipt)
    if audience not in ("preview", "entitled"):
        raise SectorViewUnavailable("invalid_audience")
    if (isinstance(preview_rows, bool) or not isinstance(preview_rows, int)
            or not 0 <= preview_rows <= 100):
        raise SectorViewUnavailable("invalid_preview")
    if not isinstance(inputs, SectorViewInputs) or not all(
        isinstance(doc, dict) for doc in (
            inputs.central, inputs.cycles, inputs.baskets, inputs.handoff, inputs.action_board
        )
    ):
        raise SectorViewUnavailable("invalid_inputs")
    try:
        core_sessions = (inputs.central.get("as_of"), inputs.cycles["meta"].get("asOf"))
        theme = inputs.baskets["theme_intel"]
        context = inputs.handoff["theme_context"]
        secondary_sessions = (
            inputs.baskets.get("as_of"), theme.get("as_of"), context.get("as_of"),
            inputs.action_board.get("as_of"),
        )
        if not all(_session(value) == receipt.source_session for value in core_sessions):
            raise SectorViewUnavailable("mixed_core_sessions")
        if not all(_session(value) == baseline for value in secondary_sessions):
            raise SectorViewUnavailable("mixed_brief_sessions")
    except (KeyError, TypeError, AttributeError):
        raise SectorViewUnavailable("missing_source_contract") from None
    if inputs.action_board.get("schema") != "sector_intelligence_action_board.v1":
        raise SectorViewUnavailable("invalid_action_board_contract")
    leadership = context.get("leadership")
    if not isinstance(leadership, dict):
        raise SectorViewUnavailable("missing_leadership")
    strength = leadership.get("strength")
    if (not isinstance(strength, list) or len(strength) > 1000
            or any(not isinstance(group, dict) for group in strength)):
        raise SectorViewUnavailable("invalid_leadership")
    groups = [_pick(group, _GROUP_FIELDS) for group in strength]
    subject = groups[0] if groups else None
    state = leadership.get("state")
    # Labels are copied from the accepted Macro Brief template, not reclassified.
    titles = {
        "rotating": ("Leadership is rotating.", "领涨正在轮动。"),
        "strain": ("Leadership under pressure.", "领涨开始承压。"),
        "steady": ("Leadership is holding.", "领涨格局延续。"),
    }
    headline = titles.get(state, ("Leadership not measured.", "领涨状态暂无实测。"))
    lead = _pick(leadership, ("state", "days_in_state", "stance_en", "stance_zh"))
    lead["strength"] = groups
    trailing = leadership.get("trailing_leader")
    lead["trailing_leader"] = _pick(trailing, _GROUP_FIELDS) if isinstance(trailing, dict) else None
    series = build_brief_series(subject.get("id") if subject else None, inputs.baskets.get("chart"))
    if series is not None and series["end"] != baseline:
        raise SectorViewUnavailable("comparison_session_mismatch")
    comparison = {
        "status": "available" if series else "unavailable",
        "reason": None if series else "matching_closes_unavailable",
        "subject": deepcopy(subject),
        "basket_kind": ("equal_weight_sector_basket"
                        if subject and str(subject.get("id", "")).startswith("us_sector_")
                        else "theme_basket") if subject else None,
        "benchmark": "SPY",
        "measure": "20_session_relative_wealth",
        # Carry the owner's construction/history disclosure. The chart payload
        # does not declare a uniform price/TR basis, so never infer one here.
        "source_notes": _pick(inputs.baskets, ("construction", "history_note", "note")),
        "price_basis": "not_declared_by_chart",
        "series": series,
    }
    core, core_ids = _core(inputs.central, receipt.source_session)
    if "captured_classification" in core:
        captured = datetime.fromisoformat(core["captured_classification"]["capture"]["captured_at"].replace("Z", "+00:00"))
        published = datetime.fromisoformat(receipt.published_at.replace("Z", "+00:00"))
        if captured > published:
            raise SectorViewUnavailable("classification_capture_after_publication")
    history = _history(inputs.cycles, receipt.source_session, core_ids)
    factor = inputs.handoff.get("factor_season")
    data = {
        "schema": "sector_native_view.v1",
        "audience": audience,
        "core": core,
        "history": history,
        "brief": {
            "as_of": baseline,
            "status": "declared_older_baseline" if baseline != receipt.source_session else "available",
            "headline": {"en": headline[0], "zh": headline[1]},
            "leadership": lead,
            "comparison": comparison,
            "factor_season": _pick(factor, _FACTOR_FIELDS) if isinstance(factor, dict) else None,
        },
        "action_board": {
            "as_of": baseline,
            **_board(inputs.action_board.get("action_board"),
                     audience=audience, preview_rows=preview_rows),
        },
    }
    # Incumbent byte parity (tests/test_sector_native_view.py golden hashes): an
    # unproduced optional input leaves the hashed projection untouched, so the key
    # is ABSENT while no block is produced or malformed. Consumers read an absent
    # key through ``typed_blocks_of`` (every block unavailable/not_produced). Once
    # any block is produced or malformed the full twelve-block object is emitted.
    typed = _typed_blocks(inputs, audience)
    if any(b["reason"] not in ("not_produced", "audience_not_entitled")
           for b in typed.values()):
        data["typed_blocks"] = typed
    try:
        encoded_data = json.dumps(data, ensure_ascii=False, allow_nan=False,
                                  sort_keys=True, separators=(",", ":")).encode("utf-8")
        # Hash only the authorized representation. Hidden-row changes cannot
        # change a preview hash when visible content and approved counts agree.
        public_receipt["content_sha256"] = hashlib.sha256(encoded_data).hexdigest()
        output = {"data": data, "receipt": public_receipt}
        encoded = json.dumps(output, ensure_ascii=False, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise SectorViewUnavailable("invalid_projection_value") from None
    if len(encoded) > MAX_VIEW_BYTES:
        raise SectorViewUnavailable("projection_too_large")
    return output
