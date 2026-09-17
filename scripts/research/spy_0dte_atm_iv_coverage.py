#!/usr/bin/env python3
"""Coverage-only PIT ATM-IV audit for the SPY 0DTE prereg."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import urllib.parse
import urllib.request
from typing import Any, Mapping

import spy_0dte_a1_features as a1

PARTITIONS = (
    ("development", "2023-01-03", "2024-06-28"),
    ("validation", "2024-07-01", "2025-06-30"),
    ("holdout", "2025-07-01", "2026-07-14"),
    ("forensic_quarantine", "2026-07-15", "2026-09-15"),
)
CLOCKS = a1.DECISION_CLOCKS
MAX_WORKERS = 4


class CoverageError(ValueError):
    pass


def _response(payload: Any) -> list[Any]:
    if isinstance(payload, Mapping) and set(payload) == {"response"}:
        payload = payload["response"]
    if not isinstance(payload, list):
        raise CoverageError("Theta response shape is invalid")
    return payload


def _fetch_json(
    base_url: str, path: str, params: Mapping[str, str], timeout: int
) -> Any:
    url = f"{base_url.rstrip('/')}{path}?{urllib.parse.urlencode(dict(params))}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200 or response.geturl() != url:
            raise CoverageError("Theta source did not return exact HTTP 200")
        return json.load(response)


def _panel_dates(base_url: str, timeout: int) -> list[str]:
    stock = _response(
        _fetch_json(
            base_url,
            "/stock/list/dates/quote",
            {"symbol": "SPY", "format": "json"},
            timeout,
        )
    )
    exps = _response(
        _fetch_json(
            base_url,
            "/option/list/expirations",
            {"symbol": "SPY", "format": "json"},
            timeout,
        )
    )
    stock_dates = {
        str(row["date"])
        for row in stock
        if isinstance(row, Mapping) and "date" in row
    }
    expiration_dates = {
        str(row["expiration"])
        for row in exps
        if isinstance(row, Mapping) and "expiration" in row
    }
    return sorted(
        d
        for d in stock_dates
        if "2023-01-03" <= d <= "2026-09-15" and d in expiration_dates
    )


def atm_coverage(payload: Any, session_date: str) -> dict[str, Any]:
    prices = a1.collapse_underlying_prices(payload, session_date)
    out: dict[str, Any] = {
        "minute_count": sum(
            a1._clock_at("2000-01-01", minute) in prices for minute in range(31)
        )
    }
    for clock in CLOCKS:
        features = a1.atm_iv_features(
            payload,
            session_date,
            decision_clock=clock,
            prices=prices,
        )
        prefix = clock[:5]
        out[prefix + "_atm_iv_level"] = features["atm_iv_level"] is not None
        out[prefix + "_atm_iv_change"] = (
            features["atm_iv_change_from_first_valid"] is not None
        )
        out[prefix + "_anchor_minute"] = features[
            "atm_iv_anchor_minutes_from_open"
        ]
    return out


def _audit_day(
    base_url: str, session_date: str, timeout: int
) -> dict[str, Any]:
    ymd = session_date.replace("-", "")
    params = {
        "symbol": "SPY",
        "expiration": ymd,
        "date": ymd,
        "start_time": "09:30:00.000",
        "end_time": "10:00:00.000",
        "interval": "1m",
        "strike_range": "4",
        "right": "both",
        "format": "json",
    }
    try:
        payload = _fetch_json(
            base_url, "/option/history/greeks/all", params, timeout
        )
        return {
            "date": session_date,
            "error": None,
            **atm_coverage(payload, session_date),
        }
    except Exception as exc:
        return {"date": session_date, "error": type(exc).__name__}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for name, start, end in PARTITIONS:
        part = [row for row in rows if start <= row["date"] <= end]
        s: dict[str, Any] = {
            "sessions": len(part),
            "errors": sum(bool(row.get("error")) for row in part),
            "price_31m_complete": sum(
                not row.get("error") and row.get("minute_count") == 31
                for row in part
            ),
        }
        for clock in CLOCKS:
            prefix = clock[:5]
            s[prefix + "_atm_iv_level_available"] = sum(
                not row.get("error")
                and bool(row.get(prefix + "_atm_iv_level"))
                for row in part
            )
            s[prefix + "_atm_iv_change_available"] = sum(
                not row.get("error")
                and bool(row.get(prefix + "_atm_iv_change"))
                for row in part
            )
        summary[name] = s
    return summary


def run_live(base_url: str, timeout: int, max_workers: int) -> dict[str, Any]:
    if base_url.rstrip("/") not in {
        "http://127.0.0.1:25503/v3",
        "http://localhost:25503/v3",
    }:
        raise CoverageError("Theta source must be incumbent localhost v3 Terminal")
    if not 1 <= max_workers <= MAX_WORKERS:
        raise CoverageError("max_workers outside frozen cap")
    dates = _panel_dates(base_url, timeout)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(pool.map(lambda d: _audit_day(base_url, d, timeout), dates))
    return {
        "schema": "spy_0dte_atm_iv_coverage/v1",
        "status": "coverage_only_no_outcomes_no_gamma",
        "panel_dates": dates,
        "summary": summarize(rows),
        "errors": [row for row in rows if row.get("error")],
        "missing": {
            clock[:5]: [
                row["date"]
                for row in rows
                if not row.get("error")
                and not row.get(clock[:5] + "_atm_iv_level")
            ]
            for clock in CLOCKS
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25503/v3")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = run_live(args.base_url, args.timeout, args.max_workers)
    body = json.dumps(result, sort_keys=True, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
    print(
        json.dumps(
            {
                "panel_sessions": len(result["panel_dates"]),
                "summary": result["summary"],
                "error_count": len(result["errors"]),
                "missing_counts": {
                    key: len(value) for key, value in result["missing"].items()
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
