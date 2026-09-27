"""Pure episode-aware evidence derivation for international Risk Radar.

This module reads no files and writes no state. It derives conservative independent
trial units from the existing canonical forward-log rows. A sparse-log 42-calendar-day
fallback is allowed only after observed quiet (for alert re-arm) or as a two-horizon
buffer (for base windows); gaps alone never manufacture an alert reset.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from engine.neuralweb.constitution import wilson_lower

ALERT_STATES = frozenset({"elevated", "risk-off"})
FORWARD_HORIZON_OBSERVATIONS = 21
CALENDAR_FALLBACK_DAYS = 42
WILSON_Z_ONE_SIDED_90 = 1.645


def parse_asof_date(value: Any) -> date | None:
    """Parse one canonical ISO session date, rejecting truncated junk."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    text = value.strip()
    if (
        len(text) < 10
        or text[4] != "-"
        or text[7] != "-"
        or not (text[:4] + text[5:7] + text[8:10]).isdigit()
    ):
        return None

    try:
        parsed = date.fromisoformat(text[:10])
        if len(text) == 10:
            return parsed
        if text[10] not in {"T", " "}:
            return None
        datetime.fromisoformat(
            text[:-1] + "+00:00" if text.endswith("Z") else text
        )
        return parsed
    except (TypeError, ValueError):
        return None


def _ordered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one valid canonical row per ISO session, preserving first-writer truth."""
    indexed: list[tuple[str, int, dict[str, Any]]] = []
    seen_sessions: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        parsed = parse_asof_date(row.get("asof"))
        if parsed is None:
            continue
        session = parsed.isoformat()
        if session in seen_sessions:
            continue
        seen_sessions.add(session)
        indexed.append((session, index, row))
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [row for _, _, row in indexed]


def _calendar_days(left_asof: str, right_asof: str) -> int | None:
    """Return elapsed calendar days for valid ISO dates, otherwise fail closed."""
    left = parse_asof_date(left_asof)
    right = parse_asof_date(right_asof)
    if left is None or right is None:
        return None
    return (right - left).days


def _is_alert(row: dict[str, Any]) -> bool:
    """Return the exact legacy row-gate alert flag."""
    return bool(row.get("alert"))


def _is_loud(row: dict[str, Any]) -> bool:
    """Return the episode-state definition; broader than the legacy alert flag."""
    return _is_alert(row) or row.get("state") in ALERT_STATES


def _is_graded(row: dict[str, Any]) -> bool:
    """Return the exact legacy truthy-grade predicate."""
    graded = row.get("graded")
    return isinstance(graded, dict) and bool(graded)


def _has_authority_outcome(row: dict[str, Any]) -> bool:
    """True only when a row has the binary outcome required by authority.v2."""
    graded = row.get("graded")
    return (
        isinstance(graded, dict)
        and isinstance(graded.get("any_dd5_within_h21"), bool)
    )


def _is_hit(row: dict[str, Any]) -> bool:
    graded = row.get("graded") or {}
    return bool(graded.get("any_dd5_within_h21"))


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _wilson_upper(hits: int, n: int, *, z: float = WILSON_Z_ONE_SIDED_90) -> float | None:
    if n <= 0:
        return None
    misses = n - hits
    return max(0.0, min(1.0, 1.0 - wilson_lower(misses, n, z=z)))


def _loud_episodes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse loud rows until 21 quiet observations or observed-quiet + 42 days."""
    episodes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    quiet_observations = 0

    for row in rows:
        if _is_loud(row):
            elapsed = (
                _calendar_days(current["last_loud_asof"], str(row["asof"]))
                if current is not None
                else None
            )
            rearmed = (
                current is None
                or quiet_observations >= FORWARD_HORIZON_OBSERVATIONS
                or (
                    quiet_observations > 0
                    and elapsed is not None
                    and elapsed >= CALENDAR_FALLBACK_DAYS
                )
            )
            if rearmed:
                current = {
                    "anchor": row,
                    "anchor_asof": str(row["asof"]),
                    "last_loud_asof": str(row["asof"]),
                    "loud_row_count": 1,
                }
                episodes.append(current)
            else:
                current["last_loud_asof"] = str(row["asof"])
                current["loud_row_count"] += 1
            quiet_observations = 0
        elif current is not None:
            quiet_observations += 1

    return episodes


