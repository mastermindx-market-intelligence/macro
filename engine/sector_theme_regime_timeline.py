"""Pure as-issued multi-session regime chronology over existing P2 research previews.

NO history writer, event broadcaster, model fit, trade, alert, data store, network
or customer publication. Input snapshots must be retained upstream by the
existing owner. We never infer original knowledge from caller-supplied dates.

Separates:
- true common-measured member flips (existing breadth_change contract),
- changed coverage/roster,
- bounded aggregate breadth differences that remain uncertain,
- rolling-window RS level changes, which are NOT momentum acceleration.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import math

from engine.leadership_rotation_context import breadth_change

SCHEMA = "sector_theme_regime_timeline/v1"
INPUT_SCHEMA = "sector_theme_owner_preview/v1"
WINDOW = ("market", "benchmark_id", "price_basis", "session_basis", "horizon")


def _hold(reason: str) -> dict:
    return {
        "schema": SCHEMA, "status": "HELD", "reason": reason,
        "observations": [], "changes": [],
        "customer_publication": False, "forecast_authority": False,
        "ranking_or_trading_authority": False,
    }


def _time(raw: object) -> datetime | None:
    if type(raw) is not str:
        return None
    try:
        val = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if val.utcoffset() is None:
            return None
        return val.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _num(raw: object) -> float | None:
    if not isinstance(raw, Mapping) or (
        raw.get("status") != "measured" or raw.get("unit") != "fraction"
    ):
        return None
    val = raw.get("value")
    if type(val) not in (int, float):
        return None
    try:
        n = float(val)
    except (TypeError, ValueError, OverflowError):
        return None
    return n if math.isfinite(n) else None


def _breadth_bounds(raw: object) -> tuple[float, float] | None:
    if (not isinstance(raw, Mapping)
            or raw.get("bounds_kind") != "identification_bounds_not_confidence_interval"):
        return None
    b, c = raw.get("identification_bounds"), raw.get("coverage")
    if (not isinstance(b, (list, tuple)) or len(b) != 2
            or any(type(x) not in (int, float) for x in b)
            or type(c) not in (int, float)):
        return None
    try:
        lo, hi, coverage = (float(b[0]), float(b[1]), float(c))
    except (TypeError, ValueError, OverflowError):
        return None
    if (not all(math.isfinite(x) for x in (lo, hi, coverage))
            or not 0 <= lo <= hi <= 1 or not 0 <= coverage <= 1):
        return None
    value = raw.get("value")
    if raw.get("status") == "measured":
        if type(value) not in (int, float):
            return None
        try:
            k = float(value)
        except (ValueError, OverflowError):
            return None
        if (not math.isfinite(k) or not 0 <= k <= 1
                or abs(coverage * k - lo) > 1e-9
                or abs(hi - lo - (1 - coverage)) > 1e-9):
            return None
    elif raw.get("status") == "unmeasured":
        if (abs(coverage) > 1e-9 or abs(lo) > 1e-9 or
                abs(hi - 1.0) > 1e-9):
            return None
    else:
        return None
    return lo, hi


def _bool_state(row: Mapping, metric: str) -> bool | None:
    if metric == "positive_return":
        raw = row.get("return_frac")
        v = _num(raw)
        return None if v is None else v > 0
    if metric == "uptrend":
        value = row.get("trend")
        return None if value not in ("up", "down", "mixed") else value == "up"
    raise ValueError("unknown metric")


def _copy_change_summary(change: Mapping) -> dict:
    # The underlying native incumbent emits full ticker lists; keep
    # exact identity but never call end-to-end changes an intrabar event trace.
    keys = (
        "common_known", "newly_positive_common", "newly_negative_common",
        "new_coverage_positive", "new_coverage_negative", "lost_coverage",
        "entrants", "exits",
    )
    return {
        "same_cohort_rule": "paired common measured securities only",
        "endpoint_only_not_intrawindow_crossing_history": True,
        **{key: list(change.get(key, [])) for key in keys},
        "composition_only": change.get("composition_only") is True,
    }


def _aggregate_delta(before: object, after: object) -> dict:
    lohi1, lohi2 = _breadth_bounds(before), _breadth_bounds(after)
    if lohi1 is None or lohi2 is None:
        return {"status": "unmeasured", "reason": "invalid_or_missing_breadth_bounds"}
    # These are identification bounds, NOT statistical confidence intervals.
    low = max(-1.0, lohi2[0] - lohi1[1])
    high = min(1.0, lohi2[1] - lohi1[0])
    trend = (
        "broadening_proven" if low > 0
        else "narrowing_proven" if high < 0
        else "direction_not_identified"
    )
    return {
        "status": "bounded", "delta_identification_bounds": [low, high],
        "bounds_kind": "logical_identification_not_confidence_interval",
        "direction": trend,
        "units": "fraction_points",
        "interpretation": "change_in_endpoint_population_breadth_not_acceleration",
    }


def compose_regime_timeline(previews: Sequence[Mapping]) -> dict:
    """Chronological, same-group, same-benchmark research-only chronology.

    Requires at least two as-issued source-preview records. No interpolation,
    revision replay, output persistence or forward outcome access occurs.
    """
    if isinstance(previews, (str, bytes)) or not isinstance(previews, Sequence) or (
        len(previews) < 2
    ):
        return _hold("need_two_source_previews")
    first_basis = None
    first_group = None
    accepted = []
    last_cutoff = last_end = None
    for row in previews:
        if (not isinstance(row, Mapping) or row.get("schema") != INPUT_SCHEMA
                or row.get("status") != "RESEARCH_PREVIEW_ONLY"
                or any(row.get(k) is not False for k in (
                    "eligible_for_customer_publication",
                    "eligible_for_historical_prediction", "trading_or_alert_authority"
                ))):
            return _hold("unqualified_or_modified_source_preview")
        basis, fp, frame = (
            row.get("comparison_basis"), row.get("fingerprint"), row.get("frame")
        )
        if (not isinstance(basis, Mapping) or not isinstance(fp, Mapping)
                or not isinstance(frame, Mapping)
                or fp.get("schema") != "sector_theme_regime_fingerprint/v1"):
            return _hold("missing_comparable_source_frames")
        group = fp.get("group")
        if not isinstance(group, Mapping) or not isinstance(frame.get("group"), Mapping):
            return _hold("missing_source_group")
        if (group.get("group_id") != frame["group"].get("group_id")
                or group.get("cohort_id") != frame["group"].get("cohort_id")
                or group.get("membership_revision")
                != frame["group"].get("membership_revision")
                or frame["group"].get("membership_mode") != row.get("basis")
                or group.get("membership_mode") != row.get("basis")):
            return _hold("group_or_mode_mismatch")
        cur_basis = tuple(basis.get(k) for k in WINDOW)
        if any(type(v) is not str or not v for v in cur_basis):
            return _hold("unknown_benchmark_or_session_basis")
        gid = group["group_id"]
        if first_basis is None:
            first_basis, first_group = cur_basis, gid
        elif first_basis != cur_basis or first_group != gid:
            return _hold("different_group_or_incompatible_basis")
        cutoff, end, start = (
            _time(basis.get("decision_at")), _time(basis.get("period_end")),
            _time(basis.get("period_start")),
        )
        if cutoff is None or end is None or start is None or not start < end <= cutoff:
            return _hold("invalid_source_clock")
        if (last_cutoff is not None
                and (cutoff <= last_cutoff or end <= last_end)):
            return _hold("nonmonotonic_source_snapshot_order")
        if (not isinstance(fp.get("horizons"), Mapping)
                or set(fp["horizons"]) != {basis["horizon"]}
                or not isinstance(fp["horizons"][basis["horizon"]], Mapping)):
            return _hold("horizon_mismatch")
        at = fp["horizons"][basis["horizon"]]
        if (at.get("period_end") != end.isoformat()
                or not isinstance(frame.get("clock"), Mapping)
                or frame["clock"].get("period_end") != end.isoformat()
                or frame["clock"].get("decision_at") != cutoff.isoformat()):
            return _hold("inconsistent_original_factor_clock")
        if not isinstance(frame.get("universe"), Mapping) or (
            not isinstance(frame.get("constituents"), Mapping)
        ):
            return _hold("missing_constituent_observation")
        members = frame["universe"].get("member_ids")
        if (not isinstance(members, list) or any(type(mid) is not str or not mid for mid in members)
                or len(members) != len(set(members))
                or frame["universe"].get("expected_n") != len(members)):
            return _hold("invalid_source_population")
        if not isinstance(at.get("participation"), Mapping):
            return _hold("missing_participation")
        if not isinstance(fp.get("authority"), Mapping) or any(
            fp["authority"].get(k) is not False for k in (
                "eligible_for_customer_publication", "predictive_promoted",
                "ranking_authority", "alert_authority", "entry_or_sizing_authority"
            )
        ):
            return _hold("fingerprint_claims_authority")
        last_cutoff, last_end = cutoff, end
        accepted.append((row, basis, fp, frame, at, members))
    records = []
    for row, basis, fp, frame, at, members in accepted:
        observations = {
            "decision_at": basis["decision_at"],
            "period_start": basis["period_start"],
            "period_end": basis["period_end"],
            "horizon": basis["horizon"],
            "cohort_id": fp["group"]["cohort_id"],
            "membership_revision": fp["group"]["membership_revision"],
            "membership_basis": row["basis"],
            "population_security_n": len(members),
            "unique_issuer_n": row.get("unique_issuer_n"),
            "measured_return_n": frame["universe"].get("measured_return_n"),
            "rs_market": _num(at.get("rs_market")),
            "rs_parent": _num(at.get("rs_parent")),
            "positive_return_breadth": _breadth_bounds(
                at["participation"].get("positive_return_breadth")),
            "uptrend_breadth": _breadth_bounds(
                at["participation"].get("uptrend_breadth")),
            "source_evidence_mode": frame.get("evidence", {}).get("mode"),
        }
        records.append(observations)
    changes = []
    for i in range(1, len(accepted)):
        prior, cur = accepted[i-1], accepted[i]
        bframe, aframe = prior[3], cur[3]
        bfp, afp = prior[2], cur[2]
        bmembers, amembers = prior[5], cur[5]
        same_group_population = (
            bmembers == amembers and
            bfp["group"].get("cohort_id") == afp["group"].get("cohort_id") and
            bfp["group"].get("membership_revision") == afp["group"].get("membership_revision") and
            prior[0].get("basis") == cur[0].get("basis")
        )
        change = {
            "from_decision_at": prior[1]["decision_at"],
            "to_decision_at": cur[1]["decision_at"],
            "stable_population": same_group_population,
            "rolling_window_rs_level_change_not_acceleration": {
                "status": "unmeasured",
                "reason": "roster_or_membership_revision_changed",
            },
            "aggregate_positive_breadth_delta": {
                "status": "unmeasured",
                "reason": "roster_or_membership_revision_changed",
            },
            "paired_member_positive_return": {
                "status": "unmeasured",
                "reason": "roster_or_membership_revision_changed",
            },
            "paired_member_uptrend": {
                "status": "unmeasured",
                "reason": "roster_or_membership_revision_changed",
            },
        }
        if same_group_population:
            b_at, a_at = prior[4], cur[4]
            before = _num(b_at.get("rs_market"))
            after = _num(a_at.get("rs_market"))
            change["rolling_window_rs_level_change_not_acceleration"] = (
                {"status": "measured", "value": after - before, "unit": "fraction"}
                if before is not None and after is not None
                else {"status": "unmeasured", "reason": "incomplete_rs_history"}
            )
            change["aggregate_positive_breadth_delta"] = _aggregate_delta(
                b_at["participation"].get("positive_return_breadth"),
                a_at["participation"].get("positive_return_breadth")
            )
            for metric, name in (
                ("positive_return", "paired_member_positive_return"),
                ("uptrend", "paired_member_uptrend"),
            ):
                prior_states, after_states = (
                    bframe["constituents"], aframe["constituents"]
                )
                before_states = {
                    member: _bool_state(prior_states.get(member) or {}, metric)
                    for member in bmembers
                }
                after_states = {
                    member: _bool_state(after_states.get(member) or {}, metric)
                    for member in amembers
                }
                paired = breadth_change(before_states, after_states)
                change[name] = {
                    "status": "measured_endpoint_pair_not_intrawindow_event_log",
                    **_copy_change_summary(paired),
                }
        changes.append(change)
    return {
        "schema": SCHEMA, "status": "RESEARCH_PREVIEW_ONLY",
        "group_id": first_group,
        "comparison_market_benchmark": first_basis[1],
        "time_basis": {
            "market": first_basis[0], "benchmark_id": first_basis[1],
            "price_basis": first_basis[2], "session_basis": first_basis[3],
            "horizon": first_basis[4],
        },
        "observations": records, "changes": changes,
        "original_issued_snapshots_authenticated": False,
        "no_interpolation_or_outcome_access_in_this_composer": True,
        "absence_of_upstream_lookahead_proven": False,
        "customer_publication": False, "forecast_authority": False,
        "ranking_or_trading_authority": False,
    }
