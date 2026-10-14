"""Synthetic tests for the pullback floor projection.

Fixtures are literal JSON written under tmp_path. These tests do not read the
stage-1 result files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import gamma

from scripts.research.grey_deer_pullback_floor_projection import (
    binding_floor,
    build_projection,
    d9_separation_stats,
    load_stage1,
    load_stage1b,
    main,
    poisson_waiting_quantiles,
)

_SENTINEL = "SENTINEL_SKILL_9.99"


def _stage1() -> dict:
    def honest(origins, events, clusters, episodes, event_months):
        return {
            "binary": {
                "honest_n": {
                    "origins": origins,
                    "events": events,
                    "clusters": clusters,
                    "episodes": episodes,
                    "event_months": event_months,
                    "event_month_list": ["2024-01"],
                }
            }
        }

    return {
        "claims": {"point": _SENTINEL},
        "episodes": {
            "h5": honest(2520, 80, 10, 4, 40),
            "h10": honest(2520, 100, 20, 0, 12),
            "h21": honest(2520, 80, 10, 4, 40),
        },
    }


def _stage1b() -> dict:
    # Gaps of 40. Horizon 5 needs 27, horizon 10 needs 32, horizon 21 needs 43.
    dates = [0, 40, 80]
    dense = [0, 5, 10, 15]

    def binary(horizon, episodes, event_dates, windows):
        return {
            "binary": {
                "origins": 504,
                "events": len(event_dates),
                "clusters": 8,
                "episodes": episodes,
                "event_months": 12,
                "event_dates": event_dates,
                "episode_windows": windows,
                "per_ticker_episodes": {"AAA": 1, "BBB": 1},
                "ticker_events": 40,
                "event_month_list": ["2024-01"],
            }
        }

    return {
        "claims": {"point": _SENTINEL},
        "bootstrap": {"lb": _SENTINEL},
        "episodes": {
            "h5": binary(5, 3, dates, [[0, 20], [21, 50], [51, 90]]),
            "h10": binary(10, 3, dates, [[0, 30], [31, 70], [71, 100]]),
            "h21": binary(21, 1, dense, [[0, 36]]),
        },
    }


def _write_fixtures(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stage1 = directory / "stage1.json"
    stage1b = directory / "stage1b.json"
    stage1.write_text(json.dumps(_stage1()))
    stage1b.write_text(json.dumps(_stage1b()))
    return stage1, stage1b


def _run(directory: Path, name: str) -> dict:
    stage1, stage1b = _write_fixtures(directory)
    out = directory / name
    code = main(
        [
            "--stage1",
            str(stage1),
            "--stage1b",
            str(stage1b),
            "--out",
            str(out),
            "--seed",
            "11",
            "--draws",
            "20000",
        ]
    )
    assert code == 0
    text = out.read_text()
    assert "Infinity" not in text
    assert "NaN" not in text
    assert _SENTINEL not in text
    payload = json.loads(text)
    _assert_finite(payload)
    return payload


def _assert_finite(obj) -> None:
    if isinstance(obj, float):
        assert math.isfinite(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            _assert_finite(value)
    elif isinstance(obj, list):
        for value in obj:
            _assert_finite(value)


def _scenario(payload, cohort, horizon, scale=1.0):
    scenarios = payload["cohorts"][cohort]["horizons"][horizon]["scenarios"]
    return next(item for item in scenarios if item["rate_scale"] == scale)


def _floor(scenario, name):
    return next(item for item in scenario["floors"] if item["floor"] == name)


def test_known_poisson_rate_median_is_near_analytic():
    rate = 0.8
    n_required = 10
    draws = poisson_waiting_quantiles(
        rate,
        n_required,
        np.random.default_rng(123),
        20_000,
    )
    analytic = float(gamma.median(a=n_required, scale=1.0 / rate))
    assert draws["p10_years"] < draws["median_years"] < draws["p90_years"]
    assert abs(draws["median_years"] - analytic) / analytic < 0.03


def test_binding_floor_picks_the_last_floor():
    assert binding_floor(
        [
            ("issued_sessions", 1.0),
            ("events", 3.0),
            ("episodes", 8.0),
        ]
    ) == "episodes"
    assert binding_floor([("events", 5.0), ("episodes", 5.0)]) == "episodes"
    assert binding_floor(
        [
            ("events", 100.0),
            ("episodes", None),
            ("event_months", 1.0),
        ]
    ) == "episodes"


def test_zero_historical_episodes_are_not_reachable(tmp_path):
    payload = _run(tmp_path, "zero.json")
    scenario = _scenario(payload, "A_spy", "h10")
    episodes = _floor(scenario, "episodes")
    assert episodes["status"] == "not_reachable"
    assert episodes["reason"] == "zero_historical_count"
    assert episodes["median_years"] is None
    assert episodes["p10_years"] is None
    assert episodes["p90_years"] is None
    assert scenario["all_floors"]["status"] == "not_reachable"
    assert scenario["all_floors"]["median_years"] is None
    assert scenario["binding_floor"] == "episodes"


def test_fixture_json_is_deterministic(tmp_path):
    stage1, stage1b = _write_fixtures(tmp_path)
    texts = []
    for name in ("one.json", "two.json"):
        out = tmp_path / name
        code = main(
            [
                "--stage1",
                str(stage1),
                "--stage1b",
                str(stage1b),
                "--out",
                str(out),
                "--seed",
                "11",
                "--draws",
                "20000",
            ]
        )
        assert code == 0
        texts.append(out.read_text())
    assert texts[0] == texts[1]
    payload = json.loads(texts[0])
    assert "Infinity" not in texts[0]
    assert "NaN" not in texts[0]
    _assert_finite(payload)


def test_script_runs_on_tmp_fixtures(tmp_path):
    payload = _run(tmp_path, "projection.json")
    assert payload["label"] == "EXPLORATORY"
    assert payload["n_draws"] >= 20_000
    assert payload["seed"] == 11
    assert payload["inputs"]["stage1"]["sha_source"] == "git hash-object"
    scenario = _scenario(payload, "A_spy", "h5")
    medians = [(row["floor"], row["median_years"]) for row in scenario["floors"]]
    assert scenario["binding_floor"] == binding_floor(medians)
    assert scenario["binding_floor"] == "episodes"
    graded = [
        _floor(_scenario(payload, "A_spy", "h5", scale), "graded_rows")["median_years"]
        for scale in (1.0, 0.5, 2.0)
    ]
    assert graded[0] == graded[1] == graded[2]
    stage1, stage1b = _write_fixtures(tmp_path)
    assert load_stage1(stage1)["h10"]["episodes"] == 0
    assert "claims" not in load_stage1b(stage1b)["h21"]


def test_panel_with_no_separating_gap_is_not_reachable(tmp_path):
    stats = d9_separation_stats([10, 20, 100], 21)
    assert stats["separation_gap_sessions"] == 43
    assert stats["max_inter_event_gap"] == 80
    assert stats["n_separating_gaps"] == 1
    assert stats["quiet_sessions_required"] == 42

    payload = _run(tmp_path, "panel.json")
    horizon = payload["cohorts"]["B_panel_d9"]["horizons"]["h21"]
    assert horizon["d9"]["n_windows"] == 1
    assert horizon["d9"]["n_separating_gaps"] == 0
    assert horizon["d9"]["planning_status"] == "not_reachable"
    assert horizon["d9"]["renewal_posterior"]["mean_years"] is None
    assert horizon["d9"]["renewal_posterior"]["mean_status"] == "infinite"
    assert math.isfinite(horizon["d9"]["renewal_posterior"]["median_years"])
    scenario = _scenario(payload, "B_panel_d9", "h21")
    episodes = _floor(scenario, "episodes")
    assert episodes["status"] == "not_reachable"
    assert episodes["reason"] == "zero_separating_gaps"
    assert scenario["binding_floor"] == "episodes"
    for scale in (0.5, 2.0):
        scaled = _floor(_scenario(payload, "B_panel_d9", "h21", scale), "episodes")
        assert scaled["status"] == "not_reachable"


def test_projection_object_matches_the_script(tmp_path):
    stage1, stage1b = _write_fixtures(tmp_path)
    direct = build_projection(
        load_stage1(stage1),
        load_stage1b(stage1b),
        seed=11,
        n_draws=20_000,
    )
    via_script = _run(tmp_path, "via.json")
    del via_script["inputs"]
    assert direct == via_script
