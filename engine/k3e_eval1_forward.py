"""I/O-free scoring core of the K3E-EVAL-1-V1 forward evaluator.

This module reads no files and no outcomes; callers pass in-memory rows on
integer NYSE-session ordinals. It defines no challenger trial identity. The
reader, admission-gated runner, and decision-law aggregator are a later change.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np

from engine.seasonality.multiplicity import benjamini_yekutieli

REGISTRATION_ID = "K3E-EVAL-1-V1"
REGISTRATION_DIGEST = "1ca158a213fca3f90c5c4fdc1359d40bf9146f2400cb10d8caa202b18f293bd4"
CLASSES = ("UP", "DOWN", "FLAT")
PRIMARY_HORIZON_SESSIONS = 21
OUTER_WINDOW_SESSIONS = 63
PURGE_SESSIONS = 63
DATE_BLOCK_SESSIONS = 63
EPISODE_FLOOR = 100
EFFECT_SIZE_THRESHOLD = 0.05
BY_Q = 0.10
SCORED_FRACTION_FLOOR = 0.60
CASE_COVERAGE_FLOOR = 0.60
REGISTERED_MOTIVATING_CASES = 4
MAX_CHALLENGER_ABSTENTION = 0.40
BOOTSTRAP_REPLICATES = 19_999
BOOTSTRAP_SEED = 480_336_034
ELIGIBLE_BASELINES = ("B0_NO_CHANGE", "B6_HISTORICAL_BASE_RATE")
PARTITIONS = (
    "F_DEV",
    "PURGE_1",
    "F_VAL",
    "PURGE_2",
    "F_HOLD",
    "PROSPECTIVE_SHADOW",
)
PRE_BOUNDARY = "PRE_BOUNDARY"

_COUNTING = ("F_DEV", "F_VAL", "F_HOLD")


def frozen_term_mismatches(registration: Mapping[str, Any]) -> list[str]:
    """Return sorted check names that fail against a parsed registration mapping."""
    failed: list[str] = []

    def _check(name: str, ok: bool) -> None:
        if not ok:
            failed.append(name)

    try:
        _check(
            "registration_id",
            registration["registration_id"] == REGISTRATION_ID,
        )
    except (KeyError, TypeError):
        failed.append("registration_id")

    try:
        sf = registration["scientific_freeze"]
    except (KeyError, TypeError):
        for key in (
            "primary_horizon_sessions",
            "effect_size_threshold",
            "outer_window",
            "purge",
            "episode_floor",
            "date_block",
            "replicates_and_seed_in_code",
            "scored_fraction_floor",
            "case_coverage_floor",
            "max_challenger_abstention",
        ):
            failed.append(key)
        sf = None

    if sf is not None:
        try:
            _check(
                "primary_horizon_sessions",
                sf["primary_horizon_sessions"] == PRIMARY_HORIZON_SESSIONS,
            )
        except (KeyError, TypeError):
            failed.append("primary_horizon_sessions")
        try:
            _check(
                "effect_size_threshold",
                sf["effect_size_threshold"] == EFFECT_SIZE_THRESHOLD,
            )
        except (KeyError, TypeError):
            failed.append("effect_size_threshold")
        try:
            cr = sf["censoring_rule"]
            _check("outer_window", "cutoff+63 sessions" in cr)
        except (KeyError, TypeError):
            failed.append("outer_window")
        try:
            fp = sf["forward_partitions"]
            _check("purge", "next 63 NYSE sessions" in fp)
            _check(
                "episode_floor",
                "at least 100 distinct issuer episodes" in fp,
            )
        except (KeyError, TypeError):
            failed.append("purge")
            failed.append("episode_floor")
        try:
            dr = sf["dependence_rule"]
            _check("date_block", "blocks of 63 NYSE sessions" in dr)
            _check(
                "replicates_and_seed_in_code",
                "Bootstrap replicate count and seed are fixed in evaluator code"
                in dr,
            )
        except (KeyError, TypeError):
            failed.append("date_block")
            failed.append("replicates_and_seed_in_code")
        try:
            cov = sf["coverage_rule"]
            _check(
                "scored_fraction_floor",
                "at least 0.60 of eligible rows are scored" in cov,
            )
            _check(
                "case_coverage_floor",
                "At least 0.60 of the four registered motivating cases" in cov,
            )
            _check(
                "max_challenger_abstention",
                "abstains on more than 0.40 of eligible rows" in cov,
            )
        except (KeyError, TypeError):
            failed.append("scored_fraction_floor")
            failed.append("case_coverage_floor")
            failed.append("max_challenger_abstention")

    try:
        mt = registration["multiple_testing"]
        _check("by_q", mt["q"] == BY_Q)
        _check("by_procedure", mt["procedure"] == "benjamini_yekutieli")
    except (KeyError, TypeError):
        failed.append("by_q")
        failed.append("by_procedure")

    try:
        _check("trial_count", registration["challenger"]["trial_count"] == 1)
    except (KeyError, TypeError):
        failed.append("trial_count")

    return sorted(set(failed))


def t1_label(
    cutoff_session: int,
    cutoff_value: float,
    observations: Iterable[tuple[int, float | None, bool]],
    as_of_session: int,
) -> tuple[str, str | None]:
    """Implement scientific_freeze.censoring_rule for one row on NYSE-session ordinals."""
    if not isinstance(cutoff_value, (int, float)) or not math.isfinite(float(cutoff_value)):
        raise ValueError("cutoff_value must be a finite number")
    cutoff_value = float(cutoff_value)

    visible_successful: list[tuple[int, float]] = []
    for session, value, ok in observations:
        if session > as_of_session:
            continue
        if session <= cutoff_session:
            continue
        if not ok or value is None:
            continue
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            continue
        visible_successful.append((session, float(value)))
    visible_successful.sort(key=lambda item: item[0])

    h = cutoff_session + PRIMARY_HORIZON_SESSIONS
    out = cutoff_session + OUTER_WINDOW_SESSIONS

    for session, value in visible_successful:
        if cutoff_session < session <= h:
            if value != cutoff_value:
                return ("UP", None) if value > cutoff_value else ("DOWN", None)
            continue

    if as_of_session < h:
        return ("PENDING", "horizon_not_reached")

    for session, value in visible_successful:
        if h <= session <= out:
            if value == cutoff_value:
                return ("FLAT", None)
            return ("CENSORED", "change_after_horizon_before_unchanged_snapshot")

    if as_of_session < out:
        return ("PENDING", "flat_window_open")

    return ("CENSORED", "no_successful_snapshot_in_flat_window")


def _validate_probs_row(row: Sequence[float]) -> None:
    if len(row) != 3:
        raise ValueError("probability row must have length 3")
    total = 0.0
    for p in row:
        if not isinstance(p, (int, float)) or not math.isfinite(float(p)) or float(p) < 0:
            raise ValueError("probability entries must be finite and non-negative")
        total += float(p)
    if abs(total - 1.0) > 1e-9:
        raise ValueError("probability row must sum to 1")


def _class_index(label: str) -> int:
    if label not in CLASSES:
        raise ValueError(f"label must be one of {CLASSES}")
    return CLASSES.index(label)


def row_log_losses(
    probs: Sequence[Sequence[float]],
    labels: Sequence[str],
) -> list[float]:
    """Per-row multiclass log loss (scientific_freeze.primary_loss)."""
    if len(probs) != len(labels) or len(probs) == 0:
        raise ValueError("probs and labels must have equal nonzero length")
    losses: list[float] = []
    for row, label in zip(probs, labels):
        _validate_probs_row(row)
        idx = _class_index(label)
        p = float(row[idx])
        losses.append(-math.log(p) if p > 0.0 else math.inf)
    return losses


def mean_log_loss(
    probs: Sequence[Sequence[float]],
    labels: Sequence[str],
) -> float:
    """Mean multiclass log loss (scientific_freeze.primary_loss)."""
    losses = row_log_losses(probs, labels)
    return math.fsum(losses) / len(losses)


def brier_score(
    probs: Sequence[Sequence[float]],
    labels: Sequence[str],
) -> float:
    """Secondary Brier score (scientific_freeze.primary_loss)."""
    if len(probs) != len(labels) or len(probs) == 0:
        raise ValueError("probs and labels must have equal nonzero length")
    total = 0.0
    n = len(probs)
    for row, label in zip(probs, labels):
        _validate_probs_row(row)
        idx = _class_index(label)
        for k in range(3):
            y = 1.0 if k == idx else 0.0
            total += (float(row[k]) - y) ** 2
    return total / n


def relative_improvement(
    baseline_loss: float | None,
    challenger_loss: float | None,
) -> float | None:
    """Relative primary loss improvement (scientific_freeze.primary_loss)."""
    if baseline_loss is None or not math.isfinite(baseline_loss) or baseline_loss <= 0:
        return None
    if challenger_loss is None:
        return None
    if challenger_loss == math.inf:
        return -math.inf
    return (baseline_loss - challenger_loss) / baseline_loss


def fit_b0_no_change(dev_labels: Sequence[str]) -> tuple[float, float, float] | None:
    """B0 no-change baseline (scientific_freeze.strongest_baseline_rule)."""
    n = len(dev_labels)
    if n == 0:
        return None
    flat = 0
    for label in dev_labels:
        if label not in CLASSES:
            raise ValueError(f"unknown label {label}")
        if label == "FLAT":
            flat += 1
    f = flat / n
    if f == 0.0 or f == 1.0:
        return None
    half = (1.0 - f) / 2.0
    return (half, half, f)


def fit_b6_base_rate(
    dev_rows: Sequence[tuple[str, str]],
) -> dict[str, tuple[float, float, float]] | None:
    """B6 historical base rate by metric (scientific_freeze.strongest_baseline_rule)."""
    if not dev_rows:
        return None
    counts: dict[str, list[int]] = {}
    for metric, label in dev_rows:
        if label not in CLASSES:
            raise ValueError(f"unknown label {label}")
        if metric not in counts:
            counts[metric] = [0, 0, 0]
        counts[metric][_class_index(label)] += 1
    model: dict[str, tuple[float, float, float]] = {}
    for metric, cts in counts.items():
        total = sum(cts)
        if total == 0 or any(c == 0 for c in cts):
            return None
        model[metric] = tuple(ct / total for ct in cts)
    return model


def score_b0(
    model: tuple[float, float, float] | None,
    labels: Sequence[str],
) -> float | None:
    """Score B0 on a label sequence (scientific_freeze.strongest_baseline_rule)."""
    if model is None:
        return None
    row = model
    return mean_log_loss([row] * len(labels), labels)


def score_b6(
    model: dict[str, tuple[float, float, float]] | None,
    rows: Sequence[tuple[str, str]],
) -> float | None:
    """Score B6 on metric-labelled rows (scientific_freeze.strongest_baseline_rule)."""
    if model is None:
        return None
    probs: list[tuple[float, float, float]] = []
    labels: list[str] = []
    for metric, label in rows:
        if metric not in model:
            return None
        probs.append(model[metric])
        labels.append(label)
    if not labels:
        return None
    return mean_log_loss(probs, labels)


def strongest_baseline(
    losses: Mapping[str, float | None],
) -> tuple[str | None, float | None]:
    """Pick strongest eligible baseline by loss (scientific_freeze.strongest_baseline_rule)."""
    for key in losses:
        if key not in ELIGIBLE_BASELINES:
            raise ValueError(f"ineligible baseline key {key}")
    best_id: str | None = None
    best_loss: float | None = None
    for key in sorted(ELIGIBLE_BASELINES):
        value = losses.get(key)
        if value is None or not math.isfinite(value):
            continue
        if best_loss is None or value < best_loss:
            best_id = key
            best_loss = value
    return (best_id, best_loss)


def cluster_bootstrap(
    diffs: Sequence[float],
    clusters: Sequence[str],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Issuer-episode clustered bootstrap (scientific_freeze.dependence_rule)."""
    if len(diffs) != len(clusters):
        raise ValueError("diffs and clusters must have equal length")
    if not diffs:
        raise ValueError("diffs cannot be empty")
    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    for d in diffs:
        if not isinstance(d, (int, float)) or not math.isfinite(float(d)):
            raise ValueError("every diff must be a finite float")
    for c in clusters:
        if not isinstance(c, str) or not c:
            raise ValueError("every cluster key must be a non-empty str")

    keys = sorted(set(clusters))
    k = len(keys)
    key_to_idx = {key: i for i, key in enumerate(keys)}
    sums = [0.0] * k
    counts = [0.0] * k
    for diff, cluster in zip(diffs, clusters):
        idx = key_to_idx[cluster]
        sums[idx] = math.fsum([sums[idx], float(diff)])
        counts[idx] += 1.0

    s = np.array(sums, dtype=np.float64)
    c = np.array(counts, dtype=np.float64)
    mean = float(s.sum() / c.sum())

    rng = np.random.default_rng(seed)
    stats = np.empty(replicates, dtype=np.float64)
    for b in range(replicates):
        idx = rng.integers(0, k, size=k)
        stats[b] = s[idx].sum() / c[idx].sum()

    ci_low, ci_high = np.quantile(stats, [0.025, 0.975])
    p_value = (1 + int(np.count_nonzero(stats <= 0.0))) / (replicates + 1)
    ci_low_f = float(ci_low)
    ci_high_f = float(ci_high)
    return {
        "mean": mean,
        "ci_low": ci_low_f,
        "ci_high": ci_high_f,
        "p_value": float(p_value),
        "excludes_zero": ci_low_f > 0.0 or ci_high_f < 0.0,
        "replicates": replicates,
        "seed": seed,
        "n_rows": len(diffs),
        "n_clusters": k,
        "numpy_version": np.__version__,
    }


