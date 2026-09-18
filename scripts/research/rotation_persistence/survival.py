"""Quartile transitions and right-censored leader-residency analysis."""
from __future__ import annotations

import math
from datetime import date
from typing import Mapping, Sequence

import pandas as pd

from .metrics import nth_session_after, pair_metrics

_QUARTILES: tuple[str, ...] = ("Q1", "Q2", "Q3", "Q4")


def _quartile_labels(frame: pd.DataFrame, ids: Sequence[str] | None = None) -> dict[str, str]:
    selected = list(ids) if ids is not None else [str(x) for x in frame.index]
    if not selected:
        return {}
    ranks = pd.to_numeric(frame.loc[selected, "rank"], errors="coerce").rank(
        method="average", ascending=True
    )
    n = len(ranks)
    q1_end = int(math.ceil(n / 4))
    q2_end = int(math.ceil(n / 2))
    q3_end = int(math.ceil(3 * n / 4))
    labels: dict[str, str] = {}
    for theme_id, rank in ranks.items():
        if rank <= q1_end:
            labels[str(theme_id)] = "Q1"
        elif rank <= q2_end:
            labels[str(theme_id)] = "Q2"
        elif rank <= q3_end:
            labels[str(theme_id)] = "Q3"
        else:
            labels[str(theme_id)] = "Q4"
    return labels


def quartile_transition_matrix(frames: Mapping[date, pd.DataFrame]) -> dict:
    """Measure transitions only across exact adjacent NYSE-session snapshots."""
    dates = sorted(frames)
    counts = {source: {target: 0 for target in _QUARTILES} for source in _QUARTILES}
    eligible = 0
    target_missing = 0
    pair_ineligible = 0

    for anchor in dates:
        target = nth_session_after(anchor, 1)
        if target not in frames:
            target_missing += 1
            continue
        assessment = pair_metrics(frames[anchor], frames[target])
        if not assessment["eligible"]:
            pair_ineligible += 1
            continue
        common = sorted(set(map(str, frames[anchor].index)).intersection(map(str, frames[target].index)))
        first_labels = _quartile_labels(frames[anchor], common)
        second_labels = _quartile_labels(frames[target], common)
        for theme_id in common:
            counts[first_labels[theme_id]][second_labels[theme_id]] += 1
        eligible += 1

    probabilities: dict[str, dict[str, float | None]] = {}
    for source, row in counts.items():
        total = sum(row.values())
        probabilities[source] = {
            target: (value / total if total else None) for target, value in row.items()
        }

    return {
        "state": "MEASURED" if eligible else "INSUFFICIENT_HISTORY",
        "pairs_eligible": eligible,
        "pairs_target_missing": target_missing,
        "pairs_ineligible": pair_ineligible,
        "counts": counts,
        "probabilities": probabilities,
    }


def _close_episode(
    output: list[dict],
    episode: dict,
    *,
    right_censored: bool,
    end_reason: str,
    exit_observed_on: date | None = None,
) -> None:
    output.append(
        {
            "theme_id": episode["theme_id"],
            "start": episode["start"].isoformat(),
            "end": episode["last"].isoformat(),
            "duration_sessions": int(episode["duration"]),
            "left_censored": bool(episode["left_censored"]),
            "right_censored": bool(right_censored),
            "end_reason": end_reason,
            "exit_observed_on": exit_observed_on.isoformat() if exit_observed_on else None,
        }
    )


