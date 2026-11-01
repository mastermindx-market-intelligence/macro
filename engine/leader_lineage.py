"""Deep-recovery LINEAGE descriptor: failed leadership versus deep corrective continuation.

Pure replay of caller-supplied completed daily sessions. No I/O, clock, registry, model,
event writer, rank, gate, size, trade or alert (authority all False). It COMPLEMENTS the
shallow ``us_leader_pullback`` lane and the ``leader_recovery`` projection and touches
neither: no import of either, no shared state, no change to their populations.

Owner-dated evidence (fundamentals / revisions, volume and demand, the intraday pivot
owner's published descriptor) is consumed read-only and reported UNKNOWN when absent —
never inferred from price alone, never back-dated, never fabricated.

Two independent axes stay apart on every row: the leadership THESIS
(INTACT / DAMAGED / CONTRADICTED / UNKNOWN) and the entry SETUP condition
(WATCH / RESET / REBUILDING / RE_IGNITION / EXTENDED / INVALIDATED). A failure verdict is
revisable: a later full re-admission opens a NEW episode linked by ``prior_episode_id``.
Nothing here is a lifetime delisting. Historical bar order is causal; current adjusted
data are NOT first-seen evidence (``EVIDENCE_MODE`` says so on every read).

The universe helper ``describe_lineage_universe`` and the structural chips
``lineage_chip`` / ``lineage_roster`` are exact-equivalent to running ``describe_lineage``
with the same peers dict: every byte of every subject's descriptor matches, including the
fingerprint, the basket mean (sequential float addition), and the failure-mode ordering
on sourcing errors.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
from typing import Callable, Iterable, Mapping

import numpy as np
import pandas as pd

SCHEMA = "leader_lineage.v1"
ERA = "leader-lineage-descriptive-2026-10-11"
EVIDENCE_MODE = "RECONSTRUCTED_CURRENT_VINTAGE"
AUTHORITY = {k: False for k in ("may_rank", "may_gate", "may_size", "may_trade", "may_alert")}
THESIS_STATES = ("INTACT", "DAMAGED", "CONTRADICTED", "UNKNOWN")
SETUP_STATES = ("WATCH", "RESET", "REBUILDING", "RE_IGNITION", "EXTENDED", "INVALIDATED")
BREAK_CLASSES = ("FAILED_BREAK", "STRUCTURAL_BREAK", "REPAIRED_TREND", "UNRESOLVED")
PHASES = ("ACTIVE", "DAMAGED", "REPAIRED", "FAILED")
ROSTER_COUNT_STATES = PHASES + ("NO_PRIOR_LEADER", "UNAVAILABLE")  # every descriptor state; roster counts sum to coverage.issuers
LADDER = (
    "higher_low_confirmed_on",        # R1  price: closes hold above the frozen trough
    "reclaim_50d_on",                 # R2  price: confirmed closes above the fast average
    "reclaim_200d_on",                # R3  price: confirmed closes above the slow average, after R2
    "rs_vs_spy_rising_on",            # R4a relative strength versus the benchmark rising, after R3
    "rs_vs_peer_basket_rising_on",    # R4b versus the leave-one-out peer basket (caller-supplied closes)
    "revisions_news_stabilized_on",   # R5  owner-dated
    "volume_demand_confirmed_on",     # R6  owner-dated
    "pivot_confirmed_on",             # R7  read-only from the intraday pivot owner's descriptor
)
REVISION_REQUIRES = ("new_leadership_qualification", "ordered_ladder_R1_R4", "owner_dated_R5_R6")

_CHIP_KEYS = ("schema", "era", "evidence_mode", "definition_sha256", "as_of", "state", "reason",
              "thesis_state", "setup_state", "break_class", "contradiction_evidence", "revisable",
              "price_ath", "rs_ath", "episode", "source_ref", "source_fingerprint_sha256")


@dataclass(frozen=True)
class LineageSpec:
    """Frozen engineering definitions — fixed BEFORE any outcome evaluation, never fitted."""
    high_window: int = 252
    fast_window: int = 50
    slow_window: int = 200
    rs_window: int = 21
    confirm_sessions: int = 3
    deep_fraction: float = 0.20
    extension_fraction: float = 0.10
    higher_low_sessions: int = 10
    structural_below_slow: int = 40
    horizon_sessions: int = 126

    def __post_init__(self):
        counts = (self.high_window, self.fast_window, self.slow_window, self.rs_window,
                  self.confirm_sessions, self.higher_low_sessions,
                  self.structural_below_slow, self.horizon_sessions)
        if any(type(n) is not int or n < 2 for n in counts):
            raise ValueError("invalid_window")
        if not self.rs_window < self.fast_window < self.slow_window <= self.high_window:
            raise ValueError("invalid_window_order")
        if not self.structural_below_slow < self.horizon_sessions:
            raise ValueError("invalid_horizon_order")
        for x in (self.deep_fraction, self.extension_fraction):
            if type(x) not in (float, int) or isinstance(x, bool) or not math.isfinite(x) or not 0 < x < 1:
                raise ValueError("invalid_fraction")

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


# ----------------------------------------------------------------------------- helpers
def _date(value) -> date:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
        raise ValueError("expected_naive_session_date")
    return stamp.date()


def _finite(value) -> bool:
    return (value is not None and isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def _num(value):
    try:
        return round(float(value), 8) if value is not None and math.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def _source_slow(series: pd.Series, cut: date) -> dict[date, float]:
    """Completed sessions at or before the cut. Duplicate dates and boolean prices raise;
    a non-numeric value becomes nan (a gap), never a carried-forward value. Always invoked
    when the fast-path preconditions are not all met (string/object dtype, NaT index, tz,
    non-normalized stamp, or any unexpected precondition breach)."""
    out: dict[date, float] = {}
    for stamp, raw in series.items():
        day = _date(stamp)
        if day > cut:
            continue
        if day in out:
            raise ValueError("duplicate_session")
        if isinstance(raw, bool):
            raise ValueError("boolean_price")
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = math.nan
        out[day] = val
    return out


def _source_fast(series: pd.Series, cut: date) -> dict[date, float]:
    """EXACT-equivalent of ``_source_slow`` when ALL preconditions hold: float64,
    pd.DatetimeIndex, naive, no NaT, normalized. Skips the per-item ``_date`` / ``float``
    calls and the per-iteration dict probe; produces byte-identical output (python dates,
    python floats, dict insertion order, duplicate_session on a within-cut repeat)."""
    idx = series.index
    vals = series.values
    cut_ts = pd.Timestamp(cut)
    mask = idx <= cut_ts
    kept_idx = idx[mask]
    kept_vals = vals[mask]
    if not kept_idx.is_unique:
        raise ValueError("duplicate_session")
    return dict(zip(kept_idx.date, kept_vals.tolist()))


def _source(series: pd.Series, cut: date) -> dict[date, float]:
    """Dispatch to the fast path when ALL preconditions hold; otherwise the slow path.
    The two paths are byte-equivalent for legal inputs."""
    idx = series.index
    if (isinstance(idx, pd.DatetimeIndex)
            and idx.tz is None
            and not idx.hasnans
            and bool((idx == idx.normalize()).all())
            and series.dtype == np.float64):
        return _source_fast(series, cut)
    return _source_slow(series, cut)


def _latest_owner_row(rows, day: date, key: str = "as_of"):
    """Newest owner-dated row at or before ``day``. Rows without a usable date are ignored
    (an undated claim is never back-dated into the history)."""
    best = None
    for row in rows or ():
        try:
            when = _date(row.get(key))
        except (TypeError, ValueError, AttributeError):
            continue
        if when <= day and (best is None or when >= best[0]):
            best = (when, row)
    return best


def _episode_id(ticker: str, qualified_on: date) -> str:
    return hashlib.sha256(f"{ticker}|{qualified_on.isoformat()}".encode()).hexdigest()[:16]


def _unavailable(day: date, reason: str) -> dict:
    return {"as_of": day.isoformat(), "state": "UNAVAILABLE", "reason": reason,
            "thesis_state": "UNKNOWN", "setup_state": "WATCH", "break_class": None,
            "contradiction_evidence": [], "revisable": None,
            "episode": None, "price_ath": None, "rs_ath": None}


def _new_episode(ticker: str, day: date, k: int, close: float, rs: float, prior: dict | None) -> dict:
    return {
        "episode_id": _episode_id(ticker, day),
        "prior_episode_id": prior["episode_id"] if prior else None,
        "leadership_qualified_at": day.isoformat(),
        "phase": "ACTIVE", "break_class": "UNRESOLVED", "revised_from": None, "revised_on": None,
        "history_complete": True, "closed_on": None, "close_reason": None,
        "price_ath": close, "price_ath_on": day.isoformat(),
        "rs_ath": rs, "rs_ath_on": day.isoformat(),
        "correction_peak_price": None, "correction_peak_on": None, "rs_at_correction_peak": rs,
        "correction_trough_price": None, "correction_trough_on": None, "rs_trough": None,
        "max_close_drawdown": 0.0, "rs_peak_to_trough": None,
        "sessions_below_50": {"consecutive_max": 0, "total": 0, "current": 0},
        "sessions_below_200": {"consecutive_max": 0, "total": 0, "current": 0},
        "repair_floor_price": None, "failed_on": None, "structural_on": None,
        "structural_watch": False, "revisable": True, "revision_requires": list(REVISION_REQUIRES),
        "ladder": {key: None for key in LADDER},
        "ladder_order_violations": [],
        "ladder_stalled": [],
        "distribution_evidence": {"state": "UNKNOWN", "basis": None},
        "accumulation_evidence": {"state": "UNKNOWN", "basis": None},
        "fundamental_deterioration": {"state": "UNKNOWN", "source_ref": None},
        "rs_vs_peer_basket": "UNKNOWN",
        "_k": k, "_trough_k": None,
        "_streaks": {"above_50": 0, "above_200": 0, "rs_spy": 0, "rs_peer": 0},
    }


def _public(ep: dict | None) -> dict | None:
    if ep is None:
        return None
    return {k: deepcopy(v) for k, v in ep.items() if not k.startswith("_")}


def _apply_owner_evidence(cur: dict, day: date, fundamentals, volume_demand, pivot) -> None:
    """Read-only projection of owner-dated rows. Absent -> UNKNOWN. Never back-dated."""
    trough_on = cur["correction_trough_on"]
    fund = _latest_owner_row(fundamentals, day)
    if fund is None:
        cur["fundamental_deterioration"] = {"state": "UNKNOWN", "source_ref": None}
    else:
        when, row = fund
        state = str(row.get("state", "UNKNOWN")).upper()
        mapped = "PRESENT" if state == "PRESENT" else "NONE" if state in ("NONE", "STABILIZED") else "UNKNOWN"
        cur["fundamental_deterioration"] = {"state": mapped, "source_ref": row.get("source_ref"),
                                            "as_of": when.isoformat()}
        if (state == "STABILIZED" and cur["ladder"]["revisions_news_stabilized_on"] is None
                and trough_on and when.isoformat() >= trough_on):
            cur["ladder"]["revisions_news_stabilized_on"] = when.isoformat()
    vol = _latest_owner_row(volume_demand, day)
    if vol is None:
        cur["distribution_evidence"] = {"state": "UNKNOWN", "basis": None}
        cur["accumulation_evidence"] = {"state": "UNKNOWN", "basis": None}
    else:
        when, row = vol
        state = str(row.get("state", "")).upper()
        basis = {"source_ref": row.get("source_ref"), "as_of": when.isoformat()}
        cur["distribution_evidence"] = {"state": "PRESENT" if state == "DISTRIBUTION" else "ABSENT", "basis": basis}
        cur["accumulation_evidence"] = {"state": "PRESENT" if state == "ACCUMULATION" else "ABSENT", "basis": basis}
        if (state == "ACCUMULATION" and cur["ladder"]["volume_demand_confirmed_on"] is None
                and trough_on and when.isoformat() >= trough_on):
            cur["ladder"]["volume_demand_confirmed_on"] = when.isoformat()
    if pivot and cur["ladder"]["pivot_confirmed_on"] is None:
        try:
            pv = _date(pivot.get("confirmed_on"))
        except (TypeError, ValueError, AttributeError):
            pv = None
        if pv is not None and pv <= day and trough_on and pv.isoformat() >= trough_on:
            cur["ladder"]["pivot_confirmed_on"] = pv.isoformat()


# ----------------------------------------------------------------------------- fingerprint
def _fingerprint(close: pd.Series, as_of, ticker: str, source_ref: str | None) -> str:
    """Same body as ``describe_lineage``'s fingerprint block. ``OverflowError`` from the
    digest is allowed to escape — callers may want to see it."""
    try:
        cut = _date(as_of)
        src = _source(close, cut)
        closes = [[k.isoformat(), _num(v)] for k, v in src.items()]
    except (TypeError, ValueError, AttributeError):
        closes = None
    return hashlib.sha256(json.dumps({"ticker": ticker, "as_of": str(as_of), "source_ref": source_ref,
                                      "close": closes}, sort_keys=True, default=str).encode()).hexdigest()


# ----------------------------------------------------------------------------- replay core
def _basket_leave_one_out_mean(vals: np.ndarray, sidx: int) -> float:
    """Sequential leave-one-out mean for the subject at position ``sidx``. The cumulative
    addition goes over the leave-one-out values in ``vals`` order — the same order the
    state machine would iterate if it called :func:`sum` per day. ``np.add.accumulate`` is
    bit-identical to a python ``sum`` over the same ordered floats; ``math.fsum``,
    ``np.sum`` and total-minus-self reductions are NOT bit-identical and would fail T7."""
    if sidx < 0 or sidx >= len(vals):
        raise IndexError("sidx out of range")
    if len(vals) <= 1:
        raise ValueError("no peers for leave-one-out")
    if sidx == 0:
        leave = vals[1:]
    elif sidx == len(vals) - 1:
        leave = vals[:-1]
    else:
        leave = np.concatenate([vals[:sidx], vals[sidx + 1:]])
    return float(np.add.accumulate(leave.astype(float))[-1]) / len(leave)


def _replay_core(*, ticker: str, prices: dict[date, float], benches: dict[date, float],
                 has_peers: bool, basket_mean: Callable[[date], float | None],
                 calendar: list[date], fundamentals: list, volume_demand: list,
                 pivot: dict | None, spec: LineageSpec, emit_rows: bool):
    """Shared state-machine over an ALREADY-trimmed calendar and ALREADY-sourced dicts.
    Used by both ``replay_lineage`` (emit_rows=True) and ``describe_lineage`` /
    ``describe_lineage_universe`` (emit_rows=False). ``basket_mean(day)`` must return the
    peer mean at ``day`` (NOT divided by the benchmark) or ``None`` if the basket does not
    exist on that day; the basket ratio is computed in the loop as ``basket_mean(day) / b``
    so the single-ticker path (``has_peers=False``) yields ``None`` cheaply. Returns
    ``(rows, episodes, n_sessions)``; ``n_sessions`` is ``len(calendar)`` on the main
    path and the early-return paths return ``1`` to match the existing single-row fallback."""
    stalled_rungs = [] if has_peers else ["rs_vs_peer_basket_rising_on"]

    hist: list[tuple[date, float, float, float | None]] = []   # (day, close, rs, basket_rs)
    closes_list: list[float] = []
    rs_list: list[float] = []
    episodes: list[dict] = []
    cur: dict | None = None
    rows: list[dict] = []

    for k, day in enumerate(calendar):
        c, b = prices.get(day, math.nan), benches.get(day, math.nan)
        if not (_finite(c) and _finite(b)):
            hist.clear()
            closes_list.clear()
            rs_list.clear()
            if cur is not None:
                cur["history_complete"] = False
                cur["_streaks"] = {key: 0 for key in cur["_streaks"]}
            if emit_rows:
                rows.append(_unavailable(day, "missing_or_invalid_completed_session"))
            elif k == len(calendar) - 1:
                rows.append(_unavailable(day, "missing_or_invalid_completed_session"))
            continue
        rs = c / b
        bmean = basket_mean(day)
        basket = bmean / b if bmean is not None else None
        hist.append((day, c, rs, basket))
        closes_list.append(c)
        rs_list.append(rs)
        n = len(hist)
        ma_fast = sum(closes_list[-spec.fast_window:]) / spec.fast_window if n >= spec.fast_window else None
        ma_slow = sum(closes_list[-spec.slow_window:]) / spec.slow_window if n >= spec.slow_window else None
        qualified = False
        if n > spec.high_window and ma_slow is not None:
            window = rs_list[-spec.high_window - 1:-1]
            qualified = (rs > max(window) and c > hist[-spec.high_window - 1][1]
                         and c > ma_slow)

        # ---- episode open / re-admission: a NEW linked episode, never a relabel of the old one
        if qualified and (cur is None or cur["phase"] != "ACTIVE"):
            if cur is not None:
                cur["closed_on"], cur["close_reason"] = day.isoformat(), "re_admitted_new_episode"
            cur = _new_episode(ticker, day, k, c, rs, cur)
            episodes.append(cur)

        if cur is not None:
            st, lad = cur["_streaks"], cur["ladder"]
            if c > cur["price_ath"]:
                cur["price_ath"], cur["price_ath_on"] = c, day.isoformat()
            if rs > cur["rs_ath"]:
                cur["rs_ath"], cur["rs_ath_on"] = rs, day.isoformat()
            if cur["phase"] == "ACTIVE":
                if c >= cur["price_ath"]:
                    cur["rs_at_correction_peak"] = rs
                dd = c / cur["price_ath"] - 1.0
                cur["max_close_drawdown"] = min(cur["max_close_drawdown"], dd)
                if dd <= -spec.deep_fraction:
                    cur["phase"] = "DAMAGED"
                    cur["correction_peak_price"], cur["correction_peak_on"] = cur["price_ath"], cur["price_ath_on"]
                    cur["correction_trough_price"], cur["correction_trough_on"] = c, day.isoformat()
                    cur["rs_trough"], cur["_trough_k"] = rs, k
            if cur["phase"] in ("DAMAGED", "REPAIRED"):
                cur["max_close_drawdown"] = min(cur["max_close_drawdown"], c / cur["correction_peak_price"] - 1.0)
                if cur["phase"] == "DAMAGED" and lad["reclaim_50d_on"] is None and c < cur["correction_trough_price"]:
                    cur["correction_trough_price"], cur["correction_trough_on"] = c, day.isoformat()
                    cur["_trough_k"] = k
                    lad["higher_low_confirmed_on"] = None
                cur["rs_trough"] = min(cur["rs_trough"], rs)
                cur["rs_peak_to_trough"] = cur["rs_trough"] / cur["rs_at_correction_peak"] - 1.0
                for key, ma in (("sessions_below_50", ma_fast), ("sessions_below_200", ma_slow)):
                    rec = cur[key]
                    if ma is not None and c < ma:
                        rec["current"] += 1
                        rec["total"] += 1
                        rec["consecutive_max"] = max(rec["consecutive_max"], rec["current"])
                    else:
                        rec["current"] = 0
                since_trough = k - cur["_trough_k"]
                # R1 higher low: the last higher_low_sessions closes all hold above the frozen trough
                if (lad["higher_low_confirmed_on"] is None and since_trough >= spec.higher_low_sessions
                        and n >= spec.higher_low_sessions
                        and min(closes_list[-spec.higher_low_sessions:]) > cur["correction_trough_price"]):
                    lad["higher_low_confirmed_on"] = day.isoformat()
                # R2 confirmed closes above the fast average, only after R1
                st["above_50"] = st["above_50"] + 1 if ma_fast is not None and c > ma_fast else 0
                if lad["reclaim_50d_on"] is None and st["above_50"] >= spec.confirm_sessions:
                    if lad["higher_low_confirmed_on"] is None:
                        cur["ladder_order_violations"].append(
                            {"rung": "reclaim_50d_on", "on": day.isoformat(), "missing": "higher_low_confirmed_on"})
                    else:
                        lad["reclaim_50d_on"] = day.isoformat()
                        cur["repair_floor_price"] = cur["correction_trough_price"]
                # R3 confirmed closes above the slow average, strictly after R2
                st["above_200"] = st["above_200"] + 1 if ma_slow is not None and c > ma_slow else 0
                if lad["reclaim_200d_on"] is None and st["above_200"] >= spec.confirm_sessions:
                    if lad["reclaim_50d_on"] is None:
                        cur["ladder_order_violations"].append(
                            {"rung": "reclaim_200d_on", "on": day.isoformat(), "missing": "reclaim_50d_on"})
                    elif lad["reclaim_50d_on"] < day.isoformat():
                        lad["reclaim_200d_on"] = day.isoformat()
                # R4 relative strength rising versus the benchmark and the leave-one-out basket, after R3
                rel_spy = rs / hist[-spec.rs_window - 1][2] - 1.0 if n > spec.rs_window else None
                st["rs_spy"] = st["rs_spy"] + 1 if rel_spy is not None and rel_spy > 0 else 0
                if (lad["rs_vs_spy_rising_on"] is None and st["rs_spy"] >= spec.confirm_sessions
                        and lad["reclaim_200d_on"] is not None):
                    lad["rs_vs_spy_rising_on"] = day.isoformat()
                if has_peers:
                    prev_basket = hist[-spec.rs_window - 1][3] if n > spec.rs_window else None
                    rel_peer = None
                    if basket is not None and prev_basket is not None and prev_basket > 0:
                        rel_peer = (rs / basket) / (hist[-spec.rs_window - 1][2] / prev_basket) - 1.0
                    st["rs_peer"] = st["rs_peer"] + 1 if rel_peer is not None and rel_peer > 0 else 0
                    cur["rs_vs_peer_basket"] = "RISING" if st["rs_peer"] > 0 else "NOT_RISING"
                    if (lad["rs_vs_peer_basket_rising_on"] is None and st["rs_peer"] >= spec.confirm_sessions
                            and lad["reclaim_200d_on"] is not None):
                        lad["rs_vs_peer_basket_rising_on"] = day.isoformat()
                else:
                    cur["rs_vs_peer_basket"] = "UNKNOWN"
                # ---- break classification, chronological and revisable
                if lad["reclaim_50d_on"] is not None and c < cur["repair_floor_price"]:
                    cur["phase"], cur["break_class"], cur["failed_on"] = "FAILED", "FAILED_BREAK", day.isoformat()
                    cur["structural_watch"] = False
                elif cur["phase"] == "DAMAGED":
                    deep_stay = cur["sessions_below_200"]["consecutive_max"] >= spec.structural_below_slow
                    cur["structural_watch"] = deep_stay and lad["reclaim_200d_on"] is None
                    if (deep_stay and lad["reclaim_200d_on"] is None and since_trough >= spec.horizon_sessions
                            and cur["break_class"] == "UNRESOLVED"):
                        cur["break_class"], cur["structural_on"] = "STRUCTURAL_BREAK", day.isoformat()
                    price_rungs = all(lad[r] for r in ("higher_low_confirmed_on", "reclaim_50d_on",
                                                       "reclaim_200d_on", "rs_vs_spy_rising_on"))
                    if price_rungs and not stalled_rungs and lad["rs_vs_peer_basket_rising_on"]:
                        if cur["break_class"] == "STRUCTURAL_BREAK":
                            cur["revised_from"], cur["revised_on"] = "STRUCTURAL_BREAK", day.isoformat()
                        cur["phase"], cur["break_class"] = "REPAIRED", "REPAIRED_TREND"
                        cur["structural_watch"] = False
                    elif price_rungs and stalled_rungs:
                        # price evidence complete but an owner input is missing: no verdict either way
                        cur["ladder_stalled"] = list(stalled_rungs)
                        if cur["break_class"] == "STRUCTURAL_BREAK":
                            cur["revised_from"], cur["revised_on"] = "STRUCTURAL_BREAK", day.isoformat()
                            cur["break_class"] = "UNRESOLVED"
                        cur["structural_watch"] = False
            if cur["phase"] != "ACTIVE":
                _apply_owner_evidence(cur, day, fundamentals, volume_demand, pivot)
            else:
                fund = _latest_owner_row(fundamentals, day)
                if fund is not None:
                    when, row = fund
                    state = str(row.get("state", "UNKNOWN")).upper()
                    cur["fundamental_deterioration"] = {
                        "state": "PRESENT" if state == "PRESENT" else "NONE" if state in ("NONE", "STABILIZED") else "UNKNOWN",
                        "source_ref": row.get("source_ref"), "as_of": when.isoformat()}
        if emit_rows:
            rows.append(_row(day, c, rs, ma_fast, ma_slow, cur, spec))
        elif k == len(calendar) - 1:
            rows.append(_row(day, c, rs, ma_fast, ma_slow, cur, spec))
    return rows, [_public(ep) for ep in episodes], len(calendar)


def _row(day: date, c: float, rs: float, ma_fast, ma_slow, cur: dict | None, spec: LineageSpec) -> dict:
    if cur is None:
        return {"as_of": day.isoformat(), "state": "NO_PRIOR_LEADER", "reason": "proxy_not_met",
                "thesis_state": "UNKNOWN", "setup_state": "WATCH", "break_class": None,
                "contradiction_evidence": [], "revisable": None,
                "episode": None, "price_ath": None, "rs_ath": None, "price": _num(c), "rs": _num(rs),
                "ma_fast": _num(ma_fast), "ma_slow": _num(ma_slow)}
    lad = cur["ladder"]
    evidence: list[str] = []
    if cur["fundamental_deterioration"]["state"] == "PRESENT":
        evidence.append("fundamental_deterioration_present")
    if cur["break_class"] == "STRUCTURAL_BREAK":
        evidence.append("structural_break_no_slow_reclaim_by_horizon")
    if evidence:
        thesis = "CONTRADICTED"
    elif cur["phase"] in ("DAMAGED", "FAILED"):
        # every price rung cleared but an owner input is missing: the thesis is unproven, never manufactured
        thesis = "UNKNOWN" if cur["ladder_stalled"] else "DAMAGED"
    elif cur["fundamental_deterioration"]["state"] == "NONE":
        thesis = "INTACT"
    else:
        thesis = "UNKNOWN"
    extended = ma_fast is not None and c > ma_fast * (1.0 + spec.extension_fraction)
    if cur["phase"] == "FAILED":
        setup = "INVALIDATED"
    elif cur["phase"] in ("ACTIVE", "REPAIRED"):
        setup = "EXTENDED" if extended else ("RE_IGNITION" if cur["phase"] == "REPAIRED" else "WATCH")
    elif lad["higher_low_confirmed_on"] or lad["reclaim_50d_on"]:
        setup = "REBUILDING"
    else:
        setup = "RESET"
    return {"as_of": day.isoformat(), "state": cur["phase"], "reason": None,
            "thesis_state": thesis, "setup_state": setup, "break_class": cur["break_class"],
            "contradiction_evidence": evidence, "revisable": cur["revisable"],
            "episode": _public(cur), "price_ath": _num(cur["price_ath"]), "rs_ath": _num(cur["rs_ath"]),
            "price": _num(c), "rs": _num(rs), "ma_fast": _num(ma_fast), "ma_slow": _num(ma_slow)}


# ----------------------------------------------------------------------------- replay / describe
def _replay(close, benchmark, *, as_of, sessions, ticker, peers, fundamentals, volume_demand, pivot, spec,
            emit_rows: bool = True):
    """Orchestrator: validate / source / trim, build the basket_mean callable, hand off to the core.
    Public surface unchanged — the universe helper takes a parallel code path."""
    fundamentals = list(fundamentals or ())
    volume_demand = list(volume_demand or ())
    try:
        cut = _date(as_of)
        calendar = [_date(d) for d in sessions]
        if calendar != sorted(set(calendar)) or not calendar or calendar[-1] != cut:
            raise ValueError("invalid_or_incomplete_calendar")
        prices, benches = _source(close, cut), _source(benchmark, cut)
        peer_src = {k: _source(v, cut) for k, v in (peers or {}).items() if k != ticker}
    except (TypeError, ValueError, OverflowError, AttributeError) as exc:
        day = as_of if type(as_of) is date else date.min
        return [_unavailable(day, str(exc))], [], 1
    starts = [min(d) for d in (prices, benches) if d]
    if len(starts) != 2:
        return [_unavailable(cut, "missing_source")], [], 1
    calendar = [d for d in calendar if d >= max(starts)]
    if not calendar:
        return [_unavailable(cut, "missing_source")], [], 1
    has_peers = bool(peer_src)
    if has_peers:
        peer_keys = list(peer_src.keys())
        def basket_mean(day):
            vals = [peer_src[k].get(day, math.nan) for k in peer_keys]
            if all(_finite(v) for v in vals):
                return sum(vals) / len(vals)
            return None
    else:
        def basket_mean(day):
            return None
    rows, episodes, n_sessions = _replay_core(
        ticker=ticker, prices=prices, benches=benches,
        has_peers=has_peers, basket_mean=basket_mean, calendar=calendar,
        fundamentals=fundamentals, volume_demand=volume_demand, pivot=pivot,
        spec=spec, emit_rows=emit_rows)
    return rows, episodes, n_sessions


def replay_lineage(
    close: pd.Series, benchmark: pd.Series, *, as_of: date, sessions: Iterable[date],
    ticker: str = "", peers: Mapping[str, pd.Series] | None = None,
    fundamentals: Iterable[dict] | None = None, volume_demand: Iterable[dict] | None = None,
    pivot: Mapping | None = None, spec: LineageSpec | None = None,
) -> list[dict]:
    """Replay the episode lineage on the caller's completed-session calendar; one row per session.

    Leadership qualification is the SAME transparent PRICE_RS_PROXY as ``leader_recovery``:
    a strict new RS high versus the previous ``high_window`` sessions, a positive
    ``high_window`` absolute return, and a close above the slow average. A deep correction
    (close drawdown >= ``deep_fraction`` from the episode's price ATH) opens the damaged
    phase with the correction peak and its RS frozen. Re-admission is a chronological
    ladder: R1 higher low -> R2 confirmed reclaim of the fast average -> R3 confirmed reclaim
    of the slow average (strictly after R2) -> R4 relative strength rising versus the benchmark
    AND versus the leave-one-out peer basket. R5-R7 are owner-dated and only reported.
    ``REPAIRED_TREND`` needs R1-R4 in order; ``STRUCTURAL_BREAK`` needs a below-slow stay of
    ``structural_below_slow`` sessions and no R3 by ``horizon_sessions`` after the trough;
    ``FAILED_BREAK`` is a close below the frozen repair floor (the trough) after R2. A missing
    peer basket stalls the ladder at R4b: the row says so and no verdict is manufactured.
    No forward fill: a missing or invalid session clears the rolling evidence and marks the
    episode history incomplete. A later qualification opens a NEW episode linked to this one.
    """
    rows, _, _ = _replay(close, benchmark, as_of=as_of, sessions=sessions, ticker=ticker, peers=peers,
                      fundamentals=fundamentals, volume_demand=volume_demand, pivot=pivot,
                      spec=spec or LineageSpec(), emit_rows=True)
    return rows


def _replay_core_direct(close, benchmark, *, as_of, sessions, ticker, peers, fundamentals, volume_demand,
                         pivot, spec, emit_rows):
    """Thin wrapper that returns (rows, episodes, n_sessions) so describe_lineage can report
    sessions_replayed == the trimmed-calendar length instead of len(rows). The orchestrator
    itself returns the same three-tuple to all callers."""
    return _replay(close, benchmark, as_of=as_of, sessions=sessions, ticker=ticker, peers=peers,
                   fundamentals=fundamentals, volume_demand=volume_demand, pivot=pivot, spec=spec,
                   emit_rows=emit_rows)


def describe_lineage(close: pd.Series, benchmark: pd.Series, *, as_of: date, sessions: Iterable[date],
                     ticker: str = "", source_ref: str | None = None, spec: LineageSpec | None = None,
                     **owner_inputs) -> dict:
    """Current lineage read at ``as_of`` plus every episode reconstructed from the history."""
    spec = spec or LineageSpec()
    rows, episodes, n_sessions = _replay_core_direct(close, benchmark, as_of=as_of, sessions=sessions,
                                                      ticker=ticker, peers=owner_inputs.get("peers"),
                                                      fundamentals=owner_inputs.get("fundamentals"),
                                                      volume_demand=owner_inputs.get("volume_demand"),
                                                      pivot=owner_inputs.get("pivot"), spec=spec,
                                                      emit_rows=False)
    current = deepcopy(rows[-1])
    fingerprint = _fingerprint(close, as_of, ticker, source_ref)
    current.update({"schema": SCHEMA, "era": ERA, "ticker": ticker, "evidence_mode": EVIDENCE_MODE,
                    "authority": dict(AUTHORITY), "definition_sha256": spec.digest,
                    "source_ref": source_ref, "source_fingerprint_sha256": fingerprint,
                    "episodes": episodes, "sessions_replayed": n_sessions})
    return current


# ----------------------------------------------------------------------------- universe
def _precompute_basket_arrays(src_dicts: dict, closes_keys: list, calendar: list[date]):
    """For every closes key, build per-day (has_basket, mean) arrays over the FULL calendar
    (calendar[-1] is the cut session). The mean is the leave-one-out sequential addition in
    closes insertion order — bit-identical to a python ``sum`` over the same ordered floats
    (np.add.accumulate is bit-identical; ``np.sum`` / ``math.fsum`` / total-minus-self are
    explicitly NOT acceptable per the lineage-enrol spec). Subjects whose own series raised
    during sourcing are recorded as ``has_basket[i] = False`` everywhere, so the universe
    helper does not need a separate invalid-set check."""
    n_days = len(calendar)
    n_keys = len(closes_keys)
    if n_keys == 0:
        return {}

    # vals_per_day[d, k] = closes_keys[k]'s value on calendar[d] (NaN when absent or non-finite)
    vals_per_day = np.full((n_days, n_keys), np.nan, dtype=float)
    for ki, key in enumerate(closes_keys):
        dct = src_dicts.get(key)
        if dct is None:
            continue
        for di, day in enumerate(calendar):
            v = dct.get(day, np.nan)
            if v is None or (isinstance(v, float) and (math.isnan(v) or v <= 0)):
                continue
            vals_per_day[di, ki] = float(v)

    basket_data: dict = {}
    for sidx in range(n_keys):
        if sidx == 0:
            leave = vals_per_day[:, 1:]
        elif sidx == n_keys - 1:
            leave = vals_per_day[:, :-1]
        else:
            leave = np.concatenate([vals_per_day[:, :sidx], vals_per_day[:, sidx + 1:]], axis=1)
        if leave.shape[1] == 0:
            basket_data[closes_keys[sidx]] = ([False] * n_days, [None] * n_days)
            continue
        has_basket = np.all(np.isfinite(leave) & (leave > 0), axis=1)
        seq_sums = np.zeros(n_days, dtype=float)
        if has_basket.any():
            seq_sums[has_basket] = np.add.accumulate(leave[has_basket], axis=1)[:, -1]
        means = np.where(has_basket, seq_sums / leave.shape[1], np.nan)
        basket_data[closes_keys[sidx]] = (has_basket.tolist(), means.tolist())
    return basket_data


def _make_basket_callable(calendar: list[date], has_basket: list[bool],
                          means: list[float | None]) -> Callable[[date], float | None]:
    day_to_idx = {d: i for i, d in enumerate(calendar)}

    def basket_mean(day):
        i = day_to_idx.get(day)
        if i is None:
            return None
        if not has_basket[i]:
            return None
        return means[i]

    return basket_mean


def describe_lineage_universe(closes: Mapping[str, pd.Series], benchmark: pd.Series, *,
                              as_of: date, sessions: Iterable[date],
                              tickers: Iterable[str] | None = None,
                              source_refs: Mapping[str, str | None] | None = None,
                              spec: LineageSpec | None = None) -> tuple[dict[str, dict], dict]:
    """Same descriptor as ``describe_lineage(..., peers=closes)`` for every subject in
    ``tickers`` (or ``list(closes.keys())`` when ``tickers`` is ``None``). The
    contract — JSON-equality for every subject — is tested in T1/T2.

    Optimization: validate cut/calendar once, source the benchmark and every closes series
    once (caching the exception), and precompute the leave-one-out basket per subject. The
    state machine still runs once per subject on a per-subject trimmed calendar, so every
    row byte matches a fresh ``describe_lineage`` call.

    No owner inputs are accepted here — the helper is purely structural. Caller-side
    fundamentals / volume / pivot rows must be merged into the descriptor at a downstream
    stage."""
    spec = spec or LineageSpec()
    closes_keys = list(closes.keys())
    if tickers is None:
        tickers = list(closes_keys)

    # 1. Validate cut/calendar once. On failure, every subject is UNAVAILABLE with the same reason.
    try:
        cut = _date(as_of)
        calendar = [_date(d) for d in sessions]
        if calendar != sorted(set(calendar)) or not calendar or calendar[-1] != cut:
            raise ValueError("invalid_or_incomplete_calendar")
    except (TypeError, ValueError, OverflowError, AttributeError) as exc:
        day = as_of if type(as_of) is date else date.min
        unavailable = _unavailable(day, str(exc))
        descs: dict[str, dict] = {}
        for t in tickers:
            ref = (source_refs or {}).get(t)
            desc = deepcopy(unavailable)
            desc.update({"schema": SCHEMA, "era": ERA, "ticker": t,
                         "evidence_mode": EVIDENCE_MODE, "authority": dict(AUTHORITY),
                         "definition_sha256": spec.digest, "source_ref": ref,
                         "source_fingerprint_sha256": _fingerprint(closes.get(t, pd.Series(dtype=float)),
                                                                   as_of, t, ref),
                         "episodes": [], "sessions_replayed": 1})
            descs[t] = desc
        coverage = {"issuers": len(tickers), "with_peer_basket": 0,
                    "with_fundamentals": 0, "with_volume_demand": 0, "with_pivot": 0}
        return descs, coverage

    # 2. Source the benchmark once.
    try:
        benches = _source(benchmark, cut)
    except (TypeError, ValueError, OverflowError, AttributeError) as exc:
        bench_exc_str: str | None = str(exc)
        benches = None
    else:
        bench_exc_str = None

    # 3. Source each closes entry once.
    src_dicts: dict[str, dict[date, float]] = {}
    src_errs: dict[str, str] = {}
    for k in closes_keys:
        try:
            src_dicts[k] = _source(closes[k], cut)
        except (TypeError, ValueError, OverflowError, AttributeError) as exc:
            src_errs[k] = str(exc)

    # 4. Precompute basket availability / leave-one-out means per subject.
    basket_data = _precompute_basket_arrays(src_dicts, closes_keys, calendar)

    descs = {}
    with_peer_basket = 0
    for t in tickers:
        ref = (source_refs or {}).get(t)
        # Per spec order: cut/calendar (handled above), subject's own sourcing, benchmark,
        # FIRST raising peer in closes insertion order excluding subject.
        if t in src_errs:
            unavailable = _unavailable(cut, src_errs[t])
            subject_prices: dict[date, float] = {}
            trimmed_calendar: list[date] = []
            has_peers = bool(closes_keys) and (len(closes_keys) - (1 if t in closes_keys else 0)) > 0
            basket_mean_fn = _make_basket_callable(calendar, [False] * len(calendar),
                                                  [None] * len(calendar))
            n_sessions = 1
            episodes: list = []
            rows = [unavailable]
        elif bench_exc_str is not None:
            unavailable = _unavailable(cut, bench_exc_str)
            subject_prices = src_dicts.get(t, {})
            trimmed_calendar = []
            has_peers = bool(closes_keys) and (len(closes_keys) - (1 if t in closes_keys else 0)) > 0
            basket_mean_fn = _make_basket_callable(calendar, [False] * len(calendar),
                                                  [None] * len(calendar))
            n_sessions = 1
            episodes = []
            rows = [unavailable]
        else:
            # Subject's own source is fine and the benchmark is fine. Look for the first
            # raising peer in closes insertion order excluding the subject.
            peer_exc: str | None = None
            for k in closes_keys:
                if k == t:
                    continue
                if k in src_errs:
                    peer_exc = src_errs[k]
                    break
            if peer_exc is not None:
                unavailable = _unavailable(cut, peer_exc)
                subject_prices = src_dicts.get(t, {})
                trimmed_calendar = []
                has_peers = bool(closes_keys) and (len(closes_keys) - (1 if t in closes_keys else 0)) > 0
                basket_mean_fn = _make_basket_callable(calendar, [False] * len(calendar),
                                                      [None] * len(calendar))
                n_sessions = 1
                episodes = []
                rows = [unavailable]
            else:
                # All sources clean. Build peer_src + per-subject trimmed calendar.
                subject_prices = src_dicts.get(t, {})
                peer_src = {k: src_dicts[k] for k in closes_keys if k != t}
                has_peers = len(peer_src) > 0
                starts = [min(d) for d in (subject_prices, benches) if d]
                if len(starts) != 2:
                    unavailable = _unavailable(cut, "missing_source")
                    subject_prices = {}
                    trimmed_calendar = []
                    basket_mean_fn = _make_basket_callable(calendar, [False] * len(calendar),
                                                          [None] * len(calendar))
                    n_sessions = 1
                    episodes = []
                    rows = [unavailable]
                else:
                    trimmed_calendar = [d for d in calendar if d >= max(starts)]
                    if not trimmed_calendar:
                        unavailable = _unavailable(cut, "missing_source")
                        subject_prices = {}
                        trimmed_calendar = []
                        basket_mean_fn = _make_basket_callable(calendar, [False] * len(calendar),
                                                              [None] * len(calendar))
                        n_sessions = 1
                        episodes = []
                        rows = [unavailable]
                    else:
                        has_basket, means = basket_data.get(t, ([False] * len(calendar),
                                                                [None] * len(calendar)))
                        basket_mean_fn = _make_basket_callable(calendar, has_basket, means)
                        rows, episodes, n_sessions = _replay_core(
                            ticker=t, prices=subject_prices, benches=benches,
                            has_peers=has_peers, basket_mean=basket_mean_fn,
                            calendar=trimmed_calendar,
                            fundamentals=[], volume_demand=[], pivot=None,
                            spec=spec, emit_rows=False)

        current = deepcopy(rows[-1])
        # Count subjects whose leave-one-out basket exists on the cut session (calendar[-1]).
        has_basket_t, _ = basket_data.get(t, ([False] * len(calendar), [None] * len(calendar)))
        if has_basket_t and has_basket_t[-1] and t not in src_errs and bench_exc_str is None:
            with_peer_basket += 1
        fingerprint = _fingerprint(closes.get(t, pd.Series(dtype=float)), as_of, t, ref)
        current.update({"schema": SCHEMA, "era": ERA, "ticker": t,
                        "evidence_mode": EVIDENCE_MODE, "authority": dict(AUTHORITY),
                        "definition_sha256": spec.digest, "source_ref": ref,
                        "source_fingerprint_sha256": fingerprint,
                        "episodes": episodes, "sessions_replayed": n_sessions})
        descs[t] = current

    coverage = {"issuers": len(tickers), "with_peer_basket": with_peer_basket,
                "with_fundamentals": 0, "with_volume_demand": 0, "with_pivot": 0}
    return descs, coverage


# ----------------------------------------------------------------------------- chips
def lineage_chip(descriptor: Mapping) -> dict:
    """Pure projection of one descriptor onto the ship-merge chip surface. A fresh
    ``authority`` is always present (the module constant is never reused); every other
    value is a deep copy or ``None`` when the key is absent."""
    out: dict = {}
    for k in _CHIP_KEYS:
        v = descriptor.get(k)
        out[k] = deepcopy(v) if v is not None else None
    out["authority"] = dict(AUTHORITY)
    return out


def lineage_roster(descriptors: Mapping[str, Mapping], coverage: Mapping, *, as_of: str) -> dict:
    """Flatten a universe of descriptors into the ship-merge roster shape. Counts every
    ROSTER_COUNT_STATES key (zero when absent), so counts sum to the issuer census; every episode gets its ladder reclaim dates surfaced.
    Raises ``ValueError("mixed_definition_digest")`` when descriptors disagree on
    ``definition_sha256``; falls back to ``LineageSpec().digest`` when ``descriptors`` is empty."""
    spec_default = LineageSpec()
    digests = {d.get("definition_sha256") for d in descriptors.values() if d.get("definition_sha256")}
    if not digests:
        definition_sha256 = spec_default.digest
    else:
        if len(digests) > 1:
            raise ValueError("mixed_definition_digest")
        definition_sha256 = next(iter(digests))

    counts = {k: 0 for k in ROSTER_COUNT_STATES}
    for desc in descriptors.values():
        state = desc.get("state")
        if state in counts:
            counts[state] += 1

    episodes: list[dict] = []
    for ticker, desc in descriptors.items():
        for ep in desc.get("episodes") or []:
            lad = ep.get("ladder") or {}
            episodes.append({
                "ticker": ticker,
                "episode_id": ep.get("episode_id"),
                "prior_episode_id": ep.get("prior_episode_id"),
                "leadership_qualified_at": ep.get("leadership_qualified_at"),
                "phase": ep.get("phase"),
                "break_class": ep.get("break_class"),
                "correction_trough_on": ep.get("correction_trough_on"),
                "reclaim_50d_on": lad.get("reclaim_50d_on"),
                "reclaim_200d_on": lad.get("reclaim_200d_on"),
                "closed_on": ep.get("closed_on"),
                "close_reason": ep.get("close_reason"),
            })

    return {"schema": SCHEMA, "era": ERA, "as_of": as_of,
            "definition_sha256": definition_sha256, "evidence_mode": EVIDENCE_MODE,
            "authority": dict(AUTHORITY),
            "episodes": episodes, "counts": counts, "coverage": dict(coverage)}