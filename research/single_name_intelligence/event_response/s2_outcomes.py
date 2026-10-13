"""S2 outcomes: windows, leg returns, decision-time direction, INFO-LEAK scan.

Prices are read ONLY here (runner phase), only for the graded US leg
(data/yahoo/BABA.parquet) and its bench (data/yahoo/SPY.parquet), only through
the pinned-blob loader, and only the columns Date, close (adjusted total
return), close_price (raw). Volume is never read.

Window law (E4): entry_anchor = the calendar day before s_US;
resolve_horizon_window(entry_anchor, h, HORIZON_UNIT_TRADING, MARKET_US);
assert fill_date == s_US (else ABSTAIN_FILL_MISMATCH; None ->
ABSTAIN_RESOLVER_NONE). Leg return = close(coverage)/close(fill) - 1 with both
endpoint bars present on exactly those sessions (else ABSTAIN_MISSING_ENDPOINT).
excess = BABA - SPY. D(s) = last NYSE session before s_US; every decision-time
quantity uses bars <= D(s); the day-s move is excluded and disclosed.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from engine.qledger import (MARKET_US, HORIZON_UNIT_TRADING,
                            resolve_horizon_window)
import lib.nyse_calendar as nyse_calendar

ABSTAIN_RESOLVER_NONE = "ABSTAIN_RESOLVER_NONE"
ABSTAIN_FILL_MISMATCH = "ABSTAIN_FILL_MISMATCH"
ABSTAIN_MISSING_ENDPOINT = "ABSTAIN_MISSING_ENDPOINT"

BABA_PATH = "data/yahoo/BABA.parquet"
SPY_PATH = "data/yahoo/SPY.parquet"
PRICE_COLUMNS = ("Date", "close", "close_price")
INFO_LEAK_STEP_TOLERANCE = 1e-6
TRAILING63_SESSIONS = 63


def _close_series(df: pd.DataFrame, column: str) -> pd.Series:
    if "Date" in df.columns:
        s = df.set_index("Date")[column]
    else:  # Date is the store's INDEX
        s = df.rename_axis("Date")[column]
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


class OutcomeEngine:
    """Price-phase engine for the graded US leg (BABA vs SPY)."""

    def __init__(self, loader) -> None:
        self.loader = loader
        self.baba = loader.read_parquet(BABA_PATH, columns=PRICE_COLUMNS)
        self.spy = loader.read_parquet(SPY_PATH, columns=PRICE_COLUMNS)
        self.baba_close = _close_series(self.baba, "close")
        self.spy_close = _close_series(self.spy, "close")
        self.baba_close_price = _close_series(self.baba, "close_price")
        self.spy_close_price = _close_series(self.spy, "close_price")
        self.nyse_sessions = sorted(
            pd.to_datetime(self.baba_close.index).date.tolist())
        self.last_bar_date = max(self.nyse_sessions)

    # -- windows and leg returns ------------------------------------------- #
    def resolve_window(self, s_us: date, h: int):
        anchor = s_us - timedelta(days=1)
        return resolve_horizon_window(anchor, h, HORIZON_UNIT_TRADING, MARKET_US)

    def leg_return(self, series: pd.Series, fill: date, coverage: date) -> float | None:
        try:
            e0 = series.loc[pd.Timestamp(fill)]
            e1 = series.loc[pd.Timestamp(coverage)]
        except KeyError:
            return None
        if not e0 or not e1:
            return None
        return float(e1) / float(e0) - 1.0

    def episode_excess(self, s_us: date, h: int) -> dict:
        """The graded outcome of one episode-leg at one horizon, or its
        abstention token (fail closed, never a fill)."""
        w = self.resolve_window(s_us, h)
        if w is None:
            return {"state": ABSTAIN_RESOLVER_NONE, "window": None}
        if w.fill_date != s_us:
            return {"state": ABSTAIN_FILL_MISMATCH, "window": {
                "fill_date": w.fill_date.isoformat(),
                "coverage_date": w.coverage_date.isoformat(),
                "expected_fill": s_us.isoformat()}}
        subj = self.leg_return(self.baba_close, w.fill_date, w.coverage_date)
        bench = self.leg_return(self.spy_close, w.fill_date, w.coverage_date)
        if subj is None or bench is None:
            return {"state": ABSTAIN_MISSING_ENDPOINT, "window": {
                "fill_date": w.fill_date.isoformat(),
                "coverage_date": w.coverage_date.isoformat()}}
        return {"state": "OK", "window": {
            "fill_date": w.fill_date.isoformat(),
            "coverage_date": w.coverage_date.isoformat(),
            "entry_note": "entry close ON fill_date (= s); the day-s move is excluded and disclosed"},
            "subject_ret": round(subj, 10), "bench_ret": round(bench, 10),
            "excess": round(subj - bench, 10)}

    # -- decision-time direction (baseline ii) ------------------------------ #
    def trailing63_direction(self, s_us: date) -> int:
        """Sign of the trailing-63-session excess at D(s): exact bars on D and
        D63 for BOTH legs, else 0 (0 -> ABSTAIN). D = last NYSE session before
        s_US on the CALENDAR (the store never defines a session); D63 = the
        session exactly 63 sessions before D."""
        d = s_us - timedelta(days=1)
        while not nyse_calendar.is_session(d):
            d -= timedelta(days=1)
        # walk back 63 sessions on the calendar
        d63 = d
        seen = 0
        while seen < TRAILING63_SESSIONS:
            d63 -= timedelta(days=1)
            if nyse_calendar.is_session(d63):
                seen += 1
        try:
            b0 = float(self.baba_close.loc[pd.Timestamp(d)])
            b1 = float(self.baba_close.loc[pd.Timestamp(d63)])
            s0 = float(self.spy_close.loc[pd.Timestamp(d)])
            s1 = float(self.spy_close.loc[pd.Timestamp(d63)])
        except KeyError:
            return 0
        if not all((b0, b1, s0, s1)):
            return 0
        excess = (b1 / b0 - 1.0) - (s1 / s0 - 1.0)
        return 1 if excess > 0 else (-1 if excess < 0 else 0)

    # -- E10 A23 INFO-LEAK predicate ----------------------------------------- #
    def info_leak_scan(self, first_tune_anchor: date | None) -> dict:
        """q_t = close_t / close_price_t per series; any |q_t/q_{t-1} - 1| >
        1e-6 on a date >= the earliest TUNE anchor and <= the last input bar."""
        out: dict = {"scanned": bool(first_tune_anchor is not None),
                     "first_tune_anchor": first_tune_anchor.isoformat() if first_tune_anchor else None,
                     "last_bar": self.last_bar_date.isoformat(),
                     "series": {}}
        if first_tune_anchor is None:
            return out
        lo = pd.Timestamp(first_tune_anchor)
        for name, close, raw in (("BABA", self.baba_close, self.baba_close_price),
                                 ("SPY", self.spy_close, self.spy_close_price)):
            common = close.index.intersection(raw.index)
            q = (close.loc[common] / raw.loc[common])
            q = q[q.index >= lo]
            steps = (q / q.shift(1) - 1.0).abs().dropna()
            offenders = steps[steps > INFO_LEAK_STEP_TOLERANCE]
            out["series"][name] = {
                "first_offending_date": (offenders.index[0].date().isoformat()
                                         if len(offenders) else None),
                "steps_above_tolerance": int(len(offenders)),
                "max_abs_step": (round(float(steps.max()), 12)
                                 if len(steps) else None),
            }
        out["leak"] = any(v["steps_above_tolerance"] > 0
                          for v in out["series"].values())
        return out
