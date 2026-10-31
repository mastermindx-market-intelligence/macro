"""Pure Plan-to-incumbent-payoff bridge; no acquisition, admission or persistence.

Inputs are retained data supplied by the authorized consumer. Structural validation
does not authenticate a provider or historical possession. Only the existing ordinary SPY/QQQ reference interpretation is supported.
The research horizon does not change the contractual expiry date. Quote data is deliberately
not an entry source: entry is the explicit options_plan_draft.v1 assumption shape.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
import json
from decimal import Decimal
from zoneinfo import ZoneInfo

from engine.options_nbbo_cohort import validate_contract
from engine.options_payoff import Leg, expiry_payoff, structure_from_legs
from lib.options_source_receipts import massive_reference_terms, ordinary_etf_terms

SCHEMA = "options.plan_expiry_preparation/v1"


def prepare_plan_draft_expiry(draft, contexts, spots, *, known_by, payoff_basis):
    """Join validated options_plan_draft.v1 pins to ordered exact source contexts.

    This adapter does not replace the durable Plan owner's full draft validator.
    It checks the mathematical/source join and preserves original snapshot clocks;
    the original Plan remains that owner's unchanged persistence payload.
    """
    def invalid(code):
        result = prepare_expiry_payoff([], spots, known_by=known_by, payoff_basis=payoff_basis)
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
            if not isinstance(context, dict) or set(context) != {"contract", "reference_observation"}:
                return invalid("CONTEXT_BASIS_UNSUPPORTED")
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
                reference_observation=context.get("reference_observation")))
            pins.append({k: deepcopy(snapshot.get(k)) for k in (
                "pinKey", "session", "asofRaw", "sourceStale", "schema")})
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return invalid("PLAN_DRAFT_INVALID")
    result = prepare_expiry_payoff(legs, spots, known_by=known_by, payoff_basis=payoff_basis)
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


def _reference_term(observation, contract):
    """Select one exact row without rewriting genuine list capture provenance."""
    root = contract["root"]
    if isinstance(observation, dict) and observation.get("path") == "/v3/reference/options/contracts":
        rows = observation.get("contracts")
        if (not isinstance(rows, list) or not 1 <= len(rows) <= 100
                or any(not isinstance(row, dict) for row in rows)):
            raise ValueError("bounded reference rows absent or invalid")
        ticker = "O:" + contract["occ_symbol"].replace(" ", "")
        selected = [row for row in rows if row.get("ticker") == ticker]
        if len(selected) != 1:
            raise ValueError("exact reference row absent or ambiguous")
        return massive_reference_terms(observation, root, contract=selected[0])
    return massive_reference_terms(observation, root)


def prepare_expiry_payoff(legs, spots, *, known_by, payoff_basis):
    """Return all-leg expiry math or a typed unpriced result, never partial math.

    Each leg has exact ``contract`` (incumbent OSI schema), ``assumptions``
    (side buy/sell, positive integer quantity, explicit user_assumption entry),
    ``reference_observation`` (incumbent retained Massive receipt).
    Explicit payoff_basis is exactly {kind: hold_to_expiry_intrinsic,
    expiration: YYYY-MM-DD}. Spots are hypothetical underlying prices at expiry.
    This model excludes early exercise, assignment and fees; it does not represent
    actual exercise, settlement, fixing, a fill or a realized outcome.
    """
    out = dict(schema=SCHEMA, status="UNPRICED", reasons=[], curve=None,
               known_by=known_by if isinstance(known_by, str) else None,
               contract_expirations=[], temporal_context=None,
               contexts=[], assumptions=dict(entry_basis="user_assumption_not_fill",
                   calculation="expiry_intrinsic_only", currency="USD",
                   fees="excluded_unknown", early_exercise="excluded", assignment="excluded",
                   underlying_price="hypothetical_at_expiry", outcome="conditional_not_realized",
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
    if (not isinstance(payoff_basis, dict) or set(payoff_basis) != {"kind", "expiration"}
            or payoff_basis["kind"] != "hold_to_expiry_intrinsic"):
        return refuse("PAYOFF_BASIS_UNSUPPORTED")
    prepared, roots, expiries = [], set(), set()
    for index, supplied in enumerate(legs):
        if not isinstance(supplied, dict):
            refuse("LEG_INVALID", index)
            continue
        if set(supplied) != {"contract", "assumptions", "reference_observation"}:
            refuse("CONTEXT_BASIS_UNSUPPORTED", index)
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
            term = ordinary_etf_terms(_reference_term(
                supplied.get("reference_observation"), contract), root=root)
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
        out["contexts"].append(dict(contract=deepcopy(contract), terms=term,
                                    assumptions=deepcopy(assumptions)))
        prepared.append(Leg(right="C" if contract["right"] == "call" else "P",
            strike=float(contract["strike"]), expiration=expiration,
            qty=assumptions["quantity"] * (1 if assumptions["side"] == "buy" else -1),
            entry_price=float(entry["premium_per_unit"]), multiplier=term["multiplier"], iv=None))
    if len(roots) != 1:
        refuse("MIXED_UNDERLYING")
    if len(expiries) != 1:
        refuse("MIXED_EXPIRY")
    out["contract_expirations"] = sorted(expiries)
    if len(expiries) == 1:
        expiration = next(iter(expiries))
        known_date = cutoff.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        relation = ("EXPIRY_DATE_BEFORE_KNOWN_BY_DATE" if expiration < known_date else
                    "EXPIRY_DATE_AFTER_KNOWN_BY_DATE" if expiration > known_date else
                    "SAME_DATE_NO_EXPIRY_INSTANT_INFERRED")
        out["temporal_context"] = dict(known_by_date_new_york=known_date,
            contract_expiration=expiration, relation=relation,
            historical_first_availability_established=False)
    if not out["reasons"] and payoff_basis["expiration"] != next(iter(expiries)):
        refuse("PAYOFF_EXPIRY_MISMATCH")
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
    out["assumptions"]["payoff_basis"] = deepcopy(payoff_basis)
    out["assumptions"]["engine"] = "engine.options_payoff.expiry_payoff"
    return out
