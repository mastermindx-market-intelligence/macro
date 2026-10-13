"""Aggregate-only China heatmap health projection used by /api/status.

This is a leaf of the existing API health owner, not another monitor.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

def _status_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def status_projection(
    data: dict[str, Any] | None,
    *,
    now: datetime,
    age_min: float | None,
    served_baseline_asof: str | None,
) -> dict[str, Any]:
    """Project one live overlay to aggregate-only public health fields."""
    from engine.prophet_live import cn_clock

    current = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    expected_phase = cn_clock.phase(current)
    # The canonical phase calls both early morning and after-hours "closed".
    # Quotes are not required before today's open, or once the daily publisher
    # has already delivered today's settled session.
    source_required = expected_phase in {
        "morning", "session_break", "afternoon", "closing_auction", "post_close",
    } or (
        expected_phase == "closed"
        and cn_clock.cst_clock(current).time() >= cn_clock.SESSION_CLOSE
        and served_baseline_asof != cn_clock.session_date(current).isoformat()
    )
    if data is None:
        return {
            "status": "missing",
            "expected_phase": expected_phase,
            "source_required": source_required,
            "served_baseline_asof": served_baseline_asof,
        }
    generated = _status_datetime(data.get("generated_at"))
    source_observed = _status_datetime(data.get("source_observed_at"))
    try:
        expected_source = cn_clock.expected_latest_quote_time(current).astimezone(timezone.utc)
    except Exception:  # noqa: BLE001 - checker will fail closed on the null lag
        expected_source = None
    quotes = data.get("quotes")
    breadth = data.get("breadth")
    baseline_asof = data.get("baseline_asof")
    phase = data.get("phase")
    return {
        "schema": data.get("schema"),
        "age_min": age_min,
        "market": data.get("market"),
        "map_type": data.get("map_type"),
        "artifact_status": data.get("status"),
        "generated_at": data.get("generated_at"),
        "heartbeat_age_sec": (
            (current - generated).total_seconds() if generated is not None else None
        ),
        "baseline_asof": baseline_asof,
        "served_baseline_asof": served_baseline_asof,
        "baseline_ok": bool(
            isinstance(baseline_asof, str)
            and isinstance(served_baseline_asof, str)
            and baseline_asof == served_baseline_asof
        ),
        "session_date": data.get("session_date"),
        "phase": phase,
        "expected_phase": expected_phase,
        "phase_ok": phase == expected_phase,
        "source_required": source_required,
        "source": data.get("source"),
        "source_observed_at": data.get("source_observed_at"),
        "source_lag_sec": (
            (expected_source - source_observed).total_seconds()
            if expected_source is not None and source_observed is not None
            else None
        ),
        "requested": data.get("requested"),
        "resolved": data.get("resolved"),
        "quotes_count": len(quotes) if isinstance(quotes, dict) else None,
        "coverage": data.get("coverage"),
        "usable": data.get("usable"),
        "fallback": data.get("fallback"),
        "breadth_n": breadth.get("n") if isinstance(breadth, dict) else None,
        "breadth_adv": breadth.get("adv") if isinstance(breadth, dict) else None,
        "breadth_dec": breadth.get("dec") if isinstance(breadth, dict) else None,
        "breadth_flat": breadth.get("flat") if isinstance(breadth, dict) else None,
        "breadth_pct_up": breadth.get("pctUp") if isinstance(breadth, dict) else None,
    }


