"""Result composition and human-readable reporting for RPH-0."""
from __future__ import annotations

import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import Mapping

import pandas as pd

from lib.nyse_calendar import sessions_between
from .contracts import AUTHORITY, ArchiveReceipt, ContractError
from .metrics import build_surface, classify_temporal_shape, derive_half_life
from .survival import build_leader_episodes, kaplan_meier, quartile_transition_matrix

SCHEMA = "research.rotation_persistence_rph0.v1"
OPERATION_KEY = "leadership-persistence-rph0-20260910-sol-001"
DEFAULT_HORIZONS = (1, 2, 3, 5, 7, 10, 15, 20)
_FORBIDDEN_OWNER_ROOTS = ("data", "site", "engine", "config")


def validate_output_dir(out_dir: Path, *, repo_root: Path | None = None) -> Path:
    """Return a resolved research output directory or reject owner-plane writes."""
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[3]
    )
    candidate = Path(out_dir).expanduser().resolve()
    if candidate == root:
        raise ContractError("output directory cannot be the repository root")
    for owner in _FORBIDDEN_OWNER_ROOTS:
        owner_root = (root / owner).resolve()
        try:
            candidate.relative_to(owner_root)
        except ValueError:
            continue
        raise ContractError(f"output directory is inside forbidden owner root: {owner}/")
    if candidate.exists() and not candidate.is_dir():
        raise ContractError(f"output path exists and is not a directory: {candidate}")
    return candidate


def _quality(
    frames: Mapping[date, pd.DataFrame], receipt: ArchiveReceipt
) -> dict:
    dates = sorted(frames)
    expected = sessions_between(dates[0], dates[-1])
    missing = [session.isoformat() for session in expected if session not in frames]
    theme_counts = [len(frame) for frame in frames.values()]
    return {
        "state": "MEASURED" if dates else "INSUFFICIENT_HISTORY",
        "sessions_present": len(dates),
        "sessions_expected": len(expected),
        "session_coverage": len(dates) / len(expected) if expected else None,
        "missing_sessions": missing,
        "theme_count_min": min(theme_counts) if theme_counts else None,
        "theme_count_median": float(median(theme_counts)) if theme_counts else None,
        "theme_count_max": max(theme_counts) if theme_counts else None,
        "non_session_rows_dropped": list(receipt.non_session_rows),
        "duplicate_asof_rows_dropped": list(receipt.duplicate_asof_rows),
    }


def _curve_from_surface(surface: dict, window: str, metric: str) -> dict[int, float | None]:
    curve: dict[int, float | None] = {}
    for horizon, cell in surface.items():
        estimate = cell["windows"][window][metric]
        curve[int(horizon)] = estimate["mean"] if estimate["state"] == "MEASURED" else None
    return curve


