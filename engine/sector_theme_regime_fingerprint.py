"""Read-only multi-horizon regime fingerprint over owned sector_theme_factor_frame/v1.

This module adds NO new regime classifier, source, history writer, scorer,
probability, ranking, trading or alert authority. It only projects observed
quantities and explicit gaps from an incumbent, already-computed factor frame.
Everything output remains UNQUALIFIED for customer use until its owner adapter
verifies source, timing, rights, PIT and population. No wall clock or I/O.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
import math
from statistics import median

SCHEMA = "sector_theme_regime_fingerprint/v1"
INPUT_SCHEMA = "sector_theme_factor_frame/v1"
AXES = (
    "absolute_trend", "rs_market", "rs_parent", "rs_velocity_acceleration",
    "participation", "breadth_velocity_acceleration",
    "concentration_dispersion", "multiscale_coherence",
    "extension_maturity", "vol_liquidity", "cross_asset_credit",
    "evidence_quality",
)
DEFERRALS = {
    "rs_velocity_acceleration": "requires_dated_serial_relative_wealth_slopes",
    "extension_maturity": "requires_qualified_past_known_run_history",
    "vol_liquidity": "requires_entitled_tape_volatility_liquidity_inputs",
    "cross_asset_credit": "requires_owner_qualified_cross_asset_and_credit_vintages",
}


def _number(v: object) -> float | None:
    # bool is not a value; infinity/nan never participate in comparisons.
    if type(v) not in (int, float):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError, OverflowError):
        return None
    return n if math.isfinite(n) else None


def _unmeasured(reason: str) -> dict:
    return {"status": "unmeasured", "reason": reason}


def _measured(value: object, unit: str = "fraction") -> dict:
    n = _number(value)
    return ({"status": "measured", "value": n, "unit": unit}
            if n is not None else _unmeasured("missing_or_invalid_measurement"))


def _value(raw: object) -> float | None:
    if not isinstance(raw, Mapping) or raw.get("status") != "measured":
        return None
    return _number(raw.get("value"))


def _numeric(raw: object) -> dict:
    if not isinstance(raw, Mapping):
        return _unmeasured("missing_input")
    n = _value(raw)
    return (_measured(n, str(raw.get("unit") or "fraction"))
            if n is not None else _unmeasured(str(raw.get("reason") or "unmeasured_input")))


def _bounds(raw: object) -> tuple[float, float] | None:
    if not isinstance(raw, Mapping) or (
        raw.get("bounds_kind") != "identification_bounds_not_confidence_interval"
    ):
        return None
    b = raw.get("bounds")
    if not isinstance(b, (list, tuple)) or len(b) != 2:
        return None
    lo, hi = _number(b[0]), _number(b[1])
    if lo is None or hi is None or not 0 <= lo <= hi <= 1:
        return None
    return lo, hi


def _breadth(raw: object) -> dict:
    b = _bounds(raw)
    if b is None or not isinstance(raw, Mapping):
        return _unmeasured("invalid_or_missing_identification_bounds")
    coverage = _number(raw.get("coverage"))
    if coverage is None or not 0 <= coverage <= 1:
        return _unmeasured("invalid_coverage")
    ko = raw.get("k_over_n")
    ratio = _number(ko) if not isinstance(ko, Mapping) else None
    if ratio is not None and not 0 <= ratio <= 1:
        return _unmeasured("invalid_k_over_n")
    if ratio is None and coverage > 0:
        return _unmeasured("invalid_k_over_n")
    return {
        "status": "measured" if ratio is not None else "unmeasured",
        "value": ratio,
        "coverage": coverage,
        "identification_bounds": [b[0], b[1]],
        "bounds_kind": "identification_bounds_not_confidence_interval",
        **({"reason": "no_measured_members"} if ratio is None else {}),
    }


def _date(raw: object, label: str) -> datetime:
    if not isinstance(raw, str):
        raise ValueError(f"{label} must be an aware timestamp")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        raise ValueError(f"{label} must be an aware timestamp") from None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be an aware timestamp")
    return value


def _validate_frames(frames: Mapping[str, Mapping]) -> tuple[list[str], dict]:
    if not isinstance(frames, Mapping) or not frames:
        raise ValueError("at least one source frame is required")
    first = None
    contract = None
    for horizon, frame in frames.items():
        if not isinstance(horizon, str) or not horizon or not isinstance(frame, Mapping):
            raise ValueError("invalid horizon/frame")
        if frame.get("schema") != INPUT_SCHEMA:
            raise ValueError("not an owned factor-frame schema")
        group, clock = frame.get("group"), frame.get("clock")
        universe, evidence, authority = (
            frame.get("universe"), frame.get("evidence"), frame.get("authority")
        )
        if not all(isinstance(v, Mapping) for v in (
            group, clock, universe, evidence, authority,
            frame.get("measures"), frame.get("constituents"),
        )):
            raise ValueError("missing required factor-frame structure")
        if clock.get("horizon") != horizon:
            raise ValueError("mixed or mislabeled horizons")
        if authority.get("display_only") is not True or (
            authority.get("predictive_promoted") is not False
            or authority.get("eligible_for_customer_publication") is not False
            or authority.get("ranking_authority") is not False
        ):
            raise ValueError("unqualified frame requests scoring or publication")
        ids = universe.get("member_ids")
        if not isinstance(ids, list) or any(type(i) is not str or not i for i in ids):
            raise ValueError("missing canonical member population")
        if len(ids) != len(set(ids)) or ids != sorted(ids):
            raise ValueError("duplicate or unstable constituent population")
        if type(universe.get("expected_n")) is not int or (
            universe["expected_n"] != len(ids)
        ):
            raise ValueError("denominator disagrees with member population")
        end = _date(clock.get("period_end"), "period_end")
        decision = _date(clock.get("decision_at"), "decision_at")
        member_known = _date(clock.get("membership_known_at"), "membership_known_at")
        if end > decision or member_known > decision:
            raise ValueError("future endpoint or membership")
        if group.get("membership_mode") == "PIT_AS_KNOWN" and member_known > end:
            raise ValueError("post-endpoint membership cannot be point-in-time")
        if evidence.get("source_rights_verified") is not False or (
            evidence.get("original_known_at_receipts_verified") is not False
        ):
            # The source P1 contract explicitly has not performed these checks.
            raise ValueError("source projection cannot assert owner qualification")
        identity = (
            group.get("group_id"), group.get("cohort_id"),
            group.get("membership_revision"), group.get("membership_mode"),
            tuple(ids), clock.get("decision_at"),
        )
        if first is None:
            first = identity
            contract = {
                "group_id": identity[0], "cohort_id": identity[1],
                "membership_revision": identity[2],
                "membership_mode": identity[3],
                "member_ids": list(ids), "decision_at": clock["decision_at"],
            }
        elif first != identity:
            raise ValueError("incompatible group, vintage, member IDs or decision clock")
    return sorted(frames), contract


def _median_and_gap(frame: Mapping) -> dict:
    members = frame["universe"]["member_ids"]
    states = frame["constituents"]
    nums = []
    for mid in members:
        row = states.get(mid)
        if not isinstance(row, Mapping):
            break
        ret = _value(row.get("return_frac"))
        if ret is None:
            break
        nums.append(ret)
    full_median = (
        _measured(median(nums)) if members and len(nums) == len(members)
        else _unmeasured("incomplete_full_cohort_returns")
    )
    m = frame["measures"]
    equal_weight = _numeric(m.get("equal_weight_full_cohort_return"))
    weighted = _numeric(m.get("lagged_weight_full_cohort_return"))
    ew_v, w_v = _value(equal_weight), _value(weighted)
    return {
        "full_cohort_median_return": full_median,
        "full_cohort_equal_weight_return": equal_weight,
        "full_cohort_lagged_weight_return": weighted,
        "weighted_minus_equal_return": (
            _measured(w_v - ew_v) if w_v is not None and ew_v is not None
            else _unmeasured("incomplete_group_return_or_lagged_weights")
        ),
        "issuer_hhi": _unmeasured("needs_qualified_lagged_issuer_weights"),
    }


def _change(frame: Mapping) -> dict:
    t = frame.get("transitions")
    if not isinstance(t, Mapping) or t.get("status") != "measured_with_endpoint_coverage":
        return {"same_member_uptrend_first_difference":
                    _unmeasured("no_qualified_previous_endpoint"),
                "second_difference_acceleration":
                    _unmeasured("requires_three_qualified_endpoints")}
    c = t.get("change")
    if not isinstance(c, Mapping):
        return {"same_member_uptrend_first_difference": _unmeasured("missing_transition"),
                "second_difference_acceleration":
                    _unmeasured("requires_three_qualified_endpoints")}
    before = c.get("common_cohort_before")
    after = c.get("common_cohort_after")
    n = c.get("common_known")
    bv = _breadth(before)
    av = _breadth(after)
    bval, aval = _value(bv), _value(av)
    diff = (_measured(aval - bval) if isinstance(n, list) and n
            and bval is not None and aval is not None
            else _unmeasured("no_common_measured_members"))
    return {"same_member_uptrend_first_difference": diff,
            "common_known_n": len(n) if isinstance(n, list) else 0,
            "new_coverage_positive_n": len(c.get("new_coverage_positive", [])),
            "new_coverage_negative_n": len(c.get("new_coverage_negative", [])),
            "composition_only": c.get("composition_only") is True,
            "second_difference_acceleration":
                _unmeasured("requires_three_qualified_endpoints")}


def _sign(v: float) -> int:
    return 1 if v > 0 else -1 if v < 0 else 0


def compose_regime_fingerprint(frames: Mapping[str, Mapping]) -> dict:
    """Project 12 descriptive axes, overlapping evidence-backed facets, no forecasts.

    Input frames must represent the exact same known cohort and decision instant.
    Different horizon period endpoints are permitted and always retained per
    horizon; their numeric return magnitudes are NEVER averaged across horizons.
    """
    horizons, contract = _validate_frames(frames)
    per = {}
    facets: list[dict] = []
    sign_parent: set[int] = set()
    for h in horizons:
        frame = frames[h]
        m = frame["measures"]
        abs_return = _numeric(m.get("equal_weight_full_cohort_return"))
        rs_market = _numeric(m.get("group_rs_market"))
        rs_parent = _numeric(m.get("group_rs_parent"))
        breadth = {
            key: _breadth(m.get(key))
            for key in ("positive_return_breadth", "positive_rs_market_breadth",
                        "positive_rs_parent_breadth", "above_ma50_breadth",
                        "above_ma200_breadth", "uptrend_breadth", "downtrend_breadth")
        }
        change = _change(frame)
        disp = _median_and_gap(frame)
        per[h] = {
            "period_end": frame["clock"]["period_end"],
            "evidence_mode": frame["evidence"].get("mode"),
            "absolute_trend": {"group_return": abs_return,
                               "uptrend_breadth": breadth["uptrend_breadth"],
                               "downtrend_breadth": breadth["downtrend_breadth"]},
            "rs_market": rs_market,
            "rs_parent": rs_parent,
            "participation": breadth,
            "breadth_velocity_acceleration": change,
            "concentration_dispersion": disp,
            "source_membership_n": frame["universe"]["expected_n"],
            "missing_by_reason": deepcopy(
                frame["universe"].get("missing_by_reason", {})),
        }
        r = _value(rs_parent)
        a = _value(abs_return)
        s = _value(rs_market)
        d = _value(change["same_member_uptrend_first_difference"])
        if r is not None and r != 0:
            sign_parent.add(_sign(r))
        if r is not None and r > 0 and d is not None and d < 0:
            facets.append({"id": "positive_parent_rs_narrowing_same_member_breadth",
                           "horizon": h, "evidence": ["rs_parent",
                           "breadth_velocity_acceleration.same_member_uptrend_first_difference"]})
        if r is not None and r < 0 and d is not None and d > 0:
            facets.append({"id": "negative_parent_rs_internal_repair",
                           "horizon": h, "evidence": ["rs_parent",
                           "breadth_velocity_acceleration.same_member_uptrend_first_difference"]})
        if a is not None and a < 0 and s is not None and s > 0:
            facets.append({"id": "positive_market_rs_with_negative_absolute_return",
                           "horizon": h, "evidence": ["absolute_trend.group_return",
                                                   "rs_market"]})
        if change.get("composition_only") is True:
            facets.append({"id": "apparent_broadening_from_composition_only",
                           "horizon": h, "evidence": ["breadth_velocity_acceleration"]})
        positive_bounds = breadth["positive_return_breadth"].get("identification_bounds")
        if positive_bounds is not None:
            lo, hi = positive_bounds
            if lo > .5:
                facets.append({"id": "majority_positive_participation_proven_by_bounds",
                               "horizon": h,
                               "evidence": ["participation.positive_return_breadth"]})
            elif hi < .5:
                facets.append({"id": "majority_negative_participation_proven_by_bounds",
                               "horizon": h,
                               "evidence": ["participation.positive_return_breadth"]})
                if a is not None and a > 0:
                    facets.append({"id": "positive_group_return_but_majority_negative",
                                   "horizon": h,
                                   "evidence": ["absolute_trend.group_return",
                                   "participation.positive_return_breadth"]})
    if 1 in sign_parent and -1 in sign_parent:
        facets.append({"id": "cross_horizon_parent_rs_sign_conflict",
                       "horizon": "multi", "evidence": ["rs_parent"]})
    signs = {h: _sign(_value(per[h]["rs_parent"]))
             for h in horizons if _value(per[h]["rs_parent"]) is not None}
    coherence = ({"status": "measured", "signs_by_horizon": signs,
                  "positive_n": sum(v > 0 for v in signs.values()),
                  "negative_n": sum(v < 0 for v in signs.values()),
                  "neutral_n": sum(v == 0 for v in signs.values()),
                  "interpretation": ("mixed" if 1 in signs.values() and -1 in signs.values()
                                     else "same_sign_or_neutral")}
                 if len(signs) >= 2 else _unmeasured("fewer_than_two_qualified_rs_horizons"))
    axes = {axis: (
        {"status": "not_yet_computed", "reason": DEFERRALS[axis]} if axis in DEFERRALS
        else {"status": "measured_descriptive_view_only"}
    ) for axis in AXES}
    axes["multiscale_coherence"] = coherence
    axes["breadth_velocity_acceleration"] = {
        "status": "first_difference_only",
        "reason": "three_endpoint_acceleration_not_available",
    }
    axes["concentration_dispersion"] = {
        "status": "partial_measured_only",
        "reason": "no_canonical_issuer_concentration_weights_or_dispersion_quantiles",
    }
    axes["evidence_quality"] = {
        "status": "unqualified_source_projection",
        "source_rights_verified": False,
        "original_known_at_receipts_verified": False,
        "eligible_for_customer_publication": False,
        "membership_mode": contract["membership_mode"],
    }
    return {
        "schema": SCHEMA,
        "group": contract,
        "horizons": per,
        "axes": axes,
        "facets": facets,
        "authority": {
            "display_only": True, "predictive_promoted": False,
            "ranking_authority": False, "alert_authority": False,
            "entry_or_sizing_authority": False,
            "eligible_for_customer_publication": False,
        },
        "limits": {
            "numeric_state_score": "absent",
            "forecast_probabilities": "absent",
            "macro_regime_authority": "incumbent_only",
            "true_subtheme_membership": "requires_independent_GMI_qualification",
            "bounds_not_confidence_intervals": True,
        },
    }
