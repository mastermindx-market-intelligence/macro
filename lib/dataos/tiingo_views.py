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
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import parse_qs, urlsplit

from collectors.tiingo_archive import decode_boats

SCHEMA_VERSION = "mastermind.tiingo.research_views.v2"

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
    """A date label stays a date, and a supplied time must be an aware instant."""
    from lib.dataos.temporal import utc
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9](?:\.[0-9]{1,9})?)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9]))?", value
    ):
        raise ValueError("invalid vendor date or timezone-aware datetime")
    day = datetime.fromisoformat(value[:10]).date().isoformat()
    if len(value) > 10:
        utc(value)
    return day


def _number(value: Any) -> float | None:
    """Null is missing; malformed content must not be silently turned into null."""
    if value is None:
        return None
    if type(value) not in (int, float, str):
        raise ValueError("vendor metric must be numeric, not boolean or structured data")
    if isinstance(value, str) and not re.fullmatch(
        r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value
    ):
        raise ValueError("invalid numeric vendor text")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError("vendor number cannot be represented") from None
    if not math.isfinite(result):
        raise ValueError("non-finite vendor number")
    if result == 0 and Decimal(str(value)) != 0:
        raise ValueError("nonzero vendor number underflows the research float representation")
    return result


def _integer_volume(value: Any) -> int | None:
    """Tiingo documents share volume as int64; do not round through float64."""
    if value is None:
        return None
    if type(value) not in (str, int, float):
        raise ValueError("share volume must be a nonnegative integer")
    try:
        exact = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("invalid share volume") from None
    if not exact.is_finite() or exact < 0 or exact > 2**63 - 1 or exact != exact.to_integral_value():
        raise ValueError("share volume must be a nonnegative int64")
    return int(exact)


def _response_identity(item: dict[str, Any], requested: str) -> tuple[str | None, str | None]:
    ticker, permanent = item.get("ticker"), item.get("permaTicker")
    for field in ("ticker", "permaTicker"):
        if field in item and (not isinstance(item[field], str) or not item[field].strip()):
            raise ValueError("invalid vendor identity field")
    if ticker is not None and ticker != requested and permanent != requested:
        raise ValueError("response ticker does not match requested source identifier")
    return ticker, permanent


def _required_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Tiingo source response expected JSON array")
    if any(not isinstance(row, dict) for row in payload):
        raise ValueError("non-mapping Tiingo record")
    return payload


