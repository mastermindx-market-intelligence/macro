"""Exact Massive snapshot byte decoder for labeled Plan reference context only.

No request, endpoint activation, current-quote admission, fill or entry inference.
The caller retains source bytes; digest consistency does not authenticate capture.
Snapshot last_updated is preserved as an exact integer, never relabeled SIP time.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json

from engine.options_nbbo_cohort import validate_contract


class QuoteContextError(ValueError):
    pass


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise QuoteContextError("duplicate JSON key")
        out[key] = value
    return out


def _price(value):
    if type(value) not in (int, Decimal):
        return None
    number = Decimal(value)
    if (not number.is_finite() or not 0 <= number <= 1e9
            or not -18 <= number.as_tuple().exponent <= 9
            or len(number.as_tuple().digits) > 32):
        return None
    return format(number, "f")


def normalize_massive_plan_quote(raw, *, contract, origin, path, observed_at, http_status):
    """Decode one bounded exact-ticker response without requesting or qualifying it.

    Decimal price strings and integer snapshot clocks avoid float precision loss.
    Missing quotes never fall back to day.close, last_trade, midpoint or fair value.
    Documented timeframe is a vendor declaration; actual entitlement, event-clock
    semantics, product session and firm conditions still need consumer evidence.
    """
    contract = validate_contract(contract)
    ticker = "O:" + contract["occ_symbol"].replace(" ", "")
    expected_path = "/v3/snapshot/options/" + contract["root"] + "/" + ticker
    if (origin not in ("https://api.massive.com", "https://api.polygon.io")
            or path != expected_path or type(http_status) is not int or http_status != 200):
        raise QuoteContextError("exact response origin/path/status mismatch")
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("missing offset")
    except (ValueError, TypeError, AttributeError):
        raise QuoteContextError("observation clock unknown") from None
    if type(raw) is not bytes or not 0 < len(raw) <= 1024 * 1024:
        raise QuoteContextError("response bytes absent or oversized")
    try:
        payload = json.loads(raw, parse_float=Decimal, object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(QuoteContextError("nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise QuoteContextError("invalid snapshot JSON") from exc
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise QuoteContextError("response not successful")
    result = payload.get("results")
    if not isinstance(result, dict):
        raise QuoteContextError("exact snapshot result absent")
    details = result.get("details")
    if (not isinstance(details, dict) or details.get("ticker") != ticker
            or details.get("contract_type") != contract["right"]
            or details.get("expiration_date") != contract["expiration"]
            or _price(details.get("strike_price")) is None
            or Decimal(str(details["strike_price"])) != Decimal(contract["strike"])):
        raise QuoteContextError("exact contract mismatch")
    underlying = result.get("underlying_asset")
    if underlying is not None and (not isinstance(underlying, dict)
                                 or underlying.get("ticker") != contract["root"]):
        raise QuoteContextError("underlying mismatch")
    out = dict(schema="options.plan_quote_context/v1", contract=contract,
        source=dict(provider="massive", origin=origin, path=path, http_status=http_status,
            response_sha256=sha256(raw).hexdigest(), response_bytes=len(raw), observed_at=observed_at),
        quote_kind="VENDOR_SNAPSHOT_REFERENCE", bid=None, ask=None, bid_size=None, ask_size=None,
        bid_exchange=None, ask_exchange=None, raw_last_updated=None, vendor_timeframe=None,
        clock_kind="MASSIVE_SNAPSHOT_LAST_UPDATED_UNVERIFIED", event_time_utc=None,
        market_session="UNKNOWN", recency="UNKNOWN", current_quote_eligible=False,
        raw_conditions=None, conditions_status="UNKNOWN", source_authentication="not_established_by_this_function",
        quality=[])
    quote = result.get("last_quote")
    if quote is None:
        out["quality"] = ["NO_QUOTE", "ACCESS_UNVERIFIED"]
        return out
    if not isinstance(quote, dict):
        raise QuoteContextError("invalid last_quote")
    for side in ("bid", "ask"):
        out[side] = _price(quote.get(side))
        size, venue = quote.get(side + "_size"), quote.get(side + "_exchange")
        out[side + "_size"] = size if type(size) is int and 0 <= size <= 1_000_000_000 else None
        out[side + "_exchange"] = venue if type(venue) is int and venue >= 0 else None
    stamp = quote.get("last_updated")
    out["raw_last_updated"] = stamp if type(stamp) is int and 0 <= stamp < 10**22 else None
    frame = quote.get("timeframe")
    conditions = quote.get("conditions")
    if (isinstance(conditions, list) and len(conditions) <= 64
            and all(type(c) is int and 0 <= c <= 1_000_000 for c in conditions)):
        out["raw_conditions"] = list(conditions)
    out["vendor_timeframe"] = frame if isinstance(frame, str) and len(frame) <= 64 else None
    out["recency"] = {"REAL-TIME": "VENDOR_REALTIME_DECLARED", "DELAYED": "DELAYED"}.get(frame, "UNKNOWN") if isinstance(frame, str) else "UNKNOWN"
    quality = out["quality"]
    if out["bid"] is None and out["ask"] is None:
        quality.append("NO_QUOTE")
    elif out["bid"] is None or out["ask"] is None:
        quality.append("ONE_SIDED")
    else:
        bid, ask = Decimal(out["bid"]), Decimal(out["ask"])
        if bid == ask:
            quality.append("LOCKED")
        elif bid > ask:
            quality.append("CROSSED")
        if bid == 0 or ask == 0:
            quality.append("ZERO_PRICE")
    if out["bid_size"] is None or out["ask_size"] is None:
        quality.append("SIZE_UNKNOWN")
    if out["bid_size"] == 0 or out["ask_size"] == 0:
        quality.append("ZERO_SIZE")
    quality.extend(["CLOCK_UNVERIFIED", "SESSION_UNKNOWN", "CONDITIONS_UNKNOWN", "ACCESS_UNVERIFIED"])
    return out
