"""Leader Radar's descriptive deep-recovery projection, not a trading engine.

Pure replay of caller-supplied completed daily sessions. No I/O, clock, registry,
model, event writer, sizing, or changes to incumbent lifecycle / shallow pullback.
Historical bar order is causal; current adjusted data are NOT first-seen evidence.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
from typing import Iterable

import pandas as pd

SCHEMA = "leader_recovery.v1"
ERA = "leader-recovery-descriptive-2026-10-10"
AUTHORITY = {k: False for k in ("may_rank", "may_gate", "may_size", "may_trade", "may_alert")}
LABELS = {
    "UNAVAILABLE": "Recovery evidence unavailable",
    "NO_PRIOR_LEADER": "No prior leadership observed",
    "ACTIVE_LEADER": "Leadership observed",
    "CORRECTING": "Leader correcting",
    "DAMAGED": "Leadership damaged",
    "REBUILDING": "Recovery attempt",
    "REIGNITING": "Trend and relative strength repairing",
    "REPAIR_PAUSED": "Repair paused; leadership unconfirmed",
    "PRICE_RECOVERED_RS_LAGGING": "Price recovered; relative leadership not restored",
    "LEADERSHIP_REESTABLISHED": "Price and relative leadership restored",
    "FAILED_REPAIR": "Recovery attempt failed",
}


@dataclass(frozen=True)
class RecoverySpec:
    """Unfitted engineering definitions, not empirically selected signal cutoffs."""
    high_window: int = 252
    fast_window: int = 50
    slow_window: int = 200
    rs_window: int = 21
    confirm_sessions: int = 3
    correction_fraction: float = 0.10
    deep_fraction: float = 0.20
    rebound_fraction: float = 0.15
    extension_fraction: float = 0.10

    def __post_init__(self):
        counts = (self.high_window, self.fast_window, self.slow_window,
                  self.rs_window, self.confirm_sessions)
        if any(type(n) is not int or n < 2 for n in counts):
            raise ValueError("invalid_window")
        if not self.rs_window < self.fast_window < self.slow_window <= self.high_window:
            raise ValueError("invalid_window_order")
        fractions = (self.correction_fraction, self.deep_fraction,
                     self.rebound_fraction, self.extension_fraction)
        if any(type(x) not in (float, int) or not math.isfinite(x) or not 0 < x < 1
               for x in fractions):
            raise ValueError("invalid_fraction")
        if self.correction_fraction >= self.deep_fraction:
            raise ValueError("invalid_drawdown_order")

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def _date(value) -> date:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
        raise ValueError("expected_naive_session_date")
    return stamp.date()


def _source(series: pd.Series, as_of: date) -> dict[date, float]:
    if not isinstance(series, pd.Series):
        raise ValueError("expected_series")
    result: dict[date, float] = {}
    # Filter future values before numeric validation and duplicate detection.
    for raw_day, raw_value in series.items():
        day = _date(raw_day)
        if day > as_of:
            continue
        if day in result:
            raise ValueError("duplicate_session")
        if isinstance(raw_value, bool):
            raise ValueError("boolean_price")
        try:
            value = float(raw_value)
        except (ValueError, TypeError, OverflowError):
            value = float("nan")
        result[day] = value
    return result


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value) and value > 0


def _number(value) -> float | None:
    return round(float(value), 8) if value is not None and math.isfinite(value) else None


def _blank(day: date, reason: str) -> dict:
    return {"as_of": day.isoformat(), "state": "UNAVAILABLE", "reason": reason,
            "prior_leader_on": None, "leader_evidence": None, "episode": None,
            "price": None, "relative_return_21": None, "extension_vs_50": None,
            "entry_context": "UNAVAILABLE", "thesis_state": "UNKNOWN"}


def replay_recovery(
    close: pd.Series, benchmark: pd.Series, *, as_of: date,
    sessions: Iterable[date], spec: RecoverySpec | None = None,
) -> list[dict]:
    """Replay a descriptive former-leader history on the incumbent calendar.

    A prior leader is a transparent PRICE_RS_PROXY: a strict new RS high versus
    the previous high_window sessions, positive absolute high_window return,
    and price above its slow average. It is NOT a fabricated incumbent event.
    Only previously observed qualification is retained; no future winner labels.
    Correction peaks and the pre-correction RS target stay frozen during damage.
    Failed repair invalidates its fixed trough, not the company's entire future.
    """
    spec = spec or RecoverySpec()
    try:
        cut = _date(as_of)
        calendar = [_date(d) for d in sessions if _date(d) <= cut]
        if calendar != sorted(set(calendar)) or not calendar or calendar[-1] != cut:
            raise ValueError("invalid_or_incomplete_calendar")
        prices, benches = _source(close, cut), _source(benchmark, cut)
    except (TypeError, ValueError, OverflowError) as exc:
        return [_blank(as_of if type(as_of) is date else date.min, str(exc))]
    starts = [min(d) for d in (prices, benches) if d]
    if len(starts) != 2:
        return [_blank(cut, "missing_source")]
    calendar = [d for d in calendar if d >= max(starts)]
    if not calendar:
        return [_blank(cut, "missing_source")]

    # No forward fill: a gap resets rolling evidence and confirmation streaks.
    window_c: list[float] = []
    window_r: list[float] = []
    lineage: str | None = None
    peak = peak_ratio = 0.0
    peak_day = None
    episode: dict | None = None
    last_completed: dict | None = None
    fast_streak = slow_streak = restored_streak = 0
    rows = []
    for pos, day in enumerate(calendar):
        c, b = prices.get(day), benches.get(day)
        r = c / b if _finite(c) and _finite(b) else None
        if not _finite(r):
            window_c.clear(); window_r.clear()
            fast_streak = slow_streak = restored_streak = 0
            if episode:
                episode["history_complete"] = False
                episode["repair_floor"] = None
                episode["repair_started_on"] = None
            row = _blank(day, "missing_or_invalid_completed_session")
            row.update(prior_leader_on=(episode or {}).get("prior_leader_on", lineage),
                       episode={k: deepcopy(v) for k, v in episode.items() if not k.startswith("_")} if episode else None)
            rows.append(row)
            continue
        window_c.append(c); window_r.append(r)
        if len(window_c) > spec.high_window + 1:
            window_c.pop(0); window_r.pop(0)
        n = len(window_c)
        ma_fast = sum(window_c[-spec.fast_window:]) / spec.fast_window if n >= spec.fast_window else None
        ma_slow = sum(window_c[-spec.slow_window:]) / spec.slow_window if n >= spec.slow_window else None
        relative = r / window_r[-spec.rs_window - 1] - 1 if n > spec.rs_window else None
        if relative is not None and not math.isfinite(relative):
            relative = None
        qualified = (n > spec.high_window and r > max(window_r[:-1])
                     and c > window_c[0] and ma_slow is not None and c > ma_slow)
        if qualified:
            lineage = day.isoformat()
        if lineage and episode is None and c >= peak:
            peak, peak_day = c, day.isoformat()
        if lineage and episode is None:
            peak_ratio = max(peak_ratio, r)
        if lineage and episode is None and peak and c / peak - 1 <= -spec.correction_fraction:
            episode = {
                "peak_on": peak_day, "peak_price": peak,
                "reference_rs": peak_ratio, "prior_leader_on": lineage, "opened_on": day.isoformat(),
                "trough_on": day.isoformat(), "trough_price": c,
                "price_high_water": peak, "price_high_water_on": peak_day,
                "max_drawdown_from_high_water": _number(c / peak - 1),
                "max_drawdown_peak_price": peak, "max_drawdown_peak_on": peak_day,
                "max_drawdown_trough_price": c, "max_drawdown_trough_on": day.isoformat(),
                "max_drawdown": _number(c / peak - 1),
                "underwater_sessions": 1, "below_200_sessions": 0,
                "failed_repairs": 0, "repair_floor": None, "repair_started_on": None,
                "last_failure_on": None, "history_complete": True,
                "recovered_on": None, "_opened_pos": pos,
            }
        fast_ok = ma_fast is not None and relative is not None and c > ma_fast and relative > 0
        slow_ok = fast_ok and ma_slow is not None and c > ma_slow
        fast_streak = fast_streak + 1 if fast_ok else 0
        slow_streak = slow_streak + 1 if slow_ok else 0
        state = "ACTIVE_LEADER" if lineage else "NO_PRIOR_LEADER"
        state_reason = "price_rs_proxy" if lineage else "no_prior_qualifying_observation"
        if episode:
            ep = episode
            ep["underwater_sessions"] = pos - ep["_opened_pos"] + 1
            if ma_slow is not None and c < ma_slow:
                ep["below_200_sessions"] += 1
            failure = ep["repair_floor"] is not None and c < ep["repair_floor"]
            if failure:
                ep["failed_repairs"] += 1
                ep["last_failure_on"] = day.isoformat()
                ep["repair_floor"] = None
                ep["repair_started_on"] = None
                fast_streak = slow_streak = restored_streak = 0
            if c < ep["trough_price"]:
                ep["trough_price"], ep["trough_on"] = c, day.isoformat()
            ep["max_drawdown"] = _number(min(ep["max_drawdown"], c / ep["peak_price"] - 1))
            if c > ep["price_high_water"]:
                ep["price_high_water"], ep["price_high_water_on"] = c, day.isoformat()
            ep["drawdown_from_high_water"] = _number(c / ep["price_high_water"] - 1)
            if ep["drawdown_from_high_water"] < ep["max_drawdown_from_high_water"]:
                ep["max_drawdown_from_high_water"] = ep["drawdown_from_high_water"]
                ep["max_drawdown_peak_price"] = ep["price_high_water"]
                ep["max_drawdown_peak_on"] = ep["price_high_water_on"]
                ep["max_drawdown_trough_price"] = c
                ep["max_drawdown_trough_on"] = day.isoformat()
            ep["original_price_target_recovered"] = c >= ep["peak_price"]
            rebound = c / ep["trough_price"] - 1
            # Restoration references the FIXED pre-correction peak, never the
            # advancing high-water mark: an in-episode rally that prints a new
            # high while RS still lags would otherwise raise the bar it must
            # clear, and a later close could never satisfy three consecutive
            # sessions at-or-above a mark that ratchets on each of them.
            # price_high_water stays an independently recorded fact so the
            # paired max-drawdown peak/trough is still measured from it.
            price_restored = ep["original_price_target_recovered"]
            rs_restored = r >= ep["reference_rs"]
            restored_streak = restored_streak + 1 if price_restored and rs_restored and slow_ok else 0
            # A repair needs a material rebound AND multiple completed closes.
            repair = rebound >= spec.rebound_fraction and fast_streak >= spec.confirm_sessions
            if failure:
                state, state_reason = "FAILED_REPAIR", "close_breached_frozen_repair_floor"
            elif restored_streak >= spec.confirm_sessions:
                state, state_reason = "LEADERSHIP_REESTABLISHED", "price_and_pre_correction_rs_restored"
            elif price_restored and not rs_restored:
                state, state_reason = "PRICE_RECOVERED_RS_LAGGING", "price_target_reclaimed_but_rs_below_frozen_target"
            elif repair and slow_streak >= spec.confirm_sessions:
                state, state_reason = "REIGNITING", "multi_session_fast_slow_and_relative_repair"
            elif repair:
                state, state_reason = "REBUILDING", "multi_session_fast_and_relative_repair"
            elif ep["repair_started_on"] and ma_slow is not None and c > ma_slow:
                state, state_reason = "REPAIR_PAUSED", "prior_repair_above_long_trend_but_confirmation_missing"
            elif ep["drawdown_from_high_water"] <= -spec.deep_fraction or (ma_slow is not None and c < ma_slow):
                state, state_reason = "DAMAGED", "deep_drawdown_or_below_long_trend"
            else:
                state, state_reason = "CORRECTING", "open_correction"
            if repair and ep["repair_floor"] is None and not failure:
                ep["repair_floor"] = ep["trough_price"]
                ep["repair_started_on"] = day.isoformat()
            # A missing interval is carried on the record (history_complete
            # stays False for the life of the episode and on its completed
            # copy); it is not a permanent bar to closing the episode. The
            # restoration evidence itself is post-gap: the gap cleared every
            # window and streak, so three confirmed closes at-or-above the
            # fixed peak and the frozen RS reference are fully observed. What
            # the gap can hide is intra-episode history (sessions, drawdown
            # extremes), which is why the flag and reason stay visible.
            if state == "LEADERSHIP_REESTABLISHED":
                if not ep["history_complete"]:
                    state_reason = "price_and_pre_correction_rs_restored_gapped_history"
                ep["recovered_on"] = day.isoformat()
            ep["price_recovered"] = price_restored
            ep["rs_recovered"] = rs_restored
            ep["rebound_from_low"] = _number(rebound)
        if ma_slow is None and lineage:
            state, state_reason = "UNAVAILABLE", "trend_history_incomplete_after_gap"
        elif not lineage and n <= spec.high_window:
            state, state_reason = "UNAVAILABLE", "insufficient_leadership_history"
        extension = c / ma_fast - 1 if ma_fast else None
        entry = ("EXTENDED" if extension is not None and extension > spec.extension_fraction
                 else "REPAIR_OBSERVATION" if state in ("REBUILDING", "REIGNITING")
                 else "WAIT")
        row = {"as_of": day.isoformat(), "state": state, "reason": state_reason,
               "prior_leader_on": (episode or {}).get("prior_leader_on", lineage),
               "latest_leader_proxy_on": lineage, "leader_evidence": "PRICE_RS_PROXY" if lineage else None,
               "episode": {k: deepcopy(v) for k, v in episode.items() if not k.startswith("_")} if episode else None,
               "price": _number(c), "relative_return_21": _number(relative),
               "extension_vs_50": _number(extension), "entry_context": entry,
               "thesis_state": "UNKNOWN", "ma_fast": _number(ma_fast), "ma_slow": _number(ma_slow),
               "fast_confirmation_sessions": fast_streak,
               "slow_confirmation_sessions": slow_streak,
               "last_completed_episode": deepcopy(last_completed)}
        rows.append(row)
        if state == "LEADERSHIP_REESTABLISHED":
            last_completed = deepcopy(row["episode"])
            episode = None
            peak, peak_ratio, peak_day = c, r, day.isoformat()
            restored_streak = 0
    return rows


def describe_recovery(close: pd.Series, benchmark: pd.Series, *, as_of: date,
                      sessions: Iterable[date], source_ref: str | None = None,
                      spec: RecoverySpec | None = None) -> dict:
    spec = spec or RecoverySpec()
    rows = replay_recovery(close, benchmark, as_of=as_of, sessions=sessions, spec=spec)
    current = deepcopy(rows[-1])
    # Preserve the useful repaired-history descriptor after the completion day.
    if current.get("episode") is None and current.get("last_completed_episode"):
        current["episode"] = deepcopy(current["last_completed_episode"])
        current["episode"]["status"] = "completed"
    elif current.get("episode"):
        current["episode"]["status"] = "open"
    transitions = []
    previous = None
    for row in rows:
        if row["state"] != previous:
            transitions.append({"as_of": row["as_of"], "from": previous,
                                "to": row["state"], "reason": row["reason"]})
            previous = row["state"]
    try:
        cut = _date(as_of)
        fingerprint_inputs = [_source(close, cut), _source(benchmark, cut)]
        canonical = [[(d.isoformat(), v if math.isfinite(v) else None)
                      for d, v in sorted(part.items())] for part in fingerprint_inputs]
        fingerprint = hashlib.sha256(json.dumps(canonical, separators=(",", ":")).encode()).hexdigest()
    except (TypeError, ValueError, OverflowError):
        fingerprint = None
    current.update(schema=SCHEMA, era=ERA, label=LABELS[current["state"]],
                   source_fingerprint_sha256=fingerprint, sampling_basis="completed_daily_close",
                   authority=deepcopy(AUTHORITY), definition=asdict(spec), definition_sha256=spec.digest,
                   source_ref=source_ref, evidence_mode="RECONSTRUCTED_CURRENT_VINTAGE",
                   first_seen_qualified=False, historical_membership_qualified=False,
                   fundamental_thesis={"state": "UNKNOWN", "reason": "requires_source_dated_fundamental_owner"},
                   transitions=transitions[-12:], transitions_total=len(transitions))
    return current


def recovery_roster(rows: list[dict], *, as_of: str, stale: bool) -> dict:
    """One read-only view over incumbent row descriptors; no independent store."""
    counts = {s: 0 for s in LABELS}
    roster = []
    if len({r["ticker"] for r in rows}) != len(rows):
        raise ValueError("duplicate_roster_identity")
    for row in rows:
        d = (row.get("display_chips") or {}).get("leader_recovery") or {}
        state = d.get("state", "UNAVAILABLE")
        counts[state if state in counts else "UNAVAILABLE"] += 1
        if not d.get("episode"):
            continue
        roster.append({"ticker": row["ticker"], "state": state, "label": LABELS.get(state, LABELS["UNAVAILABLE"]),
                       "as_of": d.get("as_of"), "episode": deepcopy(d["episode"]),
                       "entry_context": d.get("entry_context"),
                       "prior_leader_on": d.get("prior_leader_on"),
                       "thesis_state": d.get("thesis_state", "UNKNOWN")})
    roster.sort(key=lambda x: x["ticker"])
    return {"schema": "leader_recovery_roster.v1", "as_of": as_of, "stale": bool(stale),
            "counts": counts, "rows": roster, "population_rows": len(rows),
            "authority": deepcopy(AUTHORITY), "evidence_mode": "RECONSTRUCTED_CURRENT_VINTAGE"}
