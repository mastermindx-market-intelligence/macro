"""Allowlisted display of one row from the published US Prophet main list.

No ranking, admission, entry calculation, plan join or source I/O occurs here.
The caller binds the raw publication. Source clocks remain independent: the
row's signal_asof is a signal session, never an entry-assessment timestamp.
"""
from __future__ import annotations

from datetime import date, datetime
import math
import re
from typing import Any

TICKER = re.compile(r"[A-Z][A-Z0-9.-]{0,31}\Z", re.ASCII)
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z", re.ASCII)
_CLOCK = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])\Z", re.ASCII)


class BoardDetailInvalid(ValueError):
    """The publication cannot support a complete, unambiguous display read."""


def _object(value: Any, *, nullable: bool = True) -> dict:
    if value is None and nullable:
        return {}
    if not isinstance(value, dict):
        raise BoardDetailInvalid("invalid object")
    return value


def _text(value: Any, limit: int = 1024) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise BoardDetailInvalid("invalid text")
    return value


def _number(value: Any) -> int | float | None:
    if value is None:
        return None
    if type(value) not in (int, float):
        raise BoardDetailInvalid("invalid number")
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise BoardDetailInvalid("invalid number") from exc
    if not finite:
        raise BoardDetailInvalid("invalid number")
    return value


def _boolean(value: Any) -> bool | None:
    if value is not None and type(value) is not bool:
        raise BoardDetailInvalid("invalid boolean")
    return value


def _day(value: Any, *, nullable: bool = True) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not _DAY.fullmatch(value):
        raise BoardDetailInvalid("invalid session")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise BoardDetailInvalid("invalid session") from exc
    return value


def _clock(value: Any) -> str | None:
    if value is None or isinstance(value, str) and _DAY.fullmatch(value):
        return _day(value)
    if not isinstance(value, str) or not _CLOCK.fullmatch(value):
        raise BoardDetailInvalid("invalid price clock")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BoardDetailInvalid("invalid price clock") from exc
    return value


def project_board_detail(board: Any, ticker: str) -> dict:
    """Read buy[] only; valid absence means not_on_main_list, not no setup.

    Nullable fields preserve missing information, false and numeric zero. The
    adapter does not impose a new trading-geometry rule: a zero-width zone or
    a stop inside a zone may be the actual owner's published output.
    """
    if not isinstance(ticker, str) or not TICKER.fullmatch(ticker):
        raise BoardDetailInvalid("invalid requested ticker")
    board = _object(board, nullable=False)
    as_of = _day(board.get("as_of"), nullable=False)
    rows = board.get("buy")
    if not isinstance(rows, list) or len(rows) > 10_000:
        raise BoardDetailInvalid("invalid main list")
    selected = None
    seen = set()
    for value in rows:
        row = _object(value, nullable=False)
        symbol = row.get("ticker")
        if not isinstance(symbol, str):
            raise BoardDetailInvalid("invalid row identity")
        symbol = symbol.strip().upper()
        if not TICKER.fullmatch(symbol) or symbol in seen:
            raise BoardDetailInvalid("ambiguous row identity")
        seen.add(symbol)
        if symbol == ticker:
            selected = row
    if selected is None:
        return {"status": "not_on_main_list", "ticker": ticker, "as_of": as_of, "row": None}

    signal = _object(selected.get("signal"))
    hold = _object(selected.get("hold"))
    entry_raw = selected.get("entry_signal")
    entry = None
    if entry_raw is not None:
        entry_raw = _object(entry_raw, nullable=False)
        zone_raw = entry_raw.get("buy_zone")
        zone = None
        if zone_raw is not None:
            zone_raw = _object(zone_raw, nullable=False)
            zone = {"low": _number(zone_raw.get("low")), "high": _number(zone_raw.get("high"))}
        entry = {
            "status": _text(entry_raw.get("status"), 128),
            "headline": _text(entry_raw.get("headline"), 4096),
            "headline_zh": _text(entry_raw.get("headline_zh"), 4096),
            "buy_zone": zone,
            "stop": _number(entry_raw.get("stop")),
            "chase_above": _number(entry_raw.get("chase_above")),
        }
    return {
        "status": "ready", "ticker": ticker, "as_of": as_of,
        "row": {
            "ticker": ticker,
            "name": _text(selected.get("name")),
            "sector": _text(selected.get("sector")),
            "price": _number(selected.get("price")),
            "price_as_of": _clock(selected.get("price_as_of")),
            "signal_asof": _day(selected.get("signal_asof")),
            "entry_signal": entry,
            "entry_signal_null_reason": _text(selected.get("entry_signal_null_reason")),
            "hold": {"invalidation": _number(hold.get("invalidation"))},
            "signal": {
                "reason": _text(signal.get("reason"), 4096),
                "above200": _boolean(signal.get("above200")),
                "weekly_bull": _boolean(signal.get("weekly_bull")),
                "provisional": _boolean(signal.get("provisional")),
                "tier_observed_date": _day(signal.get("tier_observed_date")),
                "tier_observation_provisional": _boolean(signal.get("tier_observation_provisional")),
            },
            "lane": _text(selected.get("lane"), 128),
            "stage": _text(selected.get("stage"), 128),
        },
    }
