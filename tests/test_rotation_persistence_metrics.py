from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from scripts.research.rotation_persistence.metrics import (
    build_surface,
    classify_temporal_shape,
    derive_half_life,
    moving_block_ci,
    nth_session_after,
    pair_metrics,
)


def _frame(
    ranks: list[float],
    scores: list[float] | None = None,
    breadths: list[float | None] | None = None,
    ids: list[str] | None = None,
) -> pd.DataFrame:
    n = len(ranks)
    ids = ids or [f"t{i}" for i in range(n)]
    scores = scores or [100.0 - 5 * i for i in range(n)]
    breadths = breadths or [0.8 - 0.02 * i for i in range(n)]
    return pd.DataFrame(
        {
            "rank": ranks,
            "score": scores,
            "label": ["dominant"] * n,
            "breadth": breadths,
        },
        index=ids,
    )


def test_nth_session_after_uses_exchange_sessions_not_calendar_days() -> None:
    # 2026-09-04 was Friday; 2026-09-07 was Labor Day.
    assert nth_session_after(date(2026, 9, 4), 1) == date(2026, 9, 8)
    assert nth_session_after(date(2026, 9, 4), 2) == date(2026, 9, 9)


def test_pair_metrics_measures_identical_rank_persistence_and_top_quartile() -> None:
    first = _frame(list(range(1, 13)))
    second = _frame(list(range(1, 13)))

    result = pair_metrics(first, second)

    assert result["eligible"] is True
    assert result["n_common"] == 12
    assert result["rank_rho"] == pytest.approx(1.0)
    assert result["topq_overlap"] == pytest.approx(1.0)
    assert result["chance_overlap"] == pytest.approx(0.25)
    assert result["topq_overlap_lift"] == pytest.approx(4.0)
    assert result["leader_to_laggard"] == pytest.approx(0.0)
    assert result["laggard_to_leader"] == pytest.approx(0.0)


def test_pair_metrics_recomputes_average_tied_ranks_deterministically() -> None:
    first = _frame([1, 1, 3, 4, 5, 6, 7, 8, 9, 10])
    second = _frame([1, 1, 3, 4, 5, 6, 7, 8, 9, 10])

    result = pair_metrics(first, second)

    assert result["rank_rho"] == pytest.approx(1.0)
    assert result["topq_overlap"] == pytest.approx(1.0)


def test_pair_metrics_rejects_thin_common_set() -> None:
    first = _frame(list(range(1, 13)))
    second = _frame(list(range(1, 13)), ids=[f"x{i}" for i in range(12)])

    result = pair_metrics(first, second)

    assert result["eligible"] is False
    assert result["reason"] == "INSUFFICIENT_COMMON_COVERAGE"
    assert result["rank_rho"] is None


def test_pair_metrics_rejects_common_count_below_ten_even_at_full_coverage() -> None:
    first = _frame(list(range(1, 10)))
    second = _frame(list(range(1, 10)))

    result = pair_metrics(first, second)

    assert result["eligible"] is False
    assert result["reason"] == "INSUFFICIENT_COMMON_COUNT"


def test_score_continuation_ic_is_negative_when_leaders_lose_score() -> None:
    n = 12
    first = _frame(list(range(1, n + 1)), scores=[100.0] * n)
    deltas = list(np.linspace(-20, 20, n))
    second = _frame(list(range(1, n + 1)), scores=[100.0 + x for x in deltas])

    result = pair_metrics(first, second)

    assert result["score_continuation_ic"] == pytest.approx(-1.0)


def test_breadth_metrics_are_null_when_finite_coverage_is_below_eighty_percent() -> None:
    n = 12
    first = _frame(list(range(1, n + 1)), breadths=[0.5] * 9 + [None] * 3)
    second = _frame(list(range(1, n + 1)), breadths=[0.6] * 9 + [None] * 3)

    result = pair_metrics(first, second)

    assert result["eligible"] is True
    assert result["breadth_state"] == "INSUFFICIENT_BREADTH_COVERAGE"
    assert result["breadth_coverage"] == pytest.approx(0.75)
    assert result["leader_breadth_delta"] is None
    assert result["breadth_rank_rho"] is None


def test_breadth_metrics_measure_leader_delta_and_rank_persistence() -> None:
    n = 12
    first = _frame(list(range(1, n + 1)), breadths=list(np.linspace(0.9, 0.2, n)))
    second = _frame(list(range(1, n + 1)), breadths=list(np.linspace(1.0, 0.3, n)))

    result = pair_metrics(first, second)

    assert result["breadth_state"] == "MEASURED"
    assert result["breadth_coverage"] == pytest.approx(1.0)
    assert result["leader_breadth_delta"] == pytest.approx(0.1)
    assert result["breadth_rank_rho"] == pytest.approx(1.0)