def equity_eod(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    sym = _source_symbol(receipt)
    rows, dates = [], set()
    for item in _required_rows(payload):
        _response_identity(item, sym)
        market_day = _date(item.get("date"))
        if market_day in dates:
            raise ValueError("duplicate EOD market date in source response")
        dates.add(market_day)
        row: dict[str, Any] = {
            **ctx, "ticker_vendor": sym, "market_date": market_day,
            "source_date_vendor": item["date"],
            "session": "regular_eod_vendor", "venue_scope": "vendor_eod_aggregation",
            "adjustment_asof_utc": ctx["source_observed_at_utc"],
            "adjustment_basis_detail": "vendor_adjusted_not_historical_vintage",
            "timestamp_source": "vendor_market_date_only",
        }
        for vendor, canon in EOD_FIELDS.items():
            row[canon] = (_integer_volume(item.get(vendor))
                          if vendor in {"volume", "adjVolume"} else _number(item.get(vendor)))
        rows.append(row)
    return rows


def _as_reported(request_path: str) -> bool | None:
    values = parse_qs(urlsplit(request_path).query, keep_blank_values=True).get("asReported")
    if values is None:
        return None
    if len(values) != 1 or values[0].lower() not in {"true", "false"}:
        raise ValueError("ambiguous or invalid asReported selection")
    return values[0].lower() == "true"


def fundamentals_statements(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    symbol = _source_symbol(receipt)
    output, keys = [], set()
    as_reported = _as_reported(receipt.get("request_path", ""))
    for report in _required_rows(payload):
        statements = report.get("statementData")
        if not isinstance(statements, dict) or not statements:
            raise ValueError("expected nonempty nested statementData object")
        released = report.get("date")
        _date(released)
        fiscal_year, fiscal_quarter = report.get("year"), report.get("quarter")
        if type(fiscal_year) is not int or not 1 <= fiscal_year <= 9999:
            raise ValueError("fiscal year must be a positive calendar-year integer")
        if type(fiscal_quarter) is not int or not 0 <= fiscal_quarter <= 4:
            raise ValueError("fiscal quarter must be 0 (annual) or 1-4")
        _, permanent = _response_identity(report, symbol)
        report_count = 0
        for statement_type, items in statements.items():
            if not isinstance(statement_type, str) or not statement_type.strip() or not isinstance(items, list):
                raise ValueError("unexpected statement section type")
            for metric in items:
                if (not isinstance(metric, dict) or not isinstance(metric.get("dataCode"), str)
                        or not metric["dataCode"].strip() or "value" not in metric):
                    raise ValueError("malformed financial metric")
                code = metric["dataCode"]
                key = (released, fiscal_year, fiscal_quarter, statement_type, code)
                if key in keys:
                    raise ValueError("duplicate statement metric for the same release/period/section")
                keys.add(key)
                output.append({
                    **ctx, "ticker_or_permaticker_vendor": symbol,
                    "permaticker_vendor": permanent,
                    "statement_public_release_date_vendor": released,
                    "statement_public_release_is_vendor_claim": True,
                    "source_vintage_observed_at_utc": ctx["source_observed_at_utc"],
                    "fiscal_year": fiscal_year, "fiscal_quarter": fiscal_quarter,
                    "statement_type": statement_type, "metric_code": code,
                    "metric_value": _number(metric["value"]),
                    "metric_value_present": metric["value"] is not None,
                    "metric_unit_status": "REQUIRES_VENDOR_DEFINITION",
                    "requested_as_reported": as_reported,
                    "restatements_may_exist": as_reported is not True,
                    "actual_upstream_available_at_utc": None,
                    "temporal_profile": "REVISABLE_RELEASE",
                })
                report_count += 1
        if report_count == 0:
            raise ValueError("nonempty statement response contains no metrics")
    return output


def fundamentals_daily(payload: Any, receipt: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = receipt_context(receipt)
    symbol = _source_symbol(receipt)
    output, dates = [], set()
    for item in _required_rows(payload):
        market_day = _date(item.get("date"))
        if market_day in dates:
            raise ValueError("duplicate daily fundamental date in source response")
        dates.add(market_day)
        _, permanent = _response_identity(item, symbol)
        metrics = {k: v for k, v in item.items() if k not in {"date", "ticker", "permaTicker"}}
        if not metrics:
            raise ValueError("daily fundamental row contains no metrics")
        for key, value in metrics.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("invalid daily metric code")
            output.append({
                **ctx, "ticker_or_permaticker_vendor": symbol, "permaticker_vendor": permanent,
                "market_date": market_day, "source_date_vendor": item["date"],
                "metric_code": key, "metric_value": _number(value),
                "metric_value_present": value is not None,
                "metric_unit_status": "REQUIRES_VENDOR_DEFINITION",
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


def _research_json(raw: bytes) -> Any:
    """Read-side validation only: never repair or overwrite original source bytes."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate field in source JSON")
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError("non-standard non-finite source JSON value")

    def numeric_text(text):
        # Preserve decimal/exponent tokens until the field contract decides
        # float versus int64. Passing volume through float64 loses large shares.
        _number(text)
        return text

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite, parse_float=numeric_text)


def research_rows(raw: bytes, receipt: dict[str, Any]) -> list[dict[str, Any]] | None:
    """None means archived source lacks a reviewed L1 projector.

    No unsupported source is silently reclassified as normalized data.
    Source coverage and usable L1 coverage are separate denominators.
    """
    source = receipt.get("source")
    if receipt.get("schema") == "mastermind.tiingo.boats_firehose_receipt.v1":
        return boats_messages(raw.splitlines(), receipt)
    if source == "eod-bars":
        return equity_eod(_research_json(raw), receipt)
    if source == "fund-statements":
        return fundamentals_statements(_research_json(raw), receipt)
    if source == "fund-daily":
        return fundamentals_daily(_research_json(raw), receipt)
    if source in _INTRADAY_SOURCES:
        return intraday_history(_research_json(raw), receipt)
    if source == "crypto-bars":
        return crypto_history(_research_json(raw), receipt)
    if source in {"splits", "distributions"}:
        return corporate_action_history(_research_json(raw), receipt)
    if source in {"fund-fee-history", "distribution-yield"}:
        return historical_metrics(_research_json(raw), receipt)
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
