"""Read existing Radar artifacts and augment the existing banner payload in memory.

No collector, model execution, score recalibration, ledger write, scheduler,
publication or second banner is introduced. Existing rr_banner.v1 fields retain
their meanings. Callers own independent per-market calendar references, source
entitlements, atomic publication and client integration. A passing component
suite does not qualify those production boundaries.

Audited native pointers:
  regime/latest.json.risk_radar                    US
  china_regime/latest.json.risk_radar              CN
  hk_regime/latest.json.risk_radar                 HK
  canada_regime/latest.json.risk_radar             CA
  intl/latest.json.records[cc].risk_radar          other requested profiles

The market universe comes from the caller's explicit expected-session manifest,
not from whatever files happen to exist. Date freshness is assessed against that
independent reference, never the enclosing JSON's build/date field.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.risk_warning_projection import SET_SCHEMA, project_warning_set

_NATIVE_PATHS = {
    "us": "regime/latest.json", "cn": "china_regime/latest.json",
    "hk": "hk_regime/latest.json", "ca": "canada_regime/latest.json",
}
_MAX_SOURCE_BYTES = 16 * 1024 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _nonfinite_json(token):
    raise ValueError("non-finite JSON numeric literal: " + token)


def _read(root: Path, relative: str) -> tuple[Any, dict]:
    receipt = {"path": relative, "sha256": None, "status": "missing_file"}
    try:
        with (root / relative).open("rb") as handle:
            raw = handle.read(_MAX_SOURCE_BYTES + 1)
    except FileNotFoundError:
        return None, receipt
    except OSError:
        receipt["status"] = "unreadable_file"
        return None, receipt
    if len(raw) > _MAX_SOURCE_BYTES:
        receipt["status"] = "source_too_large"
        return None, receipt
    receipt["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_nonfinite_json)
    except (ValueError, UnicodeError, RecursionError):
        receipt["status"] = "invalid_json"
        return None, receipt
    if not isinstance(value, dict):
        receipt["status"] = "invalid_root"
        return None, receipt
    receipt["status"] = "ok"
    return value, receipt


def _previous_rows(payload: Mapping) -> dict:
    projection = payload.get("warning_projection")
    if not isinstance(projection, Mapping) or projection.get("schema") != SET_SCHEMA:
        return {}
    rows = projection.get("rows")
    if not isinstance(rows, list):
        return {}
    result = {}
    duplicates = set()
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("market"), str):
            continue
        market = row["market"]
        if market in result:
            duplicates.add(market)
        result[market] = row
    for market in duplicates:
        del result[market]  # ambiguous cache is not a trusted prior assertion
    return result


def augment_banner_payload(payload: Any, *, data_root: str | Path,
                           expected_sessions: Any, input_qualities: Any = None) -> dict:
    """Return an additive copy; read existing files, write nothing.

    `expected_sessions` must be supplied by the existing calendar/profile owner.
    This adapter intentionally has no US-calendar fallback for other markets.
    No exposure-log consumer should reinterpret the new display projection as
    a legacy extreme alert or an independently validated model trial.
    """
    if not isinstance(payload, Mapping) or payload.get("schema") != "rr_banner.v1":
        raise ValueError("target must be the existing rr_banner.v1 payload")
    # Validate/normalize configuration before touching the filesystem. Invalid or
    # absent session values remain explicit unavailable rows, not fake freshness.
    skeleton = project_warning_set({}, expected_sessions)
    markets = [row["market"] for row in skeleton["rows"]]
    normalized_sessions = {row["market"]: row["expected_session"] for row in skeleton["rows"]}
    root = Path(data_root)
    snapshots, receipts = {}, {}
    cache = {}
    for market in markets:
        relative = _NATIVE_PATHS.get(market, "intl/latest.json")
        if relative not in cache:
            cache[relative] = _read(root, relative)
        source, file_receipt = cache[relative]
        receipt = dict(file_receipt)
        receipts[market] = receipt
        if source is None:
            snapshots[market] = None
            continue
        if market in _NATIVE_PATHS:
            receipt["pointer"] = "/risk_radar"
            snapshot = source.get("risk_radar")
        else:
            receipt["pointer"] = f"/records[cc={market.upper()}]/risk_radar"
            records = source.get("records")
            if not isinstance(records, list):
                receipt["status"] = "invalid_records"
                snapshots[market] = None
                continue
            matches = [row for row in records if isinstance(row, Mapping)
                       and isinstance(row.get("cc"), str) and row["cc"].lower() == market]
            if len(matches) != 1:
                receipt["status"] = "duplicate_market_records" if matches else "missing_market_record"
                snapshots[market] = None
                continue
            snapshot = matches[0].get("risk_radar")
        if not isinstance(snapshot, Mapping):
            receipt["status"] = "missing_radar"
            snapshot = None
        snapshots[market] = snapshot
    result = deepcopy(dict(payload))
    result["warning_projection"] = project_warning_set(
        snapshots, normalized_sessions, previous=_previous_rows(payload),
        input_qualities=input_qualities,
    )
    result["warning_projection_sources"] = receipts
    return result
