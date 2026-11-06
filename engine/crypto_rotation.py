"""Display-only same-window returns versus Bitcoin on one fixed basis.

No I/O. No score, forecast, weight, or allocation. A missing input stays
unavailable. Market-cap share is never read as a price return.

The basis is fixed for this view: 30 calendar days, USD, equal member
weight, benchmark BTC. ``origin_date + 30 days`` must equal
``cohort_snapshot_date``. Every comparison row echoes that same basis.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from types import MappingProxyType

HORIZON_DAYS = 30
QUOTE_CURRENCY = "USD"
WEIGHTING = "equal_member"
BENCHMARK = "BTC"

_REQUIRED = (
    "origin_date",
    "horizon_days",
    "quote_currency",
    "cohort_snapshot_date",
    "weighting",
    "benchmark",
)
_ALLOWED = set(_REQUIRED) | {"members"}


def relative_returns(rows: Sequence[Mapping], *, basis: Mapping) -> dict:
    """Per-asset same-window USD price return minus the BTC return.

    The returned ``basis`` object is the same object on the result and on
    every comparison row. Disqualified rows stay in ``comparisons`` and stay
    out of ``signals``. A missing benchmark does not become zero.
    """
    frozen = _normalize_basis(basis)
    index = _index_rows(rows)
    symbols = frozen["members"] if "members" in frozen else tuple(index)
    benchmark_return = _price_return(index.get(frozen["benchmark"]), frozen)
    comparisons = [
        _comparison(symbol, index.get(symbol), frozen, benchmark_return)
        for symbol in symbols
    ]
    return {
        "basis": frozen,
        "benchmark_return_pct": benchmark_return,
        "comparisons": comparisons,
        "signals": [row for row in comparisons if row["signal"]],
    }


def coverage(rows: Sequence[Mapping], cohort: Sequence[str]) -> dict:
    """Declared cohort size, how many members have a usable price return, and who does not.

    ``missing`` lists every declared member that is not available, in cohort
    order. A negative return stays available. Two usable rows on different
    fixed windows raise, because this function will not pick a date.
    """
    members = _parse_members(cohort)
    index = _index_rows(rows)
    missing: list[str] = []
    windows: list[tuple[str, str]] = []
    available = 0
    for symbol in members:
        row = index.get(symbol)
        window = None if row is None else _usable_window(row)
        if window is None:
            missing.append(symbol)
            continue
        available += 1
        windows.append(window)
    unique = set(windows)
    if len(unique) > 1:
        raise ValueError(
            "cohort rows carry more than one fixed window; refusing to pick one"
        )
    window = None
    if unique:
        origin, snapshot = windows[0]
        window = {"origin_date": origin, "cohort_snapshot_date": snapshot}
    return {
        "declared": len(members),
        "available": available,
        "missing": missing,
        "window": window,
    }


def _comparison(
    symbol: str,
    row: Mapping | None,
    basis: Mapping,
    benchmark_return: float | None,
) -> dict:
    observed = _observe(row, basis)
    asset_return = observed["asset_return_pct"]
    status = observed["status"]
    reason = observed["reason"]
    relative = None
    signal = False
    if status == "available" and symbol == basis["benchmark"]:
        relative = 0.0
    elif status == "available" and benchmark_return is None:
        status = "unavailable"
        reason = "benchmark_unavailable"
    elif status == "available":
        relative = asset_return - benchmark_return
        signal = True
    return {
        "symbol": symbol,
        "basis": basis,
        "asset_return_pct": asset_return if status != "withheld" else None,
        "benchmark_return_pct": benchmark_return,
        "relative_return_pct": relative,
        "market_cap_share_change_pct": observed["share_change_pct"],
        "status": status,
        "reason": reason,
        "signal": signal,
    }


def _observe(row: Mapping | None, basis: Mapping) -> dict:
    share = _share(row)
    if row is None:
        return _obs("unavailable", "absent", None, share)
    if row.get("history_reset"):
        return _obs("unavailable", "identity_break", None, share)
    if _short_history(row):
        return _obs("unavailable", "short_history", None, share)
    if _fixed_window(row) != (basis["origin_date"], basis["cohort_snapshot_date"]):
        return _obs("unavailable", "window_unavailable", None, share)
    kind = _disqualifier(row)
    if kind == "unclassified":
        return _obs("unavailable", "unclassified", None, share)
    if kind is not None:
        # Keep the raw number off the return fields. Share, depeg, wrapper,
        # and supply changes are withheld observations, not relative returns.
        return _obs("withheld", kind, None, share)
    price = _finite(row.get("return_pct"))
    if price is None:
        return _obs("unavailable", "return_unavailable", None, share)
    return _obs("available", None, price, share)


def _obs(status: str, reason: str | None, price: float | None, share: float | None) -> dict:
    return {
        "status": status,
        "reason": reason,
        "asset_return_pct": price,
        "share_change_pct": share,
    }


def _price_return(row: Mapping | None, basis: Mapping) -> float | None:
    observed = _observe(row, basis)
    if observed["status"] != "available":
        return None
    return observed["asset_return_pct"]


def _usable_window(row: Mapping) -> tuple[str, str] | None:
    """A member counts as available only with a clean fixed-window price return."""
    if row.get("history_reset") or _short_history(row):
        return None
    window = _fixed_window(row)
    if window is None or _disqualifier(row) is not None:
        return None
    if _finite(row.get("return_pct")) is None:
        return None
    return window


def _fixed_window(row: Mapping) -> tuple[str, str] | None:
    try:
        origin = _parse_date(row.get("window_origin"), field="window_origin")
        snapshot = _parse_date(row.get("as_of"), field="as_of")
    except ValueError:
        return None
    horizon = row.get("horizon_days")
    if isinstance(horizon, bool) or horizon != HORIZON_DAYS:
        return None
    if row.get("quote_currency") != QUOTE_CURRENCY or row.get("weighting") != WEIGHTING:
        return None
    if origin + timedelta(days=HORIZON_DAYS) != snapshot:
        return None
    return origin.isoformat(), snapshot.isoformat()


def _disqualifier(row: Mapping) -> str | None:
    kind = row.get("instrument_kind")
    if kind in {"wrapper", "depeg"}:
        return str(kind)
    if row.get("wrapper") is True:
        return "wrapper"
    if row.get("depeg") is True:
        return "depeg"
    if row.get("supply_change") is True:
        return "supply_change"
    if row.get("return_kind") == "market_cap_share":
        return "share_change"
    if kind != "spot" or row.get("return_kind") != "price":
        return "unclassified"
    return None


def _short_history(row: Mapping) -> bool:
    if "history_days" not in row or row.get("history_days") is None:
        return False
    days = row.get("history_days")
    if isinstance(days, bool) or not isinstance(days, int):
        return True
    return days < HORIZON_DAYS


def _share(row: Mapping | None) -> float | None:
    if row is None or "market_cap_share_change_pct" not in row:
        return None
    return _finite(row.get("market_cap_share_change_pct"))


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _normalize_basis(basis: Mapping) -> MappingProxyType:
    if not isinstance(basis, Mapping):
        raise TypeError("basis must be a mapping")
    missing = [key for key in _REQUIRED if key not in basis]
    if missing:
        raise ValueError(f"basis missing {missing}")
    unknown = sorted(set(basis) - _ALLOWED)
    if unknown:
        raise ValueError(f"unknown basis fields {unknown}")
    if isinstance(basis.get("horizon_days"), bool) or basis.get("horizon_days") != HORIZON_DAYS:
        raise ValueError("horizon_days is fixed at 30 calendar days")
    if basis.get("quote_currency") != QUOTE_CURRENCY:
        raise ValueError("quote_currency is fixed at USD")
    if basis.get("weighting") != WEIGHTING:
        raise ValueError("weighting is fixed at equal_member")
    if basis.get("benchmark") != BENCHMARK:
        raise ValueError("benchmark is fixed at BTC")
    origin = _parse_date(basis.get("origin_date"), field="origin_date")
    snapshot = _parse_date(basis.get("cohort_snapshot_date"), field="cohort_snapshot_date")
    if origin + timedelta(days=HORIZON_DAYS) != snapshot:
        raise ValueError("origin_date + horizon_days must equal cohort_snapshot_date")
    payload: dict = {
        "origin_date": origin.isoformat(),
        "horizon_days": HORIZON_DAYS,
        "quote_currency": QUOTE_CURRENCY,
        "cohort_snapshot_date": snapshot.isoformat(),
        "weighting": WEIGHTING,
        "benchmark": BENCHMARK,
    }
    if "members" in basis:
        payload["members"] = _parse_members(basis["members"])
    return MappingProxyType(payload)


def _parse_date(value: object, *, field: str) -> date:
    if isinstance(value, datetime):
        raise ValueError(f"{field} must be a date, not a timestamp")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{field} must be YYYY-MM-DD") from None
    raise ValueError(f"{field} must be YYYY-MM-DD")


def _parse_members(cohort: object) -> tuple[str, ...]:
    if isinstance(cohort, (str, bytes)) or not isinstance(cohort, Sequence):
        raise TypeError("cohort members must be a sequence of symbols")
    symbols: list[str] = []
    for item in cohort:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("cohort member must be a non-empty symbol")
        symbol = item.strip().upper()
        if symbol in symbols:
            raise ValueError(f"duplicate cohort member {symbol}")
        symbols.append(symbol)
    return tuple(symbols)


def _index_rows(rows: object) -> dict[str, Mapping]:
    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(rows, Sequence):
        raise TypeError("rows must be a sequence of mappings")
    index: dict[str, Mapping] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError("each row must be a mapping")
        raw = row.get("symbol")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("row symbol must be a non-empty string")
        symbol = raw.strip().upper()
        if symbol in index:
            raise ValueError(f"duplicate row for {symbol}")
        index[symbol] = row
    return index
