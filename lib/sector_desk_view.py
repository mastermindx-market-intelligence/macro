"""Display-only navigation for Macro's hottest sector desk.

Consume Sector Pulse observations; never change its scores, heat tiers, stock
recommendations, allocation, or trade authority. The primary card answers one
descriptive question: which producer-declared heating desk has the strongest
verified five-session rank acceleration? Entry/recommendation state is carried
alongside that leadership read and must never suppress it.

A separate ``positive_rating_leader`` preserves the strongest Enter/Accumulate
comparison for consumers that need positive-recommendation context. It is not an
entry decision. Neither read is a fund-flow measure, a forecast, or a buy instruction.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta, timezone
from numbers import Real
from typing import Any

from lib.nyse_calendar import ET, is_session, session_n_back, sessions_behind

_THEME_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,95}\Z")

_RATING_COPY: dict[str, tuple[str, str, bool]] = {
    "enter": ("Enter", "入场", True),
    "accumulate": ("Accumulate", "增持", True),
    "hold": ("Hold", "持有", False),
    "trim": ("Trim", "减持", False),
    "avoid": ("Avoid", "回避", False),
    "exit": ("Exit", "退出", False),
}


def _rank_delta(value: Any) -> int | None:
    """JSON rank changes are integral observations; null is never zero."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
        return int(number) if math.isfinite(number) and number.is_integer() else None
    except (ValueError, OverflowError):
        return None


def _pick_unique_velocity(rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    """Pick the largest 5-session rise, then the latest session only if complete."""
    if not rows:
        return None, "unavailable"
    best_five = max(row["rank_delta_5d"] for row in rows)
    leaders = [row for row in rows if row["rank_delta_5d"] == best_five]
    if len(leaders) > 1 and all(row["rank_delta_1d"] is not None for row in leaders):
        best_one = max(row["rank_delta_1d"] for row in leaders)
        leaders = [row for row in leaders if row["rank_delta_1d"] == best_one]
    if len(leaders) != 1:
        return None, "tied"
    return leaders[0], "ready"


def opportunity_desk(
    heating: list[dict[str, Any]],
    as_of: Any,
    *,
    history: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return descriptive leadership plus separate positive-rating context.

    The public function name is retained for compatibility with the existing
    dashboard adapter. ``leader`` is the hottest verified heating desk regardless
    of recommendation verb. ``positive_rating_leader`` is separately constrained
    to incumbent Enter/Accumulate verbs without claiming executable entry.

    Reuse the NYSE calendar, including weekends/holidays and the settlement buffer.
    A dated one-session lag accommodates the daily publication lane. Two missing
    completed sessions suppress leadership instead of calling old data current.
    A remaining tie, absent history, malformed date, or invalid theme is neutral.
    No input object is mutated, and no score or trading recommendation is created.
    """
    out: dict[str, Any] = {
        "status": "unavailable",
        "leader": None,
        "positive_rating_status": "unavailable",
        "positive_rating_leader": None,
        "as_of": None,
        "as_of_label": None,
        "sessions_behind": None,
        "href": "sector_central.html",
        "positive_rating_href": "sector_central.html",
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
        out["status"] = out["positive_rating_status"] = "stale"
        return out
    behind = sessions_behind(day, now)
    out["sessions_behind"] = behind
    if behind > 1:
        out["status"] = out["positive_rating_status"] = "stale"
        return out

    # Older producers used archive row positions as days. Fail closed until the
    # canonical producer proves the exact comparison date (#7650); do not silently
    # relabel those old observations as true five-session leadership momentum.
    history = history if isinstance(history, dict) else {}
    expected = history.get("expected_comparison_as_of") or {}
    observed = history.get("comparison_as_of") or {}
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        return out
    target_five = session_n_back(day, 5)
    target_one = session_n_back(day, 1)
    if (
        history.get("basis") != "nyse_sessions"
        or target_five is None
        or expected.get("5d") != target_five.isoformat()
        or observed.get("5d") != target_five.isoformat()
    ):
        return out
    latest_session_known = (
        target_one is not None
        and observed.get("1d") == target_one.isoformat()
        and expected.get("1d") == target_one.isoformat()
    )

    candidates: list[dict[str, Any]] = []
    for row in heating if isinstance(heating, list) else []:
        if not isinstance(row, dict) or row.get("heat") != "heating":
            continue
        key = row.get("id")
        five = _rank_delta(row.get("rank_delta_5d"))
        if not isinstance(key, str) or not _THEME_ID.fullmatch(key) or five is None or five <= 0:
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            name = key.replace("_", " ").replace("-", " ").title()
        zh = row.get("name_zh")
        reco = row.get("reco") if isinstance(row.get("reco"), str) else None
        rating_en, rating_zh, positive_rating = _RATING_COPY.get(
            reco or "", ("Unavailable", "不可用", False)
        )
        candidates.append({
            "id": key,
            "name": name,
            "name_zh": zh if isinstance(zh, str) and zh else name,
            "reco": reco,
            "rating_label_en": rating_en,
            "rating_label_zh": rating_zh,
            "positive_rating": positive_rating,
            "rank_delta_5d": five,
            "rank_delta_1d": (
                _rank_delta(row.get("rank_delta_1d")) if latest_session_known else None
            ),
        })

    leader, status = _pick_unique_velocity(candidates)
    out["status"] = status
    if leader is not None:
        out["leader"] = leader
        out["href"] = f"basket/{leader['id']}.html"

    positive_candidates = [row for row in candidates if row["positive_rating"]]
    positive_leader, positive_status = _pick_unique_velocity(positive_candidates)
    out["positive_rating_status"] = positive_status
    if positive_leader is not None:
        out["positive_rating_leader"] = positive_leader
        out["positive_rating_href"] = f"basket/{positive_leader['id']}.html"
    return out
