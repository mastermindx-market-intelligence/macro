"""Offline Forex source diagnostics subordinate to the Tiingo research reader.

No bar aggregation, correction selection, calendar admission, live publication or
watch evaluation occurs here. Even dense, valid vendor rows yield no eligible
final-4H observations. A timestamp delta is an observation, not proof of lost data.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from collectors.tiingo_archive import DEFAULT_ARCHIVE, validate_request
from lib.dataos.tiingo_reader import TiingoView, TiingoViewRefusal, read_research_view

SCHEMA = "mastermind.tiingo.forex_watch_source.v1"
QUALIFICATION_GAPS = (
    "spot_identity_not_admitted",
    "historical_ohlc_basis_unqualified",
    "vendor_timestamp_start_end_unqualified",
    "4h_calendar_and_completeness_unqualified",
    "finalization_and_correction_contract_unqualified",
    "historical_availability_unverified",
    "live_feed_and_freshness_not_admitted",
    "product_rights_mapping_not_admitted",
)
OHLC = ("open", "high", "low", "close")
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_ROWS = 20_000


def _clock(value: Any) -> pd.Timestamp | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is None:
            return None
        stamp = stamp.tz_convert("UTC")
        _ = stamp.value  # Require representable nanoseconds; never silently truncate.
        return stamp
    except (ValueError, TypeError, OverflowError):
        return None


def _price_issue(value: Any) -> str | None:
    if value is None:
        return "missing"
    if isinstance(value, bool):
        return "boolean"
    if not isinstance(value, (int, float)):
        return "not_numeric"
    try:
        if not math.isfinite(value):
            return "nonfinite"
    except OverflowError:
        return "nonfinite"
    return "nonpositive" if value <= 0 else None


def _evidence_value(value: Any) -> Any:
    # The verified reader already rejects malformed/nonfinite source numbers.
    # Direct pure-function diagnostics still serialize strictly and retain why
    # a value is unusable. Immutable source bytes remain the full raw evidence.
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return {"unusable_source_value": repr(value)[:256], "python_type": type(value).__name__}


def diagnose_forex_view(view: TiingoView, *, expected_pair: str,
                        receipt_id: str) -> dict[str, Any]:
    """Project an already-verified view without granting stronger authority.

    Use read_forex_watch_source at the file boundary. This pure function cannot
    prove bytes on disk; it checks the supplied lineage and preserves all rows.
    """
    if (not isinstance(view, TiingoView) or view.source != "forex-bars"
            or view.purpose != "INSPECTION"
            or view.authority != "RESEARCH_ONLY_VENDOR_SOURCE"
            or view.pit_backtest_eligible is not False
            or view.redistribution_admitted is not False):
        raise TiingoViewRefusal("Forex diagnostics require the inspection-only research reader")
    if (not isinstance(expected_pair, str) or not re.fullmatch(r"[A-Z]{6}", expected_pair)
            or not isinstance(receipt_id, str) or not SHA.fullmatch(receipt_id)
            or not isinstance(view.source_sha256, str) or not SHA.fullmatch(view.source_sha256)
            or _clock(view.source_observed_at_utc) is None):
        raise TiingoViewRefusal("Forex diagnostics require exact pair, receipt and capture context")
    validate_request("forex-bars", expected_pair.lower(), view.source_request_path)
    if len(view.rows) > MAX_ROWS:
        raise TiingoViewRefusal("Forex diagnostic row cap exceeded; no silent truncation")
    candidates, clocks, by_instant = [], [], defaultdict(list)
    issue_counts: Counter[str] = Counter()
    frequencies = set()
    reasons = set(QUALIFICATION_GAPS)
    for ordinal, row in enumerate(view.rows):
        if (not isinstance(row, dict)
                or row.get("ticker_vendor") != expected_pair.lower()
                or row.get("source_receipt_id") != receipt_id
                or row.get("source_sha256") != view.source_sha256
                or row.get("source_observed_at_utc") != view.source_observed_at_utc
                or row.get("source_vendor") != "tiingo"
                or row.get("dataset_source") != "forex-bars"
                or any(row.get(k) is not False for k in (
                    "source_rights_admitted", "dataos_identity_admitted",
                    "pit_backtest_eligible", "canonical_price_basis_admitted"))):
            raise TiingoViewRefusal("Forex diagnostic row identity or lineage mismatch")
        prices = {key: row.get("vendor_" + key) for key in OHLC}
        issues = {key: issue for key, value in prices.items() if (issue := _price_issue(value))}
        for issue in issues.values():
            issue_counts[issue] += 1
        if not issues and not prices["low"] <= min(prices["open"], prices["close"]) <= max(prices["open"], prices["close"]) <= prices["high"]:
            issues["ohlc_bounds"] = "inconsistent"
            issue_counts["inconsistent_bounds"] += 1
        stamp = _clock(row.get("bar_at_vendor"))
        if stamp is None:
            issues["vendor_timestamp"] = "invalid_or_naive"
            issue_counts["invalid_timestamp"] += 1
        else:
            clocks.append(stamp.value)
            if stamp.second or stamp.microsecond or stamp.nanosecond:
                issue_counts["subminute_timestamp"] += 1
            # Every original row remains in candidates. This grouping only
            # diagnoses repeated instants; it never selects a correction winner.
            by_instant[stamp.value].append(tuple(
                prices[k] if _price_issue(prices[k]) is None else ("invalid", repr(prices[k]))
                for k in OHLC))
        frequency = row.get("requested_resample_frequency")
        frequencies.add(str(frequency))
        candidates.append({
            "source_row_ordinal": ordinal,
            "bar_at_vendor": _evidence_value(row.get("bar_at_vendor")),
            "vendor_ohlc": {k: _evidence_value(v) for k, v in prices.items()},
            "requested_resample_frequency": _evidence_value(frequency),
            "source_projection_version": row.get("projection_version"),
            "issues": issues,
        })
    duplicate_rows = sum(len(v) - 1 for v in by_instant.values())
    conflicting_instants = sum(len(set(v)) > 1 for v in by_instant.values())
    ordered = sorted(by_instant)
    steps = [(b - a) / 1_000_000_000 for a, b in zip(ordered, ordered[1:])]
    backwards = sum(b < a for a, b in zip(clocks, clocks[1:]))
    minute_reference = frequencies == {"1min"}
    if not candidates:
        reasons.add("empty_vendor_view")
    if duplicate_rows:
        reasons.add("duplicate_vendor_instants")
    if conflicting_instants:
        reasons.add("conflicting_vendor_observations")
    if backwards:
        reasons.add("vendor_rows_out_of_order")
    if issue_counts:
        reasons.add("vendor_observations_require_diagnosis")
    if minute_reference and any(step > 60 for step in steps):
        reasons.add("observed_timestamp_spacing_exceeds_requested_minute")
    return {
        "schema": SCHEMA, "authority": "RESEARCH_ONLY_VENDOR_SOURCE",
        "source_state": "empty" if not candidates else "diagnostic_candidates",
        "pair_candidate": expected_pair,
        "source": {**view.metadata(), "source_receipt_id": receipt_id,
                   "source_request_path": view.source_request_path},
        "dataos_identity_admitted": False, "pit_backtest_eligible": False,
        "redistribution_admitted": False, "monitoring_admitted": False,
        "candidate_observations": candidates,
        "eligible_observations": [],  # No local flag or apparently perfect data can admit a feed.
        "withheld_reasons": sorted(reasons),
        "diagnostics": {
            "rows": len(candidates), "unique_valid_timestamp_instants": len(ordered),
            "duplicate_instant_rows": duplicate_rows,
            "conflicting_ohlc_instants": conflicting_instants,
            "out_of_order_valid_timestamp_steps": backwards,
            "requested_resample_frequencies": sorted(frequencies),
            "cadence_reference_seconds": 60 if minute_reference else None,
            "observed_timestamp_steps_gt_reference": sum(step > 60 for step in steps) if minute_reference else None,
            "maximum_observed_timestamp_step_seconds": max(steps, default=None),
            "timestamp_spacing_proves_missing_data": False,
            "first_vendor_instant_utc": pd.Timestamp(ordered[0], tz="UTC").isoformat() if ordered else None,
            "last_vendor_instant_utc": pd.Timestamp(ordered[-1], tz="UTC").isoformat() if ordered else None,
            "value_issue_counts": dict(sorted(issue_counts.items())),
        },
    }


def read_forex_watch_source(day: str, receipt_id: str, *, expected_pair: str,
                            root: Path = DEFAULT_ARCHIVE, receipt_path: Path | None = None,
                            max_rows: int = MAX_ROWS, check_mount: bool = True) -> dict[str, Any]:
    """Select an exact immutable research receipt; integrity failures propagate."""
    if type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS:
        raise TiingoViewRefusal("invalid Forex diagnostic row cap")
    view = read_research_view("forex-bars", day, receipt_id, root=root,
                             purpose="INSPECTION", max_rows=max_rows,
                             receipt_path=receipt_path, check_mount=check_mount)
    return diagnose_forex_view(view, expected_pair=expected_pair, receipt_id=receipt_id)
