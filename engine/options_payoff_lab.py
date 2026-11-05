"""Options payoff lab — frozen index-ETF structures over engine/options_payoff.py.

Pure glue. This module selects legs and calls the payoff engine. It does not
price, and it does not choose a second spot or a second expiry rule: spot is
the value engine.options_skew.load_chain records, and the expiry is the one
engine.options_skew._nearest_expiry already uses for the skew ledger.

Display only. Nothing here ranks a structure or tells anyone to trade.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd

import engine.options_skew as options_skew
import engine.thetadata_store as thetadata_store
from engine.options_payoff import (
    DEFAULT_Q,
    DEFAULT_R,
    NullState,
    assumption_block,
    evidence_recipe,
    expiry_payoff,
    greeks_drift,
    scenario_grid,
    structure_from_chain,
    structure_summary,
)

SCHEMA = "mastermind.options_payoff_lab/v1"
SOURCE = "thetadata"
ROOTS = ("SPY", "QQQ", "IWM", "DIA")
CATALOG = (
    "atm_straddle",
    "rr25",
    "put_spread_95_90",
    "call_spread_105_110",
)

# Caller input, not a chain field. chain() supplies no multiplier
# (engine/options_payoff.py). Index-ETF standard contract is 100.
ETF_STANDARD_MULTIPLIER = 100.0

SPOT_SHOCKS = (-0.10, -0.05, 0.0, 0.05, 0.10)
VOL_SHOCKS = (0.0,)
HORIZONS = (0, 7, 21)
PAYOFF_POINTS = 41
PAYOFF_LOW = 0.80
PAYOFF_HIGH = 1.20

# 25-delta risk reversal, delta-first. The moneyness marks are the fallback
# the packet pins (call 1.05, put 0.95), not a second delta definition.
_RR_CALL_DELTA = 0.25
_RR_PUT_DELTA = -0.25
_RR_CALL_MONEYNESS = 1.05
_RR_PUT_MONEYNESS = 0.95


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_day(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()[:10]


def _json_safe(value):
    """Make engine output JSON-safe. A non-finite float becomes null, never 0."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        if value != value or value == float("inf") or value == float("-inf"):
            return None
        return value
    try:
        import numpy as np
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            number = float(value)
            if number != number or number == float("inf") or number == float("-inf"):
                return None
            return number
        if isinstance(value, np.bool_):
            return bool(value)
    except ImportError:
        pass
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _state(code: str, scope: str, reason: str, receipt: dict) -> dict:
    return {"code": code, "scope": scope, "reason": reason, "receipt": receipt}


def _as_state(item) -> dict | None:
    if isinstance(item, NullState):
        item = asdict(item)
    if isinstance(item, dict) and item.get("code"):
        return _json_safe(item)
    return None


