"""Synthetic tests for the v1.2 episode-rule options.

No real results JSON, no price store, no network. Hand counts are literals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.research.grey_deer_pullback_episode_rule_options as opt  # noqa: E402
import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402

# Gaps: 2, 18, 3, 37.
HAND = [0, 2, 20, 23, 60]


def _hand_windows(dates, gap: int, pre: int, post: int) -> list[list[int]]:
    """Direct reading of the window definition, used only as a test oracle."""
    ordered = [int(x) for x in np.unique(np.asarray(dates, dtype=int))]
    clusters: list[list[int]] = []
    current: list[int] = []
    for event in ordered:
        if current and event - current[-1] > gap:
            clusters.append(current)
            current = []
        current.append(event)
    if current:
        clusters.append(current)
    episodes: list[list[int]] = []
    for cluster in clusters:
        lo = cluster[0] - pre
        hi = cluster[-1] + post
        if episodes and lo <= episodes[-1][1]:
            episodes[-1][1] = max(episodes[-1][1], hi)
        else:
            episodes.append([lo, hi])
    return episodes


def _panel(dates, *, months: int = 9, origins: int = 28) -> dict:
    month_list = [f"2024-{i:02d}" for i in range(1, months + 1)]
    return {
        "event_dates": list(dates),
        "clusters": 0,
        "episode_windows": [],
        "per_ticker_episodes": {"QQQ": 2, "IWM": 3},
        "ticker_events": 8,
        "origins": origins,
        "events": len(set(dates)),
        "event_months": months,
        "event_month_list": month_list,
    }


def _spy() -> dict:
    return {"origins": 10, "events": 4, "clusters": 2, "episodes": 2, "event_months": 3}


def _report() -> dict:
    panel = {f"h{h}": _panel(HAND) for h in opt.HORIZONS}
    spy = {f"h{h}": _spy() for h in opt.HORIZONS}
    return opt.build_report(
        panel,
        spy,
        sources={
            "stage1b_path": "synthetic/stage1b.json",
            "stage1_path": "synthetic/stage1.json",
            "stage1b_sha256": "abc",
            "stage1_sha256": "def",
        },
    )


def test_frozen_constants_match_the_packet():
    assert stage1.EPISODE_PRE == 21
    assert opt.EPISODE_PRE == 21
    assert opt.POWER_MIN_EPISODES == 10
    assert opt.POWER_MIN_MONTHS == 10
    assert opt.COMMITTED_FROZEN == {5: (31, 11), 10: (20, 4), 21: (5, 1)}


def test_floor_met_requires_both_minima():
    assert opt.floor_met(10, 10) is True
    assert opt.floor_met(9, 10) is False
    assert opt.floor_met(10, 9) is False
    assert opt.floor_met(0, 0) is False


def test_reproduce_frozen_matches_stage1_on_synthetic():
    rng = np.random.default_rng(20261013)
    pool = np.arange(0, 400)
    samples = [np.zeros(0, dtype=int), np.array([17])]
    for n in (7, 40):
        samples.append(np.sort(rng.choice(pool, size=n, replace=False)))
    for idx in samples:
        for h in (1, 5, 10, 21):
            got = opt.reproduce_frozen(idx, h)
            clusters = stage1.event_clusters(idx, h)
            episodes = stage1.merge_episodes(clusters, h)
            assert got["n_clusters"] == len(clusters)
            assert got["n_episodes"] == len(episodes)
            assert got["windows"] == [[int(ep["window"][0]), int(ep["window"][1])] for ep in episodes]
            assert got["cluster_sizes"] == [int(len(c)) for c in clusters]
            assert got["cluster_windows"] == [stage1.cluster_window(c, h) for c in clusters]
        if idx.size:
            shuffled = idx[::-1].copy()
            duplicated = np.concatenate([idx, idx[:1]])
            assert opt.reproduce_frozen(shuffled, 5)["windows"] == opt.reproduce_frozen(idx, 5)["windows"]
            assert opt.reproduce_frozen(duplicated, 5)["windows"] == opt.reproduce_frozen(idx, 5)["windows"]


def test_reproduce_frozen_hand_counted():
    got = opt.reproduce_frozen(HAND, 5)
    assert got["n_clusters"] == 3
    assert got["n_episodes"] == 2
    assert got["cluster_sizes"] == [2, 2, 1]
    assert got["windows"] == [[-21, 28], [39, 65]]
    assert got["windows"] == _hand_windows(HAND, 5, 21, 5)


def test_gap_with_frozen_window_hand_counted():
    expected = {
        1: (5, 2, [[-21, 28], [39, 65]]),
        2: (4, 2, [[-21, 28], [39, 65]]),
        3: (3, 2, [[-21, 28], [39, 65]]),
        5: (3, 2, [[-21, 28], [39, 65]]),
        10: (3, 2, [[-21, 28], [39, 65]]),
        21: (2, 2, [[-21, 28], [39, 65]]),
    }
    for gap, (n_clusters, n_episodes, windows) in expected.items():
        got = opt.apply_gap_with_frozen_window(HAND, gap, 5)
        assert got["clusters"] == n_clusters
        assert got["episodes"] == n_episodes
        assert got["windows"] == windows
        assert got["windows"] == _hand_windows(HAND, gap, 21, 5)
    # g=1 must not be silently replaced by the horizon gap.
    assert opt.apply_gap_with_frozen_window(HAND, 1, 5)["clusters"] == 5
    assert opt.apply_gap_with_frozen_window(HAND, 21, 5)["clusters"] == 2


def test_window_pre_hand_counted_and_matches_oracle():
    expected = {
        0: [[0, 7], [20, 28], [60, 65]],
        5: [[-5, 7], [15, 28], [55, 65]],
        10: [[-10, 7], [10, 28], [50, 65]],
        21: [[-21, 28], [39, 65]],
    }
    for pre, windows in expected.items():
        got = opt.apply_window_pre(HAND, 5, pre)
        assert got["windows"] == windows
        assert got["episodes"] == len(windows)
        assert got["windows"] == _hand_windows(HAND, 5, pre, 5)
    rng = np.random.default_rng(7)
    for _ in range(15):
        idx = np.sort(rng.choice(np.arange(0, 180), size=12, replace=False))
        for h in (5, 10, 21):
            for pre in (0, 5, 10, 21):
                got = opt.apply_window_pre(idx, h, pre)
                assert got["windows"] == _hand_windows(idx, h, pre, h)
            frozen = stage1.merge_episodes(stage1.event_clusters(idx, h), h)
            got21 = opt.apply_window_pre(idx, h, 21)
            assert got21["windows"] == [[int(ep["window"][0]), int(ep["window"][1])] for ep in frozen]


def test_no_window_merge_hand_counted():
    got = opt.apply_frozen_gap_no_window_merge(HAND, 5)
    assert got["clusters"] == 3
    assert got["episodes"] == 3
    assert got["windows"] is None
    assert got["event_spans"] == [[0, 2], [20, 23], [60, 60]]
    # pre = 0 does not merge frozen-gap clusters on this example.
    pre0 = opt.apply_window_pre(HAND, 5, 0)
    assert pre0["episodes"] == got["episodes"]
    assert pre0["event_spans"] == got["event_spans"]


def test_quiet_reset_hand_counted():
    assert opt.apply_quiet_reset(HAND, 5)["event_spans"] == [[0, 2], [20, 23], [60, 60]]
    assert opt.apply_quiet_reset(HAND, 10)["episodes"] == 3
    assert opt.apply_quiet_reset(HAND, 21)["event_spans"] == [[0, 23], [60, 60]]
    assert opt.apply_quiet_reset(HAND, 42)["event_spans"] == [[0, 60]]
    assert opt.apply_quiet_reset(HAND, 5)["episodes"] == opt.apply_frozen_gap_no_window_merge(HAND, 5)["episodes"]


def test_quiet_reset_empty_and_single():
    for q in opt.QUIET_MENU:
        empty = opt.apply_quiet_reset([], q)
        assert empty["episodes"] == 0
        assert empty["clusters"] == 0
        assert empty["event_spans"] == []
        single = opt.apply_quiet_reset([7], q)
        assert single["episodes"] == 1
        assert single["clusters"] == 1
        assert single["event_spans"] == [[7, 7]]
    assert opt.longest_quiet_stretch([])["max_gap"] is None
    assert opt.longest_quiet_stretch([7])["max_event_free_sessions"] is None
    quiet = opt.longest_quiet_stretch(HAND)
    assert quiet["max_gap"] == 37
    assert quiet["max_event_free_sessions"] == 36
    assert quiet["left_event_index"] == 23
    assert quiet["right_event_index"] == 60


def test_extract_keeps_only_structural_fields():
    def binary(dates):
        return {
            "event_dates": dates,
            "clusters": 1,
            "episode_windows": [[0, 1]],
            "per_ticker_episodes": {"QQQ": 1},
            "ticker_events": 1,
            "origins": 14,
            "events": len(dates),
            "event_months": 1,
            "event_month_list": ["2024-01"],
            "power_floor": {"met": True},
            "bss": 0.25,
        }

    payload = {
        "bootstrap": {"n_draws": 1},
        "claims": {"point": 1},
        "episodes": {
            "h5": {"binary": binary([1, 2]), "quantile": {"bss": 1}},
            "h10": {"binary": binary([1, 2, 3])},
            "h21": {"binary": binary([4])},
        },
    }
    panel = opt.extract_panel_binary(payload)
    assert set(panel) == {"h5", "h10", "h21"}
    assert "bss" not in panel["h5"]
    assert "power_floor" not in panel["h5"]
    assert panel["h21"]["event_dates"] == [4]
    spy_payload = {
        "gates": {"x": 1},
        "episodes": {
            f"h{h}": {
                "binary": {
                    "honest_n": {
                        "origins": 3,
                        "events": 1,
                        "clusters": 1,
                        "episodes": 1,
                        "event_months": 1,
                        "bss": -0.5,
                        "event_month_list": ["2024-01"],
                    }
                }
            }
            for h in opt.HORIZONS
        },
    }
    spy = opt.extract_spy_binary_honest_n(spy_payload)
    assert set(spy["h5"]) == {"origins", "events", "clusters", "episodes", "event_months"}
    assert "bss" not in spy["h5"]


def test_months_still_bind_the_floor_when_episodes_clear():
    dates = list(range(0, 500, 50))
    assert len(dates) == 10
    panel = {f"h{h}": _panel(dates, months=9, origins=28) for h in opt.HORIZONS}
    spy = {f"h{h}": _spy() for h in opt.HORIZONS}
    report = opt.build_report(panel, spy)
    for hor in report["horizons"]:
        for row in opt.iter_rule_rows(hor):
            assert row["episodes"] == 10
            assert row["event_months"] == 9
            assert row["floor_met"] is False
    assert report["rules_meeting_floor_on_every_horizon"] == []


def test_reproduction_problems_follow_the_committed_targets():
    report = _report()
    assert opt.reproduction_problems(report)
    for row in report["reproduction"]:
        clusters, episodes = opt.COMMITTED_FROZEN[row["h"]]
        row["stored_clusters"] = clusters
        row["stored_episodes"] = episodes
        row["reproduced_clusters"] = clusters
        row["reproduced_episodes"] = episodes
        row["windows_match"] = True
        row["events_match"] = True
        row["months_match"] = True
    assert opt.reproduction_problems(report) == []
    report["reproduction"][2]["reproduced_episodes"] = 2
    problems = opt.reproduction_problems(report)
    assert len(problems) == 1
    assert "h21" in problems[0]


def test_json_and_markdown_are_deterministic(tmp_path):
    report = _report()
    first = opt.render_json(report)
    second = opt.render_json(report)
    assert first == second
    parsed = json.loads(first)
    assert parsed["disclosure"] == opt.DISCLOSURE
    assert parsed["floor_warning"] == opt.FLOOR_WARNING
    left = tmp_path / "a.json"
    right = tmp_path / "b.json"
    left.write_text(first)
    right.write_text(opt.render_json(json.loads(first)))
    # Key order is canonical, so a re-dump of the parsed object matches.
    assert left.read_bytes() == right.read_bytes()
    md_a = opt.render_markdown(report)
    md_b = opt.render_markdown(report)
    assert md_a == md_b
    (tmp_path / "memo.md").write_text(md_a)
    assert opt.DISCLOSURE in md_a
    assert opt.FLOOR_WARNING in md_a
    for hor in report["horizons"]:
        assert opt.gap_table(hor) in md_a
        assert opt.pre_table(hor) in md_a
        assert opt.quiet_table(hor) in md_a
        assert opt.nomerge_line(hor) in md_a
    assert opt.reproduction_table(report) in md_a
    assert opt.density_table(report) in md_a
    assert opt.histogram_table(report) in md_a
    assert opt.collapse_table(report) in md_a
    assert opt.comparison_table(report) in md_a
    assert opt.per_ticker_table(report) in md_a
    assert "p-hacking the power floor" in md_a


def test_gap_histogram_hand_counted():
    hist = opt.gap_histogram(HAND)
    # Gaps 2, 18, 3, 37.
    assert hist["n_gaps"] == 4
    assert hist["min"] == 2
    assert hist["max"] == 37
    assert hist["median"] == "10.5"
    by_label = {row["label"]: row["n"] for row in hist["bins"]}
    assert by_label["0"] == 0
    assert by_label["1"] == 0
    assert by_label["2"] == 1
    assert by_label["3"] == 1
    assert by_label["11-21"] == 1
    assert by_label["22-42"] == 1
    assert by_label["64+"] == 0
