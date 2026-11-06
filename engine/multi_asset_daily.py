"""Non-voting, session-labelled snapshots; NOT event-time or forecast observations.

Uses existing daily-source owners. Session labels are never converted into made-up
quote timestamps. A capture proves access to this snapshot now, not original vintage.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from engine.multi_asset_context import authority, instant, measured_comparison, stamp

SCHEMA = "mastermind.multi_asset_daily_context/v1"
METHOD = "same_us_cash_session_snapshot.v1"
SHA = re.compile(r"^[0-9a-f]{64}$")
# Exposure describes the wrapper, not the listing jurisdiction or the entire asset.
UNIVERSE = (
    ("SPY", "US large-cap equities", "美国大盘股", "equity", "US"),
    ("EFA", "Developed ex-US equities", "美国以外发达市场股票", "equity", "DM_EX_US"),
    ("EEM", "Emerging-market equities", "新兴市场股票", "equity", "EM"),
    ("FXI", "China large-cap HK-listed proxy", "中国大型港股代理", "equity", "CHINA_HK"),
    ("KWEB", "China internet offshore proxy", "中国离岸互联网代理", "equity", "CHINA_OFFSHORE"),
    ("GLD", "Gold bullion proxy", "黄金代理", "gold", "GLOBAL"),
    ("HYG", "US high-yield corporate bonds", "美国高收益公司债", "credit", "US"),
    ("TLT", "Long US Treasury duration", "美国长期国债", "rates", "US"),
    ("SHY", "1-3 year US Treasuries - not cash", "1-3年美国国债，非现金", "rates", "US"),
    ("USO", "Oil-futures fund proxy - not spot oil", "原油期货基金代理，非现货", "energy", "GLOBAL"),
    ("IBIT", "US-listed bitcoin trust proxy", "美国上市比特币信托代理", "crypto", "GLOBAL"),
)
META = {r[0]: r[1:] for r in UNIVERSE}


def _day(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("iso_session_required")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("iso_session_required") from exc
    if parsed.isoformat() != value:
        raise ValueError("iso_session_required")
    return value


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("ascii")).hexdigest()


def semantic_context(value: Mapping[str, Any]) -> dict[str, Any]:
    """Do not manufacture a new market observation when only capture/render time changes."""
    return {k: copy.deepcopy(v) for k, v in value.items() if k not in ("captured_at", "context_digest")}


def _valid_number(value: Any, *, positive: bool) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value)) and (value > 0 if positive else value >= 0)
    except (OverflowError, ValueError):
        return False


def compose_daily_context(sources: Sequence[Mapping[str, Any]], *, captured_at: str,
                          expected_session: str, start_session: str, end_session: str,
                          horizon_sessions: int = 5) -> dict[str, Any]:
    """Compare one explicit session window; never fill gaps or pick a winning window."""
    capture = stamp(instant(captured_at))
    expected, start, end = map(_day, (expected_session, start_session, end_session))
    if start >= end or end > expected:
        raise ValueError("invalid_settled_window")
    if not isinstance(horizon_sessions, int) or isinstance(horizon_sessions, bool) or not 1 <= horizon_sessions <= 252:
        raise ValueError("invalid_horizon_sessions")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)) or len(sources) > 128:
        raise ValueError("bounded_sources_required")
    counts = Counter(s.get("instrument_id") for s in sources
                     if isinstance(s, Mapping) and isinstance(s.get("instrument_id"), str))
    rows: list[dict[str, Any]] = []
    by_symbol: dict[str, list[Mapping[str, Any]]] = {}
    invalid_sources = 0
    for source in sources:
        if (not isinstance(source, Mapping) or not isinstance(source.get("instrument_id"), str)
                or source["instrument_id"] not in META):
            invalid_sources += 1
            continue
        by_symbol.setdefault(source["instrument_id"], []).append(source)
    for ticker in sorted(META):
        label_en, label_zh, asset_class, exposure = META[ticker]
        candidates = by_symbol.get(ticker, [])
        source = candidates[0] if len(candidates) == 1 else {}
        reasons: list[str] = []
        value = None
        source_hash = source.get("source_digest")
        if counts[ticker] > 1:
            reasons.append("duplicate_source")
        elif not candidates:
            reasons.append("source_missing")
        elif source.get("read_error"):
            error = source["read_error"]
            reasons.append(error if error in ("source_missing", "source_unreadable", "source_changed_during_capture",
                                              "source_shape_invalid", "source_too_large", "source_symlink_refused")
                           else "source_unreadable")
        elif not isinstance(source_hash, str) or not SHA.fullmatch(source_hash):
            reasons.append("source_digest_missing")
        elif source.get("currency") != "USD" or source.get("return_basis") != "total_return":
            reasons.append("source_basis_or_currency_mismatch")
        elif source.get("listing_market") != "US":
            reasons.append("listing_session_mismatch")
        else:
            prices = source.get("prices")
            if not isinstance(prices, Mapping):
                reasons.append("source_shape_invalid")
            elif start not in prices:
                reasons.append("start_session_missing")
            elif end not in prices:
                reasons.append("end_session_missing")
            elif not _valid_number(prices[start], positive=True) or not _valid_number(prices[end], positive=False):
                reasons.append("invalid_endpoint_price")
            else:
                try:
                    value = prices[end] / prices[start] - 1.0
                    if not math.isfinite(value):
                        reasons.append("return_overflow"); value = None
                except (OverflowError, ZeroDivisionError):
                    reasons.append("return_overflow")
        last = source.get("last_source_session")
        try:
            last = _day(last) if last is not None else None
        except ValueError:
            last = None
        rows.append({
            "instrument_id": ticker, "label_en": label_en, "label_zh": label_zh,
            "asset_class": asset_class, "exposure_region": exposure, "listing_market": "US",
            "currency": "USD", "return_basis": "total_return",
            "start_session": start, "end_session": end, "last_source_session": last,
            "status": "UNAVAILABLE" if reasons else "OBSERVED", "reasons": reasons,
            "absolute_return": value, "relative_return": None, "classification": None,
            "source_ref": "data/yahoo/" + ticker + ".parquet",
            "source_digest": source_hash if isinstance(source_hash, str) and SHA.fullmatch(source_hash) else None,
            "evidence_family_id": "yahoo_daily_adjusted_prices",
        })
    benchmark = next(row for row in rows if row["instrument_id"] == "SPY")
    comparable = 0
    for row in rows:
        if row["instrument_id"] == "SPY" or row["status"] != "OBSERVED":
            continue
        if benchmark["status"] != "OBSERVED":
            row["comparison_status"] = "UNAVAILABLE"
            row["reasons"].append("benchmark_unavailable")
            continue
        arithmetic = measured_comparison(row["absolute_return"], benchmark["absolute_return"])
        row.update({key: arithmetic[key] for key in ("relative_return", "classification")})
        row["reasons"].extend(arithmetic["reasons"])
        row["comparison_status"] = "UNAVAILABLE" if arithmetic["reasons"] else "OBSERVED"
        comparable += not arithmetic["reasons"]
    observed = sum(row["status"] == "OBSERVED" for row in rows)
    reasons = []
    if not comparable:
        status = "UNAVAILABLE"
        reasons.append("benchmark_unavailable" if benchmark["status"] != "OBSERVED" else "no_comparable_returns")
    elif end < expected:
        status = "STALE"
        reasons.append("older_than_expected_session")
    elif observed < len(rows) or comparable < len(rows) - 1 or invalid_sources:
        status = "PARTIAL"
    else:
        status = "AVAILABLE"
    result = {
        "schema": SCHEMA, "method_version": METHOD, "captured_at": capture,
        "alignment_basis": "US_CASH_SESSION_LABEL_NOT_QUOTE_TIMESTAMP",
        "window": {"start_session": start, "end_session": end, "expected_session": expected,
                   "horizon_sessions": horizon_sessions, "calendar_owner": "lib.nyse_calendar",
                   "listing_timezone": "America/New_York"},
        "status": status, "reasons": reasons, "benchmark_instrument_id": "SPY",
        "benchmark_return": benchmark["absolute_return"], "base_currency": "USD",
        "rows": rows, "coverage": {"requested": len(META), "observed": observed,
                                    "comparable": comparable, "invalid_sources": invalid_sources},
        "source_kind": "captured_mutable_daily_cache",
        "provider_available_at": None, "historical_original_availability_proven": False,
        "capture_coherence": "individually_hashed_not_atomic_bundle",
        "display_only": True, "no_predictive_claim": True, "authority": authority(),
        "limitations": ["not_intraday", "not_native_foreign_market_returns", "not_observed_fund_flows",
                        "not_point_in_time_backtest_evidence", "funds_may_overlap",
                        "cash_is_separate_from_short_duration_funds", "not_an_allocation_recommendation"],
    }
    result["context_digest"] = _digest(semantic_context(result))
    return result


def validate_daily_context(value: Any) -> dict[str, Any]:
    """Validate a non-voting derived projection; a hash is not source authentication."""
    keys = {"schema", "method_version", "captured_at", "alignment_basis", "window", "status",
            "reasons", "benchmark_instrument_id", "benchmark_return", "base_currency", "rows",
            "coverage", "source_kind", "provider_available_at", "historical_original_availability_proven",
            "capture_coherence", "display_only", "no_predictive_claim", "authority", "limitations",
            "context_digest"}
    if not isinstance(value, Mapping) or set(value) != keys or value.get("schema") != SCHEMA or value.get("method_version") != METHOD:
        raise ValueError("multi_asset_context_schema_invalid")
    auth = value.get("authority")
    if (not isinstance(auth, Mapping) or set(auth) != set(authority())
            or any(v is not False for v in auth.values()) or value.get("display_only") is not True
            or value.get("no_predictive_claim") is not True
            or value.get("historical_original_availability_proven") is not False
            or value.get("provider_available_at") is not None):
        raise ValueError("multi_asset_context_authority_invalid")
    captured = instant(value.get("captured_at"))
    try:
        if value.get("context_digest") != _digest(semantic_context(value)):
            raise ValueError("multi_asset_context_digest_invalid")
        window, rows, coverage = value["window"], value["rows"], value["coverage"]
        if (not isinstance(window, Mapping) or set(window) != {"start_session", "end_session", "expected_session",
                "horizon_sessions", "calendar_owner", "listing_timezone"}
                or not isinstance(rows, list) or len(rows) != len(META)
                or not all(isinstance(r, Mapping) and isinstance(r.get("instrument_id"), str) for r in rows)
                or [r["instrument_id"] for r in rows] != sorted(META)):
            raise ValueError("multi_asset_context_shape_invalid")
        start, end, expected = (_day(window[k]) for k in ("start_session", "end_session", "expected_session"))
        if (not start < end <= expected <= captured.date().isoformat()
                or type(window["horizon_sessions"]) is not int or not 1 <= window["horizon_sessions"] <= 252
                or window["calendar_owner"] != "lib.nyse_calendar"
                or window["listing_timezone"] != "America/New_York"):
            raise ValueError("multi_asset_context_window_invalid")
        constants = {"alignment_basis": "US_CASH_SESSION_LABEL_NOT_QUOTE_TIMESTAMP", "base_currency": "USD",
                     "benchmark_instrument_id": "SPY", "source_kind": "captured_mutable_daily_cache",
                     "capture_coherence": "individually_hashed_not_atomic_bundle"}
        if any(value[k] != v for k, v in constants.items()):
            raise ValueError("multi_asset_context_basis_invalid")
        row_keys = {"instrument_id", "label_en", "label_zh", "asset_class", "exposure_region", "listing_market",
                    "currency", "return_basis", "start_session", "end_session", "last_source_session", "status",
                    "reasons", "absolute_return", "relative_return", "classification", "source_ref", "source_digest",
                    "evidence_family_id"}
        benchmark = next(r for r in rows if r["instrument_id"] == "SPY")
        observed = comparable = 0
        for row in rows:
            ticker = row["instrument_id"]
            label_en, label_zh, asset_class, exposure = META[ticker]
            metadata = dict(label_en=label_en, label_zh=label_zh, asset_class=asset_class,
                            exposure_region=exposure, listing_market="US", currency="USD", return_basis="total_return",
                            start_session=start, end_session=end, source_ref="data/yahoo/" + ticker + ".parquet",
                            evidence_family_id="yahoo_daily_adjusted_prices")
            if (set(row) - row_keys - {"comparison_status"} or not row_keys <= set(row)
                    or any(row[k] != v for k, v in metadata.items())
                    or row["status"] not in ("OBSERVED", "UNAVAILABLE")
                    or not isinstance(row["reasons"], list) or not all(isinstance(r, str) for r in row["reasons"])):
                raise ValueError("multi_asset_context_row_invalid")
            if row["last_source_session"] is not None:
                _day(row["last_source_session"])
            source_digest = row["source_digest"]
            if source_digest is not None and (not isinstance(source_digest, str) or not SHA.fullmatch(source_digest)):
                raise ValueError("multi_asset_context_source_invalid")
            if row["status"] == "UNAVAILABLE":
                if (not row["reasons"] or any(row[k] is not None for k in ("absolute_return", "relative_return", "classification"))
                        or "comparison_status" in row):
                    raise ValueError("multi_asset_context_missing_invalid")
                continue
            absolute = row["absolute_return"]
            if (isinstance(absolute, bool) or not isinstance(absolute, (int, float))
                    or not math.isfinite(absolute) or absolute < -1 or source_digest is None):
                raise ValueError("multi_asset_context_return_invalid")
            observed += 1
            if ticker == "SPY":
                if row["reasons"] or row["relative_return"] is not None or row["classification"] is not None or "comparison_status" in row:
                    raise ValueError("multi_asset_context_benchmark_invalid")
                continue
            arithmetic = (measured_comparison(absolute, benchmark["absolute_return"])
                          if benchmark["status"] == "OBSERVED"
                          else {"relative_return": None, "classification": None, "reasons": ["benchmark_unavailable"]})
            expected_status = "UNAVAILABLE" if arithmetic["reasons"] else "OBSERVED"
            if any(row[k] != arithmetic[k] for k in arithmetic) or row.get("comparison_status") != expected_status:
                raise ValueError("multi_asset_context_arithmetic_invalid")
            comparable += expected_status == "OBSERVED"
        if (not isinstance(coverage, Mapping) or set(coverage) != {"requested", "observed", "comparable", "invalid_sources"}
                or not all(type(v) is int and v >= 0 for v in coverage.values())
                or coverage["requested"] != len(META) or coverage["observed"] != observed or coverage["comparable"] != comparable
                or value["benchmark_return"] != benchmark["absolute_return"]):
            raise ValueError("multi_asset_context_coverage_invalid")
        expected_status = ("UNAVAILABLE" if not comparable else "STALE" if end < expected else
                           "PARTIAL" if observed < len(META) or comparable < len(META) - 1 or coverage["invalid_sources"] else "AVAILABLE")
        expected_reasons = (["benchmark_unavailable" if benchmark["status"] != "OBSERVED" else "no_comparable_returns"]
                            if not comparable else ["older_than_expected_session"] if end < expected else [])
        if value["status"] != expected_status or value["reasons"] != expected_reasons:
            raise ValueError("multi_asset_context_status_invalid")
        if value["limitations"] != ["not_intraday", "not_native_foreign_market_returns", "not_observed_fund_flows",
                "not_point_in_time_backtest_evidence", "funds_may_overlap",
                "cash_is_separate_from_short_duration_funds", "not_an_allocation_recommendation"]:
            raise ValueError("multi_asset_context_limits_invalid")
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("multi_asset_context_malformed") from exc
    return copy.deepcopy(dict(value))
