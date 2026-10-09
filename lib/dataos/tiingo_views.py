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
    if source in _INTRADAY_SOURCES:
        return intraday_history(json.loads(raw), receipt)
    if source == "crypto-bars":
        return crypto_history(json.loads(raw), receipt)
    if source in {"splits", "distributions"}:
        return corporate_action_history(json.loads(raw), receipt)
    if source in {"fund-fee-history", "distribution-yield"}:
        return historical_metrics(json.loads(raw), receipt)
    return None


# Additional historical products remain VENDOR views, not canonical price bases.
# In particular an FX/composite reference bar is not an exchange execution print.
# The existing raw archive, clock, identity and publication owners are unchanged.
_INTRADAY_SOURCES = {
    "boats-bars": ("BOATS", "single_ats", "overnight", "shares"),
    "iex-bars": ("IEX", "single_exchange", "vendor_request_session", "shares"),
    "equity-intraday-bars": (None, "vendor_equity_reference", "unqualified", "unqualified"),
    "forex-bars": (None, "vendor_fx_aggregation", "unqualified", "not_provided"),
}


def _vendor_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a vendor numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite vendor number")
    return result


def _source_symbol(receipt: dict[str, Any]) -> str:
    value = receipt.get("symbol")
    if not isinstance(value, str) or not value:
        raise ValueError("historical source requires its exact vendor symbol")
    return value


def intraday_history(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Source OHLC, not a fabricated canonical raw/adjusted or executable price."""
    from lib.dataos.temporal import utc
    source = receipt["source"]
    venue, scope, session, volume_unit = _INTRADAY_SOURCES[source]
    symbol = _source_symbol(receipt)
    ctx = receipt_context(receipt)
    query = parse_qs(urlsplit(receipt.get("request_path", "")).query)
    output = []
    for item in _required_rows(payload):
        if "ticker" in item and item["ticker"] != symbol:
            raise ValueError("historical bar ticker does not match source request")
        instant = item.get("date")
        utc(instant)  # validate only; preserve the original source text/nanoseconds
        record = {
            **ctx, "ticker_vendor": symbol, "bar_at_vendor": instant,
            "source_date_label": _date(instant), "venue": venue,
            "venue_scope": scope, "session": session,
            "requested_resample_frequency": query.get("resampleFreq", [None])[-1],
            "requested_after_hours": query.get("afterHours", [None])[-1],
            "is_nbbo": False, "executable_price_proven": False,
            "canonical_price_basis_admitted": False,
            "volume_unit_vendor": volume_unit,
            "volume_available": item.get("volume") is not None,
            "vendor_volume": _vendor_number(item.get("volume")),
            "projection_version": "tiingo.additional_history.v1",
        }
        for field in OHLC:
            record["vendor_" + field] = _vendor_number(item.get(field))
        output.append(record)
    return output


def crypto_history(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten nested pair bars without dropping currency or exchange scope."""
    from lib.dataos.temporal import utc
    ctx = receipt_context(receipt)
    query = parse_qs(urlsplit(receipt.get("request_path", "")).query)
    requested = set(query.get("tickers", [""])[-1].split(","))
    if not requested or "" in requested:
        raise ValueError("crypto historical view requires an explicit requested cohort")
    output = []
    seen = set()
    for pair in _required_rows(payload):
        symbol = pair.get("ticker")
        if not isinstance(symbol, str) or symbol not in requested or symbol in seen:
            raise ValueError("crypto response has unrequested/duplicated pair")
        seen.add(symbol)
        for item in _required_rows(pair.get("priceData")):
            instant = item.get("date")
            utc(instant)
            record = {
                **ctx, "ticker_vendor": symbol, "base_currency_vendor": pair.get("baseCurrency"),
                "quote_currency_vendor": pair.get("quoteCurrency"),
                "bar_at_vendor": instant, "source_date_label": _date(instant),
                "venue_scope": "vendor_crypto_aggregation", "is_nbbo": False,
                "requested_resample_frequency": query.get("resampleFreq", [None])[-1],
                "executable_price_proven": False, "canonical_price_basis_admitted": False,
                "volume_base_currency": _vendor_number(item.get("volume")),
                "volume_quote_currency": _vendor_number(item.get("volumeNotional")),
                "trades_done_vendor": _vendor_number(item.get("tradesDone")),
                "raw_exchange_detail_present": bool(pair.get("exchangeData")),
                "projection_version": "tiingo.additional_history.v1",
            }
            for field in OHLC:
                record["vendor_" + field] = _vendor_number(item.get(field))
            output.append(record)
    return output


def corporate_action_history(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Retain cancellations and dates. This never creates adjustment factors."""
    source = receipt["source"]
    ctx = receipt_context(receipt)
    symbol = _source_symbol(receipt)
    output = []
    for item in _required_rows(payload):
        if item.get("ticker", symbol) != symbol:
            raise ValueError("corporate action ticker does not match source request")
        ex_date = _date(item.get("exDate"))
        record = {
            **ctx, "ticker_vendor": symbol, "permaticker_vendor": item.get("permaTicker"),
            "ex_date_vendor": ex_date, "event_kind": source,
            "actual_upstream_available_at_utc": None,
            "eligible_for_factor_construction": False,
            "projection_version": "tiingo.additional_history.v1",
        }
        if source == "splits":
            record.update(
                split_from_vendor=_vendor_number(item.get("splitFrom")),
                split_to_vendor=_vendor_number(item.get("splitTo")),
                split_factor_vendor=_vendor_number(item.get("splitFactor")),
                split_status_vendor=item.get("splitStatus"),
                cancellation_reported=item.get("splitStatus") == "c",
            )
        else:
            record.update(
                distribution_vendor=_vendor_number(item.get("distribution")),
                distribution_frequency_vendor=item.get("distributionFrequency"),
                cancellation_reported=item.get("distributionFrequency") == "c",
                declaration_date_vendor=item.get("declarationDate"),
                payment_date_vendor=item.get("paymentDate"),
                record_date_vendor=item.get("recordDate"),
                distribution_currency_status="NOT_ESTABLISHED_FROM_THIS_RESPONSE",
            )
        output.append(record)
    return output


def historical_metrics(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    """Fee/yield metrics are kept in vendor units; percentages are not rescaled."""
    ctx = receipt_context(receipt)
    symbol = _source_symbol(receipt)
    date_field = "prospectusDate" if receipt["source"] == "fund-fee-history" else "date"
    output = []
    for item in _required_rows(payload):
        dated = _date(item.get(date_field))
        if "ticker" in item and item["ticker"] != symbol:
            raise ValueError("metric ticker does not match source request")
        for code, value in item.items():
            if code in {date_field, "ticker", "permaTicker"}:
                continue
            if isinstance(value, (dict, list, bool)):
                raise ValueError("unreviewed metric structure; retain original raw evidence")
            output.append({
                **ctx, "ticker_vendor": symbol, "source_date_label": dated,
                "source_date_role": date_field, "metric_code": code,
                "metric_value_vendor": _vendor_number(value),
                "metric_unit_status": "VENDOR_UNITS_NOT_REINTERPRETED",
                "actual_upstream_available_at_utc": None,
                "projection_version": "tiingo.additional_history.v1",
            })
    return output
