#!/usr/bin/env python3
"""Coverage-only audit for the SPY 0DTE credit-spread prereg.

No economic outcomes are calculated. The live CLI reads the incumbent localhost
ThetaData v3 Terminal and emits only derived availability/eligibility metadata.
Raw licensed quote payloads are not persisted.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any, Mapping

import spy_0dte_credit_spread_replay as replay

CLOCKS = ("09:35:00.000", "09:45:00.000", "10:00:00.000")
PARTITIONS = (
    ("development", "2023-01-03", "2024-06-28"),
    ("validation", "2024-07-01", "2025-06-30"),
    ("holdout", "2025-07-01", "2026-07-14"),
    ("forensic_quarantine", "2026-07-15", "2026-09-15"),
)
CREDIT_LOW = 0.08
CREDIT_HIGH = 0.15
STRIKE_RANGE = 30
MAX_WORKERS = 4


class CoverageError(ValueError):
    pass


def _response(payload: Any) -> list[Any]:
    if isinstance(payload, Mapping) and set(payload) == {"response"}:
        payload = payload["response"]
    if not isinstance(payload, list):
        raise CoverageError("Theta response must be a list or exact response wrapper")
    return payload


def _side_ok(row: Mapping[str, Any], side: str) -> bool:
    try:
        px = float(row[side])
        size = int(row[f"{side}_size"])
        exchange = int(row[f"{side}_exchange"])
        condition = int(row[f"{side}_condition"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        px > 0
        and size > 0
        and exchange in replay.KNOWN_THETA_EXCHANGES
        and condition in replay.FIRM_OPRA_QUOTE_CONDITIONS
    )


def option_clock_coverage(
    payload: Any, session_date: str
) -> dict[str, dict[str, int]]:
    """Derive quote/package availability at frozen clocks without future outcomes."""
    by_clock: dict[str, dict[tuple[str, float], Mapping[str, Any]]] = defaultdict(dict)
    for group in _response(payload):
        if not isinstance(group, Mapping) or set(group) != {"contract", "data"}:
            raise CoverageError("option quote group fields are not exact")
        contract = group["contract"]
        data = group["data"]
        if not isinstance(contract, Mapping) or not isinstance(data, list):
            raise CoverageError("option quote group is malformed")
        if str(contract.get("symbol", "")).upper() != "SPY":
            raise CoverageError("option response contains a non-SPY contract")
        if str(contract.get("expiration")) != session_date:
            raise CoverageError("option response contains a non-0DTE contract")
        right_text = str(contract.get("right", "")).upper()
        right = right_text[:1]
        if right not in {"C", "P"}:
            raise CoverageError("option response right is malformed")
        try:
            strike = round(float(contract["strike"]), 3)
        except (KeyError, TypeError, ValueError) as exc:
            raise CoverageError("option response strike is malformed") from exc
        for row in data:
            if not isinstance(row, Mapping):
                raise CoverageError("option quote row is malformed")
            timestamp = str(row.get("timestamp", ""))
            if "T" not in timestamp:
                continue
            date_text, clock = timestamp.split("T", 1)
            if date_text != session_date or clock not in CLOCKS:
                continue
            key = (right, strike)
            previous = by_clock[clock].get(key)
            if previous is not None and previous != row:
                raise CoverageError(
                    "conflicting interval quote for one contract/clock"
                )
            by_clock[clock][key] = row

    out: dict[str, dict[str, int]] = {}
    for clock in CLOCKS:
        quotes = by_clock.get(clock, {})
        valid_two_sided = sum(
            1
            for row in quotes.values()
            if _side_ok(row, "bid") and _side_ok(row, "ask")
        )
        bull_band = 0
        bear_band = 0
        for (right, strike), short_row in quotes.items():
            if right == "P":
                long_row = quotes.get(("P", round(strike - 2.0, 3)))
            else:
                long_row = quotes.get(("C", round(strike + 2.0, 3)))
            if (
                long_row is None
                or not _side_ok(short_row, "bid")
                or not _side_ok(long_row, "ask")
            ):
                continue
            credit = float(short_row["bid"]) - float(long_row["ask"])
            if CREDIT_LOW - 1e-9 <= credit <= CREDIT_HIGH + 1e-9:
                if right == "P":
                    bull_band += 1
                else:
                    bear_band += 1
        out[clock] = {
            "contracts": len(quotes),
            "valid_two_sided": valid_two_sided,
            "bull_credit_band": bull_band,
            "bear_credit_band": bear_band,
        }
    return out


def partition_for_date(session_date: str) -> str:
    for name, start, end in PARTITIONS:
        if start <= session_date <= end:
            return name
    raise CoverageError(f"date outside frozen panel: {session_date}")


def summarize(
    option_rows: list[dict[str, Any]], underlying_bar_counts: Mapping[str, int]
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for name, start, end in PARTITIONS:
        rows = [row for row in option_rows if start <= row["date"] <= end]
        part: dict[str, Any] = {
            "sessions": len(rows),
            "option_errors": sum(bool(row.get("error")) for row in rows),
            "underlying_31bar_complete": sum(
                underlying_bar_counts.get(row["date"], 0) >= 31 for row in rows
            ),
        }
        for clock in CLOCKS:
            prefix = clock[:5]
            available = [row.get(clock) or {} for row in rows if not row.get("error")]
            part[f"{prefix}_any_valid_contract"] = sum(
                q.get("valid_two_sided", 0) > 0 for q in available
            )
            part[f"{prefix}_bull_credit_band"] = sum(
                q.get("bull_credit_band", 0) > 0 for q in available
            )
            part[f"{prefix}_bear_credit_band"] = sum(
                q.get("bear_credit_band", 0) > 0 for q in available
            )
            part[f"{prefix}_either_credit_band"] = sum(
                q.get("bull_credit_band", 0) > 0
                or q.get("bear_credit_band", 0) > 0
                for q in available
            )
        summary[name] = part
    return summary


def _fetch_json(
    base_url: str, path: str, params: Mapping[str, str], timeout: int
) -> Any:
    url = f"{base_url.rstrip('/')}{path}?{urllib.parse.urlencode(dict(params))}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.geturl() != url or response.status != 200:
            raise CoverageError("Theta source did not return exact HTTP 200 response")
        return json.load(response)


def _list_dates(base_url: str, timeout: int) -> tuple[list[str], list[str]]:
    stock = _response(
        _fetch_json(
            base_url,
            "/stock/list/dates/quote",
            {"symbol": "SPY", "format": "json"},
            timeout,
        )
    )
    expirations = _response(
        _fetch_json(
            base_url,
            "/option/list/expirations",
            {"symbol": "SPY", "format": "json"},
            timeout,
        )
    )
    stock_dates = sorted(
        {
            str(row["date"])
            for row in stock
            if isinstance(row, Mapping) and "date" in row
        }
    )
    expiration_dates = sorted(
        {
            str(row["expiration"])
            for row in expirations
            if isinstance(row, Mapping) and "expiration" in row
        }
    )
    return stock_dates, expiration_dates


def _audit_option_day(
    base_url: str, session_date: str, timeout: int
) -> dict[str, Any]:
    ymd = session_date.replace("-", "")
    params = {
        "symbol": "SPY",
        "expiration": ymd,
        "date": ymd,
        "start_time": "09:35:00.000",
        "end_time": "10:00:00.000",
        "interval": "5m",
        "strike_range": str(STRIKE_RANGE),
        "right": "both",
        "format": "json",
    }
    try:
        payload = _fetch_json(
            base_url, "/option/history/quote", params, timeout
        )
        return {
            "date": session_date,
            "error": None,
            **option_clock_coverage(payload, session_date),
        }
    except Exception as exc:  # record source failure; never silently impute
        return {"date": session_date, "error": type(exc).__name__}


def run_live(base_url: str, timeout: int, max_workers: int) -> dict[str, Any]:
    if base_url.rstrip("/") not in {
        "http://127.0.0.1:25503/v3",
        "http://localhost:25503/v3",
    }:
        raise CoverageError("Theta source must be the incumbent localhost v3 Terminal")
    if not 1 <= max_workers <= MAX_WORKERS:
        raise CoverageError(f"max_workers must be 1..{MAX_WORKERS}")
    stock_dates, expiration_dates = _list_dates(base_url, timeout)
    expirations = set(expiration_dates)
    dates = [
        d
        for d in stock_dates
        if "2023-01-03" <= d <= "2026-09-15" and d in expirations
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(
            pool.map(lambda d: _audit_option_day(base_url, d, timeout), dates)
        )
    # Underlying bars intentionally stay a separate canonical input. A caller can
    # join the minute-bar audit without teaching this option audit to own stock data.
    return {"panel_dates": dates, "option_rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25503/v3")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args()
    result = run_live(args.base_url, args.timeout, args.max_workers)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
