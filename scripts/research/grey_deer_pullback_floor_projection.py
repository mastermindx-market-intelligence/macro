"""Exploratory projection of years until pullback readiness floors can hold.

EXPLORATORY. Rates are taken from already-inspected history. This is a planning
projection, not a forecast, and not evidence about skill.

Two cohorts:

* A — SPY-only forward lane. Exposure sessions are the stage-1 origin count.
* B — a 14-ticker panel under prereg v1.1 D9. Origins in the stage-1b file are
  ticker-date rows. The date-axis session count is ``origins / n_tickers``.

Count floors (events, non-events, clusters, episodes, event-months) are waiting
times of a Poisson process whose rate has a Jeffreys posterior
``Gamma(shape = k + 0.5, rate = T years)``. Event-months are a separate Poisson
count of distinct months. That is an approximation: a year has at most 12
distinct months, and months are not independent of events.

Clock floors (issued sessions, calendar span, graded rows) do not use that
posterior. They assume the lane issues every US cash session.

A historical count of zero is not given a rate. The floor is ``not_reachable``
and no draw is taken, so the JSON never contains a non-finite year. On the
panel, D9 episode windows overlap until the inter-event gap is at least
``h + 21 + 1`` sessions. Zero such gaps means the episode count has not
renewed. That floor is ``not_reachable`` as well.

The script reads episode counts, windows, and session indices only. It does not
import the frozen stage-1 runners and does not read a price store.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import betabinom

REPO = Path(__file__).resolve().parents[2]

SESSIONS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365.25
EPISODE_LOOKBACK = 21
N_DRAWS_MIN = 20_000
DEFAULT_SEED = 20261013
DEFAULT_DRAWS = 20_000
RATE_SCALES = (1.0, 0.5, 2.0)
HORIZONS = (5, 10, 21)
SEPARATIONS_FOR_TEN_EPISODES = 9

FLOOR_ORDER = (
    "issued_sessions",
    "calendar_days",
    "graded_rows",
    "events",
    "non_events",
    "clusters",
    "episodes",
    "event_months",
)

FLOOR_REQUIRED = {
    "issued_sessions": 252,
    "calendar_days": 300,
    "graded_rows": 200,
    "events": 20,
    "non_events": 50,
    "clusters": 5,
    "episodes": 10,
    "event_months": 10,
}

_STAGE1_FIELDS = ("origins", "events", "clusters", "episodes", "event_months")
_STAGE1B_FIELDS = _STAGE1_FIELDS + (
    "event_dates",
    "episode_windows",
    "per_ticker_episodes",
    "ticker_events",
)

_NOT_REACHABLE = {
    "status": "not_reachable",
    "p10_years": None,
    "median_years": None,
    "p90_years": None,
}


def round_years(value: float) -> float:
    """Four decimal places. Non-finite values are refused."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite year count")
    return round(number, 4)


def poisson_waiting_quantiles(
    rate: float,
    n_required: int,
    rng: np.random.Generator,
    n_draws: int,
) -> dict[str, float]:
    """Years until ``n_required`` arrivals of a Poisson process at a known rate.

    The analytic median is the median of ``Gamma(shape=n_required, scale=1/rate)``.
    """
    if rate <= 0 or n_required <= 0 or n_draws <= 0:
        raise ValueError("rate, n_required, and n_draws must be positive")
    waits = rng.gamma(shape=float(n_required), scale=1.0 / float(rate), size=n_draws)
    return _quantile_dict(waits)


def jeffreys_waiting_draws(
    count: int,
    exposure_years: float,
    n_required: int,
    rng: np.random.Generator,
    n_draws: int,
    rate_scale: float = 1.0,
) -> np.ndarray:
    """Draw posterior-predictive waiting times. ``count == 0`` is refused upstream."""
    if count <= 0 or exposure_years <= 0 or n_required <= 0 or rate_scale <= 0:
        raise ValueError("Jeffreys draws require a positive count, exposure, and scale")
    # Posterior Gamma(shape=k+0.5, rate=T). numpy uses scale = 1/rate.
    # A sensitivity scale multiplies the rate, which multiplies that scale.
    lam = rng.gamma(
        shape=float(count) + 0.5,
        scale=float(rate_scale) / float(exposure_years),
        size=n_draws,
    )
    return rng.gamma(shape=float(n_required), scale=1.0 / lam)


