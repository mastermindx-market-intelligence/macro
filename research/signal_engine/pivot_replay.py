"""Read-only reporting over the canonical bottom ruler; never a second ledger.

As-issued describes the call receipts, not unproven historical price vintages.
Reconstructed calls remain retrospective. No signal generation or trade authority.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime
import math
import re
from statistics import median
from zoneinfo import ZoneInfo
from typing import Any, Mapping
import pandas as pd

_NY = ZoneInfo("America/New_York")
_NUMBERS = ("prox", "t_off", "undercut", "mfe60", "mae60", "fwd60")


def _stamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except (ValueError, TypeError):
        return None


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _finite(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def evaluate_pivot_calls(calls: list[dict], panels: Mapping[str, pd.DataFrame], *,
                         evaluation_at: str, mode: str = "as_issued", grader=None) -> dict:
    """Preserve every submitted call and delegate frozen 60-session arithmetic.

    Daily price labels are civil session dates, following the existing ruler.
    Evaluation excludes the current NY date: a same-day final close must not be
    silently assumed available. This is deliberately conservative at maturity.
    """
    cutoff = _stamp(evaluation_at)
    result = {"schema": "bottom_pivot_replay.v1", "mode": mode,
              "evaluation_at": evaluation_at if isinstance(evaluation_at, str) else None,
              "naturally_observed": None if mode == "as_issued" else False, "retrospective": mode != "as_issued",
              "authority": "research_only", "predictions_qualified": False,
              "grade_owner": "engine.bottom_ruler.grade_call", "calls": [],
              "limitations": ["event_census_not_supplied", "no_dead_money_definition",
                  "correlated_calls_not_independent", "outcome_panel_vintage_not_attested",
                  "current_session_excluded", "mfe_is_not_realized_return",
                  "receipt_provenance_not_authenticated"], "error": None}
    if cutoff is None or mode not in ("as_issued", "reconstructed_price_history") or not isinstance(calls, list) or not isinstance(panels, Mapping):
        result.update(error="invalid_evaluation_contract", naturally_observed=False, summary=None)
        return result
    if grader is None:
        from engine.bottom_ruler import grade_call
        grader = grade_call
    ids = Counter(x.get("id") for x in calls if isinstance(x, dict) and isinstance(x.get("id"), str))
    try:
        cutoff_day = cutoff.astimezone(_NY).date()
    except (OverflowError, ValueError):
        result.update(error="invalid_evaluation_contract", naturally_observed=False, summary=None)
        return result

    def evaluate(call: Any) -> dict:
        raw = call if isinstance(call, dict) else {}
        row = {k: raw.get(k) if isinstance(raw.get(k), str) else None
               for k in ("id", "symbol", "signal_date", "source_revision", "price_basis", "episode_id")}
        row.update(status="invalid_call", grade=None)
        if not all(row[k] and row[k].strip() for k in ("id", "symbol", "source_revision", "price_basis")):
            return row
        if ids[row["id"]] != 1:
            row["status"] = "conflict"; return row
        day = _date(row["signal_date"])
        if day is None:
            return row
        if day >= cutoff_day:
            row["status"] = "future_or_incomplete_session"; return row
        available = _stamp(raw.get("available_at"))
        if raw.get("available_at") is not None and available is None:
            row["status"] = "invalid_availability"; return row
        if available is not None and available > cutoff:
            row["status"] = "future_availability"; return row
        if mode == "as_issued":
            if available is None:
                row["status"] = "not_known"; return row
            try:
                local_available = available.astimezone(_NY)
            except (OverflowError, ValueError):
                row["status"] = "invalid_availability"; return row
            if local_available.date() != day:
                row["status"] = "delayed_issuance_requires_execution_model"; return row
            if local_available.hour < 16:
                row["status"] = "daily_close_not_yet_qualified"; return row
        panel = panels.get(row["symbol"])
        if not isinstance(panel, pd.DataFrame) or "close" not in panel:
            row["status"] = "price_missing"; return row
        if panel.attrs.get("price_basis") != row["price_basis"]:
            row["status"] = "basis_mismatch"; return row
        if not isinstance(panel.index, pd.DatetimeIndex) or panel.index.hasnans:
            row["status"] = "invalid_price_index"; return row
        # Restrict before validation/grading so later rows cannot influence it.
        data = panel.loc[[x.date() < cutoff_day for x in panel.index]]
        dates = [x.date() for x in data.index]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            row["status"] = "invalid_price_index"; return row
        if day not in dates:
            row["status"] = "price_missing"; return row
        try:
            if data["close"].map(lambda x: isinstance(x, bool)).any() or pd.api.types.is_bool_dtype(data["close"].dtype):
                row["status"] = "invalid_prices"; return row
            c = pd.to_numeric(data["close"], errors="raise")
            if c.isna().any() or not all(math.isfinite(float(x)) and float(x) > 0 for x in c):
                row["status"] = "invalid_prices"; return row
        except (TypeError, ValueError, OverflowError):
            row["status"] = "invalid_prices"; return row
        i = dates.index(day)
        if i < 10:
            row["status"] = "insufficient_history"; return row
        if i + 60 >= len(c):
            row["status"] = "immature"; return row
        hi = lo = None
        if "high" in data and "low" in data:
            try:
                h, l = pd.to_numeric(data["high"], errors="raise"), pd.to_numeric(data["low"], errors="raise")
                # The frozen ruler also uses the preceding 20-session floor.
                relevant = slice(max(0, i - 19), i + 61)
                ok = all(math.isfinite(float(a)) and math.isfinite(float(b)) and 0 < b <= float(close) <= a
                         for a, b, close in zip(h.iloc[relevant], l.iloc[relevant], c.iloc[relevant]))
                if ok:
                    hi, lo = h, l
            except (TypeError, ValueError, OverflowError):
                pass
        row["price_range_basis"] = "ohlc" if hi is not None else "close_only"
        try:
            grade = grader(c, hi, lo, row["signal_date"])
        except Exception:
            row["status"] = "grade_error"; return row
        if grade is None:
            row["status"] = "ungradable"; return row
        if not isinstance(grade, dict) or not all(_finite(grade.get(k)) for k in _NUMBERS) or grade.get("undercut_class") not in ("held", "probed", "deep", "broke") or grade.get("basis") not in ("ohlc", "close_only"):
            row["status"] = "invalid_grade"; return row
        row["grade"] = {k: grade[k] for k in (*_NUMBERS, "undercut_class", "basis")}
        row["status"] = "graded"
        return row

    result["calls"] = [evaluate(call) for call in calls]
    graded = [r for r in result["calls"] if r["status"] == "graded"]
    n, ng = len(calls), len(graded)
    ni = sum(r["status"] == "immature" for r in result["calls"])
    episodes = {r["episode_id"] for r in graded if r["episode_id"]}
    summary = {"n_submitted": n, "n_graded": ng, "n_immature": ni,
               "n_unavailable": n - ng - ni,
               "n_distinct_signal_dates": len({r["signal_date"] for r in graded}),
               "n_declared_episodes": len(episodes) if episodes else None,
               "availability_fraction": ng / n if n else None,
               "event_recall": None, "false_positive_rate": None, "dead_money_rate": None}
    for name in ("prox", "mae60", "mfe60", "undercut"):
        summary[name + "_median"] = median(r["grade"][name] for r in graded) if ng else None
    for name, predicate in (("pinpoint_fraction", lambda g: g["prox"] <= .05),
                            ("floor_held_fraction", lambda g: g["undercut"] <= .005),
                            ("floor_broke_fraction", lambda g: g["undercut"] > .10)):
        summary[name] = sum(predicate(r["grade"]) for r in graded) / ng if ng else None
    result["summary"] = summary
    return result
