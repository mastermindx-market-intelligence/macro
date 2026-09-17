#!/usr/bin/env python3
"""Coverage-only tick-path audit for frozen SPY 0DTE candidates.

The auditor reuses the preregistered entry candidate universe and replay quote
quality. It reports only source-present exit-side rows and leg-synchronization
availability. It never computes spread debit, target/stop crossings, P&L,
labels, selection scores, or economic outcomes. Raw licensed payloads are not
persisted.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import spy_0dte_coverage_manifest as entry
import spy_0dte_credit_spread_replay as replay

PANEL_START = "2023-01-03"
PANEL_END = "2026-09-15"
END_CLOCK = "15:55:00.000"
MAX_WORKERS = 4


class ClosePathCoverageError(ValueError):
    pass


MODES = ("tick_synchrony", "minute_presence")
PRIMARY_LEG_SYNCHRONY_SECONDS = Decimal("1")
ENTRY_MAX_LAG_SECONDS = 1.0
TIME_CLOSE_MAX_PACKAGE_AGE_SECONDS = 5.0


def _clock_dt(session_date: str, clock: str) -> datetime:
    try:
        return datetime.fromisoformat(f"{session_date}T{clock}")
    except ValueError as exc:
        raise ClosePathCoverageError("session date/clock is malformed") from exc


def _minute_grid(session_date: str, start_clock: str, end_clock: str) -> list[datetime]:
    start = _clock_dt(session_date, start_clock)
    end = _clock_dt(session_date, end_clock)
    if end < start:
        raise ClosePathCoverageError("close-path end precedes decision clock")
    out: list[datetime] = []
    current = start
    while current <= end:
        out.append(current)
        current += timedelta(minutes=1)
    return out


def _contract(candidate: Mapping[str, Any], role: str) -> replay.Contract:
    if role not in {"short", "long"}:
        raise ClosePathCoverageError("role must be short or long")
    try:
        right = str(candidate["short_right"]).upper()
        strike = candidate[f"{role}_strike"]
        session_date = str(candidate["session_date"])
    except KeyError as exc:
        raise ClosePathCoverageError("candidate identity is incomplete") from exc
    if right not in {"C", "P"}:
        raise ClosePathCoverageError("candidate right is malformed")
    return replay.Contract(
        "SPY",
        session_date,
        replay.Decimal(str(strike)),
        "call" if right == "C" else "put",
    )


def _rows_by_minute(
    payload: Any, contract: replay.Contract, role: str
) -> dict[datetime, replay.Quote]:
    rows = replay.qualifying_exit_quotes(payload, contract, role=role)
    out: dict[datetime, replay.Quote] = {}
    for quote in rows:
        stamp = quote.timestamp.replace(second=0, microsecond=0)
        if quote.timestamp != stamp:
            raise ClosePathCoverageError("minute-presence quote is not minute-aligned")
        previous = out.get(stamp)
        if previous is not None and previous != quote:
            raise ClosePathCoverageError("conflicting quote for one contract/minute")
        out[stamp] = quote
    return out


def candidate_minute_presence(
    candidate: Mapping[str, Any],
    short_payload: Any,
    long_payload: Any,
    *,
    end_clock: str = END_CLOCK,
) -> dict[str, Any]:
    """Measure sampled minute source continuity; never claim leg synchrony."""
    session_date = str(candidate.get("session_date", ""))
    decision_clock = str(candidate.get("decision_clock", ""))
    if decision_clock not in entry.CLOCKS:
        raise ClosePathCoverageError("candidate decision clock is not frozen")
    short_contract = _contract(candidate, "short")
    long_contract = _contract(candidate, "long")
    short_rows = _rows_by_minute(short_payload, short_contract, "short")
    long_rows = _rows_by_minute(long_payload, long_contract, "long")

    normal = 0
    zero_bid = 0
    unknown: list[str] = []
    grid = _minute_grid(session_date, decision_clock, end_clock)
    for stamp in grid:
        short_quote = short_rows.get(stamp)
        long_quote = long_rows.get(stamp)
        if short_quote is None or long_quote is None:
            unknown.append(stamp.isoformat())
            continue
        if long_quote.bid > 0:
            normal += 1
        elif long_quote.bid == 0:
            zero_bid += 1
        else:
            unknown.append(stamp.isoformat())
    return {
        "session_date": session_date,
        "decision_clock": decision_clock,
        "family": str(candidate.get("family", "")),
        "short_right": str(candidate.get("short_right", "")),
        "short_strike": float(candidate["short_strike"]),
        "long_strike": float(candidate["long_strike"]),
        "expected_minutes": len(grid),
        "normal_package_minutes": normal,
        "zero_bid_carry_minutes": zero_bid,
        "unknown_minutes": len(unknown),
        "first_unknown": unknown[0] if unknown else None,
        "last_unknown": unknown[-1] if unknown else None,
        "full_minute_presence": not unknown,
        "synchrony_proven": False,
    }


def _ready_summary(
    short_rows: Sequence[replay.Quote],
    long_rows: Sequence[replay.Quote],
    *,
    decision_at: datetime,
    end_at: datetime,
    max_leg_age_seconds: Decimal,
) -> dict[str, Any]:
    events = sorted(
        [(q.timestamp, 0, q) for q in short_rows]
        + [(q.timestamp, 1, q) for q in long_rows],
        key=lambda row: (row[0], row[1]),
    )
    latest: dict[int, replay.Quote] = {}
    ready_by_time: dict[datetime, str] = {}
    for now, leg, quote in events:
        if now < decision_at or now > end_at:
            continue
        latest[leg] = quote
        if len(latest) != 2:
            continue
        short_quote, long_quote = latest[0], latest[1]
        age = Decimal(
            str(
                max(
                    (now - short_quote.timestamp).total_seconds(),
                    (now - long_quote.timestamp).total_seconds(),
                )
            )
        )
        if age > max_leg_age_seconds:
            continue
        ready_by_time[now] = "zero_bid_carry" if long_quote.bid == 0 else "normal"

    stamps = sorted(ready_by_time)
    gaps = [
        (later - earlier).total_seconds()
        for earlier, later in zip(stamps, stamps[1:])
    ]
    first_lag = (stamps[0] - decision_at).total_seconds() if stamps else None
    end_lag = (end_at - stamps[-1]).total_seconds() if stamps else None
    limit = float(max_leg_age_seconds)
    return {
        "ready_events": len(stamps),
        "normal_ready_events": sum(state == "normal" for state in ready_by_time.values()),
        "zero_bid_carry_ready_events": sum(
            state == "zero_bid_carry" for state in ready_by_time.values()
        ),
        "first_ready": stamps[0].isoformat() if stamps else None,
        "last_ready": stamps[-1].isoformat() if stamps else None,
        "decision_lag_seconds": first_lag,
        "end_lag_seconds": end_lag,
        "max_ready_gap_seconds": max(gaps) if gaps else None,
        "decision_boundary_ready": first_lag is not None and first_lag <= limit,
        "end_boundary_ready": end_lag is not None and 0 <= end_lag <= limit,
    }


def candidate_path_availability(
    candidate: Mapping[str, Any],
    short_payload: Any,
    long_payload: Any,
    *,
    end_clock: str = END_CLOCK,
) -> dict[str, Any]:
    """Measure exact-tick source/synchrony availability without economics."""
    session_date = str(candidate.get("session_date", ""))
    decision_clock = str(candidate.get("decision_clock", ""))
    if decision_clock not in entry.CLOCKS:
        raise ClosePathCoverageError("candidate decision clock is not frozen")
    decision_at = _clock_dt(session_date, decision_clock)
    end_at = _clock_dt(session_date, end_clock)
    if end_at < decision_at:
        raise ClosePathCoverageError("close-path end precedes decision clock")

    short_contract = _contract(candidate, "short")
    long_contract = _contract(candidate, "long")
    short_rows = replay.qualifying_exit_quotes(
        short_payload, short_contract, role="short"
    )
    long_rows = replay.qualifying_exit_quotes(
        long_payload, long_contract, role="long"
    )
    short_rows = [q for q in short_rows if decision_at <= q.timestamp <= end_at]
    long_rows = [q for q in long_rows if decision_at <= q.timestamp <= end_at]

    synchrony = {
        str(limit): _ready_summary(
            short_rows,
            long_rows,
            decision_at=decision_at,
            end_at=end_at,
            max_leg_age_seconds=limit,
        )
        for limit in replay.SYNCHRONY_GRID_SECONDS
    }
    primary = synchrony[str(PRIMARY_LEG_SYNCHRONY_SECONDS)]
    decision_lag = primary["decision_lag_seconds"]
    end_lag = primary["end_lag_seconds"]
    primary_entry_ready = (
        decision_lag is not None
        and 0 <= float(decision_lag) <= ENTRY_MAX_LAG_SECONDS
    )
    # Time-close freshness is deliberately separate from leg synchrony: the
    # package must first satisfy the 1s leg fence, then that package may be up
    # to 5s old at the exact 15:55 boundary.
    primary_time_close_ready = (
        end_lag is not None
        and 0 <= float(end_lag) <= TIME_CLOSE_MAX_PACKAGE_AGE_SECONDS
    )
    return {
        "session_date": session_date,
        "decision_clock": decision_clock,
        "family": str(candidate.get("family", "")),
        "short_right": str(candidate.get("short_right", "")),
        "short_strike": float(candidate["short_strike"]),
        "long_strike": float(candidate["long_strike"]),
        "short_exit_rows": len(short_rows),
        "long_exit_rows": len(long_rows),
        "long_zero_bid_rows": sum(q.bid == 0 for q in long_rows),
        "primary_leg_synchrony_seconds": float(PRIMARY_LEG_SYNCHRONY_SECONDS),
        "primary_entry_max_lag_seconds": ENTRY_MAX_LAG_SECONDS,
        "primary_time_close_max_package_age_seconds": TIME_CLOSE_MAX_PACKAGE_AGE_SECONDS,
        "primary_entry_ready": primary_entry_ready,
        "primary_time_close_ready": primary_time_close_ready,
        "synchrony": synchrony,
    }


def _fetch_entry_payload(base_url: str, session_date: str, timeout: int) -> Any:
    ymd = session_date.replace("-", "")
    return entry._fetch_json(
        base_url,
        "/option/history/quote",
        {
            "symbol": "SPY",
            "expiration": ymd,
            "date": ymd,
            "start_time": entry.CLOCKS[0],
            "end_time": entry.CLOCKS[-1],
            "interval": "5m",
            "strike_range": str(entry.STRIKE_RANGE),
            "right": "both",
            "format": "json",
        },
        timeout,
    )


def _fetch_contract_path(
    base_url: str, contract: replay.Contract, timeout: int, *, interval: str = "tick"
) -> Any:
    if interval not in {"tick", "1m"}:
        raise ClosePathCoverageError("close-path interval must be tick or 1m")
    ymd = contract.expiration.replace("-", "")
    return entry._fetch_json(
        base_url,
        "/option/history/quote",
        {
            "symbol": "SPY",
            "expiration": ymd,
            "strike": f"{contract.strike:.3f}",
            "right": contract.right,
            "date": ymd,
            "start_time": entry.CLOCKS[0],
            "end_time": END_CLOCK,
            "interval": interval,
            "format": "json",
        },
        timeout,
    )


def audit_day(
    base_url: str, session_date: str, timeout: int, *, mode: str = "tick_synchrony"
) -> dict[str, Any]:
    if mode not in MODES:
        raise ClosePathCoverageError("close-path mode is not frozen")
    try:
        entry_payload = _fetch_entry_payload(base_url, session_date, timeout)
        entry_coverage = entry.option_clock_coverage(entry_payload, session_date)
        candidates = [
            candidate
            for clock in entry.CLOCKS
            for candidate in entry.eligible_candidates(entry_payload, session_date, clock)
        ]
    except Exception as exc:
        return {
            "date": session_date,
            "partition": entry.partition_for_date(session_date),
            "entry_error": type(exc).__name__,
            "entry_coverage": None,
            "candidate_paths": [],
        }

    unique_contracts: dict[tuple[str, str], replay.Contract] = {}
    for candidate in candidates:
        for role in ("short", "long"):
            contract = _contract(candidate, role)
            unique_contracts[(contract.right, str(contract.strike))] = contract
    path_payloads: dict[tuple[str, str], Any] = {}
    contract_errors: dict[tuple[str, str], str] = {}
    for key, contract in unique_contracts.items():
        try:
            path_payloads[key] = _fetch_contract_path(
                base_url, contract, timeout,
                interval="tick" if mode == "tick_synchrony" else "1m",
            )
        except Exception as exc:  # source failure stays explicit, never imputed
            contract_errors[key] = type(exc).__name__

    paths: list[dict[str, Any]] = []
    for candidate in candidates:
        short = _contract(candidate, "short")
        long = _contract(candidate, "long")
        short_key = (short.right, str(short.strike))
        long_key = (long.right, str(long.strike))
        if short_key in contract_errors or long_key in contract_errors:
            paths.append({
                "session_date": session_date,
                "decision_clock": candidate["decision_clock"],
                "family": candidate["family"],
                "short_right": candidate["short_right"],
                "short_strike": candidate["short_strike"],
                "long_strike": candidate["long_strike"],
                "source_error": contract_errors.get(short_key) or contract_errors.get(long_key),
            })
            continue
        try:
            if mode == "tick_synchrony":
                paths.append(candidate_path_availability(
                    candidate, path_payloads[short_key], path_payloads[long_key]
                ))
            else:
                paths.append(candidate_minute_presence(
                    candidate, path_payloads[short_key], path_payloads[long_key]
                ))
        except Exception as exc:
            paths.append({
                "session_date": session_date,
                "decision_clock": candidate["decision_clock"],
                "family": candidate["family"],
                "short_right": candidate["short_right"],
                "short_strike": candidate["short_strike"],
                "long_strike": candidate["long_strike"],
                "source_error": type(exc).__name__,
            })
    return {
        "date": session_date,
        "partition": entry.partition_for_date(session_date),
        "entry_error": None,
        "entry_coverage": entry_coverage,
        "candidate_paths": paths,
    }


def summarize(
    rows: list[Mapping[str, Any]], *, mode: str = "tick_synchrony"
) -> dict[str, Any]:
    if mode not in MODES:
        raise ClosePathCoverageError("close-path mode is not frozen")
    summary: dict[str, Any] = {}
    for partition, start, end in entry.PARTITIONS:
        part_rows = [row for row in rows if start <= str(row["date"]) <= end]
        paths = [p for row in part_rows for p in row.get("candidate_paths", [])]
        by_clock: dict[str, Any] = {}
        for clock in entry.CLOCKS:
            clock_paths = [p for p in paths if p.get("decision_clock") == clock]
            valid = [p for p in clock_paths if "source_error" not in p]
            entry_states = [
                (row.get("entry_coverage") or {}).get(clock, {})
                for row in part_rows if not row.get("entry_error")
            ]
            entry_summary = {
                "sessions_any_valid_contract": sum(
                    int(q.get("valid_two_sided", 0)) > 0 for q in entry_states
                ),
                "sessions_bull_credit_band": sum(
                    int(q.get("bull_credit_band", 0)) > 0 for q in entry_states
                ),
                "sessions_bear_credit_band": sum(
                    int(q.get("bear_credit_band", 0)) > 0 for q in entry_states
                ),
                "sessions_either_credit_band": sum(
                    int(q.get("bull_credit_band", 0)) > 0
                    or int(q.get("bear_credit_band", 0)) > 0
                    for q in entry_states
                ),
            }
            if mode == "minute_presence":
                by_clock[clock] = {
                    **entry_summary,
                    "candidate_paths": len(clock_paths),
                    "source_errors": len(clock_paths) - len(valid),
                    "full_minute_presence": sum(
                        bool(p.get("full_minute_presence")) for p in valid
                    ),
                    "paths_with_zero_bid_carry": sum(
                        int(p.get("zero_bid_carry_minutes", 0)) > 0 for p in valid
                    ),
                    "paths_with_unknown_minutes": sum(
                        int(p.get("unknown_minutes", 0)) > 0 for p in valid
                    ),
                    "synchrony_proven": False,
                }
                continue
            grid_summary: dict[str, Any] = {}
            for limit in replay.SYNCHRONY_GRID_SECONDS:
                key = str(limit)
                states = [p["synchrony"][key] for p in valid]
                grid_summary[key] = {
                    "paths_with_any_ready_event": sum(s["ready_events"] > 0 for s in states),
                    "decision_boundary_ready": sum(bool(s["decision_boundary_ready"]) for s in states),
                    "end_boundary_ready": sum(bool(s["end_boundary_ready"]) for s in states),
                    "paths_with_zero_bid_carry_ready": sum(
                        s["zero_bid_carry_ready_events"] > 0 for s in states
                    ),
                }
            by_clock[clock] = {
                **entry_summary,
                "candidate_paths": len(clock_paths),
                "source_errors": len(clock_paths) - len(valid),
                "primary_entry_ready": sum(
                    bool(p.get("primary_entry_ready")) for p in valid
                ),
                "primary_time_close_ready": sum(
                    bool(p.get("primary_time_close_ready")) for p in valid
                ),
                "primary_leg_synchrony_seconds": float(PRIMARY_LEG_SYNCHRONY_SECONDS),
                "entry_max_lag_seconds": ENTRY_MAX_LAG_SECONDS,
                "time_close_max_package_age_seconds": TIME_CLOSE_MAX_PACKAGE_AGE_SECONDS,
                "grid": grid_summary,
            }
        summary[partition] = {
            "sessions": len(part_rows),
            "entry_errors": sum(bool(row.get("entry_error")) for row in part_rows),
            "by_clock": by_clock,
        }
    return summary


def run_live(
    base_url: str,
    timeout: int,
    max_workers: int,
    start_date: str,
    end_date: str,
    mode: str = "tick_synchrony",
) -> dict[str, Any]:
    if base_url.rstrip("/") not in {
        "http://127.0.0.1:25503/v3",
        "http://localhost:25503/v3",
    }:
        raise ClosePathCoverageError("Theta source must be the incumbent localhost v3 Terminal")
    if not 1 <= max_workers <= MAX_WORKERS:
        raise ClosePathCoverageError(f"max_workers must be 1..{MAX_WORKERS}")
    if mode not in MODES:
        raise ClosePathCoverageError("close-path mode is not frozen")
    if not (PANEL_START <= start_date <= end_date <= PANEL_END):
        raise ClosePathCoverageError("requested range is outside the frozen panel")
    stock_dates, expiration_dates = entry._list_dates(base_url, timeout)
    expirations = set(expiration_dates)
    dates = [d for d in stock_dates if start_date <= d <= end_date and d in expirations]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(pool.map(lambda d: audit_day(base_url, d, timeout, mode=mode), dates))
    return {
        "schema": "spy_0dte_close_path_coverage/v1",
        "status": "coverage_only_no_economic_values",
        "mode": mode,
        "interval": "tick" if mode == "tick_synchrony" else "1m",
        "synchrony_grid_seconds": (
            [str(v) for v in replay.SYNCHRONY_GRID_SECONDS]
            if mode == "tick_synchrony" else []
        ),
        "start_date": start_date,
        "end_date": end_date,
        "rows": rows,
        "summary": summarize(rows, mode=mode),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:25503/v3")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--start-date", default=PANEL_START)
    parser.add_argument("--end-date", default=PANEL_END)
    parser.add_argument("--mode", choices=MODES, default="tick_synchrony")
    parser.add_argument("--out")
    args = parser.parse_args()
    result = run_live(
        args.base_url, args.timeout, args.max_workers,
        args.start_date, args.end_date, args.mode,
    )
    text = json.dumps(result, sort_keys=True, separators=(",", ":"))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(text + "\n")
        tmp.replace(out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