def _independent_windows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select authority-complete anchors separated by 21 rows or 42 calendar days."""
    selected: list[dict[str, Any]] = []
    last_anchor_index: int | None = None
    last_anchor_asof: str | None = None
    for index, row in enumerate(rows):
        if not _has_authority_outcome(row):
            continue
        elapsed = (
            _calendar_days(last_anchor_asof, str(row["asof"]))
            if last_anchor_asof is not None
            else None
        )
        independent = (
            last_anchor_index is None
            or index - last_anchor_index >= FORWARD_HORIZON_OBSERVATIONS
            or (
                elapsed is not None
                and elapsed >= CALENDAR_FALLBACK_DAYS
            )
        )
        if independent:
            selected.append(row)
            last_anchor_index = index
            last_anchor_asof = str(row["asof"])
    return selected


def derive_evidence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive row descriptors and conservative episode-aware authority evidence."""
    # Preserve the exact raw pre-v2 denominator/base-rate inputs as an explicit
    # compatibility fence. The cleaned canonical view below may only be used by
    # the new episode contract; it must never silently replace legacy inputs.
    legacy_graded = [
        row for row in rows if isinstance(row, dict) and _is_graded(row)
    ]
    legacy_alerts = [row for row in legacy_graded if _is_alert(row)]
    legacy_alert_hits = sum(_is_hit(row) for row in legacy_alerts)
    legacy_base_hits = sum(_is_hit(row) for row in legacy_graded)
    legacy_incomplete_authority_rows = sum(
        not _has_authority_outcome(row) for row in legacy_graded
    )

    ordered = _ordered_rows(rows)
    graded = [row for row in ordered if _has_authority_outcome(row)]
    loud_rows = [row for row in graded if _is_alert(row)]
    row_hits = sum(_is_hit(row) for row in loud_rows)
    row_base_hits = sum(_is_hit(row) for row in graded)

    all_loud_episodes = _loud_episodes(ordered)
    matured_loud_episodes = [
        episode
        for episode in all_loud_episodes
        if _has_authority_outcome(episode["anchor"])
    ]
    unmatured_loud_episodes = [
        episode
        for episode in all_loud_episodes
        if not _has_authority_outcome(episode["anchor"])
    ]
    episode_hits = sum(_is_hit(episode["anchor"]) for episode in matured_loud_episodes)

    independent = _independent_windows(ordered)
    independent_hits = sum(_is_hit(row) for row in independent)

    episode_precision = _ratio(episode_hits, len(matured_loud_episodes))
    episode_base_rate = _ratio(independent_hits, len(independent))
    episode_precision_lower = (
        wilson_lower(
            episode_hits,
            len(matured_loud_episodes),
            z=WILSON_Z_ONE_SIDED_90,
        )
        if matured_loud_episodes
        else None
    )
    episode_base_upper = _wilson_upper(independent_hits, len(independent))
    episode_lift_lb = (
        episode_precision_lower / episode_base_upper
        if episode_precision_lower is not None
        and episode_base_upper is not None
        and episode_base_upper > 0.0
        else None
    )

    independent_asof = str(independent[-1]["asof"]) if independent else None
    loud_episode_asof = (
        str(matured_loud_episodes[-1]["anchor_asof"])
        if matured_loud_episodes
        else None
    )
    episode_evidence_asof = (
        min(independent_asof, loud_episode_asof)
        if independent_asof is not None and loud_episode_asof is not None
        else None
    )

    return {
        "legacy_n_total_graded_rows": len(legacy_graded),
        "legacy_n_alert_rows": len(legacy_alerts),
        "legacy_n_alert_hits": legacy_alert_hits,
        "legacy_n_incomplete_authority_rows": legacy_incomplete_authority_rows,
        "legacy_row_base_rate_dd5_h21": _ratio(
            legacy_base_hits, len(legacy_graded)
        ),
        "legacy_row_evidence_asof": (
            legacy_graded[-1].get("asof") if legacy_graded else None
        ),
        "n_total_graded_rows": len(graded),
        "n_loud_rows": len(loud_rows),
        "n_row_hits": row_hits,
        "daily_row_precision": _ratio(row_hits, len(loud_rows)),
        "row_base_rate_dd5_h21": _ratio(row_base_hits, len(graded)),
        "row_evidence_asof": str(graded[-1]["asof"]) if graded else None,
        "n_independent_episodes": len(independent),
        "n_independent_episode_hits": independent_hits,
        "independent_episode_anchors": [str(row["asof"]) for row in independent],
        "independent_evidence_asof": independent_asof,
        "n_loud_episodes": len(matured_loud_episodes),
        "n_episode_hits": episode_hits,
        "loud_episode_anchors": [
            str(episode["anchor_asof"]) for episode in matured_loud_episodes
        ],
        "loud_episode_evidence_asof": loud_episode_asof,
        "n_unmatured_loud_episodes": len(unmatured_loud_episodes),
        "unmatured_loud_episode_anchors": [
            str(episode["anchor_asof"]) for episode in unmatured_loud_episodes
        ],
        "episode_precision": episode_precision,
        "episode_precision_lower_90": episode_precision_lower,
        "episode_base_rate_dd5_h21": episode_base_rate,
        "episode_base_rate_upper_90": episode_base_upper,
        "episode_lift_lb": episode_lift_lb,
        "episode_evidence_asof": episode_evidence_asof,
    }
