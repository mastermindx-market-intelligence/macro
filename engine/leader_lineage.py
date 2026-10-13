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
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
from typing import Iterable, Mapping

import pandas as pd

SCHEMA = "leader_lineage.v1"
ERA = "leader-lineage-descriptive-2026-10-11"
EVIDENCE_MODE = "RECONSTRUCTED_CURRENT_VINTAGE"
AUTHORITY = {k: False for k in ("may_rank", "may_gate", "may_size", "may_trade", "may_alert")}
THESIS_STATES = ("INTACT", "DAMAGED", "CONTRADICTED", "UNKNOWN")
SETUP_STATES = ("WATCH", "RESET", "REBUILDING", "RE_IGNITION", "EXTENDED", "INVALIDATED")
BREAK_CLASSES = ("FAILED_BREAK", "STRUCTURAL_BREAK", "REPAIRED_TREND", "UNRESOLVED")
PHASES = ("ACTIVE", "DAMAGED", "REPAIRED", "FAILED")
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


def _source(series: pd.Series, cut: date) -> dict[date, float]:
    """Completed sessions at or before the cut. Duplicate dates and boolean prices raise;
    a non-numeric value becomes nan (a gap), never a carried-forward value."""
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


# ----------------------------------------------------------------------------- replay
def _replay(close, benchmark, *, as_of, sessions, ticker, peers, fundamentals, volume_demand, pivot, spec):
    fundamentals = list(fundamentals or ())
    volume_demand = list(volume_demand or ())
    try:
        cut = _date(as_of)
        # The caller's completed-session calendar must be strictly increasing and END at as_of:
        # a session dated after as_of is a contradiction, never silently dropped (sources may
        # extend past as_of; they are cut, the calendar is not).
        calendar = [_date(d) for d in sessions]
        if calendar != sorted(set(calendar)) or not calendar or calendar[-1] != cut:
            raise ValueError("invalid_or_incomplete_calendar")
        prices, benches = _source(close, cut), _source(benchmark, cut)
        peer_src = {k: _source(v, cut) for k, v in (peers or {}).items() if k != ticker}
    except (TypeError, ValueError, OverflowError, AttributeError) as exc:
        day = as_of if type(as_of) is date else date.min
        return [_unavailable(day, str(exc))], []
    starts = [min(d) for d in (prices, benches) if d]
    if len(starts) != 2:
        return [_unavailable(cut, "missing_source")], []
    calendar = [d for d in calendar if d >= max(starts)]
    if not calendar:
        return [_unavailable(cut, "missing_source")], []
    stalled_rungs = [] if peer_src else ["rs_vs_peer_basket_rising_on"]

    hist: list[tuple[date, float, float, float | None]] = []   # (day, close, rs, basket_rs)
    episodes: list[dict] = []
    cur: dict | None = None
    rows: list[dict] = []

    for k, day in enumerate(calendar):
        c, b = prices.get(day, math.nan), benches.get(day, math.nan)
        if not (_finite(c) and _finite(b)):
            hist.clear()
            if cur is not None:
                cur["history_complete"] = False
                cur["_streaks"] = {key: 0 for key in cur["_streaks"]}
            rows.append(_unavailable(day, "missing_or_invalid_completed_session"))
            continue
        rs = c / b
        basket = None
        if peer_src:
            vals = [src.get(day, math.nan) for src in peer_src.values()]
            if all(_finite(v) for v in vals):
                basket = (sum(vals) / len(vals)) / b
        hist.append((day, c, rs, basket))
        n = len(hist)
        closes = [h[1] for h in hist]
        ma_fast = sum(closes[-spec.fast_window:]) / spec.fast_window if n >= spec.fast_window else None
        ma_slow = sum(closes[-spec.slow_window:]) / spec.slow_window if n >= spec.slow_window else None
        qualified = False
        if n > spec.high_window and ma_slow is not None:
            window = hist[-spec.high_window - 1:-1]
            qualified = (rs > max(h[2] for h in window) and c > hist[-spec.high_window - 1][1]
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
                        and min(closes[-spec.higher_low_sessions:]) > cur["correction_trough_price"]):
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
                if peer_src:
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
        rows.append(_row(day, c, rs, ma_fast, ma_slow, cur, spec))
    return rows, [_public(ep) for ep in episodes]


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
    rows, _ = _replay(close, benchmark, as_of=as_of, sessions=sessions, ticker=ticker, peers=peers,
                      fundamentals=fundamentals, volume_demand=volume_demand, pivot=pivot,
                      spec=spec or LineageSpec())
    return rows


def describe_lineage(close: pd.Series, benchmark: pd.Series, *, as_of: date, sessions: Iterable[date],
                     ticker: str = "", source_ref: str | None = None, spec: LineageSpec | None = None,
                     **owner_inputs) -> dict:
    """Current lineage read at ``as_of`` plus every episode reconstructed from the history."""
    spec = spec or LineageSpec()
    rows, episodes = _replay(close, benchmark, as_of=as_of, sessions=sessions, ticker=ticker,
                             peers=owner_inputs.get("peers"), fundamentals=owner_inputs.get("fundamentals"),
                             volume_demand=owner_inputs.get("volume_demand"), pivot=owner_inputs.get("pivot"),
                             spec=spec)
    current = deepcopy(rows[-1])
    try:
        closes = [[k.isoformat(), _num(v)] for k, v in _source(close, _date(as_of)).items()]
    except (TypeError, ValueError, AttributeError):
        closes = None
    fingerprint = hashlib.sha256(json.dumps({"ticker": ticker, "as_of": str(as_of), "source_ref": source_ref,
                                             "close": closes}, sort_keys=True, default=str).encode()).hexdigest()
    current.update({"schema": SCHEMA, "era": ERA, "ticker": ticker, "evidence_mode": EVIDENCE_MODE,
                    "authority": dict(AUTHORITY), "definition_sha256": spec.digest,
                    "source_ref": source_ref, "source_fingerprint_sha256": fingerprint,
                    "episodes": episodes, "sessions_replayed": len(rows)})
    return current
