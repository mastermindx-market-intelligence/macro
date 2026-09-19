from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from itertools import permutations
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from typing import Any, Callable

import numpy as np
import pandas as pd

SCHEMA = "skylit.r2.exposure_decomposition_feasibility/v1"
POSITION_TIER = "naive_dealer_long_calls_short_puts/v1"
EXPOSURE_UNIT = "USD dealer-delta change per +1% spot move"
KEY = ["root", "expiration", "strike", "right"]
FACTORS = ("position", "spot", "vol", "time")
CONTRACT_MULTIPLIER = 100.0
PCT_MOVE = 0.01
CONTRACT_MATCH_TARGET = 0.90
MODEL_INPUT_MATCH_TARGET = 0.90
EXPOSURE_MASS_TARGET = 0.95


class R2Refusal(ValueError):
    pass


def _default_greeks_fn():
    from engine.intraday_greeks import bs_greeks_vec
    return bs_greeks_vec


def _default_store_api():
    from engine import thetadata_store
    return thetadata_store

def _greek_method_metadata(greeks_fn: Callable | None) -> dict[str, Any]:
    if greeks_fn is None:
        from engine import intraday_greeks
        return {
            "kernel": "engine.intraday_greeks.bs_greeks_vec",
            "rate": float(intraday_greeks.DEFAULT_R),
            "dividend_yield": float(intraday_greeks.DEFAULT_Q),
            "vol_counterfactual": "sticky_strike",
            "position_tier": POSITION_TIER,
        }
    return {
        "kernel": f"{getattr(greeks_fn, '__module__', 'unknown')}.{getattr(greeks_fn, '__name__', 'callable')}",
        "rate": None,
        "dividend_yield": None,
        "vol_counterfactual": "sticky_strike",
        "position_tier": POSITION_TIER,
    }




def _default_calendar_api():
    from lib import nyse_calendar
    return nyse_calendar


def _canonical_session(value: str, calendar_api) -> date:
    try:
        parsed = date.fromisoformat(value)
    except Exception as exc:
        raise R2Refusal(f"invalid session date: {value!r}") from exc
    if not calendar_api.is_session(parsed):
        raise R2Refusal(f"not an NYSE session: {value}")
    return parsed


def _next_session(value: str, calendar_api) -> str:
    parsed = _canonical_session(value, calendar_api)
    nxt = calendar_api.session_n_forward(parsed, 1)
    if nxt is None:
        raise R2Refusal(f"calendar cannot resolve next session after {value}")
    return nxt.isoformat()


def _identity_valid_mask(frame: pd.DataFrame, root: str) -> pd.Series:
    missing = sorted(set(KEY) - set(frame.columns))
    if missing:
        raise R2Refusal(f"missing required columns: {missing}")
    strike = pd.to_numeric(frame["strike"], errors="coerce")
    expiry = pd.to_datetime(frame["expiration"], errors="coerce")
    return (
        frame["root"].astype(str).str.upper().eq(root.upper())
        & frame["right"].astype(str).str.upper().isin(["C", "P"])
        & np.isfinite(strike)
        & strike.gt(0)
        & expiry.notna()
    )


def _normalize_identity(frame: pd.DataFrame, root: str, *, require_oi: bool = False) -> pd.DataFrame:
    required = set(KEY)
    if require_oi:
        required.add("open_interest")
    missing = sorted(required - set(frame.columns))
    if missing:
        raise R2Refusal(f"missing required columns: {missing}")
    out = frame.copy()
    valid_identity = _identity_valid_mask(out, root)
    out = out[valid_identity].copy()
    out["root"] = out["root"].astype(str).str.upper()
    out["right"] = out["right"].astype(str).str.upper()
    out["expiration"] = pd.to_datetime(out["expiration"], errors="coerce").dt.date.astype(str)
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    if require_oi:
        out["open_interest"] = pd.to_numeric(out["open_interest"], errors="coerce")
        out = out[np.isfinite(out["open_interest"]) & (out["open_interest"] >= 0)].copy()
    out = out.drop_duplicates()
    if out.duplicated(KEY, keep=False).any():
        bad = out.loc[out.duplicated(KEY, keep=False), KEY].drop_duplicates().head(5)
        raise R2Refusal(f"conflicting duplicate contract identities: {bad.to_dict('records')}")
    return out.reset_index(drop=True)