def binding_floor(floors: list[tuple[str, float | None]]) -> str:
    """Return the floor that holds last.

    ``None`` means not reachable and sorts after every finite median. Equal
    medians break toward the later entry, so the last of the tied floors wins.
    """
    if not floors:
        raise ValueError("no floors")
    best_index = 0
    best_key: tuple[int, float, int] | None = None
    for index, (_name, median) in enumerate(floors):
        if median is None:
            key = (1, 0.0, index)
        else:
            key = (0, float(median), index)
        if best_key is None or key > best_key:
            best_key = key
            best_index = index
    return floors[best_index][0]


def d9_separation_stats(
    event_dates: list[int],
    horizon: int,
    lookback: int = EPISODE_LOOKBACK,
) -> dict[str, int | None]:
    """Measure D9 episode separation on stored session indices.

    A cluster window is ``[first - lookback, last + horizon]``. The next window
    starts a new episode only when its start is strictly after the previous
    window's end, which means the session-index gap is at least
    ``horizon + lookback + 1``.
    """
    dates = sorted({int(value) for value in event_dates})
    gaps = [b - a for a, b in zip(dates, dates[1:])]
    need = int(horizon) + int(lookback) + 1
    max_gap = max(gaps) if gaps else None
    return {
        "n_event_dates": len(dates),
        "n_gaps": len(gaps),
        "max_inter_event_gap": max_gap,
        "separation_gap_sessions": need,
        "n_separating_gaps": sum(gap >= need for gap in gaps),
        "longest_quiet_sessions": None if max_gap is None else max_gap - 1,
        "quiet_sessions_required": int(horizon) + int(lookback),
    }


def zero_renewal_wait_quantiles(
    n_gaps: int,
    separations_needed: int,
    exposure_years: float,
) -> dict[str, float | int | str | None]:
    """Jeffreys wait for further separations after zero observed separations.

    Each stored gap is treated as a Bernoulli trial that has not separated, with
    ``p ~ Beta(0.5, n_gaps + 0.5)``. The mean wait is infinite because the Beta
    shape on ``p`` is 0.5. Quantiles of the additional gaps come from the
    beta-binomial survival function and are finite. This is the proof distribution
    for a sample that never renewed. It is not the Poisson episode model.
    """
    if n_gaps <= 0 or separations_needed <= 0 or exposure_years <= 0:
        raise ValueError("renewal quantiles need gaps, a positive target, and exposure")

    def survival(trials: int) -> float:
        if trials <= 0:
            return 1.0
        return float(
            betabinom.cdf(separations_needed - 1, trials, 0.5, n_gaps + 0.5)
        )

    def quantile(prob_survive: float) -> int:
        lo = 0
        hi = 1
        while survival(hi) > prob_survive:
            hi *= 2
            if hi > 10**15:
                raise RuntimeError("renewal quantile did not resolve")
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if survival(mid) > prob_survive:
                lo = mid
            else:
                hi = mid
        return hi

    payload: dict[str, float | int | str | None] = {
        "model": "jeffreys_beta_binomial_zero_successes",
        "successes_observed": 0,
        "n_gaps": n_gaps,
        "separations_needed": separations_needed,
        "mean_status": "infinite",
        "mean_years": None,
    }
    names = (("p10", 0.9), ("median", 0.5), ("p90", 0.1))
    for name, prob_survive in names:
        trials = quantile(prob_survive)
        years = trials * float(exposure_years) / float(n_gaps)
        payload[f"{name}_additional_gaps"] = trials
        payload[f"{name}_years"] = round_years(years)
    return payload


def load_stage1(path: Path) -> dict[str, dict]:
    """Keep stage-1 honest-N counts. Other keys are discarded."""
    raw = json.loads(path.read_text())
    episodes = raw["episodes"]
    loaded: dict[str, dict] = {}
    for horizon in HORIZONS:
        honest = episodes[f"h{horizon}"]["binary"]["honest_n"]
        loaded[f"h{horizon}"] = {key: int(honest[key]) for key in _STAGE1_FIELDS}
    return loaded


def load_stage1b(path: Path) -> dict[str, dict]:
    """Keep stage-1b binary episode fields. Other keys are discarded."""
    raw = json.loads(path.read_text())
    episodes = raw["episodes"]
    loaded: dict[str, dict] = {}
    for horizon in HORIZONS:
        binary = episodes[f"h{horizon}"]["binary"]
        row: dict = {key: binary[key] for key in _STAGE1B_FIELDS}
        for key in ("origins", "events", "clusters", "episodes", "event_months", "ticker_events"):
            row[key] = int(row[key])
        row["event_dates"] = [int(value) for value in row["event_dates"]]
        row["episode_windows"] = [
            [int(lo), int(hi)] for lo, hi in row["episode_windows"]
        ]
        if len(set(row["event_dates"])) != row["events"]:
            raise ValueError(f"h{horizon}: event_dates and events disagree")
        if len(row["episode_windows"]) != row["episodes"]:
            raise ValueError(f"h{horizon}: episode_windows and episodes disagree")
        row["n_tickers"] = len(row["per_ticker_episodes"])
        del row["per_ticker_episodes"]
        loaded[f"h{horizon}"] = row
    return loaded


