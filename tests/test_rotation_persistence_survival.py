from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from scripts.research.rotation_persistence.survival import (
    build_leader_episodes,
    kaplan_meier,
    quartile_transition_matrix,
)


def _frame(order: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rank": list(range(1, len(order) + 1)),
            "score": [100 - i for i in range(len(order))],
            "label": ["dominant"] * len(order),
            "breadth": [0.5] * len(order),
        },
        index=order,
    )


def _base_ids() -> list[str]:
    return [f"t{i:02d}" for i in range(12)]


def test_transition_matrix_uses_only_exact_one_session_pairs() -> None:
    ids = _base_ids()
    frames = {
        date(2026, 9, 4): _frame(ids),
        date(2026, 9, 8): _frame(ids),  # exact next NYSE session after Friday
        # 2026-09-09 is missing, so Tuesday -> Thursday cannot be treated as one session.
        date(2026, 9, 10): _frame(list(reversed(ids))),
    }

    result = quartile_transition_matrix(frames)

    assert result["pairs_eligible"] == 1
    assert result["pairs_target_missing"] == 2
    assert sum(sum(row.values()) for row in result["counts"].values()) == 12
    assert result["counts"]["Q1"]["Q1"] == 3
    assert result["counts"]["Q4"]["Q4"] == 3


def test_transition_matrix_is_deterministic_and_row_normalized() -> None:
    ids = _base_ids()
    rotated = ids[3:6] + ids[:3] + ids[6:]
    frames = {
        date(2026, 9, 8): _frame(ids),
        date(2026, 9, 9): _frame(rotated),
    }

    result = quartile_transition_matrix(frames)

    assert result["counts"]["Q1"] == {"Q1": 0, "Q2": 3, "Q3": 0, "Q4": 0}
    assert result["probabilities"]["Q1"] == {
        "Q1": 0.0,
        "Q2": 1.0,
        "Q3": 0.0,
        "Q4": 0.0,
    }
    for row in result["probabilities"].values():
        if any(value is not None for value in row.values()):
            assert sum(value for value in row.values() if value is not None) == pytest.approx(1.0)


def test_observed_exit_closes_episode_without_right_censoring() -> None:
    ids = _base_ids()
    # t00 is Q1 on Friday and Tuesday, then moves to Q4 on Wednesday.
    wed = ["t03", "t04", "t05", "t06", "t07", "t08", "t09", "t10", "t11", "t01", "t02", "t00"]
    frames = {
        date(2026, 9, 4): _frame(ids),
        date(2026, 9, 8): _frame(ids),
        date(2026, 9, 9): _frame(wed),
    }

    episodes = build_leader_episodes(frames)
    episode = next(row for row in episodes if row["theme_id"] == "t00")

    assert episode["start"] == "2026-09-04"
    assert episode["end"] == "2026-09-08"
    assert episode["duration_sessions"] == 2
    assert episode["left_censored"] is True
    assert episode["right_censored"] is False
    assert episode["end_reason"] == "observed_exit"
    assert episode["exit_observed_on"] == "2026-09-09"


def test_archive_gap_right_censors_active_episode_and_does_not_bridge() -> None:
    ids = _base_ids()
    frames = {
        date(2026, 9, 4): _frame(ids),
        date(2026, 9, 8): _frame(ids),
        date(2026, 9, 10): _frame(ids),  # missing Wednesday
    }

    episodes = [row for row in build_leader_episodes(frames) if row["theme_id"] == "t00"]

    assert len(episodes) == 2
    assert episodes[0]["duration_sessions"] == 2
    assert episodes[0]["right_censored"] is True
    assert episodes[0]["end_reason"] == "archive_gap"
    assert episodes[1]["start"] == "2026-09-10"
    assert episodes[1]["left_censored"] is True
    assert episodes[1]["right_censored"] is True
    assert episodes[1]["end_reason"] == "archive_end"


def test_theme_absence_right_censors_instead_of_counting_an_exit() -> None:
    ids = _base_ids()
    second_ids = [x for x in ids if x != "t00"] + ["new"]
    frames = {
        date(2026, 9, 8): _frame(ids),
        date(2026, 9, 9): _frame(second_ids),
    }

    episode = next(row for row in build_leader_episodes(frames) if row["theme_id"] == "t00")

    assert episode["right_censored"] is True
    assert episode["end_reason"] == "theme_absent"
    assert episode["duration_sessions"] == 1


def test_archive_end_right_censors_open_episode() -> None:
    ids = _base_ids()
    frames = {
        date(2026, 9, 8): _frame(ids),
        date(2026, 9, 9): _frame(ids),
    }

    episode = next(row for row in build_leader_episodes(frames) if row["theme_id"] == "t00")

    assert episode["end"] == "2026-09-09"
    assert episode["duration_sessions"] == 2
    assert episode["left_censored"] is True
    assert episode["right_censored"] is True
    assert episode["end_reason"] == "archive_end"


def test_kaplan_meier_excludes_left_censored_and_handles_right_censoring() -> None:
    episodes = []
    for index, duration in enumerate([1, 2, 3, 4]):
        episodes.append(
            {
                "theme_id": f"e{index}",
                "duration_sessions": duration,
                "left_censored": False,
                "right_censored": False,
            }
        )
    for index, duration in enumerate([5, 6, 7, 8]):
        episodes.append(
            {
                "theme_id": f"c{index}",
                "duration_sessions": duration,
                "left_censored": False,
                "right_censored": True,
            }
        )
    episodes.append(
        {
            "theme_id": "left",
            "duration_sessions": 100,
            "left_censored": True,
            "right_censored": False,
        }
    )

    result = kaplan_meier(episodes)

    assert result["state"] == "MEASURED"
    assert result["n_episodes"] == 8
    assert result["n_events"] == 4
    assert result["n_left_censored_excluded"] == 1
    assert result["median_survival_sessions"] == 4
    assert result["curve"][3]["survival"] == pytest.approx(0.5)


def test_kaplan_meier_keeps_median_null_below_evidence_floor() -> None:
    episodes = [
        {
            "theme_id": f"t{i}",
            "duration_sessions": i + 1,
            "left_censored": False,
            "right_censored": i >= 3,
        }
        for i in range(7)
    ]

    result = kaplan_meier(episodes)

    assert result["state"] == "INSUFFICIENT_HISTORY"
    assert result["n_episodes"] == 7
    assert result["n_events"] == 3
    assert result["median_survival_sessions"] is None
    assert result["curve"]
