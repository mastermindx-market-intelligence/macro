"""Read-only presentation of an existing US model-plan record.

Original terms keep their original clocks. A board identity read supplies only
company metadata; it cannot supply a quote, management date, fill or new action.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import math
import re

_SYMBOL = re.compile(r"[A-Z0-9^][A-Z0-9.^=_-]{0,19}\Z")
_PLAN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_LIFE = {
    "watch": ("Watch", "观察"), "ready": ("Ready", "就绪"),
    "entered": ("Entered", "入场"), "delivering": ("Delivering", "达标"),
    "overtime": ("Overtime", "超时"), "invalidated": ("Invalidated", "失效"),
    "resolved": ("Resolved", "已结"),
}


def _text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return value if value > 0 and math.isfinite(value) else None
    except (OverflowError, ValueError):
        return None


def _day(value):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def present_plan_record(plan, *, identity=None, episode=None):
    """Project one native row without selecting, joining or updating any records.

    ``identity`` and ``episode`` are the caller's existing, already bound metadata
    maps. Their values never replace the plan's terms, lifecycle or source dates.
    """
    p = plan if isinstance(plan, Mapping) else {}
    identity = identity if isinstance(identity, Mapping) else {}
    episode = episode if isinstance(episode, Mapping) else {}
    board = p.get("board_read")
    board = board if isinstance(board, Mapping) else {}
    # The attached read names its security. Do not present a foreign screen's
    # metadata or date as belonging to this plan, even if the row was malformed.
    ticker = _text(p.get("asset"))
    if board.get("ticker") != ticker or not ticker:
        board = {}
    fields = board.get("fields")
    fields = fields if isinstance(fields, Mapping) else {}

    def metadata(key):
        field = fields.get(key)
        if isinstance(field, Mapping) and field.get("state") == "available":
            value = _text(field.get("value"))
            if value:
                return value
        return _text(identity.get(key))

    life = p.get("lifecycle_state")
    life = life if isinstance(life, str) and life in _LIFE else "unknown"
    en, zh = _LIFE.get(life, ("State unavailable", "状态暂缺"))
    targets = p.get("targets")
    targets = targets if isinstance(targets, (list, tuple)) else []
    zone = p.get("entry_zone")
    zone = zone if isinstance(zone, Mapping) else {}
    low, high = _amount(zone.get("low")), _amount(zone.get("high"))
    if low is None or high is None or high < low:
        low = high = None
    horizon = _amount(p.get("horizon_days"))
    if horizon is not None and horizon != int(horizon):
        horizon = None
    newer = _text(episode.get("newer"))
    return {
        "plan_id": _text(p.get("id")), "ticker": ticker,
        "href": "stock.html#" + ticker if ticker and _SYMBOL.fullmatch(ticker) else None,
        "name": metadata("name"), "sector": metadata("sector"),
        "life": life, "life_en": en, "life_zh": zh,
        "created_date": _day(p.get("plan_asof") or p.get("recorded_at")),
        "price_basis_date": _day(p.get("price_basis_date")),
        "screen_date": _day(board.get("as_of")),
        "entry": _amount(p.get("entry")), "invalidation": _amount(p.get("invalidation")),
        "t1": _amount(targets[0]) if targets else None,
        "t2": _amount(targets[1]) if len(targets) > 1 else None,
        "zone_low": low, "zone_high": high,
        "horizon_days": int(horizon) if horizon is not None else None,
        "pulse_en": _text(p.get("pulse")), "pulse_zh": _text(p.get("pulse_zh")),
        "newer_href": "#pv-" + newer if newer and _PLAN_ID.fullmatch(newer) else None,
    }
