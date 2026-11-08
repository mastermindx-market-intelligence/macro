"""Design options for a v1.2 date-axis episode rule (Grey Deer W7, D9 alt).

The frozen v1.1 panel rule is three steps: a date is an event when any ticker
has Y=1, dates cluster when the session-index gap is at most h, and clusters
merge into one episode when the windows [first - 21, last + h] overlap.
Stage 1b's h21 union collapses to one episode. This script reproduces that
collapse from the committed event dates, decomposes it, and evaluates
alternative rules on those same dates.

It imports ``event_clusters``, ``cluster_window``, ``merge_episodes`` and
``EPISODE_PRE`` from the frozen stage-1 script and does not reimplement them.
A pre-window other than 21 is the frozen overlap test on shifted indices
(see ``partition_with_pre``). No price store, no network, no skill statistic.

The memo this module writes is a design-options note. It is not a
preregistration freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.research.grey_deer_pullback_stage1 import (  # noqa: E402
    EPISODE_PRE,
    POWER_MIN_EPISODES,
    POWER_MIN_MONTHS,
    cluster_window,
    event_clusters,
    merge_episodes,
)

SCHEMA = "grey_deer_pullback_episode_rule_options/v1"
AS_OF = "2026-10-13"
HORIZONS = (5, 10, 21)
GAP_MENU = (1, 2, 3, 5, 10, 21)
PRE_MENU = (0, 5, 10, 21)
QUIET_MENU = (5, 10, 21, 42)
COMMITTED_FROZEN = {5: (31, 11), 10: (20, 4), 21: (5, 1)}
PANEL_ORDER = (
    "QQQ",
    "IWM",
    "DIA",
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
)
GAP_BINS = (
    ("0", 0, 0),
    ("1", 1, 1),
    ("2", 2, 2),
    ("3", 3, 3),
    ("4-5", 4, 5),
    ("6-10", 6, 10),
    ("11-21", 11, 21),
    ("22-42", 22, 42),
    ("43-63", 43, 63),
    ("64+", 64, None),
)
FLOOR_WARNING = (
    "Choosing a rule because it meets the 10-episode / 10-month floor "
    "on this consumed sample is p-hacking the power floor."
)
DISCLOSURE = "this rule was chosen after observing v1.1 event-date density (not skill)"
NOT_COMPUTABLE = (
    {
        "id": "breadth",
        "name": "Breadth threshold",
        "rule": (
            "A session is a panel event date only when at least m names have "
            "Y=1 on that session. A predeclared gap and window then run on "
            "the dates that survive."
        ),
        "needs": (
            "The per-session count of names with Y=1 on the comparison-set "
            "date axis, or the per-name event dates that would produce it. "
            "The committed union records only that the count was at least one. "
            "The ticker-event total is a sum across sessions, not a per-date histogram."
        ),
    },
    {
        "id": "common_shock",
        "name": "Per-ticker episodes with a common-shock correction",
        "rule": (
            "Count episodes on each name, then treat episodes that overlap in "
            "time as one common shock. Honest-N is the number of common shocks, "
            "not the sum of the per-name counts."
        ),
        "needs": (
            "Per-name event dates or per-name episode windows. The artifact "
            "stores the per-name episode count only, so overlap across names "
            "cannot be recovered."
        ),
    },
    {
        "id": "sector",
        "name": "Sector-stratified episodes",
        "rule": (
            "Form the union of event dates inside a predeclared grouping of "
            "names, then run the episode rule inside each group."
        ),
        "needs": (
            "Per-name event dates. The sector labels of these ETFs can be "
            "named without data. The dates cannot. A group union cannot be "
            "rebuilt from the panel-wide union or from per-name counts."
        ),
    },
)
CANDIDATES = (
    {
        "id": "C1",
        "title": "Frozen gap, no window merge",
        "family": "frozen_gap_no_window_merge",
        "computable": True,
        "justification": (
            "v1.1 names a cluster with the gap rule and then merges clusters "
            "whose dependence buffers overlap. The buffer exists so origins "
            "near an event are not treated as independent evidence. Overlap of "
            "two buffers is not a reason to call the clusters one spell. "
            "Dropping the window merge keeps the buffer available for a later "
            "deletion rule and lets the gap rule name the episode. The reason "
            "is the two-step structure of the frozen rule. It is not a skill "
            "result, and it is not the floor column."
        ),
    },
    {
        "id": "C2",
        "title": "Quiet-reset at Q=21, no window merge, same Q at every horizon",
        "family": "quiet_reset",
        "q": 21,
        "computable": True,
        "justification": (
            "v1.1 lets the label horizon set the gap, so a longer outcome "
            "window is also a longer chain. The frozen rule already contains "
            "a dependence scale that is not the label horizon: the 21-session "
            "pre-window. A quiet-reset at 21, on each horizon's own event "
            "dates, with no window merge, uses that scale at every horizon. "
            "The union's event-date occupancy is why a gap as short as the "
            "label horizon chains sessions. A v1.2 preregistration has to "
            "disclose that this density was seen. 21 is taken from the "
            "pre-window constant. It is not taken from the rows that clear "
            "the floor."
        ),
    },
    {
        "id": "C3",
        "title": "Breadth threshold m=2, after per-date counts are retained",
        "family": "breadth",
        "computable": False,
        "justification": (
            "The panel event date is any session on which at least one name "
            "has Y=1. That union is what fills the date axis. A spell that is "
            "supposed to be shared needs a second name on the session. m=2 is "
            "that minimum confirmation. It is a property of a common-move "
            "question. This memo has no episode count for it: the artifacts "
            "do not store per-date breadth. A preregistration that wants a "
            "breadth rule has to keep those counts and must not choose m by "
            "which value clears the floor on this sample."
        ),
    },
)

DEFAULT_STAGE1B = ROOT / "research/grey_deer/pullback_stage1b/PULLBACK_STAGE1B_RESULTS.json"
DEFAULT_STAGE1 = ROOT / "research/grey_deer/PULLBACK_STAGE1_RESULTS_2026-10-11.json"
DEFAULT_JSON = (
    ROOT / "research/grey_deer/pullback_episode_rule_options/EPISODE_RULE_OPTIONS_2026-10-13.json"
)
DEFAULT_MD = ROOT / "research/grey_deer/PULLBACK_EPISODE_RULE_OPTIONS_V1_2_2026-10-13.md"


def event_date_index(event_dates) -> np.ndarray:
    """Sorted unique session indices. An event date is a set element."""
    arr = np.asarray(event_dates, dtype=int).reshape(-1)
    if arr.size == 0:
        return np.zeros(0, dtype=int)
    return np.unique(arr)


def floor_met(n_episodes: int, n_event_months: int) -> bool:
    """True when both frozen power-floor minima are met."""
    return (
        int(n_episodes) >= int(POWER_MIN_EPISODES)
        and int(n_event_months) >= int(POWER_MIN_MONTHS)
    )


def _ratio(numerator: int, denominator: int) -> dict:
    num = int(numerator)
    den = int(denominator)
    text = None if den == 0 else f"{num / den:.6f}"
    return {"numerator": num, "denominator": den, "text": text}


def reproduce_frozen(event_dates, h: int) -> dict:
    """Cluster and merge with the frozen stage-1 functions.

    Returns counts and windows. ``windows`` is the merged
    ``[first - EPISODE_PRE, last + h]`` list. ``cluster_windows`` is
    ``cluster_window`` on each cluster before the merge.
    """
    h = int(h)
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, h)
    episodes = merge_episodes(clusters, h)
    return {
        "h": h,
        "n_event_dates": int(dates.size),
        "n_clusters": int(len(clusters)),
        "n_episodes": int(len(episodes)),
        "windows": [[int(ep["window"][0]), int(ep["window"][1])] for ep in episodes],
        "cluster_sizes": [int(len(c)) for c in clusters],
        "cluster_windows": [cluster_window(c, h) for c in clusters],
    }


def partition_with_pre(clusters: list[np.ndarray], post: int, pre: int) -> list[dict]:
    """Overlap-merge ``clusters``. Each window is ``[first - pre, last + post]``.

    ``pre == EPISODE_PRE`` calls ``merge_episodes`` directly. Any other pre
    shifts every session index by ``EPISODE_PRE - pre`` and calls
    ``merge_episodes`` with post length ``post - (EPISODE_PRE - pre)``. The
    frozen window ``[first' - 21, last' + post']`` then equals
    ``[first - pre, last + post]``, so the overlap test stays inside the
    frozen function. Returned member arrays are in the original index.
    """
    post = int(post)
    pre = int(pre)
    if pre < 0:
        raise ValueError("pre must be >= 0")
    if not clusters:
        return []
    if pre == int(EPISODE_PRE):
        merged = merge_episodes(clusters, post)
        delta = 0
    else:
        delta = int(EPISODE_PRE) - pre
        shifted = [np.asarray(c, dtype=int) + delta for c in clusters]
        merged = merge_episodes(shifted, post - delta)
    if sum(len(ep["clusters"]) for ep in merged) != len(clusters):
        raise RuntimeError("merge_episodes did not return every cluster")
    out = []
    for ep in merged:
        members = [np.asarray(c, dtype=int) - delta for c in ep["clusters"]]
        out.append(
            {
                "window": [int(ep["window"][0]), int(ep["window"][1])],
                "event_span": [int(members[0][0]), int(members[-1][-1])],
            }
        )
    return out


def _pack_partition(h: int, clusters: list[np.ndarray], parts: list[dict], *, windows: bool) -> dict:
    return {
        "h": int(h),
        "clusters": int(len(clusters)),
        "episodes": int(len(parts)),
        "windows": [p["window"] for p in parts] if windows else None,
        "event_spans": [p["event_span"] for p in parts],
    }


def apply_gap_with_frozen_window(event_dates, gap: int, horizon_h: int) -> dict:
    """Gap threshold ``gap``, then the frozen window merge at horizon ``horizon_h``.

    The window pre is ``EPISODE_PRE`` and the window post is the label horizon,
    not ``gap``.
    """
    gap = int(gap)
    horizon_h = int(horizon_h)
    if gap < 1:
        raise ValueError("gap must be >= 1")
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, gap)
    parts = partition_with_pre(clusters, horizon_h, int(EPISODE_PRE))
    packed = _pack_partition(horizon_h, clusters, parts, windows=True)
    packed["gap"] = gap
    packed["pre"] = int(EPISODE_PRE)
    packed["post"] = horizon_h
    return packed


def apply_frozen_gap_no_window_merge(event_dates, h: int) -> dict:
    """Frozen gap. Each cluster is one episode. No window merge."""
    h = int(h)
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, h)
    spans = [[int(c[0]), int(c[-1])] for c in clusters]
    return {
        "h": h,
        "clusters": int(len(clusters)),
        "episodes": int(len(clusters)),
        "windows": None,
        "event_spans": spans,
    }


def apply_window_pre(event_dates, h: int, pre: int) -> dict:
    """Frozen gap, window pre ``pre``, window post ``h``."""
    h = int(h)
    pre = int(pre)
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, h)
    parts = partition_with_pre(clusters, h, pre)
    packed = _pack_partition(h, clusters, parts, windows=True)
    packed["pre"] = pre
    packed["post"] = h
    return packed


def apply_quiet_reset(event_dates, q: int) -> dict:
    """New episode after at least ``q`` consecutive event-free sessions.

    Between event indices ``e`` and ``f`` the event-free count is ``f - e - 1``.
    A break is ``f - e - 1 >= q``, i.e. a session-index gap strictly greater
    than ``q``. That is ``event_clusters(dates, q)`` with no window merge.
    An empty set has 0 episodes. A single date has 1.
    """
    q = int(q)
    if q < 1:
        raise ValueError("Q must be >= 1")
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, q)
    spans = [[int(c[0]), int(c[-1])] for c in clusters]
    return {
        "q": q,
        "clusters": int(len(clusters)),
        "episodes": int(len(clusters)),
        "windows": None,
        "event_spans": spans,
    }


def gap_histogram(event_dates) -> dict:
    """Histogram of session-index gaps between consecutive event dates."""
    dates = event_date_index(event_dates)
    if dates.size < 2:
        gaps: list[int] = []
    else:
        gaps = [int(g) for g in np.diff(dates).tolist()]
    counts = []
    for label, lo, hi in GAP_BINS:
        if hi is None:
            n = sum(1 for g in gaps if g >= lo)
        else:
            n = sum(1 for g in gaps if lo <= g <= hi)
        counts.append({"label": label, "n": int(n)})
    return {
        "n_gaps": int(len(gaps)),
        "min": None if not gaps else int(min(gaps)),
        "max": None if not gaps else int(max(gaps)),
        "median": _median_text(gaps),
        "bins": counts,
    }


def _median_text(gaps: list[int]) -> str | None:
    if not gaps:
        return None
    ordered = sorted(gaps)
    n = len(ordered)
    if n % 2 == 1:
        return str(ordered[n // 2])
    total = ordered[n // 2 - 1] + ordered[n // 2]
    if total % 2 == 0:
        return str(total // 2)
    return f"{total / 2:.1f}"


def longest_quiet_stretch(event_dates) -> dict:
    """Longest run of event-free sessions between consecutive event dates.

    Event-free sessions between indices ``e`` and ``f`` equal ``f - e - 1``.
    Ties take the earliest pair. Empty and singleton inputs have no interior
    stretch.
    """
    dates = event_date_index(event_dates)
    if dates.size < 2:
        return {
            "max_gap": None,
            "max_event_free_sessions": None,
            "left_event_index": None,
            "right_event_index": None,
        }
    gaps = np.diff(dates)
    i = int(np.argmax(gaps))
    gap = int(gaps[i])
    return {
        "max_gap": gap,
        "max_event_free_sessions": gap - 1,
        "left_event_index": int(dates[i]),
        "right_event_index": int(dates[i + 1]),
    }


def collapse_decomposition(event_dates, h: int) -> dict:
    """Split the frozen reduction into the gap rule and the window merge.

    For a non-empty event-date set the frozen functions satisfy
    ``n_clusters = 1 + count(gaps > h)`` and
    ``n_episodes = 1 + count(gaps > h + EPISODE_PRE)``.
    A gap of ``h + EPISODE_PRE`` still merges. Only a strictly larger gap
    starts a new episode.
    """
    h = int(h)
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, h)
    episodes = merge_episodes(clusters, h)
    reach = h + int(EPISODE_PRE)
    if dates.size < 2:
        gaps = np.zeros(0, dtype=int)
    else:
        gaps = np.diff(dates)
    n_gt_h = int(np.sum(gaps > h)) if gaps.size else 0
    n_gt_reach = int(np.sum(gaps > reach)) if gaps.size else 0
    n_dates = int(dates.size)
    n_clusters = int(len(clusters))
    n_episodes = int(len(episodes))
    if n_dates == 0:
        if n_clusters != 0 or n_episodes != 0:
            raise RuntimeError("empty event dates produced a cluster")
    else:
        if n_clusters != 1 + n_gt_h:
            raise RuntimeError(
                f"h={h}: clusters {n_clusters} != 1 + gaps>{h} ({n_gt_h})"
            )
        if n_episodes != 1 + n_gt_reach:
            raise RuntimeError(
                f"h={h}: episodes {n_episodes} != 1 + gaps>{reach} ({n_gt_reach})"
            )
    owner: dict[int, int] = {}
    for ep_i, ep in enumerate(episodes):
        for cluster in ep["clusters"]:
            owner[id(cluster)] = ep_i
    cluster_rows = []
    for i, cluster in enumerate(clusters):
        window = cluster_window(cluster, h)
        cluster_rows.append(
            {
                "index": i,
                "first": int(cluster[0]),
                "last": int(cluster[-1]),
                "n_dates": int(len(cluster)),
                "window": [int(window[0]), int(window[1])],
                "episode": int(owner[id(cluster)]),
            }
        )
    boundaries = []
    for left, right in zip(cluster_rows, cluster_rows[1:]):
        gap = int(right["first"] - left["last"])
        reglued = left["episode"] == right["episode"]
        if reglued != (gap <= reach):
            raise RuntimeError(
                f"h={h}: boundary gap {gap} reglued={reglued} disagrees with reach {reach}"
            )
        boundaries.append(
            {
                "left_last": left["last"],
                "right_first": right["first"],
                "gap": gap,
                "event_free_sessions": gap - 1,
                "reglued": bool(reglued),
            }
        )
    absorbed_gap = n_dates - n_clusters
    absorbed_window = n_clusters - n_episodes
    reduction = n_dates - n_episodes
    return {
        "n_event_dates": n_dates,
        "n_clusters": n_clusters,
        "n_episodes": n_episodes,
        "dates_absorbed_by_gap": int(absorbed_gap),
        "clusters_absorbed_by_window": int(absorbed_window),
        "reduction_dates_to_episodes": int(reduction),
        "gap_share_of_reduction": _ratio(absorbed_gap, reduction),
        "window_share_of_reduction": _ratio(absorbed_window, reduction),
        "n_gaps_gt_h": n_gt_h,
        "n_gaps_gt_reach": n_gt_reach,
        "merge_reach": int(reach),
        "n_boundaries": int(len(boundaries)),
        "n_boundaries_reglued": int(sum(1 for b in boundaries if b["reglued"])),
        "clusters": cluster_rows,
        "boundaries": boundaries,
        "surviving_boundary_gaps": [b["gap"] for b in boundaries if not b["reglued"]],
    }


def _rule_row(family: str, label: str, result: dict, event_months: int, extra: dict) -> dict:
    row = {
        "family": family,
        "label": label,
        "clusters": int(result["clusters"]),
        "episodes": int(result["episodes"]),
        "event_months": int(event_months),
        "floor_met": bool(floor_met(result["episodes"], event_months)),
        "windows": result["windows"],
        "event_spans": result["event_spans"],
    }
    row.update(extra)
    return row


def _horizon_block(h: int, panel: dict, spy: dict) -> dict:
    dates = panel["event_dates"]
    months = int(panel["event_months"])
    month_list = [str(m) for m in panel["event_month_list"]]
    frozen = reproduce_frozen(dates, h)
    collapse = collapse_decomposition(dates, h)
    gap_rows = []
    for g in GAP_MENU:
        result = apply_gap_with_frozen_window(dates, g, h)
        gap_rows.append(
            _rule_row(
                "gap_with_frozen_window",
                f"g={g}",
                result,
                months,
                {
                    "gap": int(g),
                    "pre": int(EPISODE_PRE),
                    "post": int(h),
                    "same_windows_as_frozen": result["windows"] == frozen["windows"],
                },
            )
        )
    no_merge = apply_frozen_gap_no_window_merge(dates, h)
    no_merge_row = _rule_row(
        "frozen_gap_no_window_merge",
        "no window merge",
        no_merge,
        months,
        {"gap": int(h)},
    )
    pre_rows = []
    for pre in PRE_MENU:
        result = apply_window_pre(dates, h, pre)
        pre_rows.append(
            _rule_row(
                "window_pre",
                f"pre={pre}",
                result,
                months,
                {
                    "pre": int(pre),
                    "post": int(h),
                    "gap": int(h),
                    "same_windows_as_frozen": result["windows"] == frozen["windows"],
                },
            )
        )
    quiet_rows = []
    for q in QUIET_MENU:
        result = apply_quiet_reset(dates, q)
        quiet_rows.append(
            _rule_row(
                "quiet_reset",
                f"Q={q}",
                result,
                months,
                {
                    "q": int(q),
                    "same_episodes_as_no_window_merge": (
                        int(result["episodes"]) == int(no_merge["episodes"])
                        and result["event_spans"] == no_merge["event_spans"]
                    ),
                },
            )
        )
    frozen_spans = _frozen_event_spans(dates, h)
    for row in quiet_rows:
        row["same_partition_as_frozen"] = row["event_spans"] == frozen_spans
    per = {str(k): int(v) for k, v in sorted(panel["per_ticker_episodes"].items())}
    n_tickers = len(per)
    origins = int(panel["origins"])
    balanced = n_tickers > 0 and origins % n_tickers == 0
    implied = (origins // n_tickers) if balanced else None
    n_dates = int(frozen["n_event_dates"])
    ticker_events = int(panel["ticker_events"])
    stored_windows = [[int(a), int(b)] for a, b in panel["episode_windows"]]
    return {
        "h": int(h),
        "n_event_dates": n_dates,
        "stored_events": int(panel["events"]),
        "events_match_event_dates": int(panel["events"]) == n_dates,
        "origins_rows": origins,
        "n_tickers": n_tickers,
        "balanced_cross_section": bool(balanced),
        "implied_sessions": None if implied is None else int(implied),
        "event_dates_over_origins": _ratio(n_dates, origins),
        "date_axis_occupancy": (
            None if implied is None else _ratio(n_dates, implied)
        ),
        "event_months": months,
        "event_months_match_list": months == len(month_list),
        "event_month_first": None if not month_list else month_list[0],
        "event_month_last": None if not month_list else month_list[-1],
        "event_month_list": month_list,
        "ticker_events": ticker_events,
        "mean_tickers_per_event_date": _ratio(ticker_events, n_dates),
        "per_ticker_episodes": per,
        "sum_per_ticker_episodes": int(sum(per.values())),
        "spy": {
            "origins": int(spy["origins"]),
            "events": int(spy["events"]),
            "clusters": int(spy["clusters"]),
            "episodes": int(spy["episodes"]),
            "event_months": int(spy["event_months"]),
            "floor_met": bool(floor_met(spy["episodes"], spy["event_months"])),
        },
        "gap_histogram": gap_histogram(dates),
        "longest_quiet_stretch": longest_quiet_stretch(dates),
        "collapse": collapse,
        "frozen_windows": frozen["windows"],
        "stored_windows_match": stored_windows == frozen["windows"],
        "stored_clusters": int(panel["clusters"]),
        "stored_episodes": int(len(panel["episode_windows"])),
        "rules": {
            "gap_with_frozen_window": gap_rows,
            "frozen_gap_no_window_merge": no_merge_row,
            "window_pre": pre_rows,
            "quiet_reset": quiet_rows,
        },
        "checks": {
            "gap_menu_windows_equal_frozen": all(
                row["same_windows_as_frozen"] for row in gap_rows
            ),
            "pre0_equals_no_window_merge": (
                next(row["episodes"] for row in pre_rows if row["pre"] == 0)
                == no_merge_row["episodes"]
                and next(row["event_spans"] for row in pre_rows if row["pre"] == 0)
                == no_merge_row["event_spans"]
            ),
            "quiet_q_eq_h_equals_no_window_merge": next(
                row["same_episodes_as_no_window_merge"]
                for row in quiet_rows
                if row["q"] == h
            ),
            "quiet_q_eq_reach_equals_frozen": next(
                (
                    row["same_partition_as_frozen"]
                    for row in quiet_rows
                    if row["q"] == h + int(EPISODE_PRE)
                ),
                None,
            ),
        },
    }


def _frozen_event_spans(event_dates, h: int) -> list[list[int]]:
    dates = event_date_index(event_dates)
    clusters = event_clusters(dates, int(h))
    episodes = merge_episodes(clusters, int(h))
    spans = []
    for ep in episodes:
        members = ep["clusters"]
        spans.append([int(members[0][0]), int(members[-1][-1])])
    return spans


def extract_panel_binary(payload: dict) -> dict[str, dict]:
    """Copy structural binary episode fields. Skill keys are not copied."""
    episodes = payload["episodes"]
    out: dict[str, dict] = {}
    for h in HORIZONS:
        binary = episodes[f"h{h}"]["binary"]
        out[f"h{h}"] = {
            "event_dates": [int(x) for x in binary["event_dates"]],
            "clusters": int(binary["clusters"]),
            "episode_windows": [[int(a), int(b)] for a, b in binary["episode_windows"]],
            "per_ticker_episodes": {
                str(k): int(v) for k, v in binary["per_ticker_episodes"].items()
            },
            "ticker_events": int(binary["ticker_events"]),
            "origins": int(binary["origins"]),
            "events": int(binary["events"]),
            "event_months": int(binary["event_months"]),
            "event_month_list": [str(m) for m in binary["event_month_list"]],
        }
    return out


def extract_spy_binary_honest_n(payload: dict) -> dict[str, dict]:
    """Copy stage-1 binary honest-N counts. No other stage-1 block is read."""
    episodes = payload["episodes"]
    out: dict[str, dict] = {}
    for h in HORIZONS:
        hn = episodes[f"h{h}"]["binary"]["honest_n"]
        out[f"h{h}"] = {
            "origins": int(hn["origins"]),
            "events": int(hn["events"]),
            "clusters": int(hn["clusters"]),
            "episodes": int(hn["episodes"]),
            "event_months": int(hn["event_months"]),
        }
    return out


def build_report(panel_by_h: dict[str, dict], spy_by_h: dict[str, dict], sources: dict | None = None) -> dict:
    """Full options report. Does not check the committed 31/11, 20/4, 5/1 targets."""
    horizons = []
    reproduction = []
    for h in HORIZONS:
        block = _horizon_block(h, panel_by_h[f"h{h}"], spy_by_h[f"h{h}"])
        committed_c, committed_e = COMMITTED_FROZEN[h]
        reproduction.append(
            {
                "h": int(h),
                "committed_clusters": int(committed_c),
                "committed_episodes": int(committed_e),
                "stored_clusters": int(block["stored_clusters"]),
                "stored_episodes": int(block["stored_episodes"]),
                "reproduced_clusters": int(block["collapse"]["n_clusters"]),
                "reproduced_episodes": int(block["collapse"]["n_episodes"]),
                "windows_match": bool(block["stored_windows_match"]),
                "events_match": bool(block["events_match_event_dates"]),
                "months_match": bool(block["event_months_match_list"]),
            }
        )
        horizons.append(block)
    source_block = {
        "stage1b_path": None,
        "stage1_path": None,
        "stage1b_sha256": None,
        "stage1_sha256": None,
        "stage1b_fields": (
            "episodes[h].binary event_dates, clusters, episode_windows, "
            "per_ticker_episodes, ticker_events, origins, events, event_months, "
            "event_month_list"
        ),
        "stage1_fields": (
            "episodes[h].binary.honest_n origins, events, clusters, episodes, event_months"
        ),
    }
    if sources:
        source_block.update(sources)
    return {
        "schema": SCHEMA,
        "as_of": AS_OF,
        "family": "binary",
        "memo_status": "design_options_not_a_prereg_freeze",
        "episode_pre": int(EPISODE_PRE),
        "power_floor": {
            "min_episodes": int(POWER_MIN_EPISODES),
            "min_months": int(POWER_MIN_MONTHS),
        },
        "disclosure": DISCLOSURE,
        "floor_warning": FLOOR_WARNING,
        "sources": source_block,
        "reproduction": reproduction,
        "horizons": horizons,
        "not_computable": [dict(item) for item in NOT_COMPUTABLE],
        "candidates": [dict(item) for item in CANDIDATES],
        "rules_meeting_floor_on_every_horizon": rules_meeting_every_horizon_labels(
            {"horizons": horizons}
        ),
    }


def reproduction_problems(report: dict) -> list[str]:
    """Differences from the committed cluster and episode counts."""
    problems = []
    for row in report["reproduction"]:
        h = int(row["h"])
        if int(row["reproduced_clusters"]) != int(row["committed_clusters"]) or int(
            row["reproduced_episodes"]
        ) != int(row["committed_episodes"]):
            problems.append(
                "h{h} reproduced {rc}/{re} != committed {cc}/{ce}".format(
                    h=h,
                    rc=row["reproduced_clusters"],
                    re=row["reproduced_episodes"],
                    cc=row["committed_clusters"],
                    ce=row["committed_episodes"],
                )
            )
        if int(row["stored_clusters"]) != int(row["committed_clusters"]) or int(
            row["stored_episodes"]
        ) != int(row["committed_episodes"]):
            problems.append(
                "h{h} stored {sc}/{se} != committed {cc}/{ce}".format(
                    h=h,
                    sc=row["stored_clusters"],
                    se=row["stored_episodes"],
                    cc=row["committed_clusters"],
                    ce=row["committed_episodes"],
                )
            )
        if not row["windows_match"]:
            problems.append(f"h{h} reproduced episode windows != stored episode_windows")
        if not row["events_match"]:
            problems.append(f"h{h} stored events != len(event_dates)")
        if not row["months_match"]:
            problems.append(f"h{h} stored event_months != len(event_month_list)")
    return problems


def iter_rule_rows(horizon: dict):
    rules = horizon["rules"]
    yield from rules["gap_with_frozen_window"]
    yield rules["frozen_gap_no_window_merge"]
    yield from rules["window_pre"]
    yield from rules["quiet_reset"]


def rules_meeting_every_horizon_labels(report: dict) -> list[str]:
    """Labels whose floor is met at every horizon, in menu order."""
    sets = []
    order: list[str] = []
    for horizon in report["horizons"]:
        met = []
        for row in iter_rule_rows(horizon):
            if row["label"] not in order:
                order.append(row["label"])
            if row["floor_met"]:
                met.append(row["label"])
        sets.append(set(met))
    if not sets:
        return []
    common = set.intersection(*sets)
    return [label for label in order if label in common]


def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def _floor_word(met: bool) -> str:
    return "met" if met else "not met"


def reproduction_table(report: dict) -> str:
    rows = []
    for row in report["reproduction"]:
        rows.append(
            [
                f"h{row['h']}",
                str(row["committed_clusters"]),
                str(row["reproduced_clusters"]),
                str(row["committed_episodes"]),
                str(row["reproduced_episodes"]),
                "yes" if row["windows_match"] else "no",
            ]
        )
    return _md_table(
        ["h", "committed clusters", "reproduced clusters", "committed episodes", "reproduced episodes", "windows match"],
        rows,
    )


def density_table(report: dict) -> str:
    rows = []
    for hor in report["horizons"]:
        occ = hor["date_axis_occupancy"]
        rows.append(
            [
                f"h{hor['h']}",
                str(hor["n_event_dates"]),
                str(hor["origins_rows"]),
                hor["event_dates_over_origins"]["text"],
                "" if hor["implied_sessions"] is None else str(hor["implied_sessions"]),
                "" if occ is None else occ["text"],
                str(hor["event_months"]),
                str(hor["ticker_events"]),
                hor["mean_tickers_per_event_date"]["text"] or "",
            ]
        )
    return _md_table(
        [
            "h",
            "event dates",
            "origins (rows)",
            "event dates / origins",
            "implied sessions",
            "date-axis occupancy",
            "event months",
            "ticker-events",
            "mean names per event date",
        ],
        rows,
    )


def histogram_table(report: dict) -> str:
    labels = [b["label"] for b in report["horizons"][0]["gap_histogram"]["bins"]]
    rows = []
    for label in labels:
        row = [label]
        for hor in report["horizons"]:
            n = next(b["n"] for b in hor["gap_histogram"]["bins"] if b["label"] == label)
            row.append(str(n))
        rows.append(row)
    for name, key in (
        ("n gaps", "n_gaps"),
        ("min", "min"),
        ("median", "median"),
        ("max", "max"),
    ):
        row = [name]
        for hor in report["horizons"]:
            value = hor["gap_histogram"][key]
            row.append("" if value is None else str(value))
        rows.append(row)
    quiet = ["longest event-free"]
    for hor in report["horizons"]:
        value = hor["longest_quiet_stretch"]["max_event_free_sessions"]
        quiet.append("" if value is None else str(value))
    rows.append(quiet)
    headers = ["gap"] + [f"h{hor['h']}" for hor in report["horizons"]]
    return _md_table(headers, rows)


def collapse_table(report: dict) -> str:
    rows = []
    for hor in report["horizons"]:
        col = hor["collapse"]
        rows.append(
            [
                f"h{hor['h']}",
                str(col["n_event_dates"]),
                str(col["n_clusters"]),
                str(col["n_episodes"]),
                str(col["dates_absorbed_by_gap"]),
                str(col["clusters_absorbed_by_window"]),
                f"{col['gap_share_of_reduction']['numerator']}/{col['gap_share_of_reduction']['denominator']}",
                f"{col['window_share_of_reduction']['numerator']}/{col['window_share_of_reduction']['denominator']}",
                str(col["merge_reach"]),
                str(col["n_boundaries_reglued"]),
                str(col["n_boundaries"]),
                str(col["n_gaps_gt_h"]),
                str(col["n_gaps_gt_reach"]),
            ]
        )
    return _md_table(
        [
            "h",
            "event dates",
            "clusters",
            "episodes",
            "dates absorbed by gap",
            "clusters absorbed by window",
            "gap share of reduction",
            "window share of reduction",
            "merge reach",
            "boundaries re-glued",
            "boundaries",
            "gaps > h",
            "gaps > reach",
        ],
        rows,
    )


def gap_table(horizon: dict) -> str:
    rows = []
    for row in horizon["rules"]["gap_with_frozen_window"]:
        rows.append(
            [
                str(row["gap"]),
                str(row["clusters"]),
                str(row["episodes"]),
                str(row["event_months"]),
                _floor_word(row["floor_met"]),
            ]
        )
    return _md_table(["g", "clusters", "episodes", "event months", "floor"], rows)


def nomerge_line(horizon: dict) -> str:
    row = horizon["rules"]["frozen_gap_no_window_merge"]
    return (
        f"h{horizon['h']}: clusters = episodes = {row['episodes']}, "
        f"event months {row['event_months']}, floor {_floor_word(row['floor_met'])}."
    )


def pre_table(horizon: dict) -> str:
    rows = []
    for row in horizon["rules"]["window_pre"]:
        rows.append(
            [
                str(row["pre"]),
                str(row["clusters"]),
                str(row["episodes"]),
                str(row["event_months"]),
                _floor_word(row["floor_met"]),
            ]
        )
    return _md_table(["pre", "clusters", "episodes", "event months", "floor"], rows)


def quiet_table(horizon: dict) -> str:
    rows = []
    for row in horizon["rules"]["quiet_reset"]:
        rows.append(
            [
                str(row["q"]),
                str(row["episodes"]),
                str(row["event_months"]),
                _floor_word(row["floor_met"]),
            ]
        )
    return _md_table(["Q", "episodes", "event months", "floor"], rows)


def comparison_table(report: dict) -> str:
    rows = []
    for hor in report["horizons"]:
        rows.append(
            [
                f"h{hor['h']}",
                str(hor["collapse"]["n_episodes"]),
                str(hor["sum_per_ticker_episodes"]),
                str(hor["spy"]["episodes"]),
                str(hor["spy"]["clusters"]),
                str(hor["spy"]["events"]),
                str(hor["spy"]["event_months"]),
                str(hor["spy"]["origins"]),
                _floor_word(hor["spy"]["floor_met"]),
            ]
        )
    return _md_table(
        [
            "h",
            "panel episodes",
            "sum of per-ticker episodes",
            "SPY episodes",
            "SPY clusters",
            "SPY events",
            "SPY event months",
            "SPY origins",
            "SPY floor",
        ],
        rows,
    )


def per_ticker_table(report: dict) -> str:
    keys = []
    for name in PANEL_ORDER:
        if any(name in hor["per_ticker_episodes"] for hor in report["horizons"]):
            keys.append(name)
    extra = sorted(
        {
            name
            for hor in report["horizons"]
            for name in hor["per_ticker_episodes"]
            if name not in keys
        }
    )
    keys.extend(extra)
    rows = []
    for name in keys:
        row = [name]
        for hor in report["horizons"]:
            value = hor["per_ticker_episodes"].get(name)
            row.append("" if value is None else str(value))
        rows.append(row)
    total = ["sum"]
    for hor in report["horizons"]:
        total.append(str(hor["sum_per_ticker_episodes"]))
    rows.append(total)
    headers = ["ticker"] + [f"h{hor['h']}" for hor in report["horizons"]]
    return _md_table(headers, rows)


def _window_text(windows: list[list[int]]) -> str:
    if not windows:
        return "(none)"
    return "; ".join(f"{a}..{b}" for a, b in windows)


def _consequence(report: dict, family: str, q: int | None = None) -> str:
    bits = []
    for hor in report["horizons"]:
        if family == "frozen_gap_no_window_merge":
            row = hor["rules"]["frozen_gap_no_window_merge"]
        elif family == "quiet_reset":
            row = next(item for item in hor["rules"]["quiet_reset"] if item["q"] == q)
        else:
            raise KeyError(family)
        bits.append(
            f"h{hor['h']} {row['episodes']} episodes, floor {_floor_word(row['floor_met'])}"
        )
    return "; ".join(bits) + "."


def _collapse_prose(hor: dict) -> str:
    col = hor["collapse"]
    quiet = hor["longest_quiet_stretch"]
    h = hor["h"]
    reach = col["merge_reach"]
    sentences = [
        (
            f"h{h}. A frozen episode boundary exists only where two consecutive "
            f"event dates have session-index gap greater than {reach} "
            f"(h + {EPISODE_PRE}). A frozen cluster boundary exists where the "
            f"gap is greater than {h}. On this union that is "
            f"{col['n_gaps_gt_h']} cluster boundaries and "
            f"{col['n_gaps_gt_reach']} episode boundaries, so "
            f"{col['n_clusters']} clusters and {_episodes_phrase(col['n_episodes'])}."
        )
    ]
    if quiet["max_gap"] is None:
        sentences.append("There is no interior gap.")
    elif int(quiet["max_gap"]) <= int(reach):
        sentences.append(
            f"The longest gap is {quiet['max_gap']} "
            f"({quiet['max_event_free_sessions']} event-free sessions, "
            f"between session indices {quiet['left_event_index']} and "
            f"{quiet['right_event_index']}). That is at most the reach, so "
            f"every shorter gap is too, and the horizon is one episode."
        )
    else:
        surviving = col["surviving_boundary_gaps"]
        shown = ", ".join(str(g) for g in surviving) if surviving else "(none)"
        sentences.append(
            f"The longest gap is {quiet['max_gap']} "
            f"({quiet['max_event_free_sessions']} event-free sessions, "
            f"between session indices {quiet['left_event_index']} and "
            f"{quiet['right_event_index']}), which is above the reach. "
            f"Gaps that stay as episode boundaries: {shown}."
        )
    if col["n_boundaries"] <= 6 and col["boundaries"]:
        gaps = ", ".join(str(b["gap"]) for b in col["boundaries"])
        sizes = ", ".join(str(c["n_dates"]) for c in col["clusters"])
        sentences.append(
            f"Cluster sizes in event dates: {sizes}. "
            f"Cluster-boundary gaps: {gaps}."
        )
    gap_share = col["gap_share_of_reduction"]
    win_share = col["window_share_of_reduction"]
    sentences.append(
        f"Of the reduction from {col['n_event_dates']} event dates to "
        f"{_episodes_phrase(col['n_episodes'])}, the gap rule absorbs "
        f"{col['dates_absorbed_by_gap']} "
        f"({gap_share['numerator']}/{gap_share['denominator']}"
        + (f", {gap_share['text']}" if gap_share["text"] else "")
        + f") and the window merge absorbs {col['clusters_absorbed_by_window']} "
        f"({win_share['numerator']}/{win_share['denominator']}"
        + (f", {win_share['text']}" if win_share["text"] else "")
        + "). "
        f"The window re-glues {col['n_boundaries_reglued']} of "
        f"{col['n_boundaries']} cluster boundaries."
    )
    return " ".join(sentences)


def _episodes_phrase(n: int) -> str:
    n = int(n)
    return "1 episode" if n == 1 else f"{n} episodes"


def _gap_check_prose(hor: dict) -> str:
    h = hor["h"]
    checks = hor["checks"]
    reach = hor["collapse"]["merge_reach"]
    if checks["gap_menu_windows_equal_frozen"] and max(GAP_MENU) <= reach:
        return (
            f"Every gap g in the menu is at most {max(GAP_MENU)}, and the "
            f"window reach is {reach}. Tightening g only splits clusters that "
            f"the window merge joins again, so every g has the same episodes "
            f"and the same windows as the frozen h{h} rule. Cluster counts "
            f"still change. Varying the gap without shrinking the window "
            f"cannot raise episode N at this horizon."
        )
    if checks["gap_menu_windows_equal_frozen"]:
        return (
            f"On this sample every menu gap produced the same episode windows "
            f"as the frozen h{h} rule."
        )
    return f"Menu gaps do not all reproduce the frozen h{h} episode windows."


def _pre_check_prose(hor: dict) -> str:
    if not hor["checks"]["pre0_equals_no_window_merge"]:
        return ""
    return (
        "pre = 0 does not merge any frozen-gap cluster, because a cluster "
        "boundary already has gap greater than h and the pre = 0 reach is h. "
        "Those episodes are the no-window-merge episodes."
    )


def _quiet_check_prose(hor: dict) -> str:
    h = hor["h"]
    checks = hor["checks"]
    reach = hor["collapse"]["merge_reach"]
    lines = []
    if checks["quiet_q_eq_h_equals_no_window_merge"]:
        lines.append(f"Quiet-reset Q = {h} is the frozen gap with no window merge.")
    if checks["quiet_q_eq_reach_equals_frozen"]:
        lines.append(
            f"Quiet-reset Q = {reach} is the frozen episode partition, because "
            f"both break only when the gap is greater than {reach}."
        )
    return " ".join(lines)


def _panel_vs_spy_sentence(hor: dict) -> str:
    panel_n = int(hor["collapse"]["n_episodes"])
    spy_n = int(hor["spy"]["episodes"])
    if panel_n < spy_n:
        relation = "below"
    elif panel_n > spy_n:
        relation = "above"
    else:
        relation = "equal to"
    return (
        f"At h{hor['h']} the panel has {_episodes_phrase(panel_n)}, "
        f"{relation} SPY's {_episodes_phrase(spy_n)}."
    )


def _union_versus_sum_sentence(report: dict) -> str:
    hor = next(item for item in report["horizons"] if int(item["h"]) == 21)
    return (
        f"At h21 the union-and-window rule has {_episodes_phrase(hor['collapse']['n_episodes'])}, "
        f"SPY has {_episodes_phrase(hor['spy']['episodes'])}, and the sum of per-ticker "
        f"episodes is {hor['sum_per_ticker_episodes']}."
    )


def render_markdown(report: dict) -> str:
    """Design-options memo. Every count is taken from ``report``."""
    sources = report["sources"]
    parts: list[str] = [
        f"# Pullback episode-rule options, v1.2 ({report['as_of']})",
        "",
        "This memo is a design-options note for the seat. It is not a preregistration freeze. It does not choose a rule. Counts below are properties of the binary event-date axis. They are not measures of model skill.",
        "",
        (
            f"Stage-1b file `{sources['stage1b_path']}` sha256 `{sources['stage1b_sha256']}`. "
            f"Fields: {sources['stage1b_fields']}. "
            f"Stage-1 file `{sources['stage1_path']}` sha256 `{sources['stage1_sha256']}`. "
            f"Fields: {sources['stage1_fields']}."
        ),
        "",
        (
            "Gap clustering and window overlap call `event_clusters`, `cluster_window` and "
            "`merge_episodes` in the frozen stage-1 script. A pre-window other than "
            f"{report['episode_pre']} is that same overlap test after a shift of the session "
            "indices, so the frozen pre lines up with the requested pre and the post length "
            "is shifted the other way. At pre = "
            f"{report['episode_pre']} the call is unshifted. Event-months are the committed "
            "count of distinct calendar months of the union event dates. None of the "
            "computable rules drop a date, so that count is copied onto every row. It is "
            "not rebuilt from a session calendar."
        ),
        "",
        "## Frozen v1.1 rule",
        "",
        "The panel rule that produced the stage-1b episodes is three steps.",
        "",
        "1. A panel event date is any session index on which at least one of the panel names has Y=1. Several names on the same session are one event date.",
        f"2. Event dates form a cluster when the gap in session index is at most h. A gap greater than h starts a new cluster.",
        f"3. Each cluster has a window from {report['episode_pre']} sessions before its first event date through h sessions after its last. Clusters whose windows overlap become one episode.",
        "",
        (
            f"The power floor is {report['power_floor']['min_episodes']} episodes and "
            f"{report['power_floor']['min_months']} distinct event months. Below either "
            "number a claim is underpowered, whatever else is true of it. The floor was "
            "set before these panel counts existed. It is not a target for the episode rule."
        ),
        "",
        "## Reproduction",
        "",
        "Rebuilding clusters and episodes from the stored union event dates, with the frozen functions, matches the stored counts and the stored windows.",
        "",
        reproduction_table(report),
        "",
    ]
    for hor in report["horizons"]:
        parts.append(
            f"h{hor['h']} windows: {_window_text(hor['frozen_windows'])}."
        )
    parts.extend(
        [
            "",
            "## Why the panel collapses",
            "",
            (
                "`origins` in the stage-1b binary block is a count of ticker-date rows in "
                "the comparison set, not a count of sessions. It divides evenly by the "
                "number of per-ticker keys, which is consistent with a complete "
                "cross-section and an implied session count of origins divided by that "
                "width. A balanced pattern of missing rows could also divide evenly, so "
                "the implied session count is an inference from that divisibility, not a "
                "stored session list. Date-axis occupancy is event dates divided by the "
                "implied session count. Event dates divided by origins is the row ratio. "
                "On a balanced cross-section the row ratio equals the occupancy divided "
                "by the number of names."
            ),
            "",
            density_table(report),
            "",
            (
                "The histogram counts session-index gaps between consecutive union event "
                "dates. A gap of 1 means the next event date is the next session. "
                "Event-free sessions between two event dates equal the gap minus 1. "
                "The longest quiet stretch is the maximum of those interior runs. It does "
                "not include sessions before the first event date or after the last."
            ),
            "",
            histogram_table(report),
            "",
            (
                "Event-month span of the union: "
                + "; ".join(
                    f"h{hor['h']} {hor['event_month_first']} to {hor['event_month_last']}"
                    for hor in report["horizons"]
                )
                + "."
            ),
            "",
            collapse_table(report),
            "",
        ]
    )
    for hor in report["horizons"]:
        parts.append(_collapse_prose(hor))
        parts.append("")
    parts.extend(
        [
            (
                "The gap rule does most of the reduction in headcount when the typical "
                "gap is one session: neighbouring event dates fall into one cluster. "
                "The window merge is the step that removes the remaining boundaries. "
                + " ".join(_panel_vs_spy_sentence(hor) for hor in report["horizons"])
                + " The shortfall versus SPY, where there is one, is the union plus "
                "the window, not a shortage of ticker-level events."
            ),
            "",
            "## Computable alternatives",
            "",
            FLOOR_WARNING,
            "",
            (
                "The floor column is a consequence of each rule on this already-consumed "
                "union. Searching the column for `met` and freezing that row uses the "
                "same sample that would later be called evidence. That is p-hacking the "
                "power floor. Event-months do not move across these rows, because every "
                "computable rule keeps the same event dates. "
                + (
                    "On this panel the month half of the floor is already met at every horizon. "
                    if all(
                        hor["event_months"] >= report["power_floor"]["min_months"]
                        for hor in report["horizons"]
                    )
                    else "On this panel the month half of the floor is not met at every horizon. "
                )
                + "Only the episode count can change the floor bit among these rows, "
                "and only a rule that drops dates could change the month count."
            ),
            "",
            (
                "Rules that meet the floor at every horizon in the tables: "
                + (
                    ", ".join(report["rules_meeting_floor_on_every_horizon"])
                    if report["rules_meeting_floor_on_every_horizon"]
                    else "(none)"
                )
                + ". Selecting one of those labels because it is on this list is the "
                "p-hack named above. They are shown so the trap is visible."
            ),
            "",
        ]
    )
    for hor in report["horizons"]:
        parts.append(f"### h{hor['h']}")
        parts.append("")
        parts.append("Gap g with the frozen window merge (pre = "
                     f"{report['episode_pre']}, post = h).")
        parts.append("")
        parts.append(gap_table(hor))
        parts.append("")
        parts.append(_gap_check_prose(hor))
        parts.append("")
        parts.append("Frozen gap with no window merge.")
        parts.append("")
        parts.append(nomerge_line(hor))
        parts.append("")
        parts.append("Frozen gap, window pre varied, post = h.")
        parts.append("")
        parts.append(pre_table(hor))
        pre_note = _pre_check_prose(hor)
        if pre_note:
            parts.append("")
            parts.append(pre_note)
        parts.append("")
        parts.append(
            "Quiet-reset: a new episode starts only after Q consecutive "
            "event-free sessions (session-index gap greater than Q). No window merge."
        )
        parts.append("")
        parts.append(quiet_table(hor))
        quiet_note = _quiet_check_prose(hor)
        if quiet_note:
            parts.append("")
            parts.append(quiet_note)
        parts.append("")
    parts.extend(
        [
            "## Not computable from the committed artifacts",
            "",
            (
                "The three designs below need data the artifacts do not store. "
                "No episode count, month count or floor bit is available for them, "
                "and none is guessed here."
            ),
            "",
        ]
    )
    for item in report["not_computable"]:
        parts.append(f"### {item['name']}")
        parts.append("")
        parts.append(item["rule"])
        parts.append("")
        parts.append(f"Data required: {item['needs']}")
        parts.append("")
    parts.extend(
        [
            "## Per-ticker sums and SPY",
            "",
            (
                "Stage-1 binary honest-N is the single-series SPY run. SPY is not a key "
                "in the panel's per-ticker episode counts. The panel and SPY use the "
                "same frozen cluster and window rule. They do not use the same event dates."
            ),
            "",
            comparison_table(report),
            "",
            "Per-ticker episode counts stored beside the panel floor. The sum is not an input to the floor.",
            "",
            per_ticker_table(report),
            "",
            (
                "Per-ticker episodes are not independent and the sum is not an honest N. "
                "Each name runs the episode rule on its own event dates. The artifact "
                "keeps the count and drops the dates. Adding the counts treats each "
                "name's episode as a separate piece of evidence. One selloff that prints "
                "Y=1 on several names increments several counters for one shock. The "
                "mean number of names with Y=1 on a union event date, ticker-events "
                "divided by union event dates, is the co-occurrence in the density "
                "table. That average is not a per-date breadth histogram: the same mean "
                "can be many single-name dates plus a few broad dates, or a steady "
                "breadth. The sum is an upper count of name-level spells. It is not a "
                "count of independent spells."
            ),
            "",
            (
                "The union rule makes the opposite mistake. Any one name marks the "
                "session for the whole panel, and the window then chains those marks. "
                + _union_versus_sum_sentence(report)
                + " None of these counts is the number of common shocks. That number needs "
                "the per-name dates."
            ),
            "",
            "## Candidates for a v1.2 preregistration",
            "",
            (
                "Two computable candidates and one candidate that has to wait for new "
                "fields. The justifications use the structure of the frozen rule and, "
                "where they use the union's occupancy, they are covered by the disclosure "
                "in the next section. None of them is chosen because its floor column "
                "says met. Consequence counts are reported so a failure of the floor is "
                "visible. They are not the selection criterion."
            ),
            "",
        ]
    )
    for cand in report["candidates"]:
        parts.append(f"### {cand['id']}. {cand['title']}")
        parts.append("")
        parts.append(cand["justification"])
        parts.append("")
        if cand["computable"] and cand["family"] == "frozen_gap_no_window_merge":
            parts.append(
                "Consequence on this sample, not a reason to prefer the row: "
                + _consequence(report, "frozen_gap_no_window_merge")
            )
        elif cand["computable"] and cand["family"] == "quiet_reset":
            parts.append(
                "Consequence on this sample, not a reason to prefer the row: "
                + _consequence(report, "quiet_reset", q=int(cand["q"]))
            )
        else:
            parts.append(
                "No episode count is computed. Computing one would require the "
                "per-date breadth, which is not in the artifact."
            )
        parts.append("")
    parts.extend(
        [
            "## Disclosure a v1.2 preregistration must carry",
            "",
            DISCLOSURE,
            "",
            (
                "This memo does not freeze a rule. A later preregistration that freezes "
                "one of the candidates, or any other rule motivated by these tables, "
                "carries that sentence."
            ),
            "",
        ]
    )
    return "\n".join(parts)


def format_stdout(report: dict) -> str:
    lines = []
    for row in report["reproduction"]:
        lines.append(
            "REPRODUCTION h{h} clusters {rc}/{cc} episodes {re}/{ce} windows_match {wm}".format(
                h=row["h"],
                rc=row["reproduced_clusters"],
                cc=row["committed_clusters"],
                re=row["reproduced_episodes"],
                ce=row["committed_episodes"],
                wm=row["windows_match"],
            )
        )
    lines.append(
        "FLOOR_ON_EVERY_HORIZON "
        + (
            ", ".join(report["rules_meeting_floor_on_every_horizon"])
            if report["rules_meeting_floor_on_every_horizon"]
            else "(none)"
        )
    )
    for hor in report["horizons"]:
        bits = [f"h{hor['h']}"]
        for row in iter_rule_rows(hor):
            bits.append(f"{row['label']}={row['episodes']}")
        lines.append(" ".join(bits))
    return "\n".join(lines) + "\n"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grey Deer v1.2 episode-rule options")
    parser.add_argument("--stage1b", type=Path, default=DEFAULT_STAGE1B)
    parser.add_argument("--stage1", type=Path, default=DEFAULT_STAGE1)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    stage1b_payload = json.loads(args.stage1b.read_text())
    panel = extract_panel_binary(stage1b_payload)
    del stage1b_payload
    stage1_payload = json.loads(args.stage1.read_text())
    spy = extract_spy_binary_honest_n(stage1_payload)
    del stage1_payload
    report = build_report(
        panel,
        spy,
        sources={
            "stage1b_path": _display_path(args.stage1b),
            "stage1_path": _display_path(args.stage1),
            "stage1b_sha256": _sha256_file(args.stage1b),
            "stage1_sha256": _sha256_file(args.stage1),
        },
    )
    problems = reproduction_problems(report)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 2
    text = render_json(report)
    markdown = render_markdown(report)
    if DISCLOSURE not in markdown or FLOOR_WARNING not in markdown:
        print("markdown missing required disclosure or floor warning", file=sys.stderr)
        return 2
    for hor in report["horizons"]:
        if gap_table(hor) not in markdown or quiet_table(hor) not in markdown:
            print(f"markdown missing h{hor['h']} tables", file=sys.stderr)
            return 2
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(text)
    args.md_out.write_text(markdown)
    sys.stdout.write(format_stdout(report))
    print(f"wrote {args.json_out}")
    print(f"wrote {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
