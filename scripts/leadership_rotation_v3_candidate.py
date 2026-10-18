"""LR-W6 H1 V3 candidate: synthetic-only, non-inferential delay diagnostic.

This is NOT the V3 pre-registration, a P0 size/power simulator, a P1/P2/P3
reader, or a market-data consumer. The only input is caller-supplied phases
and alarm indices from synthetic P0 data. It deliberately reuses the frozen
T11 episode classifier (and its original matching/burden definitions).

Research contract:
  research/LEADERSHIP_ROTATION_V3_CANDIDATE_2026-10-18.md §2/§6

No future-price outcomes, V3 pass/claim decision, release gate or cache here.
"""
from __future__ import annotations

from statistics import fmean
from typing import Sequence

from scripts import leadership_rotation_episodes as ep

__all__ = ["candidate_h1_synthetic_comparison"]

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
