"""Synthetic tests for the Grey Deer episode sample builder.

Run:
    python3 -m pytest -q tests/test_grey_deer_episode_samples.py -rA

Synthetic seeded series only. No ``data/`` read or write, no network.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_episode_samples as samples  # noqa: E402
import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402

LONG_DROPS = (400, 1100)
BUFFER = 63


def make_close(
    n: int = 1600,
    drop_at: tuple[int, ...] = LONG_DROPS,
    seed: int = 12345,
    sigma: float = 0.0008,
    start: float = 137.135,
) -> pd.Series:
    """Seeded geometric walk with a permanent 12% level shift at each drop.

    Daily noise is far below the 5% loss label, so the only event origins are
    the sessions whose forward window reaches a shift.
    """
    rng = np.random.default_rng(seed)
    px = float(start) * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    for drop in drop_at:
        px[int(drop) :] *= 0.88
    index = pd.bdate_range("2014-01-02", periods=n)
    return pd.Series(px, index=index, name="close")


def _origins(close: pd.Series, h: int) -> np.ndarray:
    y = stage1.build_labels(close)[h]["Y"]
    return np.flatnonzero(y.eq(1).fillna(False).to_numpy(dtype=bool))


def _expected_origins(n: int, drops: tuple[int, ...], h: int) -> list[int]:
    last_mature = n - 1 - h
    out: list[int] = []
    for drop in drops:
        out.extend(range(max(0, drop - h), min(drop, last_mature + 1)))
    return out


def _intervals_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 <= b1 and b0 <= a1


@pytest.fixture(scope="module")
def long_close() -> pd.Series:
    return make_close()


@pytest.fixture(scope="module")
def long_sample(long_close: pd.Series) -> dict:
    return samples.build_sample(long_close, ticker="SYN", seed=20261013)


@pytest.mark.parametrize("h", [5, 10, 21])
def test_episodes_found_around_injected_drawdowns(long_close, h):
    origins = _origins(long_close, h)
    assert origins.tolist() == _expected_origins(len(long_close), LONG_DROPS, h)
    episodes = samples.event_episodes(long_close, h)
    assert len(episodes) == 2
    dates = [pd.Timestamp(x).strftime("%Y-%m-%d") for x in long_close.index]
    for k, drop in enumerate(LONG_DROPS):
        ep = episodes[k]
        assert ep["episode_id"] == f"h{h}-e{k:03d}"
        assert ep["n_event_origins"] == h
        assert ep["first_event"] == dates[drop - h]
        assert ep["last_event"] == dates[drop - 1]
        lo, hi = ep["window_idx"]
        assert lo == drop - h - stage1.EPISODE_PRE
        assert hi == drop - 1 + h
        assert lo <= drop <= hi
        assert ep["window"] == [dates[lo], dates[hi]]


def test_windows_match_frozen_merge_after_clip():
    series = (
        make_close(),
        make_close(n=90, drop_at=(3, 70), seed=7),
    )
    saw_left_clip = False
    for close in series:
        n = len(close)
        for h in stage1.HORIZONS:
            origins = _origins(close, h)
            merged = stage1.merge_episodes(stage1.event_clusters(origins, h), h)
            episodes = samples.event_episodes(close, h)
            assert len(episodes) == len(merged)
            for ep, raw in zip(episodes, merged):
                raw_lo, raw_hi = int(raw["window"][0]), int(raw["window"][1])
                if raw_lo < 0:
                    saw_left_clip = True
                lo = max(0, raw_lo)
                hi = min(n - 1, raw_hi)
                assert ep["window_idx"] == [lo, hi]
                assert ep["window_idx"][0] >= 0
                assert ep["window_idx"][1] < n
                assert ep["n_event_origins"] == int(sum(len(c) for c in raw["clusters"]))
    assert saw_left_clip


@pytest.mark.parametrize("h", [5, 10, 21])
def test_controls_respect_episode_buffer(long_close, long_sample, h):
    block = long_sample["horizons"][str(h)]
    episodes = block["episodes"]
    controls = block["controls"]
    assert block["shortfall"] == 0
    assert len(controls) == 3 * len(episodes)
    by_id = {ep["episode_id"]: ep for ep in episodes}
    for control in controls:
        start, end = control["window_idx"]
        ep = by_id[control["episode_id"]]
        assert end - start == ep["window_idx"][1] - ep["window_idx"][0]
        assert 0 <= start <= end < len(long_close)
        span = (start - BUFFER, end + BUFFER)
        for other in episodes:
            elo, ehi = other["window_idx"]
            assert not _intervals_overlap(span[0], span[1], elo, ehi)


@pytest.mark.parametrize("h", [5, 10, 21])
def test_controls_contain_no_event_origin(long_close, long_sample, h):
    origins = set(_origins(long_close, h).tolist())
    for control in long_sample["horizons"][str(h)]["controls"]:
        start, end = control["window_idx"]
        assert not any(start <= origin <= end for origin in origins)


@pytest.mark.parametrize("h", [5, 10, 21])
def test_controls_do_not_overlap_each_other(long_sample, h):
    controls = long_sample["horizons"][str(h)]["controls"]
    for i, left in enumerate(controls):
        for right in controls[i + 1 :]:
            a0, a1 = left["window_idx"]
            b0, b1 = right["window_idx"]
            assert not _intervals_overlap(a0, a1, b0, b1)


def test_month_matched_when_match_is_possible(long_close, long_sample):
    dates = [pd.Timestamp(x).strftime("%Y-%m-%d") for x in long_close.index]
    for h in (5, 10, 21):
        block = long_sample["horizons"][str(h)]
        by_id = {ep["episode_id"]: ep for ep in block["episodes"]}
        assert block["controls"]
        for ep in block["episodes"]:
            month = ep["window"][0][5:7]
            outside = [
                i
                for i, iso in enumerate(dates)
                if iso[5:7] == month and not any(
                    other["window_idx"][0] <= i <= other["window_idx"][1]
                    for other in block["episodes"]
                )
            ]
            assert len(outside) >= 20
        for control in block["controls"]:
            ep = by_id[control["episode_id"]]
            same_month = control["window"][0][5:7] == ep["window"][0][5:7]
            assert control["month_matched"] is True
            assert same_month
            assert control["seed"] == 20261013


def test_month_matched_falls_back_when_start_month_is_blocked():
    close = make_close()
    h = 5
    probe = samples.event_episodes(close, h)
    march = set()
    for ep in probe:
        lo, hi = ep["window_idx"]
        march.update(range(lo, hi + 1))
    dates = []
    for i in range(len(close)):
        year = 1990 + (i % 40)
        day = (i % 28) + 1
        month = 3 if i in march else 7
        dates.append(pd.Timestamp(year=year, month=month, day=day))
    close = close.copy()
    close.index = pd.DatetimeIndex(dates)
    episodes = samples.event_episodes(close, h)
    controls = samples.negative_controls(close, h, episodes, seed=20261013)
    assert episodes
    assert controls
    assert len(controls) == 3 * len(episodes)
    for control in controls:
        ep = next(ep for ep in episodes if ep["episode_id"] == control["episode_id"])
        assert ep["window"][0][5:7] == "03"
        assert control["window"][0][5:7] == "07"
        assert control["month_matched"] is False


def test_same_seed_is_byte_identical_and_other_seed_differs(long_close):
    first = samples.build_sample(long_close, ticker="SYN", seed=20261013)
    second = samples.build_sample(long_close, ticker="SYN", seed=20261013)
    other = samples.build_sample(long_close, ticker="SYN", seed=7)
    blob_a = json.dumps(first, sort_keys=True)
    blob_b = json.dumps(second, sort_keys=True)
    assert blob_a == blob_b
    assert blob_a.encode("utf-8") == blob_b.encode("utf-8")
    for h in ("5", "10", "21"):
        assert first["horizons"][h]["episodes"] == other["horizons"][h]["episodes"]
        assert [c["window_idx"] for c in first["horizons"][h]["controls"]] != [
            c["window_idx"] for c in other["horizons"][h]["controls"]
        ]


def test_shortfall_on_short_series_does_not_raise():
    close = make_close(n=40, drop_at=(15,), seed=3)
    sample = samples.build_sample(close, ticker="SYN", seed=20261013)
    assert sample["n_sessions"] == 40
    for h, block in sample["horizons"].items():
        assert block["episodes"], h
        expected = 3 * len(block["episodes"])
        assert len(block["controls"]) < expected
        assert block["shortfall"] == expected - len(block["controls"])
    direct = samples.negative_controls(
        close, 5, sample["horizons"]["5"]["episodes"], seed=20261013
    )
    assert direct == sample["horizons"]["5"]["controls"]


def test_json_contains_no_raw_close(long_close, long_sample):
    blob = json.dumps(long_sample, sort_keys=True)

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                assert isinstance(key, str)
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
        elif isinstance(obj, (str, int, bool)):
            return
        else:
            raise AssertionError(type(obj))

    walk(long_sample)
    for value in long_close.to_numpy(dtype=float):
        assert repr(float(value)) not in blob
    assert long_sample["schema"] == samples.SCHEMA
    assert set(long_sample) == {
        "schema",
        "ticker",
        "seed",
        "n_sessions",
        "first",
        "last",
        "input_sha256",
        "horizons",
    }
    assert set(long_sample["horizons"]) == {"5", "10", "21"}


def test_input_sha256_recipe(long_close, long_sample):
    lines = []
    for label, value in zip(long_close.index, long_close.to_numpy(dtype=float)):
        iso = pd.Timestamp(label).strftime("%Y-%m-%d")
        lines.append(f"{iso} {repr(float(value))}")
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    assert long_sample["input_sha256"] == digest
    assert len(digest) == 64


def test_adjacent_control_is_allowed_when_buffer_is_zero():
    # n=76, drop at 40, h=5. Frozen window is [14, 44], length 31.
    # The only in-range start that clears that window is 45: control [45, 75]
    # shares no session with the episode. A pad of 0 must accept it.
    close = make_close(n=76, drop_at=(40,), seed=9)
    h = 5
    episodes = samples.event_episodes(close, h)
    assert len(episodes) == 1
    assert episodes[0]["window_idx"] == [14, 44]
    controls = samples.negative_controls(
        close, h, episodes, seed=1, per_episode=3, buffer_sessions=0
    )
    assert [c["window_idx"] for c in controls] == [[45, 75]]
    assert controls[0]["control_id"] == f"{episodes[0]['episode_id']}-c000"


def test_max_tries_below_one_places_nothing(long_close):
    episodes = samples.event_episodes(long_close, 5)
    assert episodes
    assert samples.negative_controls(long_close, 5, episodes, seed=1, max_tries=0) == []
    placed = samples.negative_controls(long_close, 5, episodes, seed=1, max_tries=1)
    assert len(placed) == 3 * len(episodes)


def test_main_requires_a_path_and_matches_build_sample(tmp_path, capsys):
    with pytest.raises(SystemExit):
        samples.main([])
    dates = pd.bdate_range("2020-01-02", periods=40)
    px = np.array([100.0] * 15 + [88.0] * 25)
    frame = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "close": px})
    path = tmp_path / "closes.csv"
    frame.to_csv(path, index=False)
    rc = samples.main([str(path), "--ticker", "SYN", "--seed", "11", "--horizons", "5"])
    assert rc == 0
    text = capsys.readouterr().out
    got = json.loads(text)
    reloaded = pd.Series(px, index=pd.to_datetime(dates))
    expected = samples.build_sample(reloaded, ticker="SYN", seed=11, horizons=(5,))
    assert got == expected
    assert "100.0" not in text
    assert "88.0" not in text


def test_rng_source_is_default_rng():
    text = Path(samples.__file__).read_text(encoding="utf-8")
    assert "default_rng" in text
    assert "np.random.seed" not in text
    assert "RandomState" not in text
    assert "random.seed" not in text
    for name in ("event_clusters", "merge_episodes", "cluster_window"):
        assert f"def {name}" not in text


def _consecutive_sessions(n: int, start: date = date(2014, 1, 2)) -> list[date]:
    origin = start.toordinal()
    return [date.fromordinal(origin + offset) for offset in range(n)]


def _mask_from_runs(n: int, runs: tuple[int, ...], gap: int = 1) -> list[bool]:
    mask: list[bool] = []
    for index, length in enumerate(runs):
        if index:
            mask.extend([False] * gap)
        mask.extend([True] * length)
    mask.extend([False] * (n - len(mask)))
    if len(mask) != n:
        raise AssertionError(f"mask length {len(mask)} != {n}")
    return mask


def _true_run_lengths(mask: tuple[bool, ...]) -> list[int]:
    lengths: list[int] = []
    current = 0
    for flag in mask:
        if flag:
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return lengths


def _assert_runs_do_not_touch(mask: tuple[bool, ...]) -> None:
    ends: list[int] = []
    starts: list[int] = []
    in_run = False
    for index, flag in enumerate(mask):
        if flag and not in_run:
            starts.append(index)
            in_run = True
        elif in_run and not flag:
            ends.append(index - 1)
            in_run = False
    if in_run:
        ends.append(len(mask) - 1)
    for end, start in zip(ends, starts[1:]):
        assert start - end >= 2


def test_preserves_run_lengths_count_and_separation():
    n_sessions = 400
    runs = (3, 5, 1, 21)
    sessions = list(pd.bdate_range("2014-01-02", periods=n_sessions).date)
    on_mask = _mask_from_runs(n_sessions, runs)
    assert _true_run_lengths(tuple(on_mask)) == [3, 5, 1, 21]
    masks = samples.matched_protection_masks(sessions, on_mask, n=200, seed=20261013)
    assert len(masks) == 200
    k = sum(runs)
    for mask in masks:
        assert isinstance(mask, tuple)
        assert len(mask) == n_sessions
        assert sum(mask) == k
        assert all(type(flag) is bool for flag in mask)
        assert sorted(_true_run_lengths(mask)) == sorted(runs)
        _assert_runs_do_not_touch(mask)


def test_masks_match_for_the_same_seed_and_differ_for_the_next():
    n_sessions = 400
    runs = (3, 5, 1, 21)
    sessions = list(pd.bdate_range("2014-01-02", periods=n_sessions).date)
    on_mask = _mask_from_runs(n_sessions, runs)
    first = samples.matched_protection_masks(sessions, on_mask, n=30, seed=20261013)
    second = samples.matched_protection_masks(sessions, on_mask, n=30, seed=20261013)
    other = samples.matched_protection_masks(sessions, on_mask, n=30, seed=20261014)
    assert first == second
    assert first != other


def test_no_protection_returns_all_false_masks():
    sessions = _consecutive_sessions(12)
    on_mask = [False] * 12
    masks = samples.matched_protection_masks(sessions, on_mask, n=7, seed=3)
    assert masks == [tuple(on_mask)] * 7


def test_all_true_mask_is_copied():
    sessions = _consecutive_sessions(9)
    on_mask = [True] * 9
    masks = samples.matched_protection_masks(sessions, on_mask, n=6, seed=5)
    assert masks == [tuple(on_mask)] * 6


def test_tight_equal_runs_have_a_single_placement():
    on_mask = [True] * 4 + [False] + [True] * 4
    sessions = _consecutive_sessions(len(on_mask))
    masks = samples.matched_protection_masks(sessions, on_mask, n=10, seed=9)
    assert masks == [tuple(on_mask)] * 10


def test_tight_distinct_runs_only_permute():
    sessions = _consecutive_sessions(4)
    on_mask = [True, True, False, True]
    masks = samples.matched_protection_masks(sessions, on_mask, n=200, seed=11)
    allowed = {
        (True, True, False, True),
        (True, False, True, True),
    }
    assert set(masks) == allowed


def test_rejects_sessions_and_on_mask_length_mismatch():
    sessions = _consecutive_sessions(4)
    with pytest.raises(ValueError, match="on_mask"):
        samples.matched_protection_masks(sessions, [True, False])


def test_rejects_sessions_that_are_not_strictly_increasing():
    sessions = _consecutive_sessions(4)
    bad = [sessions[0], sessions[1], sessions[2], sessions[1]]
    on_mask = [False, True, False, True]
    with pytest.raises(ValueError, match="sessions"):
        samples.matched_protection_masks(bad, on_mask)


def test_rejects_n_below_one():
    sessions = _consecutive_sessions(3)
    on_mask = [True, False, False]
    with pytest.raises(ValueError, match="n must be"):
        samples.matched_protection_masks(sessions, on_mask, n=0)


def test_rejects_block_other_than_21():
    sessions = _consecutive_sessions(3)
    on_mask = [True, False, False]
    with pytest.raises(ValueError, match="block"):
        samples.matched_protection_masks(sessions, on_mask, block=20)


def test_rejects_non_bool_on_mask_element():
    sessions = _consecutive_sessions(3)
    with pytest.raises(ValueError, match="on_mask"):
        samples.matched_protection_masks(sessions, [True, 1, False])


def test_numpy_bool_on_mask_is_accepted():
    sessions = _consecutive_sessions(8)
    on_mask = np.array(_mask_from_runs(8, (2, 3)), dtype=bool)
    assert isinstance(on_mask[0], np.bool_)
    masks = samples.matched_protection_masks(sessions, on_mask, n=5, seed=2)
    assert len(masks) == 5
    for mask in masks:
        assert sorted(_true_run_lengths(mask)) == [2, 3]
        assert sum(mask) == 5


def test_n_sets_how_many_masks_are_returned():
    sessions = _consecutive_sessions(40)
    on_mask = _mask_from_runs(40, (3, 5))
    assert len(samples.matched_protection_masks(sessions, on_mask, n=1, seed=1)) == 1
    assert len(samples.matched_protection_masks(sessions, on_mask, n=200, seed=1)) == 200


def test_run_longer_than_block_is_kept_whole():
    sessions = _consecutive_sessions(80)
    on_mask = _mask_from_runs(80, (30, 8))
    masks = samples.matched_protection_masks(sessions, on_mask, n=20, seed=4)
    for mask in masks:
        assert sorted(_true_run_lengths(mask)) == [8, 30]
        _assert_runs_do_not_touch(mask)


def test_single_run_starts_are_roughly_uniform():
    n_sessions = 30
    run = 5
    n_masks = 2000
    sessions = _consecutive_sessions(n_sessions)
    on_mask = [True] * run + [False] * (n_sessions - run)
    masks = samples.matched_protection_masks(
        sessions, on_mask, n=n_masks, seed=20261013
    )
    assert len(masks) == n_masks
    starts: list[int] = []
    for mask in masks:
        assert sum(mask) == run
        start = mask.index(True)
        assert mask[start : start + run] == tuple(True for _ in range(run))
        assert True not in mask[:start]
        assert True not in mask[start + run :]
        starts.append(start)
    counts = Counter(starts)
    expected = n_masks / 26
    assert set(counts) == set(range(26))
    for start in range(26):
        freq = counts[start]
        assert expected * 0.5 <= freq <= expected * 2.0


def test_public_signature_uses_the_frozen_defaults():
    assert samples.DEFAULT_MASK_N == 200
    assert samples.DEFAULT_MASK_BLOCK == 21
    sig = inspect.signature(samples.matched_protection_masks)
    assert list(sig.parameters) == ["sessions", "on_mask", "n", "seed", "block"]
    assert sig.parameters["n"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["seed"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["block"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["n"].default == 200
    assert sig.parameters["seed"].default == 20261013
    assert sig.parameters["block"].default == 21
    assert sig.parameters["sessions"].annotation == "Sequence[date]"
    assert sig.parameters["on_mask"].annotation == "Sequence[bool]"
    assert sig.return_annotation == "list[tuple[bool, ...]]"
    sessions = _consecutive_sessions(6)
    on_mask = [False, True, True, False, False, False]
    assert len(samples.matched_protection_masks(sessions, on_mask)) == 200
