"""Ticker-specific, display-only options observations for Brain's existing read tools."""
from __future__ import annotations

import re
import sys
from datetime import date

from lib.options_coverage import options_session_status

_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,14}")


def _number(value: object, *, positive: bool = False) -> float | None:
    if type(value) not in (int, float) or not abs(value) <= sys.float_info.max:
        return None
    if positive and value <= 0:
        return None
    return value


def published_volatility(ticker: str, params: dict, expected: date) -> dict:
    """Show bounded, dated observations from the existing member Options Hub."""
    result = {
        "ticker": ticker,
        "expected_session": expected.isoformat(),
        "exact_contract_quote": "unavailable",
        "contract_iv": None,
        "note": "These are underlying or expiry-level observations. A strike premium, contract IV, "
                "spread, breakeven or executable price requires a matched, timestamped contract quote.",
    }
    if not _SYMBOL.fullmatch(ticker):
        return result
    result["options_hub"] = hub_volatility(ticker, params, expected)
    return result

def hub_volatility(ticker: str, params: dict, expected: date) -> dict:
    """Read a single product projection after the gateway has checked member access."""
    from app.hub_data import read_vol
    from fastapi import HTTPException

    missing = {"status": "unavailable", "root": ticker}
    try:
        book = read_vol(ticker)
    except (HTTPException, OSError, ValueError):
        return missing
    if (not isinstance(book, dict) or book.get("schema") != "options_hub.vol/v1"
            or book.get("root") != ticker):
        return missing
    status = options_session_status(book.get("asof"), expected)
    if status == "unavailable":
        return missing
    result = {
        "root": ticker, "source": "ThetaData / Options Hub", "as_of": book["asof"],
        "status": "cached_after_source_error" if book.get("stale") else status,
        "iv_unit": "percent", "underlying_atm_iv_30d": _number(book.get("atm_iv"), positive=True),
        "iv_percentile_252": _number(book.get("iv_rank_252")),
    }
    if result["underlying_atm_iv_30d"] is None and not any(book.get(key) for key in ("smile", "term")):
        result["status"] = "no_observations"
    expiry = params.get("expiration")
    if not isinstance(expiry, str) or not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", expiry):
        return result
    term = book.get("term")
    if not isinstance(term, list):
        return result
    # A month-only request reports represented expiries. An exact side/strike IV
    # is eligible only when the user/model supplies an exact date and all keys match.
    prefix = expiry + "-" if len(expiry) == 7 else None
    terms = {}
    duplicates = set()
    for row in term:
        if not isinstance(row, dict) or not isinstance(row.get("exp"), str):
            continue
        day = row["exp"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            continue
        try:
            date.fromisoformat(day)
        except ValueError:
            continue
        if day < book["asof"] or not (day == expiry or (prefix and day.startswith(prefix))):
            continue
        if day in terms:
            duplicates.add(day)
        terms[day] = _number(row.get("atm_iv"), positive=True)
    result["expiry_observations"] = [
        {"expiration": day, "atm_iv_pct": terms[day] if day not in duplicates else None}
        for day in sorted(terms)
    ]
    side, strike = params.get("right"), _number(params.get("strike"), positive=True)
    if prefix or side not in ("put", "call") or strike is None:
        return result
    points = []
    matched_expiries = 0
    smiles = book.get("smile")
    for smile in smiles if isinstance(smiles, list) else ():
        if not isinstance(smile, dict) or smile.get("exp") != expiry or not isinstance(smile.get("points"), list):
            continue
        matched_expiries += 1
        for point in smile["points"]:
            if isinstance(point, dict) and _number(point.get("strike"), positive=True) == strike:
                points.append(_number(point.get(f"{side}_iv"), positive=True))
    result["selected_smile_point"] = {
        "expiration": expiry, "strike": strike, "right": side,
        "iv_pct": points[0] if matched_expiries == 1 and len(points) == 1 else None,
        "basis": "published end-of-day smile point; no bid or ask",
    }
    return result
