#!/usr/bin/env python3
"""Coverage-only audit for causal SPY opening and structural-stop bars.

Research only. Reads the incumbent ThetaData v3 Terminal consolidated UTP/CTA
one-minute stock OHLC feed and emits only derived source-availability metadata.
No licensed raw rows, outcomes, gamma, scores, sizing, orders, or trade authority.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
from typing import Any, Mapping

import spy_0dte_a1_features as a1
import spy_0dte_coverage_manifest as panel

START_CLOCK = "09:30:00.000"
OPENING_END_CLOCK = "09:59:00.000"  # 10:00 decision sees completed 09:30..09:59.
STRUCTURAL_END_CLOCK = "15:54:00.000"  # 15:55 is the exact time-close boundary.
MAX_WORKERS = 4
DECISION_MINUTES = {
    "09:35:00.000": 5,
    "09:45:00.000": 15,
    "10:00:00.000": 30,
}


class BarCoverageError(ValueError):
    pass


def bar_clock_coverage(payload: Any, session_date: str) -> dict[str, Any]:
    bars = a1.parse_underlying_bars(payload, session_date)
    out: dict[str, Any] = {}
    for clock, minutes in DECISION_MINUTES.items():
        required = [a1._clock_at("2000-01-01", minute) for minute in range(minutes)]
        missing = [bar_clock for bar_clock in required if bar_clock not in bars]
        # After entry, a structural stop can react only after a one-minute bar
        # completes. The final eligible breach bar opens 15:54 and completes at
        # the preregistered 15:55 time-close boundary.
        structural_required = [
            a1._clock_at("2000-01-01", minute)
            for minute in range(minutes, 385)
        ]
        structural_missing = [
            bar_clock for bar_clock in structural_required if bar_clock not in bars
        ]
        out[clock] = {
            "expected_completed_bars": minutes,
            "present_completed_bars": minutes - len(missing),
            "complete": not missing,
            "first_missing": missing[0] if missing else None,
            "last_missing": missing[-1] if missing else None,
            "open_available": a1.OPEN_CLOCK in bars,
            "decision_price_available": required[-1] in bars,
            "structural_expected_bars": len(structural_required),
            "structural_present_bars": len(structural_required) - len(structural_missing),
            "structural_path_complete": not structural_missing,
            "structural_first_missing": structural_missing[0] if structural_missing else None,
            "structural_last_missing": structural_missing[-1] if structural_missing else None,
        }
    return out


def _fetch_day(base_url: str, session_date: str, timeout: int) -> Any:
    ymd = session_date.replace("-", "")
    return panel._fetch_json(
        base_url,
        "/stock/history/ohlc",
        {
            "symbol": "SPY",
            "date": ymd,
            "interval": "1m",
            "start_time": START_CLOCK,
            "end_time": STRUCTURAL_END_CLOCK,
            "venue": "utp_cta",
            "format": "json",
        },
        timeout,
    )


def audit_day(base_url: str, session_date: str, timeout: int) -> dict[str, Any]:
    try:
        payload = _fetch_day(base_url, session_date, timeout)
        return {
            "date": session_date,
            "partition": panel.partition_for_date(session_date),
            "error": None,
            **bar_clock_coverage(payload, session_date),
        }
    except Exception as exc:  # explicit source/null state; never impute
        return {
            "date": session_date,
            "partition": panel.partition_for_date(session_date),
            "error": type(exc).__name__,
        }


def summarize(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for partition, start, end in panel.PARTITIONS:
        part_rows = [row for row in rows if start <= str(row["date"]) <= end]
        part: dict[str, Any] = {
            "sessions": len(part_rows),
            "errors": sum(bool(row.get("error")) for row in part_rows),
        }
        for clock in a1.DECISION_CLOCKS:
            valid = [row.get(clock) or {} for row in part_rows if not row.get("error")]
            prefix = clock[:5]
            part[f"{prefix}_complete"] = sum(bool(state.get("complete")) for state in valid)
            part[f"{prefix}_open_available"] = sum(bool(state.get("open_available")) for state in valid)
            part[f"{prefix}_decision_price_available"] = sum(
                bool(state.get("decision_price_available")) for state in valid
            )
            part[f"{prefix}_structural_path_complete"] = sum(
                bool(state.get("structural_path_complete")) for state in valid
            )
        summary[partition] = part
    return summary


def run_live(base_url: str, timeout: int, max_workers: int) -> dict[str, Any]:
    if base_url.rstrip("/") not in {
        "http://127.0.0.1:25503/v3",
        "http://localhost:25503/v3",
    }:
        raise BarCoverageError("Theta source must be the incumbent localhost v3 Terminal")
    if not 1 <= max_workers <= MAX_WORKERS:
        raise BarCoverageError(f"max_workers must be 1..{MAX_WORKERS}")
    stock_dates, expiration_dates = panel._list_dates(base_url, timeout)
    expirations = set(expiration_dates)
    dates = [
        d for d in stock_dates
        if "2023-01-03" <= d <= "2026-09-15" and d in expirations
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(pool.map(lambda d: audit_day(base_url, d, timeout), dates))
    return {
        "schema": "spy_0dte_underlying_bar_coverage/v1",
        "status": "coverage_only_no_outcomes_no_gamma",
        "source": "ThetaData_v3_stock_history_ohlc",
        "venue": "utp_cta",
        "interval": "1m",
        "bar_window": [START_CLOCK, STRUCTURAL_END_CLOCK],
        "opening_window_end": OPENING_END_CLOCK,
        "structural_window_end": STRUCTURAL_END_CLOCK,
        "panel_dates": dates,
        "errors": {row["date"]: row["error"] for row in rows if row.get("error")},
        "missing": {
            clock[:5]: [
                row["date"] for row in rows
                if not row.get("error") and not (row.get(clock) or {}).get("complete")
            ]
            for clock in a1.DECISION_CLOCKS
        },
        "missing_structural": {
            clock[:5]: [
                row["date"] for row in rows
                if not row.get("error")
                and not (row.get(clock) or {}).get("structural_path_complete")
            ]
            for clock in a1.DECISION_CLOCKS
        },
        "summary": summarize(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25503/v3")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = run_live(args.base_url, args.timeout, args.max_workers)
    text = json.dumps(result, sort_keys=True, separators=(",", ":"))
    if args.out:
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(text + "\n"); tmp.replace(out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
