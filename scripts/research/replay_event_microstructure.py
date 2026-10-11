"""Bounded, no-persistence replay for the event-microstructure research study.

This is a research transport adapter around the existing Polygon/Massive stocks
REST client. It intentionally does NOT reuse Entry Radar C3's cache or create a
minute-data store. One invocation fetches one declared session for a small,
bounded symbol set, runs the pure research calculator, prints JSON, and exits.

USO is an explicitly disclosed oil-price proxy, not WTI/Brent truth.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from research import event_microstructure_study as study  # noqa: E402

SCHEMA = "research.event_microstructure_replay.v1"
AGGS_PATH = "/v2/aggs/ticker/{symbol}/range/1/minute/{session}/{session}"
AGGS_PARAMS: dict[str, Any] = {
    "adjusted": "true",
    "sort": "asc",
    "limit": 50000,
}
MAX_SYMBOLS = 6
_SYMBOL_RE = re.compile(r"\A[A-Z][A-Z0-9.-]{0,14}\Z")
_ALLOWED_MODES = frozenset({"public_reconstruction", "operational_pit"})


class ReplayContractError(ValueError):
    """Raised when a replay request would exceed its bounded research contract."""


def _utc(value: str, field: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ReplayContractError(f"{field} is required")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ReplayContractError(f"{field} must be ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ReplayContractError(f"{field} must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _symbol(value: str, field: str) -> str:
    symbol = str(value or "").strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ReplayContractError(f"{field} is not a bounded U.S.-listed symbol")
    return symbol


def _polygon_symbol(symbol: str) -> str:
    return symbol.replace("-", ".")


def default_transport() -> Callable[[str, Mapping[str, Any]], list[dict[str, Any]]]:
    """Resolve the incumbent entitled REST transport lazily."""
    from collectors.polygon_options import PolygonOptions  # noqa: PLC0415

    client = PolygonOptions()
    if not client.enabled():
        raise ReplayContractError(
            "POLYGON_API_KEY/MASSIVE_API_KEY is unavailable on this host"
        )

    def _get(path: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        return list(client._get(path, dict(params)) or [])  # noqa: SLF001

    return _get


def minute_close_points(
    rows: Sequence[Mapping[str, Any]],
    *,
    session: date,
) -> list[dict[str, Any]]:
    """Convert Massive minute aggregates into PIT-safe close observations.

    Massive/Polygon aggregate t is the minute START in epoch milliseconds.
    The minute close cannot be known at that start timestamp, so the research
    observation is stamped at t + 60 seconds. Using t directly would introduce
    one minute of look-ahead into the event ordering.
    """
    out: list[dict[str, Any]] = []
    seen: dict[datetime, float] = {}
    for idx, row in enumerate(rows):
        try:
            start_ms = int(row["t"])
            close = float(row["c"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReplayContractError(
                f"vendor row {idx} lacks valid t/c fields"
            ) from exc
        if close <= 0:
            raise ReplayContractError(f"vendor row {idx} has non-positive close")
        start = datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc)
        known_at = start + timedelta(minutes=1)
        prior = seen.get(known_at)
        if prior is not None and prior != close:
            raise ReplayContractError(
                f"conflicting vendor closes at {_iso(known_at)}"
            )
        seen[known_at] = close
    for ts, close in sorted(seen.items()):
        out.append({"ts": _iso(ts), "price": close})
    return out


def fetch_session(
    symbol: str,
    session: date,
    *,
    transport: Callable[[str, Mapping[str, Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    """Fetch one symbol/session and return points plus a bounded source receipt."""
    canonical = _symbol(symbol, "symbol")
    path = AGGS_PATH.format(
        symbol=_polygon_symbol(canonical),
        session=session.isoformat(),
    )
    rows = transport(path, dict(AGGS_PARAMS)) or []
    points = minute_close_points(rows, session=session)
    first = points[0]["ts"] if points else None
    last = points[-1]["ts"] if points else None
    return {
        "symbol": canonical,
        "source": "massive_polygon_stocks_rest_minute_aggs",
        "endpoint": path,
        "params": dict(AGGS_PARAMS),
        "session": session.isoformat(),
        "row_count": len(points),
        "first_close_known_at": first,
        "last_close_known_at": last,
        "points": points,
    }


def replay(
    *,
    event: Mapping[str, Any],
    session: date,
    causal_symbol: str,
    response_symbol: str,
    benchmark_symbol: str,
    secondary_causal_symbol: str | None = None,
    mode: str = "public_reconstruction",
    transport: Callable[[str, Mapping[str, Any]], list[dict[str, Any]]] | None = None,
    causal_threshold_bps: float = 25.0,
    response_threshold_bps: float = 25.0,
) -> dict[str, Any]:
    """Run one bounded event replay with zero persistence."""
    if mode not in _ALLOWED_MODES:
        raise ReplayContractError(f"unsupported mode: {mode}")
    symbols = [
        _symbol(causal_symbol, "causal_symbol"),
        _symbol(response_symbol, "response_symbol"),
        _symbol(benchmark_symbol, "benchmark_symbol"),
    ]
    secondary = (
        _symbol(secondary_causal_symbol, "secondary_causal_symbol")
        if secondary_causal_symbol
        else None
    )
    if secondary:
        symbols.append(secondary)
    if len(set(symbols)) != len(symbols):
        raise ReplayContractError("replay symbols must be distinct")
    if len(symbols) > MAX_SYMBOLS:
        raise ReplayContractError("symbol bound exceeded")

    available_at = _utc(str(event.get("available_at") or ""), "event.available_at")
    if abs((available_at.date() - session).days) > 1:
        raise ReplayContractError(
            "event available_at is inconsistent with the declared session"
        )

    get = transport or default_transport()
    fetched = {
        symbol: fetch_session(symbol, session, transport=get)
        for symbol in symbols
    }

    primary = study.analyze_event(
        event=event,
        causal_points=fetched[symbols[0]]["points"],
        response_points=fetched[symbols[1]]["points"],
        benchmark_points=fetched[symbols[2]]["points"],
        mode=mode,
        causal_direction=-1,
        response_direction=1,
        causal_threshold_bps=causal_threshold_bps,
        response_threshold_bps=response_threshold_bps,
    )
    secondary_result = None
    if secondary is not None:
        secondary_result = study.first_threshold_cross(
            fetched[secondary]["points"],
            anchor=primary["known_at"],
            direction=-1,
            threshold_bps=causal_threshold_bps,
            horizon_minutes=10,
        )

    return {
        "schema": SCHEMA,
        "authority": dict(study.AUTHORITY),
        "mode": mode,
        "event_id": primary["event_id"],
        "session": session.isoformat(),
        "causal_proxy": {
            "symbol": symbols[0],
            "role": "oil_price_proxy_not_direct_crude",
        },
        "secondary_causal": None if secondary is None else {
            "symbol": secondary,
            "role": "energy_equity_secondary_check",
            "threshold_result": secondary_result,
        },
        "response": {"symbol": symbols[1]},
        "benchmark": {"symbol": symbols[2]},
        "study_result": primary,
        "sources": {
            symbol: {
                key: value
                for key, value in receipt.items()
                if key != "points"
            }
            for symbol, receipt in fetched.items()
        },
        "persistence": "none_stdout_only",
        "direct_crude_status": (
            "not_used; direct WTI/Brent minute authority is a separate source gate"
        ),
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--event-id", required=True)
    p.add_argument("--session", required=True)
    p.add_argument("--event-time", required=True)
    p.add_argument("--available-at", required=True)
    p.add_argument("--observed-at")
    p.add_argument(
        "--mode",
        choices=sorted(_ALLOWED_MODES),
        default="public_reconstruction",
    )
    p.add_argument("--causal", default="USO")
    p.add_argument("--secondary-causal", default="XLE")
    p.add_argument("--response", default="SMH")
    p.add_argument("--benchmark", default="QQQ")
    p.add_argument("--causal-threshold-bps", type=float, default=25.0)
    p.add_argument("--response-threshold-bps", type=float, default=25.0)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        session = date.fromisoformat(args.session)
    except ValueError as exc:
        raise SystemExit("--session must be YYYY-MM-DD") from exc

    available = _utc(args.available_at, "--available-at")
    observed = (
        _utc(args.observed_at, "--observed-at")
        if args.observed_at
        else datetime.now(timezone.utc)
    )
    if args.mode == "operational_pit" and not args.observed_at:
        raise SystemExit("--observed-at is required for operational_pit")

    event = {
        "event_id": args.event_id,
        "event_time": _iso(_utc(args.event_time, "--event-time")),
        "available_at": _iso(available),
        "observed_at": _iso(observed),
    }
    try:
        result = replay(
            event=event,
            session=session,
            causal_symbol=args.causal,
            secondary_causal_symbol=args.secondary_causal or None,
            response_symbol=args.response,
            benchmark_symbol=args.benchmark,
            mode=args.mode,
            causal_threshold_bps=args.causal_threshold_bps,
            response_threshold_bps=args.response_threshold_bps,
        )
    except (ReplayContractError, study.StudyContractError) as exc:
        print(json.dumps({"schema": SCHEMA, "error": str(exc)}, sort_keys=True))
        return 2

    json.dump(result, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
