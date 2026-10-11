"""Point-in-time equity trade-pressure versus NBBO response, research-only.

Inputs are source-owner-normalized events, not a new vendor adapter or store.
Quotes must be a *continuous*, qualified SIP NBBO update sequence for the
symbol/session, NOT occasional quote snapshots attached to trades. The upstream
owner must prove capture completeness, original availability stamps, condition
eligibility and revision links. This module never upgrades those source claims.

No participant identification, order-level replenishment, predictive ranking,
trading authority, or live alerts. Quote-rule signs are explicitly proxies.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, Context

SCHEMA = "equity.pressure_response_observation/v0"
MODES = frozenset({"ACTUAL_AS_SEEN", "HISTORICAL_RECEIVABILITY", "FINAL_VINTAGE"})
VENUES = frozenset({"LIT", "TRF", "UNKNOWN"})
ACTIONS = frozenset({"ORIGINAL", "REPLACE", "CANCEL"})
MAX_FIXED_DECIMAL_CHARS = 128  # native input width, BEFORE fixed-point rendering
_EXACT_PRECISION = 2 * MAX_FIXED_DECIMAL_CHARS + 16


def _bounded_decimal(value: Decimal, name: str, *, max_width=MAX_FIXED_DECIMAL_CHARS) -> Decimal:
    """Reject exponent-amplified fixed-point values before formatting.

    R0 is deliberately source-independent from draft TP1; this is its private
    deterministic input-resource ceiling, not a new quote-signing authority.
    """
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    digits = value.as_tuple()
    count = len(digits.digits)
    exponent = digits.exponent
    left = count + exponent
    if exponent >= 0:
        width = count + exponent
    elif left > 0:
        width = count + 1
    else:
        width = 2 - left + count
    if type(max_width) is not int or not 1 <= max_width <= 2 * _EXACT_PRECISION:
        raise ValueError("invalid fixed-decimal width budget")
    if width + digits.sign > max_width:
        raise ValueError(f"{name} exceeds bounded decimal width")
    return value


def _midpoint(quote):
    """Calculate exact quote midpoint before downstream rounded markouts."""
    exact = Context(prec=_EXACT_PRECISION)
    return exact.divide(exact.add(quote["bid"], quote["ask"]), Decimal(2))



def _int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _positive_int(value, name):
    if type(value) is not int or value <= 0 or value.bit_length() > 425:
        raise ValueError(f"{name} must be a bounded positive integer")
    return value


def _name(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} requires a nonempty string")
    return value


def _amount(value, name, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(f"{name} must be a decimal number")
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} is not decimal") from exc
    if not d.is_finite() or (d < 0 if allow_zero else d <= 0):
        raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")
    return _bounded_decimal(d, name)


def _fmt(value):
    return format(value, "f")


def _quote(row, symbol, session):
    if row.get("ticker") != symbol or row.get("session") != session:
        raise ValueError("quote symbol/session mismatch")
    result = dict(row)
    for key in ("id", "source_receipt"):
        _name(row.get(key), f"quote.{key}")
    for key in ("sip_ns", "available_ns"):
        _int(row.get(key), f"quote.{key}")
    if row["available_ns"] < row["sip_ns"]:
        raise ValueError("quote availability precedes its SIP clock")
    for key in ("bid_size", "ask_size"):
        _int(row.get(key), f"quote.{key}")
    # Preserve locked/crossed/zero prices as an *unusable quote update*. Never
    # skip them and silently match a stale earlier valid quote.
    result["bid"] = _amount(row.get("bid"), "quote.bid", allow_zero=True)
    result["ask"] = _amount(row.get("ask"), "quote.ask", allow_zero=True)
    result["valid"] = (result["bid"] > 0 and result["ask"] > result["bid"]
                       and row["bid_size"] > 0 and row["ask_size"] > 0)
    for key in ("bid_exchange", "ask_exchange"):
        if row.get(key) is not None:
            _name(row[key], f"quote.{key}")
    return result


def _trade(row, symbol, session):
    if row.get("ticker") != symbol or row.get("session") != session:
        raise ValueError("trade symbol/session mismatch")
    result = dict(row)
    for key in ("id", "source_receipt", "eligibility_rules_ref"):
        _name(row.get(key), f"trade.{key}")
    for key in ("sip_ns", "available_ns", "revision"):
        _int(row.get(key), f"trade.{key}")
    if row["available_ns"] < row["sip_ns"]:
        raise ValueError("trade availability precedes its SIP clock")
    if row.get("action") not in ACTIONS:
        raise ValueError("unknown trade correction action")
    if row.get("venue_class") not in VENUES:
        raise ValueError("unknown venue class")
    if type(row.get("eligible_for_pressure")) is not bool:
        raise ValueError("condition eligibility must be an explicit boolean")
    result["price"] = _amount(row.get("price"), "trade.price")
    result["size"] = _positive_int(row.get("size"), "trade.size")
    return result


def _active_trades(rows, decision_ns):
    """As-of revision resolution: never backapply a future cancel/replacement."""
    grouped = defaultdict(dict)
    for row in rows:
        key = row["id"]
        rev = row["revision"]
        prior = grouped[key].get(rev)
        if prior is not None and prior != row:
            raise ValueError("conflicting duplicate trade revision")
        grouped[key][rev] = row
    active = []
    excluded = Counter()
    for revisions in grouped.values():
        ordered = sorted(revisions.values(), key=lambda r: r["revision"])
        if ordered[0]["revision"] != 0 or ordered[0]["action"] != "ORIGINAL":
            excluded["UNRESOLVED_ORIGINAL"] += 1
            continue
        if any(ordered[i]["revision"] != ordered[i - 1]["revision"] + 1
               for i in range(1, len(ordered))):
            excluded["MISSING_CORRECTION_GENERATION"] += 1
            continue
        if any(ordered[i]["available_ns"] <= ordered[i - 1]["available_ns"]
               for i in range(1, len(ordered))):
            raise ValueError("nonmonotone correction availability")
        visible = [r for r in ordered if r["available_ns"] <= decision_ns]
        if not visible:
            excluded["NOT_YET_AVAILABLE"] += 1
            continue
        chosen = visible[-1]
        if chosen["action"] == "CANCEL":
            excluded["CANCELLED_AS_OF"] += 1
        elif not chosen["eligible_for_pressure"]:
            excluded["CONDITION_INELIGIBLE"] += 1
        else:
            active.append(chosen)
    return active, excluded


def _prior_quote(quotes, times, stamp, *, max_age_ns, require_exact_order=False):
    point = bisect_left(times, stamp)
    # With millisecond SIP timestamps and no native within-tick sequence, a
    # simultaneous quote update makes the pre-trade state indeterminate.
    if require_exact_order and point < len(quotes) and quotes[point]["sip_ns"] == stamp:
        return None, "CLOCK_TIE"
    if point == 0:
        return None, "NO_PRIOR_QUOTE"
    latest = quotes[point - 1]
    if point > 1 and quotes[point - 2]["sip_ns"] == latest["sip_ns"]:
        return None, "AMBIGUOUS_QUOTE_ORDER"
    if not latest["valid"]:
        return None, "INVALID_NBBO"
    if stamp - latest["sip_ns"] > max_age_ns:
        return None, "STALE_NBBO"
    return latest, None


def _recovery(quotes, start_quote, start_ns, end_ns, side, *, max_age_ns):
    """Best-quote displayed-size recovery proxy, NEVER order replenishment."""
    if start_quote is None:
        return {"state": "UNKNOWN", "reason": "NO_START_QUOTE"}
    price_key, size_key, venue_key = ("bid", "bid_size", "bid_exchange") if side == "bid" else (
        "ask", "ask_size", "ask_exchange")
    initial_venue = start_quote.get(venue_key)
    if initial_venue is None:
        return {"state": "UNKNOWN", "reason": "VENUE_UNOBSERVED"}
    updates = [q for q in quotes if start_ns <= q["sip_ns"] < end_ns]
    if not updates:
        return {"state": "UNKNOWN", "reason": "NO_QUOTE_UPDATES"}
    if any(updates[i]["sip_ns"] == updates[i - 1]["sip_ns"]
           for i in range(1, len(updates))):
        return {"state": "UNKNOWN", "reason": "AMBIGUOUS_QUOTE_ORDER"}
    if end_ns - updates[-1]["sip_ns"] > max_age_ns:
        return {"state": "UNKNOWN", "reason": "STALE_RECOVERY_ENDPOINT"}
    for q in updates:
        if not q["valid"]:
            return {"state": "UNKNOWN", "reason": "INVALID_INTERVENING_NBBO"}
        if q[price_key] != start_quote[price_key] or q.get(venue_key) != initial_venue:
            return {"state": "UNKNOWN", "reason": "BEST_PRICE_OR_VENUE_CHANGED"}
    sizes = [start_quote[size_key]] + [q[size_key] for q in updates]
    trough = min(sizes)
    depletion = sizes[0] - trough
    if depletion <= 0:
        return {"state": "UNKNOWN", "reason": "NO_VISIBLE_DEPLETION"}
    return {"state": "MEASURED_PROXY", "depletion_shares": depletion,
            "recovered_shares": max(0, sizes[-1] - trough),
            "original_shares": sizes[0], "final_shares": sizes[-1],
            "best_exchange": initial_venue, "price": _fmt(start_quote[price_key])}


def measure_window(*, ticker, session, start_ns, end_ns, decision_ns,
                   watermark_ns, watermark_seen_ns, watermark_receipt,
                   source_manifest, evidence_mode, max_quote_age_ns,
                   trades, quotes):
    """Compute research-only PIT measurements for one completed half-open window.

    Input timestamps are integer UTC Unix nanoseconds. 'decision_ns' is the
    decision/availability cutoff, not a fabricated historical publication clock.
    'watermark_ns' must be a *qualified combined T+Q completeness* watermark
    whose 'watermark_seen_ns' is no later than 'decision_ns'. The source
    owner, not this function, proves the watermark's authenticity.

    'eligible_for_pressure' is a source-condition-policy decision made upstream.
    Do not pass unknown condition eligibility as True. Missing original receipts
    are errors. This function never fetches, publishes or changes source state.
    """
    _name(ticker, "ticker")
    _name(session, "session")
    _name(watermark_receipt, "watermark_receipt")
    _name(source_manifest, "source_manifest")
    for label, value in (("start_ns", start_ns), ("end_ns", end_ns),
                         ("decision_ns", decision_ns), ("watermark_ns", watermark_ns),
                         ("watermark_seen_ns", watermark_seen_ns),
                         ("max_quote_age_ns", max_quote_age_ns)):
        _int(value, label)
    if start_ns >= end_ns:
        raise ValueError("window endpoints out of order")
    if evidence_mode not in MODES:
        raise ValueError("unrecognized evidence mode")
    if watermark_seen_ns > decision_ns:
        raise ValueError("future watermark receipt")
    if watermark_seen_ns < watermark_ns:
        raise ValueError("watermark receipt precedes the completed event time")
    if watermark_ns < end_ns or end_ns > decision_ns:
        return {"schema": SCHEMA, "state": "NOT_MATURE", "reason": "WINDOW_NOT_COMPLETE",
                "ticker": ticker, "session": session, "window_end_ns": end_ns,
                "decision_ns": decision_ns, "evidence_mode": evidence_mode,
                "authority": "RESEARCH_ONLY"}
    # A later source generation cannot poison an earlier as-seen measurement.
    # Validate availability clocks first, then parse only records already known.
    q_seen = [_quote(q, ticker, session) for q in quotes
              if _int(q.get("available_ns"), "quote.available_ns") <= decision_ns]
    q_seen.sort(key=lambda q: (q["sip_ns"], q["id"]))
    # Same native ID must not refer to conflicting quote versions.
    dedup = {}
    for q in q_seen:
        prior = dedup.get(q["id"])
        if prior is not None and prior != q:
            raise ValueError("conflicting duplicate NBBO event identity")
        dedup[q["id"]] = q
    q_seen = sorted(dedup.values(), key=lambda q: (q["sip_ns"], q["id"]))
    q_times = [q["sip_ns"] for q in q_seen]
    norm_t = [_trade(t, ticker, session) for t in trades
              if _int(t.get("available_ns"), "trade.available_ns") <= decision_ns]
    # Resolve correction chains as a unit; keep exclusions scoped to this window
    # instead of counting unrelated same-session events.
    window_ids = {t["id"] for t in norm_t if start_ns <= t["sip_ns"] < end_ns}
    active, exclusions = _active_trades(
        [t for t in norm_t if t["id"] in window_ids], decision_ns)
    active = sorted((t for t in active if start_ns <= t["sip_ns"] < end_ns),
                    key=lambda t: (t["sip_ns"], t["id"]))
    policy_refs = sorted({t["eligibility_rules_ref"] for t in active})
    if len(policy_refs) > 1:
        raise ValueError("mixed trade-condition policies require separate measurement windows")
    buy = sell = unknown = Decimal(0)
    exact = Context(prec=_EXACT_PRECISION)
    counts = Counter()
    prints = []
    for trade in active:
        notional = exact.multiply(trade["price"], Decimal(trade["size"]))
        side = "UNKNOWN"
        quote_id = None
        age_ns = None
        if trade["venue_class"] != "LIT":
            reason = "OFF_EXCHANGE_OR_UNKNOWN_VENUE"
        else:
            q, reason = _prior_quote(q_seen, q_times, trade["sip_ns"],
                                     max_age_ns=max_quote_age_ns, require_exact_order=True)
            if (q is not None and evidence_mode != "FINAL_VINTAGE"
                    and q["available_ns"] > trade["available_ns"]):
                # A SIP-prior quote that arrived only after the print was not
                # available for contemporaneous pressure classification.
                # Later final-vintage research remains separately labeled.
                # Never fall back to an older quote as if the newer update
                # did not happen in the market.
                q = None
                reason = "QUOTE_NOT_AVAILABLE_AT_TRADE_RECEIPT"
            if q is not None:
                quote_id = q["id"]
                age_ns = trade["sip_ns"] - q["sip_ns"]
                if trade["price"] > q["ask"] or trade["price"] < q["bid"]:
                    reason = "OUTSIDE_NBBO"
                else:
                    mid = _midpoint(q)
                    if trade["price"] > mid:
                        side = "BUY_PROXY"
                        reason = None
                    elif trade["price"] < mid:
                        side = "SELL_PROXY"
                        reason = None
                    else:
                        reason = "MIDPOINT_AMBIGUOUS"
        if side == "BUY_PROXY":
            buy = exact.add(buy, notional)
        elif side == "SELL_PROXY":
            sell = exact.add(sell, notional)
        else:
            unknown = exact.add(unknown, notional)
            counts[reason] += 1
        prints.append({"trade_id": trade["id"], "revision": trade["revision"],
                       "side_proxy": side, "reason": reason, "quote_id": quote_id,
                       "quote_age_ns": age_ns, "venue_class": trade["venue_class"],
                       "source_receipt": trade["source_receipt"],
                       "quote_source_receipt": q["source_receipt"] if quote_id else None})
    start_q, start_reason = _prior_quote(q_seen, q_times, start_ns, max_age_ns=max_quote_age_ns)
    end_q, end_reason = _prior_quote(q_seen, q_times, end_ns, max_age_ns=max_quote_age_ns)
    response = None
    if start_q is not None and end_q is not None:
        start_mid = _midpoint(start_q)
        end_mid = _midpoint(end_q)
        response = _fmt(((end_mid / start_mid) - 1) * Decimal(10000))
    classified = exact.add(buy, sell)
    gross = exact.add(classified, unknown)
    return {
        "schema": SCHEMA, "authority": "RESEARCH_ONLY", "state": "MEASURED" if active else "NO_ELIGIBLE_PRINTS",
        "ticker": ticker, "session": session, "start_ns": start_ns, "end_ns": end_ns,
        "decision_ns": decision_ns, "watermark_ns": watermark_ns,
        "watermark_seen_ns": watermark_seen_ns, "watermark_receipt": watermark_receipt,
        "source_manifest": source_manifest, "evidence_mode": evidence_mode,
        "max_quote_age_ns": max_quote_age_ns, "condition_policy_refs": policy_refs,
        "n_active_prints": len(active), "n_excluded_revisions_or_conditions": dict(sorted(exclusions.items())),
        "n_unclassified": dict(sorted(counts.items())),
        "buy_proxy_notional_usd": _fmt(buy), "sell_proxy_notional_usd": _fmt(sell),
        "unknown_notional_usd": _fmt(unknown), "gross_active_notional_usd": _fmt(gross),
        "classified_notional_coverage": _fmt(classified / gross) if gross else None,
        "pressure_balance": _fmt(exact.subtract(buy, sell) / classified) if classified else None,
        "midpoint_response_bps": response,
        "response_null_reason": ({"start": start_reason, "end": end_reason} if response is None else None),
        "bid_size_recovery": _recovery(q_seen, start_q, start_ns, end_ns, "bid", max_age_ns=max_quote_age_ns),
        "ask_size_recovery": _recovery(q_seen, start_q, start_ns, end_ns, "ask", max_age_ns=max_quote_age_ns),
        "print_diagnostics_private_only": prints,
        "interpretation": "MEASURED_TRADE_PRESSURE_AND_BEST_QUOTE_PROXY_NOT_ACTOR_INTENT",
        "absorption_signal": None,  # Requires a separate outcome-blind calibration owner.
    }
