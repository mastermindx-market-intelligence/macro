"""Read-only carry/funding projection for the existing Forex dashboard.

This module does not calculate a carry-unwind scenario, freshness score, trade
signal or funding verdict. It projects current owners with explicit units and
keeps direct USD cross-currency basis unavailable until an admitted source
exists.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from numbers import Real
from typing import Any

import math
import pandas as pd


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _measure(value: object, unit: str, *, lo: float | None = None,
             hi: float | None = None, unavailable: bool = False) -> dict[str, Any]:
    if unavailable:
        return {"status": "unavailable", "value": None, "unit": unit}
    number = _finite(value)
    if number is None or (lo is not None and number < lo) or (hi is not None and number > hi):
        return {"status": "invalid", "value": None, "unit": unit}
    return {"status": "available", "value": number, "unit": unit}


def _date(value: object) -> str | None:
    # pandas interprets numeric scalars as nanoseconds from the Unix epoch.
    # Numeric values are valid for measures, but never for date identity.
    if isinstance(value, (bool, Real)):
        return None
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if pd.isna(stamp):
        return None
    return stamp.date().isoformat()


def _latest_point(frame: object, family: str) -> dict[str, Any]:
    base = {"status": "unavailable", "value": None, "calculated_through": None,
            "source_family": family}
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return base
    try:
        series = pd.to_numeric(frame.iloc[:, 0], errors="coerce")
    except Exception:
        return {**base, "status": "invalid"}
    # Do not forward fill here; expose the latest actually present stored point.
    series = series.dropna()
    if series.empty:
        return base
    value = series.iloc[-1]
    # pandas can coerce booleans to numeric in some dtypes; inspect the original cell.
    raw = frame.loc[series.index[-1]].iloc[0]
    if isinstance(raw, bool):
        return {**base, "status": "invalid"}
    number = _finite(value)
    stamp = _date(series.index[-1])
    if number is None or stamp is None:
        return {**base, "status": "invalid"}
    return {"status": "available", "value": number, "calculated_through": stamp,
            "source_family": family}


def collect_funding_context(
    read_store: Callable[[str, str], object],
    intl_risk_artifact: object = None,
    regime_artifact: object = None,
) -> dict[str, Any]:
    """Collect contextual funding evidence through existing published owners.

    OFR fields retain their latest stored observation dates. SOFR-IORB is read
    from data/intl_risk/latest.json rather than recomputing contagion inside
    the Forex builder. A2/P2 and CP-bill come from the existing regime artifact.
    Artifact build/as-of dates are not promoted to vendor observation times.
    No direct market-wide USD x-ccy basis source is implied by any proxy.
    """
    try:
        ofr = _latest_point(read_store("ofr_fsi", "fsi"), "ofr_fsi")
    except Exception:
        ofr = {"status": "unavailable", "value": None, "calculated_through": None,
               "source_family": "ofr_fsi"}
    try:
        ofr_funding = _latest_point(read_store("ofr_fsi", "fsi_funding"), "ofr_fsi")
    except Exception:
        ofr_funding = {"status": "unavailable", "value": None, "calculated_through": None,
                       "source_family": "ofr_fsi"}

    intl = intl_risk_artifact if isinstance(intl_risk_artifact, Mapping) else {}
    corridor = {
        "status": "unavailable", "value_bp": None, "hot": None,
        "last5_all_positive": None, "calculated_through": None,
        "artifact_built": intl.get("built") if isinstance(intl.get("built"), str) else None,
        "source_family": "intl_risk_two_tier",
        "unit": "basis_points",
    }
    try:
        leg = ((((intl.get("two_tier") or {}).get("tier2") or {}).get("legs") or {})
               .get("sofr_iorb_corridor") or {})
        value_pp = _finite(leg.get("value"))
        hot = leg.get("hot")
        last5 = leg.get("last5_all_positive")
        if value_pp is not None and isinstance(hot, bool) and isinstance(last5, bool):
            # contagion.two_tier_read stores SOFR-IORB in percentage points;
            # the user-facing funding desk displays basis points.
            value_bp = value_pp * 100.0
            if math.isfinite(value_bp):
                corridor.update(
                    status="available", value_bp=round(value_bp, 6), hot=hot,
                    last5_all_positive=last5,
                    threshold=leg.get("threshold"), caveat=leg.get("caveat"),
                )
    except Exception:
        corridor["status"] = "invalid"

    regime = regime_artifact if isinstance(regime_artifact, Mapping) else {}
    regime_as_of = _date(regime.get("asof"))
    try:
        systemic = ((regime.get("conditions") or {}).get("systemic_stress") or {})
        if not isinstance(systemic, Mapping):
            systemic = {}
    except Exception:
        systemic = {}

    def artifact_spread(key: str, family: str, *, stress_key: str | None = None) -> dict[str, Any]:
        if key not in systemic:
            return {
                "status": "unavailable", "value_bp": None, "unit": "basis_points",
                "artifact_as_of": regime_as_of, "source_family": family,
                **({"stress_state": None} if stress_key else {}),
            }
        value = _finite(systemic.get(key))
        status = "available" if value is not None else "invalid"
        out = {
            "status": status,
            "value_bp": value if status == "available" else None,
            "unit": "basis_points",
            "artifact_as_of": regime_as_of,
            "source_family": family,
        }
        if stress_key:
            state = systemic.get(stress_key)
            out["stress_state"] = state if isinstance(state, str) and state else None
        return out

    a2p2 = artifact_spread("a2p2_spread_bps", "regime_systemic_stress")
    cp_bill = artifact_spread(
        "cp_bill_spread_bps", "regime_systemic_stress", stress_key="cp_stress",
    )

    return {
        "ofr_fsi": ofr,
        "ofr_funding": ofr_funding,
        "sofr_iorb": corridor,
        "a2p2_spread": a2p2,
        "cp_bill_spread": cp_bill,
        "direct_usd_xccy_basis": {
            "status": "unavailable", "reason": "not_collected",
            "source_family": "direct_usd_xccy_basis",
        },
    }


def _pair_rows(pairs: object) -> list[dict[str, Any]]:
    if not isinstance(pairs, Sequence) or isinstance(pairs, (str, bytes)):
        return []
    candidates = [p for p in pairs if isinstance(p, Mapping) and isinstance(p.get("key"), str)]
    counts = Counter(p["key"] for p in candidates)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    allowed_pos = {"crowded_long", "crowded_short", "neutral"}
    for pair in candidates:
        key = pair["key"]
        if key in seen:
            continue
        seen.add(key)
        conflict = counts[key] != 1
        context_only = pair.get("carry_context") is True
        carry = _measure(pair.get("carry_diff"), "percentage_points_annualized",
                         unavailable=context_only or conflict)
        ctv = _measure(pair.get("carry_to_vol"), "ratio",
                       unavailable=context_only or conflict)
        rate10 = _measure(pair.get("rate_diff_10y"), "percentage_points",
                          unavailable=conflict)
        pos = _measure(pair.get("pos_pctile"), "percentile_rank_0_100", lo=0, hi=100,
                       unavailable=conflict)
        state = pair.get("pos_state") if pair.get("pos_state") in allowed_pos else None
        positioning = {**pos, "state": state if pos["status"] == "available" else None}
        out.append({
            "pair": key, "label": pair.get("label") or key, "base": pair.get("base"),
            "identity_status": "conflict" if conflict else "ok",
            "carry_context_only": context_only,
            "carry_diff": carry, "carry_to_vol": ctv, "rate_diff_10y": rate10,
            "positioning": positioning,
            "source_freshness": "unknown",
            "calculation_date": None,
        })
    return out


def _receipt(prob: object) -> dict[str, Any]:
    base = {"status": "unavailable", "headline_frequency": None,
            "semantics": "past_conditional_frequency_not_forecast"}
    if not isinstance(prob, Mapping):
        return base
    status = prob.get("status")
    if status == "insufficient":
        return {**base, "status": "insufficient",
                "semantics": "insufficient_sample_not_forecast"}
    if status != "ok":
        return base
    vals = {k: _finite(prob.get(k)) for k in ("p_cond", "base_rate")}
    n_raw, horizon = prob.get("n_raw"), prob.get("N")
    valid_prob = all(vals[k] is not None and 0 <= vals[k] <= 1
                     for k in ("p_cond", "base_rate"))
    valid_n = (not isinstance(n_raw, bool) and isinstance(n_raw, int) and n_raw > 0
               and not isinstance(horizon, bool) and isinstance(horizon, int) and horizon > 0)
    if not valid_prob or not valid_n:
        return base
    return {
        "status": "ok", "headline_frequency": vals["p_cond"],
        "conditional_frequency": vals["p_cond"], "base_rate": vals["base_rate"],
        "n_raw": n_raw, "horizon_sessions": horizon,
        "uncertainty": {
            "status": "withheld_unqualified",
            "method": "legacy_n_raw_over_horizon_wilson",
            "reason": "dependence_adjustment_not_qualified",
        },
        "semantics": "past_conditional_frequency_not_forecast",
    }

def _carry_unwind(regime: object) -> dict[str, Any]:
    base = {
        "state": "unknown", "active": None, "intensity": None,
        "n_fired": None, "min_legs": None, "legs": [],
        "historical_receipt": _receipt(None),
    }
    if not isinstance(regime, Mapping):
        return base
    scenarios = regime.get("scenarios")
    if not isinstance(scenarios, list):
        return base
    matches = [s for s in scenarios if isinstance(s, Mapping) and s.get("key") == "carry_unwind"]
    if len(matches) != 1:
        return base
    s = matches[0]
    active, intensity = s.get("active"), _finite(s.get("intensity_today"))
    nf, ml = s.get("n_fired"), s.get("min_legs")
    counts_ok = (not isinstance(nf, bool) and isinstance(nf, int) and nf >= 0
                 and not isinstance(ml, bool) and isinstance(ml, int) and ml > 0)
    active_ok = isinstance(active, bool)
    intensity_ok = intensity is not None and 0 <= intensity <= 100
    state = "unknown"
    if active_ok and counts_ok and intensity_ok and active == (nf >= ml):
        state = "active" if active else "inactive"

    legs = []
    raw_legs = s.get("fired_legs")
    legs_integrity = isinstance(raw_legs, list)
    seen_leg_ids: set[str] = set()
    fired_count = 0
    if isinstance(raw_legs, list):
        for leg in raw_legs:
            if not isinstance(leg, Mapping) or not isinstance(leg.get("id"), str):
                legs_integrity = False
                continue
            leg_id = leg["id"]
            if leg_id in seen_leg_ids:
                legs_integrity = False
                continue
            seen_leg_ids.add(leg_id)
            absent_raw, fired_raw = leg.get("absent"), leg.get("fired")
            if not isinstance(absent_raw, bool) or not isinstance(fired_raw, bool):
                legs_integrity = False
            absent = absent_raw is True
            fired = fired_raw if isinstance(fired_raw, bool) else None
            value = _finite(leg.get("value"))
            status = "unavailable" if absent else ("available" if value is not None else "invalid")
            if absent and fired is True:
                legs_integrity = False
            if not absent and status != "available":
                legs_integrity = False
            if status == "available" and fired is True:
                fired_count += 1
            legs.append({
                "id": leg_id, "kind": leg.get("kind"),
                "label_en": leg.get("en"), "label_zh": leg.get("zh"),
                "status": status, "fired": fired if status == "available" else False,
                "value": value if status == "available" else None,
            })
    if not counts_ok or not legs_integrity or fired_count != nf:
        state = "unknown"
    return {
        "state": state, "active": active if state != "unknown" else None,
        "intensity": intensity if intensity_ok else None,
        "n_fired": nf if counts_ok else None, "min_legs": ml if counts_ok else None,
        "legs": legs, "historical_receipt": _receipt(s.get("prob")),
        "as_of": regime.get("as_of"), "illustrative": bool(s.get("illustrative")),
        "discriminator_en": s.get("disc_en"), "discriminator_zh": s.get("disc_zh"),
    }


def _funding_view(funding: object) -> dict[str, Any]:
    source = funding if isinstance(funding, Mapping) else {}

    def raw_point(key: str, *, bp: bool = False) -> dict[str, Any]:
        item = source.get(key)
        unit = "basis_points" if bp else "index_level"
        if not isinstance(item, Mapping):
            return {"status": "unavailable", "value_bp" if bp else "value": None,
                    "calculated_through": None, "family": key}
        status = item.get("status") if item.get("status") in {"available", "unavailable", "invalid"} else "invalid"
        field = "value_bp" if bp else "value"
        val = _finite(item.get(field)) if status == "available" else None
        if status == "available" and val is None:
            status = "invalid"
        out = {"status": status, field: val if status == "available" else None,
               "calculated_through": _date(item.get("calculated_through")),
               "family": item.get("source_family") or key, "unit": unit}
        if isinstance(item.get("artifact_built"), str):
            out["artifact_built"] = item.get("artifact_built")
        if item.get("artifact_as_of") is not None:
            out["artifact_as_of"] = _date(item.get("artifact_as_of"))
        if isinstance(item.get("stress_state"), str):
            out["stress_state"] = item.get("stress_state")
        if bp:
            out["hot"] = item.get("hot") if isinstance(item.get("hot"), bool) else None
            out["last5_all_positive"] = item.get("last5_all_positive") if isinstance(item.get("last5_all_positive"), bool) else None
            out["threshold"] = item.get("threshold")
            out["caveat"] = item.get("caveat")
        return out

    ofr = raw_point("ofr_fsi")
    off = raw_point("ofr_funding")
    corridor = raw_point("sofr_iorb", bp=True)
    a2p2 = raw_point("a2p2_spread", bp=True)
    cp_bill = raw_point("cp_bill_spread", bp=True)
    direct = source.get("direct_usd_xccy_basis")
    direct_view = {
        "status": "unavailable", "reason": "not_collected",
        "family": "direct_usd_xccy_basis",
    }
    if isinstance(direct, Mapping) and direct.get("status") == "unavailable":
        direct_view["reason"] = direct.get("reason") or "not_collected"

    observed = sum(x["status"] == "available" for x in (ofr, off, corridor, a2p2, cp_bill))
    return {
        "state": "partial" if observed < 5 or direct_view["status"] != "available" else "complete",
        "ofr_fsi": ofr, "ofr_funding": off, "sofr_iorb": corridor,
        "a2p2_spread": a2p2, "cp_bill_spread": cp_bill,
        "direct_usd_xccy_basis": direct_view,
        "ofr_family_independent_votes": False,
        "funding_interpretation": "proxy_context_only",
        "source_freshness": "unknown",
    }


def project_carry_funding(pairs: object, regime: object, funding: object) -> dict[str, Any]:
    """Project existing evidence without creating a new carry/funding diagnosis."""
    return {
        "version": 1,
        "display_only": True,
        "semantics": "evidence_projection_not_trade_or_forecast",
        "rate_edges": _pair_rows(pairs),
        "carry_unwind": _carry_unwind(regime),
        "funding": _funding_view(funding),
        "limitations": [
            "no_composite_score",
            "canonical_carry_unwind_state_not_recomputed",
            "pair_source_freshness_unknown",
            "ofr_total_and_funding_are_related_not_independent_votes",
            "funding_proxies_do_not_prove_direct_fx_swap_basis_normal",
            "direct_usd_cross_currency_basis_unavailable",
        ],
    }
