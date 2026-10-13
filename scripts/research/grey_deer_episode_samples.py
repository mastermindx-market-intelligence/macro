"""Grey Deer episode and matched negative-control sample builder.

One close series in. Frozen-rule event episodes and seeded control windows
out. Later mechanism studies (T13, T14, T19) freeze this sample before they
look at outcomes.

Labels, clusters and episode windows are the stage-1 functions. This module
calls them and does not reimplement them. The contract is
``research/grey_deer/EPISODE_SAMPLE_SPEC_2026-10-13.md``.

No file reads, no network, no price store. The optional CLI takes a CSV path
as a required argument and has no default path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402

SCHEMA = "grey_deer_episode_samples.v1"
DEFAULT_HORIZONS = (5, 10, 21)
DEFAULT_SEED = 20261013
DEFAULT_PER_EPISODE = 3
DEFAULT_BUFFER_SESSIONS = 63
DEFAULT_MAX_TRIES = 10_000

# Tripwire: the schema names these frozen constants. A silent change in the
# pinned stage-1 module would relabel episodes without a schema bump.
if tuple(int(h) for h in stage1.HORIZONS) != DEFAULT_HORIZONS:
    raise RuntimeError(
        f"stage-1 horizons are {tuple(stage1.HORIZONS)}, not {DEFAULT_HORIZONS}"
    )
if int(stage1.EPISODE_PRE) != 21:
    raise RuntimeError(f"stage-1 EPISODE_PRE is {stage1.EPISODE_PRE}, not 21")


def _iso_dates(index) -> list[str]:
    """Session dates as ``YYYY-MM-DD`` in index order."""
    out: list[str] = []
    for label in index:
        ts = pd.Timestamp(label)
        if pd.isna(ts):
            raise ValueError("close index contains a missing session date")
        out.append(ts.strftime("%Y-%m-%d"))
    return out


def _input_sha256(close: pd.Series) -> str:
    """Hex SHA-256 of the series identity. Not invertible to a close.

    One line per session, ``YYYY-MM-DD`` + space + ``repr(float(close))``,
    joined with ``\\n`` and no trailing newline.
    """
    dates = _iso_dates(close.index)
    values = close.to_numpy(dtype=float)
    lines = [f"{iso} {repr(float(value))}" for iso, value in zip(dates, values)]
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _event_origin_indices(close: pd.Series, h: int) -> np.ndarray:
    """Session indices where the frozen horizon-``h`` label ``Y`` equals 1.

    ``build_labels`` returns ``{horizon: {"A": series, "Y": series}}``.
    Immature rows stay missing and are not origins.
    """
    h = int(h)
    labels = stage1.build_labels(close)
    if h not in stage1.HORIZONS or h not in labels:
        known = tuple(int(x) for x in stage1.HORIZONS)
        raise ValueError(f"horizon {h} is outside the frozen horizons {known}")
    y = labels[h]["Y"]
    flag = y.eq(1).fillna(False).to_numpy(dtype=bool)
    return np.flatnonzero(flag)


def event_episodes(close: pd.Series, h: int) -> list[dict]:
    """Event episodes for one horizon, in time order.

    Origins are ``Y == 1`` from ``build_labels``. Clustering and the episode
    window are ``event_clusters`` and ``merge_episodes`` (that path calls
    ``cluster_window`` and pads with ``EPISODE_PRE``). The emitted window is
    the frozen window clipped to ``[0, n_sessions - 1]``, as ISO dates and as
    those same session indices.

    ``episode_id`` is ``h{h}-e{k:03d}`` with ``k`` starting at 0.
    """
    h = int(h)
    n = int(len(close))
    if n == 0:
        return []
    origins = _event_origin_indices(close, h)
    merged = stage1.merge_episodes(stage1.event_clusters(origins, h), h)
    dates = _iso_dates(close.index)
    episodes: list[dict] = []
    for k, merged_ep in enumerate(merged):
        raw_lo = int(merged_ep["window"][0])
        raw_hi = int(merged_ep["window"][1])
        lo = max(0, raw_lo)
        hi = min(n - 1, raw_hi)
        clusters = merged_ep["clusters"]
        first_i = int(clusters[0][0])
        last_i = int(clusters[-1][-1])
        episodes.append(
            {
                "episode_id": f"h{h}-e{k:03d}",
                "window": [dates[lo], dates[hi]],
                "window_idx": [lo, hi],
                "n_event_origins": int(sum(len(cluster) for cluster in clusters)),
                "first_event": dates[first_i],
                "last_event": dates[last_i],
            }
        )
    return episodes


def _eligible_pools(
    n: int,
    length: int,
    buffer_sessions: int,
    episode_windows: list[tuple[int, int]],
    origins: np.ndarray,
    accepted: list[tuple[int, int]],
    dates: list[str],
    target_month: int,
) -> tuple[list[int], list[int]]:
    """In-range starts split into month-matched and the rest.

    A start is eligible when the window sits inside the series, the padded
    span ``[start - buffer, end + buffer]`` misses every episode window, the
    window holds no event origin, and the window misses every accepted
    control. The scan is one pass over a finite start list.
    """
    if length <= 0 or length > n:
        return [], []
    n_starts = n - length + 1
    banned = np.zeros(n_starts, dtype=bool)
    pad = int(buffer_sessions)
    for elo, ehi in episode_windows:
        lo_ban = int(elo) - (length - 1 + pad)
        hi_ban = int(ehi) + pad
        a = max(0, lo_ban)
        b = min(n_starts - 1, hi_ban)
        if a <= b:
            banned[a : b + 1] = True
    for origin in origins:
        o = int(origin)
        a = max(0, o - length + 1)
        b = min(n_starts - 1, o)
        if a <= b:
            banned[a : b + 1] = True
    for c0, c1 in accepted:
        a = max(0, int(c0) - length + 1)
        b = min(n_starts - 1, int(c1))
        if a <= b:
            banned[a : b + 1] = True
    matched: list[int] = []
    other: list[int] = []
    for start in np.flatnonzero(~banned):
        start_i = int(start)
        if int(dates[start_i][5:7]) == target_month:
            matched.append(start_i)
        else:
            other.append(start_i)
    return matched, other


def _propose(
    rng: np.random.Generator,
    matched: list[int],
    other: list[int],
    max_tries: int,
) -> tuple[int, bool] | None:
    """One uniform draw from the preferred pool, or None.

    ``max_tries`` is the proposal cap for this slot. The pools are already
    the complete eligible sets, so the first proposal hits. Any cap below 1
    places nothing. A positive cap still finds a window whenever one exists,
    and it prefers a month match whenever one exists.
    """
    if max_tries < 1:
        return None
    if matched:
        return int(matched[int(rng.integers(0, len(matched)))]), True
    if other:
        return int(other[int(rng.integers(0, len(other)))]), False
    return None


def negative_controls(
    close: pd.Series,
    h: int,
    episodes: list[dict],
    *,
    seed: int,
    per_episode: int = DEFAULT_PER_EPISODE,
    buffer_sessions: int = DEFAULT_BUFFER_SESSIONS,
    max_tries: int = DEFAULT_MAX_TRIES,
) -> list[dict]:
    """Seeded control windows matched to ``episodes``.

    Episodes are filled in list order, slots in order, from one
    ``numpy.random.default_rng(seed)``. Each accepted control removes its
    window from later draws. A slot whose eligible set is empty is skipped
    and the rest of that episode's slots are skipped with it. The caller
    records the shortfall as ``len(episodes) * per_episode - len(returned)``.
    This function returns fewer controls and does not raise when the series
    runs out of room.

    ``buffer_sessions`` is the pad in the span rule and is meant to be >= 0.
    """
    h = int(h)
    seed = int(seed)
    per_episode = int(per_episode)
    buffer_sessions = int(buffer_sessions)
    max_tries = int(max_tries)
    n = int(len(close))
    if n == 0 or per_episode <= 0 or max_tries < 1 or not episodes:
        return []
    dates = _iso_dates(close.index)
    origins = _event_origin_indices(close, h)
    episode_windows = [
        (int(ep["window_idx"][0]), int(ep["window_idx"][1])) for ep in episodes
    ]
    rng = np.random.default_rng(seed)
    accepted: list[tuple[int, int]] = []
    controls: list[dict] = []
    for ep in episodes:
        lo = int(ep["window_idx"][0])
        hi = int(ep["window_idx"][1])
        length = hi - lo + 1
        target_month = int(str(ep["window"][0])[5:7])
        episode_id = str(ep["episode_id"])
        placed = 0
        for _slot in range(per_episode):
            matched, other = _eligible_pools(
                n,
                length,
                buffer_sessions,
                episode_windows,
                origins,
                accepted,
                dates,
                target_month,
            )
            choice = _propose(rng, matched, other, max_tries)
            if choice is None:
                break
            start, month_matched = choice
            end = start + length - 1
            accepted.append((start, end))
            controls.append(
                {
                    "control_id": f"{episode_id}-c{placed:03d}",
                    "episode_id": episode_id,
                    "window": [dates[start], dates[end]],
                    "window_idx": [int(start), int(end)],
                    "month_matched": bool(month_matched),
                    "seed": seed,
                }
            )
            placed += 1
    return controls


def build_sample(
    close: pd.Series,
    *,
    ticker: str,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Episodes, controls and shortfall for each horizon.

    Each horizon starts a new ``default_rng(seed)``. Horizons do not share a
    random stream. The dict holds no raw closes. ``shortfall`` is
    ``len(episodes) * 3 - len(controls)`` using the default ``per_episode``.
    """
    seed = int(seed)
    dates = _iso_dates(close.index)
    horizon_out: dict[str, dict] = {}
    for h in horizons:
        h = int(h)
        episodes = event_episodes(close, h)
        controls = negative_controls(
            close,
            h,
            episodes,
            seed=seed,
            per_episode=DEFAULT_PER_EPISODE,
            buffer_sessions=DEFAULT_BUFFER_SESSIONS,
            max_tries=DEFAULT_MAX_TRIES,
        )
        horizon_out[str(h)] = {
            "episodes": episodes,
            "controls": controls,
            "shortfall": int(len(episodes) * DEFAULT_PER_EPISODE - len(controls)),
        }
    return {
        "schema": SCHEMA,
        "ticker": str(ticker),
        "seed": seed,
        "n_sessions": int(len(close)),
        "first": dates[0] if dates else "",
        "last": dates[-1] if dates else "",
        "input_sha256": _input_sha256(close),
        "horizons": horizon_out,
    }