def build_result(
    frames: Mapping[date, pd.DataFrame],
    receipt: ArchiveReceipt,
    *,
    produced_at: str,
    recent_sessions: int = 20,
    bootstrap_resamples: int = 2_000,
    bootstrap_seed: int = 20_260_910,
    min_pairs: int = 8,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> dict:
    """Compose the strict research result from already-normalized frames."""
    surface = build_surface(
        frames,
        horizons=horizons,
        recent_sessions=recent_sessions,
        min_pairs=min_pairs,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    transition = quartile_transition_matrix(frames)
    episodes = build_leader_episodes(frames)
    km = kaplan_meier(episodes)

    half_lives = {
        window: derive_half_life(_curve_from_surface(surface, window, "rank_rho"))
        for window in ("all", "recent", "prior")
    }
    recent_score_curve = _curve_from_surface(surface, "recent", "score_continuation_ic")
    shape = classify_temporal_shape(recent_score_curve)
    shape["basis"] = "published_score_continuation_ic"
    shape["curve"] = {
        str(horizon): value for horizon, value in sorted(recent_score_curve.items())
    }

    return {
        "schema_version": SCHEMA,
        "operation_key": OPERATION_KEY,
        "produced_at": produced_at,
        "source": receipt.to_dict(),
        "parameters": {
            "horizons_sessions": list(horizons),
            "recent_sessions": int(recent_sessions),
            "minimum_pair_count": int(min_pairs),
            "minimum_common_themes": 10,
            "minimum_common_fraction": 0.80,
            "minimum_breadth_fraction": 0.80,
            "bootstrap": {
                "method": "circular_moving_block",
                "resamples": int(bootstrap_resamples),
                "seed": int(bootstrap_seed),
                "interval": 0.90,
            },
        },
        "quality": _quality(frames, receipt),
        "surface": surface,
        "transition_matrix": transition,
        "residency": {
            "episodes": episodes,
            "kaplan_meier": km,
        },
        "half_life": half_lives,
        "temporal_shape": shape,
        "authority": dict(AUTHORITY),
        "notes": [
            "Measures persistence of published theme ranks, scores and breadth; it is not an economic-return backtest.",
            "The source archive is keep-first point-in-time model output; RPH-0 does not claim historical raw-membership reconstruction.",
            "Exact TradingView/MACD timeframe usefulness remains owned by WS:TEMPORAL-GRAIN-INTELLIGENCE and Prophet Entry Truth.",
            "A null half-life or insufficient cell is an honest successful result, not a pipeline failure.",
        ],
    }


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(result: dict) -> str:
    """Render a deterministic summary whose claims are bounded by the result contract."""
    source = result["source"]
    quality = result["quality"]
    shape = result["temporal_shape"]
    lines = [
        "# Leadership Persistence RPH-0",
        "",
        f"**Operation:** `{result['operation_key']}`  ",
        f"**Produced at:** `{result['produced_at']}`  ",
        "**Authority:** research/display context only; no rank, gate, size, trade, Prophet or Oracle authority.",
        "",
        "## Result",
        "",
        f"**Published-output temporal shape:** `{shape['label']}`",
        "",
        f"Short-horizon published-score continuation median: **{_fmt(shape.get('short_median'))}**.  ",
        f"Long-horizon published-score continuation median: **{_fmt(shape.get('long_median'))}**.",
        "",
        "This label describes the dynamics of the existing published theme scores. It is not a return forecast or a holding-period instruction.",
        "",
        "## Source and quality",
        "",
        f"- Source: `{source['source_path']}`",
        f"- SHA-256: `{source['source_sha256']}`",
        f"- Valid archive dates: {source['first_asof']} through {source['last_asof']} ({source['rows_valid']} rows)",
        f"- Exchange-session coverage: {_fmt(quality['session_coverage'])} ({quality['sessions_present']} of {quality['sessions_expected']})",
        f"- Theme count: min {quality['theme_count_min']}, median {_fmt(quality['theme_count_median'], 1)}, max {quality['theme_count_max']}",
        f"- Missing sessions inside range: {len(quality['missing_sessions'])}",
        "",
        "## Persistence surface",
        "",
        "| Horizon | Recent rank rho | Recent score continuation | Recent top-Q survival | Recent eligible anchors | All eligible anchors |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon in result["parameters"]["horizons_sessions"]:
        cell = result["surface"][str(horizon)]
        recent = cell["windows"]["recent"]
        rank = recent["rank_rho"]
        score = recent["score_continuation_ic"]
        overlap = recent["topq_overlap"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(horizon),
                    _fmt(rank["mean"]),
                    _fmt(score["mean"]),
                    _fmt(overlap["mean"]),
                    str(rank["n"]),
                    str(cell["pairs_eligible"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Honest half-life assessment",
            "",
            "| Window | State | Half-life, sessions | Starting rho | Half target |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for window in ("recent", "prior", "all"):
        item = result["half_life"][window]
        lines.append(
            f"| {window} | `{item['state']}` | {_fmt(item['half_life_sessions'], 2)} | "
            f"{_fmt(item['start_rho'])} | {_fmt(item['half_target'])} |"
        )

    km = result["residency"]["kaplan_meier"]
    lines.extend(
        [
            "",
            "## Top-quartile residency",
            "",
            f"- Episode rows: {len(result['residency']['episodes'])}",
            f"- KM state: `{km['state']}`",
            f"- KM eligible episodes: {km['n_episodes']} ({km['n_events']} observed exits; {km['n_right_censored']} right-censored)",
            f"- Left-censored episodes excluded from KM: {km['n_left_censored_excluded']}",
            f"- Median survival: {_fmt(km['median_survival_sessions'], 0)} sessions",
            "",
            "## One-session quartile transition probabilities",
            "",
            "| From \\ To | Q1 | Q2 | Q3 | Q4 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for source_label in ("Q1", "Q2", "Q3", "Q4"):
        row = result["transition_matrix"]["probabilities"][source_label]
        lines.append(
            f"| {source_label} | {_fmt(row['Q1'])} | {_fmt(row['Q2'])} | "
            f"{_fmt(row['Q3'])} | {_fmt(row['Q4'])} |"
        )

    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in result["notes"])
    lines.append("")
    return "\n".join(lines)


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