def _collect_states(*objects, extra=()) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for obj in objects:
        for item in getattr(obj, "states", ()) or ():
            state = _as_state(item)
            if state is None:
                continue
            key = (state.get("code"), state.get("scope"), state.get("reason"))
            if key in seen:
                continue
            seen.add(key)
            out.append(state)
    for item in extra:
        state = _as_state(item)
        if state is None:
            continue
        key = (state.get("code"), state.get("scope"), state.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        out.append(state)
    return out


def _spot_value(frame) -> float | None:
    """The spot column load_chain already computed. No second derivation."""
    if frame is None or getattr(frame, "empty", True) or "spot" not in getattr(frame, "columns", []):
        return None
    series = pd.to_numeric(frame["spot"], errors="coerce").dropna()
    if series.empty:
        return None
    spot = float(series.iloc[0])
    if spot != spot or spot <= 0.0:
        return None
    return spot


def _strikes(chain_df, expiration: str, right: str | None) -> list[float]:
    sub = chain_df[chain_df["expiration"].astype(str).str[:10] == expiration]
    if right is not None and "right" in sub.columns:
        sub = sub[sub["right"].astype(str).str.upper() == right]
    if sub.empty or "strike" not in sub.columns:
        return []
    values = pd.to_numeric(sub["strike"], errors="coerce").dropna()
    found = sorted({float(v) for v in values})
    return found


def _nearest_strike(strikes: list[float], mark: float) -> float | None:
    if not strikes:
        return None
    return min(strikes, key=lambda strike: (abs(strike - mark), strike))


def _strike_by_delta(chain_df, expiration: str, right: str, delta_mark: float, moneyness_mark: float):
    """Delta-first, matching the shape of options_skew._iv_at_delta.

    When every delta on this side is missing, fall back to the strike nearest
    `moneyness_mark`. The receipt records which rule fired.
    """
    sub = chain_df[chain_df["expiration"].astype(str).str[:10] == expiration]
    sub = sub[sub["right"].astype(str).str.upper() == right]
    if sub.empty:
        return None, "no_listed_strike"
    deltas = pd.to_numeric(sub["delta"], errors="coerce") if "delta" in sub.columns else None
    if deltas is not None and bool(deltas.notna().any()):
        work = sub.assign(
            _distance=(deltas - delta_mark).abs(),
            _strike=pd.to_numeric(sub["strike"], errors="coerce"),
        )
        work = work[work["_distance"].notna() & work["_strike"].notna()]
        if not work.empty:
            work = work.sort_values(["_distance", "_strike"], kind="mergesort")
            return float(work.iloc[0]["_strike"]), "delta"
    strike = _nearest_strike(_strikes(chain_df, expiration, right), moneyness_mark)
    if strike is None:
        return None, "no_listed_strike"
    return strike, "moneyness"


def _leg(right: str, strike: float | None, expiration: str, qty: int) -> dict:
    return {
        "right": right,
        "strike": strike,
        "expiration": expiration,
        "qty": qty,
    }


def _receipt(leg_index: int, right: str, qty: int, rule: str, strike: float | None) -> dict:
    return {
        "leg": leg_index,
        "right": right,
        "qty": qty,
        "rule": rule,
        "strike": strike,
    }


def _catalog_specs(chain_df, expiration: str, spot: float) -> list[tuple[str, list[dict], list[dict]]]:
    atm = _nearest_strike(_strikes(chain_df, expiration, None), spot)
    call_25, call_rule = _strike_by_delta(
        chain_df, expiration, "C", _RR_CALL_DELTA, spot * _RR_CALL_MONEYNESS,
    )
    put_25, put_rule = _strike_by_delta(
        chain_df, expiration, "P", _RR_PUT_DELTA, spot * _RR_PUT_MONEYNESS,
    )
    put_long = _nearest_strike(_strikes(chain_df, expiration, "P"), spot * 0.95)
    put_short = _nearest_strike(_strikes(chain_df, expiration, "P"), spot * 0.90)
    call_long = _nearest_strike(_strikes(chain_df, expiration, "C"), spot * 1.05)
    call_short = _nearest_strike(_strikes(chain_df, expiration, "C"), spot * 1.10)
    return [
        (
            "atm_straddle",
            [_leg("C", atm, expiration, 1), _leg("P", atm, expiration, 1)],
            [
                _receipt(0, "C", 1, "nearest_spot", atm),
                _receipt(1, "P", 1, "nearest_spot", atm),
            ],
        ),
        (
            "rr25",
            [_leg("C", call_25, expiration, 1), _leg("P", put_25, expiration, -1)],
            [
                _receipt(0, "C", 1, call_rule, call_25),
                _receipt(1, "P", -1, put_rule, put_25),
            ],
        ),
        (
            "put_spread_95_90",
            [_leg("P", put_long, expiration, 1), _leg("P", put_short, expiration, -1)],
            [
                _receipt(0, "P", 1, "nearest_moneyness", put_long),
                _receipt(1, "P", -1, "nearest_moneyness", put_short),
            ],
        ),
        (
            "call_spread_105_110",
            [_leg("C", call_long, expiration, 1), _leg("C", call_short, expiration, -1)],
            [
                _receipt(0, "C", 1, "nearest_moneyness", call_long),
                _receipt(1, "C", -1, "nearest_moneyness", call_short),
            ],
        ),
    ]


def _payoff_spots(spot: float) -> list[float]:
    last = PAYOFF_POINTS - 1
    span = PAYOFF_HIGH - PAYOFF_LOW
    return [spot * (PAYOFF_LOW + span * i / last) for i in range(PAYOFF_POINTS)]


def _structure_record(chain_df, root: str, asof: str, spot: float, name: str, specs: list[dict], rules: list[dict]) -> dict:
    multipliers = [ETF_STANDARD_MULTIPLIER] * len(specs)
    structure = structure_from_chain(
        chain_df,
        root=root,
        asof_date=asof,
        leg_specs=specs,
        multipliers=multipliers,
    )
    summary = structure_summary(structure, base_spot=spot, evaluation_date=asof)
    payoff = expiry_payoff(structure, _payoff_spots(spot))
    grids = {
        str(days): asdict(scenario_grid(
            structure,
            base_spot=spot,
            spot_shocks=SPOT_SHOCKS,
            vol_shocks=VOL_SHOCKS,
            days_forward=days,
            evaluation_date=asof,
        ))
        for days in HORIZONS
    }
    drift = greeks_drift(
        structure,
        base_spot=spot,
        days_forward=HORIZONS,
        evaluation_date=asof,
    )
    assumptions = assumption_block(structure, r=DEFAULT_R, q=DEFAULT_Q)
    recipe = evidence_recipe(
        structure,
        r=DEFAULT_R,
        q=DEFAULT_Q,
        spot_shocks=SPOT_SHOCKS,
        vol_shocks=VOL_SHOCKS,
        days_forward=HORIZONS,
    )
    return {
        "name": name,
        "selection_rule": rules,
        "summary": asdict(summary),
        "expiry_payoff": asdict(payoff),
        "scenario_grids": grids,
        "greeks_drift": asdict(drift),
        "assumptions": asdict(assumptions),
        "evidence_recipe": recipe,
        "states": _collect_states(structure, summary, payoff, drift, extra=[
            state for grid in grids.values() for state in (grid.get("states") or [])
        ]),
    }


def _root_shell(root: str, spot, expiration, tenor_days, structures, states) -> dict:
    return {
        "root": root,
        "spot": spot,
        "expiration": expiration,
        "tenor_days": tenor_days,
        "structures": structures,
        "states": states,
    }


def _structure_is_built(record: dict) -> bool:
    payoff = record.get("expiry_payoff") or {}
    return payoff.get("max_gain") is not None or payoff.get("max_loss") is not None


def _counts(roots: list[dict]) -> dict:
    priced = 0
    built = 0
    nulls = 0
    for root in roots:
        root_built = 0
        for record in root["structures"]:
            if _structure_is_built(record):
                built += 1
                root_built += 1
            else:
                nulls += 1
        if root_built:
            priced += 1
        elif not root["structures"]:
            nulls += len(CATALOG)
    return {
        "roots_priced": priced,
        "structures_built": built,
        "structures_null": nulls,
    }


def _envelope(asof: str | None, generated: str, roots: list[dict], states: list[dict]) -> dict:
    return _json_safe({
        "schema": SCHEMA,
        "asof": asof,
        "generated_utc": generated,
        "source": SOURCE,
        "roots": roots,
        "counts": _counts(roots),
        "states": states,
    })


def _build_root(asof: str, root: str, store) -> dict:
    chain_df = thetadata_store.chain(asof, root, store=store)
    if chain_df is None or len(chain_df) == 0:
        return _root_shell(
            root, None, None, None, [],
            [_state(
                "CHAIN_EMPTY",
                "root",
                "The chain for this root has no rows on this session.",
                {"root": root, "asof": asof},
            )],
        )

    loaded, load_state = options_skew.load_chain(asof, store=store, roots=[root])
    spot = _spot_value(loaded)
    if spot is None:
        return _root_shell(
            root, None, None, None, [],
            [_state(
                "SPOT_UNAVAILABLE",
                "root",
                "The skew chain did not record a usable spot for this root.",
                {"root": root, "asof": asof, "load_state": load_state},
            )],
        )

    chosen = options_skew._nearest_expiry(loaded)
    if chosen is None or getattr(chosen, "empty", True):
        return _root_shell(
            root, spot, None, None, [],
            [_state(
                "NO_USABLE_TENOR",
                "root",
                "No listed expiration passed the skew tenor rule for this root.",
                {"root": root, "asof": asof},
            )],
        )

    expiration = _iso_day(chosen["expiry"].iloc[0])
    tenor_days = float(chosen["T"].astype(float).iloc[0]) * 365.0
    work = chain_df.copy()
    work["expiration"] = work["expiration"].map(_iso_day)
    on_expiry = work[work["expiration"] == expiration]
    if on_expiry.empty:
        return _root_shell(
            root, spot, expiration, tenor_days, [],
            [_state(
                "NO_USABLE_TENOR",
                "root",
                "The skew tenor expiry is not in this root's chain rows.",
                {"root": root, "asof": asof, "expiration": expiration},
            )],
        )

    structures = [
        _structure_record(work, root, asof, spot, name, specs, rules)
        for name, specs, rules in _catalog_specs(work, expiration, spot)
    ]
    return _root_shell(root, spot, expiration, tenor_days, structures, [])


def build_payoff_lab(asof: str, *, store=None, roots=ROOTS) -> dict:
    """One session of the frozen catalog. `store` is a ThetaData store root."""
    generated = _utc_now()
    if store is None:
        store = thetadata_store.resolve_thetadata_store(
            required=False, purpose="options_payoff_lab")
    if store is None:
        return _envelope(asof, generated, [], [_state(
            "STORE_UNRESOLVED",
            "artifact",
            "The ThetaData store is not available, so no root was priced.",
            {"asof": asof},
        )])
    rows = [_build_root(asof, root, store) for root in roots]
    top = [state for row in rows for state in row["states"]]
    return _envelope(asof, generated, rows, top)