def test_moving_block_ci_is_deterministic_and_ordered() -> None:
    values = [float(i) for i in range(20)]
    first = moving_block_ci(values, block_len=3, n_resamples=500, seed=42)
    second = moving_block_ci(values, block_len=3, n_resamples=500, seed=42)

    assert first == second
    assert first is not None
    assert first[0] < np.mean(values) < first[1]


def test_build_surface_uses_exact_endpoint_dates_and_does_not_forward_fill() -> None:
    frame = _frame(list(range(1, 13)))
    frames = {
        date(2026, 9, 4): frame,
        date(2026, 9, 8): frame,
        # Wednesday 09-09 is deliberately missing.
        date(2026, 9, 10): frame,
    }

    surface = build_surface(
        frames,
        horizons=(1, 2),
        recent_sessions=20,
        min_pairs=1,
        bootstrap_resamples=50,
        bootstrap_seed=7,
    )

    # h=1: Friday -> Tuesday exists; Tuesday -> Wednesday missing; Thursday -> Friday absent.
    assert surface["1"]["pairs_eligible"] == 1
    assert surface["1"]["pairs_target_missing"] == 2
    # h=2: Friday -> Wednesday missing; Tuesday -> Thursday exists; Thursday target absent.
    assert surface["2"]["pairs_eligible"] == 1
    assert surface["2"]["pairs_target_missing"] == 2


def test_build_surface_emits_honest_null_below_minimum_pairs() -> None:
    frame = _frame(list(range(1, 13)))
    frames = {
        date(2026, 9, 4): frame,
        date(2026, 9, 8): frame,
    }

    surface = build_surface(
        frames,
        horizons=(1,),
        recent_sessions=20,
        min_pairs=2,
        bootstrap_resamples=50,
        bootstrap_seed=7,
    )

    metric = surface["1"]["windows"]["recent"]["rank_rho"]
    assert metric == {
        "state": "INSUFFICIENT_HISTORY",
        "n": 1,
        "mean": None,
        "ci90": None,
    }


def test_derive_half_life_interpolates_first_half_crossing() -> None:
    result = derive_half_life({1: 0.8, 3: 0.5, 5: 0.3, 7: 0.1})

    assert result["state"] == "MEASURED"
    assert result["half_life_sessions"] == pytest.approx(4.0)
    assert result["start_rho"] == pytest.approx(0.8)
    assert result["half_target"] == pytest.approx(0.4)


@pytest.mark.parametrize(
    ("curve", "reason"),
    [
        ({1: 0.8, 3: 0.6, 5: 0.4}, "INSUFFICIENT_HORIZONS"),
        ({1: 0.0, 3: -0.1, 5: -0.2, 7: -0.3}, "NONPOSITIVE_START"),
        ({1: 0.2, 3: 0.3, 5: 0.4, 7: 0.5}, "NON_DECAYING"),
        ({1: 0.8, 3: 0.5, 5: 0.7, 7: 0.2}, "NON_MONOTONE"),
        ({1: 0.8, 3: 0.7, 5: 0.6, 7: 0.5}, "NO_HALF_CROSSING"),
    ],
)
def test_derive_half_life_keeps_invalid_curves_null(
    curve: dict[int, float], reason: str
) -> None:
    result = derive_half_life(curve)

    assert result["state"] == reason
    assert result["half_life_sessions"] is None


@pytest.mark.parametrize(
    ("curve", "expected"),
    [
        ({1: -0.2, 2: -0.1, 3: -0.1, 5: -0.2, 10: 0.1, 15: 0.2}, "MULTI_SCALE"),
        ({1: -0.2, 2: -0.1, 3: -0.1, 5: -0.2, 10: -0.01, 15: 0.0}, "REVERSAL_DOMINANT"),
        ({1: 0.2, 2: 0.1, 3: 0.1, 5: 0.2, 10: 0.1, 15: 0.2}, "CONTINUATION_DOMINANT"),
        ({1: 0.0, 2: 0.01, 3: -0.01, 5: 0.0, 10: 0.0, 15: 0.01}, "TRANSITIONAL"),
        ({1: -0.2, 10: 0.2}, "INSUFFICIENT_HISTORY"),
    ],
)
def test_classify_temporal_shape_uses_frozen_thresholds(
    curve: dict[int, float], expected: str
) -> None:
    result = classify_temporal_shape(curve)

    assert result["label"] == expected
