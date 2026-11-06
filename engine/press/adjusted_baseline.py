"""Fixed, offline qualification of the October 7 NVIDIA analytical baseline.

This is an evidence reader, never a Press fact-pool admission or collector.
The caller owns one logical fetch through the incumbent market-data transport.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
import math
import re
import statistics
from zoneinfo import ZoneInfo

import pandas as pd

from engine.stock_technicals import snapshot
from lib.nyse_calendar import sessions_between

START = date(2024, 10, 14)
CUTOFF = date(2026, 10, 7)
PATH = f"/v2/aggs/ticker/NVDA/range/1/day/{START}/{CUTOFF}"
PARAMS = {"adjusted": "true", "sort": "asc", "limit": 5000}
DOCUMENTATION = "https://massive.com/docs/rest/stocks/aggregates/custom-bars"
METRICS = ("pct_vs_50dma", "pct_vs_200dma", "rsi14", "hv20", "hv_pctile")
_ET = ZoneInfo("America/New_York")


class BaselineRefused(ValueError):
    """Fixed diagnostics only; never include provider content or credentials."""


def canonical_payload(payload: dict) -> bytes:
    try:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode()
    except (ValueError, TypeError):
        raise BaselineRefused("payload_not_canonical_json") from None
    if len(raw) > 1024 * 1024:
        raise BaselineRefused("payload_too_large")
    return raw


def qualify(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise BaselineRefused("response_not_successful")
    if payload.get("ticker") != "NVDA" or payload.get("adjusted") is not True:
        raise BaselineRefused("identity_or_adjustment_mismatch")
    if payload.get("next_url"):
        raise BaselineRefused("pagination_not_admitted")
    if set(payload) - {"status", "ticker", "adjusted", "next_url", "request_id",
                       "queryCount", "resultsCount", "count", "results"}:
        raise BaselineRefused("unqualified_response_field")
    if "request_id" in payload and (not isinstance(payload["request_id"], str) or
            not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", payload["request_id"])):
        raise BaselineRefused("invalid_request_identity")
    raw = canonical_payload(payload)
    rows = payload.get("results")
    if not isinstance(rows, list) or not 300 <= len(rows) <= 600:
        raise BaselineRefused("coverage_size")
    for name in ("queryCount", "resultsCount", "count"):
        if name in payload and (type(payload[name]) is not int or payload[name] != len(rows)):
            raise BaselineRefused("response_count_mismatch")

    dates, values = [], []
    for row in rows:
        if not isinstance(row, dict) or type(row.get("t")) is not int:
            raise BaselineRefused("invalid_timestamp")
        if set(row) - {"t", "o", "h", "l", "c", "v", "vw", "n", "otc"}:
            raise BaselineRefused("unqualified_bar_field")
        for optional in ("vw", "n"):
            if optional in row and (type(row[optional]) not in (int, float) or
                    not math.isfinite(row[optional]) or row[optional] < 0):
                raise BaselineRefused("invalid_optional_bar_field")
        if "n" in row and type(row["n"]) is not int:
            raise BaselineRefused("invalid_trade_count")
        try:
            stamp = datetime.fromtimestamp(row["t"] / 1000, timezone.utc).astimezone(_ET)
        except (ValueError, OSError, OverflowError):
            raise BaselineRefused("invalid_timestamp") from None
        if stamp.time() != time(0) or not START <= stamp.date() <= CUTOFF:
            raise BaselineRefused("timestamp_outside_daily_contract")
        numeric = []
        for key in ("o", "h", "l", "c", "v"):
            value = row.get(key)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise BaselineRefused("nonfinite_or_nonnumeric_bar")
            numeric.append(float(value))
        o, h, low, c, volume = numeric
        if min(o, h, low, c) <= 0 or volume < 0 or not low <= min(o, c) <= max(o, c) <= h:
            raise BaselineRefused("incoherent_bar")
        if row.get("otc") not in (None, False):
            raise BaselineRefused("unexpected_instrument_market")
        dates.append(stamp.date())
        values.append(numeric)
    # Exact comparison rejects omissions, duplicates, reordering and extra days.
    expected = sessions_between(START, CUTOFF)
    if dates != expected:
        raise BaselineRefused("exchange_session_coverage_mismatch")
    frame = pd.DataFrame(values, columns=("open", "high", "low", "close", "volume"),
                         index=pd.DatetimeIndex(dates))
    result = snapshot(frame.close, frame.high, frame.low, frame.volume)
    selected = {key: result[key] for key in METRICS}
    if any(value is None or not math.isfinite(value) for value in selected.values()):
        raise BaselineRefused("analytical_coverage_incomplete")
    for key in ("rsi14", "hv_pctile"):
        if not 0 <= selected[key] <= 100:
            raise BaselineRefused("analytical_range")
    for window in (50, 200):
        independent = round((float(frame.close.iloc[-1]) /
                             statistics.fmean(frame.close.tail(window)) - 1) * 100, 1)
        if selected[f"pct_vs_{window}dma"] != independent:
            raise BaselineRefused("independent_arithmetic_mismatch")
    return {
        "kind": "press_fixed_nvda_adjusted_baseline/v1",
        "ticker": "NVDA", "first_session": str(START), "cutoff": str(CUTOFF),
        "rows": len(rows), "canonical_parsed_payload_sha256": hashlib.sha256(raw).hexdigest(),
        "documentation": DOCUMENTATION,
        "basis": "provider-asserted split-adjusted daily eligible-trade aggregates; not total return or authenticated regular-session close",
        "vintage": "current-vintage historical reconstruction, not a point-in-time availability claim",
        "question": "What trend and volatility conditions preceded the October 8 science commitment announcement?",
        "analytical_results": selected,
        "engine": "engine.stock_technicals.snapshot; full fixed range, default windows, no benchmark",
        "checks": {"exact_exchange_sessions": True, "finite_coherent_ohlcv": True,
                   "independent_50_and_200_day_arithmetic": True},
        "external_observations_remain_external": True,
        "allow_stage": False, "allow_emit": False, "publication_approved": False,
        "scope": "analytical qualification only; no event attribution, trading authority or automatic Press fact admission",
    }