def _series_from_csv(path: str, date_col: str, close_col: str) -> pd.Series:
    frame = pd.read_csv(path)
    missing = [col for col in (date_col, close_col) if col not in frame.columns]
    if missing:
        raise ValueError(f"CSV is missing columns {missing}")
    values = pd.to_numeric(frame[close_col], errors="raise").to_numpy(dtype=float)
    index = pd.to_datetime(frame[date_col])
    return pd.Series(values, index=index)


def main(argv: list[str] | None = None) -> int:
    """Print one sample JSON for a CSV given on the command line.

    ``csv_path`` is required. There is no default path.
    """
    parser = argparse.ArgumentParser(
        prog="grey_deer_episode_samples",
        description=(
            "Build a Grey Deer episode sample from one close CSV. "
            "The CSV path is required; there is no default path."
        ),
    )
    parser.add_argument("csv_path", help="CSV path. Required.")
    parser.add_argument("--ticker", required=True, help="Ticker stored on the sample.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=None,
        help="Horizons to emit. Default: 5 10 21.",
    )
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--close-col", default="close")
    args = parser.parse_args(argv)
    try:
        close = _series_from_csv(args.csv_path, args.date_col, args.close_col)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    horizons = tuple(int(h) for h in args.horizons) if args.horizons is not None else DEFAULT_HORIZONS
    sample = build_sample(close, ticker=args.ticker, horizons=horizons, seed=int(args.seed))
    sys.stdout.write(json.dumps(sample, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