def build_projection(
    stage1: dict[str, dict],
    stage1b: dict[str, dict],
    *,
    seed: int,
    n_draws: int,
) -> dict:
    """Project both cohorts. ``n_draws`` must be at least 20,000."""
    if n_draws < N_DRAWS_MIN:
        raise ValueError(f"n_draws must be >= {N_DRAWS_MIN}")
    rng = np.random.default_rng(np.random.SeedSequence(int(seed)))
    panel_widths = {int(stage1b[f"h{horizon}"]["n_tickers"]) for horizon in HORIZONS}
    if len(panel_widths) != 1:
        raise ValueError("panel ticker count differs by horizon")
    panel_n = panel_widths.pop()
    cohorts = {
        "A_spy": _project_cohort(
            "A_spy",
            "SPY-only forward lane",
            stage1,
            panel=False,
            rng=rng,
            n_draws=n_draws,
            seed=seed,
        ),
        "B_panel_d9": _project_cohort(
            "B_panel_d9",
            f"{panel_n}-ticker panel forward lane under D9",
            stage1b,
            panel=True,
            rng=rng,
            n_draws=n_draws,
            seed=seed,
        ),
    }
    return {
        "label": "EXPLORATORY",
        "schema": "grey_deer_pullback_floor_projection/v1",
        "seed": int(seed),
        "n_draws": int(n_draws),
        "sessions_per_year": SESSIONS_PER_YEAR,
        "calendar_days_per_year": CALENDAR_DAYS_PER_YEAR,
        "episode_lookback_sessions": EPISODE_LOOKBACK,
        "quantile_method": "numpy linear quantile of posterior-predictive draws",
        "jeffreys": "Gamma(shape=count+0.5, rate=exposure_years); waiting time Gamma(shape=n_required, rate=lambda)",
        "event_months_model": "separate Poisson approximation of distinct event-months",
        "exposure": "sessions/252; panel sessions = origins/n_tickers",
        "floors_required": dict(FLOOR_REQUIRED),
        "rate_scales": list(RATE_SCALES),
        "cohorts": cohorts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage1",
        type=Path,
        default=REPO / "research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.json",
    )
    parser.add_argument(
        "--stage1b",
        type=Path,
        default=REPO / "research/grey_deer/pullback_stage1b/PULLBACK_STAGE1B_RESULTS.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO / "research/grey_deer/pullback_floor_projection/FLOOR_PROJECTION_2026-10-13.json",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    args = parser.parse_args(argv)

    stage1 = load_stage1(args.stage1)
    stage1b = load_stage1b(args.stage1b)
    payload = build_projection(stage1, stage1b, seed=args.seed, n_draws=args.draws)
    payload["inputs"] = {
        "stage1": _blob_sha(args.stage1, REPO),
        "stage1b": _blob_sha(args.stage1b, REPO),
    }
    _write_json(payload, args.out)
    _print_summary(payload, args.out)
    return 0


def _project_cohort(
    cohort_id: str,
    label: str,
    horizons: dict[str, dict],
    *,
    panel: bool,
    rng: np.random.Generator,
    n_draws: int,
    seed: int,
) -> dict:
    projected = {}
    for horizon in HORIZONS:
        projected[f"h{horizon}"] = _project_horizon(
            horizons[f"h{horizon}"],
            horizon=horizon,
            panel=panel,
            rng=rng,
            n_draws=n_draws,
            seed=seed,
        )
    return {"id": cohort_id, "label": label, "panel": panel, "horizons": projected}


def _project_horizon(
    source: dict,
    *,
    horizon: int,
    panel: bool,
    rng: np.random.Generator,
    n_draws: int,
    seed: int,
) -> dict:
    n_tickers = int(source["n_tickers"]) if panel else 1
    if n_tickers <= 0:
        raise ValueError("n_tickers must be positive")
    origins = int(source["origins"])
    sessions = origins / n_tickers
    exposure_years = sessions / SESSIONS_PER_YEAR
    if exposure_years <= 0:
        raise ValueError("exposure years must be positive")
    event_rows = int(source["ticker_events"]) if panel else int(source["events"])
    non_event_rows = origins - event_rows
    if non_event_rows < 0:
        raise ValueError("event rows exceed origins")
    counts = {
        "origins": origins,
        "n_tickers": n_tickers,
        "sessions": _maybe_int(sessions),
        "exposure_years": round_years(exposure_years),
        "event_rows": event_rows,
        "event_dates": int(source["events"]),
        "non_event_rows": non_event_rows,
        "clusters": int(source["clusters"]),
        "episodes": int(source["episodes"]),
        "event_months": int(source["event_months"]),
    }
    rates = {
        name: round_years(counts[name] / exposure_years)
        for name in ("event_rows", "event_dates", "non_event_rows", "clusters", "episodes", "event_months")
    }
    d9 = None
    structural_zero = False
    if panel:
        d9 = _d9_block(source, horizon=horizon, exposure_years=exposure_years, seed=seed, n_draws=n_draws)
        structural_zero = int(d9["n_separating_gaps"]) == 0
    lag = horizon / SESSIONS_PER_YEAR
    poisson_counts = {
        "events": event_rows,
        "non_events": non_event_rows,
        "clusters": counts["clusters"],
        "episodes": counts["episodes"],
        "event_months": counts["event_months"],
    }
    scenarios = []
    for scale in RATE_SCALES:
        scenarios.append(
            _scenario(
                scale=scale,
                horizon=horizon,
                n_tickers=n_tickers,
                exposure_years=exposure_years,
                lag=lag,
                poisson_counts=poisson_counts,
                structural_zero=structural_zero,
                rng=rng,
                n_draws=n_draws,
            )
        )
    history = {
        "source_counts": {
            "origins": origins,
            "events": int(source["events"]),
            "clusters": counts["clusters"],
            "episodes": counts["episodes"],
            "event_months": counts["event_months"],
        },
        "counts": counts,
        "rates_per_year": rates,
        "label_lag_years": round_years(lag),
        "scenarios": scenarios,
    }
    if panel:
        history["source_counts"]["ticker_events"] = int(source["ticker_events"])
        history["d9"] = d9
    return history


def _d9_block(
    source: dict,
    *,
    horizon: int,
    exposure_years: float,
    seed: int,
    n_draws: int,
) -> dict:
    stats = d9_separation_stats(source["event_dates"], horizon)
    windows = source["episode_windows"]
    block: dict = {
        "episode_windows": windows,
        "n_windows": len(windows),
        "window_lengths": [hi - lo + 1 for lo, hi in windows],
        **stats,
    }
    if int(stats["n_separating_gaps"]) != 0:
        block["planning_status"] = "renewals_observed"
        return block
    block["planning_status"] = "not_reachable"
    n_gaps = int(stats["n_gaps"] or 0)
    if n_gaps > 0:
        block["renewal_posterior"] = zero_renewal_wait_quantiles(
            n_gaps,
            SEPARATIONS_FOR_TEN_EPISODES,
            exposure_years,
        )
    if int(source["episodes"]) > 0:
        # Rejected reading: treat the unseparated window as one Poisson arrival.
        cf_rng = np.random.default_rng(np.random.SeedSequence([int(seed), 17, int(horizon)]))
        draws = jeffreys_waiting_draws(
            int(source["episodes"]),
            exposure_years,
            FLOOR_REQUIRED["episodes"],
            cf_rng,
            n_draws,
            rate_scale=1.0,
        )
        lag = horizon / SESSIONS_PER_YEAR
        quant = _quantile_dict(draws + lag)
        block["rejected_independent_poisson"] = {
            "used_for_planning": False,
            "reason": "zero separating gaps; the single window is not a renewal",
            "historical_episodes": int(source["episodes"]),
            **quant,
        }
    return block


def _scenario(
    *,
    scale: float,
    horizon: int,
    n_tickers: int,
    exposure_years: float,
    lag: float,
    poisson_counts: dict[str, int],
    structural_zero: bool,
    rng: np.random.Generator,
    n_draws: int,
) -> dict:
    rows = []
    medians: list[tuple[str, float | None]] = []
    stack: list[np.ndarray] = []
    blocked = False
    for name in FLOOR_ORDER:
        if name == "issued_sessions":
            years = FLOOR_REQUIRED["issued_sessions"] / SESSIONS_PER_YEAR
            row, waits = _clock_row(name, years, n_draws)
        elif name == "calendar_days":
            years = FLOOR_REQUIRED["calendar_days"] / CALENDAR_DAYS_PER_YEAR
            row, waits = _clock_row(name, years, n_draws)
        elif name == "graded_rows":
            sessions_needed = horizon + math.ceil(FLOOR_REQUIRED["graded_rows"] / n_tickers)
            years = sessions_needed / SESSIONS_PER_YEAR
            row, waits = _clock_row(name, years, n_draws)
        else:
            count = poisson_counts[name]
            unreachable = count <= 0 or (name == "episodes" and structural_zero)
            if unreachable:
                reason = "zero_historical_count" if count <= 0 else "zero_separating_gaps"
                row = {"floor": name, "reason": reason, **_NOT_REACHABLE}
                waits = None
                blocked = True
            else:
                draws = jeffreys_waiting_draws(
                    count,
                    exposure_years,
                    FLOOR_REQUIRED[name],
                    rng,
                    n_draws,
                    rate_scale=scale,
                )
                waits = draws + lag
                row = {"floor": name, "status": "ok", "reason": None, **_quantile_dict(waits)}
        rows.append(row)
        medians.append((name, row["median_years"]))
        if waits is not None:
            stack.append(waits)
    chosen = binding_floor(medians)
    if blocked:
        all_floors = {"floor": "all_floors", "reason": "a floor is not reachable", **_NOT_REACHABLE}
        for row in rows:
            row["share_last"] = 1.0 if row["median_years"] is None else 0.0
    else:
        combined = np.max(np.stack(stack, axis=0), axis=0)
        all_floors = {"floor": "all_floors", "status": "ok", "reason": None, **_quantile_dict(combined)}
        for row, waits in zip(rows, stack):
            row["share_last"] = round_years(float(np.mean(np.isclose(waits, combined))))
    chosen_row = next(row for row in rows if row["floor"] == chosen)
    return {
        "rate_scale": scale,
        "binding_floor": chosen,
        "binding_share": chosen_row["share_last"],
        "all_floors": all_floors,
        "floors": rows,
    }


def _clock_row(name: str, years: float, n_draws: int) -> tuple[dict, np.ndarray]:
    value = round_years(years)
    row = {
        "floor": name,
        "status": "ok",
        "reason": None,
        "p10_years": value,
        "median_years": value,
        "p90_years": value,
    }
    return row, np.full(n_draws, value, dtype=float)


def _quantile_dict(draws: np.ndarray) -> dict[str, float]:
    if draws.shape != (draws.size,) or draws.size == 0:
        raise ValueError("draws must be a non-empty vector")
    if not np.isfinite(draws).all():
        raise ValueError("non-finite waiting time")
    p10, median, p90 = np.quantile(draws, [0.1, 0.5, 0.9], method="linear")
    return {
        "p10_years": round_years(p10),
        "median_years": round_years(median),
        "p90_years": round_years(p90),
    }


def _maybe_int(value: float) -> int | float:
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return int(rounded)
    return round_years(value)


def _blob_sha(path: Path, repo: Path) -> dict[str, str]:
    resolved = path.resolve()
    record = {"path": str(resolved)}
    try:
        rel = resolved.relative_to(repo.resolve()).as_posix()
    except ValueError:
        rel = None
    if rel is not None:
        proc = subprocess.run(
            ["git", "rev-parse", f"HEAD:{rel}"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            record["path"] = rel
            record["git_blob_sha"] = proc.stdout.strip()
            record["sha_source"] = "git rev-parse HEAD:<path>"
            return record
    proc = subprocess.run(
        ["git", "hash-object", str(resolved)],
        check=True,
        capture_output=True,
        text=True,
    )
    record["git_blob_sha"] = proc.stdout.strip()
    record["sha_source"] = "git hash-object"
    return record


def _write_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, allow_nan=False, sort_keys=True) + "\n"
    if "Infinity" in text or "NaN" in text:
        raise ValueError("JSON would contain a non-finite token")
    path.write_text(text)


def _print_summary(payload: dict, path: Path) -> None:
    print("EXPLORATORY")
    print(f"seed={payload['seed']} draws={payload['n_draws']}")
    for cohort_id, cohort in payload["cohorts"].items():
        for horizon, body in cohort["horizons"].items():
            base = next(item for item in body["scenarios"] if item["rate_scale"] == 1.0)
            all_floors = base["all_floors"]
            median = all_floors["median_years"]
            print(
                f"{cohort_id} {horizon} binding={base['binding_floor']} "
                f"all_floors_median={median} origins={body['counts']['origins']}"
            )
    print(f"wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