def cluster_key(
    issuer_ref: str,
    episode_id: str | None,
    event_cluster_id: str | None,
) -> str:
    """Build issuer-episode cluster key (scientific_freeze.dependence_rule)."""
    if not isinstance(issuer_ref, str) or not issuer_ref:
        raise ValueError("issuer_ref must be a non-empty str")
    if episode_id is None:
        return "issuer:" + issuer_ref
    return (
        "issuer:"
        + issuer_ref
        + "|episode:"
        + episode_id
        + "|event:"
        + (event_cluster_id or "")
    )


def date_block_keys(
    cutoff_sessions: Sequence[int],
    *,
    block: int = DATE_BLOCK_SESSIONS,
) -> list[str]:
    """Date-block cluster keys (scientific_freeze.dependence_rule)."""
    if not cutoff_sessions:
        raise ValueError("cutoff_sessions cannot be empty")
    if block < 1:
        raise ValueError("block must be at least 1")
    first = min(cutoff_sessions)
    return ["block:" + str((session - first) // block) for session in cutoff_sessions]


def episode_id(
    issuer_ref: str,
    metric: str,
    period: str,
    episode_start_session: str,
) -> str:
    """Episode identity hash (scientific_freeze.effective_n_rule)."""
    for name, value in (
        ("issuer_ref", issuer_ref),
        ("metric", metric),
        ("period", period),
        ("episode_start_session", episode_start_session),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty str")
    payload = json.dumps(
        [issuer_ref, metric, period, episode_start_session],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def by_family_decision(
    p_values: Sequence[float],
    *,
    q: float = BY_Q,
) -> dict[str, Any]:
    """Benjamini-Yekutieli family decision (multiple_testing)."""
    adjusted = benjamini_yekutieli(p_values)
    rejected = [a <= q for a in adjusted]
    return {
        "m": len(adjusted),
        "q": q,
        "adjusted": adjusted,
        "rejected": rejected,
    }


def assign_partitions(
    rows: Sequence[tuple[int, str | None, int | None]],
    boundary_session: int,
) -> dict[str, Any]:
    """Forward partition assignment (scientific_freeze.forward_partitions)."""
    n = len(rows)
    partitions_out: list[str] = [PRE_BOUNDARY] * n
    excluded: list[str | None] = [None] * n

    for _cutoff, episode_id_val, ep_start in rows:
        if episode_id_val is not None and ep_start is None:
            raise ValueError("episode_id requires episode_start_session")

    starts: dict[str, int | None] = {p: None for p in _COUNTING}
    closes: dict[str, int | None] = {p: None for p in _COUNTING}
    episode_counts: dict[str, int] = {p: 0 for p in _COUNTING}
    status: dict[str, str] = {p: "NOT_STARTED" for p in _COUNTING}

    by_session: dict[int, list[int]] = {}
    for i, (cutoff, _eid, _est) in enumerate(rows):
        if cutoff < boundary_session:
            partitions_out[i] = PRE_BOUNDARY
        else:
            by_session.setdefault(cutoff, []).append(i)

    # mode: COUNTING name, PURGE_1, PURGE_2, or SHADOW
    mode = "F_DEV"
    count_start = boundary_session
    episodes: set[str] = set()
    purge_end: int | None = None
    shadow_after: int | None = None

    starts["F_DEV"] = boundary_session
    status["F_DEV"] = "OPEN"

    def _count_row(name: str, idx: int, eid: str | None, est: int | None) -> None:
        partitions_out[idx] = name
        if eid is None:
            return
        if est is not None and est < count_start:
            excluded[idx] = "episode_started_before_partition"
            return
        if est is not None and est >= count_start:
            episodes.add(eid)

    def _close_counting(name: str, close_s: int) -> None:
        nonlocal mode, count_start, episodes, purge_end, shadow_after
        closes[name] = close_s
        status[name] = "CLOSED"
        episode_counts[name] = len(episodes)
        if name == "F_DEV":
            mode = "PURGE_1"
            purge_end = close_s + PURGE_SESSIONS
        elif name == "F_VAL":
            mode = "PURGE_2"
            purge_end = close_s + PURGE_SESSIONS
        elif name == "F_HOLD":
            mode = "SHADOW"
            shadow_after = close_s
            episodes = set()

    for s in sorted(by_session.keys()):
        if shadow_after is not None and s > shadow_after:
            for idx in by_session[s]:
                partitions_out[idx] = "PROSPECTIVE_SHADOW"
            continue

        if mode == "PURGE_1" and purge_end is not None and s > purge_end:
            mode = "F_VAL"
            count_start = purge_end + 1
            episodes = set()
            starts["F_VAL"] = count_start
            status["F_VAL"] = "OPEN"
            purge_end = None
        if mode == "PURGE_2" and purge_end is not None and s > purge_end:
            mode = "F_HOLD"
            count_start = purge_end + 1
            episodes = set()
            starts["F_HOLD"] = count_start
            status["F_HOLD"] = "OPEN"
            purge_end = None

        if mode == "PURGE_1":
            if purge_end is not None and s <= purge_end:
                for idx in by_session[s]:
                    partitions_out[idx] = "PURGE_1"
                if s == purge_end:
                    mode = "F_VAL"
                    count_start = purge_end + 1
                    episodes = set()
                    starts["F_VAL"] = count_start
                    status["F_VAL"] = "OPEN"
                continue
        if mode == "PURGE_2":
            if purge_end is not None and s <= purge_end:
                for idx in by_session[s]:
                    partitions_out[idx] = "PURGE_2"
                if s == purge_end:
                    mode = "F_HOLD"
                    count_start = purge_end + 1
                    episodes = set()
                    starts["F_HOLD"] = count_start
                    status["F_HOLD"] = "OPEN"
                continue

        if mode in _COUNTING:
            name = mode
            for idx in by_session[s]:
                _eid, _est = rows[idx][1], rows[idx][2]
                _count_row(name, idx, _eid, _est)
            episode_counts[name] = len(episodes)
            if len(episodes) >= EPISODE_FLOOR:
                _close_counting(name, s)

    return {
        "partitions": partitions_out,
        "excluded": excluded,
        "starts": starts,
        "closes": closes,
        "episode_counts": episode_counts,
        "status": status,
    }


def coverage_summary(
    row_statuses: Sequence[str],
    *,
    challenger_abstained: int,
) -> dict[str, Any]:
    """Coverage and abstention summary (scientific_freeze.coverage_rule)."""
    n_eligible = len(row_statuses)
    if challenger_abstained < 0 or challenger_abstained > n_eligible:
        raise ValueError("challenger_abstained out of range")
    n_scored = sum(1 for s in row_statuses if s == "SCORED")
    scored_fraction: float | None
    if n_eligible == 0:
        scored_fraction = None
    else:
        scored_fraction = n_scored / n_eligible
    by_reason: dict[str, int] = {}
    for s in row_statuses:
        if s == "SCORED":
            continue
        by_reason[s] = by_reason.get(s, 0) + 1
    by_reason = dict(sorted(by_reason.items()))
    abstention_fraction: float | None
    if n_eligible == 0:
        abstention_fraction = None
    else:
        abstention_fraction = challenger_abstained / n_eligible
    scored_floor_met = (
        scored_fraction is not None and scored_fraction >= SCORED_FRACTION_FLOOR
    )
    abstention_ok = (
        abstention_fraction is not None
        and abstention_fraction <= MAX_CHALLENGER_ABSTENTION
    )
    unestimable = not scored_floor_met or not abstention_ok
    return {
        "n_eligible": n_eligible,
        "n_scored": n_scored,
        "scored_fraction": scored_fraction,
        "by_reason": by_reason,
        "scored_floor_met": scored_floor_met,
        "challenger_abstention_fraction": abstention_fraction,
        "abstention_ok": abstention_ok,
        "unestimable": unestimable,
    }


def case_coverage(
    answered_cases: int,
    registered_cases: int = REGISTERED_MOTIVATING_CASES,
) -> dict[str, Any]:
    """Motivating case coverage (scientific_freeze.coverage_rule)."""
    if registered_cases < 1:
        raise ValueError("registered_cases must be at least 1")
    if answered_cases < 0 or answered_cases > registered_cases:
        raise ValueError("answered_cases out of range")
    fraction = answered_cases / registered_cases
    return {
        "answered": answered_cases,
        "registered": registered_cases,
        "fraction": fraction,
        "met": fraction >= CASE_COVERAGE_FLOOR,
    }
