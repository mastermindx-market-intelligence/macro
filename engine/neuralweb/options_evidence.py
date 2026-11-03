"""Ticker-specific, display-only options observations for Brain's existing read tools."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from lib import nyse_calendar

_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,14}")
_FAMILIES = {
    "gex": ("iv30", "gamma_regime", "gamma_regime_structurally_constant", "dist_to_flip_pct",
            "wall_up_dist_pct", "wall_down_dist_pct", "max_pain_dist_pct", "pin_risk",
            "gex_confirm_verdict", "vanna_hedge_5d", "opex_days"),
    "skew": ("skew", "skew_5d_chg"),
    "ivspread": ("ivspread_rel", "ivspread_5d_chg"),
    "flow": ("net_doi", "doi_pc", "fresh_contracts", "fresh_premium_mn", "zerodte_share"),
}


def _session_status(stamp: object, expected: date) -> str:
    try:
        session = date.fromisoformat(stamp) if isinstance(stamp, str) else None
    except ValueError:
        session = None
    if session is None or not nyse_calendar.is_session(session) or session > expected:
        return "unavailable"
    return "latest_completed_session" if session == expected else "historical"


def current_state(row: dict, expected: date) -> dict:
    """A recent skew print cannot renew older GEX, volatility spread or flow evidence."""
    row = dict(row)
    statuses = {}
    for family, fields in _FAMILIES.items():
        status = _session_status(row.get(f"src_{family}_asof"), expected)
        statuses[family] = status
        if status != "latest_completed_session":
            for field in fields:
                if field in row:
                    row[field] = None
    # These exposures come from a separately dated chain. The entry table does not carry
    # that chain's clock. The row maximum and GEX summary date cannot qualify them.
    for field in ("front7_charm_share", "front7_gex_share", "signed_vanna_pressure"):
        if field in row:
            row[field] = None
    row["stored_evidence_quality"] = row.pop("evidence_quality", None)
    count = sum(status == "latest_completed_session" for status in statuses.values())
    row["evidence_quality"] = ("stale", "thin", "partial", "partial", "full")[count]
    row["source_status"] = statuses
    row["expected_session"] = expected.isoformat()
    return row


def _read_object(path: Path, limit: int) -> dict:
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) <= limit:
            value = json.loads(raw)
            if isinstance(value, dict):
                return value
    except (OSError, ValueError, RecursionError):
        pass
    return {}


def _number(value: object, *, positive: bool = False) -> float | None:
    if type(value) not in (int, float) or not abs(value) <= sys.float_info.max:
        return None
    if positive and value <= 0:
        return None
    return value


def published_volatility(root: Path, ticker: str, params: dict, expected: date) -> dict:
    """Bounded projections of the same issuer-level observations already shown on the desks."""
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
    skew = _read_object(root / "site/options_skew/latest.json", 4_000_000)
    names = skew.get("names")
    obs = names.get(ticker) if isinstance(names, dict) else None
    if (skew.get("source") == "thetadata" and skew.get("source_state") == "ok"
            and isinstance(obs, dict) and obs.get("underlying") == ticker):
        status = _session_status(obs.get("asof"), expected)
        if status != "unavailable":
            result["theta_skew_observation"] = {
                "source": "ThetaData skew desk", "as_of": obs["asof"], "status": status,
                "iv_unit": "decimal", "tenor_days": _number(obs.get("tenor_days"), positive=True),
                "atm_call_iv": _number(obs.get("atm_call_iv"), positive=True),
                "otm_put_iv": _number(obs.get("otm_put_iv"), positive=True),
                "skew": _number(obs.get("skew")),
            }
    return result

def hub_volatility(ticker: str, params: dict, expected: date) -> dict:
    """Read a single product projection after the gateway has checked member access."""
    from app.hub import hub_vol
    from fastapi import HTTPException

    missing = {"status": "unavailable", "root": ticker}
    try:
        book = hub_vol(ticker)
    except (HTTPException, OSError, ValueError):
        return missing
    if (not isinstance(book, dict) or book.get("schema") != "options_hub.vol/v1"
            or book.get("root") != ticker):
        return missing
    status = _session_status(book.get("asof"), expected)
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
