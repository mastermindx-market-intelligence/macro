"""Dated currency returns for country research, separate from regime features.

The incumbent strength feature is unchanged. This contract uses actual daily
quotes, a trailing three-calendar-month window, and exact quote conversion.
Same-day bars are excluded because the incumbent daily adapter can include
unfinished observations. A source reference is not a recorded retrieval clock.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from math import isclose, isfinite
from numbers import Real
import re
from urllib.parse import quote

SCHEMA = "intl_currency_observation.v1"
METHOD = "local_currency_usd_return_3_calendar_months_v1"
MAX_END_AGE_DAYS = 14
MAX_REFERENCE_GAP_DAYS = 7
SPECS = {
    "JP": ("JPY", "USDJPY=X", "local_per_USD", ("JPY=X", "USDJPY=X")),
    "KR": ("KRW", "USDKRW=X", "local_per_USD", ("USDKRW=X",)),
    "TW": ("TWD", "USDTWD=X", "local_per_USD", ("USDTWD=X",)),
    "IN": ("INR", "USDINR=X", "local_per_USD", ("USDINR=X",)),
    "AU": ("AUD", "AUDUSD=X", "USD_per_local", ("AUDUSD=X",)),
    "GB": ("GBP", "GBPUSD=X", "USD_per_local", ("GBPUSD=X",)),
    "EZ": ("EUR", "EURUSD=X", "USD_per_local", ("EURUSD=X",)),
}


def _day(value):
    if type(value) is date:
        return value
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _price(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        value = float(value)
    except (ValueError, OverflowError):
        return None
    return value if isfinite(value) and value > 0 else None


def reference_date(end: date) -> date:
    """Subtract three calendar months, clamping the day in shorter months."""
    month_index = end.year * 12 + end.month - 1 - 3
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(end.day, monthrange(year, month)[1]))


def _source_url(cc):
    return "https://finance.yahoo.com/quote/" + quote(SPECS[cc][3][0], safe="") + "/history/"


def provider_dataset_url(cc):
    return ("https://query1.finance.yahoo.com/v8/finance/chart/"
            + quote(SPECS[cc][1], safe="") + "?range=6mo&interval=1d")


def incumbent_source_context(cc, country_config):
    """Call only at the known incumbent-store assembly boundary.

    Existing frames do not carry retrieval receipts. Keep those fields null
    instead of substituting a calculation, file-modification or price date.
    """
    spec = SPECS.get(cc) if type(cc) is str else None
    if (not spec or type(country_config) is not dict
            or country_config.get("fx") != spec[1]
            or country_config.get("fx_invert") is not (spec[2] == "local_per_USD")):
        return None
    return {
        "provider": "Yahoo Finance", "collector": "intl_prices",
        "price_field": "close", "kind": "configured_store",
        "source_url": _source_url(cc), "dataset_url": None,
        "retrieved_at": None, "response_sha256": None, "provider_symbol": None,
    }


def captured_source_context(cc, *, retrieved_at, response_sha256, provider_symbol):
    """Source context for an independently retained incumbent-provider response."""
    if type(cc) is not str or cc not in SPECS:
        return None
    return {
        "provider": "Yahoo Finance", "collector": "intl_prices",
        "price_field": "close", "kind": "captured_response",
        "source_url": _source_url(cc), "dataset_url": provider_dataset_url(cc),
        "retrieved_at": retrieved_at, "response_sha256": response_sha256,
        "provider_symbol": provider_symbol,
    }


def _captured_day(source):
    try:
        retrieved = datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00"))
        return retrieved.astimezone(timezone.utc).date() if retrieved.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _observation_cutoff(source, today):
    # A retained intraday bar cannot become complete by replaying it later.
    # UTC capture-day exclusion is deliberately conservative at timezone edges.
    return min(today, _captured_day(source)) if source["kind"] == "captured_response" else today


def _valid_source(source, cc, today):
    keys = {"provider", "collector", "price_field", "kind", "source_url",
            "dataset_url", "retrieved_at", "response_sha256", "provider_symbol"}
    if (type(source) is not dict or set(source) != keys
            or source["provider"] != "Yahoo Finance"
            or source["collector"] != "intl_prices"
            or source["price_field"] != "close"
            or source["source_url"] != _source_url(cc)):
        return False
    if source["kind"] == "configured_store":
        return all(source[k] is None for k in (
            "dataset_url", "retrieved_at", "response_sha256", "provider_symbol"))
    if (source["kind"] != "captured_response"
            or source["dataset_url"] != provider_dataset_url(cc)
            or source["provider_symbol"] not in SPECS[cc][3]
            or type(source["response_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", source["response_sha256"]) is None
            or type(source["retrieved_at"]) is not str):
        return False
    captured = _captured_day(source)
    return captured is not None and captured <= today


def _return(start, end, convention):
    ratio = start / end if convention == "local_per_USD" else end / start
    value = (ratio - 1.0) * 100.0
    return value if ratio > 0 and isfinite(value) else None


def _digest(payload):
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _missing(cc, reason):
    return {"schema": SCHEMA, "cc": cc, "status": "unavailable", "reason": reason}


def build_currency_observation(cc, observations, *, today, source):
    """Select endpoints from actual (ISO date, positive quote) observations.

    Identical duplicates collapse. Conflicting selected dates are withheld.
    Missing/invalid quotes do not receive invented prices or dates.
    """
    if type(today) is not date:
        raise ValueError("invalid_currency_evaluation_date")
    if type(cc) is not str or cc not in SPECS:
        return _missing(cc, "unsupported_currency")
    if not _valid_source(source, cc, today):
        return _missing(cc, "source_unavailable")
    if not isinstance(observations, (list, tuple)):
        return _missing(cc, "observation_unavailable")
    cutoff = _observation_cutoff(source, today)
    by_day = {}
    for item in observations:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        observed, value = _day(item[0]), _price(item[1])
        if observed is None or observed >= cutoff or value is None:
            continue
        by_day.setdefault(observed, set()).add(value)
    if not by_day:
        return _missing(cc, "observation_unavailable")
    end = max(by_day)
    if (today - end).days > MAX_END_AGE_DAYS:
        return _missing(cc, "observation_stale")
    try:
        target = reference_date(end)
    except ValueError:
        return _missing(cc, "reference_unavailable")
    anchors = [d for d in by_day if d <= target]
    if not anchors:
        return _missing(cc, "reference_unavailable")
    start = max(anchors)
    if (target - start).days > MAX_REFERENCE_GAP_DAYS:
        return _missing(cc, "reference_too_distant")
    if len(by_day[end]) != 1 or len(by_day[start]) != 1:
        return _missing(cc, "conflicting_observation")
    start_quote, end_quote = next(iter(by_day[start])), next(iter(by_day[end]))
    value = _return(start_quote, end_quote, SPECS[cc][2])
    if value is None:
        return _missing(cc, "invalid_return")
    payload = {
        "schema": SCHEMA, "status": "available", "cc": cc,
        "currency": SPECS[cc][0], "counter_currency": "USD",
        "ticker": SPECS[cc][1], "quote_convention": SPECS[cc][2],
        "method": METHOD, "unit": "percent", "same_day_policy": "exclude",
        "reference_target": target.isoformat(),
        "start": {"date": start.isoformat(), "quote": start_quote},
        "end": {"date": end.isoformat(), "quote": end_quote},
        "value": value, "source": dict(source),
    }
    return {**payload, "evidence_sha256": _digest(payload)}


def currency_observation_view(raw, cc, *, today):
    """Validate identity/dates/provenance and recompute the displayed return.

    This verifies the serialized endpoints. The producer seeing the full series
    is responsible for selecting the latest eligible observations.
    """
    missing = {"available": False, "value": None, "quality": "missing",
               "start_date": None, "end_date": None, "source_url": None}
    if type(cc) is not str or cc not in SPECS or type(today) is not date or type(raw) is not dict:
        return missing
    keys = {"schema", "status", "cc", "currency", "counter_currency", "ticker",
            "quote_convention", "method", "unit", "same_day_policy",
            "reference_target", "start", "end", "value", "source", "evidence_sha256"}
    if (set(raw) != keys or raw["schema"] != SCHEMA or raw["status"] != "available"
            or raw["cc"] != cc or raw["currency"] != SPECS[cc][0]
            or raw["counter_currency"] != "USD" or raw["ticker"] != SPECS[cc][1]
            or raw["quote_convention"] != SPECS[cc][2] or raw["method"] != METHOD
            or raw["unit"] != "percent" or raw["same_day_policy"] != "exclude"
            or not _valid_source(raw["source"], cc, today)):
        return missing
    if any(type(raw[k]) is not dict or set(raw[k]) != {"date", "quote"} for k in ("start", "end")):
        return missing
    start, end = _day(raw["start"]["date"]), _day(raw["end"]["date"])
    a, b = _price(raw["start"]["quote"]), _price(raw["end"]["quote"])
    if (start is None or end is None or a is None or b is None
            or not start < end < _observation_cutoff(raw["source"], today)
            or (today - end).days > MAX_END_AGE_DAYS):
        return missing
    try:
        target = reference_date(end)
    except ValueError:
        return missing
    if (raw["reference_target"] != target.isoformat()
            or not 0 <= (target - start).days <= MAX_REFERENCE_GAP_DAYS):
        return missing
    value = _return(a, b, SPECS[cc][2])
    try:
        if (value is None or type(raw["value"]) not in (int, float)
                or not isfinite(raw["value"])
                or not isclose(raw["value"], value, rel_tol=1e-12, abs_tol=1e-12)):
            return missing
    except OverflowError:
        return missing
    try:
        if raw["evidence_sha256"] != _digest({k: v for k, v in raw.items() if k != "evidence_sha256"}):
            return missing
    except (TypeError, ValueError):
        return missing
    return {
        "available": True, "value": value,
        "quality": "current" if (today - end).days <= 4 else "dated",
        "currency": SPECS[cc][0], "quote_convention": SPECS[cc][2],
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "reference_target": target.isoformat(), "reference_gap_days": (target - start).days,
        "start_quote": a, "end_quote": b,
        "provider": raw["source"]["provider"], "source_url": raw["source"]["source_url"],
        "retrieved_at": raw["source"]["retrieved_at"],
        "evidence_sha256": raw["evidence_sha256"],
    }
