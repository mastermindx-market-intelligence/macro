"""Causal, raw-close pullback observations; never a forecast or a policy gate.

This is a re-derivable view, not a ledger. Historical transition dates are
reconstructed from the current source vintage, never claimed as issued alerts.
No risk score is accepted: forecast intensity cannot prove a realized decline.
See research/grey_deer/CN_PULLBACK_OBSERVATION_PLAN_2026-09-29.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from hashlib import sha256
from math import isfinite
from numbers import Real
from statistics import fmean
from typing import Callable, Iterable


@dataclass(frozen=True)
class Rules:
    version: str = "close_path.v1"
    reference_closes: int = 63
    onset_drawdown: float = 0.02
    onset_closes: int = 2
    shock_drawdown: float = 0.05
    stabilization_closes: int = 3
    recovery_above_ma_closes: int = 5
    recovery_no_low_closes: int = 10
    trend_repair_above_ma_closes: int = 20
    trend_repair_no_low_closes: int = 21
    reclaim_closes: int = 2


RULES = Rules()
SCHEMA = "pullback_observation.v1"


def _next_observation(previous: date, current: date,
                      is_session: Callable[[date], bool]) -> bool:
    """No unobserved expected session may count toward persistence."""
    probe = previous + timedelta(days=1)
    while probe < current:
        if is_session(probe):
            return False
        probe += timedelta(days=1)
    return current > previous and is_session(current)


def _empty(expected: date, reason: str, **extra) -> dict:
    return {"schema": SCHEMA, "rules": asdict(RULES), "available": False,
            "quality": reason, "expected_session": expected.isoformat(),
            "asof": None, "phase": "unavailable", "active": None,
            "drawdown_pct": None, "loss_recovered_pct": None, **extra}


def observe(rows: Iterable[tuple[str, float]], *, expected_session: date,
            is_session: Callable[[date], bool]) -> dict:
    """Describe the price path visible at ``expected_session``.

    Input dates must be daily ISO session labels, not intraday timestamps.
    Same-value duplicates collapse; conflicting duplicates fail closed. Future
    rows are excluded before price validation, preserving prefix causality.
    The caller supplies the owning exchange calendar, never a weekday guess.
    """
    if not is_session(expected_session):
        return _empty(expected_session, "invalid_expected_session")
    normalized: dict[date, float] = {}
    calendar_disagreements: set[date] = set()
    future_count = duplicate_count = 0
    try:
        for stamp, value in rows:
            if not isinstance(stamp, str) or len(stamp) != 10:
                return _empty(expected_session, "invalid_session_label")
            day = date.fromisoformat(stamp)
            if day > expected_session:
                future_count += 1
                continue
            if not is_session(day):
                # The owning CN calendar is a deliberately approximate rule
                # calendar. Keep source history intact; a disagreement inside
                # the selected evidence window blocks the current view below.
                calendar_disagreements.add(day)
            if isinstance(value, bool) or not isinstance(value, Real):
                return _empty(expected_session, "invalid_close")
            price = float(value)
            if not isfinite(price) or price <= 0:
                return _empty(expected_session, "invalid_close")
            if day in normalized:
                if normalized[day] != price:
                    return _empty(expected_session, "conflicting_duplicate")
                duplicate_count += 1
            normalized[day] = price
    except (TypeError, ValueError, OverflowError):
        return _empty(expected_session, "invalid_observation")
    records = sorted(normalized.items())
    if not records:
        return _empty(expected_session, "no_history")
    digest = sha256("\n".join(f"{d.isoformat()},{p.hex()}" for d, p in records).encode()).hexdigest()
    provenance = {"asof": records[-1][0].isoformat(), "source_digest": digest,
                  "sample_count": len(records), "excluded_future_rows": future_count,
                  "collapsed_identical_duplicates": duplicate_count,
                  "calendar_disagreement_count": len(calendar_disagreements),
                  "last_calendar_disagreement": max(calendar_disagreements).isoformat() if calendar_disagreements else None,
                  "history_basis": "reconstructed_current_source_vintage"}
    if len(records) < RULES.reference_closes:
        return _empty(expected_session, "insufficient_history", **provenance)
    result = _replay(records, is_session)
    evidence_start = min(date.fromisoformat(result["peak_session"]),
                         date.fromisoformat(result["price_path"]["dates"][0]))
    if any(day >= evidence_start for day in calendar_disagreements):
        return _empty(expected_session, "calendar_disagreement", **provenance)
    result.update(schema=SCHEMA, rules=asdict(RULES), available=True,
                  quality="current", expected_session=expected_session.isoformat(),
                  **provenance)
    if records[-1][0] != expected_session:
        return _empty(expected_session, "delayed", **provenance,
                      last_observation={"asof": provenance["asof"],
                                        "phase": result["phase"],
                                        "drawdown_pct": result["drawdown_pct"]})
    return result


def _peak(records: list[tuple[date, float]], lo: int, hi: int) -> int:
    # Equal highs use the most recent close; a flat top does not age needlessly.
    return max(range(lo, hi), key=lambda j: (records[j][1], j))


def _replay(records: list[tuple[date, float]], is_session: Callable[[date], bool]) -> dict:
    prices = [p for _, p in records]
    pending = episode = None
    reference_floor = 0
    contiguous = above20 = gap_count = 0
    view: dict = {}
    for i, (day, price) in enumerate(records):
        joined = i == 0 or _next_observation(records[i - 1][0], day, is_session)
        contiguous = contiguous + 1 if joined else 1
        if not joined:
            gap_count += 1
            pending = None
            above20 = 0
            if episode:
                episode["no_new_low_closes"] = 0
                episode["reclaim_streak"] = 0
        ma5 = fmean(prices[max(0, i - 4):i + 1])
        ma20 = fmean(prices[max(0, i - 19):i + 1])
        above20 = above20 + 1 if i >= 19 and price > ma20 else 0
        if i < RULES.reference_closes - 1:
            continue
        # Exact trailing window: RULES.reference_closes includes today's
        # settled close. Keeping i-reference_closes would retain a 64th close
        # for one extra session and could turn an aged-out high into a false
        # shock/onset. The display's recent_63_drawdown uses the same basis.
        peak_i = _peak(records, max(reference_floor, i - RULES.reference_closes + 1), i + 1)
        if episode is None:
            ref_i = pending["peak_index"] if pending else peak_i
            below = 1.0 - price / prices[ref_i]
            if below + 1e-12 >= RULES.onset_drawdown:
                if pending is None:
                    pending = {"peak_index": ref_i, "streak": 0, "first_index": i}
                pending["streak"] += 1
                if (pending["streak"] >= RULES.onset_closes
                        or below + 1e-12 >= RULES.shock_drawdown):
                    low_i = min(range(ref_i, i + 1), key=lambda j: prices[j])
                    episode = {"peak_index": ref_i, "start_index": i,
                               "low_index": low_i, "no_new_low_closes": 0,
                               "reclaim_streak": 0, "phase": "underway",
                               "transitions": [(i, "underway")]}
                    pending = None
            else:
                pending = None
        if episode is not None:
            if price < prices[episode["low_index"]]:
                episode["low_index"] = i
                episode["no_new_low_closes"] = 0
            elif i > episode["start_index"]:
                episode["no_new_low_closes"] = (
                    episode["no_new_low_closes"] + 1 if joined else 0)
            reference = prices[episode["peak_index"]]
            episode["reclaim_streak"] = (
                episode["reclaim_streak"] + 1 if price >= reference else 0)
            rising20 = ma20 > fmean(prices[i - 24:i - 4])
            stable = (contiguous >= 5
                      and episode["no_new_low_closes"] >= RULES.stabilization_closes
                      and price > ma5)
            recovering = (contiguous >= 25 and rising20
                          and above20 >= RULES.recovery_above_ma_closes
                          and episode["no_new_low_closes"] >= RULES.recovery_no_low_closes)
            phase = "recovering" if recovering else ("stabilizing" if stable else "underway")
            if episode["reclaim_streak"]:
                phase = "recovering"  # one reclaimed close is not resolution
            resolution = None
            if episode["reclaim_streak"] >= RULES.reclaim_closes:
                resolution = "prior_high_reclaimed"
            elif (contiguous >= 40 and rising20
                  and above20 >= RULES.trend_repair_above_ma_closes
                  and episode["no_new_low_closes"] >= RULES.trend_repair_no_low_closes
                  and price > max(prices[i - 20:i])):
                resolution = "trend_repaired_below_prior_high"
            if resolution:
                phase = "repaired"
            if phase != episode["phase"]:
                episode["transitions"].append((i, phase))
                episode["transitions"] = episode["transitions"][-6:]
            episode["phase"] = phase
            view = {"phase": phase, "active": resolution is None,
                    "event": dict(episode), "reference_index": episode["peak_index"],
                    "resolution": resolution, "reference_floor_index": reference_floor}
            if resolution:
                reference_floor = i
                episode = None  # re-arm locally, never erase the unresolved peak by age
        else:
            view = {"phase": "developing" if pending else "monitoring", "active": False,
                    "event": None, "reference_index": pending["peak_index"] if pending else peak_i,
                    "resolution": None, "reference_floor_index": reference_floor}
    return _finish(records, view, contiguous, gap_count)


def _finish(records: list[tuple[date, float]], view: dict, contiguous: int,
            gap_count: int) -> dict:
    last = len(records) - 1
    price = records[last][1]
    event = view["event"]
    peak_i = view["reference_index"]
    peak_date, peak = records[peak_i]
    low_i = event["low_index"] if event else min(range(peak_i, last + 1), key=lambda j: records[j][1])
    low_date, low = records[low_i]
    start_i = event["start_index"] if event else None
    recovered = max(0.0, min(100.0, 100.0 * (price - low) / (peak - low))) if peak > low else None
    chart_start = max(view["reference_floor_index"], last - 62)
    price_path = {"dates": [d.isoformat() for d, _ in records[chart_start:]],
                  "vals": [round(min(0.0, 100.0 * (p / peak - 1.0)), 4)
                           for _, p in records[chart_start:]]}
    timeline = [{"kind": "peak", "date": peak_date.isoformat(), "close": peak}]
    if event:
        timeline.extend([
            {"kind": "confirmed", "date": records[start_i][0].isoformat(), "close": records[start_i][1]},
            {"kind": "low", "date": low_date.isoformat(), "close": low},
        ])
    timeline.append({"kind": "latest", "date": records[-1][0].isoformat(), "close": price})
    timeline.sort(key=lambda row: row["date"])
    transitions = [{"date": records[j][0].isoformat(), "phase": phase}
                   for j, phase in (event["transitions"] if event else [])]
    recent_peak_i = _peak(records, max(0, last - 62), last + 1)
    return {
        "phase": view["phase"], "active": view["active"], "resolution": view["resolution"],
        "close": price, "peak_close": peak, "peak_session": peak_date.isoformat(),
        "peak_basis": "frozen_at_onset" if event else ("post_repair_high" if view["reference_floor_index"] else "preceding_63_closes"),
        "reference_reset_session": records[view["reference_floor_index"]][0].isoformat() if view["reference_floor_index"] else None,
        "low_close": low if event else None, "low_session": low_date.isoformat() if event else None,
        "onset_session": records[start_i][0].isoformat() if event else None,
        "observed_closes_since_onset": last - start_i + 1 if event else None,
        "drawdown_pct": round(min(0.0, 100.0 * (price / peak - 1.0)), 4),
        "recent_63_drawdown_pct": round(min(0.0, 100.0 * (price / records[recent_peak_i][1] - 1.0)), 4),
        "below_20_close_average": price < fmean(p for _, p in records[-20:]),
        "loss_recovered_pct": round(recovered, 2) if recovered is not None and event else None,
        "no_new_low_closes": event["no_new_low_closes"] if event else None,
        "contiguous_closes": contiguous, "history_gap_count": gap_count,
        "price_path": price_path, "timeline": timeline, "price_transitions": transitions,
    }
