"""Tiingo L0 to L1 research-only views in existing Data OS vocabulary.

Source authority: collectors.tiingo_archive immutable raw receipts.
This is a vendor-specific *provisional* reader. It does not change canonical
L2 security identity, historical availability, licensing, or live price priority.

Backtest admission is NEVER inferred from a 2026 fetch of years-old revised
data. Every row is tagged with a receipt vintage, vendor symbol, and explicit
not-yet-PIT-eligible flags. Raw price is kept distinct from vendor-adjusted
series and corporate-action data. Full historical PIT training requires a
canonical Data OS as-of identity / universe & availability decision.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import parse_qs, urlsplit

from collectors.tiingo_archive import decode_boats

SCHEMA_VERSION = "mastermind.tiingo.research_views.v1"

OHLC = ("open", "high", "low", "close")
EOD_FIELDS = {
    **{x: x + "_raw" for x in OHLC},
    **{"adj" + x.capitalize(): x + "_tradj" for x in OHLC},
    "volume": "volume_raw", "adjVolume": "volume_vendor_adjusted",
    "divCash": "dividend_cash", "splitFactor": "split_factor",
}


def receipt_context(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_vendor": "tiingo",
        "dataset_source": receipt.get("source", "boats-firehose"),
        "source_sha256": receipt["raw_sha256"],
        "source_observed_at_utc": receipt.get("observed_at_utc")
                                 or receipt.get("first_received_at_utc"),
        "source_rights_admitted": False,
        "dataos_identity_admitted": False,
        "pit_backtest_eligible": False,
        "vendor_historical_availability": "UNVERIFIED",
        "source_view_schema": SCHEMA_VERSION,
    }


def _date(value: Any) -> str:
    if not isinstance(value, str) or len(value) < 10:
        raise ValueError("missing date")
    dt = datetime.fromisoformat(value[:10])
    return dt.date().isoformat()


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _required_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Tiingo source response expected JSON array")
    if any(not isinstance(row, dict) for row in payload):
        raise ValueError("non-mapping Tiingo record")
    return payload


def equity_eod(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    sym = receipt.get("symbol")
    if not sym:
        raise ValueError("equity EOD source receipt missing ticker")
    rows = []
    for item in _required_rows(payload):
        if not item.get("date"):
            raise ValueError("missing EOD market date")
        row: dict[str, Any] = {
            **ctx, "ticker_vendor": sym,
            "market_date": _date(item["date"]),
            "session": "regular_eod_vendor",
            "venue_scope": "vendor_eod_aggregation",
            "adjustment_asof_utc": ctx["source_observed_at_utc"],
            "adjustment_basis_detail": "vendor_adjusted_not_historical_vintage",
            "timestamp_source": "vendor_market_date_only",
        }
        for vendor, canon in EOD_FIELDS.items():
            row[canon] = _number(item.get(vendor))
        rows.append(row)
    return rows


def _as_reported(request_path: str) -> bool | None:
    p = parse_qs(urlsplit(request_path).query)
    val = p.get("asReported", [])
    if not val:
        return None
    return val[-1].lower() == "true"


def fundamentals_statements(payload: Any, receipt: dict[str, Any]
                            ) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    output = []
    as_reported = _as_reported(receipt.get("request_path", ""))
    for report in _required_rows(payload):
        released = report.get("date")
        statements = report.get("statementData", {})
        if statements is None:
            statements = {}
        if not isinstance(statements, dict):
            raise ValueError("expected nested statementData object")
        for statement_type, items in statements.items():
            if not isinstance(items, list):
                raise ValueError("unexpected statement section type")
            for metric in items:
                if not isinstance(metric, dict) or not metric.get("dataCode"):
                    raise ValueError("malformed financial metric")
                output.append({
                    **ctx,
                    "ticker_or_permaticker_vendor": receipt.get("symbol"),
                    "statement_public_release_date_vendor": released,
                    "statement_public_release_is_vendor_claim": True,
                    "source_vintage_observed_at_utc": ctx["source_observed_at_utc"],
                    "fiscal_year": report.get("year"),
                    "fiscal_quarter": report.get("quarter"),
                    "statement_type": statement_type,
                    "metric_code": str(metric["dataCode"]),
                    "metric_value": _number(metric.get("value")),
                    "requested_as_reported": as_reported,
                    "restatements_may_exist": not (as_reported is True),
                    "actual_upstream_available_at_utc": None,
                    "temporal_profile": "REVISABLE_RELEASE",
                })
    return output


def fundamentals_daily(payload: Any, receipt: dict[str, Any]
                       ) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    output = []
    for item in _required_rows(payload):
        if "date" not in item:
            raise ValueError("daily fundamentals without date")
        market_day = _date(item["date"])
        for key, value in item.items():
            if key == "date":
                continue
            output.append({
                **ctx,
                "ticker_or_permaticker_vendor": receipt.get("symbol"),
                "market_date": market_day,
                "metric_code": key,
                "metric_value": _number(value),
                "actual_upstream_available_at_utc": None,
                "temporal_profile": "SNAPSHOT_SERIES",
            })
    return output


def boats_messages(lines: Iterable[bytes], receipt: dict[str, Any]
                   ) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    output: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        outer = json.loads(line)
        raw = outer["raw_message"]
        arrival = outer["received_at"]
        event = decode_boats(json.loads(raw), arrival)
        if event is None:
            continue
        output.append({
            **ctx, **event, "is_nbbo": False,
            "venue_scope": "single_ats",
            "materialization_disposition": "RESEARCH_ONLY",
            "transport_continuity": "NOT_PROVEN",
            "raw_message_sha256": hashlib.sha256(
                raw.encode("utf-8")).hexdigest(),
        })
    return output


def research_rows(raw: bytes, receipt: dict[str, Any]) -> list[dict[str, Any]] | None:
    """None means archived source lacks a reviewed L1 projector.

    No unsupported source is silently reclassified as normalized data.
    Source coverage and usable L1 coverage are separate denominators.
    """
    source = receipt.get("source")
    if receipt.get("schema") == "mastermind.tiingo.boats_firehose_receipt.v1":
        return boats_messages(raw.splitlines(), receipt)
    if source == "eod-bars":
        return equity_eod(json.loads(raw), receipt)
    if source == "fund-statements":
        return fundamentals_statements(json.loads(raw), receipt)
    if source == "fund-daily":
        return fundamentals_daily(json.loads(raw), receipt)
    return None
