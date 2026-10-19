"""LR-W6 V3 candidates: synthetic-only H1 timing, H2 control, H3 contrast.

This is NOT the V3 pre-registration, a P0 size/power simulator, a P1/P2/P3
reader, or a market-data consumer. All inputs are caller-supplied synthetic
P0 phases, alarm indices or information-date records with NO forward outcomes.
H1 reuses the frozen T11 episode classifier and its matching/burden definitions.
H2 tests eligibility of prior B1 controls without constructing a return label.
H3 tests source-dated paired contrast arithmetic on caller-labelled P0 outcomes,
never inferential claims or the original real-data P1/P2/P3 source.

Research contract:
  research/LEADERSHIP_ROTATION_V3_CANDIDATE_2026-10-18.md §2/§6

No future-price outcomes, V3 pass/claim decision, release gate or cache here.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import fmean
from typing import Sequence

from scripts import leadership_rotation_episodes as ep

__all__ = ["candidate_h1_synthetic_comparison", "SyntheticPriorControl", "candidate_h2_prior_control_match", "SyntheticH3Event", "candidate_h3_synthetic_interaction", "candidate_v3_p0_pair_diagnostic"]

MATCH_WINDOW = 40
MISS_DELAY = MATCH_WINDOW + 1
MARGIN_EARLIER = 5.0


def candidate_h1_synthetic_comparison(
    phases: Sequence[ep.UpPhase],
    a1_alarms: Sequence[int],
    b2_alarms: Sequence[int],
    *,
    measured_sessions: int,
) -> dict:
    """Compare independent A1 and B2 delays, miss-censored at 41 sessions.

    Caller must supply SYNTHETIC phase/alarm indices. Real-market readers are
    intentionally absent. Full statistical inference/power cannot be inferred
    from any single synthetic demonstration.

    Returns 'NOT_EXECUTABLE' for zero qualifying onsets; never gives a spurious
    zero-event timing pass. One-event/one-attempt and alarm burden are delegated
    to the incumbent episode classifier, not implemented anew.
    """
    if isinstance(measured_sessions, bool) or not isinstance(measured_sessions, int) or measured_sessions <= 0:
        raise ValueError("measured_sessions must be a positive integer")

    ordered = sorted((ph for ph in phases if ph.qualifies), key=lambda ph: ph.T)
    if len({ph.T for ph in ordered}) != len(ordered):
        raise ValueError("qualifying phase onsets must be unique")
    if any(ph.T < 0 or ph.P < ph.T + MATCH_WINDOW or ph.P >= measured_sessions for ph in ordered):
        raise ValueError("qualifying phases must be complete and within the synthetic calendar")

    for name, alarms in (("a1_alarms", a1_alarms), ("b2_alarms", b2_alarms)):
        if any(isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < measured_sessions for a in alarms):
            raise ValueError(f"{name} must contain integer indices inside the synthetic calendar")

    if not ordered:
        return {
            "scope": "P0_SYNTHETIC_ONLY",
            "status": "NOT_EXECUTABLE",
            "reason": "NO_QUALIFYING_ONSETS",
            "n_onsets": 0,
            "v3_preregistered": False,
            "size_or_power_proven": False,
            "h1_delay_advantage_sessions": None,
        }

    def arm_diagnostic(alarms: Sequence[int]) -> dict:
        # Freeze accepted T11/R3 matching precedence and within-pair merge.
        kept, merged = ep.merge_within_pair(alarms)
        classified = ep.classify_alarms(kept, ordered, window=MATCH_WINDOW)
        metrics = ep.episode_metrics(
            classified, ordered, measured_sessions,
            merged_away=len(merged),
        )
        first = {r["phase_T"]: r["delay"] for r in classified if r["cls"] == "MATCHED"}
        if len(first) != metrics["n_matched"]:
            raise ValueError("incumbent classifier produced duplicate matched onsets")
        delay = [int(first.get(ph.T, MISS_DELAY)) for ph in ordered]
        if any(d < 0 or d > MISS_DELAY for d in delay):
            raise ValueError("invalid synthetic match/censor delay")
        return {
            "onset_delays": delay,
            "mean_censor_aware_delay": fmean(delay),
            "n_detected": metrics["n_matched"],
            "n_missed": metrics["n_miss"],
            "detection_fraction": metrics["detection"],
            "unmatched_alarm_burden_per_pair_year": metrics["burden"],
            "n_repeated": metrics["n_repeated"],
            "n_late": metrics["n_late"],
            "n_false_start": metrics["n_false_start"],
            "n_merged_away": metrics["merged_away"],
        }

    a1 = arm_diagnostic(a1_alarms)
    b2 = arm_diagnostic(b2_alarms)
    advantage = fmean([b - a for a, b in zip(a1["onset_delays"], b2["onset_delays"])])
    return {
        "scope": "P0_SYNTHETIC_ONLY",
        "status": "DESCRIPTIVE",
        "n_onsets": len(ordered),
        "v3_preregistered": False,
        "size_or_power_proven": False,
        "margin_h1_earlier_sessions": MARGIN_EARLIER,
        "h1_delay_advantage_sessions": advantage,
        "candidate_delay_margin_met_only": advantage >= MARGIN_EARLIER,
        "a1": a1,
        "b2": b2,
    }


# Research-only structural anti-leakage control for a future H2-V3 P0 harness.
# It deliberately carries ZERO forward outcomes. The accepted P0 owner, not
# this helper, owns all price series, honest-N, exposure and inference.
@dataclass(frozen=True)
class SyntheticPriorControl:
    pair_id: str
    origin: int                  # NYSE synthetic calendar index (close t)
    volatility_quintile: int     # 0..4 computed using information at own origin
    feature_asof: int            # receipt: last date input for the quintile
    a1_active: bool              # frozen A1 hysteresis state at own origin
    warmup_sessions: int         # past sessions available before origin


def candidate_h2_prior_control_match(
    a1_event: SyntheticPriorControl,
    candidate_b1_dates: Sequence[SyntheticPriorControl],
) -> dict:
    """Select a past, matured B1 comparison origin using no future outcomes.

    Same registered pair, equal *own-date* past-volatility quintile, B1 day
    with A1 not active, and origin c within [t-63,t-21]. At c+20 < t the
    reference's future-20 outcome has matured, but it is NEVER passed to this
    selector and cannot influence tie-breaks. No comparison is powered or
    preregistered by the selection alone. All inputs are synthetic P0 caller
    objects, not market-data rows or durable events.
    """
    def validate(x: SyntheticPriorControl) -> None:
        if type(x) is not SyntheticPriorControl:
            raise TypeError("P0 event must be SyntheticPriorControl")
        if not isinstance(x.pair_id, str) or not x.pair_id.strip():
            raise ValueError("nonempty synthetic pair identity required")
        if any(type(v) is not int for v in (
            x.origin, x.volatility_quintile, x.feature_asof, x.warmup_sessions
        )):
            raise ValueError("synthetic calendar and quintile fields must be integers")
        if x.origin < 0 or x.warmup_sessions < 0 or x.warmup_sessions > x.origin:
            raise ValueError("synthetic warmup cannot exceed origin or be negative")
        if x.feature_asof < 0 or x.feature_asof > x.origin:
            raise ValueError("LOOKAHEAD_FEATURE_DATE")
        if x.volatility_quintile not in range(5):
            raise ValueError("volatility quintile must be 0..4")
        if type(x.a1_active) is not bool:
            raise ValueError("A1 active must be boolean")

    validate(a1_event)
    for candidate in candidate_b1_dates:
        validate(candidate)
    if not a1_event.a1_active:
        raise ValueError("A1 test origin must have A1 active")
    if a1_event.warmup_sessions < 252:
        return {
            "scope": "P0_SYNTHETIC_ONLY", "status": "NOT_EXECUTABLE",
            "reason": "A1_WARMUP_UNAVAILABLE", "control_t": None,
            "v3_preregistered": False, "size_or_power_proven": False,
        }

    # Qualified sources are selected on their own information date.
    matches = [
        c for c in candidate_b1_dates
        if c.pair_id == a1_event.pair_id
        and c.warmup_sessions >= 252
        and not c.a1_active
        and c.volatility_quintile == a1_event.volatility_quintile
        and 21 <= a1_event.origin - c.origin <= 63
    ]
    # Duplicate candidate origins mean source identity is ambiguous. This
    # check is applied to *eligible matches*, not unrelated date populations.
    if len({c.origin for c in matches}) != len(matches):
        raise ValueError("AMBIGUOUS_DUPLICATE_CONTROL")
    if not matches:
        return {
            "scope": "P0_SYNTHETIC_ONLY", "status": "UNMATCHED",
            "reason": "NO_PRIOR_COMPARABLE_CONTROL", "control_t": None,
            "v3_preregistered": False, "size_or_power_proven": False,
        }
    picked = max(matches, key=lambda c: c.origin)
    if picked.origin + 20 >= a1_event.origin:
        raise ValueError("FORWARD_OUTCOME_NOT_MATURED")
    return {
        "scope": "P0_SYNTHETIC_ONLY", "status": "MATCHED",
        "a1_t": a1_event.origin, "control_t": picked.origin,
        "control_age_sessions": a1_event.origin - picked.origin,
        "control_forward20_matured_before_a1": True,
        "v3_preregistered": False, "size_or_power_proven": False,
    }



@dataclass(frozen=True)
class SyntheticH3Event:
    """Caller-labelled P0 event; no real source reader or inferred trade."""

    pair_id: str
    origin: int
    arm: str                     # A1 original pair, B3 receiver-only reference
    donor_weak: bool              # past donor-relative-to-SPY classification
    receiver_spy_sign: int        # past -1/0/+1 momentum sign
    volatility_quintile: int      # 0..4, computed from past input only
    feature_asof: int             # latest index used by pre-origin features
    warmup_sessions: int
    residual_y20: float | None    # synthetic matured future-only label, never selector
    matured_at: int | None        # origin+20 iff measured


def candidate_h3_synthetic_interaction(
    a1_events: Sequence[SyntheticH3Event],
    b3_events: Sequence[SyntheticH3Event],
) -> dict:
    """Test only H3 arithmetic and past-only, one-to-one B3 eligibility.

    The actual A1/B3 generators, SPY beta-residual Y20 labels, pair universe,
    volatility quintiles, censoring and bootstrap remain original owner code.
    Here the input is a *synthetic P0 demonstration*, not a market file.

    Pre-origin features are checked for lookahead; matched B3 choice uses
    exclusively pair, donor-weakness, receiver momentum, vol quintile, date and
    one-to-one availability. Only AFTER selection can Y20^res labels contribute
    to the effect-modifier arithmetic. No effect p-value, power or market claim.
    """

    def validate(x: SyntheticH3Event, expected_arm: str) -> None:
        if type(x) is not SyntheticH3Event:
            raise TypeError("H3 P0 input must be SyntheticH3Event")
        if not isinstance(x.pair_id, str) or not x.pair_id.strip():
            raise ValueError("nonempty synthetic pair identity required")
        if x.arm != expected_arm:
            raise ValueError("INCORRECT_FROZEN_ARM")
        if any(type(z) is not int for z in (
            x.origin, x.receiver_spy_sign, x.volatility_quintile,
            x.feature_asof, x.warmup_sessions
        )):
            raise ValueError("H3 calendar and feature values must be integers")
        if x.origin < 0 or not 0 <= x.feature_asof <= x.origin:
            raise ValueError("LOOKAHEAD_FEATURE_DATE")
        if x.receiver_spy_sign not in (-1, 0, 1):
            raise ValueError("invalid receiver momentum sign")
        if x.volatility_quintile not in range(5):
            raise ValueError("volatility quintile must be 0..4")
        if type(x.donor_weak) is not bool:
            raise ValueError("donor_weak must be boolean, not imputed")
        if not 0 <= x.warmup_sessions <= x.origin:
            raise ValueError("invalid source warmup")
        if x.residual_y20 is None:
            if x.matured_at is not None:
                raise ValueError("unmeasured residual must not claim maturity")
        else:
            if type(x.residual_y20) not in (int, float) or not math.isfinite(float(x.residual_y20)):
                raise ValueError("invalid future residual observation")
            if type(x.matured_at) is not int or x.matured_at != x.origin + 20:
                raise ValueError("residual Y20 requires exact future-only maturity")

    for x in a1_events:
        validate(x, "A1")
    for x in b3_events:
        validate(x, "B3")
    all_events = list(a1_events) + list(b3_events)
    event_ids = [(x.arm, x.pair_id, x.origin) for x in all_events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("AMBIGUOUS_DUPLICATE_H3_EVENT")

    # Greedy oldest-onset-first pairing; one physical B3 alarm can be used
    # only once, even if multiple A1 events pass through its risk set.
    used: set[tuple[str, int]] = set()
    eligible_counts = {True: 0, False: 0}
    measured_differences = {True: [], False: []}
    chosen: list[dict] = []
    unpaired = 0
    unmeasured = 0
    for a in sorted(a1_events, key=lambda x: (x.origin, x.pair_id)):
        if a.warmup_sessions < 252:
            unpaired += 1
            continue
        risk_set = [
            b for b in b3_events
            if b.pair_id == a.pair_id
            and (b.pair_id, b.origin) not in used
            and b.warmup_sessions >= 252
            and b.donor_weak == a.donor_weak
            and b.receiver_spy_sign == a.receiver_spy_sign
            and b.volatility_quintile == a.volatility_quintile
            and 21 <= a.origin - b.origin <= 63
        ]
        if not risk_set:
            unpaired += 1
            continue
        b = max(risk_set, key=lambda x: x.origin)
        used.add((b.pair_id, b.origin))
        eligible_counts[a.donor_weak] += 1
        # Record time-based selection even if the outcome was not measurable.
        chosen.append({
            "a1_t": a.origin, "b3_t": b.origin,
            "pair_id": a.pair_id, "donor_weak": a.donor_weak,
        })
        if a.residual_y20 is None or b.residual_y20 is None:
            unmeasured += 1
            continue
        measured_differences[a.donor_weak].append(
            float(a.residual_y20) - float(b.residual_y20)
        )

    result = {
        "scope": "P0_SYNTHETIC_ONLY",
        "status": "NOT_EXECUTABLE",
        "reason": "MISSING_MEASURED_H3_STRATUM",
        "n_a1": len(a1_events),
        "n_selected": len(chosen),
        "n_unpaired": unpaired,
        "n_unmeasured": unmeasured,
        "n_weak": len(measured_differences[True]),
        "n_not_weak": len(measured_differences[False]),
        "selected_dates": chosen,
        "delta_log_units": None,
        "v3_preregistered": False,
        "size_or_power_proven": False,
        "matching_and_cluster_inference_proven": False,
    }
    if measured_differences[True] and measured_differences[False]:
        result["status"] = "DESCRIPTIVE"
        result["reason"] = None
        result["delta_log_units"] = (
            fmean(measured_differences[True]) -
            fmean(measured_differences[False])
        )
    return result



def candidate_v3_p0_pair_diagnostic(ps, *, start: int, end: int) -> dict:
    """Run ALL three proposed contrasts through original frozen P0 arms.

    Explicit synthetic PairSeries supplied by the caller; no store, config,
    production reader, input file, network, ledger or publication imports.
    This smoke exercise is NOT a preregistered family test, a size/power result,
    a synthetic-generator claim, or a permission to read P1/P2/P3 market data.
    """
    import numpy as np
    from scripts import leadership_rotation_study as st
    from scripts.leadership_rotation_run import PairSeries, _evaluate_pair_core

    if type(ps) is not PairSeries or type(start) is not int or type(end) is not int:
        raise TypeError("P0 diagnostic needs an explicit PairSeries and integer window")
    if not 0 <= start <= end < len(ps.spy):
        raise ValueError("invalid synthetic formation window")
    if len(ps.num) != len(ps.spy) or len(ps.den) != len(ps.spy):
        raise ValueError("P0 synthetic legs must have the same calendar length")
    if not np.all(np.isfinite(ps.num)) or not np.all(np.isfinite(ps.den)) or not np.all(np.isfinite(ps.spy)):
        raise ValueError("P0 diagnostic requires measured synthetic prices")
    if np.any(ps.num <= 0) or np.any(ps.den <= 0) or np.any(ps.spy <= 0):
        raise ValueError("invalid synthetic price basis")

    core = _evaluate_pair_core(ps, start=start, end=end)
    if not core["formation"]["eligible"]:
        return {
            "scope": "P0_SYNTHETIC_ONLY", "status": "NOT_EXECUTABLE",
            "reason": "NO_SYNTHETIC_FORMATION", "pair_id": ps.pair_id,
            "v3_preregistered": False, "size_or_power_proven": False,
        }
    actual_start = int(core["formation"]["start"])
    R = np.asarray(core["R"], dtype=float)
    n = len(R)
    if any(int(x) < actual_start or int(x) > end
           for x in core["a1_kept"] + core["b2_kept"] + core["b3_kept"]):
        raise ValueError("frozen arm entries escaped synthetic formation")

    h1 = candidate_h1_synthetic_comparison(
        core["phases"], core["a1_kept"], core["b2_kept"],
        measured_sessions=n,
    )
    # Exact history-at-date rank of rolling 63-observation relative volatility.
    # Even the rolling-vol quintile map is computed from past dates only:
    # no full-sample threshold/normalizer may contaminate a P0 match.
    changes = np.diff(R)
    vols = np.full(n, np.nan)
    for t in range(63, n):
        win = changes[t - 63:t]
        if np.all(np.isfinite(win)):
            vols[t] = np.std(win, ddof=1)
    quintile: dict[int, int] = {}
    for t in range(max(actual_start, 313), end + 1):
        window = vols[max(63, t - 251):t + 1]
        finite = window[np.isfinite(window)]
        if len(finite) < 200 or not np.isfinite(vols[t]):
            continue
        q = min(4, int(5 * float(np.sum(finite < vols[t])) / len(finite)))
        quintile[t] = q

    a1_state, _, _ = st.arm_a1(R)
    controls = [
        SyntheticPriorControl(
            ps.pair_id, int(t), quintile[t], int(t),
            bool(a1_state[t]), int(t),
        )
        for t in core["b1_days"] if int(t) in quintile
    ]
    h2 = {
        "total_a1": len(core["a1_kept"]),
        "feature_unavailable": 0,
        "matched": 0,
        "unmatched": 0,
        "control_dates": [],
        "status": "DIAGNOSTIC_ONLY",
    }
    for t in core["a1_kept"]:
        if t not in quintile:
            h2["feature_unavailable"] += 1
            continue
        event = SyntheticPriorControl(
            ps.pair_id, int(t), quintile[t], int(t), bool(a1_state[t]), int(t),
        )
        selection = candidate_h2_prior_control_match(event, controls)
        if selection["status"] == "MATCHED":
            h2["matched"] += 1
            h2["control_dates"].append((int(t), selection["control_t"]))
        else:
            h2["unmatched"] += 1

    log_numspy = np.log(ps.num / ps.spy)
    log_denspy = np.log(ps.den / ps.spy)

    def h3_events(rows, arm):
        out: list[SyntheticH3Event] = []
        unavailable = 0
        for rec in rows:
            t = int(rec["t"])
            if t not in quintile or t < 20:
                unavailable += 1
                continue
            den_move = float(log_denspy[t] - log_denspy[t - 20])
            recv_move = float(log_numspy[t] - log_numspy[t - 20])
            if not np.isfinite(den_move) or not np.isfinite(recv_move):
                unavailable += 1
                continue
            future = rec["y_res_20"]
            label = (
                float(future["y"])
                if future["state"] == "MATURED" and future["y"] is not None
                else None
            )
            out.append(SyntheticH3Event(
                pair_id=ps.pair_id, origin=t, arm=arm,
                donor_weak=den_move < 0,
                receiver_spy_sign=int(np.sign(recv_move)),
                volatility_quintile=quintile[t], feature_asof=t,
                warmup_sessions=t, residual_y20=label,
                matured_at=(t + 20) if label is not None else None,
            ))
        return out, unavailable

    a1, omitted_a1 = h3_events(core["a1_out"], "A1")
    b3, omitted_b3 = h3_events(core["b3_out"], "B3")
    h3 = candidate_h3_synthetic_interaction(a1, b3)
    return {
        "scope": "P0_SYNTHETIC_ONLY",
        "status": "DIAGNOSTIC_ONLY",
        "pair_id": ps.pair_id,
        "group": ps.group,
        "window": [actual_start, int(end)],
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "h3_feature_unavailable": {"a1": omitted_a1, "b3": omitted_b3},
        "v3_preregistered": False,
        "size_or_power_proven": False,
        "predictive_capability_qualified": False,
    }