def build_leader_episodes(frames: Mapping[date, pd.DataFrame]) -> list[dict]:
    """Build contiguous top-quartile episodes without bridging archive gaps.

    Duration is the number of adjacent observed NYSE-session snapshots in which the
    theme was Q1.  A theme absent from the next snapshot is censored, never treated as
    a measured leadership exit.
    """
    dates = sorted(frames)
    if not dates:
        return []

    output: list[dict] = []
    active: dict[str, dict] = {}
    previous_date: date | None = None
    previous_ids: set[str] = set()

    for position, current_date in enumerate(dates):
        frame = frames[current_date]
        current_ids = set(map(str, frame.index))
        current_labels = _quartile_labels(frame)
        current_top = {theme_id for theme_id, label in current_labels.items() if label == "Q1"}

        if previous_date is None:
            for theme_id in sorted(current_top):
                active[theme_id] = {
                    "theme_id": theme_id,
                    "start": current_date,
                    "last": current_date,
                    "duration": 1,
                    "left_censored": True,
                }
            previous_date = current_date
            previous_ids = current_ids
            continue

        adjacent = nth_session_after(previous_date, 1) == current_date
        if not adjacent:
            for episode in list(active.values()):
                _close_episode(
                    output,
                    episode,
                    right_censored=True,
                    end_reason="archive_gap",
                )
            active.clear()
            for theme_id in sorted(current_top):
                active[theme_id] = {
                    "theme_id": theme_id,
                    "start": current_date,
                    "last": current_date,
                    "duration": 1,
                    "left_censored": True,
                }
            previous_date = current_date
            previous_ids = current_ids
            continue

        for theme_id, episode in list(active.items()):
            if theme_id not in current_ids:
                _close_episode(
                    output,
                    episode,
                    right_censored=True,
                    end_reason="theme_absent",
                )
                del active[theme_id]
            elif theme_id not in current_top:
                _close_episode(
                    output,
                    episode,
                    right_censored=False,
                    end_reason="observed_exit",
                    exit_observed_on=current_date,
                )
                del active[theme_id]
            else:
                episode["last"] = current_date
                episode["duration"] += 1

        for theme_id in sorted(current_top.difference(active)):
            active[theme_id] = {
                "theme_id": theme_id,
                "start": current_date,
                "last": current_date,
                "duration": 1,
                "left_censored": theme_id not in previous_ids,
            }

        previous_date = current_date
        previous_ids = current_ids

    for episode in list(active.values()):
        _close_episode(
            output,
            episode,
            right_censored=True,
            end_reason="archive_end",
        )

    return sorted(output, key=lambda row: (row["start"], row["theme_id"], row["end"]))


def kaplan_meier(
    episodes: Sequence[dict],
    *,
    min_episodes: int = 8,
    min_events: int = 4,
) -> dict:
    """Kaplan-Meier estimate over episodes with observed starts.

    Left-censored episodes are retained in the episode ledger but excluded from this
    estimator because ordinary KM cannot represent an unknown entry time.
    """
    usable: list[tuple[int, bool]] = []
    left_excluded = 0
    for episode in episodes:
        if bool(episode.get("left_censored")):
            left_excluded += 1
            continue
        try:
            duration = int(episode.get("duration_sessions"))
        except (TypeError, ValueError):
            continue
        if duration <= 0:
            continue
        event = not bool(episode.get("right_censored"))
        usable.append((duration, event))

    curve: list[dict] = []
    survival = 1.0
    for duration in sorted({item[0] for item in usable}):
        at_risk = sum(1 for observed, _ in usable if observed >= duration)
        events = sum(1 for observed, event in usable if observed == duration and event)
        censored = sum(1 for observed, event in usable if observed == duration and not event)
        if at_risk and events:
            survival *= 1.0 - events / at_risk
        curve.append(
            {
                "duration_sessions": duration,
                "at_risk": at_risk,
                "events": events,
                "censored": censored,
                "survival": float(survival),
            }
        )

    n_events = sum(1 for _, event in usable if event)
    measured = len(usable) >= min_episodes and n_events >= min_events
    median: int | None = None
    if measured:
        median = next(
            (
                int(point["duration_sessions"])
                for point in curve
                if point["survival"] <= 0.5
            ),
            None,
        )
    return {
        "state": "MEASURED" if measured else "INSUFFICIENT_HISTORY",
        "n_episodes": len(usable),
        "n_events": n_events,
        "n_right_censored": len(usable) - n_events,
        "n_left_censored_excluded": left_excluded,
        "median_survival_sessions": median,
        "curve": curve,
    }
