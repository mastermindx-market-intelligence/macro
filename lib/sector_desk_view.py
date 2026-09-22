"""Display-only navigation for Macro's rising opportunity desk.

Consume Sector Pulse observations; never change its scores, heat tiers, stock
recommendations, or allocation. Existing Enter/Accumulate ratings determine
opportunity eligibility; five-session rank improvement orders those desks for
further research. The latest session breaks a tie only when every co-leader has
that observation. This is not an opportunity forecast or a fund-inflow measure.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta, timezone
from numbers import Real
from typing import Any

from lib.nyse_calendar import ET, is_session, session_n_back, sessions_behind

_THEME_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}\Z")


def _rank_delta(value: Any) -> int | None:
    """JSON rank changes are integral observations; null is never zero."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
        return int(number) if math.isfinite(number) and number.is_integer() else None
    except (ValueError, OverflowError):
        return None


def opportunity_desk(
    heating: list[dict[str, Any]],
    as_of: Any,
    *,
    history: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Select among existing positive ratings in the FULL heating population.

    Reuse the NYSE calendar, including weekends/holidays and the settlement buffer.
    A dated one-session lag accommodates the daily publication lane. Two missing
    completed sessions suppress the leader instead of calling old data current.
    A remaining tie, absent history, malformed date, or invalid theme is neutral.
    No input object is mutated, and no score or trading recommendation is created.
    """
    out: dict[str, Any] = {
        "status": "unavailable", "leader": None, "as_of": None,
        "as_of_label": None, "sessions_behind": None, "href": "sector_central.html",
    }
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    today = now.astimezone(ET).date()
    try:
        if not isinstance(as_of, str) or len(as_of) != 10:
            return out
        day = date.fromisoformat(as_of)
        if day > today or not is_session(day):
            return out
    except ValueError:
        return out
    out.update(as_of=day.isoformat(), as_of_label=f"{day:%b} {day.day}")
    # Bound calendar work for very old/corrupt artifacts; do not walk decades.
    if day < today - timedelta(days=14):
        out["status"] = "stale"
        return out
    behind = sessions_behind(day, now)
    out["sessions_behind"] = behind
    if behind > 1:
        out["status"] = "stale"
        return out

    # Older producers used archive row positions as days. Fail closed until the
    # canonical producer proves the exact comparison date (#7650); do not silently
    # relabel those old observations as true five-session opportunity momentum.
    history = history if isinstance(history, dict) else {}
    expected = history.get("expected_comparison_as_of") or {}
    observed = history.get("comparison_as_of") or {}
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        return out
    target_five = session_n_back(day, 5)
    target_one = session_n_back(day, 1)
    if (history.get("basis") != "nyse_sessions" or target_five is None
            or expected.get("5d") != target_five.isoformat()
            or observed.get("5d") != target_five.isoformat()):
        return out
    latest_session_known = (target_one is not None
                            and observed.get("1d") == target_one.isoformat()
                            and expected.get("1d") == target_one.isoformat())

    candidates: list[dict[str, Any]] = []
    for row in heating if isinstance(heating, list) else []:
        if not isinstance(row, dict) or row.get("heat") != "heating":
            continue
        recommendation = row.get("reco")
        if not isinstance(recommendation, str) or recommendation not in {"enter", "accumulate"}:
            continue
        key = row.get("id")
        five = _rank_delta(row.get("rank_delta_5d"))
        if not isinstance(key, str) or not _THEME_ID.fullmatch(key) or five is None or five <= 0:
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            name = key.replace("_", " ").replace("-", " ").title()
        zh = row.get("name_zh")
        candidates.append({
            "id": key, "name": name, "name_zh": zh if isinstance(zh, str) and zh else name,
            "reco": row["reco"],
            "reco_en": "Accumulate" if row["reco"] == "accumulate" else "Enter",
            "reco_zh": "增持" if row["reco"] == "accumulate" else "入场",
            "rank_delta_5d": five, "rank_delta_1d": (_rank_delta(row.get("rank_delta_1d"))
                              if latest_session_known else None),
        })
    if not candidates:
        return out
    best_five = max(row["rank_delta_5d"] for row in candidates)
    leaders = [row for row in candidates if row["rank_delta_5d"] == best_five]
    if len(leaders) > 1 and all(row["rank_delta_1d"] is not None for row in leaders):
        best_one = max(row["rank_delta_1d"] for row in leaders)
        leaders = [row for row in leaders if row["rank_delta_1d"] == best_one]
    if len(leaders) != 1:
        out["status"] = "tied"
        return out
    leader = leaders[0]
    out.update(status="ready", leader=leader, href=f"basket/{leader['id']}.html")
    return out
