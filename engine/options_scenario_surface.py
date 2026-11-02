"""Conditional Greek surfaces and supplied-inventory hedge-target scenarios.

Additive Options Workbench R2 model. This is not observed strike x clock history
and not a predicted price path. It reuses engine.intraday_greeks.bs_greeks_vec,
so it creates no second Greek or pricing kernel.

The original surface's V1 assumptions are explicit: fixed input OI, sticky-strike
input IV, deterministic time roll-forward and incumbent +call/-put dealer signs.
The additive hedge-target entry point instead requires supplied signed positions
and explicit SPX/SPXW fixing identities; it never observes dealer ownership.
"""
from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
import math
from numbers import Real
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np

from engine.intraday_greeks import (
    CONTRACT_MULTIPLIER,
    DEFAULT_Q,
    DEFAULT_R,
    PCT_MOVE,
    bs_greeks_vec,
    implied_vol_vec,
)

SCHEMA = "options.scenario_surface/v1"
PRODUCT_KIND = "conditional_price_time_scenario"
VOL_MAP_STICKY_STRIKE = "sticky_strike"
IV_SOURCE_PROVIDED = "provided_iv"
IV_SOURCE_MID_SOLVE = "solve_from_mid"
MINUTES_PER_YEAR = 365.0 * 24.0 * 60.0
ET = ZoneInfo("America/New_York")
INVENTORY_FLOW_METHOD = "supplied_prior_minus_participation_times_signed_flow/v1"
INVENTORY_ADJUSTED_METHOD = "supplied_prior_minus_participation_times_signed_flow_plus_adjustments/v1"


def _scenario_number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return result


def _scenario_clock(value: Any, name: str) -> datetime:
    try:
        return datetime.fromisoformat(_require_aware_iso(value).replace("Z", "+00:00")).astimezone(ZoneInfo("UTC"))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be a known timezone-aware timestamp") from exc