def _canon_number(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    number = float(value)
    if number == 0:
        number = 0.0
    return format(number, ".12g")


def _digest_frame(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return hashlib.sha256(b"").hexdigest()
    ordered = frame.sort_values(KEY, kind="mergesort")
    lines: list[str] = []
    for row in ordered.itertuples(index=False, name=None):
        mapping = dict(zip(ordered.columns, row))
        parts = []
        for col in columns:
            value = mapping.get(col)
            if col in {"root", "expiration", "right"}:
                parts.append(str(value))
            else:
                parts.append(_canon_number(value))
        lines.append("\t".join(parts))
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def _exposure_gex(
    position: np.ndarray,
    spot: np.ndarray,
    vol: np.ndarray,
    time_years: np.ndarray,
    strike: np.ndarray,
    right: np.ndarray,
    *,
    greeks_fn: Callable | None = None,
) -> np.ndarray:
    fn = greeks_fn or _default_greeks_fn()
    is_call = np.asarray(right) == "C"
    _, gamma, _, _ = fn(spot, strike, time_years, vol, is_call)
    sign = np.where(is_call, 1.0, -1.0)
    exposure = sign * gamma * CONTRACT_MULTIPLIER * position * np.square(spot) * PCT_MOVE
    valid = (
        np.isfinite(position) & (position >= 0)
        & np.isfinite(spot) & (spot > 0)
        & np.isfinite(vol) & (vol > 0)
        & np.isfinite(time_years) & (time_years > 0)
        & np.isfinite(strike) & (strike > 0)
        & np.isfinite(exposure)
    )
    return np.where(valid, exposure, np.nan)


def build_settled_state(
    session: str,
    root: str,
    *,
    store: str | Path | None = None,
    store_api=None,
    calendar_api=None,
    greeks_fn: Callable | None = None,
) -> dict[str, Any]:
    store_api = store_api or _default_store_api()
    calendar_api = calendar_api or _default_calendar_api()
    session_day = _canonical_session(session, calendar_api)
    oi_publication_session = _next_session(session, calendar_api)
    if store is None:
        store = store_api.resolve_thetadata_store(required=True, purpose="skylit-r2-stage0")

    base_raw = store_api.chain(session, root.upper(), store=store)
    if base_raw is None or base_raw.empty:
        raise R2Refusal(f"no EOD/Greeks chain for {root.upper()} {session}")
    identity_mask = _identity_valid_mask(base_raw, root)
    invalid_identity_rows = int((~identity_mask).sum())
    if invalid_identity_rows:
        raise R2Refusal(
            f"malformed contract identity rows for {root.upper()} {session}: "
            f"{invalid_identity_rows}/{len(base_raw)}"
        )
    base = _normalize_identity(base_raw, root)
    for col in ("implied_vol", "underlying_price"):
        if col not in base.columns:
            raise R2Refusal(f"chain missing {col} for {root.upper()} {session}")
    base["implied_vol"] = pd.to_numeric(base["implied_vol"], errors="coerce")
    base["underlying_price"] = pd.to_numeric(base["underlying_price"], errors="coerce")
    if "open_interest" in base.columns:
        base["prior_open_interest"] = pd.to_numeric(base["open_interest"], errors="coerce")
    else:
        base["prior_open_interest"] = np.nan
    unexpired = base[pd.to_datetime(base["expiration"]).dt.date > session_day].copy()
    if unexpired.empty:
        raise R2Refusal(f"no unexpired contracts for {root.upper()} {session}")

    oi_raw = store_api.oi_for_date(oi_publication_session, root.upper(), store=store)
    if oi_raw is None or oi_raw.empty:
        raise R2Refusal(
            f"no next-session OI publication for {root.upper()} {session} via {oi_publication_session}"
        )
    oi = _normalize_identity(oi_raw, root, require_oi=True)
    oi = oi.rename(columns={"open_interest": "settled_open_interest"})

    # Coverage denominators are the complete unexpired identity board.  Do not
    # filter away a contract merely because one model input is missing: that
    # would let missing IV/OI disappear from the denominator and falsely qualify
    # a partial source board.
    merged = unexpired.merge(
        oi[KEY + ["settled_open_interest"]],
        on=KEY,
        how="left",
        validate="one_to_one",
    )
    expiry = pd.to_datetime(merged["expiration"])
    merged["time_years"] = (expiry.dt.date - session_day).map(lambda x: x.days / 365.0)

    eligible_n = int(len(merged))
    spot_mask = np.isfinite(merged["underlying_price"]) & (merged["underlying_price"] > 0)
    spot_input_rate = float(spot_mask.mean()) if eligible_n else 0.0
    spots = merged.loc[spot_mask, "underlying_price"]
    if spots.empty:
        raise R2Refusal(f"no qualified underlying_price for {root.upper()} {session}")
    spot = float(spots.median())
    spot_range_bps = float((spots.max() - spots.min()) / spot * 10000.0) if spot else float("nan")
    merged["spot"] = spot

    iv_mask = np.isfinite(merged["implied_vol"]) & (merged["implied_vol"] > 0)
    model_input_rate = float(iv_mask.mean()) if eligible_n else 0.0
    settled_mask = np.isfinite(merged["settled_open_interest"])
    prior_mask = np.isfinite(merged["prior_open_interest"]) & (merged["prior_open_interest"] >= 0)
    settled_rate = float(settled_mask.mean()) if eligible_n else 0.0
    prior_rate = float(prior_mask.mean()) if eligible_n else 0.0

    prior_exposure = _exposure_gex(
        merged["prior_open_interest"].to_numpy(float),
        merged["spot"].to_numpy(float),
        merged["implied_vol"].to_numpy(float),
        merged["time_years"].to_numpy(float),
        merged["strike"].to_numpy(float),
        merged["right"].to_numpy(str),
        greeks_fn=greeks_fn,
    )
    prior_mass = np.abs(prior_exposure)
    reference_mask = iv_mask & prior_mask & np.isfinite(prior_mass)
    prior_mass_den = float(np.sum(prior_mass[reference_mask])) if reference_mask.any() else 0.0
    if (
        model_input_rate < MODEL_INPUT_MATCH_TARGET
        or prior_rate < CONTRACT_MATCH_TARGET
        or not np.isfinite(prior_mass_den)
        or prior_mass_den <= 0
    ):
        exposure_mass_coverage = None
    else:
        matched_reference = reference_mask & settled_mask
        exposure_mass_coverage = float(
            np.sum(prior_mass[matched_reference]) / prior_mass_den
        )

    qualified = bool(
        model_input_rate >= MODEL_INPUT_MATCH_TARGET
        and spot_input_rate >= MODEL_INPUT_MATCH_TARGET
        and settled_rate >= CONTRACT_MATCH_TARGET
        and prior_rate >= CONTRACT_MATCH_TARGET
        and exposure_mass_coverage is not None
        and exposure_mass_coverage >= EXPOSURE_MASS_TARGET
    )

    usable = merged[iv_mask & settled_mask].copy()
    usable["position"] = usable["settled_open_interest"].astype(float)
    usable["vol"] = usable["implied_vol"].astype(float)
    usable["exposure_gex"] = _exposure_gex(
        usable["position"].to_numpy(float),
        usable["spot"].to_numpy(float),
        usable["vol"].to_numpy(float),
        usable["time_years"].to_numpy(float),
        usable["strike"].to_numpy(float),
        usable["right"].to_numpy(str),
        greeks_fn=greeks_fn,
    )
    usable = usable[np.isfinite(usable["exposure_gex"])].copy().reset_index(drop=True)

    base_digest_cols = KEY + ["implied_vol", "underlying_price", "prior_open_interest"]
    oi_digest_cols = KEY + ["settled_open_interest"]
    return {
        "session": session,
        "root": root.upper(),
        "exposure_unit": EXPOSURE_UNIT,
        "position_publication_session": oi_publication_session,
        "decision_eligible_not_before_session": oi_publication_session,
        "source_availability_precision": "session_only_from_current_store_reader",
        "spot": spot,
        "spot_cross_contract_range_bps": spot_range_bps,
        "spot_input_contract_rate": spot_input_rate,
        "unexpired_identity_contracts": int(len(unexpired)),
        "model_input_contract_rate": model_input_rate,
        "iv_contract_rate": model_input_rate,
        "eligible_contracts": eligible_n,
        "settled_oi_matched_contracts": int(settled_mask.sum()),
        "settled_oi_contract_rate": settled_rate,
        "prior_oi_contract_rate": prior_rate,
        "settled_oi_exposure_mass_coverage_on_prior_known_mass": exposure_mass_coverage,
        "target_gate_pass": qualified,
        "base_input_sha256": _digest_frame(merged, base_digest_cols),
        "settled_oi_input_sha256": _digest_frame(
            merged[settled_mask].copy(),
            oi_digest_cols,
        ),
        "frame": usable[
            KEY + ["position", "spot", "vol", "time_years", "exposure_gex"]
        ].copy(),
    }


def decompose_survivors(
    state0: pd.DataFrame,
    state1: pd.DataFrame,
    *,
    greeks_fn: Callable | None = None,
) -> dict[str, Any]:
    joined = state0.merge(
        state1,
        on=KEY,
        how="inner",
        suffixes=("_0", "_1"),
        validate="one_to_one",
    )
    if joined.empty:
        raise R2Refusal("no surviving contracts across the two qualified states")
    strike = joined["strike"].to_numpy(float)
    right = joined["right"].to_numpy(str)
    x0 = {
        "position": joined["position_0"].to_numpy(float),
        "spot": joined["spot_0"].to_numpy(float),
        "vol": joined["vol_0"].to_numpy(float),
        "time": joined["time_years_0"].to_numpy(float),
    }
    x1 = {
        "position": joined["position_1"].to_numpy(float),
        "spot": joined["spot_1"].to_numpy(float),
        "vol": joined["vol_1"].to_numpy(float),
        "time": joined["time_years_1"].to_numpy(float),
    }

    def evaluate(values: dict[str, np.ndarray]) -> np.ndarray:
        return _exposure_gex(
            values["position"],
            values["spot"],
            values["vol"],
            values["time"],
            strike,
            right,
            greeks_fn=greeks_fn,
        )

    e0 = evaluate(x0)
    e1 = evaluate(x1)
    if not np.isfinite(e0).all() or not np.isfinite(e1).all():
        raise R2Refusal("non-finite survivor exposure at an endpoint")
    contrib = {name: np.zeros(len(joined), dtype=float) for name in FACTORS}
    perms = list(permutations(FACTORS))
    for perm in perms:
        current = {name: x0[name].copy() for name in FACTORS}
        before = evaluate(current)
        for name in perm:
            current[name] = x1[name]
            after = evaluate(current)
            contrib[name] += after - before
            before = after
    for name in FACTORS:
        contrib[name] /= float(len(perms))

    raw = e1 - e0
    reconstructed = sum(contrib.values())
    closure = raw - reconstructed
    net = {name: float(np.sum(values)) for name, values in contrib.items()}
    abs_mass = {name: float(np.sum(np.abs(values))) for name, values in contrib.items()}
    total_abs = float(sum(abs_mass.values()))
    share = {
        name: (abs_mass[name] / total_abs if total_abs > 0 else None)
        for name in FACTORS
    }
    return {
        "survivor_contracts": int(len(joined)),
        "raw_survivor_change_net": float(np.sum(raw)),
        "component_net": net,
        "component_abs_mass": abs_mass,
        "component_abs_share": share,
        "aggregate_closure_error": float(np.sum(closure)),
        "max_contract_closure_error_abs": float(np.max(np.abs(closure))),
    }


def _composition_summary(
    state0: pd.DataFrame,
    state1: pd.DataFrame,
    session1: str,
) -> dict[str, Any]:
    k0 = state0.set_index(KEY)
    k1 = state1.set_index(KEY)
    only0 = k0.index.difference(k1.index)
    only1 = k1.index.difference(k0.index)
    known_expired = []
    unresolved_exit = []
    cutoff = date.fromisoformat(session1)
    for key in only0:
        expiry = date.fromisoformat(str(key[1]))
        (known_expired if expiry <= cutoff else unresolved_exit).append(key)
    expired_net = (
        -float(k0.loc[known_expired, "exposure_gex"].sum())
        if known_expired
        else 0.0
    )
    unresolved_exit_net = (
        -float(k0.loc[unresolved_exit, "exposure_gex"].sum())
        if unresolved_exit
        else 0.0
    )
    unresolved_entry_net = (
        float(k1.loc[only1, "exposure_gex"].sum())
        if len(only1)
        else 0.0
    )
    return {
        "known_expiry_deaths": len(known_expired),
        "known_expiry_death_net": expired_net,
        "unresolved_exits": len(unresolved_exit),
        "unresolved_exit_net": unresolved_exit_net,
        "unresolved_entries": int(len(only1)),
        "unresolved_entry_net": unresolved_entry_net,
        "full_map_composition_resolved": not unresolved_exit and len(only1) == 0,
    }


def _public_state_summary(state: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in state.items() if k != "frame"}


def analyze_pair(
    session0: str,
    session1: str,
    root: str,
    *,
    store: str | Path | None = None,
    store_api=None,
    calendar_api=None,
    greeks_fn: Callable | None = None,
) -> dict[str, Any]:
    calendar_api = calendar_api or _default_calendar_api()
    s0 = _canonical_session(session0, calendar_api)
    s1 = _canonical_session(session1, calendar_api)
    expected = calendar_api.session_n_forward(s0, 1)
    if expected is None or expected != s1:
        raise R2Refusal(
            f"sessions must be consecutive NYSE sessions: {session0} -> {session1}"
        )
    state0 = build_settled_state(
        session0,
        root,
        store=store,
        store_api=store_api,
        calendar_api=calendar_api,
        greeks_fn=greeks_fn,
    )
    state1 = build_settled_state(
        session1,
        root,
        store=store,
        store_api=store_api,
        calendar_api=calendar_api,
        greeks_fn=greeks_fn,
    )
    base = {
        "schema": SCHEMA,
        "research_authority": "research_only",
        "position_tier": POSITION_TIER,
        "exposure_unit": EXPOSURE_UNIT,
        "method": _greek_method_metadata(greeks_fn),
        "outcome_labels_opened": False,
        "root": root.upper(),
        "session0": session0,
        "session1": session1,
        "elapsed_calendar_days": (s1 - s0).days,
        "pair_decision_eligible_not_before_session": state1["decision_eligible_not_before_session"],
        "decomposition_scope": "survivor_contracts_only",
        "state0": _public_state_summary(state0),
        "state1": _public_state_summary(state1),
        "limitations": [
            "settled EOD position for session S is consumed from next-session OI publication",
            "current store reader binds OI availability only to the publication session, not an exact intraday availability timestamp",
            "Tier A dealer sign convention is an estimate: calls long / puts short",
            "new-contract births and non-expiry disappearances remain unresolved composition in Stage 0",
            "this analyzer opens no future market or option outcome labels",
        ],
    }
    if not state0["target_gate_pass"] or not state1["target_gate_pass"]:
        base["status"] = "INSUFFICIENT_COVERAGE"
        base["decomposition"] = None
        return base

    decomposition = decompose_survivors(
        state0["frame"],
        state1["frame"],
        greeks_fn=greeks_fn,
    )
    composition = _composition_summary(state0["frame"], state1["frame"], session1)
    base["status"] = "SURVIVOR_DECOMPOSITION_COMPLETE"
    base["decomposition"] = decomposition
    base["composition"] = composition
    return base


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Research-only R2 daily exposure decomposition feasibility analyzer"
    )
    p.add_argument("--root", required=True)
    p.add_argument(
        "--session0",
        required=True,
        help="Earlier settled NYSE session, YYYY-MM-DD",
    )
    p.add_argument(
        "--session1",
        required=True,
        help="Next settled NYSE session, YYYY-MM-DD",
    )
    p.add_argument(
        "--store",
        help="Optional ThetaData store override; canonical resolver is used otherwise",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = analyze_pair(
            args.session0,
            args.session1,
            args.root,
            store=args.store,
        )
    except R2Refusal as exc:
        print(json.dumps(
            {"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)},
            sort_keys=True,
        ))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
