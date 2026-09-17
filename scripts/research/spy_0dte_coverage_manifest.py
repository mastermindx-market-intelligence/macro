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
from datetime import datetime, timedelta
from decimal import Decimal
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
ENTRY_LOOKBACK_SECONDS = Decimal("1")
ENTRY_WINDOW_SECONDS = Decimal("1")
ENTRY_SYNCHRONY_SECONDS = Decimal("1")


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


def _quotes_by_clock(
    payload: Any, session_date: str
) -> dict[str, dict[tuple[str, float], Mapping[str, Any]]]:
    """Parse exact 0DTE quote rows at the frozen clocks."""
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
        right = str(contract.get("right", "")).upper()[:1]
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
                raise CoverageError("conflicting interval quote for one contract/clock")
            by_clock[clock][key] = row
    return by_clock


def _eligible_candidates_from_quotes(
    session_date: str,
    clock: str,
    quotes: Mapping[tuple[str, float], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for right, strike in sorted(quotes, key=lambda item: (item[0] != "P", item[1])):
        short_row = quotes[(right, strike)]
        long_strike = round(strike - 2.0, 3) if right == "P" else round(strike + 2.0, 3)
        long_row = quotes.get((right, long_strike))
        if (
            long_row is None
            or not _side_ok(short_row, "bid")
            or not _side_ok(long_row, "ask")
        ):
            continue
        short_bid = float(short_row["bid"])
        long_ask = float(long_row["ask"])
        credit = short_bid - long_ask
        if not (CREDIT_LOW - 1e-9 <= credit <= CREDIT_HIGH + 1e-9):
            continue
        width = 2.0
        max_loss = (width - credit) * 100.0
        candidates.append(
            {
                "session_date": session_date,
                "decision_clock": clock,
                "decision_timestamp": f"{session_date}T{clock}",
                "family": "bull_put" if right == "P" else "bear_call",
                "short_right": right,
                "short_strike": strike,
                "long_strike": long_strike,
                "width": width,
                "entry_credit": credit,
                "max_loss_per_spread": max_loss,
                "reward_risk": credit / (width - credit),
                "short_bid": short_bid,
                "short_bid_size": int(short_row["bid_size"]),
                "short_bid_exchange": int(short_row["bid_exchange"]),
                "short_bid_condition": int(short_row["bid_condition"]),
                "long_ask": long_ask,
                "long_ask_size": int(long_row["ask_size"]),
                "long_ask_exchange": int(long_row["ask_exchange"]),
                "long_ask_condition": int(long_row["ask_condition"]),
            }
        )
    return candidates


def _tick_quotes_by_contract(
    payload: Any, session_date: str
) -> dict[tuple[str, float], list[replay.Quote]]:
    out: dict[tuple[str, float], list[replay.Quote]] = {}
    for group_payload in _response(payload):
        if not isinstance(group_payload, Mapping) or set(group_payload) != {"contract", "data"}:
            raise CoverageError("tick entry contract group fields are not exact")
        identity = group_payload["contract"]
        if not isinstance(identity, Mapping):
            raise CoverageError("tick entry contract identity is malformed")
        if str(identity.get("symbol", "")).upper() != "SPY":
            raise CoverageError("tick entry response contains a non-SPY contract")
        if str(identity.get("expiration")) != session_date:
            raise CoverageError("tick entry response contains a non-0DTE contract")
        right = str(identity.get("right", "")).upper()[:1]
        if right not in {"C", "P"}:
            raise CoverageError("tick entry response right is malformed")
        try:
            strike = round(float(identity["strike"]), 3)
        except (KeyError, TypeError, ValueError) as exc:
            raise CoverageError("tick entry response strike is malformed") from exc
        key = (right, strike)
        if key in out:
            raise CoverageError("duplicate tick entry contract group")
        contract = replay.Contract(
            "SPY", session_date, Decimal(str(strike)),
            "call" if right == "C" else "put",
        )
        out[key] = replay.source_quotes({"response": [group_payload]}, contract)
    return out


def eligible_candidates_from_tick_window(
    payload: Any, session_date: str, clock: str
) -> list[dict[str, Any]]:
    """First executable credit-band crossing within the frozen 1s entry window.

    The payload must include enough pre-decision ticks to seed current NBBO state.
    Every source row updates state; no invalidated quote may be carried forward.
    """
    if clock not in CLOCKS:
        raise CoverageError("decision clock is not frozen")
    decision_at = datetime.fromisoformat(f"{session_date}T{clock}")
    end_at = decision_at + timedelta(seconds=float(ENTRY_WINDOW_SECONDS))
    quotes = _tick_quotes_by_contract(payload, session_date)
    candidates: list[dict[str, Any]] = []
    for right, strike in sorted(quotes, key=lambda item: (item[0] != "P", item[1])):
        long_strike = round(strike - 2.0, 3) if right == "P" else round(strike + 2.0, 3)
        long_rows = quotes.get((right, long_strike))
        if long_rows is None:
            continue
        packages = replay.package_quotes(
            quotes[(right, strike)], long_rows,
            action="entry",
            max_leg_age_seconds=ENTRY_SYNCHRONY_SECONDS,
            start_at=decision_at,
            end_at=end_at,
        )
        package = next(
            (
                item for item in packages
                if Decimal(str(CREDIT_LOW)) - Decimal("1e-9")
                <= item.value
                <= Decimal(str(CREDIT_HIGH)) + Decimal("1e-9")
            ),
            None,
        )
        if package is None:
            continue
        credit = float(package.value)
        width = 2.0
        candidates.append({
            "session_date": session_date,
            "decision_clock": clock,
            "decision_timestamp": f"{session_date}T{clock}",
            "entry_timestamp": package.timestamp.isoformat(timespec="milliseconds"),
            "entry_delay_seconds": (package.timestamp - decision_at).total_seconds(),
            "entry_leg_age_seconds": float(package.leg_age_seconds),
            "family": "bull_put" if right == "P" else "bear_call",
            "short_right": right,
            "short_strike": strike,
            "long_strike": long_strike,
            "width": width,
            "entry_credit": credit,
            "max_loss_per_spread": (width - credit) * 100.0,
            "reward_risk": credit / (width - credit),
        })
    return candidates


def eligible_candidates(
    payload: Any, session_date: str, clock: str
) -> list[dict[str, Any]]:
    """Enumerate every executable $2 vertical in the frozen entry-credit band.

    This is a pre-outcome candidate universe only. It performs no arm scoring,
    containment filtering, trade selection, sizing, exits, or gamma logic.
    """
    if clock not in CLOCKS:
        raise CoverageError("decision clock is not frozen")
    quotes = _quotes_by_clock(payload, session_date).get(clock, {})
    return _eligible_candidates_from_quotes(session_date, clock, quotes)


def option_clock_coverage(
    payload: Any, session_date: str
) -> dict[str, dict[str, int]]:
    """Derive quote/package availability at frozen clocks without future outcomes."""
    by_clock = _quotes_by_clock(payload, session_date)
    out: dict[str, dict[str, int]] = {}
    for clock in CLOCKS:
        quotes = by_clock.get(clock, {})
        valid_two_sided = sum(
            1
            for row in quotes.values()
            if _side_ok(row, "bid") and _side_ok(row, "ask")
        )
        candidates = _eligible_candidates_from_quotes(session_date, clock, quotes)
        out[clock] = {
            "contracts": len(quotes),
            "valid_two_sided": valid_two_sided,
            "bull_credit_band": sum(c["family"] == "bull_put" for c in candidates),
            "bear_credit_band": sum(c["family"] == "bear_call" for c in candidates),
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
