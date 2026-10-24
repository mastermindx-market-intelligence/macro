"""Pure Plan-to-incumbent-payoff bridge; no acquisition, admission or persistence.

Inputs are retained data supplied by the authorized consumer. Structural validation
does not authenticate a provider, an owner-authored fixing binding, or historical
possession. Only the existing ordinary SPY/QQQ reference interpretation is supported.
The research horizon is not an expiry/fixing substitute. Quote data is deliberately
not an entry source: entry is the explicit options_plan_draft.v1 assumption shape.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
import re
import json
from decimal import Decimal
from zoneinfo import ZoneInfo

from engine.options_nbbo_cohort import validate_contract
from engine.options_payoff import Leg, expiry_payoff, structure_from_legs
from lib.options_source_receipts import massive_reference_terms, ordinary_etf_terms

SCHEMA = "options.plan_expiry_preparation/v1"


def prepare_plan_draft_expiry(draft, contexts, spots, *, known_by):
    """Join validated options_plan_draft.v1 pins to ordered exact source contexts.

    This adapter does not replace the durable Plan owner's full draft validator.
    It checks the mathematical/source join and preserves original snapshot clocks;
    the original Plan remains that owner's unchanged persistence payload.
    """
    def invalid(code):
        result = prepare_expiry_payoff([], spots, known_by=known_by)
        result["reasons"] = [dict(code=code, leg=None)]
        return result

    try:
        if len(json.dumps(draft, allow_nan=False).encode()) > 64 * 1024:
            return invalid("PLAN_DRAFT_INVALID")
        if (not isinstance(draft, dict) or draft.get("schema") != "options_plan_draft.v1"
                or not isinstance(draft.get("legs"), list) or not 1 <= len(draft["legs"]) <= 4
                or not isinstance(contexts, (list, tuple)) or len(contexts) != len(draft["legs"])):
            return invalid("PLAN_DRAFT_INVALID")
        legs, pins = [], []
        for source_leg, context in zip(draft["legs"], contexts):
            contract = validate_contract(context["contract"])
            snapshot = source_leg["snapshot"]; identity = snapshot["identity"]
            if (identity["root"] != contract["root"] or identity["exp"] != contract["expiration"]
                    or identity["right"] != {"call": "C", "put": "P"}[contract["right"]]
                    or type(identity["strike"]) not in (int, float)
                    or Decimal(str(identity["strike"])) != Decimal(contract["strike"])):
                return invalid("PIN_CONTEXT_IDENTITY_MISMATCH")
            pin_terms = identity.get("terms", {})
            if (identity.get("adjustedRootHint") is True or not isinstance(pin_terms, dict)
                    or any(pin_terms.get(k) is not None and pin_terms[k] != v for k, v in dict(
                        multiplier=100, deliverable="100_underlying_shares", settlement="physical",
                        exercise_style="american").items())):
                return invalid("PIN_TERMS_CONFLICT")
            legs.append(dict(contract=contract, assumptions=source_leg["assumptions"],
                reference_observation=context.get("reference_observation"),
                settlement_context=context.get("settlement_context")))
            pins.append({k: deepcopy(snapshot.get(k)) for k in (
                "pinKey", "session", "asofRaw", "sourceStale", "schema")})
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return invalid("PLAN_DRAFT_INVALID")
    result = prepare_expiry_payoff(legs, spots, known_by=known_by)
    result["source_pins"] = pins
    return result


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp absent")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp offset absent")
    return parsed


def _number(value, maximum):
    return (type(value) in (int, float) and 0 <= value <= maximum
            and math.isfinite(value))


def _reference(value):
    return (isinstance(value, str) and len(value) <= 2048
            and re.fullmatch(r"https://[^\s#]+#sha256=[a-f0-9]{64}", value) is not None)


def prepare_expiry_payoff(legs, spots, *, known_by):
    """Return all-leg expiry math or a typed unpriced result, never partial math.

    Each leg has exact ``contract`` (incumbent OSI schema), ``assumptions``
    (side buy/sell, positive integer quantity, explicit user_assumption entry),
    ``reference_observation`` (incumbent retained Massive receipt), and
    ``settlement_context``. The latter is a caller-owned evidence seam, not a
    receipt issuer: exact contract, economic_expiry_at, available_at, fixing_ref
    (content-bound source), and fixing_basis=official_close. Actual qualification
    of that source/fixing remains the consumer's obligation before product use.
    """
    out = dict(schema=SCHEMA, status="UNPRICED", reasons=[], curve=None,
               contexts=[], assumptions=dict(entry_basis="user_assumption_not_fill",
                   calculation="expiry_intrinsic_only", currency="USD",
                   fees="excluded_unknown", early_exercise="not_modeled",
                   current_quote_required=False, source_authentication="not_established_by_this_function"))

    def refuse(code, index=None):
        out["reasons"].append(dict(code=code, leg=index))
        return out

    try:
        cutoff = _instant(known_by)
    except (ValueError, TypeError, OverflowError):
        return refuse("KNOWN_BY_UNKNOWN")
    if not isinstance(legs, (list, tuple)) or not 1 <= len(legs) <= 4:
        return refuse("LEGS_INVALID")
    if (not isinstance(spots, (list, tuple)) or not 1 <= len(spots) <= 1001
            or any(not _number(s, 1e9) for s in spots)):
        return refuse("SPOTS_INVALID")
    prepared, roots, expiries, horizons, fixing_bases = [], set(), set(), set(), set()
    for index, supplied in enumerate(legs):
        if not isinstance(supplied, dict):
            refuse("LEG_INVALID", index)
            continue
        try:
            contract = validate_contract(supplied.get("contract"))
        except (ValueError, TypeError, OverflowError):
            refuse("IDENTITY_INVALID", index)
            continue
        root, expiration = contract["root"], contract["expiration"]
        roots.add(root); expiries.add(expiration)
        assumptions = supplied.get("assumptions")
        if (not isinstance(assumptions, dict) or set(assumptions) != {"side", "quantity", "entry"}
                or assumptions["side"] not in ("buy", "sell")
                or type(assumptions["quantity"]) is not int
                or not 1 <= assumptions["quantity"] <= 1_000_000):
            refuse("POSITION_ASSUMPTION_INVALID", index)
            continue
        entry = assumptions["entry"]
        if entry is None:
            refuse("ENTRY_ASSUMPTION_MISSING", index)
            continue
        if (not isinstance(entry, dict) or set(entry) != {"kind", "premium_per_unit", "currency"}
                or entry["kind"] != "user_assumption" or entry["currency"] != "USD"
                or not _number(entry["premium_per_unit"], 1e9)):
            refuse("ENTRY_ASSUMPTION_INVALID", index)
            continue
        try:
            term = ordinary_etf_terms(massive_reference_terms(
                supplied.get("reference_observation"), root), root=root)
            expected = (root, expiration, contract["strike_millis"], contract["right"])
            actual = (term["root"], term["expiration"], round(term["strike"] * 1000),
                      {"C": "call", "P": "put"}[term["right"]])
            if (expected != actual or term.get("multiplier") != 100
                    or term.get("deliverable") != "100_underlying_shares"
                    or term.get("currency") != "USD"
                    or term.get("cfi", "O" + term["right"] + "ASPS") != "O" + term["right"] + "ASPS"):
                raise ValueError("unsupported terms")
            if _instant(term["available_at"]) > cutoff:
                raise ValueError("terms not known by cutoff")
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            refuse("TERMS_UNQUALIFIED", index)
            continue
        binding = supplied.get("settlement_context")
        try:
            if (not isinstance(binding, dict) or set(binding) != {
                    "contract", "economic_expiry_at", "available_at", "fixing_ref", "fixing_basis"}
                    or validate_contract(binding["contract"]) != contract
                    or binding["fixing_basis"] != "official_close"
                    or not _reference(binding["fixing_ref"])):
                raise ValueError("fixing binding missing or incompatible")
            horizon = _instant(binding["economic_expiry_at"])
            if (horizon.astimezone(ZoneInfo("America/New_York")).date().isoformat() != expiration
                    or _instant(binding["available_at"]) > cutoff):
                raise ValueError("fixing clock unqualified")
        except (ValueError, TypeError, KeyError, OverflowError):
            refuse("SETTLEMENT_FIXING_UNQUALIFIED", index)
            continue
        horizons.add(horizon); fixing_bases.add(binding["fixing_basis"])
        out["contexts"].append(dict(contract=deepcopy(contract), terms=term,
                                    settlement_context=deepcopy(binding), assumptions=deepcopy(assumptions)))
        prepared.append(Leg(right="C" if contract["right"] == "call" else "P",
            strike=float(contract["strike"]), expiration=expiration,
            qty=assumptions["quantity"] * (1 if assumptions["side"] == "buy" else -1),
            entry_price=float(entry["premium_per_unit"]), multiplier=term["multiplier"], iv=None))
    if len(roots) != 1:
        refuse("MIXED_UNDERLYING")
    if len(expiries) != 1:
        refuse("MIXED_EXPIRY")
    if not out["reasons"] and (len(horizons) != 1 or len(fixing_bases) != 1):
        refuse("INCOMPATIBLE_SETTLEMENT_HORIZON")
    if out["reasons"]:
        return out
    structure = structure_from_legs(prepared, root=next(iter(roots)), asof_date=cutoff.date().isoformat())
    calculated = expiry_payoff(structure, spots)
    # Incumbent AssumptionBlock includes BS/rate/IV metadata for other functions.
    # Expiry intrinsic uses none of it; expose only this calculation's semantics.
    out["curve"] = dict(spots=list(calculated.spots), pnl=list(calculated.pnl),
        cost=calculated.cost, max_gain=calculated.max_gain, max_loss=calculated.max_loss,
        breakevens=list(calculated.breakevens))
    out["status"] = "PREPARED_EXPIRY_PAYOFF"
    out["assumptions"]["economic_expiry_at"] = next(iter(horizons)).isoformat()
    out["assumptions"]["engine"] = "engine.options_payoff.expiry_payoff"
    return out
