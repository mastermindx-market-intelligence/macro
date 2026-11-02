"""Descriptive measurements of a caller-supplied, deduplicated print population.

This pure, currently unmounted helper does not acquire, deduplicate or publish
data. The producer must call it before NBBO/signing/notability filters and bind
its universe, coverage start and transactional state before publishing results.
Execution location is not buyer/seller identity, opening intent or market share.
"""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
                     ROUND_HALF_EVEN, localcontext)
import math
import re


LOCATIONS = (
    "below_bid", "at_bid", "inside_below_mid", "at_mid",
    "inside_above_mid", "at_ask", "above_ask", "UNKNOWN",
)
POPULATION = "caller_supplied_source_valid_deduplicated_observations"
_MAX_JSON_NUMBER = Decimal(str(float.fromhex("0x1.fffffffffffffp+1023")))


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return Decimal(str(value)) if math.isfinite(value) else None
    except (ValueError, OverflowError):
        return None


def _clock(value):
    if type(value) is not str:
        return None
    try:
        clock = datetime.fromisoformat(value)
        return clock if clock.utcoffset() is not None else None
    except ValueError:
        return None


def _valid(row):
    if not isinstance(row, Mapping):
        return False
    root, expiry = row.get("root"), row.get("expiration")
    # Same canonical alphabet as the incumbent Flow source validator, including
    # index aliases and punctuation-bearing roots; no silent universe narrowing.
    if type(root) is not str or re.fullmatch(r"[A-Z0-9.^=-]+", root) is None:
        return False
    if type(expiry) is not str:
        return False
    try:
        if date.fromisoformat(expiry).isoformat() != expiry:
            return False
    except ValueError:
        return False
    if row.get("right") not in ("C", "P") or _clock(row.get("trade_timestamp")) is None:
        return False
    for field in ("price", "strike"):
        value = _number(row.get(field))
        if value is None or value <= 0:
            return False
    return (
        type(row.get("size")) is int and 0 < row["size"] <= 2**63 - 1
        and type(row.get("sequence")) is int and 0 <= row["sequence"] <= 2**63 - 1
    )


def _location(row):
    bid, ask = _number(row.get("bid")), _number(row.get("ask"))
    quote, trade = _clock(row.get("quote_timestamp")), _clock(row["trade_timestamp"])
    if bid is None or ask is None or bid <= 0 or ask <= bid or quote is None or quote > trade:
        return "UNKNOWN"
    price = _number(row["price"])
    if price < bid:
        return "below_bid"
    if price == bid:
        return "at_bid"
    if price > ask:
        return "above_ask"
    if price == ask:
        return "at_ask"
    midpoint = (bid + ask) / 2
    if price == midpoint:
        return "at_mid"
    return "inside_below_mid" if price < midpoint else "inside_above_mid"


def _venue(value):
    # An integer code and a string code are intentionally distinct. This does
    # not interpret a provider-specific code or map it to a named exchange.
    if type(value) is int and 0 <= value <= 2**63 - 1:
        return f"int:{value}"
    if type(value) is str and value and value == value.strip() and len(value) <= 128:
        return f"str:{value}"
    return "UNKNOWN"


def _premium(row):
    multiplier = _number(row.get("premium_multiplier"))
    if row.get("premium_basis") != "qualified_contract_terms" or multiplier is None or multiplier <= 0:
        return None
    value = _number(row["price"]) * row["size"] * multiplier
    return value if value.is_finite() and value <= _MAX_JSON_NUMBER and float(value) > 0 else None


def _bucket():
    return {"print_count": 0, "contract_volume": 0, "premium_qualified_print_count": 0,
            "_premium": Decimal(0)}


def _add(bucket, size, premium):
    bucket["print_count"] += 1
    bucket["contract_volume"] += size
    if premium is not None:
        bucket["premium_qualified_print_count"] += 1
        bucket["_premium"] += premium


def _finish(bucket):
    result = {key: value for key, value in bucket.items() if key != "_premium"}
    count, qualified = result["print_count"], result["premium_qualified_print_count"]
    value = bucket["_premium"]
    result["premium_print_coverage"] = qualified / count if count else None
    result["qualified_premium_usd"] = float(value) if qualified and value <= _MAX_JSON_NUMBER else None
    result["premium_total_status"] = (
        "UNREPRESENTABLE" if qualified and value > _MAX_JSON_NUMBER
        else "QUALIFIED_SUBTOTAL" if qualified else "UNAVAILABLE"
    )
    return result


def measure_observed_prints(rows: list[dict] | None) -> dict:
    """Return JSON-safe totals and disjoint C/P, venue and location partitions.

    None is unavailable; [] is an observed empty population. Missing contract
    terms never become a standard 100 multiplier. Unknown quotes still count
    toward observed prints/volume. Premium is a qualified subtotal, not the
    total premium of uncovered contracts. Core sizes/sequences use int64 bounds
    to match the incumbent source validator; booleans are never numeric inputs.
    """
    if rows is not None and not isinstance(rows, list):
        raise TypeError("rows must be a list or None")
    if rows is None:
        return {"schema": "options.observed_statistics/v1", "population": POPULATION,
                "status": "UNAVAILABLE", "input_count": None, "rejected_count": None,
                "totals": None, "rights": None, "venues": None, "locations": None,
                "nbbo_print_coverage": None, "venue_print_coverage": None}
    totals = _bucket()
    rights = {key: _bucket() for key in ("C", "P")}
    locations = {key: _bucket() for key in LOCATIONS}
    venues, rejected = {}, 0
    # Include the entire binary64 exponent span as well as significant digits,
    # so reordering tiny and large positive premiums cannot discard small rows.
    # Isolate exponent limits, rounding and traps as well as precision. A caller
    # may have configured a small Emax/Emin or enabled Inexact/Rounded traps.
    # All binary64 inputs and their products fit inside this private span.
    arithmetic = Context(
        prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
        capitals=1, clamp=0, flags=[],
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )
    with localcontext(arithmetic):
        for row in rows:
            try:
                valid = _valid(row)
            except (ValueError, OverflowError, InvalidOperation):
                valid = False
            if not valid:
                rejected += 1
                continue
            location, venue, premium = _location(row), _venue(row.get("exchange")), _premium(row)
            for bucket in (totals, rights[row["right"]], locations[location], venues.setdefault(venue, _bucket())):
                _add(bucket, row["size"], premium)
    count = totals["print_count"]
    return {
        "schema": "options.observed_statistics/v1", "population": POPULATION,
        "status": "OBSERVED" if count else "NO_VALID_ROWS" if rows else "OBSERVED_EMPTY",
        "input_count": len(rows), "rejected_count": rejected,
        "totals": _finish(totals), "rights": {k: _finish(v) for k, v in rights.items()},
        "venues": {k: _finish(venues[k]) for k in sorted(venues)},
        "locations": {k: _finish(v) for k, v in locations.items()},
        "nbbo_print_coverage": (count - locations["UNKNOWN"]["print_count"]) / count if count else None,
        "venue_print_coverage": (count - venues.get("UNKNOWN", {"print_count": 0})["print_count"]) / count if count else None,
    }