def _scenario_ref(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _expiry_cohort(expiry: str, clock: datetime) -> str:
    days = (date.fromisoformat(expiry) - clock.astimezone(ET).date()).days
    return "past_expiry" if days < 0 else "0DTE" if days == 0 else "1-7D" if days <= 7 else "8+D"


def build_inventory_scenario(
    prior_positions: dict[str, float],
    signed_flow: dict[str, float],
    *,
    dealer_fraction: float,
    scenario_id: str,
    nontrade_adjustments: dict[str, float] | None = None,
) -> dict:
    """Condition a supplied prior on an already-qualified signed Flow aggregate.

    Positive Flow means customer-initiated buying under the caller's *scenario*;
    dealer inventory changes by minus participation times that flow. This function
    neither signs trades nor reconstructs an event ledger. Callers must supply the
    same explicit contract universe on both sides, including measured zeros; an
    absent or unknown flow is never a zero. Corrections/packages and source clocks
    remain with the existing Flow owner and the consuming snapshot receipt.
    Supplied nontrade adjustments have the same explicit universe; omission
    means a disclosed zero-adjustment scenario assumption, not measured absence.
    """
    scenario_id = _scenario_ref(scenario_id, "scenario_id")
    fraction = _scenario_number(dealer_fraction, "dealer_fraction")
    if not 0 <= fraction <= 1:
        raise ValueError("dealer_fraction must be in [0, 1]")
    if not isinstance(prior_positions, dict) or not isinstance(signed_flow, dict):
        raise ValueError("inventory and Flow must be contract-keyed mappings")
    if not prior_positions or set(prior_positions) != set(signed_flow):
        raise ValueError("prior and Flow must have the same nonempty explicit contract universe")
    supplied_adjustments = nontrade_adjustments is not None
    if supplied_adjustments and (not isinstance(nontrade_adjustments, dict) or
                                set(nontrade_adjustments) != set(prior_positions)):
        raise ValueError("nontrade adjustments must have the same explicit contract universe")
    starting, ending, flow, trade, adjustments = {}, {}, {}, {}, {}
    for key in sorted(prior_positions):
        _scenario_ref(key, "contract_id")
        starting[key] = _scenario_number(prior_positions[key], "prior position")
        flow[key] = _scenario_number(signed_flow[key], "signed Flow")
        trade[key] = -fraction * flow[key]
        adjustments[key] = _scenario_number(nontrade_adjustments[key], "nontrade adjustment") if supplied_adjustments else 0.
        try:
            ending[key] = _scenario_number(math.fsum((starting[key], trade[key], adjustments[key])), "ending position")
        except OverflowError as exc:
            raise ValueError("ending position must be finite") from exc
    return {
        "scenario_id": scenario_id, "evidence_class": "SCENARIO",
        "starting": starting, "ending": ending,
        "method": INVENTORY_ADJUSTED_METHOD if supplied_adjustments else INVENTORY_FLOW_METHOD,
        "dealer_fraction": fraction, "signed_flow": flow,
        "trade_increment": trade, "nontrade_adjustments": adjustments,
        "nontrade_assumption": "supplied" if supplied_adjustments else "assumed_zero",
    }


def build_hedge_target_change(
    contracts: list[dict], *, observed_at: str, as_of: str, spot: float,
    target_spot: float, target_at: str, inventory: dict,
    expected_contract_ids: list[str], universe_ref: str, source_receipt: dict,
    expiry_scope: list[str] | None = None, iv_shift: float = 0.0,
    target_iv_by_contract: dict[str, float] | None = None,
    r: float = DEFAULT_R, q: float = DEFAULT_Q,
    max_source_age_seconds: float = 60.0,
) -> dict:
    """Exact conditional SPX-risk hedge targets within a supplied SPX/SPXW book.

    Reuses the incumbent pricing kernel. Whole-book numbers require every member
    of the *supplied* universe; that is never a claim of national-market coverage.
    Explicit fixing times come from qualified contract reference data, not dates
    or a one-hour vendor TTE floor. At/crossing fixing is unavailable pending a
    separate settlement/unwind model. This pure function publishes nothing.
    """
    observed = _scenario_clock(observed_at, "observed_at")
    cutoff = _scenario_clock(as_of, "as_of")
    target = _scenario_clock(target_at, "target_at")
    if observed > cutoff or target < observed:
        raise ValueError("anchor must be available by as_of and target cannot precede anchor")
    s0 = _scenario_number(spot, "spot", positive=True)
    s1 = _scenario_number(target_spot, "target_spot", positive=True)
    shift = _scenario_number(iv_shift, "iv_shift")
    r = _scenario_number(r, "r")
    q = _scenario_number(q, "q")
    max_age = _scenario_number(max_source_age_seconds, "max_source_age_seconds", positive=True)
    universe_ref = _scenario_ref(universe_ref, "universe_ref")
    if not isinstance(source_receipt, dict):
        raise ValueError("source_receipt must be a mapping")
    receipt = {"source_ref": _scenario_ref(source_receipt.get("source_ref"), "source_ref")}
    for key in ("source_revision", "contract_reference_revision"):
        raw_revision = source_receipt.get(key)
        receipt[key] = None if raw_revision is None else _scenario_ref(raw_revision, key)
    clocks = [_scenario_clock(source_receipt.get(k), k) for k in
              ("source_observed_at", "received_at", "consumer_available_at")]
    source, received, available = clocks
    if not source <= received <= available <= cutoff or source > observed:
        raise ValueError("source receipt violates causal availability ordering")
    for key, clock in zip(("source_observed_at", "received_at", "consumer_available_at"), clocks):
        receipt[key] = clock.isoformat()
    if not isinstance(expected_contract_ids, list) or not expected_contract_ids:
        raise ValueError("expected_contract_ids must name a nonempty source universe")
    expected = [_scenario_ref(x, "expected contract_id") for x in expected_contract_ids]
    expected_set = set(expected)
    if len(expected_set) != len(expected):
        raise ValueError("duplicate expected contract_id")
    if target_iv_by_contract is not None:
        if not isinstance(target_iv_by_contract, dict) or set(target_iv_by_contract) != expected_set:
            raise ValueError("target IV must name the entire explicit contract universe")
        if shift != 0:
            raise ValueError("target_iv_by_contract and nonzero iv_shift are mutually exclusive")
    if not isinstance(inventory, dict) or inventory.get("evidence_class") != "SCENARIO":
        raise ValueError("inventory must explicitly be a SCENARIO, not observed dealer ownership")
    inv_id = _scenario_ref(inventory.get("scenario_id"), "inventory scenario_id")
    start, end = inventory.get("starting"), inventory.get("ending")
    if not isinstance(start, dict) or not isinstance(end, dict):
        raise ValueError("starting and ending positions must be contract-keyed mappings")
    if set(start) - expected_set or set(end) - expected_set:
        raise ValueError("inventory contains contracts outside supplied universe")
    inv_assumptions = {"method": "supplied_signed_positions"}
    if "method" in inventory:
        if inventory["method"] not in {INVENTORY_FLOW_METHOD, INVENTORY_ADJUSTED_METHOD}:
            raise ValueError("unsupported inventory method")
        adjusted = inventory["method"] == INVENTORY_ADJUSTED_METHOD
        if adjusted and not isinstance(inventory.get("nontrade_adjustments"), dict):
            raise ValueError("adjusted inventory requires explicit nontrade adjustments")
        conditioned = build_inventory_scenario(
            start, inventory.get("signed_flow"),
            dealer_fraction=inventory.get("dealer_fraction"), scenario_id=inv_id,
            nontrade_adjustments=inventory.get("nontrade_adjustments") if adjusted else None,
        )
        if conditioned["ending"] != end or any(
            key in inventory and inventory[key] != conditioned[key]
            for key in ("trade_increment", "nontrade_adjustments", "nontrade_assumption")
        ):
            raise ValueError("conditioned inventory does not match its supplied Flow assumptions")
        inv_assumptions = {key: conditioned[key] for key in (
            "method", "dealer_fraction", "signed_flow", "trade_increment",
            "nontrade_adjustments", "nontrade_assumption",
        )}
    scope = None
    if expiry_scope is not None:
        if not isinstance(expiry_scope, list) or not expiry_scope:
            raise ValueError("expiry_scope must be a nonempty list or null")
        scope = sorted({date.fromisoformat(x).isoformat() for x in expiry_scope})
    if not isinstance(contracts, list):
        raise ValueError("contracts must be a list")
    rows, seen, economic = [], set(), set()
    for raw in contracts:
        if not isinstance(raw, dict):
            raise ValueError("contract must be a mapping")
        key = _scenario_ref(raw.get("contract_id"), "contract_id")
        if key in seen or key not in expected_set:
            raise ValueError("duplicate or out-of-universe contract_id")
        seen.add(key)
        option_root = raw.get("option_root")
        settlement = raw.get("settlement")
        if (option_root, settlement) not in {("SPX", "AM"), ("SPXW", "PM")}:
            raise ValueError("requires explicit standard SPX/AM or SPXW/PM contract identity")
        expiry = date.fromisoformat(raw.get("expiry", "")).isoformat()
        fixing = _scenario_clock(raw.get("fixing_at"), "fixing_at")
        if fixing.astimezone(ET).date().isoformat() != expiry:
            raise ValueError("fixing date must match the contract expiry in New York")
        if raw.get("right") not in {"C", "P"}:
            raise ValueError("right must be exactly C or P")
        strike = _scenario_number(raw.get("strike"), "strike", positive=True)
        mult = _scenario_number(raw.get("multiplier"), "multiplier", positive=True)
        if mult != 100:
            raise ValueError("nonstandard deliverables require a separately qualified risk transform")
        identity = (option_root, expiry, raw["right"], strike)
        if identity in economic:
            raise ValueError("duplicate economic contract under different IDs")
        economic.add(identity)
        rows.append({"contract_id": key, "option_root": option_root, "expiry": expiry,
                     "right": raw["right"], "strike": strike, "multiplier": mult,
                     "settlement": settlement, "fixing_at": fixing.isoformat(),
                     "anchor_cohort": _expiry_cohort(expiry, observed),
                     "endpoint_cohort": _expiry_cohort(expiry, target),
                     "iv": raw.get("iv"), "n0": start.get(key), "n1": end.get(key)})
    rows.sort(key=lambda row: row["contract_id"])
    selected = [row for row in rows if scope is None or row["expiry"] in scope]
    selected_ids = {row["contract_id"] for row in selected}
    reasons = []
    if seen != expected_set:
        reasons.append("missing_contracts")
    if not selected or (scope is not None and set(scope) - {row["expiry"] for row in selected}):
        reasons.append("empty_expiry_scope")
    if (cutoff - source).total_seconds() > max_age:
        reasons.append("stale_source")
    for row in rows:
        # Validate even excluded members: malformed source data must not vanish
        # from content identity or be promoted to a zero position.
        for key in ("iv", "n0", "n1"):
            try:
                row[key] = _scenario_number(row[key], key, positive=(key == "iv"))
            except ValueError:
                row[key] = None
                if row["contract_id"] in selected_ids:
                    reasons.append("unknown_inventory" if key != "iv" else "invalid_iv")
        target_iv = (target_iv_by_contract[row["contract_id"]] if target_iv_by_contract is not None
                     else row["iv"] + shift if row["iv"] is not None else None)
        try:
            row["target_iv"] = _scenario_number(target_iv, "target IV", positive=True)
        except ValueError:
            row["target_iv"] = None
            if row["contract_id"] in selected_ids:
                reasons.append("invalid_target_iv")
        if row["contract_id"] in selected_ids:
            fixing = datetime.fromisoformat(row["fixing_at"])
            if fixing <= target:
                reasons.append("fixing_boundary")
    out = {
        "schema": "options.hedge_target_change/v1", "evidence_class": "SCENARIO",
        "root": "SPX", "observed_at": observed.isoformat(), "as_of": cutoff.isoformat(),
        "target_at": target.isoformat(), "spot": s0, "target_spot": s1,
        "source_receipt": receipt, "source_age_seconds": (cutoff - source).total_seconds(),
        "inventory_scenario_id": inv_id, "inventory_assumptions": inv_assumptions, "contracts": rows,
        "coverage": {"scope": "supplied_universe", "universe_ref": universe_ref,
                     "expected_contract_ids": sorted(expected), "received": len(rows),
                     "selected": len(selected), "expiry_scope": scope,
                     "missing_contract_ids": sorted(expected_set - seen)},
        "assumptions": {"pricing": "engine.intraday_greeks.bs_greeks_vec",
                        "pricing_convention": "European_constant_carry_pricing_delta",
                        "vol_map": "supplied_contract_endpoint_iv" if target_iv_by_contract is not None else "sticky_strike_parallel_shift",
                        "iv_shift": shift,
                        "cohort_convention": "anchor_calendar_days_America/New_York",
                        "r": r, "q": q, "year_days": 365,
                        "max_source_age_seconds": max_age},
        "units": {"target_change": "SPX_index_equivalent_units",
                  "reference_notional_usd": "target_SPX_times_change_in_hedge_units"},
        "authority": {"calibrated_probability": False, "actual_dealer_inventory": False,
                      "executed_flow": False, "trading": False, "can_publish": False,
                      "ranking": False, "portfolio": False, "sizing": False, "auto_exit": False},
        "warnings": ["Supplied inventory scenario, not observed dealer positions.",
                     "SPX risk units are not executable shares; reference notional is not cash or ES contracts.",
                     "Source receipt is caller supplied; this calculation grants no data or distribution rights.",
                     "Endpoint target change is not path turnover, impact or a price forecast."],
        "hedge": None, "attribution": None, "by_expiry": [], "by_cohort": [],
        "cohort_migrations": [{"contract_id": row["contract_id"], "from": row["anchor_cohort"], "to": row["endpoint_cohort"]}
                              for row in selected if row["anchor_cohort"] != row["endpoint_cohort"]],
    }
    if not reasons:
        strike = np.array([row["strike"] for row in selected])
        iv = np.array([row["iv"] for row in selected])
        endpoint_iv = np.array([row["target_iv"] for row in selected])
        n0 = np.array([row["n0"] for row in selected])
        n1 = np.array([row["n1"] for row in selected])
        mult = np.array([row["multiplier"] for row in selected])
        fixing = [datetime.fromisoformat(row["fixing_at"]) for row in selected]
        t0 = np.array([(x - observed).total_seconds() / (365 * 86400) for x in fixing])
        t1 = np.array([(x - target).total_seconds() / (365 * 86400) for x in fixing])
        calls = np.array([row["right"] == "C" for row in selected])
        with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
            d0, gamma, vanna, charm = bs_greeks_vec(s0, strike, t0, iv, calls, r=r, q=q)
            d1 = bs_greeks_vec(s1, strike, t1, endpoint_iv, calls, r=r, q=q)[0]
            b0, b1 = -n0 * mult * d0, -n1 * mult * d1
            change = b1 - b0
            repricing = -mult * (n0 / 2 + n1 / 2) * (d1 - d0)
            position = -mult * (n1 - n0) * (d0 / 2 + d1 / 2)
            linear = -mult * (n0 * (gamma * (s1 - s0) + vanna * (endpoint_iv - iv) +
                      charm * ((target - observed).total_seconds() / (365 * 86400))) + (n1 - n0) * d0)
        vectors = [d0, d1, b0, b1, change, repricing, position, linear]
        if not all(np.isfinite(x).all() for x in vectors):
            reasons.append("nonfinite_repricing")
        else:
            try:
                total = math.fsum(change)
                gross = math.fsum(abs(change))
                hedge = {"anchor_target": math.fsum(b0), "endpoint_target": math.fsum(b1),
                         "target_change": total, "reference_notional_usd": s1 * total,
                         "gross_contract_target_changes": gross,
                         "cancellation_ratio": abs(total) / gross if gross else None}
                attribution = {"method": "symmetric_inventory_repricing",
                               "repricing": math.fsum(repricing), "inventory": math.fsum(position),
                               "linear_approximation": math.fsum(linear),
                               "linear_residual": total - math.fsum(linear),
                               "identity_residual": total - math.fsum(repricing) - math.fsum(position)}
                if not all(v is None or math.isfinite(v) for v in hedge.values()):
                    raise OverflowError
                if not all(math.isfinite(v) for k, v in attribution.items() if k != "method"):
                    raise OverflowError
                groups = sorted({(x["option_root"], x["expiry"], x["fixing_at"]) for x in selected})
                by_expiry = [{"option_root": root, "expiry": expiry, "fixing_at": fixing_at,
                              "target_change": math.fsum(change[i] for i, row in enumerate(selected)
                                  if (row["option_root"], row["expiry"], row["fixing_at"]) == (root, expiry, fixing_at))}
                             for root, expiry, fixing_at in groups]
                by_cohort = []
                for cohort in ("0DTE", "1-7D", "8+D"):
                    members = [i for i, row in enumerate(selected) if row["anchor_cohort"] == cohort]
                    by_cohort.append({"cohort": cohort, "contracts": len(members),
                                      "anchor_target": math.fsum(b0[i] for i in members),
                                      "endpoint_target": math.fsum(b1[i] for i in members),
                                      "target_change": math.fsum(change[i] for i in members)})
                out.update(hedge=hedge, attribution=attribution, by_expiry=by_expiry, by_cohort=by_cohort)
            except (OverflowError, ValueError):
                reasons.append("nonfinite_repricing")
    out["unavailable_reasons"] = sorted(set(reasons))
    out["status"] = "unavailable" if reasons else "complete_for_supplied_universe"
    encoded = json.dumps(out, sort_keys=True, separators=(",", ":"), allow_nan=False)
    out["content_id"] = "hedge-target:" + sha256(encoded.encode()).hexdigest()
    return out


def _finite_positive(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) and out > 0 else None


def _finite_number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _sum_or_none(values: np.ndarray) -> float | None:
    with np.errstate(over="ignore", invalid="ignore"):
        total = float(np.sum(values))
    return total if np.isfinite(total) else None


def _source_clock_bounds(
    contracts: list[dict],
    field: str,
    *,
    observed_dt: datetime,
) -> tuple[str | None, str | None]:
    """Fail a source-clock envelope closed when any contributing member is unknown.

    This mirrors the incumbent live-flow provenance rule: known-only min/max bounds are
    dishonest for a mixed known/unknown contract set. A known source instant after the
    market observation is an impossible PIT state and is rejected instead of backdated.
    """
    if not contracts:
        return None, None
    instants: list[datetime] = []
    has_unknown = False
    observed_utc = observed_dt.astimezone(ZoneInfo("UTC"))
    for contract in contracts:
        raw = contract.get(field)
        if not isinstance(raw, str) or not raw.strip():
            has_unknown = True
            continue
        try:
            dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            has_unknown = True
            continue
        if dt.tzinfo is None or dt.utcoffset() is None:
            has_unknown = True
            continue
        dt = dt.astimezone(ZoneInfo("UTC"))
        if dt > observed_utc:
            raise ValueError(f"{field} cannot be after observed_at")
        instants.append(dt)
    # Unknown bounds do not excuse a future timestamp in another contributor.
    if has_unknown:
        return None, None
    instants.sort()
    return (
        instants[0].isoformat().replace("+00:00", "Z"),
        instants[-1].isoformat().replace("+00:00", "Z"),
    )


def _require_aware_iso(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a non-empty timezone-aware ISO timestamp")
    raw = value.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be a timezone-aware ISO timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    return raw


def _price_grid(values: Iterable[Any]) -> list[float]:
    out = sorted({x for v in values if (x := _finite_positive(v)) is not None})
    if len(out) < 2:
        raise ValueError("price_grid must contain at least two distinct positive prices")
    return out


def _horizons(values: Iterable[Any]) -> list[int]:
    out: set[int] = set()
    for value in values:
        if isinstance(value, bool):
            raise ValueError("horizons_minutes must contain non-negative integers")
        try:
            x = int(value)
            same = float(value) == float(x)
        except (TypeError, ValueError) as exc:
            raise ValueError("horizons_minutes must contain non-negative integers") from exc
        if not same or x < 0:
            raise ValueError("horizons_minutes must contain non-negative integers")
        out.add(x)
    if not out:
        raise ValueError("horizons_minutes must not be empty")
    return sorted(out)


def _normalize_contracts(
    contracts: list[dict],
    *,
    expiry_scope: set[str] | None,
    max_dte_days: float | None,
    iv_source: str,
) -> tuple[list[dict], dict[str, int]]:
    valid: list[dict] = []
    counts = {
        "input": len(contracts),
        "valid_snapshot": 0,
        "omitted_invalid": 0,
        "omitted_scope": 0,
        "iv_input": 0,
        "iv_solved": 0,
        "omitted_iv_unsolved": 0,
    }
    for raw in contracts:
        if not isinstance(raw, dict):
            counts["omitted_invalid"] += 1
            continue
        strike = _finite_positive(raw.get("strike"))
        T = _finite_positive(raw.get("exp_years"))
        oi = _finite_positive(raw.get("oi"))
        right = str(raw.get("right", "")).upper()[:1]
        expiry_raw = raw.get("expiry")
        exp_str_raw = raw.get("exp_str")
        expiry = str(expiry_raw).strip()[:10] if expiry_raw is not None and str(expiry_raw).strip() else None
        exp_str = str(exp_str_raw).strip()[:10] if exp_str_raw is not None and str(exp_str_raw).strip() else None
        if expiry is not None and exp_str is not None and expiry != exp_str:
            counts["omitted_invalid"] += 1
            continue
        expiry = expiry or exp_str
        iv = _finite_positive(raw.get("iv")) if iv_source == IV_SOURCE_PROVIDED else None
        mid = _finite_positive(raw.get("mid")) if iv_source == IV_SOURCE_MID_SOLVE else None
        source_value = iv if iv_source == IV_SOURCE_PROVIDED else mid
        if strike is None or T is None or source_value is None or oi is None or right not in {"C", "P"}:
            counts["omitted_invalid"] += 1
            continue
        if expiry_scope is not None and expiry not in expiry_scope:
            counts["omitted_scope"] += 1
            continue
        if max_dte_days is not None and T * 365.0 > max_dte_days:
            counts["omitted_scope"] += 1
            continue
        row = {
            "strike": strike,
            "exp_years": T,
            "oi": oi,
            "right": right,
            "expiry": expiry,
            "trade_at": raw.get("trade_at"),
            "quote_at": raw.get("quote_at"),
        }
        if iv_source == IV_SOURCE_PROVIDED:
            row["iv"] = iv
            counts["iv_input"] += 1
        else:
            row["mid"] = mid
        valid.append(row)
    counts["valid_snapshot"] = len(valid)
    return valid, counts


def _zero_crossings(xs: list[float], ys: list[float | None]) -> list[float]:
    out: list[float] = []
    for i in range(len(xs) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if y0 is None or y1 is None:
            continue
        x0, x1 = xs[i], xs[i + 1]
        if y0 == 0.0:
            x = x0
        elif (y0 < 0) != (y1 < 0):
            x = x0 - y0 * (x1 - x0) / (y1 - y0) if y1 != y0 else x0
        else:
            continue
        if not out or abs(out[-1] - x) > 1e-10:
            out.append(float(x))
    if ys and ys[-1] == 0.0:
        x = float(xs[-1])
        if not out or abs(out[-1] - x) > 1e-10:
            out.append(x)
    return out


def build_scenario_surface(
    contracts: list[dict],
    *,
    root: str,
    observed_at: str,
    spot: float,
    price_grid: list[float],
    horizons_minutes: list[int],
    expiry_scope: list[str] | None = None,
    max_dte_days: float | None = None,
    oi_vintage: str | None = None,
    iv_observed_at: str | None = None,
    vol_map: str = VOL_MAP_STICKY_STRIKE,
    iv_source: str = IV_SOURCE_PROVIDED,
    r: float = DEFAULT_R,
    q: float = DEFAULT_Q,
    mult: float = CONTRACT_MULTIPLIER,
    pm: float = PCT_MOVE,
) -> dict:
    """Build a typed conditional price x future-time exposure field."""
    root = str(root or "").upper().strip()
    if not root:
        raise ValueError("root is required")
    observed_at = _require_aware_iso(observed_at)
    S0 = _finite_positive(spot)
    if S0 is None:
        raise ValueError("spot must be positive and finite")
    prices = _price_grid(price_grid)
    horizons = _horizons(horizons_minutes)
    if vol_map != VOL_MAP_STICKY_STRIKE:
        raise ValueError("v1 supports only vol_map='sticky_strike'")
    if iv_source not in {IV_SOURCE_PROVIDED, IV_SOURCE_MID_SOLVE}:
        raise ValueError(
            "iv_source must be 'provided_iv' or 'solve_from_mid'"
        )
    r_clean = _finite_number(r)
    q_clean = _finite_number(q)
    mult_clean = _finite_positive(mult)
    pm_clean = _finite_positive(pm)
    if r_clean is None or q_clean is None or mult_clean is None or pm_clean is None:
        raise ValueError("r/q must be finite and mult/pm must be positive finite values")
    r, q, mult, pm = r_clean, q_clean, mult_clean, pm_clean
    observed_dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if iv_observed_at is not None:
        iv_observed_at = _require_aware_iso(iv_observed_at)
        iv_dt = datetime.fromisoformat(iv_observed_at.replace("Z", "+00:00"))
        if iv_dt > observed_dt:
            raise ValueError("iv_observed_at cannot be after observed_at")
    elif iv_source == IV_SOURCE_MID_SOLVE:
        raise ValueError("iv_observed_at is required when iv_source='solve_from_mid'")

    oi_vintage = str(oi_vintage).strip() if oi_vintage is not None else None
    oi_vintage = oi_vintage or None
    if oi_vintage is not None:
        try:
            oi_date = date.fromisoformat(oi_vintage)
        except ValueError as exc:
            raise ValueError("oi_vintage must be an ISO YYYY-MM-DD date") from exc
        if oi_date >= observed_dt.astimezone(ET).date():
            raise ValueError("oi_vintage must be strictly before the observation ET date")
    if max_dte_days is not None:
        max_dte_days = _finite_positive(max_dte_days)
        if max_dte_days is None:
            raise ValueError("max_dte_days must be positive and finite")
    expiry_set = {str(x) for x in expiry_scope} if expiry_scope is not None else None
    normalized, counts = _normalize_contracts(
        contracts,
        expiry_scope=expiry_set,
        max_dte_days=max_dte_days,
        iv_source=iv_source,
    )

    if iv_source == IV_SOURCE_MID_SOLVE and normalized:
        K0 = np.asarray([c["strike"] for c in normalized], dtype=float)
        T0 = np.asarray([c["exp_years"] for c in normalized], dtype=float)
        mids0 = np.asarray([c["mid"] for c in normalized], dtype=float)
        calls0 = np.asarray([c["right"] == "C" for c in normalized], dtype=bool)
        solved = implied_vol_vec(mids0, S0, K0, T0, calls0, r=r, q=q)
        frozen: list[dict] = []
        for contract, solved_iv in zip(normalized, solved):
            if not np.isfinite(solved_iv) or solved_iv <= 0:
                counts["omitted_iv_unsolved"] += 1
                continue
            row = dict(contract)
            row.pop("mid", None)
            row["iv"] = float(solved_iv)
            frozen.append(row)
        normalized = frozen
        counts["iv_solved"] = len(normalized)
        counts["valid_snapshot"] = len(normalized)

    trade_at_first, trade_at_last = _source_clock_bounds(
        normalized, "trade_at", observed_dt=observed_dt
    )
    quote_at_first, quote_at_last = _source_clock_bounds(
        normalized, "quote_at", observed_dt=observed_dt
    )

    grids = {"gex": [], "vex": [], "cex": []}
    horizon_meta: list[dict] = []
    zero_crossings: dict[str, list[dict]] = {key: [] for key in grids}

    for horizon in horizons:
        dt_years = horizon / MINUTES_PER_YEAR
        live = [c for c in normalized if c["exp_years"] - dt_years > 0]
        if not live:
            none_row = [None for _ in prices]
            for key in grids:
                grids[key].append(list(none_row))
            horizon_meta.append({
                "horizon_minutes": horizon,
                "active_contracts": 0,
                "active_snapshot_fraction": 0.0 if normalized else None,
            })
            for metric in zero_crossings:
                zero_crossings[metric].append({
                    "horizon_minutes": horizon,
                    "prices": [],
                })
            continue

        K = np.asarray([c["strike"] for c in live], dtype=float)
        T = np.asarray([c["exp_years"] - dt_years for c in live], dtype=float)
        iv = np.asarray([c["iv"] for c in live], dtype=float)
        oi = np.asarray([c["oi"] for c in live], dtype=float)
        is_call = np.asarray([c["right"] == "C" for c in live], dtype=bool)
        sign = np.where(is_call, 1.0, -1.0)

        row_g: list[float | None] = []
        row_v: list[float | None] = []
        row_c: list[float | None] = []
        for sx in prices:
            _, gamma, vanna, charm = bs_greeks_vec(sx, K, T, iv, is_call, r=r, q=q)
            finite = np.isfinite(gamma) & np.isfinite(vanna) & np.isfinite(charm)
            if not finite.any():
                row_g.append(None)
                row_v.append(None)
                row_c.append(None)
                continue
            with np.errstate(over="ignore", invalid="ignore"):
                g = sign[finite] * gamma[finite] * oi[finite] * mult * sx * sx * pm
                v = sign[finite] * vanna[finite] * oi[finite] * mult * sx * pm
                c = sign[finite] * (charm[finite] / 365.0) * oi[finite] * mult * sx
            row_g.append(_sum_or_none(g))
            row_v.append(_sum_or_none(v))
            row_c.append(_sum_or_none(c))

        grids["gex"].append(row_g)
        grids["vex"].append(row_v)
        grids["cex"].append(row_c)
        horizon_meta.append({
            "horizon_minutes": horizon,
            "active_contracts": len(live),
            "active_snapshot_fraction": round(len(live) / len(normalized), 6) if normalized else None,
        })
        for metric, row in (
            ("gex", row_g),
            ("vex", row_v),
            ("cex", row_c),
        ):
            zero_crossings[metric].append({
                "horizon_minutes": horizon,
                "prices": _zero_crossings(prices, row),
            })

    return {
        "schema": SCHEMA,
        "product_kind": PRODUCT_KIND,
        "root": root,
        "observed_at": observed_at,
        "spot_at_observation": float(S0),
        "price_grid": prices,
        "horizons_minutes": horizons,
        "grids": grids,
        "zero_crossings": zero_crossings,
        "gamma_zero_crossings": [
            {
                "horizon_minutes": row["horizon_minutes"],
                "gamma_zeros": list(row["prices"]),
            }
            for row in zero_crossings["gex"]
        ],
        "horizon_meta": horizon_meta,
        "source_counts": counts,
        "source_clocks": {
            "market_observed_at": observed_at,
            "iv_observed_at": iv_observed_at,
            "oi_vintage": oi_vintage,
            "trade_at_first": trade_at_first,
            "trade_at_last": trade_at_last,
            "quote_at_first": quote_at_first,
            "quote_at_last": quote_at_last,
        },
        "expiry_scope": sorted(expiry_set) if expiry_set is not None else None,
        "max_dte_days": max_dte_days,
        "conventions": {
            "r": r,
            "q": q,
            "contract_multiplier": mult,
            "pct_move": pm,
        },
        "assumptions": {
            "inventory": "fixed_input_oi_snapshot",
            "vol_map": VOL_MAP_STICKY_STRIKE,
            "iv_source": iv_source,
            "time": "deterministic_roll_forward_from_input_exp_years",
            "dealer_sign": "assumed_long_call_short_put",
            "price_axis": "scenario_not_forecast",
            "observed_history": False,
        },
        "units": {
            "gex": "usd_per_1pct_spot_move",
            "vex": "usd_delta_per_1_vol_point",
            "cex": "usd_delta_per_calendar_day",
        },
        "warnings": [
            "modeled conditional field; not observed history",
            "scenario prices are not a predicted path",
            "open interest and frozen per-contract IV are fixed at the observation snapshot",
            "missing OI/IV source clocks remain null rather than inheriting market_observed_at",
            "dealer sign is assumption-based, not observed participant inventory",
        ],
    }
